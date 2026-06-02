"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CharacterSheetModal } from "@/components/game/CharacterSheetModal";
import { DialogueView } from "@/components/game/DialogueView";
import { DungeonView } from "@/components/game/DungeonView";
import { EncounterPanel } from "@/components/game/EncounterPanel";
import { EssenceDetailModal } from "@/components/game/EssenceDetailModal";
import { GameMenu } from "@/components/game/GameMenu";
import { HelpPanel } from "@/components/game/HelpPanel";
import { InputBar, type InputBarHandle } from "@/components/game/InputBar";
import { InventoryPanel } from "@/components/game/InventoryPanel";
import { MapPanel } from "@/components/game/MapPanel";
import { NarrativePanel } from "@/components/game/NarrativePanel";
import { PartyPanel } from "@/components/game/PartyPanel";
import { StatusBar } from "@/components/game/StatusBar";
import { SuggestedActions } from "@/components/game/SuggestedActions";
import type {
  CharacterListRow,
  CharacterSheetData,
  EncounterPanelData,
  EssenceSlot,
  InventoryPanelData,
  InventoryRow,
  NarrativePanelData,
  NarrativeSpan,
  PartyMember,
  PartyMemberMood,
  PartyPanelData,
  StatusBarData,
} from "@/components/game/types";
import { DEMO_DUNGEON, DEMO_ESSENCE } from "@/lib/game/mockData";
import { useFreeformAction } from "@/lib/hooks/useFreeformAction";
import { useGameState } from "@/lib/hooks/useGameState";
import { useKeyboard } from "@/lib/hooks/useKeyboard";
import { usePostAction } from "@/lib/hooks/usePostAction";
import { RACES } from "@/lib/types/character";
import { parseDialogue, type ParsedDialogue } from "@/lib/game/dialogue";
import { collectEssenceSkills, skillMeta } from "@/lib/game/skills";
import { getStoredStartNarrative } from "@/lib/session";
import { unmaskIp } from "@/lib/api/v2";
import type { CharacterV2, StateResponse } from "@/lib/api/v2";

// 미궁 1층 cycle = 7일 = 168h (backend dungeon_clock.FLOOR_CYCLE_HOURS 정합)
const MAX_HOURS = 168;

// 정수 흡수 narrative pattern — action_handlers.py 정합
const ESSENCE_RE = /「캐릭터의 영혼에 '([^']+)'이\(가\) 스며듭니다\.」/g;

function paragraphToSpans(text: string): NarrativeSpan[] {
  const spans: NarrativeSpan[] = [];
  let lastIndex = 0;
  const pattern = new RegExp(ESSENCE_RE.source, "g");
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      spans.push({ kind: "plain", text: text.substring(lastIndex, match.index) });
    }
    spans.push({ kind: "essence", text: match[0] });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    spans.push({ kind: "plain", text: text.substring(lastIndex) });
  }

  return spans.length > 0 ? spans : [{ kind: "plain", text }];
}

function narrativeStringToData(text: string, turn: number): NarrativePanelData {
  // ★ 게임 화면 원작 명칭 — narrative 본문에도 unmaskIp (라스카니아 → 라프도니아)
  const paragraphs = unmaskIp(text)
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0)
    .map((p) => ({ spans: paragraphToSpans(p) }));
  return {
    turn,
    // ★ DEMO fallback 금지 (harness 재설계) — 빈 응답은 빈 narrative (위장 X)
    paragraphs,
  };
}

