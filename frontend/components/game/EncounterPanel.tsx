"use client";

import type {
  EncounterPanelData,
  EncounterTarget,
  EncounterAction,
  StatusEffectDisplay,
} from "./types";

interface Props {
  data: EncounterPanelData;
  onTarget?: (id: string) => void;
  onAction?: (id: string) => void;
}

function Target({
  target,
  onClick,
}: {
  target: EncounterTarget;
  onClick?: () => void;
}) {
  const isHostile = target.kind === "hostile";
  const borderClass = isHostile
    ? "border-l-tile-enemy hover:bg-crimson/5"
    : "border-l-amber hover:bg-amber/5";
  const portraitColor = isHostile
    ? "text-tile-enemy border-crimson/40"
    : "text-amber border-amber/40";
  const tagColor = isHostile ? "text-crimson" : "text-amber";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`mb-1 flex w-full items-center gap-3 border border-transparent border-l-[3px] bg-bg-elev px-4 py-2.5 text-left transition hover:translate-x-0.5 ${borderClass}`}
    >
      <span
        className={`relative flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center border bg-bg-void font-mono text-[0.95rem] font-bold ${portraitColor}`}
      >
        {target.ch}
      </span>
      <span className="flex flex-1 flex-col gap-0.5">
        <span className="font-serif text-[0.95rem] font-bold text-text-bright">
          {target.name}
        </span>
        <span
          className={`font-mono text-[0.65rem] tracking-[0.1em] ${tagColor}`}
        >
          {target.tag}
        </span>
      </span>
    </button>
  );
}

function ActionBtn({
  action,
  onClick,
}: {
  action: EncounterAction;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex cursor-pointer items-center justify-center gap-1.5 border border-border-rune bg-gradient-to-b from-bg-elev to-bg-panel px-2 py-2 font-sans text-[0.78rem] text-text-bright transition hover:-translate-y-px hover:border-amber hover:bg-gradient-to-b hover:from-amber/[0.08] hover:to-bg-panel hover:[box-shadow:0_0_12px_var(--torch-glow)]"
    >
      <span>{action.label}</span>
      <span className="rounded-[1px] border border-amber/25 bg-amber/[0.12] px-1.5 py-0.5 font-mono text-[0.65rem] text-amber">
        {action.key}
      </span>
    </button>
  );
}

const STATUS_LABEL: Record<string, string> = {
  poison: "독",
  paralyze: "마비",
  bleed: "출혈",
  burn: "화상",
  slow: "둔화",
};

function StatusBadge({ effect }: { effect: StatusEffectDisplay }) {
  const label = STATUS_LABEL[effect.type] ?? effect.type;
  return (
    <span className="rounded-[1px] border border-crimson/40 bg-crimson/10 px-1.5 py-0.5 font-mono text-[0.6rem] text-crimson">
      {label} {effect.duration}턴
    </span>
  );
}

export function EncounterPanel({ data, onTarget, onAction }: Props) {
  const statusEffects = data.status_effects ?? [];
  return (
    <div className="relative overflow-y-auto border-b border-border-rune bg-bg-panel px-6 py-4">
      <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-crimson to-transparent opacity-40" />

      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[0.65rem] uppercase tracking-[0.3em] text-crimson">
          ⚔ ENCOUNTER
        </span>
        <span className="font-mono text-[0.65rem] text-text-mute">
          {data.targets.length} TARGETS
        </span>
      </div>

      {data.targets.map((t) => (
        <Target
          key={t.id}
          target={t}
          onClick={onTarget ? () => onTarget(t.id) : undefined}
        />
      ))}

      {statusEffects.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {statusEffects.map((e, i) => (
            <StatusBadge key={`${e.type}-${i}`} effect={e} />
          ))}
        </div>
      )}

      <div className="mt-2.5 grid grid-cols-4 gap-1.5">
        {data.actions.map((a) => (
          <ActionBtn
            key={a.id}
            action={a}
            onClick={onAction ? () => onAction(a.id) : undefined}
          />
        ))}
      </div>
    </div>
  );
}
