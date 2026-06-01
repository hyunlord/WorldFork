"use client";

import { useEffect } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  onCharacter: () => void;
  onMap: () => void;
  onHelp: () => void;
}

interface MenuItem {
  testid: string;
  label: string;
  glyph: string;
  onSelect: (p: Props) => void;
}

const ITEMS: MenuItem[] = [
  { testid: "menu-character", label: "캐릭터", glyph: "@", onSelect: (p) => p.onCharacter() },
  { testid: "menu-map", label: "지도", glyph: "▦", onSelect: (p) => p.onMap() },
  { testid: "menu-help", label: "도움말", glyph: "?", onSelect: (p) => p.onHelp() },
];

/**
 * StatusBar ≡ MENU 드롭다운 — 캐릭터 · 지도 · 도움말 진입점.
 *
 * 기존 캐릭터(키/PartyPanel)에 더해 지도·도움말 onClick을 한 메뉴로 묶는다.
 * 항목 선택 시 해당 패널을 열고 메뉴를 닫는다.
 */
export function GameMenu(props: Props) {
  const { open, onClose } = props;

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
      className="fixed inset-0 z-[90]"
      onClick={onClose}
      data-testid="game-menu-backdrop"
    >
      <div
        className="absolute right-6 top-[54px] w-[180px] animate-modal-in overflow-hidden border border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel [box-shadow:0_16px_40px_rgba(0,0,0,0.7),0_0_20px_var(--torch-glow)]"
        onClick={(e) => e.stopPropagation()}
        data-testid="game-menu"
      >
        <span className="pointer-events-none absolute inset-x-[8%] top-0 h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-50" />
        {ITEMS.map((item) => (
          <button
            key={item.testid}
            type="button"
            data-testid={item.testid}
            onClick={() => {
              item.onSelect(props);
              onClose();
            }}
            className="flex w-full cursor-pointer items-center gap-3 border-b border-border-rune/40 px-4 py-3 text-left font-serif text-[0.95rem] text-text-mid transition last:border-b-0 hover:bg-amber/[0.08] hover:text-amber"
          >
            <span className="w-5 font-mono text-amber-bright">{item.glyph}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