function buildCharacterSheet(player: CharacterV2): CharacterSheetData {
  const race = String(player.race ?? "unknown");
  const raceInfo = RACES.find((r) => r.id === race);
  const hp = Number(player.hp ?? 0);
  const hpMax = Number(player.hp_max ?? 100);
  const hpPct = Math.round((hp / Math.max(1, hpMax)) * 100);
  const soulPower = Number((player as Record<string, unknown>).soul_power ?? 0);
  const soulPowerMax = Number((player as Record<string, unknown>).soul_power_max ?? 0);
  const level = Number((player as Record<string, unknown>).level ?? 1);
  const grade = Number((player as Record<string, unknown>).grade ?? 1);
  const essencesRaw = (player as Record<string, unknown>).essences;
  const essences = Array.isArray(essencesRaw) ? essencesRaw : [];

  const essenceSlots: EssenceSlot[] = [
    ...essences.map((e: unknown) => {
      const ess = e as Record<string, unknown>;
      return {
        state: "filled" as const,
        icon: "◆",
        label: String(ess.name ?? "정수"),
      };
    }),
    { state: "empty" as const, icon: "·", label: "빈 슬롯" },
  ];

  const raceTraitsRaw = (player as Record<string, unknown>).race_traits;
  const traits: string[] = Array.isArray(raceTraitsRaw)
    ? (raceTraitsRaw as string[])
    : (raceInfo?.traits ?? []);

  // ★ 흡수 정수 magic·skill (active/passive) 우선 노출 + race trait
  const essenceSkills = collectEssenceSkills(player as Record<string, unknown>);
  const skillRows: CharacterListRow[] = [
    ...essenceSkills.map((s) => ({
      name: s.name,
      meta: skillMeta(s),
      value: s.kind === "active" ? "A" : "P",
    })),
    ...traits.map((t) => ({ name: t, value: "" })),
  ];

  return {
    name: String(player.name ?? "탐험가"),
    portraitCh: "@",
    subtitle: `~ ${raceInfo?.nameKo ?? race} · ${grade}등급 ~`,
    statSections: [
      {
        header: "기본",
        stats: [
          { label: "HP", value: `${hp} / ${hpMax}`, bar: hpPct },
          ...(soulPowerMax > 0
            ? [
                {
                  label: "영혼력",
                  value: `${soulPower} / ${soulPowerMax}`,
                  bar: Math.round((soulPower / soulPowerMax) * 100),
                },
              ]
            : []),
          { label: "레벨", value: String(level) },
          { label: "등급", value: `${grade}등급`, amber: true },
        ],
      },
      ...(raceInfo != null
        ? [
            {
              header: "전투",
              stats: [
                { label: "공격", value: String(raceInfo.attack) },
                { label: "방어", value: String(raceInfo.defense) },
                { label: "민첩", value: String(raceInfo.dex) },
                { label: "행운", value: String(raceInfo.luck) },
              ],
            },
          ]
        : []),
    ],
    essenceSlots,
    skillRows,
    equipRows: [],
  };
}

function buildInventory(player: CharacterV2 | null): InventoryPanelData {
  if (!player) return { sections: [] };  // ★ DEMO fallback 금지 — state 없으면 빈
  const p = player as Record<string, unknown>;
  const eq = (p.equipment ?? {}) as Record<string, unknown>;
  const inv = (p.inventory ?? {}) as Record<string, unknown>;
  const items = Array.isArray(inv.items) ? (inv.items as Record<string, unknown>[]) : [];

  const weapon = eq.weapon as Record<string, unknown> | null | undefined;
  const armor = eq.armor as Record<string, unknown> | null | undefined;
  const acc1 = eq.accessory_1 as Record<string, unknown> | null | undefined;
  const acc2 = eq.accessory_2 as Record<string, unknown> | null | undefined;
  const equipRows: InventoryRow[] = [
    { label: "무기", value: weapon ? String(weapon.name) : "없음" },
    { label: "방어구", value: armor ? String(armor.name) : "없음" },
  ];
  if (acc1) equipRows.push({ label: "장신구 1", value: String(acc1.name) });
  if (acc2) equipRows.push({ label: "장신구 2", value: String(acc2.name) });

  const stoneMap: Record<string, number> = {};
  const resourceRows: InventoryRow[] = [];
  for (const item of items) {
    const category = String(item.category ?? "");
    const name = String(item.name ?? "아이템");
    const grade = item.grade;
    if (grade != null) {
      const key = `${grade}등급 마석`;
      stoneMap[key] = (stoneMap[key] ?? 0) + 1;
    } else if (category === "마도구" || name.includes("횃불")) {
      resourceRows.push({ label: name, value: "활성", kind: "amber" });
    } else if (category !== "무기" && category !== "방어구" && category !== "장신구") {
      resourceRows.push({ label: name, value: "1" });
    }
  }
  for (const [label, count] of Object.entries(stoneMap)) {
    resourceRows.push({ label, value: `× ${count}` });
  }
  if (resourceRows.length === 0) {
    resourceRows.push({ label: "자원 없음", value: "-" });
  }

  return {
    sections: [
      { header: "장비", rows: equipRows },
      { header: "자원", rows: resourceRows },
    ],
  };
}

