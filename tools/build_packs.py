#!/usr/bin/env python3
"""Convert the AlienEvo Fabric (Palladium/KubeJS) jar into a Bedrock add-on.

Usage:
    python3 tools/build_packs.py AlienEvo-1.1.3-fabric.jar [addon.jar ...]

Add-on jars (Into The Omniverse, Omni Extras, The Anur Trio, Wildvine,
Aliens Untapped, Chromastone) add new aliens and animations.

The script regenerates every *generated* file of packs/AlienEvo_RP and
packs/AlienEvo_BP (textures, geometry, attachables, sounds, items, blocks,
recipes, language files).  Hand written files (scripts, manifests, the player
client entity, loot tables, features) are left untouched.  Finally it zips both
packs into dist/AlienEvo.mcaddon.
"""
import glob
import io
import json
import math
import os
import re
import shutil
import sys
import zipfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animations import TRIGGER_TICKS, build_alien_animations
from icons import render_icon
from layers import VFS, resolve
import sanitize
import structures

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "packs", "AlienEvo_RP")
BP = os.path.join(ROOT, "packs", "AlienEvo_BP")
DIST = os.path.join(ROOT, "dist")

ITEM_FORMAT = "1.21.90"
BLOCK_FORMAT = "1.21.90"

# Java armor bone -> Bedrock player bone.  Attachable bones that share a name
# with a bone of the player skeleton follow that bone's animation.
BONE_MAP = {
    "armorHead": "head",
    "armorBody": "body",
    "armorLeftArm": "leftArm",
    "armorRightArm": "rightArm",
    "armorLeftLeg": "leftLeg",
    "armorRightLeg": "rightLeg",
}

BOOT_PARENT = {"armorLeftBoot": "leftLeg", "armorRightBoot": "rightLeg"}

AE = "assets/alienevo"
AF = "assets/afomni"
T_AL = AE + "/textures/models/aliens"
G_AL = AE + "/geo/aliens"
BADGE_TEX = AE + "/textures/models/badge"

# Omnitrix glow palette (prototype default) used to tint white glow masks.
GLOW = ["b3ff40", "a7f72e", "8ed721", "77b81a", "639d11"]


# Every alien: render layer file of the Java mods (resolved by layers.py).
# "scale" comes from global.alienevo_scale_N (55 == player size).
L = "assets/alienevo/palladium/render_layers/aliens"
ALIENS = [
    dict(id=1, key="pyronite", name="Heatblast", scale=57, layer=f"{L}/alien_1/pyronite.json"),
    dict(id=2, key="vulpimancer", name="Wildmutt", scale=52, layer=f"{L}/alien_2/vulpimancer.json"),
    dict(id=3, key="petrosapien", name="Diamondhead", scale=62, layer=f"{L}/alien_3/petrosapien.json"),
    dict(id=4, key="kineceleran", name="XLR8", scale=65, layer=f"{L}/alien_4/kineceleran.json"),
    dict(id=5, key="galvan", name="Grey Matter", scale=50, layer=f"{L}/alien_5/galvan.json"),
    dict(id=6, key="tetramand", name="Four Arms", scale=75, layer=f"{L}/alien_6/tetramand.json"),
    dict(id=7, key="lepidopterran", name="Stinkfly", scale=37, layer=f"{L}/alien_7/lepidopterran.json"),
    dict(id=8, key="piscciss_volann", name="Ripjaws", scale=60, layer=f"{L}/alien_8/piscciss_volann.json"),
    dict(id=9, key="galvanic_mechamorph", name="Upgrade", scale=65, layer=f"{L}/alien_9/galvanic_mechamorph.json"),
    dict(id=10, key="ectonurite", name="Ghostfreak", scale=68, layer=f"{L}/alien_10/ectonurite.json"),
    dict(id=11, key="arburian_pelarota", name="Cannonbolt", scale=45, layer=f"{L}/alien_11/arburian_pelarota.json"),
    dict(id=31, key="methanosian", name="Swampfire", scale=55, layer="assets/afomni/palladium/render_layers/methanosian.json"),
    dict(id=32, key="sonorosian", name="Echo Echo", scale=55, layer="assets/afomni/palladium/render_layers/sonorosian.json"),
    dict(id=33, key="vaxasaurian", name="Humungousaur", scale=55, layer="assets/afomni/palladium/render_layers/vaxasaurian.json"),
    dict(id=34, key="aerophibian", name="Jetray", scale=55, layer=f"{L}/alien_34/aerophibian.json"),
    dict(id=35, key="necrofriggian", name="Big Chill", scale=55, layer="assets/afomni/palladium/render_layers/necrofriggian_cloak.json"),
    # Chromastone add-on replaces the old afomni model.
    dict(id=36, key="crystalsapien", name="Chromastone", scale=55, layer="assets/chromastone/palladium/render_layers/crystalsapien.json"),
    dict(id=80, key="nucleonix", name="Atomix", scale=55, layer=f"{L}/alien_60/atomix.json"),
    dict(id=100, key="dragonoid", name="Dragonoid", scale=55, layer=f"{L}/alien_100/dragonoid.json"),
    dict(id=101, key="astrobot", name="Astro Bot", scale=55, layer=f"{L}/alien_101/astrobot.json"),
    # Omni Extras
    dict(id=110, key="opticoid", name="Eye Guy", scale=70, layer="assets/omni_extras/palladium/render_layers/opticoid.json"),
    dict(id=111, key="perkgourmand", name="Upchuck (Perk)", scale=40, layer="assets/omni_extras/palladium/render_layers/perk_gourmand.json"),
    dict(id=112, key="murkgourmand", name="Upchuck (Murk)", scale=40, layer="assets/omni_extras/palladium/render_layers/murk_gourmand.json"),
    dict(id=190, key="talpaedan", name="Armodrillo", scale=55, layer="assets/omni_extras/palladium/render_layers/talpaedan.json"),
    dict(id=192, key="orishan", name="Water Hazard", scale=60, layer="assets/omni_extras/palladium/render_layers/orishan.json"),
    dict(id=193, key="amperi", name="Ampfibian", scale=55, layer="assets/omni_extras/palladium/render_layers/amperi.json"),
    dict(id=299, key="nosedeenian", name="Buzzshock", scale=55, layer="assets/omni_extras/palladium/render_layers/nosedeenian.json"),
    # The Anur Trio
    dict(id=209, key="loboan", name="Benwolf", scale=57, layer="assets/anur/palladium/render_layers/loboan.json"),
    dict(id=211, key="transylian", name="Frankenstrike", scale=57, layer="assets/anur/palladium/render_layers/transylian.json"),
    # Wildvine
    dict(id=222, key="florauna", name="Wildvine", scale=70, layer="assets/florauna/palladium/render_layers/aliens/alien_222/florauna.json"),
    # Aliens Untapped
    dict(id=200, key="merlinisapien", name="Chamalien", scale=60, layer="assets/untapped/palladium/render_layers/aliens/alien_200/merlinisapien.json"),
    dict(id=201, key="ickthyperambuloid", name="Walkatrout", scale=60, layer="assets/untapped/palladium/render_layers/aliens/alien_201/ickthyperambuloid.json"),
    dict(id=202, key="splixson", name="Ditto", scale=60, layer="assets/untapped/palladium/render_layers/aliens/alien_202/splixson.json"),
    dict(id=203, key="oryctini", name="Eatle", scale=60, layer="assets/untapped/palladium/render_layers/aliens/alien_203/oryctini.json"),
    # Into The Omniverse
    dict(id=501, key="sonorosian_ov", name="Echo Echo (Omniverse)", scale=55, layer="assets/aeo/palladium/render_layers/aliens/alien_32/sonorosian.json"),
    dict(id=503, key="necrofriggian_ov", name="Big Chill (Omniverse)", scale=55, layer="assets/aeo/palladium/render_layers/aliens/alien_35/necrofriggian_cloak.json"),
]

COLORS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
          "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black"]


def crystal_suffix(color):
    return "" if color == "lime" else "_" + color


# Simple items: (id, texture, max_stack, extra components)
def simple_items():
    items = []
    for c in COLORS:
        items.append((f"upgrade_crystal{crystal_suffix(c)}", f"upgrade_crystal{crystal_suffix(c)}", 64, {"tags": ["alienevo:upgrade_crystals"]}))
        items.append((f"upgrade_shards{crystal_suffix(c)}", f"upgrade_shards{crystal_suffix(c)}", 64, {"tags": ["alienevo:upgrade_shards"]}))
    for name in ["galvan_scrap", "galvan_metal", "upgrade_chip", "machine_key", "machine_urn"]:
        items.append((name, name, 64, {}))
    items += [
        ("plumber_badge", "plumber_badge", 1, {}),
        ("machine_scroll", "machine_scroll", 1, {}),
        ("code_tablet", "code_tablet", 1, {"custom": "alienevo:code_tablet"}),
        ("code_tablet_selfdestruct", "code_tablet_selfdestruct", 1, {"custom": "alienevo:code_tablet"}),
        ("smithing_template_galvan", "smithing_template_galvan", 64, {}),
        ("prototype_core", "prototype_core", 1, {"glint": True}),
    ]
    return items


OMNITRIX_ITEMS = [
    # id, base texture, glow layers, tier
    ("prototype_omnitrix", "prototype_omnitrix", ["prototype_omnitrix_glow_1", "prototype_omnitrix_glow_2"], 0),
    ("prototype_omnitrix_phase1", "prototype_omnitrix_phase1", ["prototype_omnitrix_glow_1", "prototype_omnitrix_glow_2"], 1),
    ("prototype_omnitrix_phase2", "prototype_omnitrix_phase2", ["prototype_omnitrix_glow_1", "prototype_omnitrix_glow_2"], 2),
    ("prototype_omnitrix_10k", "10k_omnitrix", ["10k_omnitrix_glow_1", "10k_omnitrix_glow_2"], 3),
    # Same powers as the 10k; recalibrated at the workbench (attachable: build_recal).
    ("recal_omnitrix", "recal_omnitrix", ["recal_omnitrix_glow_1", "recal_omnitrix_glow_2"], 3),
]

# Galvan tools: tier "level 3, 1756 uses, speed 8, +3 damage" (better than iron).
TOOLS = [
    ("galvan_sword", "sword", 8),
    ("galvan_pickaxe", "pickaxe", 6),
    ("galvan_axe", "axe", 9),
    ("galvan_shovel", "shovel", 5),
    ("galvan_hoe", "hoe", 4),
    ("ancient_staff", "staff", 9),
]


class Jar:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.names = set(self.z.namelist())

    def read(self, name):
        return self.z.read(name)

    def json(self, name):
        return json.loads(self.read(name).decode("utf-8"))

    def image(self, name):
        return Image.open(io.BytesIO(self.read(name))).convert("RGBA")

    def exists(self, name):
        return name in self.names


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def save_png(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)


def reset_dir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)


def tint(img, hex_color):
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    px = img.load()
    out = Image.new("RGBA", img.size)
    po = out.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            pr, pg, pb, pa = px[x, y]
            po[x, y] = (pr * r // 255, pg * g // 255, pb * b // 255, pa)
    return out


def composite(images):
    size = (max(i.size[0] for i in images), max(i.size[1] for i in images))
    out = Image.new("RGBA", size)
    for im in images:
        if im.size != size:
            im = im.resize(size, Image.NEAREST)
        out = Image.alpha_composite(out, im)
    return out


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def convert_geo(src, identifier, renames=None):
    """GeckoLib armor geometry -> attachable geometry.

    armorHead/armorBody/... become the player bone names so they follow the
    player's animation.  A bone that already uses one of those names is renamed
    (recorded in `renames`, used for the animations too).
    """
    geo = src["minecraft:geometry"][0]
    desc = dict(geo["description"])
    desc["identifier"] = identifier
    names = {b["name"] for b in geo.get("bones", [])}
    rename = dict(BONE_MAP)
    # Bedrock bone names are case-insensitive: GeckoLib "Head" collides with
    # the armour bone renamed to "head".
    lower = {n.lower() for n in names}
    for old in list(names):
        if old in BONE_MAP:
            continue
        target = next((v for k, v in BONE_MAP.items() if v.lower() == old.lower() and k in names), None)
        if target is not None:
            new = old + "_inner"
            while new.lower() in lower:
                new += "_"
            lower.add(new.lower())
            rename[old] = new
    if renames is not None:
        renames.update({k: v for k, v in rename.items() if k not in BONE_MAP})
    bones = []
    for bone in geo.get("bones", []):
        bone = dict(bone)
        bone["name"] = rename.get(bone["name"], bone["name"])
        if "parent" in bone:
            bone["parent"] = rename.get(bone["parent"], bone["parent"])
        elif bone["name"] in BOOT_PARENT:
            bone["parent"] = BOOT_PARENT[bone["name"]]
        bones.append(bone)
    # Per-face uv_rotation needs the 1.21.0 geometry format.
    fmt = "1.21.0" if '"uv_rotation"' in json.dumps(bones) else "1.12.0"
    return {"format_version": fmt, "minecraft:geometry": [{"description": desc, "bones": bones}]}


def java_block_model_to_geo(model, identifier, tex_size):
    """Convert a Java block model (elements) into Bedrock block geometry."""
    tw, th = tex_size
    su, sv = tw / 16.0, th / 16.0
    cubes = []
    for el in model["elements"]:
        f, t = el["from"], el["to"]
        size = [t[0] - f[0], t[1] - f[1], t[2] - f[2]]
        # Blockbench: Java x is mirrored on export to Bedrock, blocks are centred on 8,0,8.
        origin = [8 - t[0], f[1], f[2] - 8]
        cube = {"origin": origin, "size": size, "uv": {}}
        rot = el.get("rotation")
        if rot and rot.get("angle"):
            o = rot["origin"]
            axis = {"x": 0, "y": 1, "z": 2}[rot["axis"]]
            r = [0, 0, 0]
            r[axis] = rot["angle"]
            cube["pivot"] = [8 - o[0], o[1], o[2] - 8]
            cube["rotation"] = [-r[0], -r[1], r[2]]
        for face, data in el.get("faces", {}).items():
            uv = data.get("uv")
            if uv is None:
                continue
            u0, v0, u1, v1 = uv[0] * su, uv[1] * sv, uv[2] * su, uv[3] * sv
            u, v, w, h = u0, v0, u1 - u0, v1 - v0
            if face in ("up", "down"):
                u, v, w, h = u + w, v + h, -w, -h
            cube["uv"][face] = {"uv": [round(u, 4), round(v, 4)], "uv_size": [round(w, 4), round(h, 4)]}
        cubes.append(cube)
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {"identifier": identifier, "texture_width": tw, "texture_height": th,
                            "visible_bounds_width": 2, "visible_bounds_height": 2.5, "visible_bounds_offset": [0, 0.75, 0]},
            "bones": [{"name": "block", "pivot": [0, 0, 0], "cubes": cubes}],
        }],
    }


