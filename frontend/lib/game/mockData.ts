/**
 * Phase B placeholder 데이터.
 *
 * 백엔드 v2 state 가 아직 채우지 못하는 UI 필드 (encounter 시각화, narrative spans,
 * tile map, party 호감도 등) 의 mock. Phase D 이후 server-driven 으로 교체.
 */

import type {
  CharacterSheetData,
  DungeonViewData,
  EncounterPanelData,
  EssenceDetailData,
  InventoryPanelData,
  NarrativePanelData,
  PartyPanelData,
  Tile,
  TileType,
  TownViewData,
} from "@/components/game/types";

const ROW = (s: string, mapping: Record<string, TileType>): Tile[] =>
  Array.from(s).map((ch) => ({
    ch,
    type: mapping[ch] ?? (ch === " " ? "blank" : "floor"),
  }));

const TILE_MAP: Record<string, TileType> = {
  "▓": "wall",
  "·": "floor",
  "@": "player",
  g: "enemy",
  b: "enemy",
  H: "npc",
  E: "npc",
  "!": "item",
  "?": "item",
  ">": "stair",
  "<": "stair",
  "|": "door",
  " ": "blank",
};

export const DEMO_DUNGEON: DungeonViewData = {
  turn: 142,
  rows: [
    ROW("▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓", TILE_MAP),
    ROW("▓·················▓", TILE_MAP),
    ROW("▓·!········g·····▓", TILE_MAP),
    ROW("▓·················▓", TILE_MAP),
    ROW("▓···@··H··········▓", TILE_MAP),
    ROW("▓·················▓", TILE_MAP),
    ROW("▓···········?·····▓", TILE_MAP),
    ROW("▓·················▓", TILE_MAP),
    ROW("▓▓▓▓|▓▓▓▓▓▓▓▓▓▓>▓▓", TILE_MAP),
    ROW("    ····▓", TILE_MAP),
    ROW("    ·b··▓", TILE_MAP),
    ROW("    ····▓", TILE_MAP),
    ROW("    ▓▓▓▓▓", TILE_MAP),
  ],
  legend: [
    { ch: "@", type: "player", label: "본인" },
    { ch: "g", type: "enemy", label: "고블린" },
    { ch: "b", type: "enemy", label: "약탈자" },
    { ch: "H", type: "npc", label: "한스" },
    { ch: "!", type: "item", label: "물약" },
    { ch: "?", type: "item", label: "두루마리" },
    { ch: ">", type: "stair", label: "계단" },
  ],
};

export const DEMO_NARRATIVE: NarrativePanelData = {
  turn: 142,
  paragraphs: [
    {
      spans: [
        {
          kind: "plain",
          text: "비요른이 횃불을 켜자 어둠이 걷히며 주변이 선명하게 드러납니다. 붉은 불빛이 벽면을 비추며 ",
        },
        { kind: "emph", text: "10미터 너머까지 시야를 확보" },
        {
          kind: "plain",
          text: "했고, 그림자 속에서 한 명의 인물이 고요히 서 있는 것이 보입니다.",
        },
      ],
    },
    {
      spans: [
        { kind: "plain", text: "그는 " },
        { kind: "name", text: "한스" },
        {
          kind: "plain",
          text: "라 불리는, 길드의 노련한 탐험가였습니다. 깊은 눈빛으로 비요른을 바라보며 살짝 고개를 끄덕입니다. ",
        },
        { kind: "whisper", text: '"오랜만이군, 젊은이..."' },
      ],
    },
    {
      spans: [
        { kind: "plain", text: "북동쪽 방향에서 " },
        { kind: "danger", text: "고블린의 그르렁대는 소리" },
        {
          kind: "plain",
          text: "가 들립니다. 비석 공동으로 향하는 문이 살짝 열려 있습니다.",
        },
      ],
    },
  ],
};

export const DEMO_ENCOUNTER: EncounterPanelData = {
  targets: [
    {
      id: "hans",
      ch: "H",
      name: "한스",
      tag: "우호적 · 길드원",
      kind: "friendly",
    },
    {
      id: "goblin",
      ch: "g",
      name: "고블린",
      tag: "적대 · 거리 6칸",
      kind: "hostile",
    },
  ],
  actions: [
    { id: "attack", label: "공격", key: "a" },
    { id: "talk", label: "대화", key: "t" },
    { id: "pickup", label: "줍기", key: "g" },
    { id: "rest", label: "휴식", key: "." },
  ],
};

