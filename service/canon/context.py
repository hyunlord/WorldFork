"""Phase D step 5/6a/6b/6c — EntityIndex + SpawnTable + ItemRegistry + CanonFacts 전역 싱글톤.

app.py circular import 방지를 위해 별도 모듈로 분리.
app.py lifespan 에서 set_* 호출.
"""

from __future__ import annotations

from service.canon.entity_index import EntityIndex
from service.canon.items import ItemRegistry
from service.canon.schema import CanonFacts
from service.canon.spawn import SpawnTable

_entity_index: EntityIndex | None = None
_spawn_table: SpawnTable | None = None
_item_registry: ItemRegistry | None = None
_canon_facts: CanonFacts | None = None


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


def get_item_registry() -> ItemRegistry | None:
    return _item_registry


def set_item_registry(registry: ItemRegistry) -> None:
    global _item_registry
    _item_registry = registry


def clear_item_registry() -> None:
    global _item_registry
    _item_registry = None


def get_canon_facts() -> CanonFacts | None:
    return _canon_facts


def set_canon_facts(facts: CanonFacts) -> None:
    global _canon_facts
    _canon_facts = facts


def clear_canon_facts() -> None:
    global _canon_facts
    _canon_facts = None
