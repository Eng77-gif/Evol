// Alien abilities.  The Java mod drives these with Palladium abilities bound to
// keys; here the selected ability is cast by using the Omnitrix while
// transformed (sneak + use opens the ability menu).

import { BlockPermutation, system } from "@minecraft/server";
import { shoot } from "./projectiles.js";
import { getEnergy, setEnergy } from "./state.js";
import {
    add, beam, coneTargets, effect, flatView, hurt, knockFrom, launch, nearbyTargets,
    normalize, particle, rotateY, scale, sound,
} from "./util.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Vector3} Vector3 */
/** @typedef {{ name: string, desc: string, cooldown: number, run: (p: Player) => void | boolean }} Ability */

/** Toggle states that last while transformed. */
export const toggles = {
    /** @type {Set<string>} */ rolling: new Set(),
    /** @type {Map<string, number>} */ speedGear: new Map(),
    /** @type {Set<string>} */ fireShield: new Set(),
    /** @type {Map<string, { dmg: number, at: number }>} */ slamOnLand: new Map(),
};

/** @param {Player} p */
export function clearToggles(p) {
    toggles.rolling.delete(p.id);
    toggles.speedGear.delete(p.id);
    toggles.fireShield.delete(p.id);
    toggles.slamOnLand.delete(p.id);
}

const FIRE = "alienevo:pyronite_flame";

/** Flame/ice/sonic cone. @param {Player} p @param {string} particleId @param {(e: import("@minecraft/server").Entity) => void} hit */
function breath(p, particleId, hit, range = 7, pulses = 8) {
    let n = 0;
    const id = system.runInterval(() => {
        if (!p.isValid || n++ >= pulses) {
            system.clearRun(id);
            return;
        }
        const eye = p.getHeadLocation();
        const view = p.getViewDirection();
        for (let d = 1; d <= range; d += 1) {
            for (let k = 0; k < 2; k++) {
                const jitter = { x: (Math.random() - 0.5) * d * 0.3, y: (Math.random() - 0.5) * d * 0.3, z: (Math.random() - 0.5) * d * 0.3 };
                particle(p, particleId, add(add(eye, scale(view, d)), jitter));
            }
        }
        if (n % 2 === 0) for (const e of coneTargets(p, range, 0.75)) hit(e);
    }, 2);
}

/**
 * Damage + knock away everything around the player.
 * @param {Player} p @param {number} radius @param {number} damage @param {number} up
 */
function slam(p, radius, damage, up, particleId = "minecraft:huge_explosion_emitter") {
    particle(p, particleId, p.location);
    for (let a = 0; a < 360; a += 30) {
        const r = rotateY({ x: radius * 0.7, y: 0, z: 0 }, a);
        particle(p, "minecraft:large_explosion", add(p.location, r));
    }
    sound(p, "random.explode", 0.8, 0.7);
    for (const e of nearbyTargets(p, p.location, radius)) {
        hurt(e, damage, p);
        knockFrom(e, p.location, 1.2, up);
    }
}

/** Temporary blocks that revert after a while. @param {Player} p @param {Vector3} loc @param {string} type @param {number} ticks */
function tempBlock(p, loc, type, ticks) {
    try {
        const b = p.dimension.getBlock(loc);
        if (!b || !(b.isAir || b.typeId === "minecraft:short_grass" || b.typeId === "minecraft:snow_layer")) return;
        const old = b.permutation;
        b.setType(type);
        system.runTimeout(() => {
            try {
                if (b.isValid && b.typeId === type) b.setPermutation(old);
            } catch {
                // Chunk unloaded.
            }
        }, ticks);
    } catch {
        // Ignore.
    }
}

/** @type {Record<string, string>} */
const ORES = {
    "minecraft:coal_ore": "§8Coal", "minecraft:deepslate_coal_ore": "§8Coal",
    "minecraft:iron_ore": "§7Iron", "minecraft:deepslate_iron_ore": "§7Iron",
    "minecraft:copper_ore": "§6Copper", "minecraft:deepslate_copper_ore": "§6Copper",
    "minecraft:gold_ore": "§eGold", "minecraft:deepslate_gold_ore": "§eGold", "minecraft:nether_gold_ore": "§eGold",
    "minecraft:redstone_ore": "§cRedstone", "minecraft:deepslate_redstone_ore": "§cRedstone",
    "minecraft:lapis_ore": "§9Lapis", "minecraft:deepslate_lapis_ore": "§9Lapis",
    "minecraft:diamond_ore": "§bDiamond", "minecraft:deepslate_diamond_ore": "§bDiamond",
    "minecraft:emerald_ore": "§aEmerald", "minecraft:deepslate_emerald_ore": "§aEmerald",
    "minecraft:ancient_debris": "§4Ancient Debris", "minecraft:quartz_ore": "§fQuartz",
};

