'use strict';
// ─────────────────────────────────────────────────────────────
//  bosses.js — 스테이지 보스 6종 (각자 고유 패턴 + 체력 50% 이하 분노 모드)
// ─────────────────────────────────────────────────────────────

const FLOOR_Y = 176; // 보스 구역 바닥 높이 (11번째 줄 위)

class Boss {
  constructor(world, x, y, hp, w, h) {
    this.world = world;
    this.maxHp = Math.max(4, Math.round(hp * world.diff.bossHp));
    this.hp = this.maxHp;
    this.w = w; this.h = h;
    this.x = x - w / 2; this.y = y - h;
    this.vx = 0; this.vy = 0; this.dir = -1;
    this.t = 0; this.st = 1.2; this.state = 'intro'; this.n = 0;
    this.flash = 0; this.inv = 0; this.dead = false; this.deathT = 0;
    this.spd = world.diff.bossSpeed;
    this.hazards = []; // 장판/기둥 공격 {x,y,w,h,life,warn,kind}
    this.L = (world.arenaCol + 1) * TILE; this.Rb = world.level.w - TILE;
  }
  get cx() { return this.x + this.w / 2; }
  get cy() { return this.y + this.h / 2; }
  get enraged() { return this.hp <= this.maxHp / 2; }
  vulnerable() { return this.world.bossState === 'fight' && this.inv <= 0 && !this.dead; }
  box() { return { x: this.x + 2, y: this.y + 2, w: this.w - 4, h: this.h - 2 }; }
  hurtboxes() { return [this.box()]; }
  hitboxes() {
    const out = this.dead ? [] : [this.box()];
    for (const hz of this.hazards) if (hz.warn <= 0 && hz.life > 0) out.push(hz);
    return out;
  }
  hit(dmg) {
    const w = this.world;
    this.hp -= dmg; this.flash = 0.15; this.inv = 0.14;
    Sound.play('bosshit'); w.shake = Math.max(w.shake, 2); w.hitstop = 0.035;
    w.spark(this.cx + U.rand(-8, 8), this.cy + U.rand(-8, 8), '#ffffff');
    if (this.hp <= 0) { this.hp = 0; this.dead = true; this.hazards = []; w.bossDefeated(); }
  }
  update(dt) {
    const w = this.world;
    this.t += dt;
    if (this.flash > 0) this.flash -= dt;
    if (this.inv > 0) this.inv -= dt;
    if (this.dead) {
      this.deathT += dt;
      if (Math.floor(this.deathT * 9) !== Math.floor((this.deathT - dt) * 9)) {
        w.burst(this.cx + U.rand(-this.w / 2, this.w / 2), this.cy + U.rand(-this.h / 2, this.h / 2), 8, ['#ffffff', '#ffe85a', '#ff8a2a']);
        w.ring(this.cx + U.rand(-10, 10), this.cy + U.rand(-10, 10), '#ffffff');
        if (Math.floor(this.deathT * 3) !== Math.floor((this.deathT - dt) * 3)) { Sound.play('boom'); w.shake = 4; }
      }
      return;
    }
    for (const hz of this.hazards) {
      if (hz.warn > 0) { hz.warn -= dt; if (hz.warn <= 0 && hz.sfx) Sound.play(hz.sfx); }
      else hz.life -= dt;
    }
    this.hazards = this.hazards.filter((hz) => hz.warn > 0 || hz.life > 0);
    if (w.bossState === 'intro') { this.intro(dt); return; }
    if (w.player.dead) return;
    this.ai(dt);
  }
  intro(dt) {}
  shoot(o) { this.world.shots.push(new Shot(Object.assign({ owner: 'enemy' }, o))); }
  aim(ox, oy, speed, spread = 0) {
    const p = this.world.player;
    const a = Math.atan2(p.cy - oy, p.cx - ox) + spread;
    return { vx: Math.cos(a) * speed, vy: Math.sin(a) * speed };
  }
  addPillar(x, warn, life, kind, top = 0, sfx = 'fire') {
    this.hazards.push({ x: x - 7, y: top, w: 14, h: FLOOR_Y - top, warn, life, kind, sfx, t: 0 });
  }
  drawHazards(c, t) {
    for (const hz of this.hazards) {
      const x = Math.round(hz.x);
      if (hz.warn > 0) {
        if (Math.floor(t * 12) % 2) {
          R(c, x, FLOOR_Y - 2, hz.w, 2, hz.kind === 'bolt' ? '#fff27a' : '#ff4a4a');
          if (hz.kind === 'bolt') R(c, x + 2, hz.y, hz.w - 4, 6, 'rgba(80,80,120,0.8)');
          else for (let i = 0; i < 3; i++) R(c, x + 2 + i * 4, FLOOR_Y - 5 - (Math.floor(t * 20 + i) % 4), 2, 2, '#ffb02a');
        }
        continue;
      }
      if (hz.kind === 'bolt') {
        c.fillStyle = 'rgba(255,255,200,0.35)'; c.fillRect(x - 3, hz.y, hz.w + 6, hz.h);
        let px = x + hz.w / 2;
        for (let y = hz.y; y < hz.y + hz.h; y += 8) { const nx = x + hz.w / 2 + U.rand(-4, 4); c.strokeStyle = '#fff27a'; c.lineWidth = 2; c.beginPath(); c.moveTo(px, y); c.lineTo(nx, y + 8); c.stroke(); px = nx; }
      } else if (hz.kind === 'tentacle') {
        const k = Math.min(1, (0.9 - hz.life) * 6 + 0.2);
        const hh = Math.round(hz.h * Math.min(1, k));
        const top = FLOOR_Y - hh;
        for (let y = top; y < FLOOR_Y; y += 4) { const off = Math.round(Math.sin(y * 0.15 + t * 10) * 2); R(c, x + 2 + off, y, hz.w - 4, 4, '#9a4ac8'); R(c, x + 3 + off, y + 1, 2, 2, '#e0a8ff'); }
        R(c, x + 4, top - 3, hz.w - 8, 3, '#9a4ac8');
      } else {
        const fl = Math.sin(t * 30) * 2;
        c.fillStyle = 'rgba(160,40,220,0.45)'; c.fillRect(x - 2 + fl, hz.y, hz.w + 4, hz.h);
        R(c, x + 2, hz.y, hz.w - 4, hz.h, hz.kind === 'flame' ? '#ff6a1a' : '#6a1aa8');
        R(c, x + 5, hz.y, hz.w - 10, hz.h, hz.kind === 'flame' ? '#ffd23a' : '#d88aff');
      }
    }
  }
  clampArena() { this.x = U.clamp(this.x, this.L, this.Rb - this.w); }
}

