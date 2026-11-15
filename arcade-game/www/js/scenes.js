'use strict';
// ─────────────────────────────────────────────────────────────
//  scenes.js — 게임 흐름(Flow)과 모든 화면(타이틀~엔딩)
// ─────────────────────────────────────────────────────────────

const Game = {
  scene: null, next: null, fade: 0, fadeDir: 0, t: 0,
  go(factory, fast) {
    if (this.fadeDir === 1) return;
    this.next = factory; this.fadeDir = 1; this.fadeSpeed = fast ? 6 : 4;
  },
  set(scene) { this.scene = scene; UI.resetSel(0); Input.controls = false; Input.resetAll(); Input.clearActions(); if (scene.enter) scene.enter(); },
  update(dt) {
    this.t += dt;
    if (this.fadeDir === 1) {
      this.fade += dt * this.fadeSpeed;
      if (this.fade >= 1) { this.fade = 1; this.fadeDir = -1; const f = this.next; this.next = null; this.set(f()); }
      return;
    }
    if (this.fadeDir === -1) { this.fade -= dt * this.fadeSpeed; if (this.fade <= 0) { this.fade = 0; this.fadeDir = 0; } }
    if (G.portrait) return;
    this.scene.update(dt);
  },
  draw() {
    this.scene.draw(this.t);
    const c = G.sctx;
    if (this.fade > 0) { c.fillStyle = `rgba(4,2,14,${this.fade})`; c.fillRect(0, 0, G.W, G.H); }
    if (G.portrait) {
      c.fillStyle = 'rgba(4,2,14,0.94)'; c.fillRect(0, 0, G.W, G.H);
      const s = Math.min(G.W, G.H) / 160;
      c.save(); c.translate(G.W / 2, G.H / 2 - 20 * s); c.rotate(-Math.PI / 2 * ((Math.sin(this.t * 2) + 1) / 2));
      c.strokeStyle = '#ffd86a'; c.lineWidth = 3 * s; G.roundRect(c, -14 * s, -24 * s, 28 * s, 48 * s, 4 * s); c.stroke(); c.restore();
      c.font = G.font(9 * s); c.fillStyle = '#fff'; c.textAlign = 'center';
      c.fillText('화면을 가로로 돌려 주세요', G.W / 2, G.H / 2 + 30 * s);
    }
  },
};

// ═════════ 게임 진행 흐름 ═════════
const Flow = {
  run: null,
  newGame(char, diff) {
    this.run = {
      char, diff, stage: 0, lives: DIFFICULTY[diff].lives, coins: 0, score: 0, hpBonus: 0,
      carryShield: false, carryCharm: false, time: 0, stageStart: null,
    };
    Save.setRun(this.run);
    Game.go(() => new StoryScene(STORY.prologue.lines, { bg: 'castle', music: 'dark', right: null, pipiLate: true, done: () => this.startStage(0) }));
  },
  continueGame() {
    this.run = JSON.parse(JSON.stringify(Save.run));
    this.startStage(this.run.stage);
  },
  startStage(i) {
    const run = this.run;
    run.stage = i;
    run.stageStart = { coins: run.coins, score: run.score, lives: run.lives };
    Save.setRun(run);
    const st = STAGES[i];
    Game.go(() => new StoryScene(STORY.stages[i].intro, { bg: st.theme, music: 'story', right: i === 5 ? 'morvath' : null, done: () => Game.go(() => new StageIntroScene(i)) }));
  },
  stageClear(stats) {
    const run = this.run, i = run.stage;
    Game.go(() => new ResultScene(stats, () => {
      const st = STAGES[i];
      const nextStage = i + 1;
      run.stage = Math.min(nextStage, STAGES.length - 1);
      if (nextStage < STAGES.length) { run.stage = nextStage; Save.setRun(run); }
      Game.go(() => new StoryScene(STORY.stages[i].outro, {
        bg: st.theme, music: i === 5 ? 'dark' : 'story', right: 'boss', bossStage: i,
        done: () => {
          if (nextStage >= STAGES.length) Game.go(() => new StoryScene(STORY.ending.lines, { bg: 'sky', music: 'ending', right: 'sage', ending: true, done: () => Game.go(() => new CreditsScene()) }));
          else Game.go(() => new ShopScene());
        },
      }));
    }));
  },
  gameOver() { Game.go(() => new GameOverScene()); },
  retryStage() {
    const run = this.run, ss = run.stageStart;
    run.lives = DIFFICULTY[run.diff].lives;
    run.coins = Math.floor(ss.coins / 2);
    run.score = ss.score;
    run.stageStart = { coins: run.coins, score: run.score, lives: run.lives };
    Save.setRun(run);
    Game.go(() => new StageIntroScene(run.stage));
  },
};

