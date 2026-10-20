// Omnitrix Workbench (workbench.js of the Java mod): upgrades the Prototype
// Omnitrix through its evolution phases and shows its status.

import { EquipmentSlot, ItemStack, system } from "@minecraft/server";
import { ActionFormData, MessageFormData } from "@minecraft/server-ui";
import { ALIENS, OMNITRIX_TIERS } from "./aliens.js";
import { omnitrixTier, playWatch } from "./omnitrix.js";
import { hasMasterControl, setMasterControl } from "./state.js";
import { particle, sound } from "./util.js";

/** @typedef {import("@minecraft/server").Player} Player */

/** Cost of upgrading FROM the tier at that index. */
const UPGRADE_COST = [
    [{ id: "alienevo:upgrade_chip", count: 2, label: "Galvan Circuit" }, { tag: "alienevo:upgrade_crystals", count: 4, label: "Omni Crystal (any colour)" }],
    [{ id: "alienevo:upgrade_chip", count: 4, label: "Galvan Circuit" }, { tag: "alienevo:upgrade_crystals", count: 8, label: "Omni Crystal (any colour)" }, { id: "minecraft:diamond_block", count: 1, label: "Block of Diamond" }],
    [{ id: "alienevo:upgrade_chip", count: 8, label: "Galvan Circuit" }, { tag: "alienevo:upgrade_crystals", count: 16, label: "Omni Crystal (any colour)" }, { id: "minecraft:netherite_ingot", count: 1, label: "Netherite Ingot" }],
];

/** @param {import("@minecraft/server").ItemStack} item @param {{ id?: string, tag?: string }} req */
function matches(item, req) {
    return req.id ? item.typeId === req.id : !!req.tag && item.hasTag(req.tag);
}

/** @param {Player} p @param {{ id?: string, tag?: string, count: number }} req */
function countOf(p, req) {
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv) return 0;
    let n = 0;
    for (let i = 0; i < inv.size; i++) {
        const it = inv.getItem(i);
        if (it && matches(it, req)) n += it.amount;
    }
    return n;
}

/** @param {Player} p @param {{ id?: string, tag?: string, count: number }} req */
function take(p, req) {
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv) return;
    let left = req.count;
    for (let i = 0; i < inv.size && left > 0; i++) {
        const it = inv.getItem(i);
        if (!it || !matches(it, req)) continue;
        const n = Math.min(left, it.amount);
        left -= n;
        if (it.amount - n <= 0) inv.setItem(i, undefined);
        else {
            it.amount -= n;
            inv.setItem(i, it);
        }
    }
}