// ═════════ 1. 가시멧돼지 브램블 ═════════
class Bramble extends Boss {
  constructor(w, x, y) { super(w, x, y, 12, 34, 24); this.state = 'idle'; this.onGround = true; }
  intro(dt) { this.dir = -1; this.legT = this.t; }
  ai(dt) {
    const w = this.world, p = w.player;
    this.vy += GRAV * dt; this.y += this.vy * dt;
    this.onGround = false;
    if (this.y + this.h >= FLOOR_Y) { this.y = FLOOR_Y - this.h; if (this.vy > 0 && this.state === 'leap') this.land(); this.vy = 0; this.onGround = true; }
    this.st -= dt;
    switch (this.state) {
      case 'idle':
        this.dir = U.sign(p.cx - this.cx) || this.dir;
        if (this.st <= 0) {
          this.n++;
          if (this.n % 3 === 0) {
            this.state = 'leap'; this.vy = -340;
            this.vx = U.clamp((p.cx - this.cx) * 1.2, -160, 160) * this.spd;
            Sound.play('jump');
          } else { this.state = 'prep'; this.st = 0.5 / this.spd; Sound.play('roar'); }
        }
        break;
      case 'prep':
        if (Math.random() < 0.4) w.dust(this.cx - this.dir * 14, FLOOR_Y, 1);
        if (this.st <= 0) this.state = 'charge';
        break;
      case 'charge': {
        this.x += this.dir * 175 * this.spd * (this.enraged ? 1.25 : 1) * dt;
        if (Math.random() < 0.5) w.dust(this.cx - this.dir * 14, FLOOR_Y, 1);
        if (this.x <= this.L || this.x + this.w >= this.Rb) {
          this.clampArena(); this.state = 'stun'; this.st = 1.0;
          w.shake = 5; Sound.play('boom');
          const cnt = this.enraged ? 5 : 3;
          for (let i = 0; i < cnt; i++) {
            const ax = U.rand(this.L + 10, this.Rb - 10);
            this.shoot({ x: ax, y: -10 - i * 30, vx: 0, vy: 20, grav: 280, kind: 'acorn', r: 3, life: 4 });
          }
        }
        break;
      }
      case 'stun':
        if (this.st <= 0) {
          this.state = 'idle'; this.st = 0.7 / this.spd;
          if (this.enraged) for (const s of [-0.5, 0, 0.5]) { const v = this.aim(this.cx, this.y, 120, s); this.shoot({ x: this.cx, y: this.y, vx: v.vx, vy: v.vy - 60, grav: 200, kind: 'seed', r: 3, life: 3 }); }
        }
        break;
      case 'leap':
        this.x += this.vx * dt; this.clampArena();
        break;
    }
  }
  land() {
    const w = this.world;
    w.shake = 4; Sound.play('boom');
    for (const d of [-1, 1]) this.shoot({ x: this.cx + d * 16, y: FLOOR_Y - 5, vx: d * 130 * this.spd, vy: 0, kind: 'shock', r: 5, life: 1.8, ghost: true });
    this.state = 'idle'; this.st = 0.8 / this.spd; this.vx = 0;
  }
  vulnerable() { return super.vulnerable(); }
  draw(c, t) {
    const fl = this.flash > 0;
    const P = (x, y, w, h, col) => R(c, x, y, w, h, fl ? '#ffffff' : col);
    c.save();
    c.translate(Math.round(this.cx), Math.round(this.y + this.h));
    c.scale(this.dir, 1);
    const run = this.state === 'charge' ? Math.floor(t * 16) % 2 : 0;
    const sh = this.state === 'prep' ? (Math.floor(t * 30) % 2 ? 1 : -1) : 0;
    c.translate(sh, 0);
    // 다리
    P(-13, -6 - run, 4, 6 + run, '#4a2a14'); P(-6, -6 + run, 4, 6 - run, '#4a2a14'); P(4, -6 - run, 4, 6 + run, '#4a2a14'); P(10, -6 + run, 4, 6 - run, '#4a2a14');
    // 몸통
    P(-16, -20, 30, 15, '#7a4a2a'); P(-14, -22, 24, 2, '#7a4a2a'); P(-16, -8, 30, 2, '#5a341a');
    P(-12, -18, 10, 3, '#9a6a3a');
    // 가시 등
    for (let i = 0; i < 6; i++) { const sx = -14 + i * 4; P(sx, -26 - (i % 2) * 2, 3, 5 + (i % 2) * 2, '#3a9a3a'); P(sx + 1, -27 - (i % 2) * 2, 1, 1, '#a8f0a0'); }
    // 머리
    P(10, -18, 10, 11, '#8a5a32'); P(18, -12, 5, 5, '#c88a6a'); P(20, -11, 1, 1, '#3a1a0a'); P(22, -11, 1, 1, '#3a1a0a');
    P(13, -16, 3, 3, this.enraged ? '#ff2a2a' : '#ffd23a'); P(14, -15, 1, 1, '#000');
    P(18, -8, 2, 4, '#ffffff'); P(19, -10, 2, 2, '#ffffff');
    P(10, -21, 3, 4, '#6a3a1a');
    // 꼬리
    P(-18, -18 + Math.round(Math.sin(t * 10)), 3, 2, '#5a341a');
    c.restore();
  }
}

