"use client";

/**
 * Rift Entry — Phase 7b skeleton.
 */

import { GameLayout } from "@/components/GameLayout";
import { useGameState } from "@/lib/hooks/useGameState";

export default function RiftPage() {
  const { data, loading } = useGameState();
  const location = data?.state.location;
  const world = data?.state.world;

  return (
    <GameLayout>
      <div className="screen rift-screen">
        <h2>균열</h2>
        {loading ? (
          <div className="loading">불러오는 중...</div>
        ) : (
          <div className="rift-info">
            <div>현재 realm: <strong>{location?.realm ?? "?"}</strong></div>
            <div>
              안에 있나: <strong>{location?.rift_id ? "Yes" : "No"}</strong>
            </div>
            <div>
              현재 rift_id:{" "}
              <strong>{location?.rift_id ?? "(없음)"}</strong>
            </div>
            <h3>활성 균열</h3>
            {world?.active_rifts.length === 0 ? (
              <div className="empty">
                활성 균열 없음 (★ OFFER_TO_STONE으로 활성화 필요)
              </div>
            ) : (
              <ul>
                {world?.active_rifts.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </GameLayout>
  );
}