# --------------------------------------------------------------------------
# Resource pack
# --------------------------------------------------------------------------

# In first person only the alien's arms are drawn (they replace the player's
# own first person arm, see build_player_entity).
FIRST_PERSON_ARMS = [{"*": "!v.alienevo_fp"}, {"rightArm": "1.0"}]

# Render controllers of an attachable cannot use context variables
# (c.is_first_person, c.owning_entity), so the attachable copies what it
# needs into its own variables first; queries there ask the wearer.
FORM_VARS = ["v.alienevo_fp = c.is_first_person;"]


def watch_vars():
    omni = ", ".join(f"'alienevo:{i[0]}'" for i in OMNITRIX_ITEMS)
    out = FORM_VARS + [
        "v.alienevo_alien = q.equipped_item_any_tag('slot.armor.chest', 'alienevo:alien_form');",
        f"v.alienevo_offhand = q.is_item_name_any('slot.weapon.offhand', 0, {omni});",
        "v.alienevo_wv = q.property('alienevo:wv');",
        "v.alienevo_sel = q.property('alienevo:sel');",
        "v.alienevo_glow = q.property('alienevo:glow');",
    ]
    return out + [f"v.alienevo_col{i} = q.property('alienevo:col{i}');" for i in range(len(WATCH_SLOTS))]


WATCH_COND = "(!v.alienevo_fp || v.alienevo_offhand || v.alienevo_wv) && !v.alienevo_alien"


def is_translucent(img):
    a = img.getchannel("A")
    hist = a.histogram()
    partial = sum(hist[1:255])
    return partial > 0.01 * img.size[0] * img.size[1]


def build_aliens(vfs, lang):
    geo_dir = os.path.join(RP, "models", "entity", "aliens")
    tex_dir = os.path.join(RP, "textures", "entity", "aliens")
    att_dir = os.path.join(RP, "attachables", "aliens")
    anim_dir = os.path.join(RP, "animations", "aliens")
    ctrl_dir = os.path.join(RP, "animation_controllers", "aliens")
    icon_dir = os.path.join(RP, "textures", "ui", "aliens")
    for d in (geo_dir, tex_dir, att_dir, anim_dir, ctrl_dir, icon_dir):
        reset_dir(d)

    controllers = {}
    triggers_out = {}
    for alien in ALIENS:
        key = alien["key"]
        layers = resolve(vfs, alien["layer"])
        if not layers:
            raise SystemExit(f"no visible layers for {key}")
        # Group layers by model, keeping the order of the render layer file.
        parts = []
        for layer in layers:
            part = next((p for p in parts if p["geo"] == layer["geo"]), None)
            if part is None:
                part = {"geo": layer["geo"], "base": [], "glow": []}
                parts.append(part)
            img = layer["image"]
            frames = layer["frames"]
            if "/badge/badge_glow" in layer["tex_path"]:
                img = tint(img, GLOW[0])
            (part["glow"] if layer["glow"] else part["base"]).append(img)
            if frames:
                part.setdefault("anim", {})["glow" if layer["glow"] else "base"] = (
                    len(part["glow"] if layer["glow"] else part["base"]) - 1, frames, layer["frame_ticks"])

        textures, geometry, rcs = {}, {}, []
        renames = {}
        materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha", "translucent": "entity_alphablend"}
        for i, part in enumerate(parts):
            pid = f"{key}_{i}"
            geo_id = f"geometry.alienevo.{pid}"
            write_json(os.path.join(geo_dir, f"{pid}.geo.json"), convert_geo(vfs.json(part["geo"]), geo_id, renames))
            geometry[f"part{i}"] = geo_id
            if part["base"]:
                img = composite(part["base"])
                save_png(img, os.path.join(tex_dir, f"{pid}.png"))
                textures[f"part{i}"] = f"textures/entity/aliens/{pid}"
                mat = "translucent" if is_translucent(img) else "default"
                rc = f"controller.render.alienevo.{pid}"
                controllers[rc] = {"geometry": f"Geometry.part{i}", "materials": [{"*": f"Material.{mat}"}],
                                   "textures": [f"Texture.part{i}"], "part_visibility": FIRST_PERSON_ARMS}
                rcs.append(rc)
            if part["glow"]:
                save_png(composite(part["glow"]), os.path.join(tex_dir, f"{pid}_glow.png"))
                textures[f"part{i}_glow"] = f"textures/entity/aliens/{pid}_glow"
                rcg = f"controller.render.alienevo.{pid}_glow"
                controllers[rcg] = {"geometry": f"Geometry.part{i}", "materials": [{"*": "Material.glow"}],
                                    "textures": [f"Texture.part{i}_glow"], "part_visibility": FIRST_PERSON_ARMS}
                anim = part.get("anim", {}).get("glow")
                if anim:
                    # Flip-book (e.g. Heatblast's flames): one texture per frame,
                    # chosen from the attachable's life time.
                    idx, frames, ticks = anim
                    names = []
                    for f, frame in enumerate(frames):
                        layers_f = list(part["glow"])
                        layers_f[idx] = frame
                        save_png(composite(layers_f), os.path.join(tex_dir, f"{pid}_glow_f{f}.png"))
                        textures[f"part{i}_glow_f{f}"] = f"textures/entity/aliens/{pid}_glow_f{f}"
                        names.append(f"Texture.part{i}_glow_f{f}")
                    fps = 20.0 / ticks
                    controllers[rcg]["arrays"] = {"textures": {"Array.frames": names}}
                    controllers[rcg]["textures"] = [f"Array.frames[math.mod(math.floor(q.life_time * {fps}), {len(names)})]"]
                rcs.append(rcg)

        animations, animate, trig_index = build_alien_animations(vfs, key, layers, anim_dir, ctrl_dir, renames)
        triggers_out[key] = trig_index
        desc = {
            "identifier": f"alienevo:form_{key}",
            "materials": materials,
            "textures": textures,
            "geometry": geometry,
            "scripts": {"parent_setup": "v.chest_layer_visible = 0.0; v.helmet_layer_visible = 0.0; v.leg_layer_visible = 0.0; v.boot_layer_visible = 0.0;",
                        "pre_animation": list(FORM_VARS)},
            "render_controllers": rcs,
        }
        if animations:
            desc["animations"] = animations
            desc["scripts"]["animate"] = animate
        write_json(os.path.join(att_dir, f"form_{key}.json"), {"format_version": "1.10.0", "minecraft:attachable": {"description": desc}})
        lang[f"item.alienevo:form_{key}"] = alien["name"]
        icon = render_icon(vfs.json(parts[0]["geo"]), composite(parts[0]["base"] + parts[0]["glow"]))
        save_png(icon, os.path.join(icon_dir, f"{key}.png"))

    write_json(os.path.join(RP, "render_controllers", "alienevo.render_controllers.json"),
               {"format_version": "1.10.0", "render_controllers": controllers})
    return triggers_out


# Real alien sizes: "size_change" (palladium:size, Pehkui) ability of each
# alien's power.  The old global.alienevo_scale_N values only sized the GUI
# preview.  Clamped to 3 so the camera stays usable.
SIZES = {
    "pyronite": 1.1, "vulpimancer": 1.0, "petrosapien": 1.35, "kineceleran": 1.1, "galvan": 0.25,
    "tetramand": 2.0, "lepidopterran": 1.0, "piscciss_volann": 1.17, "galvanic_mechamorph": 1.4,
    "ectonurite": 1.3, "arburian_pelarota": 1.33, "methanosian": 1.7, "sonorosian": 0.5, "vaxasaurian": 2.8,
    "aerophibian": 1.0, "necrofriggian": 1.0, "crystalsapien": 1.45, "nucleonix": 3.3, "dragonoid": 8.7,
    "astrobot": 0.55, "opticoid": 1.65, "perkgourmand": 0.63, "murkgourmand": 0.63, "talpaedan": 2.3,
    "orishan": 1.25, "amperi": 1.0, "nosedeenian": 0.65, "loboan": 1.3, "transylian": 1.0, "florauna": 1.4,
    "merlinisapien": 1.0, "ickthyperambuloid": 0.63, "splixson": 0.9, "oryctini": 1.6,
    "sonorosian_ov": 0.5, "necrofriggian_ov": 1.0,
}
MAX_SIZE = 3.0


def alien_size(key):
    return max(0.25, min(MAX_SIZE, SIZES.get(key, 1.0)))


OMNITRIX_LAYER = "assets/alienevo/palladium/render_layers/prototype_omnitrix.json"


def build_omnitrix(vfs, triggers_out):
    """The Omnitrix item is drawn as the GeckoLib watch on the player's left
    wrist while it is held (attachable bones follow the player's bones)."""
    geo_dir = os.path.join(RP, "models", "entity", "omnitrix")
    tex_dir = os.path.join(RP, "textures", "entity", "omnitrix")
    att_dir = os.path.join(RP, "attachables", "omnitrix")
    anim_dir = os.path.join(RP, "animations", "omnitrix")
    ctrl_dir = os.path.join(RP, "animation_controllers", "omnitrix")
    for d in (geo_dir, tex_dir, att_dir, anim_dir, ctrl_dir):
        reset_dir(d)
    base_layers = resolve(vfs, OMNITRIX_LAYER)
    fixed = {}
    for layer in base_layers:
        for trig in layer["triggers"]:
            fixed.setdefault(trig, len(fixed) + 1)
    triggers_out["omnitrix"] = fixed
    controllers = {}
    variants = {"prototype": None, "10k": {"AlienEvo.10kPhase": 1}}
    for variant, scores in variants.items():
        layers = resolve(vfs, OMNITRIX_LAYER, scores)
        parts = []
        for layer in layers:
            part = next((p for p in parts if p["geo"] == layer["geo"]), None)
            if part is None:
                part = {"geo": layer["geo"], "base": [], "glow": []}
                parts.append(part)
            img = layer["image"]
            (part["glow"] if layer["glow"] else part["base"]).append(img)
            if "/models/sil/" in layer["tex_path"]:
                part["sil"] = img.size
        textures, geometry, rcs, renames = {}, {}, [], {}
        # Hidden in first person, except while looking at the watch (dial / code entry).
        cond = WATCH_COND
        slot_dir = os.path.join(tex_dir, "slots")
        if variant == "prototype":
            write_watch_slot_textures(vfs, slot_dir)
        for i, part in enumerate(parts):
            pid = f"omnitrix_{variant}_{i}"
            gid = f"geometry.alienevo.{pid}"
            geo = convert_geo(vfs.json(part["geo"]), gid, renames)
            if part.get("sil"):
                # GeckoLib draws the silhouette level with the core face; lift it
                # a little so Bedrock does not hide it behind the face.
                for bone in geo["minecraft:geometry"][0]["bones"]:
                    for cube in bone.get("cubes", []):
                        cube["origin"][0] = round(cube["origin"][0] + 0.15, 4)
            write_json(os.path.join(geo_dir, f"{pid}.geo.json"), geo)
            geometry[f"part{i}"] = gid
            if part.get("sil"):
                # Silhouette of the alien on the dial (omnitrix_cycle -> sil/alien_N).
                names = []
                for alien in ALIENS:
                    src_path = next((f"assets/{ns}/textures/models/sil/alien_{alien['id']}.png" for ns in ("alienevo", "aeo", "untapped", "omni_evo")
                                     if vfs.exists(f"assets/{ns}/textures/models/sil/alien_{alien['id']}.png")), None)
                    img = vfs.image(src_path).resize(part["sil"], Image.NEAREST) if src_path else Image.new("RGBA", part["sil"])
                    save_png(img, os.path.join(tex_dir, f"sil_{alien['key']}.png"))
                    textures[f"sil_{alien['key']}"] = f"textures/entity/omnitrix/sil_{alien['key']}"
                    names.append(f"Texture.sil_{alien['key']}")
                rc = f"controller.render.alienevo.{pid}"
                controllers[rc] = {"geometry": f"Geometry.part{i}", "materials": [{"*": "Material.default"}],
                                   "arrays": {"textures": {"Array.sils": names}},
                                   "textures": ["Array.sils[v.alienevo_sel]"]}
                rcs.append({rc: f"{cond} && v.alienevo_sel >= 0"})
                continue
            for kind, mat in (("base", "default"), ("glow", "glow")):
                if not part[kind]:
                    continue
                suffix = "" if kind == "base" else "_glow"
                save_png(composite(part[kind]), os.path.join(tex_dir, f"{pid}{suffix}.png"))
                textures[f"part{i}{suffix}"] = f"textures/entity/omnitrix/{pid}{suffix}"
                rc = f"controller.render.alienevo.{pid}{suffix}"
                controllers[rc] = {"geometry": f"Geometry.part{i}", "materials": [{"*": f"Material.{mat}"}],
                                   "textures": [f"Texture.part{i}{suffix}"]}
                if kind == "glow":
                    # Glow colour module: one recoloured texture per Omni Crystal colour.
                    names = [f"Texture.part{i}{suffix}"]
                    for ci, colour in enumerate(CRYSTAL_ORDER):
                        save_png(recolor(composite(part[kind]), DYE_RGB[colour]), os.path.join(tex_dir, f"{pid}{suffix}_{ci}.png"))
                        textures[f"part{i}{suffix}_{ci}"] = f"textures/entity/omnitrix/{pid}{suffix}_{ci}"
                        names.append(f"Texture.part{i}{suffix}_{ci}")
                    controllers[rc]["arrays"] = {"textures": {"Array.glow": names}}
                    controllers[rc]["textures"] = ["Array.glow[v.alienevo_glow + 1]"]
                rcs.append({rc: cond})
            if i == 0:
                # Colour modules: the watch drawn again, slightly inflated, with
                # the overlay of each slot picked from the player's properties.
                ogid = f"{gid}_overlay"
                write_json(os.path.join(geo_dir, f"{pid}_overlay.geo.json"),
                           inflate_geo(convert_geo(vfs.json(part["geo"]), ogid), 0.02))
                geometry["overlay"] = ogid
                textures["blank"] = "textures/entity/omnitrix/slots/blank"
                for si, slot in enumerate(WATCH_SLOTS):
                    names = ["Texture.blank"]
                    for ci in range(len(CRYSTAL_ORDER)):
                        textures[f"{slot}_{ci}"] = f"textures/entity/omnitrix/slots/{slot}_{ci}"
                        names.append(f"Texture.{slot}_{ci}")
                    rc = f"controller.render.alienevo.omnitrix_{variant}_{slot}"
                    controllers[rc] = {"geometry": "Geometry.overlay", "materials": [{"*": "Material.default"}],
                                       "arrays": {"textures": {"Array.colors": names}},
                                       "textures": [f"Array.colors[v.alienevo_col{si} + 1]"]}
                    rcs.append({rc: f"{cond} && v.alienevo_col{si} >= 0"})
        animations, animate, _ = build_alien_animations(vfs, f"omnitrix_{variant}", layers, anim_dir, ctrl_dir, renames, fixed)
        items = [i[0] for i in OMNITRIX_ITEMS if (i[3] == 3) == (variant == "10k") and i[0] != "recal_omnitrix"]
        for item in items:
            desc = {
                "identifier": f"alienevo:{item}",
                "materials": {"default": "entity_alphatest", "glow": "entity_emissive_alpha"},
                "textures": textures,
                "geometry": geometry,
                "render_controllers": rcs,
            }
            desc["scripts"] = {"pre_animation": watch_vars()}
            if animations:
                desc["animations"] = animations
                desc["scripts"]["animate"] = animate
            write_json(os.path.join(att_dir, f"{item}.json"), {"format_version": "1.10.0", "minecraft:attachable": {"description": desc}})
    print("recal holograms:", build_recal(vfs, controllers, fixed))
    write_json(os.path.join(RP, "render_controllers", "alienevo.omnitrix.render_controllers.json"),
               {"format_version": "1.10.0", "render_controllers": controllers})


