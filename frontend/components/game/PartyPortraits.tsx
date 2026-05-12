"use client";

/**
 * PartyPortraits — 중상단 비요른 / 에르웬 portrait.
 *
 * Phase 6 gameplay_screen.html .party 본격.
 */

import type { CharacterV2 } from "@/lib/api/v2";

const GAMEPLAY_PORTRAIT_BY_NAME: Record<string, string> = {
  비요른: "/assets/worldfork/ui_gameplay_bjorn.png",
  에르웬: "/assets/worldfork/ui_gameplay_erwen.png",
};

interface PartyPortraitsProps {
  characters: Record<string, CharacterV2>;
}

export function PartyPortraits({ characters }: PartyPortraitsProps) {
  const names = Object.keys(characters);
  return (
    <div className="party-portraits">
      {names.map((name) => {
        const bgImage =
          GAMEPLAY_PORTRAIT_BY_NAME[name] ??
          "/assets/worldfork/ui_gameplay_bjorn.png";
        return (
          <div
            key={name}
            className="party-member"
            style={{ backgroundImage: `url(${bgImage})` }}
            role="img"
            aria-label={`${name} 초상화`}
          >
            <div className="party-name">{name}</div>
          </div>
        );
      })}
    </div>
  );
}