// ═════════ 타이틀 ═════════
class TitleScene {
  constructor() { this.t = 0; this.mode = 'press'; this.modal = null; }
  enter() { if (Sound.ctx) Sound.music('title'); }
  items() {
    const S = G.S, w = 128 * S, h = 21 * S, x = (G.W - w) / 2;
    let y = 100 * S;
    const run = Save.run;
    const list = [
      { label: '새 게임', on: () => Game.go(() => new CharSelectScene()) },
      {
        label: '이어하기', sub: run ? `${STAGES[run.stage].sub} · ${CHARACTERS[run.char].name} · ${DIFFICULTY[run.diff].name}` : '저장된 진행 없음',
        disabled: !run, on: () => Flow.continueGame(),
      },
      { label: '조작 방법', on: () => { this.modal = 'help'; } },
      { label: '설정', on: () => { this.modal = 'settings'; UI.resetSel(0); } },
    ];
    return list.map((b) => { const o = Object.assign({ x, y, w, h: b.sub ? h * 1.25 : h }, b); y += o.h + 5 * S; return o; });
  }
  settingsItems() {
    const S = G.S, w = 150 * S, h = 20 * S, x = (G.W - w) / 2;
    const st = Save.settings;
    let y = 64 * S;
    const onoff = (v) => (v ? '켜짐' : '꺼짐');
    const list = [
      { label: `효과음: ${onoff(st.sfx)}`, on: () => { st.sfx = !st.sfx; Save.write(); Sound.applySettings(); } },
      { label: `배경음악: ${onoff(st.music)}`, on: () => { st.music = !st.music; Save.write(); Sound.applySettings(); } },
      { label: `진동: ${onoff(st.vibrate)}`, on: () => { st.vibrate = !st.vibrate; Save.write(); vibrate(40); } },
      { label: this.confirmWipe ? '정말 삭제할까요? (한 번 더)' : '진행 기록 삭제', on: () => { if (this.confirmWipe) { Save.wipe(); this.confirmWipe = false; } else this.confirmWipe = true; } },
      { label: '닫기', on: () => { this.modal = null; this.confirmWipe = false; UI.resetSel(0); } },
    ];
    return list.map((b) => { const o = Object.assign({ x, y, w, h }, b); y += h + 5 * S; return o; });
  }
  update(dt) {
    this.t += dt;
    if (this.mode === 'press') {
      if (Input.taps.length || Input.nav.ok) { Sound.init(); Sound.play('confirm'); Sound.music('title'); this.mode = 'menu'; }
      return;
    }
    if (this.modal === 'help') { if (Input.taps.length || Input.nav.ok || Input.nav.back) { this.modal = null; Sound.play('back'); } return; }
    if (this.modal === 'settings') { if (Input.nav.back) { this.modal = null; return; } UI.handle(this.settingsItems()); return; }
    UI.handle(this.items());
  }
  draw(t) {
    const c = G.bctx;
    const camX = this.t * 24;
    Backgrounds.draw(c, 'forest', camX, this.t, G.VW);
    drawGroundBand(c, 'forest', camX);
    // 주인공들
    const gx = G.VW / 2;
    drawHero(c, 'mina', 40, 176, 1, 'run', this.t);
    drawHero(c, 'leo', 62, 176, 1, 'run', this.t + 0.2);
    drawHero(c, 'sera', 84, 176, 1, 'run', this.t + 0.4);
    drawPipi(c, 100, 150, this.t);
    drawEnemy(c, { type: 'walker', x: G.VW - 70 + Math.sin(this.t) * 10, y: 164, w: 14, h: 12, dir: -1, flash: 0, vy: 0 }, 'forest', this.t);
    drawEnemy(c, { type: 'flyer', x: G.VW - 48, y: 120 + Math.sin(this.t * 2) * 8, w: 14, h: 10, dir: -1, flash: 0 }, 'forest', this.t);
    G.present();
    const S = G.S, sc = G.sctx;
    // 로고
    const ly = this.mode === 'press' ? 62 * S : 44 * S;
    sc.save();
    sc.font = G.font(32 * S, 900); sc.textAlign = 'center'; sc.textBaseline = 'middle';
    sc.lineJoin = 'round'; sc.strokeStyle = '#1a1040'; sc.lineWidth = 7 * S; sc.strokeText('별조각 퀘스트', G.W / 2, ly);
    const g = sc.createLinearGradient(0, ly - 16 * S, 0, ly + 16 * S);
    g.addColorStop(0, '#fff6b0'); g.addColorStop(0.5, '#ffd23a'); g.addColorStop(1, '#ff8a2a');
    sc.fillStyle = g; sc.fillText('별조각 퀘스트', G.W / 2, ly);
    sc.restore();
    G.text('STARSHARD QUEST', G.W / 2, ly + 22 * S, 9, '#bfe8ff', 'center');
    for (let i = 0; i < 5; i++) {
      const a = this.t * 1.2 + i * 1.256;
      blit((cc, x, y) => drawStarShape(cc, x, y - 8, 4 + (i % 2), '#fff6b0', '#ffd23a'), G.W / 2 + Math.cos(a) * 130 * S, ly + Math.sin(a) * 18 * S, S * 0.9, 0.8);
    }
    if (this.mode === 'press') {
      if (Math.floor(this.t * 2) % 2 === 0) G.text('화면을 터치하세요', G.W / 2, 150 * S, 11, '#ffffff', 'center');
      G.text('© 2026 Starshard Quest · 오리지널 게임', G.W / 2, 214 * S, 6, 'rgba(255,255,255,0.7)', 'center', { weight: 500 });
      return;
    }
    if (this.modal === 'help') return this.drawHelp();
    if (this.modal === 'settings') {
      UI.dim(0.65);
      G.text('설정', G.W / 2, 44 * S, 14, '#ffd86a', 'center');
      this.settingsItems().forEach((b, i) => UI.button(b, i === UI.sel, this.t));
      return;
    }
    const items = this.items();
    items.forEach((b, i) => UI.button(b, i === UI.sel, this.t));
    const rec = Save.data.records;
    const cleared = DIFF_ORDER.filter((d) => rec[d] && rec[d].cleared).map((d) => DIFFICULTY[d].name);
    if (cleared.length) G.text('★ 클리어: ' + cleared.join(' · '), G.W / 2, 216 * S, 7, '#ffe85a', 'center');
  }
  drawHelp() {
    const S = G.S;
    UI.dim(0.75);
    const w = Math.min(G.W - 20 * S, 330 * S), x = (G.W - w) / 2, y = 14 * S, h = 196 * S;
    G.panel(x, y, w, h);
    G.text('조작 방법', G.W / 2, y + 14 * S, 13, '#ffd86a', 'center');
    const lines = [
      ['왼쪽 화면', '아무 곳이나 누르고 끌면 조이스틱 — 좌우 이동'],
      ['A 버튼', '점프 (길게 누르면 높이, 짧게 누르면 낮게) · 물속에서는 헤엄'],
      ['B 버튼', '공격 — 적 처치, 벽돌·★블록 부수기'],
      ['밟기', '대부분의 적은 위에서 밟아서도 물리칠 수 있어요 (가시 달린 적 제외)'],
      ['체크포인트', '깃발에 닿으면 쓰러져도 그 자리에서 다시 시작'],
      ['아이템', '하트=체력  빨간 구슬=파워업  파란 방패=보호막  별=무적  초록 병=1UP'],
      ['상점', '스테이지 사이에 코인으로 아이템을 살 수 있어요'],
      ['키보드', '← → 이동 · Z/스페이스 점프 · X 공격 · Esc 일시정지'],
    ];
    let yy = y + 32 * S;
    for (const [k, v] of lines) {
      G.text(k, x + 12 * S, yy, 7.5, '#8ad8ff', 'left');
      const ls = G.wrap(v, w - 82 * S, 7);
      ls.forEach((l, i) => G.text(l, x + 70 * S, yy + i * 9 * S, 7, '#ffffff', 'left', { weight: 600 }));
      yy += Math.max(1, ls.length) * 9 * S + 7 * S;
    }
    G.text('화면을 누르면 닫혀요', G.W / 2, y + h - 9 * S, 7, '#c8c4f0', 'center', { weight: 600 });
  }
}

