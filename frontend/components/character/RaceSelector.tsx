"use client";

import type { Race } from "@/lib/types/character";
import { RACES } from "@/lib/types/character";

interface Props {
  value: Race | null;
  onChange: (race: Race) => void;
  disabled?: boolean;
}

export function RaceSelector({ value, onChange, disabled = false }: Props) {
  return (
    <div className="space-y-3">
      <h2
        className={[
          "font-serif text-lg tracking-[0.15em]",
          disabled ? "text-text-faint" : "text-amber",
        ].join(" ")}
      >
        종족
        {disabled && (
          <span className="ml-3 font-sans text-xs tracking-normal text-text-mute">
            바바리안 고정
          </span>
        )}
      </h2>
      <div className="grid grid-cols-5 gap-2">
        {RACES.map((race) => (
          <button
            key={race.id}
            type="button"
            disabled={disabled}
            onClick={() => { onChange(race.id); }}
            className={[
              "rounded border p-3 text-center transition-all",
              disabled
                ? "cursor-not-allowed opacity-40"
                : "cursor-pointer",
              !disabled && value === race.id
                ? "border-amber bg-bg-elev [box-shadow:0_0_12px_rgba(232,168,56,0.15)]"
                : !disabled
                  ? "border-border-rune bg-bg-panel hover:border-amber/40 hover:bg-bg-elev"
                  : "border-border-rune bg-bg-panel",
            ].join(" ")}
          >
            <div className="font-serif text-sm tracking-[0.05em] text-text-bright">
              {race.nameKo}
            </div>
            <div className="mt-1 font-mono text-xs text-text-faint">HP {race.hp}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
