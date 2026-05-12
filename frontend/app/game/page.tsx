"use client";

/**
 * Gameplay Screen — Phase 7b skeleton (★ HUD 3-column).
 */

import { GameLayout } from "@/components/GameLayout";
import { useGameState } from "@/lib/hooks/useGameState";

export default function GamePage() {
  const { data, loading } = useGameState();

  if (loading) {
    return (
      <GameLayout>
        <div className="loading">불러오는 중...</div>
      </GameLayout>
    );
  }

  const chars = data?.state.characters ?? {};
  const location = data?.state.location;
  const world = data?.state.world;

  return (
    <GameLayout>
      <div className="screen gameplay-screen">
        <div className="hud-left">
          {Object.entries(chars).map(([name, c]) => (
            <div key={name} className="character-hud">
              <h3>{name}</h3>
              <div>HP: {String(c.hp)}/{String(c.hp_max)}</div>
              <div>Race: {String(c.race)}</div>
            </div>
          ))}
        </div>
        <div className="hud-center">
          <div>위치: {location?.sub_area ?? "unknown"}</div>
          <div>Realm: {location?.realm ?? "?"}</div>
          <div>
            Rift: {location?.rift_id ? location.rift_id : "(밖)"}
          </div>
          <div>
            활성 균열: {world?.active_rifts.length ?? 0}개
          </div>
          <div>경과: {world?.hours_in_dungeon ?? 0}h</div>
        </div>
        <div className="hud-right">
          <h3>파티</h3>
          <ul>
            {(world?.party_members ?? []).map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      </div>
    </GameLayout>
  );
}
