"""Convert the Java structures of AlienEvo and its add-ons to Bedrock.

* Java structure templates (.nbt) become Bedrock .mcstructure files.
* Jigsaw structures (crash site, machine stronghold) are assembled offline by
  connecting the jigsaw blocks of their pieces.
* Java block states are mapped with minecraft-data's blocksJ2B table
  (tools/data/blocks_j2b.json holds the states used here).
* Chests/barrels/suspicious blocks keep their loot tables; the add-on loot
  tables are converted to Bedrock loot tables.
* A feature + feature rule per structure places it during world generation.
"""
import glob
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbt import (BYTE, COMPOUND, INT, LIST, STRING, Byte, Compound, Int, List, String, read_java,  # noqa: E402
                 write_bedrock)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "packs", "AlienEvo_BP")
MAPPING_SUBSET = os.path.join(ROOT, "tools", "data", "blocks_j2b.json")
BLOCK_VERSION = 18168832  # 1.21.60 block palette version; newer games upgrade it

# Java 1.20.1 names renamed later in Java (the table uses current names).
JAVA_RENAMES = {"minecraft:grass": "minecraft:short_grass", "minecraft:chain": "minecraft:iron_chain"}

# Blocks of other mods.
MOD_BLOCKS = {
    "alienevo:galvan_pod": ("alienevo:galvan_pod", "facing"),
    "alienevo:omnitrix_workbench": ("alienevo:omnitrix_workbench", "facing"),
    "alienevo:machined_metal": ("alienevo:machined_metal", None),
    "alienevo:machined_panel": ("alienevo:machined_panel", None),
    "afomni:blue_ice": ("minecraft:blue_ice", None),
    "omni_extras:opticoid_slime": ("minecraft:slime", None),
    "palladium:titanium_ore": ("minecraft:iron_ore", None),
    "palladium:titanium_block": ("minecraft:iron_block", None),
    "palladium:lead_ore": ("minecraft:iron_ore", None),
    "palladium:lead_block": ("minecraft:iron_block", None),
    "palladium:raw_lead_block": ("minecraft:raw_iron_block", None),
    "palladium:redstone_flux_crystal_cluster": ("minecraft:amethyst_cluster", None),
    "palladium:deepslate_redstone_flux_crystal_geode": ("minecraft:budding_amethyst", None),
}

# Java loot table -> Bedrock loot table path.
VANILLA_LOOT = {
    "minecraft:chests/village/village_plains_house": "loot_tables/chests/village/village_plains_house.json",
    "minecraft:chests/village/village_toolsmith": "loot_tables/chests/village/village_toolsmith.json",
    "minecraft:chests/village/village_cartographer": "loot_tables/chests/village/village_cartographer.json",
    "minecraft:chests/village/village_temple": "loot_tables/chests/village/village_temple.json",
    "minecraft:chests/stronghold_library": "loot_tables/chests/stronghold_library.json",
    "minecraft:chests/simple_dungeon": "loot_tables/chests/simple_dungeon.json",
    "minecraft:chests/woodland_mansion": "loot_tables/chests/woodland_mansion.json",
    "minecraft:chests/end_city_treasure": "loot_tables/chests/end_city_treasure.json",
}

BLOCK_ENTITY_IDS = {
    "minecraft:chest": "Chest", "minecraft:trapped_chest": "Chest", "minecraft:barrel": "Barrel",
    "minecraft:brushable_block": "BrushableBlock", "minecraft:mob_spawner": "MobSpawner",
}

DYES = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray", "cyan",
        "purple", "blue", "brown", "green", "red", "black"]


# ------------------------------------------------------------------ structures

S = "data/{ns}/structures/{path}.nbt"

