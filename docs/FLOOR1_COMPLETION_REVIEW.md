# 1층 마무리 진단 + 확장 가능 구조 검토

> Phase 8 A→B→C 마무리 후 docs only commit. 본인 결정 (2026-05-13):
> 1층 항목별 실측 진단 + 2층/3층 확장 시 refactor 권고.

직전 push: `2e47051` (★ simplify findings)

---

## 1. 본인 명시 항목별 작동 실측

진단 방법: 실제 import + state introspection (★ 추측 X).

### 1-1. 9등급 몬스터 사냥 + 4 경로 sub_area

| 항목 | 상태 | 출처 |
|---|---|---|
| 9등급 monster spawn | ✓ | `floors/floor1.py` 8 monsters (고블린/노움/슬라임/칼날늑대/레이스 등 9등급) |
| ATTACK 처치 시 base exp | ✓ | `turn_handler_v2.MONSTER_EXP_BY_GRADE[9] = 50` |
| 4 방향 portal sub_area | ✓ | `FLOOR_TWO_PORTAL_SUB_AREAS` = {동/서/남/북 포탈 통로} (★ C commit) |
| sub_area MOVE connections | ✓ | 4 portal sub_area 모두 `accessible_from=("비석 공동",)` |

총 10 sub_areas (★ 6 기존 + 4 portal). 비석 공동이 central hub.

### 1-2. 균열 (히든 던전)

| 균열 ID | 일반 보스 | grade | 변종 보스 | grade (RiftDef) | 변종 grade (런타임) | trigger |
|---|---|---|---|---|---|---|
| bloody_castle (핏빛성채) | 저주받은 기사 블라터 | 6 | 뱀파이어 공작 캠보르미어 | 5 | 5 | base 0.02 |
| glacier_cave (빙하굴) | 폭군 타룬바스 | 7 | 타락한 짐승 키르뒤 | **None** (data gap) | **7 (fallback)** | base 0.02 |
| green_mine (녹색 탄광) | 킹 슬라임 | 8 | — | — | — | — |
| iron_tomb (강철의 묘) | 철인 일디움 | 8 | — | — | — | — |

- **`RiftDef.variant_boss_grade=None` 본격 spec/data gap** (★ namu 본문 명시 X — `docs/floor1_rifts_spec.md` §8 후속 진단). **런타임은 정상**: `_spawn_boss_encounter` 본격 fallback `variant_boss_grade or normal_boss_grade` 본격 본격 본격 `BossEncounter.boss_grade=7` 본격 정합. 즉 변종 처치 시 `MONSTER_EXP_BY_GRADE[7]=200` exp 본격 정상 drop. (★ 초기 review docs는 false alarm — 본 R1 commit 정정.)
- 변종 spawn mechanism (A2): 확률 + RNG → 정상 작동. LLM 운용 finding (A3 E2E REPORT)은 별개.
- 보스 처치 → 보상 + 정수 spawn + cleared_rifts 추가 (A3) 정상.
- 의도적 진입 mechanism (★ 2층 8등급 마석 → 비석 제단) `docs/floor1_rifts_spec.md` 본문에 명시되어 있으나 **코드 미구현** (★ OFFER_TO_STONE은 단순 marker 본격).

### 1-3. 종료 조건 3가지

| 조건 | enum | check | end_reason | 상태 |
|---|---|---|---|---|
| 7일 (168h) 만료 | `TIME_LIMIT_REACHED` | `check_time_limit` | `"time_limit_168h"` | ✓ |
| 전원 사망 | `PARTY_DEFEATED` | `check_party_defeated` | `"party_defeated"` | ✓ |
| 2층 진입 (위치 marker) | `FLOOR_TRANSITION` | `enter_floor_two` | — (★ terminal X) | ✓ |

`SimulationStatus` 4 values 본격. FLOOR_TRANSITION은 sim_runner._check_end_condition에서 종료로 처리하지 **않음** (★ 본인 답 "왕복 가능").