// ═════════ 캐릭터 선택 ═════════
class CharSelectScene {
  constructor() { this.t = 0; this.pick = 0; }
  enter() { Sound.music('title'); }
  layout() {
    const S = G.S;
    const cw = Math.min(118 * S, (G.W - 40 * S) / 3), ch = 132 * S, gap = 8 * S;
    const total = cw * 3 + gap * 2, x0 = (G.W - total) / 2, y0 = 34 * S;
    return CHAR_ORDER.map((id, i) => ({ id, x: x0 + i * (cw + gap), y: y0, w: cw, h: ch }));
  }
  buttons() {
    const S = G.S, h = 20 * S, y = G.H - h - 10 * S;
    return [
      { x: 10 * S, y, w: 70 * S, h, label: '◀ 뒤로', on: () => Game.go(() => new TitleScene()) },
      { x: G.W - 110 * S, y, w: 100 * S, h, label: '선택 ▶', color: '#7af0a0', color2: '#2ab86a', on: () => Game.go(() => new DiffSelectScene(CHAR_ORDER[this.pick])) },
    ];
  }
  update(dt) {
    this.t += dt;
    if (Input.nav.dx) { this.pick = (this.pick + Input.nav.dx + 3) % 3; Sound.play('select'); Input.nav.dx = 0; }
    if (Input.nav.back) { Game.go(() => new TitleScene()); return; }
    for (const tp of Input.taps) {
      this.layout().forEach((cd, i) => {
        if (tp.x >= cd.x && tp.x <= cd.x + cd.w && tp.y >= cd.y && tp.y <= cd.y + cd.h) {
          if (this.pick === i) { Sound.play('confirm'); Game.go(() => new DiffSelectScene(CHAR_ORDER[this.pick])); }
          else { this.pick = i; Sound.play('select'); }
        }
      });
    }
    UI.sel = 1;
    if (Input.nav.ok) { Sound.play('confirm'); Game.go(() => new DiffSelectScene(CHAR_ORDER[this.pick])); Input.nav.ok = false; return; }
    UI.handle(this.buttons(), { horizontal: true });
    UI.sel = 1;
  }
  draw(t) {
    UI.starfield(this.t);
    const S = G.S;
    G.text('캐릭터 선택', G.W / 2, 17 * S, 13, '#ffd86a', 'center');
    this.layout().forEach((cd, i) => {
      const def = CHARACTERS[cd.id], sel = i === this.pick;
      G.panel(cd.x, cd.y, cd.w, cd.h, { fill: sel ? 'rgba(60,40,130,0.92)' : 'rgba(20,16,50,0.8)', stroke: sel ? '#ffd86a' : 'rgba(255,255,255,0.25)', lw: sel ? 2.5 : 1 });
      const cx = cd.x + cd.w / 2;
      G.sctx.fillStyle = sel ? 'rgba(255,220,120,0.18)' : 'rgba(255,255,255,0.05)';
      G.sctx.beginPath(); G.sctx.ellipse(cx, cd.y + 62 * S, 22 * S, 5 * S, 0, 0, Math.PI * 2); G.sctx.fill();
      blit((c, x, y) => drawHero(c, cd.id, x, y, 1, sel ? (Math.floor(this.t / 1.6) % 2 ? 'attack' : 'run') : 'idle', this.t, { atkP: (this.t * 2.5) % 1 }), cx, cd.y + 62 * S, S * 2.1, sel ? 1 : 0.65);
      G.text(def.name, cx, cd.y + 74 * S, 12, sel ? '#ffffff' : '#c8c4f0', 'center');
      G.text(def.title, cx, cd.y + 85 * S, 7, sel ? '#ffd86a' : '#8a86b0', 'center', { weight: 700 });
      let yy = cd.y + 96 * S;
      for (const [k, v] of Object.entries(def.stats)) {
        G.text(k, cd.x + 9 * S, yy, 6.5, '#d8d4ff', 'left', { weight: 700, outline: false });
        for (let j = 0; j < 5; j++) {
          G.sctx.fillStyle = j < v ? (sel ? '#ffd23a' : '#9a8a50') : 'rgba(255,255,255,0.15)';
          G.sctx.fillRect(cd.x + 34 * S + j * ((cd.w - 44 * S) / 5), yy - 2.5 * S, (cd.w - 46 * S) / 5, 5 * S);
        }
        yy += 8.5 * S;
      }
    });
    const def = CHARACTERS[CHAR_ORDER[this.pick]];
    const lines = G.wrap(def.desc + '  [' + def.special + ']', G.W - 220 * S, 7.5);
    lines.slice(0, 2).forEach((l, i) => G.text(l, G.W / 2, 178 * S + i * 10 * S, 7.5, '#ffffff', 'center', { weight: 600 }));
    this.buttons().forEach((b, i) => UI.button(b, i === 1, this.t));
  }
}