RECAL_LAYER = "assets/alienevo/palladium/render_layers/recal_omnitrix.json"
# Always-on GeckoLib controllers of the recal layer: Bedrock multiplies scales,
# so the "hide hologram" reset would hide it for good; visibility is done by
# the render controller instead.
RECAL_SKIP_LOOPS = {"animation.recal.holo", "animation.recal.xlr8"}


def build_recal(vfs, controllers, fixed):
    """Recalibrated Omnitrix (Omniverse watch): the 3D hologram of the alien
    on the dial stands on the core while the watch is up (recal_omnitrix.json)."""
    geo_dir = os.path.join(RP, "models", "entity", "omnitrix")
    tex_dir = os.path.join(RP, "textures", "entity", "omnitrix")
    anim_dir = os.path.join(RP, "animations", "omnitrix")
    ctrl_dir = os.path.join(RP, "animation_controllers", "omnitrix")
    layers = resolve(vfs, RECAL_LAYER)
    for layer in layers:
        layer["loops"] = [n for n in layer["loops"] if n not in RECAL_SKIP_LOOPS]
    cond = WATCH_COND
    textures, geometry, rcs, renames = {}, {}, [], {}
    watch = [l for l in layers if "/holograms/" not in l["geo"]]
    gid = "geometry.alienevo.omnitrix_recal"
    write_json(os.path.join(geo_dir, "omnitrix_recal.geo.json"), convert_geo(vfs.json(watch[0]["geo"]), gid, renames))
    geometry["watch"] = gid
    for kind, mat in (("base", "default"), ("glow", "glow")):
        imgs = [l["image"] for l in watch if l["glow"] == (kind == "glow")]
        if not imgs:
            continue
        save_png(composite(imgs), os.path.join(tex_dir, f"omnitrix_recal_{kind}.png"))
        textures[f"watch_{kind}"] = f"textures/entity/omnitrix/omnitrix_recal_{kind}"
        rc = f"controller.render.alienevo.omnitrix_recal_{kind}"
        controllers[rc] = {"geometry": "Geometry.watch", "materials": [{"*": f"Material.{mat}"}], "textures": [f"Texture.watch_{kind}"]}
        rcs.append({rc: cond})
    # One hologram geometry per alien (index = HOLO_KEYS order, like alienevo:sel).
    empty = {"format_version": "1.12.0", "minecraft:geometry": [{"description": {
        "identifier": "geometry.alienevo.holo_none", "texture_width": 16, "texture_height": 16}, "bones": [{"name": "holo_none", "pivot": [0, 0, 0]}]}]}
    write_json(os.path.join(geo_dir, "holo_none.geo.json"), empty)
    geometry["holo_none"] = "geometry.alienevo.holo_none"
    textures["holo_none"] = "textures/entity/omnitrix/slots/blank"
    geos, texs, found = [], [], 0
    for alien in ALIENS:
        src = next((f"assets/{ns}/geo/holograms/alien_{alien['id']}.geo.json" for ns in ("alienevo", "omni_evo", "evo_reds_alienpack", "aeo")
                    if vfs.exists(f"assets/{ns}/geo/holograms/alien_{alien['id']}.geo.json")), None)
        tex = src and src.replace("/geo/", "/textures/models/").replace(".geo.json", ".png")
        if not src or not vfs.exists(tex):
            geos.append("Geometry.holo_none")
            texs.append("Texture.holo_none")
            continue
        found += 1
        geo = vfs.json(src)
        # Bones of the alien inside the hologram must not be mistaken for the
        # player's bones (Bedrock matches attachable bones by name).
        keep = set(BONE_MAP) | {"recal_omnitrix", "core", "hologram"}
        for b in geo["minecraft:geometry"][0]["bones"]:
            b.pop("locators", None)
            if b["name"] not in keep:
                b["name"] = f"{alien['key']}__{b['name']}"
            if b.get("parent") and b["parent"] not in keep:
                b["parent"] = f"{alien['key']}__{b['parent']}"
        hid = f"geometry.alienevo.recal_holo_{alien['key']}"
        write_json(os.path.join(geo_dir, f"recal_holo_{alien['key']}.geo.json"), convert_geo(geo, hid))
        save_png(vfs.image(tex), os.path.join(tex_dir, f"recal_holo_{alien['key']}.png"))
        geometry[f"holo_{alien['key']}"] = hid
        textures[f"holo_{alien['key']}"] = f"textures/entity/omnitrix/recal_holo_{alien['key']}"
        geos.append(f"Geometry.holo_{alien['key']}")
        texs.append(f"Texture.holo_{alien['key']}")
    sel = "v.alienevo_sel"
    rc = "controller.render.alienevo.omnitrix_recal_hologram"
    controllers[rc] = {"arrays": {"geometries": {"Array.holo": geos}, "textures": {"Array.holo_tex": texs}},
                       "geometry": f"Array.holo[{sel}]", "materials": [{"*": "Material.hologram"}],
                       "textures": [f"Array.holo_tex[{sel}]"], "ignore_lighting": True}
    rcs.append({rc: f"v.alienevo_wv && {sel} >= 0 && !v.alienevo_alien"})
    animations, animate, _ = build_alien_animations(vfs, "omnitrix_recal", layers, anim_dir, ctrl_dir, renames, fixed)
    desc = {
        "identifier": "alienevo:recal_omnitrix",
        "materials": {"default": "entity_alphatest", "glow": "entity_emissive_alpha", "hologram": "entity_alphablend"},
        "textures": textures,
        "geometry": geometry,
        "render_controllers": rcs,
    }
    desc["scripts"] = {"pre_animation": watch_vars()}
    if animations:
        desc["animations"] = animations
        desc["scripts"]["animate"] = animate
    write_json(os.path.join(RP, "attachables", "omnitrix", "recal_omnitrix.json"),
               {"format_version": "1.10.0", "minecraft:attachable": {"description": desc}})
    return found


def write_watch_slot_textures(vfs, out_dir):
    reset_dir(out_dir)
    blank = Image.new("RGBA", (64, 64))
    save_png(blank, os.path.join(out_dir, "blank.png"))
    src = AE + "/textures/models/prototype_omnitrix"
    for slot in WATCH_SLOTS:
        for ci in range(len(CRYSTAL_ORDER)):
            path = f"{src}/{slot}/{slot}_{ci}.png"
            img = vfs.image(path) if vfs.exists(path) else blank
            save_png(img, os.path.join(out_dir, f"{slot}_{ci}.png"))


def recolor(img, hex_color):
    """Re-hue a green glow texture to another colour, keeping its shading."""
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    out = img.copy()
    px = out.load()
    ref = 0.299 * 0xb3 + 0.587 * 0xff + 0.114 * 0x40
    for y in range(out.size[1]):
        for x in range(out.size[0]):
            pr, pg, pb, pa = px[x, y]
            if pa == 0:
                continue
            k = (0.299 * pr + 0.587 * pg + 0.114 * pb) / ref
            px[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), pa)
    return out


def inflate_geo(geo, amount):
    for g in geo["minecraft:geometry"]:
        for bone in g.get("bones", []):
            for cube in bone.get("cubes", []):
                cube["inflate"] = round(cube.get("inflate", 0) + amount, 4)
    return geo


MOBS = [
    # key, render layer, name, health, attack, speed, size, spawn weight, egg colours
    dict(key="machine_husk", layer=f"{L}/machine/machine_husk.json", name="Machine Husk", health=30, attack=5,
         speed=0.23, width=0.7, height=2.0, weight=40, loot="machine_husk", egg=("#3a3f45", "#8cff3a")),
    dict(key="machine_husk_staff", layer=f"{L}/machine/machine_husk_staff.json", name="Machine Husk Priest", health=36,
         attack=7, speed=0.22, width=0.7, height=2.0, weight=15, loot="machine_husk_staff", egg=("#3a3f45", "#e0c040")),
    dict(key="machine_husk_baby", layer=f"{L}/machine/machine_husk_baby.json", name="Machine Drone", health=12,
         attack=3, speed=0.33, width=0.5, height=0.9, weight=25, loot="machine_husk", egg=("#3a3f45", "#40e0ff")),
]


