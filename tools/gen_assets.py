#!/usr/bin/env python3
"""Sinh item JSON, recipe và texture pixel-art cho addon Đấu La Đại Lục (không cần PIL)."""
import json, math, os, struct, zlib

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon")
BP = os.path.join(ROOT, "DLDL_BP")
RP = os.path.join(ROOT, "DLDL_RP")


def write_png(path, px):
    h, w = len(px), len(px[0])
    raw = b"".join(b"\x00" + b"".join(bytes(c) for c in row) for row in px)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def blank(n=16):
    return [[(0, 0, 0, 0) for _ in range(n)] for _ in range(n)]


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def ring(color, edge, n=16, ro=7.2, ri=4.2):
    px = blank(n)
    c = (n - 1) / 2
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - c, y - c)
            if ri <= d <= ro:
                t = (d - ri) / (ro - ri)
                col = mix(color, edge, abs(t - 0.5) * 2)
                if x + y < n - 3 and abs(d - (ri + ro) / 2) < 0.8:
                    col = mix(col, (255, 255, 255), 0.45)
                px[y][x] = col
    return px


def crystal():
    px = blank()
    for y in range(16):
        for x in range(16):
            if abs(x - 7.5) / 5.5 + abs(y - 7.5) / 7.5 <= 1:
                t = y / 15
                col = mix((180, 120, 255), (60, 220, 255), t)
                if x < 7.5 and abs(x - 7.5) / 5.5 + abs(y - 7.5) / 7.5 > 0.7:
                    col = mix(col, (255, 255, 255), 0.5)
                if abs(x - 7.5) < 0.6:
                    col = mix(col, (255, 255, 255), 0.3)
                px[y][x] = col
    return px


def token():
    px = blank()
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - 7.5, y - 7.5)
            if d <= 7.3:
                col = mix((255, 215, 80), (170, 110, 20), d / 7.3)
                if d <= 4.2:
                    col = mix((90, 170, 255), (20, 60, 160), d / 4.2)
                if 3.0 <= d <= 3.6 or (d <= 1.2):
                    col = (255, 245, 200, 255)
                px[y][x] = col
    return px


def bone():
    px = blank()
    pts = [(i, 15 - i) for i in range(3, 13)]
    for x, y in pts:
        for dx, dy in ((0, 0), (1, 0), (0, -1)):
            px[y + dy][x + dx] = (245, 240, 220, 255)
    for cx, cy in ((3, 12), (2, 13), (12, 3), (13, 2)):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                xx, yy = cx + dx, cy + dy
                if 0 <= xx < 16 and 0 <= yy < 16:
                    px[yy][xx] = (255, 250, 235, 255)
    # viền vàng (hồn cốt phát sáng)
    out = blank()
    for y in range(16):
        for x in range(16):
            if px[y][x][3]:
                out[y][x] = px[y][x]
            elif any(0 <= x + a < 16 and 0 <= y + b < 16 and px[y + b][x + a][3] for a in (-1, 0, 1) for b in (-1, 0, 1)):
                out[y][x] = (255, 200, 60, 200)
    return out


def herb():
    px = blank()
    for y in range(6, 16):
        px[y][7] = (60, 140, 50, 255)
    leaves = [(5, 9), (4, 8), (3, 7), (9, 10), (10, 9), (11, 8), (6, 6), (5, 5), (9, 6), (10, 5), (8, 12), (9, 12)]
    for x, y in leaves:
        px[y][x] = (90, 200, 80, 255)
        if y + 1 < 16:
            px[y + 1][x] = (60, 160, 60, 255)
    for x, y in ((7, 2), (6, 3), (8, 3), (7, 3), (7, 4), (6, 1), (8, 1)):
        px[y][x] = (120, 220, 255, 255)
    px[2][7] = (255, 255, 255, 255)
    return px


def pack_icon():
    n = 64
    px = [[(18, 14, 34, 255) for _ in range(n)] for _ in range(n)]
    cols = [(240, 240, 240), (255, 215, 60), (170, 80, 255), (40, 40, 40), (230, 40, 40)]
    c = (n - 1) / 2
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - c, (y - c) * 1.0)
            for i, col in enumerate(cols):
                r = 9 + i * 5
                if abs(d - r) < 1.6:
                    px[y][x] = mix(col, (255, 255, 255), 0.15 if i != 3 else 0.0)
                    if i == 3 and abs(d - r) > 1.0:
                        px[y][x] = (150, 60, 200, 255)
            if d < 6:
                px[y][x] = mix((90, 200, 255), (20, 60, 160), d / 6)
    return px


RINGS = [
    ("10", (235, 235, 235), (170, 170, 170)),
    ("100", (255, 220, 60), (190, 140, 0)),
    ("1000", (170, 80, 255), (90, 20, 170)),
    ("10000", (35, 30, 40), (130, 50, 190)),
    ("100000", (235, 40, 40), (130, 0, 0)),
]

