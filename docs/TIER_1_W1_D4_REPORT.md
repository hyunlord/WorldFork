# Tier 1 W1 D4 보고서 — 풀 사이클

날짜: 2026-05-01  
작업: AI Playtester 풀 사이클 (게임 프롬프트 개선 + 배치 + Seed 변환 + 단위 테스트)

---

## 1. 작업 요약

| 작업 | 내용 | 상태 |
|------|------|------|
| 인프라 구축 | seed_converter.py (FindingToEvalSeed + SeedManager) | ✅ |
| 인프라 구축 | batch.py (BatchRunner + BatchRunResult) | ✅ |
| eval 디렉토리 | evals/auto_added/ + 초기 seed 파일 | ✅ |
| 설정 | config/harness.yaml (auto_seed 한도) | ✅ |
| Round 1 BEFORE | casual_korean_player × W1 D3 원본 프롬프트 | ✅ |
| 게임 프롬프트 개선 | max_tokens 200→500, 5-section system prompt | ✅ |
| Round 2 AFTER | casual_korean_player × 개선 프롬프트 | ✅ |
| 배치 실행 | 6 페르소나 × novice_dungeon_run | ✅ |
| Seed 변환 | 28 findings → 10 추가 (한도 적용) | ✅ |
| 단위 테스트 | test_seed_converter.py (16건) + test_batch.py (8건) | ✅ |

---

## 2. Before/After 비교 (casual_korean_player)

### 측정 조건
- 동일 페르소나: `casual_korean_player`
- 동일 시나리오: `novice_dungeon_run`
- 동일 게임 LLM: `qwen35-9b-q3` (port 8081)
- 동일 Playtester: `claude-code` CLI
- 변경 요소: 게임 GM 시스템 프롬프트 + max_tokens만 변경

### Before vs After 비교표

| 항목 | W1 D3 원본 | Round 1 BEFORE | Round 2 AFTER |
|------|-----------|----------------|---------------|
| `max_tokens` | 200 | 200 | **500** |
| 시스템 프롬프트 | 기본 1줄 | 기본 1줄 | **5-section** |
| `n_turns_played` | 2 | 4 | **7** |
| `fun_rating` | 1/5 | 2/5 | 2/5 (변화 없음) |
| `would_replay` | false | false | false |
| `abandoned` | true | true | true |
| `elapsed_seconds` | 30.0s | 52.3s | 38.8s |
| `findings` 수 | 4 | 4 | 5 |
| 최고 심각도 | critical (잘림) | critical (잘림) | critical (인코딩버그) |

### 개선된 것
- `truncation` 버그 해소: max_tokens 200→500으로 텍스트 잘림 제거
- `tone` 이슈 완화: 5-section 프롬프트로 공문서체(귀하/~습니까) 감소
- 턴 수 증가: 2턴 → 7턴 (플레이어가 더 오래 플레이)

### 개선되지 않은 것
- `fun_rating`: 2/5 유지 (내용 품질 문제, 프롬프트 엔지니어링으로 해결 불가)
- `would_replay`: 여전히 false
- 이탈: 여전히 abandon

### 새로 발생한 문제
- `encoding_bug` (critical): `'籠여져'` — 한자 깨짐 문자 노출
  - 원인: 9B Q3 토크나이저 edge case (low-quant 모델 특성)
  - 분류: 게임 LLM 품질 문제, 프롬프트 개선과 무관

### 결론
> 프롬프트 엔지니어링은 **기술적 버그(잘림/공문서체)를 제거**하는 데 효과적이지만,  
> **콘텐츠 품질(세계관 매력/재미 훅)에는 영향을 주지 못한다.**

---

## 3. 6-페르소나 배치 결과

**실행 조건**: game_client=qwen35-9b-q3, max_turns=30, sleep_between=5.0, work_name="novice_dungeon_run"

### 페르소나별 요약

| 페르소나 | 완주 | 재미 | 이탈 이유 | Findings |
|---------|------|------|-----------|---------|
| casual_korean_player | ❌ | 2/5 | 14턴 — verbose 누적 이탈 | 6 |
| confused_beginner | ❌ (오류) | 0/5 | CLI not found: gemini | 0 |
| troll | ❌ (거부) | 0/5 | claude-code가 IP 추출 시도 거부 | 0 |
| hardcore_lore_fan | ❌ | 2/5 | Turn 1 이탈 — 세계관 얕음 | 3 |
| roleplayer | ✅ | 4/5 | 완주 30턴 | 0 |
| speed_runner | ❌ | 2/5 | 8턴 — 진행 너무 느림 | 6 |

**avg_fun**: 1.67/5.0 (완주 페르소나 제외 시 2.0/4개)

### Findings 집계

| 구분 | 수치 |
|------|------|
| 총 findings | 15 |
| critical | 0 (배치에서는 없음) |
| major | 9 |
| minor (moderate 포함) | 6 |

