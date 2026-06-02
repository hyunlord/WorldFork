"use client";

export interface SurroundingEntity {
  kind: "npc" | "exit" | "object";
  label: string;
}

interface Props {
  locationLabel: string;
  entities: SurroundingEntity[];
}

const ICON: Record<SurroundingEntity["kind"], string> = {
  npc: "☻",
  exit: "⌖",
  object: "◈",
};

const KIND_LABEL: Record<SurroundingEntity["kind"], string> = {
  npc: "인물",
  exit: "길",
  object: "사물",
};

/**
 * 주변 엔티티 패널 — 마을(inVillage)은 EncounterPanel(전투)을 띄우지 않으므로,
 * 주변에 무엇이 있는지(부족장 등 NPC, 미궁 입구 같은 출구)를 여기서 보여준다.
 *
 * session encounters의 비적대 NPC + 위치 맥락 출구를 모아 게임 주변을 가시화.
 */
export function SurroundingsPanel({ locationLabel, entities }: Props) {
  return (
    <div
      data-testid="surroundings-panel"
      className="overflow-y-auto border-t border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel px-6 py-4"
    >
      <div className="mb-3 flex items-center gap-2 border-b border-border-rune pb-2 font-mono text-[0.62rem] uppercase tracking-[0.3em] text-amber">
        <span className="animate-torch-flicker text-amber-bright">◆</span>
        <span>주변 · {locationLabel}</span>
      </div>

      {entities.length === 0 ? (
        <p className="font-narrative text-sm italic text-text-mute">
          주변에 눈에 띄는 것이 없다.
        </p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {entities.map((ent, i) => (
            <li
              key={i}
              data-testid={`surrounding-${ent.kind}`}
              className="flex items-center gap-2.5 font-sans text-[0.9rem] text-text-mid"
            >
              <span className="font-mono text-amber-bright">{ICON[ent.kind]}</span>
              <span className="min-w-[2.4rem] font-mono text-[0.62rem] uppercase tracking-[0.12em] text-text-mute">
                {KIND_LABEL[ent.kind]}
              </span>
              <span className="text-text-bright">{ent.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
