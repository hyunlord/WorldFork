"use client";

import { useEffect } from "react";
import type {
  EssenceAbilityCategory,
  EssenceCategoryKind,
  EssenceDetailData,
  EssenceSkill,
  EssenceTotalEffect,
} from "./types";

interface Props {
  data: EssenceDetailData | null;
  open: boolean;
  onClose: () => void;
  onRemove?: () => void;
  onUpgrade?: () => void;
}

const CAT_BORDER: Record<EssenceCategoryKind, string> = {
  combat: "border-l-crimson",
  physical: "border-l-amber",
  sensory: "border-l-success",
  social: "border-l-cyan",
  mystic: "border-l-arcane",
  mental: "border-l-gold",
};

function AbilityCat({ cat }: { cat: EssenceAbilityCategory }) {
  return (
    <div
      className={`flex flex-col gap-1.5 border border-border-rune border-l-[3px] bg-bg-elev px-3.5 py-2.5 ${CAT_BORDER[cat.kind]}`}
    >
      <span className="font-mono text-[0.6rem] uppercase tracking-[0.2em] text-text-mute">
        {cat.label}
      </span>
      <div className="flex flex-col gap-1">
        {cat.items.map((item, i) => (
          <div
            key={i}
            className="flex items-center justify-between text-[0.82rem]"
          >
            <span className="font-serif text-text-bright">{item.name}</span>
            <span
              className={`font-mono text-[0.75rem] font-bold ${item.unknown ? "italic font-narrative text-text-mute" : "text-amber-bright"}`}
            >
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SkillRow({ skill }: { skill: EssenceSkill }) {
  return (
    <div className="flex items-center justify-between border border-border-rune border-l-[3px] border-l-arcane bg-bg-elev px-4 py-2.5">
      <div className="flex flex-col gap-0.5">
        <span className="font-serif text-[0.95rem] font-bold text-text-bright">
          {skill.name}
        </span>
        <span className="font-mono text-[0.65rem] tracking-[0.1em] text-text-mute">
          {skill.meta}
        </span>
        {skill.desc && (
          <span
            className={`mt-0.5 font-narrative text-[0.78rem] italic ${skill.dormant ? "text-text-mute" : "text-text-mid"}`}
          >
            {skill.desc}
          </span>
        )}
      </div>
      <span
        className={`font-mono text-[0.85rem] font-bold ${skill.dormant ? "italic text-text-mute" : "text-amber-bright"}`}
      >
        {skill.level}
      </span>
    </div>
  );
}

function TotalItem({ item }: { item: EssenceTotalEffect }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-[0.6rem] uppercase tracking-[0.15em] text-text-mute">
        {item.label}
      </span>
      <span
        className={`font-mono text-base font-bold [text-shadow:0_0_6px_var(--torch-glow)] ${item.minus ? "text-crimson [text-shadow:0_0_6px_rgba(214,59,59,0.4)]" : "text-amber-bright"}`}
      >
        {item.value}
      </span>
    </div>
  );
}

export function EssenceDetailModal({
  data,
  open,
  onClose,
  onRemove,
  onUpgrade,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open || !data) return null;

  return (
    <div
      className="fixed inset-0 z-[110] flex animate-backdrop-in items-center justify-center bg-[rgba(5,5,8,0.88)] p-8 backdrop-blur-[6px]"
      onClick={onClose}
    >
      <div
        className="relative grid max-h-[90vh] w-full max-w-[720px] animate-modal-in grid-rows-[auto_1fr_auto] overflow-hidden border border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel [box-shadow:0_24px_64px_rgba(0,0,0,0.8),0_0_32px_var(--torch-glow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="pointer-events-none absolute inset-x-[5%] top-0 h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-60" />

        <header className="flex items-center justify-between border-b border-border-rune bg-gradient-to-r from-amber/[0.06] to-transparent px-7 py-5">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 animate-torch-flicker items-center justify-center border border-amber bg-bg-void font-mono text-3xl font-bold text-amber-bright [text-shadow:0_0_12px_var(--torch-glow)]">
              ◆
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
                {data.rank}
              </span>
              <span className="font-serif text-2xl font-bold tracking-[0.05em] text-text-bright">
                {data.name}
              </span>
              {data.subtitle && (
                <span className="font-narrative text-[0.85rem] italic text-text-mute">
                  {data.subtitle}
                </span>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 cursor-pointer items-center justify-center border border-border-rune bg-transparent text-lg text-text-mute hover:border-amber hover:text-amber"
          >
            ×
          </button>
        </header>

        <div className="overflow-y-auto px-7 py-6">
          <section className="mb-6">
            <div className="mb-3 flex items-center gap-2 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
              <span className="text-amber-bright">◆</span>
              <span>정의 · 본문 정합</span>
            </div>
            <div className="essence-desc border-l-[3px] border-amber bg-amber/[0.04] px-5 py-4 font-narrative text-[0.95rem] italic leading-[1.85] text-text-bright">
              {data.description}
            </div>
          </section>

          <section className="mb-6">
            <div className="mb-3 flex items-center gap-2 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
              <span className="text-amber-bright">◆</span>
              <span>능력치 · 효과</span>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {data.abilities.map((cat, i) => (
                <AbilityCat key={i} cat={cat} />
              ))}
            </div>
          </section>

          <section className="mb-6">
            <div className="mb-3 flex items-center gap-2 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
              <span className="text-amber-bright">◆</span>
              <span>부여 스킬 · 능동/수동</span>
            </div>
            <div className="flex flex-col gap-2">
              {data.skills.map((s, i) => (
                <SkillRow key={i} skill={s} />
              ))}
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-center gap-2 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
              <span className="text-amber-bright">◆</span>
              <span>정수 총 효과</span>
            </div>
            <div className="border border-amber bg-gradient-to-br from-amber/[0.08] to-arcane/[0.04] px-5 py-4">
              <div className="mt-2 grid grid-cols-3 gap-3.5">
                {data.totals.map((t, i) => (
                  <TotalItem key={i} item={t} />
                ))}
              </div>
              {data.sourceCitation && (
                <div className="mt-3 border-t border-dashed border-border-rune/40 pt-2 font-mono text-[0.65rem] tracking-[0.05em] text-text-mute">
                  <strong className="text-cyan">SRC</strong>{" "}
                  {data.sourceCitation}
                </div>
              )}
            </div>
          </section>
        </div>

        <footer className="flex items-center justify-between border-t border-border-rune bg-bg-deep px-7 py-4">
          <span className="font-mono text-[0.7rem] tracking-[0.1em] text-text-mute">
            {data.footerMeta ?? "★ Phase C audit 후 본문 정합"}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onRemove}
              className="cursor-pointer border border-border-rune bg-bg-elev px-4 py-2 font-sans text-[0.85rem] text-text-bright transition hover:border-crimson hover:bg-crimson/[0.08] hover:text-crimson"
            >
              정수 제거
            </button>
            <button
              type="button"
              onClick={onUpgrade}
              className="cursor-pointer border border-border-rune bg-bg-elev px-4 py-2 font-sans text-[0.85rem] text-text-bright transition hover:border-amber hover:bg-amber/5 hover:text-amber"
            >
              스킬 강화
            </button>
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer border border-amber bg-gradient-to-b from-amber/20 to-amber/[0.08] px-4 py-2 font-sans text-[0.85rem] font-bold text-amber-bright"
            >
              닫기
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
