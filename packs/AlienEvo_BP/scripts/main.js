// AlienEvo for Minecraft Bedrock 26.50 - entry point.

import {
    CommandPermissionLevel, CustomCommandParamType, CustomCommandStatus, EquipmentSlot, system, world,
} from "@minecraft/server";
import { initAbilityTicks, setPlayerLookup } from "./abilities.js";
import { revealCodes, useCodeTablet } from "./codes.js";
import { initWorldDial } from "./dial.js";
import { ALIEN_BY_KEY, ALIENS } from "./aliens.js";
import { currentAlien, detransform, initOmnitrix, omnitrixTier, transform, useOmnitrix } from "./omnitrix.js";
import { openPod } from "./pod.js";
import { initProjectiles } from "./projectiles.js";
import {
    getAlien, getExtraDna, getLevel, getPoints, getXp, setAllSkills, setExtraDna, setLevel, setMasterControl,
    setPoints, setRecharge, setXp,
} from "./state.js";
import { STRUCTURES } from "./structure_data.js";
import { initHud } from "./hud.js";
import { initWorldgen, placeStructure } from "./worldgen.js";
import { sound } from "./util.js";
import { openWorkbench } from "./workbench.js";

/** @typedef {import("@minecraft/server").Player} Player */

system.beforeEvents.startup.subscribe((ev) => {
    ev.itemComponentRegistry.registerCustomComponent("alienevo:omnitrix", {
        onUse: (e) => {
            const tier = omnitrixTier(e.itemStack);
            const p = e.source;
            if (tier >= 0) system.run(() => p.isValid && useOmnitrix(p, tier));
        },
    });

    ev.itemComponentRegistry.registerCustomComponent("alienevo:code_tablet", {
        onUse: (e) => {
            if (e.itemStack) useCodeTablet(e.source, e.itemStack.typeId);
        },
    });

    // Galvan tools lose durability when mining, like vanilla tools.
    ev.itemComponentRegistry.registerCustomComponent("alienevo:tool_durability", {
        onMineBlock: (e) => {
            const p = e.source;
            if (p.typeId !== "minecraft:player") return;
            const player = /** @type {Player} */ (p);
            if (player.getGameMode() === "Creative") return;
            const eq = player.getComponent("minecraft:equippable");
            const item = eq?.getEquipment(EquipmentSlot.Mainhand);
            const dur = item?.getComponent("minecraft:durability");
            if (!item || !dur) return;
            const unbreaking = item.getComponent("minecraft:enchantable")?.getEnchantment("unbreaking")?.level ?? 0;
            if (Math.random() >= 1 / (unbreaking + 1)) return;
            if (dur.damage + 1 >= dur.maxDurability) {
                eq?.setEquipment(EquipmentSlot.Mainhand, undefined);
                sound(player, "random.break");
            } else {
                dur.damage += 1;
                eq?.setEquipment(EquipmentSlot.Mainhand, item);
            }
        },
    });

    ev.blockComponentRegistry.registerCustomComponent("alienevo:workbench", {
        onPlayerInteract: (e) => {
            if (e.player) openWorkbench(e.player, e.block);
        },
    });

    ev.blockComponentRegistry.registerCustomComponent("alienevo:galvan_pod", {
        onPlayerInteract: (e) => {
            if (e.player) openPod(e.player, e.block);
        },
    });

    // ---------------------------------------------------------------- commands
    const reg = ev.customCommandRegistry;
    reg.registerEnum("alienevo:alien", ["all", ...ALIENS.map((a) => a.key)]);

    reg.registerCommand({
        name: "alienevo:transform",
        description: "Transform into an alien (Omnitrix not required).",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "alienevo:alien", type: CustomCommandParamType.Enum }],
        optionalParameters: [{ name: "target", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, key, targets) => {
        const alien = ALIEN_BY_KEY.get(key);
        if (!alien) return { status: CustomCommandStatus.Failure, message: `Unknown alien: ${key}` };
        const players = playersFor(origin, targets);
        system.run(() => players.forEach((p) => transform(p, alien)));
        return { status: CustomCommandStatus.Success, message: `Transformed into ${alien.name}.` };
    });

    reg.registerCommand({
        name: "alienevo:detransform",
        description: "Return to human form.",
        permissionLevel: CommandPermissionLevel.Any,
        optionalParameters: [{ name: "target", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, targets) => {
        const players = playersFor(origin, targets);
        system.run(() => players.forEach((p) => getAlien(p) && detransform(p, "manual")));
        return { status: CustomCommandStatus.Success };
    });

    reg.registerCommand({
        name: "alienevo:unlock",
        description: "Unlock alien DNA regardless of the Omnitrix tier.",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "alienevo:alien", type: CustomCommandParamType.Enum }],
        optionalParameters: [{ name: "target", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, key, targets) => {
        const ids = key === "all" ? ALIENS.map((a) => a.id) : [ALIEN_BY_KEY.get(key)?.id ?? 0].filter(Boolean);
        const players = playersFor(origin, targets);
        system.run(() => players.forEach((p) => setExtraDna(p, [...getExtraDna(p), ...ids])));
        return { status: CustomCommandStatus.Success, message: `Unlocked ${key}.` };
    });

    reg.registerCommand({
        name: "alienevo:mastercontrol",
        description: "Enable or disable Omnitrix Master Control (no time limit).",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "enabled", type: CustomCommandParamType.Boolean }],
        optionalParameters: [{ name: "target", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, enabled, targets) => {
        const players = playersFor(origin, targets);
        system.run(() => players.forEach((p) => setMasterControl(p, !!enabled)));
        return { status: CustomCommandStatus.Success, message: `Master Control: ${enabled}` };
    });

    reg.registerEnum("alienevo:structure", STRUCTURES);
    reg.registerCommand({
        name: "alienevo:structure",
        description: "Place an AlienEvo structure at your position (normally generated in new chunks).",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "alienevo:structure", type: CustomCommandParamType.Enum }],
    }, (origin, name) => {
        const src = origin.sourceEntity;
        if (!src) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
        system.run(() => placeStructure(src, String(name)));
        return { status: CustomCommandStatus.Success, message: `Placing ${name}...` };
    });

    reg.registerCommand({
        name: "alienevo:unlockskills",
        description: "Unlock every ability of every alien (skill tree).",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "enabled", type: CustomCommandParamType.Boolean }],
        optionalParameters: [{ name: "target", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, enabled, targets) => {
        const players = playersFor(origin, targets);
        system.run(() => players.forEach((p) => setAllSkills(p, !!enabled)));
        return { status: CustomCommandStatus.Success };
    });

    reg.registerCommand({
        name: "alienevo:revealcode",
        description: "Show your Master Control and Self Destruct codes.",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        optionalParameters: [{ name: "target", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, targets) => {
        const players = playersFor(origin, targets);
        system.run(() => players.forEach((p) => revealCodes(p)));
        return { status: CustomCommandStatus.Success };
    });

    reg.registerCommand({
        name: "alienevo:recharge",
        description: "Instantly recharge the Omnitrix.",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        optionalParameters: [{ name: "target", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, targets) => {
        const players = playersFor(origin, targets);
        system.run(() => players.forEach((p) => setRecharge(p, 0)));
        return { status: CustomCommandStatus.Success };
    });
});

/**
 * @param {import("@minecraft/server").CustomCommandOrigin} origin
 * @param {Player[] | undefined} targets
 * @returns {Player[]}
 */
function playersFor(origin, targets) {
    if (targets && targets.length) return targets;
    const src = origin.sourceEntity;
    return src && src.typeId === "minecraft:player" ? [/** @type {Player} */ (src)] : [];
}

// ---------------------------------------------------------------- alien XP (xp.js)

world.afterEvents.entityDie.subscribe((ev) => {
    const killer = ev.damageSource.damagingEntity;
    if (!killer || killer.typeId !== "minecraft:player") return;
    const p = /** @type {Player} */ (killer);
    const alien = currentAlien(p);
    if (!alien) return;
    const level = getLevel(p, alien.key);
    if (level >= 10) return;
    let maxHealth = 20;
    try {
        maxHealth = ev.deadEntity.getComponent("minecraft:health")?.effectiveMax ?? 20;
    } catch {
        // Entity is gone.
    }
    const xp = getXp(p, alien.key) + Math.round(maxHealth * 0.425);
    const needed = level === 0 ? 100 : 100 * level;
    if (xp >= needed) {
        setLevel(p, alien.key, level + 1);
        setPoints(p, alien.key, getPoints(p, alien.key) + 1);
        setXp(p, alien.key, level + 1 >= 10 ? 0 : xp - needed);
        sound(p, "random.levelup");
        p.sendMessage(`${alien.color}${alien.name}§a reached level §f${level + 1}§a! §7+1 skill point, ability cooldowns -${(level + 1) * 3}%`);
    } else {
        setXp(p, alien.key, xp);
    }
});

// ---------------------------------------------------------------- startup

setPlayerLookup((id) => {
    const e = world.getEntity(id);
    return e && e.isValid && e.typeId === "minecraft:player" ? /** @type {Player} */ (e) : undefined;
});
initProjectiles();
initAbilityTicks();
initOmnitrix();
initWorldDial();
initWorldgen();
initHud();

world.afterEvents.playerSpawn.subscribe((ev) => {
    if (!ev.initialSpawn) return;
    const p = ev.player;
    if (p.getDynamicProperty("alienevo:welcome")) return;
    p.setDynamicProperty("alienevo:welcome", true);
    system.runTimeout(() => {
        if (!p.isValid) return;
        p.sendMessage("§a[AlienEvo] §7Find §fGalvan Pods§7 around the world to collect Galvan Scrap, Omni Shards and the §aPrototype Omnitrix Core§7.\n§7Craft the §aPrototype Omnitrix§7 and use it to pick an alien. Tap the air with the Omnitrix on your wrist to open it. While transformed: tap = selected ability, sneak + tap = next ability (the Omnitrix slot opens the menu).");
    }, 100);
});

