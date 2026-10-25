#!/usr/bin/env python3
"""Sinh hồn thú có model 3D riêng: geometry, texture, animation, client entity, BP entity, spawn rule.

Mỗi model được mô tả bằng các bone + cube; texture được tự xếp (box UV) và tô màu theo từng cube.
"""
import json, math, os, random

from gen_assets import write_png, RP, BP

random.seed(77)

TIER_HEALTH = [1.0, 1.5, 2.4, 4.0, 7.0]
TIER_DAMAGE = [1.0, 1.3, 1.7, 2.4, 3.5]
TIER_SCALE = [0.8, 0.95, 1.1, 1.3, 1.55]


def C(origin, size, color, face=None, top=None):
    """cube: color = (r,g,b), face = painter cho mặt trước (north), top = painter cho mặt trên."""
    return {"origin": origin, "size": size, "color": color, "face": face, "top": top}


def B(name, parent, pivot, cubes=(), rotation=None):
    return {"name": name, "parent": parent, "pivot": pivot, "cubes": list(cubes), "rotation": rotation}


# ───────────── Painter chi tiết ─────────────

def eyes(color, y_frac=0.35, gap_frac=0.22, size=1):
    def paint(px, x, y, w, h):
        cy = y + max(1, int(h * y_frac))
        for cx in (x + int(w / 2 - w * gap_frac) - size, x + int(w / 2 + w * gap_frac)):
            for dx in range(size + 1):
                for dy in range(size):
                    put(px, cx + dx, cy + dy, color)
    return paint


def human_face(px, x, y, w, h):
    skin = (226, 200, 190)
    for i in range(1, w - 1):
        for j in range(1, h - 1):
            put(px, x + i, y + j, shade(skin, 0.9 + random.random() * 0.15))
    eyes((180, 0, 20))(px, x, y, w, h)
    for i in range(w // 2 - 2, w // 2 + 2):
        put(px, x + i, y + h - 3, (90, 20, 30))  # miệng
    put(px, x + w // 2 - 1, y + h - 2, (240, 240, 240))
    put(px, x + w // 2, y + h - 2, (240, 240, 240))


def spider_mark(px, x, y, w, h):
    for i in range(w):
        for j in range(h):
            dx, dy = i - w / 2, j - h / 2
            if abs(abs(dx) - abs(dy) * 0.6) < 1.2 and abs(dy) < h * 0.35:
                put(px, x + i, y + j, (200, 20, 40))
            elif abs(dx) < 1 and j % 4 == 0:
                put(px, x + i, y + j, (160, 40, 160))


def stripes(color, every=3):
    def paint(px, x, y, w, h):
        for i in range(w):
            for j in range(h):
                if (i + j) % every == 0:
                    put(px, x + i, y + j, color)
    return paint


def beast_face(eye, nose=None):
    def paint(px, x, y, w, h):
        eyes(eye, 0.3, 0.25, 1)(px, x, y, w, h)
        if nose:
            for i in range(w // 2 - 1, w // 2 + 1):
                put(px, x + i, y + h - 2, nose)
    return paint


def put(px, x, y, c):
    if 0 <= y < len(px) and 0 <= x < len(px[0]):
        px[y][x] = tuple(c[:3]) + (255,)


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


# ───────────── Xếp UV & tô texture ─────────────

def layout(bones, width):
    cubes = [c for b in bones for c in b["cubes"]]
    order = sorted(cubes, key=lambda c: -(c["size"][1] + c["size"][2]))
    x = y = row_h = 0
    for c in order:
        w, h, d = c["size"]
        fw, fh = 2 * (w + d), h + d
        if x + fw > width:
            x, y, row_h = 0, y + row_h, 0
        c["uv"] = [x, y]
        x += fw
        row_h = max(row_h, fh)
    height = 16
    while height < y + row_h:
        height *= 2
    return height


def paint(bones, width, height):
    px = [[(0, 0, 0, 0)] * width for _ in range(height)]
    for b in bones:
        for c in b["cubes"]:
            u, v = c["uv"]
            w, h, d = c["size"]
            faces = {
                "top": (u + d, v, w, d, 1.15),
                "bottom": (u + d + w, v, w, d, 0.7),
                "east": (u, v + d, d, h, 0.85),
                "north": (u + d, v + d, w, h, 1.0),
                "west": (u + d + w, v + d, d, h, 0.85),
                "south": (u + 2 * d + w, v + d, w, h, 0.9),
            }
            for name, (fx, fy, fw, fh, f) in faces.items():
                for i in range(fw):
                    for j in range(fh):
                        n = 0.88 + random.random() * 0.2
                        edge = 0.82 if i in (0, fw - 1) or j in (0, fh - 1) else 1.0
                        put(px, fx + i, fy + j, shade(c["color"], f * n * edge))
            if c["face"]:
                fx, fy, fw, fh, _ = faces["north"]
                c["face"](px, fx, fy, fw, fh)
            if c["top"]:
                fx, fy, fw, fh, _ = faces["top"]
                c["top"](px, fx, fy, fw, fh)
    return px


def geometry(ident, bones, width, height, bounds):
    out = []
    for b in bones:
        jb = {"name": b["name"], "pivot": b["pivot"]}
        if b["parent"]:
            jb["parent"] = b["parent"]
        if b["rotation"]:
            jb["rotation"] = b["rotation"]
        if b["cubes"]:
            jb["cubes"] = [{"origin": c["origin"], "size": c["size"], "uv": c["uv"]} for c in b["cubes"]]
        out.append(jb)
    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": f"geometry.dld.{ident}",
                "texture_width": width,
                "texture_height": height,
                "visible_bounds_width": bounds[0],
                "visible_bounds_height": bounds[1],
                "visible_bounds_offset": [0, bounds[1] / 2, 0],
            },
            "bones": out,
        }],
    }