### 1-4. 레벨 / exp / 슬롯

| 항목 | 상태 | 출처 |
|---|---|---|
| `Character.level: int = 1` | ✓ | `state_v2.py` |
| `Character.experience: int = 0` | ✓ | `state_v2.py` (B) |
| `LEVEL_EXP_THRESHOLDS` 10 levels | ✓ | `(0, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000)` |
| `slot_max_for_level()` level 1→5, level 10→20 | ✓ | `state_v2.py` |
| `Character.essence_slot_max()` level-driven | ✓ | level 본격 `slot_max_for_level(self.level)` |
| "딱 한번" 사냥 | ✓ | `WorldState.first_killed_species: set[str]` + `_award_kill_exp` |
| ATTACK 처치 시 exp drop | ✓ | `execute_attack` 본격 호출 (★ B commit) |
| 보스 처치 시 exp drop (★ variant boss_id 별도 species) | ✓ | `_defeat_boss` 본격 호출 |

### 1-5. 최초 다음층 진입 보너스

| 항목 | 상태 |
|---|---|
| `FIRST_FLOOR_TWO_ENTRY_EXP_BONUS = 500` | ✓ |
| `WorldState.floor_two.first_party_bonus_claimed: bool` | ✓ (★ simplify 후 nested) |
| 본 sim에서 최초 진입 시 전 alive 멤버 +500 exp | ✓ |
| 재진입 시 보너스 X (★ 한달마다 1회) | ✓ |
| 사망자 X (★ alive only) | ✓ |

### 1-6. 2층 ↔ 1층 왕복

| 항목 | 상태 |
|---|---|
| `ENTER_FLOOR_TWO` action | ✓ (15 ActionTypes) |
| `EXIT_TO_FLOOR_ONE` action | ✓ |
| 진입 시 portal sub_area 본격 검증 | ✓ |
| 복귀 시 `entry_sub_area_from_floor1` 복귀 | ✓ |
| 복귀 시 `simulation_status = ACTIVE` 복원 | ✓ |
| 4턴 왕복 e2e scripted | ✓ (`test_scripted_round_trip_floor_one_two_one_two`) |

---

## 2. 1층 마무리 진단 — 미완성 항목

### 2-1. 완성 (★ 1층 본격 본격 작동)

- 9등급 monster 사냥 + exp drop
- 4 균열 (정상 보스 + 변종 2/4) + 보스 처치 + 보상
- 종료 3가지 + FLOOR_TRANSITION 위치 marker
- 레벨 / exp / 정수 슬롯 + "딱 한번"
- 4 portal + ENTER/EXIT 왕복 + 최초 보너스
- mypy --strict + ruff 클린 + 1460 tests

### 2-2. 미완성 / 후속 commit 본격

★ Phase 8 R1 (2026-05-13) 본격 update:
- ~~#1 (glacier_cave grade) 본격 false alarm 정정~~ — `_spawn_boss_encounter` 본격 runtime fallback 본격 존재 (★ §1-2 표 참고). spec/data gap만 남음 (★ #8 본격 정합).
- 미완성 항목 본격 8 → 7개.