STRUCTURES = [
    # name, start piece, pool pieces (jigsaw), placement
    dict(name="pod", piece="alienevo:pod", place="surface", y=-4, spacing=32, biomes=["plains", "forest", "taiga", "savanna", "jungle", "birch"]),
    dict(name="galvan_mine", piece="alienevo:galvan_mine", place="surface", y=-10, spacing=32, biomes=["plains", "desert", "savanna", "taiga", "mesa"]),
    dict(name="galvan_priory", piece="alienevo:galvan_priory", place="surface", y=0, spacing=32, biomes=["plains", "desert", "savanna", "taiga"]),
    dict(name="machine_tower", piece="alienevo:machine_tower", place="surface", y=0, spacing=40, biomes=["plains", "forest", "taiga", "mountains", "birch"]),
    dict(name="machine_well", piece="alienevo:machine_well", place="surface", y=-4, spacing=60, biomes=["plains", "forest", "taiga", "mountains", "birch"]),
    dict(name="machine_blast_chamber", piece="alienevo:machine_blast_chamber", place="underground", y=(-40, 10), spacing=60, biomes=["overworld"]),
    dict(name="machine_stronghold", piece="alienevo:machine_stronghold_ne",
         pool=["alienevo:machine_stronghold_nw", "alienevo:machine_stronghold_sw", "alienevo:machine_stronghold_se"],
         place="underground", y=(-45, -10), spacing=120, biomes=["overworld"]),
    # The Omnitrix core lies in the crashed ship (obtain_core power in Java):
    # one chest of the ship always holds it.
    dict(name="crash_site", piece="alienevo:ship2", pool=["alienevo:ship1", "alienevo:ship3", "alienevo:ship4"],
         core_chest=True, place="surface", y=-3, spacing=64, biomes=["plains", "forest", "taiga", "savanna", "desert", "mesa", "birch"]),
    # Add-ons
    dict(name="loboan_skull", piece="anur:loboan/loboan_skull", place="surface", y=0, spacing=60, biomes=["taiga"]),
    dict(name="talpaedan_crash_site", piece="omni_extras:talpaedan_crash_site", place="surface", y=0, spacing=60, biomes=["desert"]),
    dict(name="ruined_galvan_tower", piece="omni_extras:ruined_galvan_tower", place="surface", y=0, spacing=42, biomes=["plains", "taiga"]),
    dict(name="abandoned_lab", piece="omni_extras:abandoned_lab", place="underground", y=(-30, 20), spacing=42, biomes=["plains", "taiga", "forest", "jungle"]),
    dict(name="alien_prison", piece="untapped:alien_prison", place="surface", y=-22, spacing=42, biomes=["mesa"]),
    dict(name="xylene_crashsite", piece="omni_extras:xylene_crashsite", place="surface", y=-5, spacing=50, biomes=["frozen"]),
]

UNDERGROUND_ALLOW = ["minecraft:stone", "minecraft:deepslate", "minecraft:tuff", "minecraft:granite", "minecraft:diorite",
                     "minecraft:andesite", "minecraft:dirt", "minecraft:gravel", "minecraft:air", "minecraft:water",
                     "minecraft:lava", "minecraft:coal_ore", "minecraft:iron_ore", "minecraft:copper_ore",
                     "minecraft:deepslate_iron_ore", "minecraft:deepslate_coal_ore", "minecraft:clay"]


def piece_path(ref):
    ns, path = ref.split(":", 1)
    return S.format(ns=ns, path=path)


# ------------------------------------------------------------------ block states

def java_key(name, props):
    name = JAVA_RENAMES.get(name, name)
    if not props:
        return f"{name}[]"
    return f"{name}[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]"


def parse_state(s):
    m = re.match(r"([^\[]+)\[(.*)\]$", s)
    name, body = (m.group(1), m.group(2)) if m else (s, "")
    states = {}
    for part in filter(None, body.split(",")):
        k, v = part.split("=", 1)
        states[k] = v
    return name, states


