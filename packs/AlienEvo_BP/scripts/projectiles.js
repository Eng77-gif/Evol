// Projectiles fired by abilities.  Each projectile remembers what it does on
// impact; vanilla projectiles (fireballs, arrows) keep their own behaviour and
// only get the extra effects.

import { system, world } from "@minecraft/server";
import { add, effect, hurt, knockFrom, nearbyTargets, particle, scale } from "./util.js";

/** @typedef {import("@minecraft/server").Entity} Entity */
/** @typedef {import("@minecraft/server").Player} Player */

/**
 * @typedef {{
 *   owner: Player, damage: number, trail?: string, impact?: string,
 *   effects?: [string, number, number][], fire?: number, radius?: number,
 *   knockback?: number, freeze?: boolean, ticks: number
 * }} Shot
 */

/** @type {Map<string, Shot>} */
const shots = new Map();

/**
 * @param {Player} owner
 * @param {string} type entity id of the projectile
 * @param {number} speed blocks per tick
 * @param {Omit<Shot, "owner" | "ticks"> & { spread?: number, offset?: number }} opts
 */
export function shoot(owner, type, speed, opts) {
    const view = owner.getViewDirection();
    const yaw = (opts.offset ?? 0) * (Math.PI / 180);
    const dir = {
        x: view.x * Math.cos(yaw) - view.z * Math.sin(yaw),
        y: view.y,
        z: view.x * Math.sin(yaw) + view.z * Math.cos(yaw),
    };
    const spawn = add(owner.getHeadLocation(), scale(dir, 1.2));
    let proj;
    try {
        proj = owner.dimension.spawnEntity(type, spawn);
    } catch {
        return undefined;
    }
    const comp = proj.getComponent("minecraft:projectile");
    if (comp) {
        comp.owner = owner;
        comp.shoot(scale(dir, speed), { uncertainty: opts.spread ?? 0 });
    } else {
        try {
            proj.applyImpulse(scale(dir, speed));
        } catch {
            // Ignore.
        }
    }
    shots.set(proj.id, { ...opts, owner, ticks: 0 });
    return proj;
}

/** @param {Shot} shot @param {import("@minecraft/server").Dimension} dim @param {import("@minecraft/server").Vector3} loc */
function impact(shot, dim, loc) {
    if (shot.impact) {
        try {
            dim.spawnParticle(shot.impact, loc);
        } catch {
            // Ignore.
        }
    }
    if (shot.radius && shot.owner.isValid) {
        for (const e of nearbyTargets(shot.owner, loc, shot.radius)) {
            apply(shot, e, loc);
        }
    }
}

/** @param {Shot} shot @param {Entity} target @param {import("@minecraft/server").Vector3} from */
function apply(shot, target, from) {
    if (!shot.owner.isValid || target.id === shot.owner.id) return;
    if (shot.damage) hurt(target, shot.damage, shot.owner, "projectile");
    for (const [id, ticks, amp] of shot.effects ?? []) effect(target, id, ticks, amp);
    if (shot.fire) {
        try {
            target.setOnFire(shot.fire, true);
        } catch {
            // Ignore.
        }
    }
    if (shot.knockback) knockFrom(target, from, shot.knockback, 0.35);
    if (shot.freeze) particle(target, "minecraft:snowflake_particle", target.location);
}

export function initProjectiles() {
    world.afterEvents.projectileHitEntity.subscribe((ev) => {
        const shot = shots.get(ev.projectile.id);
        if (!shot) return;
        shots.delete(ev.projectile.id);
        const hit = ev.getEntityHit().entity;
        if (hit) apply(shot, hit, ev.location);
        impact(shot, ev.dimension, ev.location);
    });

    world.afterEvents.projectileHitBlock.subscribe((ev) => {
        const shot = shots.get(ev.projectile.id);
        if (!shot) return;
        shots.delete(ev.projectile.id);
        impact(shot, ev.dimension, ev.location);
        if (shot.freeze) {
            const b = ev.getBlockHit().block;
            try {
                const above = b.above();
                if (b.typeId === "minecraft:water") b.setType("minecraft:frosted_ice");
                else if (above?.isAir) above.setType("minecraft:snow_layer");
            } catch {
                // Ignore.
            }
        }
    });

    // Particle trails for the (invisible) energy bolts.
    system.runInterval(() => {
        for (const [id, shot] of shots) {
            shot.ticks++;
            const e = world.getEntity(id);
            if (!e || !e.isValid || shot.ticks > 200) {
                shots.delete(id);
                continue;
            }
            if (shot.trail) particle(e, shot.trail, e.location);
        }
    }, 1);
}
