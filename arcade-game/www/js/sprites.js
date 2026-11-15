'use strict';
// ─────────────────────────────────────────────────────────────
//  sprites.js — 캐릭터 / 적 / 아이템 / NPC 픽셀아트 (모두 코드로 그림)
//  좌표 기준: (x, y) = 발 밑 가운데, dir = 바라보는 방향(1 / -1)
// ─────────────────────────────────────────────────────────────

const HERO_STYLE = {
  leo: {
    skin: '#f8c89a', skinD: '#d89a6a', hair: '#ffd23a', hairD: '#d8a018', top: '#2f6fe0', topD: '#1d4aa8', topL: '#5a94ff',
    pants: '#34325a', boot: '#7a4420', accent: '#20b8a0', eye: '#1a1a2a',
  },
  mina: {
    skin: '#f8d0a8', skinD: '#d8a07a', hair: '#9a5ae0', hairD: '#6a34a8', top: '#2fb86a', topD: '#1e8048', topL: '#6ae09a',
    pants: '#1e5a3a', boot: '#2a2a3a', accent: '#ff4a5a', eye: '#2a1a3a',
  },
  sera: {
    skin: '#fcd8c0', skinD: '#e0a888', hair: '#ffa8cc', hairD: '#e070a0', top: '#8a4ae0', topD: '#5a2aa8', topL: '#b07aff',
    pants: '#4a2a6a', boot: '#4a2a6a', accent: '#ffd86a', eye: '#2a1a4a',
  },
};

