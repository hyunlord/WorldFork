"""30턴 자동 풀 플레이 + 패턴 분석 (★ Tier 2 D11+).

본인 짚은 본질:
- 1턴 검증 ≠ 30턴 검증
- 작업 빨리 끝남 = 진짜 검증 X
- '검증도 안 되고 있는걸로 보임'

진짜 데이터 측정:
  1. /game/start
  2. N회 /game/turn 진짜 호출 (★ 평균 15s × 30 = 7.5분+)
  3. /game/end + saved_path
  4. 보고서:
     - 응답 시간 분포 (min/max/avg/median/p95/total)
     - Finding #5 — '플레이어' 메타 단어
     - Finding #1 — 선택지 패턴
     - Finding #4 — 반복 (첫 80자 / 마지막 80자 / 선택지)
     - 한자 stochasticity
     - 잘림

사용:
  python tools/play_30_turns_auto.py
  python tools/play_30_turns_auto.py --turns 5
  python tools/play_30_turns_auto.py --port 8090

Exit: 0 = 완료, 1 = fail
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from typing import Any


def _request(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    timeout: float = 180.0,
) -> tuple[int, bytes]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _detect_hanja(text: str) -> list[str]:
    """한자 (U+4E00-U+9FFF)."""
    return [c for c in text if "一" <= c <= "鿿"]


def _detect_choices(text: str) -> list[str]:
    """선택지 (1./2./3. 패턴)."""
    return re.findall(r"^\s*\d+[\.\)]\s*([^\n]{1,80})", text, re.MULTILINE)


def _detect_meta_words(text: str) -> list[str]:
    """'플레이어' 메타 단어 (★ Finding #5)."""
    return re.findall(r"플레이어(?:님|씨|분)?", text)


def _is_truncated(text: str) -> bool:
    """잘림 (★ 종결어미 X)."""
    if not text or len(text) < 10:
        return True
    last = text.rstrip()[-1] if text.rstrip() else ""
    return last not in "다요까.!?\"'」』"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--turns", type=int, default=30)
    parser.add_argument(
        "--actions",
        default="1,2,3,1,2,3,1,2,3,1",
        help="행동 패턴 (★ 콤마 구분, 순환)",
    )
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    actions = args.actions.split(",")

    print(f"\n{'=' * 70}")
    print("30턴 자동 풀 플레이 + 패턴 분석")
    print(f"{'=' * 70}")
    print(f"Backend: {base}")
    print(f"Turns: {args.turns}")
    print(f"Actions: {actions}\n")

    print("[1/N] /game/start...")
    status, body = _request("POST", f"{base}/game/start", body={})
    if status != 200:
        print(f"❌ /game/start: HTTP {status}")
        return 1
    data = json.loads(body)
    sid = data["session_id"]
    print(f"  ✅ session: {sid[:12]}...")

    turn_records: list[dict[str, Any]] = []
    print(f"\n[2/N] {args.turns}턴 진짜 호출 (★ 시간 ↑)...")

    for i in range(args.turns):
        action = actions[i % len(actions)]
        t0 = time.time()
        status, body = _request(
            "POST",
            f"{base}/game/turn",
            body={"session_id": sid, "user_action": action},
            timeout=180.0,
        )
        elapsed = time.time() - t0

        if status != 200:
            print(f"  Turn {i + 1}: ❌ HTTP {status} ({elapsed:.1f}s)")
            try:
                err = json.loads(body)
                print(f"    detail: {err.get('detail', 'N/A')[:100]}")
            except Exception:
                pass
            return 1

        try:
            t_data = json.loads(body)
        except Exception as e:
            print(f"  Turn {i + 1}: ❌ JSON 파싱 실패: {e}")
            return 1

        gm_text = t_data.get("response", "") or t_data.get("gm_response", "")
        # ★ D fix: API 보장 항상 total_score 있음 — 누락 시 명시적 raise
        if "total_score" not in t_data:
            print(
                f"  Turn {i + 1}: ❌ API 응답에 total_score 누락 — "
                f"keys={list(t_data.keys())}"
            )
            return 1
        score = t_data["total_score"]

        hanja = _detect_hanja(gm_text)
        choices = _detect_choices(gm_text)
        meta = _detect_meta_words(gm_text)
        truncated = _is_truncated(gm_text)

        record = {
            "turn": i + 1,
            "action": action,
            "elapsed_s": elapsed,
            "score": score,
            "text_length": len(gm_text),
            "gm_text_first80": gm_text[:80],
            "gm_text_last80": gm_text[-80:] if len(gm_text) > 80 else "",
            "hanja_count": len(hanja),
            "hanja_chars": "".join(hanja[:10]) if hanja else "",
            "choices_count": len(choices),
            "choices": choices[:3],
            "meta_words": meta,
            "truncated": truncated,
        }
        turn_records.append(record)

        flags = ""
        if hanja:
            flags += f" 한자{len(hanja)}"
        if meta:
            flags += f" 메타{len(meta)}"
        if truncated:
            flags += " 잘림"
        if not choices:
            flags += " 선택지X"
        print(
            f"  Turn {i + 1:2d}: {elapsed:5.1f}s, score={score:5.1f}, "
            f"choices={len(choices)},{flags}"
        )

    print("\n[3/N] /game/end...")
    status, body = _request(
        "POST", f"{base}/game/end", body={"session_id": sid}
    )
    if status == 200:
        data = json.loads(body)
        saved = data.get("saved_path", "N/A")
        print(f"  ✅ saved: {saved}")
    else:
        print(f"  ⚠️ /game/end: HTTP {status}")

    print(f"\n{'=' * 70}")
    print(f"{args.turns}턴 보고서")
    print(f"{'=' * 70}\n")

    times = [r["elapsed_s"] for r in turn_records]
    print("[응답 시간]")
    print(f"  min: {min(times):.1f}s")
    print(f"  max: {max(times):.1f}s")
    print(f"  avg: {sum(times) / len(times):.1f}s")
    print(f"  median: {statistics.median(times):.1f}s")
    if len(times) >= 20:
        p95 = sorted(times)[int(len(times) * 0.95)]
        print(f"  p95: {p95:.1f}s")
    print(f"  total: {sum(times):.1f}s ({sum(times) / 60:.1f}min)")

    print("\n[점수]")
    scores = [r["score"] for r in turn_records]
    print(
        f"  min/max/avg: {min(scores):.1f} / {max(scores):.1f} / "
        f"{sum(scores) / len(scores):.1f}"
    )

    print("\n[Finding #5 — 호칭/메타 단어]")
    meta_total = sum(len(r["meta_words"]) for r in turn_records)
    meta_turns = sum(1 for r in turn_records if r["meta_words"])
    print(
        f"  '플레이어' 메타: {meta_total}회 ({meta_turns}/{len(turn_records)} 턴)"
    )
    if meta_turns:
        for r in turn_records:
            if r["meta_words"]:
                print(f"    Turn {r['turn']}: {r['meta_words']}")

    print("\n[Finding #1 — 선택지 패턴]")
    no_choices = sum(1 for r in turn_records if r["choices_count"] == 0)
    one_two = sum(1 for r in turn_records if 1 <= r["choices_count"] <= 2)
    three_plus = sum(1 for r in turn_records if r["choices_count"] >= 3)
    print(f"  선택지 0개: {no_choices}/{len(turn_records)} 턴")
    print(f"  선택지 1-2개: {one_two}/{len(turn_records)} 턴")
    print(f"  선택지 3+: {three_plus}/{len(turn_records)} 턴")

    print("\n[Finding #4 — 반복 패턴]")
    first80_counter: Counter[str] = Counter(
        r["gm_text_first80"] for r in turn_records
    )
    print(
        f"  첫 80자 중복: {sum(c - 1 for c in first80_counter.values() if c > 1)}회"
    )
    repeated_first = [(t, c) for t, c in first80_counter.items() if c > 1]
    if repeated_first:
        print("  중복 첫 80자:")
        for t, c in repeated_first[:3]:
            print(f"    {c}회: {t[:60]}...")

    all_choices: list[str] = []
    for r in turn_records:
        all_choices.extend(r["choices"])
    choice_counter: Counter[str] = Counter(all_choices)
    repeated_choices = [(t, c) for t, c in choice_counter.items() if c > 1]
    if repeated_choices:
        print("  중복 선택지:")
        for t, c in repeated_choices[:5]:
            print(f"    {c}회: {t[:60]}")

    print("\n[한자 / 9B Q3 stochasticity]")
    hanja_total = sum(r["hanja_count"] for r in turn_records)
    hanja_turns = sum(1 for r in turn_records if r["hanja_count"] > 0)
    print(
        f"  한자: {hanja_total}자 ({hanja_turns}/{len(turn_records)} 턴)"
    )
    if hanja_turns:
        for r in turn_records[:3]:
            if r["hanja_chars"]:
                print(f"    Turn {r['turn']}: {r['hanja_chars']}")

    print("\n[잘림]")
    truncated_turns = sum(1 for r in turn_records if r["truncated"])
    print(f"  잘림: {truncated_turns}/{len(turn_records)} 턴")

    print("\n[전체 턴별 첫 80자 + 마지막 80자]")
    for r in turn_records:
        print(
            f"\n[Turn {r['turn']}] action={r['action']}, "
            f"{r['elapsed_s']:.1f}s, score={r['score']:.1f}"
        )
        print(f"  ▶ {r['gm_text_first80']}")
        if r["gm_text_last80"]:
            print(f"  ◀ {r['gm_text_last80']}")
        if r["choices"]:
            for c in r["choices"]:
                print(f"    [선택] {c[:60]}")

    print(f"\n{'=' * 70}")
    print("진짜 본질 진단")
    print(f"{'=' * 70}")

    findings_active: list[str] = []
    if meta_total > 0:
        findings_active.append(
            f"#5 호칭: '플레이어' {meta_total}회 (★ fix 효과 X)"
        )
    if no_choices > 0:
        findings_active.append(
            f"#1 선택지 X: {no_choices} 턴 (★ fix 효과 X)"
        )
    if repeated_first or repeated_choices:
        findings_active.append(
            f"#4 반복: 첫80자 {len(repeated_first)}건 + 선택지 "
            f"{len(repeated_choices)}건 (★ fix 효과 X)"
        )
    if hanja_total > 0:
        findings_active.append(
            f"한자: {hanja_total}자 (★ 9B Q3 stochastic, Tier 3 영역)"
        )
    if truncated_turns > 0:
        findings_active.append(f"잘림: {truncated_turns} 턴")

    if findings_active:
        print(f"\n진짜 발견 ({len(findings_active)}건):")
        for f in findings_active:
            print(f"  - {f}")
    else:
        print(
            f"\n✅ 5턴 finding 4개 진짜 차단 입증 (★ {args.turns}턴 진짜 데이터)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
