#!/usr/bin/env python3
"""Static checks of the generated packs: every reference between files must
resolve, geometry/animation files must be well formed.  Exits 1 on errors."""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "packs", "AlienEvo_RP")
BP = os.path.join(ROOT, "packs", "AlienEvo_BP")
errors = []


def err(msg):
    errors.append(msg)


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        err(f"{path}: invalid JSON ({e})")
        return None


def tex_exists(base):
    return any(os.path.exists(os.path.join(RP, base + ext)) for ext in (".png", ".tga"))


def molang_ok(expr):
    if not isinstance(expr, str):
        return True
    depth = 0
    for ch in expr:
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            return False
    return depth == 0


# ------------------------------------------------------------- JSON files
for path in glob.glob(os.path.join(ROOT, "packs", "**", "*.json"), recursive=True):
    load(path)

# ------------------------------------------------------------- geometry
geometries = {}
for path in glob.glob(os.path.join(RP, "models", "**", "*.json"), recursive=True):
    d = load(path)
    if not d:
        continue
    if d.get("format_version") not in ("1.12.0", "1.16.0", "1.21.0"):
        err(f"{path}: unexpected geometry format {d.get('format_version')}")
    for g in d.get("minecraft:geometry", []):
        gid = g["description"]["identifier"]
        names = [b["name"] for b in g.get("bones", [])]
        if len(names) != len(set(names)):
            dup = sorted({n for n in names if names.count(n) > 1})
            err(f"{path}: duplicate bones {dup}")
        for b in g.get("bones", []):
            if "parent" in b and b["parent"] not in names:
                err(f"{path}: bone {b['name']} has unknown parent {b['parent']}")
            for c in b.get("cubes", []):
                if "size" not in c or "origin" not in c:
                    err(f"{path}: cube without origin/size in {b['name']}")
        geometries[gid] = set(names)

# ------------------------------------------------------------- render controllers
render_controllers = {}
for path in glob.glob(os.path.join(RP, "render_controllers", "*.json")):
    d = load(path) or {}
    render_controllers.update(d.get("render_controllers", {}))

# ------------------------------------------------------------- animations
animations = {}
for path in glob.glob(os.path.join(RP, "animations", "**", "*.json"), recursive=True):
    d = load(path) or {}
    for name, a in d.get("animations", {}).items():
        if name in animations:
            err(f"{path}: duplicate animation {name}")
        animations[name] = a
        for bone, chans in (a.get("bones") or {}).items():
            for ch, v in chans.items():
                if ch not in ("rotation", "position", "scale"):
                    err(f"{path}: {name}/{bone} unknown channel {ch}")
                frames = v.values() if isinstance(v, dict) and "post" not in v and "pre" not in v else [v]
                for fr in frames:
                    vals = [fr.get("pre"), fr.get("post")] if isinstance(fr, dict) else [fr]
                    if isinstance(fr, dict) and set(fr) - {"pre", "post", "lerp_mode"}:
                        err(f"{path}: {name}/{bone}/{ch} unknown keyframe keys {sorted(fr)}")
                    for val in vals:
                        if val is None:
                            continue
                        if isinstance(val, list):
                            if len(val) != 3 or any(not isinstance(x, (int, float, str)) for x in val):
                                err(f"{path}: {name}/{bone}/{ch} bad vector {val}")
                        elif not isinstance(val, (int, float, str)):
                            err(f"{path}: {name}/{bone}/{ch} bad value {val}")
                for expr in re.findall(r'"([^"]*)"', json.dumps(v)):
                    if not molang_ok(expr):
                        err(f"{path}: {name}/{bone} bad molang {expr}")

VANILLA_ANIMS = set()
_vp = os.path.join(ROOT, "tools", "data", "vanilla_animations.txt")
if os.path.exists(_vp):
    with open(_vp, encoding="utf-8") as f:
        VANILLA_ANIMS = {line.strip() for line in f if line.strip()}

