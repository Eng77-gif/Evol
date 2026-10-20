// The Omnitrix: alien selection, transformation, timer and recharge.
// Ported from transform.js, detransform.js, omnitrix_timer.js, recharge.js and
// store_armor.js of the Java mod.

import { EquipmentSlot, ItemLockMode, ItemStack, system, world } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { ABILITIES, clearToggles, toggles } from "./abilities.js";
import { ALIEN_BY_ID, ALIENS, MAX_TIMER, OMNITRIX_TIERS, RECHARGE_TIMER } from "./aliens.js";
import { ANIM_TRIGGERS } from "./anim_data.js";
import {
    availableAliens, getAbilityIndex, getAlien, getLevel, getPlaylist, getRecharge, getSelected, getTimer,
    getXp, hasMasterControl, setAbilityIndex, setAlien, setPlaylist, setRecharge, setSelected, setTimer,
} from "./state.js";
import { actionbar, add, formatTime, particle, sound } from "./util.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("./aliens.js").Alien} Alien */

const ARMOR_SLOTS = [EquipmentSlot.Head, EquipmentSlot.Chest, EquipmentSlot.Legs, EquipmentSlot.Feet];
const INFINITE = 20000000;

/** @param {import("@minecraft/server").ItemStack | undefined} item */
export function omnitrixTier(item) {
    if (!item) return -1;
    return OMNITRIX_TIERS.findIndex((t) => t.item === item.typeId);
}

/** Highest tier Omnitrix the player carries (hand or inventory). @param {Player} p */
export function carriedTier(p) {
    let best = -1;
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (inv) {
        for (let i = 0; i < inv.size; i++) best = Math.max(best, omnitrixTier(inv.getItem(i)));
    }
    best = Math.max(best, omnitrixTier(p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Offhand)));
    return best;
}

/** @param {Player} p */
export function currentAlien(p) {
    return ALIEN_BY_ID.get(getAlien(p));
}

// ------------------------------------------------------------------ armor

/** Move worn armour into the inventory (or drop it) so the alien model shows. @param {Player} p */
function stashArmor(p) {
    const eq = p.getComponent("minecraft:equippable");
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!eq || !inv) return;
    for (const slot of ARMOR_SLOTS) {
        const item = eq.getEquipment(slot);
        if (!item || item.hasTag("alienevo:alien_form")) continue;
        eq.setEquipment(slot, undefined);
        const left = inv.addItem(item);
        if (left) p.dimension.spawnItem(left, p.location);
    }
}

/** @param {Player} p @param {Alien} alien */
function equipForm(p, alien) {
    const form = new ItemStack(`alienevo:form_${alien.key}`, 1);
    form.lockMode = ItemLockMode.slot;
    form.keepOnDeath = true;
    p.getComponent("minecraft:equippable")?.setEquipment(EquipmentSlot.Chest, form);
}

/** @param {Player} p */
function removeForm(p) {
    const eq = p.getComponent("minecraft:equippable");
    if (!eq) return;
    const item = eq.getEquipment(EquipmentSlot.Chest);
    if (item?.hasTag("alienevo:alien_form")) eq.setEquipment(EquipmentSlot.Chest, undefined);
    // Never leave a form item anywhere else.
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (inv) {
        for (let i = 0; i < inv.size; i++) {
            if (inv.getItem(i)?.hasTag("alienevo:alien_form")) inv.setItem(i, undefined);
        }
    }
}

// ------------------------------------------------------------------ effects

/** @param {Player} p @param {Alien} alien */
function applyEffects(p, alien, force = false) {
    for (const [id, amp] of alien.effects) {
        if (id === "speed" && (toggles.speedGear.has(p.id) || toggles.rolling.has(p.id))) continue;
        const cur = p.getEffect(id);
        if (!force && cur && cur.amplifier >= amp) continue;
        try {
            p.addEffect(id, INFINITE, { amplifier: amp, showParticles: false });
        } catch {
            // Unknown effect.
        }
    }
}

