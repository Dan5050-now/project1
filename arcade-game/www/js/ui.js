'use strict';
// ─────────────────────────────────────────────────────────────
//  ui.js — 버튼/패널/아이콘/HUD/터치 컨트롤 그리기 도우미
// ─────────────────────────────────────────────────────────────

const SPR = document.createElement('canvas');
SPR.width = 128; SPR.height = 128;
const SPRC = SPR.getContext('2d');

// 픽셀아트를 화면(고해상도) 좌표에 확대해서 그림. drawFn은 (64, 112)를 발밑으로 사용
function blit(drawFn, x, y, scale, alpha = 1) {
  SPRC.clearRect(0, 0, 128, 128);
  SPRC.imageSmoothingEnabled = false;
  drawFn(SPRC, 64, 112);
  const c = G.sctx;
  c.save();
  c.imageSmoothingEnabled = false;
  c.globalAlpha = alpha;
  c.drawImage(SPR, 0, 0, 128, 128, Math.round(x - 64 * scale), Math.round(y - 112 * scale), Math.round(128 * scale), Math.round(128 * scale));
  c.restore();
}
function blitIcon(kind, x, y, scale) { blit((c, cx, cy) => drawItem(c, kind, cx, cy - 8, 0.4, true), x, y + 8 * scale, scale); }

const UI = {
  sel: 0,
  resetSel(i = 0) { this.sel = i; },
  // 버튼 목록 처리 (터치 + 키보드). 버튼: {x,y,w,h,label,on,disabled}
  handle(items, opts = {}) {
    const n = items.length;
    if (!n) return false;
    if (this.sel >= n) this.sel = 0;
    const d = opts.horizontal ? Input.nav.dx || Input.nav.dy : Input.nav.dy || Input.nav.dx;
    if (d) { this.sel = (this.sel + d + n) % n; Sound.play('select'); }
    if (Input.nav.ok) {
      const it = items[this.sel];
      if (it.disabled) Sound.play('deny');
      else { if (!it.silent) Sound.play('confirm'); it.on(); }
      return true;
    }
    for (const tp of Input.taps) {
      for (let i = 0; i < n; i++) {
        const b = items[i];
        if (tp.x >= b.x && tp.x <= b.x + b.w && tp.y >= b.y && tp.y <= b.y + b.h) {
          this.sel = i;
          if (b.disabled) { Sound.play('deny'); return true; }
          if (!b.silent) Sound.play('confirm');
          b.on();
          return true;
        }
      }
    }
    return false;
  },
  button(b, selected, t) {
    const c = G.sctx, S = G.S;
    const pulse = selected ? 1 + Math.sin(t * 6) * 0.02 : 1;
    const w = b.w * pulse, h = b.h * pulse, x = b.x - (w - b.w) / 2, y = b.y - (h - b.h) / 2;
    c.save();
    G.roundRect(c, x, y + 2 * S, w, h, 6 * S); c.fillStyle = 'rgba(0,0,0,0.35)'; c.fill();
    G.roundRect(c, x, y, w, h, 6 * S);
    const g = c.createLinearGradient(0, y, 0, y + h);
    if (b.disabled) { g.addColorStop(0, '#4a4860'); g.addColorStop(1, '#34324a'); }
    else if (selected) { g.addColorStop(0, b.color || '#ffd86a'); g.addColorStop(1, b.color2 || '#e8902a'); }
    else { g.addColorStop(0, '#3e3a7a'); g.addColorStop(1, '#26235a'); }
    c.fillStyle = g; c.fill();
    c.lineWidth = 1.5 * S; c.strokeStyle = selected ? '#ffffff' : 'rgba(255,255,255,0.35)'; c.stroke();
    c.restore();
    const col = b.disabled ? '#8a88a0' : selected ? '#2a1a08' : '#ffffff';
    const size = b.size || 10;
    if (b.sub) {
      G.text(b.label, x + w / 2, y + h * 0.38, size, col, 'center', { outline: selected ? false : undefined });
      G.text(b.sub, x + w / 2, y + h * 0.72, size * 0.62, selected ? '#4a3010' : '#c8c4f0', 'center', { outline: false, weight: 600 });
    } else G.text(b.label, x + w / 2, y + h / 2 + 0.5 * S, size, col, 'center', { outline: selected ? false : undefined });
  },
  dim(a = 0.6) { const c = G.sctx; c.fillStyle = `rgba(6,4,20,${a})`; c.fillRect(0, 0, G.W, G.H); },
  starfield(t, top = '#140f30', bot = '#2c1c58') {
    const c = G.sctx;
    const g = c.createLinearGradient(0, 0, 0, G.H);
    g.addColorStop(0, top); g.addColorStop(1, bot);
    c.fillStyle = g; c.fillRect(0, 0, G.W, G.H);
    for (let i = 0; i < 70; i++) {
      const x = U.hash(i, 1, 3) * G.W, y = U.hash(i, 2, 3) * G.H;
      const a = 0.3 + 0.7 * Math.abs(Math.sin(t * (0.5 + U.hash(i, 3, 3)) + i));
      c.fillStyle = `rgba(255,255,255,${a})`;
      const s = (U.hash(i, 4, 3) < 0.2 ? 2 : 1) * G.S * 0.6;
      c.fillRect(x, y, s, s);
    }
  },
  heart(x, y, s, full) {
    const c = G.sctx;
    const px = (a, b, w, h, col) => { c.fillStyle = col; c.fillRect(x + a * s, y + b * s, w * s, h * s); };
    const main = full ? '#ff3a5a' : '#3a2a4a', edge = full ? '#ffc0c8' : '#5a4a6a';
    px(1, 0, 3, 1, main); px(5, 0, 3, 1, main); px(0, 1, 9, 3, main); px(1, 4, 7, 1, main); px(2, 5, 5, 1, main); px(3, 6, 3, 1, main); px(4, 7, 1, 1, main);
    px(1, 1, 2, 1, edge);
  },
};

