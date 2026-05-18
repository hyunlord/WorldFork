"use client";

/**
 * Minimap — 1층 6 sub_areas (★ floor1.py 정합).
 *
 * 본격 본문 (★ floor1.py):
 * - 진입점 (★ 시작)
 * - 북쪽 통로 (★ 고블린)
 * - 남쪽 통로 (★ 노움/슬라임)
 * - 비석 공동 (★ 374화 의도적 균열)
 * - 동쪽 통로 (★ 칼날늑대/레이스)
 * - 포탈 근처 (★ 2층 진입)
 */

interface SubAreaSpec {
  name: string;
  x: number;
  y: number;
}

const SUB_AREAS: ReadonlyArray<SubAreaSpec> = [
  { name: "진입점", x: 0, y: 110 },
  { name: "북쪽 통로", x: 90, y: 10 },
  { name: "비석 공동", x: 90, y: 110 },
  { name: "남쪽 통로", x: 90, y: 210 },
  { name: "동쪽 통로", x: 180, y: 110 },
  { name: "포탈 근처", x: 180, y: 210 },
];

interface MinimapProps {
  currentSubArea?: string | null;
}

export function Minimap({ currentSubArea }: MinimapProps) {
  return (
    <div className="minimap">
      <div className="minimap-title">▣ 1층 미궁</div>
      <div className="minimap-grid">
        {SUB_AREAS.map((area) => (
          <div
            key={area.name}
            className={`sub-area${area.name === currentSubArea ? " current" : ""}`}
            style={{ top: `${area.y}px`, left: `${area.x}px` }}
          >
            {area.name}
          </div>
        ))}
      </div>
    </div>
  );
}
