"""Phase D step 5 — EntityIndex 전역 싱글톤.

app.py circular import 방지를 위해 별도 모듈로 분리.
app.py lifespan 에서 set_entity_index() 호출.
handler / freeform_handler 에서 get_entity_index() 호출.
"""

from __future__ import annotations

from service.canon.entity_index import EntityIndex

_entity_index: EntityIndex | None = None


def get_entity_index() -> EntityIndex | None:
    return _entity_index


def set_entity_index(idx: EntityIndex) -> None:
    global _entity_index
    _entity_index = idx


def clear_entity_index() -> None:
    global _entity_index
    _entity_index = None