# ───────────── Model từng hồn thú ─────────────

def spider_bones():
    body, dark, red = (45, 25, 55), (25, 15, 30), (120, 20, 40)
    bones = [
        B("root", None, [0, 0, 0]),
        B("body", "root", [0, 9, 0], [C([-5, 6, -5], [10, 7, 10], body)]),
        B("abdomen", "body", [0, 10, 5], [C([-7, 6, 5], [14, 11, 15], dark, top=spider_mark)]),
        B("head", "body", [0, 10, -5], [
            C([-4, 6, -12], [8, 7, 7], body, face=human_face),
            C([-3, 4, -12], [2, 3, 2], red), C([1, 4, -12], [2, 3, 2], red),
        ]),
    ]
    for i, z in enumerate([-4, -1, 2, 5]):
        yaw = [-35, -12, 12, 35][i]
        bones.append(B(f"leg_r{i}", "body", [5, 10, z], [C([5, 9, z - 1], [10, 2, 2], body), C([13, 0, z - 1], [2, 9, 2], dark)], [0, -yaw, 0]))
        bones.append(B(f"leg_l{i}", "body", [-5, 10, z], [C([-15, 9, z - 1], [10, 2, 2], body), C([-15, 0, z - 1], [2, 9, 2], dark)], [0, yaw, 0]))
    return bones


def wolf_bones():
    fur, light, stripe = (140, 190, 215), (225, 240, 250), (40, 80, 150)
    return [
        B("root", None, [0, 0, 0]),
        B("body", "root", [0, 10, 0], [
            C([-4, 7, -7], [8, 7, 14], fur, top=stripes(stripe, 4)),
            C([-5, 7, -10], [10, 9, 5], light),
        ]),
        B("head", "body", [0, 13, -10], [
            C([-4, 10, -16], [8, 7, 6], light, face=beast_face((30, 220, 255), (30, 30, 40))),
            C([-2, 10, -19], [4, 3, 3], light, face=beast_face((0, 0, 0), (20, 20, 20))),
            C([-4, 17, -13], [2, 3, 1], fur), C([2, 17, -13], [2, 3, 1], fur),
        ]),
        B("tail", "body", [0, 13, 7], [C([-1, 5, 7], [2, 8, 2], light)], [40, 0, 0]),
        B("leg_fl", "body", [2.5, 7, -5], [C([1, 0, -6], [3, 7, 3], fur)]),
        B("leg_fr", "body", [-2.5, 7, -5], [C([-4, 0, -6], [3, 7, 3], fur)]),
        B("leg_bl", "body", [2.5, 7, 5], [C([1, 0, 3], [3, 7, 3], fur)]),
        B("leg_br", "body", [-2.5, 7, 5], [C([-4, 0, 3], [3, 7, 3], fur)]),
    ]


