// Hồn thú có model riêng: AI chiến thuật + hồn kỹ riêng cho từng loài.
//
// Khác quái thường, chúng:
//  - quan sát vị trí/vận tốc mục tiêu và chọn chiêu theo khoảng cách, máu của bản thân
//  - ra chiêu có báo trước (hạt cảnh báo) — người chơi né được nếu để ý
//  - đoán trước hướng di chuyển khi ném đá, đánh vòng sườn theo bầy, rút lui hồi máu khi yếu
//  - né đạn: bị bắn tên sẽ lách sang bên
import { world, system, EntityDamageCause, EntityInitializationCause, GameMode } from "@minecraft/server";
import { RING_TIERS, weightedPick } from "./data.js";

const P = "dld:";
const DIMENSIONS = ["overworld", "nether", "the_end"];
const TIER_DAMAGE = [1.0, 1.3, 1.7, 2.4, 3.5];

export const CUSTOM_BEASTS = {
  "dld:demon_spider": { name: "Nhân Diện Ma Chu", tiers: [0, 1, 2], weights: [50, 35, 15] },
  "dld:wind_wolf": { name: "Phong Lang", tiers: [0, 1, 2], weights: [55, 35, 10] },
  "dld:gold_claw_bear": { name: "Ám Kim Khủng Trảo Hùng", tiers: [1, 2, 3], weights: [45, 40, 15] },
  "dld:titan_ape": { name: "Thái Thản Cự Viên", tiers: [3, 4], weights: [70, 30] },
};

// ───────────── Tiện ích ─────────────

const brains = new Map(); // entity.id -> trạng thái AI

function brainOf(e) {
  let b = brains.get(e.id);
  if (!b) {
    b = { cd: {}, busy: 0, side: Math.random() < 0.5 ? 1 : -1, flags: {} };
    brains.set(e.id, b);
  }
  return b;
}

function tierOf(e) {
  return e.getDynamicProperty(P + "tier") ?? 0;
}

function dmgMult(e) {
  return TIER_DAMAGE[tierOf(e)] ?? 1;
}

function fx(dim, id, loc) {
  try {
    dim.spawnParticle(id, loc);
  } catch {}
}

function snd(e, id, pitch = 1, volume = 1.5) {
  try {
    e.dimension.playSound(id, e.location, { pitch, volume });
  } catch {}
}

function anim(e, name) {
  try {
    e.playAnimation(`animation.dld.${e.typeId.slice(P.length)}.${name}`, {
      controller: "dld_skill",
      stopExpression: "query.any_animation_finished",
      blendOutTime: 0.2,
    });
  } catch {}
}

function sub(a, b) {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}
function flatLen(v) {
  return Math.hypot(v.x, v.z);
}
function norm2(v) {
  const l = flatLen(v) || 1;
  return { x: v.x / l, z: v.z / l };
}

function hpRatio(e) {
  const h = e.getComponent("minecraft:health");
  return h ? h.currentValue / h.effectiveMax : 1;
}

function playersNear(dim, loc, r) {
  return dim.getPlayers({ location: loc, maxDistance: r, excludeGameModes: [GameMode.Creative, GameMode.Spectator] });
}

function hit(src, target, amount, kb = 0, up = 0.3) {
  try {
    target.applyDamage(amount * dmgMult(src), { cause: EntityDamageCause.entityAttack, damagingEntity: src });
    if (kb) {
      const d = norm2(sub(target.location, src.location));
      target.applyKnockback({ x: d.x * kb, z: d.z * kb }, up);
    }
  } catch {}
}

function effect(target, id, sec, amp) {
  try {
    target.addEffect(id, Math.round(sec * 20), { amplifier: amp });
  } catch {}
}

function ring(dim, center, r, id, n = 16, y = 0.2) {
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    fx(dim, id, { x: center.x + Math.cos(a) * r, y: center.y + y, z: center.z + Math.sin(a) * r });
  }
}

function line(dim, from, to, id, step = 0.7) {
  const d = sub(to, from);
  const len = Math.hypot(d.x, d.y, d.z);
  for (let t = 0; t < len; t += step) {
    const k = t / len;
    fx(dim, id, { x: from.x + d.x * k, y: from.y + d.y * k, z: from.z + d.z * k });
  }
}

