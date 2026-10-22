// Structure generation (the Java mod's structure sets): the world is divided
// into regions of `spacing` chunks per structure; each region gets one
// attempt at a random spot.  When a player comes close the spot's biome is
// checked and the structure is placed with the structure manager, keeping
// the chunks it covers loaded with a temporary ticking area.

import { system, world } from "@minecraft/server";
import { STRUCTURE_SPECS } from "./structure_data.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Entity} Entity */
/** @typedef {import("@minecraft/server").Dimension} Dimension */

const NEAR = 72;
const SALT_KEY = "alienevo:gen_salt";

/** Deterministic 0..1 random for a region. @param {number} salt @param {string} name @param {number} rx @param {number} rz @param {number} k */
function rand(salt, name, rx, rz, k) {
    let h = salt ^ 0x9e3779b9;
    for (const c of `${name}:${rx}:${rz}:${k}`) h = Math.imul(h ^ c.charCodeAt(0), 0x5bd1e995) ^ (h >>> 13);
    h = Math.imul(h ^ (h >>> 15), 0x27d4eb2d);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

function salt() {
    let v = world.getDynamicProperty(SALT_KEY);
    if (typeof v !== "number") {
        v = Math.floor(Math.random() * 2147483647);
        world.setDynamicProperty(SALT_KEY, v);
    }
    return v;
}

/**
 * Places a structure with its corner at `origin`.
 * @param {Dimension} dim @param {string} name @param {import("@minecraft/server").Vector3} origin
 * @param {(msg: string) => void} [tell]
 */
export function placeAt(dim, name, origin, tell) {
    const id = `alienevo:${name}`;
    const structure = world.structureManager.get(id);
    if (!structure) {
        tell?.(`§cStructure ${id} was not found in the behavior pack.`);
        return;
    }
    const size = structure.size;
    const area = `alienevo_${name}_${origin.x}_${origin.z}`.replace(/-/g, "m");
    try {
        dim.runCommand(`tickingarea add ${origin.x} ${origin.y} ${origin.z} ${origin.x + size.x} ${origin.y + size.y} ${origin.z + size.z} ${area} true`);
    } catch (e) {
        tell?.(`§7(ticking area not added: ${e})`);
    }
    let tries = 0;
    const attempt = () => {
        tries++;
        try {
            world.structureManager.place(structure, dim, origin, { includeEntities: true });
            tell?.(`§aPlaced ${name} §7(${size.x}x${size.y}x${size.z}) at ${origin.x} ${origin.y} ${origin.z}.`);
        } catch (e) {
            if (tries < 20) {
                system.runTimeout(attempt, 10);
                return;
            }
            tell?.(`§cCould not place ${name}: ${e}`);
            console.warn(`[AlienEvo] could not place ${name}: ${e}`);
        }
        try {
            dim.runCommand(`tickingarea remove ${area}`);
        } catch {
            // Ignore.
        }
    };
    system.runTimeout(attempt, 10);
}

/** Places a structure centred on an entity (the /placestructure command). @param {Entity} src @param {string} name */
export function placeStructure(src, name) {
    const structure = world.structureManager.get(`alienevo:${name}`);
    const size = structure?.size ?? { x: 0, y: 0, z: 0 };
    const loc = src.location;
    const tell = (/** @type {string} */ msg) => {
        if (src.typeId === "minecraft:player") /** @type {Player} */ (src).sendMessage(msg);
    };
    placeAt(src.dimension, name, { x: Math.floor(loc.x - size.x / 2), y: Math.floor(loc.y), z: Math.floor(loc.z - size.z / 2) }, tell);
}

/** @param {Player} p @param {number} s */
function scan(p, s) {
    const dim = p.dimension;
    if (dim.id !== "minecraft:overworld") return;
    const loc = p.location;
    for (const spec of STRUCTURE_SPECS) {
        const region = spec.spacing * 16;
        const rx = Math.floor(loc.x / region);
        const rz = Math.floor(loc.z / region);
        const key = `alienevo:gen:${spec.name}:${rx}:${rz}`;
        if (world.getDynamicProperty(key)) continue;
        const margin = Math.max(spec.size[0], spec.size[2]) + 8;
        const span = Math.max(1, region - margin * 2);
        const cx = rx * region + margin + Math.floor(rand(s, spec.name, rx, rz, 1) * span);
        const cz = rz * region + margin + Math.floor(rand(s, spec.name, rx, rz, 2) * span);
        if (Math.abs(cx - loc.x) > NEAR || Math.abs(cz - loc.z) > NEAR) continue;
        world.setDynamicProperty(key, true);
        let top;
        try {
            top = dim.getTopmostBlock({ x: cx, z: cz });
        } catch {
            top = undefined;
        }
        if (!top) {
            world.setDynamicProperty(key, undefined); // chunk not ready, try later
            continue;
        }
        let tags = [];
        try {
            tags = dim.getBiome({ x: cx, y: top.location.y, z: cz }).getTags();
        } catch {
            // Unknown biome: treat as plain overworld.
            tags = ["overworld"];
        }
        if (!spec.biomes.some((b) => tags.includes(b))) continue;
        if (top.isLiquid) continue;
        let y;
        if (spec.place === "underground") {
            const [lo, hi] = /** @type {number[]} */ (spec.y);
            y = Math.floor(lo + rand(s, spec.name, rx, rz, 3) * (hi - lo));
            if (y + spec.size[1] > top.location.y - 4) y = top.location.y - 4 - spec.size[1];
        } else {
            y = top.location.y + 1 + /** @type {number} */ (spec.y);
        }
        placeAt(dim, spec.name, { x: cx - Math.floor(spec.size[0] / 2), y, z: cz - Math.floor(spec.size[2] / 2) });
    }
}

export function initWorldgen() {
    system.runInterval(() => {
        const s = salt();
        for (const p of world.getAllPlayers()) {
            try {
                scan(p, s);
            } catch (e) {
                console.warn(`[AlienEvo] worldgen: ${e}`);
            }
        }
    }, 60);
}
