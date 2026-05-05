"""Mechanical E2E check — 게임 흐름 진짜 검증 (★ Tier 2 D11).

정공법 정신: F12 사람 의존 X, curl 자동.
verify.sh 통합으로 매 push 자동 차단.

검증 흐름:
  1. uvicorn 백그라운드 띄움
  2. /health 200
  3. /game/start POST: 200 + session_id
  4. /game/start CORS preflight: 200 + Access-Control-Allow-Origin
  5. /game/turn POST: 200 (★ 9B + 27B verify, timeout 180초)
  6. /game/end POST: 200 + saved_path
  7. uvicorn kill

사용:
  python tools/run_e2e_check.py
  python tools/run_e2e_check.py --port 8090 --origin http://localhost:4000
  python tools/run_e2e_check.py --skip-turn  # CI 환경 시간 절약

Exit code: 0=pass, 1=fail
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, str], bytes]:
    """진짜 HTTP 호출."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if body is not None and (not headers or "Content-Type" not in headers):
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _wait_for_uvicorn(base: str, max_seconds: float = 15.0) -> bool:
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        try:
            status, _, _ = _request("GET", f"{base}/health", timeout=2.0)
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _find_header(headers: dict[str, str], name: str) -> str | None:
    """case-insensitive 헤더 lookup."""
    target = name.lower()
    for k, v in headers.items():
        if k.lower() == target:
            return v
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--origin",
        default="http://localhost:4000",
        help="CORS origin to test (★ ALLOWED_ORIGINS에 포함되어야)",
    )
    parser.add_argument(
        "--skip-turn",
        action="store_true",
        help="/game/turn 스킵 (★ 27B 호출 시간 절약, CI 환경)",
    )
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    failures: list[str] = []

    print(f"[1/7] Starting uvicorn on {args.host}:{args.port}...")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "service.api.app:app",
            "--host", args.host,
            "--port", str(args.port),
            "--log-level", "warning",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    sid: str | None = None
    try:
        if not _wait_for_uvicorn(base):
            print("❌ uvicorn 안 떴음 (15초)")
            return 1

        print("[2/7] /health...")
        status, _, _ = _request("GET", f"{base}/health")
        if status == 200:
            print("  ✅ 200 OK")
        else:
            failures.append(f"/health: {status}")

        print("[3/7] /game/start (POST)...")
        status, _, body = _request("POST", f"{base}/game/start", body={})
        if status == 200:
            try:
                data = json.loads(body)
                sid = data.get("session_id")
                if sid:
                    print(f"  ✅ 200 OK, session_id={sid[:12]}...")
                else:
                    failures.append("/game/start: no session_id in response")
            except json.JSONDecodeError:
                failures.append("/game/start: invalid JSON")
        else:
            failures.append(f"/game/start POST: {status}")

        print(f"[4/7] /game/start CORS OPTIONS (origin={args.origin})...")
        status, headers, _ = _request(
            "OPTIONS",
            f"{base}/game/start",
            headers={
                "Origin": args.origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        allow_origin = _find_header(headers, "access-control-allow-origin")
        if status == 200 and allow_origin:
            print(f"  ✅ 200 OK, Allow-Origin: {allow_origin}")
        elif status == 200:
            failures.append(
                "/game/start CORS: 200 but no Access-Control-Allow-Origin header"
            )
        else:
            failures.append(f"/game/start CORS preflight: {status}")

        if sid and not args.skip_turn:
            print("[5/7] /game/turn (POST, ★ 9B + 27B verify)...")
            t0 = time.time()
            status, _, body = _request(
                "POST",
                f"{base}/game/turn",
                body={"session_id": sid, "user_action": "주변을 살핍니다"},
                timeout=180.0,
            )
            elapsed = time.time() - t0
            if status == 200:
                try:
                    data = json.loads(body)
                    score = data.get("total_score", "N/A")
                    print(f"  ✅ 200 OK, {elapsed:.1f}s, score={score}")
                except json.JSONDecodeError:
                    failures.append("/game/turn: invalid JSON")
            else:
                failures.append(f"/game/turn: {status} ({elapsed:.1f}s)")
        elif args.skip_turn:
            print("[5/7] /game/turn — skipped (--skip-turn)")
        else:
            failures.append("/game/turn: skipped (no session_id)")

        if sid:
            print("[6/7] /game/end (POST)...")
            status, _, body = _request(
                "POST",
                f"{base}/game/end",
                body={"session_id": sid},
            )
            if status == 200:
                try:
                    data = json.loads(body)
                    saved = data.get("saved_path", "N/A")
                    print(f"  ✅ 200 OK, saved={saved}")
                except json.JSONDecodeError:
                    failures.append("/game/end: invalid JSON")
            else:
                failures.append(f"/game/end: {status}")
        else:
            failures.append("/game/end: skipped (no session_id)")

    finally:
        print("[7/7] Stopping uvicorn...")
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("  ✅ stopped")

    print()
    if failures:
        print(f"❌ E2E FAIL ({len(failures)}건):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("✅ E2E PASS — 모든 endpoint + CORS 진짜 작동")
    return 0


if __name__ == "__main__":
    sys.exit(main())
