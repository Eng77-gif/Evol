import {
  world,
  system,
  ItemStack,
  GameMode,
  EntityDamageCause,
  EntityInitializationCause,
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
} from "@minecraft/server";
import { ActionFormData, MessageFormData } from "@minecraft/server-ui";
import {
  RING_TIERS,
  RING_SAFE_TIER,
  MARTIAL_SOULS,
  SOUL_BONES,
  BEAST_TYPES,
  BEAST_TIER_WEIGHTS,
  BEAST_CHANCE,
  titleOf,
  expToNext,
  weightedPick,
} from "./data.js";
import { beastName } from "./beasts.js";

const P = "dld:";
const TARGET_EXCLUDE_TYPES = ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:armor_stand", "minecraft:lightning_bolt"];
const DIMENSIONS = ["overworld", "nether", "the_end"];

// ───────────────────────── Trạng thái người chơi ─────────────────────────

function get(player, key, def) {
  const v = player.getDynamicProperty(P + key);
  return v === undefined ? def : v;
}
function set(player, key, value) {
  player.setDynamicProperty(P + key, value);
}

function getState(player) {
  return {
    soul: get(player, "soul", ""),
    innate: get(player, "innate", 0),
    level: get(player, "level", 0),
    exp: get(player, "exp", 0),
    mana: get(player, "mana", 0),
    rings: String(get(player, "rings", "")),
    skill: get(player, "skill", 0),
    active: get(player, "active", false),
    bones: String(get(player, "bones", "000000")),
  };
}

function maxMana(st) {
  return 100 + st.level * 15 + st.innate * 10;
}

function soulOf(st) {
  return MARTIAL_SOULS[st.soul];
}

function ringsText(rings) {
  return [...rings].map((t) => RING_TIERS[+t].color + "◉").join("") || "§7(chưa có)";
}

/** Cấp tối đa hiện có thể đạt với số hồn hoàn đang có. */
function levelCap(st) {
  return Math.min(100, (st.rings.length + 1) * 10);
}

const lastCapNotice = new Map();

