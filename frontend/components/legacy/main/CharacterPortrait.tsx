/**
 * CharacterPortrait — 양쪽 portrait + name/race/hp.
 *
 * Phase 6 main_screen.html .character.left/.right 정합.
 */

interface CharacterPortraitProps {
  name: string;
  imageSrc: string;
  side: "left" | "right";
  race?: string;
  hp?: number;
  hpMax?: number;
}

export function CharacterPortrait({
  name,
  imageSrc,
  side,
  race,
  hp,
  hpMax,
}: CharacterPortraitProps) {
  return (
    <div className={`character-portrait ${side}`}>
      <div
        className="portrait-image"
        style={{ backgroundImage: `url(${imageSrc})` }}
        role="img"
        aria-label={`${name} 초상화`}
      />
      <div className="portrait-info">
        <div className="portrait-name">{name}</div>
        {race && <div className="portrait-race">{race}</div>}
        {hp !== undefined && hpMax !== undefined && (
          <div className="portrait-hp">
            HP {hp}/{hpMax}
          </div>
        )}
      </div>
    </div>
  );
}