def bear_bones():
    fur, dark, gold = (55, 40, 30), (30, 22, 18), (240, 190, 50)
    return [
        B("root", None, [0, 0, 0]),
        B("body", "root", [0, 14, 0], [
            C([-8, 8, -10], [16, 14, 22], fur, top=stripes(gold, 7)),
            C([-7, 20, -8], [14, 4, 10], dark),
        ]),
        B("head", "body", [0, 18, -10], [
            C([-6, 12, -18], [12, 10, 9], fur, face=beast_face((255, 210, 40))),
            C([-3, 12, -22], [6, 5, 4], dark, face=beast_face((0, 0, 0), (10, 10, 10))),
            C([-6, 22, -14], [3, 3, 2], dark), C([3, 22, -14], [3, 3, 2], dark),
        ]),
        B("leg_fl", "body", [5, 10, -6], [C([2, 0, -9], [6, 10, 6], fur), C([2, 0, -11], [6, 2, 2], gold)]),
        B("leg_fr", "body", [-5, 10, -6], [C([-8, 0, -9], [6, 10, 6], fur), C([-8, 0, -11], [6, 2, 2], gold)]),
        B("leg_bl", "body", [5, 10, 8], [C([2, 0, 5], [6, 10, 6], fur)]),
        B("leg_br", "body", [-5, 10, 8], [C([-8, 0, 5], [6, 10, 6], fur)]),
    ]


def ape_bones():
    fur, skin, dark = (75, 50, 35), (190, 150, 115), (45, 30, 22)
    return [
        B("root", None, [0, 0, 0]),
        B("torso", "root", [0, 24, 0], [
            C([-12, 28, -7], [24, 20, 14], fur),
            C([-9, 22, -6], [18, 6, 12], skin),
            C([-8, 32, -8], [16, 12, 1], skin),
        ]),
        B("head", "torso", [0, 48, -2], [
            C([-6, 48, -9], [12, 11, 11], fur, face=beast_face((255, 40, 30))),
            C([-5, 46, -11], [10, 5, 4], skin, face=beast_face((30, 10, 10), (20, 10, 10))),
            C([-6, 57, -10], [12, 2, 2], dark),
        ]),
        B("arm_l", "torso", [14, 45, 0], [C([12, 26, -4], [8, 20, 8], fur), C([11, 16, -5], [10, 10, 10], skin)]),
        B("arm_r", "torso", [-14, 45, 0], [C([-20, 26, -4], [8, 20, 8], fur), C([-21, 16, -5], [10, 10, 10], skin)]),
        B("leg_l", "root", [6, 22, 0], [C([2, 0, -4], [9, 22, 8], fur)]),
        B("leg_r", "root", [-6, 22, 0], [C([-11, 0, -4], [9, 22, 8], fur)]),
    ]


# ───────────── Animation ─────────────

WALK = "query.modified_distance_moved"
SPD = "query.modified_move_speed"


def rot(x="0", y="0", z="0"):
    return {"rotation": [x, y, z]}


def kf(*frames):
    """frames: (time, [x,y,z])"""
    return {"rotation": {f"{t:.2f}": v for t, v in frames}}


