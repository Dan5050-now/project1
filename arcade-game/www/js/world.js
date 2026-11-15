'use strict';
// ─────────────────────────────────────────────────────────────
//  world.js — 레벨, 플레이어, 적, 아이템, 발사체, 발판, 파티클, 카메라
// ─────────────────────────────────────────────────────────────

const GRAV = 900;

// ═════════ 레벨 (타일 지도) ═════════
class Level {
  constructor(stageIdx) {
    const st = STAGES[stageIdx];
    this.stage = st;
    this.themeName = st.theme;
    this.theme = THEMES[st.theme];
    this.seed = stageIdx * 101 + 7;
    const rows = MAPS[st.id];
    this.cols = rows[0].length;
    this.w = this.cols * TILE;
    this.tiles = new Uint8Array(this.cols * ROWS);
    this.spawns = [];
    this.lava = [];
    const map = { '#': T.SOLID, B: T.BREAK, '?': T.ITEM, 1: T.HIDDEN, '=': T.ONEWAY, '^': T.SPIKE, v: T.SPIKEC, L: T.LAVA, l: T.LAVAB, Q: T.QUICK, q: T.QUICKB };
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < this.cols; c++) {
        const ch = rows[r][c] || '.';
        if (map[ch] != null) {
          this.tiles[r * this.cols + c] = map[ch];
          if (ch === 'L' || ch === 'l') this.lava.push({ c, r, top: ch === 'L' });
        } else if (ch !== '.') this.spawns.push({ ch, col: c, row: r });
      }
    }
    this.canvas = document.createElement('canvas');
    this.canvas.width = this.w; this.canvas.height = VH;
    this.ctx = this.canvas.getContext('2d');
    this.renderAll();
  }
  tileAt(c, r) {
    if (c < 0 || c >= this.cols) return T.SOLID;
    if (r < 0 || r >= ROWS) return T.EMPTY;
    return this.tiles[r * this.cols + c];
  }
  setTile(c, r, v) {
    if (c < 0 || c >= this.cols || r < 0 || r >= ROWS) return;
    this.tiles[r * this.cols + c] = v;
    this.redraw(c, r);
  }
  renderAll() {
    this.ctx.clearRect(0, 0, this.w, VH);
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < this.cols; c++) {
      const v = this.tiles[r * this.cols + c];
      if (v !== T.EMPTY && v !== T.LAVA && v !== T.LAVAB) drawTile(this.ctx, v, c, r, this);
    }
  }
  redraw(c, r) {
    this.ctx.clearRect((c - 1) * TILE, (r - 1) * TILE, TILE * 3, TILE * 3);
    for (let rr = r - 1; rr <= r + 2; rr++) for (let cc = c - 1; cc <= c + 1; cc++) {
      const v = this.tileAt(cc, rr);
      if (rr >= 0 && rr < ROWS && v !== T.EMPTY && v !== T.LAVA && v !== T.LAVAB && cc >= 0 && cc < this.cols) drawTile(this.ctx, v, cc, rr, this);
    }
  }
}

function isSolid(code) { return SOLID_TILES.has(code); }

// 몸체(사각형)와 타일 충돌 처리 — 플레이어·적·아이템 공용
const Phys = {
  moveX(w, b, dx, enemy) {
    if (!dx) return false;
    b.x += dx;
    const lv = w.level;
    const top = Math.floor(b.y / TILE), bot = Math.floor((b.y + b.h - 0.01) / TILE);
    if (dx > 0) {
      const col = Math.floor((b.x + b.w - 0.01) / TILE);
      for (let r = top; r <= bot; r++) if (isSolid(lv.tileAt(col, r))) { b.x = col * TILE - b.w; return true; }
    } else {
      const col = Math.floor(b.x / TILE);
      for (let r = top; r <= bot; r++) if (isSolid(lv.tileAt(col, r))) { b.x = (col + 1) * TILE; return true; }
    }
    if (b.x < 0) { b.x = 0; return true; }
    if (b.x + b.w > lv.w) { b.x = lv.w - b.w; return true; }
    return false;
  },
  // 반환: { land: bool, ceil: {c, r, code} | null }
  moveY(w, b, dy, enemy) {
    const res = { land: false, ceil: null, landCodes: [] };
    if (!dy) return res;
    const lv = w.level;
    const prevBottom = b.y + b.h;
    b.y += dy;
    const left = Math.floor(b.x / TILE), right = Math.floor((b.x + b.w - 0.01) / TILE);
    if (dy > 0) {
      const row = Math.floor((b.y + b.h - 0.01) / TILE);
      if (row < 0 || row >= ROWS) return res;
      for (let c = left; c <= right; c++) {
        const code = lv.tileAt(c, row);
        const floorLike = code === T.ONEWAY || (enemy && (code === T.QUICK || code === T.LAVA));
        if (isSolid(code) || (floorLike && prevBottom <= row * TILE + 0.5)) {
          b.y = row * TILE - b.h; res.land = true;
          for (let cc = left; cc <= right; cc++) res.landCodes.push(lv.tileAt(cc, row));
          return res;
        }
      }
    } else {
      const row = Math.floor(b.y / TILE);
      if (row < 0) return res;
      let best = null, bd = 1e9;
      const cx = b.x + b.w / 2;
      for (let c = left; c <= right; c++) {
        const code = lv.tileAt(c, row);
        if (isSolid(code)) {
          const d = Math.abs((c + 0.5) * TILE - cx);
          if (d < bd) { bd = d; best = { c, r: row, code }; }
        }
      }
      if (best) { b.y = (row + 1) * TILE; res.ceil = best; }
    }
    return res;
  },
  solidAtPx(w, x, y) { return isSolid(w.level.tileAt(Math.floor(x / TILE), Math.floor(y / TILE))); },
  tileAtPx(w, x, y) { return w.level.tileAt(Math.floor(x / TILE), Math.floor(y / TILE)); },
};

// ═════════ 플레이어 ═════════
class Player {
  constructor(world, cd, x, y) {
    this.w = 10; this.h = 15;
    this.world = world; this.cd = cd;
    this.x = x; this.y = y; this.vx = 0; this.vy = 0;
    this.dir = 1; this.onGround = false; this.groundPlat = null;
    this.coyote = 0; this.jumpBuf = 0; this.airJumps = 0; this.canCut = false;
    this.maxHp = Math.max(2, cd.hp + world.diff.hpBonus + (world.run.hpBonus || 0));
    this.hp = this.maxHp;
    this.inv = 0; this.hurtT = 0; this.atkT = 0; this.atkCD = 0; this.atkHits = null; this.atkFired = false;
    this.shield = false; this.powerT = 0; this.starT = 0;
    this.dead = false; this.deadT = 0; this.win = false; this.t = 0; this.freeze = 0;
    this.inQuick = false; this.stompChain = 0; this.animT = 0; this.landT = 0;
  }
  get cx() { return this.x + this.w / 2; }
  get cy() { return this.y + this.h / 2; }

