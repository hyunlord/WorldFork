"use client";

import { useEffect, useRef } from "react";

import type { NarrativePanelData, NarrativeSpan } from "./types";

interface Props {
  data: NarrativePanelData;
}

function Span({ span, idx }: { span: NarrativeSpan; idx: number }) {
  switch (span.kind) {
    case "emph":
      return (
        <span
          key={idx}
          className="italic text-amber-bright [text-shadow:0_0_8px_var(--torch-glow)]"
        >
          {span.text}
        </span>
      );
    case "name":
      return (
        <span key={idx} className="font-bold text-cyan">
          {span.text}
        </span>
      );
    case "danger":
      return (
        <span key={idx} className="font-bold text-crimson">
          {span.text}
        </span>
      );
    case "whisper":
      return (
        <span
          key={idx}
          className="italic text-[0.95em] text-text-mid"
        >
          {span.text}
        </span>
      );
    case "essence":
      return (
        <span
          key={idx}
          className="rounded bg-amber/10 px-1 font-medium text-amber [text-shadow:0_0_6px_var(--torch-glow)]"
        >
          {span.text}
        </span>
      );
    case "plain":
    default:
      return <span key={idx}>{span.text}</span>;
  }
}

export function NarrativePanel({ data }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // ★ 히스토리 누적 시 최신 narrative가 하단 — 새 paragraph마다 끝으로 스크롤
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [data.paragraphs.length]);

  return (
    <div
      ref={scrollRef}
      className="relative overflow-y-auto border-b border-border-rune bg-gradient-to-b from-bg-panel to-bg-deep px-7 py-6"
    >
      <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-40" />

      <div className="mb-5 flex items-center gap-2.5 border-b border-border-rune pb-2.5 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
        <span className="animate-torch-flicker text-amber-bright">◆</span>
        <span>NARRATIVE · TURN {data.turn}</span>
        <span className="ml-auto text-[0.85em] text-amber-dim">◆</span>
      </div>

      <div className="narrative-body font-narrative text-[1.05rem] leading-[1.9] tracking-[0.01em] text-text-bright">
        {data.paragraphs.map((p, i) => (
          <p
            key={i}
            className="mb-4 animate-whisper-fade-in [animation-fill-mode:backwards]"
            style={{ animationDelay: `${i * 0.15}s` }}
          >
            {p.spans.map((s, j) => (
              <Span key={j} span={s} idx={j} />
            ))}
          </p>
        ))}
      </div>
    </div>
  );
}