// ═════════ 난이도 선택 ═════════
class DiffSelectScene {
  constructor(char) { this.char = char; this.t = 0; }
  enter() { UI.resetSel(1); }
  items() {
    const S = G.S, w = Math.min(220 * S, G.W - 40 * S), h = 34 * S, x = (G.W - w) / 2;
    let y = 40 * S;
    const list = DIFF_ORDER.map((d) => {
      const df = DIFFICULTY[d];
      const o = { x, y, w, h, label: df.name, sub: df.desc, size: 12, color: df.color, color2: df.color, on: () => Flow.newGame(this.char, d) };
      y += h + 7 * S; return o;
    });
    return list;
  }
  update(dt) {
    this.t += dt;
    if (Input.nav.back) { Game.go(() => new CharSelectScene()); return; }
    UI.handle(this.items().concat([this.backBtn()]));
  }
  backBtn() { const S = G.S; return { x: 10 * S, y: G.H - 30 * S, w: 70 * S, h: 20 * S, label: '◀ 뒤로', on: () => Game.go(() => new CharSelectScene()) }; }
  draw(t) {
    UI.starfield(this.t, '#1a0f30', '#3a1c48');
    const S = G.S;
    G.text('난이도 선택', G.W / 2, 20 * S, 13, '#ffd86a', 'center');
    this.items().forEach((b, i) => UI.button(b, i === UI.sel, this.t));
    UI.button(this.backBtn(), UI.sel === 3, this.t);
    blit((c, x, y) => drawHero(c, this.char, x, y, -1, 'idle', this.t), G.W - 40 * S, 200 * S, S * 2);
    blit((c, x, y) => drawPipi(c, x, y - 30, this.t), G.W - 66 * S, 200 * S, S * 1.6);
    G.text('화면을 눌러 난이도를 고르면 모험이 시작돼요', G.W / 2, 166 * S, 7, '#c8c4f0', 'center', { weight: 600 });
  }
}

// ═════════ 스토리 컷신 ═════════
const NAMES = { pipi: '피피', sage: '현자 오르반', toto: '상인 토토', morvath: '그림자왕 모르바스' };
class StoryScene {
  constructor(lines, opts) {
    this.lines = lines; this.opts = opts; this.i = 0; this.chars = 0; this.t = 0;
    this.right = opts.right || null; this.pipiShown = !opts.pipiLate;
    this.ending = !!opts.ending;
    this.updateActors();
  }
  enter() { Sound.music(this.opts.music || 'story'); }
  get line() { return this.lines[this.i]; }
  updateActors() {
    const ln = this.line;
    if (!ln) return;
    if (ln.who === 'pipi') this.pipiShown = true;
    if (['sage', 'morvath', 'boss', 'toto'].includes(ln.who)) this.right = ln.who;
    this.text = fillText(ln.text);
    this.chars = 0;
  }
  advance() {
    if (this.chars < this.text.length) { this.chars = this.text.length; return; }
    this.i++;
    if (this.i >= this.lines.length) { this.finish(); return; }
    Sound.play('blip');
    this.updateActors();
  }
  finish() { if (this.done) return; this.done = true; this.opts.done(); }
  skipBtn() { const S = G.S; return { x: G.W - 64 * S, y: 6 * S, w: 58 * S, h: 16 * S, label: '건너뛰기 ▶▶', size: 7, silent: true, on: () => { Sound.play('back'); this.finish(); } }; }
  update(dt) {
    this.t += dt;
    if (this.done) return;
    const prev = Math.floor(this.chars);
    this.chars = Math.min(this.text.length, this.chars + dt * 30);
    if (Math.floor(this.chars) !== prev && Math.floor(this.chars) % 3 === 0) Sound.play('blip');
    for (const tp of Input.taps) {
      const b = this.skipBtn();
      if (tp.x >= b.x && tp.y >= b.y && tp.x <= b.x + b.w && tp.y <= b.y + b.h) { b.on(); return; }
      this.advance(); return;
    }
    if (Input.nav.ok || Input._jump) { Input._jump = false; this.advance(); }
    if (Input.nav.back) this.finish();
  }
  draw(t) {
    const c = G.bctx, ln = this.line || this.lines[this.lines.length - 1];
    const bg = this.opts.bg;
    const camX = this.t * 6;
    const GY = 136; // 컷신용 지면 높이 (대화창 위로 올림)
    Backgrounds.draw(c, bg, camX, this.t, G.VW);
    c.save(); c.translate(0, GY - 176); drawGroundBand(c, bg, camX); c.restore();
    R(c, 0, GY + 48, G.VW, VH - GY - 48, THEMES[bg].dirt);
    if (this.ending) {
      const gx = G.VW / 2, gy = 46;
      c.fillStyle = `rgba(255,240,170,${0.25 + Math.sin(this.t * 3) * 0.1})`; c.beginPath(); c.arc(gx, gy, 26, 0, Math.PI * 2); c.fill();
      drawItem(c, 'shard', gx, gy, this.t);
    }
    G.present();
    const S = G.S;
    const narr = ln.who === 'narr';
    if (narr) UI.dim(0.55);
    const k = S * 2, fy = GY * S;
    const hx = G.W * 0.3, rx = G.W * 0.7;
    const talking = (who) => ln.who === who && !narr;
    const bob = (who) => (talking(who) && this.chars < this.text.length ? (Math.floor(this.t * 8) % 2 ? -1 : 0) : 0);
    const al = (who) => (narr ? 0.35 : talking(who) ? 1 : 0.7);
    const run = Flow.run;
    if (!(this.opts.pipiLate && this.i < 4)) blit((cc, x, y) => drawHero(cc, run.char, x, y + bob('hero'), 1, this.ending && this.i >= 3 ? 'win' : 'idle', this.t), hx, fy, k, al('hero'));
    if (this.pipiShown) blit((cc, x, y) => drawPipi(cc, x, y - 34 + bob('pipi'), this.t), hx + 22 * S, fy, k, al('pipi'));
    const r = this.right;
    if (r === 'sage') blit((cc, x, y) => drawSage(cc, x, y + bob('sage'), this.t), rx, fy, k, al('sage'));
    else if (r === 'toto') blit((cc, x, y) => drawToto(cc, x, y + bob('toto'), this.t), rx, fy, k, al('toto'));
    else if (r === 'morvath') blit((cc, x, y) => drawMorvath(cc, x, y + bob('morvath'), this.t, { dir: -1, alpha: 0.95 }), rx, fy, k, al('morvath'));
    else if (r === 'boss' && this.opts.bossStage != null) blit((cc, x, y) => drawBossPortrait(cc, STAGES[this.opts.bossStage].boss, x, y, this.t), rx, fy, k * 0.85, al('boss'));
    // 대화 상자
    const bw = Math.min(G.W - 16 * S, 380 * S), bx = (G.W - bw) / 2, bh = 54 * S, by = G.H - bh - 6 * S;
    if (narr) {
      const ls = G.wrap(this.text.slice(0, Math.floor(this.chars)), bw - 30 * S, 9.5);
      const full = G.wrap(this.text, bw - 30 * S, 9.5);
      const y0 = G.H / 2 - (full.length * 13 * S) / 2;
      ls.forEach((l, i) => G.text(l, G.W / 2, y0 + i * 13 * S, 9.5, '#fff6d8', 'center', { weight: 700 }));
    } else {
      G.panel(bx, by, bw, bh, { fill: 'rgba(14,12,40,0.92)' });
      let name = NAMES[ln.who] || '';
      if (ln.who === 'hero') name = heroName();
      if (ln.who === 'boss') name = STAGES[this.opts.bossStage].bossName;
      const nameCol = { hero: '#8ad8ff', pipi: '#ffe85a', sage: '#a8f0c8', morvath: '#ff8aa8', boss: '#ffb07a', toto: '#ffc890' }[ln.who] || '#fff';
      const nw = G.measure(name, 8) + 16 * S;
      G.panel(bx + 8 * S, by - 9 * S, nw, 15 * S, { fill: '#2a2068', stroke: nameCol, lw: 1.2, r: 4 });
      G.text(name, bx + 8 * S + nw / 2, by - 1.5 * S, 8, nameCol, 'center');
      const ls = G.wrap(this.text.slice(0, Math.floor(this.chars)), bw - 24 * S, 8.5);
      ls.slice(0, 3).forEach((l, i) => G.text(l, bx + 12 * S, by + 16 * S + i * 12 * S, 8.5, '#ffffff', 'left', { weight: 600, outline: false }));
    }
    if (this.chars >= this.text.length && Math.floor(this.t * 3) % 2 === 0) G.text('▼', bx + bw - 12 * S, by + bh - 9 * S, 7, '#ffd86a', 'center');
    const sb = this.skipBtn();
    UI.button(sb, false, this.t);
    G.text(`${Math.min(this.i + 1, this.lines.length)} / ${this.lines.length}`, 10 * S, 13 * S, 6.5, 'rgba(255,255,255,0.7)', 'left', { weight: 600 });
  }
}