ITEMS = {}  # id -> (texture px, extra components)


def item_json(ident, icon, extra):
    comps = {"minecraft:icon": icon, "minecraft:max_stack_size": 64}
    comps.update(extra)
    return {
        "format_version": "1.21.40",
        "minecraft:item": {
            "description": {"identifier": ident, "menu_category": {"category": "items"}},
            "components": comps,
        },
    }


def main():
    tex = {}
    items = [
        ("awakening_crystal", crystal(), {"minecraft:glint": True, "minecraft:max_stack_size": 16}),
        ("spirit_token", token(), {"minecraft:max_stack_size": 1, "minecraft:hand_equipped": True}),
        ("soul_bone", bone(), {"minecraft:glint": True, "minecraft:max_stack_size": 16, "minecraft:rarity": {"value": "epic"}}),
        ("immortal_herb", herb(), {
            "minecraft:food": {"nutrition": 6, "saturation_modifier": 1.0, "can_always_eat": True},
            "minecraft:use_modifiers": {"use_duration": 1.6, "movement_modifier": 0.35},
            "minecraft:use_animation": "eat",
            "minecraft:rarity": {"value": "rare"},
        }),
    ]
    rarity = ["common", "uncommon", "rare", "epic", "epic"]
    for i, (age, col, edge) in enumerate(RINGS):
        extra = {"minecraft:max_stack_size": 16, "minecraft:rarity": {"value": rarity[i]}}
        if i >= 2:
            extra["minecraft:glint"] = True
        items.append((f"soul_ring_{i}", ring(col, edge), extra))

    for name, px, extra in items:
        ident = f"dld:{name}"
        icon = f"dld_{name}"
        with open(os.path.join(BP, "items", f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(item_json(ident, icon, extra), f, indent=2, ensure_ascii=False)
        write_png(os.path.join(RP, "textures", "items", f"{name}.png"), px)
        tex[icon] = {"textures": f"textures/items/{name}"}

    with open(os.path.join(RP, "textures", "item_texture.json"), "w") as f:
        json.dump({"resource_pack_name": "dldl", "texture_name": "atlas.items", "texture_data": tex}, f, indent=2)

    icon = pack_icon()
    write_png(os.path.join(BP, "pack_icon.png"), icon)
    write_png(os.path.join(RP, "pack_icon.png"), icon)

    # Hạt hiệu ứng hồn hoàn (màu theo niên hạn)
    for i, (age, col, edge) in enumerate(RINGS):
        c = [round(v / 255, 3) for v in (col if i != 3 else (60, 20, 90))] + [1.0]
        particle = {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {
                    "identifier": f"dld:soul_ring_{i}",
                    "basic_render_parameters": {"material": "particles_alpha", "texture": "textures/particle/particles"},
                },
                "components": {
                    "minecraft:emitter_rate_instant": {"num_particles": 1},
                    "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                    "minecraft:emitter_shape_point": {},
                    "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
                    "minecraft:particle_initial_speed": 0,
                    "minecraft:particle_appearance_billboard": {
                        "size": [0.12, 0.12],
                        "facing_camera_mode": "lookat_xyz",
                        "uv": {"texture_width": 128, "texture_height": 128, "uv": [24, 0], "uv_size": [8, 8]},
                    },
                    "minecraft:particle_appearance_tinting": {"color": c},
                    "minecraft:particle_appearance_lighting": {},
                },
            },
        }
        with open(os.path.join(RP, "particles", f"soul_ring_{i}.json"), "w") as f:
            json.dump(particle, f, indent=2)

    recipes = {
        "awakening_crystal": {
            "pattern": [" A ", "ADA", " A "],
            "key": {"A": {"item": "minecraft:amethyst_shard"}, "D": {"item": "minecraft:diamond"}},
            "result": {"item": "dld:awakening_crystal"},
            "unlock": [{"item": "minecraft:amethyst_shard"}],
        },
        "spirit_token": {
            "pattern": [" G ", "GLG", " S "],
            "key": {"G": {"item": "minecraft:gold_ingot"}, "L": {"item": "minecraft:lapis_lazuli"}, "S": {"item": "minecraft:stick"}},
            "result": {"item": "dld:spirit_token"},
            "unlock": [{"item": "minecraft:gold_ingot"}],
        },
    }
    for name, r in recipes.items():
        body = {"description": {"identifier": f"dld:{name}"}, "tags": ["crafting_table"]}
        body.update(r)
        with open(os.path.join(BP, "recipes", f"{name}.json"), "w") as f:
            json.dump({"format_version": "1.20.10", "minecraft:recipe_shaped": body}, f, indent=2)


if __name__ == "__main__":
    main()