// ═════════ 2. 수정 골렘 그라닛 ═════════
class Granit extends Boss {
  constructor(w, x, y) { super(w, x, y, 16, 30, 40); this.state = 'walk'; this.st = 1.4; this.arm = 0; }
  ai(dt) {
    const w = this.world, p = w.player;
    this.y = FLOOR_Y - this.h;
    this.st -= dt;
    switch (this.state) {
      case 'walk':
        this.dir = U.sign(p.cx - this.cx) || this.dir;
        this.x += this.dir * 26 * this.spd * dt; this.clampArena();
        this.arm = 0;
        if (this.st <= 0) { this.n++; if (this.n % 2) { this.state = 'raise'; this.st = 0.75 / this.spd; } else { this.state = 'wind'; this.st = 0.5 / this.spd; } }
        break;
      case 'raise':
        this.arm = Math.min(1, this.arm + dt * 3);
        if (this.st <= 0) this.slam();
        break;
      case 'wind':
        this.arm = -1;
        if (this.st <= 0) this.throwRock();
        break;
      case 'recover':
        this.arm = U.approach(this.arm, 0, dt * 2);
        if (this.st <= 0) { this.state = 'walk'; this.st = (this.enraged ? 1.0 : 1.6) / this.spd; }
        break;
    }
  }
  slam() {
    const w = this.world;
    this.state = 'recover'; this.st = 1.1; this.arm = -0.3;
    w.shake = 6; Sound.play('boom');
    for (const d of [-1, 1]) this.shoot({ x: this.cx + d * 18, y: FLOOR_Y - 5, vx: d * 110 * this.spd, vy: 0, kind: 'shock', r: 5, life: 2, ghost: true });
    const cnt = this.enraged ? 6 : 4;
    for (let i = 0; i < cnt; i++) {
      const rx = U.rand(this.L + 12, this.Rb - 12);
      this.hazards.push({ x: rx - 6, y: FLOOR_Y - 2, w: 12, h: 2, warn: 0.55 + i * 0.12, life: 0, kind: 'marker', spawnRock: true });
    }
  }
  throwRock() {
    const w = this.world, p = w.player;
    this.state = 'recover'; this.st = 0.9; this.arm = 1;
    const throws = this.enraged ? 2 : 1;
    for (let k = 0; k < throws; k++) {
      const tof = 1.15 + k * 0.25;
      const ox = this.cx + this.dir * 12, oy = this.y + 6;
      const vy = -260;
      const g = (2 * -vy) / tof;
      const s = new Shot({ owner: 'enemy', x: ox, y: oy, vx: (p.cx - ox) / tof, vy, grav: g, kind: 'rock', r: 6, life: 4, big: true });
      s.onDie = (wd) => { for (const a of [-2.4, -1.57, -0.7]) wd.shots.push(new Shot({ owner: 'enemy', x: s.x, y: s.y - 8, vx: Math.cos(a) * 90, vy: Math.sin(a) * 120, grav: 400, kind: 'crystal', r: 3, life: 2 })); Sound.play('break'); };
      w.shots.push(s);
    }
    Sound.play('shot');
  }
  update(dt) {
    super.update(dt);
    // 경고 표시가 끝나면 천장에서 돌이 떨어진다
    for (const hz of this.hazards) if (hz.spawnRock && hz.warn <= 0 && !hz.spawned) {
      hz.spawned = true; hz.life = 0;
      this.shoot({ x: hz.x + 6, y: 34, vx: 0, vy: 60, grav: 600, kind: 'rock', r: 5, life: 3 });
    }
  }
  hitboxes() { return [this.box()].concat(this.hazards.filter((h) => h.kind !== 'marker' && h.warn <= 0 && h.life > 0)); }
  draw(c, t) {
    const fl = this.flash > 0;
    const P = (x, y, w, h, col) => R(c, x, y, w, h, fl ? '#ffffff' : col);
    for (const hz of this.hazards) if (hz.kind === 'marker' && hz.warn > 0 && Math.floor(t * 12) % 2) { R(c, Math.round(hz.x), FLOOR_Y - 2, 12, 2, '#ff4a4a'); R(c, Math.round(hz.x) + 4, 36, 4, 3, '#8a7ab0'); }
    c.save();
    c.translate(Math.round(this.cx), FLOOR_Y);
    c.scale(this.dir, 1);
    const step = this.state === 'walk' ? Math.floor(t * 4) % 2 : 0;
    P(-12, -10 + step, 9, 10 - step, '#4c4466'); P(3, -10 + (1 - step), 9, 10 - (1 - step), '#4c4466');
    P(-14, -34, 28, 25, '#5e5680'); P(-14, -34, 28, 2, '#8a82b0'); P(-14, -11, 28, 2, '#3a3352');
    P(-6, -28, 12, 10, '#3a3352'); P(-3, -26, 6, 6, this.enraged ? '#ff4a6a' : '#6ef0ff'); P(-2, -25, 2, 2, '#ffffff');
    P(-9, -42, 18, 9, '#5e5680'); P(-9, -42, 18, 1, '#8a82b0');
    P(-5, -39, 3, 2, this.enraged ? '#ff4a4a' : '#ffe85a'); P(3, -39, 3, 2, this.enraged ? '#ff4a4a' : '#ffe85a');
    P(-17, -38, 5, 6, '#6ef0ff'); P(-16, -41, 2, 3, '#bff8ff'); P(12, -38, 5, 6, '#6ef0ff'); P(14, -41, 2, 3, '#bff8ff');
    const ay = Math.round(-this.arm * 16);
    P(-21, -32 + ay, 7, 18, '#4c4466'); P(-22, -16 + ay, 9, 7, '#5e5680');
    P(14, -32 + ay, 7, 18, '#4c4466'); P(13, -16 + ay, 9, 7, '#5e5680');
    if (this.state === 'wind') { P(14, -48, 10, 10, '#8a7ab0'); P(16, -46, 3, 3, '#6ef0ff'); }
    c.restore();
  }
}