function impulse(e, v) {
  try {
    e.applyImpulse(v);
  } catch {}
}

/** Đặt hồi chiêu và khóa hành động trong `busy` tick. */
function use(b, key, cdTicks, busyTicks) {
  const now = system.currentTick;
  b.cd[key] = now + Math.round(cdTicks * (b.flags.enraged ? 0.7 : 1));
  b.busy = now + busyTicks;
}
function ready(b, key) {
  return (b.cd[key] ?? 0) <= system.currentTick;
}

function later(e, ticks, fn) {
  system.runTimeout(() => {
    if (e.isValid) fn();
  }, ticks);
}

function warn(e, text, r = 24) {
  for (const p of playersNear(e.dimension, e.location, r)) p.onScreenDisplay.setActionBar(text);
}

// Chiến thuật chung: rút lui hồi phục khi máu thấp (mỗi 30 giây một lần).
function retreat(e, b, target, regenAmp, extra) {
  if (hpRatio(e) > 0.3 || !ready(b, "retreat")) return false;
  const away = norm2(sub(e.location, target.location));
  impulse(e, { x: away.x * 1.4, y: 0.35, z: away.z * 1.4 });
  effect(e, "regeneration", 6, regenAmp);
  effect(e, "speed", 6, 1);
  extra?.();
  use(b, "retreat", 600, 30);
  return true;
}

// ───────────── Nhân Diện Ma Chu ─────────────
// Mạng nhện trói từ xa, phun độc vào vị trí sắp tới, vồ khi mục tiêu bị trói, ẩn thân khi yếu.

function spider(e, b, t, dist) {
  const dim = e.dimension;
  if (retreat(e, b, t, 1, () => effect(e, "invisibility", 5, 0))) return;

  if (dist > 4 && dist < 16 && ready(b, "web")) {
    use(b, "web", 160, 18);
    anim(e, "web");
    snd(e, "mob.spider.say", 0.6);
    later(e, 12, () => {
      if (!t.isValid) return;
      const from = { x: e.location.x, y: e.location.y + 0.8, z: e.location.z };
      line(dim, from, { x: t.location.x, y: t.location.y + 1, z: t.location.z }, "minecraft:white_smoke_particle", 0.5);
      if (flatLen(sub(t.location, e.location)) < 18) {
        effect(t, "slowness", 4, 3);
        effect(t, "weakness", 4, 0);
        hit(e, t, 2);
        b.flags.webbed = system.currentTick + 80;
      }
    });
    return;
  }
  // Mục tiêu đang bị trói → vồ tới
  if ((b.flags.webbed ?? 0) > system.currentTick && dist > 3 && dist < 12 && ready(b, "leap")) {
    use(b, "leap", 100, 20);
    anim(e, "leap");
    const d = norm2(sub(t.location, e.location));
    const f = Math.min(1.6, dist * 0.16);
    impulse(e, { x: d.x * f, y: 0.55, z: d.z * f });
    later(e, 12, () => {
      for (const p of playersNear(dim, e.location, 2.8)) hit(e, p, 5, 0.6);
    });
    return;
  }
  if (dist < 9 && ready(b, "spit")) {
    use(b, "spit", 200, 20);
    anim(e, "spit");
    // Phun vào vị trí mục tiêu sắp đến
    const v = t.getVelocity();
    const spot = { x: t.location.x + v.x * 10, y: t.location.y, z: t.location.z + v.z * 10 };
    for (let i = 0; i < 3; i++) later(e, i * 5, () => ring(dim, spot, 2.5, "minecraft:villager_angry", 10));
    later(e, 16, () => {
      ring(dim, spot, 1.5, "minecraft:mobspell_emitter", 8);
      for (const p of playersNear(dim, spot, 2.5)) {
        effect(p, "poison", 5, 1);
        hit(e, p, 3);
      }
    });
  }
}

// ───────────── Phong Lang ─────────────
// Đi theo bầy: hú gọi đồng đội và tăng sức, đánh vòng sườn, phóng phong nhận, lao tới.

