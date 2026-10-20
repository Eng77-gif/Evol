"""Offline renderer for Bedrock geometry (+ an optional animation pose).

Used to inspect the converted alien models without the game:
    python3 tools/render.py <attachable.json> out.png [--time T] [--rest]

Follows the Blockbench conventions for Bedrock models: model x is mirrored,
bone and cube rotations are applied as [-x, -y, z] in Z*Y*X order around
their pivots.
"""
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "packs", "AlienEvo_RP")


def rot_matrix(rx, ry, rz):
    rx, ry, rz = (math.radians(a) for a in (rx, ry, rz))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def affine(m3=None, t=(0, 0, 0)):
    m = np.eye(4)
    if m3 is not None:
        m[:3, :3] = m3
    m[:3, 3] = t
    return m


def around(pivot, m3):
    p = np.array(pivot, dtype=float)
    return affine(t=p) @ affine(m3) @ affine(t=-p)


# ---------------------------------------------------------------- molang

def molang(expr, t):
    if isinstance(expr, (int, float)):
        return float(expr)
    e = str(expr).lower()
    e = e.replace("query.anim_time", "q.anim_time").replace("q.anim_time", f"({t})")
    e = re.sub(r"q\.life_time", f"({t})", e)
    e = re.sub(r"(v|variable|q|query|c|context)\.[a-z_0-9.>-]+", "0", e)
    e = e.replace("math.", "")
    env = {"sin": lambda d: math.sin(math.radians(d)), "cos": lambda d: math.cos(math.radians(d)),
           "abs": abs, "clamp": lambda v, a, b: max(a, min(b, v)), "pow": pow, "sqrt": math.sqrt,
           "pi": math.pi, "floor": math.floor, "ceil": math.ceil, "round": round, "mod": math.fmod,
           "lerp": lambda a, b, k: a + (b - a) * k, "min": min, "max": max, "random": lambda a, b: (a + b) / 2}
    try:
        return float(eval(e.rstrip(";"), {"__builtins__": {}}, env))  # noqa: S307 - local tool
    except Exception:  # noqa: BLE001
        return 0.0


def vec(v, t, default):
    if isinstance(v, dict):
        v = v.get("post", v.get("pre", default))
    if isinstance(v, (int, float, str)):
        v = [v, v, v]
    return [molang(x, t) for x in v]


def sample(channel, t, default):
    if not isinstance(channel, dict) or "post" in channel or "pre" in channel:
        return vec(channel, t, default)
    keys = sorted((float(k), v) for k, v in channel.items())
    if not keys:
        return default
    if t <= keys[0][0]:
        return vec(keys[0][1], t, default)
    if t >= keys[-1][0]:
        return vec(keys[-1][1], t, default)
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            a, b = vec(v0, t, default), vec(v1, t, default)
            k = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return [x + (y - x) * k for x, y in zip(a, b)]
    return default


def pose_from(animations, t):
    """{bone: (rot, pos, scale)} summed over animations like Bedrock does."""
    pose = {}
    for anim in animations:
        length = anim.get("animation_length")
        tt = t
        if anim.get("loop") is True and length:
            tt = t % length
        elif length:
            tt = min(t, length)
        for bone, chans in (anim.get("bones") or {}).items():
            r, p, s = pose.get(bone, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))
            if "rotation" in chans:
                r = [a + b for a, b in zip(r, sample(chans["rotation"], tt, [0, 0, 0]))]
            if "position" in chans:
                p = [a + b for a, b in zip(p, sample(chans["position"], tt, [0, 0, 0]))]
            if "scale" in chans:
                s = [a * b for a, b in zip(s, sample(chans["scale"], tt, [1, 1, 1]))]
            pose[bone] = (r, p, s)
    return pose


# ---------------------------------------------------------------- geometry

FACES = {
    # name: corner indices (x, y, z bits) in drawing order
    "north": [(1, 1, 0), (0, 1, 0), (0, 0, 0), (1, 0, 0)],
    "south": [(0, 1, 1), (1, 1, 1), (1, 0, 1), (0, 0, 1)],
    "east": [(0, 1, 0), (0, 1, 1), (0, 0, 1), (0, 0, 0)],
    "west": [(1, 1, 1), (1, 1, 0), (1, 0, 0), (1, 0, 1)],
    "up": [(1, 1, 1), (0, 1, 1), (0, 1, 0), (1, 1, 0)],
    "down": [(1, 0, 0), (0, 0, 0), (0, 0, 1), (1, 0, 1)],
}


