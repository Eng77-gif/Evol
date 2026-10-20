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


# Movement animations found by name in the alien's animation files.
# (state, regex on the short animation name, owner condition)
MOVEMENT = [
    ("fly", r"(^|_)(flight|fly|flying|hover)(_on)?$", "c.owning_entity->v.alienevo_fly"),
    ("swim", r"(swim_fast|tail_swim|swim)$", "c.owning_entity->q.is_swimming"),
    ("sprint", r"^sprint\d*$", "c.owning_entity->q.is_sprinting && c.owning_entity->q.is_on_ground"),
    ("walk", r"^walk$", "c.owning_entity->q.modified_move_speed > 0.1 && c.owning_entity->q.is_on_ground"),
]


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
        if name in loops:
            converted[new]["loop"] = True
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
    if triggers:
        states = {"default": {"transitions": []}}
        if fixed_index:
            index = {t: fixed_index[t] for t in triggers if t in fixed_index}
        else:
            index = {t: i for i, t in enumerate(triggers, start=1)}
        for trig, (name, mode) in triggers.items():
            if trig not in index:
                continue
            i = index[trig]
            animations[f"t{i}"] = names[name]
            states["default"]["transitions"].append({f"t{i}": f"{OWNER_VAR} == {i}"})
            hold = mode in ("then_play_and_hold", "then_loop") or sources[name].get("loop") in (True, "hold_on_last_frame")
            transitions = [{f"t{j}": f"{OWNER_VAR} == {j}"} for j in index.values() if j != i]
            if not hold:
                transitions.append({"default": f"q.all_animations_finished && {OWNER_VAR} != {i}"})
            states[f"t{i}"] = {"animations": [f"t{i}"], "transitions": transitions, "blend_transition": 0.15}
        ctrl = f"controller.animation.alienevo.{key}"
        controllers[ctrl] = {"initial_state": "default", "states": states}
        animations["triggers"] = ctrl
        animate.append("triggers")

    if movement:
        states = {"default": {"transitions": [{state: cond} for state, (_, cond) in movement.items()]}}
        for state, (name, cond) in movement.items():
            animations[f"move_{state}"] = names[name]
            # Higher priority states (earlier in MOVEMENT) can interrupt lower ones.
            others = [{s: c} for s, (_, c) in movement.items() if s != state]
            states[state] = {"animations": [f"move_{state}"], "blend_transition": 0.2,
                             "transitions": [{"default": f"!({cond})"}] + others}
        ctrl = f"controller.animation.alienevo.{key}.movement"
        controllers[ctrl] = {"initial_state": "default", "states": states}
        animations["movement"] = ctrl
        animate.append("movement")

    if controllers:
        write_json(os.path.join(ctrl_dir, f"{key}.controller.json"),
                   {"format_version": "1.10.0", "animation_controllers": controllers})
    return animations, animate, index


def signal_animations(count, path):
    anims = {
        # Flight state for the movement controllers (kept until switched off).
        "animation.alienevo.flight.on": {"animation_length": 0.05, "timeline": {"0.0": "v.alienevo_fly = 1;"}},
        "animation.alienevo.flight.off": {"animation_length": 0.05, "timeline": {"0.0": "v.alienevo_fly = 0;"}},
    }
    for i in range(1, count + 1):
        anims[f"animation.alienevo.signal.{i}"] = {
            "animation_length": 0.3,
            "timeline": {"0.0": f"v.alienevo_anim = {i};", "0.25": "v.alienevo_anim = 0;"},
        }
    write_json(path, {"format_version": "1.8.0", "animations": anims})
