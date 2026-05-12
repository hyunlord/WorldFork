"use client";

/**
 * Gameplay Screen — Phase 7d implement (★ Phase 6 gameplay_screen.html → React).
 *
 * 본 page 본격:
 * - useGameState + useRecentActions (두 hook)
 * - 5 components 본격 (GameHUD, Minimap, Narrative, ActionGrid, PartyPortraits)
 * - 좌상 HUD / 우상 위치 + 시간 / 중상 파티 / 좌하 미니맵 / 중 내러티브 / 우하 행동
 */

import { useCallback } from "react";

import { GameLayout } from "@/components/GameLayout";
import { ActionGrid } from "@/components/game/ActionGrid";
import { GameHUD } from "@/components/game/GameHUD";
import { Minimap } from "@/components/game/Minimap";
import { Narrative } from "@/components/game/Narrative";
import { PartyPortraits } from "@/components/game/PartyPortraits";
import { useGameState } from "@/lib/hooks/useGameState";
import { useRecentActions } from "@/lib/hooks/useRecentActions";

const MAX_HOURS = 168;

export default function GamePage() {
  const { data, loading, error } = useGameState();
  const { data: actionsData } = useRecentActions(5);

  const handleAction = useCallback((actionId: string) => {
    // ★ Phase 7d: console.log only — POST API 본격 7h
    // eslint-disable-next-line no-console
    console.log("Action selected:", actionId);
  }, []);

  if (loading) {
    return (
      <GameLayout>
        <div className="screen gameplay-screen-bg">
          <div className="loading-center">불러오는 중...</div>
        </div>
      </GameLayout>
    );
  }

  if (error || !data) {
    return (
      <GameLayout>
        <div className="screen gameplay-screen-bg">
          <div className="error-center">
            상태 API 본격 X: {error?.message ?? "no data"}
          </div>
        </div>
      </GameLayout>
    );
  }

  const characters = data.state.characters;
  const world = data.state.world;
  const location = data.state.location;

  const hoursInDungeon = world.hours_in_dungeon ?? 0;
  const hoursRemaining = Math.max(0, MAX_HOURS - hoursInDungeon);

  const subArea = location.sub_area ?? "진입점";
  const inRift = Boolean(location.rift_id);

  const actions = actionsData?.actions ?? [];

  return (
    <GameLayout>
      <div className="screen gameplay-screen-bg">
        {/* 좌상단 HUD */}
        <GameHUD characters={characters} />

        {/* 우상단 위치 / 잔여 시간 */}
        <div className="game-hud-right">
          <div className="dungeon-time-hud">
            <div className="time-label">미궁 잔여</div>
            <div className="hours-remaining">{hoursRemaining}h</div>
          </div>
          <div className="location-info">
            <div>현재 위치</div>
            <div className="location-name">{subArea}</div>
          </div>
        </div>

        {/* 중상단 파티 */}
        <PartyPortraits characters={characters} />

        {/* 좌하단 미니맵 */}
        <Minimap currentSubArea={subArea} />

        {/* 중앙 내러티브 */}
        <Narrative turn={data.turn} recentActions={actions} />

        {/* 우하단 행동 13 */}
        <ActionGrid
          onAction={handleAction}
          inRift={inRift}
          hasFloatingEssence={false}
        />
      </div>
    </GameLayout>
  );
}
