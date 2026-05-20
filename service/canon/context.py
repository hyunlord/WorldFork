"""Phase D step 5/6a — EntityIndex + SpawnTable 전역 싱글톤.

app.py circular import 방지를 위해 별도 모듈로 분리.
app.py lifespan 에서 set_entity_index() / set_spawn_table() 호출.
"""

from __future__ import annotations

from service.canon.entity_index import EntityIndex
from service.canon.spawn import SpawnTable

_entity_index: EntityIndex | None = None
_spawn_table: SpawnTable | None = None


def get_entity_index() -> EntityIndex | None:
    return _entity_index


def set_entity_index(idx: EntityIndex) -> None:
    global _entity_index
    _entity_index = idx


def clear_entity_index() -> None:
    global _entity_index
    _entity_index = None


def get_spawn_table() -> SpawnTable | None:
    return _spawn_table


def set_spawn_table(table: SpawnTable) -> None:
    global _spawn_table
    _spawn_table = table


def clear_spawn_table() -> None:
    global _spawn_table
    _spawn_table = None
