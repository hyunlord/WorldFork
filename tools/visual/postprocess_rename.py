"""ComfyUI 본격 출력 자료 post-process — 본격 path 자동 진단 + rename.

본 commit (★ 옵션 3, 본인 finding 직접 답):
- ComfyUI cwd 본격 자동 진단 (★ character_base.detect_comfyui_output_dir 본격 활용)
- 본격 자료 → ~/ComfyUI/output/worldfork/ 본격 이동
- 본격 rename (★ 비요른_00_*.png 등)
- character_base.py rename 사일런트 실패 본격 답
- Phase 2 본격 재사용 가능 (★ 미래 안전)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import requests

from .character_base import (
    CHARACTERS,
    POSES,
    detect_comfyui_output_dir,
)

COMFYUI_API = "http://localhost:8188"
TARGET_DIR = Path.home() / "ComfyUI" / "output" / "worldfork"

CHARACTER_NAMES: list[str] = list(CHARACTERS.keys())


def parse_history_for_files() -> list[dict[str, Any]]:
    """ComfyUI history API → 본격 자료 metadata 추출.

    본격 본질:
    - prompt 본격 분석 (★ barbarian/faerie 진단)
    - pose 본격 매칭 (★ POSES index)
    - 본격 file path metadata
    """
    response = requests.get(f"{COMFYUI_API}/history", timeout=10)
    response.raise_for_status()
    history = response.json()

    entries: list[dict[str, Any]] = []
    for prompt_id, info in history.items():
        prompt_data = info.get("prompt", [])
        if not prompt_data or len(prompt_data) < 3:
            continue

        # workflow 본격 분석 (★ CLIPTextEncode positive prompt 추출)
        workflow = prompt_data[2] if len(prompt_data) > 2 else {}
        prompt_text = ""
        for node in workflow.values():
            if node.get("class_type") == "CLIPTextEncode":
                text = node.get("inputs", {}).get("text", "")
                if text:  # ★ negative는 빈 string이라 skip
                    prompt_text = text
                    break

        # 캐릭터 본격 진단
        character: str | None = None
        if "barbarian" in prompt_text.lower():
            character = "비요른"
        elif "faerie" in prompt_text.lower():
            character = "에르웬"
        if not character:
            continue

        # pose 본격 매칭 (★ POSES 인덱스)
        pose_idx = -1
        for i, pose in enumerate(POSES):
            if pose in prompt_text:
                pose_idx = i
                break

        # 자료 본격 path
        outputs = info.get("outputs", {})
        for node_outputs in outputs.values():
            for img in node_outputs.get("images", []):
                entries.append(
                    {
                        "prompt_id": prompt_id,
                        "character": character,
                        "pose_idx": pose_idx,
                        "filename": img.get("filename"),
                        "subfolder": img.get("subfolder", ""),
                    }
                )

    return entries


def postprocess_files(
    source_dir: Path,
    target_dir: Path,
    dry_run: bool = False,
) -> dict[str, list[Path]]:
    """ComfyUI output → target_dir 본격 이동 + rename."""
    target_dir.mkdir(parents=True, exist_ok=True)

    entries = parse_history_for_files()
    print(f"history 본격 entries: {len(entries)}")

    moved: dict[str, list[Path]] = {name: [] for name in CHARACTER_NAMES}

    for entry in entries:
        character = entry["character"]
        pose_idx = entry["pose_idx"]
        filename = entry["filename"]
        subfolder = entry["subfolder"]

        if not filename:
            continue

        if subfolder:
            src = source_dir / subfolder / filename
        else:
            src = source_dir / filename

        if not src.exists():
            print(f"  ⚠️ X 발견: {src}")
            continue

        if pose_idx >= 0 and pose_idx < len(POSES):
            pose_slug = (
                POSES[pose_idx][:30].replace(" ", "_").replace(",", "")
            )
        else:
            pose_slug = "unknown"

        existing_count = len(moved[character])
        dst_name = f"{character}_{existing_count:02d}_{pose_slug}.png"
        dst = target_dir / dst_name

        if dry_run:
            print(f"  [dry-run] {src} → {dst}")
        else:
            try:
                src.rename(dst)
                print(f"  → {dst.name}")
            except OSError:
                # cross-device fallback (★ /proc cwd → home 다른 mount)
                shutil.move(str(src), str(dst))
                print(f"  → {dst.name} (★ shutil)")

        moved[character].append(dst)

    return moved


def main() -> int:
    print("=" * 80)
    print("Visual Phase 1 — post-process 본격 (★ 옵션 3)")
    print("=" * 80)

    try:
        r = requests.get(f"{COMFYUI_API}/system_stats", timeout=5)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] ComfyUI 접속 X: {e}")
        return 1

    source_dir = detect_comfyui_output_dir()
    if source_dir is None:
        print("[ERROR] ComfyUI output dir 본격 X 진단")
        return 1

    print(f"[OK] ComfyUI output: {source_dir}")
    print(f"[OK] target: {TARGET_DIR}")

    moved = postprocess_files(source_dir=source_dir, target_dir=TARGET_DIR)

    metadata: dict[str, Any] = {
        "phase": "Phase 1 v2 post-process",
        "source_dir": str(source_dir),
        "target_dir": str(TARGET_DIR),
        "moved_files": {
            name: [p.name for p in paths]
            for name, paths in moved.items()
        },
        "total_moved": sum(len(paths) for paths in moved.values()),
    }
    metadata_path = TARGET_DIR / "phase1_v2_postprocess_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 본격 결과 ===")
    for name, paths in moved.items():
        print(f"{name}: {len(paths)}장 본격")
    print(f"metadata: {metadata_path}")
    print(f"본인 검수: {TARGET_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
