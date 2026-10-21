"""Omnitrix HUD (scripts/hud.js): the Omnitrix badge with health and energy
bars at the top left and the ability bar of the Java mod (Palladium
ability_bar/interface_alien.png with the alien ability icons of
textures/gui/aliens) at the right while transformed.

The script sends its state as a title starting with PREFIX.  A hidden data
control keeps the last such title ("preserved text"), the HUD controls show
or hide on the tokens in it, and the vanilla title display skips it.
"""
import os
import re

from PIL import Image, ImageDraw

PREFIX = "aev:"
KEY_WIDTH = 20  # hud.js KEY_WIDTH
DATA_LEN = len(PREFIX) + 5 + 5 + 4 + (KEY_WIDTH + 3) + 4 + 4 + 4 * 5
BAR_SLOTS = 4  # hud.js BAR_SLOTS
S = 4  # textures are drawn at 1 px per UI unit and saved S times larger

G = "assets/alienevo/textures/gui"
A = f"{G}/aliens"
X = "assets/omni_extras/textures/gui/playlists"
U = "assets/untapped/textures/gui/aliens"
ICONS = {
    "fireball": f"{A}/alien_1/pyro_fireball", "fire_blast": f"{A}/alien_1/pyro_blast",
    "flame_breath": f"{A}/alien_1/pyro_firebreath", "pyro_jump": f"{A}/alien_1/pyro_flight",
    "fireball_barrage": f"{A}/alien_1/pyro_nova", "fire_shield": f"{A}/alien_1/pyro_shield",
    "pounce": f"{A}/alien_2/leap", "quill_barrage": f"{A}/alien_2/quills", "bite": f"{A}/alien_2/bite",
    "predator_sense": f"{A}/alien_2/roar",
    "crystal_shards": f"{A}/alien_3/shards_default", "crystal_wave": f"{A}/alien_3/spikes_default",
    "crystal_shield": f"{A}/alien_3/dome_default",
    "speed_gear": f"{A}/alien_4/speed", "dash": f"{A}/alien_4/boost", "tornado": f"{A}/alien_4/cyclone2",
    "slide": f"{A}/alien_4/water_running",
    "galvan_leap": f"{A}/alien_5/leap", "ore_scan": f"{A}/alien_5/helmet", "tinker": f"{A}/alien_5/suit_0",
    "ground_slam": f"{A}/alien_6/slam", "boulder_throw": f"{A}/alien_6/boulder", "sonic_clap": f"{A}/alien_6/sonic_clap",
    "charge_leap": f"{A}/alien_6/leap",
    "slime_shot": f"{A}/alien_7/slime_spit", "toxic_gas": f"{A}/alien_7/gas", "insect_eyes": f"{A}/alien_7/sonar_pulse",
    "jet_burst": f"{A}/alien_7/flight", "water_cushion": f"{A}/alien_7/fire_supression",
    "aqua_jet": f"{A}/alien_8/waterdash", "tidal_spin": f"{A}/alien_8/whirlpool", "tail_spin": f"{A}/alien_8/tailswipe",
    "super_leap": f"{A}/alien_8/leap", "water_cannon": f"{A}/alien_8/wave", "water_blast": f"{A}/alien_8/wave",
    "energy_beam": f"{A}/alien_9/beam_default", "liquid_form": f"{A}/alien_9/puddle_default",
    "spike_hands": f"{A}/alien_9/spikes_default", "laser_jump": f"{A}/alien_9/glide_default",
    "rocket_punch": f"{A}/alien_9/punch", "lightning_strike": f"{A}/alien_9/storm", "stun_field": f"{A}/alien_9/lightning_beams",
    "phase": f"{A}/alien_10/intangible", "shadow_strike": f"{A}/alien_10/shadowstrike", "scare": f"{A}/alien_10/scare",
    "roll": f"{A}/alien_11/ball", "roll_leap": f"{A}/alien_11/leap", "sound_wall": f"{A}/alien_11/block",
    "earthquake": f"{A}/alien_11/rumble",
    "prism_beam": f"{A}/alien_176/double_beam", "energy_release": f"{A}/alien_176/beam_barrage",
    "howl": f"{A}/alien_209/howl",
    "bloom": f"{A}/alien_222/pollination", "vine_snare": f"{A}/alien_222/vine", "fruit_bomb": f"{A}/alien_222/fruit",
    "freeze_breath": f"{X}/opticoid/ice_beam/ice_beam_default", "ice_shards": f"{X}/opticoid/ice_aoe",
    "atomic_beam": f"{X}/opticoid/energy/energy_default", "nuclear_burst": f"{X}/opticoid/overcharge/overcharge_default",
    "eye_beam": f"{X}/opticoid/eye_beam/eye_beam_default", "super_eye_beam": f"{X}/opticoid/shoulder_beam/shoulder_beam_default",
    "elemental_eyes": f"{X}/opticoid/el_sel/el_sel_default",
    "swallow": f"{X}/gourmand/perk/swallow/swallow_default", "gut_blast": f"{X}/gourmand/perk/mega_spit/mega_spit_default",
    "drill": f"{X}/talpaedan/drill/drill_2_default", "quake": f"{X}/talpaedan/jump_slam/jump_slam_default",
    "sonic_scream": f"{X}/nosedeenian/scream/scream_default", "neuroshock": f"{X}/nosedeenian/zap/zap_default",
    "electro_bolt": f"{X}/nosedeenian/thunder_beam/thunder_beam_default",
    "discharge": f"{X}/nosedeenian/discharge/discharge_default",
    "camouflage": f"{U}/alien_200/camouflage", "stinger": f"{U}/alien_200/stinger_combo",
    "flip": f"{U}/alien_202/flip", "clone_swarm": f"{U}/alien_202/split", "taunt": f"{U}/alien_202/taunt",
    "uppercut": f"{U}/alien_202/uppercut",
    "eat": f"{U}/alien_203/eat_up", "horn_beam": f"{U}/alien_203/beam", "ram": f"{U}/alien_203/ram",
}
FALLBACK_ICON = f"{G}/prototype/base_empty"