/** @param {Player} p @param {import("@minecraft/server").Block} block */
export async function openWorkbench(p, block) {
    const eq = p.getComponent("minecraft:equippable");
    const held = eq?.getEquipment(EquipmentSlot.Mainhand);
    const tier = omnitrixTier(held);
    if (tier < 0) {
        p.sendMessage("§7Hold an §aOmnitrix§7 in your main hand to work on it.");
        sound(p, "alienevo.prototype_failsafe");
        return;
    }
    sound(p, "alienevo.prototype_hourglass");
    const next = OMNITRIX_TIERS[tier + 1];
    const cost = UPGRADE_COST[tier];
    const newAliens = next ? ALIENS.filter((a) => a.tier === tier + 1).map((a) => `${a.color}${a.name}`).join("§7, ") : "";
    let body = `§fOmnitrix: §a${OMNITRIX_TIERS[tier].name}\n§fDNA samples: §a${ALIENS.filter((a) => a.tier <= tier).length}\n§fMaster Control: ${hasMasterControl(p) ? "§aunlocked" : "§clocked"}\n\n`;
    if (next && cost) {
        body += `§eUpgrade to ${next.name}§7 unlocks: ${newAliens}${tier + 1 === 3 ? "§7 and §aMaster Control" : ""}\n§7Cost:\n`;
        for (const req of cost) {
            const have = countOf(p, req);
            body += `${have >= req.count ? "§a" : "§c"} - ${req.count}x ${req.label} §8(${have})\n`;
        }
    } else {
        body += "§aThis Omnitrix is fully evolved.";
    }
    const form = new ActionFormData().title("§2Omnitrix Workbench").body(body);
    if (next) form.button("§2Upgrade", "textures/ui/smithing_icon");
    form.button("§5Customize colours", "textures/items/upgrade_crystal_magenta");
    form.button("§7Close");
    const res = await form.show(p);
    if (res.canceled || res.selection === undefined) return;
    if (res.selection === (next ? 1 : 0)) {
        await customizeMenu(p);
        return;
    }
    if (res.selection !== 0 || !next || !cost) return;

    if (!cost.every((req) => countOf(p, req) >= req.count)) {
        p.sendMessage("§cYou are missing materials for this upgrade.");
        sound(p, "alienevo.prototype_failsafe");
        return;
    }
    system.run(() => {
        const current = eq?.getEquipment(EquipmentSlot.Mainhand);
        if (omnitrixTier(current) !== tier) return;
        for (const req of cost) take(p, req);
        eq?.setEquipment(EquipmentSlot.Mainhand, new ItemStack(next.item, 1));
        if (tier + 1 === 3) setMasterControl(p, true);
        sound(p, "alienevo.prototype_core_place");
        sound(p, "random.levelup", 0.6, 1.2);
        particle(p, "minecraft:totem_particle", block.center());
        p.sendMessage(`§aYour Omnitrix evolved into the §2${next.name}§a!`);
    });
}

/** Code Tablets unlock Master Control or start the Self Destruct sequence. @param {Player} p @param {string} typeId */
export async function useCodeTablet(p, typeId) {
    if (typeId === "alienevo:code_tablet") {
        if (hasMasterControl(p)) {
            p.sendMessage("§7Master Control is already unlocked.");
            return;
        }
        system.run(() => {
            setMasterControl(p, true);
            consumeHeld(p, typeId);
            sound(p, "alienevo.prototype_master_control");
            playWatch(p, "master_control");
            p.sendMessage("§a§lMaster Control unlocked! §r§7The Omnitrix will no longer time out.");
        });
        return;
    }
    const res = await new MessageFormData()
        .title("§4Self Destruct")
        .body("§cThis will activate the Omnitrix self destruct sequence.\n§7In 10 seconds a huge explosion will destroy everything around you.\n\nAre you sure?")
        .button1("§4Activate")
        .button2("§7Cancel")
        .show(p);
    if (res.canceled || res.selection !== 0) return;
    system.run(() => {
        consumeHeld(p, typeId);
        let n = 10;
        const id = system.runInterval(() => {
            if (!p.isValid) return system.clearRun(id);
            if (n > 0) {
                p.onScreenDisplay.setTitle(`§4${n}`, { fadeInDuration: 0, stayDuration: 20, fadeOutDuration: 0 });
                sound(p, "alienevo.prototype_sdm_blink");
                n--;
                return;
            }
            system.clearRun(id);
            sound(p, "alienevo.prototype_sdm");
            try {
                p.dimension.createExplosion(p.location, 10, { breaksBlocks: true, causesFire: true, source: p });
            } catch {
                // Ignore.
            }
        }, 20);
    });
}

/** @param {Player} p @param {string} typeId */
function consumeHeld(p, typeId) {
    const eq = p.getComponent("minecraft:equippable");
    const held = eq?.getEquipment(EquipmentSlot.Mainhand);
    if (held?.typeId !== typeId) return;
    if (held.amount > 1) {
        held.amount--;
        eq?.setEquipment(EquipmentSlot.Mainhand, held);
    } else {
        eq?.setEquipment(EquipmentSlot.Mainhand, undefined);
    }
}

