# barbarian — state schema 후보 (★ 본인 결정 대기)

> 자료 분석: `docs/design/barbarian_extracted.md`
> 본인 의문: "RPG적 요소가 있는건 작품에 따라 다르지" → 작품 매칭 본질
> 본 commit: 디자인 후보만, 본격 구현은 본인 결정 후

## 본인 결정 기준 (★ 반복 가능)

| 측면 | 가중치 |
|------|--------|
| 작품 게임감 정합 | ★★★ |
| 30분 시나리오 (Tier 0) 적합 | ★★ |
| 본인 컨디션 한계 (★ 컴팩트) | ★ |
| 추후 확장 여지 | ★ |
| Mechanical 검증 가능 (점수 0 토큰) | ★★★ |

## 후보 A — 단순 누적 (★ 기존 영역 A plan)

```python
@dataclass
class Character:
    hp: int
    inventory: list[str]
```

**장점**:
- 즉각 구현 (★ 30분 안)
- 기존 `service/game/state.py` 와 정합
- LLM이 다루기 쉬움

**단점**:
- 사이드뷰 액션 RPG 게임감 X
- 자료의 정수/종족/외피/스킬/도감 진짜 누락
- 본인 의문 ("작품에 따라 다르지") 진짜 정합 X

## 후보 B — 팬게임 매칭 (★ 본인 직관 정합 가설)

```python
from dataclasses import dataclass, field
from enum import Enum

class ItemKind(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    OTHER = "other"

@dataclass
class Item:
    name: str
    kind: ItemKind
    description: str = ""

@dataclass
class Skill:
    slot: str               # "Q" / "W" / "E" / "R"
    name: str
    cost: int               # 자원 소모 (★ 정수 또는 stamina)
    cooldown: int           # 턴 단위
    description: str

@dataclass
class CodexEntry:
    kind: str               # "monster" / "item" / "location"
    name: str
    discovered: bool        # 도감 = 발견 시 진짜
    notes: str = ""

@dataclass
class Location:
    floor: int              # 1~8+
    is_rift: bool = False   # 균열 여부 (★ 난이도 +1)
    description: str = ""

@dataclass
class Character:
    name: str
    race: str               # "바바리안" 등
    hp: int
    hp_max: int
    inventory: list[Item] = field(default_factory=list)
    equipped: dict[str, Item] = field(default_factory=dict)  # weapon / armor
    skills: dict[str, Skill] = field(default_factory=dict)   # slot -> skill
    codex: list[CodexEntry] = field(default_factory=list)
    location: Location | None = None
    alive: bool = True      # 영구사망

@dataclass
class GameState:
    character: Character
    turn: int
    history: list  # 기존 turn history 유지
    game_over: bool = False
```

**장점**:
- 팬게임 진짜 매칭 (★ Q/W/E/R / I 인벤 / TAB 도감)
- 본인 직관 정합 (★ 작품 게임감 진짜)
- Mechanical 검증 명확 (★ HP 0 = 영구사망 게이트)

**단점**:
- 큰 디자인 — 6개 dataclass + Enum
- LLM이 다중 schema 다루는 stochastic 위험
- 30분 시나리오에 Skill/Codex 진짜 활용? 검증 필요

## 후보 C — 작품 + 팬게임 종합 (★ 풀 시뮬레이션)

후보 B에 추가:

```python
@dataclass
class Companion:
    name: str               # "에르웬" 등
    race: str
    role: str               # "사제" / "연금술사" / "탐험가"
    alive: bool = True
    revivable: bool = True  # 작품 부활 시스템 (★ 검증 필요)
    bond: int = 0           # 호감도

@dataclass
class WorldState:
    explored_floors: set[int] = field(default_factory=set)
    discovered_npcs: list[str] = field(default_factory=list)
    discovered_factions: list[str] = field(default_factory=list)  # 노아르크/라프도니아
    story_progress: int = 0  # 0~100 (★ 30분 시나리오 진행도)

@dataclass
class GameState:
    character: Character    # B와 같음
    party: list[Companion]  # 파티 (★ 에르웬 등)
    world: WorldState
    turn: int
    history: list
    triggered_events: list[str]  # 트리거된 이벤트
    game_over: bool = False
```

**장점**:
- 진짜 풀 시뮬레이션 (★ 파티/세계관 진짜)
- 작품 핵심 시스템 (정수/외피/원탁회의 등) 추가 여지
- 다음 사이클 확장 base

**단점**:
- 매우 큰 디자인 (★ 8+ dataclass)
- Tier 0 (★ 30분 시나리오) overkill 위험
- LLM context window 압박 (★ 27B 25-100s 응답 더 느려짐)
- 본인 컨디션 한계 → 다음 세션 본격

## 후보 B-lite (★ 본인 권장 — 추가 제안)

후보 B에서 30분 시나리오에 진짜 핵심만:

```python
@dataclass
class Item:
    name: str
    kind: str   # "weapon" / "armor" / "consumable" / "other"
    notes: str = ""

@dataclass
class Skill:
    slot: str   # "Q" / "W" / "E" / "R"
    name: str
    description: str  # cost/cooldown은 LLM 자유 묘사 (★ Tier 0 검증 후 strict)

@dataclass
class Character:
    name: str
    race: str
    hp: int
    hp_max: int
    location_floor: int           # 단순 int (Location dataclass X)
    inventory: list[Item] = field(default_factory=list)
    equipped_weapon: Item | None = None
    equipped_armor: Item | None = None
    skills: list[Skill] = field(default_factory=list)  # 0~4개
    codex_seen: set[str] = field(default_factory=set)  # 단순 string set
    alive: bool = True

@dataclass
class GameState:
    character: Character
    turn: int
    history: list
    game_over: bool = False
```

**장점**:
- 후보 B의 90% 게임감, 절반 복잡도
- Codex/Location 단순화 → LLM 부담 ↓
- Mechanical 검증: HP, alive, 인벤토리 명확
- 후보 C로 점진 확장 가능 (★ Companion 추가 등)

**단점**:
- Skill에 cost/cooldown 없음 → "마나가 부족하다" 같은 시뮬레이션 못함 (★ Tier 0 OK?)
- Location은 floor 만 (★ "균열" 등 nuance X)

## 비교 표

| 후보 | dataclass 수 | 작품 정합 | Tier 0 적합 | 본인 컨디션 부담 | 확장성 |
|------|--------------|-----------|-------------|------------------|--------|
| A | 1 | ★ | ★★★ | ★ | ★ |
| B | 6 | ★★★ | ★★ | ★★★ | ★★★ |
| **B-lite** | **4** | **★★★** | **★★★** | **★★** | **★★★** |
| C | 8+ | ★★★★ | ★ | ★★★★ | ★★★★ |

## 본인 결정 시점

- **A 또는 B-lite**: 다음 commit 즉각 구현 (★ ~1-2시간)
- **B**: 다음 세션 본격 (★ ~2-4시간)
- **C**: 다음다음 세션 + 별도 디자인 사이클 (★ ~1주+)

## 다음 사이클 우선순위 (★ 본인 결정)

A/B-lite/B/C 결정 후:
1. **state schema** 코드 (★ `service/game/state.py` 또는 신규)
2. **scenario YAML 갱신** (★ `service/game/scenarios/*.yaml`)
3. **prompt 갱신** (★ `service/game/loop.py` build_gm_prompt)
4. **Mechanical 검증 갱신** (★ `core/verify/mechanical.py`)
5. **frontend UI** (★ 인벤토리 / HP / 스킬 표시)

순서는 본인 결정 (★ 백엔드 먼저? UI 먼저?).
