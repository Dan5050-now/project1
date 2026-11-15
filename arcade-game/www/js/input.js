'use strict';
// ─────────────────────────────────────────────────────────────
//  input.js — 터치 가상 조이스틱/버튼 + 키보드(PC 테스트용)
// ─────────────────────────────────────────────────────────────

const Input = {
  keys: {},
  axisX: 0, axisY: 0,
  jumpHeld: false, attackHeld: false,
  _jump: false, _attack: false, _pause: false,
  taps: [],                 // 메뉴용 터치 좌표 목록
  nav: { dx: 0, dy: 0, ok: false, back: false },
  controls: false,          // 플레이 중 터치 컨트롤 활성화 여부
  touchSeen: false,
  stick: { id: null, cx: 0, cy: 0, x: 0, y: 0, nx: 0, ny: 0, r: 30 },
  btn: {
    jump: { x: 0, y: 0, r: 0, ids: new Set(), label: 'A' },
    attack: { x: 0, y: 0, r: 0, ids: new Set(), label: 'B' },
  },
  pauseBtn: { x: 0, y: 0, r: 0 },
  pointerRole: new Map(),

  init(canvas) {
    this.canvas = canvas;
    const pos = (e) => {
      const r = canvas.getBoundingClientRect();
      return { x: (e.clientX - r.left) * (G.W / r.width), y: (e.clientY - r.top) * (G.H / r.height) };
    };
    canvas.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      Sound.init();
      if (e.pointerType === 'touch') this.touchSeen = true;
      try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* 무시 */ }
      const p = pos(e);
      this.taps.push(p);
      if (!this.controls) return;
      const pb = this.pauseBtn;
      if (Math.hypot(p.x - pb.x, p.y - pb.y) < pb.r * 1.6) { this._pause = true; return; }
      if (p.x < G.W * 0.42) {
        if (this.stick.id === null) {
          const s = this.stick;
          s.id = e.pointerId;
          s.cx = U.clamp(p.x, s.r * 1.1, G.W * 0.42 - s.r);
          s.cy = U.clamp(p.y, G.H * 0.3, G.H - s.r * 1.1);
          s.x = p.x; s.y = p.y;
          this.pointerRole.set(e.pointerId, 'stick');
          this.updateStick();
        }
      } else {
        const role = this.buttonAt(p.x, p.y, true);
        if (role) this.press(e.pointerId, role);
      }
    }, { passive: false });
    canvas.addEventListener('pointermove', (e) => {
      if (!this.pointerRole.has(e.pointerId)) return;
      e.preventDefault();
      const p = pos(e);
      const role = this.pointerRole.get(e.pointerId);
      if (role === 'stick') {
        this.stick.x = p.x; this.stick.y = p.y; this.updateStick();
      } else {
        // 손가락을 미끄러뜨려 A↔B 버튼 전환
        const nr = this.buttonAt(p.x, p.y, false);
        if (nr && nr !== role) { this.release(e.pointerId); this.press(e.pointerId, nr); }
      }
    }, { passive: false });
    const up = (e) => { this.release(e.pointerId); };
    canvas.addEventListener('pointerup', up);
    canvas.addEventListener('pointercancel', up);
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    window.addEventListener('keydown', (e) => {
      const k = e.code;
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Space'].includes(k)) e.preventDefault();
      if (this.keys[k]) return;
      this.keys[k] = true;
      this.keyUsed = true;
      Sound.init();
      if (k === 'KeyZ' || k === 'Space' || k === 'KeyK' || k === 'ArrowUp' || k === 'KeyW') this._jump = true;
      if (k === 'KeyX' || k === 'KeyJ') this._attack = true;
      if (k === 'Escape' || k === 'KeyP') { this._pause = true; this.nav.back = true; }
      if (k === 'ArrowLeft' || k === 'KeyA') this.nav.dx = -1;
      if (k === 'ArrowRight' || k === 'KeyD') this.nav.dx = 1;
      if (k === 'ArrowUp' || k === 'KeyW') this.nav.dy = -1;
      if (k === 'ArrowDown' || k === 'KeyS') this.nav.dy = 1;
      if (k === 'Enter' || k === 'Space' || k === 'KeyZ') this.nav.ok = true;
      if (k === 'Backspace') this.nav.back = true;
    });
    window.addEventListener('keyup', (e) => { this.keys[e.code] = false; });
    window.addEventListener('blur', () => this.resetAll());
  },

  buttonAt(x, y, generous) {
    let best = null, bd = 1e9;
    for (const role of ['jump', 'attack']) {
      const b = this.btn[role];
      const d = Math.hypot(x - b.x, y - b.y);
      if (d < bd) { bd = d; best = role; }
    }
    const lim = this.btn[best].r * (generous ? 2.2 : 1.25);
    return bd < lim ? best : (generous ? best : null);
  },
  press(id, role) {
    this.pointerRole.set(id, role);
    const b = this.btn[role];
    if (b.ids.size === 0) { if (role === 'jump') this._jump = true; else this._attack = true; }
    b.ids.add(id);
  },
  release(id) {
    const role = this.pointerRole.get(id);
    if (!role) return;
    this.pointerRole.delete(id);
    if (role === 'stick') {
      this.stick.id = null; this.stick.nx = 0; this.stick.ny = 0;
    } else this.btn[role].ids.delete(id);
  },
  updateStick() {
    const s = this.stick;
    let dx = s.x - s.cx, dy = s.y - s.cy;
    const d = Math.hypot(dx, dy);
    if (d > s.r) {
      // 손가락이 멀리 가면 조이스틱 중심이 따라온다 (플로팅 조이스틱)
      const over = d - s.r;
      s.cx += (dx / d) * over; s.cy += (dy / d) * over;
      dx = s.x - s.cx; dy = s.y - s.cy;
    }
    s.nx = dx / s.r; s.ny = dy / s.r;
  },
  resetAll() {
    this.keys = {};
    this.pointerRole.clear();
    this.stick.id = null; this.stick.nx = 0; this.stick.ny = 0;
    this.btn.jump.ids.clear(); this.btn.attack.ids.clear();
  },

  layout() {
    const S = G.S;
    this.stick.r = 26 * S;
    this.btn.jump.r = 19 * S;
    this.btn.attack.r = 16 * S;
    this.btn.jump.x = G.W - 30 * S; this.btn.jump.y = G.H - 34 * S;
    this.btn.attack.x = G.W - 74 * S; this.btn.attack.y = G.H - 24 * S;
    this.pauseBtn.r = 10 * S; this.pauseBtn.x = G.W - 16 * S; this.pauseBtn.y = 15 * S;
    if (this.stick.id === null) { this.stick.cx = 44 * S; this.stick.cy = G.H - 44 * S; }
  },

  // 매 프레임 시작 시 호출
  poll() {
    let ax = 0;
    if (this.keys.ArrowLeft || this.keys.KeyA) ax -= 1;
    if (this.keys.ArrowRight || this.keys.KeyD) ax += 1;
    let ay = 0;
    if (this.keys.ArrowUp || this.keys.KeyW) ay -= 1;
    if (this.keys.ArrowDown || this.keys.KeyS) ay += 1;
    if (this.stick.id !== null) {
      // 플랫폼 게임은 디지털 입력이 조작감이 좋다 → 임계값 넘으면 최대 속도
      if (Math.abs(this.stick.nx) > 0.28) ax = U.sign(this.stick.nx);
      if (Math.abs(this.stick.ny) > 0.5) ay = U.sign(this.stick.ny);
    }
    this.axisX = ax; this.axisY = ay;
    this.jumpHeld = this.btn.jump.ids.size > 0 || !!(this.keys.KeyZ || this.keys.Space || this.keys.KeyK || this.keys.ArrowUp || this.keys.KeyW);
    this.attackHeld = this.btn.attack.ids.size > 0 || !!(this.keys.KeyX || this.keys.KeyJ);
  },
  // 프레임 끝에서 일회성 입력 정리
  endFrame() {
    this.taps.length = 0;
    this.nav.dx = 0; this.nav.dy = 0; this.nav.ok = false; this.nav.back = false;
  },
  jumpPressed() { const v = this._jump; this._jump = false; return v; },
  attackPressed() { const v = this._attack; this._attack = false; return v; },
  pausePressed() { const v = this._pause; this._pause = false; return v; },
  clearActions() { this._jump = false; this._attack = false; this._pause = false; },
};
