"""Final clean-up of the generated resource pack, for errors Bedrock reports
in its content log that the converters cannot see one model at a time.

Geometry: Bedrock merges the skeletons of every geometry of an attachable or
client entity, and bone names are case-insensitive.  A bone that appears
twice with different parents (GeckoLib "Head" under the armour bone "head",
or the same bone in two parts) makes a loop ("Infinite loop detected in
geometry skeletal hierarchy") and the model is not drawn.  Locators of the
same name in several geometries are dropped too.

Animations: GeckoLib keyframes that Bedrock rejects (easing names in place
of values, catmullrom with Molang values, a keyframe object without a time,
an empty bone list).
"""
import glob
import json
import os
import re

EASING = re.compile(r"^(ease[A-Za-z]*|linear|step|catmullrom|bezier)$", re.I)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ------------------------------------------------------------------ geometry

def _rename(bones, bone, new):
    old = bone["name"]
    for b in bones:
        if b.get("parent") == old:
            b["parent"] = new
    bone["name"] = new


def fix_skeleton(geos):
    """geos: list of geometry dicts merged by one attachable/entity (in
    render order).  Returns the number of renamed bones."""
    renamed = 0
    parents = {}  # lower name -> lower parent (first definition wins)
    for gi, geo in enumerate(geos):
        bones = geo.get("bones", [])
        for b in bones:
            b.pop("locators", None)
        local = set()
        for b in bones:
            low = b["name"].lower()
            par = b.get("parent")
            lpar = par.lower() if par else None
            clash = low in local or (low in parents and parents[low] != lpar) or lpar == low
            if clash:
                base = f"{b['name']}_p{gi}"
                new, n = base, 1
                taken = {x["name"].lower() for x in bones} | set(parents)
                while new.lower() in taken:
                    n += 1
                    new = f"{base}_{n}"
                _rename(bones, b, new)
                renamed += 1
                low = new.lower()
            local.add(low)
        for b in bones:
            par = b.get("parent")
            parents.setdefault(b["name"].lower(), par.lower() if par else None)
    return renamed


def fix_geometries(rp):
    files = {}
    by_id = {}
    for path in glob.glob(os.path.join(rp, "models", "**", "*.json"), recursive=True):
        data = _load(path)
        files[path] = data
        for g in data.get("minecraft:geometry", []):
            by_id[g["description"]["identifier"]] = (path, g)
    touched = set()
    renamed = 0
    users = glob.glob(os.path.join(rp, "attachables", "**", "*.json"), recursive=True) + \
        glob.glob(os.path.join(rp, "entity", "*.json"))
    for path in sorted(users):
        data = _load(path)
        desc = (data.get("minecraft:attachable") or data.get("minecraft:client_entity") or {}).get("description", {})
        ids = [g for g in desc.get("geometry", {}).values() if g in by_id]
        geos = [by_id[g][1] for g in ids]
        renamed += fix_skeleton(geos)
        touched |= {by_id[g][0] for g in ids}
    for path in touched:
        _save(path, files[path])
    return renamed


def skeleton_problems(rp):
    """For validate.py: (user, bone) pairs that would still clash."""
    by_id = {}
    for path in glob.glob(os.path.join(rp, "models", "**", "*.json"), recursive=True):
        for g in _load(path).get("minecraft:geometry", []):
            by_id[g["description"]["identifier"]] = g
    out = []
    users = glob.glob(os.path.join(rp, "attachables", "**", "*.json"), recursive=True) + \
        glob.glob(os.path.join(rp, "entity", "*.json"))
    for path in sorted(users):
        data = _load(path)
        desc = (data.get("minecraft:attachable") or data.get("minecraft:client_entity") or {}).get("description", {})
        parents, locators = {}, {}
        for gid in desc.get("geometry", {}).values():
            g = by_id.get(gid)
            if not g:
                continue
            seen = set()
            for b in g.get("bones", []):
                low = b["name"].lower()
                par = (b.get("parent") or "").lower() or None
                if low in seen or par == low or (low in parents and parents[low] != par):
                    out.append((os.path.basename(path), b["name"]))
                seen.add(low)
                parents.setdefault(low, par)
                for loc, val in (b.get("locators") or {}).items():
                    if loc in locators and locators[loc] != val:
                        out.append((os.path.basename(path), f"locator {loc}"))
                    locators.setdefault(loc, val)
    return out


