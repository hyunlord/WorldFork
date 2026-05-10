"""prepare_lora_dataset.py 본격 단위 검증 (★ Phase 5)."""

from __future__ import annotations

from tools.visual.prepare_lora_dataset import (
    DATASET_DIR,
    SOURCE_DIR,
    TRIGGER_WORD,
)


def test_trigger_word_is_bjorn_warrior() -> None:
    assert TRIGGER_WORD == "bjorn_warrior"


def test_dataset_dir_under_source() -> None:
    """dataset이 source 하위 본격."""
    assert DATASET_DIR.parent == SOURCE_DIR


def test_source_dir_is_worldfork() -> None:
    assert SOURCE_DIR.name == "worldfork"
