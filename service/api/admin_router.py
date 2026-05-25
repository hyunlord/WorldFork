"""I-B2: runtime canon reload endpoint (audit-step4-2)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from service.canon.context import (
    set_canon_facts,
    set_entity_index,
    set_item_registry,
    set_spawn_table,
)
from service.canon.entity_index import EntityIndex
from service.canon.items import ItemRegistry
from service.canon.loader import load_canon_facts
from service.canon.spawn import SpawnTable

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/canon/reload")
async def reload_canon() -> dict[str, object]:
    """canon_facts_v3.json runtime reload — 서버 재시작 없이 즉시 반영."""
    try:
        facts = load_canon_facts()
        set_canon_facts(facts)
        set_entity_index(EntityIndex(facts))
        set_spawn_table(SpawnTable(facts))
        set_item_registry(ItemRegistry(facts))
        return {
            "status": "ok",
            "entity_counts": {
                "characters": len(facts.characters),
                "locations": len(facts.locations),
                "essences": len(facts.essences),
                "races": len(facts.races),
                "mechanisms": len(facts.mechanisms),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"reload failed: {exc}") from exc