controllers = {}
for path in glob.glob(os.path.join(RP, "animation_controllers", "**", "*.json"), recursive=True):
    d = load(path) or {}
    for name, c in d.get("animation_controllers", {}).items():
        controllers[name] = c
        states = c.get("states", {})
        if c.get("initial_state", "default") not in states:
            err(f"{path}: {name} initial state missing")
        for sname, st in states.items():
            for t in st.get("transitions", []):
                for target, cond in t.items():
                    if target not in states:
                        err(f"{path}: {name}.{sname} -> unknown state {target}")
                    if not molang_ok(cond):
                        err(f"{path}: bad molang {cond}")

# ------------------------------------------------------------- attachables / client entities
for path in glob.glob(os.path.join(RP, "attachables", "**", "*.json"), recursive=True) + \
        glob.glob(os.path.join(RP, "entity", "*.json")):
    d = load(path) or {}
    desc = (d.get("minecraft:attachable") or d.get("minecraft:client_entity") or {}).get("description", {})
    ident = desc.get("identifier", "")
    if ident == "minecraft:player":
        continue
    for k, t in desc.get("textures", {}).items():
        if not tex_exists(t):
            err(f"{path}: texture {t} missing")
    for k, g in desc.get("geometry", {}).items():
        if g not in geometries:
            err(f"{path}: geometry {g} missing")
    for rc in desc.get("render_controllers", []):
        name = rc if isinstance(rc, str) else next(iter(rc))
        if name not in render_controllers:
            err(f"{path}: render controller {name} missing")
            continue
        r = render_controllers[name]
        if r["geometry"].startswith("Array."):
            garrays = r.get("arrays", {}).get("geometries", {})
            arr = r["geometry"].split("[", 1)[0]
            if arr not in garrays:
                err(f"{path}: {name} uses undefined {arr}")
            for g in garrays.get(arr, []):
                if g.split(".", 1)[1] not in desc.get("geometry", {}):
                    err(f"{path}: {name} array {arr} uses {g} not defined")
        else:
            g = r["geometry"].split(".", 1)[1]
            if g not in desc.get("geometry", {}):
                err(f"{path}: {name} uses Geometry.{g} not defined")
        arrays = r.get("arrays", {}).get("textures", {})
        for t in r.get("textures", []):
            if t.startswith("Array."):
                arr = t.split("[", 1)[0]
                if arr not in arrays:
                    err(f"{path}: {name} uses undefined {arr}")
                if not molang_ok(t):
                    err(f"{path}: {name} bad molang {t}")
                continue
            if t.split(".", 1)[1] not in desc.get("textures", {}):
                err(f"{path}: {name} uses {t} not defined")
        for arr, items in arrays.items():
            for t in items:
                if t.split(".", 1)[1] not in desc.get("textures", {}):
                    err(f"{path}: {name} array {arr} uses {t} not defined")
        for m in r.get("materials", []):
            for v in m.values():
                if v.split(".", 1)[1] not in desc.get("materials", {}):
                    err(f"{path}: {name} uses {v} not defined")
    for short, full in desc.get("animations", {}).items():
        if full not in animations and full not in controllers and full not in VANILLA_ANIMS:
            err(f"{path}: animation {full} missing")
    for a in desc.get("scripts", {}).get("animate", []):
        short = a if isinstance(a, str) else next(iter(a))
        if short not in desc.get("animations", {}):
            err(f"{path}: animate {short} not in animations")
    if path.endswith(".json") and "attachables" in path:
        item = os.path.join(BP, "items", ident.split(":")[1] + ".json")
        if not os.path.exists(item):
            err(f"{path}: no item {ident}")

# ------------------------------------------------------------- items / blocks / textures
item_tex = (load(os.path.join(RP, "textures", "item_texture.json")) or {}).get("texture_data", {})
terrain = (load(os.path.join(RP, "textures", "terrain_texture.json")) or {}).get("texture_data", {})
for k, v in list(item_tex.items()) + list(terrain.items()):
    if not tex_exists(v["textures"]):
        err(f"atlas {k}: texture {v['textures']} missing")
lang = {}
with open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8") as f:
    for line in f:
        if "=" in line:
            k, v = line.rstrip("\n").split("=", 1)
            lang[k] = v
