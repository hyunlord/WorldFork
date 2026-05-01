# Auto-Added Eval Seeds

자료 AI_PLAYTESTER 5.3 — 자동 추가는 별도, 본인 검토 후 채택.

## 워크플로

```
AI Playtester 발견 이슈
   ↓
seed_converter.py → EvalSeed
   ↓
SeedManager → 한도 체크 (max_per_day=20, max_per_category=5)
   ↓
auto_added/{category}.jsonl 에 append
   ↓
주 1회 본인 검토 (수동)
   ↓
승인된 것만 → evals/{category}/v_next.jsonl
```

## 한도 (자료 5.4)

- max_per_day: 20
- max_per_category: 5
- review_within_days: 7 (검토 안 하면 자동 폐기)