def spider_anims():
    walk = {}
    for i in range(4):
        for side, s in (("r", 1), ("l", -1)):
            ph = (i * 90 + (0 if side == "r" else 180)) % 360
            walk[f"leg_{side}{i}"] = rot(
                "0",
                f"math.cos({WALK} * 60 + {ph}) * 22 * {SPD}",
                f"math.max(0, math.sin({WALK} * 60 + {ph})) * {-s * 25} * {SPD}",
            )
    walk["abdomen"] = rot(f"math.sin(query.anim_time * 90) * 3")
    legs_up = {f"leg_{s}{i}": kf((0, [0, 0, 0]), (0.25, [0, 0, (-30 if s == 'r' else 30)]), (0.6, [0, 0, 0])) for s in "rl" for i in range(4)}
    return {
        "walk": {"loop": True, "bones": walk},
        "attack": {"animation_length": 0.4, "bones": {"head": kf((0, [0, 0, 0]), (0.15, [25, 0, 0]), (0.4, [0, 0, 0])),
                                                      "leg_r0": kf((0, [0, 0, 0]), (0.15, [0, 0, 40]), (0.4, [0, 0, 0])),
                                                      "leg_l0": kf((0, [0, 0, 0]), (0.15, [0, 0, -40]), (0.4, [0, 0, 0]))}},
        "web": {"animation_length": 0.8, "bones": {"abdomen": kf((0, [0, 0, 0]), (0.3, [-55, 0, 0]), (0.5, [-50, 0, 0]), (0.8, [0, 0, 0])),
                                                   "body": kf((0, [0, 0, 0]), (0.3, [15, 0, 0]), (0.8, [0, 0, 0]))}},
        "spit": {"animation_length": 0.7, "bones": {"head": kf((0, [0, 0, 0]), (0.3, [-30, 0, 0]), (0.45, [25, 0, 0]), (0.7, [0, 0, 0]))}},
        "leap": {"animation_length": 0.6, "bones": legs_up},
    }


def quad_walk(amp, speed=38.17):
    return {
        "leg_fl": rot(f"math.cos({WALK} * {speed}) * {amp} * {SPD}"),
        "leg_br": rot(f"math.cos({WALK} * {speed}) * {amp} * {SPD}"),
        "leg_fr": rot(f"-math.cos({WALK} * {speed}) * {amp} * {SPD}"),
        "leg_bl": rot(f"-math.cos({WALK} * {speed}) * {amp} * {SPD}"),
    }


def wolf_anims():
    walk = quad_walk(50)
    walk["tail"] = rot("0", f"math.sin(query.anim_time * 300) * 15")
    return {
        "walk": {"loop": True, "bones": walk},
        "attack": {"animation_length": 0.4, "bones": {"head": kf((0, [0, 0, 0]), (0.15, [20, 0, 0]), (0.4, [0, 0, 0]))}},
        "howl": {"animation_length": 1.4, "bones": {"head": kf((0, [0, 0, 0]), (0.3, [-60, 0, 0]), (1.1, [-60, 0, 0]), (1.4, [0, 0, 0])),
                                                    "body": kf((0, [0, 0, 0]), (0.3, [-15, 0, 0]), (1.1, [-15, 0, 0]), (1.4, [0, 0, 0]))}},
        "blade": {"animation_length": 0.5, "bones": {"head": kf((0, [0, 0, 0]), (0.15, [-20, -30, 0]), (0.3, [15, 30, 0]), (0.5, [0, 0, 0])),
                                                     "leg_fl": kf((0, [0, 0, 0]), (0.2, [-70, 0, 0]), (0.5, [0, 0, 0]))}},
        "dash": {"animation_length": 0.5, "bones": {"leg_fl": kf((0, [0, 0, 0]), (0.25, [-60, 0, 0]), (0.5, [0, 0, 0])),
                                                    "leg_fr": kf((0, [0, 0, 0]), (0.25, [-60, 0, 0]), (0.5, [0, 0, 0])),
                                                    "leg_bl": kf((0, [0, 0, 0]), (0.25, [60, 0, 0]), (0.5, [0, 0, 0])),
                                                    "leg_br": kf((0, [0, 0, 0]), (0.25, [60, 0, 0]), (0.5, [0, 0, 0]))}},
    }


