// The Omnitrix used in the world, like the show and the Java mod.  The left
// arm is raised in front of the camera (player property alienevo:wv) and the
// dial is turned by turning your view (or left/right):
//
//  - alien dial: a hologram of the selected alien rises from the core, use
//    the Omnitrix again or jump to slam the core down, sneak to close.
//  - code entry (settings mode, codes.js): each turn of the dial changes the
//    highlighted digit, jump moves to the next digit, sneak closes.  The code
//    is checked every time it changes, like the display_code ability.

import { InputPermissionCategory, system, world } from "@minecraft/server";
import { ALIEN_BY_ID } from "./aliens.js";
import { checkCode } from "./codes.js";
import { HOLO_KEYS } from "./holo_data.js";
import { playWatch, selectionList, transform, wearsRecal } from "./omnitrix.js";
import { getAlien, getRecharge, getSelected, setSelected } from "./state.js";
import { actionbar, sound } from "./util.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Entity} Entity */
/** @typedef {import("./aliens.js").Alien} Alien */

const HOLOGRAM = "alienevo:omnitrix_hologram";
/** Degrees of view rotation per dial step. */
const STEP = 28;
const IDLE_TICKS = 400;

/**
 * @typedef {{ mode: "dial" | "code", list: Alien[], index: number, digits: number[], pos: number,
 *             yaw: number, holo?: Entity, spin: number, idle: number, moveX: number, closing: boolean }} Dial
 */
/** @type {Map<string, Dial>} */
const dials = new Map();

/** @param {Player} p */
export const isDialOpen = (p) => dials.has(p.id);

/** Shows an alien's silhouette on the watch face. @param {Player} p @param {string | undefined} key */
export function showOnDial(p, key) {
    try {
        p.setProperty("alienevo:sel", key ? HOLO_KEYS.indexOf(key) : -1);
    } catch {
        // Player left.
    }
}

/** Icon of an alien as a text glyph. @param {string} key */
const glyph = (key) => String.fromCharCode(0xe100 + Math.max(0, HOLO_KEYS.indexOf(key)));

/** @param {Player} p @param {boolean} on */
function watchView(p, on) {
    try {
        p.setProperty("alienevo:wv", on);
        p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, !on);
    } catch {
        // Player left.
    }
}

/** @param {Player} p @param {"dial" | "code"} mode @param {Alien[]} list */
function open(p, mode, list) {
    closeWorldDial(p, false);
    const index = Math.max(0, list.findIndex((a) => a.id === getSelected(p)));
    /** @type {Dial} */
    const dial = { mode, list, index, digits: [0, 0, 0, 0, 0, 0], pos: 0, yaw: p.getRotation().y, spin: 0, idle: 0, moveX: 0, closing: false };
    dials.set(p.id, dial);
    watchView(p, true);
    return dial;
}

/** Alien selection dial. @param {Player} p @param {number} tier */
export function openWorldDial(p, tier) {
    const list = selectionList(p, tier);
    if (!list.length) {
        actionbar(p, "§cNo alien DNA available.");
        return;
    }
    const dial = open(p, "dial", list);
    sound(p, wearsRecal(p) ? "alienevo.recal_activation" : "alienevo.prototype_activate");
    playWatch(p, "open_trigger");
    try {
        dial.holo = p.dimension.spawnEntity(HOLOGRAM, holoPos(p, 0));
    } catch {
        dial.holo = undefined;
    }
    show(p, dial);
}

/** Code entry (settings mode of the watch). @param {Player} p */
export function openCodeMode(p) {
    const dial = open(p, "code", []);
    sound(p, "alienevo.prototype_activate");
    playWatch(p, "settings_trigger");
    showOnDial(p, undefined);
    show(p, dial);
}

