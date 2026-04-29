# Evals — Eval Set (JSONL)

`docs/HARNESS_CORE.md` 5장 참조.

## 구조

```
evals/
├── persona_consistency/
│   ├── v1.jsonl
│   └── v2.jsonl   # 변경 시 +1
├── korean_quality/
├── json_validity/
├── ai_breakout/
├── game_state_hallucination/
└── auto_added/    # AI Playtester 자동 추가 (격리)
```

## 정책

- 이전 버전 절대 삭제 X (회귀 비교용)
- 변경 시 version +1 + harness.yaml 업데이트