  update(dt) {
    const w = this.world;
    this.t += dt; this.animT += dt;
    if (this.dead) {
      this.deadT += dt;
      this.vy += GRAV * 0.8 * dt; this.y += this.vy * dt;
      return;
    }
    if (this.inv > 0) this.inv -= dt;
    if (this.hurtT > 0) this.hurtT -= dt;
    if (this.powerT > 0) this.powerT -= dt;
    if (this.starT > 0) { this.starT -= dt; if (Math.random() < 0.5) w.spark(this.cx + U.rand(-6, 6), this.cy + U.rand(-8, 8), U.pick(['#ffe85a', '#ff8ae0', '#8af0ff'])); }
    if (this.atkCD > 0) this.atkCD -= dt;
    if (this.landT > 0) this.landT -= dt;

    // 발판에 타고 있으면 같이 이동
    if (this.groundPlat) {
      const p = this.groundPlat;
      if (p.solidTop && U.rectOverlap(this.x + 1, this.y + this.h - 2, this.w - 2, 6, p)) {
        Phys.moveX(w, this, p.dx);
        this.y = p.y - this.h;
      } else this.groundPlat = null;
    }

    const control = !this.win && this.freeze <= 0 && this.hurtT <= 0;
    if (this.freeze > 0) this.freeze -= dt;
    const jumpP = Input.jumpPressed(), atkP = Input.attackPressed();
    const ax = control ? Input.axisX : 0;
    const water = w.water;
    const quick = this.inQuick;
    let maxSp = this.cd.speed * (water ? 0.72 : 1) * (quick ? 0.4 : 1);
    if (this.atkT > 0 && this.onGround && this.cd.attack !== 'kick') maxSp *= 0.55;
    const accel = (this.onGround ? this.cd.accel : this.cd.accel * 0.8) * (water ? 0.6 : 1);
    const decel = this.onGround ? 1400 : 600;
    if (this.hurtT <= 0) this.vx = U.approach(this.vx, ax * maxSp, (ax !== 0 ? accel : decel) * dt);
    if (ax !== 0 && this.atkT <= 0) this.dir = ax;

    // 점프 / 수영
    if (control && jumpP) this.jumpBuf = 0.13;
    if (this.jumpBuf > 0) this.jumpBuf -= dt;
    if (water) {
      if (this.jumpBuf > 0) {
        this.vy = -138; this.jumpBuf = 0; Sound.play('swim');
        w.bubble(this.cx, this.y + 2);
      }
      this.vy += 280 * dt;
      if (this.vy > 78) this.vy = 78;
      if (this.y < 6) { this.y = 6; if (this.vy < 0) this.vy = 0; }
    } else {
      if (this.onGround || quick) { this.coyote = 0.09; this.airJumps = this.cd.airJumps; }
      else this.coyote -= dt;
      if (this.jumpBuf > 0 && this.coyote > 0) {
        this.vy = -this.cd.jump * (quick ? 0.85 : 1);
        this.coyote = 0; this.jumpBuf = 0; this.onGround = false; this.groundPlat = null; this.canCut = true;
        Sound.play('jump');
        w.dust(this.cx, this.y + this.h, 4);
      } else if (this.jumpBuf > 0 && this.airJumps > 0 && !this.onGround) {
        this.vy = -this.cd.jump * 0.9; this.airJumps--; this.jumpBuf = 0; this.canCut = true;
        Sound.play('djump');
        w.ring(this.cx, this.y + this.h, '#ffffff');
      }
      if (this.canCut && this.vy < 0 && !Input.jumpHeld) { this.vy *= 0.45; this.canCut = false; }
      if (this.vy >= 0) this.canCut = false;
      const g = this.vy > 0 ? GRAV * 1.12 : GRAV;
      this.vy += g * dt;
      if (quick) { if (this.vy > 16) this.vy = 16; }
      else if (this.vy > 380) this.vy = 380;
    }

    // 공격
    if (control && atkP && this.atkCD <= 0) this.startAttack();
    if (this.atkT > 0) { this.atkT -= dt; this.updateAttack(); }

    // 이동 & 충돌
    const wasGround = this.onGround;
    if (Phys.moveX(w, this, this.vx * dt)) this.vx = 0;
    const prevBottom = this.y + this.h;
    const ry = Phys.moveY(w, this, this.vy * dt);
    this.onGround = false;
    if (ry.land) {
      if (!wasGround && this.vy > 200) { w.dust(this.cx, this.y + this.h, 3); this.landT = 0.08; }
      this.vy = 0; this.onGround = true; this.groundPlat = null; this.stompChain = 0;
      if (ry.landCodes.includes(T.SPIKE)) this.hurt(1, this.cx, true);
    }
    if (ry.ceil) {
      this.vy = 0; this.canCut = false;
      const code = ry.ceil.code;
      if (code === T.BREAK || code === T.ITEM || code === T.HIDDEN) w.breakBlock(ry.ceil.c, ry.ceil.r, 'head');
      else if (code === T.SPIKEC) { this.hurt(1, this.cx, false); this.vy = 60; }
      else if (!water) Sound.play('bump');
    }
    // 움직이는 발판 / 무너지는 블록 착지
    if (this.vy >= 0 && !this.onGround) {
      for (const p of w.plats) {
        if (!p.solidTop) continue;
        const pTopPrev = p.y - p.dy;
        if (prevBottom <= pTopPrev + 2 && this.y + this.h >= p.y && this.x + this.w > p.x + 1 && this.x < p.x + p.w - 1) {
          this.y = p.y - this.h; this.vy = 0; this.onGround = true; this.groundPlat = p; this.stompChain = 0;
          p.onStand && p.onStand(this);
          break;
        }
      }
    } else if (this.groundPlat) this.onGround = true;

    // 모래늪
    const footCode = Phys.tileAtPx(w, this.cx, this.y + this.h - 1);
    const wasQuick = this.inQuick;
    this.inQuick = footCode === T.QUICK || footCode === T.QUICKB;
    if (this.inQuick && !wasQuick) { Sound.play('splash'); w.dust(this.cx, this.y + this.h, 5, '#e0aa66'); }
    if (this.inQuick && Math.random() < 0.2) w.dust(this.cx + U.rand(-5, 5), this.y + this.h - 4, 1, '#e0aa66');
    const headCode = Phys.tileAtPx(w, this.cx, this.y + 3);
    if (headCode === T.QUICK || headCode === T.QUICKB) this.die('sink');
    // 용암
    const lavaCode = Phys.tileAtPx(w, this.cx, this.y + this.h - 3);
    if (lavaCode === T.LAVA || lavaCode === T.LAVAB) { w.burst(this.cx, this.y + this.h, 12, ['#ff5a1a', '#ffd23a']); this.die('burn'); }
    // 낭떠러지
    if (this.y > VH + 24) this.die('fall');
    if (this.y < -40) this.y = -40;
  }

