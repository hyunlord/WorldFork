"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { CharacterSheetModal } from "@/components/game/CharacterSheetModal";
import { DungeonView } from "@/components/game/DungeonView";
import { EncounterPanel } from "@/components/game/EncounterPanel";
import { EssenceDetailModal } from "@/components/game/EssenceDetailModal";
import { InputBar, type InputBarHandle } from "@/components/game/InputBar";
import { InventoryPanel } from "@/components/game/InventoryPanel";
import { NarrativePanel } from "@/components/game/NarrativePanel";
import { PartyPanel } from "@/components/game/PartyPanel";
import { StatusBar } from "@/components/game/StatusBar";
import type {
  CharacterListRow,
  CharacterSheetData,
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
import {
  DEMO_DUNGEON,
  DEMO_ENCOUNTER,
  DEMO_ESSENCE,
  DEMO_INVENTORY,
  DEMO_NARRATIVE,
  DEMO_PARTY,
} from "@/lib/game/mockData";
import { useFreeformAction } from "@/lib/hooks/useFreeformAction";
import { useGameState } from "@/lib/hooks/useGameState";
import { useKeyboard } from "@/lib/hooks/useKeyboard";
import { usePostAction } from "@/lib/hooks/usePostAction";
import { RACES } from "@/lib/types/character";
import type { CharacterV2, StateResponse } from "@/lib/api/v2";

const MAX_HOURS = 174;

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
  const paragraphs = text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0)
    .map((p) => ({ spans: paragraphToSpans(p) }));
  return {
    turn,
    paragraphs: paragraphs.length > 0 ? paragraphs : DEMO_NARRATIVE.paragraphs,
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

  const skillRows: CharacterListRow[] = traits.map((t) => ({
    name: t,
    value: "",
  }));

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
  if (!player) return DEMO_INVENTORY;
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
  if (!data) return DEMO_PARTY;
  const chars = Object.values(data.state.characters);
  if (chars.length === 0) return DEMO_PARTY;

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

export default function GamePage() {
  const { data } = useGameState();
  const { execute, executing } = usePostAction();
  const freeform = useFreeformAction();
  const inputRef = useRef<InputBarHandle>(null);

  const [charOpen, setCharOpen] = useState(false);
  const [essenceOpen, setEssenceOpen] = useState(false);
  const [turnCount, setTurnCount] = useState(DEMO_NARRATIVE.turn);

  const player = useMemo<CharacterV2 | null>(() => {
    if (!data) return null;
    const characters = data.state.characters ?? {};
    return (
      (Object.values(characters).find(
        (c) => (c as Record<string, unknown>).is_player === true,
      ) as CharacterV2 | undefined) ?? null
    );
  }, [data]);

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
      essenceMax: level + 1,
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
    return DEMO_NARRATIVE;
  }, [freeform.lastResponse, turnCount]);

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
    <div className="grid h-screen grid-rows-[50px_1fr_70px] overflow-hidden">
      <StatusBar data={statusData} />

      <div className="grid grid-cols-[1.4fr_1fr] overflow-hidden">
        <DungeonView data={DEMO_DUNGEON} />

        <div className="grid grid-rows-[1fr_220px_230px] overflow-hidden bg-bg-deep">
          <NarrativePanel data={narrativeData} />
          <EncounterPanel
            data={DEMO_ENCOUNTER}
            onAction={(id) => {
              if (id === "talk" || id === "attack" || id === "rest") {
                void execute({ action_type: id });
              }
            }}
          />
          <InventoryPanel data={inventoryData} />
        </div>
      </div>

      <InputBar
        ref={inputRef}
        onSubmit={handleSubmit}
        onShortcut={handleShortcut}
        disabled={executing || freeform.loading}
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
    </div>
  );
}