/** @param {Player} p @param {Alien} alien */
function removeEffects(p, alien) {
    const ids = new Set(alien.effects.map((e) => e[0]));
    ids.add("speed");
    for (const id of ids) {
        const cur = p.getEffect(id);
        // Only remove the infinite effects we added, not potions.
        if (cur && cur.duration > INFINITE / 2) p.removeEffect(id);
    }
}

// ------------------------------------------------------------------ transform

/** @param {Player} p @param {Alien} alien */
export function transform(p, alien) {
    const prev = currentAlien(p);
    if (prev) {
        removeEffects(p, prev);
        clearToggles(p);
    }
    stashArmor(p);
    equipForm(p, alien);
    setAlien(p, alien.id);
    setSelected(p, alien.id);
    if (!prev) setTimer(p, MAX_TIMER);
    applyEffects(p, alien, true);
    try {
        p.nameTag = `${alien.color}${alien.name}`;
    } catch {
        // Ignore.
    }
    sound(p, prev ? "alienevo.prototype_cycle_2" : "alienevo.prototype_transform");
    sound(p, "alienevo.prototype_1_transform", 0.6);
    for (let i = 0; i < 20; i++) {
        particle(p, "minecraft:villager_happy", add(p.location, { x: (Math.random() - 0.5) * 1.5, y: Math.random() * 2.2, z: (Math.random() - 0.5) * 1.5 }));
    }
    particle(p, "minecraft:totem_particle", add(p.location, { x: 0, y: 1, z: 0 }));
    actionbar(p, `§a§l${alien.name}!`);
}

/**
 * @param {Player} p
 * @param {"manual" | "timeout" | "death"} reason
 */
export function detransform(p, reason) {
    const alien = currentAlien(p);
    removeForm(p);
    if (alien) removeEffects(p, alien);
    clearToggles(p);
    if (flying.delete(p.id)) setFlightAnim(p, false);
    setAlien(p, 0);
    setTimer(p, 0);
    try {
        p.nameTag = p.name;
    } catch {
        // Ignore.
    }
    if (reason === "timeout") {
        setRecharge(p, RECHARGE_TIMER);
        sound(p, "alienevo.prototype_timeout");
        p.sendMessage(`§cThe Omnitrix timed out! §7Recharging for ${formatTime(RECHARGE_TIMER)}.`);
    } else {
        sound(p, "alienevo.prototype_detransform");
    }
    for (let i = 0; i < 15; i++) {
        particle(p, reason === "timeout" ? "minecraft:redstone_wire_dust_particle" : "minecraft:villager_happy",
            add(p.location, { x: (Math.random() - 0.5) * 1.5, y: Math.random() * 2, z: (Math.random() - 0.5) * 1.5 }));
    }
}

// ------------------------------------------------------------------ menus

/** @param {Player} p @param {number} tier */
function selectionList(p, tier) {
    const all = availableAliens(p, tier);
    const playlist = getPlaylist(p).filter((id) => all.some((a) => a.id === id));
    return playlist.length ? playlist.map((id) => /** @type {Alien} */ (ALIEN_BY_ID.get(id))) : all;
}