// ═════════ 스테이지 시작 카드 ═════════
class StageIntroScene {
  constructor(i, checkpoint) { this.i = i; this.t = 0; this.checkpoint = checkpoint; }
  enter() { Sound.musicStop(); Sound.play('checkpoint'); }
  update(dt) {
    this.t += dt;
    if (this.t > 2.3 || (this.t > 0.6 && (Input.taps.length || Input.nav.ok))) {
      if (!this.gone) { this.gone = true; Game.go(() => new PlayScene(this.i, this.checkpoint), true); }
    }
  }
  draw(t) {
    const c = G.sctx, S = G.S;
    c.fillStyle = '#05030f'; c.fillRect(0, 0, G.W, G.H);
    const st = STAGES[this.i];
    const k = U.easeOutBack(Math.min(1, this.t * 2.2));
    G.text(st.sub, G.W / 2, 68 * S, 11 * k, '#ffd86a', 'center');
    G.text(st.name, G.W / 2, 92 * S, 20 * k, '#ffffff', 'center');
    blit((cc, x, y) => drawHero(cc, Flow.run.char, x, y, 1, 'idle', this.t), G.W / 2 - 18 * S, 150 * S, S * 2);
    G.text('× ' + Flow.run.lives, G.W / 2 + 6 * S, 138 * S, 12, '#ffffff', 'left');
    G.text(DIFFICULTY[Flow.run.diff].name + ' 난이도', G.W / 2, 180 * S, 7, DIFFICULTY[Flow.run.diff].color, 'center');
  }
}

