"use client";

import type { PartyMember, PartyPanelData } from "./types";

interface Props {
  data: PartyPanelData;
  onMember?: (id: string) => void;
}

function Member({
  member,
  onClick,
}: {
  member: PartyMember;
  onClick?: () => void;
}) {
  const hpPct = Math.max(0, Math.min(100, (member.hp / member.hpMax) * 100));
  const affPct =
    member.affinity != null
      ? Math.max(0, Math.min(100, member.affinity))
      : null;
  const hpLow = hpPct < 30;

  const memberCls = member.isSelf
    ? "border-l-[2px] border-l-amber bg-amber/5"
    : member.injured
      ? "border-l-[2px] border-l-crimson"
      : "border-l-[2px] border-l-transparent";

  const portraitCls = member.isSelf
    ? "text-amber-bright border-amber [text-shadow:0_0_6px_var(--torch-glow)]"
    : member.injured
      ? "text-crimson border-crimson"
      : "text-cyan border-cyan";

  const moodCls =
    member.mood === "alert"
      ? "text-amber border-amber/30"
      : member.mood === "wounded"
        ? "text-crimson border-crimson/30"
        : member.mood === "confident"
          ? "text-success border-success/30"
          : "text-text-mute border-border-rune";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full cursor-pointer items-center gap-2.5 border-b border-dashed border-border-rune/40 px-3 py-2.5 text-left transition last:border-b-0 hover:bg-amber/5 ${memberCls}`}
    >
      <span
        className={`relative flex h-9 w-9 flex-shrink-0 items-center justify-center border bg-bg-void font-mono text-[1.1rem] font-bold ${portraitCls}`}
      >
        {member.portraitCh}
        <span className="absolute -bottom-2 -right-0.5 rounded-[1px] bg-bg-void px-1 font-mono text-[0.5rem] tracking-[0.05em] text-text-faint">
          {member.isSelf ? "YOU" : "P-H"}
        </span>
      </span>

      <span className="flex min-w-0 flex-1 flex-col">
        <span className="flex items-center justify-between font-serif text-[0.85rem] font-bold text-text-bright">
          <span>{member.name}</span>
          <span className="font-mono text-[0.55rem] tracking-[0.1em] text-text-mute">
            {member.role}
          </span>
        </span>

        <span className="mt-1 flex flex-col gap-0.5">
          <span className="flex items-center gap-1.5">
            <span className="w-4 font-mono text-[0.55rem] tracking-[0.1em] text-text-mute">
              HP
            </span>
            <span className="relative h-[5px] flex-1 overflow-hidden rounded-[1px] border border-border-rune bg-bg-deep">
              <span
                className={`block h-full ${hpLow ? "bg-gradient-to-r from-crimson-dim to-crimson" : "bg-gradient-to-r from-crimson-dim to-amber"}`}
                style={{ width: `${hpPct}%` }}
              />
            </span>
            <span className="min-w-7 text-right font-mono text-[0.6rem] text-text-mid">
              {member.hp}/{member.hpMax}
            </span>
          </span>

          {affPct != null && (
            <span className="flex items-center gap-1.5">
              <span className="w-4 font-mono text-[0.55rem] tracking-[0.1em] text-text-mute">
                호감
              </span>
              <span className="relative h-[5px] flex-1 overflow-hidden rounded-[1px] border border-border-rune bg-bg-deep">
                <span
                  className="block h-full bg-gradient-to-r from-arcane to-cyan"
                  style={{ width: `${affPct}%` }}
                />
              </span>
              <span className="min-w-7 text-right font-mono text-[0.6rem] text-text-mid">
                {member.affinityLabel ?? `${affPct}`}
              </span>
            </span>
          )}
        </span>

        {member.moodLabel && (
          <span className="mt-1 flex gap-1 font-mono text-[0.6rem]">
            <span
              className={`border bg-bg-elev px-1.5 py-0.5 tracking-[0.05em] ${moodCls}`}
            >
              {member.moodLabel}
            </span>
          </span>
        )}
      </span>
    </button>
  );
}

export function PartyPanel({ data, onMember }: Props) {
  return (
    <aside className="fixed right-5 top-[70px] z-50 w-[250px] border border-border-rune bg-[rgba(8,8,16,0.92)] backdrop-blur-[6px] [box-shadow:0_8px_24px_rgba(0,0,0,0.6),0_0_16px_var(--torch-glow)]">
      <header className="flex items-center justify-between border-b border-border-rune bg-gradient-to-r from-amber/[0.08] to-transparent px-3.5 py-2">
        <span className="font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
          <span className="animate-torch-flicker text-amber-bright">◆ </span>
          PARTY
        </span>
        <span className="font-mono text-[0.65rem] text-text-mute">
          {data.members.length} 명
        </span>
      </header>

      <div className="flex flex-col">
        {data.members.map((m) => (
          <Member
            key={m.id}
            member={m}
            onClick={onMember ? () => onMember(m.id) : undefined}
          />
        ))}
      </div>

      <footer className="border-t border-border-rune bg-gradient-to-r from-transparent to-amber/5 px-3.5 py-2 text-center">
        <span className="font-mono text-[0.6rem] tracking-[0.1em] text-text-mute">
          <span className="mx-0.5 rounded-[1px] bg-amber/10 px-1 py-0.5 text-amber">
            c
          </span>
          본인 sheet
          <span className="mx-0.5 ml-2 rounded-[1px] bg-amber/10 px-1 py-0.5 text-amber">
            p
          </span>
          파티 detail
        </span>
      </footer>
    </aside>
  );
}
