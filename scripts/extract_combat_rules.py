"""combat mechanism rules 추출 — description → 27B → rules(list[str]).

mechanisms 96.1% rules 미입력 첫 진입 (combat 266 subset).

schema 정합: Mechanism.rules 는 list[str] (기존 10건 형식) — effect/trigger/cost를
간결 bullet 문장으로 추출. IP 보호: 산출물 rule 문자열에 mask_text(GENERIC_REPLACEMENTS).

pilot: --limit N (기본 전체). LLM 9B(8083) 부재 시 27B(8081).
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import httpx

from service.pipeline.ip_masking import mask_text

CANON_PATH = Path(".local/canon/canon_facts_v3.json")

# 27B(8081) 우선 — combat rule 추출은 추론 품질 우위
LLM_CANDIDATES: Final[list[tuple[str, str]]] = [
    ("http://localhost:8081/v1/chat/completions", "qwen3.6-27b"),
    ("http://localhost:8083/v1/chat/completions", "qwen35-9b-q3"),
]

# description 최소 길이 — 너무 짧으면 추출 근거 부족 → skip
_MIN_DESC = 20

_EXTRACTION_SYSTEM = """combat mechanism 규칙 추출 전문가.

주어진 mechanism 설명에서 전투 규칙을 간결한 bullet 문장으로 추출한다.

각 rule은 effect(효과) / trigger(발동 조건) / cost(비용) 중 하나를 담는 짧은 문장:
- effect 예: "절삭력 피해로 변환", "5분간 정화"
- trigger 예: "레이드 모드에서 발동", "클리어 후 등장"
- cost 예: "영혼력 소모", "쿨다운 존재"

규칙:
- 설명에 명시/강하게 암시된 규칙만 — 무리한 추측 금지
- 전투 규칙이 없으면 (행사/등급/개념 등) rules 빈 배열
- 고유명사는 일반 표현으로 (산출물은 IP 비식별)

JSON only. 키는 "rules" (문장 배열, 최대 5).
출력 예: {"rules": ["절삭력 피해로 변환", "레이드/사냥 모드 스왑 가능"]}
"""


def has_rules(m: dict[str, Any]) -> bool:
    r = m.get("rules")
    return isinstance(r, list) and len(r) > 0


def strip_thinking_tags(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


async def extract_rules(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    name: str,
    description: str,
) -> list[str]:
    """27B 추출 → IP 마스킹된 rule 문자열 list."""
    user = f"mechanism: {name}\n설명: {description[:600]}\n\n전투 규칙 추출. JSON only."
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _EXTRACTION_SYSTEM},
            {"role": "user", "content": user},
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
            return []
        parsed = json.loads(m.group(0))
        rules_raw = parsed.get("rules", [])
        if not isinstance(rules_raw, list):
            return []
        out: list[str] = []
        for r in rules_raw[:5]:
            if isinstance(r, str) and r.strip():
                # ★ IP 보호 — 산출물 rule에 마스킹 적용
                out.append(mask_text(r.strip()).masked)
        return out
    except Exception as e:
        print(f"  LLM error [{name}]: {e}", file=sys.stderr)
        return []


async def _pick_endpoint(client: httpx.AsyncClient) -> tuple[str, str]:
    for endpoint, model in LLM_CANDIDATES:
        base = endpoint.replace("/v1/chat/completions", "/v1/models")
        try:
            resp = await client.get(base, timeout=5.0)
            if resp.status_code == 200:
                print(f"=== LLM endpoint: {endpoint} ({model}) ===")
                return endpoint, model
        except Exception:
            continue
    raise RuntimeError("가용 LLM endpoint 없음 (8081/8083)")


_TARGET_VERSION = "3.5.0"


def _bump_version(current: str) -> str:
    parts = current.lstrip("v").split(".")
    if len(parts) == 3 and parts[0] == "3" and parts[1] == "4":
        return _TARGET_VERSION
    return current


async def _main_async(limit: int | None) -> int:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    mechs: list[dict[str, Any]] = data.get("mechanisms", [])
    combat = [m for m in mechs if m.get("category") == "combat"]
    print(f"=== combat mechanisms: {len(combat)} ===")

    targets = [
        m for m in combat
        if not has_rules(m) and len(str(m.get("description") or "")) >= _MIN_DESC
    ]
    skip_short = sum(
        1 for m in combat
        if not has_rules(m) and len(str(m.get("description") or "")) < _MIN_DESC
    )
    print(f"추출 대상 (rules 없음 + desc≥{_MIN_DESC}): {len(targets)}")
    print(f"skip (desc 짧음): {skip_short} / 기존 rules 보유: "
          f"{sum(1 for m in combat if has_rules(m))}")

    if limit is not None:
        targets = targets[:limit]
        print(f"★ pilot limit {limit} → {len(targets)}건 처리")

    extracted = 0
    rule_total = 0
    async with httpx.AsyncClient() as client:
        endpoint, model = await _pick_endpoint(client)
        print(f"\nLLM 추출 시작 (~{len(targets) * 3 / 60:.0f}분)")
        for i, m in enumerate(targets):
            rules = await extract_rules(
                client, endpoint, model,
                str(m.get("name", "")), str(m.get("description") or ""),
            )
            if rules:
                m["rules"] = rules
                extracted += 1
                rule_total += len(rules)
            if (i + 1) % 25 == 0:
                print(f"  progress: {i + 1}/{len(targets)} (추출 {extracted})")

    print("\n=== 추출 결과 ===")
    print(f"  rules 추출 성공: {extracted}/{len(targets)}")
    print(f"  총 rule 문장: {rule_total}")

    filled = sum(1 for m in combat if has_rules(m))
    print(f"  combat rules coverage: {filled}/{len(combat)} "
          f"({filled / len(combat) * 100:.1f}%)")

    # sample
    print("\n=== 추출 sample ===")
    shown = 0
    for m in combat:
        if has_rules(m) and shown < 5:
            print(f"  {m.get('name')!r}: {m['rules']}")
            shown += 1

    if limit is None:
        current = str(data.get("version", "3.4.0"))
        data["version"] = _bump_version(current)
        data["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(CANON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n=== version: {current} → {data['version']} (저장) ===")
    else:
        print("\n=== pilot 모드 — 저장 X (검증용) ===")
    return 0


def main() -> int:
    limit: int | None = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    return asyncio.run(_main_async(limit))


if __name__ == "__main__":
    sys.exit(main())
