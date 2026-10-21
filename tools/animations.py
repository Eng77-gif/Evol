"""Convert GeckoLib alien animations into Bedrock attachable animations.

* Looping controllers of the Palladium render layer (idle, tail, wings...) are
  played all the time by the attachable.
* Triggered animations (bite, beam, ball_in...) are played by an animation
  controller of the attachable.  The server script sets the synced player
  property alienevo:anim = n for a moment, which the attachable reads through
  c.owning_entity->q.property('alienevo:anim').
"""
import json
import math
import os
import re

BONE_MAP = {
    "armorHead": "head",
    "armorBody": "body",
    "armorLeftArm": "leftArm",
    "armorRightArm": "rightArm",
    "armorLeftLeg": "leftLeg",
    "armorRightLeg": "rightLeg",
}

LERP = {"linear": "linear", "step": "step"}
# Synced player property set by the server script (see BP entities/player.json).
# An attachable reads the wearer's state through public variables of the
# player client entity (build_player_entity), like vanilla v.attack_time.
OWNER_VAR = "v.alienevo_anim"

# Ticks each trigger keeps alienevo:anim set (-1 = held until the next
# trigger), per model key; written to anim_data.js for the scripts.
TRIGGER_TICKS = {}


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def sanitize(name):
    name = name.lower()
    for prefix in ("animation.", "anim."):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return re.sub(r"[^a-z0-9_.]", "_", name)


def molang(v):
    """GeckoLib accepts a few things Bedrock does not."""
    if isinstance(v, str):
        v = v.replace("query.anim_time", "q.anim_time")
        v = v.strip() or "0"
    return v


def convert_value(v):
    if isinstance(v, list):
        return [molang(x) for x in v]
    if isinstance(v, (int, float, str)):
        return molang(v)
    return v


def convert_channel(ch):
    if not isinstance(ch, dict):
        return convert_value(ch)
    # Either a single keyframe object ({"vector": ...}) or a time -> keyframe map.
    if "vector" in ch or "post" in ch:
        return convert_keyframe(ch)
    out = {}
    for t, kf in ch.items():
        try:
            key = str(round(float(t), 4))
        except ValueError:
            continue
        out[key] = convert_keyframe(kf)
    return out


def convert_keyframe(kf):
    if not isinstance(kf, dict):
        return convert_value(kf)
    if "vector" in kf:
        easing = str(kf.get("easing", "linear")).lower()
        lerp = LERP.get(easing, "catmullrom" if easing != "linear" else "linear")
        if lerp == "linear":
            return convert_value(kf["vector"])
        return {"post": convert_value(kf["vector"]), "lerp_mode": lerp}
    out = {}
    for k in ("pre", "post"):
        if k in kf:
            v = kf[k]
            # GeckoLib also writes {"post": {"vector": [...]}}.
            if isinstance(v, dict):
                v = v.get("vector", [0, 0, 0])
            out[k] = convert_value(v)
    if "lerp_mode" in kf and kf["lerp_mode"] in ("linear", "catmullrom", "step"):
        out["lerp_mode"] = kf["lerp_mode"]
    return out


def convert_animation(anim, renames=None):
    out = {}
    # override_previous_animation is dropped: on Bedrock it would also wipe
    # the motion the bones inherit from the wearer (walking, punching).
    for k in ("loop", "animation_length", "blend_weight", "anim_time_update"):
        if k in anim:
            out[k] = anim[k]
    bones = {}
    for bone, chans in (anim.get("bones") or {}).items():
        b = {}
        for ch in ("rotation", "position", "scale"):
            if ch in chans:
                b[ch] = convert_channel(chans[ch])
        if b:
            name = (renames or {}).get(bone) or BONE_MAP.get(bone, bone)
            bones[name] = b
    out["bones"] = bones
    return out


# Movement animations found by name in the alien's animation files.
# (state, regex on the short animation name, owner condition)
MOVEMENT = [
    ("fly", r"(^|_)(flight|fly|flying|hover)(_on)?$", "v.alienevo_fly"),
    ("swim", r"(swim_fast|tail_swim|swim)$", "v.alienevo_swim"),
    ("sprint", r"^sprint\d*$", "v.alienevo_sprint && v.alienevo_ground"),
    ("walk", r"^walk$", "v.alienevo_speed > 0.1 && v.alienevo_ground"),
]


