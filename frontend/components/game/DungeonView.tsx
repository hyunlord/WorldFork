"use client";

import type { DungeonViewData, TileType } from "./types";

interface Props {
  data: DungeonViewData;
}

const TILE_CLASS: Record<TileType, string> = {
  wall: "text-tile-wall [text-shadow:0_0_1px_rgba(0,0,0,0.8)]",
  floor: "text-tile-floor opacity-60",
  player:
    "text-tile-player [text-shadow:0_0_12px_rgba(255,200,87,0.9),0_0_3px_rgba(255,200,87,1)] animate-player-pulse",
  enemy: "text-tile-enemy [text-shadow:0_0_8px_rgba(255,85,85,0.7)]",
  npc: "text-amber [text-shadow:0_0_10px_rgba(232,168,56,0.7)]",
  item:
    "text-tile-item [text-shadow:0_0_6px_rgba(102,224,255,0.5)] animate-ember-pulse",
  stair: "text-tile-stair [text-shadow:0_0_6px_rgba(102,255,204,0.5)]",
  door: "text-amber-dim",
  blank: "text-transparent",
};

const LEGEND_LABEL_COLOR: Record<TileType, string> = {
  player: "text-tile-player",
  enemy: "text-tile-enemy",
  npc: "text-amber",
  item: "text-tile-item",
  stair: "text-tile-stair",
  door: "text-amber-dim",
  wall: "text-tile-wall",
  floor: "text-tile-floor",
  blank: "text-text-mute",
};

export function DungeonView({ data }: Props) {
  return (
    <div className="relative flex flex-col overflow-hidden border-r border-border-rune bg-bg-canvas bg-[radial-gradient(circle_at_50%_50%,var(--color-tile-floor)_0%,var(--color-bg-canvas)_70%)]">
      <span className="pointer-events-none absolute left-2 top-2 z-[3] font-serif text-2xl text-amber-dim opacity-40">
        ◆
      </span>
      <span className="pointer-events-none absolute right-2 top-2 z-[3] font-serif text-2xl text-amber-dim opacity-40">
        ◆
      </span>
      <span className="pointer-events-none absolute bottom-2 left-2 z-[3] font-serif text-2xl text-amber-dim opacity-40">
        ◆
      </span>
      <span className="pointer-events-none absolute bottom-2 right-2 z-[3] font-serif text-2xl text-amber-dim opacity-40">
        ◆
      </span>

      <div className="absolute right-3.5 top-3.5 z-10 border border-border-rune bg-[rgba(8,8,16,0.92)] px-3.5 py-1.5 font-mono text-[0.7rem] tracking-[0.15em] text-text-mid backdrop-blur-[4px] shadow-[0_4px_16px_rgba(0,0,0,0.5)]">
        TURN{" "}
        <span className="font-bold text-amber [text-shadow:0_0_6px_var(--torch-glow)]">
          {data.turn}
        </span>
      </div>

      <div className="relative flex flex-1 items-center justify-center font-mono">
        <span
          className="pointer-events-none absolute inset-0 z-[4] mix-blend-screen animate-torch-flicker"
          style={{
            background:
              "radial-gradient(ellipse 260px 200px at 50% 50%, rgba(255, 200, 87, 0.18) 0%, rgba(232, 168, 56, 0.08) 40%, transparent 80%)",
          }}
        />
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-amber-bright [animation:float-ember_4s_infinite] [box-shadow:0_0_6px_var(--color-amber)] bottom-[30%] left-[35%]" />
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-amber-bright [animation:float-ember_5s_infinite_1.5s] [box-shadow:0_0_6px_var(--color-amber)] bottom-[35%] left-[55%]" />
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-amber-bright [animation:float-ember_4.5s_infinite_2.8s] [box-shadow:0_0_6px_var(--color-amber)] bottom-[25%] left-[48%]" />
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-amber-bright [animation:float-ember_5.5s_infinite_0.8s] [box-shadow:0_0_6px_var(--color-amber)] bottom-[28%] left-[62%]" />

        <pre className="relative z-[2] m-0 whitespace-pre font-mono text-[1.4rem] font-bold leading-[1.25] tracking-[0.1em]">
          {data.rows.map((row, ri) => (
            <div key={ri}>
              {row.map((tile, ci) => (
                <span key={ci} className={TILE_CLASS[tile.type]}>
                  {tile.ch}
                </span>
              ))}
            </div>
          ))}
        </pre>

        <span
          className="pointer-events-none absolute inset-0 z-[5]"
          style={{
            background:
              "radial-gradient(ellipse 380px 280px at 50% 50%, transparent 0%, rgba(0,0,0,0.4) 50%, rgba(0,0,0,0.95) 90%)",
          }}
        />
      </div>

      {data.legend && data.legend.length > 0 && (
        <div className="absolute bottom-3.5 left-3.5 z-10 flex gap-4 border border-border-rune bg-[rgba(8,8,16,0.92)] px-3.5 py-2 font-mono text-[0.65rem] text-text-mute shadow-[0_4px_16px_rgba(0,0,0,0.5)] backdrop-blur-[4px]">
          {data.legend.map((entry, i) => (
            <span key={i}>
              <strong
                className={`mr-1 font-bold ${LEGEND_LABEL_COLOR[entry.type]}`}
              >
                {entry.ch}
              </strong>
              {entry.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
