// Dữ liệu Đấu La Đại Lục: võ hồn, hồn kỹ, hồn hoàn, cấp bậc.

/** Niên hạn hồn hoàn: 10 / 100 / 1.000 / 10.000 / 100.000 năm */
export const RING_TIERS = [
  { age: "10 năm", color: "§f", name: "Bạch", mult: 1.0, exp: 10 },
  { age: "100 năm", color: "§e", name: "Hoàng", mult: 1.5, exp: 30 },
  { age: "1.000 năm", color: "§5", name: "Tử", mult: 2.4, exp: 80 },
  { age: "10.000 năm", color: "§0", name: "Hắc", mult: 4.0, exp: 220 },
  { age: "100.000 năm", color: "§c", name: "Hồng", mult: 7.0, exp: 700 },
];

/** Niên hạn tối đa an toàn cho hồn hoàn thứ i (chỉ số tier). Vượt 1 bậc: 30% thành công. */
export const RING_SAFE_TIER = [1, 2, 2, 3, 3, 3, 4, 4, 4];

export const TITLES = [
  [100, "§6§lThần"],
  [91, "§cPhong Hào Đấu La"],
  [81, "§4Hồn Đấu La"],
  [71, "§dHồn Thánh"],
  [61, "§5Hồn Đế"],
  [51, "§9Hồn Vương"],
  [41, "§3Hồn Tông"],
  [31, "§bHồn Tôn"],
  [21, "§aĐại Hồn Sư"],
  [11, "§2Hồn Sư"],
  [0, "§7Hồn Sĩ"],
];

export function titleOf(level) {
  for (const [min, name] of TITLES) if (level >= min) return name;
  return TITLES[TITLES.length - 1][1];
}

export function expToNext(level) {
  return 30 + level * 8;
}

/** Hồn cốt: mỗi bộ phận cho một hiệu ứng vĩnh viễn. */
export const SOUL_BONES = [
  { name: "Đầu Cốt", effect: "night_vision", amp: 0 },
  { name: "Khu Can Cốt", effect: "resistance", amp: 0 },
  { name: "Tả Tý Cốt", effect: "strength", amp: 0 },
  { name: "Hữu Tý Cốt", effect: "haste", amp: 1 },
  { name: "Tả Thối Cốt", effect: "speed", amp: 0 },
  { name: "Hữu Thối Cốt", effect: "jump_boost", amp: 1 },
];

/*
 * Hành động hồn kỹ (các trường số được nhân với hệ số niên hạn khi thi triển):
 *  aoe    { r, dmg, fx?, fire?, kb?, pull? }       — sát thương quanh bản thân
 *  beam   { range, dmg, fx?, fire?, kb?, n? }      — đánh mục tiêu theo hướng nhìn
 *  self   { fx }                                   — tăng ích bản thân
 *  allies { r, fx?, heal?, mana? }                 — tăng ích / hồi máu đồng đội (gồm bản thân)
 *  leap   { power, up }                            — lao về phía trước
 *  storm  { r, n, dmg, fire? }                     — sấm/lửa giáng xuống n mục tiêu ngẫu nhiên
 * fx: [[hiệu ứng, giây, cấp], ...]
 */
