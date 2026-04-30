# WorldFork

> LLM 기반 한국어 인터랙티브 게임 — 좋아하는 작품 세계관에서 캐릭터로 살아보기

## 개요

WorldFork는 사용자가 좋아하는 작품(소설, 만화, 게임)의 세계관에 들어가서 직접 캐릭터로 살아볼 수 있는 게임 서비스입니다.

**차별화 포인트:**
- 단순 채팅 X, 진짜 게임 메커니즘 (스탯, 인벤토리, 영구 상태)
- 작품명 입력 → 자동 검색 + 플랜 생성 + 사용자 검토 / 수정 (Tier 1+)
- 4축 다양성 (진입 방식 / 모드 / 장르 / 자유도)
- Cross-Model 검증으로 일관성 / 안전성 확보

## 현재 상태

🎉 **Tier 0 (검증 단계) 완료** (2026-04-30)

핵심 산출물:
- ✅ 하네스 3단 (Mechanical / LLM Judge / Eval Set)
- ✅ Layer 1 Ship Gate 100/100 A등급
- ✅ AI Playtester 3 페르소나 정의
- ✅ 50 Eval 케이스 (5 카테고리)
- ✅ ~6,142줄 코드, 223 tests pass

다음: **Tier 1 (DGX Local LLM)** 진입 결정 대기.

상세: `docs/RETROSPECTIVE_TIER_0.md` 참조.

## 문서

- [ROADMAP](docs/ROADMAP.md) — 비전, Tier 0-3, 위험 분석 (v0.2)
- [HARNESS_CORE](docs/HARNESS_CORE.md) — 검증 엔진 (v0.2)
- [HARNESS_LAYER1_DEV](docs/HARNESS_LAYER1_DEV.md) — 개발 하네스
- [HARNESS_LAYER2_SERVICE](docs/HARNESS_LAYER2_SERVICE.md) — 서비스 하네스 (v0.2)
- [AI_PLAYTESTER](docs/AI_PLAYTESTER.md) — AI 도그푸딩 (v0.2)
- [INTEGRATED_RESEARCH_ANALYSIS](docs/INTEGRATED_RESEARCH_ANALYSIS.md) — Phase B 딥리서치 통합 분석
- [PHASE_C_LAUNCH_GUIDE](docs/PHASE_C_LAUNCH_GUIDE.md) — Phase C 진입 가이드

## 시작하기 (Tier 0)

```bash
# 1. 환경 셋업
git clone https://github.com/hyunlord/WorldFork.git
cd WorldFork
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows
pip install -e ".[dev]"

# 2. API 키 설정
cp .env.example .env
# .env 편집, ANTHROPIC_API_KEY 입력

# 3. 첫 실행 (Day 1 산출물 — 곧 추가됨)
python -m service.game.loop
```

## 아키텍처

```
core/      # HARNESS_CORE (LLM Client / 검증 / Eval)
service/   # HARNESS_LAYER2 (게임 파이프라인 / 상태)
tools/     # AI Playtester / 외부 Eval 도구
docs/      # 설계 문서
research/  # Phase B 딥리서치 결과
```

상세: `docs/HARNESS_CORE.md` 참조.

## 기여

이 프로젝트는 1인 개발 + 친구 베타 단계입니다. 외부 기여는 Tier 3 출시 후 검토.

## 라이선스

MIT — [LICENSE](LICENSE) 참조

## 영감 / 참고 작품

WorldFork의 첫 시나리오는 정윤강 작가의 웹소설 *<게임 속 바바리안으로 살아남기>*에서 영감을 받았습니다. 모든 캐릭터 이름과 고유 설정은 변경되었으며, 직접 인용 없이 장르 / 분위기만 차용합니다.
