export type ScenarioMode = "bjorn" | "new_explorer";

export type Race = "barbarian" | "human" | "dwarf" | "beastkin" | "fairy";

export interface RaceInfo {
  id: Race;
  nameKo: string;
  hp: number;
  soulPower: number;
  maxEssences: number;
  attack: number;
  defense: number;
  dex: number;
  luck: number;
  traits: string[];
  description: string;
}

export interface CharacterCreateRequest {
  scenario_mode: ScenarioMode;
  race?: Race;
  weapon?: string;
}

export interface WeaponInfo {
  name: string;
  description: string;
}

// 성인식 선택 무기 — backend service/canon/scenario.py COMING_OF_AGE_WEAPONS 정합
export const COMING_OF_AGE_WEAPONS: WeaponInfo[] = [
  { name: "한손 검", description: "균형 잡힌 한손 검 — 무난한 선택." },
  { name: "양손 대검", description: "묵직한 양손 대검 — 한 방이 강하다." },
  { name: "메이스", description: "타격용 둔기 — 둔중하나 확실하다." },
  { name: "쇠곤봉", description: "단단한 쇠곤봉 — 다루기 쉽다." },
  { name: "창", description: "긴 사거리의 창 — 거리를 벌린다." },
  { name: "작살", description: "갈고리 달린 작살 — 끌어당긴다." },
  { name: "양손 도끼", description: "위력적인 양손 도끼 — 묵직한 일격." },
  { name: "도리깨", description: "사슬 달린 도리깨 — 변칙적이다." },
  { name: "대형 망치", description: "강력한 대형 망치 — 가장 무겁다." },
  { name: "방패", description: "되팔 때 가장 비싸다 — 그 누구도 고르지 않은 선택." },
];

export const DEFAULT_WEAPON = "방패";

export interface CharacterCreateResponse {
  session_id: string;
  scenario_mode: string;
  race: string;
  starting_location: string;
  starting_floor: number;
  hp: number;
  max_hp: number;
  soul_power: number;
  max_essences: number;
  race_traits: string[];
  scenario_description: string;
  starting_narrative: string;
  starting_weapon: string;
}

// 5종 종족 정보 — backend service/canon/races.py 정합
export const RACES: RaceInfo[] = [
  {
    id: "barbarian",
    nameKo: "바바리안",
    hp: 120,
    soulPower: 10,
    maxEssences: 1,
    attack: 14,
    defense: 6,
    dex: 8,
    luck: 5,
    traits: ["근력 +5", "체력 +3", "유연성 -2", "수영 불가"],
    description: "거대한 체구와 강한 근력을 지닌 종족. 마법 재능 X.",
  },
  {
    id: "human",
    nameKo: "인간",
    hp: 100,
    soulPower: 10,
    maxEssences: 1,
    attack: 10,
    defense: 5,
    dex: 10,
    luck: 10,
    traits: ["균형 stat", "정수 흡수 +10%"],
    description: "라스카니아에서 가장 흔한 종족. 모든 stat 균형, 후반 포텐.",
  },
  {
    id: "dwarf",
    nameKo: "드워프",
    hp: 110,
    soulPower: 10,
    maxEssences: 1,
    attack: 11,
    defense: 9,
    dex: 6,
    luck: 7,
    traits: ["방어력 +4", "회피 +5%", "무구의 축복 — 장비 효율 ↑"],
    description: "장인과 광부의 종족. 야금술과 건축 특화.",
  },
  {
    id: "beastkin",
    nameKo: "수인",
    hp: 105,
    soulPower: 10,
    maxEssences: 1,
    attack: 12,
    defense: 5,
    dex: 15,
    luck: 8,
    traits: ["민첩성 +5", "후각 — 어둠 탐지 ↑", "발톱 — 비무장 공격 +3"],
    description: "동물귀를 지닌 종족. 민첩성과 감각 능력 특화.",
  },
  {
    id: "fairy",
    nameKo: "요정",
    hp: 80,
    soulPower: 20,
    maxEssences: 2,
    attack: 7,
    defense: 3,
    dex: 14,
    luck: 11,
    traits: ["영혼력 +10", "정수 슬롯 +1", "회피 +10%", "체력 낮음"],
    description: "정령술을 쓰는 종족. 뛰어난 기감과 정수 친화력.",
  },
];