/** Alien selection dial. @param {Player} p @param {number} tier */
export async function openDial(p, tier) {
    const list = selectionList(p, tier);
    const selected = getSelected(p);
    sound(p, "alienevo.prototype_activate");
    playWatch(p, "open_trigger");
    const form = new ActionFormData()
        .title(`§a${OMNITRIX_TIERS[tier].name}`)
        .body(`§7Pick an alien. §8(Sneak + use to transform into the last selected alien instantly.)\n§7Master Control: ${hasMasterControl(p) ? "§aON" : "§cOFF"}`);
    for (const a of list) {
        const lvl = getLevel(p, a.key);
        form.button(`${a.id === selected ? "§2> " : ""}${a.color}${a.name}§r\n§8Lv ${lvl} - ${a.abilities.length} abilities`, `textures/ui/aliens/${a.key}`);
    }
    form.button("§9Playlist...", "textures/ui/icon_recipe_item");
    form.button("§8Alien Codex", "textures/ui/icon_book_writable");
    const res = await form.show(p);
    if (res.canceled || res.selection === undefined) {
        playWatch(p, "close_trigger");
        return;
    }
    if (res.selection < list.length) {
        const alien = list[res.selection];
        // Spin the dial to the alien, then slam the core down (like the Java mod).
        playWatch(p, list.indexOf(alien) % 2 ? "spinl_trigger" : "spinr_trigger");
        sound(p, "alienevo.prototype_cycle_1");
        system.runTimeout(() => {
            if (!p.isValid) return;
            playWatch(p, "close_trigger");
            sound(p, "alienevo.prototype_cycle_2");
        }, 6);
        system.runTimeout(() => {
            if (!p.isValid || getRecharge(p) > 0 || getAlien(p)) return;
            transform(p, alien);
        }, 16);
    } else if (res.selection === list.length) {
        playWatch(p, "playlist_swap");
        await editPlaylist(p, tier);
    } else {
        await codex(p, tier);
    }
}

/** @param {Player} p @param {number} tier */
async function editPlaylist(p, tier) {
    const all = availableAliens(p, tier);
    const playlist = getPlaylist(p);
    const form = new ActionFormData()
        .title("§9Playlist")
        .body(`§7Toggle which aliens appear on the dial (max 10).\n§7Empty playlist = all available aliens.\n§7Current: §f${playlist.length}`);
    for (const a of all) form.button(`${playlist.includes(a.id) ? "§a[x] " : "§8[ ] "}${a.color}${a.name}`, `textures/ui/aliens/${a.key}`);
    form.button("§cClear playlist");
    const res = await form.show(p);
    if (res.canceled || res.selection === undefined) return;
    if (res.selection === all.length) {
        setPlaylist(p, []);
    } else {
        const id = all[res.selection].id;
        const next = playlist.includes(id) ? playlist.filter((x) => x !== id) : [...playlist, id];
        if (next.length > 10) {
            p.sendMessage("§cA playlist holds at most 10 aliens.");
        } else {
            setPlaylist(p, next);
            sound(p, "alienevo.playlist_swap");
        }
    }
    await editPlaylist(p, tier);
}

/** @param {Player} p @param {number} tier */
async function codex(p, tier) {
    const form = new ActionFormData().title("§8Alien Codex");
    for (const a of ALIENS) {
        const unlocked = availableAliens(p, tier).includes(a);
        form.button(unlocked ? `${a.color}${a.name}` : `§8??? §7(${OMNITRIX_TIERS[a.tier].name})`, unlocked ? `textures/ui/aliens/${a.key}` : "textures/ui/lock");
    }
    const res = await form.show(p);
    if (res.canceled || res.selection === undefined) return;
    const a = ALIENS[res.selection];
    if (!availableAliens(p, tier).includes(a)) return codex(p, tier);
    const lines = a.abilities.map((id) => `§e${ABILITIES[id].name}§7: ${ABILITIES[id].desc}`);
    const info = new ActionFormData()
        .title(`${a.color}${a.name}`)
        .body(`§f${a.desc}\n\n§7Level §f${getLevel(p, a.key)}§7/10  XP §f${getXp(p, a.key)}\n\n${lines.join("\n")}${a.flight ? "\n§bFlight§7: double tap jump in the air." : ""}${a.climb ? "\n§bWall Climb§7: walk into a wall." : ""}`)
        .button("§7Back");
    await info.show(p);
    return codex(p, tier);
}

/**
 * Plays a GeckoLib trigger animation on the alien model (see tools/animations.py).
 * @param {Player} p @param {Alien} alien @param {string} trigger
 */