def _first_last_scale(channel):
    """(scale at the first keyframe, scale at the last keyframe) or None."""
    def val(v):
        if isinstance(v, dict):
            v = v.get("post", v.get("pre", v.get("vector")))
            if isinstance(v, dict):
                v = v.get("vector")
        if isinstance(v, (int, float)):
            return [v, v, v]
        if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
            return v
        return None
    if isinstance(channel, dict) and not ({"post", "pre", "vector"} & set(channel)):
        keys = []
        for k, v in channel.items():
            try:
                keys.append((float(k), v))
            except ValueError:
                pass
        if not keys:
            return None, None
        keys.sort(key=lambda x: x[0])
        return val(keys[0][1]), val(keys[-1][1])
    v = val(channel)
    return v, v


def hidden_at_rest(trigger_anims):
    """Bones that GeckoLib shows only during an ability (scaled to 0 at rest).

    A bone is hidden when an "on" animation starts with it at scale 0 (the
    part pops in during the ability)."""
    hidden, shown = set(), set()
    for name, anim in trigger_anims.items():
        ending = any(w in short(name) for w in ("off", "out", "close", "end", "unextend", "stop"))
        for bone, chans in (anim.get("bones") or {}).items():
            if "scale" not in chans:
                continue
            if ending:
                continue
            first, last = _first_last_scale(chans["scale"])
            zero = lambda v: v is not None and all(abs(x) < 1e-3 for x in v)
            # Pops in: keyframed from 0 to a visible size.
            if zero(first) and last is not None and not zero(last):
                hidden.add(bone)
    return hidden


def short(name):
    return name.split(".")[-1].lower()


