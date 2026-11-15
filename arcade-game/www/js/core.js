'use strict';
// ─────────────────────────────────────────────────────────────
//  core.js — 공통 상수, 수학 유틸, 난수, 저장 데이터
// ─────────────────────────────────────────────────────────────

const TILE = 16;          // 타일 한 칸 크기 (게임 픽셀)
const ROWS = 14;          // 화면 세로 타일 수
const VH = ROWS * TILE;   // 게임 화면 세로 해상도 (224)
const STEP = 1 / 60;      // 고정 물리 시간 간격

const U = {
  clamp: (v, a, b) => (v < a ? a : v > b ? b : v),
  lerp: (a, b, t) => a + (b - a) * t,
  sign: (v) => (v < 0 ? -1 : v > 0 ? 1 : 0),
  approach(v, target, delta) {
    return v < target ? Math.min(v + delta, target) : Math.max(v - delta, target);
  },
  overlap: (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y,
  rectOverlap: (ax, ay, aw, ah, b) => ax < b.x + b.w && ax + aw > b.x && ay < b.y + b.h && ay + ah > b.y,
  dist: (ax, ay, bx, by) => Math.hypot(bx - ax, by - ay),
  rand: (a, b) => a + Math.random() * (b - a),
  randInt: (a, b) => Math.floor(a + Math.random() * (b - a + 1)),
  pick: (arr) => arr[Math.floor(Math.random() * arr.length)],
  // 결정적(seed 고정) 난수 — 맵·배경을 매번 같게 그리기 위함
  rng(seed) {
    let s = (seed >>> 0) || 0x9e3779b9;
    return () => {
      s ^= s << 13; s >>>= 0;
      s ^= s >>> 17;
      s ^= s << 5; s >>>= 0;
      return s / 4294967296;
    };
  },
  hash(x, y, seed = 0) {
    let h = (x * 374761393 + y * 668265263 + seed * 2246822519) >>> 0;
    h = ((h ^ (h >>> 13)) * 1274126177) >>> 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  },
  easeOutBack(t) {
    const c1 = 1.70158, c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
  easeOutCubic: (t) => 1 - Math.pow(1 - t, 3),
  fmt(n, len) { return String(Math.floor(n)).padStart(len, '0'); },
};

// ─── 저장 데이터 (localStorage) ───
const Save = {
  KEY: 'starshard_quest_v1',
  data: null,
  load() {
    try { this.data = JSON.parse(localStorage.getItem(this.KEY)) || {}; }
    catch (e) { this.data = {}; }
    if (!this.data.settings) this.data.settings = { sfx: true, music: true, vibrate: true };
    if (!this.data.records) this.data.records = {};
    return this.data;
  },
  write() {
    try { localStorage.setItem(this.KEY, JSON.stringify(this.data)); } catch (e) { /* 저장 불가 환경 */ }
  },
  get settings() { return this.data.settings; },
  get run() { return this.data.run || null; },
  setRun(run) { this.data.run = JSON.parse(JSON.stringify(run)); this.write(); },
  clearRun() { delete this.data.run; this.write(); },
  record(diff, char, score) {
    const key = diff;
    const r = this.data.records[key] || { cleared: false, best: 0, chars: {} };
    r.cleared = true;
    r.best = Math.max(r.best, score);
    r.chars[char] = true;
    this.data.records[key] = r;
    this.write();
  },
  wipe() { this.data = { settings: this.data.settings, records: {} }; this.write(); },
};

// 진동 (지원되는 기기에서만)
function vibrate(ms) {
  try { if (Save.settings.vibrate && navigator.vibrate) navigator.vibrate(ms); } catch (e) { /* 무시 */ }
}
