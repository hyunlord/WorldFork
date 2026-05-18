"use client";

import { useEffect, useState } from "react";
import type {
  CharacterListRow,
  CharacterSheetData,
  CharacterStatBig,
  EssenceSlot,
} from "./types";

interface Props {
  data: CharacterSheetData;
  open: boolean;
  onClose: () => void;
  onEssenceClick?: (slotIdx: number) => void;
}

const TABS = ["스탯", "정수", "스킬", "인벤", "기록"] as const;
type Tab = (typeof TABS)[number];

function BigStat({ stat }: { stat: CharacterStatBig }) {
  const valueCls = stat.unidentified
    ? "italic font-narrative text-text-mute"
    : stat.amber
      ? "text-amber-bright [text-shadow:0_0_6px_var(--torch-glow)]"
      : "text-text-bright";

  if (stat.bar != null) {
    return (
      <div className="mb-3">
        <div className="mb-1 flex justify-between">
          <span className="font-sans text-[0.9rem] text-text-mid">
            {stat.label}
          </span>
          <span className={`font-mono text-[0.95rem] font-bold ${valueCls}`}>
            {stat.value}
          </span>
        </div>
        <div className="relative h-2.5 w-full overflow-hidden border border-border-rune bg-bg-void">
          <div
            className="h-full bg-gradient-to-r from-crimson-dim to-amber [box-shadow:0_0_8px_var(--torch-glow)]"
            style={{ width: `${stat.bar}%` }}
          />
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between border-b border-dashed border-border-rune/30 py-2 last:border-b-0">
      <span className="font-sans text-[0.9rem] text-text-mid">
        {stat.label}
      </span>
      <span className={`font-mono text-[0.95rem] font-bold ${valueCls}`}>
        {stat.value}
      </span>
    </div>
  );
}

function Slot({
  slot,
  idx,
  onClick,
}: {
  slot: EssenceSlot;
  idx: number;
  onClick?: () => void;
}) {
  const stateCls =
    slot.state === "filled"
      ? "border-amber/40 bg-gradient-to-br from-amber/10 to-amber/[0.02]"
      : slot.state === "uncertain"
        ? "border-arcane/40 bg-gradient-to-br from-amber/10 to-amber/[0.02]"
        : slot.state === "locked"
          ? "border-border-rune bg-bg-elev opacity-40"
          : "border-dashed border-border-rune";

  const iconCls =
    slot.state === "filled"
      ? "text-amber-bright"
      : slot.state === "uncertain"
        ? "text-arcane"
        : slot.state === "locked"
          ? "text-text-faint"
          : "text-text-mute";

  const labelCls =
    slot.state === "filled" ? "text-text-bright" : "text-text-mute";

  return (
    <button
      type="button"
      onClick={onClick}
      data-slot-idx={idx}
      className={`flex aspect-square cursor-pointer flex-col items-center justify-center border bg-bg-void p-1.5 transition hover:border-amber hover:bg-amber/5 ${stateCls}`}
    >
      <span className={`font-mono text-xl font-bold ${iconCls}`}>
        {slot.icon}
      </span>
      <span
        className={`mt-1 text-center font-mono text-[0.55rem] tracking-[0.05em] ${labelCls}`}
      >
        {slot.label}
      </span>
    </button>
  );
}

function ListRow({ row }: { row: CharacterListRow }) {
  const valueCls = row.unidentified
    ? "italic text-text-mute"
    : "text-amber-bright";
  return (
    <div className="flex items-center justify-between border-b border-dashed border-border-rune/30 py-2 text-[0.85rem] last:border-b-0">
      <div className="flex flex-col gap-0.5">
        <span className="font-serif text-text-bright">{row.name}</span>
        {row.meta && (
          <span className="font-mono text-[0.65rem] tracking-[0.1em] text-text-mute">
            {row.meta}
          </span>
        )}
      </div>
      <span className={`font-mono text-[0.78rem] font-bold ${valueCls}`}>
        {row.value}
      </span>
    </div>
  );
}

export function CharacterSheetModal({
  data,
  open,
  onClose,
  onEssenceClick,
}: Props) {
  const [tab, setTab] = useState<Tab>("스탯");

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
    >
      <div
        className="relative grid max-h-[88vh] w-[90%] max-w-[880px] animate-modal-in grid-rows-[auto_1fr] overflow-hidden border border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel [box-shadow:0_24px_64px_rgba(0,0,0,0.8),0_0_32px_var(--torch-glow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="pointer-events-none absolute inset-x-[5%] top-0 h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-60" />

        <header className="flex items-center justify-between border-b border-border-rune bg-bg-deep px-7 py-4">
          <div className="flex items-center gap-4">
            <div className="flex h-[52px] w-[52px] items-center justify-center border border-amber bg-bg-void font-mono text-2xl font-bold text-amber-bright [text-shadow:0_0_12px_var(--torch-glow)]">
              {data.portraitCh}
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="font-serif text-2xl font-bold tracking-[0.05em] text-text-bright">
                {data.name}
              </span>
              <span className="font-narrative text-[0.85rem] italic text-text-mute">
                {data.subtitle}
              </span>
            </div>
          </div>

          <div className="flex gap-1.5">
            {TABS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`cursor-pointer border px-3.5 py-2 font-mono text-[0.7rem] uppercase tracking-[0.15em] ${
                  tab === t
                    ? "border-amber bg-amber/[0.12] text-amber"
                    : "border-border-rune bg-bg-elev text-text-mid"
                }`}
              >
                {t}
              </button>
            ))}
            <button
              type="button"
              onClick={onClose}
              className="ml-2 flex h-8 w-8 cursor-pointer items-center justify-center border border-border-rune bg-transparent text-lg text-text-mute hover:border-amber hover:text-amber"
            >
              ×
            </button>
          </div>
        </header>

        <div className="grid grid-cols-[1fr_1.2fr] overflow-hidden">
          <div className="overflow-y-auto border-r border-border-rune px-7 py-6">
            {data.statSections.map((sec) => (
              <section key={sec.header} className="mb-6 last:mb-0">
                <div className="mb-3 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
                  {sec.header}
                </div>
                {sec.stats.map((s, i) => (
                  <BigStat key={i} stat={s} />
                ))}
              </section>
            ))}
          </div>

          <div className="overflow-y-auto px-7 py-6">
            <section className="mb-6">
              <div className="mb-3 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
                정수 슬롯
              </div>
              <div className="grid grid-cols-4 gap-2">
                {data.essenceSlots.map((slot, i) => (
                  <Slot
                    key={i}
                    slot={slot}
                    idx={i}
                    onClick={
                      onEssenceClick && slot.state !== "locked"
                        ? () => onEssenceClick(i)
                        : undefined
                    }
                  />
                ))}
              </div>
            </section>

            <section className="mb-6">
              <div className="mb-3 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
                스킬
              </div>
              {data.skillRows.map((r, i) => (
                <ListRow key={i} row={r} />
              ))}
            </section>

            <section>
              <div className="mb-3 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
                장비
              </div>
              {data.equipRows.map((r, i) => (
                <ListRow key={i} row={r} />
              ))}
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
