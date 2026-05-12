/**
 * DungeonTimer — 미궁 잔여 시간 (★ low 본격 pulse).
 *
 * Phase 6 main_screen.html .dungeon-time 정합.
 */

interface DungeonTimerProps {
  hoursRemaining: number;
  maxHours?: number;
}

export function DungeonTimer({
  hoursRemaining,
  maxHours = 168,
}: DungeonTimerProps) {
  const percentage = (hoursRemaining / maxHours) * 100;
  const isLow = percentage < 30;

  return (
    <div className={`dungeon-timer${isLow ? " low" : ""}`}>
      <div className="timer-label">미궁 잔여 시간</div>
      <div className="timer-hours">{hoursRemaining}h</div>
      <div className="timer-max">/ {maxHours}h</div>
    </div>
  );
}