function addExp(player, amount) {
  const st = getState(player);
  if (!st.soul || st.level >= 100) return;
  let { level, exp } = st;
  exp += amount;
  const cap = levelCap(st);
  let leveled = false;
  while (level < 100 && exp >= expToNext(level)) {
    if (level >= cap) {
      exp = expToNext(level);
      const now = system.currentTick;
      if ((lastCapNotice.get(player.id) ?? -9999) + 600 < now) {
        lastCapNotice.set(player.id, now);
        player.sendMessage(`§e⚠ Hồn lực đã đạt bình cảnh cấp ${level}! Hãy săn hồn thú và hấp thu §6hồn hoàn thứ ${st.rings.length + 1}§e để đột phá.`);
      }
      break;
    }
    exp -= expToNext(level);
    level++;
    leveled = true;
  }
  set(player, "level", level);
  set(player, "exp", exp);
  if (leveled) {
    const newTitle = titleOf(level);
    player.onScreenDisplay.setTitle("§6Đột phá!", { subtitle: `${newTitle} §f- Cấp ${level}`, fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
    player.playSound("random.levelup");
    if (titleOf(st.level) !== newTitle) world.sendMessage(`§6✦ ${player.name} §fđã đột phá thành ${newTitle}§f!`);
  }
}

// ───────────────────────── Tiện ích ─────────────────────────

function isCreative(player) {
  try {
    return player.getGameMode() === GameMode.Creative;
  } catch {
    return false;
  }
}

function consumeHeld(player) {
  if (isCreative(player)) return;
  const inv = player.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  const slot = player.selectedSlotIndex;
  const item = inv.getItem(slot);
  if (!item) return;
  if (item.amount > 1) {
    item.amount -= 1;
    inv.setItem(slot, item);
  } else inv.setItem(slot, undefined);
}

function particle(dim, id, loc) {
  try {
    dim.spawnParticle(id, loc);
  } catch {}
}

function sound(player, id, pitch = 1) {
  try {
    player.dimension.playSound(id, player.location, { volume: 1, pitch });
  } catch {}
}

function addFx(entity, list) {
  for (const [id, sec, amp] of list ?? []) {
    try {
      entity.addEffect(id, Math.round(sec * 20), { amplifier: amp, showParticles: true });
    } catch {}
  }
}

function pvpOn() {
  return world.getDynamicProperty(P + "pvp") === true;
}

function validTarget(caster, e) {
  if (!e.isValid || e.id === caster.id) return false;
  if (e.typeId === "minecraft:player") return pvpOn();
  if (!e.getComponent("minecraft:health")) return false;
  try {
    const tame = e.getComponent("minecraft:tameable");
    if (tame?.isTamed) return false;
  } catch {}
  return !["minecraft:villager_v2", "minecraft:wandering_trader", "minecraft:iron_golem", "minecraft:snow_golem"].includes(e.typeId);
}

function nearbyTargets(caster, r) {
  return caster.dimension
    .getEntities({ location: caster.location, maxDistance: r, excludeFamilies: ["inanimate"], excludeTypes: TARGET_EXCLUDE_TYPES })
    .filter((e) => validTarget(caster, e));
}

function damage(caster, target, amount, opts = {}) {
  try {
    target.applyDamage(amount, {
      cause: opts.lightning ? EntityDamageCause.lightning : EntityDamageCause.entityAttack,
      damagingEntity: caster,
    });
    if (opts.fire) target.setOnFire(opts.fire, true);
    if (opts.fx) addFx(target, opts.fx);
    if (opts.kb) {
      const dx = target.location.x - caster.location.x;
      const dz = target.location.z - caster.location.z;
      const len = Math.hypot(dx, dz) || 1;
      const s = opts.kb * (opts.pull ? -1 : 1);
      target.applyKnockback({ x: (dx / len) * s, z: (dz / len) * s }, opts.pull ? 0.1 : 0.35);
    }
  } catch {}
}

// ───────────────────────── Hồn kỹ ─────────────────────────

const cooldowns = new Map(); // player.id -> { [skillIdx]: tickReady }

function runAction(player, soul, act, mult) {
  if (!player.isValid) return;
  const dim = player.dimension;
  const loc = player.location;
  const dmgOpts = { fire: act.fire, fx: act.fx, kb: act.kb ?? act.pull, pull: !!act.pull, lightning: !!soul.lightning };
  switch (act.t) {
    case "aoe": {
      for (let i = 0; i < 16; i++) {
        const a = (i / 16) * Math.PI * 2;
        particle(dim, soul.particle, { x: loc.x + Math.cos(a) * act.r * 0.7, y: loc.y + 0.5, z: loc.z + Math.sin(a) * act.r * 0.7 });
      }
      for (const t of nearbyTargets(player, act.r)) damage(player, t, act.dmg * mult, dmgOpts);
      break;
    }
    case "beam": {
      const head = player.getHeadLocation();
      const d = player.getViewDirection();
      for (let i = 1; i <= act.range; i += 1) {
        particle(dim, soul.particle, { x: head.x + d.x * i, y: head.y + d.y * i, z: head.z + d.z * i });
      }
      const hits = player
        .getEntitiesFromViewDirection({ maxDistance: act.range, excludeFamilies: ["inanimate"], excludeTypes: TARGET_EXCLUDE_TYPES })
        .map((h) => h.entity)
        .filter((e) => validTarget(player, e))
        .slice(0, act.n ?? 1);
      for (const t of hits) {
        damage(player, t, act.dmg * mult, dmgOpts);
        if (soul.lightning) particle(dim, "minecraft:electric_spark_particle", t.location);
      }
      break;
    }
    case "self":
      addFx(player, act.fx);
      particle(dim, "minecraft:totem_particle", { x: loc.x, y: loc.y + 1, z: loc.z });
      break;
    case "allies": {
      const allies = dim.getPlayers({ location: loc, maxDistance: act.r });
      for (const a of allies) {
        addFx(a, act.fx);
        if (act.heal) {
          const hp = a.getComponent("minecraft:health");
          if (hp) hp.setCurrentValue(Math.min(hp.effectiveMax, hp.currentValue + act.heal * (1 + (mult - 1) * 0.5)));
        }
        if (act.mana) {
          const st = getState(a);
          if (st.soul) set(a, "mana", Math.min(maxMana(st), st.mana + act.mana));
        }
        particle(dim, "minecraft:villager_happy", { x: a.location.x, y: a.location.y + 1, z: a.location.z });
      }
      break;
    }
    case "leap": {
      const d = player.getViewDirection();
      try {
        player.applyKnockback({ x: d.x * act.power, z: d.z * act.power }, act.up);
      } catch {}
      break;
    }
    case "storm": {
      const targets = nearbyTargets(player, act.r).sort(() => Math.random() - 0.5).slice(0, act.n);
      targets.forEach((t, i) => {
        system.runTimeout(() => {
          if (!t.isValid || !player.isValid) return;
          const tl = t.location;
          const far = Math.hypot(tl.x - player.location.x, tl.z - player.location.z) > 5;
          if (soul.lightning && far) {
            try {
              t.dimension.spawnEntity("minecraft:lightning_bolt", tl);
            } catch {}
          }
          particle(t.dimension, soul.particle, { x: tl.x, y: tl.y + 1, z: tl.z });
          particle(t.dimension, "minecraft:large_explosion", { x: tl.x, y: tl.y + 0.5, z: tl.z });
          damage(player, t, act.dmg * mult, dmgOpts);
        }, i * 4);
      });
      break;
    }
  }
}

function castSkill(player) {
  const st = getState(player);
  const soul = soulOf(st);
  if (!soul) {
    player.sendMessage("§cBạn chưa thức tỉnh võ hồn! Hãy dùng §dThủy Tinh Thức Tỉnh§c.");
    return;
  }
  if (!st.active) {
    set(player, "active", true);
    player.onScreenDisplay.setActionBar(`§aVõ hồn phụ thể: ${soul.name}`);
    sound(player, soul.sound);
  }
  if (st.rings.length === 0) {
    player.sendMessage("§7Bạn chưa có hồn hoàn nên chưa có hồn kỹ. Hãy săn hồn thú!");
    return;
  }
  const idx = Math.min(st.skill, st.rings.length - 1);
  const skill = soul.skills[idx];
  const tier = RING_TIERS[+st.rings[idx]];
  const cds = cooldowns.get(player.id) ?? {};
  const now = system.currentTick;
  if ((cds[idx] ?? 0) > now) {
    player.onScreenDisplay.setActionBar(`§c${skill.name} đang hồi: ${Math.ceil((cds[idx] - now) / 20)}s`);
    return;
  }
  // Hồn hoàn niên hạn cao tiêu hao nhiều hồn lực hơn
  const cost = Math.round(skill.cost * (1 + +st.rings[idx] * 0.15));
  if (st.mana < cost) {
    player.onScreenDisplay.setActionBar(`§cHồn lực không đủ (${Math.floor(st.mana)}/${cost})`);
    return;
  }
  set(player, "mana", st.mana - cost);
  cds[idx] = now + skill.cd * 20;
  cooldowns.set(player.id, cds);

  const mult = tier.mult * (1 + st.level / 50);
  player.onScreenDisplay.setTitle(" ", {
    subtitle: `${tier.color}◉ §fĐệ ${idx + 1} hồn kỹ: §e${skill.name}`,
    fadeInDuration: 2,
    stayDuration: 30,
    fadeOutDuration: 8,
  });
  sound(player, soul.sound, 1.2);
  skill.act.forEach((act, i) => system.runTimeout(() => runAction(player, soul, act, mult), i * 6));
}

function cycleSkill(player, dir = 1) {
  const st = getState(player);
  if (!st.rings.length) return;
  const next = (st.skill + dir + st.rings.length) % st.rings.length;
  set(player, "skill", next);
  const soul = soulOf(st);
  player.onScreenDisplay.setActionBar(`§fChọn hồn kỹ ${RING_TIERS[+st.rings[next]].color}◉${next + 1}§f: §e${soul.skills[next].name}`);
}

// ───────────────────────── Thức tỉnh, hồn hoàn, hồn cốt ─────────────────────────

function awaken(player) {
  const st = getState(player);
  if (st.soul) {
    player.sendMessage(`§7Bạn đã thức tỉnh võ hồn ${soulOf(st)?.name ?? st.soul}§7 rồi.`);
    return;
  }
  const keys = Object.keys(MARTIAL_SOULS);
  const soulId = keys[weightedPick(keys.map((k) => MARTIAL_SOULS[k].weight))];
  const innate = Math.random() < 0.08 ? 10 : 1 + Math.floor(Math.random() * 9);
  set(player, "soul", soulId);
  set(player, "innate", innate);
  set(player, "level", innate);
  set(player, "exp", 0);
  set(player, "rings", "");
  set(player, "skill", 0);
  set(player, "active", true);
  set(player, "mana", maxMana(getState(player)));
  consumeHeld(player);

  const soul = MARTIAL_SOULS[soulId];
  player.onScreenDisplay.setTitle("§dVõ Hồn Thức Tỉnh!", { subtitle: soul.name, fadeInDuration: 10, stayDuration: 60, fadeOutDuration: 20 });
  sound(player, "random.totem");
  addFx(player, [["levitation", 2, 0], ["slow_falling", 5, 0]]);
  for (let i = 0; i < 20; i++) system.runTimeout(() => player.isValid && particle(player.dimension, soul.particle, player.location), i * 2);
  const innateText = innate === 10 ? "§6Tiên Thiên Mãn Hồn Lực (10)!" : `§fTiên thiên hồn lực: §b${innate}`;
  world.sendMessage(`§d✦ ${player.name} §fđã thức tỉnh võ hồn ${soul.name}§f — ${innateText}`);
}

function absorbRing(player, tier) {
  const st = getState(player);
  if (!st.soul) {
    player.sendMessage("§cPhải thức tỉnh võ hồn trước khi hấp thu hồn hoàn.");
    return;
  }
  const idx = st.rings.length;
  if (idx >= 9) {
    player.sendMessage("§7Bạn đã có đủ 9 hồn hoàn.");
    return;
  }
  const need = (idx + 1) * 10;
  if (st.level < need) {
    player.sendMessage(`§cHồn lực chưa đủ! Hồn hoàn thứ ${idx + 1} cần đạt cấp §e${need}§c (hiện tại ${st.level}).`);
    return;
  }
  const safe = RING_SAFE_TIER[idx];
  const t = RING_TIERS[tier];
  let ok;
  if (tier <= safe) ok = true;
  else if (tier === safe + 1) ok = Math.random() < (st.innate >= 10 ? 0.5 : 0.3);
  else ok = false;

  consumeHeld(player);
  if (!ok) {
    const hp = player.getComponent("minecraft:health");
    try {
      player.applyDamage(Math.max(4, (hp?.effectiveMax ?? 20) * 0.45), { cause: EntityDamageCause.magic });
    } catch {}
    addFx(player, [["nausea", 10, 0], ["slowness", 10, 2], ["weakness", 20, 1]]);
    player.onScreenDisplay.setTitle("§cHấp thu thất bại!", { subtitle: `Hồn hoàn ${t.age} vượt quá giới hạn thân thể`, fadeInDuration: 5, stayDuration: 50, fadeOutDuration: 10 });
    sound(player, "random.explode", 0.8);
    return;
  }
  set(player, "rings", st.rings + tier);
  set(player, "skill", idx);
  set(player, "active", true);
  addFx(player, [["levitation", 3, 0], ["slow_falling", 6, 0], ["regeneration", 10, 2]]);
  for (let i = 0; i < 30; i++) {
    system.runTimeout(() => {
      if (!player.isValid) return;
      const a = i * 0.6;
      const l = player.location;
      particle(player.dimension, `dld:soul_ring_${tier}`, { x: l.x + Math.cos(a) * 1.2, y: l.y + i * 0.08, z: l.z + Math.sin(a) * 1.2 });
    }, i);
  }
  sound(player, "random.levelup", 0.7);
  const soul = soulOf(st);
  player.onScreenDisplay.setTitle(`${t.color}Hồn hoàn thứ ${idx + 1}`, { subtitle: `§fHồn kỹ mới: §e${soul.skills[idx].name}`, fadeInDuration: 10, stayDuration: 60, fadeOutDuration: 20 });
  world.sendMessage(`§6✦ ${player.name} §fđã hấp thu ${t.color}hồn hoàn ${t.age}§f làm hồn hoàn thứ ${idx + 1}! ${ringsText(st.rings + tier)}`);
  addExp(player, t.exp);
}

function useSoulBone(player) {
  const st = getState(player);
  if (!st.soul) {
    player.sendMessage("§cPhải thức tỉnh võ hồn trước khi dung hợp hồn cốt.");
    return;
  }
  const bones = [...st.bones.padEnd(6, "0")];
  const free = bones.map((b, i) => (b === "0" ? i : -1)).filter((i) => i >= 0);
  if (!free.length) {
    player.sendMessage("§7Bạn đã dung hợp đủ 6 khối hồn cốt.");
    return;
  }
  const pick = free[Math.floor(Math.random() * free.length)];
  bones[pick] = "1";
  set(player, "bones", bones.join(""));
  consumeHeld(player);
  player.onScreenDisplay.setTitle("§6Dung hợp hồn cốt", { subtitle: `§e${SOUL_BONES[pick].name}`, fadeInDuration: 5, stayDuration: 50, fadeOutDuration: 10 });
  sound(player, "random.totem", 1.3);
  world.sendMessage(`§6✦ ${player.name} §fđã dung hợp hồn cốt §e${SOUL_BONES[pick].name}§f!`);
}

function eatHerb(player) {
  const st = getState(player);
  if (!st.soul) return;
  set(player, "mana", maxMana(st));
  addFx(player, [["regeneration", 15, 2], ["absorption", 60, 2]]);
  addExp(player, 120 + st.level * 4);
  player.sendMessage("§aTiên thảo hóa thành hồn lực tràn vào cơ thể bạn!");
}

// ───────────────────────── Giao diện ─────────────────────────

async function showForm(player, form) {
  for (let i = 0; i < 10; i++) {
    const res = await form.show(player);
    if (res.cancelationReason !== "UserBusy") return res;
    await new Promise((r) => system.runTimeout(r, 10));
  }
}

function profileText(player) {
  const st = getState(player);
  const soul = soulOf(st);
  if (!soul) return "§7Chưa thức tỉnh võ hồn.\n\nDùng §dThủy Tinh Thức Tỉnh§7 (chế tạo: 4 thạch anh tím + 1 kim cương).";
  const bones = [...st.bones].map((b, i) => (b === "1" ? SOUL_BONES[i].name : null)).filter(Boolean);
  return [
    `§fVõ hồn: ${soul.name}`,
    `§fDanh hiệu: ${titleOf(st.level)} §f(Cấp ${st.level})`,
    `§fTiên thiên hồn lực: §b${st.innate}`,
    `§fKinh nghiệm: §a${st.exp}/${expToNext(st.level)}`,
    `§fHồn lực: §9${Math.floor(st.mana)}/${maxMana(st)}`,
    `§fHồn hoàn: ${ringsText(st.rings)}`,
    `§fHồn cốt: §e${bones.length ? bones.join(", ") : "§7không có"}`,
    `§fTrạng thái: ${st.active ? "§aĐang phụ thể" : "§7Thu hồi"}`,
  ].join("\n");
}

async function openMenu(player) {
  const st = getState(player);
  const form = new ActionFormData()
    .title("§l§6Đấu La Đại Lục")
    .body(profileText(player))
    .button("§lChọn hồn kỹ")
    .button(st.active ? "§lThu hồi võ hồn" : "§lVõ hồn phụ thể")
    .button("§lHướng dẫn")
    .button("Đóng");
  const res = await showForm(player, form);
  if (!res || res.canceled) return;
  if (res.selection === 0) return openSkillMenu(player);
  if (res.selection === 1) {
    if (!st.soul) return;
    set(player, "active", !st.active);
    player.onScreenDisplay.setActionBar(st.active ? "§7Đã thu hồi võ hồn" : `§aVõ hồn phụ thể: ${soulOf(st).name}`);
    if (!st.active) sound(player, soulOf(st).sound);
  }
  if (res.selection === 2) return openGuide(player);
}

async function openSkillMenu(player) {
  const st = getState(player);
  const soul = soulOf(st);
  if (!soul || !st.rings.length) {
    player.sendMessage("§7Chưa có hồn kỹ nào.");
    return;
  }
  const form = new ActionFormData().title("§lHồn kỹ").body("Chọn hồn kỹ sẽ thi triển khi dùng §6Võ Hồn Lệnh§r:");
  [...st.rings].forEach((t, i) => {
    const s = soul.skills[i];
    form.button(`${RING_TIERS[+t].color}◉ §r${i + 1}. ${s.name}${i === st.skill ? " §a✔" : ""}\n§8Hồn lực ${Math.round(s.cost * (1 + +t * 0.15))} | Hồi ${s.cd}s`);
  });
  const res = await showForm(player, form);
  if (!res || res.canceled || res.selection === undefined) return;
  set(player, "skill", res.selection);
  player.onScreenDisplay.setActionBar(`§fĐã chọn: §e${soul.skills[res.selection].name}`);
}

async function openGuide(player) {
  const body = [
    "§l§61. Thức tỉnh võ hồn§r",
    "Dùng §dThủy Tinh Thức Tỉnh§r để nhận ngẫu nhiên 1 trong 6 võ hồn: Lam Ngân Thảo, Hạo Thiên Chùy, Thất Bảo Lưu Ly Tháp, Bạch Hổ, Tà Hỏa Phượng Hoàng, Lam Điện Bá Vương Long.",
    "",
    "§l§62. Tu luyện§r",
    "Giết quái và §bngồi xuống (sneak) đứng yên§r để minh tưởng, tăng hồn lực. Ăn §aTiên Thảo§r (đôi khi rơi khi phá cỏ) để tăng mạnh.",
    "",
    "§l§63. Hồn thú & hồn hoàn§r",
    "Quái vật có thể là §fHồn Thú§r 10 / 100 / 1.000 / 10.000 / 100.000 năm. Giết chúng để rơi hồn hoàn. Mỗi 10 cấp phải hấp thu 1 hồn hoàn để đột phá.",
    "Giới hạn an toàn: hoàn 1 ≤ 100 năm, hoàn 2-3 ≤ 1.000 năm, hoàn 4-6 ≤ 10.000 năm, hoàn 7-9 ≤ 100.000 năm. Vượt 1 bậc: 30% thành công (Mãn hồn lực: 50%).",
    "",
    "§l§64. Hồn kỹ§r",
    "Mỗi hồn hoàn cho 1 hồn kỹ. Cầm §6Võ Hồn Lệnh§r: dùng = thi triển; ngồi + dùng = mở menu. Niên hạn càng cao, hồn kỹ càng mạnh.",
    "",
    "§l§65. Hồn cốt§r",
    "Hồn thú vạn năm trở lên có thể rơi §eHồn Cốt§r — dung hợp để nhận 1 trong 6 hiệu ứng vĩnh viễn.",
    "",
    "§l§6Lệnh§r: /dld:hoso, /dld:pvp (OP), /dld:reset (OP), /dld:setlevel (OP)",
  ].join("\n");
  await showForm(player, new MessageFormData().title("§lHướng dẫn").body(body).button1("Đã hiểu").button2("Quay lại"));
}

// ───────────────────────── Sự kiện ─────────────────────────

const lastUse = new Map();

function onUseItem(player, item) {
  if (!item || !item.typeId.startsWith(P)) return;
  const now = system.currentTick;
  if ((lastUse.get(player.id) ?? -10) + 4 > now) return;
  lastUse.set(player.id, now);

  const id = item.typeId.slice(P.length);
  if (id === "awakening_crystal") return awaken(player);
  if (id === "soul_bone") return useSoulBone(player);
  if (id.startsWith("soul_ring_")) return absorbRing(player, +id.slice("soul_ring_".length));
  if (id === "spirit_token") {
    if (player.isSneaking) openMenu(player);
    else castSkill(player);
  }
}

world.afterEvents.itemUse.subscribe((ev) => onUseItem(ev.source, ev.itemStack));
world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  if (ev.isFirstEvent) onUseItem(ev.player, ev.itemStack);
});

