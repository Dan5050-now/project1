'use strict';
// ─────────────────────────────────────────────────────────────
//  audio.js — WebAudio 합성 효과음 + 자동 작곡 배경음악
//  (외부 음원 파일 없이 코드로 소리를 만든다)
// ─────────────────────────────────────────────────────────────

const Sound = {
  ctx: null, master: null, sfxBus: null, musBus: null, noiseBuf: null,
  song: null, songName: null, step: 0, nextTime: 0, timer: null,

  init() {
    if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    this.ctx = new AC();
    this.master = this.ctx.createGain(); this.master.gain.value = 0.9;
    this.master.connect(this.ctx.destination);
    this.sfxBus = this.ctx.createGain(); this.sfxBus.gain.value = 0.55; this.sfxBus.connect(this.master);
    this.musBus = this.ctx.createGain(); this.musBus.gain.value = 0.3; this.musBus.connect(this.master);
    const len = this.ctx.sampleRate;
    this.noiseBuf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    const d = this.noiseBuf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    this.timer = setInterval(() => this.schedule(), 25);
    this.applySettings();
  },
  suspend() { if (this.ctx && this.ctx.state === 'running') this.ctx.suspend(); },
  resume() { if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume(); },
  applySettings() {
    if (!this.ctx) return;
    this.sfxBus.gain.value = Save.settings.sfx ? 0.55 : 0;
    this.musBus.gain.value = Save.settings.music ? 0.3 : 0;
  },

  // ─── 기본 음원 ───
  tone(type, f0, f1, dur, vol, when = 0, bus = this.sfxBus, attack = 0.005) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime + when;
    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(Math.max(20, f0), t);
    if (f1 && f1 !== f0) o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(bus);
    o.start(t); o.stop(t + dur + 0.02);
  },
  noise(dur, vol, freq = 2000, when = 0, ftype = 'lowpass', bus = this.sfxBus, f1 = 0) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime + when;
    const s = this.ctx.createBufferSource();
    s.buffer = this.noiseBuf;
    const f = this.ctx.createBiquadFilter();
    f.type = ftype; f.frequency.setValueAtTime(freq, t);
    if (f1) f.frequency.exponentialRampToValueAtTime(f1, t + dur);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(bus);
    s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.02);
  },
  seq(notes, stepDur, type = 'square', vol = 0.18) {
    // notes: [midi|null,...]
    notes.forEach((n, i) => {
      if (n == null) return;
      const f = midiFreq(n);
      this.tone(type, f, f, stepDur * 0.95, vol, i * stepDur);
    });
  },

  // ─── 효과음 ───
  play(name) {
    if (!this.ctx || !Save.settings.sfx) return;
    switch (name) {
      case 'jump': this.tone('square', 260, 620, 0.14, 0.16); break;
      case 'djump': this.tone('square', 420, 900, 0.12, 0.14); this.tone('triangle', 840, 1400, 0.1, 0.08, 0.03); break;
      case 'swim': this.tone('sine', 300, 520, 0.12, 0.12); this.noise(0.08, 0.05, 1800, 0, 'bandpass'); break;
      case 'sword': this.noise(0.12, 0.22, 3500, 0, 'bandpass', this.sfxBus, 900); break;
      case 'kick': this.noise(0.08, 0.2, 1800, 0, 'bandpass', this.sfxBus, 600); this.tone('square', 180, 90, 0.08, 0.1); break;
      case 'magic': this.tone('triangle', 900, 1600, 0.12, 0.14); this.tone('sine', 1350, 2200, 0.1, 0.07, 0.02); break;
      case 'coin': this.tone('square', 988, 988, 0.06, 0.12); this.tone('square', 1319, 1319, 0.16, 0.12, 0.06); break;
      case 'break': this.noise(0.18, 0.35, 1200, 0, 'lowpass', this.sfxBus, 200); this.tone('square', 150, 60, 0.12, 0.12); break;
      case 'bump': this.tone('square', 140, 90, 0.07, 0.12); break;
      case 'hurt': this.tone('sawtooth', 520, 140, 0.25, 0.2); this.noise(0.12, 0.12, 900); break;
      case 'stomp': this.tone('square', 320, 120, 0.1, 0.18); this.noise(0.06, 0.12, 800); break;
      case 'hit': this.tone('square', 600, 200, 0.07, 0.14); this.noise(0.05, 0.12, 2500, 0, 'highpass'); break;
      case 'defeat': this.tone('square', 700, 90, 0.2, 0.15); this.noise(0.2, 0.2, 1500, 0, 'lowpass', this.sfxBus, 100); break;
      case 'clink': this.tone('triangle', 1600, 1200, 0.08, 0.12); break;
      case 'power': [0, 4, 7, 12, 16].forEach((s, i) => this.tone('square', midiFreq(67 + s), 0, 0.08, 0.12, i * 0.06)); break;
      case 'heart': this.tone('sine', 660, 990, 0.2, 0.18); this.tone('sine', 990, 1320, 0.2, 0.12, 0.1); break;
      case 'oneup': [76, 79, 88, 84, 86, 91].forEach((n, i) => this.tone('square', midiFreq(n), 0, 0.09, 0.12, i * 0.08)); break;
      case 'shield': this.tone('triangle', 400, 1200, 0.3, 0.16); break;
      case 'shieldbreak': this.noise(0.3, 0.25, 4000, 0, 'highpass'); this.tone('triangle', 1200, 300, 0.25, 0.12); break;
      case 'select': this.tone('square', 880, 880, 0.05, 0.1); break;
      case 'confirm': this.tone('square', 660, 660, 0.06, 0.12); this.tone('square', 990, 990, 0.12, 0.12, 0.06); break;
      case 'back': this.tone('square', 500, 300, 0.1, 0.1); break;
      case 'buy': this.tone('square', 784, 784, 0.06, 0.12); this.tone('square', 1046, 1046, 0.06, 0.12, 0.07); this.tone('square', 1568, 1568, 0.14, 0.12, 0.14); break;
      case 'deny': this.tone('square', 220, 200, 0.18, 0.14); break;
      case 'blip': this.tone('square', 1200, 1200, 0.02, 0.04); break;
      case 'shot': this.tone('square', 900, 400, 0.08, 0.08); break;
      case 'fire': this.noise(0.25, 0.18, 900, 0, 'lowpass', this.sfxBus, 300); break;
      case 'boom': this.noise(0.5, 0.45, 900, 0, 'lowpass', this.sfxBus, 60); this.tone('sine', 120, 35, 0.45, 0.35); break;
      case 'thunder': this.noise(0.6, 0.45, 3000, 0, 'lowpass', this.sfxBus, 100); break;
      case 'bosshit': this.tone('square', 220, 110, 0.12, 0.2); this.noise(0.08, 0.2, 3000, 0, 'highpass'); break;
      case 'roar': this.tone('sawtooth', 160, 70, 0.6, 0.22); this.noise(0.6, 0.18, 600, 0, 'lowpass', this.sfxBus, 200); break;
      case 'checkpoint': [72, 76, 79, 84].forEach((n, i) => this.tone('triangle', midiFreq(n), 0, 0.12, 0.16, i * 0.07)); break;
      case 'die': this.musicStop(); this.seq([79, 78, 77, null, 72, 71, 70, null, 64, null, 60], 0.09, 'square', 0.16); break;
      case 'crumble': this.noise(0.25, 0.15, 600, 0, 'lowpass'); break;
      case 'splash': this.noise(0.25, 0.2, 1500, 0, 'bandpass', this.sfxBus, 400); break;
      case 'teleport': this.tone('sine', 300, 1500, 0.25, 0.14); this.tone('sine', 1500, 300, 0.25, 0.1, 0.12); break;
      case 'shard': [72, 76, 79, 84, 88, 91, 96].forEach((n, i) => this.tone('triangle', midiFreq(n), 0, 0.25, 0.14, i * 0.07)); break;
      case 'pause': this.tone('square', 660, 660, 0.06, 0.1); this.tone('square', 440, 440, 0.08, 0.1, 0.07); break;
    }
  },
  jingle(name) {
    if (!this.ctx) return;
    this.musicStop();
    if (!Save.settings.music) return;
    const J = {
      clear: [[72, 76, 79, 84, null, 79, 84, null, 88, 88, 88, null], 0.1],
      gameover: [[67, null, 64, null, 60, null, 62, 60, 59, null, 55, null, null, 48], 0.16],
      fanfare: [[67, 67, 67, 72, null, null, 71, null, 72, null, 76, 79, 76, 84], 0.11],
    };
    const [notes, sd] = J[name];
    notes.forEach((n, i) => {
      if (n == null) return;
      const f = midiFreq(n);
      this.tone('square', f, f, sd * 0.95, 0.16, i * sd, this.musBus);
      this.tone('triangle', f / 2, f / 2, sd * 0.95, 0.2, i * sd, this.musBus);
    });
  },

  // ─── 배경음악 ───
  music(name) {
    if (this.songName === name && this.song) return;
    this.songName = name;
    this.song = SONGS[name] ? buildSong(SONGS[name]) : null;
    this.step = 0;
    if (this.ctx) this.nextTime = this.ctx.currentTime + 0.08;
  },
  musicStop() { this.song = null; this.songName = null; },

  schedule() {
    if (!this.ctx || !this.song || this.ctx.state !== 'running') return;
    const sd = 60 / this.song.bpm / 2; // 8분음표 길이
    if (this.nextTime < this.ctx.currentTime - 0.3) this.nextTime = this.ctx.currentTime + 0.05;
    while (this.nextTime < this.ctx.currentTime + 0.12) {
      this.playStep(this.step, this.nextTime - this.ctx.currentTime, sd);
      this.step = (this.step + 1) % this.song.length;
      this.nextTime += sd;
    }
  },
  playStep(step, when, sd) {
    const s = this.song;
    const lead = s.lead[step];
    if (lead) {
      const f = midiFreq(lead.n);
      this.tone(s.leadWave, f, f, sd * lead.len * 0.92, 0.1, when, this.musBus, 0.01);
      if (s.echo) this.tone(s.leadWave, f, f, sd * lead.len * 0.8, 0.035, when + sd * 1.5, this.musBus, 0.01);
    }
    const b = s.bass[step];
    if (b) { const f = midiFreq(b.n); this.tone('triangle', f, f, sd * b.len * 0.95, 0.28, when, this.musBus, 0.005); }
    const arp = s.arp && s.arp[step];
    if (arp) { const f = midiFreq(arp); this.tone('sine', f, f, sd * 0.45, 0.05, when, this.musBus); this.tone('sine', midiFreq(arp + 7), 0, sd * 0.4, 0.035, when + sd / 2, this.musBus); }
    const d = s.drums[step % s.drums.length];
    if (d & 1) this.tone('sine', 150, 45, 0.12, 0.35, when, this.musBus);
    if (d & 2) this.noise(0.1, 0.16, 1800, when, 'bandpass', this.musBus);
    if (d & 4) this.noise(0.03, 0.06, 7000, when, 'highpass', this.musBus);
  },
};