def bear_anims():
    rear = lambda t1, t2, end: {
        "body": kf((0, [0, 0, 0]), (t1, [-40, 0, 0]), (t2, [-40, 0, 0]), (end, [0, 0, 0])),
        "leg_bl": kf((0, [0, 0, 0]), (t1, [40, 0, 0]), (t2, [40, 0, 0]), (end, [0, 0, 0])),
        "leg_br": kf((0, [0, 0, 0]), (t1, [40, 0, 0]), (t2, [40, 0, 0]), (end, [0, 0, 0])),
    }
    claw = rear(0.2, 1.1, 1.3)
    claw["leg_fl"] = kf((0, [0, 0, 0]), (0.2, [-100, 0, 0]), (0.35, [-20, 0, 0]), (0.5, [-100, 0, 0]), (0.65, [-20, 0, 0]), (0.8, [-110, 0, 0]), (1.0, [10, 0, 0]), (1.3, [0, 0, 0]))
    claw["leg_fr"] = kf((0, [0, 0, 0]), (0.27, [-20, 0, 0]), (0.42, [-100, 0, 0]), (0.57, [-20, 0, 0]), (0.72, [-100, 0, 0]), (0.9, [10, 0, 0]), (1.3, [0, 0, 0]))
    roar = rear(0.3, 1.2, 1.5)
    roar["head"] = kf((0, [0, 0, 0]), (0.3, [-35, 0, 0]), (0.5, [-30, -10, 0]), (0.7, [-30, 10, 0]), (1.2, [-30, 0, 0]), (1.5, [0, 0, 0]))
    return {
        "walk": {"loop": True, "bones": quad_walk(35, 30)},
        "attack": {"animation_length": 0.5, "bones": {"leg_fl": kf((0, [0, 0, 0]), (0.2, [-90, 0, 0]), (0.5, [0, 0, 0])), "head": kf((0, [0, 0, 0]), (0.2, [15, 0, 0]), (0.5, [0, 0, 0]))}},
        "claw": {"animation_length": 1.3, "bones": claw},
        "roar": {"animation_length": 1.5, "bones": roar},
        "charge": {"animation_length": 0.9, "bones": {"head": kf((0, [0, 0, 0]), (0.2, [30, 0, 0]), (0.75, [30, 0, 0]), (0.9, [0, 0, 0])),
                                                      "body": kf((0, [0, 0, 0]), (0.2, [10, 0, 0]), (0.75, [10, 0, 0]), (0.9, [0, 0, 0]))}},
    }


