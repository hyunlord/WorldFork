/**
 * 실 게임 state → DungeonView 타일 (★ DEMO_DUNGEON mock 제거).
 *
 * backend는 공간 타일 맵을 두지 않는다(state_v2: 사이드뷰 좌표는 Tier 4 — 현재 X).
 * 게임은 추상 로그라이크 — location(floor)/encounters(적 리스트)/characters(본인).
 * 따라서 이 어댑터는 방 프레임(벽/바닥)을 합성하되, 배치 엔티티는 ★ 실 state에서만
 * 가져온다 — 실 본인 + 실 encounters(적 수/종류 반영). 가짜 엔티티(과거 한스/약탈자)
 * 0. state 없으면 null 반환 → 호출자가 mock 대신 명시적 로딩을 띄운다(DEMO fallback
 * 우려 차단). ※ 좌표는 예시(공간 시뮬 부재)나 무엇이 있는가는 실데이터다.
 */

import type { GameStateV2 } from "@/lib/api/v2";

import type { DungeonViewData, Tile, TileType } from "@/components/game/types";

// ★ 방을 좌측 패널에 더 채우기 위해 격자 확대(픽셀 2단계 — 작은 방+빈 어둠 해소).
//   배치 spot(아래)은 모두 이 범위 내. 엔티티 수는 실 state(불변).
const COLS = 15;
const ROWS = 11;
// 적 배치 후보(내부 상단~중앙, 결정적). 실 encounters 수만큼 앞에서 채운다.
const ENEMY_SPOTS: ReadonlyArray<readonly [number, number]> = [
  [2, 3],
  [2, 9],
  [3, 6],
  [4, 4],
  [4, 10],
  [5, 7],
];
const PLAYER_SPOT: readonly [number, number] = [ROWS - 3, 6]; // 하단 중앙
const STAIR_SPOT: readonly [number, number] = [1, COLS - 2]; // 상단 우측(하강 출구)
const MAX_ENEMIES = ENEMY_SPOTS.length;

const CH: Record<TileType, string> = {
  wall: "▓",
  floor: "·",
  player: "@",
  enemy: "g",
  npc: "N",
  item: "!",
  stair: ">",
  door: "|",
  blank: " ",
};

function tile(type: TileType): Tile {
  return { ch: CH[type], type };
}

/**
 * 실 게임 state → 던전 타일 격자. state 없거나 마을(floor<1)이면 null.
 *
 * 엔티티는 실 state에서만: 본인(characters의 is_player) + 적(encounters의 hostile).
 * mock 엔티티를 만들지 않는다.
 */
export function buildDungeonView(
  state: GameStateV2 | null,
  turn: number,
): DungeonViewData | null {
  if (!state) return null;
  const floor = state.location?.floor ?? 0;
  if (floor < 1) return null; // 마을(0층)은 DungeonView 미사용

  // 방 프레임 — 테두리 wall, 내부 floor
  const grid: Tile[][] = [];
  for (let r = 0; r < ROWS; r += 1) {
    const row: Tile[] = [];
    for (let c = 0; c < COLS; c += 1) {
      const border = r === 0 || r === ROWS - 1 || c === 0 || c === COLS - 1;
      row.push(tile(border ? "wall" : "floor"));
    }
    grid.push(row);
  }

  // 하단 중앙 테두리에 출입문(진입 방향)
  grid[ROWS - 1][6] = tile("door");
  // 하강 출구(계단) — 실제 층 이동 지점
  grid[STAIR_SPOT[0]][STAIR_SPOT[1]] = tile("stair");

  // ★ 실 적 — encounters의 적대 항목만, 그 수만큼 배치(가짜 X)
  const encounters = state.encounters ?? [];
  const hostiles = encounters.filter(
    (e) => e.hostile === true || e.is_hostile === true,
  );
  const shown = hostiles.slice(0, MAX_ENEMIES);
  shown.forEach((_, i) => {
    const [r, c] = ENEMY_SPOTS[i];
    grid[r][c] = tile("enemy");
  });

  // ★ 본인 — characters의 is_player(실 state)
  grid[PLAYER_SPOT[0]][PLAYER_SPOT[1]] = tile("player");

  // 범례 — 화면에 실제로 그린 것만
  const legend: { ch: string; type: TileType; label: string }[] = [
    { ch: CH.player, type: "player", label: "본인" },
  ];
  if (shown.length > 0) {
    legend.push({ ch: CH.enemy, type: "enemy", label: `적 ×${shown.length}` });
  }
  legend.push({ ch: CH.stair, type: "stair", label: "하강 출구" });

  return { turn, rows: grid, legend };
}
