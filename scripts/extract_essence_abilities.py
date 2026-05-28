"""I-G1 essence abilities 자동 추출.

704 빈 essence를 ep_number / quote / wiki 정합 27B LLM 추출.

logic:
1. 빈 essence iterate
2. fallback chain:
   - ep_number → 본문 ep file 27B 추출
   - citations.quote 27B 추출
   - wiki citation 27B 추출 (★ quote 없는 wiki도 포함)
3. text + parsed 갱신
4. canon_facts in-place update + version bump
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
EP_DIR = Path(".local/canon/audit_episodes")

LLM_ENDPOINT = "http://localhost:8081/v1/chat/completions"
LLM_MODEL = "qwen3.6-27b"

_VALID_TIERS: Final = frozenset(["상", "중", "하"])

_EXTRACTION_SYSTEM = """한국어 RPG essence ability 추출 전문가.

주어진 본문에서 essence의 ability를 추출한다.

format: "특성명(등급)" — 등급은 상/중/하 중 1개.
예: "유연성(하), 후각(하), 독 내성(하)"

본문에 명시되지 않으면 abilities_text는 빈 string.

JSON only (추가 설명 금지). 키는 반드시 "abilities_text" 와 "parsed".
parsed의 각 원소는 반드시 "name" 과 "tier" 키 (★ "level" 사용 금지).

출력 예시:
{"abilities_text": "유연성(하), 후각(하)",
 "parsed": [{"name": "유연성", "tier": "하"}, {"name": "후각", "tier": "하"}]}

규칙:
- 본문에 명시된 ability만 추출 — 추측 금지
- 등급 명시되지 않으면 tier는 "중"
- ability가 없으면 abilities_text 빈 string + parsed 빈 list
"""


def is_empty_abilities(essence: dict[str, Any]) -> bool:
    """abilities 실질 빈 정합."""
    abilities = essence.get("abilities")
    if not abilities:
        return True
    if isinstance(abilities, dict):
        text = abilities.get("text", "")
        if not text or len(str(text)) < 10:
            return True
    if isinstance(abilities, str):
        return len(abilities) < 10
    return False


def get_ep_numbers(essence: dict[str, Any]) -> list[int]:
    """citations 본 ep_number list 추출."""
    eps: list[int] = []
    for c in essence.get("citations", []):
        if isinstance(c, dict):
            ep = c.get("ep_number")
            if isinstance(ep, int):
                eps.append(ep)
    return eps


def get_quotes(essence: dict[str, Any]) -> list[str]:
    """citations 본 quote list (★ 30자 이상)."""
    qs: list[str] = []
    for c in essence.get("citations", []):
        if isinstance(c, dict):
            q = c.get("quote")
            if isinstance(q, str) and len(q) >= 30:
                qs.append(q)
    return qs


def get_wiki_pages(essence: dict[str, Any]) -> list[str]:
    """citations 본 wiki_page list."""
    ws: list[str] = []
    for c in essence.get("citations", []):
        if isinstance(c, dict):
            w = c.get("wiki_page")
            if isinstance(w, str) and w:
                ws.append(w)
    return ws


def load_ep_text(ep_number: int) -> str | None:
    """ep file 본문 load."""
    ep_path = EP_DIR / f"ep_{ep_number:04d}.md"
    if not ep_path.exists():
        return None
    try:
        return ep_path.read_text(encoding="utf-8")
    except OSError:
        return None


def strip_thinking_tags(text: str) -> str:
    """27B thinking tags 제거 (Qwen3 정합)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _truncate_ep_text(text: str, essence_name: str, max_chars: int = 8000) -> str:
    """ep text를 essence name 근처로 truncate (context window 정합)."""
    if len(text) <= max_chars:
        return text
    idx = text.find(essence_name)
    if idx < 0:
        idx = text.find(essence_name.replace(" ", ""))
    if idx < 0:
        return text[:max_chars]
    start = max(0, idx - 2500)
    end = min(len(text), idx + 5500)
    return text[start:end]