def ape_anims():
    walk = {
        "leg_l": rot(f"math.cos({WALK} * 25) * 30 * {SPD}"),
        "leg_r": rot(f"-math.cos({WALK} * 25) * 30 * {SPD}"),
        "arm_l": rot(f"-math.cos({WALK} * 25) * 25 * {SPD}"),
        "arm_r": rot(f"math.cos({WALK} * 25) * 25 * {SPD}"),
        "torso": rot(f"5 + math.sin(query.anim_time * 80) * 2", f"math.cos({WALK} * 25) * 6 * {SPD}"),
    }
    both = lambda frames: {"arm_l": kf(*frames), "arm_r": kf(*frames)}
    slam = both([(0, [0, 0, 0]), (0.5, [-175, 0, 0]), (0.9, [-175, 0, 0]), (1.1, [-30, 0, 0]), (1.5, [0, 0, 0])])
    slam["torso"] = kf((0, [0, 0, 0]), (0.5, [-15, 0, 0]), (0.9, [-15, 0, 0]), (1.1, [35, 0, 0]), (1.5, [0, 0, 0]))
    roar = {
        "arm_l": kf((0, [0, 0, 0]), (0.2, [-90, 0, 40]), (0.35, [-80, 0, 10]), (0.5, [-90, 0, 40]), (0.65, [-80, 0, 10]), (0.8, [-90, 0, 40]), (1.2, [0, 0, 0])),
        "arm_r": kf((0, [0, 0, 0]), (0.27, [-80, 0, -10]), (0.42, [-90, 0, -40]), (0.57, [-80, 0, -10]), (0.72, [-90, 0, -40]), (1.2, [0, 0, 0])),
        "head": kf((0, [0, 0, 0]), (0.2, [-30, 0, 0]), (1.0, [-30, 0, 0]), (1.2, [0, 0, 0])),
        "torso": kf((0, [0, 0, 0]), (0.2, [-12, 0, 0]), (1.0, [-12, 0, 0]), (1.2, [0, 0, 0])),
    }
    return {
        "walk": {"loop": True, "bones": walk},
        "attack": {"animation_length": 0.6, "bones": {"arm_r": kf((0, [0, 0, 0]), (0.2, [-60, 0, -20]), (0.35, [-100, 0, 0]), (0.6, [0, 0, 0])),
                                                      "torso": kf((0, [0, 0, 0]), (0.35, [10, -20, 0]), (0.6, [0, 0, 0]))}},
        "slam": {"animation_length": 1.5, "bones": slam},
        "throw": {"animation_length": 1.1, "bones": {"arm_r": kf((0, [0, 0, 0]), (0.5, [-160, 0, -20]), (0.7, [-170, 0, -20]), (0.85, [-40, 0, 0]), (1.1, [0, 0, 0])),
                                                     "torso": kf((0, [0, 0, 0]), (0.5, [-10, 25, 0]), (0.85, [15, -20, 0]), (1.1, [0, 0, 0]))}},
        "roar": {"animation_length": 1.2, "bones": roar},
        "punch": {"animation_length": 0.8, "bones": {"arm_l": kf((0, [0, 0, 0]), (0.15, [-90, 0, 0]), (0.3, [0, 0, 0])),
                                                     "arm_r": kf((0, [0, 0, 0]), (0.35, [0, 0, 0]), (0.5, [-90, 0, 0]), (0.8, [0, 0, 0])),
                                                     "torso": kf((0, [0, 0, 0]), (0.15, [0, -15, 0]), (0.5, [0, 15, 0]), (0.8, [0, 0, 0]))}},
    }


# ───────────── Định nghĩa loài ─────────────

SPECIES = {
    "demon_spider": {
        "name": "Nhân Diện Ma Chu", "bones": spider_bones, "anims": spider_anims, "tex_w": 128,
        "health": 30, "damage": 4, "speed": 0.3, "box": [1.6, 1.0], "bounds": [4, 2],
        "egg": ["#2d1937", "#c8142a"], "climb": True,
        "spawn": {"tags": ["forest", "jungle", "swamp"], "bright": [0, 7], "weight": 18, "herd": [1, 1]},
    },
    "wind_wolf": {
        "name": "Phong Lang", "bones": wolf_bones, "anims": wolf_anims, "tex_w": 64,
        "health": 22, "damage": 4, "speed": 0.34, "box": [0.8, 1.0], "bounds": [2, 2],
        "egg": ["#8cbed7", "#285096"], "pack": True,
        "spawn": {"tags": ["taiga", "plains", "forest", "extreme_hills"], "bright": [0, 15], "weight": 8, "herd": [2, 4]},
    },
    "gold_claw_bear": {
        "name": "Ám Kim Khủng Trảo Hùng", "bones": bear_bones, "anims": bear_anims, "tex_w": 128,
        "health": 60, "damage": 7, "speed": 0.27, "box": [1.6, 1.6], "bounds": [4, 3],
        "egg": ["#37281e", "#f0be32"], "kb_res": 0.6,
        "spawn": {"tags": ["forest", "taiga", "extreme_hills"], "bright": [0, 15], "weight": 5, "herd": [1, 1]},
    },
    "titan_ape": {
        "name": "Thái Thản Cự Viên", "bones": ape_bones, "anims": ape_anims, "tex_w": 128,
        "health": 160, "damage": 12, "speed": 0.26, "box": [1.8, 3.6], "bounds": [5, 5],
        "egg": ["#4b3223", "#ff2a1e"], "kb_res": 1.0, "boss": True,
        "spawn": {"tags": ["jungle"], "bright": [0, 15], "weight": 2, "herd": [1, 1], "density": 1},
    },
}