class Mapper:
    def __init__(self, full_table=None):
        self.table = {}
        if full_table and os.path.exists(full_table):
            with open(full_table, encoding="utf-8") as f:
                self.table = json.load(f)
        elif os.path.exists(MAPPING_SUBSET):
            with open(MAPPING_SUBSET, encoding="utf-8") as f:
                self.table = json.load(f)
        self.used = {}
        self.missing = set()
        self.by_name = {}
        for k in self.table:
            self.by_name.setdefault(k.split("[", 1)[0], []).append(k)

    def lookup(self, name, props):
        key = java_key(name, props)
        if key in self.table:
            self.used[key] = self.table[key]
            return self.table[key]
        base = key.split("[", 1)[0]
        cands = self.by_name.get(base)
        if cands:
            # Closest state: most matching properties.
            want = set(f"{k}={v}" for k, v in (props or {}).items())
            best = max(cands, key=lambda c: len(want & set(parse_state(c)[1].items() and
                                                          [f"{a}={b}" for a, b in parse_state(c)[1].items()])))
            self.used[best] = self.table[best]
            return self.table[best]
        self.missing.add(key)
        return None

    def bedrock(self, name, props):
        """-> (bedrock name, {state: value})"""
        props = dict(props or {})
        if name in MOD_BLOCKS:
            target, facing_key = MOD_BLOCKS[name]
            states = {}
            # Every state the block defines must be in the palette, or the
            # game cannot resolve it ("Unknown block during Deferred
            # BlockDescriptor resolution").
            if facing_key and target.startswith("alienevo:"):
                states["minecraft:cardinal_direction"] = props.get(facing_key, "north")
            if target == "alienevo:galvan_pod":
                states["alienevo:opened"] = "false"
            return target, states
        if name == "minecraft:void_air" or name == "minecraft:cave_air":
            name = "minecraft:air"
        res = self.lookup(name, props)
        if res is None:
            return "minecraft:air", {}
        return parse_state(res)


def state_tag(v):
    if v in ("true", "false"):
        return Byte(1 if v == "true" else 0)
    if re.fullmatch(r"-?\d+", v):
        return Int(int(v))
    return String(v)


# ------------------------------------------------------------------ templates

class Template:
    """A Java template, with absolute block positions after assembly."""

    def __init__(self, data, offset=(0, 0, 0)):
        self.size = data["size"]
        pal = data.get("palette") or data["palettes"][0]
        self.palette = pal
        self.blocks = []
        ox, oy, oz = offset
        for b in data["blocks"]:
            x, y, z = b["pos"]
            self.blocks.append(((x + ox, y + oy, z + oz), b["state"], b.get("nbt")))
        self.offset = offset

    def jigsaws(self):
        out = []
        for pos, st, nbt in self.blocks:
            p = self.palette[st]
            if p["Name"] == "minecraft:jigsaw" and nbt:
                orient = p.get("Properties", {}).get("orientation", "north_up")
                out.append({"pos": pos, "facing": orient.split("_")[0], "name": nbt.get("name", ""),
                            "target": nbt.get("target", ""), "pool": nbt.get("pool", ""),
                            "final": nbt.get("final_state", "minecraft:air")})
        return out


DIRS = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}


def assemble(vfs, spec):
    """Place the start piece and attach every pool piece through jigsaws."""
    start = Template(read_java(vfs.read(piece_path(spec["piece"]))))
    placed = [start]
    remaining = list(spec.get("pool", []))
    queue = [start]
    while queue and remaining:
        cur = queue.pop(0)
        for j in cur.jigsaws():
            if j["pool"] in ("", "minecraft:empty"):
                continue
            for ref in list(remaining):
                data = read_java(vfs.read(piece_path(ref)))
                cand = Template(data)
                match = next((k for k in cand.jigsaws() if k["name"] == j["target"] and k["facing"] == OPPOSITE[j["facing"]]), None)
                if not match:
                    continue
                d = DIRS[j["facing"]]
                want = (j["pos"][0] + d[0], j["pos"][1] + d[1], j["pos"][2] + d[2])
                off = (want[0] - match["pos"][0], want[1] - match["pos"][1], want[2] - match["pos"][2])
                piece = Template(data, off)
                placed.append(piece)
                queue.append(piece)
                remaining.remove(ref)
                break
    return placed