export function playTrigger(p, alien, trigger) {
    /** @type {Record<string, number> | undefined} */
    const table = /** @type {any} */ (ANIM_TRIGGERS)[alien.key];
    const index = table?.[trigger];
    if (!index) return;
    try {
        p.playAnimation(`animation.alienevo.signal.${index}`, { blendOutTime: 0, controller: "alienevo_signal" });
    } catch {
        // Player left.
    }
}

/** Animation of the Omnitrix watch on the wrist. @param {Player} p @param {string} trigger */
export function playWatch(p, trigger) {
    const index = /** @type {any} */ (ANIM_TRIGGERS).omnitrix?.[trigger];
    if (!index) return;
    try {
        p.playAnimation(`animation.alienevo.signal.${index}`, { blendOutTime: 0, controller: "alienevo_signal" });
    } catch {
        // Player left.
    }
}

/** Tells the alien model whether the player flies. @param {Player} p @param {boolean} on */
export function setFlightAnim(p, on) {
    try {
        p.playAnimation(on ? "animation.alienevo.flight.on" : "animation.alienevo.flight.off", { blendOutTime: 0, controller: "alienevo_flight" });
    } catch {
        // Player left.
    }
}

/** @param {Player} p @param {Alien} alien @param {string} abilityId */
function animateAbility(p, alien, abilityId) {
    if (abilityId === "roll") {
        playTrigger(p, alien, toggles.rolling.has(p.id) ? "ball_in" : "ball_out");
        return;
    }
    const anim = alien.anims?.[abilityId];
    if (!anim) return;
    if (typeof anim === "string") {
        playTrigger(p, alien, anim);
        return;
    }
    const [start, end, ticks] = anim;
    playTrigger(p, alien, start);
    system.runTimeout(() => {
        if (p.isValid && getAlien(p) === alien.id) playTrigger(p, alien, end);
    }, ticks);
}

/** @type {Map<string, number>} */
const cooldowns = new Map();

/** @param {Player} p @param {string} abilityId */
function cooldownLeft(p, abilityId) {
    return Math.max(0, (cooldowns.get(`${p.id}:${abilityId}`) ?? 0) - system.currentTick);
}

/** @param {Player} p @param {Alien} alien @param {number} [index] */
export function castAbility(p, alien, index) {
    const i = index ?? getAbilityIndex(p, alien.key);
    const id = alien.abilities[i] ?? alien.abilities[0];
    const ability = ABILITIES[id];
    if (!ability) return;
    const left = cooldownLeft(p, id);
    if (left > 0) {
        actionbar(p, `§c${ability.name} §7ready in §f${(left / 20).toFixed(1)}s`);
        return;
    }
    // Levels (from killing mobs as this alien) shorten cooldowns by up to 30%.
    const cd = Math.round(ability.cooldown * (1 - getLevel(p, alien.key) * 0.03));
    if (ability.run(p) !== false) {
        cooldowns.set(`${p.id}:${id}`, system.currentTick + cd);
        animateAbility(p, alien, id);
    }
}

/** @param {Player} p @param {Alien} alien */
async function abilityMenu(p, alien) {
    const sel = getAbilityIndex(p, alien.key);
    const form = new ActionFormData()
        .title(`${alien.color}${alien.name}`)
        .body("§7Choose an ability. Using the Omnitrix casts the selected ability.");
    alien.abilities.forEach((id, i) => {
        const a = ABILITIES[id];
        const left = cooldownLeft(p, id);
        form.button(`${i === sel ? "§2> " : ""}§0${a.name}${left > 0 ? ` §c(${(left / 20).toFixed(0)}s)` : ""}\n§8${a.desc}`);
    });
    form.button("§cDetransform", "textures/ui/cancel");
    const res = await form.show(p);
    if (res.canceled || res.selection === undefined) return;
    if (res.selection >= alien.abilities.length) {
        system.run(() => detransform(p, "manual"));
        return;
    }
    const index = res.selection;
    setAbilityIndex(p, alien.key, index);
    system.run(() => castAbility(p, alien, index));
}

