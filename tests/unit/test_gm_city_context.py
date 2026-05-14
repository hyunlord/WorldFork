"""Phase 8 village mech (GM prompt only) — _format_city_context unit 본격.

검증 본질:
- realm != CITY → 빈 문자열
- realm == CITY + city_id None → 빈 문자열
- realm == CITY + 미등록 city_id → "본격 데이터 X" fallback
- realm == CITY + RAPDONIA + valid sub_area → sub_area name + description + NPC + connections
- realm == CITY + RAPDONIA + 미등록 sub_area → fallback
- district_7_plaza (★ 162화 hub) → 아이나르 / 에르웬 / 미샤 + 인접 6
- central_library → 라그나 + district_7_plaza 인접

본 commit (a-2)+(a-3) 본격 SKIP된 GM prompt wire — 환전 mechanism 본격 후속.
"""

from __future__ import annotations

from service.game.gm_agent import _format_city_context

# ─── 1. Edge cases: empty fallbacks ───


def test_no_loc_returns_empty() -> None:
    assert _format_city_context({}) == ""


def test_realm_not_city_returns_empty() -> None:
    ctx = {"v2_initial_location": {"realm": "미궁", "sub_area": "진입점"}}
    assert _format_city_context(ctx) == ""


def test_city_id_none_returns_empty() -> None:
    """realm=CITY 본격 city_id 본격 X → 빈 문자열."""
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": None,
        }
    }
    assert _format_city_context(ctx) == ""


def test_unknown_city_id_fallback() -> None:
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "x",
            "city_id": "unknown_city",
        }
    }
    out = _format_city_context(ctx)
    assert "unknown_city" in out
    assert "본격 데이터 X" in out


def test_unknown_sub_area_fallback() -> None:
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "nonexistent_sub_area",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "라프도니아" in out
    assert "sub_area X" in out
    assert "nonexistent_sub_area" in out


# ─── 2. RAPDONIA district_7_plaza (★ hub) ───


def test_plaza_shows_city_and_sub_area_names() -> None:
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "라프도니아" in out
    assert "라프도니아 7구역 중앙 광장" in out


def test_plaza_shows_description() -> None:
    """162화 본문 정합 — '모임 장소' 등 description 포함."""
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "모임 장소" in out or "포탈" in out


def test_plaza_shows_3_canonical_npcs() -> None:
    """광장 본격 비요른 동료 3명 (★ 본문 정합)."""
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "여기 NPC:" in out
    assert "아이나르" in out
    assert "에르웬" in out
    assert "미샤" in out


def test_plaza_shows_connections() -> None:
    """plaza = hub → 인접 다수 (★ a-2 sub_areas)."""
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "district_7_plaza",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "이동 가능:" in out
    # 최소 일부 시설명 본격 (★ a-2 plaza connections)
    assert any(
        kw in out
        for kw in ["여관", "잡화점", "주점", "환전소", "도서관", "탐험가 길드"]
    )


# ─── 3. central_library (★ 라그나) ───


def test_library_shows_ragna() -> None:
    """라비기온 중앙 도서관 — 사서 라그나 (★ namu §4.3)."""
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "central_library",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "라비기온 중앙 도서관" in out
    assert "라그나" in out


# ─── 4. exchange_office (★ 후속 commit 본격 hint 없음) ───


def test_exchange_office_shows_sub_area_no_action_hint() -> None:
    """본 commit 본격 환전 mechanism X → action hint 본격 X.

    후속 commit (★ Item.grade + Character.stone + EXCHANGE_MAGE_STONES) 시
    "EXCHANGE_MAGE_STONES 본격 본격" hint 추가.
    """
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "exchange_office",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "환전소" in out
    # 본 commit 본격 — EXCHANGE_MAGE_STONES action hint 본격 X (후속)
    assert "EXCHANGE_MAGE_STONES" not in out


# ─── 5. Sub area without NPCs (★ tavern) ───


def test_tavern_no_npcs_no_npc_line() -> None:
    """주점 본격 npc_ids 빈 set → 'NPC:' 줄 본격 X."""
    ctx = {
        "v2_initial_location": {
            "realm": "도시",
            "sub_area": "tavern",
            "city_id": "rapdonia",
        }
    }
    out = _format_city_context(ctx)
    assert "주점" in out
    assert "여기 NPC:" not in out