function buildParty(data: StateResponse | null): PartyPanelData {
  // ★ DEMO fallback 금지 (harness 재설계) — state 없거나 빈 party면 파티원 0 (위장 X)
  if (!data) return { members: [] };
  const chars = Object.values(data.state.characters);
  if (chars.length === 0) return { members: [] };

  const members: PartyMember[] = chars.map((c) => {
    const char = c as CharacterV2 & Record<string, unknown>;
    const hp = Number(char.hp ?? 100);
    const hpMax = Number(char.hp_max ?? 100);
    const grade = Number(char.grade ?? 1);
    const isPlayer = Boolean(char.is_player);
    const hpPct = hpMax > 0 ? hp / hpMax : 1;
    const mood: PartyMemberMood =
      hpPct < 0.3 ? "wounded" : hpPct < 0.7 ? "alert" : "confident";
    const moodLabel =
      mood === "wounded" ? "부상" : mood === "alert" ? "경계" : "양호";
    return {
      id: String(char.name ?? "unknown"),
      name: String(char.name ?? "탐험가"),
      portraitCh: isPlayer ? "@" : String(char.name ?? "N")[0] ?? "N",
      role: `${grade}등급`,
      isSelf: isPlayer,
      hp,
      hpMax,
      mood,
      moodLabel,
    };
  });
  members.sort((a, b) => (a.isSelf ? -1 : b.isSelf ? 1 : 0));
  return { members };
}

// ★ session encounters(전투 enemy) → EncounterPanel — 5종 mechanic 결과 시각화
function buildEncounter(
  encounters: Record<string, unknown>[] | undefined,
): EncounterPanelData {
  const actions = [
    { id: "attack", label: "공격", key: "a" },
    { id: "talk", label: "대화", key: "t" },
    { id: "rest", label: "휴식", key: "." },
  ];
  if (!encounters || encounters.length === 0) return { targets: [], actions };
  return {
    targets: encounters.map((e, i) => ({
      id: `enemy-${i}`,
      ch: String((e.name as string | undefined) ?? "?").charAt(0) || "?",
      name: unmaskIp(String(e.name ?? "적")),
      tag: `적대 · HP ${e.hp ?? "?"}/${e.max_hp ?? "?"}`,
      kind: "hostile" as const,
    })),
    actions,
  };
}

// ★ 상황별 배경 이미지 (ComfyUI PNG) — ASCII 단절 해소 (비주얼 재검토)
function bgImage(floor: number, riftId: string | null | undefined): string {
  const base = "/assets/worldfork/";
  if (floor === 0) return `${base}ui_main_bg.png`; // 성인식 마을/성지
  if (riftId) return `${base}ui_rift_${riftId}.png`; // 던전 rift (bloody_castle 등)
  return `${base}ui_gameplay_bg_crystal.png`; // 기본 던전
}

