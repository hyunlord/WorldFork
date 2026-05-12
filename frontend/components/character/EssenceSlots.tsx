"use client";

/**
 * EssenceSlots — 정수 5 슬롯 (★ state_v2.py 정합).
 *
 * 본문 본격: character.essences (★ list of Essence dict)
 * - color: "빨강" / "파랑" / "초록" / "노랑" / "흰색" / "검정" / "무지개"
 * - name: "고블린 정수" 등
 * - grade: int 9-1
 * - essence_type: "DPS_MELEE" 등
 */

interface EssenceEntry {
  name?: string;
  color?: string;
  grade?: number;
  essence_type?: string;
}

interface EssenceSlotsProps {
  essences: EssenceEntry[];
  maxSlots?: number;
}

const COLOR_TO_CSS: Record<string, string> = {
  빨강: "#c44d4d",
  파랑: "#4d7cc4",
  초록: "#5cb377",
  노랑: "#d4af37",
  흰색: "#e8e8d8",
  검정: "#2a2a2a",
  무지개:
    "linear-gradient(135deg,#c44d4d 0%,#d4af37 25%,#5cb377 50%,#4d7cc4 75%,#a06bd4 100%)",
};

function colorStyle(color?: string): React.CSSProperties {
  if (!color) return { background: "rgba(60,60,60,0.6)" };
  const css = COLOR_TO_CSS[color];
  if (!css) return { background: "#888" };
  if (css.includes("gradient")) {
    return { background: css, boxShadow: `0 0 16px rgba(255,255,255,0.4)` };
  }
  return { backgroundColor: css, boxShadow: `0 0 16px ${css}` };
}

export function EssenceSlots({ essences, maxSlots = 5 }: EssenceSlotsProps) {
  return (
    <div className="essence-slots-panel">
      <div className="panel-title">
        ▣ 정수 슬롯{" "}
        <span className="slot-count">
          {essences.length}/{maxSlots}
        </span>
      </div>
      <div className="essence-slots-row">
        {Array.from({ length: maxSlots }).map((_, i) => {
          const e = essences[i];
          if (!e) {
            return (
              <div key={i} className="essence-slot empty">
                <div className="essence-orb empty" />
                <span className="essence-slot-label">—</span>
              </div>
            );
          }
          return (
            <div
              key={i}
              className="essence-slot filled"
              title={e.name ?? e.color ?? ""}
            >
              <div className="essence-orb filled" style={colorStyle(e.color)} />
              <span className="essence-slot-label">
                {e.color ?? e.name ?? "?"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