world.afterEvents.itemCompleteUse.subscribe((ev) => {
  if (ev.itemStack?.typeId === "dld:immortal_herb") eatHerb(ev.source);
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  const player = ev.player;
  if (!ev.initialSpawn || get(player, "kit", false)) return;
  set(player, "kit", true);
  const inv = player.getComponent("minecraft:inventory")?.container;
  inv?.addItem(new ItemStack("dld:awakening_crystal", 1));
  inv?.addItem(new ItemStack("dld:spirit_token", 1));
  player.sendMessage("§6§l[Đấu La Đại Lục]§r §fChào mừng hồn sư! Dùng §dThủy Tinh Thức Tỉnh§f để thức tỉnh võ hồn, ngồi + dùng §6Võ Hồn Lệnh§f để mở menu.");
});

// Hồn thú xuất hiện
world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  if (ev.cause !== EntityInitializationCause.Spawned && ev.cause !== EntityInitializationCause.Born) return;
  if (!e.isValid || !(e.typeId in BEAST_TYPES) || Math.random() > BEAST_CHANCE) return;
  const tier = weightedPick(BEAST_TIER_WEIGHTS);
  const t = RING_TIERS[tier];
  const forever = 20000000;
  try {
    e.setDynamicProperty(P + "tier", tier);
    e.addTag("dld_beast");
    e.addEffect("health_boost", forever, { amplifier: tier * 2, showParticles: false });
    e.addEffect("regeneration", 200, { amplifier: 4, showParticles: false });
    if (tier >= 1) e.addEffect("strength", forever, { amplifier: tier - 1, showParticles: false });
    if (tier >= 2) e.addEffect("resistance", forever, { amplifier: Math.min(tier - 2, 2), showParticles: false });
    if (tier >= 3) e.addEffect("speed", forever, { amplifier: 0, showParticles: false });
    // Chỉ đặt tên cho hồn thú vạn năm trở lên để không chặn việc quái tự biến mất
    if (tier >= 3) e.nameTag = `${t.color}${BEAST_TYPES[e.typeId]} §f${t.age}`;
  } catch {}
});