async def extract_via_llm(
    client: httpx.AsyncClient,
    essence_name: str,
    source_text: str,
    grade: int | None,
) -> dict[str, Any]:
    """27B 정합 ability 추출.

    return: {"text": str, "parsed": list[dict]}
    """
    grade_str = f" (grade {grade})" if grade else ""
    user_prompt = (
        f"essence name: {essence_name}{grade_str}\n"
        f"본문 텍스트:\n{source_text}"
    )

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": _EXTRACTION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.1,
        # ★ Qwen3 reasoning 모드 비활성화 — content에 직접 답변
        "chat_template_kwargs": {"enable_thinking": False},
    }

    try:
        resp = await client.post(LLM_ENDPOINT, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        # content null 시 reasoning_content fallback
        raw = msg.get("content") or msg.get("reasoning_content") or ""
        content = strip_thinking_tags(str(raw))

        # JSON object 위치 추출 (앞뒤 noise 정합)
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
        print(f"  LLM error [{essence_name}]: {e}", file=sys.stderr)
        return {"text": "", "parsed": []}


async def extract_for_essence(
    client: httpx.AsyncClient,
    essence: dict[str, Any],
) -> dict[str, Any] | None:
    """essence 1개 ability 추출 — fallback chain."""
    name = str(essence.get("name", ""))
    grade_val = essence.get("grade")
    grade = grade_val if isinstance(grade_val, int) else None

    # 1. ep_number 본문 ep
    for ep_num in get_ep_numbers(essence)[:3]:
        ep_text = load_ep_text(ep_num)
        if not ep_text:
            continue
        if name in ep_text or name.replace(" ", "") in ep_text.replace(" ", ""):
            truncated = _truncate_ep_text(ep_text, name)
            result = await extract_via_llm(client, name, truncated, grade)
            if result["text"]:
                return result

    # 2. citation quote fallback
    quotes = get_quotes(essence)
    if quotes:
        combined = "\n\n".join(quotes[:5])
        result = await extract_via_llm(client, name, combined, grade)
        if result["text"]:
            return result

    # 3. wiki page hint fallback (★ wiki 본문 X — name만 hint)
    wikis = get_wiki_pages(essence)
    if wikis:
        wiki_hint = (
            f"나무위키 항목: {wikis[0]}\n"
            f"이 essence는 게임 속 바바리안으로 살아남기 본문 정합 정수."
        )
        result = await extract_via_llm(client, name, wiki_hint, grade)
        if result["text"]:
            return result

    return None


async def _main_async() -> int:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    essences: list[dict[str, Any]] = data.get("essences", [])
    print(f"=== total essence: {len(essences)} ===")

    empty_essences = [e for e in essences if is_empty_abilities(e)]
    print(f"=== 빈 abilities: {len(empty_essences)} ===")

    # 추출 대상 분류
    has_source: list[dict[str, Any]] = []
    no_source = 0
    for e in empty_essences:
        if get_ep_numbers(e) or get_quotes(e) or get_wiki_pages(e):
            has_source.append(e)
        else:
            no_source += 1

    print(f"  추출 가능 (source 있음): {len(has_source)}")
    print(f"  추출 X (source 없음):   {no_source}")
    print(f"\nLLM 호출 시작 (~{len(has_source) * 3 / 60:.0f}분 예상)")

    extracted = 0
    failed = 0
    total = len(has_source)

    async with httpx.AsyncClient() as client:
        for i, essence in enumerate(has_source):
            result = await extract_for_essence(client, essence)
            if result and result["text"]:
                essence["abilities"] = result
                extracted += 1
            else:
                failed += 1
            if (i + 1) % 50 == 0:
                print(
                    f"  progress: {i + 1}/{total} "
                    f"(성공 {extracted}, 실패 {failed})"
                )

    print("\n=== 추출 결과 ===")
    print(f"  성공: {extracted}")
    print(f"  실패 (source 있음, LLM 추출 X): {failed}")
    print(f"  skip (source X): {no_source}")

    # 최종 coverage
    final_filled = sum(
        1 for e in essences
        if isinstance(e.get("abilities"), dict)
        and len(str(e["abilities"].get("text", ""))) >= 10
    )
    print("\n=== 최종 coverage ===")
    print(f"  filled: {final_filled} / {len(essences)} "
          f"({final_filled / len(essences) * 100:.1f}%)")

    # tier 분포
    tier_counts: Counter[str] = Counter()
    for e in essences:
        a = e.get("abilities")
        if isinstance(a, dict):
            for p in a.get("parsed", []):
                if isinstance(p, dict):
                    t = p.get("tier", "")
                    if isinstance(t, str):
                        tier_counts[t] += 1
    if tier_counts:
        print("\n=== parsed tier 분포 ===")
        for t in ["상", "중", "하"]:
            print(f"  {t}: {tier_counts.get(t, 0)}")

    # version bump
    current_ver = str(data.get("version", "3.2.0"))
    parts = current_ver.split(".")
    if len(parts) == 3 and parts[1] == "2":
        data["version"] = f"{parts[0]}.3.0"
    data["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(CANON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n=== version: {current_ver} → {data['version']} ===")
    print(f"=== last_updated: {data['last_updated']} ===")
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    sys.exit(main())
