/**
 * PartyStats — 좌/우 stats blocks (★ 탐사대 / 층 / 누적 / 등급).
 *
 * Phase 6 main_screen.html .stats.left/.right 정합.
 */

interface PartyStatsProps {
  partySize: number;
  currentFloor?: string;
  maxFloor?: string;
  dungeonGrade?: string;
  totalHours?: number;
}

export function PartyStats({
  partySize,
  currentFloor = "1층",
  maxFloor = "10층",
  dungeonGrade = "9등급",
  totalHours = 0,
}: PartyStatsProps) {
  return (
    <>
      <div className="party-stats left">
        <div className="stat-label">탐사대</div>
        <div className="stat-value">{partySize}명</div>
        <div className="stat-label">현재 층</div>
        <div className="stat-value">
          {currentFloor} / {maxFloor}
        </div>
      </div>
      <div className="party-stats right">
        <div className="stat-label">총 누적 시간</div>
        <div className="stat-value">{totalHours}h</div>
        <div className="stat-label">미궁 등급</div>
        <div className="stat-value">{dungeonGrade}</div>
      </div>
    </>
  );
}