def bp_entity(sid, s):
    ident = f"dld:{sid}"
    comps = {
        "minecraft:type_family": {"family": ["dld_beast", "dld_custom", sid, "monster", "mob"]},
        "minecraft:health": {"value": s["health"], "max": s["health"]},
        "minecraft:attack": {"damage": s["damage"]},
        "minecraft:movement": {"value": s["speed"]},
        "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": True, "avoid_damage_blocks": True, "can_walk": True},
        "minecraft:movement.basic": {},
        "minecraft:jump.static": {},
        "minecraft:physics": {},
        "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
        "minecraft:collision_box": {"width": s["box"][0], "height": s["box"][1]},
        "minecraft:nameable": {},
        "minecraft:follow_range": {"value": 40, "max": 48},
        "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
        "minecraft:experience_reward": {"on_death": "query.last_hit_by_player ? 10 + query.random_integer(0, 10) : 0"},
        "minecraft:damage_sensor": {"triggers": [{"cause": "fall", "deals_damage": "no"}]},
        "minecraft:hurt_on_condition": {"damage_conditions": [{"filters": {"test": "in_lava", "subject": "self"}, "cause": "lava", "damage_per_tick": 4}]},
        "minecraft:conditional_bandwidth_optimization": {},
        "minecraft:behavior.float": {"priority": 0},
        "minecraft:behavior.melee_attack": {"priority": 3, "speed_multiplier": 1.25, "track_target": True, "require_complete_path": False},
        "minecraft:behavior.nearest_attackable_target": {
            "priority": 2, "must_see": False, "reselect_targets": True, "within_radius": 32,
            "entity_types": [
                {"filters": {"test": "is_family", "subject": "other", "value": "player"}, "max_dist": 32},
                {"filters": {"test": "is_family", "subject": "other", "value": "irongolem"}, "max_dist": 20},
            ],
        },
        "minecraft:behavior.hurt_by_target": {"priority": 1, "alert_same_type": bool(s.get("pack"))},
        "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 0.9},
        "minecraft:behavior.look_at_player": {"priority": 7, "look_distance": 12, "probability": 0.05},
        "minecraft:behavior.random_look_around": {"priority": 8},
    }
    if s.get("climb"):
        comps["minecraft:can_climb"] = {}
    if s.get("kb_res"):
        comps["minecraft:knockback_resistance"] = {"value": s["kb_res"]}
    if s.get("boss"):
        comps["minecraft:boss"] = {"hud_range": 48, "name": s["name"], "should_darken_sky": False}
    else:
        comps["minecraft:despawn"] = {"despawn_from_distance": {"min_distance": 48, "max_distance": 96}}

    groups, events = {}, {}
    for t in range(5):
        hp = round(s["health"] * TIER_HEALTH[t])
        groups[f"dld:tier_{t}"] = {
            "minecraft:health": {"value": hp, "max": hp},
            "minecraft:attack": {"damage": round(s["damage"] * TIER_DAMAGE[t])},
            "minecraft:scale": {"value": TIER_SCALE[t]},
        }
        events[f"dld:set_tier_{t}"] = {
            "add": {"component_groups": [f"dld:tier_{t}"]},
            "remove": {"component_groups": [f"dld:tier_{o}" for o in range(5) if o != t]},
        }
    return {
        "format_version": "1.21.40",
        "minecraft:entity": {
            "description": {"identifier": ident, "is_spawnable": True, "is_summonable": True, "is_experimental": False},
            "component_groups": groups,
            "components": comps,
            "events": events,
        },
    }