/** @param {Player} p @param {boolean} [playClose] */
export function closeWorldDial(p, playClose = true) {
    const dial = dials.get(p.id);
    if (!dial) return;
    dials.delete(p.id);
    removeHolo(dial);
    watchView(p, false);
    if (!p.isValid) return;
    const sel = ALIEN_BY_ID.get(getSelected(p));
    showOnDial(p, sel?.key);
    try {
        p.onScreenDisplay.setTitle(" ", { fadeInDuration: 0, stayDuration: 0, fadeOutDuration: 0 });
    } catch {
        // Ignore.
    }
    if (playClose) {
        playWatch(p, dial.mode === "code" ? "settings_trigger_close" : "close_trigger");
        actionbar(p, " ");
    }
}

/** Use / jump: slam the core down (dial) or move to the next digit (code). @param {Player} p */
export function confirmWorldDial(p) {
    const dial = dials.get(p.id);
    if (!dial || dial.closing) return;
    if (dial.mode === "code") {
        dial.pos = (dial.pos + 1) % 6;
        dial.idle = 0;
        sound(p, "alienevo.prototype_cycle_2", 0.6);
        show(p, dial);
        return;
    }
    dial.closing = true;
    const alien = dial.list[dial.index];
    setSelected(p, alien.id);
    sound(p, "alienevo.prototype_cycle_2");
    playWatch(p, "close_trigger");
    system.runTimeout(() => {
        if (!p.isValid) return;
        closeWorldDial(p, false);
        if (getRecharge(p) > 0 || getAlien(p)) return;
        transform(p, alien);
    }, 8);
}

/** @param {Dial} dial */
function removeHolo(dial) {
    try {
        if (dial.holo?.isValid) dial.holo.remove();
    } catch {
        // Already gone.
    }
    dial.holo = undefined;
}

/** In front of the eyes, above the raised watch. @param {Player} p @param {number} t */
function holoPos(p, t) {
    const eye = p.getHeadLocation();
    const yaw = (p.getRotation().y * Math.PI) / 180;
    const fx = -Math.sin(yaw), fz = Math.cos(yaw);
    return { x: eye.x + fx * 1.6, y: eye.y - 0.5 + Math.sin(t / 8) * 0.04, z: eye.z + fz * 1.6 };
}

/** @param {Player} p @param {Dial} dial */
function show(p, dial) {
    if (dial.mode === "code") {
        // Same display as the Java mod: "0 0 §e0§r 0 0 0".
        const digits = dial.digits.map((d, i) => (i === dial.pos ? `§e${d}§r` : `${d}`)).join(" ");
        actionbar(p, `${digits}\n§7Turn: digit  Jump/Use: next  Sneak: close`);
        return;
    }
    const alien = dial.list[dial.index];
    const prev = dial.list[(dial.index - 1 + dial.list.length) % dial.list.length];
    const next = dial.list[(dial.index + 1) % dial.list.length];
    // Alien strip (icon glyphs, font/glyph_E1.png) like the selection wheel.
    const n = dial.list.length;
    const at = (/** @type {number} */ k) => glyph(dial.list[(dial.index + k + n * 3) % n].key);
    const strip = n >= 5 ? `§8${at(-2)} §7${at(-1)}  §f${at(0)}  §7${at(1)} §8${at(2)}` : dial.list.map((a, i) => (i === dial.index ? `§f${glyph(a.key)}` : `§8${glyph(a.key)}`)).join(" ");
    try {
        p.onScreenDisplay.setTitle(strip, { subtitle: `${alien.color}${alien.name}`, fadeInDuration: 0, stayDuration: 200, fadeOutDuration: 4 });
    } catch {
        // Player left.
    }
    actionbar(p, `§8${prev.name} §7◄  ${alien.color}§l${alien.name}§r  §7► §8${next.name}\n§7Turn: spin  §a● Use/Jump: transform  §7Sneak: close`);
    showOnDial(p, alien.key);
    const i = HOLO_KEYS.indexOf(alien.key);
    try {
        if (dial.holo?.isValid && i >= 0) dial.holo.setProperty("alienevo:alien", i);
    } catch {
        // Ignore.
    }
}

