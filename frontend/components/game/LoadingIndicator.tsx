"use client";

interface Props {
  visible: boolean;
}

/**
 * LLM 호출 중 표시 — GB10 환경에서 narrative 생성은 10-16초 걸린다.
 *
 * 직전엔 입력/버튼 disabled만 걸려 화면이 정지한 듯 보였다. 호출 동안
 * 회전 룬 + "이야기를 짓는 중"으로 진행을 가시화해 멈춘 느낌을 없앤다.
 */
export function LoadingIndicator({ visible }: Props) {
  if (!visible) return null;

  return (
    <div
      data-testid="loading-indicator"
      className="pointer-events-none absolute bottom-[78px] left-1/2 z-[75] flex -translate-x-1/2 items-center gap-2.5 border border-amber/50 bg-bg-deep/90 px-4 py-2 font-mono text-[0.82rem] text-amber [box-shadow:0_0_16px_var(--torch-glow)]"
    >
      <span className="inline-block animate-spin text-amber-bright">◆</span>
      <span className="animate-pulse tracking-[0.1em]">이야기를 짓는 중…</span>
    </div>
  );
}
