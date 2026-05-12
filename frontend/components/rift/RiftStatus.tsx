"use client";

/**
 * RiftStatus — 상단 균열 상태 본격.
 */

interface RiftStatusProps {
  activeRiftCount: number;
  totalRiftCount: number;
  inRift: boolean;
  currentRiftName?: string | null;
}

export function RiftStatus({
  activeRiftCount,
  totalRiftCount,
  inRift,
  currentRiftName,
}: RiftStatusProps) {
  return (
    <div className="rift-status">
      <div className="rift-status-main">
        <span className="status-label">활성 균열</span>
        <span className="status-value">
          {activeRiftCount} / {totalRiftCount}
        </span>
      </div>
      {inRift && currentRiftName && (
        <div className="rift-status-current">
          <span className="current-label">현재</span>
          <span className="current-name">🔴 {currentRiftName} 안</span>
        </div>
      )}
    </div>
  );
}
