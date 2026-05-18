#!/bin/bash
# Phase A.3-a — SGLang 27B 6 variant container restart + bench.
#
# 사용: bash scripts/bench_mtp_variants.sh <variant>
#   variant: v1 | v2 | v3 | v4 | v5 | v6
#
# 각 variant 본 container destroy → recreate → /health 대기 → bench_mtp.py 실행.

set -euo pipefail

VARIANT="${1:-}"
if [[ -z "$VARIANT" ]]; then
  echo "usage: $0 <v1|v2|v3|v4|v5|v6>"
  exit 2
fi

CONTAINER="sglang-narrative-27b-fp8-mtp"
IMAGE="lmsysorg/sglang:latest"
MODEL_HOST="/home/hyunlord/models/hf/Qwen-Qwen3.6-27B"
PORT=8081
OUT_DIR="docs/phase_a"
OUT="$OUT_DIR/mtp_bench_${VARIANT}.json"

mkdir -p "$OUT_DIR"

# variant flag
case "$VARIANT" in
  v1)
    LABEL="v1_steps2_draft2"
    SPEC_FLAGS=(--speculative-algo NEXTN --speculative-num-steps 2 \
                --speculative-eagle-topk 1 --speculative-num-draft-tokens 2)
    SPEC_ENV=(-e SGLANG_ENABLE_SPEC_V2=1)
    ;;
  v2)
    LABEL="v2_steps2_draft4"
    SPEC_FLAGS=(--speculative-algo NEXTN --speculative-num-steps 2 \
                --speculative-eagle-topk 1 --speculative-num-draft-tokens 4)
    SPEC_ENV=(-e SGLANG_ENABLE_SPEC_V2=1)
    ;;
  v3)
    LABEL="v3_steps1_draft2"
    SPEC_FLAGS=(--speculative-algo NEXTN --speculative-num-steps 1 \
                --speculative-eagle-topk 1 --speculative-num-draft-tokens 2)
    SPEC_ENV=(-e SGLANG_ENABLE_SPEC_V2=1)
    ;;
  v4)
    LABEL="v4_steps4_draft2"
    SPEC_FLAGS=(--speculative-algo NEXTN --speculative-num-steps 4 \
                --speculative-eagle-topk 1 --speculative-num-draft-tokens 2)
    SPEC_ENV=(-e SGLANG_ENABLE_SPEC_V2=1)
    ;;
  v5)
    LABEL="v5_steps3_draft2"
    SPEC_FLAGS=(--speculative-algo NEXTN --speculative-num-steps 3 \
                --speculative-eagle-topk 1 --speculative-num-draft-tokens 2)
    SPEC_ENV=(-e SGLANG_ENABLE_SPEC_V2=1)
    ;;
  v6)
    LABEL="v6_mtp_disabled"
    SPEC_FLAGS=()
    SPEC_ENV=()
    ;;
  *)
    echo "unknown variant: $VARIANT"
    exit 2
    ;;
esac

echo "============================================================"
echo "Variant: $VARIANT ($LABEL)"
echo "============================================================"

docker stop "$CONTAINER" >/dev/null 2>&1 || true
docker rm "$CONTAINER" >/dev/null 2>&1 || true

echo "[start] docker run …"
docker run -d \
  --name "$CONTAINER" \
  --gpus all \
  --shm-size 32g \
  -p "${PORT}:${PORT}" \
  -v "${MODEL_HOST}:/model" \
  "${SPEC_ENV[@]}" \
  "$IMAGE" \
  python -m sglang.launch_server \
    --model-path /model \
    --served-model-name qwen3.6-27b \
    --host 0.0.0.0 \
    --port "$PORT" \
    --tp-size 1 \
    --mem-fraction-static 0.70 \
    --context-length 32768 \
    --quantization fp8 \
    --reasoning-parser qwen3 \
    --grammar-backend xgrammar \
    --mamba-scheduler-strategy extra_buffer \
    "${SPEC_FLAGS[@]}" \
  >/dev/null

echo "[wait] /health (★ max 600s) …"
T0=$(date +%s)
while true; do
  if curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1; then
    echo "  ready in $(( $(date +%s) - T0 ))s"
    break
  fi
  if [[ $(( $(date +%s) - T0 )) -ge 600 ]]; then
    echo "  TIMEOUT — last 30 log lines:"
    docker logs --tail 30 "$CONTAINER" 2>&1
    exit 1
  fi
  sleep 5
done

# settling delay (★ cuda graph capture 안정화)
sleep 8

echo "[bench] …"
.venv/bin/python scripts/bench_mtp.py \
  --label "$LABEL" \
  --runs 1 \
  --warmup \
  --output "$OUT" 2>&1 | tail -25

echo "[done] $OUT"
