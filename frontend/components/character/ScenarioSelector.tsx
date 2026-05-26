"use client";

import type { ScenarioMode } from "@/lib/types/character";

interface Props {
  value: ScenarioMode;
  onChange: (mode: ScenarioMode) => void;
}

export function ScenarioSelector({ value, onChange }: Props) {
  return (
    <div className="space-y-3">
      <h2 className="font-serif text-lg tracking-[0.15em] text-amber">시나리오</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ScenarioOption
          mode="bjorn"
          title="비요른 시나리오"
          description="바바리안 투르윈의 첫 미궁 도전. 종족 고정."
          selected={value === "bjorn"}
          onClick={() => { onChange("bjorn"); }}
        />
        <ScenarioOption
          mode="new_explorer"
          title="신규 탐험가"
          description="자유 종족 선택. 라스카니아 차원광장에서 첫 진입."
          selected={value === "new_explorer"}
          onClick={() => { onChange("new_explorer"); }}
        />
      </div>
    </div>
  );
}

interface OptionProps {
  mode: ScenarioMode;
  title: string;
  description: string;
  selected: boolean;
  onClick: () => void;
}

function ScenarioOption({ title, description, selected, onClick }: OptionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded border p-4 text-left transition-all",
        selected
          ? "border-amber bg-bg-elev [box-shadow:0_0_12px_rgba(232,168,56,0.15)]"
          : "border-border-rune bg-bg-panel hover:border-amber/40 hover:bg-bg-elev",
      ].join(" ")}
    >
      <div className="font-serif tracking-[0.1em] text-text-bright">{title}</div>
      <div className="mt-1 text-sm text-text-mute">{description}</div>
    </button>
  );
}