function drawHero(c, id, x, y, dir, pose, t, o = {}) {
  const st = HERO_STYLE[id];
  const fl = o.flash;
  const P = (px, py, w, h, col) => R(c, px, py, w, h, fl ? '#ffffff' : col);
  c.save();
  c.translate(Math.round(x), Math.round(y));
  if (pose === 'dead') { c.rotate(t * 10); c.translate(0, 8); }
  c.scale(dir, 1);
  if (o.alpha != null) c.globalAlpha = o.alpha;

  let by = 0, lf = 0, lb = 0, lfy = 0, lby = 0, arm = 'down';
  const runF = Math.floor(t * 12) % 4;
  switch (pose) {
    case 'idle': by = Math.sin(t * 3) > 0.3 ? 1 : 0; break;
    case 'run': lf = [2, 0, -2, 0][runF]; lb = -lf; lfy = runF === 0 ? -1 : 0; lby = runF === 2 ? -1 : 0; by = runF % 2 ? -1 : 0; arm = runF < 2 ? 'fwd' : 'back'; break;
    case 'jump': lf = 2; lfy = -2; lb = -1; lby = -1; arm = 'up'; break;
    case 'fall': lf = 1; lb = -2; arm = 'out'; break;
    case 'swim': lf = Math.sin(t * 12) > 0 ? 2 : -1; lb = -lf; lfy = -1; arm = Math.sin(t * 8) > 0 ? 'fwd' : 'out'; break;
    case 'hurt': by = 1; lf = 2; lb = 1; arm = 'out'; break;
    case 'win': arm = 'raise'; by = Math.sin(t * 8) > 0 ? -1 : 0; break;
    case 'attack': arm = 'atk'; break;
    case 'dead': arm = 'out'; break;
  }
  const atkP = o.atkP || 0;
  const kick = id === 'mina' && pose === 'attack';

  // 머리 뒤 장식 (뒤에 그려짐)
  if (id === 'leo') {
    const flap = Math.floor(t * 8) % 2;
    P(-8, -17 + by + flap, 4, 1, st.accent); P(-7, -16 + by, 2, 1, st.accent);
  } else if (id === 'mina') {
    const w1 = Math.round(Math.sin(t * 9) * 1.5);
    P(-8, -17 + by, 4, 3, st.hair); P(-10, -15 + by + w1, 3, 3, st.hair); P(-11, -13 + by + w1, 2, 2, st.hairD);
    // 빨간 스카프 (휘날림)
    const s1 = Math.round(Math.sin(t * 12) * 1.5), s2 = Math.round(Math.sin(t * 12 + 1.5) * 2);
    P(-7, -11 + by + s1, 4, 2, st.accent); P(-10, -10 + by + s2, 3, 2, st.accent); P(-12, -9 + by + s2, 2, 1, '#c82a3a');
  } else {
    P(-6, -17 + by, 3, 9, st.hair); P(-7, -10 + by, 2, 3, st.hairD);
  }
  // 뒷팔
  if (arm !== 'atk' || id === 'mina') P(-5, -10 + by, 2, 4, st.topD);
  // 다리
  if (id === 'sera') {
    P(-3 + lb, -2 + lby, 3, 2, st.boot); P(0 + lf, -2 + lfy, 3, 2, st.boot);
  } else if (kick) {
    const ext = atkP < 0.75 ? 1 : 0.5;
    P(-3, -5, 3, 2, st.pants); P(-3, -3, 3, 3, st.boot);
    P(1, -7, Math.round(7 * ext), 3, st.pants); P(1 + Math.round(7 * ext), -8, 3, 4, st.boot); P(1 + Math.round(7 * ext), -8, 3, 1, '#f0f0f8');
  } else {
    P(-3 + lb, -5 + lby, 3, 2, st.pants); P(-3 + lb, -3 + lby, 3, 3, st.boot);
    P(0 + lf, -5 + lfy, 3, 2, st.pants); P(0 + lf, -3 + lfy, 3, 3, st.boot);
    if (id === 'mina') { P(-3 + lb, -3 + lby, 3, 1, '#f0f0f8'); P(0 + lf, -3 + lfy, 3, 1, '#f0f0f8'); }
  }
  // 몸통
  if (id === 'sera') {
    P(-4, -11 + by, 8, 9 - by, st.top); P(-5, -5 + by, 10, 3 - by, st.top);
    P(-5, -3, 10, 1, st.accent); P(-1, -11 + by, 2, 8, st.topL); P(-4, -11 + by, 8, 1, st.accent);
  } else {
    P(-4, -11 + by, 8, 6, st.top); P(-4, -11 + by, 8, 1, st.topL); P(-4, -6 + by, 8, 1, st.topD);
    if (id === 'leo') { P(-2, -10 + by, 5, 3, '#d8e0ee'); P(-2, -10 + by, 5, 1, '#ffffff'); P(-4, -7 + by, 8, 1, '#6a3a1a'); P(0, -7 + by, 2, 1, '#ffd23a'); }
    else { P(-4, -8 + by, 8, 1, st.accent); P(2, -10 + by, 1, 2, st.topD); }
  }
  // 머리
  const hy = -18 + by + (pose === 'hurt' ? 0 : 0);
  P(-4, hy, 8, 7, st.skin); P(-4, hy + 6, 8, 1, st.skinD);
  // 눈
  if (pose === 'hurt' || pose === 'dead') { P(1, hy + 3, 1, 1, st.eye); P(3, hy + 3, 1, 1, st.eye); P(2, hy + 4, 1, 1, st.eye); }
  else if (pose === 'win') { P(1, hy + 3, 3, 1, st.eye); }
  else { P(2, hy + 2, 1, 3, st.eye); P(2, hy + 2, 1, 1, '#ffffff'); }
  P(1, hy + 5, 2, 1, '#ff9a9a');
  // 머리카락 / 모자
  if (id === 'leo') {
    P(-5, hy - 1, 9, 3, st.hair); P(-5, hy + 1, 2, 4, st.hair); P(-4, hy - 2, 2, 1, st.hair); P(-1, hy - 3, 2, 2, st.hair); P(2, hy - 2, 2, 1, st.hair);
    P(3, hy + 1, 1, 1, st.hair); P(-5, hy + 2, 2, 1, st.hairD); P(-4, hy + 1, 8, 1, st.accent);
  } else if (id === 'mina') {
    P(-5, hy - 1, 9, 3, st.hair); P(-5, hy + 1, 2, 5, st.hair); P(2, hy, 3, 2, st.hair); P(-3, hy - 2, 5, 1, st.hair);
    P(-4, hy + 1, 8, 1, st.accent);
  } else {
    P(-5, hy, 3, 7, st.hair); P(3, hy + 1, 2, 2, st.hair);
    P(-7, hy, 14, 2, '#6a34c0'); P(-7, hy + 1, 14, 1, '#4a2090');
    P(-4, hy - 4, 8, 4, '#6a34c0'); P(-3, hy - 7, 6, 3, '#6a34c0'); P(-2, hy - 9, 4, 2, '#6a34c0'); P(-2, hy - 11, 3, 2, '#6a34c0'); P(-3, hy - 12, 2, 1, '#6a34c0');
    P(-1, hy - 3, 2, 2, '#ffe040'); P(-4, hy - 1, 8, 1, st.accent);
  }
  // 앞팔 + 무기
  const ay = -10 + by;
  if (id === 'leo') {
    if (arm === 'atk') {
      if (atkP < 0.22) { P(0, ay - 5, 2, 5, st.top); P(0, ay - 6, 2, 2, st.skin); P(-1, ay - 15, 2, 9, '#e8f0ff'); P(-2, ay - 7, 4, 1, '#e0a020'); }
      else { P(1, ay + 1, 5, 2, st.top); P(5, ay + 1, 2, 2, st.skin); P(7, ay, 12, 2, '#e8f0ff'); P(7, ay, 12, 1, '#ffffff'); P(6, ay - 1, 1, 4, '#e0a020'); }
    } else {
      drawArm(P, arm, ay, st);
      if (arm === 'raise') { P(1, ay - 18, 2, 10, '#e8f0ff'); P(0, ay - 8, 4, 1, '#e0a020'); }
      else { P(-6, ay - 4, 2, 2, '#e0a020'); P(-6, ay - 2, 1, 6, '#9aa8c0'); }
    }
  } else if (id === 'mina') {
    if (arm === 'atk') { P(-1, ay - 1, 2, 4, st.top); P(-1, ay + 3, 2, 1, st.skin); }
    else drawArm(P, arm, ay, st);
  } else {
    // 지팡이
    if (arm === 'atk') {
      P(1, ay + 1, 4, 2, st.top); P(4, ay + 1, 2, 2, st.skin);
      P(2, ay + 1, 12, 1, '#a8743e'); P(13, ay - 1, 3, 3, '#7af0ff'); P(14, ay, 1, 1, '#ffffff');
    } else {
      drawArm(P, arm === 'raise' ? 'raise' : 'down', ay, st);
      const sy = arm === 'raise' ? -10 : 0;
      P(3, ay - 6 + sy, 1, 16, '#a8743e'); P(2, ay - 9 + sy, 3, 3, '#7af0ff'); P(3, ay - 8 + sy, 1, 1, '#ffffff');
    }
  }
  c.restore();
}
function drawArm(P, arm, ay, st) {
  switch (arm) {
    case 'fwd': P(1, ay, 4, 2, st.top); P(4, ay, 2, 2, st.skin); break;
    case 'back': P(-2, ay, 2, 4, st.top); P(-2, ay + 4, 2, 1, st.skin); break;
    case 'up': P(1, ay - 4, 2, 4, st.top); P(1, ay - 5, 2, 1, st.skin); break;
    case 'out': P(2, ay - 1, 4, 2, st.top); P(5, ay - 2, 2, 2, st.skin); break;
    case 'raise': P(1, ay - 7, 2, 7, st.top); P(1, ay - 8, 2, 2, st.skin); break;
    default: P(1, ay, 2, 4, st.top); P(1, ay + 4, 2, 1, st.skin);
  }
}