/** @param {Player} p @param {Dial} dial @param {number} dir */
function step(p, dial, dir) {
    if (dial.closing) return;
    dial.idle = 0;
    if (dial.mode === "code") {
        dial.digits[dial.pos] = (dial.digits[dial.pos] + dir + 10) % 10;
        playWatch(p, dir < 0 ? "code_left" : "code_right");
        sound(p, "alienevo.prototype_cycle_1");
        if (checkCode(p, dial.digits.join(""))) {
            dial.digits = [0, 0, 0, 0, 0, 0];
            dial.pos = 0;
            dial.closing = true;
            system.runTimeout(() => p.isValid && closeWorldDial(p, false), 40);
            return;
        }
        show(p, dial);
        return;
    }
    if (dial.list.length < 2) return;
    dial.index = (dial.index + dir + dial.list.length) % dial.list.length;
    playWatch(p, dir < 0 ? "spinl_trigger" : "spinr_trigger");
    sound(p, wearsRecal(p) ? "alienevo.recal_cycle" : "alienevo.prototype_cycle_1");
    show(p, dial);
}

export function initWorldDial() {
    system.runInterval(() => {
        for (const [id, dial] of dials) {
            const p = /** @type {Player | undefined} */ (world.getEntity(id));
            if (!p || !p.isValid) {
                removeHolo(dial);
                dials.delete(id);
                continue;
            }
            if ((dial.mode === "dial" && getAlien(p)) || ++dial.idle > IDLE_TICKS) {
                closeWorldDial(p);
                continue;
            }
            // Turning the view turns the dial.
            const yaw = p.getRotation().y;
            let delta = yaw - dial.yaw;
            if (delta > 180) delta -= 360;
            if (delta < -180) delta += 360;
            if (Math.abs(delta) >= STEP) {
                dial.yaw += Math.sign(delta) * STEP;
                step(p, dial, delta > 0 ? 1 : -1);
            }
            // Left / right buttons (when the device still reports them).
            const mx = p.inputInfo.getMovementVector().x;
            const dir = mx > 0.5 ? -1 : mx < -0.5 ? 1 : 0;
            if (dir && dir !== dial.moveX) step(p, dial, dir);
            dial.moveX = dir;
            if (dial.mode === "code") {
                if (system.currentTick % 20 === 0 && !dial.closing) show(p, dial);
                continue;
            }

            dial.spin = (dial.spin + 4) % 360;
            if (!dial.holo?.isValid) {
                try {
                    dial.holo = p.dimension.spawnEntity(HOLOGRAM, holoPos(p, dial.idle));
                    show(p, dial);
                } catch {
                    continue;
                }
            }
            try {
                dial.holo?.teleport(holoPos(p, system.currentTick), { rotation: { x: 0, y: dial.spin } });
            } catch {
                // Ignore.
            }
        }
    }, 1);

    world.afterEvents.playerButtonInput.subscribe((ev) => {
        if (ev.newButtonState !== "Pressed" || !dials.has(ev.player.id)) return;
        if (ev.button === "Jump") confirmWorldDial(ev.player);
    });

    world.afterEvents.playerLeave.subscribe((ev) => {
        const dial = dials.get(ev.playerId);
        if (dial) removeHolo(dial);
        dials.delete(ev.playerId);
    });

    // Movement is locked while the watch is up; never leave it locked.
    world.afterEvents.playerSpawn.subscribe((ev) => watchView(ev.player, false));

    // Stray holograms (server stopped while a dial was open).
    system.runInterval(() => {
        const live = new Set([...dials.values()].map((d) => d.holo?.id));
        for (const dim of ["overworld", "nether", "the_end"]) {
            try {
                for (const e of world.getDimension(dim).getEntities({ type: HOLOGRAM })) {
                    if (!live.has(e.id)) e.remove();
                }
            } catch {
                // Ignore.
            }
        }
    }, 100);
}
