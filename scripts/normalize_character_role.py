"""I-E2 character role 정규화.

1,792 character role → 6 taxonomy 통합.

logic:
1. 직접 mapping — 기존 role 명확 매핑
2. keyword 패턴 — substring 포함 여부 판단
3. LLM 재분류 — background 정합 (9B port 8083)
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import httpx

CANON_PATH = Path(".local/canon/canon_facts_v3.json")
LLM_ENDPOINT = "http://localhost:8083/v1/chat/completions"

# ── taxonomy constants ──────────────────────────────────────────────────────

ROLE_PROTAGONIST: Final = "주인공"
ROLE_COMPANION: Final = "동료"
ROLE_MAJOR_NPC: Final = "주요 NPC"
ROLE_RESIDENT: Final = "주민"
ROLE_EXTRA: Final = "엑스트라"
ROLE_META: Final = "메타"

ALL_ROLES: Final = frozenset([
    ROLE_PROTAGONIST,
    ROLE_COMPANION,
    ROLE_MAJOR_NPC,
    ROLE_RESIDENT,
    ROLE_EXTRA,
    ROLE_META,
])

# ── 직접 exact mapping ──────────────────────────────────────────────────────

DIRECT_MAPPING: Final[dict[str, str]] = {
    # 주인공
    "주인공": ROLE_PROTAGONIST,
    "플레이어": ROLE_PROTAGONIST,
    "주인공, 탐험가": ROLE_PROTAGONIST,
    "주인공/지휘관": ROLE_PROTAGONIST,
    "바바리안, 플레이어": ROLE_PROTAGONIST,
    "protagonist_alias": ROLE_PROTAGONIST,
    "narrator/protagonist": ROLE_PROTAGONIST,
    "본체/주인공": ROLE_PROTAGONIST,
    "플레이어 (사망)": ROLE_PROTAGONIST,
    "각색 (시즌 1)": ROLE_PROTAGONIST,
    "각색 (시즌 2~)": ROLE_PROTAGONIST,
    "게임빙의물 장르의 중심 인물": ROLE_PROTAGONIST,
    # 동료
    "동료": ROLE_COMPANION,
    "파티원": ROLE_COMPANION,
    "팀원": ROLE_COMPANION,
    "원정대원": ROLE_COMPANION,
    "원정대원(일기 기록자)": ROLE_COMPANION,
    "원정대장": ROLE_COMPANION,
    "주인공의 동료": ROLE_COMPANION,
    "비요른의 동료": ROLE_COMPANION,
    "동료/탐험가": ROLE_COMPANION,
    "동료/캐릭터": ROLE_COMPANION,
    "동행자": ROLE_COMPANION,
    "동반자": ROLE_COMPANION,
    "아군 탱커": ROLE_COMPANION,
    "아군 신관": ROLE_COMPANION,
    "이백호 팀원": ROLE_COMPANION,
    "탐사군 멤버": ROLE_COMPANION,
    "탐사군 일원": ROLE_COMPANION,
    "탐사단원": ROLE_COMPANION,
    "아나바다 클랜 단원, 원년 멤버": ROLE_COMPANION,
    "아나바다 클랜원": ROLE_COMPANION,
    "아나바다 클랜 단원": ROLE_COMPANION,
    "아나바다 클랜 구성원": ROLE_COMPANION,
    "아나바다 클랜 부단장": ROLE_COMPANION,
    "오르큘리스 핵심 멤버": ROLE_COMPANION,
    "오르큘리스 멤버": ROLE_COMPANION,
    "팀 애플 나라크의 동료": ROLE_COMPANION,
    "팀 애플 나라크 구성원": ROLE_COMPANION,
    "원탁 멤버": ROLE_COMPANION,
    "원탁 참가자": ROLE_COMPANION,
    "동료, 샬롯의 오빠": ROLE_COMPANION,
    "동료/목소리 제공자": ROLE_COMPANION,
    "주인공, 아멜리아의 동료": ROLE_COMPANION,
    "렉스의 동료": ROLE_COMPANION,
    "발견된 동료": ROLE_COMPANION,
    "고인, 전 동료": ROLE_COMPANION,
    "사망한 동료 (왕가 공인 8등급 마법사)": ROLE_COMPANION,
    "동료, 마법사": ROLE_COMPANION,
    "바바리안 동료": ROLE_COMPANION,
    "요정 파티원": ROLE_COMPANION,
    "6층 활동 팀": ROLE_COMPANION,
    # 주요 NPC
    "귀족": ROLE_MAJOR_NPC,
    "왕": ROLE_MAJOR_NPC,
    "왕족": ROLE_MAJOR_NPC,
    "신": ROLE_MAJOR_NPC,
    "사서": ROLE_MAJOR_NPC,
    "길드 마스터": ROLE_MAJOR_NPC,
    "길드장": ROLE_MAJOR_NPC,
    "탐험가 길드의 길드장": ROLE_MAJOR_NPC,
    "탐험가 길드 지부장": ROLE_MAJOR_NPC,
    "탐험가 길드 7지역장": ROLE_MAJOR_NPC,
    "촌장": ROLE_MAJOR_NPC,
    "부족장": ROLE_MAJOR_NPC,
    "백작": ROLE_MAJOR_NPC,
    "자작": ROLE_MAJOR_NPC,
    "공작": ROLE_MAJOR_NPC,
    "남작": ROLE_MAJOR_NPC,
    "후작": ROLE_MAJOR_NPC,
    "여백작": ROLE_MAJOR_NPC,
    "공 (귀족/직함)": ROLE_MAJOR_NPC,
    "황제": ROLE_MAJOR_NPC,
    "재상": ROLE_MAJOR_NPC,
    "귀족, 협력자": ROLE_MAJOR_NPC,
    "리더, 남작": ROLE_MAJOR_NPC,
    "기사단장": ROLE_MAJOR_NPC,
    "왕실 기사단장": ROLE_MAJOR_NPC,
    "지역장": ROLE_MAJOR_NPC,
    "지부장": ROLE_MAJOR_NPC,
    "대신관": ROLE_MAJOR_NPC,
    "추기경": ROLE_MAJOR_NPC,
    "대주교": ROLE_MAJOR_NPC,
    "여신": ROLE_MAJOR_NPC,
    "성녀": ROLE_MAJOR_NPC,
    "종교 지도자": ROLE_MAJOR_NPC,
    "종교 지도자 후보": ROLE_MAJOR_NPC,
    "클랜 수장": ROLE_MAJOR_NPC,
    "군단장": ROLE_MAJOR_NPC,
    "수장": ROLE_MAJOR_NPC,
    "장미기사단": ROLE_MAJOR_NPC,
    "국가 수반": ROLE_MAJOR_NPC,
    "단장": ROLE_MAJOR_NPC,
    "부단장": ROLE_MAJOR_NPC,
    "신/존재": ROLE_MAJOR_NPC,
    "신적 존재": ROLE_MAJOR_NPC,
    "악신": ROLE_MAJOR_NPC,
    "어둠의 군주": ROLE_MAJOR_NPC,
    "공포의 군주": ROLE_MAJOR_NPC,
    "기록의 군주": ROLE_MAJOR_NPC,
    "어둠의 정령왕": ROLE_MAJOR_NPC,
    "대신관 (사망/유품 전달)": ROLE_MAJOR_NPC,
    "사망자, 신관": ROLE_MAJOR_NPC,
    "탐험가 길드 관계자": ROLE_MAJOR_NPC,
    "영웅": ROLE_MAJOR_NPC,
    "철의 영웅": ROLE_MAJOR_NPC,
    "황금 세대 탐험가": ROLE_MAJOR_NPC,
    "상위 모험가": ROLE_MAJOR_NPC,
    # 주민
    "탐험가": ROLE_RESIDENT,
    "마법사": ROLE_RESIDENT,
    "전사": ROLE_RESIDENT,
    "기사": ROLE_RESIDENT,
    "장인": ROLE_RESIDENT,
    "상인": ROLE_RESIDENT,
    "대장장이": ROLE_RESIDENT,
    "성기사": ROLE_RESIDENT,
    "용병": ROLE_RESIDENT,
    "사제": ROLE_RESIDENT,
    "신관": ROLE_RESIDENT,
    "소환술사": ROLE_RESIDENT,
    "흑마법사": ROLE_RESIDENT,
    "네크로맨서": ROLE_RESIDENT,
    "이능술사": ROLE_RESIDENT,
    "마녀": ROLE_RESIDENT,
    "탐색꾼": ROLE_RESIDENT,
    "항해사": ROLE_RESIDENT,
    "경관": ROLE_RESIDENT,
    "군인": ROLE_RESIDENT,
    "행정원": ROLE_RESIDENT,
    "바바리안": ROLE_RESIDENT,
    "바바리안 전사": ROLE_RESIDENT,
    "수인 주민": ROLE_RESIDENT,
    "주민, 노동자": ROLE_RESIDENT,
    "노동자, 전사": ROLE_RESIDENT,
    "5등급 탐험가": ROLE_RESIDENT,
    "3등급 탐험가": ROLE_RESIDENT,
    "과거 탐험가 (사망)": ROLE_RESIDENT,
    "예언가": ROLE_RESIDENT,
    "치료자": ROLE_RESIDENT,
    "경비대장": ROLE_RESIDENT,
    "탐험가 (사망)": ROLE_RESIDENT,
    "사망자, 이능술사": ROLE_RESIDENT,
    "사망자, 마법사": ROLE_RESIDENT,
    "사망자, 성기사": ROLE_RESIDENT,
    "사망자, 트롤 소환사": ROLE_RESIDENT,
    "사망자, 배신자로 몰려 처형": ROLE_RESIDENT,
    "explorer": ROLE_RESIDENT,
    "priest": ROLE_RESIDENT,
    # 엑스트라
    "적": ROLE_EXTRA,
    "적대 세력": ROLE_EXTRA,
    "적군": ROLE_EXTRA,
    "적대자": ROLE_EXTRA,
    "악령": ROLE_EXTRA,
    "몬스터": ROLE_EXTRA,
    "보스": ROLE_EXTRA,
    "변이종 몬스터": ROLE_EXTRA,
    "희생자": ROLE_EXTRA,
    "사망자": ROLE_EXTRA,
    "과거 인물": ROLE_EXTRA,
    "간접 언급": ROLE_EXTRA,
    "정수 원주체": ROLE_EXTRA,
    "미정": ROLE_EXTRA,
    "불명": ROLE_EXTRA,
    "N/A": ROLE_EXTRA,
    "언급된 존재": ROLE_EXTRA,
    "언급된 인물": ROLE_EXTRA,
    "과거 적": ROLE_EXTRA,
    "적대 세력/불청객": ROLE_EXTRA,
    "적대 세력/전사자": ROLE_EXTRA,
    "전사자": ROLE_EXTRA,
    "사망자, 아쿠라바 팀 소속 마법사": ROLE_EXTRA,
    "사망자, 카이슬란의 친구/수하": ROLE_EXTRA,
    "사망자, 리어드 애쉬드": ROLE_EXTRA,
    "사망자, 제5팀 궁수": ROLE_EXTRA,
    "소환수": ROLE_EXTRA,
    "소환수/분신체 대상": ROLE_EXTRA,
    "소환수/캐릭터": ROLE_EXTRA,
    "3등급 몬스터": ROLE_EXTRA,
    "4등급 몬스터": ROLE_EXTRA,
    "7등급 몬스터": ROLE_EXTRA,
    "존재": ROLE_EXTRA,
    "비교 대상": ROLE_EXTRA,
    "비교 대상 몬스터": ROLE_EXTRA,
    "마물": ROLE_EXTRA,
    "보스/적": ROLE_EXTRA,
    "보스/도플갱어 본체": ROLE_EXTRA,
    "히든 보스": ROLE_EXTRA,
    "중간 보스": ROLE_EXTRA,
    "공포의 군주 / 보스 몬스터": ROLE_EXTRA,
    "균열 수호자": ROLE_EXTRA,
    "수호자": ROLE_EXTRA,
    "과거 적대자": ROLE_EXTRA,
    "과거 등장인물(회상)": ROLE_EXTRA,
    "등장인물 (회상)": ROLE_EXTRA,
    "등장인물 (언급)": ROLE_EXTRA,
    "과거 언급 인물": ROLE_EXTRA,
    "과거 적대자 (언급)": ROLE_EXTRA,
    "의심 대상 (간접 언급)": ROLE_EXTRA,
    "의심 대상": ROLE_EXTRA,
    # 메타
    "커뮤니티 유저": ROLE_META,
    "커뮤니티 사용자": ROLE_META,
    "유저": ROLE_META,
    "DC 유저": ROLE_META,
    "커뮤니티 회원": ROLE_META,
    "커뮤니티 관리자": ROLE_META,
    "게시판 댓글 작성자": ROLE_META,
    "시청자": ROLE_META,
    "방장": ROLE_META,
    "작가": ROLE_META,
    "게임 마스터": ROLE_META,
    "게임 제작자/클리어자": ROLE_META,
    "1대 매니저": ROLE_META,
    "2대 매니저": ROLE_META,
    "플레이어 그룹": ROLE_META,
    "고인물": ROLE_META,
    "미국인": ROLE_META,
    "닉네임": ROLE_META,
    "이명": ROLE_META,
    "figure": ROLE_META,
    "deity": ROLE_META,
}

# ── LLM 재분류 명시 트리거 (exact miss 후 keyword 앞에 체크) ─────────────────

_LLM_TRIGGERS: Final = frozenset([
    "캐릭터",
    "등장인물",  # "장인" 키워드 오탐 방지
    "클랜",
    "조직",
    "기관",
    "과거 인물",
    "고대 인물",
    "고대 군주 (신화)",
])

# ── keyword 패턴 (exact miss 시 substring 판단) ─────────────────────────────

# (keywords_tuple, role) — 우선순위 순서 유지
_KEYWORD_RULES: list[tuple[tuple[str, ...], str]] = [
    # 메타 우선
    (("커뮤니티", "유저", "DC 유저", "게시판 댓글", "시청자", "방장"), ROLE_META),
    # 주인공
    (("주인공", "플레이어", "protagonist", "narrator"), ROLE_PROTAGONIST),
    # 동료
    (("동료", "파티원", "팀원", "원정대원", "탐사군", "아군",
      "오르큘리스", "원탁 멤버", "원탁 참가자", "동행자", "동반자",
      "탐사단원"), ROLE_COMPANION),
    # 주요 NPC (직책/직위 보유자)
    (("귀족", "왕", "왕족", "황제", "재상", "공작", "백작", "자작",
      "남작", "후작", "여백작", "대신관", "추기경", "대주교",
      "기사단장", "왕실 기사단", "지역장", "지부장", "단장", "부족장",
      "촌장", "수장", "군단장", "클랜 수장", "길드장", "길드 마스터",
      "장미기사단", "여신", "성녀", "악신",
      "어둠의 군주", "기록의 군주", "공포의 군주"), ROLE_MAJOR_NPC),
    # 주민 (직업 보유)
    (("탐험가", "마법사", "전사", "기사", "상인", "대장장이",
      "성기사", "용병", "사제", "신관", "소환술사", "흑마법사",
      "네크로맨서", "이능술사", "마녀", "탐색꾼", "항해사",
      "군인", "경관", "행정원", "바바리안", "궁수", "치료자",
      "경비", "의사", "건축", "기록자", "마도사"), ROLE_RESIDENT),
    # 엑스트라 (적/사망/몬스터)
    (("적대", "몬스터", "보스", "악령", "희생자", "수호자",
      "사망자", "전사자", "소환수", "마물", "히든", "중간 보스"), ROLE_EXTRA),
]


def _keyword_classify(role: str) -> str | None:
    """keyword 포함 여부로 분류. 매칭 X → None."""
    lower = role.lower()
    for keywords, target_role in _KEYWORD_RULES:
        for kw in keywords:
            if kw in lower or kw in role:
                return target_role
    return None


def classify_direct(role: str | None) -> str | None:
    """기존 role → taxonomy 직접 분류.

    return:
    - taxonomy role (직접 매핑 또는 keyword 매칭)
    - None (LLM 재분류 필요)
    """
    if not role or not role.strip():
        return None

    s = role.strip()

    # 1. exact match
    if s in DIRECT_MAPPING:
        return DIRECT_MAPPING[s]

    # 2. LLM 트리거 명시 (keyword 오탐 방지)
    if s in _LLM_TRIGGERS:
        return None

    # 3. keyword substring match
    result = _keyword_classify(s)
    if result is not None:
        return result

    # 4. LLM 재분류 필요
    return None


# ── LLM 재분류 ──────────────────────────────────────────────────────────────

_CLASSIFIER_SYSTEM = """/no_think
한국어 RPG character role 분류 전문가. background 정합 6 taxonomy 중 1개 분류.