# ------------------------------------------------------------------ animations

def _is_molang(v):
    return isinstance(v, str) and not re.fullmatch(r"\s*-?[\d.]+\s*", v)


def _clean_vector(v):
    """None if the value is unusable."""
    if isinstance(v, list):
        if any(isinstance(x, str) and EASING.match(x.strip()) for x in v):
            vals = [0 if isinstance(x, str) and EASING.match(x.strip()) else x for x in v]
            return None if all(isinstance(x, str) and EASING.match(x.strip()) for x in v) else vals
        return v
    if isinstance(v, str) and EASING.match(v.strip()):
        return None
    return v


def _keyframe_value(kf):
    if isinstance(kf, dict):
        return kf.get("post", kf.get("pre"))
    return kf


def clean_channel(ch):
    """Returns the cleaned channel or None to drop it."""
    if isinstance(ch, dict):
        if not any(re.fullmatch(r"-?[\d.]+", k) for k in ch):
            # A single keyframe object without a time ({"post": ..., "lerp_mode": ...}).
            return clean_channel(_keyframe_value(ch))
        out = {}
        for t, kf in ch.items():
            if not re.fullmatch(r"-?[\d.]+", t):
                continue
            if isinstance(kf, dict):
                kf = {k: v for k, v in kf.items() if k in ("pre", "post", "lerp_mode")}
                for k in ("pre", "post"):
                    if k in kf:
                        kf[k] = _clean_vector(kf[k])
                        if kf[k] is None:
                            del kf[k]
                if "pre" not in kf and "post" not in kf:
                    continue
            else:
                kf = _clean_vector(kf)
                if kf is None:
                    continue
            out[t] = kf
        if not out:
            return None
        # Bedrock only knows linear and catmullrom.  A GeckoLib "step" keyframe
        # holds the previous value until its time: {"pre": previous, "post": value}.
        prev = None
        for t in sorted(out, key=float):
            kf = out[t]
            value = _keyframe_value(kf)
            if isinstance(kf, dict) and kf.get("lerp_mode") not in (None, "linear", "catmullrom"):
                step = kf.get("lerp_mode") == "step"
                kf = {k: v for k, v in kf.items() if k != "lerp_mode"}
                if step and prev is not None and "pre" not in kf:
                    kf = {"pre": prev, "post": kf.get("post", value)}
                out[t] = kf if set(kf) != {"post"} else kf["post"]
            prev = value
        # Bedrock precomputes catmullrom curves: every keyframe must be constant.
        values = [_keyframe_value(kf) for kf in out.values()]
        flat = [x for v in values for x in (v if isinstance(v, list) else [v])]
        if any(isinstance(kf, dict) and kf.get("lerp_mode") == "catmullrom" for kf in out.values()) and \
                any(_is_molang(x) for x in flat):
            out = {t: (_keyframe_value(kf) if isinstance(kf, dict) and set(kf) <= {"post", "pre", "lerp_mode"}
                       and kf.get("lerp_mode") == "catmullrom" else kf) for t, kf in out.items()}
        return out
    return _clean_vector(ch)


def clean_animation(anim):
    bones = anim.get("bones")
    if isinstance(bones, dict):
        for name in list(bones):
            chans = bones[name]
            for c in list(chans):
                if c in ("rotation", "position", "scale"):
                    v = clean_channel(chans[c])
                    if v is None:
                        del chans[c]
                    else:
                        chans[c] = v
            if not chans:
                del bones[name]
        if not bones:
            # Bedrock needs at least one bone entry.
            anim["bones"] = {"alienevo_none": {"rotation": [0, 0, 0]}}


def fix_animations(rp):
    n = 0
    for path in glob.glob(os.path.join(rp, "animations", "**", "*.json"), recursive=True):
        data = _load(path)
        before = json.dumps(data, sort_keys=True)
        for anim in data.get("animations", {}).values():
            clean_animation(anim)
        if json.dumps(data, sort_keys=True) != before:
            _save(path, data)
            n += 1
    return n


def animation_problems(rp):
    out = []
    for path in glob.glob(os.path.join(rp, "animations", "**", "*.json"), recursive=True):
        for name, anim in _load(path).get("animations", {}).items():
            copy = json.loads(json.dumps(anim))
            clean_animation(copy)
            if copy != anim:
                out.append((os.path.basename(path), name))
    return out
