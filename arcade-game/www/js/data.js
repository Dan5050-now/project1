'use strict';
// ─────────────────────────────────────────────────────────────
//  data.js — 캐릭터, 난이도, 상점, 스테이지 정보, 스토리 대사
// ─────────────────────────────────────────────────────────────

const CHARACTERS = {
  leo: {
    id: 'leo', name: '레오', title: '용감한 검사',
    desc: '균형 잡힌 능력치. 넓은 검 베기로 적과 블록을 시원하게 부순다.',
    special: '파워업 시 검기 발사',
    hp: 4, speed: 104, accel: 820, jump: 332, airJumps: 0,
    attack: 'sword', atkDur: 0.26, atkCD: 0.32, reach: 20,
    stats: { 공격: 4, 속도: 3, 점프: 3, 사거리: 2 },
  },
  mina: {
    id: 'mina', name: '미나', title: '바람의 닌자',
    desc: '가장 빠르고 공중에서 한 번 더 점프할 수 있다. 대신 체력이 약하다.',
    special: '2단 점프 · 빠른 연속 발차기',
    hp: 3, speed: 126, accel: 980, jump: 338, airJumps: 1,
    attack: 'kick', atkDur: 0.2, atkCD: 0.22, reach: 15,
    stats: { 공격: 3, 속도: 5, 점프: 5, 사거리: 1 },
  },
  sera: {
    id: 'sera', name: '세라', title: '별빛 마법사',
    desc: '마법 구슬로 멀리 있는 적을 공격한다. 이동이 느리고 점프가 낮다.',
    special: '원거리 공격 · 파워업 시 3방향 발사',
    hp: 3, speed: 98, accel: 760, jump: 324, airJumps: 0,
    attack: 'magic', atkDur: 0.24, atkCD: 0.36, reach: 0,
    stats: { 공격: 3, 속도: 2, 점프: 2, 사거리: 5 },
  },
};
const CHAR_ORDER = ['leo', 'mina', 'sera'];

const DIFFICULTY = {
  easy: {
    id: 'easy', name: '쉬움', color: '#5ae08a', lives: 5, hpBonus: 1,
    enemySpeed: 0.8, enemyFire: 0.6, enemyHp: 0, bossHp: 0.7, bossSpeed: 0.85, thin: true, invTime: 2.0,
    desc: '목숨 5개 · 체력 +1 · 적이 느리고 수가 적음',
  },
  normal: {
    id: 'normal', name: '보통', color: '#ffd23a', lives: 3, hpBonus: 0,
    enemySpeed: 1, enemyFire: 1, enemyHp: 0, bossHp: 1, bossSpeed: 1, thin: false, invTime: 1.6,
    desc: '목숨 3개 · 표준 밸런스',
  },
  hard: {
    id: 'hard', name: '어려움', color: '#ff5a6a', lives: 2, hpBonus: -1,
    enemySpeed: 1.25, enemyFire: 1.5, enemyHp: 1, bossHp: 1.4, bossSpeed: 1.2, thin: false, invTime: 1.3,
    desc: '목숨 2개 · 체력 -1 · 적이 빠르고 단단함',
  },
};
const DIFF_ORDER = ['easy', 'normal', 'hard'];

const SHOP_ITEMS = [
  { id: 'life', name: '생명 +1', desc: '남은 목숨이 하나 늘어난다', price: 60, icon: 'life' },
  { id: 'heartc', name: '하트 그릇', desc: '최대 체력 +1 (최대 2번)', price: 90, icon: 'heart', max: 2 },
  { id: 'shield', name: '보호막', desc: '다음 스테이지를 보호막과 함께 시작', price: 30, icon: 'shield' },
  { id: 'charm', name: '파워 부적', desc: '다음 스테이지 시작 30초간 파워업', price: 40, icon: 'power' },
];

const STAGES = [
  { id: 'forest', name: '그린우드 숲', sub: 'STAGE 1', theme: 'forest', music: 'forest', boss: 'bramble', bossName: '가시멧돼지 브램블', bossLine: '크르릉! 이 숲은 내 거다!' },
  { id: 'cave', name: '수정 동굴', sub: 'STAGE 2', theme: 'cave', music: 'cave', boss: 'granit', bossName: '수정 골렘 그라닛', bossLine: '침입자… 부순다…' },
  { id: 'sea', name: '산호 바다', sub: 'STAGE 3', theme: 'sea', music: 'sea', boss: 'okto', bossName: '심연의 크라켄 옥토', bossLine: '바다는 그림자의 것이야!' },
  { id: 'desert', name: '타오르는 사막', sub: 'STAGE 4', theme: 'desert', music: 'desert', boss: 'dungar', bossName: '모래 웜 둔가르', bossLine: '쿠르르르… 모래 속으로 사라져라!' },
  { id: 'sky', name: '구름 성채', sub: 'STAGE 5', theme: 'sky', music: 'sky', boss: 'tempest', bossName: '폭풍 그리폰 템페스트', bossLine: '하늘을 넘보는 자, 번개로 심판하리라!' },
  { id: 'castle', name: '그림자 성', sub: 'FINAL STAGE', theme: 'castle', music: 'castle', boss: 'morvath', bossName: '그림자왕 모르바스', bossLine: '빛 따위… 이 어둠으로 삼켜주마!' },
];