// Săn hồn thú
world.afterEvents.entityDie.subscribe((ev) => {
  const dead = ev.deadEntity;
  const killer = ev.damageSource.damagingEntity;
  if (!killer || killer.typeId !== "minecraft:player" || dead.typeId === "minecraft:player") return;
  let tier;
  let loc;
  let dim;
  try {
    tier = dead.getDynamicProperty(P + "tier");
    loc = dead.location;
    dim = dead.dimension;
  } catch {
    return;
  }
  if (tier === undefined) {
    addExp(killer, 2);
    return;
  }
  const t = RING_TIERS[tier];
  dim.spawnItem(new ItemStack(`dld:soul_ring_${tier}`, 1), loc);
  const boneChance = [0, 0, 0.01, 0.08, 0.35][tier];
  if (Math.random() < boneChance) {
    dim.spawnItem(new ItemStack("dld:soul_bone", 1), loc);
    world.sendMessage(`§6✦ Hồn cốt xuất thế! ${killer.name} §fđã nhận được §eHồn Cốt§f từ hồn thú ${t.color}${t.age}§f!`);
  }
  if (tier >= 2 && Math.random() < 0.15) dim.spawnItem(new ItemStack("dld:immortal_herb", 1), loc);
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    particle(dim, `dld:soul_ring_${tier}`, { x: loc.x + Math.cos(a), y: loc.y + 0.6, z: loc.z + Math.sin(a) });
  }
  killer.onScreenDisplay.setActionBar(`§fĐã săn ${t.color}Hồn Thú ${t.age}§f — hồn hoàn rơi ra!`);
  addExp(killer, t.exp);
});

