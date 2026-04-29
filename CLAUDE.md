# CLAUDE.md — WorldFork 프로젝트 컨텍스트 (Claude Code용)

이 프로젝트에서 Claude Code가 작업할 때 매번 참조하는 컨텍스트.

## 프로젝트 개요

LLM 기반 한국어 인터랙티브 게임. 사용자가 좋아하는 작품 세계관에 들어가서 캐릭터로 살아보는 서비스.

## 현재 위치

Tier 0 (검증 단계) — `docs/ROADMAP.md` 5장 참조

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

## Tier 0 완료 조건 (졸업)

`docs/ROADMAP.md` 5장 "Tier 0 졸업 조건" 참조. 핵심:
- 30분 시나리오 완주 가능
- 본인 5회 + 친구 3-5명 플레이
- 친구 3명 이상 끝까지 완주
- Mechanical check 통과율 80%+
- Layer 1 ship gate 매 commit 작동

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

1. `docs/ROADMAP.md` 5장 (Tier 0)
2. 현재 Day 확인 (git log 또는 README 상단 표시)
3. 해당 Day 산출물 체크리스트 진행

## 본 작업이 어디까지 와야 하는지 모를 때

`docs/PHASE_C_LAUNCH_GUIDE.md` 의 12.1 진행 체크리스트 참조.