  startAttack() {
    const w = this.world, cd = this.cd;
    this.atkT = cd.atkDur; this.atkCD = cd.atkCD; this.atkHits = new Set(); this.atkFired = false;
    if (cd.attack === 'sword') Sound.play('sword');
    else if (cd.attack === 'kick') {
      Sound.play('kick');
      if (!this.onGround) this.vx += this.dir * 40;
    } else {
      Sound.play('magic');
      const ox = this.cx + this.dir * 9, oy = this.y + 5;
      const n = w.shots.filter((s) => s.owner === 'player' && s.kind === 'orb').length;
      if (n < 4) {
        const angles = this.powerT > 0 ? [-0.22, 0, 0.22] : [0];
        for (const a of angles) w.shots.push(new Shot({ x: ox, y: oy, vx: Math.cos(a) * 235 * this.dir, vy: Math.sin(a) * 235, owner: 'player', kind: 'orb', r: 4, life: 0.6, dmg: this.powerT > 0 ? 2 : 1, breaks: true }));
      }
    }
  }
  attackBox() {
    const cd = this.cd;
    if (cd.attack === 'sword') {
      const reach = cd.reach + (this.powerT > 0 ? 6 : 0);
      return { x: this.dir > 0 ? this.x + this.w - 3 : this.x - reach + 3, y: this.y - 7, w: reach, h: this.h + 9 };
    }
    if (cd.attack === 'kick') return { x: this.dir > 0 ? this.x + this.w - 2 : this.x - cd.reach + 2, y: this.y + 3, w: cd.reach, h: this.h - 2 };
    return null;
  }
  updateAttack() {
    const w = this.world, cd = this.cd;
    if (cd.attack === 'magic') return;
    const el = cd.atkDur - this.atkT;
    const active = cd.attack === 'sword' ? el > 0.05 && el < 0.2 : el > 0.02 && el < 0.16;
    if (!active) return;
    if (!this.atkFired) {
      this.atkFired = true;
      if (cd.attack === 'sword') w.slash(this);
      if (this.powerT > 0) {
        const kind = cd.attack === 'sword' ? 'wave' : 'gust';
        w.shots.push(new Shot({ x: this.cx + this.dir * 12, y: this.cy - (kind === 'wave' ? 2 : 0), vx: this.dir * 210, vy: 0, owner: 'player', kind, r: kind === 'wave' ? 6 : 4, life: kind === 'wave' ? 0.5 : 0.35, dmg: 1, pierce: true, breaks: true }));
      }
    }
    const box = this.attackBox();
    const dmg = this.powerT > 0 ? 2 : 1;
    for (const e of w.enemies) {
      if (!e.alive || this.atkHits.has(e)) continue;
      if (U.overlap(box, e)) { this.atkHits.add(e); e.hit(dmg, this); }
    }
    if (w.boss && w.boss.vulnerable() && !this.atkHits.has(w.boss)) {
      for (const hb of w.boss.hurtboxes()) if (U.overlap(box, hb)) { this.atkHits.add(w.boss); w.boss.hit(dmg); break; }
    }
    for (const s of w.shots) if (s.owner === 'enemy' && !s.big && U.rectOverlap(s.x - s.r, s.y - s.r, s.r * 2, s.r * 2, box)) { s.dead = true; w.spark(s.x, s.y, '#ffffff'); Sound.play('clink'); }
    // 블록 부수기
    const c0 = Math.floor(box.x / TILE), c1 = Math.floor((box.x + box.w - 1) / TILE);
    const r0 = Math.floor(Math.max(0, box.y) / TILE), r1 = Math.floor((box.y + box.h - 1) / TILE);
    for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) {
      const code = w.level.tileAt(c, r);
      const key = 'b' + c + '_' + r;
      if ((code === T.BREAK || code === T.ITEM || code === T.HIDDEN) && !this.atkHits.has(key)) { this.atkHits.add(key); w.breakBlock(c, r, 'attack'); }
    }
  }

  hurt(dmg, fromX, bounce) {
    const w = this.world;
    if (this.dead || this.inv > 0 || this.starT > 0 || this.win) return;
    if (this.shield) {
      this.shield = false; this.inv = 1.0; Sound.play('shieldbreak');
      w.burst(this.cx, this.cy, 10, ['#8ad0ff', '#ffffff']);
      return;
    }
    this.hp -= dmg; w.stats.damage += dmg;
    vibrate(60);
    if (this.hp <= 0) { this.hp = 0; this.die('hit'); return; }
    this.inv = w.diff.invTime; this.hurtT = 0.32;
    const away = this.cx < fromX ? -1 : 1;
    this.vx = away * 110; this.vy = bounce ? -230 : -160;
    this.onGround = false; this.groundPlat = null;
    Sound.play('hurt'); w.shake = Math.max(w.shake, 3); w.hitstop = 0.06;
  }
  die(reason) {
    if (this.dead || this.win) return;
    this.dead = true; this.deadT = 0; this.hp = 0;
    this.vy = reason === 'fall' ? -120 : -280; this.vx = 0;
    if (reason === 'fall') this.y = VH;
    Sound.play('die'); vibrate(200);
    this.world.shake = 4;
  }

  draw(c, t) {
    if (this.inv > 0 && !this.dead && Math.floor(t * 20) % 2 === 0) return;
    let pose = 'idle';
    if (this.dead) pose = 'dead';
    else if (this.win) pose = 'win';
    else if (this.hurtT > 0) pose = 'hurt';
    else if (this.atkT > 0) pose = 'attack';
    else if (this.world.water && !this.onGround) pose = 'swim';
    else if (!this.onGround && !this.inQuick) pose = this.vy < 0 ? 'jump' : 'fall';
    else if (Math.abs(this.vx) > 12) pose = 'run';
    const fx = this.cx, fy = this.y + this.h + (this.inQuick ? 0 : 0);
    if (this.powerT > 0 && !this.dead) {
      c.fillStyle = `rgba(255,120,60,${0.22 + Math.sin(t * 12) * 0.1})`;
      c.beginPath(); c.ellipse(fx, fy - 9, 11, 13, 0, 0, Math.PI * 2); c.fill();
    }
    const atkP = this.atkT > 0 ? 1 - this.atkT / this.cd.atkDur : 0;
    drawHero(c, this.cd.id, fx, fy, this.dir, pose, this.animT, { atkP, flash: this.starT > 0 && Math.floor(t * 15) % 3 === 0 });
    if (this.shield && !this.dead) {
      c.strokeStyle = `rgba(140,210,255,${0.6 + Math.sin(t * 8) * 0.25})`; c.lineWidth = 1;
      c.beginPath(); c.arc(Math.round(fx) + 0.5, Math.round(fy - 9) + 0.5, 13, 0, Math.PI * 2); c.stroke();
    }
  }
}

// ═════════ 적 ═════════
const ENEMY_DEF = {
  e: { type: 'walker', w: 14, h: 12, hp: 1, speed: 30, stomp: true, score: 100 },
  h: { type: 'hopper', w: 12, h: 12, hp: 1, speed: 55, stomp: true, score: 150 },
  y: { type: 'flyer', w: 14, h: 10, hp: 1, speed: 40, stomp: true, score: 150 },
  t: { type: 'turret', w: 14, h: 16, hp: 2, speed: 0, stomp: false, score: 200 },
  c: { type: 'chaser', w: 12, h: 12, hp: 2, speed: 34, stomp: false, score: 200 },
  o: { type: 'spiky', w: 14, h: 12, hp: 1, speed: 24, stomp: false, score: 0, invuln: true },
  d: { type: 'dropper', w: 10, h: 14, hp: 1, speed: 0, stomp: false, score: 50 },
};

