#!/bin/bash
# Ship Gate 전 서비스 헬스체크·자동 기동 (★ SKIP_VERIFY 상시 우회 제거).
#
# down 서비스 자동 start → gate의 Eval Smoke(8083) / Browser E2E(4000) 단계가
# 인프라 미가동 때문에 점수를 잃는 구조적 문제 해결.
#
# 설계 원칙:
# - 자동 기동 대상: 9B(8083) llama-server, backend(8090) uvicorn, frontend(4000) next dev
# - 검토만(자동 start X): 27B(8081) docker sglang (root 권한)
# - backend는 /health(실제 FastAPI)로 판별 — http.server 잔재 오판 방지
# - 실패 시 경고만 — gate 강제 중단 X (해당 단계만 점수 영향)
# - 멱등: 이미 UP이면 skip
#
# 환경 변수:
#   SKIP_ENSURE=1     → 전체 skip
#   ENSURE_9B=0       → 9B 자동 기동 skip
#   ENSURE_BACKEND=0  → backend 자동 기동 skip
#   ENSURE_FE=0       → frontend 자동 기동 skip

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ─── 기동 대상 정의 (★ Step 1 진단 정합) ───
LLAMA_SERVER="${LLAMA_SERVER:-/home/hyunlord/repos/llama.cpp/build/bin/llama-server}"
MODEL_9B="${MODEL_9B:-/home/hyunlord/models/gguf/qwen35-9b/Qwen3.5-9B-UD-Q3_K_XL.gguf}"
MODEL_GEMMA="${MODEL_GEMMA:-/home/hyunlord/models/poc/gemma-4-12B-it-Q4_K_M.gguf}"
PORT_9B=8083
PORT_GEMMA=8085   # pivotal GM (Gemma 4 12B) — local_client get_gemma4_12b 정합
PORT_FE=4000
PORT_BACKEND=8090
PORT_27B=8081

LLM_HEALTH_TIMEOUT="${LLM_HEALTH_TIMEOUT:-90}"   # 9B model load 대기 (초)
GEMMA_HEALTH_TIMEOUT="${GEMMA_HEALTH_TIMEOUT:-180}"  # Gemma 12B load 대기 (초)
FE_HEALTH_TIMEOUT="${FE_HEALTH_TIMEOUT:-120}"    # next dev cold compile 대기 (초)
HEALTH_INTERVAL=3


# ─── 헬스체크 ───
_check() {
    # $1 port, $2 path
    curl -sf -m 3 "http://localhost:${1}${2}" >/dev/null 2>&1
}

_wait_health() {
    # $1 name, $2 port, $3 path, $4 timeout
    local name=$1 port=$2 path=$3 timeout=$4 elapsed=0
    echo "[ensure]   ${name} 헬스체크 대기 (max ${timeout}s)..."
    while [ "$elapsed" -lt "$timeout" ]; do
        if _check "$port" "$path"; then
            echo "[ensure]   ${name} (${port}) ✅ UP (${elapsed}s)"
            return 0
        fi
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
    done
    echo "[ensure]   ${name} (${port}) ⚠️  ${timeout}s 내 미응답"
    return 1
}


# ─── 9B (8083) llama-server ───
ensure_9b() {
    if [ "${ENSURE_9B:-1}" != "1" ]; then
        echo "[ensure] 9B (8083) skip (ENSURE_9B=0)"
        return 0
    fi
    if _check "$PORT_9B" "/health"; then
        echo "[ensure] 9B (8083) ✅ 이미 UP"
        return 0
    fi
    if [ ! -x "$LLAMA_SERVER" ]; then
        echo "[ensure] 9B (8083) ⚠️  llama-server 바이너리 없음: $LLAMA_SERVER"
        return 1
    fi
    if [ ! -f "$MODEL_9B" ]; then
        echo "[ensure] 9B (8083) ⚠️  model 파일 없음: $MODEL_9B"
        return 1
    fi
    echo "[ensure] 9B (8083) DOWN → llama-server 자동 start..."
    nohup "$LLAMA_SERVER" \
        -m "$MODEL_9B" \
        --port "$PORT_9B" \
        --host 0.0.0.0 \
        -ngl 99 \
        -c 8192 \
        --jinja \
        > /tmp/llama_9b.log 2>&1 &
    disown
    _wait_health "9B" "$PORT_9B" "/health" "$LLM_HEALTH_TIMEOUT"
}