export const MARTIAL_SOULS = {
  blue_silver: {
    name: "§9Lam Ngân Thảo",
    weight: 22,
    particle: "minecraft:villager_happy",
    sound: "dig.grass",
    passive: [["regeneration", 0]],
    skills: [
      { name: "Triền Nhiễu", cost: 15, cd: 6, act: [{ t: "beam", range: 10, dmg: 3, fx: [["slowness", 4, 3]] }] },
      { name: "Ký Sinh", cost: 25, cd: 8, act: [{ t: "beam", range: 10, dmg: 4, fx: [["poison", 6, 1], ["weakness", 6, 0]] }] },
      { name: "Lam Ngân Lao Lung", cost: 40, cd: 12, act: [{ t: "aoe", r: 6, dmg: 4, fx: [["slowness", 6, 5], ["mining_fatigue", 6, 2]] }] },
      { name: "Lam Ngân Đột Thứ", cost: 50, cd: 10, act: [{ t: "aoe", r: 5, dmg: 8, kb: 0.8, fx: [["slowness", 3, 2]] }] },
      { name: "Lam Ngân Hồi Sinh", cost: 60, cd: 20, act: [{ t: "allies", r: 8, heal: 8, fx: [["regeneration", 8, 1]] }] },
      { name: "Lam Ngân Bá Vương Thương", cost: 80, cd: 14, act: [{ t: "beam", range: 16, dmg: 14, n: 4, kb: 1.2 }] },
      { name: "Lam Ngân Hoàng Phụ Thể", cost: 100, cd: 40, act: [{ t: "self", fx: [["resistance", 20, 1], ["regeneration", 20, 1], ["strength", 20, 1]] }] },
      { name: "Lam Ngân Thiên Võng", cost: 140, cd: 30, act: [{ t: "aoe", r: 10, dmg: 12, fx: [["slowness", 10, 6], ["weakness", 10, 2]] }] },
      { name: "Lam Ngân Hoàng Lĩnh Vực", cost: 220, cd: 60, act: [{ t: "aoe", r: 14, dmg: 18, fx: [["slowness", 12, 6], ["poison", 8, 2]] }, { t: "allies", r: 14, heal: 20, fx: [["regeneration", 15, 2]] }] },
    ],
  },
  clear_sky_hammer: {
    name: "§8Hạo Thiên Chùy",
    weight: 10,
    particle: "minecraft:huge_explosion_emitter",
    sound: "random.anvil_land",
    passive: [["strength", 0]],
    skills: [
      { name: "Trọng Kích", cost: 15, cd: 5, act: [{ t: "aoe", r: 3, dmg: 6, kb: 1.0 }] },
      { name: "Hạo Thiên Chấn", cost: 25, cd: 8, act: [{ t: "aoe", r: 5, dmg: 6, fx: [["slowness", 4, 2]] }] },
      { name: "Phá Không Chùy", cost: 35, cd: 9, act: [{ t: "beam", range: 12, dmg: 12, kb: 1.5 }] },
      { name: "Đại Lực Thần Thông", cost: 45, cd: 25, act: [{ t: "self", fx: [["strength", 20, 2], ["haste", 20, 2]] }] },
      { name: "Loạn Phi Phong Chùy Pháp", cost: 70, cd: 14, act: [{ t: "aoe", r: 5, dmg: 7 }, { t: "aoe", r: 5, dmg: 7 }, { t: "aoe", r: 6, dmg: 9, kb: 1.4 }] },
      { name: "Hạo Thiên Bá Thể", cost: 90, cd: 40, act: [{ t: "self", fx: [["resistance", 20, 2], ["absorption", 30, 3]] }] },
      { name: "Hạo Thiên Chân Thân", cost: 120, cd: 50, act: [{ t: "self", fx: [["strength", 30, 3], ["resistance", 30, 1], ["speed", 30, 1]] }] },
      { name: "Đại Tu Di Chùy", cost: 160, cd: 35, act: [{ t: "aoe", r: 10, dmg: 6, pull: 1.2 }, { t: "aoe", r: 4, dmg: 24, kb: 2.0 }] },
      { name: "Hạo Thiên Cửu Tuyệt", cost: 240, cd: 70, act: [{ t: "aoe", r: 8, dmg: 16 }, { t: "aoe", r: 10, dmg: 16 }, { t: "aoe", r: 12, dmg: 22, kb: 2.5 }] },
    ],
  },
  seven_treasure: {
    name: "§bThất Bảo Lưu Ly Tháp",
    weight: 12,
    particle: "minecraft:totem_particle",
    sound: "random.orb",
    passive: [["regeneration", 0]],
    skills: [
      { name: "Nhất Viết: Lực", cost: 15, cd: 10, act: [{ t: "allies", r: 10, fx: [["strength", 20, 0]] }] },
      { name: "Nhị Viết: Tốc", cost: 20, cd: 10, act: [{ t: "allies", r: 10, fx: [["speed", 20, 1]] }] },
      { name: "Tam Viết: Hồn", cost: 30, cd: 15, act: [{ t: "allies", r: 10, mana: 40, fx: [["regeneration", 10, 0]] }] },
      { name: "Tứ Viết: Ngự", cost: 40, cd: 15, act: [{ t: "allies", r: 10, fx: [["resistance", 20, 1]] }] },
      { name: "Ngũ Viết: Công", cost: 50, cd: 15, act: [{ t: "allies", r: 10, fx: [["strength", 20, 1], ["haste", 20, 1]] }] },
      { name: "Lục Viết: Nhược", cost: 60, cd: 15, act: [{ t: "aoe", r: 10, dmg: 2, fx: [["weakness", 15, 2], ["slowness", 15, 2]] }] },
      { name: "Thất Viết: Thất Bảo Biến", cost: 90, cd: 40, act: [{ t: "allies", r: 12, fx: [["strength", 30, 1], ["speed", 30, 1], ["resistance", 30, 1], ["regeneration", 15, 1]] }] },
      { name: "Lưu Ly Hồi Xuân", cost: 120, cd: 40, act: [{ t: "allies", r: 14, heal: 30, mana: 80, fx: [["absorption", 30, 3]] }] },
      { name: "Thất Bảo Lưu Ly Lĩnh Vực", cost: 200, cd: 70, act: [{ t: "allies", r: 16, heal: 40, mana: 150, fx: [["strength", 40, 2], ["resistance", 40, 2], ["speed", 40, 1], ["regeneration", 20, 2]] }, { t: "aoe", r: 16, dmg: 4, fx: [["weakness", 20, 3]] }] },
    ],
  },
  white_tiger: {
    name: "§fBạch Hổ",
    weight: 16,
    particle: "minecraft:critical_hit_emitter",
    sound: "mob.ravager.roar",
    passive: [["strength", 0], ["speed", 0]],
    skills: [
      { name: "Bạch Hổ Hộ Thân Chướng", cost: 15, cd: 15, act: [{ t: "self", fx: [["resistance", 10, 1], ["absorption", 15, 0]] }] },
      { name: "Bạch Hổ Liệt Quang Ba", cost: 25, cd: 7, act: [{ t: "beam", range: 12, dmg: 8, n: 3 }] },
      { name: "Bạch Hổ Kim Cương Biến", cost: 35, cd: 25, act: [{ t: "self", fx: [["strength", 20, 1], ["speed", 20, 1]] }] },
      { name: "Bạch Hổ Phá Diệt Sát", cost: 50, cd: 10, act: [{ t: "leap", power: 2.2, up: 0.4 }, { t: "aoe", r: 4, dmg: 12, kb: 1.0 }] },
      { name: "Bạch Hổ Lưu Tinh Vũ", cost: 70, cd: 14, act: [{ t: "storm", r: 10, n: 6, dmg: 9 }] },
      { name: "Bạch Hổ Liệt Quang Pháo", cost: 90, cd: 16, act: [{ t: "beam", range: 20, dmg: 20, n: 5, kb: 1.5 }] },
      { name: "Bạch Hổ Chân Thân", cost: 120, cd: 50, act: [{ t: "self", fx: [["strength", 30, 3], ["speed", 30, 2], ["resistance", 30, 1]] }] },
      { name: "U Minh Bạch Hổ", cost: 160, cd: 35, act: [{ t: "leap", power: 3, up: 0.5 }, { t: "aoe", r: 7, dmg: 26, kb: 2.0 }] },
      { name: "Bạch Hổ Lĩnh Vực", cost: 230, cd: 70, act: [{ t: "storm", r: 14, n: 12, dmg: 16 }, { t: "self", fx: [["strength", 30, 3]] }] },
    ],
  },
  phoenix: {
    name: "§6Tà Hỏa Phượng Hoàng",
    weight: 16,
    particle: "minecraft:mobflame_single",
    sound: "mob.blaze.shoot",
    passive: [["fire_resistance", 0]],
    skills: [
      { name: "Phượng Hoàng Hỏa Tuyến", cost: 15, cd: 5, act: [{ t: "beam", range: 12, dmg: 4, fire: 4 }] },
      { name: "Dục Hỏa Phượng Hoàng", cost: 25, cd: 8, act: [{ t: "aoe", r: 4, dmg: 5, fire: 5 }] },
      { name: "Phượng Dực Thiên Tường", cost: 30, cd: 10, act: [{ t: "leap", power: 1.8, up: 1.0 }, { t: "self", fx: [["slow_falling", 6, 0]] }] },
      { name: "Phượng Hoàng Xuyên Vân Kích", cost: 50, cd: 10, act: [{ t: "beam", range: 16, dmg: 12, fire: 6, n: 4 }] },
      { name: "Phượng Hoàng Hỏa Vũ", cost: 70, cd: 14, act: [{ t: "storm", r: 10, n: 8, dmg: 8, fire: 6 }] },
      { name: "Niết Bàn Trùng Sinh", cost: 90, cd: 45, act: [{ t: "allies", r: 3, heal: 30, fx: [["regeneration", 10, 2], ["fire_resistance", 60, 0]] }] },
      { name: "Phượng Hoàng Chân Thân", cost: 120, cd: 50, act: [{ t: "self", fx: [["strength", 30, 2], ["speed", 30, 1], ["fire_resistance", 60, 0]] }, { t: "aoe", r: 5, dmg: 6, fire: 8 }] },
      { name: "Phượng Hoàng Thiên Hỏa", cost: 160, cd: 35, act: [{ t: "aoe", r: 9, dmg: 18, fire: 10, kb: 1.0 }] },
      { name: "Tà Hỏa Phượng Hoàng Lĩnh Vực", cost: 230, cd: 70, act: [{ t: "storm", r: 16, n: 14, dmg: 15, fire: 10 }, { t: "aoe", r: 8, dmg: 10, fire: 10 }] },
    ],
  },
  blue_lightning_dragon: {
    name: "§3Lam Điện Bá Vương Long",
    weight: 8,
    particle: "minecraft:electric_spark_particle",
    sound: "ambient.weather.thunder",
    passive: [["resistance", 0]],
    lightning: true,
    skills: [
      { name: "Lôi Điện Kích", cost: 15, cd: 5, act: [{ t: "beam", range: 14, dmg: 6 }] },
      { name: "Lôi Long Trảo", cost: 25, cd: 8, act: [{ t: "aoe", r: 4, dmg: 7, kb: 0.8 }] },
      { name: "Lam Điện Hộ Thể", cost: 30, cd: 20, act: [{ t: "self", fx: [["resistance", 20, 1], ["speed", 20, 0]] }] },
      { name: "Lôi Đình Vạn Quân", cost: 55, cd: 12, act: [{ t: "storm", r: 10, n: 5, dmg: 12 }] },
      { name: "Bá Vương Long Tức", cost: 75, cd: 14, act: [{ t: "beam", range: 22, dmg: 18, n: 5, kb: 1.2 }] },
      { name: "Long Uy", cost: 90, cd: 25, act: [{ t: "aoe", r: 12, dmg: 4, fx: [["weakness", 15, 2], ["slowness", 10, 2]] }] },
      { name: "Lam Điện Bá Vương Long Chân Thân", cost: 130, cd: 50, act: [{ t: "self", fx: [["strength", 30, 3], ["resistance", 30, 2], ["speed", 30, 1]] }] },
      { name: "Cửu Thiên Lôi Phạt", cost: 170, cd: 35, act: [{ t: "storm", r: 14, n: 10, dmg: 18 }] },
      { name: "Lôi Đình Lĩnh Vực", cost: 240, cd: 70, act: [{ t: "storm", r: 18, n: 16, dmg: 22 }, { t: "aoe", r: 6, dmg: 12, kb: 2.0 }] },
    ],
  },
};

