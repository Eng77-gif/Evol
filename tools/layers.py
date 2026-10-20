"""Resolve Palladium render layers (GeckoLib) of AlienEvo and its add-ons.

A render layer file describes an alien as a list of GeckoLib layers, each with
a model, a texture (with variables and transformers), optional conditions and
an animation controller.  This module evaluates those layers for the default
state of an alien (Prototype uniform, no ability active) so the result can be
turned into a Bedrock attachable.
"""
import io
import json
import re
import zipfile

from PIL import Image


class VFS:
    """All jars merged; later jars override earlier ones (add-ons over base)."""

    def __init__(self, paths):
        self.files = {}
        self.versions = {}
        for path in paths:
            z = zipfile.ZipFile(path)
            for name in z.namelist():
                if not name.endswith("/"):
                    self.files[name] = z
                    self.versions.setdefault(name, []).append(z)

    def exists(self, name):
        return name in self.files

    def read(self, name):
        return self.files[name].read(name)

    def json(self, name):
        text = self.read(name).decode("utf-8-sig")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Some add-on files contain // comments or trailing commas.
            text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
            text = re.sub(r",(\s*[}\]])", r"\1", text)
            return json.loads(text)

    def all_json(self, name):
        """Every jar's copy of a file (e.g. sounds.json is merged, not replaced)."""
        out = []
        for z in self.versions.get(name, []):
            text = z.read(name).decode("utf-8-sig")
            text = re.sub(r",(\s*[}\]])", r"\1", text)
            out.append(json.loads(text))
        return out

    def image(self, name):
        return Image.open(io.BytesIO(self.read(name))).convert("RGBA")

    def names(self, prefix):
        return [n for n in self.files if n.startswith(prefix)]


def rl_path(ref, kind=""):
    """'ns:path' -> 'assets/ns/path'."""
    if ref is None:
        return None
    ns, path = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
    return f"assets/{ns}/{path}"


# Default values of the variables used in texture/model paths.
VAR_CHOICES = {
    "UNIFORM": ["prototype", "default"],
    "BADGE": ["prototype"],
    "WATCHSTATE": ["default"],
}
GENERIC_CHOICES = ["-1", "0", "", "prototype", "default", "1", "purple", "green"]


def substitute(vfs, path):
    """Replace #VARS in a path with the first combination that exists."""
    if path is None:
        return None
    names = re.findall(r"#([A-Z0-9]+)", path)
    if not names:
        return path if vfs.exists(path) else None

    def rec(p, rest):
        if not rest:
            return p if vfs.exists(p) else None
        name = rest[0]
        for choice in VAR_CHOICES.get(name, GENERIC_CHOICES):
            r = rec(p.replace("#" + name, choice, 1), rest[1:])
            if r:
                return r
        return None

    return rec(path, names)


def evaluate(cond, scores=None):
    """Evaluate a Palladium condition for an alien in its idle default state.

    `scores` overrides scoreboard objectives (e.g. AlienEvo.10kPhase = 1)."""
    scores = scores or {}
    if isinstance(cond, bool):
        return cond
    if isinstance(cond, list):
        return all(evaluate(c, scores) for c in cond)
    t = cond.get("type", "")
    if t == "palladium:not":
        return not evaluate(cond.get("conditions", []), scores)
    if t == "palladium:or":
        return any(evaluate(c, scores) for c in cond.get("conditions", []))
    if t == "palladium:and":
        return all(evaluate(c, scores) for c in cond.get("conditions", []))
    if t in ("palladium:ability_integer_property", "palladium:integer_property", "palladium:objective_score"):
        lo = cond.get("min", cond.get("min_score", -(10 ** 9)))
        hi = cond.get("max", cond.get("max_score", 10 ** 9))
        value = scores.get(cond.get("objective", ""), 0)
        return lo <= value <= hi
    if t in ("alienevo:uniform_type", "alienevo:watch_type"):
        return cond.get("value") == "prototype"
    if t == "alienevo:has_timeout_bubble":
        return cond.get("value") is False
    # ability_enabled, ability_unlocked, crouching, is_swimming, has_power, ...
    return False


def layer_visible(layer, scores=None):
    for key in ("conditions", "third_person_conditions"):
        if key in layer and not evaluate(layer[key], scores):
            return False
    return True


def flatten(layer, scores=None):
    if layer.get("type") == "palladium:compound":
        if not layer_visible(layer, scores):
            return []
        out = []
        for sub in layer.get("layers", []):
            out += flatten(sub, scores)
        return out
    return [layer] if layer_visible(layer, scores) else []


def build_texture(vfs, tex):
    """Texture of a layer with overlay / alpha mask transformers applied."""
    base = tex.get("base") if isinstance(tex, dict) else tex
    path = substitute(vfs, rl_path(base))
    if not path:
        return None, None
    img = vfs.image(path)
    if isinstance(tex, dict):
        for tr in tex.get("transformers", []):
            t = tr.get("type")
            if t == "palladium:overlay":
                op = substitute(vfs, rl_path(tr.get("overlay")))
                if op:
                    ov = vfs.image(op)
                    if ov.size != img.size:
                        ov = ov.resize(img.size, Image.NEAREST)
                    img = Image.alpha_composite(img, ov)
            elif t == "palladium:alpha_mask":
                mp = substitute(vfs, rl_path(tr.get("mask")))
                if mp:
                    mask = vfs.image(mp)
                    if mask.size != img.size:
                        mask = mask.resize(img.size, Image.NEAREST)
                    a = img.getchannel("A")
                    ma = mask.getchannel("A")
                    from PIL import ImageChops
                    img.putalpha(ImageChops.multiply(a, ma))
    return img, path


def resolve(vfs, layer_file, scores=None):
    """Return the visible layers of a render layer file.

    [{geo, image, tex_path, glow, anim_file, loops, triggers}]
    """
    data = vfs.json(layer_file)
    out = []
    for layer in flatten(data, scores):
        if layer.get("type") != "geckolib:default":
            continue
        model = layer.get("model")
        # Player-model layers give a "normal" and a "slim" (Alex) model.
        mbase = (model.get("base") or model.get("normal")) if isinstance(model, dict) else model
        geo = substitute(vfs, rl_path(mbase))
        if not geo:
            continue
        img, tex_path = build_texture(vfs, layer.get("texture"))
        if img is None:
            continue
        loops, triggers = [], {}
        for ctrl in layer.get("animation_controller", []) or []:
            if ctrl.get("triggers"):
                for trig, val in ctrl["triggers"].items():
                    if isinstance(val, list):
                        v = val[0] if val else {}
                        triggers[trig] = (v.get("animation"), v.get("type", "then_play"))
                    else:
                        triggers[trig] = (val, "then_play")
            elif ctrl.get("animation"):
                loops.append(ctrl["animation"])
        anim = layer.get("animation_file")
        out.append({
            "geo": geo,
            "image": img,
            "tex_path": tex_path,
            "glow": layer.get("render_type") in ("glow", "eyes"),
            "translucent": layer.get("render_type") in ("translucent", "entity_translucent"),
            "anim_file": rl_path(anim) if anim else None,
            "loops": loops,
            "triggers": triggers,
        })
    return out