/** @type {Record<string, Ability>} */
export const ABILITIES = {
    // ---------------------------------------------------------------- fire
    fireball: {
        name: "Fireball", desc: "Throw a ball of fire.", cooldown: 10,
        run: (p) => {
            shoot(p, "minecraft:small_fireball", 1.6, { damage: 3, fire: 4, trail: "alienevo:pyronite_ball" });
            sound(p, "alienevo.heatblast_fireshot");
        },
    },
    fire_blast: {
        name: "Fire Blast", desc: "Launch a large explosive fireball.", cooldown: 80,
        run: (p) => {
            shoot(p, "minecraft:fireball", 1.2, { damage: 6, fire: 6 });
            sound(p, "alienevo.heatblast_fireball");
        },
    },
    flame_breath: {
        name: "Flame Breath", desc: "Breathe a cone of fire.", cooldown: 60,
        run: (p) => {
            sound(p, "alienevo.heatblast_firebreath_start");
            breath(p, FIRE, (e) => {
                hurt(e, 3, p, "fire");
                try {
                    e.setOnFire(5, true);
                } catch {
                    // Ignore.
                }
            });
        },
    },
    pyro_jump: {
        name: "Pyro Jump", desc: "Rocket upward on a burst of flame.", cooldown: 40,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 1.2, y: 1.3, z: v.z * 1.2 });
            for (let i = 0; i < 8; i++) particle(p, "alienevo:pyronite_flares", add(p.location, { x: Math.random() - 0.5, y: 0, z: Math.random() - 0.5 }));
            sound(p, "alienevo.heatblast_surf");
        },
    },
    fireball_barrage: {
        name: "Fireball Barrage", desc: "Fire a spread of fireballs.", cooldown: 40,
        run: (p) => {
            for (const off of [-12, -6, 0, 6, 12]) shoot(p, "minecraft:small_fireball", 1.5, { damage: 4, fire: 4, offset: off });
            sound(p, "alienevo.heatblast_fireball");
        },
    },
    fire_shield: {
        name: "Fire Shield", desc: "Toggle a ring of fire that burns nearby enemies.", cooldown: 20,
        run: (p) => {
            if (toggles.fireShield.has(p.id)) toggles.fireShield.delete(p.id);
            else toggles.fireShield.add(p.id);
            p.sendMessage(toggles.fireShield.has(p.id) ? "§6Fire Shield: ON" : "§7Fire Shield: OFF");
        },
    },

    // ---------------------------------------------------------------- wildmutt
    pounce: {
        name: "Pounce", desc: "Leap at your prey.", cooldown: 30,
        run: (p) => {
            const v = p.getViewDirection();
            launch(p, { x: v.x * 2.2, y: Math.max(0.5, v.y + 0.6), z: v.z * 2.2 });
            toggles.slamOnLand.set(p.id, { dmg: 6, at: system.currentTick });
        },
    },
    quill_barrage: {
        name: "Quill Barrage", desc: "Fire a spread of sharp quills.", cooldown: 60,
        run: (p) => {
            for (const off of [-15, -7, 0, 7, 15]) shoot(p, "minecraft:arrow", 2.2, { damage: 2, offset: off, spread: 2 });
            sound(p, "alienevo.quill_shot");
        },
    },
    bite: {
        name: "Bite", desc: "Lunge forward and bite.", cooldown: 20,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 1.4, y: 0.2, z: v.z * 1.4 });
            sound(p, "alienevo.bite");
            system.runTimeout(() => {
                if (!p.isValid) return;
                for (const e of coneTargets(p, 3.5, 0.5)) hurt(e, 8, p);
            }, 4);
        },
    },
    predator_sense: {
        name: "Predator Sense", desc: "Smell every creature around you.", cooldown: 100,
        run: (p) => {
            const list = nearbyTargets(p, p.location, 32);
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ > 10) return system.clearRun(id);
                for (const e of list) if (e.isValid) particle(e, "minecraft:villager_angry", add(e.location, { x: 0, y: 2.2, z: 0 }));
            }, 10);
            p.sendMessage(`§6You sense §e${list.length}§6 creatures nearby.`);
        },
    },

    // ---------------------------------------------------------------- diamondhead
    crystal_shards: {
        name: "Crystal Shards", desc: "Fire razor sharp Taydenite shards.", cooldown: 20,
        run: (p) => {
            for (const off of [-5, 0, 5]) shoot(p, "minecraft:arrow", 2.6, { damage: 4, offset: off, spread: 1, impact: "minecraft:critical_hit_emitter" });
            sound(p, "alienevo.diamond_blade");
        },
    },
    crystal_wave: {
        name: "Crystal Wave", desc: "Raise a line of crystal spikes.", cooldown: 80,
        run: (p) => {
            const v = flatView(p);
            for (let i = 1; i <= 10; i++) {
                system.runTimeout(() => {
                    if (!p.isValid) return;
                    const at = add(p.location, scale(v, i + 1));
                    const loc = { x: Math.floor(at.x), y: Math.floor(p.location.y), z: Math.floor(at.z) };
                    tempBlock(p, loc, "minecraft:amethyst_cluster", 100);
                    particle(p, "minecraft:critical_hit_emitter", { x: loc.x + 0.5, y: loc.y + 0.5, z: loc.z + 0.5 });
                    for (const e of nearbyTargets(p, { x: loc.x + 0.5, y: loc.y, z: loc.z + 0.5 }, 1.6)) {
                        hurt(e, 7, p);
                        launch(e, { x: 0, y: 0.7, z: 0 });
                    }
                }, i * 2);
            }
            sound(p, "break.amethyst_cluster", 1, 0.6);
        },
    },
    crystal_shield: {
        name: "Crystal Shield", desc: "Harden into an almost unbreakable shield.", cooldown: 240,
        run: (p) => {
            effect(p, "resistance", 100, 3);
            effect(p, "slowness", 100, 2);
            sound(p, "alienevo.diamond_blade_sheathe");
        },
    },

    // ---------------------------------------------------------------- xlr8
    speed_gear: {
        name: "Speed Gear", desc: "Shift between speed gears 1-5.", cooldown: 5,
        run: (p) => {
            const g = ((toggles.speedGear.get(p.id) ?? 1) % 5) + 1;
            toggles.speedGear.set(p.id, g);
            effect(p, "speed", 20000000, g * 2 - 1);
            p.sendMessage(`§3Speed gear: §b${g}`);
        },
    },
    dash: {
        name: "Dash", desc: "Burst forward at supersonic speed.", cooldown: 20,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 3.2, y: 0.15, z: v.z * 3.2 });
            for (let i = 0; i < 6; i++) particle(p, "minecraft:knockback_roar_particle", add(p.location, scale(v, -i)));
        },
    },
    tornado: {
        name: "Tornado", desc: "Run in circles to create a tornado.", cooldown: 100,
        run: (p) => {
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ > 30) return system.clearRun(id);
                for (let a = 0; a < 360; a += 45) particle(p, "minecraft:knockback_roar_particle", add(p.location, rotateY({ x: 2.5, y: n * 0.1, z: 0 }, a + n * 30)));
                if (n % 5 === 0) for (const e of nearbyTargets(p, p.location, 5)) {
                    hurt(e, 2, p);
                    launch(e, { x: 0, y: 0.6, z: 0 });
                }
            }, 2);
        },
    },

    // ---------------------------------------------------------------- grey matter
    galvan_leap: {
        name: "Galvan Leap", desc: "Jump many times your own height.", cooldown: 20,
        run: (p) => {
            const v = p.getViewDirection();
            launch(p, { x: v.x * 1.5, y: 1.1, z: v.z * 1.5 });
        },
    },
    ore_scan: {
        name: "Analyse", desc: "Calculate where nearby ores are hidden.", cooldown: 200,
        run: (p) => {
            /** @type {Map<string, number>} */
            const found = new Map();
            const base = p.location;
            const r = 8;
            for (let x = -r; x <= r; x++) for (let y = -r; y <= r; y++) for (let z = -r; z <= r; z++) {
                let b;
                try {
                    b = p.dimension.getBlock({ x: base.x + x, y: base.y + y, z: base.z + z });
                } catch {
                    continue;
                }
                if (!b) continue;
                const name = ORES[b.typeId];
                if (!name) continue;
                found.set(name, (found.get(name) ?? 0) + 1);
                particle(p, "minecraft:villager_happy", { x: b.location.x + 0.5, y: b.location.y + 0.5, z: b.location.z + 0.5 });
            }
            const lines = [...found].map(([k, v]) => `${k}§7: §f${v}`);
            p.sendMessage(lines.length ? `§aOres within ${r} blocks:\n` + lines.join("\n") : "§7No ores nearby.");
        },
    },
    tinker: {
        name: "Tinker", desc: "Repair the item in your other hand.", cooldown: 600,
        run: (p) => {
            const eq = p.getComponent("minecraft:equippable");
            const item = eq?.getEquipment(/** @type {any} */ ("Offhand"));
            const dur = item?.getComponent("minecraft:durability");
            if (!item || !dur) {
                p.sendMessage("§7Hold a damaged item in your offhand.");
                return false;
            }
            dur.damage = Math.max(0, dur.damage - Math.ceil(dur.maxDurability / 4));
            eq?.setEquipment(/** @type {any} */ ("Offhand"), item);
            sound(p, "random.anvil_use", 0.6, 1.6);
        },
    },

    // ---------------------------------------------------------------- four arms
    ground_slam: {
        name: "Ground Slam", desc: "Smash the ground with all four fists.", cooldown: 60,
        run: (p) => slam(p, 5, 8, 0.7),
    },
    boulder_throw: {
        name: "Boulder Throw", desc: "Rip up a boulder and throw it.", cooldown: 60,
        run: (p) => {
            shoot(p, "alienevo:boulder", 1.4, { damage: 10, radius: 2.5, knockback: 1.2, impact: "minecraft:huge_explosion_emitter" });
            sound(p, "dig.stone", 1, 0.6);
        },
    },
    sonic_clap: {
        name: "Sonic Clap", desc: "Clap all four hands to make a shockwave.", cooldown: 80,
        run: (p) => {
            particle(p, "alienevo:sonic_boom", add(p.getHeadLocation(), scale(p.getViewDirection(), 2)));
            sound(p, "alienevo.sonic_boom");
            for (const e of coneTargets(p, 10, 0.6)) {
                hurt(e, 6, p);
                knockFrom(e, p.location, 2.5, 0.5);
            }
        },
    },
    charge_leap: {
        name: "Charge Leap", desc: "Leap high and slam down on landing.", cooldown: 60,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 1.6, y: 1.4, z: v.z * 1.6 });
            toggles.slamOnLand.set(p.id, { dmg: 8, at: system.currentTick });
        },
    },

    // ---------------------------------------------------------------- stinkfly
    slime_shot: {
        name: "Slime Shot", desc: "Spit sticky slime that slows enemies.", cooldown: 15,
        run: (p) => {
            shoot(p, "alienevo:energy_bolt", 1.6, {
                damage: 3, trail: "alienevo:slime_trail", impact: "alienevo:slime",
                effects: [["slowness", 100, 3]],
            });
            sound(p, "mob.slime.small");
        },
    },
    toxic_gas: {
        name: "Toxic Gas", desc: "Release a cloud of toxic gas.", cooldown: 120,
        run: (p) => {
            const at = p.location;
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ > 10) return system.clearRun(id);
                for (let i = 0; i < 10; i++) particle(p, "alienevo:gas", add(at, { x: (Math.random() - 0.5) * 8, y: Math.random() * 2, z: (Math.random() - 0.5) * 8 }));
                for (const e of nearbyTargets(p, at, 4.5)) {
                    effect(e, "poison", 80, 1);
                    effect(e, "nausea", 120, 0);
                }
            }, 10);
            sound(p, "alienevo.stinkfly_rattle");
        },
    },
    insect_eyes: {
        name: "Insect Eyes", desc: "See clearly in the dark and spot creatures.", cooldown: 200,
        run: (p) => {
            effect(p, "night_vision", 1200, 0);
            for (const e of nearbyTargets(p, p.location, 24)) particle(e, "minecraft:villager_angry", add(e.location, { x: 0, y: 2.2, z: 0 }));
        },
    },

    // ---------------------------------------------------------------- ripjaws
    aqua_jet: {
        name: "Aqua Jet", desc: "Torpedo through the water.", cooldown: 30,
        run: (p) => {
            const v = p.getViewDirection();
            const mult = p.isInWater ? 3 : 1.2;
            launch(p, { x: v.x * mult, y: v.y * mult + 0.1, z: v.z * mult });
            for (let i = 0; i < 6; i++) particle(p, "minecraft:water_wake_particle", add(p.location, scale(v, -i)));
            system.runTimeout(() => {
                if (!p.isValid) return;
                for (const e of nearbyTargets(p, p.location, 3)) hurt(e, 7, p);
            }, 5);
        },
    },
    tidal_spin: {
        name: "Tidal Spin", desc: "Spin to create a whirlpool around you.", cooldown: 100,
        run: (p) => {
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ > 20) return system.clearRun(id);
                for (let a = 0; a < 360; a += 45) particle(p, "minecraft:water_wake_particle", add(p.location, rotateY({ x: 2, y: 0.5, z: 0 }, a + n * 25)));
                if (n % 4 === 0) for (const e of nearbyTargets(p, p.location, 4)) {
                    hurt(e, 3, p);
                    knockFrom(e, p.location, -0.4, 0.1);
                }
            }, 2);
        },
    },

    // ---------------------------------------------------------------- upgrade / astrobot
    energy_beam: {
        name: "Energy Beam", desc: "Fire a concentrated energy beam.", cooldown: 40,
        run: (p) => {
            const { targets } = beam(p, 32, "minecraft:villager_happy");
            for (const e of targets) hurt(e, 8, p, "magic");
            sound(p, "beacon.activate", 0.8, 2);
        },
    },
    liquid_form: {
        name: "Liquid Form", desc: "Melt into living metal and slip away.", cooldown: 200,
        run: (p) => {
            effect(p, "invisibility", 120, 0);
            effect(p, "resistance", 120, 4);
            effect(p, "speed", 120, 2);
        },
    },
    spike_hands: {
        name: "Spike Hands", desc: "Form spiked fists.", cooldown: 240,
        run: (p) => {
            effect(p, "strength", 300, 2);
            sound(p, "random.anvil_land", 0.5, 1.6);
        },
    },
    laser_jump: {
        name: "Laser Jump", desc: "Blast off with laser boots.", cooldown: 40,
        run: (p) => {
            for (const e of nearbyTargets(p, p.location, 3)) hurt(e, 5, p, "magic");
            particle(p, "minecraft:huge_explosion_emitter", p.location);
            launch(p, { x: 0, y: 1.6, z: 0 });
        },
    },
    rocket_punch: {
        name: "Rocket Punch", desc: "Rocket forward fist first.", cooldown: 30,
        run: (p) => {
            const v = p.getViewDirection();
            launch(p, { x: v.x * 2.5, y: v.y * 2 + 0.2, z: v.z * 2.5 });
            system.runTimeout(() => {
                if (!p.isValid) return;
                for (const e of nearbyTargets(p, p.location, 3)) {
                    hurt(e, 8, p);
                    knockFrom(e, p.location, 1.5, 0.4);
                }
            }, 5);
        },
    },

    // ---------------------------------------------------------------- ghostfreak / big chill
    phase: {
        name: "Intangibility", desc: "Turn invisible and intangible.", cooldown: 200,
        run: (p) => {
            effect(p, "invisibility", 160, 0);
            effect(p, "resistance", 160, 4);
            sound(p, "mob.vex.charge", 1, 0.6);
        },
    },
    shadow_strike: {
        name: "Shadow Strike", desc: "Dash through enemies and hurt them.", cooldown: 40,
        run: (p) => {
            const v = p.getViewDirection();
            launch(p, { x: v.x * 2.8, y: v.y * 1.5 + 0.1, z: v.z * 2.8 });
            effect(p, "resistance", 15, 4);
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ > 6) return system.clearRun(id);
                particle(p, "minecraft:soul_particle", p.location);
                for (const e of nearbyTargets(p, p.location, 2)) hurt(e, 3, p, "magic");
            }, 1);
        },
    },
    scare: {
        name: "Scare", desc: "Terrify everything around you.", cooldown: 120,
        run: (p) => {
            for (const e of nearbyTargets(p, p.location, 10)) {
                effect(e, "weakness", 200, 1);
                effect(e, "slowness", 200, 1);
                knockFrom(e, p.location, 1, 0.2);
            }
            sound(p, "mob.ghast.scream", 1, 0.6);
        },
    },
    freeze_breath: {
        name: "Freeze Breath", desc: "Breathe freezing mist.", cooldown: 60,
        run: (p) => {
            breath(p, "minecraft:snowflake_particle", (e) => {
                hurt(e, 3, p, "freezing");
                effect(e, "slowness", 120, 3);
            });
            // Freeze water in front of the player.
            const eye = p.getHeadLocation();
            const view = p.getViewDirection();
            for (let d = 1; d <= 7; d++) {
                const at = add(eye, scale(view, d));
                for (let dy = 0; dy >= -3; dy--) {
                    try {
                        const b = p.dimension.getBlock({ x: at.x, y: at.y + dy, z: at.z });
                        if (b?.typeId === "minecraft:water") b.setType("minecraft:frosted_ice");
                    } catch {
                        // Ignore.
                    }
                }
            }
        },
    },
    ice_shards: {
        name: "Ice Shards", desc: "Throw shards of ice.", cooldown: 20,
        run: (p) => {
            for (const off of [-4, 0, 4]) shoot(p, "alienevo:energy_bolt", 1.8, {
                damage: 3, offset: off, trail: "minecraft:snowflake_particle", freeze: true,
                effects: [["slowness", 80, 2]],
            });
            sound(p, "random.glass", 0.6, 1.4);
        },
    },

    // ---------------------------------------------------------------- cannonbolt
    roll: {
        name: "Roll", desc: "Curl into a ball and roll over enemies (toggle).", cooldown: 10,
        run: (p) => {
            if (toggles.rolling.has(p.id)) {
                toggles.rolling.delete(p.id);
                p.removeEffect("speed");
                p.sendMessage("§7Roll: OFF");
            } else {
                toggles.rolling.add(p.id);
                effect(p, "speed", 20000000, 3);
                sound(p, "alienevo.arburian_roll");
                p.sendMessage("§6Roll: ON");
            }
        },
    },
    roll_leap: {
        name: "Roll Leap", desc: "Bounce into the air.", cooldown: 40,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 2, y: 1.2, z: v.z * 2 });
            toggles.slamOnLand.set(p.id, { dmg: 6, at: system.currentTick });
        },
    },

    // ---------------------------------------------------------------- swampfire
    bloom: {
        name: "Bloom", desc: "Make plants grow around you.", cooldown: 100,
        run: (p) => {
            const r = 4;
            for (let x = -r; x <= r; x++) for (let z = -r; z <= r; z++) for (let y = -2; y <= 2; y++) {
                let b;
                try {
                    b = p.dimension.getBlock({ x: p.location.x + x, y: p.location.y + y, z: p.location.z + z });
                } catch {
                    continue;
                }
                if (!b) continue;
                const growth = b.permutation.getState("growth");
                if (typeof growth === "number") {
                    try {
                        b.setPermutation(b.permutation.withState("growth", 7));
                        particle(p, "minecraft:crop_growth_emitter", b.center());
                    } catch {
                        // Different max growth.
                    }
                } else if (b.typeId === "minecraft:grass_block" && Math.random() < 0.25) {
                    const above = b.above();
                    if (above?.isAir) {
                        above.setPermutation(BlockPermutation.resolve(Math.random() < 0.5 ? "minecraft:short_grass" : "minecraft:poppy"));
                        particle(p, "minecraft:crop_growth_emitter", above.center());
                    }
                }
            }
        },
    },
    vine_snare: {
        name: "Vine Snare", desc: "Entangle enemies in vines.", cooldown: 80,
        run: (p) => {
            for (const e of nearbyTargets(p, p.location, 7)) {
                effect(e, "slowness", 100, 5);
                hurt(e, 4, p);
                particle(e, "minecraft:villager_happy", e.location);
            }
        },
    },

    // ---------------------------------------------------------------- echo echo
    sonic_scream: {
        name: "Sonic Scream", desc: "Unleash a devastating scream.", cooldown: 40,
        run: (p) => {
            const eye = p.getHeadLocation();
            const v = p.getViewDirection();
            for (let d = 2; d <= 10; d += 2) particle(p, "alienevo:afomni_sonic_scream", add(eye, scale(v, d)));
            sound(p, "alienevo.sonorosian_scream");
            for (const e of coneTargets(p, 11, 0.7)) {
                hurt(e, 6, p, "sonicBoom");
                knockFrom(e, p.location, 1.8, 0.4);
            }
        },
    },
    sound_wall: {
        name: "Wall of Sound", desc: "Surround yourself with a wall of sound.", cooldown: 160,
        run: (p) => {
            effect(p, "resistance", 100, 2);
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ > 10) return system.clearRun(id);
                for (let a = 0; a < 360; a += 30) particle(p, "minecraft:note_particle", add(p.location, rotateY({ x: 3, y: 1, z: 0 }, a)));
                for (const e of nearbyTargets(p, p.location, 3.5)) knockFrom(e, p.location, 1.2, 0.3);
            }, 10);
        },
    },

    // ---------------------------------------------------------------- humungousaur
    earthquake: {
        name: "Earthquake", desc: "Stomp to shake the earth.", cooldown: 80,
        run: (p) => slam(p, 7, 10, 0.9),
    },
    super_leap: {
        name: "Super Leap", desc: "Leap huge distances.", cooldown: 40,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 2.2, y: 1.5, z: v.z * 2.2 });
            toggles.slamOnLand.set(p.id, { dmg: 10, at: system.currentTick });
        },
    },
    tail_spin: {
        name: "Tail Spin", desc: "Sweep enemies away with your tail.", cooldown: 40,
        run: (p) => {
            for (const e of nearbyTargets(p, p.location, 4)) {
                hurt(e, 6, p);
                knockFrom(e, p.location, 1.8, 0.3);
            }
            for (let a = 0; a < 360; a += 30) particle(p, "minecraft:knockback_roar_particle", add(p.location, rotateY({ x: 2.5, y: 0.5, z: 0 }, a)));
        },
    },

    // ---------------------------------------------------------------- jetray
    neuroshock: {
        name: "Neuroshock Blast", desc: "Fire paralysing energy blasts.", cooldown: 25,
        run: (p) => {
            const { targets } = beam(p, 32, "minecraft:electric_spark_particle");
            for (const e of targets) {
                hurt(e, 7, p, "magic");
                effect(e, "slowness", 60, 4);
            }
            sound(p, "alienevo.jet_shoot");
        },
    },
    jet_burst: {
        name: "Jet Burst", desc: "Accelerate to incredible speed.", cooldown: 40,
        run: (p) => {
            const v = p.getViewDirection();
            launch(p, { x: v.x * 3.5, y: v.y * 3 + 0.2, z: v.z * 3.5 });
            sound(p, "alienevo.jet_blast");
        },
    },

    // ---------------------------------------------------------------- chromastone
    prism_beam: {
        name: "Prism Beam", desc: "Fire stored energy as a rainbow beam (stronger with more energy).", cooldown: 40,
        run: (p) => {
            const energy = getEnergy(p);
            const { targets } = beam(p, 32, "minecraft:endrod");
            for (const e of targets) hurt(e, 5 + energy / 10, p, "magic");
            setEnergy(p, energy - 20);
        },
    },
    energy_release: {
        name: "Energy Release", desc: "Release all stored energy at once.", cooldown: 160,
        run: (p) => {
            const energy = getEnergy(p);
            slam(p, 6, 4 + energy / 8, 0.8, "minecraft:totem_particle");
            setEnergy(p, 0);
        },
    },

    // ---------------------------------------------------------------- atomix
    atomic_beam: {
        name: "Atomic Beam", desc: "Fire a beam of nuclear energy.", cooldown: 60,
        run: (p) => {
            const { targets, end } = beam(p, 40, "minecraft:villager_happy");
            for (const e of targets) hurt(e, 10, p, "magic");
            particle(p, "minecraft:huge_explosion_emitter", end);
        },
    },
    nuclear_burst: {
        name: "Nuclear Winner", desc: "A massive nuclear blast that does not break blocks.", cooldown: 200,
        run: (p) => {
            const { end } = beam(p, 30, "minecraft:villager_happy");
            try {
                p.dimension.createExplosion(end, 5, { breaksBlocks: false, causesFire: false, source: p });
            } catch {
                // Ignore.
            }
        },
    },
    // ---------------------------------------------------------------- eye guy
    eye_beam: {
        name: "Eye Beam", desc: "Fire laser beams from your eyes.", cooldown: 20,
        run: (p) => {
            const { targets } = beam(p, 32, "minecraft:electric_spark_particle");
            for (const e of targets) hurt(e, 8, p, "magic");
            sound(p, "alienevo.omni_extras.eyebeam");
        },
    },
    super_eye_beam: {
        name: "Super Eye Beam", desc: "Every eye fires at once.", cooldown: 140,
        run: (p) => {
            const { targets, end } = beam(p, 40, "minecraft:basic_flame_particle");
            for (const e of targets) hurt(e, 14, p, "magic");
            try {
                p.dimension.createExplosion(end, 2.5, { breaksBlocks: false, causesFire: false, source: p });
            } catch {
                // Ignore.
            }
            sound(p, "alienevo.omni_extras.otherbeam");
        },
    },
    elemental_eyes: {
        name: "Elemental Eyes", desc: "Burn, freeze or shock everything around you.", cooldown: 120,
        run: (p) => {
            const mode = Math.floor(Math.random() * 3);
            const particleId = ["minecraft:basic_flame_particle", "minecraft:snowflake_particle", "minecraft:electric_spark_particle"][mode];
            for (let a = 0; a < 360; a += 20) particle(p, particleId, add(p.location, rotateY({ x: 3, y: 1, z: 0 }, a)));
            for (const e of nearbyTargets(p, p.location, 6)) {
                hurt(e, 5, p, mode === 0 ? "fire" : mode === 1 ? "freezing" : "lightning");
                if (mode === 0) {
                    try {
                        e.setOnFire(5, true);
                    } catch {
                        // Ignore.
                    }
                } else if (mode === 1) effect(e, "slowness", 120, 3);
                else effect(e, "weakness", 120, 1);
            }
            p.sendMessage(["§6Fire eyes!", "§bIce eyes!", "§eShock eyes!"][mode]);
        },
    },

    // ---------------------------------------------------------------- upchuck
    swallow: {
        name: "Swallow", desc: "Pull the nearest creature in and eat it.", cooldown: 60,
        run: (p) => {
            const target = coneTargets(p, 7, 0.5)[0];
            if (!target) {
                p.sendMessage("§7Nothing to eat in front of you.");
                return false;
            }
            knockFrom(target, p.location, -1.2, 0.2);
            system.runTimeout(() => {
                if (!p.isValid) return;
                if (target.isValid) hurt(target, 8, p);
                effect(p, "saturation", 1, 2);
                effect(p, "absorption", 400, 1);
                setEnergy(p, getEnergy(p) + 25);
                sound(p, "alienevo.omni_extras.swallow");
            }, 6);
        },
    },
    gut_blast: {
        name: "Gut Blast", desc: "Spit out eaten matter as an explosive energy ball (stronger with more energy).", cooldown: 50,
        run: (p) => {
            const energy = getEnergy(p);
            shoot(p, "alienevo:energy_bolt", 1.4, {
                damage: 6 + energy / 10, trail: "minecraft:villager_happy", explode: 1.5 + energy / 50,
            });
            setEnergy(p, energy - 25);
            sound(p, "alienevo.omni_extras.blast");
        },
    },

    // ---------------------------------------------------------------- armodrillo
    drill: {
        name: "Drill", desc: "Jackhammer a 3x3 tunnel in front of you.", cooldown: 30,
        run: (p) => {
            const eye = p.getHeadLocation();
            const view = p.getViewDirection();
            const right = normalize({ x: -view.z, y: 0, z: view.x });
            const up = normalize({ x: view.y * view.x * -1, y: 1, z: view.y * view.z * -1 });
            for (let d = 1; d <= 4; d++) {
                system.runTimeout(() => {
                    if (!p.isValid) return;
                    const c = add(eye, scale(view, d));
                    for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) breakBlock(p, add(add(c, scale(right, i)), scale(up, j)));
                    particle(p, "minecraft:huge_explosion_emitter", c);
                }, d * 3);
            }
            sound(p, "dig.stone", 1, 0.5);
        },
    },
    quake: {
        name: "Quake", desc: "Pound the ground to create an earthquake.", cooldown: 80,
        run: (p) => slam(p, 7, 9, 0.8),
    },

    // ---------------------------------------------------------------- water hazard
    water_cannon: {
        name: "Water Cannon", desc: "Blast enemies away with pressurised water.", cooldown: 25,
        run: (p) => {
            const { targets, end } = beam(p, 24, "minecraft:water_splash_particle");
            for (const e of targets) {
                hurt(e, 5, p);
                knockFrom(e, p.location, 2.2, 0.4);
                try {
                    e.extinguishFire(true);
                } catch {
                    // Ignore.
                }
            }
            particle(p, "minecraft:water_evaporation_bucket_emitter", end);
            sound(p, "random.splash");
        },
    },
    water_cushion: {
        name: "Water Cushion", desc: "Surround yourself with a protective water bubble.", cooldown: 200,
        run: (p) => {
            effect(p, "resistance", 200, 2);
            effect(p, "slow_falling", 200, 0);
            for (let a = 0; a < 360; a += 30) particle(p, "minecraft:basic_bubble_particle_manual", add(p.location, rotateY({ x: 1.2, y: 1, z: 0 }, a)));
        },
    },

    // ---------------------------------------------------------------- electricity
    electro_bolt: {
        name: "Electro Bolt", desc: "Fire a bolt of electricity.", cooldown: 20,
        run: (p) => {
            const { targets } = beam(p, 28, "minecraft:electric_spark_particle");
            for (const e of targets) {
                hurt(e, 6, p, "lightning");
                effect(e, "slowness", 40, 3);
            }
            sound(p, "random.fizz", 0.8, 1.6);
        },
    },
    lightning_strike: {
        name: "Lightning Strike", desc: "Call lightning down where you look.", cooldown: 100,
        run: (p) => {
            const { end } = beam(p, 40, "minecraft:electric_spark_particle");
            try {
                p.dimension.spawnEntity("minecraft:lightning_bolt", end);
            } catch {
                // Ignore.
            }
        },
    },
    discharge: {
        name: "Discharge", desc: "Release a burst of electricity around you.", cooldown: 100,
        run: (p) => {
            for (let a = 0; a < 360; a += 20) particle(p, "minecraft:electric_spark_particle", add(p.location, rotateY({ x: 3.5, y: 1, z: 0 }, a)));
            for (const e of nearbyTargets(p, p.location, 6)) {
                hurt(e, 7, p, "lightning");
                knockFrom(e, p.location, 0.8, 0.3);
            }
            sound(p, "ambient.weather.lightning.impact", 0.6, 1.4);
        },
    },
    stun_field: {
        name: "Stun Field", desc: "Electrify the air and stun nearby enemies.", cooldown: 120,
        run: (p) => {
            for (const e of nearbyTargets(p, p.location, 7)) {
                hurt(e, 4, p, "lightning");
                effect(e, "slowness", 100, 5);
                effect(e, "weakness", 100, 1);
                particle(e, "minecraft:electric_spark_particle", add(e.location, { x: 0, y: 1, z: 0 }));
            }
            sound(p, "ambient.weather.thunder", 0.5, 1.5);
        },
    },

    // ---------------------------------------------------------------- benwolf
    howl: {
        name: "Sonic Howl", desc: "A howl that blasts enemies away.", cooldown: 60,
        run: (p) => {
            const eye = p.getHeadLocation();
            const v = p.getViewDirection();
            for (let d = 2; d <= 12; d += 2) particle(p, "alienevo:sonic_boom", add(eye, scale(v, d)));
            sound(p, "mob.wolf.big.growl", 1, 0.6);
            for (const e of coneTargets(p, 13, 0.7)) {
                hurt(e, 7, p, "sonicBoom");
                knockFrom(e, p.location, 2, 0.4);
                effect(e, "nausea", 100, 0);
            }
        },
    },

    // ---------------------------------------------------------------- wildvine / chamalien
    fruit_bomb: {
        name: "Fruit Bomb", desc: "Throw an exploding, poisonous seed pod.", cooldown: 40,
        run: (p) => {
            shoot(p, "alienevo:energy_bolt", 1.2, {
                damage: 4, trail: "minecraft:villager_happy", explode: 1.5, radius: 3,
                effects: [["poison", 100, 1]],
            });
        },
    },
    camouflage: {
        name: "Camouflage", desc: "Blend into your surroundings.", cooldown: 300,
        run: (p) => {
            effect(p, "invisibility", 600, 0);
            effect(p, "speed", 600, 0);
            sound(p, "alienevo.omni_extras.stalk");
        },
    },
    stinger: {
        name: "Stinger", desc: "Lunge and sting with a paralysing tail.", cooldown: 30,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 1.5, y: 0.25, z: v.z * 1.5 });
            system.runTimeout(() => {
                if (!p.isValid) return;
                for (const e of coneTargets(p, 3.5, 0.4)) {
                    hurt(e, 6, p);
                    effect(e, "poison", 100, 1);
                    effect(e, "slowness", 60, 4);
                }
            }, 4);
        },
    },

    // ---------------------------------------------------------------- walkatrout
    slide: {
        name: "Slide", desc: "Slide on your slippery belly.", cooldown: 30,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 2.4, y: 0.05, z: v.z * 2.4 });
            effect(p, "speed", 60, 2);
            for (let i = 0; i < 6; i++) particle(p, "minecraft:water_splash_particle", add(p.location, scale(v, -i * 0.5)));
        },
    },
    water_blast: {
        name: "Water Blast", desc: "Fire a jet of water.", cooldown: 20,
        run: (p) => {
            shoot(p, "alienevo:energy_bolt", 1.6, { damage: 4, knockback: 1.5, trail: "minecraft:water_splash_particle", impact: "minecraft:water_evaporation_bucket_emitter" });
            sound(p, "random.splash");
        },
    },
    flip: {
        name: "Flip", desc: "Backflip into the air and land with a splash.", cooldown: 40,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: -v.x * 0.8, y: 1.1, z: -v.z * 0.8 });
            toggles.slamOnLand.set(p.id, { dmg: 4, at: system.currentTick });
        },
    },

    // ---------------------------------------------------------------- ditto
    clone_swarm: {
        name: "Clone Swarm", desc: "Split into copies that pile onto nearby enemies.", cooldown: 120,
        run: (p) => {
            const targets = nearbyTargets(p, p.location, 6);
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ >= 6) return system.clearRun(id);
                for (const e of targets) {
                    if (!e.isValid) continue;
                    hurt(e, 2, p);
                    particle(e, "minecraft:critical_hit_emitter", add(e.location, { x: 0, y: 1, z: 0 }));
                }
            }, 5);
            sound(p, "alienevo.untapped.ditto_taunt");
        },
    },
    taunt: {
        name: "Taunt", desc: "Mock enemies so they become weak and slow.", cooldown: 80,
        run: (p) => {
            for (const e of nearbyTargets(p, p.location, 10)) {
                effect(e, "weakness", 160, 1);
                effect(e, "slowness", 160, 0);
            }
            sound(p, "alienevo.untapped.ditto_taunt");
        },
    },
    uppercut: {
        name: "Uppercut", desc: "Launch an enemy into the air.", cooldown: 30,
        run: (p) => {
            for (const e of coneTargets(p, 3.5, 0.5)) {
                hurt(e, 6, p);
                launch(e, { x: 0, y: 1.1, z: 0 });
            }
        },
    },

    // ---------------------------------------------------------------- eatle
    eat: {
        name: "Eat", desc: "Eat the block you look at to store energy.", cooldown: 15,
        run: (p) => {
            let hit;
            try {
                hit = p.getBlockFromViewDirection({ maxDistance: 4 });
            } catch {
                hit = undefined;
            }
            if (!hit || !canBreak(hit.block.typeId)) {
                p.sendMessage("§7Look at a block to eat it.");
                return false;
            }
            particle(p, "minecraft:huge_explosion_emitter", hit.block.center());
            hit.block.setType("minecraft:air");
            effect(p, "saturation", 1, 1);
            setEnergy(p, getEnergy(p) + 10);
            sound(p, "random.burp");
        },
    },
    horn_beam: {
        name: "Horn Beam", desc: "Fire eaten matter as an energy beam (stronger with more energy).", cooldown: 60,
        run: (p) => {
            const energy = getEnergy(p);
            const { targets, end } = beam(p, 36, "minecraft:endrod");
            for (const e of targets) hurt(e, 6 + energy / 6, p, "magic");
            if (energy >= 50) {
                try {
                    p.dimension.createExplosion(end, 3, { breaksBlocks: false, causesFire: false, source: p });
                } catch {
                    // Ignore.
                }
            }
            setEnergy(p, energy - 30);
            sound(p, "alienevo.untapped.oryctini_beam");
        },
    },
    ram: {
        name: "Ram", desc: "Charge horn first.", cooldown: 40,
        run: (p) => {
            const v = flatView(p);
            launch(p, { x: v.x * 2.6, y: 0.2, z: v.z * 2.6 });
            let n = 0;
            const id = system.runInterval(() => {
                if (!p.isValid || n++ > 8) return system.clearRun(id);
                for (const e of nearbyTargets(p, p.location, 2.2)) {
                    hurt(e, 8, p);
                    knockFrom(e, p.location, 2, 0.5);
                }
            }, 1);
            sound(p, "alienevo.untapped.oryctini_blast");
        },
    },
};