export const DEMO_INVENTORY: InventoryPanelData = {
  sections: [
    {
      header: "장비",
      rows: [
        { label: "무기", value: "청동 단검 +1" },
        { label: "방어구", value: "가죽 갑옷" },
        { label: "횃불", value: "활성 · 50%", kind: "amber" },
      ],
    },
    {
      header: "자원",
      rows: [
        { label: "9등급 마석", value: "× 3" },
        { label: "정수 슬롯", value: "2 / ?" },
        { label: "미식별", value: "검증 X · 1", kind: "unidentified" },
      ],
    },
  ],
};

export const DEMO_PARTY: PartyPanelData = {
  members: [
    {
      id: "self",
      name: "비요른",
      portraitCh: "@",
      role: "7등급",
      isSelf: true,
      hp: 75,
      hpMax: 100,
      mood: "alert",
      moodLabel: "경계",
    },
    {
      id: "hans",
      name: "한스",
      portraitCh: "H",
      role: "길드원",
      isSelf: false,
      hp: 60,
      hpMax: 100,
      affinity: 45,
      affinityLabel: "중립",
      mood: "confident",
      moodLabel: "자신",
    },
  ],
};

export const DEMO_CHARACTER: CharacterSheetData = {
  name: "비요른",
  portraitCh: "@",
  subtitle: "~ 미궁 탐험가 · 7등급 ~",
  statSections: [
    {
      header: "기본",
      stats: [
        { label: "HP", value: "75 / 100", bar: 75 },
        { label: "기력", value: "8 / 10", bar: 80 },
        { label: "등급", value: "7등급", amber: true },
        { label: "다음 등급", value: "조건 X · 길드 시험", unidentified: true },
      ],
    },
    {
      header: "전투",
      stats: [
        { label: "공격", value: "14" },
        { label: "방어", value: "9" },
        { label: "민첩", value: "11" },
        { label: "치명", value: "측정 X", unidentified: true },
      ],
    },
    {
      header: "상태",
      stats: [
        { label: "시간", value: "24h / 174h" },
        { label: "위치", value: "1층 · 진입점" },
        { label: "횃불", value: "활성 · 50%", amber: true },
      ],
    },
  ],
  essenceSlots: [
    { state: "filled", icon: "◆", label: "힘 정수 · 9등급" },
    { state: "uncertain", icon: "◇", label: "검증 X" },
    { state: "empty", icon: "·", label: "empty" },
    { state: "locked", icon: "✕", label: "locked" },
  ],
  skillRows: [
    { name: "강타", meta: "힘 정수 9등급 · 능동", value: "레벨 3" },
    {
      name: "??? · 미검증",
      meta: "검증 X · 사용 X",
      value: "측정 X",
      unidentified: true,
    },
  ],
  equipRows: [
    { name: "청동 단검 +1", meta: "무기 · 공격 +3", value: "착용" },
    { name: "가죽 갑옷", meta: "방어구 · 방어 +2", value: "착용" },
    { name: "9등급 마석 × 3", meta: "자원 · 마석", value: "소지" },
  ],
};