// ═════════ 3. 심연의 크라켄 옥토 ═════════
class Okto extends Boss {
  constructor(w, x, y) { super(w, x, y, 16, 36, 34); this.state = 'float'; this.st = 1.5; this.homeX = this.x; this.baseY = this.y; }
  intro(dt) { this.y = this.baseY + Math.sin(this.t * 1.5) * 6; }
  ai(dt) {
    const w = this.world, p = w.player;
    this.st -= dt;
    this.dir = U.sign(p.cx - this.cx) || -1;
    switch (this.state) {
      case 'float':
        this.x = U.approach(this.x, this.homeX, 80 * dt);
        this.y = 60 + Math.sin(this.t * 1.3) * 45;
        if (this.st <= 0) {
          this.n++;
          const m = this.n % 3;
          if (m === 1) { this.state = 'ink'; this.st = 0.25; this.bursts = this.enraged ? 3 : 2; }
          else if (m === 2) { this.state = 'tentacle'; this.st = 1.4; for (let i = 0; i < (this.enraged ? 3 : 2); i++) this.addTentacle(p.cx + (i === 0 ? 0 : (i === 1 ? -46 : 46)), 0.75 + i * 0.25); }
          else { this.state = 'dash'; this.st = 0.6; this.dashY = U.clamp(p.cy - this.h / 2, 30, FLOOR_Y - this.h - 4); Sound.play('roar'); }
        }
        break;
      case 'ink':
        if (this.st <= 0) {
          this.bursts--; this.st = 0.55;
          Sound.play('shot');
          const n = this.enraged ? 7 : 5;
          for (let i = 0; i < n; i++) { const v = this.aim(this.cx - 10, this.cy, 85 * this.spd, (i - (n - 1) / 2) * 0.22); this.shoot({ x: this.cx - 10, y: this.cy, vx: v.vx, vy: v.vy, kind: 'ink', r: 4, life: 4 }); }
          if (this.bursts <= 0) { this.state = 'float'; this.st = 1.6 / this.spd; }
        }
        break;
      case 'tentacle':
        this.y = 60 + Math.sin(this.t * 1.3) * 45;
        if (this.st <= 0) { this.state = 'float'; this.st = 1.4 / this.spd; }
        break;
      case 'dash':
        if (this.st > 0) { this.y = U.approach(this.y, this.dashY, 140 * dt); this.x = U.approach(this.x, this.homeX + 10, 60 * dt); }
        else {
          this.x -= 230 * this.spd * dt;
          if (this.x <= this.L) { this.x = this.L; this.state = 'return'; }
        }
        break;
      case 'return':
        this.x = U.approach(this.x, this.homeX, 110 * dt);
        this.y = U.approach(this.y, 60, 60 * dt);
        if (Math.abs(this.x - this.homeX) < 2) { this.state = 'float'; this.st = 1.2 / this.spd; }
        break;
    }
  }
  addTentacle(x, warn) {
    x = U.clamp(x, this.L + 10, this.Rb - 10);
    this.hazards.push({ x: x - 6, y: FLOOR_Y - 70, w: 12, h: 70, warn, life: 0.9, kind: 'tentacle', sfx: 'splash' });
  }
  draw(c, t) {
    this.drawHazards(c, t);
    const fl = this.flash > 0;
    const P = (x, y, w, h, col) => R(c, x, y, w, h, fl ? '#ffffff' : col);
    const x = Math.round(this.x), y = Math.round(this.y);
    for (let i = 0; i < 6; i++) {
      for (let k = 0; k < 5; k++) {
        const off = Math.round(Math.sin(t * 5 + i + k * 0.7) * (k * 0.8));
        P(x + 3 + i * 5 + off, y + 24 + k * 4, 4 - (k > 3 ? 1 : 0), 4, k % 2 ? '#7a2aa8' : '#9a4ac8');
      }
    }
    P(x + 2, y + 6, 32, 20, '#9a4ac8'); P(x + 5, y + 2, 26, 4, '#9a4ac8'); P(x + 9, y, 18, 2, '#9a4ac8');
    P(x + 8, y + 3, 8, 3, '#d8a0ff');
    for (let i = 0; i < 4; i++) P(x + 6 + i * 7, y + 20, 3, 3, '#e0a8ff');
    P(x + 7, y + 10, 8, 8, '#ffffff'); P(x + 21, y + 10, 8, 8, '#ffffff');
    const ex = this.dir < 0 ? 0 : 3;
    P(x + 8 + ex, y + 12, 4, 5, this.enraged ? '#ff2a4a' : '#1a0a2a'); P(x + 22 + ex, y + 12, 4, 5, this.enraged ? '#ff2a4a' : '#1a0a2a');
    P(x + 6, y + 8, 9, 2, '#5a1a7a'); P(x + 21, y + 8, 9, 2, '#5a1a7a');
  }
}