# ------------------------------------------------------------------ conversion

def loot_path(table):
    if not table:
        return None
    if table in VANILLA_LOOT:
        return VANILLA_LOOT[table]
    ns, path = table.split(":", 1)
    return f"loot_tables/alienevo/structures/{ns}/{path}.json"


def convert(vfs, mapper, spec, out_dir, loot_tables):
    pieces = assemble(vfs, spec)
    # Bounding box of all pieces.
    lo = [min(p.offset[i] for p in pieces) for i in range(3)]
    hi = [max(p.offset[i] + p.size[i] for p in pieces) for i in range(3)]
    size = [hi[i] - lo[i] for i in range(3)]
    sx, sy, sz = size
    n = sx * sy * sz
    layer0 = [-1] * n
    layer1 = [-1] * n
    palette = []
    pal_index = {}
    pos_data = {}

    def pidx(name, states):
        key = (name, tuple(sorted(states.items())))
        if key not in pal_index:
            pal_index[key] = len(palette)
            palette.append(Compound({
                "name": String(name),
                "states": Compound({k: state_tag(v) for k, v in states.items()}),
                "version": Int(BLOCK_VERSION),
            }))
        return pal_index[key]

    water = None
    jigsaw_count = 0
    core_left = bool(spec.get("core_chest"))
    for piece in pieces:
        for (x, y, z), st, nbt in piece.blocks:
            p = piece.palette[st]
            name, props = p["Name"], dict(p.get("Properties", {}))
            if name == "minecraft:jigsaw":
                jigsaw_count += 1
                fname, fprops = parse_state(nbt.get("final_state", "minecraft:air") if nbt else "minecraft:air")
                name, props = fname, fprops
            if name in ("minecraft:structure_block",):
                name, props = "minecraft:air", {}
            if name == "minecraft:structure_void":
                continue
            waterlogged = props.pop("waterlogged", "false") == "true"
            bname, bstates = mapper.bedrock(name, {**props, **({"waterlogged": "false"} if "waterlogged" in p.get("Properties", {}) else {})})
            i = ((x - lo[0]) * sy + (y - lo[1])) * sz + (z - lo[2])
            if not (0 <= i < n):
                continue
            layer0[i] = pidx(bname, bstates)
            if waterlogged or name == "minecraft:water":
                if name != "minecraft:water":
                    if water is None:
                        water = pidx("minecraft:water", {"liquid_depth": "0"})
                    layer1[i] = water
            be = block_entity(name, props, nbt, (x - lo[0], y - lo[1], z - lo[2]), loot_tables)
            if be and core_left and be.get("id").v == "Chest" and "LootTable" in be:
                be["LootTable"] = String(CORE_LOOT)
                core_left = False
            if be:
                pos_data[str(i)] = Compound({"block_entity_data": Compound(be)})

    root = Compound({
        "format_version": Int(1),
        "size": List(INT, [Int(v) for v in size]),
        "structure_world_origin": List(INT, [Int(0), Int(0), Int(0)]),
        "structure": Compound({
            "block_indices": List(LIST, [List(INT, [Int(v) for v in layer0]), List(INT, [Int(v) for v in layer1])]),
            "entities": List(COMPOUND, []),
            "palette": Compound({"default": Compound({
                "block_palette": List(COMPOUND, palette),
                "block_position_data": Compound(pos_data),
            })}),
        }),
    })
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, spec["name"] + ".mcstructure"), "wb") as f:
        f.write(write_bedrock(root))
    return size, len(pieces), len(palette)


CORE_LOOT = "loot_tables/alienevo/structures/crash_site_core.json"


