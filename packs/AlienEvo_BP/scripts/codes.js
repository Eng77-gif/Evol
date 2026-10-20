// Omnitrix code system (codes.js / code_hints.js of the Java mod): every
// player has a secret 6-digit Master Control code and a Self Destruct code.
// Code Tablets reveal one digit each; the code is dialled on the Omnitrix.
// Transformation tablets (Aliens Untapped) give the code of one alien's DNA.

import { EquipmentSlot, ItemStack, system } from "@minecraft/server";
import { ALIEN_BY_KEY, ALIENS } from "./aliens.js";
import { showOnDial } from "./dial.js";
import { playWatch } from "./omnitrix.js";
import { getAlien, getExtraDna, hasMasterControl, setExtraDna, setMasterControl, setSelected } from "./state.js";
import { sound } from "./util.js";

/** @typedef {import("@minecraft/server").Player} Player */

const MASTER = "alienevo:code_master";
const SELF_DESTRUCT = "alienevo:code_sd";
const TRANSFORMATION = "alienevo:code_transformation";
const USED = { master: "alienevo:code_used_master", sd: "alienevo:code_used_sd" };

function randomCode() {
    let code = "";
    for (let i = 0; i < 6; i++) code += Math.floor(Math.random() * 9) + 1;
    return code;
}

/** @param {Player} p @param {string} key */
function str(p, key) {
    const v = p.getDynamicProperty(key);
    return typeof v === "string" ? v : "";
}

/** Generates the codes the first time they are needed. @param {Player} p */
export function ensureCodes(p) {
    let master = str(p, MASTER);
    if (!master && !hasMasterControl(p)) {
        master = randomCode();
        p.setDynamicProperty(MASTER, master);
    }
    if (!str(p, SELF_DESTRUCT)) {
        let sd;
        do sd = randomCode(); while (sd === master);
        p.setDynamicProperty(SELF_DESTRUCT, sd);
    }
    return { master, sd: str(p, SELF_DESTRUCT) };
}

/** "MC: 1 2 3 4 5 6  SD: ..." like the reveal_code ability. @param {Player} p */
export function revealCodes(p) {
    const { master, sd } = ensureCodes(p);
    let text = "";
    if (master) text += `§aMC: ${master.split("").join(" ")}§r  `;
    text += `§cSD: ${sd.split("").join(" ")}`;
    p.onScreenDisplay.setActionBar(text);
    p.sendMessage(text);
}

/** Right-clicking an unread Code Tablet reveals one digit in its lore. @param {Player} p @param {string} typeId */
export function useCodeTablet(p, typeId) {
    system.run(() => {
        if (!p.isValid) return;
        const eq = p.getComponent("minecraft:equippable");
        const item = eq?.getEquipment(EquipmentSlot.Mainhand);
        if (!item || item.typeId !== typeId) return;
        const lore = item.getLore();
        if (lore.length) {
            lore.forEach((l) => p.sendMessage(l));
            return;
        }
        if (typeId === "alienevo:code_tablet_transformation") {
            readTransformationTablet(p, item, eq);
            return;
        }
        if (typeId === "alienevo:broken_code_tablet") {
            repairTablet(p, item, eq);
            return;
        }
        const sdTablet = typeId === "alienevo:code_tablet_selfdestruct";
        const codes = ensureCodes(p);
        const code = sdTablet ? codes.sd : codes.master;
        if (!code) {
            p.sendMessage("§7Master Control is already unlocked.");
            return;
        }
        // Each tablet shows a digit the previous tablets did not.
        const usedKey = sdTablet ? USED.sd : USED.master;
        let used = str(p, usedKey).split("").map(Number);
        let free = [0, 1, 2, 3, 4, 5].filter((i) => !used.includes(i));
        if (!free.length) {
            used = [];
            free = [0, 1, 2, 3, 4, 5];
        }
        const pos = free[Math.floor(Math.random() * free.length)];
        p.setDynamicProperty(usedKey, [...used, pos].join(""));
        const colour = sdTablet ? "§c" : "§6";
        const digits = [...code].map((d, i) => (i === pos ? `${colour}${d}` : `${colour}§k0§r`)).join(" ");
        item.setLore([sdTablet ? "§4Self Destruct" : "§aMaster Control", `${sdTablet ? "§c" : "§e"}Code: ${digits}`]);
        if (item.amount > 1) {
            const rest = item.clone();
            rest.amount = item.amount - 1;
            rest.setLore([]);
            item.amount = 1;
            p.getComponent("minecraft:inventory")?.container?.addItem(rest);
        }
        eq?.setEquipment(EquipmentSlot.Mainhand, item);
        sound(p, "alienevo.prototype_cycle_color");
        p.sendMessage(`${sdTablet ? "§4Self Destruct" : "§aMaster Control"} §7digit ${pos + 1}: ${colour}${code[pos]}`);
    });
}

/**
 * Transformation tablet: shows the code that adds this alien's DNA.
 * @param {Player} p @param {import("@minecraft/server").ItemStack} item
 * @param {import("@minecraft/server").EntityEquippableComponent | undefined} eq
 */