class Enemy {
  constructor(world, ch, col, row) {
    const d = ENEMY_DEF[ch];
    Object.assign(this, { type: d.type, w: d.w, h: d.h, hp: d.hp, speed: d.speed, stomp: d.stomp, score: d.score, invuln: !!d.invuln });
    this.world = world;
    const theme = world.level.themeName;
    if (this.type === 'walker' && theme === 'castle') this.hp = 2;
    if (this.hp >= 2) this.hp += world.diff.enemyHp;
    this.x = col * TILE + (TILE - this.w) / 2;
    this.y = (row + 1) * TILE - this.h;
    if (this.type === 'dropper') this.y = row * TILE;
    this.x0 = this.x; this.y0 = this.y;
    this.vx = 0; this.vy = 0; this.dir = -1; this.t = Math.random() * 3;
    this.alive = true; this.flash = 0; this.onGround = false; this.state = 'idle';
    this.timer = 1 + Math.random(); this.active = false;
    this.jelly = this.type === 'hopper' && world.water;
  }
  get cx() { return this.x + this.w / 2; }
  get cy() { return this.y + this.h / 2; }
  update(dt) {
    const w = this.world, p = w.player, spd = w.diff.enemySpeed;
    this.t += dt;
    if (this.flash > 0) this.flash -= dt;
    const toP = U.sign(p.cx - this.cx) || 1;
    const distP = U.dist(this.cx, this.cy, p.cx, p.cy);
    switch (this.type) {
      case 'walker': case 'spiky': {
        this.vx = this.dir * this.speed * spd;
        this.gravityMove(dt);
        if (this.hitWall) this.dir *= -1;
        else if (this.onGround) {
          const ahead = this.dir > 0 ? this.x + this.w + 1 : this.x - 1;
          const below = Phys.tileAtPx(w, ahead, this.y + this.h + 2);
          if (!(isSolid(below) || below === T.ONEWAY || below === T.QUICK)) this.dir *= -1;
        }
        break;
      }
      case 'hopper': {
        if (this.jelly) {
          this.vy += 40 * dt; if (this.vy > 22) this.vy = 22;
          this.timer -= dt * spd;
          if (this.timer <= 0) { this.vy = -70; this.timer = 1.4 + Math.random() * 0.6; }
          this.vx = toP * 12 * spd;
          this.x += this.vx * dt; this.y += this.vy * dt;
          if (this.y > this.y0 + 20) this.y = this.y0 + 20;
          if (this.y < this.y0 - 60) { this.y = this.y0 - 60; this.vy = 0; }
          this.dir = toP;
          break;
        }
        this.gravityMove(dt);
        if (this.onGround) {
          this.vx = 0; this.dir = toP;
          this.timer -= dt * spd;
          if (this.timer <= 0 && distP < 200) { this.vy = -250; this.vx = this.dir * this.speed * spd; this.timer = 1.1 + Math.random() * 0.7; }
        }
        if (this.hitWall) this.vx = 0;
        break;
      }
      case 'flyer': {
        this.x += this.dir * this.speed * spd * dt;
        if (Math.abs(this.x - this.x0) > 72 || Phys.solidAtPx(w, this.dir > 0 ? this.x + this.w : this.x, this.cy)) this.dir *= -1;
        this.y = this.y0 + Math.sin(this.t * 2.5) * 14;
        break;
      }
      case 'turret': {
        this.dir = toP;
        this.timer -= dt * w.diff.enemyFire;
        if (this.state === 'fire') { this.stateT -= dt; if (this.stateT <= 0) this.state = 'idle'; }
        if (this.timer <= 0 && Math.abs(p.cx - this.cx) < 210 && !p.dead) {
          this.timer = 2.4 + Math.random() * 0.6; this.state = 'fire'; this.stateT = 0.3;
          this.fire();
        }
        break;
      }
      case 'chaser': {
        if (distP < 150 && !p.dead) {
          const sp = this.speed * spd;
          this.vx = U.approach(this.vx, ((p.cx - this.cx) / distP) * sp, 60 * dt);
          this.vy = U.approach(this.vy, ((p.cy - this.cy) / distP) * sp, 60 * dt);
        } else {
          this.vx = U.approach(this.vx, (this.x0 - this.x) * 0.5, 30 * dt);
          this.vy = U.approach(this.vy, (this.y0 - this.y) * 0.5, 30 * dt);
        }
        this.x += this.vx * dt; this.y += this.vy * dt + Math.sin(this.t * 3) * 0.2;
        if (Math.abs(this.vx) > 3) this.dir = U.sign(this.vx);
        const skin = ENEMY_SKIN.chaser[w.level.themeName];
        if (skin === 'puffer') {
          const near = distP < 45;
          if (near && this.state !== 'puff') { this.state = 'puff'; this.w = 16; this.h = 16; this.x -= 2; this.y -= 2; }
          else if (!near && this.state === 'puff') { this.state = 'idle'; this.w = 12; this.h = 12; this.x += 2; this.y += 2; }
        }
        break;
      }
      case 'dropper': {
        if (this.state === 'idle') {
          if (Math.abs(p.cx - this.cx) < 22 && p.y > this.y) { this.state = 'shake'; this.stateT = 0.35; Sound.play('crumble'); }
        } else if (this.state === 'shake') {
          this.stateT -= dt; if (this.stateT <= 0) this.state = 'fall';
        } else {
          this.vy += GRAV * 0.9 * dt; this.y += this.vy * dt;
          if (Phys.solidAtPx(w, this.cx, this.y + this.h) || this.y > VH) {
            this.alive = false; w.burst(this.cx, this.y + this.h, 8, [w.level.theme.dirtL, w.level.theme.dirt]); Sound.play('break');
          }
        }
        break;
      }
    }
  }
  gravityMove(dt) {
    const w = this.world;
    this.vy += (w.water ? 300 : GRAV) * dt;
    if (this.vy > 300) this.vy = 300;
    this.hitWall = Phys.moveX(w, this, this.vx * dt, true);
    const r = Phys.moveY(w, this, this.vy * dt, true);
    this.onGround = r.land;
    if (r.land || r.ceil) this.vy = 0;
    if (this.y > VH + 40) this.alive = false;
  }
  fire() {
    const w = this.world, p = w.player, theme = w.level.themeName;
    const ox = this.cx + this.dir * 6, oy = this.y + 5;
    const ang = Math.atan2(p.cy - oy, p.cx - ox);
    Sound.play('shot');
    if (theme === 'forest') {
      w.shots.push(new Shot({ x: ox, y: oy, vx: this.dir * 70, vy: -170, grav: 380, owner: 'enemy', kind: 'seed', r: 3, life: 3 }));
    } else if (theme === 'desert') {
      for (const a of [-0.35, 0, 0.35]) w.shots.push(new Shot({ x: ox, y: oy, vx: Math.cos(ang + a) * 85, vy: Math.sin(ang + a) * 85, owner: 'enemy', kind: 'needle', r: 2, life: 3 }));
    } else {
      const kind = { cave: 'crystal', sea: 'pearl', sky: 'wind', castle: 'fire' }[theme];
      w.shots.push(new Shot({ x: ox, y: oy, vx: Math.cos(ang) * 90, vy: Math.sin(ang) * 90, owner: 'enemy', kind, r: 3, life: 3.5 }));
    }
  }
  hit(dmg, src) {
    const w = this.world;
    if (!this.alive) return;
    if (this.invuln && !(src && src.starT > 0)) {
      Sound.play('clink'); w.spark(this.cx, this.cy, '#ffffff'); this.flash = 0.08;
      return;
    }
    this.hp -= dmg; this.flash = 0.12;
    if (this.hp <= 0) this.kill();
    else { Sound.play('hit'); w.spark(this.cx, this.cy, '#ffffff'); }
  }
  kill() {
    const w = this.world;
    this.alive = false;
    Sound.play('defeat');
    w.burst(this.cx, this.cy, 10, ['#ffffff', '#ffe85a', PAL[w.level.themeName].a]);
    w.ring(this.cx, this.cy, '#ffffff');
    w.addScore(this.score || 50, this.cx, this.y);
    w.stats.kills++;
    if (Math.random() < 0.28) w.spawnItem(Math.random() < 0.15 ? 'heart' : 'coin', this.cx, this.cy, true);
  }
  draw(c, t) { drawEnemy(c, this, this.world.level.themeName, this.t); }
}