export default function GamePage() {
  const { data } = useGameState();
  const { execute, executing } = usePostAction();
  const freeform = useFreeformAction();
  const inputRef = useRef<InputBarHandle>(null);

  const [charOpen, setCharOpen] = useState(false);
  const [essenceOpen, setEssenceOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [mapOpen, setMapOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [dialogueOpen, setDialogueOpen] = useState(false);
  const [turnCount, setTurnCount] = useState(0);
  // ★ 성인식 시작 narrative — hydration 안전 위해 effect로 localStorage 읽기
  const [startNarrative, setStartNarrative] = useState<string | null>(null);
  useEffect(() => {
    setStartNarrative(getStoredStartNarrative());
  }, []);

  const player = useMemo<CharacterV2 | null>(() => {
    if (!data) return null;
    const characters = data.state.characters ?? {};
    return (
      (Object.values(characters).find(
        (c) => (c as Record<string, unknown>).is_player === true,
      ) as CharacterV2 | undefined) ?? null
    );
  }, [data]);

  // ★ 성인식 마을(floor 0) — 던전맵/조우 미표시 (DEMO 한스 노출 X, 성인식 narrative 중심)
  const inVillage = (data?.state.location?.floor ?? 0) === 0;

  // ★ 전투 enemy — session encounters 실데이터 (5종 mechanic 결과 시각화)
  const encounterData = useMemo<EncounterPanelData>(
    () => buildEncounter(data?.state.encounters),
    [data],
  );

  // ★ 상황별 배경 이미지 (ComfyUI PNG — ASCII 단절 해소)
  const bgUrl = bgImage(
    data?.state.location?.floor ?? 0,
    data?.state.location?.rift_id,
  );

  const statusData = useMemo<StatusBarData>(() => {
    if (!data) {
      return {
        mode: "dungeon",
        hp: 75,
        hpMax: 100,
        hoursInDungeon: 24,
        hoursMax: MAX_HOURS,
        locationLabel: "1층 · 진입점",
        timeOfDay: "밤",
      };
    }
    const hp = Number(player?.hp ?? 75);
    const hpMax = Number(player?.hp_max ?? 100);
    const soulPower = Number((player as Record<string, unknown> | null)?.soul_power ?? 0);
    const soulPowerMax = Number((player as Record<string, unknown> | null)?.soul_power_max ?? 0);
    const level = Number((player as Record<string, unknown> | null)?.level ?? 1);
    const essencesRaw = (player as Record<string, unknown> | null)?.essences;
    const essenceCount = Array.isArray(essencesRaw) ? essencesRaw.length : 0;
    const maxEssences = Number(
      (player as Record<string, unknown> | null)?.max_essences ?? level + 1,
    );
    const sub = data.state.location.sub_area ?? "진입점";
    const floor = data.state.location.floor;
    return {
      mode: "dungeon",
      hp,
      hpMax,
      hoursInDungeon: data.state.world.hours_in_dungeon ?? 0,
      hoursMax: MAX_HOURS,
      locationLabel: floor != null ? `${floor}층 · ${sub}` : sub,
      timeOfDay: "밤",
      soulPower,
      soulPowerMax,
      essenceCount,
      essenceMax: maxEssences,
      playerLevel: level,
      floorNumber: floor ?? 0,
    };
  }, [data, player]);

  const charSheetData = useMemo<CharacterSheetData | null>(() => {
    if (!player) return null;
    return buildCharacterSheet(player);
  }, [player]);

  const inventoryData = useMemo<InventoryPanelData>(
    () => buildInventory(player),
    [player],
  );

  const partyData = useMemo<PartyPanelData>(
    () => buildParty(data),
    [data],
  );

  const handleSubmit = useCallback(
    async (text: string) => {
      const resp = await freeform.submit(text);
      if (resp) {
        setTurnCount((t) => t + 1);
      }
    },
    [freeform],
  );

  const narrativeData = useMemo<NarrativePanelData>(() => {
    if (freeform.lastResponse) {
      return narrativeStringToData(freeform.lastResponse.narrative, turnCount);
    }
    // ★ 첫 턴 입력 전 — 성인식 시작 narrative(부족장 선언)를 첫 화면에 표시
    if (startNarrative) {
      return narrativeStringToData(startNarrative, turnCount);
    }
    // ★ DEMO fallback 금지 (harness 재설계) — 데모 스토리 대신 명시적 시작 안내
    return {
      turn: turnCount,
      paragraphs: [
        { spans: [{ kind: "plain", text: "행동을 입력해 모험을 시작하세요." }] },
      ],
    };
  }, [freeform.lastResponse, turnCount, startNarrative]);

  // ★ 추천 행동 버튼 — 응답의 suggested_actions, 첫 화면엔 마을/던전 기본 3항목
  const suggestedActions = useMemo<string[]>(() => {
    const fromResp = freeform.lastResponse?.suggested_actions;
    if (fromResp && fromResp.length > 0) return fromResp;
    if (!freeform.lastResponse) {
      return inVillage
        ? ["주변을 둘러본다", "부족장에게 말을 건다", "무기를 점검한다"]
        : ["주변을 살핀다", "앞으로 나아간다", "잠시 쉰다"];
    }
    return [];
  }, [freeform.lastResponse, inVillage]);

  // ★ NPC 대화(case A) — handle_dialogue narrative의 큰따옴표 발화 감지 → 전용 UI
  const dialogueData = useMemo<ParsedDialogue>(
    () =>
      freeform.lastResponse
        ? parseDialogue(freeform.lastResponse.narrative)
        : { isDialogue: false, speaker: "대화 상대", segments: [] },
    [freeform.lastResponse],
  );

  // 새 응답이 대화면 전용 UI 자동 표시 (turnCount = 응답 수신 트리거)
  useEffect(() => {
    if (turnCount > 0 && dialogueData.isDialogue) setDialogueOpen(true);
  }, [turnCount, dialogueData.isDialogue]);

  const handleShortcut = useCallback((key: string) => {
    if (key === "c" || key === "p") setCharOpen(true);
  }, []);

  useKeyboard(
    (key) => {
      if (key === "Escape") {
        if (essenceOpen) {
          setEssenceOpen(false);
          return;
        }
        if (charOpen) {
          setCharOpen(false);
          return;
        }
        inputRef.current?.blur();
        return;
      }
      if (key === "/") {
        inputRef.current?.focus();
        return;
      }
      handleShortcut(key.toLowerCase());
    },
    { enabled: true, ignoreWhenInput: true },
  );

  return (
    <div
      className="grid h-screen grid-rows-[50px_1fr_70px] overflow-hidden bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: `url(${bgUrl})` }}
      data-testid="game-background"
    >
      <StatusBar data={statusData} onMenu={() => setMenuOpen((v) => !v)} />

      <div
        className={
          inVillage
            ? "overflow-hidden bg-bg-deep/80"
            : "grid grid-cols-[1.4fr_1fr] overflow-hidden"
        }
      >
        {/* ★ 던전맵은 floor 1+ 에서만 (성인식 마을 floor 0 미표시 — 비주얼 후속) */}
        {!inVillage && <DungeonView data={DEMO_DUNGEON} />}

        <div
          className={
            inVillage
              ? "grid grid-rows-[1fr_230px] overflow-hidden bg-bg-deep/80"
              : "grid grid-rows-[1fr_220px_230px] overflow-hidden bg-bg-deep/80"
          }
        >
          <NarrativePanel data={narrativeData} />
          {/* ★ 조우 패널은 던전에서만 (성인식 마을 미표시) */}
          {!inVillage && (
            <EncounterPanel
              data={encounterData}
              onAction={(id) => {
                if (id === "talk" || id === "attack" || id === "rest") {
                  void execute({ action_type: id });
                }
              }}
            />
          )}
          <InventoryPanel data={inventoryData} />
        </div>
      </div>

      <InputBar
        ref={inputRef}
        onSubmit={handleSubmit}
        onShortcut={handleShortcut}
        disabled={executing || freeform.loading}
        placeholder={
          inVillage
            ? "무엇을 할지 입력하세요  ·  예: 부족장에게 다가가 말을 건다"
            : "무엇을 할지 입력하세요  ·  예: 주변을 살핀다"
        }
      />

      {/* ★ 추천 행동 버튼 — placeholder 힌트 대신 클릭 가능한 3항목 */}
      <SuggestedActions
        actions={suggestedActions}
        onSelect={handleSubmit}
        disabled={executing || freeform.loading}
      />

      {/* ★ NPC 대화 전용 UI (case A) — narrative 큰따옴표 발화 → ui_dialogue 프레임 */}
      <DialogueView
        data={dialogueData}
        open={dialogueOpen}
        onClose={() => setDialogueOpen(false)}
      />

      {freeform.error && (
        <div className="pointer-events-none absolute bottom-[80px] left-1/2 -translate-x-1/2 border border-crimson bg-bg-deep/90 px-4 py-2 font-mono text-xs text-crimson">
          {freeform.error}
        </div>
      )}

      <PartyPanel
        data={partyData}
        onMember={(id) => {
          if (id === "self") setCharOpen(true);
        }}
      />

      {charSheetData != null && (
        <CharacterSheetModal
          data={charSheetData}
          open={charOpen}
          onClose={() => setCharOpen(false)}
          onEssenceClick={() => setEssenceOpen(true)}
        />
      )}

      <EssenceDetailModal
        data={DEMO_ESSENCE}
        open={essenceOpen}
        onClose={() => setEssenceOpen(false)}
      />

      {/* ★ 메뉴 — ≡ MENU onClick → 캐릭터 · 지도 · 도움말 */}
      <GameMenu
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onCharacter={() => setCharOpen(true)}
        onMap={() => setMapOpen(true)}
        onHelp={() => setHelpOpen(true)}
      />

      <MapPanel
        open={mapOpen}
        onClose={() => setMapOpen(false)}
        floor={data?.state.location?.floor ?? null}
        subArea={data?.state.location?.sub_area ?? null}
        riftId={data?.state.location?.rift_id ?? null}
        activeRifts={data?.state.world?.active_rifts ?? []}
      />

      <HelpPanel open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
