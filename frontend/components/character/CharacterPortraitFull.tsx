"use client";

/**
 * CharacterPortraitFull — 풀바디 portrait + 이름 + 종족.
 *
 * Phase 6 character_sheet.html .character-art 정합.
 */

interface CharacterPortraitFullProps {
  name: string;
  imageSrc: string;
  race?: string;
  className?: string;
}

export function CharacterPortraitFull({
  name,
  imageSrc,
  race,
  className,
}: CharacterPortraitFullProps) {
  return (
    <div className="character-portrait-full">
      <div
        className="portrait-full-image"
        style={{ backgroundImage: `url(${imageSrc})` }}
        role="img"
        aria-label={`${name} 풀바디 초상화`}
      />
      <div className="portrait-full-info">
        <div className="portrait-full-name">{name}</div>
        {race && (
          <div className="portrait-full-meta">
            {race}
            {className ? ` · ${className}` : ""}
          </div>
        )}
      </div>
    </div>
  );
}
