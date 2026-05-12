"use client";

/**
 * DialogueInfo — 우 정보 panel (★ 발견 정보 + 단서 + 시간).
 *
 * Phase 6 dialogue_screen.html .info-panel 정합.
 */

export interface DiscoveryItem {
  key: string;
  value: string;
  isNew?: boolean;
}

export interface Clue {
  text: string;
}

interface DialogueInfoProps {
  discoveryItems?: DiscoveryItem[];
  clues?: Clue[];
  hoursRemaining?: number;
}

export function DialogueInfo({
  discoveryItems = [],
  clues = [],
  hoursRemaining,
}: DialogueInfoProps) {
  return (
    <div className="info-panel">
      <div className="info-section">
        <div className="info-section-title">▣ 발견 정보</div>
        {discoveryItems.length === 0 ? (
          <div className="empty-message">발견된 정보 X.</div>
        ) : (
          discoveryItems.map((item, i) => (
            <div key={i} className="info-item">
              <span className="info-key">{item.key}:</span> {item.value}
              {item.isNew && <span className="new-tag">NEW</span>}
            </div>
          ))
        )}
      </div>

      <div className="info-section">
        <div className="info-section-title">▣ 단서</div>
        {clues.length === 0 ? (
          <div className="empty-message">단서 X.</div>
        ) : (
          clues.map((clue, i) => (
            <div key={i} className="clue">
              {clue.text}
            </div>
          ))
        )}
      </div>

      {hoursRemaining !== undefined && (
        <div className="info-section">
          <div className="info-section-title">▣ 미궁 시간</div>
          <div className="hours-large">{hoursRemaining}h 남음</div>
        </div>
      )}
    </div>
  );
}
