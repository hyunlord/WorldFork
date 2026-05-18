"use client";

import type {
  NarrativeSpan,
  TownPoi,
  TownRunSummaryRow,
  TownViewData,
} from "./types";

interface Props {
  data: TownViewData;
  onPoi?: (id: string) => void;
}

function TownSpan({ span }: { span: NarrativeSpan }) {
  switch (span.kind) {
    case "emph":
      return <span className="italic text-amber-bright">{span.text}</span>;
    case "whisper":
      return <span className="italic text-text-mid">{span.text}</span>;
    case "name":
      return <span className="font-bold text-cyan">{span.text}</span>;
    case "danger":
      return <span className="font-bold text-crimson">{span.text}</span>;
    case "plain":
    default:
      return <span>{span.text}</span>;
  }
}

function PoiMarker({
  poi,
  onClick,
}: {
  poi: TownPoi;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{ top: poi.hotspot.top, left: poi.hotspot.left }}
      className="absolute z-[4] flex -translate-x-1/2 -translate-y-1/2 cursor-pointer flex-col items-center transition"
    >
      <span className="block h-3.5 w-3.5 animate-window-glow rounded-full border-2 border-amber-bright bg-amber [box-shadow:0_0_12px_var(--color-amber),0_0_4px_var(--color-amber-bright)] group-hover:scale-125" />
      <span className="mt-1.5 whitespace-nowrap border border-border-rune bg-[rgba(8,8,16,0.92)] px-2 py-0.5 font-serif text-[0.75rem] tracking-[0.05em] text-text-bright backdrop-blur-[2px]">
        {poi.name}
      </span>
    </button>
  );
}

function SummaryValueCell({ row }: { row: TownRunSummaryRow }) {
  const cls =
    row.kind === "amber"
      ? "text-amber-bright"
      : row.kind === "gold"
        ? "text-gold"
        : row.kind === "success"
          ? "text-success"
          : "text-text-bright";
  return (
    <span className={`font-mono text-[0.78rem] ${cls}`}>{row.value}</span>
  );
}

export function TownView({ data, onPoi }: Props) {
  return (
    <div className="relative flex flex-1 flex-row overflow-hidden">
      <div className="relative flex-1 overflow-hidden border-r border-border-rune bg-gradient-to-b from-bg-canvas to-bg-canvas-2 p-6">
        <div className="pointer-events-none absolute left-1/2 top-6 z-[5] -translate-x-1/2 font-serif text-2xl tracking-[0.3em] text-amber [text-shadow:0_0_12px_rgba(232,168,56,0.4)]">
          <span className="mx-3 text-[0.7em] align-middle text-amber-dim">
            ◆
          </span>
          {data.title}
          <span className="mx-3 text-[0.7em] align-middle text-amber-dim">
            ◆
          </span>
        </div>
        <div className="pointer-events-none absolute left-1/2 top-[3.6rem] z-[5] -translate-x-1/2 font-narrative text-[0.85rem] italic tracking-[0.2em] text-text-mute">
          {data.subtitle}
        </div>

        <span
          className="pointer-events-none absolute inset-0 z-[3]"
          style={{
            background:
              "radial-gradient(ellipse 70% 50% at center, transparent 0%, rgba(20, 20, 30, 0.4) 80%, rgba(8, 8, 16, 0.7) 100%)",
          }}
        />

        <span className="pointer-events-none absolute top-[30%] left-0 z-[4] h-20 w-full animate-drift bg-gradient-to-r from-transparent via-amber/[0.04] to-transparent" />
        <span className="pointer-events-none absolute top-[60%] left-0 z-[4] h-20 w-full animate-drift bg-gradient-to-r from-transparent via-amber/[0.04] to-transparent [animation-direction:reverse] [animation-duration:30s]" />

        {data.pois.map((poi) => (
          <PoiMarker
            key={poi.id}
            poi={poi}
            onClick={onPoi ? () => onPoi(poi.id) : undefined}
          />
        ))}
      </div>

      <aside className="grid w-[420px] grid-rows-[220px_1fr_230px] overflow-hidden bg-bg-deep">
        <section className="relative overflow-y-auto border-b border-border-rune bg-bg-panel px-6 py-4">
          <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-40" />
          <div className="mb-3 flex items-center gap-1.5 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
            <span className="text-amber-bright">◆</span>
            <span>건물 · QUICK ACCESS</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {data.pois.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={onPoi ? () => onPoi(p.id) : undefined}
                className="flex cursor-pointer flex-col gap-0.5 border border-border-rune bg-gradient-to-b from-bg-elev to-bg-panel px-3 py-2.5 text-left transition hover:translate-x-0.5 hover:border-amber hover:bg-gradient-to-b hover:from-amber/[0.08] hover:to-bg-panel hover:[box-shadow:0_0_12px_rgba(232,168,56,0.2)]"
              >
                <span className="flex items-center justify-between font-serif text-[0.9rem] font-bold text-text-bright">
                  <span>{p.name}</span>
                  <span className="rounded-[1px] border border-amber/25 bg-amber/10 px-1.5 py-0.5 font-mono text-[0.65rem] text-amber">
                    {p.key}
                  </span>
                </span>
                <span className="font-sans text-[0.7rem] text-text-mute">
                  {p.desc}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="relative overflow-y-auto border-b border-border-rune bg-gradient-to-b from-bg-panel to-bg-deep px-6 py-5">
          <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-arcane to-transparent opacity-40" />
          <div className="mb-3 flex items-center gap-1.5 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-arcane">
            <span className="text-amber-bright">◆</span>
            <span>소문 · 최근</span>
          </div>
          <div className="font-narrative text-[0.95rem] leading-[1.85] text-text-bright">
            {data.news.paragraphs.map((p, i) => (
              <p key={i} className="mb-3 last:mb-0">
                {p.spans.map((s, j) => (
                  <TownSpan key={j} span={s} />
                ))}
              </p>
            ))}
          </div>
        </section>

        <section className="relative grid grid-cols-2 gap-5 overflow-y-auto bg-bg-panel px-6 py-4">
          <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-cyan to-transparent opacity-30" />
          {data.summary.map((sec) => (
            <div key={sec.header} className="flex flex-col">
              <div className="mb-2 border-b border-border-rune pb-1.5 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-text-mute">
                {sec.header}
              </div>
              {sec.rows.map((r, i) => (
                <div
                  key={i}
                  className="flex justify-between border-b border-dashed border-border-soft/40 py-1 text-[0.82rem] last:border-b-0"
                >
                  <span className="text-text-mid">{r.label}</span>
                  <SummaryValueCell row={r} />
                </div>
              ))}
            </div>
          ))}
        </section>
      </aside>
    </div>
  );
}