// ═════════ 4. 모래 웜 둔가르 ═════════
class Dungar extends Boss {
  constructor(w, x, y) {
    super(w, x, y, 14, 18, 16);
    this.state = 'under'; this.st = 1.0; this.mx = this.x; this.hx = this.x; this.hy = FLOOR_Y + 40; this.trail = [];
    this.segs = 7;
  }
  intro(dt) {
    // 등장 연출: 한 번 솟구쳤다 들어감
    if (!this.introStarted) { this.introStarted = true; this.state = 'introJump'; this.hx = this.cx; this.hy = FLOOR_Y + 10; this.vy = -330; this.vx = -40; }
    if (this.state !== 'introJump') return;
    this.moveHead(dt);
    if (this.hy > FLOOR_Y + 40 && this.vy > 0) { this.state = 'under'; this.st = 0.6; this.vy = 0; this.mx = this.hx; }
  }
  moveHead(dt) {
    this.vy += 420 * dt; this.hx += this.vx * dt; this.hy += this.vy * dt;
    this.hx = U.clamp(this.hx, this.L + 10, this.Rb - 10);
    this.trail.unshift({ x: this.hx, y: this.hy });
    if (this.trail.length > 60) this.trail.pop();
    this.x = this.hx - this.w / 2; this.y = this.hy - this.h / 2;
  }
  ai(dt) {
    const w = this.world, p = w.player;
    this.st -= dt;
    if (this.state === 'introJump') this.state = 'under';
    if (this.state === 'under') {
      this.mx = U.approach(this.mx, p.cx, 130 * this.spd * dt);
      this.hy = FLOOR_Y + 40;
      this.trail.unshift({ x: this.mx, y: this.hy }); if (this.trail.length > 60) this.trail.pop();
      if (Math.random() < 0.7) w.dust(this.mx + U.rand(-6, 6), FLOOR_Y, 1, '#e0aa66');
      if (this.st <= 0) {
        this.state = 'rise';
        this.hx = this.mx; this.vy = -390 * Math.min(1.15, this.spd);
        this.vx = (this.mx < (this.L + this.Rb) / 2 ? 1 : -1) * U.rand(50, 80);
        this.spat = false; Sound.play('roar'); w.shake = 4;
        w.burst(this.mx, FLOOR_Y, 14, ['#e0aa66', '#c88a4a', '#f8d8a0']);
      }
    } else if (this.state === 'rise') {
      const pvy = this.vy;
      this.moveHead(dt);
      if (pvy < 0 && this.vy >= 0 && !this.spat) {
        this.spat = true; Sound.play('shot');
        const n = this.enraged ? 5 : 3;
        for (let i = 0; i < n; i++) { const v = this.aim(this.hx, this.hy, 110, (i - (n - 1) / 2) * 0.3); this.shoot({ x: this.hx, y: this.hy, vx: v.vx, vy: v.vy, grav: 120, kind: 'sand', r: 4, life: 3 }); }
      }
      if (this.hy > FLOOR_Y + 40 && this.vy > 0) {
        this.state = 'under'; this.st = (this.enraged ? 0.9 : 1.3) / this.spd; this.mx = this.hx;
        w.burst(this.hx, FLOOR_Y, 10, ['#e0aa66', '#c88a4a']); Sound.play('splash');
      }
    }
  }
  vulnerable() { return super.vulnerable() && this.hy < FLOOR_Y - 4; }
  hurtboxes() { return [{ x: this.hx - 10, y: this.hy - 9, w: 20, h: 18 }]; }
  hitboxes() {
    if (this.dead) return [];
    const out = [];
    if (this.hy < FLOOR_Y) out.push({ x: this.hx - 9, y: this.hy - 8, w: 18, h: 16 });
    for (let i = 1; i <= this.segs; i++) {
      const s = this.trail[i * 6];
      if (s && s.y < FLOOR_Y - 4) out.push({ x: s.x - 6, y: s.y - 6, w: 12, h: 12 });
    }
    return out;
  }
  draw(c, t) {
    const fl = this.flash > 0;
    c.save();
    c.beginPath(); c.rect(this.world.cam.x - 20, -50, G.VW + 40, FLOOR_Y + 50); c.clip();
    for (let i = this.segs; i >= 1; i--) {
      const s = this.trail[i * 6]; if (!s) continue;
      const r = 8 - i * 0.4;
      c.fillStyle = fl ? '#fff' : (i % 2 ? '#c88a4a' : '#b07438');
      c.beginPath(); c.arc(Math.round(s.x), Math.round(s.y), r, 0, Math.PI * 2); c.fill();
      R(c, Math.round(s.x - r + 2), Math.round(s.y - 2), Math.round(r * 2 - 4), 2, fl ? '#fff' : '#8a5a28');
      R(c, Math.round(s.x - 1), Math.round(s.y - r - 2), 2, 3, fl ? '#fff' : '#f2c47a');
    }
    const hx = Math.round(this.hx), hy = Math.round(this.hy);
    const P = (x, y, w, h, col) => R(c, x, y, w, h, fl ? '#ffffff' : col);
    const open = this.state === 'rise' && this.vy > -150 && this.vy < 150 ? 3 : 0;
    P(hx - 10, hy - 9, 20, 16, '#d8a058'); P(hx - 8, hy - 11, 16, 2, '#d8a058'); P(hx - 10, hy + 5, 20, 3, '#9a6a30');
    P(hx - 6, hy - 6, 4, 4, this.enraged ? '#ff3a3a' : '#2a1a10'); P(hx + 2, hy - 6, 4, 4, this.enraged ? '#ff3a3a' : '#2a1a10');
    P(hx - 5, hy - 6, 1, 1, '#fff'); P(hx + 3, hy - 6, 1, 1, '#fff');
    P(hx - 7, hy + 1, 14, 2 + open, '#5a2a10');
    for (let i = 0; i < 4; i++) P(hx - 6 + i * 4, hy + 1, 2, 2, '#ffffff');
    P(hx - 12, hy - 12, 4, 6, '#9a6a30'); P(hx + 8, hy - 12, 4, 6, '#9a6a30');
    c.restore();
  }
}

