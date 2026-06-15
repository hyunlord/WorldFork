"""mechanism rules 추출 — description → 27B → rules(list[str]). category 공통(DRY).

extract_combat_rules generalize (★ d2d6706): category 파라미터로 combat/magic/skill 공통.
Mechanism.rules = list[str] (effect/trigger/cost 간결 bullet). magic은 element도 bullet 포함
(Mechanism schema에 element 필드 없음 — schema 변경 회피).
IP 보호: 산출물 rule에 mask_text. LLM 27B(8081) 우선, 9B(8083) fallback.

사용: python scripts/extract_mechanism_rules.py --category magic [--limit 50]
  --limit N: pilot (저장 X) / 미지정: 전체 (저장 + version minor bump)
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

from service.content.worldfork import WORLDFORK_PACK

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def mask_ip(text: str) -> str:
    """IP 고유명사만 변환 (라프도니아→라스카니아 등).

    ★ mask_text 대신 사용 — mask_text는 '넘버스/바바리안' 같은 게임 용어를
      fallback 이름으로 오변환. 여기선 변환 매핑(고유명사)만 적용. 매핑은 콘텐츠팩 소유(A1.2b).
    """
    for kw, repl in WORLDFORK_PACK.ip_replacements.items():
        text = text.replace(kw, repl)
    return text

LLM_CANDIDATES: Final[list[tuple[str, str]]] = [
    ("http://localhost:8081/v1/chat/completions", "qwen3.6-27b"),
    ("http://localhost:8083/v1/chat/completions", "qwen35-9b-q3"),
]

_MIN_DESC = 20

# category별 추출 prompt — rules: list[str] (effect/trigger/cost bullet)
_COMBAT_SYSTEM = """combat mechanism 규칙 추출 전문가.

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

_MAGIC_SYSTEM = """마법(magic) mechanism 규칙 추출 전문가.

주어진 마법 설명에서 규칙을 간결한 bullet 문장으로 추출한다.

각 rule은 effect/trigger/cost/element 중 하나를 담는 짧은 문장:
- effect 예: "20m 반경 폭발", "광역 회복"
- trigger 예: "영창 후 시전", "매개체 필요"
- cost 예: "영혼력 대량 소모", "합동 시전 필요"
- element 예: "불 속성", "냉기 속성" (속성 마법인 경우)

규칙:
- 설명에 명시/강하게 암시된 규칙만 — 무리한 추측 금지
- 마법 규칙이 없으면 (재료/등급/개념 등) rules 빈 배열
- 속성 마법이면 element bullet 포함 (불/냉기/전격/신성력/빛/독)
- 고유명사는 일반 표현으로 (산출물은 IP 비식별)

JSON only. 키는 "rules" (문장 배열, 최대 5).
출력 예: {"rules": ["20m 반경 폭발", "불 속성", "합동 시전 필요"]}
"""

_SKILL_SYSTEM = """스킬(skill) mechanism 규칙 추출 전문가.

주어진 스킬 설명에서 규칙을 간결한 bullet 문장으로 추출한다.

각 rule은 effect/trigger/cost/element 중 하나를 담는 짧은 문장:
- effect 예: "단일 대상 절삭 피해", "3초간 이동 속도 증가"
- trigger 예: "지속(패시브) 발동", "연계기로 발동", "능동 사용"
- cost 예: "영혼력 소모", "쿨다운 존재", "체력 대가"
- element 예: "화염 속성", "냉기 속성" (속성 스킬인 경우)

규칙:
- 설명에 명시/강하게 암시된 규칙만 — 무리한 추측 금지
- 스킬 규칙이 없으면 (장소/시간/개념/시스템 등) rules 빈 배열
- 속성 스킬이면 element bullet 포함 (화염/냉기/전격/신성력/빛/독)
- 고유명사는 일반 표현으로 (산출물은 IP 비식별)

JSON only. 키는 "rules" (문장 배열, 최대 5).
출력 예: {"rules": ["단일 대상 절삭 피해", "화염 속성", "영혼력 소모"]}
"""