// Tiên thảo mọc trong cỏ
world.afterEvents.playerBreakBlock.subscribe((ev) => {
  const id = ev.brokenBlockPermutation.type.id;
  if (!["minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern"].includes(id)) return;
  if (Math.random() < 0.01) {
    ev.dimension.spawnItem(new ItemStack("dld:immortal_herb", 1), ev.block.center());
    ev.player.sendMessage("§aBạn tìm thấy một gốc §2Tiên Thảo§a!");
  }
});

// ───────────────────────── Vòng lặp ─────────────────────────

// Mỗi giây: hồi hồn lực, minh tưởng, hiệu ứng bị động
system.runInterval(() => {
  for (const player of world.getAllPlayers()) {
    const st = getState(player);
    const soul = soulOf(st);
    [...st.bones].forEach((b, i) => {
      if (b === "1") {
        const bone = SOUL_BONES[i];
        try {
          player.addEffect(bone.effect, 300, { amplifier: bone.amp, showParticles: false });
        } catch {}
      }
    });
    if (!soul) continue;
    const v = player.getVelocity();
    const meditating = player.isSneaking && Math.abs(v.x) + Math.abs(v.z) < 0.01 && player.isOnGround;
    const regen = (2 + st.level / 5) * (meditating ? 3 : 1);
    const max = maxMana(st);
    if (st.mana < max) set(player, "mana", Math.min(max, st.mana + regen));
    if (meditating) {
      addExp(player, 1 + Math.floor(st.level / 10));
      const l = player.location;
      particle(player.dimension, "minecraft:villager_happy", { x: l.x + (Math.random() - 0.5), y: l.y + 1.5, z: l.z + (Math.random() - 0.5) });
    }
    if (st.active) {
      for (const [id, amp] of soul.passive) {
        try {
          player.addEffect(id, 60, { amplifier: amp, showParticles: false });
        } catch {}
      }
    }
  }
}, 20);

