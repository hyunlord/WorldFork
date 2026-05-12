"use client";

/**
 * Main Screen — Phase 7c implement (★ Phase 6 main_screen.html → React).
 *
 * 본 page 본격:
 * - 5 components 본격 (Logo, MainMenu, CharacterPortrait, DungeonTimer, PartyStats)
 * - useGameState 본격 backend state binding
 * - Phase 6 ui_main_bg.png 본격 background
 */

import { GameLayout } from "@/components/GameLayout";
import { CharacterPortrait } from "@/components/main/CharacterPortrait";
import { DungeonTimer } from "@/components/main/DungeonTimer";
import { Logo } from "@/components/main/Logo";
import { MainMenu } from "@/components/main/MainMenu";
import { PartyStats } from "@/components/main/PartyStats";
import { useGameState } from "@/lib/hooks/useGameState";

const PORTRAIT_BY_NAME: Record<string, string> = {
  비요른: "/assets/worldfork/ui_main_bjorn.png",
  에르웬: "/assets/worldfork/ui_main_erwen.png",
};

const MAX_HOURS = 168;

export default function MainPage() {
  const { data, loading, error } = useGameState();

  if (loading) {
    return (
      <GameLayout>
        <div className="screen main-screen-bg">
          <div className="loading-center">불러오는 중...</div>
        </div>
      </GameLayout>
    );
  }

  if (error || !data) {
    return (
      <GameLayout>
        <div className="screen main-screen-bg">
          <div className="error-center">
            상태 API 본격 X: {error?.message ?? "no data"}
          </div>
        </div>
      </GameLayout>
    );
  }

  const characters = data.state.characters;
  const world = data.state.world;
  const characterNames = Object.keys(characters);

  const hoursInDungeon = world.hours_in_dungeon ?? 0;
  const hoursRemaining = Math.max(0, MAX_HOURS - hoursInDungeon);
  const partySize = characterNames.length;

  return (
    <GameLayout>
      <div className="screen main-screen-bg">
        <DungeonTimer hoursRemaining={hoursRemaining} maxHours={MAX_HOURS} />

        <Logo />

        <PartyStats
          partySize={partySize}
          currentFloor="1층"
          maxFloor="10층"
          dungeonGrade="9등급"
          totalHours={hoursInDungeon}
        />

        <MainMenu />

        {characterNames.map((name, idx) => {
          const c = characters[name];
          if (!c) return null;
          const side: "left" | "right" = idx === 0 ? "left" : "right";
          const imageSrc =
            PORTRAIT_BY_NAME[name] ??
            "/assets/worldfork/ui_main_bjorn.png";
          return (
            <CharacterPortrait
              key={name}
              name={name}
              imageSrc={imageSrc}
              side={side}
              race={typeof c.race === "string" ? c.race : undefined}
              hp={typeof c.hp === "number" ? c.hp : undefined}
              hpMax={typeof c.hp_max === "number" ? c.hp_max : undefined}
            />
          );
        })}
      </div>
    </GameLayout>
  );
}