_SYSTEMS: Final[dict[str, str]] = {
    "combat": _COMBAT_SYSTEM,
    "magic": _MAGIC_SYSTEM,
    "skill": _SKILL_SYSTEM,
}


def get_extract_system(category: str) -> str:
    """category별 추출 prompt — 미지원 category는 combat fallback."""
    return _SYSTEMS.get(category, _COMBAT_SYSTEM)


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
    system: str,
) -> list[str]:
    """27B 추출 → IP 마스킹된 rule 문자열 list (★ category 공통)."""
    user = f"mechanism: {name}\n설명: {description[:600]}\n\n규칙 추출. JSON only."
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
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
                out.append(mask_ip(r.strip()))  # ★ IP 보호 (고유명사만)
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


def _bump_minor(current: str) -> str:
    """version minor 증가 (3.5.0 → 3.6.0)."""
    parts = current.lstrip("v").split(".")
    if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}.{int(parts[1]) + 1}.0"
    return current


async def _main_async(category: str, limit: int | None) -> int:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    mechs: list[dict[str, Any]] = data.get("mechanisms", [])
    subset = [m for m in mechs if m.get("category") == category]
    print(f"=== {category} mechanisms: {len(subset)} ===")

    targets = [
        m for m in subset
        if not has_rules(m) and len(str(m.get("description") or "")) >= _MIN_DESC
    ]
    skip_short = sum(
        1 for m in subset
        if not has_rules(m) and len(str(m.get("description") or "")) < _MIN_DESC
    )
    print(f"추출 대상 (rules 없음 + desc≥{_MIN_DESC}): {len(targets)}")
    print(f"skip (desc 짧음): {skip_short} / 기존 rules 보유: "
          f"{sum(1 for m in subset if has_rules(m))}")

    if limit is not None:
        targets = targets[:limit]
        print(f"★ pilot limit {limit} → {len(targets)}건 처리")

    system = get_extract_system(category)
    extracted = 0
    rule_total = 0
    async with httpx.AsyncClient() as client:
        endpoint, model = await _pick_endpoint(client)
        print(f"\nLLM 추출 시작 (~{len(targets) * 3 / 60:.0f}분)")
        for i, m in enumerate(targets):
            rules = await extract_rules(
                client, endpoint, model,
                str(m.get("name", "")), str(m.get("description") or ""), system,
            )
            if rules:
                m["rules"] = rules
                extracted += 1
                rule_total += len(rules)
            if (i + 1) % 50 == 0:
                print(f"  progress: {i + 1}/{len(targets)} (추출 {extracted})")

    print("\n=== 추출 결과 ===")
    print(f"  rules 추출 성공: {extracted}/{len(targets)}")
    print(f"  총 rule 문장: {rule_total}")

    filled = sum(1 for m in subset if has_rules(m))
    print(f"  {category} rules coverage: {filled}/{len(subset)} "
          f"({filled / len(subset) * 100:.1f}%)")

    print("\n=== 추출 sample ===")
    shown = 0
    for m in subset:
        if has_rules(m) and shown < 5:
            print(f"  {m.get('name')!r}: {m['rules']}")
            shown += 1

    if limit is None:
        current = str(data.get("version", "3.5.0"))
        data["version"] = _bump_minor(current)
        data["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(CANON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n=== version: {current} → {data['version']} (저장) ===")
    else:
        print("\n=== pilot 모드 — 저장 X (검증용) ===")
    return 0


def main() -> int:
    category = "combat"
    limit: int | None = None
    argv = sys.argv
    if "--category" in argv:
        idx = argv.index("--category")
        if idx + 1 < len(argv):
            category = argv[idx + 1]
    if "--limit" in argv:
        idx = argv.index("--limit")
        if idx + 1 < len(argv):
            limit = int(argv[idx + 1])
    return asyncio.run(_main_async(category, limit))


if __name__ == "__main__":
    sys.exit(main())
