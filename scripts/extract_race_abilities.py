"""races ability_tiers 자동 추출.

442 race를 description + 기존 abilities 이름 정합 LLM tiered 추출.

source 우선순위:
1. 기존 abilities list (ability 이름) — 가장 풍부
2. description (>=15자)
3. 둘 다 결합

logic:
1. ability_tiers 빈 race iterate
2. source 결합 → LLM 추출 (text + parsed)
3. canon_facts in-place update + version bump

★ 9B(8083) 부재 시 27B(8081) 사용 — 동일 추출 작업, 상위 모델.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import httpx

CANON_PATH = Path(".local/canon/canon_facts_v3.json")

# 9B(8083) 우선, 부재 시 27B(8081) fallback
LLM_CANDIDATES: Final[list[tuple[str, str]]] = [
    ("http://localhost:8083/v1/chat/completions", "qwen35-9b-q3"),
    ("http://localhost:8081/v1/chat/completions", "qwen3.6-27b"),
]

_VALID_TIERS: Final = frozenset(["상", "중", "하"])

_EXTRACTION_SYSTEM = """한국어 RPG 종족 ability 추출 전문가.

주어진 종족 설명에서 ability를 추출한다.

format: "특성명(등급)" — 등급은 상/중/하 중 1개.
예: "강인함(상), 재생(중), 추위 저항(하)"

설명에 ability가 없으면 abilities_text는 빈 string.

JSON only (추가 설명 금지). 키는 반드시 "abilities_text" 와 "parsed".
parsed의 각 원소는 반드시 "name" 과 "tier" 키 (★ "level" 금지).

출력 예시:
{"abilities_text": "강인함(상), 재생(중)",
 "parsed": [{"name": "강인함", "tier": "상"}, {"name": "재생", "tier": "중"}]}

규칙:
- 설명에 명시되거나 강하게 암시된 ability만 — 무리한 추측 금지
- 등급 명시되지 않으면 tier는 "중"
- ability가 없으면 abilities_text 빈 string + parsed 빈 list
- 서술형 문장은 핵심 특성명으로 압축 (예: "정보를 쉽게 얻음" → "정보 수집(중)")
"""


def has_existing_tiers(race: dict[str, Any]) -> bool:
    """ability_tiers 실질 입력 여부."""
    at = race.get("ability_tiers")
    if isinstance(at, dict):
        return len(str(at.get("text", ""))) >= 5
    return False


def build_source(race: dict[str, Any]) -> str:
    """LLM source 결합 — description + 기존 abilities 이름."""
    parts: list[str] = []
    desc = race.get("description")
    if isinstance(desc, str) and len(desc.strip()) >= 1:
        parts.append(f"설명: {desc.strip()[:800]}")
    abilities = race.get("abilities")
    if isinstance(abilities, list) and abilities:
        names = ", ".join(str(a) for a in abilities[:15])
        parts.append(f"알려진 특성: {names}")
    return "\n".join(parts)


def strip_thinking_tags(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


async def extract_via_llm(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    race_name: str,
    source_text: str,
) -> dict[str, Any]:
    """LLM 정합 ability tiered 추출.

    return: {"text": str, "parsed": list[dict]}
    """
    user_prompt = f"종족: {race_name}\n{source_text}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _EXTRACTION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.1,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        resp = await client.post(endpoint, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        raw = msg.get("content") or msg.get("reasoning_content") or ""
        content = strip_thinking_tags(str(raw))

        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not m:
            return {"text": "", "parsed": []}
        try:
            result = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"text": "", "parsed": []}

        text = str(result.get("abilities_text", "")).strip()
        raw_parsed = result.get("parsed", [])
        valid_parsed: list[dict[str, str]] = []
        if isinstance(raw_parsed, list):
            for p in raw_parsed:
                if not isinstance(p, dict):
                    continue
                name = p.get("name")
                tier = p.get("tier")
                if (
                    isinstance(name, str) and name.strip()
                    and isinstance(tier, str) and tier in _VALID_TIERS
                ):
                    valid_parsed.append({"name": name.strip(), "tier": tier})
        return {"text": text, "parsed": valid_parsed}

    except Exception as e:
        print(f"  LLM error [{race_name}]: {e}", file=sys.stderr)
        return {"text": "", "parsed": []}


async def _pick_endpoint(client: httpx.AsyncClient) -> tuple[str, str]:
    """가용 LLM endpoint 선택 (9B 우선, 27B fallback)."""
    for endpoint, model in LLM_CANDIDATES:
        base = endpoint.replace("/v1/chat/completions", "/v1/models")
        try:
            resp = await client.get(base, timeout=5.0)
            if resp.status_code == 200:
                print(f"=== LLM endpoint: {endpoint} ({model}) ===")
                return endpoint, model
        except Exception:
            continue
    raise RuntimeError("가용 LLM endpoint 없음 (8083/8081 모두 down)")


async def _main_async() -> int:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    races: list[dict[str, Any]] = data.get("races", [])
    print(f"=== total race: {len(races)} ===")

    targets: list[dict[str, Any]] = []
    no_source = 0
    for r in races:
        if has_existing_tiers(r):
            continue
        if build_source(r):
            targets.append(r)
        else:
            no_source += 1

    print(f"=== 추출 대상 (source 보유): {len(targets)} ===")
    print(f"=== source X (skip): {no_source} ===")

    extracted = 0
    failed = 0
    total = len(targets)

    async with httpx.AsyncClient() as client:
        endpoint, model = await _pick_endpoint(client)
        print(f"\nLLM 호출 시작 (~{total * 3 / 60:.0f}분 예상)")
        for i, race in enumerate(targets):
            name = str(race.get("name", ""))
            source = build_source(race)
            result = await extract_via_llm(client, endpoint, model, name, source)
            if result["text"]:
                race["ability_tiers"] = result
                extracted += 1
            else:
                failed += 1
            if (i + 1) % 50 == 0:
                print(f"  progress: {i + 1}/{total} (성공 {extracted}, 실패 {failed})")

    print("\n=== 추출 결과 ===")
    print(f"  성공: {extracted}")
    print(f"  실패 (source 있음, ability 추출 X): {failed}")
    print(f"  skip (source X): {no_source}")

    filled = sum(1 for r in races if has_existing_tiers(r))
    print(f"\n=== ability_tiers coverage: {filled}/{len(races)} "
          f"({filled / len(races) * 100:.1f}%) ===")

    tier_counts: Counter[str] = Counter()
    for r in races:
        at = r.get("ability_tiers")
        if isinstance(at, dict):
            for p in at.get("parsed", []):
                if isinstance(p, dict):
                    t = p.get("tier")
                    if isinstance(t, str):
                        tier_counts[t] += 1
    if tier_counts:
        print("=== parsed tier 분포 ===")
        for t in ["상", "중", "하"]:
            print(f"  {t}: {tier_counts.get(t, 0)}")

    current_ver = str(data.get("version", "3.3.0"))
    parts = current_ver.split(".")
    if len(parts) == 3 and parts[1] == "3":
        data["version"] = f"{parts[0]}.4.0"
    data["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(CANON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n=== version: {current_ver} → {data['version']} ===")
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    sys.exit(main())