def block_entity(name, props, nbt, pos, loot_tables):
    x, y, z = pos
    common = {"x": Int(x), "y": Int(y), "z": Int(z), "isMovable": Byte(1)}
    if name.endswith("_bed"):
        color = name.split(":")[1][:-4]
        return {"id": String("Bed"), "color": Byte(DYES.index(color) if color in DYES else 14), **common}
    if name.endswith("_banner"):
        color = name.split(":")[1].replace("_wall_banner", "").replace("_banner", "")
        return {"id": String("Banner"), "Base": Int(15 - DYES.index(color) if color in DYES else 0), **common}
    if not nbt:
        return None
    jid = nbt.get("id", name)
    bid = BLOCK_ENTITY_IDS.get(jid) or BLOCK_ENTITY_IDS.get(name)
    if bid is None:
        return None
    be = {"id": String(bid), **common}
    if bid in ("Chest", "Barrel", "BrushableBlock"):
        table = nbt.get("LootTable")
        path = loot_path(table)
        if path:
            be["LootTable"] = String(path)
            be["LootTableSeed"] = Int(0)
            if table not in VANILLA_LOOT:
                loot_tables.add(table)
        if bid != "BrushableBlock":
            be["Items"] = List(COMPOUND, [])
    elif bid == "MobSpawner":
        ent = (nbt.get("SpawnData", {}).get("entity", {}) or {}).get("id", "minecraft:zombie")
        # Spawners of the machine strongholds spawn the Machine Husks.
        be["EntityIdentifier"] = String("alienevo:machine_husk" if ent == "minecraft:husk" else ent)
    return be


# ------------------------------------------------------------------ loot tables

ITEM_SUBSTITUTES = {
    "palladium:raw_titanium": "minecraft:raw_iron", "palladium:titanium_ingot": "minecraft:iron_ingot",
    "palladium:lead_ingot": "minecraft:iron_ingot", "palladium:raw_lead": "minecraft:raw_iron",
}


def known_item(name, bp_items):
    name = ITEM_SUBSTITUTES.get(name, name)
    if name.startswith("minecraft:"):
        return name
    return name if name in bp_items else None


def convert_number(v):
    if isinstance(v, dict):
        if v.get("type", "minecraft:uniform").endswith("uniform"):
            return {"min": v.get("min", 1), "max": v.get("max", 1)}
        if "value" in v:
            return v["value"]
    return v


def convert_loot(java, bp_items):
    pools = []
    for pool in java.get("pools", []):
        entries = []
        for e in pool.get("entries", []):
            t = e.get("type", "").split(":")[-1]
            if t == "empty":
                entries.append({"type": "empty", "weight": e.get("weight", 1)})
                continue
            if t != "item":
                continue
            item = known_item(e.get("name", ""), bp_items)
            if not item:
                continue
            out = {"type": "item", "name": item, "weight": e.get("weight", 1)}
            fns = []
            for fn in e.get("functions", []):
                f = fn.get("function", "").split(":")[-1]
                if f == "set_count":
                    fns.append({"function": "set_count", "count": convert_number(fn.get("count", 1))})
            if fns:
                out["functions"] = fns
            entries.append(out)
        if not entries:
            continue
        p = {"rolls": convert_number(pool.get("rolls", 1)), "entries": entries}
        conds = [{"condition": "random_chance", "chance": c["chance"]} for c in pool.get("conditions", [])
                 if c.get("condition", "").endswith("random_chance")]
        if conds:
            p["conditions"] = conds
        pools.append(p)
    return {"pools": pools}


