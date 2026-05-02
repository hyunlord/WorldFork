"""Hook 이벤트 CLI 엔트리포인트 — pre-commit/pre-push 에서 호출.

사용:
  python scripts/run_hook.py post_code          # stdin에서 diff 읽기
  python scripts/run_hook.py post_verify --score 85 --threshold 95

종료 코드:
  0: abort 없음 (정상)
  1: abort 발생 (게이트 차단)
  2: 알 수 없는 이벤트
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.harness.hooks import HookEvent, HookManager


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: run_hook.py <event> [--score N] [--threshold N]", file=sys.stderr)
        sys.exit(2)

    event_name = sys.argv[1]
    try:
        event = HookEvent(event_name)
    except ValueError:
        print(f"Unknown event: {event_name!r}", file=sys.stderr)
        sys.exit(2)

    payload: dict[str, object] = {}

    # --score / --threshold 파싱
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--score" and i + 1 < len(args):
            payload["score"] = int(args[i + 1])
            i += 2
        elif args[i] == "--threshold" and i + 1 < len(args):
            payload["threshold"] = int(args[i + 1])
            i += 2
        else:
            i += 1

    # diff: stdin 또는 payload 없음
    if event in (HookEvent.POST_CODE, HookEvent.PRE_CODE):
        if not sys.stdin.isatty():
            payload["diff"] = sys.stdin.read()

    manager = HookManager()
    ctx = manager.trigger(event, payload)

    if ctx.abort:
        print(f"Hook aborted: {ctx.abort_reason}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