// ------------------------------------------------------------ colour modules
// Like the Java workbench: every part of the watch can be recoloured with an
// Omni Crystal of that colour; the glow too.  Stored in synced player
// properties (BP entities/player.json) read by the watch attachable.

const SLOTS = ["Primary base", "Secondary base", "Tertiary base", "Buttons", "Core (side)", "Core (top)",
    "Dial (inner)", "Dial (outer)", "Tubes"];
const COLOURS = ["lime", "white", "light_gray", "gray", "black", "brown", "red", "orange", "yellow", "green",
    "cyan", "light_blue", "blue", "purple", "magenta", "pink"];
const COLOUR_NAMES = ["Lime", "White", "Light Gray", "Gray", "Black", "Brown", "Red", "Orange", "Yellow", "Green",
    "Cyan", "Light Blue", "Blue", "Purple", "Magenta", "Pink"];

/** @param {number} i */
const crystalId = (i) => (COLOURS[i] === "lime" ? "alienevo:upgrade_crystal" : `alienevo:upgrade_crystal_${COLOURS[i]}`);

/** @param {Player} p @param {string} prop */
function getColour(p, prop) {
    const v = p.getProperty(prop);
    return typeof v === "number" ? v : -1;
}

/** @param {Player} p */
async function customizeMenu(p) {
    const form = new ActionFormData().title("§5Omnitrix Colours").body("§7Pick a part of the watch. Each new colour costs one Omni Crystal of that colour.");
    SLOTS.forEach((name, i) => {
        const c = getColour(p, `alienevo:col${i}`);
        form.button(`${name}\n§8${c < 0 ? "Default" : COLOUR_NAMES[c]}`, c < 0 ? "textures/ui/icon_recipe_item" : `textures/items/${crystalId(c).split(":")[1]}`);
    });
    const g = getColour(p, "alienevo:glow");
    form.button(`§aGlow\n§8${g < 0 ? "Default" : COLOUR_NAMES[g]}`, g < 0 ? "textures/ui/icon_recipe_item" : `textures/items/${crystalId(g).split(":")[1]}`);
    form.button("§cReset all to default");
    const res = await form.show(p);
    if (res.canceled || res.selection === undefined) return;
    if (res.selection === SLOTS.length + 1) {
        system.run(() => {
            for (let i = 0; i < SLOTS.length; i++) p.setProperty(`alienevo:col${i}`, -1);
            p.setProperty("alienevo:glow", -1);
            sound(p, "alienevo.color_module_insert");
        });
        return;
    }
    const prop = res.selection < SLOTS.length ? `alienevo:col${res.selection}` : "alienevo:glow";
    const label = res.selection < SLOTS.length ? SLOTS[res.selection] : "Glow";
    await colourMenu(p, prop, label);
    await customizeMenu(p);
}

/** @param {Player} p @param {string} prop @param {string} label */
async function colourMenu(p, prop, label) {
    const form = new ActionFormData().title(`§5${label}`).body("§7Choose a colour (needs one matching Omni Crystal).");
    form.button("§8Default", "textures/ui/icon_recipe_item");
    COLOURS.forEach((_, i) => {
        const have = countOf(p, { id: crystalId(i), count: 1 });
        form.button(`${have > 0 ? "§0" : "§8"}${COLOUR_NAMES[i]} §8(${have})`, `textures/items/${crystalId(i).split(":")[1]}`);
    });
    const res = await form.show(p);
    if (res.canceled || res.selection === undefined) return;
    const colour = res.selection - 1;
    system.run(() => {
        if (colour >= 0) {
            const req = { id: crystalId(colour), count: 1 };
            if (countOf(p, req) < 1) {
                p.sendMessage(`§cYou need a ${COLOUR_NAMES[colour]} Omni Crystal.`);
                return;
            }
            take(p, req);
        }
        p.setProperty(prop, colour);
        sound(p, "alienevo.color_module_insert");
        sound(p, "alienevo.prototype_cycle_color", 0.6);
    });
}