def build_mobs(vfs, lang):
    """Machine husks of the Java mod (husks with a Palladium render layer)
    as Bedrock entities using the GeckoLib models."""
    geo_dir = os.path.join(RP, "models", "entity", "mobs")
    tex_dir = os.path.join(RP, "textures", "entity", "mobs")
    for d in (geo_dir, tex_dir):
        reset_dir(d)
    controllers = {}
    for mob in MOBS:
        key = mob["key"]
        layers = resolve(vfs, mob["layer"])
        geo_src = layers[0]["geo"]
        base = composite([l["image"] for l in layers if not l["glow"]])
        glow = [l["image"] for l in layers if l["glow"]]
        gid = f"geometry.alienevo.{key}"
        write_json(os.path.join(geo_dir, f"{key}.geo.json"), convert_geo(vfs.json(geo_src), gid))
        save_png(base, os.path.join(tex_dir, f"{key}.png"))
        textures = {"default": f"textures/entity/mobs/{key}"}
        rcs = [f"controller.render.alienevo.mob.{key}"]
        controllers[rcs[0]] = {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]}
        if glow:
            save_png(composite(glow), os.path.join(tex_dir, f"{key}_glow.png"))
            textures["glow"] = f"textures/entity/mobs/{key}_glow"
            rcs.append(f"controller.render.alienevo.mob.{key}_glow")
            controllers[rcs[1]] = {"geometry": "Geometry.default", "materials": [{"*": "Material.glow"}], "textures": ["Texture.glow"]}
        write_json(os.path.join(RP, "entity", f"{key}.entity.json"), {
            "format_version": "1.10.0",
            "minecraft:client_entity": {"description": {
                "identifier": f"alienevo:{key}",
                "materials": {"default": "entity_alphatest", "glow": "entity_emissive_alpha"},
                "textures": textures,
                "geometry": {"default": gid},
                "animations": {
                    "move": "animation.humanoid.move",
                    "look_at_target": "animation.humanoid.look_at_target.default",
                    "attack": "animation.zombie.attack_bare_hand",
                },
                "scripts": {
                    "pre_animation": ["variable.tcos0 = (Math.cos(query.modified_distance_moved * 38.17) * query.modified_move_speed / variable.gliding_speed_value) * 57.3;"],
                    "initialize": ["variable.gliding_speed_value = 1.0;"],
                    "animate": ["move", "look_at_target", {"attack": "variable.attack_time > 0"}],
                },
                "render_controllers": rcs,
                "spawn_egg": {"base_color": mob["egg"][0], "overlay_color": mob["egg"][1]},
            }},
        })
        write_json(os.path.join(BP, "entities", f"{key}.json"), {
            "format_version": "1.21.90",
            "minecraft:entity": {
                "description": {"identifier": f"alienevo:{key}", "is_spawnable": True, "is_summonable": True},
                "components": {
                    "minecraft:type_family": {"family": ["machine", "monster", "mob"]},
                    "minecraft:health": {"value": mob["health"], "max": mob["health"]},
                    "minecraft:attack": {"damage": mob["attack"]},
                    "minecraft:movement": {"value": mob["speed"]},
                    "minecraft:collision_box": {"width": mob["width"], "height": mob["height"]},
                    "minecraft:physics": {},
                    "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
                    "minecraft:jump.static": {},
                    "minecraft:movement.basic": {},
                    "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_damage_blocks": True, "can_open_doors": False},
                    "minecraft:can_climb": {},
                    "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
                    "minecraft:nameable": {},
                    "minecraft:despawn": {"despawn_from_distance": {}},
                    "minecraft:loot": {"table": f"loot_tables/alienevo/entities/{mob['loot']}.json"},
                    "minecraft:experience_reward": {"on_death": "q.last_hit_by_player ? 8 : 0"},
                    "minecraft:behavior.float": {"priority": 0},
                    "minecraft:behavior.melee_box_attack": {"priority": 2, "speed_multiplier": 1.2, "track_target": True},
                    "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 0.8},
                    "minecraft:behavior.look_at_player": {"priority": 7, "look_distance": 8},
                    "minecraft:behavior.random_look_around": {"priority": 8},
                    "minecraft:behavior.hurt_by_target": {"priority": 1},
                    "minecraft:behavior.nearest_attackable_target": {
                        "priority": 2, "must_see": True, "reselect_targets": True,
                        "entity_types": [{"filters": {"any_of": [
                            {"test": "is_family", "subject": "other", "value": "player"},
                            {"test": "is_family", "subject": "other", "value": "irongolem"}]}, "max_dist": 24}],
                    },
                },
            },
        })
        write_json(os.path.join(BP, "spawn_rules", f"{key}.json"), {
            "format_version": "1.8.0",
            "minecraft:spawn_rules": {
                "description": {"identifier": f"alienevo:{key}", "population_control": "monster"},
                "conditions": [{
                    "minecraft:spawns_underground": {},
                    "minecraft:brightness_filter": {"min": 0, "max": 7, "adjust_for_weather": False},
                    "minecraft:height_filter": {"min": -64, "max": 20},
                    "minecraft:weight": {"default": mob["weight"] // 10},
                    "minecraft:density_limit": {"underground": 3},
                    "minecraft:biome_filter": {"test": "has_biome_tag", "value": "overworld"},
                }],
            },
        })
        lang[f"entity.alienevo:{key}.name"] = mob["name"]
        lang[f"item.spawn_egg.entity.alienevo:{key}.name"] = f"Spawn {mob['name']}"
        src = f"data/alienevo/loot_tables/entities/{mob['loot']}.json"
        bp_items = {f"alienevo:{os.path.splitext(f)[0]}" for f in os.listdir(os.path.join(BP, "items"))}
        loot = structures.convert_loot(vfs.json(src), bp_items)
        # Aliens Untapped: add_machine_husk_drop (transformation tablet); the
        # Primus Link Circuit of the (not ported) Volaticus Biopsis drops from priests.
        extra = {"machine_husk": ("alienevo:code_tablet_transformation", 0.1),
                 "machine_husk_staff": ("alienevo:primus_link_circuit", 0.05)}.get(mob["loot"])
        if extra:
            loot.setdefault("pools", []).append({"rolls": 1, "entries": [{"type": "item", "name": extra[0], "weight": 1}],
                                                 "conditions": [{"condition": "killed_by_player"},
                                                                {"condition": "random_chance", "chance": extra[1]}]})
        write_json(os.path.join(BP, "loot_tables", "alienevo", "entities", f"{mob['loot']}.json"), loot)
    write_json(os.path.join(RP, "render_controllers", "alienevo.mobs.render_controllers.json"),
               {"format_version": "1.10.0", "render_controllers": controllers})


GALVAN_TIERS = [0, 10, 70, 150, 250]
ITEM_SUBSTITUTES = {"palladium:raw_titanium": "minecraft:raw_iron"}


def _trade_item(ref, bp_items):
    if isinstance(ref, str):
        ref = {"item": ref, "count": 1}
    item = ITEM_SUBSTITUTES.get(ref["item"], ref["item"])
    if item.startswith("untapped:"):
        item = "alienevo:" + item.split(":", 1)[1]
    if not item.startswith("minecraft:") and item not in bp_items:
        return None
    return {"item": item, "quantity": ref.get("count", 1)}


def build_galvan_scientist(vfs, lang):
    """Galvan Scientist villager (profession alienevo:galvan_scientist of the
    Java mod) with its trade levels converted to a Bedrock trade table."""
    key = "galvan_scientist"
    bp_items = {f"alienevo:{os.path.splitext(f)[0]}" for d in ("items", "blocks") for f in os.listdir(os.path.join(BP, d))}
    bp_items |= {f"alienevo:{i[0]}" for i in UNTAPPED_ITEMS}
    tiers = []
    for level in range(1, 6):
        groups, seen = [], set()
        files = sorted(n for n in vfs.files if re.fullmatch(rf"addon/[a-z_]+/villager_trades/galvan_trades_{level}\.json", n))
        for data in (d for n in files for d in vfs.all_json(n)):
            for t in data.get("trades", []):
                want, give = _trade_item(t["price"], bp_items), _trade_item(t["for_sale"], bp_items)
                sig = json.dumps([want, give])
                if want and give and sig not in seen:
                    seen.add(sig)
                    groups.append({"wants": [want], "gives": [give], "trader_exp": t.get("xp", 1),
                                   "max_uses": t.get("max_trades", 12), "reward_exp": True})
        # Java villagers offer 2 random trades from each level's pool.
        pools = [{"num_to_select": min(2, len(groups)), "trades": groups}] if groups else []
        if level == 4:
            # Cartographer trades of the Java mod (commands.txt) moved here.
            pools.append({"trades": [
                {"wants": [{"item": "alienevo:galvan_scrap", "quantity": 16}], "gives": [{"item": "alienevo:machine_key"}],
                 "trader_exp": 10, "max_uses": 3, "reward_exp": True},
                {"wants": [{"item": "alienevo:galvan_scrap", "quantity": 32}], "gives": [{"item": "alienevo:machine_urn"}],
                 "trader_exp": 10, "max_uses": 3, "reward_exp": True},
            ]})
        if pools:
            tiers.append({"total_exp_required": GALVAN_TIERS[level - 1], "groups": pools})
    write_json(os.path.join(BP, "trading", "alienevo", f"{key}.json"), {"tiers": tiers})

    geo_dir = os.path.join(RP, "models", "entity", "mobs")
    tex_dir = os.path.join(RP, "textures", "entity", "mobs")
    base = "assets/alienevo/palladium/model_layers/galvan_villager"
    tex = "assets/alienevo/textures/models/aliens/galvan_villager"
    geos, textures = {}, {"glow": f"textures/entity/mobs/{key}_glow"}
    for i in (1, 2, 3):
        gid = f"geometry.alienevo.{key}_{i}"
        g = vfs.json(f"{base}/galvan_villager_0{i}.json")
        g["minecraft:geometry"][0]["description"]["identifier"] = gid
        write_json(os.path.join(geo_dir, f"{key}_{i}.geo.json"), g)
        save_png(vfs.image(f"{tex}/galvan_villager_0{i}.png"), os.path.join(tex_dir, f"{key}_{i}.png"))
        geos[f"v{i}"] = gid
        textures[f"v{i}"] = f"textures/entity/mobs/{key}_{i}"
    save_png(vfs.image(f"{tex}/galvan_villager_glow.png"), os.path.join(tex_dir, f"{key}_glow.png"))
    write_json(os.path.join(RP, "animations", f"alienevo.{key}.animation.json"), {
        "format_version": "1.8.0",
        "animations": {
            f"animation.alienevo.{key}.move": {"loop": True, "bones": {
                "left_leg": {"rotation": ["math.cos(q.anim_time * 38.17 * 16) * 40 * q.modified_move_speed", 0, 0]},
                "right_leg": {"rotation": ["-math.cos(q.anim_time * 38.17 * 16) * 40 * q.modified_move_speed", 0, 0]},
                "arms": {"rotation": ["math.sin(q.life_time * 90) * 3", 0, 0]},
                "body": {"position": [0, "math.abs(math.cos(q.anim_time * 38.17 * 16)) * 0.4 * q.modified_move_speed", 0]},
            }},
            f"animation.alienevo.{key}.look": {"loop": True, "bones": {
                "head": {"rotation": ["-q.target_x_rotation", "-q.target_y_rotation", 0]},
            }},
            f"animation.alienevo.{key}.blink": {"loop": True, "animation_length": 4.0, "bones": {
                "pupil": {"scale": {"0.0": [1, 1, 1], "3.85": [1, 1, 1], "3.9": [1, 0.1, 1], "4.0": [1, 1, 1]}},
                "pupil2": {"scale": {"0.0": [1, 1, 1], "3.85": [1, 1, 1], "3.9": [1, 0.1, 1], "4.0": [1, 1, 1]}},
            }},
        },
    })
    rc_base = f"controller.render.alienevo.mob.{key}"
    arrays_geo = {"Array.geos": ["Geometry.v1", "Geometry.v2", "Geometry.v3"]}
    arrays_tex = {"Array.skins": ["Texture.v1", "Texture.v2", "Texture.v3"]}
    write_json(os.path.join(RP, "render_controllers", f"alienevo.{key}.render_controllers.json"), {
        "format_version": "1.10.0",
        "render_controllers": {
            rc_base: {"arrays": {"geometries": arrays_geo, "textures": arrays_tex},
                      "geometry": "Array.geos[q.variant]", "materials": [{"*": "Material.default"}],
                      "textures": ["Array.skins[q.variant]"]},
            f"{rc_base}_glow": {"arrays": {"geometries": arrays_geo},
                                "geometry": "Array.geos[q.variant]", "materials": [{"*": "Material.glow"}],
                                "textures": ["Texture.glow"]},
        },
    })
    write_json(os.path.join(RP, "entity", f"{key}.entity.json"), {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": f"alienevo:{key}",
            "materials": {"default": "entity_alphatest", "glow": "entity_emissive_alpha"},
            "textures": textures,
            "geometry": geos,
            "animations": {"move": f"animation.alienevo.{key}.move", "look": f"animation.alienevo.{key}.look",
                           "blink": f"animation.alienevo.{key}.blink"},
            "scripts": {"animate": ["move", "look", "blink"]},
            "render_controllers": [rc_base, f"{rc_base}_glow"],
            "spawn_egg": {"base_color": "#86d698", "overlay_color": "#332e27"},
        }},
    })
    variants = {f"alienevo:v{i}": {"minecraft:variant": {"value": i}} for i in range(3)}
    write_json(os.path.join(BP, "entities", f"{key}.json"), {
        "format_version": "1.21.90",
        "minecraft:entity": {
            "description": {"identifier": f"alienevo:{key}", "is_spawnable": True, "is_summonable": True},
            "component_groups": variants,
            "components": {
                "minecraft:type_family": {"family": ["galvan", "villager", "mob"]},
                "minecraft:health": {"value": 20, "max": 20},
                "minecraft:movement": {"value": 0.5},
                "minecraft:collision_box": {"width": 0.5, "height": 0.75},
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
                "minecraft:jump.static": {},
                "minecraft:movement.basic": {},
                "minecraft:navigation.walk": {"can_path_over_water": True, "can_open_doors": True, "avoid_damage_blocks": True},
                "minecraft:nameable": {},
                "minecraft:persistent": {},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
                "minecraft:economy_trade_table": {"display_name": f"entity.alienevo:{key}.name",
                                                  "table": f"trading/alienevo/{key}.json", "new_screen": True,
                                                  "persist_trades": True, "cured_discount": [-25, -20]},
                "minecraft:trade_resupply": {},
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:behavior.panic": {"priority": 1, "speed_multiplier": 0.9},
                "minecraft:behavior.trade_with_player": {"priority": 2},
                "minecraft:behavior.look_at_trading_player": {"priority": 2},
                "minecraft:behavior.avoid_mob_type": {"priority": 3, "entity_types": [{"filters": {"test": "is_family", "subject": "other", "value": "machine"}, "max_dist": 8, "walk_speed_multiplier": 0.6, "sprint_speed_multiplier": 0.9}]},
                "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 0.4},
                "minecraft:behavior.look_at_player": {"priority": 7, "look_distance": 8},
                "minecraft:behavior.random_look_around": {"priority": 8},
            },
            "events": {"minecraft:entity_spawned": {"randomize": [{"weight": 1, "add": {"component_groups": [g]}} for g in variants]}},
        },
    })
    write_json(os.path.join(BP, "spawn_rules", f"{key}.json"), {
        "format_version": "1.8.0",
        "minecraft:spawn_rules": {
            "description": {"identifier": f"alienevo:{key}", "population_control": "animal"},
            "conditions": [{
                "minecraft:spawns_on_surface": {},
                "minecraft:brightness_filter": {"min": 7, "max": 15, "adjust_for_weather": False},
                "minecraft:weight": {"default": 1},
                "minecraft:density_limit": {"surface": 1},
                "minecraft:herd": {"min_size": 1, "max_size": 1},
                "minecraft:biome_filter": {"all_of": [{"test": "has_biome_tag", "value": "overworld"},
                                                      {"test": "has_biome_tag", "operator": "!=", "value": "ocean"}]},
            }],
        },
    })
    lang[f"entity.alienevo:{key}.name"] = "Galvan Scientist"
    lang[f"item.spawn_egg.entity.alienevo:{key}.name"] = "Spawn Galvan Scientist"
    return sum(len(g["trades"]) for t in tiers for g in t["groups"])