function wolf(e, b, t, dist) {
  const dim = e.dimension;
  const pack = dim.getEntities({ location: e.location, maxDistance: 16, type: "dld:wind_wolf" });

  if (retreat(e, b, t, 1, () => {
    anim(e, "howl");
    snd(e, "mob.wolf.howl", 1.2);
    for (const w of pack) effect(w, "strength", 8, 0);
  })) return;

  if (ready(b, "howl") && dist < 20) {
    use(b, "howl", 500, 28);
    anim(e, "howl");
    snd(e, "mob.wolf.howl", 0.8, 2);
    for (const w of pack) {
      effect(w, "speed", 12, 1);
      effect(w, "strength", 12, 0);
    }
    // Lẻ loi thì gọi bầy (mỗi con chỉ gọi một lần)
    if (pack.length < 3 && !b.flags.called) {
      b.flags.called = true;
      later(e, 30, () => {
        try {
          const w = dim.spawnEntity("dld:wind_wolf", { x: e.location.x + 2, y: e.location.y, z: e.location.z + 2 });
          w.setDynamicProperty(P + "called", true);
        } catch {}
      });
      warn(e, "§bTiếng hú của Phong Lang vang lên... bầy sói đang tới!");
    }
    return;
  }
  if (dist > 4 && dist < 12 && ready(b, "blade")) {
    use(b, "blade", 100, 12);
    anim(e, "blade");
    snd(e, "random.bow", 1.6);
    later(e, 6, () => {
      if (!t.isValid) return;
      line(dim, { x: e.location.x, y: e.location.y + 0.8, z: e.location.z }, { x: t.location.x, y: t.location.y + 1, z: t.location.z }, "minecraft:wind_explosion_emitter", 1.5);
      hit(e, t, 4, 0.5);
    });
    return;
  }
  // Đánh vòng sườn: lách ngang quanh mục tiêu thay vì lao thẳng
  if (dist > 2 && dist < 7 && ready(b, "flank")) {
    use(b, "flank", 30, 6);
    const d = norm2(sub(t.location, e.location));
    if (Math.random() < 0.25) b.side *= -1;
    impulse(e, { x: -d.z * b.side * 0.6 + d.x * 0.2, y: 0.1, z: d.x * b.side * 0.6 + d.z * 0.2 });
    return;
  }
  if (dist >= 7 && dist < 14 && ready(b, "dash")) {
    use(b, "dash", 120, 10);
    anim(e, "dash");
    const d = norm2(sub(t.location, e.location));
    impulse(e, { x: d.x * 1.3, y: 0.25, z: d.z * 1.3 });
  }
}

// ───────────── Ám Kim Khủng Trảo Hùng ─────────────
// Liên hoàn trảo khi áp sát, gầm làm suy yếu, tụ lực xung phong (né được), Kim Cương Bất Hoại khi yếu.

function bear(e, b, t, dist) {
  const dim = e.dimension;
  if (hpRatio(e) < 0.4 && ready(b, "guard")) {
    use(b, "guard", 800, 20);
    anim(e, "roar");
    effect(e, "resistance", 6, 2);
    effect(e, "regeneration", 6, 2);
    snd(e, "random.anvil_use", 0.6);
    for (let i = 0; i < 6; i++) later(e, i * 10, () => ring(dim, e.location, 1.4, "minecraft:totem_particle", 10, 1));
    warn(e, "§6Ám Kim Khủng Trảo Hùng thi triển §eKim Cương Bất Hoại§6!");
    return;
  }
  if (dist < 3.8 && ready(b, "claw")) {
    use(b, "claw", 140, 26);
    anim(e, "claw");
    snd(e, "mob.polarbear.warning", 0.7);
    [5, 11, 17].forEach((tick, i) =>
      later(e, tick, () => {
        for (const p of playersNear(dim, e.location, 3.8)) hit(e, p, 4, i === 2 ? 1.6 : 0.2, i === 2 ? 0.5 : 0.1);
        fx(dim, "minecraft:critical_hit_emitter", { x: e.location.x, y: e.location.y + 1, z: e.location.z });
      }),
    );
    return;
  }
  if (dist < 10 && ready(b, "roar")) {
    use(b, "roar", 400, 30);
    anim(e, "roar");
    snd(e, "mob.ravager.roar", 0.8, 2);
    fx(dim, "minecraft:knockback_roar_particle", e.location);
    for (const p of playersNear(dim, e.location, 10)) {
      effect(p, "weakness", 8, 1);
      effect(p, "slowness", 3, 1);
    }
    return;
  }
  if (dist > 6 && dist < 18 && ready(b, "charge")) {
    use(b, "charge", 240, 36);
    anim(e, "charge");
    snd(e, "mob.polarbear.warning", 0.5, 2);
    for (let i = 0; i < 3; i++) later(e, i * 5, () => fx(dim, "minecraft:villager_angry", { x: e.location.x, y: e.location.y + 2.2, z: e.location.z }));
    // Chốt hướng lúc tụ lực — mục tiêu tránh sang bên sẽ né được
    const aim = { ...t.location };
    later(e, 15, () => {
      const d = norm2(sub(aim, e.location));
      const hitIds = new Set();
      for (let k = 0; k < 4; k++) {
        later(e, k * 3, () => {
          impulse(e, { x: d.x * 0.9, y: 0.05, z: d.z * 0.9 });
          fx(dim, "minecraft:large_explosion", e.location);
          for (const p of playersNear(dim, e.location, 2.2)) {
            if (hitIds.has(p.id)) continue;
            hitIds.add(p.id);
            hit(e, p, 9, 2.2, 0.6);
          }
        });
      }
    });
  }
}