// ═════════ 플레이 ═════════
class PlayScene {
  constructor(i, checkpoint) {
    this.i = i; this.t = 0; this.paused = false; this.respawnT = 0;
    this.world = new World(i, Flow.run, checkpoint);
    Flow.run.carryShield = false; Flow.run.carryCharm = false;
    this.banner = null;
  }
  enter() {
    Input.controls = true;
    Sound.music(STAGES[this.i].music);
    this.signT = 0;
  }
  pauseItems() {
    const S = G.S, w = 150 * S, h = 21 * S, x = (G.W - w) / 2;
    let y = 72 * S;
    const st = Save.settings;
    const list = [
      { label: '계속하기', on: () => this.resume() },
      { label: `소리: ${st.sfx && st.music ? '켜짐' : st.sfx || st.music ? '일부' : '꺼짐'}`, on: () => { const v = !(st.sfx && st.music); st.sfx = v; st.music = v; Save.write(); Sound.applySettings(); } },
      { label: '스테이지 처음부터', sub: '목숨 1개 소모', on: () => { Flow.run.lives--; if (Flow.run.lives <= 0) { Flow.gameOver(); return; } Game.go(() => new StageIntroScene(this.i)); } },
      { label: '타이틀로 나가기', sub: '스테이지 시작 시점까지 저장됨', on: () => Game.go(() => new TitleScene()) },
    ];
    return list.map((b) => { const o = Object.assign({ x, y, w, h: b.sub ? h * 1.25 : h }, b); y += o.h + 5 * S; return o; });
  }
  pause() { if (this.paused || this.world.player.dead) return; this.paused = true; Input.controls = false; Input.resetAll(); Sound.play('pause'); UI.resetSel(0); }
  resume() { this.paused = false; Input.controls = true; Input.clearActions(); }
  update(dt) {
    this.t += dt;
    const w = this.world;
    if (this.paused) {
      if (Input.nav.back) { this.resume(); return; }
      UI.handle(this.pauseItems());
      return;
    }
    if (Input.pausePressed()) { this.pause(); return; }
    w.update(dt);
    for (const ev of w.events) {
      if (ev.type === 'bossIntro') this.banner = { kind: 'boss', t: 0 };
      if (ev.type === 'clear') this.banner = { kind: 'clear', t: 0 };
    }
    w.events.length = 0;
    if (this.banner) { this.banner.t += dt; if (this.banner.kind === 'boss' && this.banner.t > 2.2) this.banner = null; }
    const p = w.player;
    if (p.dead && p.deadT > 2.3 && !this.handled) {
      this.handled = true;
      Flow.run.lives--;
      if (Flow.run.lives <= 0) Flow.gameOver();
      else { const cp = w.checkpoint; Game.go(() => new StageIntroScene(this.i, cp)); }
    }
    if (w.clearT > 3.3 && !this.handled) {
      this.handled = true;
      const s = w.stats;
      Flow.stageClear({ kills: s.kills, coins: s.coins, time: s.time, damage: s.damage, stage: this.i });
    }
  }
  draw(t) {
    const w = this.world, S = G.S;
    w.draw(G.bctx);
    G.present();
    // 떠오르는 점수 글자
    for (const tx of w.texts) {
      const sx = (tx.x - w.cam.x) * S, sy = tx.y * S;
      G.text(tx.text, sx, sy, 6.5, tx.col, 'center', { alpha: 1 - tx.t / 0.9 });
    }
    // 표지판 말풍선
    const p = w.player;
    for (const s of w.signs) {
      if (s.text && Math.abs(p.cx - s.x) < 34) {
        const bw = Math.min(G.W * 0.7, G.measure(s.text, 8) + 24 * S), bx = (G.W - bw) / 2, by = 46 * S;
        G.panel(bx, by, bw, 20 * S, { fill: 'rgba(255,248,225,0.95)', stroke: '#8a5a2a', lw: 2 });
        G.text(s.text, G.W / 2, by + 10.5 * S, 8, '#3a2410', 'center', { outline: false });
      }
    }
    if (!this.paused) drawHUD(w, this.t);
    if (!this.paused && !p.dead && w.clearT < 0) drawTouchControls(this.t);
    if (this.banner) {
      const b = this.banner;
      if (b.kind === 'boss') {
        const a = Math.min(1, b.t * 3) * Math.min(1, (2.2 - b.t) * 3);
        G.sctx.fillStyle = `rgba(80,0,20,${0.45 * a})`; G.sctx.fillRect(0, 70 * S, G.W, 60 * S);
        if (Math.floor(b.t * 6) % 2 === 0) G.text('⚠ WARNING ⚠', G.W / 2, 84 * S, 12, '#ff4a5a', 'center', { alpha: a });
        G.text(w.level.stage.bossName, G.W / 2, 103 * S, 15, '#ffffff', 'center', { alpha: a });
        G.text('「' + w.level.stage.bossLine + '」', G.W / 2, 120 * S, 8, '#ffc0c8', 'center', { alpha: a });
      } else {
        const k = U.easeOutBack(Math.min(1, b.t * 2));
        G.text('STAGE CLEAR!', G.W / 2, 80 * S, 22 * k, '#ffe85a', 'center');
        if (b.t > 0.6) G.text(`별조각 ${this.i + 1} / 6 획득!`, G.W / 2, 104 * S, 10, '#bff4ff', 'center');
      }
    }
    if (p.dead && p.deadT > 0.8 && Flow.run.lives - 1 <= 0) G.text('GAME OVER', G.W / 2, G.H / 2, 20, '#ff5a6a', 'center', { alpha: Math.min(1, p.deadT - 0.8) });
    if (this.paused) {
      UI.dim(0.7);
      G.text('일시 정지', G.W / 2, 40 * S, 16, '#ffd86a', 'center');
      G.text(`${STAGES[this.i].sub} · ${STAGES[this.i].name}`, G.W / 2, 58 * S, 8, '#d8d4ff', 'center', { weight: 600 });
      this.pauseItems().forEach((b, i) => UI.button(b, i === UI.sel, this.t));
    }
  }
}

