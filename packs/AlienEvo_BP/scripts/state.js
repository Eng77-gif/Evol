// Per-player Omnitrix state, stored in dynamic properties so it survives
// relogging (replaces the Palladium properties / scoreboards of the Java mod).

import { ALIENS } from "./aliens.js";

/** @typedef {import("@minecraft/server").Player} Player */

const P = {
    alien: "alienevo:alien",
    timer: "alienevo:timer",
    recharge: "alienevo:recharge",
    selected: "alienevo:selected",
    playlist: "alienevo:playlist",
    unlocked: "alienevo:unlocked",
    master: "alienevo:master_control",
    ability: "alienevo:ability_",
    level: "alienevo:level_",
    xp: "alienevo:xp_",
    energy: "alienevo:energy",
    points: "alienevo:points_",
    skills: "alienevo:skills_",
    allSkills: "alienevo:all_skills",
};

/** @param {Player} p @param {string} key @param {number} def */
function num(p, key, def = 0) {
    const v = p.getDynamicProperty(key);
    return typeof v === "number" ? v : def;
}

/** Current alien id (0 = human form). @param {Player} p */
export const getAlien = (p) => num(p, P.alien);
/** @param {Player} p @param {number} id */
export const setAlien = (p, id) => p.setDynamicProperty(P.alien, id);

/** Ticks left in alien form. @param {Player} p */
export const getTimer = (p) => num(p, P.timer);
/** @param {Player} p @param {number} t */
export const setTimer = (p, t) => p.setDynamicProperty(P.timer, t);

/** Ticks left until the Omnitrix can be used again. @param {Player} p */
export const getRecharge = (p) => num(p, P.recharge);
/** @param {Player} p @param {number} t */
export const setRecharge = (p, t) => p.setDynamicProperty(P.recharge, t);

/** Alien shown on the dial. @param {Player} p */
export const getSelected = (p) => num(p, P.selected, 1);
/** @param {Player} p @param {number} id */
export const setSelected = (p, id) => p.setDynamicProperty(P.selected, id);

/** @param {Player} p */
export const hasMasterControl = (p) => p.getDynamicProperty(P.master) === true;
/** @param {Player} p @param {boolean} v */
export const setMasterControl = (p, v) => p.setDynamicProperty(P.master, v);

/** Energy stored by Chromastone. @param {Player} p */
export const getEnergy = (p) => num(p, P.energy);
/** @param {Player} p @param {number} v */
export const setEnergy = (p, v) => p.setDynamicProperty(P.energy, Math.max(0, Math.min(100, v)));

/**
 * Extra DNA unlocked with /alienevo:unlock (on top of what the Omnitrix tier holds).
 * @param {Player} p
 * @returns {number[]}
 */
export function getExtraDna(p) {
    try {
        const v = p.getDynamicProperty(P.unlocked);
        return typeof v === "string" ? JSON.parse(v) : [];
    } catch {
        return [];
    }
}

/** @param {Player} p @param {number[]} ids */
export function setExtraDna(p, ids) {
    p.setDynamicProperty(P.unlocked, JSON.stringify([...new Set(ids)]));
}

/**
 * Up to 10 aliens chosen as the quick playlist; empty means "all available".
 * @param {Player} p
 * @returns {number[]}
 */
export function getPlaylist(p) {
    try {
        const v = p.getDynamicProperty(P.playlist);
        return typeof v === "string" ? JSON.parse(v) : [];
    } catch {
        return [];
    }
}

/** @param {Player} p @param {number[]} ids */
export function setPlaylist(p, ids) {
    p.setDynamicProperty(P.playlist, JSON.stringify(ids.slice(0, 10)));
}

/**
 * Every alien whose DNA the player can use with an Omnitrix of the given tier.
 * @param {Player} p @param {number} tier
 */
export function availableAliens(p, tier) {
    const extra = getExtraDna(p);
    return ALIENS.filter((a) => a.tier <= tier || extra.includes(a.id));
}

/** Selected ability index of an alien. @param {Player} p @param {string} key */
export const getAbilityIndex = (p, key) => num(p, P.ability + key);
/** @param {Player} p @param {string} key @param {number} i */
export const setAbilityIndex = (p, key, i) => p.setDynamicProperty(P.ability + key, i);

/** @param {Player} p @param {string} key */
export const getLevel = (p, key) => num(p, P.level + key);
/** @param {Player} p @param {string} key @param {number} v */
export const setLevel = (p, key, v) => p.setDynamicProperty(P.level + key, v);
/** @param {Player} p @param {string} key */
export const getXp = (p, key) => num(p, P.xp + key);
/** @param {Player} p @param {string} key @param {number} v */
export const setXp = (p, key, v) => p.setDynamicProperty(P.xp + key, v);

// ------------------------------------------------------------ skill tree
// Like the Powers screen of the Java mod: the first FREE_SKILLS abilities of an
// alien are available at once, the others are unlocked with skill points
// earned by levelling that alien.

export const FREE_SKILLS = 2;

/** @param {Player} p @param {string} key */
export const getPoints = (p, key) => num(p, P.points + key);
/** @param {Player} p @param {string} key @param {number} v */
export const setPoints = (p, key, v) => p.setDynamicProperty(P.points + key, Math.max(0, v));

/** @param {Player} p @param {string} key @returns {number[]} */
function unlockedSkills(p, key) {
    try {
        const v = p.getDynamicProperty(P.skills + key);
        return typeof v === "string" ? JSON.parse(v) : [];
    } catch {
        return [];
    }
}

/** @param {Player} p @param {string} key @param {number} index */
export function isSkillUnlocked(p, key, index) {
    return index < FREE_SKILLS || p.getDynamicProperty(P.allSkills) === true || unlockedSkills(p, key).includes(index);
}

/** @param {Player} p @param {string} key @param {number} index */
export function unlockSkill(p, key, index) {
    p.setDynamicProperty(P.skills + key, JSON.stringify([...new Set([...unlockedSkills(p, key), index])]));
}

/** @param {Player} p @param {boolean} v */
export const setAllSkills = (p, v) => p.setDynamicProperty(P.allSkills, v);
