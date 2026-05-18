"use client";

/**
 * CombatActions — 전투 본격 행동 panel.
 *
 * 본문 정합 (★ service/sim/types.py PlayerActionType subset):
 * - attack / flee / use_item / absorb_essence / wait — 전투 본격 가능
 * - explore / communicate / rest — 전투 중 disable
 */

interface CombatActionDef {
  id: string;
  label: string;
  primary?: boolean;
  combatDisabled?: boolean;
}

const COMBAT_ACTIONS: ReadonlyArray<CombatActionDef> = [
  { id: "attack", label: "공격", primary: true },
  { id: "flee", label: "도주" },
  { id: "use_item", label: "아이템" },
  { id: "absorb_essence", label: "정수 흡수" },
  { id: "explore", label: "탐색", combatDisabled: true },
  { id: "communicate", label: "대화", combatDisabled: true },
  { id: "wait", label: "대기" },
  { id: "rest", label: "휴식", combatDisabled: true },
];

interface CombatActionsProps {
  currentTurn?: string;
  onAction?: (actionId: string) => void;
  inCombat?: boolean;
}

export function CombatActions({
  currentTurn,
  onAction,
  inCombat = true,
}: CombatActionsProps) {
  return (
    <div className="action-panel">
      <div className="panel-title">
        {currentTurn ? `▣ ${currentTurn}의 차례` : "▣ 행동 선택"}
      </div>
      <div className="action-buttons">
        {COMBAT_ACTIONS.map((a) => {
          const disabled = inCombat && Boolean(a.combatDisabled);
          return (
            <button
              key={a.id}
              type="button"
              className={
                "combat-btn" +
                (a.primary ? " primary" : "") +
                (disabled ? " disabled" : "")
              }
              disabled={disabled}
              onClick={() => onAction?.(a.id)}
            >
              {a.label}
              {disabled && <span className="cost">전투 중 X</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
