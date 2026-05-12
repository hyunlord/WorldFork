"use client";

/**
 * CombatLog — 우 하단 전투 로그 본격.
 *
 * Phase 6 combat_screen.html .log 정합.
 */

interface CombatLogProps {
  entries: Record<string, unknown>[];
}

function actorColorClass(actor: string): string {
  if (actor === "비요른") return "bjorn";
  if (actor === "에르웬") return "erwen";
  if (actor === "GM" || actor === "enemy") return "enemy";
  return "";
}

export function CombatLog({ entries }: CombatLogProps) {
  return (
    <div className="combat-log">
      <div className="log-title">▣ 전투 로그</div>
      {entries.length === 0 ? (
        <div className="empty-message">전투 시작 대기 중...</div>
      ) : (
        entries.map((entry, i) => {
          const actor =
            (entry.actor_name as string | undefined) ??
            (entry.actor as string | undefined) ??
            "GM";
          const description =
            (entry.description as string | undefined) ??
            (entry.narration as string | undefined) ??
            (entry.message as string | undefined) ??
            JSON.stringify(entry).slice(0, 120);
          return (
            <div key={i} className="log-entry">
              <span className={`actor ${actorColorClass(actor)}`}>
                {actor}
              </span>{" "}
              {description}
            </div>
          );
        })
      )}
    </div>
  );
}