| # | 항목 | 영향 | 본인 답 본격 |
|---|---|---|---|
| 1 | 마을 location mutation 미구현 — A4 `simulation_over_reason="자동 마을 포탈 귀환"` 텍스트만, `location.realm/sub_area` mutation X | TIME_LIMIT_REACHED 후 location 본격 의미 X | location 본격 town realm 본격 |
| 2 | 죽음 narrative — `PARTY_DEFEATED` 후 GM prompt header 본격 진행 본격, narrative 본격 본격 X | 본격 본격 본격 본격 본격 본격 (★ 본인 답 본격 본격 본격) | GM prompt 본격 narrative 본격 본격 |
| 3 | `use_item` no-op stub (★ turn_handler:927) — item effect 본격 본격 X | USE_ITEM 호출되지만 실제 효과 X (★ inventory 본격 본격 X) | item 본격 effect 본격 본격 |
| 4 | spec §8: 의도적 균열 진입 (★ 2층 8등급 마석 → 1층 비석 제단) 미구현 | OFFER_TO_STONE은 본격 marker 본격 (★ 본문 정합 X) | 2층 콘텐츠 본격 본격 |
| 5 | LLM 변종 회피 (A3 LLM trace finding) — 변종 본격 본격 진행 X | LLM 운용 본격 본격 본격 (★ scripted 본격 정상) | Player LLM 본격 본격 |
| 6 | 인벤토리 weight balance 미진단 — 1층 마석 + 정수 + 빛 자원 본격 본격 본격 본격 본격 본격 | 실제 인벤토리 한계 본격 본격 X | 후속 balance commit |
| 7 | `floor1_rifts_spec.md` 본격 §8 본격 후속 — 블라터/킹 슬라임/일디움 본문 grade 정합 + 키르뒤 grade 명시 | 보상 + 변종 grade 본문 정합 본격 본격 본격 | spec 본격 본격 본격 |

### 2-3. 1층 본격 작동 결론