taxonomy:
- 주인공: 본문 주인공 (비요른 / 투르윈 정합)
- 동료: 파티원 / 원정 동료 / 클랜 단원
- 주요 NPC: 본문 dialogue 다수 + 중요 역할 (사서 / 귀족 / 길드 마스터)
- 주민: 일반 NPC + 직업 보유 (탐험가 / 상인 / 마법사 / 전사 / 장인)
- 엑스트라: 한번 등장 단역 (군중 / 익명 / 적)
- 메타: 본문 외 (커뮤니티 유저 / 작가 언급)

응답:
- JSON only: {"role": "주민"}
- 위 6개 중 1개만 정확히
- 추가 설명 X
"""


async def classify_via_llm(
    client: httpx.AsyncClient,
    name: str,
    background: str,
    original_role: str | None = None,
) -> str:
    """LLM 호출로 background 정합 role 분류."""
    parts = [f"name: {name}"]
    if original_role:
        parts.append(f"old_role: {original_role}")
    parts.append(f"background: {background[:500]}")
    user_prompt = "\n".join(parts)

    payload = {
        "model": "qwen35-9b-q3",
        "messages": [
            {"role": "system", "content": _CLASSIFIER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 50,
        "temperature": 0.1,
    }

    try:
        resp = await client.post(LLM_ENDPOINT, json=payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # thinking 태그 제거 (Qwen3 정합)
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # JSON 파싱 시도
        try:
            result = json.loads(content)
            role = str(result.get("role", "")).strip()
        except json.JSONDecodeError:
            # 텍스트에서 taxonomy 추출
            for r in [ROLE_PROTAGONIST, ROLE_COMPANION, ROLE_MAJOR_NPC,
                      ROLE_RESIDENT, ROLE_EXTRA, ROLE_META]:
                if r in content:
                    return r
            role = ""

        return role if role in ALL_ROLES else ROLE_EXTRA

    except Exception as e:
        print(f"  LLM error [{name}]: {e}", file=sys.stderr)
        return ROLE_EXTRA


async def _classify_batch(
    characters_to_classify: list[dict[str, object]],
) -> dict[str, str]:
    """LLM 일괄 분류 (sequential — port 부하 방지)."""
    results: dict[str, str] = {}
    total = len(characters_to_classify)

    async with httpx.AsyncClient() as client:
        for i, c in enumerate(characters_to_classify):
            name = str(c.get("name", ""))
            background = str(c.get("background") or "")
            original_role = c.get("role")
            original_role_str = str(original_role) if original_role is not None else None

            if not background:
                results[name] = ROLE_EXTRA
                continue

            role = await classify_via_llm(client, name, background, original_role_str)
            results[name] = role

            if (i + 1) % 100 == 0:
                print(f"  LLM progress: {i + 1}/{total}")

    return results


# ── main ────────────────────────────────────────────────────────────────────

_TARGET_VERSION = "3.2.0"


def _bump_version(current: str) -> str:
    if current == _TARGET_VERSION:
        return _TARGET_VERSION
    parts = current.lstrip("v").split(".")
    if len(parts) == 3 and parts[0] == "3" and parts[1] == "1":
        return _TARGET_VERSION
    return current


async def _main_async() -> int:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    characters: list[dict[str, object]] = data.get("characters", [])
    print(f"=== total: {len(characters)} ===")

    # Step 1: 직접 mapping
    direct_count = 0
    llm_needed: list[dict[str, object]] = []

    for c in characters:
        original = c.get("role")
        classified = classify_direct(original if isinstance(original, str) else None)
        if classified is not None:
            c["role"] = classified
            direct_count += 1
        else:
            llm_needed.append(c)

    print(f"\n직접 mapping: {direct_count}")
    print(f"LLM 재분류 필요: {len(llm_needed)}")

    # Step 2: LLM 재분류
    if llm_needed:
        no_bg = sum(1 for c in llm_needed if not c.get("background"))
        with_bg = len(llm_needed) - no_bg
        print(f"  background X → 엑스트라 즉시: {no_bg}")
        print(f"  LLM 분류 예정: {with_bg}")
        est_min = with_bg * 1.5 / 60
        print(f"\nLLM 분류 시작 (~{est_min:.0f}분 예상) ===")

        llm_results = await _classify_batch(llm_needed)

        for c in llm_needed:
            name = str(c.get("name", ""))
            c["role"] = llm_results.get(name, ROLE_EXTRA)

    # 검증
    invalid = [c for c in characters if c.get("role") not in ALL_ROLES]
    if invalid:
        print(f"\n⚠ invalid role: {len(invalid)}개", file=sys.stderr)
        for c in invalid[:5]:
            print(f"  {c.get('name')!r} → {c.get('role')!r}", file=sys.stderr)
        return 1

    # 최종 분포
    final_roles: Counter[str | None] = Counter(str(c.get("role")) for c in characters)
    print("\n=== 최종 분포 ===")
    for role, count in final_roles.most_common():
        pct = count / len(characters) * 100
        print(f"  {role!r}: {count} ({pct:.1f}%)")

    # version bump + 저장
    current_ver = str(data.get("version", "3.1.0"))
    data["version"] = _bump_version(current_ver)
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
