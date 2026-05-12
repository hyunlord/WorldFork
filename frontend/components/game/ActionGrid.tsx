"use client";

/**
 * ActionGrid — 13 PlayerActionType buttons (★ service/sim/types.py 정합).
 *
 * 본문 본격 13:
 *   ACTIVATE_LIGHT, MOVE, EXPLORE, ATTACK, ABSORB_ESSENCE, USE_ITEM,
 *   OFFER_TO_STONE, ENTER_RIFT, EXIT_RIFT, REST, WAIT, COMMUNICATE, FLEE
 *
 * Phase 7d 본격: console.log only (★ 본격 API integration 7h).
 */

interface ActionDef {
  id: string;
  label: string;
  primary?: boolean;
}

const ACTIONS: ReadonlyArray<ActionDef> = [
  { id: "activate_light", label: "빛 활성" },
  { id: "move", label: "이동" },
  { id: "explore", label: "탐색" },
  { id: "attack", label: "공격" },
  { id: "absorb_essence", label: "정수 흡수", primary: true },
  { id: "use_item", label: "아이템" },
  { id: "offer_to_stone", label: "비석 공물" },
  { id: "enter_rift", label: "균열 진입" },
  { id: "exit_rift", label: "균열 이탈" },
  { id: "rest", label: "휴식" },
  { id: "wait", label: "대기" },
  { id: "communicate", label: "대화" },
  { id: "flee", label: "도주" },
];

interface ActionGridProps {
  onAction?: (actionId: string) => void;
  inRift?: boolean;
  hasFloatingEssence?: boolean;
}

export function ActionGrid({
  onAction,
  inRift = false,
  hasFloatingEssence = false,
}: ActionGridProps) {
  function isDisabled(id: string): boolean {
    if (id === "enter_rift" && inRift) return true;
    if (id === "exit_rift" && !inRift) return true;
    if (id === "absorb_essence" && !hasFloatingEssence) return true;
    return false;
  }

  return (
    <div className="actions">
      <div className="actions-title">▣ 행동 선택</div>
      <div className="action-grid">
        {ACTIONS.map((action) => {
          const disabled = isDisabled(action.id);
          return (
            <button
              key={action.id}
              type="button"
              className={
                "action-btn" +
                (action.primary ? " primary" : "") +
                (disabled ? " disabled" : "")
              }
              disabled={disabled}
              onClick={() => onAction?.(action.id)}
            >
              {action.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