def build_alien_animations(vfs, key, layers, anim_dir, ctrl_dir, renames=None, fixed_index=None):
    """Returns (attachable animations map, animate list, {trigger: index}).

    fixed_index: use this trigger numbering (shared by several attachables)."""
    sources = {}
    loops, triggers = [], {}
    loops_taken = False
    all_anims = {}
    for layer in layers:
        f = layer["anim_file"]
        if not f or not vfs.exists(f):
            continue
        anims = vfs.json(f).get("animations", {})
        for n, a in anims.items():
            all_anims.setdefault(n, a)
        # Idle loops of the main (first animated) layer only: other layers of
        # the same alien may hold alternative poses (e.g. cloak on / off).
        if not loops_taken and layer["loops"]:
            loops_taken = True
            for name in layer["loops"]:
                if name in anims and name not in loops:
                    loops.append(name)
                    sources[name] = anims[name]
        for trig, (name, mode) in layer["triggers"].items():
            if name in anims and trig not in triggers:
                triggers[trig] = (name, mode)
                sources[name] = anims[name]

    # Movement states (fly / swim / sprint / walk) from every animation of the
    # alien that the render layer does not already use.  Triggers that the Java
    # mod fired on movement (sprinting, walking, flight_on) become states too.
    movement = {}
    for trig in list(triggers):
        name, _ = triggers[trig]
        t = trig.lower()
        if t.endswith("nt") or "off" in t:
            if any(k in t for k in ("sprint", "walk", "flight")):
                del triggers[trig]
            continue
        for state, _, cond in MOVEMENT:
            key_word = {"fly": "flight", "swim": "swim", "sprint": "sprint", "walk": "walk"}[state]
            if key_word in t and state not in movement:
                movement[state] = (name, cond)
                del triggers[trig]
                break
    used = set(loops) | {n for n, _ in triggers.values()} | {n for n, _ in movement.values()}
    for state, pattern, cond in MOVEMENT:
        if state in movement:
            continue
        for name, anim in all_anims.items():
            if name in used or short(name).endswith("nt") or "off" in short(name):
                continue
            if re.search(pattern, short(name)):
                movement[state] = (name, cond)
                sources[name] = anim
                used.add(name)
                break
    # Keep the original order of MOVEMENT (priority) and register the sources.
    movement = {state: movement[state] for state, _, _ in MOVEMENT if state in movement}
    for name, _ in movement.values():
        sources[name] = all_anims[name]
    if not sources:
        return {}, [], {}

    converted = {}
    names = {}
    for name, anim in sources.items():
        new = f"animation.alienevo.{key}.{sanitize(name)}"
        names[name] = new
        converted[new] = convert_animation(anim, renames)
        if name in loops and converted[new].get("loop") is not True:
            # A looping controller keeps animations that drive themselves with
            # q.anim_time running; keyframed ones keep their own loop mode
            # (e.g. "hold_on_last_frame" for a pose like cloak_on).
            uses_time = "anim_time" in json.dumps(anim)
            converted[new]["loop"] = True if uses_time else converted[new].get("loop", "hold_on_last_frame")
    for state, (name, _) in movement.items():
        conv = converted[names[name]]
        # Poses such as "flight_on" are held, everything else loops.
        if conv.get("loop") not in (True, "hold_on_last_frame"):
            conv["loop"] = "hold_on_last_frame" if short(name).endswith("_on") else True
    write_json(os.path.join(anim_dir, f"{key}.animation.json"), {"format_version": "1.8.0", "animations": converted})

    animations, animate = {}, []
    for i, name in enumerate(loops):
        animations[f"loop{i}"] = names[name]
        animate.append(f"loop{i}")
    controllers = {}

    index = {}
    rest_bones = hidden_at_rest({n: sources[n] for n, _ in triggers.values()})
    if rest_bones:
        rest = f"animation.alienevo.{key}.rest_pose"
        converted[rest] = {"loop": True, "bones": {
            ((renames or {}).get(b) or BONE_MAP.get(b, b)): {"scale": 0} for b in sorted(rest_bones)}}
        write_json(os.path.join(anim_dir, f"{key}.animation.json"), {"format_version": "1.8.0", "animations": converted})
        animations["rest"] = rest
    # Attachables cannot use animation controllers (the game looks their
    # animations up on the wearer), so everything is a conditional entry of
    # scripts.animate and trigger animations restart through anim_time_update.
    if rest_bones:
        animate.append({"rest": f"{OWNER_VAR} == 0"})
    if triggers:
        if fixed_index:
            index = {t: fixed_index[t] for t in triggers if t in fixed_index}
        else:
            index = {t: i for i, t in enumerate(triggers, start=1)}
        ticks = TRIGGER_TICKS.setdefault(key, {})
        for trig, (name, mode) in triggers.items():
            if trig not in index:
                continue
            i = index[trig]
            src = converted[names[name]]
            anim = json.loads(json.dumps(src))
            hold = mode in ("then_play_and_hold", "then_loop") or src.get("loop") in (True, "hold_on_last_frame")
            if mode == "then_loop" or src.get("loop") is True:
                anim["loop"] = True
            elif hold:
                anim["loop"] = "hold_on_last_frame"
            anim["anim_time_update"] = f"({OWNER_VAR} == {i}) ? (q.anim_time + q.delta_time) : 0.0"
            tname = f"{names[name]}.t{i}"
            converted[tname] = anim
            animations[f"t{i}"] = tname
            animate.append({f"t{i}": f"{OWNER_VAR} == {i}"})
            length = float(src.get("animation_length", 1.0) or 1.0)
            ticks[i] = -1 if hold else int(math.ceil(length * 20)) + 2
        write_json(os.path.join(anim_dir, f"{key}.animation.json"), {"format_version": "1.8.0", "animations": converted})

    if movement:
        earlier = []
        for state, (name, cond) in movement.items():
            animations[f"move_{state}"] = names[name]
            # Higher priority states (earlier in MOVEMENT) win.
            full = " && ".join([f"({cond})"] + [f"!({c})" for c in earlier])
            animate.append({f"move_{state}": full})
            earlier.append(cond)

    if controllers:
        write_json(os.path.join(ctrl_dir, f"{key}.controller.json"),
                   {"format_version": "1.10.0", "animation_controllers": controllers})
    return animations, animate, index