function midiFreq(n) { return 440 * Math.pow(2, (n - 69) / 12); }

// ─── 자동 작곡: 화성 진행 위에 규칙 기반으로 멜로디를 만든다 ───
const SCALES = {
  major: [0, 2, 4, 5, 7, 9, 11],
  minor: [0, 2, 3, 5, 7, 8, 10],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  harmonic: [0, 2, 3, 5, 7, 8, 11],
  mixo: [0, 2, 4, 5, 7, 9, 10],
};
const RHYTHMS = [
  [1, 0, 1, 1, 1, 0, 1, 0], [1, 1, 1, 0, 1, 0, 1, 1], [1, 0, 0, 1, 1, 0, 1, 0],
  [1, 0, 1, 0, 1, 1, 1, 0], [1, 1, 0, 1, 1, 0, 1, 0], [1, 0, 1, 1, 0, 1, 1, 0],
  [1, 0, 0, 0, 1, 0, 1, 1], [1, 1, 1, 1, 1, 0, 1, 0],
];
const CALM_RHYTHMS = [[1, 0, 0, 0, 1, 0, 1, 0], [1, 0, 1, 0, 1, 0, 0, 0], [1, 0, 0, 1, 1, 0, 0, 0], [1, 0, 0, 0, 0, 0, 1, 0]];

