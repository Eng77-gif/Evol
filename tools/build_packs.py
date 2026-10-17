#!/usr/bin/env python3
"""Convert the AlienEvo Fabric (Palladium/KubeJS) jar into a Bedrock add-on.

Usage:
    python3 tools/build_packs.py path/to/AlienEvo-1.1.3-fabric.jar

The script regenerates every *generated* file of packs/AlienEvo_RP and
packs/AlienEvo_BP (textures, geometry, attachables, sounds, items, blocks,
recipes, language files).  Hand written files (scripts, manifests, the player
client entity, loot tables, features) are left untouched.  Finally it zips both
packs into dist/AlienEvo.mcaddon.
"""
import io
import json
import os
import re
import shutil
import sys
import zipfile

from PIL import Image

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


def badge(alien_dir, name="badge_prototype"):
    return {"geo": f"{G_AL}/{alien_dir}/{name}.geo.json"}


# Every alien that has a model in the jar.  "parts" are rendered with the
# composite of "layers"; "glow" layers are rendered with an emissive material.
# "scale" comes from global.alienevo_scale_N (55 == player size).
ALIENS = [
    dict(id=1, key="pyronite", name="Heatblast", scale=57, parts=[
        dict(geo=f"{G_AL}/alien_1/pyronite_prototype.geo.json",
             layers=[f"{T_AL}/alien_1/heatblast_prototype.png", f"{T_AL}/alien_1/heatblast_ext_prototype.png"],
             glow=[f"{T_AL}/alien_1/heatblast_0_glow_prototype.png"])],
         badge=badge("alien_1")),
    dict(id=2, key="vulpimancer", name="Wildmutt", scale=52, parts=[
        dict(geo=f"{G_AL}/alien_2/vulpimancer_prototype.geo.json",
             layers=[f"{T_AL}/alien_2/vulpimancer_skin_prototype.png", f"{T_AL}/alien_2/vulpimancer_uniform_prototype.png"])],
         badge=badge("alien_2")),
    dict(id=3, key="petrosapien", name="Diamondhead", scale=62, parts=[
        dict(geo=f"{G_AL}/alien_3/petrosapien_prototype.geo.json",
             layers=[f"{T_AL}/alien_3/petrosapien_skin_prototype.png", f"{T_AL}/alien_3/petrosapien_uniform_prototype.png"],
             glow=[f"{T_AL}/alien_3/petrosapien_glow_prototype.png"])],
         badge=badge("alien_3")),
    dict(id=4, key="kineceleran", name="XLR8", scale=65, parts=[
        dict(geo=f"{G_AL}/alien_4/kineceleran_prototype.geo.json",
             layers=[f"{T_AL}/alien_4/kineceleran_skin_prototype.png", f"{T_AL}/alien_4/kineceleran_uniform_prototype.png"],
             glow=[f"{T_AL}/alien_4/kineceleran_glow_prototype.png"])],
         badge=badge("alien_4")),
    dict(id=5, key="galvan", name="Grey Matter", scale=50, parts=[
        dict(geo=f"{G_AL}/alien_5/galvan_prototype.geo.json",
             layers=[f"{T_AL}/alien_5/galvan_skin_prototype.png", f"{T_AL}/alien_5/galvan_uniform_prototype.png"],
             glow=[f"{T_AL}/alien_5/galvan_glow_prototype.png"])],
         badge=badge("alien_5")),
    dict(id=6, key="tetramand", name="Four Arms", scale=75, parts=[
        dict(geo=f"{G_AL}/alien_6/tetramand_prototype.geo.json",
             layers=[f"{T_AL}/alien_6/tetramand_skin_prototype.png", f"{T_AL}/alien_6/tetramand_uniform_prototype.png"],
             glow=[f"{T_AL}/alien_6/tetramand_glow_prototype.png"]),
        dict(geo=f"{G_AL}/alien_6/tetramand_arms_prototype.geo.json",
             layers=[f"{T_AL}/alien_6/tetramand_skin_prototype.png", f"{T_AL}/alien_6/tetramand_uniform_prototype.png"])],
         badge=badge("alien_6")),
    dict(id=7, key="lepidopterran", name="Stinkfly", scale=37, parts=[
        dict(geo=f"{G_AL}/alien_7/lepidopterran_prototype.geo.json",
             layers=[f"{T_AL}/alien_7/lepidopterran_uniform_prototype.png", f"{T_AL}/alien_7/lepidopterran_skin_prototype.png"],
             glow=[f"{T_AL}/alien_7/lepidopterran_glow_prototype.png"]),
        dict(geo=f"{G_AL}/alien_7/lepidopterran_legs_prototype.geo.json",
             layers=[f"{T_AL}/alien_7/lepidopterran_skin_prototype.png"]),
        dict(geo=f"{G_AL}/alien_7/lepidopterran_wings.geo.json",
             layers=[f"{T_AL}/alien_7/wings_prototype.png"], translucent=True)],
         badge=badge("alien_7")),
    dict(id=8, key="piscciss_volann", name="Ripjaws", scale=60, parts=[
        dict(geo=f"{G_AL}/alien_8/piscciss_volann_prototype.geo.json",
             layers=[f"{T_AL}/alien_8/piscciss_volann_skin_prototype.png", f"{T_AL}/alien_8/piscciss_volann_uniform_prototype.png"],
             glow=[f"{T_AL}/alien_8/piscciss_volann_glow_prototype.png"])],
         badge=badge("alien_8")),
    dict(id=9, key="galvanic_mechamorph", name="Upgrade", scale=65, parts=[
        dict(geo=f"{G_AL}/alien_9/galvanic_mechamorph_prototype.geo.json",
             layers=[f"{T_AL}/alien_9/galvanic_mechamorph_prototype.png"],
             glow=[f"{T_AL}/alien_9/galvanic_mechamorph_glow_prototype.png"])],
         badge=badge("alien_9")),
    dict(id=10, key="ectonurite", name="Ghostfreak", scale=68, parts=[
        dict(geo=f"{G_AL}/alien_10/ectonurite_prototype.geo.json",
             layers=[f"{T_AL}/alien_10/ectonurite_skin_0_prototype.png"],
             glow=[f"{T_AL}/alien_10/ectonurite_glow_prototype.png"], translucent=True)],
         badge=badge("alien_10")),
    dict(id=11, key="arburian_pelarota", name="Cannonbolt", scale=45, parts=[
        dict(geo=f"{G_AL}/alien_11/arburian_pelarota_prototype.geo.json",
             layers=[f"{T_AL}/alien_11/arburian_pelarota_prototype.png"],
             glow=[f"{T_AL}/alien_11/arburian_pelarota_glow_prototype.png"])],
         badge=badge("alien_11")),
    dict(id=31, key="methanosian", name="Swampfire", scale=55, parts=[
        dict(geo=f"{AF}/geo/methanosian.geo.json", layers=[f"{AF}/textures/models/methanosian/methanosian.png"])]),
    dict(id=32, key="sonorosian", name="Echo Echo", scale=55, parts=[
        dict(geo=f"{AF}/geo/sonorosian.geo.json", layers=[f"{AF}/textures/models/sonorosian/sonorosian.png"],
             glow=[f"{AF}/textures/models/sonorosian/sonorosian_glow.png"])]),
    dict(id=33, key="vaxasaurian", name="Humungousaur", scale=55, parts=[
        dict(geo=f"{AF}/geo/vaxasaurian.geo.json", layers=[f"{AF}/textures/models/vaxasaurian/vaxasaurian.png"])]),
    dict(id=34, key="aerophibian", name="Jetray", scale=55, parts=[
        dict(geo=f"{G_AL}/alien_34/aerophibian.geo.json", layers=[f"{T_AL}/alien_34/aerophibian.png"])]),
    dict(id=35, key="necrofriggian", name="Big Chill", scale=55, parts=[
        dict(geo=f"{AF}/geo/necrofriggian.geo.json", layers=[f"{AF}/textures/models/necrofriggian/necrofriggian_0.png"],
             glow=[f"{AF}/textures/models/necrofriggian/necrofriggian_glow.png"])]),
    dict(id=36, key="crystalsapien", name="Chromastone", scale=55, parts=[
        dict(geo=f"{AF}/geo/crystalsapien.geo.json", layers=[f"{AF}/textures/models/crystalsapien/crystalsapien.png"],
             glow=[f"{AF}/textures/models/crystalsapien/chromastone_glow.png"])]),
    dict(id=80, key="nucleonix", name="Atomix", scale=55, parts=[
        dict(geo=f"{G_AL}/alien_60/atomix.geo.json", layers=[f"{T_AL}/alien_60/atomix.png"],
             glow=[f"{T_AL}/alien_60/atomix_glow_0.png"])]),
    dict(id=100, key="dragonoid", name="Dragonoid", scale=55, parts=[
        dict(geo=f"{G_AL}/alien_100/dragonoid.geo.json", layers=[f"{T_AL}/alien_100/dragonoid.png"],
             glow=[f"{T_AL}/alien_100/dragonoid_glow.png"])]),
    dict(id=101, key="astrobot", name="Astro Bot", scale=55, parts=[
        dict(geo=f"{G_AL}/alien_101/astrobot.geo.json", layers=[f"{T_AL}/alien_101/astrobot.png"],
             glow=[f"{T_AL}/alien_101/astrobot_glow.png"])]),
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

def convert_geo(src, identifier):
    geo = src["minecraft:geometry"][0]
    desc = dict(geo["description"])
    desc["identifier"] = identifier
    bones = []
    for bone in geo.get("bones", []):
        bone = dict(bone)
        bone["name"] = BONE_MAP.get(bone["name"], bone["name"])
        if "parent" in bone:
            bone["parent"] = BONE_MAP.get(bone["parent"], bone["parent"])
        elif bone["name"] in BOOT_PARENT:
            bone["parent"] = BOOT_PARENT[bone["name"]]
        bones.append(bone)
    return {"format_version": "1.12.0", "minecraft:geometry": [{"description": desc, "bones": bones}]}


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

def build_aliens(jar, lang):
    geo_dir = os.path.join(RP, "models", "entity", "aliens")
    tex_dir = os.path.join(RP, "textures", "entity", "aliens")
    att_dir = os.path.join(RP, "attachables", "aliens")
    for d in (geo_dir, tex_dir, att_dir):
        reset_dir(d)

    controllers = {}
    badge_img = composite([jar.image(f"{BADGE_TEX}/badge_prototype.png")] + [
        jar.image(f"{BADGE_TEX}/prototype/{p}/{p}_0.png") for p in ("core_side", "core_top", "dial_inner", "dial_outer")
        if jar.exists(f"{BADGE_TEX}/prototype/{p}/{p}_0.png")])
    save_png(badge_img, os.path.join(tex_dir, "badge.png"))
    save_png(tint(jar.image(f"{BADGE_TEX}/badge_glow_default_prototype.png"), GLOW[0]), os.path.join(tex_dir, "badge_glow.png"))

    for alien in ALIENS:
        key = alien["key"]
        textures, geometry, rcs = {}, {}, []
        materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha", "translucent": "entity_alphablend"}
        for i, part in enumerate(alien["parts"]):
            pid = f"{key}_{i}"
            geo_id = f"geometry.alienevo.{pid}"
            write_json(os.path.join(geo_dir, f"{pid}.geo.json"), convert_geo(jar.json(part["geo"]), geo_id))
            save_png(composite([jar.image(p) for p in part["layers"]]), os.path.join(tex_dir, f"{pid}.png"))
            geometry[f"part{i}"] = geo_id
            textures[f"part{i}"] = f"textures/entity/aliens/{pid}"
            mat = "translucent" if part.get("translucent") else "default"
            rc = f"controller.render.alienevo.{pid}"
            controllers[rc] = {"geometry": f"Geometry.part{i}", "materials": [{"*": f"Material.{mat}"}],
                               "textures": [f"Texture.part{i}"]}
            rcs.append({rc: "!c.is_first_person"})
            if part.get("glow"):
                save_png(composite([jar.image(p) for p in part["glow"]]), os.path.join(tex_dir, f"{pid}_glow.png"))
                textures[f"part{i}_glow"] = f"textures/entity/aliens/{pid}_glow"
                rcg = f"controller.render.alienevo.{pid}_glow"
                controllers[rcg] = {"geometry": f"Geometry.part{i}", "materials": [{"*": "Material.glow"}],
                                    "textures": [f"Texture.part{i}_glow"]}
                rcs.append({rcg: "!c.is_first_person"})
        if alien.get("badge"):
            geo_id = f"geometry.alienevo.{key}_badge"
            write_json(os.path.join(geo_dir, f"{key}_badge.geo.json"), convert_geo(jar.json(alien["badge"]["geo"]), geo_id))
            geometry["badge"] = geo_id
            textures["badge"] = "textures/entity/aliens/badge"
            textures["badge_glow"] = "textures/entity/aliens/badge_glow"
            rcs.append({"controller.render.alienevo.badge": "!c.is_first_person"})
            rcs.append({"controller.render.alienevo.badge_glow": "!c.is_first_person"})

        write_json(os.path.join(att_dir, f"form_{key}.json"), {
            "format_version": "1.10.0",
            "minecraft:attachable": {
                "description": {
                    "identifier": f"alienevo:form_{key}",
                    "materials": materials,
                    "textures": textures,
                    "geometry": geometry,
                    "scripts": {"parent_setup": "v.chest_layer_visible = 0.0; v.helmet_layer_visible = 0.0; v.leg_layer_visible = 0.0; v.boot_layer_visible = 0.0;"},
                    "render_controllers": rcs,
                }
            },
        })
        lang[f"item.alienevo:form_{key}"] = alien["name"]

    controllers["controller.render.alienevo.badge"] = {"geometry": "Geometry.badge", "materials": [{"*": "Material.default"}],
                                                       "textures": ["Texture.badge"]}
    controllers["controller.render.alienevo.badge_glow"] = {"geometry": "Geometry.badge", "materials": [{"*": "Material.glow"}],
                                                            "textures": ["Texture.badge_glow"]}
    write_json(os.path.join(RP, "render_controllers", "alienevo.render_controllers.json"),
               {"format_version": "1.10.0", "render_controllers": controllers})

    # Holograms of the aliens are used as the selection icons.
    icon_dir = os.path.join(RP, "textures", "ui", "aliens")
    reset_dir(icon_dir)
    for alien in ALIENS:
        img = jar.image(alien["parts"][0]["layers"][0])
        # Face of a humanoid 64x64 skin is at (8,8)-(16,16).
        scale = img.size[0] // 64 or 1
        face = img.crop((8 * scale, 8 * scale, 16 * scale, 16 * scale)).resize((32, 32), Image.NEAREST)
        save_png(face, os.path.join(icon_dir, f"{alien['key']}.png"))


def build_player_scale_animation():
    """Scale the player skeleton (and therefore the attachable) per alien."""
    expr = "1.0"
    for alien in ALIENS:
        s = round(alien["scale"] / 55.0, 3)
        if s != 1.0:
            expr = f"q.is_item_name_any('slot.armor.chest', 0, 'alienevo:form_{alien['key']}') ? {s} : ({expr})"
    write_json(os.path.join(RP, "animations", "alienevo.player.animation.json"), {
        "format_version": "1.8.0",
        "animations": {
            "animation.alienevo.player.scale": {
                "loop": True,
                "bones": {"root": {"scale": "v.alienevo_scale"}},
            }
        },
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


def build_player_entity(scale_expr):
    """Patch the vanilla player client entity (Bedrock 1.26) so the player's own
    body is hidden while an alien form is worn, and the skeleton is scaled."""
    with open(os.path.join(ROOT, "tools", "vanilla_player.entity.json"), encoding="utf-8") as f:
        data = json.load(f)
    desc = data["minecraft:client_entity"]["description"]
    alien = "q.equipped_item_any_tag('slot.armor.chest', 'alienevo:alien_form')"
    desc["scripts"]["pre_animation"].append(f"v.alienevo_is_alien = {alien};")
    desc["scripts"]["pre_animation"].append(f"v.alienevo_scale = {scale_expr};")
    desc["animations"]["alienevo_scale"] = "animation.alienevo.player.scale"
    desc["scripts"]["animate"].append({"alienevo_scale": "!v.is_first_person && v.alienevo_is_alien"})
    rcs = []
    for rc in desc["render_controllers"]:
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
        save_png(jar.image(f"{src}/{item_id}.png"), os.path.join(tex_dir, f"{item_id}.png"))
        item_textures[f"alienevo:{item_id}"] = {"textures": f"textures/items/{item_id}"}
    # Alien form items reuse the selection icons.
    for alien in ALIENS:
        item_textures[f"alienevo:form_{alien['key']}"] = {"textures": f"textures/ui/aliens/{alien['key']}"}


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
    for ns in ("alienevo", "afomni"):
        sj = f"assets/{ns}/sounds.json"
        if not jar.exists(sj):
            continue
        for event, data in jar.json(sj).items():
            files = []
            for s in data.get("sounds", []):
                name = s["name"] if isinstance(s, dict) else s
                sns, path = name.split(":") if ":" in name else (ns, name)
                src = f"assets/{sns}/sounds/{path}.ogg"
                if not jar.exists(src):
                    continue
                dst = os.path.join(out, path + ".ogg")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f:
                    f.write(jar.read(src))
                files.append({"name": f"sounds/alienevo/{path}", "volume": 1.0})
            if files:
                defs[f"alienevo.{event}"] = {"category": "player", "sounds": files}
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


def package():
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
    lang, item_textures, terrain = {}, {}, {}
    build_lang(jar, lang)
    build_aliens(jar, lang)
    build_player_entity(build_player_scale_animation())
    build_projectiles(jar)
    build_items_rp(jar, lang, item_textures)
    build_blocks_rp(jar, terrain)
    build_sounds(jar)
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": "alienevo", "texture_name": "atlas.items", "texture_data": item_textures})
    write_json(os.path.join(RP, "textures", "terrain_texture.json"),
               {"resource_pack_name": "alienevo", "texture_name": "atlas.terrain", "padding": 8, "num_mip_levels": 4,
                "texture_data": terrain})
    save_png(jar.image("alienevo_icon.png").resize((256, 256), Image.NEAREST), os.path.join(RP, "pack_icon.png"))
    save_png(jar.image("alienevo_icon.png").resize((256, 256), Image.NEAREST), os.path.join(BP, "pack_icon.png"))
    build_items_bp()
    build_blocks_bp()
    build_recipes(jar)
    write_lang(lang)
    package()


if __name__ == "__main__":
    main()