export const DEMO_ESSENCE: EssenceDetailData = {
  rank: "9등급 정수",
  name: "??? 정수",
  subtitle: "~ Phase C audit 후 본문 정합 추출 ~",
  description:
    "정수의 본문 정의는 Phase C audit 시점에 추출됩니다. 740 episode + 나무위키 153 페이지 + DC posts 약 30,000 개를 종합 분석 후, canon_facts.json 에 등재된 실제 정의가 이 영역에 표시됩니다. 현 시점은 UI 구조 검증용 placeholder.",
  abilities: [
    {
      kind: "combat",
      label: "전투",
      items: [
        { name: "공격", value: "+5" },
        { name: "치명타", value: "측정 X", unknown: true },
      ],
    },
    {
      kind: "physical",
      label: "신체",
      items: [
        { name: "근력", value: "+3" },
        { name: "민첩", value: "+1" },
      ],
    },
    {
      kind: "sensory",
      label: "감각",
      items: [
        { name: "시야", value: "검증 X", unknown: true },
        { name: "후각", value: "예민" },
      ],
    },
    {
      kind: "social",
      label: "사회",
      items: [
        { name: "위협감", value: "+2" },
        { name: "설득", value: "불명", unknown: true },
      ],
    },
    {
      kind: "mystic",
      label: "마법",
      items: [
        { name: "마력", value: "+0" },
        { name: "저항", value: "+1" },
      ],
    },
    {
      kind: "mental",
      label: "정신",
      items: [
        { name: "집중", value: "+1" },
        { name: "광기 저항", value: "측정 X", unknown: true },
      ],
    },
  ],
  skills: [
    {
      name: "강타",
      meta: "능동 · 기력 2 · 쿨다운 3턴",
      desc: "단일 적에게 큰 충격. 잠시 휘청거리게 만듭니다.",
      level: "레벨 3",
    },
    {
      name: "근력 강화",
      meta: "수동 · 상시",
      desc: "근력이 자연 상승. 무거운 무기 사용 가능.",
      level: "상시",
    },
    {
      name: "???",
      meta: "검증 X · 미식별",
      desc: "더 강한 스킬이 봉인되어 있을 가능성. 등급 상승 시 발현.",
      level: "미발현",
      dormant: true,
    },
  ],
  totals: [
    { label: "공격", value: "+8" },
    { label: "방어", value: "+2" },
    { label: "민첩", value: "+1" },
    { label: "근력", value: "+5" },
    { label: "감각", value: "예민" },
    { label: "부작용", value: "불면", minus: true },
  ],
  sourceCitation: '본문 ep42, ep178 / 나무위키 "정수" 문단 / DC 게시판 검증 X',
  footerMeta: "슬롯 1 · 본문 사례 5건 추출 예정",
};

export const DEMO_TOWN: TownViewData = {
  title: "라스카니아",
  subtitle: "~ 변경 도시 ~",
  pois: [
    {
      id: "guild",
      name: "탐험가 길드",
      desc: "의뢰 / 정보 / 등급",
      key: "1",
      hotspot: { top: "18%", left: "22%" },
    },
    {
      id: "temple",
      name: "신전",
      desc: "정수 흡수 / 식별 / 치유",
      key: "2",
      hotspot: { top: "18%", left: "50%" },
    },
    {
      id: "exam",
      name: "등급 시험소",
      desc: "등급 시험",
      key: "3",
      hotspot: { top: "18%", left: "78%" },
    },
    {
      id: "smith",
      name: "대장간",
      desc: "무기 / 방어구 강화",
      key: "4",
      hotspot: { top: "48%", left: "14%" },
    },
    {
      id: "market",
      name: "거래소",
      desc: "마석 거래 / 시세",
      key: "5",
      hotspot: { top: "48%", left: "86%" },
    },
    {
      id: "tavern",
      name: "선술집",
      desc: "소문 / 동료 만남",
      key: "6",
      hotspot: { top: "78%", left: "22%" },
    },
    {
      id: "home",
      name: "본인 거처",
      desc: "휴식 / 저장 / 정비",
      key: "7",
      hotspot: { top: "78%", left: "50%" },
    },
    {
      id: "rift",
      name: "균열 입구",
      desc: "미궁 진입",
      key: "8",
      hotspot: { top: "78%", left: "78%" },
    },
  ],
  news: {
    paragraphs: [
      {
        spans: [
          { kind: "plain", text: "선술집의 노인이 속삭입니다 — " },
          {
            kind: "whisper",
            text: '"5층 어딘가에 누군가가 8등급 정수를 봤다더군."',
          },
        ],
      },
      {
        spans: [
          { kind: "plain", text: "길드 게시판에 새 의뢰가 붙었습니다. " },
          { kind: "emph", text: "에르웬" },
          { kind: "plain", text: "이 비석 공동에서 본인을 기다리고 있습니다." },
        ],
      },
    ],
  },
  summary: [
    {
      header: "직전 RUN",
      rows: [
        { label: "던전", value: "1층 · 174h" },
        { label: "처치", value: "고블린 ×4 / 약탈자 ×1", kind: "success" },
        { label: "수집", value: "마석 +180", kind: "gold" },
      ],
    },
    {
      header: "상태",
      rows: [
        { label: "HP", value: "100 / 100" },
        { label: "정수 슬롯", value: "2 / ?" },
        { label: "동료", value: "한스 · 대기", kind: "amber" },
      ],
    },
  ],
};