/** Omnitrix item used. @param {Player} p @param {number} tier */
export function useOmnitrix(p, tier) {
    const alien = currentAlien(p);
    if (alien) {
        if (p.isSneaking) abilityMenu(p, alien);
        else castAbility(p, alien);
        return;
    }
    const recharge = getRecharge(p);
    if (recharge > 0) {
        sound(p, "alienevo.prototype_failsafe");
        actionbar(p, `§cRecharging... §f${formatTime(recharge)}`);
        return;
    }
    if (p.isSneaking) {
        const target = ALIEN_BY_ID.get(getSelected(p));
        if (target && selectionList(p, tier).includes(target)) {
            transform(p, target);
            return;
        }
    }
    openDial(p, tier);
}

// ------------------------------------------------------------------ flight

/** @type {Map<string, { since: number, ground: number }>} */
export const flying = new Map();
/** @type {Map<string, number>} */
const lastJump = new Map();

/** @param {Player} p @param {Alien} alien */
function flightTick(p, alien) {
    const f = flying.get(p.id);
    if (!f || !alien.flight) return;
    if (p.isOnGround) {
        if (++f.ground > 10) {
            flying.delete(p.id);
            playTrigger(p, alien, "flight_off");
            setFlightAnim(p, false);
            return;
        }
    } else {
        f.ground = 0;
    }
    const speed = alien.flight;
    const mv = p.inputInfo.getMovementVector();
    const view = p.getViewDirection();
    const flat = Math.sqrt(view.x * view.x + view.z * view.z) || 1;
    const fx = view.x / flat, fz = view.z / flat;
    // Right vector of the camera.
    const rx = -fz, rz = fx;
    const hx = (fx * mv.y - rx * mv.x) * speed;
    const hz = (fz * mv.y - rz * mv.x) * speed;
    let vy = 0.0;
    if (p.inputInfo.getButtonState(/** @type {any} */ ("Jump")) === "Pressed") vy = 0.45;
    else if (p.isSneaking) vy = -0.45;
    else if (mv.y > 0.1) vy = view.y * speed;
    try {
        p.applyKnockback({ x: hx, z: hz }, vy);
    } catch {
        // Ignore.
    }
    if (system.currentTick % 4 === 0) particle(p, alien.key === "dragonoid" || alien.key === "pyronite" ? "minecraft:basic_flame_particle" : "minecraft:white_smoke_particle", p.location);
}

// ------------------------------------------------------------------ passives

/** @type {Map<string, number>} */
const dryTicks = new Map();

/** @param {Player} p @param {Alien} alien */
function passiveTick(p, alien) {
    if (alien.climb) {
        const mv = p.inputInfo.getMovementVector();
        if (mv.y > 0.3) {
            const view = p.getViewDirection();
            const flat = Math.sqrt(view.x * view.x + view.z * view.z) || 1;
            const front = { x: p.location.x + (view.x / flat) * 0.6, y: p.location.y + 0.5, z: p.location.z + (view.z / flat) * 0.6 };
            try {
                const b = p.dimension.getBlock(front);
                if (b && !b.isAir && !b.isLiquid && b.typeId !== "minecraft:short_grass") {
                    p.applyKnockback({ x: (view.x / flat) * 0.05, z: (view.z / flat) * 0.05 }, 0.28);
                }
            } catch {
                // Ignore.
            }
        }
    }
    if (alien.key === "kineceleran" && !p.isSneaking) {
        // Run across water.
        try {
            const below = p.dimension.getBlock({ x: p.location.x, y: p.location.y - 0.2, z: p.location.z });
            const v = p.getVelocity();
            if (below?.typeId === "minecraft:water" && Math.abs(v.x) + Math.abs(v.z) > 0.15) {
                p.applyKnockback({ x: v.x, z: v.z }, 0.12);
                if (system.currentTick % 2 === 0) particle(p, "minecraft:water_wake_particle", p.location);
            }
        } catch {
            // Ignore.
        }
    }
    if (alien.aquatic) {
        if (p.isInWater) {
            if (system.currentTick % 20 !== 0) return;
            dryTicks.set(p.id, 0);
            p.addEffect("conduit_power", 40, { showParticles: false });
            p.addEffect("strength", 40, { amplifier: 1, showParticles: false });
            p.addEffect("speed", 40, { amplifier: 2, showParticles: false });
        } else {
            const dry = (dryTicks.get(p.id) ?? 0) + 2;
            dryTicks.set(p.id, dry);
            if (dry > 600) p.addEffect("slowness", 40, { amplifier: 1, showParticles: false });
            if (dry > 1200 && dry % 40 === 0) {
                p.applyDamage(1, { cause: /** @type {any} */ ("drowning") });
                actionbar(p, "§9Ripjaws is drying out! Find water.");
            }
        }
    }
}

