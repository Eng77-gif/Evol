import { system, world } from "@minecraft/server";

/** @typedef {import("@minecraft/server").Vector3} Vector3 */
/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Entity} Entity */

/** @param {Vector3} a @param {Vector3} b */
export const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
/** @param {Vector3} a @param {Vector3} b */
export const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
/** @param {Vector3} a @param {number} s */
export const scale = (a, s) => ({ x: a.x * s, y: a.y * s, z: a.z * s });
/** @param {Vector3} a */
export const length = (a) => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
/** @param {Vector3} a */
export const normalize = (a) => {
    const l = length(a) || 1;
    return scale(a, 1 / l);
};
/** @param {Vector3} a @param {Vector3} b */
export const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
/** @param {Vector3} a @param {Vector3} b */
export const distance = (a, b) => length(sub(a, b));

/** Horizontal look direction of a player. @param {Entity} p */
export function flatView(p) {
    const v = p.getViewDirection();
    const l = Math.sqrt(v.x * v.x + v.z * v.z) || 1;
    return { x: v.x / l, y: 0, z: v.z / l };
}

/** Rotate a direction around the Y axis. @param {Vector3} v @param {number} deg */
export function rotateY(v, deg) {
    const r = (deg * Math.PI) / 180;
    const c = Math.cos(r), s = Math.sin(r);
    return { x: v.x * c - v.z * s, y: v.y, z: v.x * s + v.z * c };
}

/** @param {Entity} e @param {string} particle @param {Vector3} [loc] */
export function particle(e, particle, loc) {
    try {
        e.dimension.spawnParticle(particle, loc ?? e.location);
    } catch {
        // Unloaded chunk or unknown particle.
    }
}

/** @param {Entity} e @param {string} sound @param {number} [volume] @param {number} [pitch] */
export function sound(e, sound, volume = 1, pitch = 1) {
    try {
        e.dimension.playSound(sound, e.location, { volume, pitch });
    } catch {
        // Ignore.
    }
}

/** @param {Player} p @param {string} msg */
export function actionbar(p, msg) {
    try {
        p.onScreenDisplay.setActionBar(msg);
    } catch {
        // Player left.
    }
}

/**
 * Sets the velocity of a player (applyImpulse does not work on players).
 * @param {Entity} e @param {Vector3} v
 */
export function launch(e, v) {
    try {
        if (e.typeId === "minecraft:player") {
            e.applyKnockback({ x: v.x, z: v.z }, v.y);
        } else {
            e.clearVelocity();
            e.applyImpulse(v);
        }
    } catch {
        // Entity may be gone.
    }
}

/**
 * Hostile-to-attacker check used by every area ability.
 * @param {Entity} source @param {Entity} target
 */
export function canHit(source, target) {
    if (!target.isValid || target.id === source.id) return false;
    const t = target.typeId;
    if (t === "minecraft:item" || t === "minecraft:xp_orb" || t === "minecraft:armor_stand" ||
        t === "minecraft:painting" || t.startsWith("alienevo:")) return false;
    if (t === "minecraft:player") {
        if (!world.gameRules.pvp) return false;
        /** @type {Player} */ (target);
        try {
            if (/** @type {Player} */ (target).getGameMode() === "Creative") return false;
        } catch {
            return false;
        }
    }
    try {
        if (!target.getComponent("minecraft:health")) return false;
    } catch {
        return false;
    }
    return true;
}

/**
 * Entities around a point that the source may damage.
 * @param {Entity} source @param {Vector3} center @param {number} radius
 */
export function nearbyTargets(source, center, radius) {
    try {
        return source.dimension
            .getEntities({ location: center, maxDistance: radius, excludeFamilies: ["inanimate"] })
            .filter((e) => canHit(source, e));
    } catch {
        return [];
    }
}

/**
 * Entities in a cone in front of the source.
 * @param {Entity} source @param {number} range @param {number} minDot cos of the half angle
 */
export function coneTargets(source, range, minDot = 0.6) {
    const eye = source.getHeadLocation();
    const view = source.getViewDirection();
    return nearbyTargets(source, eye, range).filter((e) => {
        const to = sub(add(e.location, { x: 0, y: 0.9, z: 0 }), eye);
        const d = length(to);
        return d < 0.5 || dot(scale(to, 1 / d), view) >= minDot;
    });
}

/**
 * @param {Entity} target @param {number} amount @param {Entity} source
 * @param {string} [cause] an EntityDamageCause value
 */
export function hurt(target, amount, source, cause) {
    try {
        target.applyDamage(amount, { cause: /** @type {any} */ (cause ?? "entityAttack"), damagingEntity: source });
    } catch {
        // Target died or became invalid.
    }
}

/** @param {Entity} target @param {string} effect @param {number} ticks @param {number} [amp] */
export function effect(target, effect, ticks, amp = 0) {
    try {
        target.addEffect(effect, ticks, { amplifier: amp, showParticles: true });
    } catch {
        // Ignore.
    }
}

/** Knock an entity away from a point. @param {Entity} e @param {Vector3} from @param {number} h @param {number} v */
export function knockFrom(e, from, h, v) {
    const d = sub(e.location, from);
    const l = Math.sqrt(d.x * d.x + d.z * d.z) || 1;
    try {
        e.applyKnockback({ x: (d.x / l) * h, z: (d.z / l) * h }, v);
    } catch {
        // Some entities cannot be knocked back.
    }
}

/**
 * Draws particles along a line, returns the end point (first solid block).
 * @param {Entity} source @param {number} range @param {string} particleId
 */
export function beam(source, range, particleId) {
    const eye = source.getHeadLocation();
    const view = source.getViewDirection();
    let end = add(eye, scale(view, range));
    try {
        const hit = source.dimension.getBlockFromRay(eye, view, { maxDistance: range, includePassableBlocks: false });
        if (hit) end = add(hit.block.location, hit.faceLocation);
    } catch {
        // Ray left the world.
    }
    const dist = distance(eye, end);
    for (let d = 1; d < dist; d += 0.5) {
        particle(source, particleId, add(eye, scale(view, d)));
    }
    /** @type {Entity[]} */
    let targets = [];
    try {
        targets = source
            .getEntitiesFromViewDirection({ maxDistance: dist })
            .map((h) => h.entity)
            .filter((e) => canHit(source, e));
    } catch {
        // Ignore.
    }
    return { end, targets };
}

/** @param {number} ticks */
export function wait(ticks) {
    return new Promise((resolve) => system.runTimeout(() => resolve(undefined), ticks));
}

/** @param {number} ticks */
export function formatTime(ticks) {
    const s = Math.max(0, Math.ceil(ticks / 20));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