// 대사: who = narr | hero | pipi | sage | toto | morvath | boss
// text는 문자열 또는 { leo, mina, sera } (캐릭터별 대사)
const STORY = {
  prologue: {
    bg: 'castle', music: 'dark',
    lines: [
      { who: 'narr', text: '빛의 왕국 루미나. 하늘 탑 꼭대기의 「별의 수정」이 온 세상을 밝게 비추고 있었다.' },
      { who: 'narr', text: '그러던 어느 밤, 그림자왕 모르바스가 나타나 별의 수정을 여섯 조각으로 부숴 버렸다.' },
      { who: 'morvath', text: '크하하하! 빛의 시대는 끝났다! 조각들은 내 그림자에 물든 수호자들이 지킬 것이다!' },
      { who: 'narr', text: '빛을 잃은 세상은 조금씩 어둠에 물들어 갔다…' },
      { who: 'sage', text: '{hero}야, 잘 왔다. 별의 수정이 마지막으로 남긴 빛의 정령이 너를 선택했단다.' },
      { who: 'pipi', text: '안녕! 난 별의 정령 피피야. 흩어진 별조각 여섯 개를 모두 모으면 수정을 되살릴 수 있어!' },
      { who: 'hero', text: { leo: '맡겨 주세요! 이 검에 걸고 반드시 빛을 되찾겠습니다!', mina: '후훗, 바람보다 빠르게 다녀올게요!', sera: '별빛 마법의 힘으로… 꼭 해낼게요.' } },
      { who: 'sage', text: '첫 번째 조각의 기운은 동쪽 그린우드 숲에서 느껴진다. 부디 조심하거라.' },
    ],
  },
  stages: [
    {
      intro: [
        { who: 'pipi', text: '여기가 그린우드 숲이야. 원래는 새들이 노래하던 평화로운 곳인데…' },
        { who: 'pipi', text: '숲의 동물들이 그림자에 홀려서 난폭해졌어. 표지판을 잘 읽어 봐!' },
        { who: 'hero', text: { leo: '숲의 친구들을 구해 주자!', mina: '좋아, 단숨에 돌파한다!', sera: '조심해서 가 보자, 피피.' } },
      ],
      outro: [
        { who: 'boss', text: '꾸에엑… 몸이… 가벼워졌다… 나는 대체 무슨 짓을…' },
        { who: 'pipi', text: '첫 번째 별조각이야! 브램블은 원래 숲을 지키던 착한 수호자였어.' },
        { who: 'boss', text: '고맙다, 꼬마 영웅. 동쪽 산의 수정 동굴에서도 같은 그림자의 기운이 느껴졌다.' },
        { who: 'hero', text: { leo: '다음은 동굴이군. 가자, 피피!', mina: '동굴이라… 어두운 건 좀 싫지만, 가자!', sera: '수정 동굴… 마력이 강한 곳이야. 서두르자.' } },
      ],
    },
    {
      intro: [
        { who: 'narr', text: '수정 동굴 — 광부들이 빛나는 수정을 캐던 깊은 동굴.' },
        { who: 'pipi', text: '천장에 매달린 종유석을 조심해! 밑을 지나가면 떨어질 거야.' },
        { who: 'hero', text: { leo: '방심하지 않겠어.', mina: '떨어지기 전에 지나가면 그만이지!', sera: '피피, 빛을 조금만 밝혀 줄래?' } },
      ],
      outro: [
        { who: 'boss', text: '나는… 동굴의 문지기 그라닛… 모르바스에게 마음을 빼앗기고 있었군…' },
        { who: 'boss', text: '고맙다, 작은 영웅이여. 이 지하수를 따라가면 산호 바다로 이어진다.' },
        { who: 'pipi', text: '조각 두 개! 내 빛이 강해졌어. 물속에서도 숨 쉴 수 있게 「물방울 축복」을 걸어 줄게!' },
        { who: 'hero', text: { leo: '바닷속이라니, 기대되는걸!', mina: '수영이라면 자신 있어!', sera: '물방울 축복… 따뜻한 마법이네.' } },
      ],
    },
    {
      intro: [
        { who: 'narr', text: '산호 바다 — 바닷속 왕국의 아름다운 정원.' },
        { who: 'pipi', text: '점프 버튼을 누를 때마다 위로 헤엄칠 수 있어. 가시 산호와 복어는 조심!' },
      ],
      outro: [
        { who: 'boss', text: '먹물이… 맑아졌어. 미안해, 바다를 어지럽혀서…' },
        { who: 'boss', text: '거대한 그림자가 사막의 피라미드 쪽으로 내려가는 걸 봤어.' },
        { who: 'pipi', text: '세 번째 조각! 이제 절반이야!' },
        { who: 'morvath', text: '제법이군, 꼬마. 하지만 사막의 태양 아래서 바싹 말라 버려라!' },
        { who: 'hero', text: { leo: '모르바스! 기다려라, 반드시 간다!', mina: '흥, 협박 따위 안 통해!', sera: '…절대 지지 않아.' } },
      ],
    },
    {
      intro: [
        { who: 'narr', text: '타오르는 사막 — 고대 왕국의 유적이 잠든 곳.' },
        { who: 'pipi', text: '모래늪에 빠지면 점프로 빨리 빠져나와! 오래 있으면 가라앉아 버려.' },
      ],
      outro: [
        { who: 'boss', text: '쿠르르… 그림자가… 걷혔다… 고대의 벽화를… 보아라…' },
        { who: 'narr', text: '벽화에는 구름 위의 성채와, 바람의 돌로 이어진 하늘길이 그려져 있었다.' },
        { who: 'pipi', text: '다섯 번째 조각은 하늘에 있어! 바람의 돌을 타고 구름 성채까지 올라가자!' },
        { who: 'hero', text: { leo: '하늘이라… 떨어지지 않게 조심해야겠군.', mina: '높이 뛰는 건 내 전문이지!', sera: '바람의 마력이 느껴져. 가자!' } },
      ],
    },
    {
      intro: [
        { who: 'narr', text: '구름 성채 — 하늘을 지키는 폭풍의 성.' },
        { who: 'pipi', text: '발판이 움직이고 무너져! 아래로 떨어지면 끝이야, 침착하게!' },
      ],
      outro: [
        { who: 'boss', text: '폭풍이 잠잠해지는군… 나는 원래 하늘 탑의 수호자였다.' },
        { who: 'boss', text: '모르바스는 그림자 성에서 마지막 조각을 쥐고 너를 기다리고 있다.' },
        { who: 'pipi', text: '{hero}… 사실 말하지 못한 게 있어. 나는 별의 수정의 「심장」이야.' },
        { who: 'pipi', text: '마지막 조각과 내가 하나가 되면 수정은 완전히 되살아나. 끝까지 함께 가 줄래?' },
        { who: 'hero', text: { leo: '당연하지! 우린 처음부터 동료였잖아!', mina: '무슨 소리야! 처음부터 끝까지 함께야!', sera: '피피… 응. 끝까지 함께야.' } },
      ],
    },
    {
      intro: [
        { who: 'narr', text: '그림자 성 — 빛이 닿지 않는 마지막 성.' },
        { who: 'morvath', text: '여기까지 오다니. 하지만 그림자는 영원하다. 이곳이 너의 무덤이 될 것이다!' },
        { who: 'pipi', text: '용암과 천장 가시투성이야… 점프 버튼을 짧게 누르면 낮게 뛸 수 있어!' },
        { who: 'hero', text: { leo: '마지막 싸움이다. 간다!', mina: '여기서 끝내 주겠어!', sera: '모두의 빛을… 되찾을 거야!' } },
      ],
      outro: [
        { who: 'morvath', text: '말도 안 돼… 그림자가… 빛에…' },
        { who: 'morvath', text: '…나는 그저… 눈부신 빛 속에서 홀로 외로웠던 그림자였을 뿐인데…' },
        { who: 'pipi', text: '그림자는 빛이 있어야 생겨나. 빛과 그림자는 함께 살아갈 수 있어.' },
        { who: 'morvath', text: '…함께…라. 그런 말을 들은 건… 처음이군…' },
      ],
    },
  ],
  ending: {
    bg: 'sky', music: 'ending',
    lines: [
      { who: 'narr', text: '여섯 개의 별조각과 피피의 빛이 하나가 되자, 별의 수정이 다시 하늘 탑에서 빛나기 시작했다.' },
      { who: 'sage', text: '정말 잘 해냈다, {hero}. 루미나에 다시 아침이 찾아왔구나.' },
      { who: 'pipi', text: '고마워, {hero}! 나는 수정 속에서 언제나 너를 비추고 있을게.' },
      { who: 'hero', text: { leo: '피피, 고마워. 이 검은 앞으로도 모두를 지키는 데 쓸게.', mina: '언제든 부르면 바람처럼 달려갈게!', sera: '네 빛은… 내 마법 속에 영원히 남아 있을 거야.' } },
      { who: 'narr', text: '그리고 하늘 탑 아래, 작은 그림자 하나가 따스한 햇살 곁에 조용히 머물렀다.' },
    ],
  },
};

const SIGN_TEXTS = {
  forest: [
    '왼쪽 화면을 누른 채 움직이면 조이스틱! ◀ ▶',
    'A 버튼: 점프 — 길게 누르면 더 높이 뛰어요',
    'B 버튼: 공격 — 벽돌 블록도 부술 수 있어요',
    '★ 블록에는 아이템이 숨어 있어요',
  ],
  sea: ['물속에서는 A 버튼을 연타해서 헤엄쳐요'],
  desert: ['모래늪! 점프 버튼으로 빨리 빠져나오세요'],
  sky: ['움직이는 구름에 올라타세요. 떨어지면 끝!'],
};
