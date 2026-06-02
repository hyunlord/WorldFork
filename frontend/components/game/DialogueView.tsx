"use client";

import { useEffect } from "react";

import type { ParsedDialogue } from "@/lib/game/dialogue";

interface Props {
  data: ParsedDialogue;
  open: boolean;
  onClose: () => void;
}

// ui_dialogue PNG (frontend/public/assets/worldfork) — 대화창 프레임 배경.
const DIALOGUE_BG = "/assets/worldfork/ui_dialogue_message_stone.png";

// 화자 성별 추정 → 초상(ui_dialogue_other_*). 단서 없으면 남성 기본.
const FEMALE_HINTS = ["실렌", "여인", "소녀", "여성", "어머니", "딸", "아내", "마녀", "여사제"];

function portraitForSpeaker(speaker: string): string {
  const female = FEMALE_HINTS.some((h) => speaker.includes(h));
  return `/assets/worldfork/ui_dialogue_other_${female ? "female" : "male"}.png`;
}

/**
 * NPC 대화 전용 UI — handle_dialogue narrative를 발화/지문 분리 표시.
 *
 * narrative 텍스트로만 흐르던 NPC 대화(case A)를 ui_dialogue PNG 프레임 위에
 * 화자 + 발화 말풍선 + 지문으로 구성한 visual-novel 식 대화창으로 보여준다.
 */
export function DialogueView({ data, open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open || !data.isDialogue) return null;

  return (
    <div
      className="pointer-events-none absolute inset-x-0 bottom-[78px] z-[80] flex justify-center px-6"
      data-testid="dialogue-view"
    >
      <div
        className="pointer-events-auto relative w-full max-w-[760px] animate-modal-in overflow-hidden border border-amber/50 bg-cover bg-center bg-no-repeat [box-shadow:0_16px_48px_rgba(0,0,0,0.7),0_0_24px_var(--torch-glow)]"
        style={{ backgroundImage: `url(${DIALOGUE_BG})` }}
      >
        <div className="flex gap-4 bg-[rgba(8,8,12,0.78)] px-7 py-5 backdrop-blur-[2px]">
          {/* ★ 화자 초상 — 현 FLUX 일러스트(ui_dialogue_other_*) 활용 */}
          <img
            src={portraitForSpeaker(data.speaker)}
            alt={data.speaker}
            data-testid="dialogue-portrait"
            className="h-[150px] w-[116px] shrink-0 self-start border border-amber/40 object-cover [box-shadow:0_0_14px_rgba(0,0,0,0.6)]"
          />

          <div className="flex-1">
          <div className="mb-3 flex items-center justify-between border-b border-amber/30 pb-2">
            <span
              className="font-serif text-[1.05rem] font-bold tracking-[0.05em] text-amber-bright [text-shadow:0_0_10px_var(--torch-glow)]"
              data-testid="dialogue-speaker"
            >
              ◆ {data.speaker}
            </span>
            <button
              type="button"
              onClick={onClose}
              className="flex h-7 w-7 cursor-pointer items-center justify-center border border-border-rune bg-transparent text-base text-text-mute hover:border-amber hover:text-amber"
              aria-label="대화 닫기"
            >
              ×
            </button>
          </div>

          <div className="flex flex-col gap-2.5 font-narrative text-[1.02rem] leading-[1.7]">
            {data.segments.map((seg, i) =>
              seg.kind === "speech" ? (
                <p
                  key={i}
                  className="text-text-bright [text-shadow:0_0_6px_rgba(232,168,56,0.25)]"
                  data-testid="dialogue-speech"
                >
                  <span className="mr-1.5 text-amber">"</span>
                  {seg.text}
                  <span className="ml-1.5 text-amber">"</span>
                </p>
              ) : (
                <p
                  key={i}
                  className="text-[0.92rem] italic text-text-mid"
                >
                  {seg.text}
                </p>
              ),
            )}
          </div>
          </div>
        </div>
      </div>
    </div>
  );
}