// ───────────── Thái Thản Cự Viên (boss) ─────────────
// Địa chấn (nhảy lên để né), ném đá đoán trước hướng chạy, đấm liên hoàn, nhảy đập, cuồng bạo khi dưới 50% máu.

function ape(e, b, t, dist) {
  const dim = e.dimension;
  if (!b.flags.enraged && hpRatio(e) < 0.5) {
    b.flags.enraged = true;
    b.busy = system.currentTick + 26;
    anim(e, "roar");
    snd(e, "mob.enderdragon.growl", 0.5, 3);
    effect(e, "strength", 9999, 1);
    effect(e, "speed", 9999, 0);
    fx(dim, "minecraft:knockback_roar_particle", e.location);
    warn(e, "§c§lThái Thản Cự Viên nổi cuồng bạo!", 40);
    return;
  }
  if (dist < 4.5 && ready(b, "punch")) {
    use(b, "punch", 80, 16);
    anim(e, "punch");
    later(e, 4, () => playersNear(dim, e.location, 4.5).forEach((p) => hit(e, p, 6, 0.4)));
    later(e, 10, () => playersNear(dim, e.location, 4.5).forEach((p) => hit(e, p, 7, 1.8, 0.5)));
    snd(e, "mob.irongolem.throw", 0.6);
    return;
  }
  if (dist < 8 && ready(b, "slam")) {
    use(b, "slam", 180, 32);
    anim(e, "slam");
    warn(e, "§eThái Thản Cự Viên chuẩn bị §cĐịa Chấn§e — nhảy lên để né!");
    for (let i = 0; i < 4; i++) later(e, i * 5, () => ring(dim, e.location, 7, "minecraft:villager_angry", 20));
    later(e, 22, () => {
      snd(e, "random.explode", 0.5, 3);
      for (let r = 1.5; r <= 7; r += 1.5) ring(dim, e.location, r, "minecraft:large_explosion", Math.round(r * 4));
      for (const p of playersNear(dim, e.location, 7)) {
        if (!p.isOnGround) continue; // đang nhảy thì né được
        hit(e, p, 12, 1.2, 0.9);
        effect(p, "slowness", 3, 2);
      }
    });
    return;
  }
  if (dist >= 8 && dist < 30 && ready(b, "throw")) {
    use(b, "throw", 140, 24);
    anim(e, "throw");
    snd(e, "dig.stone", 0.5, 2);
    later(e, 14, () => {
      if (!t.isValid) return;
      // Đoán vị trí mục tiêu khi đá rơi xuống (sau 20 tick)
      const v = t.getVelocity();
      const land = { x: t.location.x + v.x * 20, y: t.location.y, z: t.location.z + v.z * 20 };
      const from = { x: e.location.x, y: e.location.y + 4, z: e.location.z };
      for (let k = 1; k <= 10; k++) {
        later(e, k * 2, () => {
          const f = k / 10;
          const pos = { x: from.x + (land.x - from.x) * f, y: from.y + (land.y - from.y) * f + Math.sin(f * Math.PI) * 6, z: from.z + (land.z - from.z) * f };
          fx(dim, "minecraft:large_explosion", pos);
          ring(dim, land, 3, "minecraft:villager_angry", 10);
        });
      }
      later(e, 21, () => {
        fx(dim, "minecraft:huge_explosion_emitter", land);
        try {
          dim.playSound("random.explode", land, { volume: 2, pitch: 0.7 });
        } catch {}
        for (const p of playersNear(dim, land, 3.2)) hit(e, p, 10, 1.0, 0.5);
      });
    });
    return;
  }
  if (dist > 10 && dist < 22 && ready(b, "jump")) {
    use(b, "jump", 300, 40);
    anim(e, "slam");
    const d = norm2(sub(t.location, e.location));
    const f = Math.min(2.6, dist * 0.13);
    impulse(e, { x: d.x * f, y: 1.0, z: d.z * f });
    later(e, 22, () => {
      snd(e, "random.explode", 0.6, 3);
      ring(dim, e.location, 4, "minecraft:huge_explosion_emitter", 6);
      for (const p of playersNear(dim, e.location, 5)) hit(e, p, 11, 1.6, 0.7);
    });
  }
}

