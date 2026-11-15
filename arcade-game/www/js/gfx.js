'use strict';
// ─────────────────────────────────────────────────────────────
//  gfx.js — 화면 관리, 글자 출력, 스테이지 테마(색상), 타일·배경 그리기
// ─────────────────────────────────────────────────────────────

const FONT = '"Noto Sans KR","Apple SD Gothic Neo","Malgun Gothic","Roboto",sans-serif';

const G = {
  screen: null, sctx: null, buf: null, bctx: null,
  W: 0, H: 0, VW: 400, S: 1, dpr: 1,
  init() {
    this.screen = document.getElementById('game');
    this.sctx = this.screen.getContext('2d');
    this.buf = document.createElement('canvas');
    this.bctx = this.buf.getContext('2d');
    this.resize();
    window.addEventListener('resize', () => this.resize());
    window.addEventListener('orientationchange', () => setTimeout(() => this.resize(), 200));
  },
  resize() {
    this.dpr = Math.min(window.devicePixelRatio || 1, 3);
    const cw = window.innerWidth, ch = window.innerHeight;
    this.W = Math.max(1, Math.floor(cw * this.dpr));
    this.H = Math.max(1, Math.floor(ch * this.dpr));
    this.screen.width = this.W; this.screen.height = this.H;
    this.screen.style.width = cw + 'px'; this.screen.style.height = ch + 'px';
    this.portrait = ch > cw;
    // 가로 해상도는 화면 비율에 맞춰 늘어남 (16:9 ~ 21:9 대응)
    this.VW = U.clamp(Math.round(VH * this.W / this.H), 300, 560);
    this.buf.width = this.VW; this.buf.height = VH;
    this.S = this.H / VH;
    this.bctx.imageSmoothingEnabled = false;
    if (typeof Input !== 'undefined') Input.layout();
  },
  present() {
    const c = this.sctx;
    c.imageSmoothingEnabled = false;
    c.drawImage(this.buf, 0, 0, this.VW, VH, 0, 0, this.W, this.H);
  },
  font(size, weight = 800) { return `${weight} ${Math.max(1, Math.round(size))}px ${FONT}`; },
  // 화면(고해상도) 좌표에 글자 출력. size는 게임 픽셀 단위 → S배 확대
  text(str, x, y, size, color = '#fff', align = 'left', opt = {}) {
    const c = opt.ctx || this.sctx;
    const px = size * this.S;
    c.save();
    c.font = this.font(px, opt.weight || 800);
    c.textAlign = align;
    c.textBaseline = opt.baseline || 'middle';
    if (opt.alpha != null) c.globalAlpha = opt.alpha;
    if (opt.outline !== false) {
      c.lineJoin = 'round';
      c.strokeStyle = opt.outline || 'rgba(10,8,30,0.9)';
      c.lineWidth = px * (opt.ow || 0.22);
      c.strokeText(str, x, y);
    }
    c.fillStyle = color;
    c.fillText(str, x, y);
    c.restore();
  },
  measure(str, size, weight = 800) {
    this.sctx.font = this.font(size * this.S, weight);
    return this.sctx.measureText(str).width;
  },
  // 한글 줄바꿈: 단어 단위, 너무 긴 단어는 글자 단위
  wrap(str, maxW, size) {
    const out = [];
    for (const para of String(str).split('\n')) {
      let line = '';
      for (const word of para.split(' ')) {
        const test = line ? line + ' ' + word : word;
        if (this.measure(test, size) <= maxW) { line = test; continue; }
        if (line) out.push(line);
        if (this.measure(word, size) <= maxW) { line = word; continue; }
        line = '';
        for (const ch of word) {
          if (this.measure(line + ch, size) > maxW) { out.push(line); line = ch; } else line += ch;
        }
      }
      out.push(line);
    }
    return out;
  },
  roundRect(c, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  },
  panel(x, y, w, h, opt = {}) {
    const c = this.sctx, S = this.S;
    c.save();
    c.globalAlpha = opt.alpha != null ? opt.alpha : 1;
    this.roundRect(c, x, y, w, h, (opt.r || 6) * S);
    c.fillStyle = opt.fill || 'rgba(16,14,44,0.88)';
    c.fill();
    c.lineWidth = (opt.lw || 1.5) * S;
    c.strokeStyle = opt.stroke || '#ffd86a';
    c.stroke();
    c.restore();
  },
};