GREEN = (122, 230, 40, 255)
DARK_GREEN = (52, 120, 20, 255)
BLACK = (12, 12, 12, 255)
BODY = (32, 32, 34, 255)
RIM = (88, 88, 92, 255)
RIM_LIGHT = (130, 130, 136, 255)


def parse_aliens(bp):
    """(key, [ability ids]) from BP scripts/aliens.js in codex order."""
    with open(os.path.join(bp, "scripts", "aliens.js"), encoding="utf-8") as f:
        src = f.read()
    out = []
    for m in re.finditer(r'key: "([a-z_]+)".*?abilities: \[([^\]]*)\]', src, re.S):
        out.append((m.group(1), re.findall(r'"([a-z_]+)"', m.group(2))))
    return out


def _save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.resize((img.width * S, img.height * S), Image.NEAREST).save(path, optimize=True)


def _icon(vfs, path):
    img = vfs.image(path + ".png")
    side = min(img.size)
    img = img.crop((0, 0, side, side))  # animated strips: first frame
    return img.resize((16, 16), Image.NEAREST) if side != 16 else img


def _bar_sheet(vfs):
    return vfs.image(f"{G}/ability_bar/interface_alien.png")


def ability_column(sheet, icons):
    """The ability bar of interface_alien.png with len(icons) slots, then the
    Omnitrix slot.  Slot k's 18x18 inside starts at (3, 3 + 22k); the
    Omnitrix slot's at (3, 22n + 6)."""
    n = len(icons)
    top = sheet.crop((0, 56, 24, 56 + 22 * (n - 1)))
    last = sheet.crop((0, 144, 24, 168))
    omni = sheet.crop((0, 168, 24, 192))
    img = Image.new("RGBA", (24, top.height + last.height + 1 + omni.height))
    img.alpha_composite(top, (0, 0))
    img.alpha_composite(last, (0, top.height))
    img.alpha_composite(omni, (0, top.height + last.height + 1))
    # Dark inside like the Java bar so the icons stand out.
    for k in range(n + 1):
        y = 3 + 22 * k if k < n else 22 * n + 6
        shade = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
        ImageDraw.Draw(shade).rectangle((1, 1, 16, 16), fill=(20, 20, 20, 170))
        img.alpha_composite(shade, (3, y))
    for k, icon in enumerate(icons):
        img.alpha_composite(icon, (4, 4 + 22 * k))
    return img