const BRAINS = {
  "dld:demon_spider": spider,
  "dld:wind_wolf": wolf,
  "dld:gold_claw_bear": bear,
  "dld:titan_ape": ape,
};

// ───────────── Sự kiện ─────────────

world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  const def = CUSTOM_BEASTS[e.typeId];
  if (!def || ev.cause === EntityInitializationCause.Loaded) return;
  system.run(() => {
    if (!e.isValid) return;
    let tier = def.tiers[weightedPick(def.weights)];
    // Sói được gọi tới yếu hơn con đầu đàn một bậc
    if (e.getDynamicProperty(P + "called")) tier = def.tiers[0];
    e.setDynamicProperty(P + "tier", tier);
    e.addTag("dld_beast");
    e.triggerEvent(`dld:set_tier_${tier}`);
    const t = RING_TIERS[tier];
    if (tier >= 3) e.nameTag = `${t.color}${def.name} §f${t.age}`;
    if (tier >= 4) world.sendMessage(`§c✦ Một §lHồn Thú 10 vạn năm§r§c — ${def.name} — đã xuất hiện!`);
  });
});

// Đòn đánh thường có animation riêng
world.afterEvents.entityHurt.subscribe((ev) => {
  const src = ev.damageSource.damagingEntity;
  if (src && BRAINS[src.typeId] && ev.damageSource.cause === EntityDamageCause.entityAttack) {
    const b = brains.get(src.id);
    if (!b || b.busy <= system.currentTick) anim(src, "attack");
  }
  // Né đạn: bị bắn sẽ lách sang bên
  const e = ev.hurtEntity;
  if (BRAINS[e.typeId] && ev.damageSource.cause === EntityDamageCause.projectile) {
    const chance = e.typeId === "dld:titan_ape" ? 0.2 : e.typeId === "dld:gold_claw_bear" ? 0.35 : 0.6;
    const shooter = ev.damageSource.damagingEntity;
    if (shooter && Math.random() < chance) {
      const d = norm2(sub(e.location, shooter.location));
      const s = Math.random() < 0.5 ? 1 : -1;
      impulse(e, { x: -d.z * s * 0.9, y: 0.25, z: d.x * s * 0.9 });
    }
  }
});

world.afterEvents.entityRemove.subscribe((ev) => brains.delete(ev.removedEntityId));

// Bộ não: mỗi 5 tick suy nghĩ một lần
system.runInterval(() => {
  const now = system.currentTick;
  for (const dimId of DIMENSIONS) {
    let dim;
    try {
      dim = world.getDimension(dimId);
    } catch {
      continue;
    }
    for (const e of dim.getEntities({ families: ["dld_custom"] })) {
      try {
        const think = BRAINS[e.typeId];
        if (!think) continue;
        const b = brainOf(e);
        if (b.busy > now) continue;
        const target = playersNear(dim, e.location, 28).sort(
          (a, c) => flatLen(sub(a.location, e.location)) - flatLen(sub(c.location, e.location)),
        )[0];
        if (!target) continue;
        think(e, b, target, flatLen(sub(target.location, e.location)));
      } catch {}
    }
  }
}, 5);

export function beastName(typeId, fallback) {
  return CUSTOM_BEASTS[typeId]?.name ?? fallback;
}