// 사각형 채우기 (게임 픽셀 버퍼용)
function R(c, x, y, w, h, col) { c.fillStyle = col; c.fillRect(x, y, w, h); }

// ─── 타일 코드 ───
const T = { EMPTY: 0, SOLID: 1, BREAK: 2, ITEM: 3, HIDDEN: 4, ONEWAY: 5, SPIKE: 6, SPIKEC: 7, LAVA: 8, LAVAB: 9, QUICK: 10, QUICKB: 11, GATE: 12 };
const SOLID_TILES = new Set([T.SOLID, T.BREAK, T.ITEM, T.HIDDEN, T.SPIKE, T.SPIKEC, T.GATE]);

// ─── 스테이지 테마 팔레트 ───
const THEMES = {
  forest: {
    sky: ['#5cb4ee', '#bfe8ff'], dirt: '#8a5a32', dirtD: '#6e4424', dirtL: '#a06a3c', top: '#58c840', topL: '#8ae860', topD: '#3a9a30',
    brick: '#d0883a', brickL: '#f0b060', brickD: '#8a4a18', plat: '#a8743e', platD: '#6a4420', spike: '#c8ccd8', ambient: 'leaf',
  },
  cave: {
    sky: ['#120e24', '#2a2048'], dirt: '#4c4466', dirtD: '#3a3352', dirtL: '#5e5680', top: '#7a6ac0', topL: '#a898e8', topD: '#5a4a98',
    brick: '#6a5aa8', brickL: '#9a8ad8', brickD: '#3a2e6a', plat: '#58d8e8', platD: '#2a8aa8', spike: '#a8f0ff', ambient: 'dust',
  },
  sea: {
    sky: ['#0a3a6e', '#1f86c4'], dirt: '#c8ae6a', dirtD: '#a88e50', dirtL: '#dcc488', top: '#ecd89a', topL: '#fff0c0', topD: '#c0a464',
    brick: '#e07a8e', brickL: '#ffa8b8', brickD: '#9a3a52', plat: '#ff7aa0', platD: '#b8406a', spike: '#b46ad8', ambient: 'bubble', water: true,
  },
  desert: {
    sky: ['#ff9a50', '#ffe2a0'], dirt: '#d08a50', dirtD: '#b06e38', dirtL: '#e0a468', top: '#f2c47a', topL: '#ffe0a8', topD: '#d8a058',
    brick: '#c8a060', brickL: '#ecc888', brickD: '#8a6430', plat: '#b89a70', platD: '#7a6040', spike: '#e8e0d0', ambient: 'sand',
  },
  sky: {
    sky: ['#3a86f0', '#cfeaff'], dirt: '#eef2ff', dirtD: '#c6d2f2', dirtL: '#ffffff', top: '#ffffff', topL: '#ffffff', topD: '#d8e2fa',
    brick: '#a898d8', brickL: '#d0c4f4', brickD: '#6a5aa0', plat: '#ffffff', platD: '#b8c8ee', spike: '#f0f4ff', ambient: 'wind',
  },
  castle: {
    sky: ['#0c0614', '#3a0c26'], dirt: '#3c3650', dirtD: '#2a2538', dirtL: '#4e4766', top: '#665e84', topL: '#8a82a8', topD: '#4a4262',
    brick: '#7a4a5a', brickL: '#a8707e', brickD: '#4a2434', plat: '#5a5470', platD: '#2e2a3e', spike: '#d8d0e8', ambient: 'ember',
  },
};