const SONGS = {
  title:   { seed: 11, bpm: 118, root: 60, scale: 'major', progA: [0, 5, 3, 4], progB: [3, 4, 2, 5], bass: 'drive', drums: [1, 4, 6, 4, 1, 4, 6, 4], wave: 'square', echo: true },
  forest:  { seed: 23, bpm: 132, root: 62, scale: 'major', progA: [0, 3, 4, 0], progB: [5, 3, 1, 4], bass: 'bounce', drums: [1, 4, 6, 4, 1, 1, 6, 4], wave: 'square' },
  cave:    { seed: 37, bpm: 108, root: 57, scale: 'dorian', progA: [0, 6, 5, 6], progB: [3, 0, 3, 4], bass: 'walk', drums: [1, 0, 4, 0, 2, 0, 4, 0], wave: 'triangle', arp: true, echo: true },
  sea:     { seed: 41, bpm: 96, root: 63, scale: 'major', progA: [0, 2, 3, 4], progB: [5, 2, 3, 4], bass: 'calm', drums: [1, 0, 4, 0, 0, 4, 4, 0], wave: 'sine', calm: true, arp: true, echo: true },
  desert:  { seed: 53, bpm: 124, root: 57, scale: 'harmonic', progA: [0, 0, 5, 4], progB: [3, 5, 4, 4], bass: 'walk', drums: [1, 4, 2, 4, 1, 1, 2, 4], wave: 'square' },
  sky:     { seed: 67, bpm: 140, root: 64, scale: 'mixo', progA: [0, 6, 3, 0], progB: [3, 6, 4, 4], bass: 'drive', drums: [1, 4, 6, 4, 1, 4, 6, 6], wave: 'square', echo: true },
  castle:  { seed: 79, bpm: 128, root: 55, scale: 'harmonic', progA: [0, 5, 3, 4], progB: [0, 6, 5, 4], bass: 'drive', drums: [1, 4, 2, 4, 1, 1, 2, 4], wave: 'sawtooth' },
  boss:    { seed: 97, bpm: 156, root: 57, scale: 'minor', progA: [0, 0, 5, 6], progB: [3, 4, 0, 4], bass: 'drive', drums: [1, 4, 2, 4, 1, 4, 2, 6], wave: 'square' },
  final:   { seed: 113, bpm: 164, root: 52, scale: 'harmonic', progA: [0, 1, 0, 4], progB: [5, 1, 4, 4], bass: 'drive', drums: [1, 6, 2, 6, 1, 1, 2, 6], wave: 'sawtooth' },
  shop:    { seed: 131, bpm: 104, root: 65, scale: 'major', progA: [0, 3, 0, 4], progB: [3, 3, 0, 4], bass: 'bounce', drums: [1, 0, 2, 0, 1, 0, 2, 4], wave: 'triangle', calm: true },
  story:   { seed: 149, bpm: 88, root: 62, scale: 'major', progA: [0, 5, 3, 4], progB: [3, 0, 3, 4], bass: 'calm', drums: [0, 0, 0, 0, 0, 0, 0, 0], wave: 'triangle', calm: true, arp: true, echo: true },
  dark:    { seed: 151, bpm: 80, root: 50, scale: 'harmonic', progA: [0, 5, 0, 4], progB: [5, 3, 1, 4], bass: 'calm', drums: [1, 0, 0, 0, 0, 0, 0, 0], wave: 'triangle', calm: true, arp: true },
  ending:  { seed: 167, bpm: 100, root: 60, scale: 'major', progA: [0, 4, 5, 3], progB: [0, 4, 3, 4], bass: 'bounce', drums: [1, 4, 2, 4, 1, 4, 2, 4], wave: 'square', echo: true, arp: true },
};