/** Sinh vật có thể trở thành hồn thú khi xuất hiện. */
export const BEAST_TYPES = {
  "minecraft:zombie": "Thi Quỷ",
  "minecraft:husk": "Sa Mạc Thi",
  "minecraft:skeleton": "Cốt Ma",
  "minecraft:stray": "Băng Cốt Ma",
  "minecraft:spider": "Nhân Diện Ma Chu",
  "minecraft:cave_spider": "Độc Chu",
  "minecraft:wolf": "Phong Lang",
  "minecraft:polar_bear": "Băng Hùng",
  "minecraft:enderman": "U Minh Ma",
  "minecraft:ravager": "Thái Thản Cự Viên",
  "minecraft:hoglin": "Cuồng Bạo Trư",
  "minecraft:wither_skeleton": "Tà Hồn Cốt",
  "minecraft:piglin_brute": "Bạo Hùng Vương",
  "minecraft:blaze": "Hỏa Linh",
  "minecraft:creeper": "Bạo Liệt Thú",
  "minecraft:witch": "Ma Hồn Yêu",
};

/** Trọng số sinh hồn thú theo niên hạn. */
export const BEAST_TIER_WEIGHTS = [50, 30, 14, 5, 1];
export const BEAST_CHANCE = 0.3;

export function weightedPick(weights) {
  const total = weights.reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (let i = 0; i < weights.length; i++) {
    r -= weights[i];
    if (r < 0) return i;
  }
  return weights.length - 1;
}