def box_uv(uv, size, mirror):
    u, v = uv
    w, h, d = (math.floor(x) for x in size)
    faces = {
        "east": (u, v + d, d, h), "north": (u + d, v + d, w, h),
        "west": (u + d + w, v + d, d, h), "south": (u + d + w + d, v + d, w, h),
        "up": (u + d, v, w, d), "down": (u + d + w, v + d, w, -d),
    }
    if mirror:
        faces["east"], faces["west"] = faces["west"], faces["east"]
        faces = {k: (a + c, b, -c, e) for k, (a, b, c, e) in faces.items()}
    return faces


def quads(geo, pose):
    """World-space textured quads of a geometry."""
    bones = {b["name"]: b for b in geo.get("bones", [])}
    cache = {}

    def bone_matrix(name):
        if name in cache:
            return cache[name]
        b = bones[name]
        r = list(b.get("rotation", [0, 0, 0]))
        pr, pp, ps = pose.get(name, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))
        r = [a + c for a, c in zip(r, pr)]
        pivot = b.get("pivot", [0, 0, 0])
        local = affine(t=(-pp[0], pp[1], pp[2])) @ around(pivot, np.diag(ps)) @ around(pivot, rot_matrix(-r[0], -r[1], r[2]))
        m = bone_matrix(b["parent"]) @ local if b.get("parent") in bones else local
        cache[name] = m
        return m

    out = []
    for name, b in bones.items():
        m = bone_matrix(name)
        for c in b.get("cubes", []):
            o, s = c["origin"], c["size"]
            inf = c.get("inflate", 0)
            lo = np.array(o, float) - inf
            hi = np.array(o, float) + np.array(s, float) + inf
            cm = m
            if "rotation" in c:
                cr = c["rotation"]
                cm = m @ around(c.get("pivot", [0, 0, 0]), rot_matrix(-cr[0], -cr[1], cr[2]))
            uv = c.get("uv", [0, 0])
            faces = uv if isinstance(uv, dict) else box_uv(uv, s, c.get("mirror", b.get("mirror", False)))
            for face, corners in FACES.items():
                f = faces.get(face)
                if f is None:
                    continue
                if isinstance(f, dict):
                    u, v = f.get("uv", [0, 0])
                    uw, vh = f.get("uv_size", [0, 0])
                    rect = (u, v, uw, vh)
                else:
                    rect = f
                pts = []
                for bx, by, bz in corners:
                    p = np.array([hi[0] if bx else lo[0], hi[1] if by else lo[1], hi[2] if bz else lo[2], 1.0])
                    pts.append((cm @ p)[:3])
                out.append((pts, rect))
    return out


def render(parts, size=256, view="front", pose=None, bg=(0, 0, 0, 0)):
    """parts: [(geo_json, texture Image)]. Returns an RGBA image."""
    pose = pose or {}
    items = []
    for geo_json, tex in parts:
        geo = geo_json["minecraft:geometry"][0]
        d = geo["description"]
        tw, th = d.get("texture_width", 64), d.get("texture_height", 64)
        for pts, rect in quads(geo, pose):
            items.append((pts, rect, tex, tw, th))
    if not items:
        return Image.new("RGBA", (size, size), bg)
    ang = {"front": 0, "side": 90, "back": 180, "three_quarter": 35}[view]
    ry = rot_matrix(0, ang, 0)
    # Model x is mirrored in Bedrock; the model faces -z.  Camera looks at -z face.
    allp = np.array([ry @ p for it in items for p in it[0]])
    sx = -allp[:, 0]
    sy = allp[:, 1]
    minx, maxx, miny, maxy = sx.min(), sx.max(), sy.min(), sy.max()
    span = max(maxx - minx, maxy - miny, 1e-3)
    k = (size - 8) / span
    ox = (size - (maxx - minx) * k) / 2
    oy = (size - (maxy - miny) * k) / 2
    color = np.zeros((size, size, 4), np.float32)
    color[..., :] = bg
    depth = np.full((size, size), np.inf, np.float32)
    texcache = {}
    for pts, (u, v, uw, vh), tex, tw, th in items:
        if uw == 0 or vh == 0:
            continue
        key = id(tex)
        if key not in texcache:
            texcache[key] = (np.asarray(tex.convert("RGBA"), np.float32), tex.size)
        tarr, (TW, TH) = texcache[key]
        P = np.array([ry @ p for p in pts])
        X = (-P[:, 0] - minx) * k + ox
        Y = size - ((P[:, 1] - miny) * k + oy)
        Z = P[:, 2]
        uvs = [(u + uw, v), (u, v), (u, v + vh), (u + uw, v + vh)]
        for tri in ((0, 1, 2), (0, 2, 3)):
            raster(color, depth, X[list(tri)], Y[list(tri)], Z[list(tri)],
                   [uvs[i] for i in tri], tarr, TW / tw, TH / th)
    img = Image.fromarray(np.clip(color, 0, 255).astype(np.uint8), "RGBA")
    return img