for path in glob.glob(os.path.join(BP, "items", "*.json")):
    d = load(path) or {}
    item = d.get("minecraft:item", {})
    ident = item["description"]["identifier"]
    icon = item["components"].get("minecraft:icon")
    if icon not in item_tex:
        err(f"{path}: icon {icon} not in item_texture.json")
    if f"item.{ident}" not in lang:
        err(f"{path}: no name in en_US.lang")
for path in glob.glob(os.path.join(BP, "blocks", "*.json")):
    d = load(path) or {}
    blk = d.get("minecraft:block", {})
    ident = blk["description"]["identifier"]
    for mi in blk["components"].get("minecraft:material_instances", {}).values():
        if mi["texture"] not in terrain:
            err(f"{path}: texture {mi['texture']} not in terrain_texture.json")
    geo = blk["components"].get("minecraft:geometry")
    if geo and geo not in geometries and not geo.startswith("minecraft:geometry."):
        err(f"{path}: geometry {geo} missing")
    if f"tile.{ident}.name" not in lang:
        err(f"{path}: no name in en_US.lang")

# ------------------------------------------------------------- sounds / scripts
sounds = (load(os.path.join(RP, "sounds", "sound_definitions.json")) or {}).get("sound_definitions", {})
for name, sd in sounds.items():
    for s in sd["sounds"]:
        if not os.path.exists(os.path.join(RP, s["name"] + ".ogg")):
            err(f"sound {name}: file {s['name']} missing")
script_text = ""
for path in glob.glob(os.path.join(BP, "scripts", "*.js")):
    with open(path, encoding="utf-8") as f:
        script_text += f.read()
for s in set(re.findall(r'"(alienevo\.[a-z0-9_.]+)"', script_text)):
    if s not in sounds:
        err(f"script uses unknown sound {s}")
for s in set(re.findall(r'"textures/([a-z0-9_/]+)"', script_text)):
    if not s.startswith("ui/") and not tex_exists("textures/" + s):
        err(f"script uses unknown texture textures/{s}")
for s in set(re.findall(r"`textures/ui/aliens/\$\{", script_text)):
    pass

# ------------------------------------------------------------- features
features = {}
for path in glob.glob(os.path.join(BP, "features", "*.json")):
    d = load(path) or {}
    for kind, body in d.items():
        if kind == "format_version":
            continue
        features[body["description"]["identifier"]] = body
        if kind == "minecraft:structure_template_feature":
            ns, name = body["structure_name"].split(":")
            if not os.path.exists(os.path.join(BP, "structures", ns, name + ".mcstructure")):
                err(f"{path}: structure {body['structure_name']} missing")
        if kind == "minecraft:single_block_feature" and body["places_block"].startswith("alienevo:"):
            if not os.path.exists(os.path.join(BP, "blocks", body["places_block"].split(":")[1] + ".json")):
                err(f"{path}: block {body['places_block']} missing")
for path in glob.glob(os.path.join(BP, "feature_rules", "*.json")):
    d = load(path) or {}
    rule = d.get("minecraft:feature_rules", {})
    if rule.get("description", {}).get("places_feature") not in features:
        err(f"{path}: feature {rule.get('description', {}).get('places_feature')} missing")
for path in glob.glob(os.path.join(BP, "structures", "**", "*.mcstructure"), recursive=True):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from nbt import Reader
    with open(path, "rb") as f:
        st = Reader(f.read(), little=True).root()
    size = st["size"]
    idx = st["structure"]["block_indices"]
    pal = st["structure"]["palette"]["default"]["block_palette"]
    if len(idx) != 2 or any(len(layer) != size[0] * size[1] * size[2] for layer in idx):
        err(f"{path}: block_indices do not match size {size}")
    if any(i >= len(pal) for layer in idx for i in layer):
        err(f"{path}: palette index out of range")
    for key, pd in st["structure"]["palette"]["default"]["block_position_data"].items():
        lt = pd.get("block_entity_data", {}).get("LootTable")
        if lt and lt.startswith("loot_tables/alienevo/") and not os.path.exists(os.path.join(BP, lt)):
            err(f"{path}: loot table {lt} missing")

