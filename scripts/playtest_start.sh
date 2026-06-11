#!/bin/bash
# 플레이테스트 기동 — Tailscale IP 주입 재기동 (친구 접근 + 도그푸딩 편의).
#
# 매번 수동 env 지정을 회피한다. ensure_services 로 모델/backend 를 올리되,
# frontend 는 별도로 처리한다 — 친구 브라우저가 backend(8090)를 찾으려면
# NEXT_PUBLIC_API_URL 이 Tailscale IP 여야 하고, 외부 접근을 위해 0.0.0.0 바인딩이
# 필요한데 ensure_services 의 frontend 기동은 localhost-only + env 없음이기 때문.
#
# 사용:
#   bash scripts/playtest_start.sh           # Tailscale IP 기본값
#   PLAYTEST_IP=192.168.0.18 bash scripts/playtest_start.sh   # IP 재정의
#   PLAYTEST_FE_LOCAL=1 bash scripts/playtest_start.sh        # 로컬 자가용(127.0.0.1)
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAILSCALE_IP="${PLAYTEST_IP:-100.70.109.50}"   # DGX Tailscale IP (본인 망)
PORT_FE=4000
PORT_BACKEND=8090

echo "=== 플레이테스트 기동 (Tailscale ${TAILSCALE_IP}) ==="

# 1) 모델(8085/8083) + backend(8090) — ensure_services (frontend 는 아래서 별도)
ENSURE_FE=0 bash "$REPO_ROOT/scripts/ensure_services.sh"

# 2) frontend 재기동 — 기존 4000 점유 PID 만 narrow kill (self-match 회피, 포트-PID 기반)
FE_PIDS="$(fuser "${PORT_FE}/tcp" 2>/dev/null || true)"
if [ -n "$FE_PIDS" ]; then
    echo "[playtest] frontend(4000) 기존 PID${FE_PIDS} → kill (env 재주입 위해)"
    # shellcheck disable=SC2086
    kill $FE_PIDS 2>/dev/null || true
    sleep 2
fi

# 3) frontend 기동 — Tailscale env + 0.0.0.0 (친구 외부 접근). 로컬 자가용은 127.0.0.1.
if [ "${PLAYTEST_FE_LOCAL:-0}" = "1" ]; then
    FE_API="http://localhost:${PORT_BACKEND}"
    FE_HOST="127.0.0.1"
else
    FE_API="http://${TAILSCALE_IP}:${PORT_BACKEND}"   # 친구 브라우저 → Tailscale backend
    FE_HOST="0.0.0.0"
fi
echo "[playtest] frontend 기동 — API=${FE_API} HOST=${FE_HOST}"
(
    cd "$REPO_ROOT/frontend" || exit 1
    NEXT_PUBLIC_API_URL="$FE_API" \
        nohup npm run dev -- -p "$PORT_FE" -H "$FE_HOST" \
        > /tmp/frontend_playtest.log 2>&1 &
    disown
)

# 4) 헬스체크 — 모델/backend/frontend (frontend 는 cold compile 대기)
echo "[playtest] 헬스체크..."
for port in 8085 8083 8090; do
    if curl -fsS --max-time 3 "http://localhost:$port/health" >/dev/null 2>&1; then
        echo "  :$port ✅ OK"
    else
        echo "  :$port ⚠️  확인 필요"
    fi
done
# frontend 는 next dev cold compile 으로 첫 응답이 느림 — 최대 120s 대기
for _ in $(seq 1 60); do
    if curl -fsS --max-time 3 "http://localhost:${PORT_FE}/" >/dev/null 2>&1; then
        echo "  :${PORT_FE} ✅ OK (frontend)"
        break
    fi
    sleep 2
done
if ! curl -fsS --max-time 3 "http://localhost:${PORT_FE}/" >/dev/null 2>&1; then
    echo "  :${PORT_FE} ⚠️  frontend 미응답 — /tmp/frontend_playtest.log 확인"
fi

echo ""
echo "★ 친구 접근:  http://${TAILSCALE_IP}:${PORT_FE}   (Tailscale 초대 수락 후)"
echo "★ 본인 접근:  http://localhost:${PORT_FE}"
echo "★ 모델 보호:  8083/8085 = 127.0.0.1 (친구 직접 접근 불가)"
