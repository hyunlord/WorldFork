"use client";

import type { CSSProperties } from "react";

import type { DungeonViewData, TileType } from "./types";

interface Props {
  data: DungeonViewData;
}

// ★ 게임 화면 픽셀화 — 문자 타일(@/g/b) → 16x16 픽셀 스프라이트 격자.
//   tools/gen_pixel_tiles.py가 생성한 CC0 타일(public/assets/pixel). 에셋 무관
//   매핑이라 더 정교한 팩으로 PNG만 교체 가능.
const PIX = "/assets/pixel";
const CELL = 38; // 픽셀 타일 한 칸(px) — 확대(작은 방 해소). pixelated로 선명 유지
const PIXELATED: CSSProperties = { imageRendering: "pixelated" };

// 엔티티/지형 오버레이 스프라이트 (바닥 위에 얹음). null = 바탕만.
const ENTITY_SPRITE: Partial<Record<TileType, string>> = {
  player: "player",
  enemy: "enemy",
  npc: "npc",
  item: "item",
  stair: "stair",
  door: "door",
};

// 칸 바탕: 벽은 wall, 그 외(엔티티 포함)는 floor, blank는 없음(투명).
function baseTile(type: TileType): string | null {
  if (type === "wall") return "wall";
  if (type === "blank") return null;
  return "floor";
}

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
    <div className="relative flex flex-col overflow-hidden border-r border-cyan/15 bg-[rgba(14,28,32,0.5)]">
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
        <span
          data-testid="dungeon-turn"
          className="font-bold text-amber [text-shadow:0_0_6px_var(--torch-glow)]"
        >
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
        {/* ★ 수정동굴 결정 앰비언트 — 따뜻한 횃불(중앙)에 차가운 청록(가장자리)을
            더해 배경(ui_gameplay_bg_crystal)과 톤 조화. 동굴 깊이감/광물 분위기. */}
        <span
          className="pointer-events-none absolute inset-0 z-[3] mix-blend-screen"
          style={{
            background:
              "radial-gradient(ellipse 340px 260px at 50% 45%, transparent 35%, rgba(66, 184, 204, 0.10) 78%, rgba(40, 140, 162, 0.18) 100%)",
          }}
        />
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-amber-bright [animation:float-ember_4s_infinite] [box-shadow:0_0_6px_var(--color-amber)] bottom-[30%] left-[35%]" />
        {/* ★ 결정 모트 — 일부 시안(수정 반짝)으로 동굴 광물 분위기 */}
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-cyan [animation:float-ember_5s_infinite_1.5s] [box-shadow:0_0_6px_rgba(102,224,255,0.8)] bottom-[35%] left-[55%]" />
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-amber-bright [animation:float-ember_4.5s_infinite_2.8s] [box-shadow:0_0_6px_var(--color-amber)] bottom-[25%] left-[48%]" />
        <span className="ember pointer-events-none absolute z-[6] h-[3px] w-[3px] rounded-full bg-cyan [animation:float-ember_5.5s_infinite_0.8s] [box-shadow:0_0_6px_rgba(102,224,255,0.8)] bottom-[28%] left-[62%]" />

        <div
          data-testid="dungeon-grid"
          className="relative z-[2] flex flex-col"
        >
          {data.rows.map((row, ri) => (
            <div key={ri} className="flex">
              {row.map((tile, ci) => {
                const base = baseTile(tile.type);
                // ★ 엔티티 스프라이트 — 몬스터 종류별(tile.sprite) 우선, 없으면 타입 기본.
                const sprite = tile.sprite ?? ENTITY_SPRITE[tile.type];
                // 캐릭터(본인/적/NPC)는 한 칸보다 크게(1.7×) 하단 정렬 — 상세 스프라이트가
                // 자연 비율로 타일 위에 서 있게. 소품(item/stair/door)은 칸에 맞춤.
                const isChar =
                  tile.type === "player" ||
                  tile.type === "enemy" ||
                  tile.type === "npc";
                return (
                  <div
                    key={ci}
                    data-tile={tile.type}
                    className="relative shrink-0"
                    style={{
                      width: CELL,
                      height: CELL,
                      ...(base
                        ? {
                            backgroundImage: `url(${PIX}/${base}.png)`,
                            backgroundSize: "100% 100%",
                          }
                        : {}),
                      ...PIXELATED,
                    }}
                  >
                    {sprite &&
                      (isChar ? (
                        <img
                          src={`${PIX}/${sprite}.png`}
                          alt=""
                          aria-hidden
                          draggable={false}
                          className="pointer-events-none absolute bottom-0 left-1/2 z-[1] max-w-none -translate-x-1/2"
                          style={{ height: CELL * 1.7, width: "auto", ...PIXELATED }}
                        />
                      ) : (
                        <img
                          src={`${PIX}/${sprite}.png`}
                          alt=""
                          aria-hidden
                          draggable={false}
                          className="absolute inset-0 h-full w-full"
                          style={PIXELATED}
                        />
                      ))}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

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
          {data.legend.map((entry, i) => {
            const sprite = ENTITY_SPRITE[entry.type] ?? baseTile(entry.type);
            return (
              <span key={i} className="flex items-center gap-1.5">
                {sprite ? (
                  <img
                    src={`${PIX}/${sprite}.png`}
                    alt=""
                    aria-hidden
                    draggable={false}
                    className="h-4 w-4"
                    style={PIXELATED}
                  />
                ) : (
                  <strong
                    className={`font-bold ${LEGEND_LABEL_COLOR[entry.type]}`}
                  >
                    {entry.ch}
                  </strong>
                )}
                {entry.label}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
