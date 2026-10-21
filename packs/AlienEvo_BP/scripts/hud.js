// Omnitrix HUD: the Omnitrix badge with health and energy bars (top left)
// and the Palladium ability bar of the Java mod (right side) while
// transformed.  The script sends the state as a title starting with
// HUD_PREFIX; RP ui/alienevo_hud.json keeps the last such title and draws
// it, and ui/hud_screen.json hides it from the normal title display.
//
// Layout of the title (fixed width so the UI can cut the text after it):
//   aev:[hHH][eEE][mM][b<key padded to KEY_WIDTH>][kK][nN][0c?][1c?][2c?][3c?]<text>
//   H/E  health and energy, 0-20
//   M    0 no Omnitrix, 1 ready, 2 recharging, 3 transformed
//   K    selected slot of the ability bar (abilities, then the Omnitrix slot = 4)
//   N    number of ability slots
//   ?    per ability: 0 ready, 1 cooling down, 2 locked

import { system, world } from "@minecraft/server";
import { ABILITIES } from "./abilities.js";
import { ALIEN_BY_ID, MAX_TIMER, RECHARGE_TIMER } from "./aliens.js";
import { isDialOpen } from "./dial.js";
import { cooldownLeft, currentAlien, wornTier } from "./omnitrix.js";
import { getAbilityIndex, getRecharge, getSelected, getTimer, hasMasterControl, isSkillUnlocked } from "./state.js";
import { formatTime, titleHolds } from "./util.js";

/** @typedef {import("@minecraft/server").Player} Player */

export const HUD_PREFIX = "aev:";
const KEY_WIDTH = 20;
/** Slots of the ability bar before the Omnitrix slot. */
export const BAR_SLOTS = 4;

/** @type {Map<string, string>} */
const lastSent = new Map();

/** @param {number} v @param {number} max */
const twenty = (v, max) => String(Math.max(0, Math.min(20, Math.round((v / Math.max(1, max)) * 20)))).padStart(2, "0");

/** @param {Player} p */
export function hudString(p) {
    const tier = wornTier(p);
    if (tier < 0) return `${HUD_PREFIX}[h00][e00][m0][b${"".padEnd(KEY_WIDTH, ".")}][k0][n0][0c0][1c0][2c0][3c0]`;
    const health = p.getComponent("minecraft:health");
    const h = twenty(health?.currentValue ?? 20, health?.effectiveMax ?? 20);
    const alien = currentAlien(p);
    const recharge = getRecharge(p);
    let mode = 1, energy = "20", key = "", sel = 0, count = 0, text = "";
    const states = ["0", "0", "0", "0"];
    if (alien) {
        mode = 3;
        key = alien.key;
        energy = hasMasterControl(p) ? "20" : twenty(getTimer(p), MAX_TIMER);
        count = Math.min(alien.abilities.length, BAR_SLOTS);
        sel = Math.min(getAbilityIndex(p, alien.key), alien.abilities.length);
        alien.abilities.slice(0, BAR_SLOTS).forEach((id, i) => {
            if (!isSkillUnlocked(p, alien.key, i)) states[i] = "2";
            else if (cooldownLeft(p, id) > 0) states[i] = "1";
        });
        const id = alien.abilities[sel];
        if (id) {
            const left = cooldownLeft(p, id);
            const name = ABILITIES[id]?.name ?? id;
            text = !isSkillUnlocked(p, alien.key, sel) ? `§8${name} §c(locked)` : left > 0 ? `§7${name} §c${(left / 20).toFixed(1)}s` : `§e${name}`;
        } else {
            text = "§aOmnitrix";
        }
        if (sel === alien.abilities.length) sel = BAR_SLOTS;
        if (!hasMasterControl(p)) text += ` §8| ${getTimer(p) < 200 ? "§c" : "§a"}${formatTime(getTimer(p))}`;
    } else if (recharge > 0) {
        mode = 2;
        energy = twenty(RECHARGE_TIMER - recharge, RECHARGE_TIMER);
        text = `§cRecharging §f${formatTime(recharge)}`;
    } else {
        const next = ALIEN_BY_ID.get(getSelected(p));
        key = next?.key ?? "";
        text = next ? `${next.color}${next.name}` : "";
    }
    return `${HUD_PREFIX}[h${h}][e${energy}][m${mode}][b${key.padEnd(KEY_WIDTH, ".")}][k${sel}][n${count}]${states.map((s, i) => `[${i}c${s}]`).join("")}${text}`;
}

/** @param {Player} p */
function update(p) {
    if (isDialOpen(p) || (titleHolds.get(p.id) ?? 0) > system.currentTick) return;
    const s = hudString(p);
    // Resend now and then: the UI forgets the data when the world reloads.
    if (lastSent.get(p.id) === s && system.currentTick % 200 >= 5) return;
    lastSent.set(p.id, s);
    try {
        p.onScreenDisplay.setTitle(s, { fadeInDuration: 0, stayDuration: 2, fadeOutDuration: 0 });
    } catch {
        // Player left.
    }
}

/** Forces the next update to resend (e.g. after another title replaced the data). @param {Player} p */
export function refreshHud(p) {
    lastSent.delete(p.id);
}

export function initHud() {
    system.runInterval(() => {
        for (const p of world.getAllPlayers()) update(p);
    }, 5);
    world.afterEvents.playerSpawn.subscribe(({ player }) => refreshHud(player));
}