// ═════════ 발사체 ═════════
class Shot {
  constructor(o) {
    Object.assign(this, { x: 0, y: 0, vx: 0, vy: 0, r: 3, owner: 'enemy', kind: 'pearl', dmg: 1, life: 2, grav: 0, pierce: false, homing: 0, ghost: false, big: false, t: 0, dead: false, breaks: false, hp: 0 }, o);
    this.hitSet = this.pierce ? new Set() : null;
  }
  update(dt, w) {
    this.t += dt; this.life -= dt;
    if (this.life <= 0) { this.dead = true; return; }
    if (this.homing && !w.player.dead) {
      const a = Math.atan2(w.player.cy - this.y, w.player.cx - this.x);
      const sp = Math.hypot(this.vx, this.vy);
      const cur = Math.atan2(this.vy, this.vx);
      let da = a - cur; while (da > Math.PI) da -= Math.PI * 2; while (da < -Math.PI) da += Math.PI * 2;
      const na = cur + U.clamp(da, -this.homing * dt, this.homing * dt);
      this.vx = Math.cos(na) * sp; this.vy = Math.sin(na) * sp;
    }
    this.vy += this.grav * dt;
    this.x += this.vx * dt; this.y += this.vy * dt;
    if (!this.ghost) {
      const code = Phys.tileAtPx(w, this.x, this.y);
      if (isSolid(code)) {
        if (this.owner === 'player' && this.breaks && (code === T.BREAK || code === T.ITEM || code === T.HIDDEN)) {
          w.breakBlock(Math.floor(this.x / TILE), Math.floor(this.y / TILE), 'shot');
        }
        this.dead = true; w.spark(this.x, this.y, this.color());
        if (this.onDie) this.onDie(w);
      }
    }
    if (this.x < w.cam.x - 60 || this.x > w.cam.x + G.VW + 60 || this.y > VH + 40 || this.y < -80) this.dead = true;
  }
  color() {
    return { orb: '#7af0ff', wave: '#e8f8ff', gust: '#c8ffd8', seed: '#8a5a2a', needle: '#f0f0d0', crystal: '#6ef0ff', pearl: '#ffffff', wind: '#d8f0ff', fire: '#ff8a2a', shadow: '#c06aff', ink: '#2a1a3a', rock: '#8a7ab0', sand: '#e0a868', feather: '#fff4c0', bolt: '#fff27a', acorn: '#8a5a2a', flame: '#ff5a1a' }[this.kind] || '#fff';
  }
  draw(c, t) {
    const x = Math.round(this.x), y = Math.round(this.y);
    switch (this.kind) {
      case 'orb':
        c.fillStyle = 'rgba(120,240,255,0.35)'; c.beginPath(); c.arc(x, y, 6, 0, Math.PI * 2); c.fill();
        R(c, x - 3, y - 3, 6, 6, '#7af0ff'); R(c, x - 2, y - 2, 3, 3, '#ffffff');
        R(c, x - Math.sign(this.vx) * 6, y, 2, 1, '#bff8ff'); break;
      case 'wave':
        c.strokeStyle = '#e8f8ff'; c.lineWidth = 2;
        c.beginPath(); c.arc(x - Math.sign(this.vx) * 4, y, 7, -1.1, 1.1, this.vx < 0); c.stroke();
        c.strokeStyle = 'rgba(120,200,255,0.6)'; c.beginPath(); c.arc(x - Math.sign(this.vx) * 6, y, 7, -1.1, 1.1, this.vx < 0); c.stroke(); break;
      case 'gust':
        c.fillStyle = 'rgba(200,255,220,0.7)'; c.beginPath(); c.ellipse(x, y, 6, 3, 0, 0, Math.PI * 2); c.fill(); R(c, x - 2, y - 1, 4, 2, '#fff'); break;
      case 'needle': R(c, x - 2, y - 1, 4, 2, '#f0f0d0'); R(c, x - 1, y - 1, 1, 1, '#a8a890'); break;
      case 'seed': case 'acorn': R(c, x - 2, y - 2, 5, 5, '#8a5a2a'); R(c, x - 2, y - 3, 5, 2, '#5a3a1a'); R(c, x - 1, y - 1, 1, 1, '#c8945a'); break;
      case 'rock': R(c, x - this.r, y - this.r, this.r * 2, this.r * 2, '#8a7ab0'); R(c, x - this.r, y - this.r, this.r * 2, 2, '#b8a8e0'); R(c, x - this.r + 2, y, 2, 2, '#6ef0ff'); break;
      case 'ink':
        c.fillStyle = '#2a1a3a'; c.beginPath(); c.arc(x, y, this.r, 0, Math.PI * 2); c.fill(); R(c, x - 1, y - 2, 2, 1, '#8a6aa8'); break;
      case 'fire': case 'flame':
        R(c, x - 3, y - 3, 6, 6, '#ff5a1a'); R(c, x - 2, y - 2, 4, 4, '#ffb02a'); R(c, x - 1, y - 1, 2, 2, '#fff2a0');
        if (Math.random() < 0.4) this.trail = true; break;
      case 'shadow': {
        const r = this.r + Math.sin(t * 15) * 0.8;
        c.fillStyle = 'rgba(160,60,220,0.45)'; c.beginPath(); c.arc(x, y, r + 3, 0, Math.PI * 2); c.fill();
        c.fillStyle = '#3a0a5a'; c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill();
        R(c, x - 1, y - 1, 2, 2, '#ff6ad8'); break;
      }
      case 'feather': R(c, x - 4, y - 1, 8, 2, '#fff4c0'); R(c, x - 4, y, 8, 1, '#e8c040'); break;
      case 'shock': {
        const k = Math.floor(t * 20) % 2;
        R(c, x - 5, y - 2 - k, 10, 3 + k, 'rgba(255,240,200,0.85)'); R(c, x - 3, y - 6 - k, 6, 4, 'rgba(255,255,255,0.7)'); R(c, x - 6, y + 1, 12, 2, '#c8a070');
        break;
      }
      case 'sand': c.fillStyle = '#d8a058'; c.beginPath(); c.arc(x, y, this.r, 0, Math.PI * 2); c.fill(); R(c, x - 1, y - 2, 2, 1, '#f8d8a0'); break;
      default: {
        const col = this.color();
        c.fillStyle = col; c.beginPath(); c.arc(x, y, this.r, 0, Math.PI * 2); c.fill();
        R(c, x - 1, y - 1, 1, 1, '#ffffff');
      }
    }
  }
}

// ═════════ 아이템 ═════════
class Item {
  constructor(kind, x, y, pop) {
    this.kind = kind; this.x = x - 6; this.y = y - 6; this.w = 12; this.h = 12;
    this.vx = pop ? U.rand(-30, 30) : 0; this.vy = pop ? -200 : 0;
    this.pop = pop; this.t = Math.random() * 2; this.life = pop && (kind === 'coin') ? 7 : Infinity;
    this.dead = false; this.delay = pop ? 0.25 : 0;
  }
  update(dt, w) {
    this.t += dt; this.life -= dt;
    if (this.delay > 0) this.delay -= dt;
    if (this.life <= 0) { this.dead = true; return; }
    if (this.pop) {
      this.vy += (w.water ? 250 : 650) * dt;
      if (this.vy > 260) this.vy = 260;
      if (Phys.moveX(w, this, this.vx * dt)) this.vx *= -0.5;
      const r = Phys.moveY(w, this, this.vy * dt, true);
      if (r.land) { this.vy = Math.abs(this.vy) > 80 ? -this.vy * 0.35 : 0; this.vx *= 0.8; }
      if (r.ceil) this.vy = 0;
      if (this.y > VH + 20) this.dead = true;
    }
  }
  draw(c, t) {
    if (this.life < 2 && Math.floor(t * 10) % 2) return;
    const bob = this.pop ? 0 : Math.sin(this.t * 3) * 1.5;
    drawItem(c, this.kind, this.x + 6, this.y + 6 + bob, this.t);
  }
}

// ═════════ 발판 ═════════
class MovingPlat {
  constructor(kind, col, row, phase) {
    this.kind = kind; this.w = 48; this.h = 8;
    this.x0 = col * TILE; this.y0 = (row + 1) * TILE; // 발판 윗면 = 바로 아래 칸 높이 (땅과 같은 높이)
    this.range = kind === 'h' ? 5 * TILE : 4 * TILE;
    this.period = 4.4; this.phase = phase;
    this.x = this.x0; this.y = this.y0; this.dx = 0; this.dy = 0; this.solidTop = true;
    this.update(0, 0);
  }
  update(dt, t) {
    const px = this.x, py = this.y;
    const p = (1 - Math.cos((t / this.period) * Math.PI * 2 + this.phase)) / 2;
    if (this.kind === 'h') this.x = this.x0 + p * this.range;
    else this.y = this.y0 - p * this.range;
    this.dx = this.x - px; this.dy = this.y - py;
  }
  draw(c, theme) {
    const x = Math.round(this.x), y = Math.round(this.y);
    const th = THEMES[theme];
    if (theme === 'sky') {
      c.fillStyle = '#ffffff'; c.beginPath(); c.ellipse(x + 24, y + 4, 25, 6, 0, 0, Math.PI * 2); c.fill();
      c.beginPath(); c.ellipse(x + 14, y + 1, 9, 5, 0, 0, Math.PI * 2); c.ellipse(x + 32, y, 10, 5, 0, 0, Math.PI * 2); c.fill();
      R(c, x + 6, y + 8, 36, 1, '#c8d4f4');
    } else {
      R(c, x, y, 48, 8, th.plat); R(c, x, y, 48, 1, '#ffffff'); R(c, x, y + 7, 48, 1, th.platD);
      for (let i = 4; i < 48; i += 12) R(c, x + i, y + 3, 2, 2, th.platD);
      if (theme === 'castle') { R(c, x + 2, y + 8, 2, 3, '#2a2234'); R(c, x + 44, y + 8, 2, 3, '#2a2234'); }
    }
  }
}
class Crumble {
  constructor(col, row) {
    this.x = col * TILE; this.y = row * TILE; this.x0 = this.x; this.y0 = this.y;
    this.w = 16; this.h = 16; this.dx = 0; this.dy = 0; this.state = 'idle'; this.t = 0; this.vy = 0; this.solidTop = true;
  }
  onStand() { if (this.state === 'idle') { this.state = 'shake'; this.t = 0.42; Sound.play('crumble'); } }
  update(dt, w) {
    this.dy = 0; this.dx = 0;
    if (this.state === 'shake') { this.t -= dt; if (this.t <= 0) { this.state = 'fall'; this.vy = 0; } }
    else if (this.state === 'fall') {
      this.solidTop = false;
      this.vy += GRAV * dt; this.y += this.vy * dt;
      if (this.y > VH + 30) { this.state = 'gone'; this.t = 4; }
    } else if (this.state === 'gone') {
      this.t -= dt;
      if (this.t <= 0 && !U.rectOverlap(this.x0, this.y0, 16, 16, w.player)) { this.state = 'idle'; this.y = this.y0; this.solidTop = true; w.burst(this.x + 8, this.y + 8, 5, ['#ffffff']); }
    }
  }
  draw(c, theme, t) {
    if (this.state === 'gone') return;
    const th = THEMES[theme];
    const sx = this.state === 'shake' ? (Math.floor(t * 30) % 2 ? 1 : -1) : 0;
    const x = Math.round(this.x) + sx, y = Math.round(this.y);
    R(c, x, y, 16, 16, th.brickD); R(c, x + 1, y + 1, 14, 13, th.brick); R(c, x + 1, y + 1, 14, 1, th.brickL);
    R(c, x + 4, y + 3, 1, 5, th.brickD); R(c, x + 5, y + 7, 4, 1, th.brickD); R(c, x + 9, y + 8, 1, 5, th.brickD); R(c, x + 11, y + 3, 1, 3, th.brickD);
  }
}