# ------------------------------------------------------------------ features

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def write_feature(spec):
    name = spec["name"]
    # Identifiers must match the file names or the game ignores the files.
    ident = f"alienevo:structure_{name}_feature"
    constraints = {}
    if spec["place"] == "underground":
        constraints = {"block_intersection": {"block_allowlist": UNDERGROUND_ALLOW}}
    elif spec["y"] >= 0:
        constraints = {"grounded": {}}
    write_json(os.path.join(BP, "features", f"structure_{name}_feature.json"), {
        "format_version": "1.13.0",
        "minecraft:structure_template_feature": {
            "description": {"identifier": ident},
            "structure_name": f"alienevo:{name}",
            "adjustment_radius": 8,
            "facing_direction": "random",
            "constraints": constraints,
        },
    })
    if spec["place"] == "underground":
        lo, hi = spec["y"]
        y = {"distribution": "uniform", "extent": [lo, hi]}
        pass_name = "underground_pass"
    else:
        y = f"q.heightmap(v.worldx, v.worldz) + ({spec['y']})"
        pass_name = "surface_pass"
    spacing = spec["spacing"]
    biomes = [{"test": "has_biome_tag", "operator": "==", "value": b} for b in spec["biomes"]]
    biome_filter = [{"all_of": [{"test": "has_biome_tag", "operator": "==", "value": "overworld"},
                                {"any_of": biomes}]}]
    write_json(os.path.join(BP, "feature_rules", f"structure_{name}.json"), {
        "format_version": "1.13.0",
        "minecraft:feature_rules": {
            # The identifier must match the file name or the rule is ignored.
            "description": {"identifier": f"alienevo:structure_{name}", "places_feature": ident},
            "conditions": {"placement_pass": pass_name, "minecraft:biome_filter": biome_filter},
            "distribution": {
                "iterations": 1,
                # Java: one per spacing x spacing chunks.
                "scatter_chance": {"numerator": 1, "denominator": spacing * spacing // 4},
                "x": {"distribution": "uniform", "extent": [0, 16]},
                "y": y,
                "z": {"distribution": "uniform", "extent": [0, 16]},
            },
        },
    })


def build(vfs, full_table=None):
    for old in glob.glob(os.path.join(BP, "features", "structure_*.json")) + glob.glob(os.path.join(BP, "feature_rules", "structure_*.json")):
        os.remove(old)
    mapper = Mapper(full_table)
    out_dir = os.path.join(BP, "structures", "alienevo")
    if os.path.isdir(out_dir):
        for f in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, f))
    loot_tables = set()
    report = []
    for spec in STRUCTURES:
        size, pieces, pal = convert(vfs, mapper, spec, out_dir, loot_tables)
        write_feature(spec)
        report.append(f"{spec['name']}: {size[0]}x{size[1]}x{size[2]}, {pieces} piece(s), {pal} block states")
    bp_items = {f"alienevo:{os.path.splitext(f)[0]}" for f in os.listdir(os.path.join(BP, "items"))}
    bp_items |= {f"alienevo:{os.path.splitext(f)[0]}" for f in os.listdir(os.path.join(BP, "blocks"))}
    for table in sorted(loot_tables):
        ns, path = table.split(":", 1)
        src = f"data/{ns}/loot_tables/{path}.json"
        if not vfs.exists(src):
            report.append(f"missing loot table {table}")
            continue
        write_json(os.path.join(BP, "loot_tables", "alienevo", "structures", ns, path + ".json"),
                   convert_loot(vfs.json(src), bp_items))
    with open(os.path.join(BP, "scripts", "structure_data.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by tools/structures.py - structures in BP/structures/alienevo.\n")
        f.write("export const STRUCTURES = " + json.dumps([s["name"] for s in STRUCTURES]) + ";\n")
    capsule = os.path.join(BP, "loot_tables", "alienevo", "structures", "alienevo", "galvan_capsule.json")
    core = {"pools": [{"rolls": 1, "entries": [{"type": "item", "name": "alienevo:prototype_core", "weight": 1}]}]}
    if os.path.exists(capsule):
        with open(capsule, encoding="utf-8") as f:
            core["pools"] += json.load(f)["pools"]
    write_json(os.path.join(BP, CORE_LOOT), core)
    if full_table:
        write_json(MAPPING_SUBSET, dict(sorted(mapper.used.items())))
    if mapper.missing:
        report.append("unmapped: " + ", ".join(sorted(mapper.missing)))
    return report


if __name__ == "__main__":
    from layers import VFS
    jars = [a for a in sys.argv[1:] if a.endswith(".jar")]
    table = next((a for a in sys.argv[1:] if a.endswith(".json")), None)
    for line in build(VFS(jars), table):
        print(line)
