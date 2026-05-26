"use client";

import type { StatusBarData } from "./types";

interface Props {
  data: StatusBarData;
  onMenu?: () => void;
}

const MOON_BY_TOD: Record<string, string> = {
  낮: "☀",
  밤: "🌙",
  황혼: "🌆",
  여명: "🌅",
};

const CYCLE_HOURS = 168;
const WARN_H = 24;
const CRIT_H = 1;

function CycleBar({ hoursInDungeon }: { hoursInDungeon: number }) {
  const hoursLeft = Math.max(0, CYCLE_HOURS - hoursInDungeon);
  const pct = Math.min(100, (hoursInDungeon / CYCLE_HOURS) * 100);

  const barCls =
    hoursLeft <= CRIT_H
      ? "bg-gradient-to-r from-crimson-dim to-crimson"
      : hoursLeft <= WARN_H
        ? "bg-gradient-to-r from-amber-dim to-amber"
        : "bg-gradient-to-r from-success/60 to-success";

  const textCls =
    hoursLeft <= CRIT_H
      ? "text-crimson"
      : hoursLeft <= WARN_H
        ? "text-amber"
        : "text-success";

  return (
    <span className="flex items-center gap-2 text-text-mid">
      <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
        잔여
      </span>
      <span className="relative h-2 w-[80px] overflow-hidden rounded-[1px] border border-border-rune bg-bg-void">
        <span
          className={`block h-full transition-all ${barCls}`}
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className={`font-mono font-bold ${textCls}`}>
        {Math.round(hoursLeft)}h
        <span className="text-text-mute"> / {CYCLE_HOURS}h</span>
      </span>
    </span>
  );
}

export function StatusBar({ data, onMenu }: Props) {
  const hpPct = Math.max(0, Math.min(100, (data.hp / data.hpMax) * 100));
  const tod = MOON_BY_TOD[data.timeOfDay] ?? "🌙";
  const inDungeon = data.mode === "dungeon";

  return (
    <div className="relative grid h-[50px] grid-flow-col items-center gap-4 border-b border-border-rune bg-gradient-to-b from-bg-panel to-bg-deep px-6 font-mono text-[0.8rem] shadow-[0_4px_12px_rgba(0,0,0,0.4)]">
      <span className="font-serif text-[0.95rem] font-bold tracking-[0.15em] text-amber [text-shadow:0_0_8px_var(--torch-glow)]">
        <span className="animate-torch-flicker text-amber-bright">◆ </span>
        WORLDFORK
      </span>

      {data.mode === "town" && (
        <span className="rounded-[1px] border border-arcane/30 bg-arcane/15 px-2.5 py-1 font-mono text-[0.65rem] uppercase tracking-[0.25em] text-arcane">
          TOWN MODE
        </span>
      )}

      <span className="h-6 w-px bg-gradient-to-b from-transparent via-border-rune to-transparent" />

      {inDungeon ? (
        <span className="flex items-center gap-2 text-text-mid">
          <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
            HP
          </span>
          <span className="relative h-2.5 w-[80px] overflow-hidden rounded-[1px] border border-border-rune bg-bg-void shadow-[inset_0_1px_3px_rgba(0,0,0,0.6)]">
            <span
              className="block h-full bg-gradient-to-r from-crimson-dim via-crimson to-amber-bright shadow-[0_0_8px_rgba(232,168,56,0.4)]"
              style={{ width: `${hpPct}%` }}
            />
          </span>
          <span className="font-bold text-text-bright">
            {data.hp}/{data.hpMax}
          </span>
        </span>
      ) : (
        <span className="flex items-center gap-2 text-text-mid">
          <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
            등급
          </span>
          <span className="font-bold text-amber-bright">
            {data.grade ?? "-"}
          </span>
        </span>
      )}

      {/* 영혼력 — dungeon mode */}
      {inDungeon && data.soulPower != null && (
        <>
          <span className="h-6 w-px bg-gradient-to-b from-transparent via-border-rune to-transparent" />
          <span className="flex items-center gap-1.5 text-text-mid">
            <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
              영혼력
            </span>
            <span className="font-bold text-cyan">
              {data.soulPower}
              {data.soulPowerMax != null && data.soulPowerMax > 0 && (
                <span className="text-text-mute">/{data.soulPowerMax}</span>
              )}
            </span>
          </span>
        </>
      )}

      {/* 정수 슬롯 — dungeon mode */}
      {inDungeon && data.essenceMax != null && (
        <>
          <span className="h-6 w-px bg-gradient-to-b from-transparent via-border-rune to-transparent" />
          <span className="flex items-center gap-1.5 text-text-mid">
            <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
              정수
            </span>
            <span className="font-bold text-amber">
              {data.essenceCount ?? 0}
              <span className="text-text-mute">/{data.essenceMax}</span>
            </span>
          </span>
        </>
      )}

      {/* 레벨 — dungeon mode */}
      {inDungeon && data.playerLevel != null && (
        <>
          <span className="h-6 w-px bg-gradient-to-b from-transparent via-border-rune to-transparent" />
          <span className="flex items-center gap-1.5 text-text-mid">
            <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
              Lv
            </span>
            <span className="font-bold text-text-bright">{data.playerLevel}</span>
          </span>
        </>
      )}

      <span className="h-6 w-px bg-gradient-to-b from-transparent via-border-rune to-transparent" />

      {/* 시간 / cycle bar */}
      {inDungeon ? (
        (data.floorNumber != null && data.floorNumber > 0) ? (
          <CycleBar hoursInDungeon={data.hoursInDungeon ?? 0} />
        ) : (
          <span className="flex items-center gap-2 text-text-mid">
            <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
              시간
            </span>
            <span className="font-mono font-bold text-text-bright">
              {data.hoursInDungeon ?? 0}h
              <span className="text-text-mute">
                {" "}/ {data.hoursMax ?? 174}h
              </span>
            </span>
          </span>
        )
      ) : (
        <span className="flex items-center gap-2 text-text-mid">
          <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
            마석
          </span>
          <span className="font-mono font-bold text-gold">
            {data.mageStones ?? 0}
          </span>
        </span>
      )}

      <span className="h-6 w-px bg-gradient-to-b from-transparent via-border-rune to-transparent" />

      <span className="flex items-center gap-2 text-text-mid">
        <span className="text-[0.7rem] uppercase tracking-[0.15em] text-text-mute">
          위치
        </span>
        <span className="font-serif text-text-bright">
          {data.locationLabel}
        </span>
      </span>

      <span className="h-6 w-px bg-gradient-to-b from-transparent via-border-rune to-transparent" />

      <span className="flex items-center gap-2 text-text-mid">
        <span className="animate-torch-flicker text-base text-amber">
          {tod}
        </span>
        <span>{data.timeOfDay}</span>
      </span>

      <button
        type="button"
        onClick={onMenu}
        className="ml-auto cursor-pointer border border-border-rune bg-bg-elev px-3.5 py-1.5 font-mono text-[0.7rem] tracking-[0.15em] text-text-mid transition hover:border-amber hover:bg-amber/5 hover:text-amber hover:[box-shadow:0_0_12px_var(--torch-glow)]"
      >
        ≡ MENU
      </button>

      <span className="pointer-events-none absolute inset-x-[10%] -bottom-px h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-40" />
    </div>
  );
}
