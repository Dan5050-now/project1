'use strict';
// ─────────────────────────────────────────────────────────────
//  main.js — 시작, 메인 루프, 앱 생명주기(백그라운드/뒤로가기)
// ─────────────────────────────────────────────────────────────

(function boot() {
  Save.load();
  G.init();
  Input.init(G.screen);
  Input.layout();
  Game.set(new TitleScene());

  // ─── 오류 복구 장치 ───
  // 예전에는 한 번의 오류로 다음 프레임 예약이 끊겨 화면·조작이 모두 멈췄다.
  // 이제는 오류가 나도 루프는 계속 돌고, 같은 장면에서 오류가 반복되면 안전한 곳으로 빠져나온다.
  const Recover = { scene: null, count: 0, toastT: 0 };
  function resetCanvas(c) {
    try {
      if (c.reset) c.reset(); else { c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; }
      c.imageSmoothingEnabled = false;
    } catch (e) { /* 무시 */ }
  }
  function onError(e, where) {
    console.error('[게임 오류]', where, e);
    resetCanvas(G.sctx); resetCanvas(G.bctx);
    if (Game.scene !== Recover.scene) { Recover.scene = Game.scene; Recover.count = 0; }
    Recover.count++;
    Recover.toastT = 2.5;
    if (Recover.count >= 20) {
      Recover.count = 0;
      const s = Game.scene;
      try {
        if (s instanceof StoryScene && !s.done) s.finish();   // 대화 장면이면 다음 장면으로
        else Game.set(new TitleScene());                       // 그 밖에는 타이틀로 (진행은 스테이지 시작 시점에 저장됨)
      } catch (e2) { Game.scene = new TitleScene(); }
    }
  }

  let last = performance.now(), acc = 0;
  function frame(now) {
    requestAnimationFrame(frame);   // 다음 프레임을 먼저 예약 → 오류가 나도 루프가 끊기지 않음
    let dt = (now - last) / 1000;
    last = now;
    if (dt > 0.1) dt = 0.1;
    if (dt < 0) dt = 0;
    acc += dt;
    Input.poll();
    let first = true;
    while (acc >= STEP) {
      try { Game.update(STEP); } catch (e) { onError(e, 'update'); }
      acc -= STEP;
      if (first) { Input.endFrame(); first = false; }
    }
    try { Game.draw(); } catch (e) { onError(e, 'draw'); }
    if (Recover.toastT > 0) {
      Recover.toastT -= dt;
      try { G.text('⚠ 일시적인 오류를 자동 복구했어요', 8 * G.S, G.H - 8 * G.S, 6.5, '#ffd86a', 'left', { alpha: Math.min(1, Recover.toastT) }); } catch (e) { /* 무시 */ }
    }
  }
  requestAnimationFrame(frame);

  // 앱이 백그라운드로 가면 자동 일시정지 + 소리 정지
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      if (Game.scene instanceof PlayScene) Game.scene.pause();
      Sound.suspend();
    } else Sound.resume();
  });

  // 안드로이드 뒤로가기 버튼 (Capacitor App 플러그인)
  const App = window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.App;
  if (App && App.addListener) {
    App.addListener('backButton', () => {
      const s = Game.scene;
      if (s instanceof PlayScene) { if (s.paused) s.resume(); else s.pause(); }
      else if (s instanceof TitleScene) {
        if (s.modal) s.modal = null;
        else if (s.mode === 'menu') { if (s.exitArmed) App.exitApp(); else { s.exitArmed = true; setTimeout(() => { s.exitArmed = false; }, 2000); } }
        else App.exitApp();
      } else Input.nav.back = true;
    });
  }
  // 화면 꺼짐 방지는 네이티브(MainActivity)에서 처리
  window.__game = { Game, Flow, Save };
})();