HOLO_RAMP = ((0x2c, 0x5a, 0x10), (0xb3, 0xff, 0x40), (0xf0, 0xff, 0xd0))


def hologram_texture(img):
    """Alien skin -> green see-through hologram (like the recal_omnitrix
    hologram layer of the Java mod)."""
    img = img.convert("RGBA")
    out = Image.new("RGBA", img.size)
    src, dst = img.load(), out.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            lum = (0.3 * r + 0.59 * g + 0.11 * b) / 255.0
            lo, hi = (HOLO_RAMP[0], HOLO_RAMP[1]) if lum < 0.5 else (HOLO_RAMP[1], HOLO_RAMP[2])
            t = lum * 2 if lum < 0.5 else lum * 2 - 1
            c = tuple(int(lo[i] + (hi[i] - lo[i]) * t) for i in range(3))
            # Scan lines.
            alpha = int(min(a, 255) * (0.65 if y % 2 else 0.85))
            dst[x, y] = c + (alpha,)
    return out


def build_hologram(lang):
    """alienevo:omnitrix_hologram: the selected alien floating above the
    Omnitrix while the dial is turned.  One geometry per alien, chosen by the
    synced entity property alienevo:alien."""
    key = "omnitrix_hologram"
    geo_src = os.path.join(RP, "models", "entity", "aliens")
    tex_src = os.path.join(RP, "textures", "entity", "aliens")
    geo_dir = os.path.join(RP, "models", "entity", "hologram")
    tex_dir = os.path.join(RP, "textures", "entity", "hologram")
    for d in (geo_dir, tex_dir):
        reset_dir(d)
    anim_dir = os.path.join(RP, "animations", "aliens")
    geometry, textures, keys = {}, {}, []
    for alien in ALIENS:
        akey = alien["key"]
        geo = json.load(open(os.path.join(geo_src, f"{akey}_0.geo.json")))
        g = geo["minecraft:geometry"][0]
        # Bones the alien only shows during an ability (rest_pose) are dropped.
        hidden = set()
        anim_path = os.path.join(anim_dir, f"{akey}.animation.json")
        if os.path.exists(anim_path):
            for name, anim in json.load(open(anim_path))["animations"].items():
                if name.endswith(".rest_pose"):
                    hidden |= set(anim.get("bones", {}))
        changed = True
        while changed:
            changed = False
            for b in g["bones"]:
                if b["name"] not in hidden and b.get("parent") in hidden:
                    hidden.add(b["name"])
                    changed = True
        for b in g["bones"]:
            if b["name"] in hidden:
                b.pop("cubes", None)
        # One skeleton per alien: the client entity merges all its geometries.
        for b in g["bones"]:
            b.pop("locators", None)
            b["name"] = f"{akey}__{b['name']}"
            if b.get("parent"):
                b["parent"] = f"{akey}__{b['parent']}"
        gid = f"geometry.alienevo.holo_{akey}"
        g["description"]["identifier"] = gid
        write_json(os.path.join(geo_dir, f"{akey}.geo.json"), geo)
        layers = [Image.open(os.path.join(tex_src, f"{akey}_0{s}.png")).convert("RGBA")
                  for s in ("", "_glow") if os.path.exists(os.path.join(tex_src, f"{akey}_0{s}.png"))]
        save_png(hologram_texture(composite(layers)), os.path.join(tex_dir, f"{akey}.png"))
        geometry[akey] = gid
        textures[akey] = f"textures/entity/hologram/{akey}"
        keys.append(akey)
    index = "q.property('alienevo:alien')"
    write_json(os.path.join(RP, "render_controllers", f"alienevo.{key}.render_controllers.json"), {
        "format_version": "1.10.0",
        "render_controllers": {f"controller.render.alienevo.{key}": {
            "arrays": {"geometries": {"Array.geos": [f"Geometry.{k}" for k in keys]},
                       "textures": {"Array.skins": [f"Texture.{k}" for k in keys]}},
            "geometry": f"Array.geos[{index}]",
            "materials": [{"*": "Material.default"}],
            "textures": [f"Array.skins[{index}]"],
            "ignore_lighting": True,
        }},
    })
    write_json(os.path.join(RP, "entity", f"{key}.entity.json"), {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": f"alienevo:{key}",
            "materials": {"default": "entity_alphablend"},
            "textures": textures,
            "geometry": geometry,
            "scripts": {"scale": "0.32"},
            "render_controllers": [f"controller.render.alienevo.{key}"],
        }},
    })
    write_json(os.path.join(BP, "entities", f"{key}.json"), {
        "format_version": "1.21.90",
        "minecraft:entity": {
            "description": {
                "identifier": f"alienevo:{key}", "is_spawnable": False, "is_summonable": True,
                "properties": {"alienevo:alien": {"type": "int", "range": [0, 63], "default": 0, "client_sync": True}},
            },
            "components": {
                "minecraft:type_family": {"family": ["alienevo_hologram", "inanimate"]},
                "minecraft:collision_box": {"width": 0.01, "height": 0.01},
                "minecraft:physics": {"has_gravity": False, "has_collision": False},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
                "minecraft:health": {"value": 1, "max": 1},
                "minecraft:fire_immune": {},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:conditional_bandwidth_optimization": {"default_values": {
                    "max_optimized_distance": 0, "max_dropped_ticks": 0, "use_motion_prediction_hints": True}},
            },
        },
    })
    lang[f"entity.alienevo:{key}.name"] = "Omnitrix Hologram"
    path = os.path.join(BP, "scripts", "holo_data.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("// Generated by tools/build_packs.py - geometry index of each alien in the\n")
        f.write("// alienevo:omnitrix_hologram entity (property alienevo:alien).\n")
        f.write("export const HOLO_KEYS = ")
        json.dump(keys, f)
        f.write(";\n")
    return len(keys)


def build_glyphs():
    """Alien icons as text glyphs U+E100.. (font/glyph_E1.png) so the dial can
    show the alien strip on screen like the selection wheel of the Java mod."""
    cell = 32
    sheet = Image.new("RGBA", (cell * 16, cell * 16))
    for i, alien in enumerate(ALIENS):
        icon = Image.open(os.path.join(RP, "textures", "ui", "aliens", f"{alien['key']}.png")).convert("RGBA")
        sheet.alpha_composite(icon.resize((cell, cell), Image.NEAREST), ((i % 16) * cell, (i // 16) * cell))
    save_png(sheet, os.path.join(RP, "font", "glyph_E1.png"))


WHEEL_TITLE = "alienevo:wheel"
WHEEL_SIZE = 200


def build_wheel_ui(vfs):
    """Quick change wheel of the Java mod (palladium:ability_wheel with the
    quick_wheel_sel_N textures and the player in the middle) as a JSON UI
    layout of ActionFormData forms titled WHEEL_TITLE.  Buttons 0-9 are the
    ten slots (clockwise from the top), 10 = menu, 11 = next page / close."""
    ui_dir = os.path.join(RP, "ui")
    tex_dir = os.path.join(RP, "textures", "ui", "alienevo")
    reset_dir(ui_dir)
    reset_dir(tex_dir)
    src = "assets/alienevo/textures/gui/wheel/quick_wheel_sel_{}.png"
    base = vfs.image(src.format(0))
    save_png(base.resize((384, 384), Image.NEAREST), os.path.join(tex_dir, "wheel.png"))
    bpx = base.load()
    for i in range(1, 11):
        img = vfs.image(src.format(i))
        px = img.load()
        hl = Image.new("RGBA", img.size)
        for y in range(img.size[1]):
            for x in range(img.size[0]):
                if px[x, y] != bpx[x, y]:
                    hl.putpixel((x, y), px[x, y])
        save_png(hl.resize((384, 384), Image.NEAREST), os.path.join(tex_dir, f"wheel_sel_{i}.png"))

    k = WHEEL_SIZE / 192.0
    tex_bind = [
        {"binding_name": "#form_button_texture", "binding_name_override": "#texture", "binding_type": "collection", "binding_collection_name": "form_buttons"},
        {"binding_name": "#form_button_texture_file_system", "binding_name_override": "#texture_file_system", "binding_type": "collection", "binding_collection_name": "form_buttons"},
    ]
    has_text = [
        {"binding_name": "#form_button_text", "binding_type": "collection", "binding_collection_name": "form_buttons"},
        {"binding_type": "view", "source_property_name": "(not (#form_button_text = ''))", "target_property_name": "#visible"},
    ]
    ns = {"namespace": "alienevo_wheel"}
    ns["icon"] = {"type": "image", "size": [26, 26], "layer": 4, "bindings": tex_bind}
    ns["name_label"] = {"type": "label", "layer": 6, "color": [0.7, 1.0, 0.25], "shadow": True, "text": "#form_button_text",
                        "bindings": [{"binding_name": "#form_button_text", "binding_type": "collection", "binding_collection_name": "form_buttons"}]}
    # The buttons are generated by a factory over the form_buttons collection
    # (like the vanilla form), so every generated item knows its own index;
    # each item holds the twelve possible placements and shows only its own.
    det = {"binding_type": "collection_details", "binding_collection_name": "form_buttons"}
    txt = {"binding_name": "#form_button_text", "binding_type": "collection", "binding_collection_name": "form_buttons"}

    def only(i):
        return [txt, det, {"binding_type": "view", "target_property_name": "#visible",
                           "source_property_name": f"((#collection_index = {i}) and (not (#form_button_text = '')))"}]

    variants = []
    for i in range(10):
        ang = math.radians(i * 36)
        cx, cy = (96 + 72 * math.sin(ang)) * k, (96 - 72 * math.cos(ang)) * k
        to_center = [round(WHEEL_SIZE / 2 - cx, 2), round(WHEEL_SIZE / 2 - cy, 2)]
        highlight = {"type": "image", "texture": f"textures/ui/alienevo/wheel_sel_{i + 1}", "size": [WHEEL_SIZE, WHEEL_SIZE],
                     "layer": 3, "offset": to_center}
        name = {"name@alienevo_wheel.name_label": {"offset": [to_center[0], to_center[1] + WHEEL_SIZE / 2 + 10]}}
        state = lambda hover, highlight=highlight, name=name: {"type": "panel", "size": ["100%", "100%"], "controls": (
            [{"highlight": highlight}, name] if hover else []) + [{"icon@alienevo_wheel.icon": {}}]}
        variants.append({f"slot_{i}": {
            "type": "panel", "size": [30, 30], "anchor_from": "top_left", "anchor_to": "center",
            "offset": [round(cx, 2), round(cy, 2)], "bindings": only(i),
            "controls": [{"button@common.button": {
                "size": ["100%", "100%"], "$pressed_button_name": "button.form_button_click", "bindings": [det],
                "controls": [{"default": state(False)}, {"hover": state(True)}, {"pressed": state(True)}],
            }}],
        }})
    for i, offset in ((10, [WHEEL_SIZE / 2 - 48, WHEEL_SIZE + 26]), (11, [WHEEL_SIZE / 2 + 48, WHEEL_SIZE + 26])):
        variants.append({f"text_button_{i}": {
            "type": "panel", "size": [88, 20], "anchor_from": "top_left", "anchor_to": "center", "offset": offset,
            "bindings": only(i),
            "controls": [{"button@common_buttons.light_text_button": {
                "size": ["100%", "100%"], "$pressed_button_name": "button.form_button_click",
                "$button_text": "#form_button_text", "$button_text_binding_type": "collection",
                "$button_text_grid_collection_name": "form_buttons", "$button_text_max_size": ["100%", 20],
                "bindings": [det],
            }}],
        }})
    ns["wheel_item"] = {"type": "panel", "size": ["100%", 0], "controls": variants}
    ring = [{"buttons": {
        "type": "stack_panel", "orientation": "vertical", "size": ["100%", "100%"], "layer": 3,
        "anchor_from": "top_left", "anchor_to": "top_left",
        "factory": {"name": "buttons", "control_ids": {"button": "@alienevo_wheel.wheel_item"}},
        "collection_name": "form_buttons",
        "bindings": [{"binding_name": "#form_button_contents", "binding_name_override": "#collection_length"}],
    }}]
    ns["wheel"] = {
        "type": "panel", "size": [WHEEL_SIZE, WHEEL_SIZE], "layer": 2,
        "controls": [
            {"background": {"type": "image", "texture": "textures/ui/alienevo/wheel", "size": ["100%", "100%"], "layer": 1}},
            {"player": {"type": "custom", "renderer": "live_player_renderer", "size": [44, 88], "layer": 5,
                        "offset": [0, 10], "property_bag": {"#look_at_cursor": True}}},
            {"title": {"type": "label", "text": "#form_text", "color": [0.7, 1.0, 0.25], "shadow": True, "layer": 6,
                       "offset": [0, -WHEEL_SIZE / 2 - 10]}},
        ] + ring,
    }
    is_wheel = f"(#title_text = '{WHEEL_TITLE}')"
    ns["long_form_router"] = {
        "type": "panel", "size": [0, 0],
        "controls": [
            {"default_form": {"type": "panel", "size": [0, 0],
                              "bindings": [{"binding_name": "#title_text"}, {"binding_type": "view", "source_property_name": f"(not {is_wheel})", "target_property_name": "#visible"}],
                              "controls": [{"long_form@server_form.long_form": {}}]}},
            {"wheel_form": {"type": "panel", "size": [0, 0],
                            "bindings": [{"binding_name": "#title_text"}, {"binding_type": "view", "source_property_name": is_wheel, "target_property_name": "#visible"}],
                            "controls": [{"wheel@alienevo_wheel.wheel": {}}]}},
        ],
    }
    write_json(os.path.join(ui_dir, "alienevo_wheel.json"), ns)
    write_json(os.path.join(ui_dir, "_ui_defs.json"), {"ui_defs": ["ui/alienevo_wheel.json"]})
    # Only the form factory of the vanilla screen is redirected (same content
    # as the vanilla main_screen_content of 26.x, long_form -> router).
    write_json(os.path.join(ui_dir, "server_form.json"), {
        "namespace": "server_form",
        "main_screen_content": {
            "type": "panel", "size": [0, 0],
            "controls": [{"server_form_factory": {"type": "factory", "control_ids": {
                "long_form": "@alienevo_wheel.long_form_router",
                "custom_form": "@server_form.custom_form",
            }}}],
        },
    })


def build_particles(vfs):
    """Java particle types (textures + lifetime/gravity/size) -> Bedrock
    particle effects with a flip-book of the original frames."""
    out_tex = os.path.join(RP, "textures", "particle", "alienevo")
    out_json = os.path.join(RP, "particles")
    reset_dir(out_tex)
    reset_dir(out_json)
    made = []
    for ns in ("alienevo", "afomni"):
        for path in sorted(n for n in vfs.files if n.startswith(f"assets/{ns}/particles/") and n.endswith(".json")):
            name = os.path.basename(path)[:-5]
            frames = []
            for ref in vfs.json(path).get("textures", []):
                tns, tpath = ref.split(":", 1)
                f = f"assets/{tns}/textures/particle/{tpath}.png"
                if vfs.exists(f):
                    frames.append(vfs.image(f))
            if not frames:
                continue
            w = max(f.size[0] for f in frames)
            h = max(f.size[1] for f in frames)
            strip = Image.new("RGBA", (w * len(frames), h))
            for i, f in enumerate(frames):
                strip.alpha_composite(f.resize((w, h), Image.NEAREST), (i * w, 0))
            ident = name if ns == "alienevo" else f"{ns}_{name}"
            save_png(strip, os.path.join(out_tex, f"{ident}.png"))
            spec_path = next((p for p in (f"addon/{ns}/particle_types/{name}.json",) if vfs.exists(p)), None)
            spec = vfs.json(spec_path) if spec_path else {}
            life = max(2, spec.get("lifetime", 12)) / 20.0
            gravity = spec.get("gravity", 0)
            size = round(0.12 * spec.get("quad_size", 1.0), 3)
            lit = spec.get("render_type", "lit") == "lit" and spec.get("brightness", 0) < 200
            comps = {
                "minecraft:emitter_rate_instant": {"num_particles": 1},
                "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                "minecraft:emitter_shape_point": {"direction": ["math.random(-0.3, 0.3)", "math.random(0.1, 0.6)", "math.random(-0.3, 0.3)"]},
                "minecraft:particle_initial_speed": 0.4,
                "minecraft:particle_lifetime_expression": {"max_lifetime": life},
                "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, round(-gravity * 8, 3), 0], "linear_drag_coefficient": 1.5},
                "minecraft:particle_appearance_billboard": {
                    "size": [size, size], "facing_camera_mode": "rotate_xyz",
                    "uv": {"texture_width": w * len(frames), "texture_height": h,
                           "flipbook": {"base_UV": [0, 0], "size_UV": [w, h], "step_UV": [w, 0],
                                        "frames_per_second": round(len(frames) / life, 2), "max_frame": len(frames),
                                        "stretch_to_lifetime": True, "loop": False}},
                },
            }
            if lit:
                comps["minecraft:particle_appearance_lighting"] = {}
            write_json(os.path.join(out_json, f"{ident}.json"), {
                "format_version": "1.10.0",
                "particle_effect": {
                    "description": {"identifier": f"alienevo:{ident}",
                                    "basic_render_parameters": {"material": "particles_blend",
                                                                "texture": f"textures/particle/alienevo/{ident}"}},
                    "components": comps,
                },
            })
            made.append(ident)
    return made


def build_player_scale_animation():
    """Scale the player skeleton (and therefore the attachable) per alien."""
    expr = "1.0"
    for alien in ALIENS:
        s = round(alien_size(alien["key"]), 3)
        if s != 1.0:
            expr = f"q.is_item_name_any('slot.armor.chest', 0, 'alienevo:form_{alien['key']}') ? {s} : ({expr})"
    write_json(os.path.join(RP, "animations", "alienevo.player.animation.json"), {
        "format_version": "1.8.0",
        "animations": {
            "animation.alienevo.player.scale": {
                "loop": True,
                "bones": {"root": {"scale": "v.alienevo_scale"}},
            },
            # Omnitrix worn in the offhand: the left arm with the watch rests in the
            # lower left corner (vanilla off-hand map pose).
            "animation.alienevo.player.watch_rest": {
                "loop": True,
                "bones": {"leftarm": {
                    "position": ["-14.50 + variable.is_horizontal_splitscreen * 2.0 + variable.is_vertical_splitscreen * 8.7",
                                 "-8.250 + variable.short_arm_offset_left", "11.50 + variable.is_horizontal_splitscreen * 0.5"],
                    "rotation": [195.0, 182.5, 2.5],
                    "scale": [0.75, 0.75, 0.75],
                }},
            },
            # Omnitrix held in the main hand: the hand is drawn empty (vanilla
            # empty hand pose) instead of disappearing.
            "animation.alienevo.player.held_hand": {
                "loop": True,
                "bones": {"rightarm": {
                    "position": [13.5, -10.0, 12.0],
                    "rotation": ["95.0 + variable.is_using_vr * 7.5", "-45.0 + variable.is_using_vr * 7.5", "115.0 + variable.is_using_vr * -2.5"],
                }},
            },
            "animation.alienevo.player.watch_view": {
                "loop": True,
                "bones": {"leftarm": {
                    "position": [-11.5, "-6.5 + variable.short_arm_offset_left + math.sin(q.life_time * 60) * 0.15", 11.0],
                    "rotation": [195.0, 182.5, 2.5],
                    "scale": [0.9, 0.9, 0.9],
                }},
            },
        },
    })
    write_json(os.path.join(RP, "render_controllers", "alienevo.player.render_controllers.json"), {
        "format_version": "1.10.0",
        "render_controllers": {"controller.render.alienevo.player.watch_arm": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"],
            "part_visibility": [{"*": False},
                                {"leftArm": "v.alienevo_off || q.property('alienevo:wv')"},
                                {"leftSleeve": "v.alienevo_off || q.property('alienevo:wv')"},
                                {"rightArm": "v.alienevo_main"}, {"rightSleeve": "v.alienevo_main"}],
        }},
    })
    return expr


def build_projectiles(jar):
    """Boulder projectile (Four Arms) re-uses the boulder cube of the jar."""
    src = jar.json(G_AL + "/alien_6/tetramand_boulder.geo.json")["minecraft:geometry"][0]
    cube = None
    for bone in src["bones"]:
        if bone.get("cubes"):
            cube = dict(bone["cubes"][0])
    size = cube["size"]
    cube["origin"] = [-size[0] / 2, 0, -size[2] / 2]
    cube.pop("pivot", None)
    cube.pop("rotation", None)
    write_json(os.path.join(RP, "models", "entity", "boulder.geo.json"), {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {"identifier": "geometry.alienevo.boulder", "texture_width": 32, "texture_height": 32,
                            "visible_bounds_width": 2, "visible_bounds_height": 2, "visible_bounds_offset": [0, 0.5, 0]},
            "bones": [{"name": "boulder", "pivot": [0, size[1] / 2, 0], "cubes": [cube]}],
        }],
    })
    save_png(jar.image(T_AL + "/alien_6/boulder.png"), os.path.join(RP, "textures", "entity", "boulder.png"))


def write_anim_data(triggers):
    """Trigger animation indices for the server script (generated)."""
    path = os.path.join(BP, "scripts", "anim_data.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("// Generated by tools/build_packs.py - trigger animation index per alien.\n")
        f.write("// Set as the synced player property alienevo:anim while the animation plays.\n")
        f.write("export const ANIM_TRIGGERS = ")
        json.dump(triggers, f, indent=4, sort_keys=True)
        f.write(";\n")
        f.write("// Ticks to keep alienevo:anim set for each index (-1 = until the next trigger).\n")
        f.write("export const ANIM_TICKS = ")
        json.dump({k: {str(i): t for i, t in v.items()} for k, v in TRIGGER_TICKS.items()}, f, indent=4, sort_keys=True)
        f.write(";\n")


WATCH_SLOTS = ["base_primary", "base_secondary", "base_tertiary", "buttons", "core_side", "core_top",
               "dial_inner", "dial_outer", "tubes"]
# Omni Crystal colour -> overlay index of the Java watch textures (workbench_items.js).
CRYSTAL_ORDER = ["lime", "white", "light_gray", "gray", "black", "brown", "red", "orange", "yellow", "green",
                 "cyan", "light_blue", "blue", "purple", "magenta", "pink"]
DYE_RGB = {
    "lime": "b3ff40", "white": "f9fffe", "light_gray": "c6c6c0", "gray": "6b7377", "black": "3a3a40",
    "brown": "a36a3e", "red": "ff4a3d", "orange": "ff9a2e", "yellow": "ffe04a", "green": "7fae2a",
    "cyan": "29d4d4", "light_blue": "5fd0ff", "blue": "5a64ff", "purple": "b25cff", "magenta": "ff6be8", "pink": "ffa6c4",
}


def build_player_behavior():
    """Vanilla player (Bedrock 26.50) + synced properties for the alien model
    and the Omnitrix colours."""
    with open(os.path.join(ROOT, "tools", "vanilla_player.bp.json"), encoding="utf-8") as f:
        data = json.load(f)
    props = {
        "alienevo:anim": {"type": "int", "range": [0, 63], "default": 0, "client_sync": True},
        "alienevo:fly": {"type": "bool", "default": False, "client_sync": True},
        "alienevo:glow": {"type": "int", "range": [-1, 15], "default": -1, "client_sync": True},
        # Alien on the dial (index in HOLO_KEYS, -1 = none) and "looking at the watch".
        "alienevo:sel": {"type": "int", "range": [-1, 63], "default": -1, "client_sync": True},
        "alienevo:wv": {"type": "bool", "default": False, "client_sync": True},
    }
    for i in range(len(WATCH_SLOTS)):
        props[f"alienevo:col{i}"] = {"type": "int", "range": [-1, 15], "default": -1, "client_sync": True}
    data["minecraft:entity"]["description"]["properties"] = props
    write_json(os.path.join(BP, "entities", "player.json"), data)


def build_player_entity(scale_expr):
    """Patch the vanilla player client entity (Bedrock 1.26) so the player's own
    body is hidden while an alien form is worn, and the skeleton is scaled."""
    with open(os.path.join(ROOT, "tools", "vanilla_player.entity.json"), encoding="utf-8") as f:
        data = json.load(f)
    desc = data["minecraft:client_entity"]["description"]
    alien = "q.equipped_item_any_tag('slot.armor.chest', 'alienevo:alien_form')"
    desc["scripts"].setdefault("variables", {})["variable.alienevo_is_alien"] = "public"
    desc["scripts"]["pre_animation"].append(f"v.alienevo_is_alien = {alien};")
    desc["scripts"]["pre_animation"].append(f"v.alienevo_scale = {scale_expr};")
    desc["animations"]["alienevo_scale"] = "animation.alienevo.player.scale"
    desc["scripts"]["animate"].append({"alienevo_scale": "!v.is_first_person && v.alienevo_is_alien"})
    # Looking at the watch in first person: the left arm is raised in front of
    # the camera (pose based on the vanilla off-hand map pose) and drawn.
    omni = ", ".join(f"'alienevo:{i[0]}'" for i in OMNITRIX_ITEMS)
    desc["scripts"]["variables"]["variable.alienevo_off"] = "public"
    desc["scripts"]["variables"]["variable.alienevo_main"] = "public"
    desc["scripts"]["pre_animation"].append(f"v.alienevo_off = q.is_item_name_any('slot.weapon.offhand', 0, {omni});")
    desc["scripts"]["pre_animation"].append(f"v.alienevo_main = q.is_item_name_any('slot.weapon.mainhand', 0, {omni});")
    desc["animations"]["alienevo_watch_view"] = "animation.alienevo.player.watch_view"
    desc["animations"]["alienevo_watch_rest"] = "animation.alienevo.player.watch_rest"
    desc["animations"]["alienevo_held_hand"] = "animation.alienevo.player.held_hand"
    desc["scripts"]["animate"].append({"alienevo_watch_view": "v.is_first_person && q.property('alienevo:wv')"})
    desc["scripts"]["animate"].append({"alienevo_watch_rest": "v.is_first_person && v.alienevo_off && !q.property('alienevo:wv')"})
    desc["scripts"]["animate"].append({"alienevo_held_hand": "v.is_first_person && v.alienevo_main"})
    rcs = [{"controller.render.alienevo.player.watch_arm": "v.is_first_person && !query.is_spectator && !v.alienevo_is_alien && (v.alienevo_off || v.alienevo_main || q.property('alienevo:wv'))"}]
    for rc in desc["render_controllers"]:
        if isinstance(rc, dict) and "controller.render.player.first_person" in rc:
            rc = {"controller.render.player.first_person": rc["controller.render.player.first_person"] + " && !v.alienevo_is_alien"}
        if isinstance(rc, dict) and "controller.render.player.third_person" in rc:
            rc = {"controller.render.player.third_person": rc["controller.render.player.third_person"] + " && !v.alienevo_is_alien"}
        rcs.append(rc)
    desc["render_controllers"] = rcs
    write_json(os.path.join(RP, "entity", "player.entity.json"), data)


def build_items_rp(jar, lang, item_textures):
    tex_dir = os.path.join(RP, "textures", "items")
    reset_dir(tex_dir)
    src = AE + "/textures/item"
    for item_id, tex, _, _ in simple_items():
        p = f"{src}/{tex}.png"
        if tex == "prototype_core":
            img = composite([jar.image(p)] + [tint(jar.image(f"{src}/prototype_core_glow_{i}.png"), GLOW[i - 1]) for i in (1, 2, 3)])
        else:
            img = jar.image(p)
        save_png(img.crop((0, 0, img.size[0], img.size[0])), os.path.join(tex_dir, f"{item_id}.png"))
        item_textures[f"alienevo:{item_id}"] = {"textures": f"textures/items/{item_id}"}
    for item_id, base, glows, _ in OMNITRIX_ITEMS:
        img = composite([jar.image(f"{src}/{base}.png")] + [tint(jar.image(f"{src}/{g}.png"), GLOW[0 if i == 0 else 2]) for i, g in enumerate(glows)])
        save_png(img, os.path.join(tex_dir, f"{item_id}.png"))
        item_textures[f"alienevo:{item_id}"] = {"textures": f"textures/items/{item_id}"}
    for item_id, _, _ in TOOLS:
        img = jar.image(f"{src}/{item_id}.png")
        model_path = f"{AE}/models/item/{item_id}.json"
        if jar.exists(model_path) and "elements" in jar.json(model_path):
            # 3D Blockbench item (Ancient Staff): its texture is a UV sheet,
            # so the icon is rendered from the model.
            from render import render
            model = jar.json(model_path)
            geo = java_block_model_to_geo(model, "geometry.icon", model.get("texture_size", [16, 16]))
            icon = render([(geo, img)], 256, "three_quarter")
            icon = icon.crop(icon.getbbox()) if icon.getbbox() else icon
            side = max(icon.size)
            square = Image.new("RGBA", (side, side))
            square.alpha_composite(icon, ((side - icon.size[0]) // 2, (side - icon.size[1]) // 2))
            img = square.resize((32, 32), Image.LANCZOS)
        save_png(img, os.path.join(tex_dir, f"{item_id}.png"))
        item_textures[f"alienevo:{item_id}"] = {"textures": f"textures/items/{item_id}"}
    # Alien form items reuse the selection icons.
    for alien in ALIENS:
        item_textures[f"alienevo:form_{alien['key']}"] = {"textures": f"textures/ui/aliens/{alien['key']}"}


# Aliens Untapped transformation code tablets (transformation_code.js).
UNTAPPED_ITEMS = [
    # id, max stack, custom component
    ("broken_code_tablet", 16, "alienevo:code_tablet"),
    ("blank_code_tablet", 16, None),
    ("code_tablet_transformation", 1, "alienevo:code_tablet"),
    ("primus_link_circuit", 16, None),
]


def untapped_items_rp(vfs, lang, item_textures):
    names = vfs.json("assets/untapped/lang/en_us.json")
    tex_dir = os.path.join(RP, "textures", "items")
    for item_id, _, _ in UNTAPPED_ITEMS:
        img = vfs.image(f"assets/untapped/textures/item/{item_id}.png")
        save_png(img.crop((0, 0, img.size[0], img.size[0])), os.path.join(tex_dir, f"{item_id}.png"))
        item_textures[f"alienevo:{item_id}"] = {"textures": f"textures/items/{item_id}"}
        lang[f"item.alienevo:{item_id}"] = names.get(f"item.untapped.{item_id}", item_id.replace("_", " ").title())


def untapped_items_bp():
    for item_id, stack, custom in UNTAPPED_ITEMS:
        comps = {"minecraft:icon": f"alienevo:{item_id}", "minecraft:max_stack_size": stack}
        if custom:
            comps[custom] = {}
        if item_id == "primus_link_circuit":
            comps["minecraft:rarity"] = "rare"
        write_json(os.path.join(BP, "items", f"{item_id}.json"), item_json(f"alienevo:{item_id}", comps))


def unlock_recipes():
    """1.20+ recipes need unlock data: unlocked by owning one of the
    ingredients (the "AlwaysUnlocked" context was read as an invalid
    ingredient by the game)."""
    for path in glob.glob(os.path.join(BP, "recipes", "*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, body in data.items():
            if key not in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
                continue
            ings = list(body.get("key", {}).values()) if key.endswith("shaped") else body.get("ingredients", [])
            items = [i["item"] if isinstance(i, dict) else i for i in ings
                     if isinstance(i, str) or (isinstance(i, dict) and "item" in i)]
            if items:
                body["unlock"] = [{"item": items[0]}]
            else:
                body.pop("unlock", None)
        write_json(path, data)


def untapped_recipes():
    """dupe_code_tablet*.json: a read tablet + a blank tablet = two tablets."""
    for tablet in ("code_tablet", "code_tablet_selfdestruct"):
        write_json(os.path.join(BP, "recipes", f"dupe_{tablet}.json"), {
            "format_version": "1.20.10",
            "minecraft:recipe_shapeless": {
                "description": {"identifier": f"alienevo:dupe_{tablet}"},
                "tags": ["crafting_table"],
                "ingredients": [{"item": f"alienevo:{tablet}"}, {"item": "alienevo:blank_code_tablet"}],
                "result": {"item": f"alienevo:{tablet}", "count": 2},
            },
        })


BLOCKS = {
    "omnitrix_workbench": {"name": "Omnitrix Workbench"},
    "galvan_pod": {"name": "Galvan Pod"},
    "machined_metal": {"name": "Machined Metal"},
    "machined_panel": {"name": "Machined Panel"},
    "permanent_taydenite_block": {"name": "Taydenite"},
    "permanent_smooth_taydenite_block": {"name": "Smooth Taydenite"},
}


def build_blocks_rp(jar, terrain):
    tex_dir = os.path.join(RP, "textures", "blocks")
    reset_dir(tex_dir)
    src = AE + "/textures/block"
    for name in ["machined_metal", "machined_panel", "diamond_block", "diamond_block_up", "diamond_block_2",
                 "pod_front", "pod_sides", "pod_back", "pod_top", "pod_bottom", "workbench"]:
        save_png(jar.image(f"{src}/{name}.png"), os.path.join(tex_dir, f"{name}.png"))
        terrain[f"alienevo_{name}"] = {"textures": f"textures/blocks/{name}"}
    model = jar.json(AE + "/models/block/omnitrix_workbench.json")
    write_json(os.path.join(RP, "models", "blocks", "omnitrix_workbench.geo.json"),
               java_block_model_to_geo(model, "geometry.alienevo.omnitrix_workbench", model.get("texture_size", [16, 16])))
    blocks_json = {"format_version": "1.21.40"}
    for name in BLOCKS:
        blocks_json[f"alienevo:{name}"] = {"sound": "metal" if "taydenite" not in name else "amethyst_block"}
    write_json(os.path.join(RP, "blocks.json"), blocks_json)


def build_sounds(jar):
    out = os.path.join(RP, "sounds", "alienevo")
    reset_dir(out)
    defs = {}
    namespaces = sorted({n.split("/")[1] for n in jar.files if n.endswith("/sounds.json") and n.count("/") == 2})
    for ns in namespaces:
        sj = f"assets/{ns}/sounds.json"
        merged = {}
        for version in jar.all_json(sj):
            for event, data in version.items():
                merged.setdefault(event, data)
        for event, data in merged.items():
            if event.startswith("music."):
                continue  # menu music of the add-ons, not used here
            files = []
            for s in data.get("sounds", []):
                name = s["name"] if isinstance(s, dict) else s
                sns, path = name.split(":") if ":" in name else (ns, name)
                src = f"assets/{sns}/sounds/{path}.ogg"
                if not jar.exists(src):
                    continue
                rel = path if sns in ("alienevo", "afomni") else f"{sns}/{path}"
                dst = os.path.join(out, rel + ".ogg")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f:
                    f.write(jar.read(src))
                files.append({"name": f"sounds/alienevo/{rel}", "volume": 1.0})
            if files:
                name = f"alienevo.{event}" if ns in ("alienevo", "afomni") else f"alienevo.{ns}.{event}"
                defs.setdefault(name, {"category": "player", "sounds": files})
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"),
               {"format_version": "1.20.20", "sound_definitions": defs})


def build_lang(jar, lang):
    src = jar.json(AE + "/lang/en_us.json")
    for k, v in src.items():
        if k.startswith("item.alienevo."):
            lang[f"item.alienevo:{k[len('item.alienevo.'):]}"] = v
        elif k.startswith("block.alienevo."):
            lang[f"tile.alienevo:{k[len('block.alienevo.'):]}.name"] = v
    for item_id, kind, _ in TOOLS:
        lang.setdefault(f"item.alienevo:{item_id}", item_id.replace("_", " ").title())
    lang["item.alienevo:smithing_template_galvan"] = src.get("upgrade.alienevo.galvan", "Galvan Upgrade")
    for name, data in BLOCKS.items():
        lang.setdefault(f"tile.alienevo:{name}.name", data["name"])
    lang["itemGroup.name.alienevo"] = "Alien Evolution"


# --------------------------------------------------------------------------
# Behavior pack
# --------------------------------------------------------------------------

def item_json(identifier, components, category="items", group=None):
    group = None  # custom creative groups would need an item catalog
    menu = {"category": category}
    if group:
        menu["group"] = group
    return {"format_version": ITEM_FORMAT,
            "minecraft:item": {"description": {"identifier": identifier, "menu_category": menu},
                               "components": components}}


def build_items_bp():
    out = os.path.join(BP, "items")
    reset_dir(out)
    for item_id, tex, stack, extra in simple_items():
        comps = {"minecraft:icon": f"alienevo:{item_id}", "minecraft:max_stack_size": stack}
        if extra.get("tags"):
            comps["minecraft:tags"] = {"tags": extra["tags"]}
        if extra.get("glint"):
            comps["minecraft:glint"] = True
            comps["minecraft:rarity"] = "epic"
        if extra.get("custom"):
            comps[extra["custom"]] = {}
        write_json(os.path.join(out, f"{item_id}.json"), item_json(f"alienevo:{item_id}", comps, group="itemGroup.name.alienevo"))
    for item_id, _, _, tier in OMNITRIX_ITEMS:
        comps = {
            "minecraft:icon": f"alienevo:{item_id}",
            "minecraft:max_stack_size": 1,
            "minecraft:rarity": "epic",
            "minecraft:fire_resistant": {"value": True},
            # Worn in the offhand the watch stays on the left wrist, like the
            # Curios slot of the Java mod.
            "minecraft:allow_off_hand": {"value": True},
            "minecraft:tags": {"tags": ["alienevo:omnitrix", f"alienevo:omnitrix_tier_{tier}"]},
            "alienevo:omnitrix": {"tier": tier},
        }
        write_json(os.path.join(out, f"{item_id}.json"), item_json(f"alienevo:{item_id}", comps, "equipment", "itemGroup.name.alienevo"))
    for item_id, kind, dmg in TOOLS:
        comps = {
            "minecraft:icon": f"alienevo:{item_id}",
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": True,
            "minecraft:damage": dmg,
            "minecraft:durability": {"max_durability": 1756},
            "minecraft:enchantable": {"value": 10, "slot": "sword" if kind in ("sword", "staff") else kind},
            "minecraft:repairable": {"repair_items": [{"items": ["alienevo:galvan_scrap", "alienevo:galvan_metal"], "repair_amount": "context.other->q.remaining_durability + 0.25 * context.other->q.max_durability"}]},
            "minecraft:fire_resistant": {"value": True},
            "alienevo:tool_durability": {},
        }
        tags = []
        if kind == "pickaxe":
            comps["minecraft:digger"] = {"use_efficiency": True, "destroy_speeds": [
                {"block": {"tags": "q.any_tag('minecraft:is_pickaxe_item_destructible', 'stone', 'metal', 'diamond_pick_diggable')"}, "speed": 9}]}
            tags = ["minecraft:is_pickaxe", "minecraft:diamond_tier", "minecraft:is_tool"]
        elif kind == "axe":
            comps["minecraft:digger"] = {"use_efficiency": True, "destroy_speeds": [
                {"block": {"tags": "q.any_tag('minecraft:is_axe_item_destructible', 'wood', 'pumpkin', 'plant')"}, "speed": 9}]}
            tags = ["minecraft:is_axe", "minecraft:diamond_tier", "minecraft:is_tool"]
        elif kind == "shovel":
            comps["minecraft:digger"] = {"use_efficiency": True, "destroy_speeds": [
                {"block": {"tags": "q.any_tag('minecraft:is_shovel_item_destructible', 'dirt', 'sand', 'gravel', 'grass', 'snow')"}, "speed": 9}]}
            tags = ["minecraft:is_shovel", "minecraft:diamond_tier", "minecraft:is_tool"]
        elif kind == "hoe":
            comps["minecraft:digger"] = {"use_efficiency": True, "destroy_speeds": [
                {"block": {"tags": "q.any_tag('minecraft:is_hoe_item_destructible', 'plant')"}, "speed": 9}]}
            tags = ["minecraft:is_hoe", "minecraft:diamond_tier", "minecraft:is_tool"]
        else:
            comps["minecraft:digger"] = {"use_efficiency": False, "destroy_speeds": [{"block": "minecraft:web", "speed": 15}]}
            tags = ["minecraft:is_sword", "minecraft:diamond_tier"]
        comps["minecraft:tags"] = {"tags": tags}
        write_json(os.path.join(out, f"{item_id}.json"), item_json(f"alienevo:{item_id}", comps, "equipment", "itemGroup.name.alienevo"))
    # Alien form: invisible marker worn in the chest slot that carries the model.
    for alien in ALIENS:
        comps = {
            "minecraft:icon": f"alienevo:form_{alien['key']}",
            "minecraft:max_stack_size": 1,
            "minecraft:wearable": {"slot": "slot.armor.chest", "protection": 0},
            "minecraft:tags": {"tags": ["alienevo:alien_form"]},
        }
        write_json(os.path.join(out, f"form_{alien['key']}.json"), item_json(f"alienevo:form_{alien['key']}", comps, "none"))


def block_json(identifier, components, permutations=None, traits=None, states=None):
    desc = {"identifier": identifier, "menu_category": {"category": "construction"}}
    if traits:
        desc["traits"] = traits
    if states:
        desc["states"] = states
    if "minecraft:material_instances" in components and "minecraft:geometry" not in components:
        # 1.21.90 blocks need both components ("Block definition parsing failed").
        components = dict(components, **{"minecraft:geometry": "minecraft:geometry.full_block"})
    data = {"description": desc, "components": components}
    if permutations:
        data["permutations"] = permutations
    return {"format_version": BLOCK_FORMAT, "minecraft:block": data}


FACING_PERMS = [
    {"condition": f"q.block_state('minecraft:cardinal_direction') == '{d}'",
     "components": {"minecraft:transformation": {"rotation": [0, r, 0]}}}
    for d, r in (("north", 0), ("west", 90), ("south", 180), ("east", 270))
]


def build_blocks_bp():
    out = os.path.join(BP, "blocks")
    reset_dir(out)
    cube = lambda tex: {"*": {"texture": tex, "render_method": "opaque"}}
    write_json(os.path.join(out, "machined_metal.json"), block_json("alienevo:machined_metal", {
        "minecraft:destructible_by_mining": {"seconds_to_destroy": 4},
        "minecraft:destructible_by_explosion": {"explosion_resistance": 6},
        "minecraft:material_instances": cube("alienevo_machined_metal"),
    }))
    write_json(os.path.join(out, "machined_panel.json"), block_json("alienevo:machined_panel", {
        "minecraft:destructible_by_mining": {"seconds_to_destroy": 4},
        "minecraft:destructible_by_explosion": {"explosion_resistance": 6},
        "minecraft:material_instances": cube("alienevo_machined_panel"),
    }))
    for name, side in (("permanent_taydenite_block", "alienevo_diamond_block"), ("permanent_smooth_taydenite_block", "alienevo_diamond_block_2")):
        write_json(os.path.join(out, f"{name}.json"), block_json(f"alienevo:{name}", {
            "minecraft:destructible_by_mining": {"seconds_to_destroy": 12},
            "minecraft:destructible_by_explosion": {"explosion_resistance": 255},
            "minecraft:light_emission": 3,
            "minecraft:material_instances": {
                "*": {"texture": side, "render_method": "opaque"},
                "up": {"texture": "alienevo_diamond_block_up", "render_method": "opaque"},
                "down": {"texture": "alienevo_diamond_block_up", "render_method": "opaque"},
            },
        }))
    write_json(os.path.join(out, "galvan_pod.json"), block_json("alienevo:galvan_pod", {
        "minecraft:destructible_by_mining": {"seconds_to_destroy": 5},
        "minecraft:destructible_by_explosion": {"explosion_resistance": 1200},
        "minecraft:loot": "loot_tables/alienevo/galvan_pod_block.json",
        "minecraft:map_color": "#5a6b74",
        "minecraft:material_instances": {
            "*": {"texture": "alienevo_pod_sides", "render_method": "opaque"},
            "north": {"texture": "alienevo_pod_front", "render_method": "opaque"},
            "south": {"texture": "alienevo_pod_back", "render_method": "opaque"},
            "up": {"texture": "alienevo_pod_top", "render_method": "opaque"},
            "down": {"texture": "alienevo_pod_bottom", "render_method": "opaque"},
        },
        "alienevo:galvan_pod": {},
    }, permutations=FACING_PERMS, traits={"minecraft:placement_direction": {"enabled_states": ["minecraft:cardinal_direction"], "y_rotation_offset": 180}},
        states={"alienevo:opened": [False, True]}))
    write_json(os.path.join(out, "omnitrix_workbench.json"), block_json("alienevo:omnitrix_workbench", {
        "minecraft:destructible_by_mining": {"seconds_to_destroy": 3},
        "minecraft:destructible_by_explosion": {"explosion_resistance": 6},
        "minecraft:geometry": "geometry.alienevo.omnitrix_workbench",
        "minecraft:collision_box": {"origin": [-8, 0, -8], "size": [16, 16, 16]},
        "minecraft:selection_box": {"origin": [-8, 0, -8], "size": [16, 16, 16]},
        "minecraft:light_dampening": 0,
        "minecraft:light_emission": 4,
        "minecraft:material_instances": {"*": {"texture": "alienevo_workbench", "render_method": "alpha_test"}},
        "alienevo:workbench": {},
    }, permutations=FACING_PERMS, traits={"minecraft:placement_direction": {"enabled_states": ["minecraft:cardinal_direction"], "y_rotation_offset": 180}}))


# Java recipe ingredients that do not exist in Bedrock.
INGREDIENT_SUBSTITUTES = {
    "palladium:raw_titanium": "minecraft:iron_ingot",
}


def convert_ingredient(ing):
    if isinstance(ing, list):
        ing = ing[0]
    if "tag" in ing:
        tag = ing["tag"]
        if tag == "alienevo:upgrade_crystals":
            return {"tag": "alienevo:upgrade_crystals"}
        if tag == "alienevo:upgrade_shards":
            return {"tag": "alienevo:upgrade_shards"}
        return {"item": "minecraft:iron_ingot"}
    item = INGREDIENT_SUBSTITUTES.get(ing["item"], ing["item"])
    return {"item": item}


def build_recipes(jar):
    out = os.path.join(BP, "recipes")
    reset_dir(out)
    prefix = "data/alienevo/recipes/"
    for name in sorted(n for n in jar.names if n.startswith(prefix) and n.endswith(".json")):
        rid = name[len(prefix):-5]
        r = jar.json(name)
        result = r.get("result", {})
        if isinstance(result, str):
            result = {"item": result}
        res = {"item": result.get("item", result.get("id")), "count": result.get("count", 1)}
        ident = f"alienevo:{rid}"
        if r["type"] == "minecraft:crafting_shaped":
            data = {"format_version": "1.20.10", "minecraft:recipe_shaped": {
                "description": {"identifier": ident}, "tags": ["crafting_table"],
                "pattern": r["pattern"], "key": {k: convert_ingredient(v) for k, v in r["key"].items()},
                "result": res}}
        elif r["type"] == "minecraft:crafting_shapeless":
            data = {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
                "description": {"identifier": ident}, "tags": ["crafting_table"],
                "ingredients": [convert_ingredient(i) for i in r["ingredients"]], "result": res}}
        else:
            # Smithing template duplication: rebuilt by hand below.
            continue
        write_json(os.path.join(out, f"{rid}.json"), data)

    # Galvan smithing upgrade: iron gear + galvan plate -> galvan gear.
    upgrades = {"iron_sword": "galvan_sword", "iron_pickaxe": "galvan_pickaxe", "iron_axe": "galvan_axe",
                "iron_shovel": "galvan_shovel", "iron_hoe": "galvan_hoe"}
    for base, result in upgrades.items():
        write_json(os.path.join(out, f"smithing_{result}.json"), {
            "format_version": "1.20.10",
            "minecraft:recipe_smithing_transform": {
                "description": {"identifier": f"alienevo:smithing_{result}"},
                "tags": ["smithing_table"],
                "template": "alienevo:smithing_template_galvan",
                "base": f"minecraft:{base}",
                "addition": "alienevo:galvan_metal",
                "result": f"alienevo:{result}",
            }})
    write_json(os.path.join(out, "smithing_template_galvan.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": "alienevo:smithing_template_galvan"}, "tags": ["crafting_table"],
            "pattern": ["#T#", "#S#", "###"],
            "key": {"#": {"item": "minecraft:iron_ingot"}, "T": {"item": "alienevo:galvan_metal"}, "S": {"item": "alienevo:galvan_scrap"}},
            "result": {"item": "alienevo:smithing_template_galvan", "count": 1}}})
    write_json(os.path.join(out, "smithing_template_galvan_dupe.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": "alienevo:smithing_template_galvan_dupe"}, "tags": ["crafting_table"],
            "pattern": ["#T#", "#S#", "###"],
            "key": {"#": {"item": "minecraft:diamond"}, "T": {"item": "alienevo:smithing_template_galvan"}, "S": {"item": "alienevo:galvan_scrap"}},
            "result": {"item": "alienevo:smithing_template_galvan", "count": 2}}})
    # Shards from a crystal (reverse of the 3x3 recipe) for every colour.
    for c in COLORS:
        s = crystal_suffix(c)
        write_json(os.path.join(out, f"upgrade_shards{s}_from_crystal.json"), {
            "format_version": "1.20.10",
            "minecraft:recipe_shapeless": {
                "description": {"identifier": f"alienevo:upgrade_shards{s}_from_crystal"}, "tags": ["crafting_table"],
                "ingredients": [{"item": f"alienevo:upgrade_crystal{s}"}],
                "result": {"item": f"alienevo:upgrade_shards{s}", "count": 9}}})