def slot_y(k, n):
    return 3 + 22 * k if k < n else 22 * n + 6


def draw_panel():
    """Badge ring + plate with two bar slots (the Omnitrix HUD plate)."""
    w, h = 120, 36
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    # Plate.
    d.polygon([(24, 5), (114, 5), (119, 10), (119, 26), (114, 31), (24, 31)], fill=BLACK)
    d.polygon([(25, 6), (113, 6), (118, 11), (118, 25), (113, 30), (25, 30)], fill=RIM)
    d.polygon([(27, 8), (112, 8), (116, 12), (116, 24), (112, 28), (27, 28)], fill=BODY)
    d.line([(26, 7), (112, 7)], fill=RIM_LIGHT)
    for x in range(92, 108, 4):
        d.rectangle((x, 6, x + 2, 6), fill=GREEN)
        d.rectangle((x, 30, x + 2, 30), fill=GREEN)
    d.rectangle((116, 14, 117, 22), fill=GREEN)
    # Bar slots.
    for y in (10, 19):
        d.rectangle((35, y, 110, y + 6), fill=BLACK)
        d.rectangle((36, y + 1, 109, y + 5), fill=(48, 48, 50, 255))
    # Badge ring.
    d.ellipse((0, 0, 35, 35), fill=BLACK)
    d.ellipse((1, 1, 34, 34), fill=RIM)
    d.ellipse((3, 3, 32, 32), fill=(58, 58, 62, 255))
    d.ellipse((5, 5, 30, 30), fill=BLACK)
    for x, y in ((17, 1), (17, 33), (1, 17), (33, 17)):
        d.rectangle((x, y, x + 1, y + 1), fill=GREEN)
    return img


def bar_fill(top, bottom):
    img = Image.new("RGBA", (1, 5))
    for y in range(5):
        t = y / 4
        img.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,))
    img.putpixel((0, 0), tuple(min(255, c + 60) for c in top[:3]) + (255,))
    return img