// ═════════ 스테이지 결과 ═════════
class ResultScene {
  constructor(stats, next) {
    this.stats = stats; this.next = next; this.t = 0;
    const timeBonus = Math.max(0, Math.round((240 - stats.time) * 20));
    const noDmg = stats.damage === 0 ? 3000 : 0;
    this.rows = [
      ['물리친 적', `${stats.kills}`, stats.kills * 100],
      ['모은 코인', `${stats.coins}`, stats.coins * 20],
      ['클리어 시간', `${Math.floor(stats.time / 60)}:${U.fmt(stats.time % 60, 2)}`, timeBonus],
      ['무피해 보너스', stats.damage === 0 ? '달성!' : `피해 ${stats.damage}`, noDmg],
    ];
    this.bonus = this.rows.reduce((s, r) => s + r[2], 0);
    this.applied = false;
  }
  enter() { Sound.jingle('clear'); }
  update(dt) {
    this.t += dt;
    if (!this.applied && this.t > 0.3) { this.applied = true; Flow.run.score += this.bonus; }
    if (this.t > 1.2 && (Input.taps.length || Input.nav.ok)) { if (!this.gone) { this.gone = true; Sound.play('confirm'); this.next(); } }
  }
  draw(t) {
    UI.starfield(this.t, '#0f1a3a', '#2a3a6a');
    const S = G.S;
    G.text(`${STAGES[this.stats.stage].sub} 클리어!`, G.W / 2, 20 * S, 15, '#ffe85a', 'center');
    blit((c, x, y) => drawItem(c, 'shard', x, y - 14, this.t), G.W / 2, 68 * S, S * 1.25);
    const w = Math.min(260 * S, G.W - 30 * S), x = (G.W - w) / 2;
    G.panel(x, 82 * S, w, 96 * S);
    this.rows.forEach((r, i) => {
      const show = this.t > 0.4 + i * 0.25;
      if (!show) return;
      const y = 96 * S + i * 15 * S;
      G.text(r[0], x + 14 * S, y, 8.5, '#d8d4ff', 'left');
      G.text(r[1], x + w * 0.55, y, 8.5, '#ffffff', 'center');
      G.text('+' + r[2], x + w - 14 * S, y, 8.5, '#ffe85a', 'right');
    });
    if (this.t > 1.4) {
      G.text('총점', x + 14 * S, 164 * S, 10, '#ffd86a', 'left');
      G.text(U.fmt(Flow.run.score, 7), x + w - 14 * S, 164 * S, 11, '#ffffff', 'right');
    }
    if (this.t > 1.2 && Math.floor(this.t * 2) % 2 === 0) G.text('화면을 터치해서 계속', G.W / 2, 206 * S, 8, '#ffffff', 'center');
  }
}

// ═════════ 상점 ═════════
class ShopScene {
  constructor() { this.t = 0; this.msg = '어서 와! 떠돌이 상인 토토의 가게야. 코인만 있으면 뭐든 팔지!'; this.msgT = 0; }
  enter() { Sound.music('shop'); UI.resetSel(0); }
  owned(it) {
    const run = Flow.run;
    if (it.id === 'heartc') return run.hpBonus >= it.max;
    if (it.id === 'shield') return run.carryShield;
    if (it.id === 'charm') return run.carryCharm;
    return false;
  }
  items() {
    const S = G.S, run = Flow.run;
    const w = Math.min(196 * S, G.W * 0.55), h = 30 * S, x = G.W - w - 12 * S;
    let y = 30 * S;
    const list = SHOP_ITEMS.map((it) => {
      const own = this.owned(it);
      const o = {
        x, y, w, h, it, own, silent: true,
        on: () => {
          if (own) { Sound.play('deny'); this.say('그건 이미 충분히 갖고 있잖아!'); return; }
          if (run.coins < it.price) { Sound.play('deny'); this.say('코인이 부족해… 스테이지에서 더 모아 와!'); return; }
          run.coins -= it.price; Sound.play('buy');
          if (it.id === 'life') run.lives++;
          if (it.id === 'heartc') run.hpBonus++;
          if (it.id === 'shield') run.carryShield = true;
          if (it.id === 'charm') run.carryCharm = true;
          Save.setRun(run);
          this.say(U.pick(['고마워! 좋은 선택이야!', '탁월한 안목인걸!', '이거 하나면 든든할 거야!']));
        },
      };
      y += h + 5 * S;
      return o;
    });
    list.push({ x, y: y + 2 * S, w, h: 22 * S, label: '출발! ▶', color: '#7af0a0', color2: '#2ab86a', go: true, on: () => Flow.startStage(Flow.run.stage) });
    return list;
  }
  say(m) { this.msg = m; this.msgT = 0; }
  update(dt) { this.t += dt; this.msgT += dt; if (Input.nav.back) return; UI.handle(this.items()); }
  draw(t) {
    const c = G.bctx, S = G.S;
    const prev = STAGES[Math.max(0, Flow.run.stage - 1)].theme;
    Backgrounds.draw(c, prev, 0, this.t, G.VW);
    drawGroundBand(c, prev, 0);
    // 노점
    const sx = 70;
    R(c, sx - 34, 132, 68, 44, '#8a5a2a'); R(c, sx - 34, 132, 68, 3, '#a8743e');
    for (let i = 0; i < 6; i++) R(c, sx - 38 + i * 13, 112, 13, 14, i % 2 ? '#ffffff' : '#e84a5a');
    R(c, sx - 38, 124, 78, 3, '#c83a4a'); R(c, sx - 36, 126, 2, 50, '#6a4420'); R(c, sx + 34, 126, 2, 50, '#6a4420');
    drawItem(c, 'heart', sx - 20, 142, this.t); drawItem(c, 'shield', sx, 142, this.t); drawItem(c, 'power', sx + 20, 142, this.t);
    drawToto(c, sx + 2, 176, this.t);
    drawHero(c, Flow.run.char, sx + 60, 176, -1, 'idle', this.t);
    drawPipi(c, sx + 78, 146, this.t);
    G.present();
    G.text('떠돌이 상점', 14 * S, 14 * S, 12, '#ffd86a', 'left');
    blitIcon('coin', 18 * S, 30 * S, S * 0.9);
    G.text(String(Flow.run.coins), 26 * S, 30 * S, 10, '#ffe85a', 'left');
    G.text(`목숨 ×${Flow.run.lives}`, 70 * S, 30 * S, 8, '#ffffff', 'left');
    // 대사
    const bw = Math.min(150 * S, G.W * 0.4);
    const ls = G.wrap(this.msg, bw - 14 * S, 7.5);
    G.panel(10 * S, 40 * S, bw, (ls.length * 10 + 10) * S, { fill: 'rgba(255,248,225,0.95)', stroke: '#8a5a2a', lw: 2 });
    ls.forEach((l, i) => G.text(l, 17 * S, 50 * S + i * 10 * S, 7.5, '#3a2410', 'left', { outline: false }));
    this.items().forEach((b, i) => {
      const sel = i === UI.sel;
      if (b.go) { UI.button(b, sel, this.t); return; }
      const it = b.it, afford = Flow.run.coins >= it.price;
      G.panel(b.x, b.y, b.w, b.h, { fill: sel ? 'rgba(70,50,140,0.95)' : 'rgba(20,16,50,0.88)', stroke: sel ? '#ffd86a' : 'rgba(255,255,255,0.3)', lw: sel ? 2 : 1 });
      blitIcon(it.icon, b.x + 15 * S, b.y + b.h / 2, S * 1.1);
      G.text(it.name, b.x + 30 * S, b.y + 10 * S, 8.5, '#ffffff', 'left');
      G.text(it.desc, b.x + 30 * S, b.y + 21 * S, 6.2, '#c8c4f0', 'left', { weight: 600, outline: false });
      const pc = b.own ? '#8a88a0' : afford ? '#ffe85a' : '#ff6a7a';
      G.text(b.own ? '보유' : String(it.price), b.x + b.w - 10 * S, b.y + 10 * S, 9, pc, 'right');
      if (!b.own) blitIcon('coin', b.x + b.w - 10 * S - G.measure(String(it.price), 9) - 6 * S, b.y + 10 * S, S * 0.7);
    });
  }
}

