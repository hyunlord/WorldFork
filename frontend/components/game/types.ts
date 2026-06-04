/**
 * Phase B UI 공유 타입.
 *
 * 컴포넌트가 받는 prop shape. 백엔드 StateResponse 매핑은 page level 에서 수행.
 */

export type DungeonMode = "dungeon" | "town";
export type TimeOfDay = "낮" | "밤" | "황혼" | "여명";

export interface StatusBarData {
  brand?: string;
  mode: DungeonMode;
  hp: number;
  hpMax: number;
  hoursInDungeon?: number;
  hoursMax?: number;
  locationLabel: string;
  timeOfDay: TimeOfDay;
  grade?: string;
  mageStones?: number;
  runLabel?: string;
  // ★ commit 2 — 신규 stat fields
  soulPower?: number;
  soulPowerMax?: number;
  essenceCount?: number;
  essenceMax?: number;
  playerLevel?: number;
  floorNumber?: number;
}

export type TileType =
  | "wall"
  | "floor"
  | "player"
  | "enemy"
  | "npc"
  | "item"
  | "stair"
  | "door"
  | "blank";

export interface Tile {
  ch: string;
  type: TileType;
  // ★ 엔티티 스프라이트 override (몬스터 종류별 — 고블린/노움/슬라임 등). 없으면
  //   TileType 기본 스프라이트. assets/pixel/<sprite>.png.
  sprite?: string;
}

export interface DungeonViewData {
  turn: number;
  rows: Tile[][];
  legend?: ReadonlyArray<{ ch: string; type: TileType; label: string }>;
}

export type NarrativeSpan =
  | { kind: "plain"; text: string }
  | { kind: "emph"; text: string }
  | { kind: "name"; text: string }
  | { kind: "danger"; text: string }
  | { kind: "whisper"; text: string }
  | { kind: "essence"; text: string };

export interface NarrativeParagraph {
  spans: NarrativeSpan[];
}

export interface NarrativePanelData {
  turn: number;
  paragraphs: NarrativeParagraph[];
}

export type EncounterTargetKind = "hostile" | "friendly";

export interface EncounterTarget {
  id: string;
  ch: string;
  name: string;
  tag: string;
  kind: EncounterTargetKind;
}

export interface EncounterAction {
  id: string;
  label: string;
  key: string;
}

export interface StatusEffectDisplay {
  type: string;
  duration: number;
  intensity: number;
}

export interface EncounterPanelData {
  targets: EncounterTarget[];
  actions: EncounterAction[];
  status_effects?: StatusEffectDisplay[];
}

export type InventoryValueKind = "normal" | "amber" | "unidentified";

export interface InventoryRow {
  label: string;
  value: string;
  kind?: InventoryValueKind;
}

export interface InventorySection {
  header: string;
  rows: InventoryRow[];
}

export interface InventoryPanelData {
  sections: InventorySection[];
}

export type PartyMemberMood = "alert" | "wounded" | "confident" | "neutral";

export interface PartyMember {
  id: string;
  name: string;
  portraitCh: string;
  role: string;
  isSelf: boolean;
  hp: number;
  hpMax: number;
  affinity?: number;
  affinityLabel?: string;
  mood?: PartyMemberMood;
  moodLabel?: string;
  injured?: boolean;
}

export interface PartyPanelData {
  members: PartyMember[];
}

export type EssenceSlotState = "filled" | "empty" | "locked" | "uncertain";

export interface EssenceSlot {
  state: EssenceSlotState;
  icon: string;
  label: string;
}

export interface CharacterStatBig {
  label: string;
  value: string;
  bar?: number;
  unidentified?: boolean;
  amber?: boolean;
}

export interface CharacterStatSection {
  header: string;
  stats: CharacterStatBig[];
}

export interface CharacterListRow {
  name: string;
  meta?: string;
  value: string;
  unidentified?: boolean;
}

export interface CharacterListSection {
  header: string;
  rows: CharacterListRow[];
}

export interface CharacterSheetData {
  name: string;
  portraitCh: string;
  /** 전신 일러스트 경로(ui_character_*). 없으면 문자 portraitCh fallback. */
  portraitImage?: string | null;
  subtitle: string;
  statSections: CharacterStatSection[];
  essenceSlots: EssenceSlot[];
  skillRows: CharacterListRow[];
  equipRows: CharacterListRow[];
}

export type EssenceCategoryKind =
  | "combat"
  | "physical"
  | "sensory"
  | "social"
  | "mystic"
  | "mental";

export interface EssenceAbilityItem {
  name: string;
  value: string;
  unknown?: boolean;
}

export interface EssenceAbilityCategory {
  kind: EssenceCategoryKind;
  label: string;
  items: EssenceAbilityItem[];
}

export interface EssenceSkill {
  name: string;
  meta: string;
  desc?: string;
  level: string;
  dormant?: boolean;
}

export interface EssenceTotalEffect {
  label: string;
  value: string;
  minus?: boolean;
}

export interface EssenceDetailData {
  rank: string;
  name: string;
  subtitle?: string;
  description: string;
  abilities: EssenceAbilityCategory[];
  skills: EssenceSkill[];
  totals: EssenceTotalEffect[];
  sourceCitation?: string;
  footerMeta?: string;
}

export interface TownPoi {
  id: string;
  name: string;
  desc: string;
  key: string;
  hotspot: { top: string; left: string };
}

export interface TownNewsItem {
  paragraphs: NarrativeParagraph[];
}

export interface TownRunSummaryRow {
  label: string;
  value: string;
  kind?: "amber" | "gold" | "success" | "normal";
}

export interface TownRunSummarySection {
  header: string;
  rows: TownRunSummaryRow[];
}

export interface TownViewData {
  title: string;
  subtitle: string;
  pois: TownPoi[];
  news: TownNewsItem;
  summary: TownRunSummarySection[];
}
