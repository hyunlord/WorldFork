"use client";

import { useEffect } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

interface HelpRow {
  key: string;
  desc: string;
}

interface HelpSection {
  header: string;
  rows: HelpRow[];
}

// 조작/시스템 설명 — InputBar 단축키 + 정수·element 전투·진행 시스템 정합.
const SECTIONS: HelpSection[] = [
  {
    header: "조작",
    rows: [
      { key: "채팅 입력 → Enter", desc: "자연어로 행동을 입력해 진행" },
      { key: "/", desc: "입력창 포커스" },
      { key: "C · P", desc: "캐릭터 시트 열기" },
      { key: "≡ 메뉴", desc: "캐릭터 · 지도 · 도움말" },
      { key: "Esc", desc: "열린 창 닫기 / 입력 해제" },
    ],
  },
  {
    header: "시스템",
    rows: [
      { key: "정수 흡수", desc: "쓰러뜨린 적의 정수를 영혼에 담아 능력 획득" },
      { key: "element 전투", desc: "무기·정수의 속성이 적 약점에 작용" },
      { key: "영혼력 · 레벨", desc: "행동·흡수로 성장 — 상단 바에 표시" },
      { key: "잔여 시간", desc: "168시간 주기 — 균열 안 체류 한계" },
    ],
  },
];

/**
 * 메뉴 도움말 — 조작 단축키 + 핵심 시스템(정수/element/진행/시간) 설명.
 */
export function HelpPanel({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex animate-backdrop-in items-center justify-center bg-[rgba(5,5,8,0.85)] backdrop-blur-[4px]"
      onClick={onClose}
      data-testid="help-panel"
    >
      <div
        className="relative w-[90%] max-w-[560px] animate-modal-in overflow-hidden border border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel [box-shadow:0_24px_64px_rgba(0,0,0,0.8),0_0_32px_var(--torch-glow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="pointer-events-none absolute inset-x-[5%] top-0 h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-60" />

        <header className="flex items-center justify-between border-b border-border-rune bg-bg-deep px-7 py-4">
          <span className="font-serif text-xl font-bold tracking-[0.05em] text-amber-bright [text-shadow:0_0_12px_var(--torch-glow)]">
            ◆ 도움말
          </span>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 cursor-pointer items-center justify-center border border-border-rune bg-transparent text-lg text-text-mute hover:border-amber hover:text-amber"
            aria-label="도움말 닫기"
          >
            ×
          </button>
        </header>

        <div className="px-7 py-6">
          {SECTIONS.map((sec) => (
            <section key={sec.header} className="mb-6 last:mb-0">
              <div className="mb-3 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
                {sec.header}
              </div>
              {sec.rows.map((row, i) => (
                <div
                  key={i}
                  className="flex items-start justify-between gap-4 border-b border-dashed border-border-rune/30 py-2.5 last:border-b-0"
                >
                  <span className="min-w-[130px] font-mono text-[0.8rem] font-bold tracking-[0.05em] text-amber-bright">
                    {row.key}
                  </span>
                  <span className="flex-1 text-right font-sans text-[0.85rem] text-text-mid">
                    {row.desc}
                  </span>
                </div>
              ))}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
