"use client";

/**
 * Narrative — 중앙 본격 (★ turn label + GM 응답).
 *
 * Phase 6 gameplay_screen.html .narrative 정합.
 */

interface NarrativeProps {
  turn: number;
  recentActions: Record<string, unknown>[];
}

export function Narrative({ turn, recentActions }: NarrativeProps) {
  const lastAction =
    recentActions.length > 0
      ? recentActions[recentActions.length - 1]
      : null;

  const narration =
    (lastAction?.narration as string | undefined) ??
    (lastAction?.description as string | undefined) ??
    (lastAction?.message as string | undefined);

  return (
    <div className="narrative">
      <div className="turn-label">— 턴 {turn} —</div>
      {narration ? (
        <p>
          <span className="gm-prefix">GM</span>
          {narration}
        </p>
      ) : (
        <p>
          <span className="gm-prefix">GM</span>
          탐사대가 미궁 안으로 발을 들였다. 어둠 속에서 무언가가 기다리고 있다.
        </p>
      )}
    </div>
  );
}
