"use client";

interface Props {
  actions: string[];
  onSelect: (action: string) => void;
  disabled?: boolean;
}

/**
 * 추천 행동 버튼 — freeform 응답의 suggested_actions(또는 시작 시 기본 3항목).
 *
 * placeholder 힌트만 있던 자리에 실제 클릭 가능한 행동 버튼을 노출한다.
 * 클릭 시 해당 문구를 그대로 freeform 입력으로 제출(onSelect → handleSubmit).
 */
export function SuggestedActions({ actions, onSelect, disabled }: Props) {
  if (actions.length === 0) return null;

  return (
    <div
      data-testid="suggested-actions"
      className="pointer-events-none absolute bottom-[78px] left-1/2 z-[70] flex -translate-x-1/2 flex-wrap justify-center gap-2 px-6"
    >
      {actions.map((action, i) => (
        <button
          key={i}
          type="button"
          data-testid="suggested-action"
          onClick={() => onSelect(action)}
          disabled={disabled}
          className="pointer-events-auto cursor-pointer border border-amber/50 bg-bg-deep/90 px-3.5 py-1.5 font-sans text-[0.82rem] text-amber transition hover:border-amber hover:bg-amber/10 hover:[box-shadow:0_0_12px_var(--torch-glow)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {action}
        </button>
      ))}
    </div>
  );
}