// ═════════ 5. 폭풍 그리폰 템페스트 ═════════
class Tempest extends Boss {
  constructor(w, x, y) { super(w, x, y, 18, 36, 26); this.state = 'hover'; this.st = 2.2; this.cxh = (this.L + this.Rb) / 2; this.featherT = 0; }
  intro(dt) { this.y = 50 + Math.sin(this.t * 3) * 6; }
  ai(dt) {
    const w = this.world, p = w.player;
    this.st -= dt;
    switch (this.state) {
      case 'hover': {
        const hw = (this.Rb - this.L) / 2 - 30;
        const tx = this.cxh + Math.sin(this.t * 0.9) * hw - this.w / 2;
        const ty = 66 + Math.sin(this.t * 1.8) * 30;
        this.x = U.approach(this.x, tx, 120 * dt); this.y = U.approach(this.y, ty, 90 * dt);
        this.dir = U.sign(p.cx - this.cx) || 1;
        this.featherT -= dt;
        if (this.featherT <= 0) {
          this.featherT = (this.enraged ? 0.55 : 0.85) / this.spd;
          const v = this.aim(this.cx, this.y + this.h, 110 * this.spd);
          this.shoot({ x: this.cx, y: this.y + this.h, vx: v.vx, vy: v.vy, kind: 'feather', r: 3, life: 3 });
        }
        if (this.st <= 0) {
          this.n++;
          if (this.n % 3 === 0) {
            this.state = 'storm'; this.st = 1.6;
            const xs = [p.cx, p.cx - 52, p.cx + 52].concat(this.enraged ? [p.cx - 104, p.cx + 104] : []);
            xs.forEach((x, i) => this.addPillar(U.clamp(x, this.L + 8, this.Rb - 8), 0.7 + i * 0.12, 0.3, 'bolt', 0, 'thunder'));
          } else { this.state = 'prep'; this.st = 0.55; Sound.play('roar'); }
        }
        break;
      }
      case 'storm':
        this.y = U.approach(this.y, 40, 60 * dt);
        if (this.st <= 0) { this.state = 'hover'; this.st = 2.0 / this.spd; }
        break;
      case 'prep':
        this.y = U.approach(this.y, 40, 80 * dt);
        if (this.st <= 0) {
          this.state = 'dive'; this.dt0 = 0;
          this.p0 = { x: this.x, y: this.y };
          const tx = U.clamp(p.cx - this.w / 2, this.L, this.Rb - this.w);
          this.p1 = { x: tx, y: FLOOR_Y - this.h + 30 };
          this.p2 = { x: tx + (tx - this.x), y: 50 };
          this.p2.x = U.clamp(this.p2.x, this.L, this.Rb - this.w);
          Sound.play('shot');
        }
        break;
      case 'dive': {
        this.dt0 += dt * this.spd / 1.15;
        const k = Math.min(1, this.dt0);
        const a = (1 - k) * (1 - k), b = 2 * (1 - k) * k, cc = k * k;
        const nx = a * this.p0.x + b * this.p1.x + cc * this.p2.x;
        const ny = a * this.p0.y + b * this.p1.y + cc * this.p2.y;
        this.dir = U.sign(nx - this.x) || this.dir;
        this.x = nx; this.y = Math.min(ny, FLOOR_Y - this.h);
        if (k > 0.45 && k < 0.55 && !this.landed) { this.landed = true; this.state = 'rest'; this.st = this.enraged ? 0.7 : 1.1; this.world.shake = 3; Sound.play('boom'); this.world.dust(this.cx, FLOOR_Y, 8); this.restK = k; }
        if (k >= 1) { this.state = 'hover'; this.st = 2.2 / this.spd; this.landed = false; }
        break;
      }
      case 'rest':
        this.y = FLOOR_Y - this.h;
        if (this.st <= 0) { this.state = 'dive'; this.dt0 = this.restK + 0.06; }
        break;
    }
  }
  draw(c, t) {
    this.drawHazards(c, t);
    const fl = this.flash > 0;
    const P = (x, y, w, h, col) => R(c, x, y, w, h, fl ? '#ffffff' : col);
    c.save();
    c.translate(Math.round(this.cx), Math.round(this.y + this.h));
    c.scale(this.dir, 1);
    const flap = this.state === 'rest' ? 0 : Math.sin(t * (this.state === 'dive' ? 6 : 12));
    const wy = Math.round(flap * 10);
    // 날개 (뒤)
    P(-14, -26 + wy, 14, 6, '#c8a048'); P(-20, -30 + wy * 1.4, 10, 5, '#e8c060'); P(-24, -33 + wy * 1.7, 6, 4, '#fff4c0');
    // 몸통 (사자)
    P(-16, -16, 26, 12, '#d8a858'); P(-16, -16, 26, 2, '#f0c878'); P(-14, -5, 4, 5, '#b08038'); P(4, -5, 4, 5, '#b08038');
    P(-20, -14 + Math.round(Math.sin(t * 6)), 5, 2, '#b08038'); P(-23, -16 + Math.round(Math.sin(t * 6)), 3, 3, '#7a5020');
    // 머리 (독수리)
    P(6, -26, 12, 12, '#ffffff'); P(8, -28, 8, 2, '#ffffff'); P(4, -18, 6, 6, '#f0f0f8');
    P(17, -22, 6, 4, '#ffb020'); P(20, -18, 3, 2, '#d88a10');
    P(12, -24, 3, 3, this.enraged ? '#ff2a4a' : '#2a6ad8'); P(13, -23, 1, 1, '#fff');
    P(6, -30, 3, 4, '#fff4c0'); P(9, -31, 3, 3, '#e8c040');
    // 날개 (앞)
    P(-6, -24 - wy, 14, 6, '#e8c060'); P(-10, -29 - wy * 1.4, 10, 5, '#fff4c0'); P(-12, -33 - wy * 1.7, 6, 4, '#ffffff');
    c.restore();
  }
}