// ─── 타일 그리기 (레벨 시작 시 큰 캔버스에 한 번만 그림) ───
function drawTile(c, code, col, row, lv) {
  const th = lv.theme, x = col * TILE, y = row * TILE, name = lv.themeName;
  const h = (a, b) => U.hash(col * 7 + a, row * 13 + b, lv.seed);
  const solidAt = (cc, rr) => SOLID_TILES.has(lv.tileAt(cc, rr)) && lv.tileAt(cc, rr) !== T.SPIKE && lv.tileAt(cc, rr) !== T.SPIKEC;
  switch (code) {
    case T.SOLID: {
      const top = !solidAt(col, row - 1) && row > 0;
      const bot = !solidAt(col, row + 1) && row < ROWS - 1;
      const left = !solidAt(col - 1, row), right = !solidAt(col + 1, row);
      if (name === 'castle') {
        R(c, x, y, 16, 16, th.dirt);
        const off = row % 2 ? 4 : 12;
        R(c, x, y + 7, 16, 1, th.dirtD); R(c, x, y + 15, 16, 1, th.dirtD);
        R(c, x + off - 4, y, 1, 7, th.dirtD); R(c, x + ((off + 8) % 16), y + 8, 1, 7, th.dirtD);
        R(c, x, y, 16, 1, th.dirtL); R(c, x, y + 8, 16, 1, th.dirtL);
        if (h(1, 1) < 0.3) R(c, x + 3 + Math.floor(h(2, 2) * 9), y + 2 + Math.floor(h(3, 3) * 10), 2, 1, th.dirtD);
      } else if (name === 'sky') {
        R(c, x, y, 16, 16, th.dirt);
        for (let i = 0; i < 3; i++) R(c, x + Math.floor(h(i, 5) * 14), y + Math.floor(h(i, 6) * 14), 2, 2, th.dirtD);
      } else if (name === 'desert') {
        R(c, x, y, 16, 16, th.dirt);
        const off = row % 2 ? 0 : 8;
        R(c, x, y + 15, 16, 1, th.dirtD); R(c, x + off, y, 1, 16, th.dirtD);
        for (let i = 0; i < 4; i++) R(c, x + Math.floor(h(i, 9) * 15), y + Math.floor(h(i, 8) * 15), 1, 1, h(i, 7) < 0.5 ? th.dirtL : th.dirtD);
      } else {
        R(c, x, y, 16, 16, th.dirt);
        for (let i = 0; i < 6; i++) {
          const v = h(i, 3);
          R(c, x + Math.floor(h(i, 1) * 15), y + Math.floor(h(i, 2) * 15), v < 0.5 ? 2 : 1, 1, v < 0.6 ? th.dirtD : th.dirtL);
        }
        if (name === 'cave' && h(9, 9) < 0.08) { R(c, x + 6, y + 6, 3, 4, '#6ef0ff'); R(c, x + 7, y + 5, 1, 1, '#d8ffff'); }
      }
      if (left) R(c, x, y, 1, 16, th.dirtD);
      if (right) R(c, x + 15, y, 1, 16, th.dirtD);
      if (bot) {
        R(c, x, y + 15, 16, 1, th.dirtD);
        if (name === 'sky') { R(c, x + 2, y + 15, 12, 1, th.dirtD); }
        if (name === 'cave' && h(4, 4) < 0.5) { const sx = x + 3 + Math.floor(h(5, 5) * 9); R(c, sx, y + 16, 3, 2, th.dirtD); R(c, sx + 1, y + 18, 1, 2, th.dirtD); }
      }
      if (top) drawSurface(c, x, y, th, name, h, left, right);
      break;
    }
    case T.BREAK: case T.HIDDEN: {
      R(c, x, y, 16, 16, th.brick);
      R(c, x, y, 16, 1, th.brickL); R(c, x, y, 1, 16, th.brickL);
      R(c, x, y + 15, 16, 1, th.brickD); R(c, x + 15, y, 1, 16, th.brickD);
      R(c, x + 1, y + 7, 14, 1, th.brickD); R(c, x + 1, y + 8, 14, 1, th.brickL);
      R(c, x + 7, y + 1, 1, 6, th.brickD); R(c, x + 8, y + 1, 1, 6, th.brickL);
      R(c, x + 3, y + 9, 1, 6, th.brickD); R(c, x + 11, y + 9, 1, 6, th.brickD);
      break;
    }
    case T.ITEM: {
      R(c, x, y, 16, 16, '#f0b020');
      R(c, x, y, 16, 1, '#ffe080'); R(c, x, y, 1, 16, '#ffe080');
      R(c, x, y + 15, 16, 1, '#a86010'); R(c, x + 15, y, 1, 16, '#a86010');
      R(c, x + 2, y + 2, 1, 1, '#a86010'); R(c, x + 13, y + 2, 1, 1, '#a86010'); R(c, x + 2, y + 13, 1, 1, '#a86010'); R(c, x + 13, y + 13, 1, 1, '#a86010');
      drawStarShape(c, x + 8, y + 8, 5, '#fff6c8', '#c87810');
      break;
    }
    case T.ONEWAY: {
      if (name === 'sky') {
        R(c, x, y + 2, 16, 5, th.plat); R(c, x, y + 7, 16, 1, th.platD);
        R(c, x + 2, y, 5, 2, th.plat); R(c, x + 9, y + 1, 5, 1, th.plat);
      } else if (name === 'cave') {
        R(c, x, y, 16, 4, th.plat); R(c, x, y + 4, 16, 1, th.platD);
        R(c, x + 2, y + 5, 2, 2, th.platD); R(c, x + 9, y + 5, 3, 3, th.platD); R(c, x + 3, y, 3, 1, '#d8ffff');
      } else if (name === 'castle') {
        R(c, x, y, 16, 4, th.plat); R(c, x, y + 4, 16, 1, th.platD);
        for (let i = 1; i < 16; i += 4) R(c, x + i, y + 1, 2, 2, th.platD);
      } else if (name === 'sea') {
        R(c, x, y, 16, 4, th.plat); R(c, x, y + 4, 16, 1, th.platD);
        R(c, x + 3, y + 5, 2, 3, th.platD); R(c, x + 10, y + 5, 2, 2, th.platD); R(c, x + 1, y, 4, 1, '#ffc8d8');
      } else {
        R(c, x, y, 16, 5, th.plat); R(c, x, y, 16, 1, th.brickL || '#e0b070'); R(c, x, y + 5, 16, 1, th.platD);
        R(c, x + 2, y + 2, 1, 1, th.platD); R(c, x + 13, y + 2, 1, 1, th.platD);
      }
      break;
    }
    case T.SPIKE: case T.SPIKEC: {
      const up = code === T.SPIKE;
      if (up) R(c, x, y + 12, 16, 4, th.dirtD); else R(c, x, y, 16, 4, th.dirtD);
      for (let k = 0; k < 2; k++) {
        const bx = x + k * 8;
        for (let i = 0; i < 4; i++) {
          const yy = up ? y + 12 - (i + 1) * 3 : y + 4 + i * 3;
          R(c, bx + i, yy, 8 - i * 2, 3, i === 3 ? '#ffffff' : th.spike);
          R(c, bx + i, yy, 1, 3, '#8a8ea0');
        }
      }
      break;
    }
    case T.GATE: {
      R(c, x, y, 16, 16, '#2a2234');
      for (let i = 1; i < 16; i += 5) { R(c, x + i, y, 3, 16, '#6a6080'); R(c, x + i, y, 1, 16, '#9a90b0'); }
      R(c, x, y + 6, 16, 2, '#4a405a');
      break;
    }
    case T.QUICK: case T.QUICKB: {
      R(c, x, y, 16, 16, code === T.QUICK ? '#c89050' : '#b07c40');
      for (let i = 0; i < 5; i++) R(c, x + Math.floor(h(i, 11) * 14), y + 3 + Math.floor(h(i, 12) * 12), 2, 1, '#9a6a34');
      if (code === T.QUICK) R(c, x, y, 16, 2, '#e0aa66');
      break;
    }
  }
}

