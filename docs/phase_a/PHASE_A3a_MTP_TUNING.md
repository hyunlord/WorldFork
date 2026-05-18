# Phase A.3-a — MTP 한국어 acceptance 튜닝

## 배경

Phase A.2 (commit `e1f60fb`) 에서 SGLang FP8 + MTP cutover 완료. 한국어 prompt 의 MTP acceptance rate 가 낮아 효율이 떨어진다는 본인 지적에 따라 speculative config 의 한국어 정합 측정.

직전 관찰:
- accept rate: 0.18 ~ 0.42 (★ 한국어 낮음)
- accept len: ~1.9 (★ 기대 3-4 미달)
- elapsed: 22 ~ 24 s/turn (Phase A.2 측정)

목표: accept rate 0.5+ 또는 latency 가 더 빠른 config 결정.

## 측정 환경

- Host: NVIDIA GB10 (CUDA 13.0)
- SGLang image: `lmsysorg/sglang:v0.5.12`
- Model: `Qwen-Qwen3.6-27B` (safetensors), `--quantization fp8` (on-the-fly)
- Common flags: `--tp-size 1 --mem-fraction-static 0.70 --context-length 32768 --reasoning-parser qwen3 --grammar-backend xgrammar --mamba-scheduler-strategy extra_buffer`
- ENV: `SGLANG_ENABLE_SPEC_V2=1` (★ v6 제외)
- 9B encounter (llama-server, port 8083) 은 측정 내내 그대로 유지

측정 도구:
- `scripts/bench_mtp.py` — 한국어 prompt 5개 × `max_tokens=400`, `temperature=0.7`
- `scripts/bench_mtp_variants.sh <v1..v6>` — container destroy → recreate → /health 대기 → bench
- 한국어 prompt 5종 (★ 본문 어조 정합):
  1. 비요른이 횃불을 켜자 어둠이 걷히며
  2. 한스가 천천히 다가왔다. 그의 눈빛은
  3. 균열 너머에서 들리는 그르렁대는 소리. 비요른은
  4. 마석 거래소의 노인은 본인을 보더니
  5. 에르웬의 손길이 비석을 어루만지자

## 결과 표 (7 config)

| Variant | num-steps | draft-tokens | elapsed avg (s) | client tok/s | accept_rate | accept_len | server tok/s |
|---------|-----------|--------------|-----------------|--------------|-------------|------------|---------------|
| baseline | 3 | 4 | 27.55 | 14.54 | 0.448 | 2.341 | 10.53 |
| v1 | 2 | 2 | 27.91 | 14.37 | 0.695 | 2.390 | 13.87 |
| v2 | 2 | 4 | 28.62 | 14.02 | 0.678 | 2.357 | 13.61 |
| v3 | 1 | 2 | 32.62 | 12.27 | 0.799 | 1.799 | 11.90 |
| **v4** | **4** | **2** | **26.41** | **15.16** | 0.526 | **3.108** | **14.36** |
| v5 | 3 | 2 | 27.42 | 14.68 | 0.547 | 2.642 | 13.76 |
| v6 | OFF | — | 52.66 | 7.60 | n/a | n/a | n/a |

`accept_rate` / `accept_len` / `server tok/s` 는 SGLang container 의 `Decode batch` 로그에서 추출 (★ `scripts/bench_mtp.py` 의 `parse_container_decode_lines` 정규식).

원본 JSON: `docs/phase_a/mtp_bench_{baseline,v1..v6}.json`

## 관찰

1. **MTP 효과 확인**: v6 (MTP off) 7.60 tok/s 대비 MTP 활성 config 12.27 ~ 15.16 tok/s — 약 **1.6 ~ 2.0×** 가속.
2. **steps 증가 → accept_len 상승, accept_rate 하락**: v3 (steps=1) accept 0.799/1.799 → v4 (steps=4) 0.526/3.108. accept_rate 가 떨어져도 accept_len 이 길어서 절대 throughput 은 증가.
3. **draft=4 (baseline, v2) 가 한국어 prompt 에 비효율**: 긴 draft 가 한국어 token sequence 와 정합 X — accept_rate 약 0.45 ~ 0.68 정체. draft=2 로 줄이면 0.53 ~ 0.80 으로 상승.
4. **v4 (steps=4, draft=2)** 가 client elapsed / client tok/s / accept_len / server tok/s 모든 정량 지표에서 1위. v5 (steps=3, draft=2) 가 근소 2위.

## 결정 — v4 적용

채택 사유:
- elapsed avg 26.41s (★ baseline 대비 −1.14s = −4.1%)
- client tok/s 15.16 (★ baseline 대비 +0.62 = +4.3%)
- accept_len 3.108 (★ baseline 2.341 대비 +0.77 = 기대 범위 3-4 진입)
- accept_rate 0.526 (★ 목표 0.5+ 통과)
- server tok/s 14.36 (★ baseline 10.53 대비 +36%)

trade-off:
- accept_rate 자체는 v1 (0.695), v3 (0.799) 가 더 높음. 그러나 짧은 draft / short steps 로 인해 절대 throughput 떨어짐.
- v4 의 accept_rate 0.526 은 한국어 prompt 다양성에 노출되면 추가 하락 가능. 본인 manual play 의 본문 어조 정합 검증 필요.

## 적용 config (★ 본 시점 컨테이너 상태)

```
docker run -d \
  --name sglang-narrative-27b-fp8-mtp \
  --gpus all --shm-size 32g \
  -p 8081:8081 \
  -v /home/hyunlord/models/hf/Qwen-Qwen3.6-27B:/model \
  -e SGLANG_ENABLE_SPEC_V2=1 \
  lmsysorg/sglang:latest \
  python -m sglang.launch_server \
    --model-path /model \
    --served-model-name qwen3.6-27b \
    --host 0.0.0.0 --port 8081 \
    --tp-size 1 \
    --mem-fraction-static 0.70 \
    --context-length 32768 \
    --quantization fp8 \
    --reasoning-parser qwen3 \
    --grammar-backend xgrammar \
    --mamba-scheduler-strategy extra_buffer \
    --speculative-algo NEXTN \
    --speculative-num-steps 4 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 2
```

## 검증 (Step 6)

- `tools/play_30_turns_auto.py` 30-turn auto play 결과는 본 commit 직후 측정.
- Ship Gate 95+ 통과 시 본 config 확정.
- 한국어 quality 본인 manual 검증 별도.

## 위험 / 미확인

1. 한국어 prompt 5종에 over-fit 가능성 — 실 backend prompt (system + character + state context) 는 길이/구조가 다르므로 일반화 측정 추가 필요.
2. accept_rate 0.526 은 prompt 분포에 민감 — 본인 manual play 30 + 친구 5명 측정 후 일반 분포 확인 권장.
3. cuda graph capture 후 첫 prompt 의 outlier (★ v6 의 첫 prompt 들 동일 52.5s) — temperature 효과 또는 cache miss 영향 측정 필요.
4. mem-fraction 0.70 + 9B 공존 GPU 점유 확인 — GB10 nvidia-smi 메모리 미표시라 실제 마진 미상.

## 후속 (Phase A.3-b+)

- xgrammar `structural_tag` schema 도입 (★ 본문 어조 강제, accept_rate 영향 측정)
- 9B encounter SGLang 이전 (★ 현재 llama-server)
- AWQ 4-bit 본 FP8 비교 (★ 메모리 마진 확대)
