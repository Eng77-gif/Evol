"""Convert GeckoLib alien animations into Bedrock attachable animations.

* Looping controllers of the Palladium render layer (idle, tail, wings...) are
  played all the time by the attachable.
* Triggered animations (bite, beam, ball_in...) are played by an animation
  controller of the attachable.  The server script starts them with
  Player.playAnimation("animation.alienevo.signal.<n>"); that animation only
  sets the public player variable v.alienevo_anim = n for a moment, which the
  attachable reads through c.owning_entity.
"""
import json
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
OWNER_VAR = "c.owning_entity->v.alienevo_anim"


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
            out[k] = convert_value(kf[k])
    if "lerp_mode" in kf and kf["lerp_mode"] in ("linear", "catmullrom", "step"):
        out["lerp_mode"] = kf["lerp_mode"]
    return out


def convert_animation(anim, renames=None):
    out = {}
    for k in ("loop", "animation_length", "override_previous_animation", "blend_weight", "anim_time_update"):
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


def build_alien_animations(vfs, key, layers, anim_dir, ctrl_dir, renames=None):
    """Returns (attachable animations map, animate list, {trigger: index})."""
    sources = {}
    loops, triggers = [], {}
    loops_taken = False
    for layer in layers:
        f = layer["anim_file"]
        if not f or not vfs.exists(f):
            continue
        anims = vfs.json(f).get("animations", {})
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
    if not sources:
        return {}, [], {}

    converted = {}
    names = {}
    for name, anim in sources.items():
        new = f"animation.alienevo.{key}.{sanitize(name)}"
        names[name] = new
        converted[new] = convert_animation(anim, renames)
        if name in loops:
            converted[new]["loop"] = True
    write_json(os.path.join(anim_dir, f"{key}.animation.json"), {"format_version": "1.8.0", "animations": converted})

    animations, animate = {}, []
    for i, name in enumerate(loops):
        animations[f"loop{i}"] = names[name]
        animate.append(f"loop{i}")

    index = {}
    if triggers:
        states = {"default": {"transitions": []}}
        trig_list = list(triggers.items())
        for i, (trig, _) in enumerate(trig_list, start=1):
            index[trig] = i
        for i, (trig, (name, mode)) in enumerate(trig_list, start=1):
            animations[f"t{i}"] = names[name]
            states["default"]["transitions"].append({f"t{i}": f"{OWNER_VAR} == {i}"})
            hold = mode in ("then_play_and_hold", "then_loop") or sources[name].get("loop") in (True, "hold_on_last_frame")
            transitions = [{f"t{j}": f"{OWNER_VAR} == {j}"} for j in range(1, len(trig_list) + 1) if j != i]
            if not hold:
                transitions.append({"default": f"q.all_animations_finished && {OWNER_VAR} != {i}"})
            states[f"t{i}"] = {"animations": [f"t{i}"], "transitions": transitions, "blend_transition": 0.15}
        ctrl = f"controller.animation.alienevo.{key}"
        write_json(os.path.join(ctrl_dir, f"{key}.controller.json"), {
            "format_version": "1.10.0",
            "animation_controllers": {ctrl: {"initial_state": "default", "states": states}},
        })
        animations["triggers"] = ctrl
        animate.append("triggers")
    return animations, animate, index


def signal_animations(count, path):
    anims = {}
    for i in range(1, count + 1):
        anims[f"animation.alienevo.signal.{i}"] = {
            "animation_length": 0.3,
            "timeline": {"0.0": f"v.alienevo_anim = {i};", "0.25": "v.alienevo_anim = 0;"},
        }
    write_json(path, {"format_version": "1.8.0", "animations": anims})