// Mỗi nửa giây: thanh trạng thái, hiệu ứng hồn hoàn quanh người
let phase = 0;
system.runInterval(() => {
  phase += 0.35;
  for (const player of world.getAllPlayers()) {
    const st = getState(player);
    const soul = soulOf(st);
    if (!soul) continue;
    const holding = player.getComponent("minecraft:inventory")?.container?.getItem(player.selectedSlotIndex)?.typeId === "dld:spirit_token";

    if (st.active && st.rings.length) {
      const l = player.location;
      [...st.rings].forEach((t, k) => {
        const y = l.y + 0.15 + ((k * 0.2 + phase * 0.25) % 2.0);
        for (let i = 0; i < 8; i++) {
          const a = (i / 8) * Math.PI * 2 + phase + k;
          particle(player.dimension, `dld:soul_ring_${t}`, { x: l.x + Math.cos(a) * 0.85, y, z: l.z + Math.sin(a) * 0.85 });
        }
      });
    }

    if (!holding && !st.active) continue;
    let bar = `${titleOf(st.level)} §7Lv.${st.level} §8| §9Hồn lực ${Math.floor(st.mana)}/${maxMana(st)}`;
    if (st.rings.length) {
      const idx = Math.min(st.skill, st.rings.length - 1);
      const ready = (cooldowns.get(player.id)?.[idx] ?? 0) - system.currentTick;
      bar += ` §8| ${RING_TIERS[+st.rings[idx]].color}◉§e${soul.skills[idx].name}${ready > 0 ? ` §c${Math.ceil(ready / 20)}s` : ""}`;
    }
    try {
      const hit = player.getEntitiesFromViewDirection({ maxDistance: 24 })[0]?.entity;
      if (hit?.hasTag("dld_beast")) {
        const t = RING_TIERS[hit.getDynamicProperty(P + "tier") ?? 0];
        bar += `\n${t.color}Hồn Thú ${t.age} §7(${beastName(hit.typeId, BEAST_TYPES[hit.typeId] ?? hit.typeId)})`;
      }
    } catch {}
    player.onScreenDisplay.setActionBar(bar);
  }
}, 10);

