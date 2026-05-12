"use client";

/**
 * ChoiceList — 선택지 본격 (★ tag color 본격).
 *
 * Phase 6 dialogue_screen.html .choices-box 정합.
 */

export type ChoiceTag = "info" | "progress" | "doubt" | "cost" | "neutral";

export interface DialogueChoice {
  id: string;
  text: string;
  tag?: ChoiceTag;
  costLabel?: string;
}

interface ChoiceListProps {
  choices: DialogueChoice[];
  onChoose?: (choiceId: string) => void;
}

const TAG_LABELS: Record<ChoiceTag, string> = {
  info: "정보",
  progress: "진행",
  doubt: "의심",
  cost: "비용",
  neutral: "중립",
};

export function ChoiceList({ choices, onChoose }: ChoiceListProps) {
  if (choices.length === 0) {
    return (
      <div className="choices-box empty">
        <div className="empty-message">현재 선택지가 없다.</div>
      </div>
    );
  }

  return (
    <div className="choices-box">
      <div className="choices-title">▣ 답변 선택</div>
      {choices.map((choice, i) => (
        <button
          key={choice.id}
          type="button"
          className="choice"
          onClick={() => onChoose?.(choice.id)}
        >
          <span className="index">{i + 1}.</span>
          <span className="choice-text">{choice.text}</span>
          {(choice.tag || choice.costLabel) && (
            <span className={`tag ${choice.tag ?? "neutral"}`}>
              {choice.costLabel ?? (choice.tag ? TAG_LABELS[choice.tag] : "")}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
