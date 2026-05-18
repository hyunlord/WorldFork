"use client";

/**
 * VfxOverlay — VFX + 데미지 number 본격.
 *
 * Phase 6 combat_screen.html .vfx 정합.
 */

type DamageType = "normal" | "crit" | "miss" | "heal";

export interface DamageNumber {
  value: number;
  type?: DamageType;
  x?: number;
  y?: number;
}

interface VfxOverlayProps {
  showAxeVfx?: boolean;
  showMagicVfx?: boolean;
  damages?: DamageNumber[];
}

function formatDamage(d: DamageNumber): string {
  if (d.type === "miss") return "MISS";
  if (d.type === "heal") return `+${d.value}`;
  if (d.type === "crit") return `${d.value}!`;
  return String(d.value);
}

export function VfxOverlay({
  showAxeVfx = false,
  showMagicVfx = false,
  damages = [],
}: VfxOverlayProps) {
  return (
    <div className="vfx-area">
      {showAxeVfx && (
        <div
          className="vfx-axe"
          style={{
            backgroundImage:
              "url(/assets/worldfork/ui_combat_vfx_axe_strike.png)",
          }}
        />
      )}
      {showMagicVfx && (
        <div
          className="vfx-magic"
          style={{
            backgroundImage:
              "url(/assets/worldfork/ui_combat_vfx_magic_missile.png)",
          }}
        />
      )}
      {damages.map((d, i) => (
        <div
          key={i}
          className={`damage-number ${d.type ?? "normal"}`}
          style={{
            top: `${d.y ?? 100 + i * 60}px`,
            left: `${d.x ?? 220 + i * 100}px`,
          }}
        >
          {formatDamage(d)}
        </div>
      ))}
    </div>
  );
}
