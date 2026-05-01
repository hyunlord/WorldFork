"""Auto-added seeds 본인 검토 도구 (자료 AI_PLAYTESTER 5.3).

대화형 CLI:
  a: accept — evals/{category}/v2.jsonl 에 추가
  r: reject — 제거 (이유 기록)
  m: modify — W1 D5 간소화: skip 처리 (직접 yaml 편집)
  s: skip — 이번 검토에서 넘어감
  q: quit — 즉시 종료, 나머지 skip 처리

사용:
  python tools/review_auto_seeds.py               # 대화형
  python tools/review_auto_seeds.py --non-interactive  # 비대화형 (테스트)
"""

import json
import sys
from pathlib import Path
from typing import Any

# DGX Spark: ko_KR.utf8 로케일에서 Python stdin 인코딩이 정확히 인식 안 될 수 있음.
# input() UnicodeDecodeError 방지용 강제 UTF-8.
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EVALS_AUTO_ADDED = Path(__file__).resolve().parents[1] / "evals" / "auto_added"
EVALS_BASE = Path(__file__).resolve().parents[1] / "evals"


# ---------------------------------------------------------------------------
# 로딩
# ---------------------------------------------------------------------------

def load_auto_seeds() -> list[dict[str, Any]]:
    """auto_added/*.jsonl 에서 시드 전부 로드."""
    seeds: list[dict[str, Any]] = []
    if not EVALS_AUTO_ADDED.exists():
        return seeds

    for jsonl_path in sorted(EVALS_AUTO_ADDED.glob("*.jsonl")):
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                seed: dict[str, Any] = json.loads(line)
                seed["_source_file"] = str(jsonl_path.name)
                seeds.append(seed)
            except json.JSONDecodeError:
                pass
    return seeds


# ---------------------------------------------------------------------------
# 표시
# ---------------------------------------------------------------------------

def _truncate(text: str, n: int = 200) -> str:
    return text[:n] + ("..." if len(text) > n else "")


def display_seed(seed: dict[str, Any], idx: int, total: int) -> None:
    """시드 한 눈에 보기."""
    meta: dict[str, Any] = seed.get("metadata", {})
    prompt: dict[str, Any] = seed.get("prompt", {})

    print()
    print("=" * 70)
    print(f"[{idx + 1}/{total}] {seed.get('id', 'unknown')}")
    print("=" * 70)
    print(f"  출처 파일   : {seed.get('_source_file', '')}")
    print(f"  Category   : {seed.get('category', '?')}")
    print(f"  Severity   : {meta.get('severity', '?')}")
    print(f"  Persona    : {meta.get('persona', '?')}")
    print(f"  Work       : {meta.get('session_work_name', '?')}")
    print(f"  발견일     : {str(meta.get('discovered_at', '?'))[:10]}")
    print()
    print("  [발견 내용]")
    desc = str(meta.get("original_description", ""))
    print(f"  {_truncate(desc, 200)}")
    print()
    print("  [게임 인트로 발췌]")
    excerpt = str(meta.get("intro_excerpt", ""))
    print(f"  {_truncate(excerpt, 150)}")
    print()
    print("  [Eval prompt / user]")
    print(f"  {_truncate(str(prompt.get('user', '')), 200)}")
    print()
    print("  [Expected behavior]")
    print(f"  {seed.get('expected_behavior', {})}")


# ---------------------------------------------------------------------------
# 검토 루프
# ---------------------------------------------------------------------------

def review_loop(
    seeds: list[dict[str, Any]],
    interactive: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """대화형 (또는 비대화형) 검토 루프.

    Returns:
        {"accepted": [...], "rejected": [...], "skipped": [...]}
    """
    result: dict[str, list[dict[str, Any]]] = {
        "accepted": [],
        "rejected": [],
        "skipped": [],
    }

    if not interactive:
        result["skipped"] = list(seeds)
        return result

    for idx, seed in enumerate(seeds):
        display_seed(seed, idx, len(seeds))

        while True:
            try:
                raw = input("\n  [a]ccept / [r]eject / [m]odify / [s]kip / [q]uit: ")
            except EOFError:
                raw = "q"

            action = raw.strip().lower()

            if action == "a":
                result["accepted"].append(seed)
                print("  → accepted ✅")
                break

            elif action == "r":
                try:
                    reason = input("  Reject reason (Enter 생략 가능): ").strip()
                except EOFError:
                    reason = ""
                rejected_seed = dict(seed)
                rejected_seed["_reject_reason"] = reason
                result["rejected"].append(rejected_seed)
                print("  → rejected ❌")
                break

            elif action == "m":
                print("  → (modify: W1 D5 간소화로 skip 처리. 직접 yaml 편집 후 재실행)")
                result["skipped"].append(seed)
                break

            elif action == "s":
                result["skipped"].append(seed)
                print("  → skipped ⏭")
                break

            elif action == "q":
                print("  → quit. 나머지 skip 처리.")
                result["skipped"].extend(seeds[idx:])
                return result

            else:
                print("  ⚠ 잘못된 입력. a / r / m / s / q 중 선택.")

    return result


# ---------------------------------------------------------------------------
# v2 promote
# ---------------------------------------------------------------------------

def promote_to_v2(
    accepted: list[dict[str, Any]],
) -> dict[str, Path]:
    """승인된 시드를 evals/{category}/v2.jsonl 에 append.

    기존 v2.jsonl 이 있으면 append. 없으면 새로 생성.
    _source_file / _reject_reason 같은 내부 키는 제거.

    Returns:
        {category: saved_path}
    """
    by_category: dict[str, list[dict[str, Any]]] = {}
    for seed in accepted:
        cat = str(seed.get("category", "general"))
        by_category.setdefault(cat, []).append(seed)

    saved: dict[str, Path] = {}
    for cat, seeds in by_category.items():
        cat_dir = EVALS_BASE / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        v2_path = cat_dir / "v2.jsonl"

        with v2_path.open("a", encoding="utf-8") as f:
            for seed in seeds:
                clean = {k: v for k, v in seed.items() if not k.startswith("_")}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")

        saved[cat] = v2_path

    return saved


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

def main(interactive: bool = True) -> None:
    seeds = load_auto_seeds()

    if not seeds:
        print("auto-added seeds 없음 (evals/auto_added/*.jsonl 확인).")
        return

    print("\n★ Auto-seed 검토 도구 (자료 AI_PLAYTESTER 5.3)")
    print(f"  총 {len(seeds)}개 시드 발견.")

    if interactive:
        try:
            cont = input("\n검토를 시작하시겠습니까? [y/N]: ").strip().lower()
        except EOFError:
            cont = "n"
        if cont != "y":
            print("취소됨.")
            return

    result = review_loop(seeds, interactive=interactive)

    # 요약
    print()
    print("=" * 70)
    print("검토 완료")
    print("=" * 70)
    print(f"  Accepted : {len(result['accepted'])}")
    print(f"  Rejected : {len(result['rejected'])}")
    print(f"  Skipped  : {len(result['skipped'])}")

    if result["accepted"]:
        saved = promote_to_v2(result["accepted"])
        print()
        print("  [Promoted → v2]")
        for cat, path in sorted(saved.items()):
            n = sum(1 for s in result["accepted"] if s.get("category") == cat)
            print(f"  {cat}: {n}개 → {path.relative_to(EVALS_BASE.parent)}")
    else:
        print()
        print("  (승인된 시드 없음 — v2.jsonl 생성 안 함)")


if __name__ == "__main__":
    main(interactive="--non-interactive" not in sys.argv)
