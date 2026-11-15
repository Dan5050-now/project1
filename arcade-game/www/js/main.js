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

  let last = performance.now(), acc = 0;
  function frame(now) {
    let dt = (now - last) / 1000;
    last = now;
    if (dt > 0.1) dt = 0.1;
    acc += dt;
    Input.poll();
    let first = true;
    while (acc >= STEP) {
      Game.update(STEP);
      acc -= STEP;
      if (first) { Input.endFrame(); first = false; }
    }
    Game.draw();
    requestAnimationFrame(frame);
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