// ─── HUD ───
function drawHUD(world, t) {
  const c = G.sctx, S = G.S, p = world.player, run = world.run;
  const x0 = 6 * S, y0 = 5 * S;
  const hw = Math.max(92, p.maxHp * 11 + 32) * S;
  G.panel(x0, y0, hw, 30 * S, { fill: 'rgba(10,8,30,0.55)', stroke: 'rgba(255,255,255,0.25)', lw: 1 });
  for (let i = 0; i < p.maxHp; i++) UI.heart(x0 + 5 * S + i * 11 * S, y0 + 4 * S, S, i < p.hp);
  let ix = x0 + 6 * S + p.maxHp * 11 * S;
  if (p.shield) { blitIcon('shield', ix + 5 * S, y0 + 8 * S, S * 0.8); ix += 12 * S; }
  if (p.powerT > 0) {
    blitIcon('power', ix + 5 * S, y0 + 8 * S, S * 0.8);
    c.fillStyle = '#ff8a5a'; c.fillRect(ix, y0 + 15 * S, 10 * S * Math.min(1, p.powerT / 15), 1.5 * S); ix += 13 * S;
  }
  if (p.starT > 0) {
    blitIcon('star', ix + 5 * S, y0 + 8 * S, S * 0.8);
    c.fillStyle = '#ffe85a'; c.fillRect(ix, y0 + 15 * S, 10 * S * (p.starT / 8), 1.5 * S);
  }
  // 목숨 / 코인 / 점수
  const ry = y0 + 22.5 * S;
  blit((cc, cx, cy) => drawHero(cc, run.char, cx, cy, 1, 'idle', 0), x0 + 10 * S, ry + 7 * S, S * 0.55);
  G.text('×' + Math.max(0, run.lives), x0 + 16 * S, ry, 8, '#ffffff');
  blitIcon('coin', x0 + 40 * S, ry - 1 * S, S * 0.7);
  G.text(String(run.coins), x0 + 45 * S, ry, 8, '#ffe85a');
  G.text(U.fmt(run.score, 7), G.W / 2, 13 * S, 9, '#ffffff', 'center');
  if (!world.boss) G.text(world.level.stage.name, G.W / 2, 24 * S, 6.5, '#d8d4ff', 'center', { weight: 600 });

  // 보스 체력바
  const b = world.boss;
  if (b && world.bossState !== 'none') {
    const bw = Math.min(G.W * 0.5, 200 * S), bx = (G.W - bw) / 2, by = 25 * S;
    G.text(world.level.stage.bossName, G.W / 2, by, 7.5, '#ffb0b8', 'center');
    G.panel(bx, by + 5 * S, bw, 7 * S, { fill: 'rgba(20,6,16,0.8)', stroke: '#ffd86a', r: 3, lw: 1 });
    const k = world.bossState === 'intro' ? Math.min(1, world.bossT / 1.5) : b.hp / b.maxHp;
    const g = c.createLinearGradient(bx, 0, bx + bw, 0);
    g.addColorStop(0, '#ff3a5a'); g.addColorStop(1, '#ff9a3a');
    c.fillStyle = g; c.fillRect(bx + 1.5 * S, by + 6.5 * S, (bw - 3 * S) * k, 4 * S);
  }
  // 일시정지 버튼
  const pb = Input.pauseBtn;
  c.save();
  c.fillStyle = 'rgba(10,8,30,0.5)'; c.beginPath(); c.arc(pb.x, pb.y, pb.r, 0, Math.PI * 2); c.fill();
  c.strokeStyle = 'rgba(255,255,255,0.5)'; c.lineWidth = S; c.stroke();
  c.fillStyle = '#fff'; c.fillRect(pb.x - 3.5 * S, pb.y - 4 * S, 2.5 * S, 8 * S); c.fillRect(pb.x + 1 * S, pb.y - 4 * S, 2.5 * S, 8 * S);
  c.restore();
}

