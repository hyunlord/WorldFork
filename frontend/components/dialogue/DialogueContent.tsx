"use client";

/**
 * DialogueContent — 중앙 대화 박스 (★ 좌상단 화살표 본격).
 *
 * Phase 6 dialogue_screen.html .dialogue-text-box 정합.
 */

interface DialogueContentProps {
  speakerLabel?: string;
  text: string;
  narration?: string;
}

export function DialogueContent({
  speakerLabel,
  text,
  narration,
}: DialogueContentProps) {
  return (
    <div className="dialogue-text-box">
      {speakerLabel && (
        <div className="dialogue-speaker-label">▸ {speakerLabel}</div>
      )}
      <div className="dialogue-content-body">
        {text || "대화 본격 X."}
        {narration && <div className="narration">{narration}</div>}
      </div>
    </div>
  );
}