function drawSurface(c, x, y, th, name, h, left, right) {
  if (name === 'forest') {
    R(c, x, y, 16, 4, th.top); R(c, x, y, 16, 1, th.topL);
    for (let i = 0; i < 16; i += 2) { const d = Math.floor(h(i, 21) * 3); if (d) R(c, x + i, y + 4, 2, d, th.topD); }
    if (h(1, 22) < 0.25) { R(c, x + 4 + Math.floor(h(2, 22) * 8), y - 2, 1, 2, th.topD); R(c, x + 6 + Math.floor(h(3, 22) * 6), y - 3, 1, 3, th.top); }
    if (h(4, 22) < 0.12) { const fx = x + 3 + Math.floor(h(5, 22) * 10); R(c, fx, y - 3, 3, 3, h(6, 22) < 0.5 ? '#ff7aa8' : '#fff27a'); R(c, fx + 1, y - 2, 1, 1, '#fff'); }
  } else if (name === 'cave') {
    R(c, x, y, 16, 3, th.top); R(c, x, y, 16, 1, th.topL);
    if (h(1, 31) < 0.18) { const cx = x + 3 + Math.floor(h(2, 31) * 9); R(c, cx, y - 4, 2, 4, '#6ef0ff'); R(c, cx + 2, y - 2, 2, 2, '#ff8ae0'); R(c, cx, y - 4, 1, 1, '#ffffff'); }
  } else if (name === 'sea') {
    R(c, x, y, 16, 3, th.top); R(c, x, y, 16, 1, th.topL);
    if (h(1, 41) < 0.15) { const sx = x + 4 + Math.floor(h(2, 41) * 8); R(c, sx, y - 2, 3, 2, '#ff9a7a'); R(c, sx + 1, y - 3, 1, 1, '#ffc8a8'); }
  } else if (name === 'desert') {
    R(c, x, y, 16, 4, th.top); R(c, x, y, 16, 1, th.topL);
    R(c, x + Math.floor(h(1, 51) * 10), y + 2, 5, 1, th.topD);
  } else if (name === 'sky') {
    R(c, x, y, 16, 3, th.topL);
    const r1 = 2 + Math.floor(h(1, 61) * 3);
    R(c, x + 2, y - r1 + 1, 6, r1, '#ffffff'); R(c, x + 8, y - 1, 6, 1, '#ffffff');
    if (left) R(c, x, y, 2, 2, 'rgba(0,0,0,0)');
  } else if (name === 'castle') {
    R(c, x, y, 16, 3, th.top); R(c, x, y, 16, 1, th.topL); R(c, x, y + 3, 16, 1, th.topD);
  }
}