// ═════════ 월드 ═════════
class World {
  constructor(stageIdx, run, checkpoint) {
    this.stageIdx = stageIdx; this.run = run;
    this.diff = DIFFICULTY[run.diff];
    this.cd = CHARACTERS[run.char];
    this.level = new Level(stageIdx);
    this.water = !!this.level.theme.water;
    this.enemies = []; this.items = []; this.shots = []; this.parts = []; this.plats = []; this.signs = []; this.flags = []; this.texts = [];
    this.boss = null; this.bossState = 'none'; this.bossT = 0; this.arenaCol = -1; this.bossSpawn = null;
    this.cam = { x: 0, minX: 0 }; this.shake = 0; this.hitstop = 0; this.t = 0; this.clearT = -1; this.flashT = 0;
    this.stats = { kills: 0, damage: 0, time: 0, coins: 0 };
    this.events = [];
    this.ambient = [];
    let start = { x: 32, y: 160 };
    let enemyIdx = 0;
    const signTexts = SIGN_TEXTS[this.level.themeName] || [];
    const sorted = this.level.spawns.slice().sort((a, b) => a.col - b.col || a.row - b.row);
    let signN = 0, flagN = 0;
    for (const s of sorted) {
      const px = s.col * TILE, py = s.row * TILE;
      switch (s.ch) {
        case 'P': start = { x: px + 3, y: py + TILE - 15 }; break;
        case 'C': this.items.push(new Item('coin', px + 8, py + 8, false)); break;
        case 'H': this.items.push(new Item('heart', px + 8, py + 8, false)); break;
        case 'S': this.signs.push({ x: px + 8, y: py + TILE, text: signTexts[signN++] || '' }); break;
        case 'K': this.flags.push({ x: px + 8, y: py + TILE, active: false, idx: flagN++ }); break;
        case 'X': this.plats.push(new Crumble(s.col, s.row)); break;
        case 'M': this.plats.push(new MovingPlat('h', s.col, s.row, 0)); break;
        case 'm': this.plats.push(new MovingPlat('h', s.col, s.row, Math.PI)); break;
        case 'N': this.plats.push(new MovingPlat('v', s.col, s.row, 0)); break;
        case 'n': this.plats.push(new MovingPlat('v', s.col, s.row, Math.PI)); break;
        case 'A': this.arenaCol = s.col; break;
        case 'Z': this.bossSpawn = { x: px + 8, y: py + TILE }; break;
        default:
          if (ENEMY_DEF[s.ch]) {
            enemyIdx++;
            if (this.diff.thin && enemyIdx % 4 === 0 && s.ch !== 'd') break;
            this.enemies.push(new Enemy(this, s.ch, s.col, s.row));
          }
      }
    }
    if (checkpoint != null && this.flags[checkpoint]) {
      const f = this.flags[checkpoint];
      f.active = true;
      for (const g of this.flags) if (g.idx < checkpoint) g.active = true;
      start = { x: f.x - 5, y: f.y - 15 };
      // 체크포인트 근처 적 제거 (부활 직후 피격 방지)
      this.enemies = this.enemies.filter((e) => Math.abs(e.cx - f.x) > 56);
    }
    this.checkpoint = checkpoint;
    this.player = new Player(this, this.cd, start.x, start.y);
    if (run.carryShield) this.player.shield = true;
    if (run.carryCharm) this.player.powerT = 30;
    this.cam.x = U.clamp(this.player.cx - G.VW * 0.4, 0, this.level.w - G.VW);
    for (let i = 0; i < 26; i++) this.ambient.push({ x: Math.random() * 600, y: Math.random() * VH, s: Math.random() });
  }

  // ─── 이벤트/효과 헬퍼 ───
  addScore(n, x, y) { this.run.score += n; if (x != null) this.texts.push({ x, y, text: String(n), t: 0, col: '#ffffff' }); }
  popText(x, y, text, col = '#ffe85a') { this.texts.push({ x, y, text, t: 0, col }); }
  spark(x, y, col) { for (let i = 0; i < 4; i++) this.parts.push({ x, y, vx: U.rand(-60, 60), vy: U.rand(-60, 60), life: 0.25, max: 0.25, col, size: 1, grav: 0 }); }
  burst(x, y, n, cols) { for (let i = 0; i < n; i++) this.parts.push({ x, y, vx: U.rand(-110, 110), vy: U.rand(-150, 40), life: U.rand(0.3, 0.6), max: 0.6, col: U.pick(cols), size: U.pick([1, 2, 2, 3]), grav: 400 }); }
  dust(x, y, n, col) { for (let i = 0; i < n; i++) this.parts.push({ x: x + U.rand(-4, 4), y, vx: U.rand(-30, 30), vy: U.rand(-25, -5), life: 0.3, max: 0.3, col: col || 'rgba(255,255,255,0.8)', size: 2, grav: 0 }); }
  ring(x, y, col) { this.parts.push({ x, y, ring: true, life: 0.3, max: 0.3, col, size: 2 }); }
  bubble(x, y) { for (let i = 0; i < 3; i++) this.parts.push({ x: x + U.rand(-3, 3), y, vx: U.rand(-8, 8), vy: U.rand(-40, -20), life: 0.8, max: 0.8, col: '#bfefff', size: 2, grav: -20, bub: true }); }
  slash(p) { this.parts.push({ slash: true, x: p.cx, y: p.cy - 1, dir: p.dir, life: 0.12, max: 0.12, power: p.powerT > 0 }); }

