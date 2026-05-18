"use client";

import type { InventoryPanelData, InventoryRow } from "./types";

interface Props {
  data: InventoryPanelData;
}

function Row({ row }: { row: InventoryRow }) {
  const valueClass =
    row.kind === "amber"
      ? "text-amber-bright [text-shadow:0_0_6px_var(--torch-glow)]"
      : row.kind === "unidentified"
        ? "italic text-text-mute"
        : "text-text-bright";

  return (
    <div className="flex items-center justify-between border-b border-dashed border-border-soft/40 py-1 text-[0.82rem] transition hover:bg-amber/[0.03] last:border-b-0">
      <span className="font-sans text-text-mid">{row.label}</span>
      <span className={`font-mono text-[0.78rem] ${valueClass}`}>
        {row.value}
      </span>
    </div>
  );
}

export function InventoryPanel({ data }: Props) {
  return (
    <div className="relative grid grid-cols-2 gap-5 overflow-y-auto bg-bg-panel px-6 py-3.5">
      <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-arcane to-transparent opacity-30" />
      {data.sections.map((section) => (
        <div key={section.header} className="flex flex-col">
          <div className="mb-2 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-text-mute">
            {section.header}
          </div>
          {section.rows.map((row, i) => (
            <Row key={i} row={row} />
          ))}
        </div>
      ))}
    </div>
  );
}