// ─── NPC ───
function drawPipi(c, x, y, t, scale = 1) {
  c.save();
  c.translate(Math.round(x), Math.round(y + Math.sin(t * 4) * 2));
  c.scale(scale, scale);
  const wing = Math.sin(t * 20) * 0.5 + 0.5;
  c.fillStyle = 'rgba(220,240,255,0.75)';
  c.beginPath(); c.ellipse(-6, -2, 5, 2 + wing * 2, -0.5, 0, Math.PI * 2); c.fill();
  c.beginPath(); c.ellipse(6, -2, 5, 2 + wing * 2, 0.5, 0, Math.PI * 2); c.fill();
  c.fillStyle = 'rgba(255,240,140,0.3)'; c.beginPath(); c.arc(0, 0, 10, 0, Math.PI * 2); c.fill();
  drawStarShape(c, 0, 0, 7, '#ffe85a', '#e8a020');
  R(c, -2, -1, 1, 2, '#3a2a10'); R(c, 1, -1, 1, 2, '#3a2a10'); R(c, -1, 2, 2, 1, '#e86a5a');
  c.restore();
}
function drawSage(c, x, y, t) {
  c.save(); c.translate(Math.round(x), Math.round(y));
  R(c, -6, -14, 12, 14, '#3a5ab0'); R(c, -6, -14, 12, 1, '#5a7ad0'); R(c, -7, -2, 14, 2, '#2a4090');
  R(c, -4, -21, 8, 7, '#f0c8a0'); R(c, -5, -22, 10, 2, '#e8e8f0'); R(c, -5, -21, 2, 5, '#e8e8f0');
  R(c, -3, -16, 7, 7, '#f4f4fa'); R(c, -2, -10, 5, 3, '#f4f4fa'); R(c, 1, -19, 1, 1, '#222'); R(c, 3, -19, 1, 1, '#222');
  R(c, -2, -20, 3, 1, '#c8c8d8'); R(c, 2, -20, 3, 1, '#c8c8d8');
  R(c, 7, -26, 2, 26, '#8a5a2a'); R(c, 5, -29, 6, 4, '#8a5a2a');
  c.fillStyle = `rgba(120,220,255,${0.5 + Math.sin(t * 3) * 0.3})`; c.fillRect(6, -28, 4, 2);
  c.restore();
}
function drawToto(c, x, y, t) {
  c.save(); c.translate(Math.round(x), Math.round(y));
  const b = Math.sin(t * 3) > 0 ? 0 : 1;
  R(c, -10, -18 + b, 8, 14, '#8a5a2a'); R(c, -10, -18 + b, 8, 2, '#a8743e'); R(c, -9, -12 + b, 6, 1, '#5a3a1a');
  R(c, -6, -16 + b, 2, 3, '#e0a020');
  R(c, -5, -12 + b, 10, 10, '#b88a5a'); R(c, -3, -10 + b, 6, 7, '#f0dcc0');
  R(c, -3, -2, 3, 2, '#5a3a1a'); R(c, 1, -2, 3, 2, '#5a3a1a');
  R(c, -5, -20 + b, 10, 8, '#b88a5a'); R(c, -6, -23 + b, 3, 4, '#b88a5a'); R(c, 3, -23 + b, 3, 4, '#b88a5a');
  R(c, -5, -17 + b, 10, 3, '#4a3a2a'); R(c, -3, -17 + b, 2, 2, '#ffffff'); R(c, 1, -17 + b, 2, 2, '#ffffff');
  R(c, -2, -16 + b, 1, 1, '#000'); R(c, 2, -16 + b, 1, 1, '#000'); R(c, -1, -14 + b, 2, 1, '#2a1a10');
  R(c, -6, -24 + b, 12, 2, '#d84a3a'); R(c, -4, -27 + b, 8, 3, '#d84a3a');
  c.restore();
}
function drawMorvath(c, x, y, t, o = {}) {
  c.save(); c.translate(Math.round(x), Math.round(y));
  const s = o.scale || 1; c.scale(s * (o.dir || 1), s);
  if (o.alpha != null) c.globalAlpha = o.alpha;
  const fl = o.flash;
  const P = (px, py, w, h, col) => R(c, px, py, w, h, fl ? '#ffffff' : col);
  const fl2 = Math.sin(t * 6);
  c.fillStyle = fl ? '#fff' : 'rgba(120,20,160,0.35)';
  c.beginPath(); c.ellipse(0, -18, 16 + fl2 * 2, 22, 0, 0, Math.PI * 2); c.fill();
  // 망토
  P(-11, -28, 22, 26, '#1a0e26');
  for (let i = 0; i < 6; i++) P(-11 + i * 4, -2, 3, 2 + ((i + Math.floor(t * 8)) % 3), '#1a0e26');
  P(-11, -28, 2, 26, '#3a1a4a'); P(9, -28, 2, 26, '#3a1a4a');
  P(-7, -26, 14, 22, '#2a1838'); P(-2, -26, 4, 22, '#4a2060');
  P(-3, -18, 6, 2, '#d8a020');
  // 얼굴
  P(-5, -36, 10, 9, '#2a1a34'); P(-6, -37, 12, 2, '#1a0e26');
  P(-4, -33, 3, 2, '#ff2a4a'); P(1, -33, 3, 2, '#ff2a4a'); P(-3, -33, 1, 1, '#ffd0d8'); P(2, -33, 1, 1, '#ffd0d8');
  // 왕관
  P(-6, -40, 12, 3, '#e8b020'); P(-6, -43, 2, 3, '#e8b020'); P(-1, -44, 2, 4, '#e8b020'); P(4, -43, 2, 3, '#e8b020');
  P(-1, -39, 2, 1, '#ff2a4a');
  // 손
  P(-14, -18 + Math.round(fl2), 3, 3, '#2a1a34'); P(11, -18 - Math.round(fl2), 3, 3, '#2a1a34');
  c.restore();
}