# ------------------------------------------------------------- particles
particles = set()
for path in glob.glob(os.path.join(RP, "particles", "*.json")):
    d = load(path) or {}
    pe = d.get("particle_effect", {})
    particles.add(pe.get("description", {}).get("identifier"))
    tex = pe.get("description", {}).get("basic_render_parameters", {}).get("texture")
    if tex and not tex_exists(tex):
        err(f"{path}: texture {tex} missing")
for pid in set(re.findall(r'"(alienevo:[a-z_0-9]+)"', script_text)):
    if pid.split(":")[1] in ("energy_bolt", "boulder") or pid.startswith("alienevo:form_"):
        continue
    if any(pid in x for x in [script_text]) and re.search(rf'particle\([^)]*"{pid}"|trail: "{pid}"|impact: "{pid}"|FIRE = "{pid}"', script_text):
        if pid not in particles:
            err(f"script uses unknown particle {pid}")

# ------------------------------------------------------------- manifests
for pack in (BP, RP):
    m = load(os.path.join(pack, "manifest.json")) or {}
    if m.get("header", {}).get("min_engine_version") != [1, 26, 50]:
        err(f"{pack}: min_engine_version is not 1.26.50")

# ------------------------------------------------------------- content log checks
# Problems Bedrock reported in the content log of a real game.
for pack in (BP, RP):
    m = load(os.path.join(pack, "manifest.json")) or {}
    versions = [m.get("header", {}).get("version", [])] + [x.get("version", []) for x in m.get("modules", [])]
    versions += [d.get("version") for d in m.get("dependencies", []) if isinstance(d.get("version"), list)]
    for v in versions:
        if any(not isinstance(x, int) or x < 0 or x > 65535 for x in v):
            err(f"{pack}: version {v} has a part above 65535 (pack import fails)")
for path in glob.glob(os.path.join(RP, "entity", "*.json")):
    desc = (load(path) or {}).get("minecraft:client_entity", {}).get("description", {})
    if not desc.get("render_controllers"):
        err(f"{path}: no render controllers")
for path in glob.glob(os.path.join(RP, "render_controllers", "*.json")):
    for name, rc in ((load(path) or {}).get("render_controllers") or {}).items():
        for pv in rc.get("part_visibility", []):
            if any("->" in str(x) for x in pv.values()):
                err(f"{name}: '->' in part_visibility")
for path in glob.glob(os.path.join(RP, "**", "*.json"), recursive=True):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if "c.owning_entity" in text or "context.owning_entity" in text:
        err(f"{path}: c.owning_entity is unknown in attachables")
for path in glob.glob(os.path.join(RP, "render_controllers", "*.json")):
    with open(path, encoding="utf-8") as f:
        if re.search(r"\bc\.(is_first_person|item_slot)", f.read()):
            err(f"{path}: context variables are unknown in render controllers")
for path in glob.glob(os.path.join(RP, "attachables", "**", "*.json"), recursive=True):
    desc = (load(path) or {}).get("minecraft:attachable", {}).get("description", {})
    for full in desc.get("animations", {}).values():
        if full.startswith("controller."):
            err(f"{path}: attachable uses animation controller {full} (looked up on the wearer)")
for path in glob.glob(os.path.join(BP, "recipes", "*.json")):
    d = load(path) or {}
    for key in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
        if key in d and "unlock" not in d[key]:
            err(f"{path}: recipe without unlock")
for path in glob.glob(os.path.join(BP, "blocks", "*.json")):
    comps = (load(path) or {}).get("minecraft:block", {}).get("components", {})
    if ("minecraft:material_instances" in comps) != ("minecraft:geometry" in comps):
        err(f"{path}: block needs both geometry and material_instances")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sanitize  # noqa: E402
for user, bone in sanitize.skeleton_problems(RP):
    err(f"{user}: skeleton clash on {bone}")
for fname, anim in sanitize.animation_problems(RP):
    err(f"{fname}: {anim} has keyframes Bedrock rejects")

if errors:
    print("\n".join(errors))
    print(f"{len(errors)} error(s)")
    sys.exit(1)
print(f"OK: {len(geometries)} geometries, {len(animations)} animations, {len(controllers)} controllers, "
      f"{len(render_controllers)} render controllers, {len(sounds)} sounds")
