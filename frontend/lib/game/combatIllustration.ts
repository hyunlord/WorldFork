/**
 * 적 이름 → 전투 일러스트(worldfork combat_monster) 매핑.
 *
 * ★ 다듬기 3순위: 1층 4 zone 전투 일러스트(칼날늑대/노움/구울/고블린)를 EncounterPanel에
 * 연결 — 기존 made-but-never-used(생성만 되고 게임 미표시)였던 일러스트를 실제 전투 조우에 표시.
 * 매핑 없으면 undefined → 컴포넌트가 문자 초상(ch)으로 폴백.
 */
export function combatIllustration(name: string): string | undefined {
  const base = "/assets/worldfork/ui_combat_monster_";
  if (name.includes("늑대")) return `${base}blade_wolf.png`;
  if (name.includes("노움")) return `${base}gnome.png`;
  if (name.includes("구울") || name.includes("레이스")) return `${base}ghoul.png`;
  if (name.includes("고블린")) return `${base}goblin.png`;
  return undefined;
}