**카테고리별 (top 3)**:
1. `verbose`: **9건** — 응답 과잉 (전체의 60%)
2. `ux`: 1건
3. 나머지: pacing/worldbuilding/space_rules/localization/too_many_choices 각 1건

### 주요 인사이트

**`verbose` 도미넌스**: 9B Q3 모델이 짧게 답하는 경향이 없음. 프롬프트로 일부 완화 가능하나 근본 해결은 콘텐츠 재설계 필요.

**`roleplayer` 아웃라이어**: 유일한 완주 페르소나. 오히려 verbose한 응답이 몰입을 높임. 페르소나별 평가 기준 분리의 필요성 확인.

**`confused_beginner` 실패**: DGX에 gemini CLI 미설치. W1 D5에서 backup_cli fallback 로직 필요.

**`troll` 실패**: claude-code가 적대적/IP 추출 시도를 거부. W1 D5에서 troll 페르소나를 codex CLI로 우회.

---

## 4. Finding → Eval Seed 변환 결과

### 전체 findings 수집

| 출처 | Findings |
|------|---------|
| Round 1 BEFORE | 4 |
| Round 2 AFTER | 5 |
| 배치 (6 세션) | 15 |
| W1 D3 초기 세션 | 4 |
| **합계** | **28** |

### SeedManager 적용 (max_per_day=20, max_per_category=5)

| 카테고리 | 변환 후 | 추가됨 | 거부됨 |
|---------|---------|--------|--------|
| korean_quality | ≥5 | 5 | 초과분 |
| general | ≥5 | 5 | 초과분 |
| ip_leakage | - | 0 | - |
| **합계** | 28 | **10** | **18** |

거부 이유: `max_per_category=5` 한도 초과 (각 카테고리 5개 이후 자동 거부)

### 생성된 파일
- `evals/auto_added/korean_quality.jsonl` — 5 seeds
- `evals/auto_added/general.jsonl` — 5 seeds

---

## 5. 단위 테스트 결과

### test_seed_converter.py (16 tests)

| 클래스 | 테스트 | 검증 내용 |
|--------|--------|-----------|
| TestFindingToEvalSeed | 11 | category 매핑, version, metadata, ID, to_jsonl roundtrip |
| TestSeedManager | 5 | 한도 내, max_per_category, max_per_day, 혼합 카테고리, jsonl 파일 생성 |

### test_batch.py (8 tests)

| 클래스 | 테스트 | 검증 내용 |
|--------|--------|-----------|
| TestBatchRunnerInit | 2 | game_client 저장, sleep_between 저장 |
| TestBatchAggregateFindings | 6 | 빈 결과, 단일 세션, severity 집계, category 집계, by_persona, avg_fun, skipped 집계, 멀티 세션 |

**총 24 단위 테스트** (모두 Mock 기반, LLM 호출 없음)

---

## 6. 게임 프롬프트 개선 내용

### 변경 전 (W1 D3)
```
system: "당신은 한국어 텍스트 어드벤처 게임의 GM입니다."
max_tokens: 200
```

### 변경 후 (W1 D4)
```
system: 5-section 프롬프트
  - 격식체 사용 (...입니다, ...있습니다)
  - 공문서체 X ('존경하는' / '귀하' / '~습니까' X)
  - 간결한 묘사 (3-5 문장 이내)
  - 한국어만 (영단어 + 괄호 한국어 형식 X)
  - 행동 선택지 2-3개 마지막에 제시

user: 3-part 구조
  1. 현재 위치 (1-2 문장)
  2. 보이는 것/들리는 것 (1-2 문장)
  3. 가능한 행동 2-3개

max_tokens: 500
```

---

## 7. 인프라 추가 목록

| 파일 | 내용 |
|------|------|
| `tools/ai_playtester/seed_converter.py` | FindingToEvalSeed, SeedManager, EvalSeed |
| `tools/ai_playtester/batch.py` | BatchRunner, BatchRunResult |
| `evals/auto_added/` | auto_added seed 디렉토리 + README |
| `evals/auto_added/general.jsonl` | 5 seeds |
| `evals/auto_added/korean_quality.jsonl` | 5 seeds |
| `config/harness.yaml` | auto_seed 한도 설정 |
| `tests/unit/test_seed_converter.py` | 16 단위 테스트 |
| `tests/unit/test_batch.py` | 8 단위 테스트 |

---

## 8. 다음 단계 (W1 D5 예고)

1. **encoding_bug 대응**: 9B Q3 토크나이저 edge case — 후처리 필터 또는 모델 교체
2. **confused_beginner 복구**: DGX에 gemini CLI 설치 또는 backup_cli fallback
3. **troll 복구**: troll 페르소나 → codex CLI로 우회
4. **verbose 근본 해결**: `max_tokens=150` 강제 또는 시나리오 콘텐츠 재설계
5. **재미 훅 개선**: 첫 30초 내 흥미 유발 요소 (위험/보상/비밀) 추가 → casual_korean_player fun_rating 3+ 목표
