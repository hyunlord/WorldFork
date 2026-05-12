"use client";

/**
 * Character Sheet — Phase 7b skeleton (★ raw Character V2 preview).
 */

import { GameLayout } from "@/components/GameLayout";
import { useGameState } from "@/lib/hooks/useGameState";

export default function CharacterPage() {
  const { data, loading } = useGameState();
  const chars = data?.state.characters ?? {};

  return (
    <GameLayout>
      <div className="screen character-screen">
        <h2>캐릭터 시트</h2>
        {loading ? (
          <div className="loading">불러오는 중...</div>
        ) : (
          Object.entries(chars).map(([name, c]) => (
            <section key={name} className="character-section">
              <h3>{name}</h3>
              <pre className="state-preview">
                {JSON.stringify(c, null, 2)}
              </pre>
            </section>
          ))
        )}
      </div>
    </GameLayout>
  );
}