def spawn_rule(sid, s):
    sp = s["spawn"]
    cond = {
        "minecraft:spawns_on_surface": {},
        "minecraft:brightness_filter": {"min": sp["bright"][0], "max": sp["bright"][1], "adjust_for_weather": True},
        "minecraft:difficulty_filter": {"min": "easy", "max": "hard"},
        "minecraft:weight": {"default": sp["weight"]},
        "minecraft:herd": {"min_size": sp["herd"][0], "max_size": sp["herd"][1]},
        "minecraft:biome_filter": {"any_of": [{"test": "has_biome_tag", "operator": "==", "value": t} for t in sp["tags"]]},
    }
    if sp.get("density"):
        cond["minecraft:density_limit"] = {"surface": sp["density"]}
    return {
        "format_version": "1.8.0",
        "minecraft:spawn_rules": {"description": {"identifier": f"dld:{sid}", "population_control": "monster"}, "conditions": [cond]},
    }


def client_entity(sid, s, anim_names):
    anims = {"look": "animation.dld.common.look_at_target"}
    anims.update({a: f"animation.dld.{sid}.{a}" for a in anim_names})
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"dld:{sid}",
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": f"textures/entity/dld/{sid}"},
                "geometry": {"default": f"geometry.dld.{sid}"},
                "animations": anims,
                "scripts": {"animate": ["look", "walk"]},
                "render_controllers": ["controller.render.default"],
                "spawn_egg": {"base_color": s["egg"][0], "overlay_color": s["egg"][1]},
            }
        },
    }


def main():
    lang = []
    common = {
        "format_version": "1.8.0",
        "animations": {"animation.dld.common.look_at_target": {"loop": True, "bones": {"head": {"rotation": ["query.target_x_rotation", "query.target_y_rotation", 0]}}}},
    }
    os.makedirs(os.path.join(RP, "animations"), exist_ok=True)
    for d in ("models/entity", "entity", "textures/entity/dld"):
        os.makedirs(os.path.join(RP, d), exist_ok=True)
    for d in ("entities", "spawn_rules"):
        os.makedirs(os.path.join(BP, d), exist_ok=True)
    with open(os.path.join(RP, "animations", "dld_common.animation.json"), "w") as f:
        json.dump(common, f, indent=1)

    for sid, s in SPECIES.items():
        bones = s["bones"]()
        h = layout(bones, s["tex_w"])
        write_png(os.path.join(RP, "textures", "entity", "dld", f"{sid}.png"), paint(bones, s["tex_w"], h))
        with open(os.path.join(RP, "models", "entity", f"{sid}.geo.json"), "w") as f:
            json.dump(geometry(sid, bones, s["tex_w"], h, s["bounds"]), f, indent=1)
        anims = s["anims"]()
        with open(os.path.join(RP, "animations", f"{sid}.animation.json"), "w") as f:
            json.dump({"format_version": "1.8.0", "animations": {f"animation.dld.{sid}.{k}": v for k, v in anims.items()}}, f, indent=1)
        with open(os.path.join(RP, "entity", f"{sid}.entity.json"), "w") as f:
            json.dump(client_entity(sid, s, anims.keys()), f, indent=1)
        with open(os.path.join(BP, "entities", f"{sid}.json"), "w") as f:
            json.dump(bp_entity(sid, s), f, indent=1)
        with open(os.path.join(BP, "spawn_rules", f"{sid}.json"), "w") as f:
            json.dump(spawn_rule(sid, s), f, indent=1)
        lang += [f"entity.dld:{sid}.name={s['name']}", f"item.spawn_egg.entity.dld:{sid}.name=Trứng {s['name']}"]

    for name in ("en_US", "en_GB"):
        path = os.path.join(RP, "texts", f"{name}.lang")
        with open(path, encoding="utf-8") as f:
            base = [l for l in f.read().splitlines() if l and not l.startswith(("entity.dld:", "item.spawn_egg.entity.dld:"))]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(base + lang) + "\n")


if __name__ == "__main__":
    main()
