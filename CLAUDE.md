# CLAUDE.md — WorldFork 프로젝트 컨텍스트 (Claude Code용)

이 프로젝트에서 Claude Code가 작업할 때 매번 참조하는 컨텍스트.

## 프로젝트 개요

세계관 속에서 사는 **자율 파티 시뮬레이션 게임** (한국어). 파티원이 성향대로 자율 행동하고,
플레이어가 자연어로 개입하면 그 지시를 성향대로 해석(순응/변형/거부)한다.

## 현재 방향 (★ V3 — 뒤집기)

현행 로드맵: [`docs/ROADMAP_V3.md`](docs/ROADMAP_V3.md) — 자율 파티 RTwP + 성향 엔진.
설계: [`docs/DESIGN_disposition_engine.md`](docs/DESIGN_disposition_engine.md).
**다음 단계: Phase 0 (성향 코어).**

> ⚠️ **V1/V2(턴제 텍스트 어드벤처)는 폐기.** `docs/ROADMAP.md`(V1) / `docs/ROADMAP_V2_BARBARIAN.md`(V2)는
> 역사 참고용. 턴제·정적 선택지·매 행동 LLM 서사 루프로 회귀하지 말 것(도그푸딩 결과 "지루").

### V3 정수 (★ 회귀 방지 — 모든 작업에 적용)

- **게임 코어 = 코드** (즉각·결정적). HP/명중/피해/위치/플래그는 코드가 확정.
- **LLM = 성향 동료의 영혼** (분기점·개입·갈등·결정적 서사만).
- ★ **매 행동 LLM 호출 금지** — 평소는 성향별 코드 패턴(0토큰), LLM은 결정적 순간만.
- **성향 5축**(충성/저돌/지혜/변덕/유대)이 자율 행동 + 지시 해석을 좌우.
- **틱 기반 RTwP**로 시작, 실시간은 나중.

## 핵심 원칙 (모든 작업에 적용)

1. **두 Layer 시스템** (개발 + 서비스, 같은 코어)
2. **Made But Never Used 회피** (도그푸딩 강제)
3. **Cross-Model Verify** (self-rationalization 방지)
4. **정보 격리** (점수 누설 X, issues only) — Tier 0 ablation 검증 중
5. **Mechanical 우선** (0 토큰 게이트)
6. **YAGNI + 검증 우선**
7. **Living Harness** (검증 기준 외부 설정)
8. **AI Playtester는 양/회귀, 인간은 질/재미** (인간 피드백 우선)
9. **CLI 활용** (claude-code / codex-cli / gemini-cli 정액제)
10. **외부 패키지 0건 streak** (`docs/HARNESS_LAYER1_DEV.md` 7장 참조)

## 단계 검증 (V3)

각 Phase = 직접 플레이로 재미 검증(도그푸딩, 가장 중요). 상세: `docs/ROADMAP_V3.md` 3장.
공통 졸업 신호:
- 그 Phase 비전이 직접 플레이에서 "재미있게" 작동
- Mechanical check / Ship gate 매 commit 작동
- made-but-never-used 없음(실게임 배선 검증)
- 재미없으면 그 단계에서 멈추고 조정(이번 여정의 교훈)

## 코드 품질 요구사항

- Python 3.11+
- mypy --strict 통과
- ruff lint 통과
- pytest 단위 테스트 (LLM mock)
- 함수/클래스 docstring (Korean OK)

## 작품 IP 처리 (게임 속 바바리안으로 살아남기)

- 캐릭터 이름 변경 (비요른 → 투르윈, 에쉬드 → 셰인 등)
- 작품명 직접 노출 X
- 고유 설정 비식별 (라프도니아 → 라스카니아 등)
- "유사 작품 영감" 표기

상세: `docs/PHASE_C_LAUNCH_GUIDE.md` 7장

## 외부 패키지 정책

기본: **외부 패키지 0건 streak**

Exception 리스트 (이미 합의된 것만):
- anthropic, openai, google-generativeai, httpx
- python-dotenv, pydantic, pyyaml
- sqlalchemy, pytest 계열
- llama-cpp-python (Tier 1+)
- next, react, vitest, playwright, msw (Tier 2+)
- **@testing-library/react, jsdom** (★ Phase D step 2 — vitest 의 React hook test, frontend 영역 only, runtime 영향 X)
- fastapi, uvicorn (Tier 2 D7+ Web UI 백엔드)
- **types-PyYAML, types-requests** (★ Tier 2 D11 — mypy --strict CI 통과 위한 type stubs, runtime 영향 X)
- **peft, trl, transformers, datasets, torch** (★ 파인튜닝 1단계 — DGX 소유자 승인. 학습 도구 only(tools/finetune/), 게임 runtime 영향 X. core/service 미사용. docs/FINETUNE_STRATEGY.md §7 근거)

이외 패키지 추가는 ROADMAP에 정당화 + 본인 승인 필요.

## 자주 사용하는 명령

```bash
# 개발 환경
source .venv/bin/activate

# 테스트
pytest tests/unit/ -v

# Lint + Type check
ruff check . && mypy core/ --strict

# 게임 실행 (Day 1 이후)
python -m service.game.loop

# Eval (Day 5 이후)
python -m core.eval.runner --eval-set persona_consistency

# Ship gate (Day 5 이후)
./scripts/verify.sh quick
./scripts/ship.sh "feat: ..."
```

## 다음 작업 알고 싶을 때

1. `docs/ROADMAP_V3.md` 3장 (Phase별 로드맵) — 현 단계 = Phase 0 (성향 코어)
2. `docs/DESIGN_disposition_engine.md` 8장 (구현 순서 제안)
3. 각 Phase 후 직접 플레이로 재미 검증(도그푸딩)
