# Research — Phase B 딥리서치 결과

> WorldFork 프로젝트 Phase B (딥리서치) 결과물 보관소.
> 각 카테고리별 raw 결과 + 본인 정리 요약.
>
> 정리: 2026-04-29

## 디렉토리 구조

```
research/
├── 00_README.md                       # 이 파일
├── 01_models_and_sft/                 # ROADMAP 9.1 결정 근거
│   ├── gemini1_raw.md                 # Strategic Analysis (244줄)
│   ├── gemini2_raw.md                 # WorldFork Architecture (315줄)
│   └── summary.md                     # 본인 정리 (한국어 핵심)
│
├── 02_competitive/                    # ROADMAP 9.2 결정 근거
│   ├── gpt1_raw.md                    # 한국 시장 경쟁 분석 (200줄)
│   └── summary.md
│
├── 03_technical_patterns/             # ROADMAP 9.3 결정 근거
│   ├── gemini2_raw.md                 # (Architecture 부분 재사용)
│   ├── gpt2_raw.md                    # 프로덕션 AI 툴링 (152줄)
│   └── summary.md
│
└── 04_eval_tools/                     # ROADMAP 9.4 결정 근거
    ├── claude1_raw.md                 # EvalRunner 보고서 (694줄)
    ├── claude2_raw.md                 # HARNESS Eval 비교 (456줄)
    └── summary.md
```

총 6개 raw 결과, 약 2060줄.

## 핵심 통합 분석

전체 통합 분석은 별도 파일:
- `INTEGRATED_RESEARCH_ANALYSIS.md` (메인 디렉토리, 602줄)

이 통합 분석이 ROADMAP / HARNESS v0.2 업데이트의 근거.

## 사용 방법

### 본인이 검토할 때

1. `INTEGRATED_RESEARCH_ANALYSIS.md` 먼저 읽기 (602줄, 핵심)
2. 의문 / 더 깊이 알고 싶은 부분 → 해당 카테고리의 raw 결과
3. 통합 분석에서 언급된 인용 / 출처 무작위 샘플 검증

### 향후 결정 근거로 활용

ROADMAP / HARNESS v0.2 변경 시:
1. 새 결정의 근거가 이 research/ 어디에 있는지 명시
2. git commit message에 `(research/01/...)` 같은 참조
3. v0.3 이상 업데이트 시 새 research/ 추가 (절대 덮어쓰기 X)

## 결과 신뢰도

각 카테고리의 신뢰도는 `summary.md` 참조.

전반적 평가:
- ★★★ (검증됨): Eval 도구 패턴 (Claude 1, 2 일치)
- ★★★ (학술 근거): Dense > MoE for 페르소나
- ★★ (출처 풍부): 한국 시장 분석
- ★★ (실측 권장): 모델 latency / quantization
- ★ (주의): 정확한 사용자 수치 / 일부 인용 링크

## 다음 단계

Phase C (Tier 0 시작) 진입:
1. ROADMAP / HARNESS v0.2 업데이트 완료 ✅
2. WorldFork 레포 첫 commit (구조 + research/ 포함)
3. Tier 0 Day 1 시작

---

*문서 끝.*