def write_lang(lang):
    text_dir = os.path.join(RP, "texts")
    os.makedirs(text_dir, exist_ok=True)
    manual = os.path.join(text_dir, "manual_en_US.lang")
    extra = {}
    if os.path.exists(manual):
        for line in open(manual, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                extra[k] = v
    lang.update(extra)
    with open(os.path.join(text_dir, "en_US.lang"), "w", encoding="utf-8") as f:
        for k in sorted(lang):
            f.write(f"{k}={lang[k]}\n")
    vi = os.path.join(text_dir, "manual_vi_VN.lang")
    vi_lang = dict(lang)
    if os.path.exists(vi):
        for line in open(vi, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vi_lang[k] = v
    with open(os.path.join(text_dir, "vi_VN.lang"), "w", encoding="utf-8") as f:
        for k in sorted(vi_lang):
            f.write(f"{k}={vi_lang[k]}\n")
    write_json(os.path.join(text_dir, "languages.json"), ["en_US", "vi_VN"])


def stamp_manifests():
    """Every build gets a new pack version: Bedrock ignores an imported pack
    whose UUID and version are already installed and keeps the old one."""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    # Bedrock stores each version part as a 16 bit number (max 65535), so use
    # days since 2026-01-01 and the minute of the day.
    days = (now.date() - datetime.date(2026, 1, 1)).days
    version = [2, days, now.hour * 60 + now.minute]
    label = f"{version[0]}.{version[1]}.{version[2]}"
    uuids = set()
    for pack in (BP, RP):
        with open(os.path.join(pack, "manifest.json"), encoding="utf-8") as f:
            uuids.add(json.load(f)["header"]["uuid"])
    for pack in (BP, RP):
        path = os.path.join(pack, "manifest.json")
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        m["header"]["version"] = version
        m["header"]["description"] = re.sub(r" \(build [0-9.]+\)$", "", m["header"]["description"]) + f" (build {label})"
        for mod in m.get("modules", []):
            mod["version"] = version
        for dep in m.get("dependencies", []):
            if dep.get("uuid") in uuids:
                dep["version"] = version
        write_json(path, m)
    print("pack version", label)


def package():
    stamp_manifests()
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "AlienEvo.mcaddon")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for pack in (BP, RP):
            base = os.path.basename(pack)
            for dirpath, _, files in os.walk(pack):
                for fn in sorted(files):
                    if fn.startswith("manual_"):
                        continue
                    full = os.path.join(dirpath, fn)
                    z.write(full, os.path.join(base, os.path.relpath(full, pack)))
    print("wrote", out, os.path.getsize(out) // 1024, "KiB")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    jar = Jar(sys.argv[1])
    vfs = VFS(sys.argv[1:])
    lang, item_textures, terrain = {}, {}, {}
    build_lang(jar, lang)
    triggers = build_aliens(vfs, lang)
    build_omnitrix(vfs, triggers)
    stale = os.path.join(RP, "animations", "alienevo.signals.animation.json")
    if os.path.exists(stale):
        os.remove(stale)
    write_anim_data(triggers)
    build_player_entity(build_player_scale_animation())
    build_player_behavior()
    build_projectiles(jar)
    print("particles:", ", ".join(build_particles(vfs)))
    build_items_rp(jar, lang, item_textures)
    untapped_items_rp(vfs, lang, item_textures)
    build_blocks_rp(jar, terrain)
    build_sounds(vfs)
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": "alienevo", "texture_name": "atlas.items", "texture_data": item_textures})
    write_json(os.path.join(RP, "textures", "terrain_texture.json"),
               {"resource_pack_name": "alienevo", "texture_name": "atlas.terrain", "padding": 8, "num_mip_levels": 4,
                "texture_data": terrain})
    save_png(jar.image("alienevo_icon.png").resize((256, 256), Image.NEAREST), os.path.join(RP, "pack_icon.png"))
    save_png(jar.image("alienevo_icon.png").resize((256, 256), Image.NEAREST), os.path.join(BP, "pack_icon.png"))
    build_items_bp()
    untapped_items_bp()
    build_blocks_bp()
    build_mobs(vfs, lang)
    print("galvan trades:", build_galvan_scientist(vfs, lang))
    print("holograms:", build_hologram(lang))
    build_glyphs()
    build_wheel_ui(vfs)
    build_recipes(jar)
    untapped_recipes()
    unlock_recipes()
    for line in structures.build(vfs):
        print("structure", line)
    write_lang(lang)
    print("sanitize: renamed bones", sanitize.fix_geometries(RP), "| fixed animation files", sanitize.fix_animations(RP))
    package()


if __name__ == "__main__":
    main()