def raster(color, depth, X, Y, Z, uvs, tarr, su, sv):
    size = color.shape[0]
    x0, x1 = int(max(0, math.floor(X.min()))), int(min(size - 1, math.ceil(X.max())))
    y0, y1 = int(max(0, math.floor(Y.min()))), int(min(size - 1, math.ceil(Y.max())))
    if x1 < x0 or y1 < y0:
        return
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    (ax, bx, cx), (ay, by, cy) = X, Y
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-9:
        return
    w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
    w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
    w2 = 1 - w0 - w1
    inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not inside.any():
        return
    z = w0 * Z[0] + w1 * Z[1] + w2 * Z[2]
    u = w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]
    v = w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]
    ti = np.clip((u * su).astype(int), 0, tarr.shape[1] - 1)
    tj = np.clip((v * sv).astype(int), 0, tarr.shape[0] - 1)
    texel = tarr[tj, ti]
    reg_depth = depth[y0:y1 + 1, x0:x1 + 1]
    ok = inside & (texel[..., 3] > 16) & (z < reg_depth)
    reg_color = color[y0:y1 + 1, x0:x1 + 1]
    reg_color[ok] = texel[ok]
    reg_depth[ok] = z[ok]


# ---------------------------------------------------------------- attachables

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def attachable_parts(path, include_glow=True):
    desc = load_json(path)["minecraft:attachable"]["description"]
    geos = {}
    for f in [os.path.join(dp, n) for dp, _, ns in os.walk(os.path.join(RP, "models")) for n in ns]:
        for g in load_json(f).get("minecraft:geometry", []):
            geos[g["description"]["identifier"]] = {"minecraft:geometry": [g]}
    rcs = {}
    for f in os.listdir(os.path.join(RP, "render_controllers")):
        rcs.update(load_json(os.path.join(RP, "render_controllers", f))["render_controllers"])
    parts = []
    for rc in desc["render_controllers"]:
        name = rc if isinstance(rc, str) else next(iter(rc))
        r = rcs[name]
        if not include_glow and name.endswith("_glow"):
            continue
        g = desc["geometry"][r["geometry"].split(".", 1)[1]]
        t = desc["textures"][r["textures"][0].split(".", 1)[1]]
        parts.append((geos[g], Image.open(os.path.join(RP, t + ".png")).convert("RGBA")))
    return desc, parts


def attachable_pose(desc, t=0.0, rest=True):
    anims = {}
    for dp, _, ns in os.walk(os.path.join(RP, "animations")):
        for n in ns:
            anims.update(load_json(os.path.join(dp, n)).get("animations", {}))
    ctrls = {}
    for dp, _, ns in os.walk(os.path.join(RP, "animation_controllers")):
        for n in ns:
            ctrls.update(load_json(os.path.join(dp, n)).get("animation_controllers", {}))
    playing = []
    amap = desc.get("animations", {})
    for short in desc.get("scripts", {}).get("animate", []):
        short = short if isinstance(short, str) else next(iter(short))
        full = amap.get(short)
        if full in anims:
            playing.append(anims[full])
        elif full in ctrls and rest:
            st = ctrls[full]["states"].get(ctrls[full].get("initial_state", "default"), {})
            for a in st.get("animations", []):
                a = a if isinstance(a, str) else next(iter(a))
                if amap.get(a) in anims:
                    playing.append(anims[amap[a]])
    return pose_from(playing, t)


def main():
    path, out = sys.argv[1], sys.argv[2]
    t = float(sys.argv[sys.argv.index("--time") + 1]) if "--time" in sys.argv else 0.0
    desc, parts = attachable_parts(path)
    pose = attachable_pose(desc, t)
    views = [render(parts, 256, v, pose) for v in ("front", "three_quarter", "side", "back")]
    sheet = Image.new("RGBA", (256 * 4, 256), (50, 50, 50, 255))
    for i, v in enumerate(views):
        sheet.alpha_composite(v, (i * 256, 0))
    sheet.save(out)


if __name__ == "__main__":
    main()
