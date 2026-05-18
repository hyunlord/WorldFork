"use client";

/**
 * RiftCard — 균열 본격 카드 (★ 4 균열).
 *
 * Phase 6 rift_entry.html .rift-card 정합.
 */

const ESSENCE_COLOR_HEX: Record<string, string> = {
  빨강: "#c44d4d",
  파랑: "#4d7cc4",
  초록: "#5cb377",
  노랑: "#d4af37",
  흰색: "#e8e8d8",
  검정: "#2a2a2a",
};

interface RiftCardProps {
  riftId: string;
  name: string;
  imageSrc: string;
  grade: number;
  rewardColor?: string;
  description: string;
  active: boolean;
  current: boolean;
  bossName?: string;
  onEnter?: (riftId: string) => void;
}

export function RiftCard({
  riftId,
  name,
  imageSrc,
  grade,
  rewardColor,
  description,
  active,
  current,
  bossName,
  onEnter,
}: RiftCardProps) {
  const rewardHex = rewardColor ? ESSENCE_COLOR_HEX[rewardColor] : undefined;

  return (
    <div
      className={
        "rift-card" +
        (active ? " active" : " inactive") +
        (current ? " current" : "")
      }
    >
      <div
        className="rift-card-image"
        style={{ backgroundImage: `url(${imageSrc})` }}
        role="img"
        aria-label={`${name} 균열 이미지`}
      >
        {!active && <div className="rift-card-locked">잠김</div>}
        {current && <div className="rift-card-current">진입 중</div>}
      </div>
      <div className="rift-card-info">
        <div className="rift-card-name">{name}</div>
        <div className="rift-card-id">{riftId}</div>
        <div className="rift-card-grade">▣ {grade}등급</div>
        {rewardColor && rewardHex && (
          <div className="rift-card-reward">
            <span className="reward-label">보상 정수</span>
            <span
              className="reward-orb"
              style={{
                backgroundColor: rewardHex,
                boxShadow: `0 0 12px ${rewardHex}`,
              }}
            />
            <span className="reward-name">{rewardColor}</span>
          </div>
        )}
        {bossName && (
          <div className="rift-card-boss">
            보스: <strong>{bossName}</strong>
          </div>
        )}
        <div className="rift-card-desc">{description}</div>
        <button
          type="button"
          className="rift-enter-btn"
          disabled={!active || current}
          onClick={() => onEnter?.(riftId)}
        >
          {current ? "이미 진입" : active ? "▸ 진입" : "활성화 필요"}
        </button>
      </div>
    </div>
  );
}