// ═════════ 6. 그림자왕 모르바스 ═════════
class Morvath extends Boss {
  constructor(w, x, y) {
    super(w, x, y, 24, 22, 40);
    this.state = 'idle'; this.st = 1.0; this.alpha = 1; this.phase2 = false; this.scale = 1;
    this.spots = [];
    const midL = this.L, midR = this.Rb;
    this.spots.push({ x: midL + 30, y: FLOOR_Y }, { x: midR - 30, y: FLOOR_Y }, { x: (midL + midR) / 2, y: FLOOR_Y });
    // 보스 구역 발판 위
    const ac = this.world.arenaCol;
    this.spots.push({ x: (ac + 5) * TILE, y: 8 * TILE }, { x: (ac + 19) * TILE, y: 8 * TILE });
  }
  intro(dt) { this.dir = -1; }
  vulnerable() { return super.vulnerable() && this.alpha > 0.6 && this.state !== 'transform'; }
  ai(dt) {
    const w = this.world, p = w.player;
    this.st -= dt;
    this.dir = U.sign(p.cx - this.cx) || this.dir;
    if (!this.phase2 && this.enraged && this.state !== 'transform') {
      this.phase2 = true; this.state = 'transform'; this.st = 1.6; this.alpha = 1;
      Sound.play('roar'); w.shake = 6; w.flashT = 0.4;
      w.shots = w.shots.filter((s) => s.owner === 'player');
      this.hazards = [];
    }
    const fast = this.phase2 ? 0.7 : 1;
    switch (this.state) {
      case 'transform':
        this.scale = U.approach(this.scale, 1.3, dt * 0.5);
        if (Math.random() < 0.5) w.spark(this.cx + U.rand(-16, 16), this.cy + U.rand(-20, 20), '#c06aff');
        if (this.st <= 0) { this.state = 'idle'; this.st = 0.5; }
        break;
      case 'idle':
        if (this.st <= 0) { this.state = 'vanish'; this.st = 0.4; Sound.play('teleport'); }
        break;
      case 'vanish':
        this.alpha = Math.max(0, this.st / 0.4);
        if (this.st <= 0) {
          const cands = this.spots.filter((s) => Math.abs(s.x - p.cx) > 70);
          const s = U.pick(cands.length ? cands : this.spots);
          this.x = s.x - this.w / 2; this.y = s.y - this.h;
          this.state = 'appear'; this.st = 0.4;
        }
        break;
      case 'appear':
        this.alpha = 1 - Math.max(0, this.st / 0.4);
        if (this.st <= 0) { this.alpha = 1; this.state = 'cast'; this.st = 0.45 * fast; }
        break;
      case 'cast':
        if (this.st <= 0) { this.attack(); this.state = 'idle'; this.st = (this.phase2 ? 1.3 : 1.8) / this.spd; }
        break;
    }
  }
  attack() {
    const w = this.world, p = w.player;
    this.n++;
    const opts = this.phase2 ? ['orbs', 'pillars', 'ring', 'summon', 'ring', 'pillars'] : ['orbs', 'pillars', 'orbs', 'summon'];
    let a = opts[this.n % opts.length];
    if (a === 'summon' && w.enemies.length >= 2) a = 'orbs';
    Sound.play('teleport');
    if (a === 'orbs') {
      const n = this.phase2 ? 4 : 3;
      for (let i = 0; i < n; i++) {
        const ang = -Math.PI / 2 + (i - (n - 1) / 2) * 0.6;
        this.shoot({ x: this.cx, y: this.y + 10, vx: Math.cos(ang) * 70, vy: Math.sin(ang) * 70, kind: 'shadow', r: 5, life: 4.5, homing: 1.7, hp: 1, ghost: true });
      }
    } else if (a === 'pillars') {
      const n = this.phase2 ? 5 : 3;
      for (let i = 0; i < n; i++) {
        const x = U.clamp(p.cx + (i - (n - 1) / 2) * 44, this.L + 8, this.Rb - 8);
        this.addPillar(x, 0.65 + i * 0.15, 0.5, 'shadowfire', 50, 'fire');
      }
    } else if (a === 'ring') {
      for (let wave = 0; wave < 2; wave++) {
        for (let i = 0; i < 12; i++) {
          const ang = (i / 12) * Math.PI * 2 + wave * 0.26;
          const s = new Shot({ owner: 'enemy', x: this.cx, y: this.cy, vx: Math.cos(ang) * (70 + wave * 25), vy: Math.sin(ang) * (70 + wave * 25), kind: 'shadow', r: 4, life: 4, ghost: true, hp: 1 });
          w.shots.push(s);
        }
      }
    } else if (a === 'summon') {
      const col = Math.floor(this.cx / TILE);
      for (const d of [-2, 2]) {
        const e = new Enemy(w, 'y', U.clamp(col + d, w.arenaCol + 2, w.level.cols - 3), 6);
        w.enemies.push(e);
        w.burst(e.cx, e.cy, 8, ['#c06aff', '#2a1838']);
      }
    }
  }
  box() { const s = this.scale; return { x: this.cx - 9 * s, y: this.y + this.h - 38 * s, w: 18 * s, h: 38 * s }; }
  draw(c, t) {
    this.drawHazards(c, t);
    drawMorvath(c, this.cx, this.y + this.h, t, { alpha: this.alpha, flash: this.flash > 0, scale: this.scale, dir: this.dir });
    if (this.phase2) {
      c.strokeStyle = `rgba(255,60,90,${0.4 + Math.sin(t * 8) * 0.3})`; c.lineWidth = 1;
      c.beginPath(); c.arc(Math.round(this.cx), Math.round(this.y + this.h - 24), 24 + Math.sin(t * 5) * 2, 0, Math.PI * 2); c.stroke();
    }
  }
}

