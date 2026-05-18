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
import type { StatusBarData } from "@/components/game/types";
import {
  DEMO_CHARACTER,
  DEMO_DUNGEON,
  DEMO_ENCOUNTER,
  DEMO_ESSENCE,
  DEMO_INVENTORY,
  DEMO_NARRATIVE,
  DEMO_PARTY,
} from "@/lib/game/mockData";
import { useGameState } from "@/lib/hooks/useGameState";
import { useKeyboard } from "@/lib/hooks/useKeyboard";
import { usePostAction } from "@/lib/hooks/usePostAction";

const MAX_HOURS = 174;

export default function GamePage() {
  const { data } = useGameState();
  const { execute, executing } = usePostAction();
  const inputRef = useRef<InputBarHandle>(null);

  const [charOpen, setCharOpen] = useState(false);
  const [essenceOpen, setEssenceOpen] = useState(false);

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
      await execute({ action_type: "natural", rationale: text });
    },
    [execute],
  );

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
          <NarrativePanel data={DEMO_NARRATIVE} />
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
        disabled={executing}
      />

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
