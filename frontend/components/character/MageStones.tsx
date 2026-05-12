"use client";

/**
 * MageStones — 9등급 마석 본격 (★ inventory items 본격 변환).
 *
 * 본격 본질: Character V2는 mage_stones 별도 X — inventory.items 본격
 * '마석' / 'mage_stone' 본격 name match 본격.
 *
 * Phase 6 character_sheet.html .magic-stones 정합 (★ 3 슬롯).
 */

interface InventoryItem {
  name?: string;
  category?: string;
  weight?: number;
}

interface MageStonesProps {
  items: InventoryItem[];
  maxSlots?: number;
}

function isMageStone(item: InventoryItem): boolean {
  const n = item.name ?? "";
  return n.includes("마석") || n.toLowerCase().includes("mage_stone");
}

export function MageStones({ items, maxSlots = 3 }: MageStonesProps) {
  const stones = items.filter(isMageStone);
  return (
    <div className="mage-stones-panel">
      <div className="panel-title">
        ▣ 9등급 마석{" "}
        <span className="slot-count">
          {stones.length}/{maxSlots}
        </span>
      </div>
      <div className="mage-stones-list">
        {Array.from({ length: maxSlots }).map((_, i) => {
          const s = stones[i];
          if (!s) {
            return (
              <div key={i} className="mage-stone empty">
                빈 슬롯
              </div>
            );
          }
          return (
            <div key={i} className="mage-stone filled">
              <div className="mage-stone-name">{s.name ?? `마석 ${i + 1}`}</div>
              {s.category && (
                <div className="mage-stone-type">{s.category}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