function createBoss(id, world, x, y) {
  switch (id) {
    case 'bramble': return new Bramble(world, x, y);
    case 'granit': return new Granit(world, x, y);
    case 'okto': return new Okto(world, x, y);
    case 'dungar': return new Dungar(world, x, y);
    case 'tempest': return new Tempest(world, x, y);
    case 'morvath': return new Morvath(world, x, y);
  }
}

// 컷신용: 정화된 보스 모습 그리기
function drawBossPortrait(c, id, x, y, t) {
  const fake = { world: { cam: { x: 0 }, diff: DIFFICULTY.normal, arenaCol: 0, level: { w: 2000, cols: 100 }, bossState: 'fight' } };
  let b;
  switch (id) {
    case 'bramble': b = Object.create(Bramble.prototype); Object.assign(b, { w: 34, h: 24, x: x - 17, y: y - 24, dir: -1, state: 'idle', flash: 0, hp: 10, maxHp: 10 }); break;
    case 'granit': b = Object.create(Granit.prototype); Object.assign(b, { w: 30, h: 40, x: x - 15, y: y - 40, dir: -1, state: 'idle', arm: 0, flash: 0, hp: 10, maxHp: 10 }); break;
    case 'okto': b = Object.create(Okto.prototype); Object.assign(b, { w: 36, h: 34, x: x - 18, y: y - 52 + Math.sin(t * 2) * 3, dir: -1, state: 'float', flash: 0, hazards: [], hp: 10, maxHp: 10 }); break;
    case 'dungar': b = Object.create(Dungar.prototype); Object.assign(b, { hx: x, hy: y - 30, trail: [], segs: 7, flash: 0, state: 'idle', vy: 0, hp: 10, maxHp: 10, world: fake.world }); for (let i = 0; i < 60; i++) b.trail.push({ x: x + 14 - Math.sin(i * 0.08) * 10, y: y - 30 + i * 1.2 }); break;
    case 'tempest': b = Object.create(Tempest.prototype); Object.assign(b, { w: 36, h: 26, x: x - 18, y: y - 26, dir: -1, state: 'rest', flash: 0, hazards: [], hp: 10, maxHp: 10 }); break;
    default: return;
  }
  b.draw(c, t);
}
