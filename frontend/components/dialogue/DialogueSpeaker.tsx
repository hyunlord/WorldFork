"use client";

/**
 * DialogueSpeaker — 좌 화자 panel.
 *
 * Phase 6 dialogue_screen.html .speaker-panel 정합.
 */

export interface SpeakerInfo {
  name: string;
  type: string;
  portraitSrc: string;
  relationLabel?: string;
  communicationLimit?: { current: number; max: number };
  signalStability?: number;
}

interface DialogueSpeakerProps {
  speaker: SpeakerInfo;
}

function renderStars(rating: number): string {
  const filled = "★".repeat(Math.max(0, Math.min(5, Math.round(rating))));
  const empty = "☆".repeat(5 - filled.length);
  return filled + empty;
}

export function DialogueSpeaker({ speaker }: DialogueSpeakerProps) {
  return (
    <div className="speaker-panel">
      <div
        className="speaker-portrait"
        style={{ backgroundImage: `url(${speaker.portraitSrc})` }}
        role="img"
        aria-label={`${speaker.name} 화자 초상화`}
      />
      <div className="speaker-name">{speaker.name}</div>
      <div className="speaker-type">
        {speaker.relationLabel ?? speaker.type}
      </div>

      <div className="speaker-stats">
        {speaker.communicationLimit && (
          <div className="stat-line">
            <span className="label">통신 가능</span>
            <span className="value">
              {speaker.communicationLimit.current} /{" "}
              {speaker.communicationLimit.max}회
            </span>
          </div>
        )}
        {speaker.signalStability !== undefined && (
          <div className="stat-line">
            <span className="label">신호 안정도</span>
            <span className="value">{renderStars(speaker.signalStability)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
