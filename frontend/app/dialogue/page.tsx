"use client";

/**
 * Dialogue Screen — Phase 7b skeleton (★ 본격 implement 7f).
 */

import { GameLayout } from "@/components/GameLayout";
import { useGameState } from "@/lib/hooks/useGameState";

export default function DialoguePage() {
  const { data, loading } = useGameState();

  return (
    <GameLayout>
      <div className="screen dialogue-screen">
        <h2>대화</h2>
        {loading ? (
          <div className="loading">불러오는 중...</div>
        ) : (
          <>
            <div className="dialogue-placeholder">
              💬 본격 implement 본격 (★ 7f)
            </div>
            <pre className="state-preview">
              Turn: {data?.turn} · 위치: {data?.state.location.sub_area}
            </pre>
          </>
        )}
      </div>
    </GameLayout>
  );
}