function readTransformationTablet(p, item, eq) {
    const alien = ALIENS[Math.floor(Math.random() * ALIENS.length)];
    const code = transformationCode(p, alien.key);
    item.setLore([`§a${alien.name}`, `§eCode: §6${code}`]);
    eq?.setEquipment(EquipmentSlot.Mainhand, item);
    sound(p, "alienevo.prototype_cycle_color");
    p.sendMessage(`§a${alien.name} §7transformation code: §6${code}§7. Dial it on the Omnitrix (menu > Enter code).`);
}

/**
 * Incomplete tablet + Galvan Circuit = blank tablet, + Primus Link Circuit =
 * transformation tablet.  Only a Galvan is smart enough to finish it.
 * @param {Player} p @param {import("@minecraft/server").ItemStack} item
 * @param {import("@minecraft/server").EntityEquippableComponent | undefined} eq
 */
function repairTablet(p, item, eq) {
    if (getAlien(p) !== ALIEN_BY_KEY.get("galvan")?.id) {
        sound(p, "note.bass", 1, 0.5);
        p.onScreenDisplay.setActionBar("§c§oYou need to be smarter to finish crafting this");
        return;
    }
    const off = eq?.getEquipment(EquipmentSlot.Offhand);
    const result = off?.typeId === "alienevo:upgrade_chip" ? "alienevo:blank_code_tablet"
        : off?.typeId === "alienevo:primus_link_circuit" ? "alienevo:code_tablet_transformation" : undefined;
    if (!off || !result) {
        sound(p, "note.bass", 1, 0.5);
        p.onScreenDisplay.setActionBar("§c§oYou need a Galvan Circuit or Primus Link Circuit (offhand)");
        return;
    }
    const shrink = (/** @type {import("@minecraft/server").ItemStack} */ it) => {
        if (it.amount <= 1) return undefined;
        it.amount--;
        return it;
    };
    eq?.setEquipment(EquipmentSlot.Offhand, shrink(off));
    eq?.setEquipment(EquipmentSlot.Mainhand, shrink(item));
    p.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(result, 1));
    sound(p, "smithing_table.use", 1, 0.5);
}

/**
 * Called whenever the code dialled on the Omnitrix changes (display_code
 * ability: the code is checked continuously, there is no "enter" button).
 * Returns true when the code did something and the dial should reset.
 * @param {Player} p @param {string} code
 */
export function checkCode(p, code) {
    const codes = ensureCodes(p);
    if (codes.master && code === codes.master) {
        if (hasMasterControl(p)) {
            // Entering it again zeroes Master Control out.
            setMasterControl(p, false);
            sound(p, "alienevo.prototype_failsafe");
            p.sendMessage("§cMaster Control zeroed out.");
            return true;
        }
        setMasterControl(p, true);
        sound(p, "alienevo.prototype_master_control");
        playWatch(p, "master_control");
        p.onScreenDisplay.setTitle("§a§lMaster Control", { fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
        p.sendMessage("§a§lMaster Control unlocked! §r§7The Omnitrix will no longer time out.");
        return true;
    }
    if (code === codes.sd) {
        p.setDynamicProperty(SELF_DESTRUCT, undefined);
        selfDestruct(p);
        return true;
    }
    // Transformation codes (Aliens Untapped): add or remove that alien's DNA.
    const tcodes = transformationCodes(p);
    const key = Object.keys(tcodes).find((k) => tcodes[k] === code);
    const alien = key ? ALIEN_BY_KEY.get(key) : undefined;
    if (!alien) return false;
    const extra = getExtraDna(p);
    if (extra.includes(alien.id)) {
        setExtraDna(p, extra.filter((id) => id !== alien.id));
        sound(p, "alienevo.prototype_core_place", 1, 0.5);
        p.sendMessage(`${alien.color}${alien.name}§c DNA removed from the Omnitrix.`);
    } else {
        setExtraDna(p, [...extra, alien.id]);
        setSelected(p, alien.id);
        showOnDial(p, alien.key);
        sound(p, "alienevo.prototype_core_place");
        p.onScreenDisplay.setTitle(`${alien.color}§l${alien.name}`, { fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10, subtitle: "§aDNA unlocked" });
        p.sendMessage(`${alien.color}${alien.name}§a DNA added to the Omnitrix!`);
    }
    playWatch(p, "close_trigger");
    return true;
}

/** @param {Player} p @returns {Record<string, string>} */
function transformationCodes(p) {
    try {
        const v = p.getDynamicProperty(TRANSFORMATION);
        return typeof v === "string" ? JSON.parse(v) : {};
    } catch {
        return {};
    }
}

/** Per-player code of an alien, generated the first time a tablet shows it. @param {Player} p @param {string} key */
function transformationCode(p, key) {
    const tcodes = transformationCodes(p);
    if (!tcodes[key]) {
        const taken = new Set([...Object.values(tcodes), str(p, MASTER), str(p, SELF_DESTRUCT)]);
        let code;
        do code = randomCode(); while (taken.has(code));
        tcodes[key] = code;
        p.setDynamicProperty(TRANSFORMATION, JSON.stringify(tcodes));
    }
    return tcodes[key];
}

/** prototype_omnitrix_sdm: 10 second countdown, then a huge explosion. @param {Player} p */
function selfDestruct(p) {
    p.sendMessage("§4§lSELF DESTRUCT SEQUENCE ACTIVATED");
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
}
