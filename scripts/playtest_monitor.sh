#!/bin/bash
# 플레이테스트 자동 점검 보조 — 도그푸딩 플레이 중 실시간 점검 스냅샷.
#
# 사용자가 플레이하는 동안 별도 터미널에서 돌린다(또는 1회 스냅샷):
#   bash scripts/playtest_monitor.sh          # 1회 스냅샷
#   bash scripts/playtest_monitor.sh --watch  # 15초마다 반복(Ctrl-C 종료)
#
# 점검 항목:
#   1) 4종 헬스 (8085/8083/8090/4000)
#   2) backend 로그 최근 ERROR/Exception/Traceback (실시간 — 막힘 원인)
#   3) GM 응답 시간 측정 (12B 8085 — 느린 곳 감지)
set -u

BACKEND_LOG="/tmp/uvicorn_backend.log"
FE_LOG="/tmp/frontend_playtest.log"

snapshot() {
    echo "──────────── 점검 스냅샷 ────────────"
    # 1) 헬스
    printf "헬스:"
    for port in 8085 8083 8090; do
        if curl -fsS --max-time 3 "http://localhost:$port/health" >/dev/null 2>&1; then
            printf " :%s✅" "$port"
        else
            printf " :%s❌" "$port"
        fi
    done
    if curl -fsS --max-time 3 "http://localhost:4000/" >/dev/null 2>&1; then
        printf " :4000✅\n"
    else
        printf " :4000❌\n"
    fi

    # 2) backend 로그 최근 에러 (막힘/예외 — 실시간)
    if [ -f "$BACKEND_LOG" ]; then
        local errs
        errs="$(grep -iE "error|exception|traceback|500 internal" "$BACKEND_LOG" 2>/dev/null | tail -3)"
        if [ -n "$errs" ]; then
            echo "⚠️ backend 최근 에러(끝 3):"
            echo "$errs" | sed 's/^/   /'
        else
            echo "backend 로그: 에러 없음 ✅"
        fi
    fi

    # 3) GM 응답 시간 (12B 8085 — 느린 곳)
    local t0 t1 dt
    t0=$(date +%s.%N)
    if curl -fsS --max-time 60 "http://localhost:8085/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d '{"model":"gemma","messages":[{"role":"user","content":"한 문장으로 동굴을 묘사하라."}],"max_tokens":60,"stream":false}' \
        >/dev/null 2>&1; then
        t1=$(date +%s.%N)
        dt=$(echo "$t1 - $t0" | bc 2>/dev/null || echo "?")
        echo "GM(12B) 응답: ${dt}s (60토큰) — 6~8s 정상, 그 이상이면 경합 의심"
    else
        echo "GM(12B) 응답: ⚠️ 실패/타임아웃"
    fi
    echo ""
}

if [ "${1:-}" = "--watch" ]; then
    echo "=== 플레이테스트 모니터 (15초 간격, Ctrl-C 종료) ==="
    while true; do
        snapshot
        sleep 15
    done
else
    echo "=== 플레이테스트 모니터 (1회 스냅샷) ==="
    snapshot
fi
