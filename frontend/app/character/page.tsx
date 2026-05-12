"use client";

/**
 * Character Sheet — Phase 7e implement (★ Phase 6 character_sheet.html → React).
 *
 * 본 page 본격:
 * - CharacterTab 본격 비요른 / 에르웬 선택
 * - 3-column grid: 좌 풀바디 / 중 stats+정수+마석 / 우 스킬
 * - useGameState 본격 binding
 */

import { useEffect, useState } from "react";

import { GameLayout } from "@/components/GameLayout";
import { CharacterPortraitFull } from "@/components/character/CharacterPortraitFull";
import { CharacterTab } from "@/components/character/CharacterTab";
import { EssenceSlots } from "@/components/character/EssenceSlots";
import { MageStones } from "@/components/character/MageStones";
import { SkillsPanel } from "@/components/character/SkillsPanel";
import { StatsPanel } from "@/components/character/StatsPanel";
import { useGameState } from "@/lib/hooks/useGameState";

const PORTRAIT_FULL_BY_NAME: Record<string, string> = {
  비요른: "/assets/worldfork/ui_character_bjorn.png",
  에르웬: "/assets/worldfork/ui_character_erwen.png",
};

interface InventoryShape {
  items?: Record<string, unknown>[];
}

export default function CharacterPage() {
  const { data, loading, error } = useGameState();
  const [selected, setSelected] = useState<string>("");

  const characters = data?.state.characters ?? {};
  const names = Object.keys(characters);

  useEffect(() => {
    if (!selected && names.length > 0) {
      setSelected(names[0]);
    }
  }, [names, selected]);

  if (loading) {
    return (
      <GameLayout>
        <div className="screen character-screen-bg">
          <div className="loading-center">불러오는 중...</div>
        </div>
      </GameLayout>
    );
  }

  if (error || !data) {
    return (
      <GameLayout>
        <div className="screen character-screen-bg">
          <div className="error-center">
            상태 API 본격 X: {error?.message ?? "no data"}
          </div>
        </div>
      </GameLayout>
    );
  }

  const character = characters[selected];
  if (!character) {
    return (
      <GameLayout>
        <div className="screen character-screen-bg">
          <CharacterTab
            names={names}
            selected={selected}
            onSelect={setSelected}
          />
          <div className="empty-message">캐릭터를 선택하세요.</div>
        </div>
      </GameLayout>
    );
  }

  const portraitSrc =
    PORTRAIT_FULL_BY_NAME[selected] ??
    "/assets/worldfork/ui_character_bjorn.png";

  const race =
    typeof character.race === "string" ? character.race : undefined;

  const essences = Array.isArray(character.essences)
    ? (character.essences as Record<string, unknown>[])
    : [];

  const inventory = (character.inventory ?? {}) as InventoryShape;
  const items = inventory.items ?? [];

  return (
    <GameLayout>
      <div className="screen character-screen-bg">
        <CharacterTab
          names={names}
          selected={selected}
          onSelect={setSelected}
        />

        <div className="character-grid">
          <div className="character-grid-left">
            <CharacterPortraitFull
              name={selected}
              imageSrc={portraitSrc}
              race={race}
            />
          </div>

          <div className="character-grid-center">
            <StatsPanel character={character} />
            <EssenceSlots essences={essences} />
            <MageStones items={items} />
          </div>

          <div className="character-grid-right">
            <SkillsPanel essences={essences} />
          </div>
        </div>
      </div>
    </GameLayout>
  );
}
