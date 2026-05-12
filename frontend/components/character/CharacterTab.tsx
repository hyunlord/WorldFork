"use client";

/**
 * CharacterTab — 비요른 / 에르웬 본격 선택.
 *
 * Phase 6 character_sheet.html .tabs 정합.
 */

interface CharacterTabProps {
  names: string[];
  selected: string;
  onSelect: (name: string) => void;
}

export function CharacterTab({
  names,
  selected,
  onSelect,
}: CharacterTabProps) {
  return (
    <div className="character-tabs">
      {names.map((name) => (
        <button
          key={name}
          type="button"
          className={`character-tab${name === selected ? " active" : ""}`}
          onClick={() => onSelect(name)}
        >
          {name === selected ? `▸ ${name}` : name}
        </button>
      ))}
    </div>
  );
}
