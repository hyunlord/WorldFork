"use client";

/**
 * Combat — Phase 7g implement (★ Phase 6 combat_screen.html → React).
 *
 * 본 page 본격:
 * - useGameState + useRecentActions
 * - current_encounter 본격 binding (★ 본 commit 본격 7a v2 API X — idle 본격)
 * - 좌 파티 / 우 적 / 중앙 VFX / 하단 행동 / 우 하단 로그
 *
 * 본격 본질:
 * - 본 commit 본격 components skeleton 본격 (★ encounter 본격 X)
 * - 7j 본격 active_encounters API 본격 본격 본격 본격 본격
 */

import { useCallback } from "react";

import { GameLayout } from "@/components/GameLayout";
import { CombatActions } from "@/components/combat/CombatActions";
import { CombatHeader } from "@/components/combat/CombatHeader";
import { CombatLog } from "@/components/combat/CombatLog";
import { EnemyCard } from "@/components/combat/EnemyCard";
import { FighterCard } from "@/components/combat/FighterCard";
import { VfxOverlay } from "@/components/combat/VfxOverlay";
import { useGameState } from "@/lib/hooks/useGameState";
import { usePostAction } from "@/lib/hooks/usePostAction";
import { useRecentActions } from "@/lib/hooks/useRecentActions";

const COMBAT_PORTRAIT_BY_NAME: Record<string, string> = {
  비요른: "/assets/worldfork/ui_combat_bjorn_action.png",
  에르웬: "/assets/worldfork/ui_combat_erwen_casting.png",
};

const MONSTER_IMAGE_BY_NAME: Record<string, string> = {
  칼날늑대: "/assets/worldfork/ui_combat_monster_blade_wolf.png",
  blade_wolf: "/assets/worldfork/ui_combat_monster_blade_wolf.png",
};

const DEFAULT_MONSTER_IMAGE =
  "/assets/worldfork/ui_combat_monster_blade_wolf.png";

interface EncounterDetailsLike {
  monster_hp?: number;
  monster_hp_max?: number;
  monster_grade?: number;
  status?: string;
}

interface EncounterLite {
  type?: string;
  name?: string;
  location?: string;
  details?: EncounterDetailsLike;
  spawned_at_turn?: number;
}

export default function CombatPage() {
  const { data, loading, error, refetch: refetchState } = useGameState();
  const { data: actionsData, refetch: refetchActions } = useRecentActions(8);
  const {
    execute,
    executing,
    error: actionError,
  } = usePostAction();

  const handleAction = useCallback(
    async (actionId: string) => {
      const result = await execute({ action_type: actionId });
      if (result) {
        await Promise.all([refetchState(), refetchActions()]);
      }
    },
    [execute, refetchActions, refetchState]
  );

  if (loading) {
    return (
      <GameLayout>
        <div className="screen combat-screen-bg">
          <div className="loading-center">불러오는 중...</div>
        </div>
      </GameLayout>
    );
  }

  if (error || !data) {
    return (
      <GameLayout>
        <div className="screen combat-screen-bg">
          <div className="error-center">
            상태 API 본격 X: {error?.message ?? "no data"}
          </div>
        </div>
      </GameLayout>
    );
  }

  const characters = data.state.characters;
  const characterNames = Object.keys(characters);
  const location = data.state.location;

  // ★ 본 commit: v2 API 본격 current_encounter 본격 X — 본격 idle.
  // 7j 본격 active_encounters expose 후 본격 binding 본격.
  const encounter = (data.state as { current_encounter?: EncounterLite })
    .current_encounter;

  const locationLabel = location.sub_area ?? location.realm ?? null;

  if (!encounter) {
    return (
      <GameLayout>
        <div className="screen combat-screen-bg">
          <CombatHeader round={0} locationLabel={locationLabel} />
          <div className="combat-idle">
            <p>현재 전투 중이 아닙니다.</p>
            <p className="hint">
              탐색 중 적과 마주치면 자동으로 전투가 시작됩니다.
            </p>
            <p className="hint">
              (★ 본 commit skeleton — 본격 encounter binding 7j 본격)
            </p>
          </div>
        </div>
      </GameLayout>
    );
  }

  const details = encounter.details ?? {};
  const monsterName = encounter.name ?? "미상";
  const monsterImg =
    MONSTER_IMAGE_BY_NAME[monsterName] ?? DEFAULT_MONSTER_IMAGE;
  const monsterHp = details.monster_hp ?? 100;
  const monsterMaxHp = details.monster_hp_max ?? monsterHp;
  const round = (encounter.spawned_at_turn ?? 0) + 1;

  return (
    <GameLayout>
      <div className="screen combat-screen-bg">
        <CombatHeader round={round} locationLabel={locationLabel} />

        {/* 좌 파티 */}
        <div className="party-side">
          {characterNames.map((name) => {
            const c = characters[name];
            if (!c) return null;
            const portraitSrc =
              COMBAT_PORTRAIT_BY_NAME[name] ??
              "/assets/worldfork/ui_combat_bjorn_action.png";
            const essences = Array.isArray(c.essences)
              ? (c.essences as { color?: string; name?: string }[])
              : [];
            const soulPower =
              typeof c.soul_power === "number" ? c.soul_power : undefined;
            const soulPowerMax =
              typeof c.soul_power_max === "number"
                ? c.soul_power_max
                : undefined;
            return (
              <FighterCard
                key={name}
                name={name}
                portraitSrc={portraitSrc}
                raceOrClass={
                  typeof c.race === "string" ? c.race : undefined
                }
                hp={typeof c.hp === "number" ? c.hp : 0}
                hpMax={typeof c.hp_max === "number" ? c.hp_max : 0}
                soulPower={soulPower}
                soulPowerMax={soulPowerMax}
                essences={essences}
              />
            );
          })}
        </div>

        {/* 우 적 */}
        <div className="enemy-side">
          <EnemyCard
            name={monsterName}
            imageSrc={monsterImg}
            hp={monsterHp}
            hpMax={monsterMaxHp}
            grade={details.monster_grade}
            status={details.status}
          />
        </div>

        {/* 중앙 VFX */}
        <VfxOverlay damages={[]} />

        {executing && (
          <div className="action-feedback executing">행동 실행 중...</div>
        )}
        {actionError && (
          <div className="action-feedback error">
            행동 실패: {actionError.message}
          </div>
        )}

        {/* 하단 행동 */}
        <CombatActions
          currentTurn={characterNames[0]}
          inCombat={true}
          onAction={handleAction}
        />

        {/* 우 하단 로그 */}
        <CombatLog entries={actionsData?.actions ?? []} />
      </div>
    </GameLayout>
  );
}