// ------------------------------------------------------------------ main loop

/** @param {Player} p @param {Alien} alien */
function hud(p, alien) {
    const ability = ABILITIES[alien.abilities[getAbilityIndex(p, alien.key)] ?? alien.abilities[0]];
    const left = cooldownLeft(p, alien.abilities[getAbilityIndex(p, alien.key)] ?? alien.abilities[0]);
    const timer = hasMasterControl(p) ? "§a∞" : (getTimer(p) < 200 ? "§c" : "§a") + formatTime(getTimer(p));
    const ab = left > 0 ? `§7${ability.name} §c${(left / 20).toFixed(1)}s` : `§e${ability.name}`;
    const extra = flying.has(p.id) ? " §b[Flying]" : "";
    actionbar(p, `${alien.color}${alien.name} §8| ${ab} §8| ${timer}${extra}`);
}

export function initOmnitrix() {
    system.runInterval(() => {
        for (const p of world.getAllPlayers()) {
            const alien = currentAlien(p);
            if (!alien) {
                const r = getRecharge(p);
                if (r > 0) {
                    setRecharge(p, Math.max(0, r - 2));
                    if (r - 2 <= 0) {
                        sound(p, "alienevo.prototype_recharge");
                        actionbar(p, "§aOmnitrix recharged!");
                    }
                }
                continue;
            }
            // Form item removed (e.g. /clear) -> detransform.
            const chest = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Chest);
            if (chest?.typeId !== `alienevo:form_${alien.key}`) {
                if (chest && !chest.hasTag("alienevo:alien_form")) {
                    stashArmor(p);
                    equipForm(p, alien);
                } else if (!chest) {
                    equipForm(p, alien);
                }
            }
            if (system.currentTick % 20 === 0) stashArmor(p);
            if (system.currentTick % 40 === 0) applyEffects(p, alien);
            if (!hasMasterControl(p)) {
                const t = getTimer(p) - 2;
                setTimer(p, t);
                if (t <= 200 && t > 0 && t % 20 === 0) sound(p, "note.pling", 0.6, 2);
                if (t <= 0) {
                    detransform(p, "timeout");
                    continue;
                }
            }
            passiveTick(p, alien);
            if (system.currentTick % 10 === 0) hud(p, alien);
        }
    }, 2);

    // Flight needs every tick to feel smooth.
    system.runInterval(() => {
        for (const id of flying.keys()) {
            const p = world.getEntity(id);
            if (!p || !p.isValid || p.typeId !== "minecraft:player") {
                flying.delete(id);
                continue;
            }
            const alien = currentAlien(/** @type {Player} */ (p));
            if (!alien) flying.delete(id);
            else flightTick(/** @type {Player} */ (p), alien);
        }
    }, 1);

    world.afterEvents.playerButtonInput.subscribe((ev) => {
        if (ev.button !== "Jump" || ev.newButtonState !== "Pressed") return;
        const p = ev.player;
        const alien = currentAlien(p);
        if (!alien?.flight) return;
        const now = system.currentTick;
        const last = lastJump.get(p.id) ?? -100;
        lastJump.set(p.id, now);
        if (now - last > 7) return;
        if (flying.has(p.id)) {
            flying.delete(p.id);
            playTrigger(p, alien, "flight_off");
            setFlightAnim(p, false);
            actionbar(p, "§7Flight: OFF");
        } else {
            flying.set(p.id, { since: now, ground: 0 });
            playTrigger(p, alien, "flight_on");
            setFlightAnim(p, true);
            p.applyKnockback({ x: 0, z: 0 }, 0.5);
            actionbar(p, "§bFlight: ON");
        }
    });

    // Damage immunities.
    world.beforeEvents.entityHurt.subscribe((ev) => {
        if (ev.hurtEntity.typeId !== "minecraft:player") return;
        const alien = ALIEN_BY_ID.get(/** @type {number} */ (ev.hurtEntity.getDynamicProperty("alienevo:alien") ?? 0));
        if (!alien) return;
        const cause = ev.damageSource.cause;
        if (alien.immune?.includes(cause)) {
            ev.cancel = true;
            if (alien.key === "crystalsapien") {
                const p = /** @type {Player} */ (ev.hurtEntity);
                const dmg = ev.damage;
                system.run(() => absorb(p, dmg));
            }
            return;
        }
        if (cause === "fall" && flying.has(ev.hurtEntity.id)) ev.cancel = true;
    });

    world.afterEvents.entityHurt.subscribe((ev) => {
        if (ev.hurtEntity.typeId !== "minecraft:player") return;
        const p = /** @type {Player} */ (ev.hurtEntity);
        if (currentAlien(p)?.key === "crystalsapien") absorb(p, ev.damage);
    });

    // Melee extras.
    world.afterEvents.entityHitEntity.subscribe((ev) => {
        if (ev.damagingEntity.typeId !== "minecraft:player") return;
        const alien = currentAlien(/** @type {Player} */ (ev.damagingEntity));
        if (alien?.melee === "fire") {
            try {
                ev.hitEntity.setOnFire(4, true);
            } catch {
                // Ignore.
            }
        } else if (alien?.melee === "shock") {
            try {
                ev.hitEntity.addEffect("slowness", 40, { amplifier: 2 });
                ev.hitEntity.dimension.spawnParticle("minecraft:electric_spark_particle", ev.hitEntity.location);
            } catch {
                // Ignore.
            }
        }
    });

    world.afterEvents.entityDie.subscribe((ev) => {
        if (ev.deadEntity.typeId !== "minecraft:player") return;
        const p = /** @type {Player} */ (ev.deadEntity);
        if (getAlien(p)) detransform(p, "death");
    });

    world.afterEvents.playerSpawn.subscribe((ev) => {
        const p = ev.player;
        system.runTimeout(() => {
            if (!p.isValid) return;
            const alien = currentAlien(p);
            if (alien) {
                equipForm(p, alien);
                applyEffects(p, alien, true);
            } else {
                removeForm(p);
            }
        }, 10);
    });

    world.afterEvents.playerLeave.subscribe((ev) => {
        flying.delete(ev.playerId);
        clearToggles(/** @type {any} */ ({ id: ev.playerId }));
    });
}

/** Chromastone stores energy from damage. @param {Player} p @param {number} dmg */
function absorb(p, dmg) {
    const cur = /** @type {number} */ (p.getDynamicProperty("alienevo:energy") ?? 0);
    p.setDynamicProperty("alienevo:energy", Math.min(100, cur + dmg * 5));
    particle(p, "minecraft:totem_particle", add(p.location, { x: 0, y: 1, z: 0 }));
}
