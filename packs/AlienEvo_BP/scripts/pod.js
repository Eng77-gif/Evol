// Galvan Pods (pod_loot.js of the Java mod).  The Java structures cannot be
// loaded by Bedrock, so pods are scattered through the world by a feature rule
// and hand out the same loot when opened.

import { ItemStack, system } from "@minecraft/server";
import { particle, sound } from "./util.js";

/** @typedef {{ item: string, weight: number, maxStack: number }} Entry */

const SHARD_COLORS = ["", "_black", "_green", "_brown", "_cyan", "_magenta", "_light_gray", "_gray", "_pink",
    "_purple", "_light_blue", "_blue", "_red", "_orange", "_white", "_yellow"];

/** @type {Record<string, { maxTotal: number, weight: number, items: Entry[] }>} */
const GROUPS = {
    shards: {
        maxTotal: 6, weight: 10,
        items: SHARD_COLORS.map((c) => ({ item: `alienevo:upgrade_shards${c}`, weight: c === "" ? 4 : 2, maxStack: 3 })),
    },
    crystals: {
        maxTotal: 2, weight: 4,
        items: SHARD_COLORS.map((c) => ({ item: `alienevo:upgrade_crystal${c}`, weight: c === "" ? 0.5 : 0.25, maxStack: 1 })),
    },
    materials: {
        maxTotal: 8, weight: 15,
        items: [
            { item: "minecraft:iron_ingot", weight: 6, maxStack: 2 },
            { item: "minecraft:copper_ingot", weight: 5, maxStack: 2 },
            { item: "alienevo:galvan_scrap", weight: 16, maxStack: 4 },
            { item: "alienevo:galvan_metal", weight: 5, maxStack: 2 },
            { item: "alienevo:upgrade_chip", weight: 2, maxStack: 1 },
            { item: "alienevo:smithing_template_galvan", weight: 3, maxStack: 1 },
        ],
    },
};

const OMNITRIX_RARITY = 300;
const CORE_RARITY = 20;
const TABLET_RARITY = 40;

/** @template T @param {T[]} list @param {(x: T) => number} w */
function weighted(list, w) {
    const total = list.reduce((s, x) => s + w(x), 0);
    let r = Math.random() * total;
    for (const x of list) {
        r -= w(x);
        if (r <= 0) return x;
    }
    return list[0];
}

function rollLoot() {
    /** @type {ItemStack[]} */
    const out = [];
    /** @type {Record<string, number>} */
    const counts = { shards: 0, crystals: 0, materials: 0 };
    const slots = Math.floor(Math.random() * 6) + 5;
    const groups = Object.entries(GROUPS);
    for (let i = 0; i < slots; i++) {
        const [name, group] = weighted(groups, (g) => g[1].weight);
        const entry = weighted(group.items, (e) => e.weight);
        const possible = Math.min(entry.maxStack, group.maxTotal - counts[name]);
        if (possible <= 0) continue;
        const n = Math.floor(Math.random() * possible) + 1;
        counts[name] += n;
        out.push(new ItemStack(entry.item, n));
    }
    if (Math.random() < 1 / CORE_RARITY) out.push(new ItemStack("alienevo:prototype_core", 1));
    if (Math.random() < 1 / TABLET_RARITY) {
        out.push(new ItemStack(Math.random() < 0.8 ? "alienevo:code_tablet" : "alienevo:code_tablet_selfdestruct", 1));
    }
    if (Math.random() < 1 / OMNITRIX_RARITY) out.push(new ItemStack("alienevo:prototype_omnitrix", 1));
    return out;
}

/** @param {import("@minecraft/server").Player} p @param {import("@minecraft/server").Block} block */
export function openPod(p, block) {
    if (block.permutation.getState(/** @type {any} */ ("alienevo:opened"))) {
        p.sendMessage("§7This Galvan Pod is empty.");
        return;
    }
    const loc = block.center();
    system.run(() => {
        try {
            block.setPermutation(block.permutation.withState(/** @type {any} */ ("alienevo:opened"), true));
        } catch {
            return;
        }
        const above = { x: loc.x, y: loc.y + 0.7, z: loc.z };
        for (const item of rollLoot()) block.dimension.spawnItem(item, above);
        sound(p, "random.chestopen", 1, 0.7);
        sound(p, "alienevo.prototype_decouple", 0.6);
        particle(p, "minecraft:villager_happy", above);
    });
}