// ─── 적 ───
const ENEMY_SKIN = {
  walker: { forest: 'slime', cave: 'beetle', sea: 'crab', desert: 'scorpion', sky: 'puff', castle: 'skeleton' },
  hopper: { forest: 'frog', cave: 'cslime', sea: 'jelly', desert: 'frog', sky: 'frog', castle: 'imp' },
  flyer: { forest: 'bird', cave: 'bat', sea: 'fish', desert: 'vulture', sky: 'bird', castle: 'bat' },
  turret: { forest: 'plant', cave: 'cannon', sea: 'clam', desert: 'cactus', sky: 'cannon', castle: 'gargoyle' },
  chaser: { forest: 'wisp', cave: 'ghost', sea: 'puffer', desert: 'spark', sky: 'spark', castle: 'ghost' },
  spiky: { forest: 'hedgehog', cave: 'hedgehog', sea: 'urchin', desert: 'hedgehog', sky: 'urchin', castle: 'hedgehog' },
  dropper: { forest: 'cone', cave: 'cone', sea: 'cone', desert: 'cone', sky: 'cone', castle: 'cone' },
};
const PAL = {
  forest: { a: '#4ac85a', b: '#2a8a3a', c: '#a8f0a0' },
  cave: { a: '#5ad8e8', b: '#2a7a98', c: '#c8f8ff' },
  sea: { a: '#ff7a4a', b: '#c84a2a', c: '#ffc0a0' },
  desert: { a: '#d8a858', b: '#9a6a28', c: '#f8d8a0' },
  sky: { a: '#ffd84a', b: '#c89a20', c: '#fff4b0' },
  castle: { a: '#c84a5a', b: '#7a2a3a', c: '#ffa0a8' },
};

