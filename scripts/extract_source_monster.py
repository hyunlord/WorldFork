"""I-G3 source_monster 자동 추출.

962 essence의 name 정합 source_monster 추출 + canon_facts_v3.json update.

추출 logic:
- "X 정수" pattern → "X"
- name 자체 monster ('정수' 미포함) → name
- 예외 list → None
"""
from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

CANON_PATH = Path(".local/canon/canon_facts_v3.json")

# 마석 suffix — "9등급 마석", "7등급 마석", "마석" 모두 포함
_MASEOK_RE = re.compile(r"(?:^\d+등급\s*)?마석$")

# 화폐 — 숫자 단위 + 스톤
_CURRENCY_RE = re.compile(r"^[\d\s천만억]+스톤$")

# '넘버스' prefix 또는 'No.' prefix
_NUMBERS_PREFIX = ("넘버스", "No.")

# 정확 예외 set (위 regex 미포함 edge case)
_EXCEPTION_EXACT: frozenset[str] = frozenset([
    "스톤",         # 단독 스톤 (화폐 단위)
    "정수 결정",    # 일반 명사
    "던전앤스톤",   # 아이템 / 게임명 — 몬스터 X
])

# "X 정수" 추출 pattern
_ESSENCE_PATTERN = re.compile(r"^(.+?)\s*정수$")


def extract_source_monster(name: str) -> str | None:
    """essence name 정합 source_monster 추출.

    규칙:
    1. 빈 입력 → None
    2. 넘버스 / No. prefix → None (아이템류)
    3. 마석 suffix → None
    4. 화폐 pattern (숫자+스톤) → None
    5. 정확 예외 set → None
    6. "X 정수" → "X"
    7. 기타 → name 자체 (몬스터명 직접 사용)
    """
    if not name or not name.strip():
        return None

    s = name.strip()

    # 1. 넘버스 / No. prefix
    if any(s.startswith(p) for p in _NUMBERS_PREFIX):
        return None

    # 2. 마석 suffix
    if _MASEOK_RE.match(s):
        return None

    # 3. 화폐 pattern
    if _CURRENCY_RE.match(s):
        return None

    # 4. 정확 예외
    if s in _EXCEPTION_EXACT:
        return None

    # 5. "X 정수" / "X의 정수" pattern — 말미 조사 '의' 제거
    m = _ESSENCE_PATTERN.match(s)
    if m:
        monster = m.group(1).strip()
        if monster.endswith("의"):
            monster = monster[:-1].rstrip()
        return monster if monster else None

    # 6. name 자체 = monster
    return s


_TARGET_VERSION = "3.1.0"


def _bump_version(current: str) -> str:
    """version string bump — 3.0.x → 3.1.0 (한 번만)."""
    if current == _TARGET_VERSION:
        return _TARGET_VERSION
    parts = current.lstrip("v").split(".")
    if len(parts) >= 3 and parts[0] == "3" and parts[1] == "0":
        return _TARGET_VERSION
    # 이미 3.1.0 이상이면 그대로
    return current


def main() -> int:
    """canon_facts에 source_monster 적용 + version bump."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    essences = data.get("essences", [])
    print(f"=== essence total: {len(essences)} ===")

    extracted = 0
    none_count = 0
    pattern_x_essence = 0
    pattern_self = 0

    for essence in essences:
        nm = essence.get("name", "")
        source = extract_source_monster(nm)
        essence["source_monster"] = source

        if source is None:
            none_count += 1
        else:
            extracted += 1
            if nm.strip().endswith("정수"):
                pattern_x_essence += 1
            else:
                pattern_self += 1

    current_ver = data.get("version", "3.0.0")
    data["version"] = _bump_version(current_ver)
    data["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(CANON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n=== 추출 결과 ===")
    print(f"  extracted: {extracted} ({extracted / len(essences) * 100:.1f}%)")
    print(f"    - 'X 정수' pattern: {pattern_x_essence}")
    print(f"    - name 자체: {pattern_self}")
    print(f"  None (예외): {none_count} ({none_count / len(essences) * 100:.1f}%)")
    print(f"\n=== version: {current_ver} → {data['version']} ===")
    print(f"=== last_updated: {data['last_updated']} ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
