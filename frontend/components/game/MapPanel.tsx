"use client";

import { useEffect } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  floor: number | null;
  subArea: string | null;
  riftId: string | null;
  activeRifts: string[];
}

// rift_id → 한글 표기 (action_handlers.py RIFT_NAME 정합) + floor 1 진입 균열.
const RIFTS: { id: string; name: string; glyph: string }[] = [
  { id: "bloody_castle", name: "핏빛성채", glyph: "♜" },
  { id: "glacier_cave", name: "빙하굴", glyph: "❄" },
  { id: "green_mine", name: "녹색 탄광", glyph: "⛏" },
  { id: "iron_tomb", name: "강철의 묘", glyph: "⚰" },
];

/**
 * 메뉴 지도 — 현재 floor/위치 + floor 1 균열 4종 표시.
 *
 * 성인식 마을(floor 0)에서는 성지/마을, 던전(floor 1+)에서는 진입한 rift를
 * 강조한다. active_rifts(WorldStateV2)로 개방된 균열을 구분.
 */
export function MapPanel({
  open,
  onClose,
  floor,
  subArea,
  riftId,
  activeRifts,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const inVillage = (floor ?? 0) === 0;
  const locationLabel = inVillage
    ? `성지 · ${subArea ?? "성인식 마을"}`
    : `${floor}층 · ${subArea ?? "균열"}`;

  return (
    <div
      className="fixed inset-0 z-[100] flex animate-backdrop-in items-center justify-center bg-[rgba(5,5,8,0.85)] backdrop-blur-[4px]"
      onClick={onClose}
      data-testid="map-panel"
    >
      <div
        className="relative w-[90%] max-w-[560px] animate-modal-in overflow-hidden border border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel [box-shadow:0_24px_64px_rgba(0,0,0,0.8),0_0_32px_var(--torch-glow)]"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="pointer-events-none absolute inset-x-[5%] top-0 h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-60" />

        <header className="flex items-center justify-between border-b border-border-rune bg-bg-deep px-7 py-4">
          <span className="font-serif text-xl font-bold tracking-[0.05em] text-amber-bright [text-shadow:0_0_12px_var(--torch-glow)]">
            ◆ 지도
          </span>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 cursor-pointer items-center justify-center border border-border-rune bg-transparent text-lg text-text-mute hover:border-amber hover:text-amber"
            aria-label="지도 닫기"
          >
            ×
          </button>
        </header>

        <div className="px-7 py-6">
          <section className="mb-6">
            <div className="mb-3 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
              현재 위치
            </div>
            <div
              className="flex items-center gap-3 border border-amber/40 bg-amber/[0.06] px-4 py-3"
              data-testid="map-current"
            >
              <span className="font-mono text-2xl text-amber-bright [text-shadow:0_0_12px_var(--torch-glow)]">
                {inVillage ? "⌂" : "@"}
              </span>
              <span className="font-serif text-[1.05rem] text-text-bright">
                {locationLabel}
              </span>
            </div>
          </section>

          <section>
            <div className="mb-3 border-b border-border-rune pb-2 font-mono text-[0.65rem] uppercase tracking-[0.3em] text-amber">
              1층 균열 4종
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {RIFTS.map((rift) => {
                const isHere = !inVillage && riftId === rift.id;
                const isOpen = activeRifts.includes(rift.id);
                const cls = isHere
                  ? "border-amber bg-amber/[0.12] text-text-bright"
                  : isOpen
                    ? "border-border-rune bg-bg-elev text-text-mid"
                    : "border-dashed border-border-rune bg-bg-void text-text-mute opacity-60";
                return (
                  <div
                    key={rift.id}
                    className={`flex items-center gap-2.5 border px-3.5 py-3 ${cls}`}
                    data-rift-id={rift.id}
                  >
                    <span className="font-mono text-xl">{rift.glyph}</span>
                    <div className="flex flex-col">
                      <span className="font-serif text-[0.95rem]">
                        {rift.name}
                      </span>
                      <span className="font-mono text-[0.6rem] uppercase tracking-[0.15em] text-text-mute">
                        {isHere ? "진입 중" : isOpen ? "개방" : "미개방"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