  spawnItem(kind, x, y, pop) { this.items.push(new Item(kind, x, y, pop)); }
  breakBlock(c, r, by) {
    const lv = this.level, code = lv.tileAt(c, r);
    if (code !== T.BREAK && code !== T.ITEM && code !== T.HIDDEN) return;
    lv.setTile(c, r, T.EMPTY);
    const x = c * TILE + 8, y = r * TILE + 8;
    const th = lv.theme;
    for (let i = 0; i < 4; i++) this.parts.push({ x: x + (i % 2 ? 4 : -4), y: y + (i < 2 ? -4 : 4), vx: (i % 2 ? 1 : -1) * U.rand(40, 90), vy: U.rand(-220, -120), life: 0.8, max: 0.8, col: code === T.ITEM ? '#f0b020' : th.brick, size: 4, grav: 700, chunk: true });
    Sound.play('break'); this.shake = Math.max(this.shake, 1.5);
    this.run.score += 10;
    const pop = by === 'head' ? { x, y: y - 10 } : { x, y };
    if (code === T.ITEM) {
      const rnd = U.hash(c, r, this.stageIdx + 3);
      const kind = rnd < 0.26 ? 'heart' : rnd < 0.55 ? 'bag' : rnd < 0.74 ? 'power' : rnd < 0.9 ? 'shield' : 'star';
      this.spawnItem(kind, pop.x, pop.y, true);
    } else if (code === T.HIDDEN) {
      this.spawnItem('life', pop.x, pop.y, true);
      this.popText(x, y - 8, '비밀 발견!', '#5ae08a');
    } else if (U.hash(c, r, this.stageIdx + 9) < 0.2) this.spawnItem('coin', pop.x, pop.y, true);
  }
  collect(it) {
    const p = this.player, run = this.run;
    it.dead = true;
    const x = it.x + 6, y = it.y;
    switch (it.kind) {
      case 'coin': run.coins++; this.stats.coins++; run.score += 10; Sound.play('coin'); this.spark(x, y + 6, '#ffe85a'); break;
      case 'bag': run.coins += 10; this.stats.coins += 10; run.score += 50; Sound.play('coin'); this.popText(x, y, '+10', '#ffe85a'); break;
      case 'heart':
        if (p.hp < p.maxHp) { p.hp++; this.popText(x, y, 'HP +1', '#ff8aa0'); } else this.addScore(500, x, y);
        Sound.play('heart'); break;
      case 'power': p.powerT = 15; Sound.play('power'); this.popText(x, y, '파워업!', '#ff8a5a'); break;
      case 'shield': p.shield = true; Sound.play('shield'); this.popText(x, y, '보호막!', '#8ad0ff'); break;
      case 'star': p.starT = 8; Sound.play('power'); this.popText(x, y, '무적!', '#ffe85a'); break;
      case 'life': run.lives++; Sound.play('oneup'); this.popText(x, y, '1UP!', '#5ae08a'); break;
      case 'shard':
        Sound.play('shard'); this.startClear(); break;
    }
  }

  // ─── 보스 ───
  startBoss() {
    const lv = this.level;
    this.bossState = 'intro'; this.bossT = 0;
    for (let r = 0; r <= 10; r++) if (lv.tileAt(this.arenaCol, r) === T.EMPTY) lv.setTile(this.arenaCol, r, T.GATE);
    this.cam.minX = Math.min(this.arenaCol * TILE, lv.w - G.VW);
    this.boss = createBoss(this.level.stage.boss, this, this.bossSpawn.x, this.bossSpawn.y);
    Sound.musicStop(); Sound.play('roar');
    this.shake = 5; this.player.freeze = 1.9;
    this.events.push({ type: 'bossIntro' });
  }
  bossDefeated() {
    this.bossState = 'dying'; this.bossT = 0;
    this.addScore(5000 * (this.diff.id === 'hard' ? 2 : 1));
    Sound.musicStop();
    this.shots = this.shots.filter((s) => s.owner === 'player');
    for (const e of this.enemies) if (e.alive) e.kill();
  }
  startClear() {
    this.clearT = 0;
    this.player.win = true; this.player.vx = 0;
    Sound.jingle('fanfare');
    this.events.push({ type: 'clear' });
  }

  // ─── 업데이트 ───
  update(dt) {
    if (this.hitstop > 0) { this.hitstop -= dt; return; }
    this.t += dt;
    if (!this.player.dead && this.clearT < 0) this.stats.time += dt;
    const p = this.player;
    for (const pl of this.plats) pl.update(dt, pl instanceof MovingPlat ? this.t : this);
    p.update(dt);

    // 카메라
    const lookAhead = p.dir * 28;
    let target = p.cx - G.VW / 2 + lookAhead;
    const maxX = this.level.w - G.VW;
    target = U.clamp(target, this.cam.minX, maxX);
    this.cam.x += (target - this.cam.x) * Math.min(1, dt * 6);
    this.cam.x = U.clamp(this.cam.x, this.cam.minX, maxX);
    if (this.shake > 0) this.shake = Math.max(0, this.shake - dt * 12);

    const viewC = this.cam.x + G.VW / 2;
    for (const e of this.enemies) {
      if (!e.alive) continue;
      if (Math.abs(e.cx - viewC) > G.VW / 2 + 90) continue;
      e.update(dt);
      if (!e.alive || p.dead || p.win) continue;
      if (U.overlap(p, e)) this.touchEnemy(e);
    }
    this.enemies = this.enemies.filter((e) => e.alive);

    for (const s of this.shots) {
      s.update(dt, this);
      if (s.dead) continue;
      if (s.owner === 'player') {
        for (const e of this.enemies) {
          if (!e.alive || (s.hitSet && s.hitSet.has(e))) continue;
          if (U.rectOverlap(s.x - s.r, s.y - s.r, s.r * 2, s.r * 2, e)) {
            e.hit(s.dmg, p);
            if (s.pierce) s.hitSet.add(e); else { s.dead = true; break; }
          }
        }
        if (!s.dead && this.boss && this.boss.vulnerable() && !(s.hitSet && s.hitSet.has(this.boss))) {
          for (const hb of this.boss.hurtboxes()) {
            if (U.rectOverlap(s.x - s.r, s.y - s.r, s.r * 2, s.r * 2, hb)) {
              this.boss.hit(s.dmg);
              if (s.pierce) s.hitSet.add(this.boss); else s.dead = true;
              break;
            }
          }
        }
        // 마법탄으로 적 탄환(그림자 구슬) 상쇄
        if (!s.dead) for (const o of this.shots) if (o.owner === 'enemy' && o.hp > 0 && !o.dead && U.dist(o.x, o.y, s.x, s.y) < o.r + s.r) { o.hp -= s.dmg; if (o.hp <= 0) { o.dead = true; this.spark(o.x, o.y, '#c06aff'); } s.dead = true; }
      } else if (!p.dead && !p.win && U.rectOverlap(s.x - s.r + 1, s.y - s.r + 1, s.r * 2 - 2, s.r * 2 - 2, p)) {
        p.hurt(s.dmg, s.x - s.vx, false);
        if (!s.big) s.dead = true;
      }
    }
    this.shots = this.shots.filter((s) => !s.dead);

    for (const it of this.items) {
      it.update(dt, this);
      if (!it.dead && it.delay <= 0 && !p.dead && U.overlap(p, it)) this.collect(it);
    }
    this.items = this.items.filter((it) => !it.dead);

    for (const f of this.flags) {
      if (!f.active && !p.dead && Math.abs(p.cx - f.x) < 10 && p.y + p.h > f.y - 34) {
        f.active = true; this.checkpoint = f.idx; Sound.play('checkpoint');
        this.burst(f.x + 6, f.y - 26, 10, ['#5ae08a', '#ffffff', '#ffe85a']);
        this.popText(f.x, f.y - 40, '체크포인트!', '#5ae08a');
      }
    }

    // 보스 진행
    if (this.bossState === 'none' && this.arenaCol >= 0 && p.x > this.arenaCol * TILE + 40 && !p.dead) this.startBoss();
    if (this.boss) {
      this.bossT += dt;
      if (this.bossState === 'intro' && this.bossT > 2.0) {
        this.bossState = 'fight';
        Sound.music(this.stageIdx === 5 ? 'final' : 'boss');
      }
      this.boss.update(dt);
      if (this.bossState === 'fight' && !p.dead && !p.win) {
        for (const hb of this.boss.hitboxes()) if (U.overlap(p, hb)) { p.hurt(1, hb.x + hb.w / 2, true); break; }
      }
      if (this.bossState === 'dying' && this.bossT > 2.4) {
        this.bossState = 'dead';
        const cx = U.clamp(this.boss.cx, this.cam.x + 40, this.cam.x + G.VW - 40);
        this.spawnItem('shard', cx, 90, true);
        this.items[this.items.length - 1].vy = -120;
        this.boss = null;
      }
    }

    if (this.clearT >= 0) this.clearT += dt;
    if (this.flashT > 0) this.flashT -= dt;

    for (const pt of this.parts) {
      pt.life -= dt;
      if (pt.slash || pt.ring) continue;
      pt.vy += (pt.grav || 0) * dt; pt.x += pt.vx * dt; pt.y += pt.vy * dt;
    }
    this.parts = this.parts.filter((pt) => pt.life > 0);
    for (const tx of this.texts) { tx.t += dt; tx.y -= 22 * dt; }
    this.texts = this.texts.filter((tx) => tx.t < 0.9);
  }
  touchEnemy(e) {
    const p = this.player;
    if (p.starT > 0) { e.invuln = false; e.hp = 0; e.kill(); return; }
    const stomping = p.vy > 40 && p.y + p.h - e.y < 9;
    if (stomping && e.stomp) {
      p.vy = Input.jumpHeld ? -320 : -200; p.canCut = false; p.y = e.y - p.h;
      p.stompChain++;
      e.hit(2, p);
      Sound.play('stomp');
      if (p.stompChain > 1) this.addScore(100 * p.stompChain, e.cx, e.y - 8);
      return;
    }
    p.hurt(1, e.cx, false);
  }