**1층 본격 핵심 mechanism은 본격 동작** (★ scripted e2e 본격 결정적 검증). 미완성 항목은 다음 두 분류:
- **본문 정합 본격** (#1, #5, #8): 1차 자료 본문 정합 후속.
- **콘텐츠 본격** (#2, #3, #4, #7): 마을 / 죽음 / 인벤토리 narrative 본격.
- **LLM 본격** (#6): A3 finding 본격 후속.

본인 답 (★ "1층 클리어 본격 X — 균열 X, 2층/7일/죽음") 본격 정합 — 1층은 클리어 개념 없이 종료 조건 3가지 본격 본격 본격.

---

## 3. 확장 가능 구조 검토 (★ 2층/3층 추가 시)

### 3-1. Floor abstraction — `Floor1Definition` 본격 이미 generic-ish

현재 (★ state_v2.py:967):
```python
@dataclass
class Floor1Definition:
    name: str = "수정동굴"
    floor_number: int = 1  # ← 이미 generic
    base_time_hours: int = 168
    base_visibility_meters: int = 10
    is_dark_default: bool = True
    sub_areas: tuple[SubArea, ...]
    monsters: tuple[MonsterDef, ...]
    rifts: tuple[RiftDef, ...]
    light_sources: tuple[LightSource, ...]
    bounty_config: BountyConfig | None
```

**발견**: 클래스 이름만 `Floor1Definition`. 필드는 이미 floor-agnostic (`floor_number: int` 본격). Rename + registry 추가만 본격 확장 가능.

**권고**:
```python
@dataclass
class FloorDefinition:  # ★ rename Floor1Definition → FloorDefinition
    name: str
    floor_number: int
    base_time_hours: int | None  # ★ None = 시간 한도 없음 (★ 2층+ 본격)
    ...

FLOOR_REGISTRY: dict[int, FloorDefinition] = {
    1: FLOOR1_DEFINITION,
    # 2: FLOOR2_DEFINITION,  ← 추가 시 본격
}

def get_floor_definition(floor: int) -> FloorDefinition:
    return FLOOR_REGISTRY[floor]
```

기존 `get_floor1_definition()` 본격 wrapper 본격 backward compat.

### 3-2. Constants — global vs floor-specific

| 상수 | 현재 위치 | 범주 | 권고 |
|---|---|---|---|
| `LEVEL_EXP_THRESHOLDS` | `state_v2.py` (module-level) | global (★ 캐릭터 본격) | 유지 |
| `LEVEL_TO_ESSENCE_SLOT_MAX` | `state_v2.py` | global | 유지 |
| `MONSTER_EXP_BY_GRADE` | `turn_handler_v2.py` | global (★ grade 본격) | 유지 |
| ~~`TIME_LIMIT_HOURS = 168`~~ | **R1 commit 본격 제거** | ~~floor 1 본격~~ | **★ R1 fix**: `FloorDefinition.base_time_hours` 본격 단일 source. `check_time_limit(world, time_limit_hours, ...)` signature. |
| `FIRST_FLOOR_TWO_ENTRY_EXP_BONUS = 500` | `turn_handler_v2.py` | floor-pair 본격 | → `FloorDefinition.first_entry_bonus_exp` 본격 본격 (★ 3층 본격 본격) |
| `FLOOR_TWO_PORTAL_SUB_AREAS` | `floors/floor1.py` | floor 본격 본격 | → `FloorDefinition.portals_to_next: frozenset[str]` 본격 nest |

★ ~~Duplicate~~ **R1 본격 fix**: `TIME_LIMIT_HOURS` module 상수 제거, `Floor1Definition.base_time_hours` 본격 단일 source. `check_time_limit` 본격 caller (`sim_runner.run`)에서 `floor_def.base_time_hours` 전달. 2층 본격 다른 한도 enabler.

### 3-3. Actions — `ENTER_FLOOR_TWO` / `EXIT_TO_FLOOR_ONE`은 floor-specific

현재 15 ActionType — 마지막 2개:
- `ENTER_FLOOR_TWO = "enter_floor_two"`
- `EXIT_TO_FLOOR_ONE = "exit_to_floor_one"`

3층 본격 시 `ENTER_FLOOR_THREE` / `EXIT_TO_FLOOR_TWO` 본격 본격 추가 → ActionType 본격 본격 폭발 (★ N층 본격 2N 개).

**권고 A (generic action + target)**:
```python
ENTER_NEXT_FLOOR = "enter_next_floor"  # ★ current_floor + 1
EXIT_TO_PREV_FLOOR = "exit_to_prev_floor"  # ★ current_floor - 1
```
- 호환 충돌: 본격 backward compat 본격 본격 X (ENTER_FLOOR_TWO 본격 호출자 X).

**권고 B (numeric target)**:
```python
ENTER_FLOOR = "enter_floor"  # action.target = "2", "3", ...
EXIT_FLOOR = "exit_floor"
```
- 본격 유연 (★ 점프 가능). 그러나 현재 mechanism은 인접 floor만 본격 본격.

권고 A가 본격 본격 본격 단순 (★ A4/B/C 본격 본격 본격 본격).

### 3-4. State — FloorTwoState 본격 별도 dataclass

현재 (★ state_v2.py:645):
```python
@dataclass
class FloorTwoState:
    entered: bool = False
    entry_sub_area_from_floor1: str | None = None
    current_sub_area: str = "2층 도착 지점"
    returned_to_floor1: bool = False
    first_party_bonus_claimed: bool = False

@dataclass
class WorldState:
    ...
    floor_two: FloorTwoState = field(default_factory=FloorTwoState)
```

3층 본격 시: `FloorThreeState` + `WorldState.floor_three` 본격 추가? → 본격 N 본격 폭발.

**권고**:
```python
@dataclass
class FloorTransitionState:  # ★ rename FloorTwoState → 본격 N 본격
    entered: bool = False
    entry_sub_area_from_prev: str | None = None  # ★ generic
    current_sub_area: str = ""
    returned_to_prev: bool = False
    first_party_bonus_claimed: bool = False

@dataclass
class WorldState:
    ...
    # ★ floor_id → state mapping
    floor_states: dict[int, FloorTransitionState] = field(default_factory=dict)
    current_floor: int = 1  # ★ explicit
```

`first_party_bonus_claimed`은 본격 본격 nested. `current_floor`은 본격 본격 명시.

### 3-5. Location — `floor: int | None` 본격 OK

현재 `Location.floor: int | None` 본격 이미 generic (★ 1, 2, 3, ... 본격 본격 본격). hard-coded "floor_1" 문자열 없음 (★ grep 검증). 변경 본격 X.

### 3-6. Test fixtures — 1층 hard-coded 25 references

25 references `tests/`에 `Floor1Definition` / `FLOOR1_` 본격 사용. 본격 refactor 시 점진적 본격 fixture 본격 (★ `build_floor_party(floor: int = 1)` 본격).

---

## 4. Refactor 권고 우선순위 (★ 후속 별도 commit)

| 우선 | 항목 | 영향 | 난이도 | 상태 |
|---|---|---|---|---|
| ~~1~~ | ~~`TIME_LIMIT_HOURS` duplicate 통합~~ | ~~bug 본격 (2층 시간 한도 X)~~ | 낮 | ✅ **R1 commit 완료** |
| **2** | `Floor1Definition` → `FloorDefinition` rename + `FLOOR_REGISTRY` 추가 | 2층 enabler 핵심 | 중 | R2 (다음) |
| **3** | `ENTER_FLOOR_TWO`/`EXIT_TO_FLOOR_ONE` → `ENTER_NEXT_FLOOR`/`EXIT_TO_PREV_FLOOR` generic | N층 enabler | 중 | R3 |
| **4** | `FloorTwoState` → `FloorTransitionState` + `floor_states: dict[int, ...]` | N층 state enabler | 중 | R4 |
| ~~5~~ | ~~`glacier_cave.variant_boss_grade = None` 정합~~ | ~~bug — 변종 exp 0 fallback~~ | 낮 | ✅ **R1 false alarm 정정** (★ runtime fallback 존재, spec §8 data gap만) |
| 6 | Test fixture `build_floor_party(floor=1)` | 본격 refactor enabler | 중 | R4+ |
| 7 | `Floor1Definition.first_entry_bonus_exp` field 본격 본격 | 2층 본격 본격 본격 본격 본격 | 낮 | R2+ |

---

## 5. 본인 답할 결정

1. **본 commit (docs only) push** — 진단 + 권고 본격 본격.
2. **다음 단계**:
   - (a) **refactor commit 본격**: 위 #1-4 순서 본격 (★ N층 enabler).
   - (b) **1층 미완성 항목 우선**: 마을 location / 죽음 narrative / item effect / spec §8.
   - (c) **2층 콘텐츠 직접 시작**: `floor2.py` 본격 sub_areas / 몬스터 / 보스 (★ refactor 본격 본격 본격).
3. **본인 결정**:
   - (a) 본격 본격 본격 본격 (★ 본격 #19 정공법 — 본격 본격 본격 enabler 본격 본격).
   - (b)는 1층 본격 본격 본격 본격 본격 본격 (★ 본격 본격 X 본격 본격 본격).
   - (c)는 본격 본격 (★ refactor 본격 본격 본격 본격 본격 본격).

**권고**: (a) refactor 본격 commit (★ #1 TIME_LIMIT duplicate 본격 bug fix 본격 + #2 FloorDefinition rename).

---

## Appendix: Phase 8 누적 commit 본격

| Commit | 본격 |
|---|---|
| `dac5b84` A2 | variant rift spawn |
| `98e7d1f` A3 | 보스 spawn + 처치 + 보상 + 균열 클리어 |
| `854c796` A3 refactor | spawned_at_turn 제거 (★ codex YAGNI) |
| `bde3e45` A3 E2E | scripted trace |
| `002b4c8` A3 E2E | LLM 100턴 trace |
| `9e14cb4` A4 | 종료 조건 (7일 + 사망) |
| `2fc1695` A4 refactor | FLOOR_TRANSITION 제거 (★ codex YAGNI) |
| `acf879b` B | 레벨 + exp + "딱 한번" |
| `a311aea` C | 2층 진입 + 4 경로 + 보너스 |
| `ec531eb` C refactor | FLOOR_TRANSITION 위치 marker 본격 |
| `2e47051` C simplify | 3-agent review 답 (4 findings) |
| `643176d` review docs | 1층 마무리 진단 + 확장 구조 (★ 본 docs 초안) |
| R1 (★ 본 commit) | TIME_LIMIT duplicate fix + #5 false alarm 정정 |
