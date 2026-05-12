"use client";

/**
 * Combat Screen — Phase 7b skeleton (★ 본격 implement 7g).
 */

import { GameLayout } from "@/components/GameLayout";
import { useGameState } from "@/lib/hooks/useGameState";

export default function CombatPage() {
  const { data, loading } = useGameState();

  return (
    <GameLayout>
      <div className="screen combat-screen">
        <h2>전투</h2>
        {loading ? (
          <div className="loading">불러오는 중...</div>
        ) : (
          <>
            <div className="combat-placeholder">
              ⚔️ 본격 implement 본격 (★ 7g)
            </div>
            <pre className="state-preview">
              {JSON.stringify(data?.state.characters, null, 2)}
            </pre>
          </>
        )}
      </div>
    </GameLayout>
  );
}
