"""postprocess_rename.py 본격 단위 검증 (★ 옵션 3 fix)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.visual.postprocess_rename import (
    CHARACTER_NAMES,
    POSES,
    detect_comfyui_output_dir,
    parse_history_for_files,
)


def test_character_names_contains_pair() -> None:
    """비요른 + 에르웬 본격."""
    assert "비요른" in CHARACTER_NAMES
    assert "에르웬" in CHARACTER_NAMES


def test_poses_count_8() -> None:
    """POSES 본격 8 (★ character_base 정합)."""
    assert len(POSES) == 8


def test_detect_comfyui_returns_path_or_none() -> None:
    """본격 진단 return 타입."""
    result = detect_comfyui_output_dir()
    assert result is None or isinstance(result, Path)


def test_parse_history_returns_list_when_empty() -> None:
    """history empty 시 빈 list 본격."""
    with patch(
        "tools.visual.postprocess_rename.requests.get"
    ) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = parse_history_for_files()
        assert result == []


def test_parse_history_extracts_character_from_barbarian_prompt() -> None:
    """barbarian prompt → 비요른 본격."""
    with patch(
        "tools.visual.postprocess_rename.requests.get"
    ) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "test_id_001": {
                "prompt": [
                    None,
                    None,
                    {
                        "4": {
                            "class_type": "CLIPTextEncode",
                            "inputs": {
                                "text": (
                                    "muscular barbarian warrior, "
                                    + POSES[0]
                                ),
                            },
                        }
                    },
                ],
                "outputs": {
                    "10": {
                        "images": [
                            {
                                "filename": "test.png",
                                "subfolder": "worldfork",
                            }
                        ],
                    }
                },
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = parse_history_for_files()
        assert len(result) == 1
        assert result[0]["character"] == "비요른"
        assert result[0]["pose_idx"] == 0
        assert result[0]["filename"] == "test.png"


def test_parse_history_extracts_character_from_faerie_prompt() -> None:
    """faerie prompt → 에르웬 본격."""
    with patch(
        "tools.visual.postprocess_rename.requests.get"
    ) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "test_id_002": {
                "prompt": [
                    None,
                    None,
                    {
                        "4": {
                            "class_type": "CLIPTextEncode",
                            "inputs": {
                                "text": (
                                    "ethereal faerie, " + POSES[3]
                                ),
                            },
                        }
                    },
                ],
                "outputs": {
                    "10": {
                        "images": [
                            {"filename": "test2.png", "subfolder": ""}
                        ],
                    }
                },
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = parse_history_for_files()
        assert len(result) == 1
        assert result[0]["character"] == "에르웬"
        assert result[0]["pose_idx"] == 3


def test_parse_history_skips_unknown_character() -> None:
    """character X 진단 시 skip 본격."""
    with patch(
        "tools.visual.postprocess_rename.requests.get"
    ) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "test_id_003": {
                "prompt": [
                    None,
                    None,
                    {
                        "4": {
                            "class_type": "CLIPTextEncode",
                            "inputs": {"text": "random unrelated prompt"},
                        }
                    },
                ],
                "outputs": {
                    "10": {"images": [{"filename": "x.png"}]}
                },
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = parse_history_for_files()
        assert result == []


def test_parse_history_skips_unmatched_pose() -> None:
    """POSES에 X 매치 시 pose_idx=-1 본격."""
    with patch(
        "tools.visual.postprocess_rename.requests.get"
    ) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "test_id_004": {
                "prompt": [
                    None,
                    None,
                    {
                        "4": {
                            "class_type": "CLIPTextEncode",
                            "inputs": {
                                "text": (
                                    "barbarian warrior, "
                                    "totally custom pose X POSES"
                                ),
                            },
                        }
                    },
                ],
                "outputs": {
                    "10": {"images": [{"filename": "y.png"}]}
                },
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = parse_history_for_files()
        assert len(result) == 1
        assert result[0]["pose_idx"] == -1