// ═════════ 게임 오버 ═════════
class GameOverScene {
  constructor() { this.t = 0; }
  enter() { Sound.jingle('gameover'); UI.resetSel(0); }
  items() {
    const S = G.S, w = 170 * S, h = 26 * S, x = (G.W - w) / 2;
    return [
      { x, y: 120 * S, w, h, label: '이어하기', sub: '스테이지 처음부터 · 코인 절반', on: () => Flow.retryStage() },
      { x, y: 154 * S, w, h: 21 * S, label: '타이틀로', on: () => Game.go(() => new TitleScene()) },
    ];
  }
  update(dt) { this.t += dt; if (this.t > 1) UI.handle(this.items()); }
  draw(t) {
    UI.starfield(this.t, '#1a0410', '#3a0820');
    const S = G.S;
    const k = U.easeOutBack(Math.min(1, this.t * 1.5));
    G.text('GAME OVER', G.W / 2, 34 * S, 24 * k, '#ff5a6a', 'center');
    blit((c, x, y) => drawHero(c, Flow.run.char, x, y, 1, 'hurt', 0), G.W / 2, 112 * S, S * 2);
    G.text(`점수 ${U.fmt(Flow.run.score, 7)}`, G.W / 2, 56 * S, 9, '#ffffff', 'center');
    if (this.t > 1) this.items().forEach((b, i) => UI.button(b, i === UI.sel, this.t));
  }
}

// ═════════ 크레딧 / 엔딩 ═════════
class CreditsScene {
  constructor() {
    this.t = 0;
    const run = Flow.run;
    Save.record(run.diff, run.char, run.score);
    Save.clearRun();
  }
  enter() { Sound.music('ending'); }
  update(dt) {
    this.t += dt;
    if (this.t > 4 && (Input.taps.length || Input.nav.ok)) { if (!this.gone) { this.gone = true; Game.go(() => new TitleScene()); } }
  }
  draw(t) {
    UI.starfield(this.t, '#0c1640', '#3a2a78');
    const S = G.S, run = Flow.run;
    const lines = [
      ['별조각 퀘스트', 18, '#ffe85a'], ['STARSHARD QUEST', 9, '#bfe8ff'], ['', 8],
      ['— 함께한 영웅 —', 9, '#ffd86a'], [`${CHARACTERS[run.char].name} · ${CHARACTERS[run.char].title}`, 10, '#ffffff'], ['', 8],
      ['— 기록 —', 9, '#ffd86a'], [`난이도 ${DIFFICULTY[run.diff].name}`, 9, '#ffffff'], [`최종 점수 ${U.fmt(run.score, 7)}`, 10, '#ffffff'], ['', 8],
      ['기획 · 프로그래밍 · 그래픽 · 음악', 8, '#c8c4f0'], ['모두 코드로 직접 만든 오리지널 게임', 8, '#c8c4f0'], ['', 8],
      ['플레이해 주셔서 감사합니다!', 11, '#ffe85a'], ['', 8], ['THE END', 16, '#ffffff'],
    ];
    let y = G.H - this.t * 26 * S;
    const endY = G.H * 0.3;
    const totalH = lines.reduce((s, l) => s + (l[1] + 8) * S, 0);
    if (y + totalH < endY + totalH * 0.6) y = endY + totalH * 0.6 - totalH;
    for (const [txt, size, col] of lines) {
      if (txt) G.text(txt, G.W / 2, y, size, col, 'center');
      y += (size + 8) * S;
    }
    blit((c, x, yy) => drawHero(c, run.char, x, yy, 1, 'win', this.t), G.W * 0.15, 200 * S, S * 2);
    blit((c, x, yy) => drawPipi(c, x, yy - 30, this.t), G.W * 0.85, 190 * S, S * 2);
    if (this.t > 4 && Math.floor(this.t * 2) % 2 === 0) G.text('화면을 터치해서 타이틀로', G.W / 2, G.H - 10 * S, 7, '#ffffff', 'center');
  }
}
