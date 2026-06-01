"use client";

import type { Race } from "@/lib/types/character";
import { RACES } from "@/lib/types/character";
import { unmaskIp } from "@/lib/api/v2";

interface Props {
  race: Race | null;
}

export function RaceDetailPanel({ race }: Props) {
  const info = race != null ? RACES.find((r) => r.id === race) : null;

  if (info == null) {
    return (
      <div className="flex min-h-[180px] items-center justify-center rounded border border-border-rune bg-bg-panel">
        <p className="text-sm text-text-faint">종족을 선택하면 상세 정보가 표시된다.</p>
      </div>
    );
  }

  return (
    <div className="rounded border border-border-rune bg-bg-panel p-6 space-y-5">
      <div>
        <h3 className="font-serif text-xl tracking-[0.15em] text-amber">{info.nameKo}</h3>
        <p className="mt-1 text-sm text-text-mid">{unmaskIp(info.description)}</p>
      </div>

      <div className="grid grid-cols-4 gap-3 md:grid-cols-7">
        <StatCell label="HP" value={info.hp} />
        <StatCell label="영혼력" value={info.soulPower} />
        <StatCell label="슬롯" value={info.maxEssences} />
        <StatCell label="공격" value={info.attack} />
        <StatCell label="방어" value={info.defense} />
        <StatCell label="민첩" value={info.dex} />
        <StatCell label="행운" value={info.luck} />
      </div>

      <div>
        <h4 className="mb-2 font-serif text-sm tracking-[0.1em] text-amber/70">특성</h4>
        <ul className="space-y-1">
          {info.traits.map((trait) => (
            <li key={trait} className="flex items-start text-sm text-text-mid">
              <span className="mr-2 text-amber/40">·</span>
              <span>{trait}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function StatCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center rounded border border-border-soft bg-bg-deep/60 px-2 py-2 text-center">
      <span className="font-mono text-xs text-text-faint">{label}</span>
      <span className="mt-1 font-mono text-base font-medium text-text-bright">{value}</span>
    </div>
  );
}