function buildSong(def) {
  const rnd = U.rng(def.seed * 7919);
  const scale = SCALES[def.scale];
  const deg2midi = (deg, base) => {
    const oct = Math.floor(deg / 7);
    const d = ((deg % 7) + 7) % 7;
    return base + oct * 12 + scale[d];
  };
  let prev = 7; // 현재 음계 위치 (도 기준 한 옥타브 위)
  const makeBar = (chord, final) => {
    const pool = def.calm ? CALM_RHYTHMS : RHYTHMS;
    const rh = final ? [1, 0, 1, 0, 1, 0, 0, 0] : pool[Math.floor(rnd() * pool.length)];
    const notes = [];
    const chordTones = [chord, chord + 2, chord + 4].map((c) => c + 7);
    for (let i = 0; i < 8; i++) {
      if (!rh[i]) continue;
      let deg;
      if (i === 0 || i === 4) {
        // 강박: 화음 구성음 중 가장 가까운 음
        let best = chordTones[0], bd = 99;
        for (const ct of chordTones) for (const o of [-7, 0, 7]) {
          const c = ct + o;
          const dd = Math.abs(c - prev) + rnd() * 1.5;
          if (dd < bd && c >= 3 && c <= 14) { bd = dd; best = c; }
        }
        deg = best;
      } else {
        const stepv = [-2, -1, -1, 1, 1, 2, 0][Math.floor(rnd() * 7)];
        deg = U.clamp(prev + stepv, 3, 14);
      }
      if (final && i === 4) deg = 7; // 프레이즈 끝은 으뜸음
      prev = deg;
      let len = 1;
      while (i + len < 8 && !rh[i + len]) len++;
      notes.push({ i, n: deg2midi(deg, def.root), len: final && i === 4 ? 4 : len });
    }
    return notes;
  };
  const phrase = (prog, endFinal) => prog.map((c, k) => makeBar(c, endFinal && k === 3));
  const A = phrase(def.progA, false);
  const A2 = A.slice(0, 3).concat([makeBar(def.progA[3], true)]);
  const B = phrase(def.progB, false);
  const bars = [A, A2, B, A2].flat();
  const chords = [def.progA, def.progA, def.progB, def.progA].flat();
  const length = bars.length * 8;
  const lead = new Array(length).fill(null);
  const bass = new Array(length).fill(null);
  const arp = def.arp ? new Array(length).fill(null) : null;
  bars.forEach((bar, bi) => bar.forEach((nt) => { lead[bi * 8 + nt.i] = { n: nt.n, len: nt.len }; }));
  chords.forEach((c, bi) => {
    const r = deg2midi(c, def.root - 24);
    const fifth = deg2midi(c + 4, def.root - 24);
    const o = bi * 8;
    switch (def.bass) {
      case 'drive': for (let i = 0; i < 8; i++) bass[o + i] = { n: i % 4 === 3 ? r + 12 : r, len: 1 }; break;
      case 'bounce': [0, 2, 4, 6].forEach((i, k) => { bass[o + i] = { n: k % 2 ? fifth : r, len: 1 }; }); break;
      case 'walk': [0, 2, 4, 6].forEach((i, k) => { bass[o + i] = { n: [r, fifth, r + 12, fifth][k], len: 2 }; }); break;
      default: bass[o] = { n: r, len: 4 }; bass[o + 4] = { n: fifth, len: 4 };
    }
    if (arp) for (let i = 0; i < 8; i += 2) arp[o + i] = deg2midi(c + [0, 2, 4, 2][i / 2] + 7, def.root - 12);
  });
  return { bpm: def.bpm, length, lead, bass, arp, drums: def.drums, leadWave: def.wave, echo: def.echo };
}
