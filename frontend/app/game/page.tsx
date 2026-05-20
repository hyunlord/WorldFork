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
  NarrativePanelData,
  StatusBarData,
} from "@/components/game/types";
import {
  DEMO_CHARACTER,
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

const MAX_HOURS = 174;

function narrativeStringToData(
  text: string,
  turn: number,
): NarrativePanelData {
  const paragraphs = text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0)
    .map((p) => ({ spans: [{ kind: "plain" as const, text: p }] }));
  return {
    turn,
    paragraphs: paragraphs.length > 0 ? paragraphs : DEMO_NARRATIVE.paragraphs,
  };
}

export default function GamePage() {
  const { data } = useGameState();
  const { execute, executing } = usePostAction();
  const freeform = useFreeformAction();
  const inputRef = useRef<InputBarHandle>(null);

  const [charOpen, setCharOpen] = useState(false);
  const [essenceOpen, setEssenceOpen] = useState(false);
  const [turnCount, setTurnCount] = useState(DEMO_NARRATIVE.turn);

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
    const characters = data.state.characters ?? {};
    const player =
      Object.values(characters).find(
        (c) => (c as { is_player?: boolean }).is_player,
      ) ?? null;
    const hp = (player?.hp as number | undefined) ?? 75;
    const hpMax = (player?.hp_max as number | undefined) ?? 100;
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
    };
  }, [data]);

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
      return narrativeStringToData(
        freeform.lastResponse.narrative,
        turnCount,
      );
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
          <InventoryPanel data={DEMO_INVENTORY} />
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
        data={DEMO_PARTY}
        onMember={(id) => {
          if (id === "self") setCharOpen(true);
        }}
      />

      <CharacterSheetModal
        data={DEMO_CHARACTER}
        open={charOpen}
        onClose={() => setCharOpen(false)}
        onEssenceClick={() => setEssenceOpen(true)}
      />

      <EssenceDetailModal
        data={DEMO_ESSENCE}
        open={essenceOpen}
        onClose={() => setEssenceOpen(false)}
      />
    </div>
  );
}