function drawEnemy(c, e, theme, t) {
  const skin = ENEMY_SKIN[e.type][theme];
  const pal = PAL[theme];
  const fl = e.flash > 0;
  const P = (px, py, w, h, col) => R(c, px, py, w, h, fl ? '#ffffff' : col);
  const cx = Math.round(e.x + e.w / 2), by = Math.round(e.y + e.h);
  c.save();
  c.translate(cx, by);
  c.scale(e.dir < 0 ? -1 : 1, 1);
  const f2 = Math.floor(t * 8) % 2;
  const eyes = (x1, y1, white = true) => {
    if (white) { P(x1, y1, 2, 3, '#ffffff'); P(x1 + 3, y1, 2, 3, '#ffffff'); }
    P(x1 + 1, y1 + 1, 1, 2, '#1a1a2a'); P(x1 + 4, y1 + 1, 1, 2, '#1a1a2a');
  };
  switch (skin) {
    case 'slime': {
      const sq = f2;
      P(-7, -9 + sq, 14, 9 - sq, '#4ac85a'); P(-5, -11 + sq, 10, 2, '#4ac85a'); P(-7, -1, 14, 1, '#2a8a3a');
      P(-4, -10 + sq, 3, 1, '#a8f0a0'); eyes(0, -8 + sq);
      P(0, -14 + sq, 1, 3, '#2a8a3a'); P(1, -15 + sq, 4, 2, '#6ae070'); break;
    }
    case 'beetle': {
      P(-7, -10, 14, 8, '#5a4a8a'); P(-6, -11, 12, 1, '#5a4a8a'); P(-5, -10, 5, 2, '#8a7ac0'); P(0, -10, 1, 8, '#3a2e5a');
      P(5, -7, 3, 4, '#3a2e5a'); P(7, -9, 2, 3, '#6ef0ff'); P(6, -6, 1, 1, '#ff4a4a');
      for (let i = 0; i < 3; i++) P(-5 + i * 4, -2, 1, 2 + ((i + f2) % 2 ? 0 : -1), '#2a2040'); break;
    }
    case 'crab': {
      P(-6, -8, 12, 6, '#ff6a4a'); P(-5, -9, 10, 1, '#ff6a4a'); P(-4, -8, 4, 1, '#ffb090');
      const cl = f2 ? 0 : 1;
      P(-10, -12 + cl, 3, 4, '#ff6a4a'); P(7, -12 + cl, 3, 4, '#ff6a4a'); P(-10, -12 + cl, 3, 1, '#ffb090'); P(7, -12 + cl, 3, 1, '#ffb090');
      P(-8, -9, 2, 2, '#c84a2a'); P(6, -9, 2, 2, '#c84a2a');
      P(-3, -12, 1, 3, '#c84a2a'); P(2, -12, 1, 3, '#c84a2a'); P(-3, -13, 2, 2, '#fff'); P(2, -13, 2, 2, '#fff'); P(-2, -12, 1, 1, '#000'); P(3, -12, 1, 1, '#000');
      for (let i = 0; i < 3; i++) P(-5 + i * 4 + (f2 ? 1 : 0), -2, 1, 2, '#c84a2a'); break;
    }
    case 'scorpion': {
      P(-6, -6, 12, 4, '#c88a3a'); P(-5, -7, 9, 1, '#e0a858'); P(-8, -8, 3, 3, '#c88a3a'); P(-9, -11, 2, 3, '#c88a3a'); P(-8, -13, 3, 2, '#c88a3a');
      P(-5, -14 + f2, 2, 2, '#ff4a3a'); P(6, -7, 3, 2, '#c88a3a'); P(8, -9, 2, 2, '#c88a3a'); P(8, -5, 2, 2, '#c88a3a');
      P(3, -6, 1, 1, '#000'); for (let i = 0; i < 3; i++) P(-4 + i * 3, -2, 1, 2, '#8a5a20'); break;
    }
    case 'puff': {
      P(-7, -9, 14, 8, '#f8faff'); P(-5, -11, 10, 2, '#f8faff'); P(-8, -6, 16, 4, '#f8faff'); P(-6, -2, 12, 1, '#c8d4f4');
      P(-4, -13, 8, 3, '#ffcc40'); P(-1, -15, 2, 2, '#ff4a4a');
      P(1, -8, 2, 2, '#1a1a2a'); P(4, -8, 2, 2, '#1a1a2a'); P(0, -9, 3, 1, '#1a1a2a');
      P(-2, -1, 2, 1, '#8a8ab0'); P(2, -1, 2, 1, '#8a8ab0'); break;
    }
    case 'skeleton': {
      P(-3, -5, 2, 5 - f2, '#d8d4c8'); P(1, -5, 2, 4 + f2, '#d8d4c8');
      P(-4, -10, 8, 6, '#5a5a7a'); P(-4, -10, 8, 1, '#8a8aaa');
      P(-3, -16, 7, 6, '#e8e4d8'); P(-1, -14, 2, 2, '#1a1a2a'); P(2, -14, 2, 2, '#1a1a2a'); P(-1, -11, 4, 1, '#8a8478');
      P(-4, -17, 9, 2, '#6a6a8a'); P(-4, -18, 2, 1, '#c84a5a');
      P(4, -11, 3, 8, '#8a2a3a'); P(5, -9, 1, 4, '#e8b020');
      P(-6, -14, 1, 12, '#c8c8d8'); P(-7, -15, 3, 1, '#c8c8d8'); break;
    }
    case 'frog': {
      const up = e.vy < -10 ? -2 : 0;
      P(-6, -7 + up, 12, 6, pal.a); P(-5, -8 + up, 10, 1, pal.a); P(-6, -2 + up, 12, 1, pal.b);
      P(-6, -10 + up, 4, 3, pal.a); P(2, -10 + up, 4, 3, pal.a); P(-5, -10 + up, 2, 2, '#fff'); P(3, -10 + up, 2, 2, '#fff'); P(-4, -9 + up, 1, 1, '#000'); P(4, -9 + up, 1, 1, '#000');
      P(-4, -4 + up, 8, 1, pal.b); P(-3, -5 + up, 6, 1, pal.c);
      if (up) { P(-7, -1, 3, 1, pal.b); P(4, -1, 3, 1, pal.b); } else { P(-7, -1, 4, 1, pal.b); P(3, -1, 4, 1, pal.b); }
      break;
    }
    case 'cslime': case 'jelly': {
      const pulse = e.vy < -10 ? 1 : 0;
      const a = skin === 'jelly' ? '#ff8ad8' : '#5ad8e8', b = skin === 'jelly' ? '#c84aa8' : '#2a7a98';
      P(-6, -11 + pulse, 12, 7 - pulse, a); P(-4, -12 + pulse, 8, 1, a); P(-3, -11 + pulse, 3, 2, '#ffffff');
      P(-1, -8, 1, 2, '#1a1a2a'); P(2, -8, 1, 2, '#1a1a2a');
      if (skin === 'jelly') for (let i = 0; i < 4; i++) P(-5 + i * 3, -4, 1, 3 + ((i + f2) % 2) * 2, b);
      else P(-6, -4, 12, 3, b);
      break;
    }
    case 'imp': {
      const w = f2 ? -1 : 1;
      P(-9, -11 + w, 4, 3, '#4a1a2a'); P(5, -11 + w, 4, 3, '#4a1a2a');
      P(-4, -10, 8, 8, '#c83a4a'); P(-3, -12, 2, 2, '#c83a4a'); P(1, -12, 2, 2, '#c83a4a');
      P(-2, -8, 1, 2, '#ffe040'); P(1, -8, 1, 2, '#ffe040'); P(-2, -5, 4, 1, '#4a1a2a');
      P(-3, -2, 2, 2, '#4a1a2a'); P(1, -2, 2, 2, '#4a1a2a'); P(-6, -4, 2, 1, '#4a1a2a'); break;
    }
    case 'bird': case 'vulture': {
      const body = skin === 'vulture' ? '#5a3a2a' : (theme === 'sky' ? '#f8f0e0' : '#4a8ae0');
      const wing = skin === 'vulture' ? '#3a2418' : (theme === 'sky' ? '#e8c040' : '#2a5ab0');
      P(-6, -7, 11, 6, body); P(5, -6, 3, 2, '#ffb020'); P(2, -6, 2, 2, '#ffffff'); P(3, -5, 1, 1, '#000');
      if (skin === 'vulture') { P(3, -9, 4, 4, '#e88a8a'); P(5, -8, 1, 1, '#000'); }
      P(-8, -5, 2, 3, wing);
      if (f2) P(-4, -12, 6, 5, wing); else P(-4, -2, 6, 4, wing);
      break;
    }
    case 'bat': {
      const body = theme === 'castle' ? '#7a1a2a' : '#5a3a8a', wing = theme === 'castle' ? '#4a0e1a' : '#3a2268';
      P(-3, -8, 6, 6, body); P(-3, -10, 1, 2, body); P(2, -10, 1, 2, body);
      P(-2, -7, 1, 1, '#ffe040'); P(1, -7, 1, 1, '#ffe040');
      if (f2) { P(-9, -10, 6, 3, wing); P(3, -10, 6, 3, wing); P(-10, -8, 2, 2, wing); P(8, -8, 2, 2, wing); }
      else { P(-9, -6, 6, 3, wing); P(3, -6, 6, 3, wing); P(-9, -3, 2, 2, wing); P(7, -3, 2, 2, wing); }
      break;
    }
    case 'fish': {
      P(-6, -8, 11, 6, '#ffa040'); P(-4, -9, 7, 1, '#ffa040'); P(-4, -8, 2, 6, '#ffffff'); P(0, -8, 2, 6, '#ffffff');
      P(3, -7, 2, 2, '#fff'); P(4, -6, 1, 1, '#000'); P(5, -5, 1, 1, '#c84a2a');
      P(-9, -10 + f2, 3, 4, '#ff7a20'); P(-9, -4 - f2, 3, 3, '#ff7a20'); P(-2, -10, 3, 2, '#ff7a20'); break;
    }
    case 'plant': case 'cactus': {
      const stem = skin === 'cactus' ? '#4a8a3a' : '#2a8a3a';
      P(-2, -8, 4, 8, stem); P(-6, -5, 4, 2, stem); P(2, -6, 4, 2, stem);
      const open = e.state === 'fire' ? 2 : 0;
      if (skin === 'cactus') {
        P(-4, -16, 8, 9, '#5a9a4a'); P(-3, -17, 6, 1, '#5a9a4a'); P(-2, -15, 1, 6, '#7aba64');
        P(-5, -14, 1, 1, '#f0f0d0'); P(4, -12, 1, 1, '#f0f0d0'); P(-5, -10, 1, 1, '#f0f0d0'); P(1, -18, 2, 2, '#ff6aa0');
        P(1, -13, 1, 1, '#000'); P(3, -13, 1, 1, '#000'); P(1, -10, 3, 1 + open / 2, '#2a4a20');
      } else {
        P(-6, -16, 12, 9, '#d83a4a'); P(-5, -17, 10, 1, '#d83a4a');
        for (let i = 0; i < 4; i++) P(-5 + i * 3, -15, 1, 1, '#ffffff');
        P(2, -13 - open, 5, 3 + open * 2, '#5a1a1a'); P(3, -12 - open, 1, 1, '#fff'); P(5, -12 - open, 1, 1, '#fff');
      }
      break;
    }
    case 'cannon': case 'gargoyle': {
      const body = skin === 'gargoyle' ? '#6a6478' : (theme === 'cave' ? '#4a3e78' : '#8aa0c8');
      const dark = skin === 'gargoyle' ? '#3a3448' : (theme === 'cave' ? '#2a2248' : '#5a6a98');
      P(-7, -6, 14, 6, dark); P(-6, -14, 12, 9, body); P(-6, -14, 12, 1, '#ffffff');
      if (skin === 'gargoyle') {
        P(-8, -16, 3, 4, body); P(5, -16, 3, 4, body); P(1, -11, 2, 2, '#ff3a3a'); P(4, -11, 2, 2, '#ff3a3a');
        P(2, -8, 6, 2, dark); P(4, -8, 1, 1, '#fff');
      } else {
        P(3, -12, 7, 5, dark); P(9, -12, 1, 5, '#2a2a3a');
        P(-2, -11, 3, 3, theme === 'cave' ? '#6ef0ff' : '#ffffff');
      }
      break;
    }
    case 'clam': {
      const open = e.state === 'fire' ? 4 : 1;
      P(-8, -5, 16, 5, '#b880d8'); P(-8, -5, 16, 1, '#e0b8ff');
      P(-7, -5 - open - 4, 14, 5, '#a070c8'); P(-6, -5 - open - 4, 12, 1, '#e0b8ff');
      if (open > 1) { P(-5, -5 - open, 10, open, '#3a1a4a'); P(-2, -4 - open, 4, 3, '#ffffff'); }
      break;
    }
    case 'wisp': case 'ghost': {
      const a = skin === 'wisp' ? '#c8ffd8' : (theme === 'castle' ? '#d8c8ff' : '#e0f0ff');
      const b = skin === 'wisp' ? '#6ae0a0' : (theme === 'castle' ? '#8a6ad8' : '#8ab0d8');
      c.globalAlpha = 0.85;
      P(-6, -12, 12, 9, a); P(-4, -14, 8, 2, a);
      for (let i = 0; i < 4; i++) P(-6 + i * 3, -3, 2, 2 + ((i + f2) % 2), b);
      P(-3, -10, 2, 3, '#2a2a4a'); P(2, -10, 2, 3, '#2a2a4a'); P(-1, -6, 3, 1, '#2a2a4a');
      c.globalAlpha = 1; break;
    }
    case 'puffer': {
      const r = e.state === 'puff' ? 7 : 5;
      c.fillStyle = fl ? '#fff' : '#ffd84a'; c.beginPath(); c.arc(0, -7, r, 0, Math.PI * 2); c.fill();
      for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; P(Math.round(Math.cos(a) * (r + 1)), Math.round(-7 + Math.sin(a) * (r + 1)), 1, 1, '#c89a20'); }
      P(1, -9, 2, 2, '#fff'); P(2, -8, 1, 1, '#000'); P(-r - 3, -9 + f2, 3, 4, '#ffb020'); break;
    }
    case 'spark': {
      const col = theme === 'desert' ? '#e8c890' : '#fff27a';
      c.globalAlpha = 0.9;
      for (let i = 0; i < 6; i++) {
        const a = t * 8 + i * Math.PI / 3;
        P(Math.round(Math.cos(a) * 6), Math.round(-7 + Math.sin(a) * 6), 2, 2, col);
      }
      P(-4, -11, 8, 8, theme === 'desert' ? '#c8a060' : '#ffe040'); P(-2, -9, 4, 4, '#ffffff');
      P(-2, -8, 1, 1, '#000'); P(1, -8, 1, 1, '#000'); c.globalAlpha = 1; break;
    }
    case 'hedgehog': case 'urchin': {
      const body = skin === 'urchin' ? '#4a2a5a' : pal.b;
      const spike = skin === 'urchin' ? '#2a1a3a' : '#e8e8f0';
      for (let i = 0; i < 7; i++) {
        const a = Math.PI + i * Math.PI / 6;
        const sx = Math.round(Math.cos(a) * 8), sy = Math.round(-5 + Math.sin(a) * 8);
        P(sx - 1, sy - 1, 2, 2, spike);
      }
      P(-6, -10, 12, 9, body); P(-4, -11, 8, 1, body);
      if (skin !== 'urchin') { P(3, -6, 4, 4, '#f0d0b0'); P(6, -5, 1, 1, '#000'); P(4, -7, 1, 1, '#000'); }
      else { P(-2, -7, 1, 1, '#ff6a6a'); P(2, -7, 1, 1, '#ff6a6a'); }
      P(-4, -1, 2, 1 + f2, '#2a1a10'); P(2, -1, 2, 2 - f2, '#2a1a10'); break;
    }
    case 'cone': {
      const col = { forest: '#7a5a3a', cave: '#5a5070', sea: '#5a6a7a', desert: '#a87a4a', sky: '#c8f0ff', castle: '#8a8aa0' }[theme];
      const dk = { forest: '#5a3a1a', cave: '#3a3450', sea: '#3a4a5a', desert: '#7a5a2a', sky: '#88c8e8', castle: '#5a5a70' }[theme];
      const shake = e.state === 'shake' ? (f2 ? 1 : -1) : 0;
      for (let i = 0; i < 7; i++) P(-5 + Math.floor(i * 0.7) + shake, -14 + i * 2, 10 - Math.floor(i * 1.4), 2, i % 2 ? dk : col);
      P(-1 + shake, -1, 2, 1, dk); break;
    }
  }
  c.restore();
}