  // ─── 그리기 ───
  draw(c) {
    const t = this.t;
    const sx = this.shake > 0 ? Math.round(U.rand(-this.shake, this.shake)) : 0;
    const sy = this.shake > 0 ? Math.round(U.rand(-this.shake, this.shake)) : 0;
    const camX = Math.round(this.cam.x) + sx;
    const theme = this.level.themeName;
    Backgrounds.draw(c, theme, camX, t, G.VW);
    this.drawAmbient(c, theme, t, true);
    c.save();
    c.translate(-camX, sy);
    // 타일
    c.drawImage(this.level.canvas, camX, 0, G.VW, VH, camX, 0, G.VW, VH);
    // 용암
    for (const L of this.level.lava) {
      const x = L.c * TILE;
      if (x < camX - 16 || x > camX + G.VW) continue;
      const y = L.r * TILE;
      R(c, x, y, 16, 16, '#d83a0a');
      if (L.top) {
        for (let i = 0; i < 16; i += 2) { const hh = 3 + Math.round(Math.sin(t * 4 + (x + i) * 0.3) * 1.5); R(c, x + i, y, 2, hh, '#ff8a1a'); R(c, x + i, y, 2, 1, '#ffe05a'); }
        if (Math.random() < 0.01) this.parts.push({ x: x + U.rand(0, 16), y, vx: 0, vy: -60, life: 0.6, max: 0.6, col: '#ffb02a', size: 2, grav: 200 });
      } else { if ((L.c + L.r) % 3 === 0) R(c, x + 4, y + 6, 3, 2, '#ff6a1a'); }
    }
    // 아이템 블록 반짝임
    const sparkle = Math.floor(t * 3) % 4;
    if (sparkle === 0) {
      const c0 = Math.floor(camX / TILE), c1 = c0 + Math.ceil(G.VW / TILE) + 1;
      for (let r = 0; r < ROWS; r++) for (let cc = c0; cc <= c1; cc++) if (this.level.tileAt(cc, r) === T.ITEM) R(c, cc * TILE + 3, r * TILE + 3, 2, 2, '#ffffff');
    }
    for (const s of this.signs) drawSign(c, s.x, s.y);
    for (const f of this.flags) drawFlag(c, f.x, f.y, f.active, t);
    for (const pl of this.plats) pl.draw(c, theme, t);
    for (const it of this.items) it.draw(c, t);
    if (this.boss) this.boss.draw(c, t);
    for (const e of this.enemies) if (e.x + e.w > camX - 20 && e.x < camX + G.VW + 20) e.draw(c, t);
    this.player.draw(c, t);
    for (const s of this.shots) s.draw(c, t);
    for (const pt of this.parts) {
      if (pt.slash) {
        const a = pt.life / pt.max;
        c.strokeStyle = pt.power ? `rgba(255,180,120,${a})` : `rgba(255,255,255,${a})`;
        c.lineWidth = 2;
        c.beginPath(); c.arc(pt.x + pt.dir * 6, pt.y, 15, pt.dir > 0 ? -1.4 : Math.PI - 0.5, pt.dir > 0 ? 0.5 : Math.PI + 1.4); c.stroke();
        c.lineWidth = 1; c.strokeStyle = `rgba(160,220,255,${a})`;
        c.beginPath(); c.arc(pt.x + pt.dir * 6, pt.y, 12, pt.dir > 0 ? -1.2 : Math.PI - 0.4, pt.dir > 0 ? 0.4 : Math.PI + 1.2); c.stroke();
        continue;
      }
      if (pt.ring) {
        const k = 1 - pt.life / pt.max;
        c.strokeStyle = pt.col; c.globalAlpha = 1 - k; c.lineWidth = 1;
        c.beginPath(); c.arc(pt.x, pt.y, 3 + k * 12, 0, Math.PI * 2); c.stroke(); c.globalAlpha = 1;
        continue;
      }
      const s = pt.chunk ? Math.max(1, Math.round(pt.size * (pt.life / pt.max) + 1)) : pt.size;
      R(c, Math.round(pt.x - s / 2), Math.round(pt.y - s / 2), s, s, pt.col);
    }
    c.restore();
    this.drawAmbient(c, theme, t, false);
    if (this.flashT > 0) { c.fillStyle = `rgba(255,255,255,${Math.min(1, this.flashT * 2)})`; c.fillRect(0, 0, G.VW, VH); }
    if (this.water) {
      // 수면
      for (let x = 0; x < G.VW; x += 4) { const yy = 3 + Math.round(Math.sin(t * 2 + (x + camX) * 0.05) * 1.5); R(c, x, yy, 4, 1, 'rgba(200,240,255,0.6)'); }
    }
  }
  drawAmbient(c, theme, t, back) {
    const n = this.ambient.length;
    for (let i = 0; i < n; i++) {
      const a = this.ambient[i];
      if ((i % 2 === 0) !== back) continue;
      const W = G.VW + 40;
      const par = back ? 0.4 : 1.2;
      let x, y;
      switch (theme) {
        case 'forest':
          x = ((a.x - this.cam.x * par + Math.sin(t + i) * 20) % W + W) % W - 20; y = (a.y + t * (12 + a.s * 10)) % (VH + 10) - 5;
          R(c, x | 0, y | 0, 2, 1, a.s < 0.5 ? '#6ac850' : '#e8c040'); break;
        case 'cave':
          x = ((a.x - this.cam.x * par) % W + W) % W - 20; y = (a.y + Math.sin(t * 0.7 + i) * 6);
          if (Math.sin(t * 2 + i * 1.7) > 0.4) R(c, x | 0, y | 0, 1, 1, '#a8f0ff'); break;
        case 'sea':
          x = ((a.x - this.cam.x * par + Math.sin(t * 2 + i) * 4) % W + W) % W - 20; y = ((a.y - t * (14 + a.s * 16)) % VH + VH) % VH;
          c.strokeStyle = 'rgba(190,240,255,0.6)'; c.lineWidth = 1; c.beginPath(); c.arc(x | 0, y | 0, 1 + a.s * 1.5, 0, Math.PI * 2); c.stroke(); break;
        case 'desert':
          x = ((a.x - this.cam.x * par - t * (40 + a.s * 50)) % W + W) % W - 20; y = a.y + Math.sin(t * 3 + i) * 3;
          R(c, x | 0, y | 0, 2, 1, 'rgba(255,220,160,0.7)'); break;
        case 'sky':
          x = ((a.x - this.cam.x * par - t * (90 + a.s * 80)) % W + W) % W - 20; y = a.y;
          R(c, x | 0, y | 0, 10 + Math.round(a.s * 10), 1, 'rgba(255,255,255,0.55)'); break;
        case 'castle':
          x = ((a.x - this.cam.x * par + Math.sin(t + i) * 8) % W + W) % W - 20; y = ((a.y - t * (16 + a.s * 20)) % VH + VH) % VH;
          R(c, x | 0, y | 0, 1, 2, a.s < 0.5 ? '#ff8a2a' : '#ffd23a'); break;
      }
    }
  }
}
