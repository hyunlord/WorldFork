"use client";

import { COMING_OF_AGE_WEAPONS } from "@/lib/types/character";

interface Props {
  value: string;
  onChange: (weapon: string) => void;
}

/**
 * 성인식 무기 선택 (★ 본문 ep_0002 — 부족장 앞에서 무기를 고른다).
 * 방패 고정 해소: 선택 무기가 시작 장착 무기 + element 정합(4284fbc).
 */
export function WeaponSelector({ value, onChange }: Props) {
  return (
    <div className="space-y-3" data-testid="weapon-selector">
      <h2 className="font-serif text-lg tracking-[0.15em] text-amber">
        성년의 무기
        <span className="ml-3 font-sans text-xs tracking-normal text-text-mute">
          성지를 떠나기 전, 스스로에게 맞는 무기를 고른다 (ep_0002)
        </span>
      </h2>
      <div className="grid grid-cols-5 gap-2">
        {COMING_OF_AGE_WEAPONS.map((w) => (
          <button
            key={w.name}
            type="button"
            onClick={() => {
              onChange(w.name);
            }}
            title={w.description}
            data-testid={`weapon-option-${w.name}`}
            className={[
              "cursor-pointer rounded border p-3 text-center transition-all",
              value === w.name
                ? "border-amber bg-bg-elev [box-shadow:0_0_12px_rgba(232,168,56,0.15)]"
                : "border-border-rune bg-bg-panel hover:border-amber/40 hover:bg-bg-elev",
            ].join(" ")}
          >
            <div className="font-serif text-sm tracking-[0.05em] text-text-bright">
              {w.name}
            </div>
          </button>
        ))}
      </div>
      {value && (
        <p className="font-sans text-xs text-text-mute" data-testid="weapon-desc">
          {COMING_OF_AGE_WEAPONS.find((w) => w.name === value)?.description}
        </p>
      )}
    </div>
  );
}