// ─── 아이템 ───
function drawItem(c, kind, x, y, t, noLabel) {
  c.save();
  c.translate(Math.round(x), Math.round(y));
  switch (kind) {
    case 'coin': {
      const w = Math.round(Math.abs(Math.cos(t * 5)) * 4) + 1;
      R(c, -w, -5, w * 2, 10, '#ffd23a'); R(c, -w, -5, w * 2, 1, '#fff2a0'); R(c, -w, 4, w * 2, 1, '#c88a10');
      if (w > 2) R(c, -1, -3, 2, 6, '#e0a820');
      break;
    }
    case 'bag': {
      R(c, -5, -3, 10, 8, '#c8883a'); R(c, -4, -5, 8, 2, '#c8883a'); R(c, -2, -7, 4, 2, '#8a5a1a');
      R(c, -4, -4, 3, 2, '#e8b060'); R(c, -1, -1, 3, 4, '#ffd23a'); R(c, -1, 0, 3, 1, '#c88a10'); break;
    }
    case 'heart': {
      const s = 1 + Math.sin(t * 6) * 0.08;
      c.scale(s, s);
      R(c, -5, -4, 4, 3, '#ff3a5a'); R(c, 1, -4, 4, 3, '#ff3a5a'); R(c, -6, -3, 12, 3, '#ff3a5a');
      R(c, -5, 0, 10, 2, '#ff3a5a'); R(c, -3, 2, 6, 2, '#ff3a5a'); R(c, -1, 4, 2, 1, '#ff3a5a'); R(c, -4, -3, 2, 1, '#ffc0c8'); break;
    }
    case 'power': {
      c.fillStyle = 'rgba(255,90,60,0.3)'; c.beginPath(); c.arc(0, 0, 8 + Math.sin(t * 8), 0, Math.PI * 2); c.fill();
      R(c, -5, -5, 10, 10, '#ff5a3a'); R(c, -4, -6, 8, 12, '#ff5a3a'); R(c, -6, -4, 12, 8, '#ff5a3a');
      R(c, -1, -4, 2, 8, '#fff2a0'); R(c, -3, -2, 6, 2, '#fff2a0'); R(c, -4, -5, 2, 2, '#ffb0a0'); break;
    }
    case 'shield': {
      c.fillStyle = 'rgba(90,180,255,0.3)'; c.beginPath(); c.arc(0, 0, 8 + Math.sin(t * 8), 0, Math.PI * 2); c.fill();
      R(c, -5, -6, 10, 7, '#4aa8ff'); R(c, -4, 1, 8, 2, '#4aa8ff'); R(c, -2, 3, 4, 2, '#4aa8ff');
      R(c, -5, -6, 10, 1, '#c8e8ff'); R(c, -1, -5, 2, 8, '#ffffff'); break;
    }
    case 'star': {
      const hue = Math.floor(t * 10) % 3;
      drawStarShape(c, 0, 0, 7, ['#ffe85a', '#ffffff', '#ffb0e0'][hue], '#e8a020');
      break;
    }
    case 'life': {
      R(c, -4, -2, 8, 7, '#3ad870'); R(c, -2, -6, 4, 4, '#3ad870'); R(c, -3, -7, 6, 1, '#8a5a2a');
      R(c, -3, -1, 2, 4, '#c8ffd8'); R(c, -4, 5, 8, 1, '#1e8a48');
      if (!noLabel) { c.font = 'bold 6px monospace'; c.fillStyle = '#ffffff'; c.textAlign = 'center'; c.fillText('1UP', 0, -9); }
      break;
    }
    case 'shard': {
      const g = 0.4 + Math.sin(t * 5) * 0.2;
      c.fillStyle = `rgba(255,240,160,${g})`; c.beginPath(); c.arc(0, 0, 14, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#bff4ff';
      c.beginPath(); c.moveTo(0, -11); c.lineTo(7, -2); c.lineTo(3, 10); c.lineTo(-3, 10); c.lineTo(-7, -2); c.closePath(); c.fill();
      c.fillStyle = '#ffffff'; c.beginPath(); c.moveTo(0, -11); c.lineTo(3, -2); c.lineTo(0, 8); c.lineTo(-3, -2); c.closePath(); c.fill();
      c.fillStyle = '#ffe85a'; c.fillRect(-1, -3, 2, 2);
      break;
    }
  }
  c.restore();
}

function drawFlag(c, x, y, active, t) {
  R(c, x - 1, y - 30, 2, 30, '#d8d8e8'); R(c, x - 2, y - 32, 4, 3, '#ffd23a');
  const wave = Math.round(Math.sin(t * 6));
  if (active) { R(c, x + 1, y - 29, 12, 4, '#3ad870'); R(c, x + 1, y - 25 + wave, 10, 4, '#3ad870'); drawStarShape(c, x + 7, y - 26, 3, '#ffffff'); }
  else { R(c, x + 1, y - 12, 9, 3, '#8a8a9a'); R(c, x + 1, y - 9, 7, 3, '#8a8a9a'); }
  R(c, x - 3, y - 2, 6, 2, '#6a6a7a');
}
function drawSign(c, x, y) {
  R(c, x - 1, y - 10, 2, 10, '#6a4420');
  R(c, x - 7, y - 18, 14, 9, '#c8945a'); R(c, x - 7, y - 18, 14, 1, '#e8b47a'); R(c, x - 7, y - 10, 14, 1, '#8a5a2a');
  R(c, x - 4, y - 15, 8, 1, '#6a4420'); R(c, x - 4, y - 13, 6, 1, '#6a4420');
}
