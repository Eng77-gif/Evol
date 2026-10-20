// In-world Omnitrix dial, like the show and the Java mod: the watch opens, a
// hologram of the selected alien rises from the core and the dial is turned
// to cycle aliens, then the core is slammed down to transform.
//
// Controls: turn your view (or press left/right) to spin the dial, use the
// Omnitrix again or jump to transform, sneak to close.

import { InputPermissionCategory, system, world } from "@minecraft/server";
import { HOLO_KEYS } from "./holo_data.js";
import { playWatch, selectionList, transform } from "./omnitrix.js";
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
 * @typedef {{ list: Alien[], index: number, yaw: number, holo?: Entity, spin: number,
 *             idle: number, moveX: number, closing: boolean }} Dial
 */
/** @type {Map<string, Dial>} */
const dials = new Map();

/** @param {Player} p */
export const isDialOpen = (p) => dials.has(p.id);

/** @param {Player} p @param {number} tier */
export function openWorldDial(p, tier) {
    const list = selectionList(p, tier);
    if (!list.length) {
        actionbar(p, "§cNo alien DNA available.");
        return;
    }
    closeWorldDial(p, false);
    const index = Math.max(0, list.findIndex((a) => a.id === getSelected(p)));
    /** @type {Dial} */
    const dial = { list, index, yaw: p.getRotation().y, spin: 0, idle: 0, moveX: 0, closing: false };
    dials.set(p.id, dial);
    try {
        p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, false);
    } catch {
        // Ignore.
    }
    sound(p, "alienevo.prototype_activate");
    playWatch(p, "open_trigger");
    try {
        dial.holo = p.dimension.spawnEntity(HOLOGRAM, holoPos(p, 0));
    } catch {
        dial.holo = undefined;
    }
    show(p, dial);
}

/** @param {Player} p @param {boolean} [playClose] */
export function closeWorldDial(p, playClose = true) {
    const dial = dials.get(p.id);
    if (!dial) return;
    dials.delete(p.id);
    removeHolo(dial);
    try {
        p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, true);
    } catch {
        // Player left.
    }
    if (playClose && p.isValid) {
        playWatch(p, "close_trigger");
        actionbar(p, " ");
    }
}

/** Slam the core down: transform into the alien on the dial. @param {Player} p */
export function confirmWorldDial(p) {
    const dial = dials.get(p.id);
    if (!dial || dial.closing) return;
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

/** In front of the eyes, a bit low, where the wrist is in first person. @param {Player} p @param {number} t */
function holoPos(p, t) {
    const eye = p.getHeadLocation();
    const yaw = (p.getRotation().y * Math.PI) / 180;
    const fx = -Math.sin(yaw), fz = Math.cos(yaw);
    return { x: eye.x + fx * 1.5, y: eye.y - 0.75 + Math.sin(t / 8) * 0.04, z: eye.z + fz * 1.5 };
}

/** @param {Player} p @param {Dial} dial */
function show(p, dial) {
    const alien = dial.list[dial.index];
    const prev = dial.list[(dial.index - 1 + dial.list.length) % dial.list.length];
    const next = dial.list[(dial.index + 1) % dial.list.length];
    actionbar(p, `§8${prev.name} §7◄  ${alien.color}§l${alien.name}§r  §7► §8${next.name}\n§7Turn: spin  §a● Use/Jump: transform  §7Sneak: close`);
    const i = HOLO_KEYS.indexOf(alien.key);
    try {
        if (dial.holo?.isValid && i >= 0) dial.holo.setProperty("alienevo:alien", i);
    } catch {
        // Ignore.
    }
}

/** @param {Player} p @param {Dial} dial @param {number} dir */
function step(p, dial, dir) {
    if (dial.closing || dial.list.length < 2) return;
    dial.index = (dial.index + dir + dial.list.length) % dial.list.length;
    dial.idle = 0;
    playWatch(p, dir < 0 ? "spinl_trigger" : "spinr_trigger");
    sound(p, "alienevo.prototype_cycle_1");
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
            if (getAlien(p) || ++dial.idle > IDLE_TICKS) {
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

    // Movement is locked while the dial is open; never leave it locked.
    world.afterEvents.playerSpawn.subscribe((ev) => {
        try {
            ev.player.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, true);
        } catch {
            // Ignore.
        }
    });

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
