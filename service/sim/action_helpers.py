"""Phase D step 3 — action handler 공용 헬퍼."""

from __future__ import annotations

import re

# 복합어 먼저 — 단일 자모 오매칭("이동" → "동") 방지
_DIRECTION_MULTICHAR: tuple[tuple[str, str], ...] = (
    ("북동쪽", "북동"), ("북서쪽", "북서"), ("남동쪽", "남동"), ("남서쪽", "남서"),
    ("북동", "북동"), ("북서", "북서"), ("남동", "남동"), ("남서", "남서"),
    ("북쪽", "북"), ("남쪽", "남"), ("동쪽", "동"), ("서쪽", "서"),
    ("위쪽", "북"), ("아래쪽", "남"), ("오른쪽", "동"), ("왼쪽", "서"),
    ("앞쪽", "북"), ("뒤쪽", "남"),
)

_ITEM_KEYWORDS: list[str] = [
    "정수", "마석", "물약", "두루마리", "단검", "검",
    "활", "방패", "갑옷", "횃불", "열쇠", "가방",
]


def extract_direction(text: str) -> str | None:
    """user_input에서 이동 방향 추출 (8방향 + 별칭).

    복합어(북쪽, 북동 등) 우선 매칭.
    단일 자(북/남/동/서)는 앞에 한글 음절이 없을 때만 매칭
    — '이동한다'의 '동' 같은 오매칭 방지.
    """
    for kw, direction in _DIRECTION_MULTICHAR:
        if kw in text:
            return direction
    for kw, direction in (("북", "북"), ("남", "남"), ("동", "동"), ("서", "서")):
        if re.search(r"(?<![가-힣])" + kw, text):
            return direction
    return None


def extract_item_from_input(text: str) -> str | None:
    """user_input에서 아이템 키워드 추출."""
    for kw in _ITEM_KEYWORDS:
        if kw in text:
            return kw
    return None


def extract_item_from_inventory(text: str, inventory: list[str]) -> str | None:
    """user_input 키워드와 inventory 교집합 — 가장 먼저 매칭된 항목."""
    for item in inventory:
        if any(kw in item for kw in text.split()):
            return item
        for kw in _ITEM_KEYWORDS:
            if kw in text and kw in item:
                return item
    return extract_item_from_input(text)


def get_entity_name(entity: dict[str, object], default: str = "대상") -> str:
    """dict에서 'name' 필드를 안전하게 추출."""
    raw = entity.get("name", default)
    return str(raw) if raw is not None else default


def get_first_enemy(encounters: list[dict[str, object]]) -> dict[str, object] | None:
    """encounters에서 적대적 개체 첫 번째 반환."""
    for enc in encounters:
        if enc.get("hostile") is True:
            return enc
    # hostile 키 없는 경우도 적으로 간주
    for enc in encounters:
        if "hostile" not in enc:
            return enc
    return None


def get_first_npc(encounters: list[dict[str, object]]) -> dict[str, object] | None:
    """encounters에서 비적대 NPC 첫 번째 반환."""
    for enc in encounters:
        if enc.get("hostile") is False:
            return enc
    return None
