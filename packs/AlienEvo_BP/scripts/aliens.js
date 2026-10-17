// Alien codex: ported from addon/alienevo/kubejs_scripts/alien_codex.js and
// the Palladium powers in data/alienevo_aliens/palladium/powers.
//
// tier    - minimum Omnitrix tier that holds this DNA
//           (0 Prototype, 1 Phase 1, 2 Phase 2, 3 Evolved/10k)
// effects - [effect id, amplifier] kept active while transformed
// immune  - damage causes that are cancelled while transformed
// flight  - double tap jump in the air to toggle flight
// climb   - walk into a wall to climb it
// melee   - extra effect applied to entities hit with a melee attack
// anims   - ability -> GeckoLib trigger animation of the alien model, or
//           [start trigger, end trigger, ticks until the end trigger]

/**
 * @typedef {{
 *   id: number, key: string, name: string, color: string, tier: number,
 *   effects: [string, number][], immune?: string[], flight?: number, climb?: boolean,
 *   melee?: string, aquatic?: boolean, abilities: string[], desc: string,
 *   anims?: Record<string, string | [string, string, number]>
 * }} Alien
 */

/** @type {Alien[]} */
export const ALIENS = [
    {
        id: 1, key: "pyronite", name: "Heatblast", color: "§6", tier: 0,
        effects: [["fire_resistance", 0], ["strength", 0]],
        immune: ["fire", "fireTick", "lava", "freezing", "campfire", "soulCampfire"],
        melee: "fire",
        abilities: ["fireball", "fire_blast", "flame_breath", "pyro_jump"],
        desc: "A living inferno from the planet Pyros. Shoots fire and is immune to heat.",
    },
    {
        id: 2, key: "vulpimancer", name: "Wildmutt", color: "§6", tier: 0,
        effects: [["speed", 1], ["strength", 0], ["night_vision", 0], ["jump_boost", 1]],
        immune: ["fall"], climb: true,
        abilities: ["pounce", "quill_barrage", "bite", "predator_sense"],
        desc: "An eyeless Vulpimancer that senses its prey through smell and sound.",
        anims: { bite: "bite_anim" },
    },
    {
        id: 3, key: "petrosapien", name: "Diamondhead", color: "§b", tier: 0,
        effects: [["resistance", 1], ["strength", 1], ["regeneration", 0]],
        immune: ["freezing"],
        abilities: ["crystal_shards", "crystal_wave", "crystal_shield"],
        desc: "A Petrosapien made of living Taydenite crystal.",
        anims: { crystal_shards: ["shards_on", "shards_off", 30], crystal_shield: ["spin", "spin_off", 100] },
    },
    {
        id: 4, key: "kineceleran", name: "XLR8", color: "§3", tier: 0,
        effects: [["speed", 3], ["jump_boost", 1]],
        immune: ["fall"],
        abilities: ["speed_gear", "dash", "tornado"],
        desc: "A Kineceleran that can run at supersonic speeds, even across water.",
        anims: { dash: ["mask_on", "mask_off", 60] },
    },
    {
        id: 5, key: "galvan", name: "Grey Matter", color: "§a", tier: 0,
        effects: [["speed", 0], ["jump_boost", 2]],
        immune: ["fall"], climb: true,
        abilities: ["galvan_leap", "ore_scan", "tinker"],
        desc: "A tiny Galvan genius. Small, agile and smarter than anyone else.",
        anims: { ore_scan: "pose_anim", tinker: "tongue_anim" },
    },
    {
        id: 6, key: "tetramand", name: "Four Arms", color: "§c", tier: 0,
        effects: [["strength", 2], ["resistance", 0], ["health_boost", 2]],
        abilities: ["ground_slam", "boulder_throw", "sonic_clap", "charge_leap"],
        desc: "A four armed Tetramand with incredible strength.",
    },
    {
        id: 7, key: "lepidopterran", name: "Stinkfly", color: "§e", tier: 0,
        effects: [["slow_falling", 0]],
        immune: ["fall"], flight: 0.55,
        abilities: ["slime_shot", "toxic_gas", "insect_eyes"],
        desc: "A Lepidopterran that flies and shoots sticky slime.",
        anims: { insect_eyes: "sonar" },
    },
    {
        id: 8, key: "piscciss_volann", name: "Ripjaws", color: "§2", tier: 0,
        effects: [["water_breathing", 0], ["night_vision", 0]],
        aquatic: true,
        abilities: ["bite", "aqua_jet", "tidal_spin"],
        desc: "A Piscciss Volann, an apex predator of the seas. Weak on land.",
        anims: { bite: "bite", tidal_spin: "swipe" },
    },
    {
        id: 9, key: "galvanic_mechamorph", name: "Upgrade", color: "§a", tier: 0,
        effects: [["haste", 1], ["regeneration", 1]],
        immune: ["fall"],
        abilities: ["energy_beam", "liquid_form", "spike_hands"],
        desc: "A Galvanic Mechamorph made of living technology.",
        anims: { spike_hands: ["hands_on", "hands_off", 300], liquid_form: ["puddle", "puddle_off", 120] },
    },
    {
        id: 10, key: "ectonurite", name: "Ghostfreak", color: "§d", tier: 0,
        effects: [["regeneration", 1], ["night_vision", 0], ["slow_falling", 0]],
        immune: ["fall", "suffocation"], flight: 0.45,
        abilities: ["phase", "shadow_strike", "scare"],
        desc: "An Ectonurite that can turn invisible and intangible.",
        anims: { scare: "tentacles", shadow_strike: "strike" },
    },
    {
        id: 11, key: "arburian_pelarota", name: "Cannonbolt", color: "§6", tier: 1,
        effects: [["resistance", 1], ["health_boost", 2]],
        immune: ["fall"],
        abilities: ["roll", "roll_leap"],
        desc: "An Arburian Pelarota that curls into an armoured ball.",
    },
    {
        id: 31, key: "methanosian", name: "Swampfire", color: "§2", tier: 1,
        effects: [["regeneration", 1], ["strength", 0]],
        immune: ["fire", "fireTick", "lava", "campfire", "soulCampfire"],
        melee: "fire",
        abilities: ["fireball", "bloom", "vine_snare"],
        desc: "A plant-like Methanosian that burns methane and regrows.",
    },
    {
        id: 32, key: "sonorosian", name: "Echo Echo", color: "§f", tier: 1,
        effects: [["speed", 0]],
        immune: ["sonicBoom"],
        abilities: ["sonic_scream", "sound_wall"],
        desc: "A Sonorosian that attacks with sonic screams.",
    },
    {
        id: 33, key: "vaxasaurian", name: "Humungousaur", color: "§6", tier: 1,
        effects: [["strength", 3], ["resistance", 1], ["health_boost", 3]],
        immune: ["fall"],
        abilities: ["earthquake", "super_leap", "tail_spin"],
        desc: "A huge Vaxasaurian with dinosaur strength.",
    },
    {
        id: 34, key: "aerophibian", name: "Jetray", color: "§c", tier: 2,
        effects: [["slow_falling", 0], ["water_breathing", 0]],
        immune: ["fall"], flight: 0.85,
        abilities: ["neuroshock", "jet_burst"],
        desc: "An Aerophibian, the fastest flyer in the Omnitrix.",
    },
    {
        id: 35, key: "necrofriggian", name: "Big Chill", color: "§b", tier: 2,
        effects: [["slow_falling", 0], ["resistance", 0]],
        immune: ["freezing", "fall"], flight: 0.5,
        abilities: ["freeze_breath", "ice_shards", "phase"],
        desc: "A Necrofriggian that freezes everything with its breath.",
    },
    {
        id: 36, key: "crystalsapien", name: "Chromastone", color: "§d", tier: 2,
        effects: [["resistance", 1], ["strength", 0]],
        immune: ["lightning", "magic"],
        abilities: ["prism_beam", "energy_release"],
        desc: "A Crystalsapien that absorbs energy and fires it back.",
        anims: { energy_release: ["explosion_start", "explosion_end", 30] },
    },
    {
        id: 80, key: "nucleonix", name: "Atomix", color: "§a", tier: 2,
        effects: [["strength", 1], ["resistance", 1], ["regeneration", 1], ["slow_falling", 0]],
        immune: ["fall", "blockExplosion", "entityExplosion"], flight: 0.6,
        abilities: ["atomic_beam", "nuclear_burst"],
        desc: "A Nucleonix, a walking nuclear reactor.",
    },
    {
        id: 100, key: "dragonoid", name: "Dragonoid", color: "§4", tier: 3,
        effects: [["strength", 1], ["fire_resistance", 0], ["slow_falling", 0]],
        immune: ["fire", "fireTick", "lava", "fall"], flight: 0.75,
        abilities: ["fireball_barrage", "flame_breath", "fire_shield"],
        desc: "A mighty Dragonoid that soars and breathes fire.",
    },
    {
        id: 101, key: "astrobot", name: "Astro Bot", color: "§9", tier: 3,
        effects: [["speed", 1], ["jump_boost", 2]],
        immune: ["fall"],
        abilities: ["laser_jump", "rocket_punch", "energy_beam"],
        desc: "A small, bouncy robot with laser boots.",
        anims: { energy_beam: ["beam_on", "beam_off", 30], rocket_punch: "punch_right", laser_jump: "spin_attack" },
    },

    // ------------------------------------------------------------ Omni Extras
    {
        id: 110, key: "opticoid", name: "Eye Guy", color: "§e", tier: 1,
        effects: [["strength", 1], ["jump_boost", 1], ["night_vision", 0]],
        abilities: ["eye_beam", "super_eye_beam", "elemental_eyes", "galvan_leap"],
        desc: "An Opticoid covered in eyes that fire lasers.",
        anims: { eye_beam: "beam_normal", super_eye_beam: "super_beam" },
    },
    {
        id: 111, key: "perkgourmand", name: "Upchuck (Perk)", color: "§2", tier: 1,
        effects: [["health_boost", 2], ["resistance", 0]],
        abilities: ["swallow", "gut_blast", "slime_shot", "bite"],
        desc: "A Perk Gourmand that eats anything and spits it back as explosive energy.",
        anims: { swallow: "swallow", gut_blast: "shoot", slime_shot: "shoot", bite: "bite" },
    },
    {
        id: 112, key: "murkgourmand", name: "Upchuck (Murk)", color: "§2", tier: 2,
        effects: [["health_boost", 3], ["resistance", 1]],
        abilities: ["swallow", "gut_blast", "slime_shot", "bite"],
        desc: "A Murk Gourmand, the tougher cousin of the Perk.",
        anims: { swallow: "swallow", gut_blast: "shoot", slime_shot: "shoot", bite: "bite" },
    },
    {
        id: 190, key: "talpaedan", name: "Armodrillo", color: "§6", tier: 2,
        effects: [["strength", 1], ["resistance", 1], ["haste", 2]],
        immune: ["fall", "blockExplosion", "entityExplosion"],
        abilities: ["drill", "quake", "charge_leap"],
        desc: "A Talpaedan that burrows with jackhammer arms and shakes the ground.",
        anims: { drill: ["spin_both", "off_both", 20], quake: "ground_shake" },
    },
    {
        id: 192, key: "orishan", name: "Water Hazard", color: "§9", tier: 1,
        effects: [["resistance", 1], ["water_breathing", 0]],
        immune: ["drowning"],
        abilities: ["water_cannon", "water_cushion", "aqua_jet"],
        desc: "An armoured Orishan that blasts high pressure water.",
    },
    {
        id: 193, key: "amperi", name: "Ampfibian", color: "§b", tier: 2,
        effects: [["water_breathing", 0], ["night_vision", 0], ["slow_falling", 0]],
        immune: ["lightning", "drowning", "fall"], flight: 0.6,
        abilities: ["electro_bolt", "discharge"],
        desc: "An Amperi, a floating jellyfish-like being of pure electricity.",
    },
    {
        id: 299, key: "nosedeenian", name: "Buzzshock", color: "§9", tier: 2,
        effects: [["speed", 1], ["slow_falling", 0]],
        immune: ["lightning", "fall"], flight: 0.55,
        abilities: ["electro_bolt", "lightning_strike", "discharge"],
        desc: "A tiny, chaotic Nosedeenian that loves electric pranks.",
        anims: { electro_bolt: "point", lightning_strike: "boom", discharge: "conduct" },
    },
    // ------------------------------------------------------------ The Anur Trio
    {
        id: 209, key: "loboan", name: "Benwolf", color: "§7", tier: 1,
        effects: [["speed", 1], ["strength", 1], ["night_vision", 0], ["jump_boost", 1]],
        immune: ["fall"], climb: true,
        abilities: ["howl", "bite", "pounce"],
        desc: "A Loboan with sharp senses and a devastating sonic howl.",
        anims: { howl: "megahowl", bite: "bite", pounce: "punch_right" },
    },
    {
        id: 211, key: "transylian", name: "Frankenstrike", color: "§a", tier: 2,
        effects: [["strength", 2], ["resistance", 1], ["health_boost", 2]],
        immune: ["lightning", "fire", "fireTick"], melee: "shock",
        abilities: ["lightning_strike", "stun_field", "ground_slam"],
        desc: "A Transylian that stores and releases lightning.",
    },
    // ------------------------------------------------------------ Wildvine
    {
        id: 222, key: "florauna", name: "Wildvine", color: "§a", tier: 1,
        effects: [["regeneration", 1], ["strength", 0]],
        immune: ["fall"], climb: true,
        abilities: ["vine_snare", "fruit_bomb", "bloom", "camouflage"],
        desc: "A Florauna, a plant being with explosive seed pods.",
        anims: { vine_snare: "spin", fruit_bomb: "fruit", camouflage: "Burrow" },
    },
    // ------------------------------------------------------------ Aliens Untapped
    {
        id: 200, key: "merlinisapien", name: "Chamalien", color: "§5", tier: 2,
        effects: [["speed", 1], ["night_vision", 0]],
        immune: ["fall"], climb: true,
        abilities: ["camouflage", "stinger", "insect_eyes"],
        desc: "A Merlinisapien that blends into its surroundings.",
        anims: { stinger: "stinger_combo_anim" },
    },
    {
        id: 201, key: "ickthyperambuloid", name: "Walkatrout", color: "§3", tier: 1,
        effects: [["water_breathing", 0], ["speed", 0]],
        abilities: ["slide", "water_blast", "flip"],
        desc: "An Ickthyperambuloid, a slippery walking fish.",
        anims: { slide: ["slide_anim", "end_slide_anim", 20], water_blast: ["tail_brush_anim", "end_tail_brush_anim", 15], flip: "flip_anim" },
    },
    {
        id: 202, key: "splixson", name: "Ditto", color: "§f", tier: 1,
        effects: [["speed", 0], ["regeneration", 0]],
        abilities: ["clone_swarm", "taunt", "uppercut"],
        desc: "A Splixson that splits into copies of itself.",
        anims: { taunt: "taunt_anim", uppercut: "uppercut_anim", clone_swarm: "flip_anim" },
    },
    {
        id: 203, key: "oryctini", name: "Eatle", color: "§8", tier: 3,
        effects: [["strength", 2], ["resistance", 2], ["health_boost", 2]],
        immune: ["blockExplosion", "entityExplosion"],
        abilities: ["eat", "horn_beam", "ram"],
        desc: "An Oryctini that eats matter and fires it back from its horn.",
        anims: { eat: "eating_anim", ram: "bear_trap_anim" },
    },
    // ------------------------------------------------------------ Into The Omniverse
    {
        id: 501, key: "sonorosian_ov", name: "Echo Echo (Omniverse)", color: "§f", tier: 3,
        effects: [["speed", 0], ["resistance", 0]],
        immune: ["sonicBoom"],
        abilities: ["sonic_scream", "sound_wall"],
        desc: "The Omniverse look of the Sonorosian.",
    },
    {
        id: 503, key: "necrofriggian_ov", name: "Big Chill (Omniverse)", color: "§b", tier: 3,
        effects: [["slow_falling", 0], ["resistance", 1]],
        immune: ["freezing", "fall"], flight: 0.55,
        abilities: ["freeze_breath", "ice_shards", "phase"],
        desc: "The Omniverse look of the Necrofriggian.",
    },
];

/** @type {Map<number, Alien>} */
export const ALIEN_BY_ID = new Map(ALIENS.map((a) => [a.id, a]));

/** @type {Map<string, Alien>} */
export const ALIEN_BY_KEY = new Map(ALIENS.map((a) => [a.key, a]));

export const OMNITRIX_TIERS = [
    { item: "alienevo:prototype_omnitrix", name: "Prototype Omnitrix" },
    { item: "alienevo:prototype_omnitrix_phase1", name: "Evolving Omnitrix (Phase 1)" },
    { item: "alienevo:prototype_omnitrix_phase2", name: "Evolving Omnitrix (Phase 2)" },
    { item: "alienevo:prototype_omnitrix_10k", name: "Evolved Omnitrix" },
];

// Timer values from omnitrix_timer.js (ticks).
export const MAX_TIMER = 6000;
export const RECHARGE_TIMER = 3000;