def badge(base, overlay, box=(6, 6, 26, 26)):
    """32x32 badge: a 16 px Omnitrix face scaled up with an image fitted in box."""
    img = base.resize((32, 32), Image.NEAREST).copy()
    if overlay is not None:
        bb = overlay.getbbox()
        if bb:
            o = overlay.crop(bb)
            bw, bh = box[2] - box[0], box[3] - box[1]
            s = min(bw / o.width, bh / o.height)
            o = o.resize((max(1, round(o.width * s)), max(1, round(o.height * s))), Image.NEAREST)
            img.alpha_composite(o, (box[0] + (bw - o.width) // 2, box[1] + (bh - o.height) // 2))
    return img


def has(token):
    return f"(not ((#preserved_text - '{token}') = #preserved_text))"


def view(expr, target="#visible"):
    return {"binding_type": "view", "source_control_name": "alienevo_hud_data",
            "source_property_name": expr, "target_property_name": target}


def image(texture, size, offset, cond, layer, anchor="top_left", **extra):
    ctrl = {"type": "image", "texture": texture, "size": size, "offset": offset, "layer": layer,
            "anchor_from": anchor, "anchor_to": anchor, "bindings": [view(cond)]}
    ctrl.update(extra)
    return ctrl


def build(vfs, rp, bp):
    aliens = parse_aliens(bp)
    assert all(len(k) <= KEY_WIDTH for k, _ in aliens)
    tex = os.path.join(rp, "textures", "ui", "alienevo", "hud")
    T = "textures/ui/alienevo/hud/"
    sheet = _bar_sheet(vfs)
    _save(draw_panel(), os.path.join(tex, "panel.png"))
    _save(bar_fill((255, 70, 60), (150, 10, 10)), os.path.join(tex, "health.png"))
    _save(bar_fill((150, 255, 60), (40, 140, 10)), os.path.join(tex, "energy.png"))
    _save(bar_fill((255, 170, 40), (170, 60, 0)), os.path.join(tex, "recharge.png"))
    face = vfs.image(f"{G}/prototype/base_empty.png")
    _save(badge(vfs.image(f"{G}/prototype/omnitrix_main/omnitrix_main_timeout.png"), None), os.path.join(tex, "badge_recharge.png"))
    _save(badge(vfs.image(f"{G}/prototype/omnitrix_main/omnitrix_main_default.png"), None), os.path.join(tex, "badge_ready.png"))
    sel = Image.new("RGBA", (20, 20))
    ImageDraw.Draw(sel).rectangle((0, 0, 19, 19), outline=GREEN)
    ImageDraw.Draw(sel).rectangle((1, 1, 18, 18), outline=(122, 230, 40, 110), fill=(122, 230, 40, 60))
    _save(sel, os.path.join(tex, "selected.png"))
    _save(sheet.crop((45, 75, 57, 91)), os.path.join(tex, "lock.png"))
    cd = Image.new("RGBA", (16, 16), (0, 0, 0, 150))
    _save(cd, os.path.join(tex, "cooldown.png"))
    missing = set()
    sil_dir = os.path.join(rp, "textures", "entity", "omnitrix")
    portrait_dir = os.path.join(rp, "textures", "ui", "aliens")

    ns = {"namespace": "alienevo_hud"}
    # Keeps the last HUD title (the usual "preserved title" pattern).
    ns["data"] = {
        "type": "panel", "size": [0, 0],
        "property_bag": {"#preserved_text": ""},
        "bindings": [
            {"binding_name": "#hud_title_text_string"},
            {"binding_name": "#hud_title_text_string", "binding_name_override": "#preserved_text",
             "binding_condition": "visibility_changed"},
            {"binding_type": "view", "target_property_name": "#visible",
             "source_property_name": f"(not (#hud_title_text_string = #preserved_text) and not ((#hud_title_text_string - '{PREFIX}') = #hud_title_text_string))"},
        ],
    }
    worn = f"((not (#preserved_text = '')) and ((#preserved_text - '[m0]') = #preserved_text))"

    # -------------------------------------------------- top left plate
    plate = [{"bg": {"type": "image", "texture": T + "panel", "size": [120, 36], "layer": 1,
                     "anchor_from": "top_left", "anchor_to": "top_left"}}]
    for k in range(1, 21):
        w = round(74 * k / 20)
        plate.append({f"health_{k}": image(T + "health", [w, 5], [36, 11], has(f"[h{k:02d}]"), 3)})
        plate.append({f"energy_{k}": image(T + "energy", [w, 5], [36, 20], f"({has(f'[e{k:02d}]')} and ((#preserved_text - '[m2]') = #preserved_text))", 3)})
        plate.append({f"recharge_{k}": image(T + "recharge", [w, 5], [36, 20], f"({has(f'[e{k:02d}]')} and {has('[m2]')})", 3)})
    plate.append({"badge_ready": image(T + "badge_ready", [26, 26], [5, 5], f"({has('[m1]')} and {has('[b' + '.' * KEY_WIDTH + ']')})", 4)})
    plate.append({"badge_recharge": image(T + "badge_recharge", [26, 26], [5, 5], has("[m2]"), 4)})
    columns = []
    for key, abilities in aliens:
        token = "[b" + key.ljust(KEY_WIDTH, ".") + "]"
        sil_path = os.path.join(sil_dir, f"sil_{key}.png")
        sil = Image.open(sil_path).convert("RGBA") if os.path.exists(sil_path) else None
        if sil is not None:
            # Black silhouette of the selected alien on the green Omnitrix face.
            px = sil.load()
            for y in range(sil.height):
                for x in range(sil.width):
                    if px[x, y][3]:
                        px[x, y] = (10, 10, 10, 255)
        _save(badge(face, sil, (9, 7, 23, 25)), os.path.join(tex, f"ready_{key}.png"))
        plate.append({f"ready_{key}": image(T + f"ready_{key}", [26, 26], [5, 5], f"({has('[m1]')} and {has(token)})", 4)})
        portrait_path = os.path.join(portrait_dir, f"{key}.png")
        if os.path.exists(portrait_path):
            portrait = Image.open(portrait_path).convert("RGBA")
            ring = Image.new("RGBA", (32, 32))
            ImageDraw.Draw(ring).ellipse((0, 0, 31, 31), fill=DARK_GREEN)
            ImageDraw.Draw(ring).ellipse((2, 2, 29, 29), fill=(20, 40, 12, 255))
            _save(badge(ring.resize((16, 16), Image.NEAREST), portrait, (5, 5, 27, 27)), os.path.join(tex, f"alien_{key}.png"))
            plate.append({f"alien_{key}": image(T + f"alien_{key}", [26, 26], [5, 5], f"({has('[m3]')} and {has(token)})", 4)})
        # ------------------------------------------ ability bar
        icons = []
        for a in abilities[:BAR_SLOTS]:
            path = ICONS.get(a, FALLBACK_ICON)
            if not vfs.exists(path + ".png"):
                missing.add(a)
                path = FALLBACK_ICON
            icons.append(_icon(vfs, path))
        col = ability_column(sheet, icons)
        col.alpha_composite(vfs.image(f"{G}/prototype/omnitrix_main/omnitrix_main_default.png"), (4, slot_y(len(icons), len(icons)) + 1))
        _save(col, os.path.join(tex, f"bar_{key}.png"))
        columns.append({f"bar_{key}": image(T + f"bar_{key}", [24, col.height], [0, 0], has(token), 1)})
    plate.append({"name": {"type": "label", "text": "#text", "layer": 5, "shadow": True, "color": [1, 1, 1],
                           "anchor_from": "top_left", "anchor_to": "top_left", "offset": [4, 38],
                           "bindings": [view(f"(#preserved_text - ('%.{DATA_LEN}s' * #preserved_text))", "#text")]}})

    # Overlays of the ability bar (selection, locks, cooldowns) per bar length.
    overlays = []
    for n in range(1, BAR_SLOTS + 1):
        for k in range(n + 1):
            y = slot_y(k, n)
            sel_token = f"[k{k if k < n else BAR_SLOTS}]"
            cond = f"({has(sel_token)} and {has(f'[n{n}]')})"
            overlays.append({f"sel_{n}_{k}": image(T + "selected", [20, 20], [2, y - 1], cond, 6)})
            if k < n:
                overlays.append({f"lock_{n}_{k}": image(T + "lock", [12, 16], [6, y + 1], f"({has(f'[{k}c2]')} and {has(f'[n{n}]')})", 7)})
                overlays.append({f"cd_{n}_{k}": image(T + "cooldown", [16, 16], [4, y + 1], f"({has(f'[{k}c1]')} and {has(f'[n{n}]')})", 5)})
    ns["root"] = {
        "type": "panel", "size": ["100%", "100%"], "layer": 30,
        "controls": [
            {"alienevo_hud_data@alienevo_hud.data": {}},
            {"plate": {"type": "panel", "size": [120, 50], "offset": [2, 2], "anchor_from": "top_left", "anchor_to": "top_left",
                       "bindings": [view(worn)], "controls": plate}},
            {"bar": {"type": "panel", "size": [24, 22 * BAR_SLOTS + 27], "offset": [-3, 0],
                     "anchor_from": "right_middle", "anchor_to": "right_middle",
                     "bindings": [view(has("[m3]"))], "controls": columns + overlays}},
        ],
    }
    ui_dir = os.path.join(rp, "ui")
    write = __import__("json").dump
    with open(os.path.join(ui_dir, "alienevo_hud.json"), "w", encoding="utf-8") as f:
        write(ns, f, indent=2)
    # The vanilla title display skips the HUD data; the HUD goes on top of the HUD screen.
    hud_screen = {
        "namespace": "hud",
        "hud_title_text": {
            "bindings": [
                {"binding_name": "#hud_title_text_string"},
                {"binding_type": "view", "target_property_name": "#visible",
                 "source_property_name": f"((#hud_title_text_string - '{PREFIX}') = #hud_title_text_string)"},
            ],
        },
        "root_panel": {
            "modifications": [{"array_name": "controls", "operation": "insert_back",
                               "value": [{"alienevo_hud@alienevo_hud.root": {}}]}],
        },
    }
    with open(os.path.join(ui_dir, "hud_screen.json"), "w", encoding="utf-8") as f:
        write(hud_screen, f, indent=2)
    defs_path = os.path.join(ui_dir, "_ui_defs.json")
    with open(defs_path, encoding="utf-8") as f:
        defs = __import__("json").load(f)
    if "ui/alienevo_hud.json" not in defs["ui_defs"]:
        defs["ui_defs"].append("ui/alienevo_hud.json")
    with open(defs_path, "w", encoding="utf-8") as f:
        write(defs, f, indent=2)
    return len(aliens), sorted(missing)