# ─── Gemma 4 12B (8085) llama-server — pivotal GM ───
#   GEMMA_GM=0(런타임) 이면 게임이 27B로 폴백하므로 서빙도 skip 가능(ENSURE_GEMMA=0).
ensure_gemma() {
    if [ "${ENSURE_GEMMA:-1}" != "1" ] || [ "${GEMMA_GM:-1}" = "0" ]; then
        echo "[ensure] Gemma (8085) skip (ENSURE_GEMMA=0 또는 GEMMA_GM=0 — 27B 폴백)"
        return 0
    fi
    if _check "$PORT_GEMMA" "/health"; then
        echo "[ensure] Gemma (8085) ✅ 이미 UP"
        return 0
    fi
    if [ ! -x "$LLAMA_SERVER" ]; then
        echo "[ensure] Gemma (8085) ⚠️  llama-server 바이너리 없음: $LLAMA_SERVER"
        return 1
    fi
    if [ ! -f "$MODEL_GEMMA" ]; then
        echo "[ensure] Gemma (8085) ⚠️  model 파일 없음: $MODEL_GEMMA"
        return 1
    fi
    echo "[ensure] Gemma (8085) DOWN → llama-server 자동 start..."
    nohup "$LLAMA_SERVER" \
        -m "$MODEL_GEMMA" \
        --port "$PORT_GEMMA" \
        --host 0.0.0.0 \
        -ngl 99 \
        -c 8192 \
        --jinja \
        > /tmp/llama_gemma.log 2>&1 &
    disown
    _wait_health "Gemma" "$PORT_GEMMA" "/health" "$GEMMA_HEALTH_TIMEOUT"
}


# ─── frontend (4000) next dev ───
# 포트 3000은 ml-hub-frontend(docker) 점유 → WorldFork는 4000 사용
ensure_frontend() {
    if [ "${ENSURE_FE:-1}" != "1" ]; then
        echo "[ensure] frontend (4000) skip (ENSURE_FE=0)"
        return 0
    fi
    if _check "$PORT_FE" "/"; then
        echo "[ensure] frontend (4000) ✅ 이미 UP"
        return 0
    fi
    if [ ! -d "$REPO_ROOT/frontend/node_modules" ]; then
        echo "[ensure] frontend (4000) ⚠️  node_modules 없음 — npm install 필요"
        return 1
    fi
    echo "[ensure] frontend (4000) DOWN → next dev 자동 start..."
    (
        cd "$REPO_ROOT/frontend" || exit 1
        nohup npm run dev -- -p "$PORT_FE" > /tmp/frontend_dev.log 2>&1 &
        disown
    )
    _wait_health "frontend" "$PORT_FE" "/" "$FE_HEALTH_TIMEOUT"
}


# ─── backend (8090) uvicorn ───
# ★ /health(실제 FastAPI)로 판별 — GET /만 받는 http.server 잔재 오판 방지.
#   8090을 http.server 잔재가 점유 시 narrow kill 후 uvicorn 기동.
ensure_backend() {
    if [ "${ENSURE_BACKEND:-1}" != "1" ]; then
        echo "[ensure] backend (8090) skip (ENSURE_BACKEND=0)"
        return 0
    fi
    if _check "$PORT_BACKEND" "/health"; then
        echo "[ensure] backend (8090) ✅ 이미 UP"
        return 0
    fi
    # /health 미응답인데 포트 점유 시 — http.server 잔재 narrow kill
    # (★ 'http.server ... 8090' 만 매칭 — 실제 'uvicorn service.api.app'는 불일치)
    if pgrep -f "http.server.*${PORT_BACKEND}" >/dev/null 2>&1; then
        echo "[ensure] backend (8090) ⚠️  http.server 잔재 점유 → kill"
        pkill -f "http.server.*${PORT_BACKEND}" 2>/dev/null || true
        sleep 1
    fi
    echo "[ensure] backend (8090) DOWN → uvicorn 자동 start..."
    (
        cd "$REPO_ROOT" || exit 1
        nohup .venv/bin/uvicorn service.api.app:app \
            --host 0.0.0.0 --port "$PORT_BACKEND" \
            > /tmp/uvicorn_backend.log 2>&1 &
        disown
    )
    _wait_health "backend" "$PORT_BACKEND" "/health" "$LLM_HEALTH_TIMEOUT"
}


# ─── 27B (8081) — 검토만 (docker sglang, root) ───
review_27b() {
    if _check "$PORT_27B" "/v1/models"; then
        echo "[ensure] 27B (8081) ✅ UP"
    else
        echo "[ensure] 27B (8081) ⚠️  DOWN — docker sglang 수동 기동 필요 (자동 start X)"
    fi
}


main() {
    if [ "${SKIP_ENSURE:-0}" = "1" ]; then
        echo "[ensure] SKIP_ENSURE=1 — 헬스체크 skip"
        return 0
    fi
    echo "=== ensure_services — Ship Gate 전 인프라 헬스체크 ==="
    local warn=0
    ensure_9b || warn=1
    ensure_gemma || warn=1
    ensure_backend || warn=1
    ensure_frontend || warn=1
    review_27b
    if [ "$warn" -eq 0 ]; then
        echo "[ensure] ✅ 자동 기동 대상 모두 UP"
    else
        echo "[ensure] ⚠️  일부 미기동 — gate 진행 (해당 단계 점수 영향)"
    fi
    return 0   # ★ gate 강제 중단 X
}

main "$@"
