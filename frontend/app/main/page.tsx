"use client";

/**
 * Main Screen — Phase 7b skeleton (★ characters preview).
 */

import { GameLayout } from "@/components/GameLayout";
import { useGameState } from "@/lib/hooks/useGameState";

export default function MainPage() {
  const { data, loading } = useGameState();

  return (
    <GameLayout>
      <div className="screen main-screen">
        <h2>메인 화면</h2>
        {loading ? (
          <div className="loading">불러오는 중...</div>
        ) : (
          <pre className="state-preview">
            {JSON.stringify(data?.state.characters, null, 2)}
          </pre>
        )}
      </div>
    </GameLayout>
  );
}