const UNBREAKABLE = new Set([
    "minecraft:bedrock", "minecraft:barrier", "minecraft:command_block", "minecraft:chain_command_block",
    "minecraft:repeating_command_block", "minecraft:structure_block", "minecraft:structure_void", "minecraft:jigsaw",
    "minecraft:end_portal", "minecraft:end_portal_frame", "minecraft:portal", "minecraft:end_gateway",
    "minecraft:reinforced_deepslate", "minecraft:light_block", "minecraft:allow", "minecraft:deny", "minecraft:border_block",
    "minecraft:water", "minecraft:lava", "minecraft:flowing_water", "minecraft:flowing_lava", "minecraft:air",
]);

/** @param {string} typeId */
function canBreak(typeId) {
    return !UNBREAKABLE.has(typeId) && !typeId.includes("light_block");
}

/** Break a block and drop it like a player would. @param {Player} p @param {Vector3} loc */
function breakBlock(p, loc) {
    try {
        const b = p.dimension.getBlock(loc);
        if (!b || !canBreak(b.typeId)) return;
        const { x, y, z } = b.location;
        p.dimension.runCommand(`setblock ${x} ${y} ${z} air destroy`);
    } catch {
        // Unloaded chunk.
    }
}

export function initAbilityTicks() {
    // Fire shield, rolling and slam-on-landing.
    system.runInterval(() => {
        for (const id of toggles.fireShield) {
            const p = /** @type {Player | undefined} */ (getPlayer(id));
            if (!p) continue;
            for (let a = 0; a < 360; a += 45) particle(p, FIRE, add(p.location, rotateY({ x: 1.5, y: 1, z: 0 }, a)));
            for (const e of nearbyTargets(p, p.location, 2.5)) {
                try {
                    e.setOnFire(3, true);
                } catch {
                    // Ignore.
                }
            }
        }
        for (const id of toggles.rolling) {
            const p = getPlayer(id);
            if (!p) continue;
            const vel = p.getVelocity();
            if (Math.abs(vel.x) + Math.abs(vel.z) < 0.15) continue;
            particle(p, "minecraft:knockback_roar_particle", p.location);
            for (const e of nearbyTargets(p, p.location, 1.8)) {
                hurt(e, 6, p);
                knockFrom(e, p.location, 1.4, 0.4);
            }
        }
        for (const [id, s] of toggles.slamOnLand) {
            const p = getPlayer(id);
            if (!p || system.currentTick - s.at > 200) {
                toggles.slamOnLand.delete(id);
                continue;
            }
            if (system.currentTick - s.at > 8 && p.isOnGround) {
                toggles.slamOnLand.delete(id);
                slam(p, 4, s.dmg, 0.5, "minecraft:large_explosion");
            }
        }
    }, 4);
}

/** @type {(id: string) => Player | undefined} */
let getPlayer = () => undefined;
/** @param {(id: string) => Player | undefined} fn */
export function setPlayerLookup(fn) {
    getPlayer = fn;
}
