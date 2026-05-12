"use client";

/**
 * ActivateRiftPanel — OFFER_TO_STONE 본격 (★ 374화 비석 공물).
 *
 * 본격 조건:
 * - 위치 = 비석 공동
 * - 정수 보유 ≥ 1 (★ 8등급 마석 본격 본격)
 *
 * Phase 6 rift_entry.html .activate 정합.
 */

interface ActivateRiftPanelProps {
  inStoneChamber: boolean;
  essenceCount: number;
  onActivate?: () => void;
}

export function ActivateRiftPanel({
  inStoneChamber,
  essenceCount,
  onActivate,
}: ActivateRiftPanelProps) {
  const canActivate = inStoneChamber && essenceCount > 0;

  return (
    <div className="activate-rift-panel">
      <div className="activate-title">▣ 균열 활성화 (OFFER_TO_STONE)</div>
      <div className="activate-desc">
        비석 공동에서 정수/8등급 마석을 공물로 바쳐 균열을 활성화한다 (★ 374화).
      </div>
      <div className="activate-status">
        <div
          className={`status-item${inStoneChamber ? " ok" : " missing"}`}
        >
          {inStoneChamber ? "✓" : "✗"} 비석 공동 위치
        </div>
        <div className={`status-item${essenceCount > 0 ? " ok" : " missing"}`}>
          {essenceCount > 0 ? "✓" : "✗"} 정수 보유 ({essenceCount})
        </div>
      </div>
      <button
        type="button"
        className="activate-btn"
        disabled={!canActivate}
        onClick={onActivate}
      >
        {canActivate ? "▸ OFFER_TO_STONE" : "조건 미충족"}
      </button>
    </div>
  );
}