function drawStarShape(c, cx, cy, r, fill, edge) {
  c.save();
  c.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 5;
    const rr = i % 2 ? r * 0.45 : r;
    c.lineTo(Math.round(cx + Math.cos(a) * rr), Math.round(cy + Math.sin(a) * rr));
  }
  c.closePath();
  if (edge) { c.strokeStyle = edge; c.lineWidth = 1; c.stroke(); }
  c.fillStyle = fill; c.fill();
  c.restore();
}

// ─── 배경 (패럴랙스) ───
// 가로 512px 단위로 반복되는 실루엣을 미리 만들어 둔다.
const BGW = 512;
function wrapNoise(rnd, amps) {
  const comps = amps.map(([k, a]) => ({ k, a, p: rnd() * Math.PI * 2 }));
  return (x) => comps.reduce((s, cp) => s + cp.a * Math.sin((x / BGW) * Math.PI * 2 * cp.k + cp.p), 0);
}
function bgCanvas() { const cv = document.createElement('canvas'); cv.width = BGW; cv.height = VH; return cv; }

const Backgrounds = {
  cache: {},
  get(name) {
    if (!this.cache[name]) this.cache[name] = this.build(name);
    return this.cache[name];
  },
  build(name) {
    const rnd = U.rng(name.length * 977 + name.charCodeAt(0) * 31);
    const layers = [];
    const silhouette = (color, base, amps, factor, extra) => {
      const cv = bgCanvas(), c = cv.getContext('2d');
      const f = wrapNoise(rnd, amps);
      for (let x = 0; x < BGW; x++) {
        const top = Math.round(base + f(x));
        R(c, x, top, 1, VH - top, color);
      }
      if (extra) extra(c, f);
      layers.push({ cv, factor });
    };
    switch (name) {
      case 'forest':
        silhouette('#9cc8dc', 120, [[2, 14], [5, 7], [11, 3]], 0.12);
        silhouette('#6eb48a', 148, [[3, 10], [7, 5]], 0.3, (c, f) => {
          for (let i = 0; i < 26; i++) {
            const tx = Math.floor(rnd() * BGW), ty = 148 + f(tx) - 6, r = 6 + Math.floor(rnd() * 8);
            c.fillStyle = '#5aa078';
            for (const dx of [0, BGW, -BGW]) { c.beginPath(); c.arc(tx + dx, ty, r, 0, Math.PI * 2); c.fill(); }
          }
        });
        silhouette('#3e8a5c', 176, [[4, 6], [9, 3]], 0.55, (c, f) => {
          for (let i = 0; i < 9; i++) {
            const tx = Math.floor(rnd() * BGW), ty = 176 + f(tx);
            for (const dx of [0, BGW, -BGW]) {
              R(c, tx + dx - 2, ty - 30, 5, 30, '#2e5a3a');
              c.fillStyle = '#357a50'; c.beginPath(); c.arc(tx + dx, ty - 38, 16, 0, Math.PI * 2); c.fill();
              c.fillStyle = '#4a9a64'; c.beginPath(); c.arc(tx + dx - 5, ty - 43, 8, 0, Math.PI * 2); c.fill();
            }
          }
        });
        break;
      case 'cave':
        silhouette('#1e1834', 60, [[3, 20], [7, 8]], 0.15, (c) => {
          for (let i = 0; i < 18; i++) {
            const x = Math.floor(rnd() * BGW), w = 6 + Math.floor(rnd() * 10), hh = 20 + Math.floor(rnd() * 50);
            for (let k = 0; k < w / 2; k++) R(c, x + k, 0, w - k * 2, hh - k * 6 > 0 ? hh - k * 6 : 0, '#1a142c');
          }
        });
        silhouette('#2a2246', 170, [[4, 14], [9, 6]], 0.35, (c) => {
          for (let i = 0; i < 14; i++) {
            const x = Math.floor(rnd() * BGW), w = 4 + Math.floor(rnd() * 8), hh = 14 + Math.floor(rnd() * 36);
            for (let k = 0; k < w; k++) R(c, x + k, 0, 1, Math.max(0, hh - Math.abs(k - w / 2) * 4), '#2a2246');
          }
        });
        break;
      case 'sea':
        silhouette('#0f4a7c', 150, [[2, 18], [6, 8]], 0.15);
        silhouette('#0b3a66', 180, [[3, 12], [8, 6], [13, 2]], 0.35, (c, f) => {
          for (let i = 0; i < 16; i++) {
            const x = Math.floor(rnd() * BGW), y = 180 + f(x), col = U.pick(['#d0507a', '#e88a40', '#9a5ad0']);
            for (const dx of [0, BGW, -BGW]) {
              R(c, x + dx, y - 14, 2, 14, col); R(c, x + dx - 4, y - 10, 4, 2, col); R(c, x + dx - 4, y - 16, 2, 6, col);
              R(c, x + dx + 2, y - 8, 4, 2, col); R(c, x + dx + 5, y - 13, 2, 5, col);
            }
          }
        });
        break;
      case 'desert':
        silhouette('#f0b878', 140, [[2, 10], [5, 4]], 0.1, (c, f) => {
          for (let i = 0; i < 3; i++) {
            const px = 60 + i * 170 + Math.floor(rnd() * 40), base = 140 + f(px) + 4, s = 30 + Math.floor(rnd() * 22);
            for (let k = 0; k < s; k++) { R(c, px - s + k, base - k, (s - k) * 2, 1, k % 6 === 0 ? '#d89a5e' : '#e4a86a'); }
          }
        });
        silhouette('#dc9a5a', 172, [[3, 9], [7, 4]], 0.32);
        silhouette('#c8844a', 196, [[4, 6], [10, 3]], 0.6, (c, f) => {
          for (let i = 0; i < 6; i++) {
            const x = Math.floor(rnd() * BGW), y = 196 + f(x);
            for (const dx of [0, BGW, -BGW]) {
              R(c, x + dx, y - 24, 5, 24, '#5a8a4a'); R(c, x + dx - 6, y - 16, 6, 3, '#5a8a4a'); R(c, x + dx - 6, y - 22, 3, 6, '#5a8a4a');
              R(c, x + dx + 5, y - 12, 5, 3, '#5a8a4a'); R(c, x + dx + 8, y - 18, 3, 6, '#5a8a4a'); R(c, x + dx + 1, y - 24, 1, 24, '#7aaa64');
            }
          }
        });
        break;
      case 'sky':
        silhouette('rgba(255,255,255,0.55)', 170, [[3, 10], [8, 6], [17, 3]], 0.1);
        silhouette('#b4c4ee', 120, [[2, 8]], 0.22, (c) => {
          c.clearRect(0, 0, BGW, VH);
          for (let i = 0; i < 3; i++) {
            const x = 40 + i * 170 + Math.floor(rnd() * 60), y = 70 + Math.floor(rnd() * 50);
            c.fillStyle = '#c4d2f4'; c.beginPath(); c.ellipse(x, y, 34, 9, 0, 0, Math.PI * 2); c.fill();
            c.fillStyle = '#9aa8d4';
            for (let k = 0; k < 6; k++) R(c, x - 24 + k * 8, y + 4, 6, 10 - Math.abs(k - 2.5) * 3, '#9aa8d4');
            if (i === 1) { R(c, x - 10, y - 30, 20, 26, '#a8b4e0'); R(c, x - 14, y - 36, 6, 32, '#a8b4e0'); R(c, x + 8, y - 36, 6, 32, '#a8b4e0'); R(c, x - 2, y - 44, 4, 14, '#a8b4e0'); }
          }
        });
        silhouette('rgba(255,255,255,0.9)', 205, [[4, 8], [9, 5], [21, 2]], 0.45);
        break;
      case 'castle':
        silhouette('#1c0e22', 140, [[2, 6]], 0.12, (c) => {
          for (let i = 0; i < 9; i++) {
            const x = Math.floor(rnd() * BGW), w = 14 + Math.floor(rnd() * 16), hh = 50 + Math.floor(rnd() * 60);
            for (const dx of [0, BGW, -BGW]) {
              R(c, x + dx, 150 - hh, w, hh + 80, '#1c0e22');
              for (let k = 0; k < w; k += 4) R(c, x + dx + k, 150 - hh - 4, 2, 4, '#1c0e22');
              if (rnd() < 0.8) R(c, x + dx + Math.floor(w / 2) - 1, 150 - hh + 12, 3, 5, '#ffb040');
            }
          }
        });
        silhouette('#2a1834', 196, [[3, 4]], 0.38, (c) => {
          for (let i = 0; i < 8; i++) {
            const x = i * 64 + 20;
            R(c, x, 40, 12, 170, '#2e1c3a'); R(c, x - 3, 40, 18, 6, '#3a2648'); R(c, x + 1, 46, 2, 160, '#3a2648');
            R(c, x + 18, 60, 14, 34, '#6a1a2a'); R(c, x + 18, 94, 4, 6, '#6a1a2a'); R(c, x + 28, 94, 4, 6, '#6a1a2a'); R(c, x + 23, 70, 4, 4, '#d8a040');
          }
        });
        break;
    }
    return { layers, theme: THEMES[name] };
  },
  draw(c, name, camX, t, vw) {
    const bg = this.get(name), th = THEMES[name];
    const g = c.createLinearGradient(0, 0, 0, VH);
    g.addColorStop(0, th.sky[0]); g.addColorStop(1, th.sky[1]);
    c.fillStyle = g; c.fillRect(0, 0, vw, VH);
    // 하늘 장식
    if (name === 'forest') {
      c.fillStyle = 'rgba(255,250,210,0.9)'; c.beginPath(); c.arc(vw * 0.78, 40, 16, 0, Math.PI * 2); c.fill();
      drawClouds(c, camX * 0.05 + t * 4, vw, 'rgba(255,255,255,0.85)', 3);
    } else if (name === 'desert') {
      c.fillStyle = 'rgba(255,240,180,0.6)'; c.beginPath(); c.arc(vw * 0.7, 52, 30, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#fff4c8'; c.beginPath(); c.arc(vw * 0.7, 52, 20, 0, Math.PI * 2); c.fill();
    } else if (name === 'sky') {
      drawClouds(c, camX * 0.06 + t * 8, vw, 'rgba(255,255,255,0.9)', 5);
    } else if (name === 'castle') {
      c.fillStyle = '#f8e8c8'; c.beginPath(); c.arc(vw * 0.82, 38, 14, 0, Math.PI * 2); c.fill();
      c.fillStyle = th.sky[0]; c.beginPath(); c.arc(vw * 0.82 + 6, 34, 12, 0, Math.PI * 2); c.fill();
      for (let i = 0; i < 30; i++) R(c, (U.hash(i, 1, 5) * vw) | 0, (U.hash(i, 2, 5) * 100) | 0, 1, 1, U.hash(i, 3, 5) < 0.5 ? '#fff' : '#a8a0c8');
    } else if (name === 'cave') {
      for (let i = 0; i < 18; i++) {
        const gx = ((U.hash(i, 4, 9) * 900 - camX * 0.2) % 900 + 900) % 900 - 100;
        const gy = 40 + U.hash(i, 5, 9) * 140;
        const a = 0.25 + 0.2 * Math.sin(t * 2 + i);
        c.fillStyle = `rgba(110,240,255,${a})`; c.fillRect(gx | 0, gy | 0, 2, 2);
      }
    }
    for (const L of bg.layers) {
      const off = -((camX * L.factor) % BGW + BGW) % BGW;
      for (let x = Math.floor(off); x < vw; x += BGW) c.drawImage(L.cv, x, 0);
    }
    if (name === 'sea') {
      // 물속 빛줄기
      c.save();
      c.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 5; i++) {
        const bx = ((i * 140 - camX * 0.25 + Math.sin(t * 0.4 + i) * 20) % (vw + 200) + vw + 200) % (vw + 200) - 100;
        c.fillStyle = 'rgba(120,200,255,0.06)';
        c.beginPath(); c.moveTo(bx, 0); c.lineTo(bx + 30, 0); c.lineTo(bx + 90, VH); c.lineTo(bx + 40, VH); c.fill();
      }
      c.restore();
    }
  },
};

function drawClouds(c, off, vw, col, n) {
  c.fillStyle = col;
  for (let i = 0; i < n; i++) {
    const span = vw + 160;
    const x = ((i * 157 + 40 - off) % span + span) % span - 80;
    const y = 18 + (i * 37) % 60;
    c.beginPath();
    c.ellipse(x, y, 22, 7, 0, 0, Math.PI * 2);
    c.ellipse(x - 10, y - 3, 10, 6, 0, 0, Math.PI * 2);
    c.ellipse(x + 8, y - 5, 12, 7, 0, 0, Math.PI * 2);
    c.fill();
  }
}