// Hào quang hồn thú niên hạn cao
system.runInterval(() => {
  for (const id of DIMENSIONS) {
    let beasts;
    try {
      beasts = world.getDimension(id).getEntities({ tags: ["dld_beast"] });
    } catch {
      continue;
    }
    for (const b of beasts) {
      try {
        const tier = b.getDynamicProperty(P + "tier") ?? 0;
        if (tier < 2) continue;
        const l = b.location;
        for (let i = 0; i < 6; i++) {
          const a = (i / 6) * Math.PI * 2 + phase;
          particle(b.dimension, `dld:soul_ring_${tier}`, { x: l.x + Math.cos(a) * 0.8, y: l.y + 0.3, z: l.z + Math.sin(a) * 0.8 });
        }
      } catch {}
    }
  }
}, 40);

// ───────────────────────── Lệnh tùy chỉnh ─────────────────────────

system.beforeEvents.startup.subscribe(({ customCommandRegistry: reg }) => {
  const playerOf = (origin) => {
    const e = origin.sourceEntity;
    return e?.typeId === "minecraft:player" ? e : undefined;
  };

  reg.registerCommand(
    { name: "dld:hoso", description: "Mở hồ sơ hồn sư Đấu La Đại Lục", permissionLevel: CommandPermissionLevel.Any },
    (origin) => {
      const p = playerOf(origin);
      if (!p) return { status: CustomCommandStatus.Failure, message: "Chỉ người chơi dùng được." };
      system.run(() => openMenu(p));
      return { status: CustomCommandStatus.Success };
    },
  );

  reg.registerCommand(
    { name: "dld:pvp", description: "Bật/tắt hồn kỹ gây sát thương lên người chơi", permissionLevel: CommandPermissionLevel.GameDirectors },
    () => {
      system.run(() => {
        const on = !pvpOn();
        world.setDynamicProperty(P + "pvp", on);
        world.sendMessage(`§6[Đấu La]§f PvP hồn kỹ: ${on ? "§cBẬT" : "§aTẮT"}`);
      });
      return { status: CustomCommandStatus.Success };
    },
  );

  reg.registerCommand(
    { name: "dld:reset", description: "Xóa võ hồn của bản thân để thức tỉnh lại", permissionLevel: CommandPermissionLevel.GameDirectors },
    (origin) => {
      const p = playerOf(origin);
      if (!p) return { status: CustomCommandStatus.Failure, message: "Chỉ người chơi dùng được." };
      system.run(() => {
        for (const k of ["soul", "innate", "level", "exp", "mana", "rings", "skill", "active", "bones"]) p.setDynamicProperty(P + k, undefined);
        cooldowns.delete(p.id);
        p.sendMessage("§eĐã xóa võ hồn. Dùng Thủy Tinh Thức Tỉnh để thức tỉnh lại.");
      });
      return { status: CustomCommandStatus.Success };
    },
  );

  reg.registerCommand(
    {
      name: "dld:setlevel",
      description: "Đặt cấp hồn lực (thử nghiệm)",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      mandatoryParameters: [{ name: "level", type: CustomCommandParamType.Integer }],
    },
    (origin, level) => {
      const p = playerOf(origin);
      if (!p) return { status: CustomCommandStatus.Failure, message: "Chỉ người chơi dùng được." };
      system.run(() => {
        if (!get(p, "soul", "")) return p.sendMessage("§cChưa thức tỉnh võ hồn.");
        set(p, "level", Math.max(1, Math.min(100, level)));
        set(p, "exp", 0);
        p.sendMessage(`§aĐã đặt cấp ${get(p, "level", 1)}.`);
      });
      return { status: CustomCommandStatus.Success };
    },
  );
});
