"""Tiny orthographic renderer: front view of a Bedrock/GeckoLib model, used as
the alien icon in the Omnitrix menus."""
from PIL import Image

SIZE = 64


def _north_uv(cube, tw, th):
    """Pixel rectangle (u, v, w, h) of the front (north) face of a cube."""
    uv = cube.get("uv", [0, 0])
    sx, sy, sz = cube["size"]
    if isinstance(uv, dict):
        face = uv.get("north")
        if not face:
            return None
        u, v = face["uv"]
        w, h = face.get("uv_size", [sx, sy])
        return u, v, w, h
    u, v = uv
    return u + sz, v + sz, sx, sy


def render_icon(geo_json, texture):
    geo = geo_json["minecraft:geometry"][0]
    desc = geo["description"]
    tw, th = desc.get("texture_width", 64), desc.get("texture_height", 64)
    sx, sy = texture.size[0] / tw, texture.size[1] / th
    quads = []
    for bone in geo.get("bones", []):
        for cube in bone.get("cubes", []):
            if "size" not in cube or "origin" not in cube:
                continue
            rect = _north_uv(cube, tw, th)
            if not rect:
                continue
            ox, oy, oz = cube["origin"]
            w, h, _ = cube["size"]
            if w <= 0 or h <= 0:
                continue
            quads.append((oz, ox, oy, w, h, rect, cube.get("mirror", bone.get("mirror", False))))
    if not quads:
        return Image.new("RGBA", (SIZE, SIZE))
    minx = min(q[1] for q in quads)
    maxx = max(q[1] + q[3] for q in quads)
    miny = min(q[2] for q in quads)
    maxy = max(q[2] + q[4] for q in quads)
    span = max(maxx - minx, maxy - miny, 1)
    k = (SIZE - 4) / span
    canvas = Image.new("RGBA", (SIZE, SIZE))
    # Back to front: the front of the model is at the lowest z.
    for oz, ox, oy, w, h, (u, v, uw, vh), mirror in sorted(quads, key=lambda q: -q[0]):
        if uw == 0 or vh == 0:
            continue
        box = (round(min(u, u + uw) * sx), round(min(v, v + vh) * sy),
               round(max(u, u + uw) * sx), round(max(v, v + vh) * sy))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        face = texture.crop(box)
        if uw < 0:
            face = face.transpose(Image.FLIP_LEFT_RIGHT)
        if vh < 0:
            face = face.transpose(Image.FLIP_TOP_BOTTOM)
        # Model x grows to the model's left, i.e. to the right of a front view.
        if not mirror:
            face = face.transpose(Image.FLIP_LEFT_RIGHT)
        pw, ph = max(1, round(w * k)), max(1, round(h * k))
        face = face.resize((pw, ph), Image.NEAREST)
        px = round((maxx - (ox + w)) * k) + (SIZE - round((maxx - minx) * k)) // 2
        py = round((maxy - (oy + h)) * k) + (SIZE - round((maxy - miny) * k)) // 2
        canvas.alpha_composite(face, (max(0, min(SIZE - 1, px)), max(0, min(SIZE - 1, py))))
    return canvas