function drawTouchControls(t) {
  if (Input.keyUsed && !Input.touchSeen) return;
  const c = G.sctx, S = G.S;
  const s = Input.stick;
  const act = s.id !== null;
  c.save();
  c.globalAlpha = act ? 0.55 : 0.32;
  c.fillStyle = 'rgba(255,255,255,0.12)'; c.strokeStyle = 'rgba(255,255,255,0.7)'; c.lineWidth = 1.5 * S;
  c.beginPath(); c.arc(s.cx, s.cy, s.r, 0, Math.PI * 2); c.fill(); c.stroke();
  c.fillStyle = 'rgba(255,255,255,0.8)';
  for (const d of [-1, 1]) {
    c.beginPath(); c.moveTo(s.cx + d * s.r * 0.78, s.cy); c.lineTo(s.cx + d * s.r * 0.58, s.cy - 5 * S); c.lineTo(s.cx + d * s.r * 0.58, s.cy + 5 * S); c.fill();
  }
  const kx = s.cx + U.clamp(s.nx, -1, 1) * s.r * 0.7, ky = s.cy + U.clamp(s.ny, -1, 1) * s.r * 0.7;
  c.globalAlpha = act ? 0.8 : 0.45;
  const g = c.createRadialGradient(kx - 3 * S, ky - 3 * S, 1, kx, ky, s.r * 0.45);
  g.addColorStop(0, '#ffffff'); g.addColorStop(1, '#9a96d8');
  c.fillStyle = g; c.beginPath(); c.arc(kx, ky, s.r * 0.42, 0, Math.PI * 2); c.fill();
  c.restore();
  for (const role of ['attack', 'jump']) {
    const b = Input.btn[role];
    const pressed = b.ids.size > 0 || (role === 'jump' ? Input.jumpHeld : Input.attackHeld);
    c.save();
    c.globalAlpha = pressed ? 0.85 : 0.5;
    const col = role === 'jump' ? ['#7ad8ff', '#2a7ad8'] : ['#ffa07a', '#d83a4a'];
    const gg = c.createRadialGradient(b.x - b.r * 0.3, b.y - b.r * 0.3, 1, b.x, b.y, b.r);
    gg.addColorStop(0, pressed ? '#ffffff' : col[0]); gg.addColorStop(1, col[1]);
    c.fillStyle = gg; c.beginPath(); c.arc(b.x, b.y + (pressed ? S : 0), b.r, 0, Math.PI * 2); c.fill();
    c.strokeStyle = 'rgba(255,255,255,0.85)'; c.lineWidth = 1.5 * S; c.stroke();
    c.restore();
    G.text(b.label, b.x, b.y - 2 * S + (pressed ? S : 0), b.r / S * 0.75, '#ffffff', 'center');
    G.text(role === 'jump' ? (Flow.run && STAGES[Flow.run.stage].theme === 'sea' ? '수영' : '점프') : '공격', b.x, b.y + b.r * 0.55, 5.5, '#ffffff', 'center', { weight: 700 });
  }
}

// 메뉴 장면용: 바닥 띠
const GroundCache = {};
function drawGroundBand(c, theme, camX) {
  if (!GroundCache[theme]) {
    const cv = document.createElement('canvas'); cv.width = 512; cv.height = VH;
    const fake = { theme: THEMES[theme], themeName: theme, seed: 5, tileAt: (cc, r) => (r >= 11 ? T.SOLID : T.EMPTY) };
    const cx = cv.getContext('2d');
    for (let r = 11; r < ROWS; r++) for (let col = 0; col < 32; col++) drawTile(cx, T.SOLID, col, r, fake);
    GroundCache[theme] = cv;
  }
  const cv = GroundCache[theme];
  const off = -((camX % 512) + 512) % 512;
  for (let x = Math.floor(off); x < G.VW; x += 512) c.drawImage(cv, x, 0);
}

function heroName() { return Flow.run ? CHARACTERS[Flow.run.char].name : '용사'; }
function fillText(text) {
  if (typeof text === 'object') text = text[Flow.run ? Flow.run.char : 'leo'];
  return String(text).replace(/\{hero\}/g, heroName());
}
