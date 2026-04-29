# Runs — 실험 결과 누적

각 실험 (eval / ablation / 도그푸딩) 결과가 timestamp 디렉토리로 저장됨.

## 구조

```
runs/
├── experiments.csv          # 모든 실험 누적 (commit)
├── 20260429_120000_a1b2c3d/ # 개별 실험 (id = timestamp_gitsha)
│   ├── config.yaml
│   ├── eval_results.json
│   ├── outputs/             # raw LLM 응답 (gitignore)
│   ├── llm_calls.csv        # 호출 로그 (gitignore)
│   └── summary.md           # 사람이 읽는 요약
```

## 정책

- 결과는 절대 삭제 X (회귀 비교용 보존)
- 큰 raw output (outputs/, llm_calls.csv)는 gitignore
- summary.md / eval_results.json / config.yaml은 commit
