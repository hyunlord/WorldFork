"""Phase D step 7 — direction field 단위 테스트."""

from __future__ import annotations

import pytest

from service.api.schemas.freeform_action import ExtractedEntities
from service.sim.intent_classifier import INTENT_CLASSIFY_SCHEMA


class TestExtractedEntitiesDirection:
    def test_direction_default_none(self) -> None:
        e = ExtractedEntities()
        assert e.direction is None

    def test_direction_north(self) -> None:
        e = ExtractedEntities(direction="north")
        assert e.direction == "north"

    def test_direction_south(self) -> None:
        e = ExtractedEntities(direction="south")
        assert e.direction == "south"

    def test_direction_east(self) -> None:
        e = ExtractedEntities(direction="east")
        assert e.direction == "east"

    def test_direction_west(self) -> None:
        e = ExtractedEntities(direction="west")
        assert e.direction == "west"

    def test_direction_invalid_stays_string(self) -> None:
        e = ExtractedEntities(direction="up")
        assert e.direction == "up"


class TestIntentClassifySchema:
    def test_entities_has_direction_property(self) -> None:
        entities_props = INTENT_CLASSIFY_SCHEMA["properties"]["entities"]["properties"]
        assert "direction" in entities_props

    def test_direction_enum_values(self) -> None:
        entities_props = INTENT_CLASSIFY_SCHEMA["properties"]["entities"]["properties"]
        direction_schema = entities_props["direction"]
        enum_vals = direction_schema.get("enum", [])
        assert "north" in enum_vals
        assert "south" in enum_vals
        assert "east" in enum_vals
        assert "west" in enum_vals

    def test_direction_in_required(self) -> None:
        required = INTENT_CLASSIFY_SCHEMA["properties"]["entities"]["required"]
        assert "direction" in required

    @pytest.mark.parametrize("field", ["actor", "location", "item", "direction"])
    def test_all_entity_fields_present(self, field: str) -> None:
        required = INTENT_CLASSIFY_SCHEMA["properties"]["entities"]["required"]
        assert field in required
