"""AI Playtester Persona 데이터 모델 + 로딩.

AI_PLAYTESTER 2.1 YAML 스키마 따름.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

PERSONAS_DIR = Path(__file__).resolve().parents[2] / "personas"


@dataclass
class PersonaBehavior:
    """페르소나 행동 패턴."""

    response_length: Literal["short", "medium", "long"] = "medium"
    pace: Literal["slow", "medium", "fast"] = "medium"
    patience: Literal["low", "medium", "high"] = "medium"
    exploration: Literal["shallow", "medium", "deep"] = "medium"


@dataclass
class PersonaPreferences:
    """페르소나 선호도."""

    fun_factor: str = "medium"
    story_depth: str = "medium"
    challenge: str = "medium"
    social: str = "medium"
    combat: str = "medium"


@dataclass
class Persona:
    """AI Playtester 페르소나."""

    id: str
    version: int
    language: str
    status: Literal["active", "experimental", "deprecated"]
    demographic: str
    behavior: PersonaBehavior
    preferences: PersonaPreferences
    expected_findings: list[str]
    cli_to_use: str
    backup_cli: str | None
    forbidden_game_llms: list[str]
    prompt_template: str
    output_schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_text: str) -> "Persona":
        data = yaml.safe_load(yaml_text)

        beh_dict = data.get("behavior", {})
        behavior = PersonaBehavior(
            response_length=beh_dict.get("response_length", "medium"),
            pace=beh_dict.get("pace", "medium"),
            patience=beh_dict.get("patience", "medium"),
            exploration=beh_dict.get("exploration", "medium"),
        )

        pref_dict = data.get("preferences", {})
        preferences = PersonaPreferences(
            fun_factor=pref_dict.get("fun_factor", "medium"),
            story_depth=pref_dict.get("story_depth", "medium"),
            challenge=pref_dict.get("challenge", "medium"),
            social=pref_dict.get("social", "medium"),
            combat=pref_dict.get("combat", "medium"),
        )

        return cls(
            id=data["id"],
            version=int(data.get("version", 1)),
            language=data.get("language", "ko"),
            status=data.get("status", "active"),
            demographic=data.get("demographic", ""),
            behavior=behavior,
            preferences=preferences,
            expected_findings=list(data.get("expected_findings", [])),
            cli_to_use=data["cli_to_use"],
            backup_cli=data.get("backup_cli"),
            forbidden_game_llms=list(data.get("forbidden_game_llms", [])),
            prompt_template=data.get("prompt_template", ""),
            output_schema=data.get("output_schema", {}),
        )


def load_persona(persona_id: str, tier: str = "tier_0") -> Persona:
    """personas/{tier}/{persona_id}.yaml 로드."""
    path = PERSONAS_DIR / tier / f"{persona_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Persona not found: {path}")
    return Persona.from_yaml(path.read_text(encoding="utf-8"))


def list_personas(tier: str = "tier_0") -> list[str]:
    """tier 디렉토리의 persona ID 목록."""
    tier_dir = PERSONAS_DIR / tier
    if not tier_dir.exists():
        return []
    return sorted([
        f.stem for f in tier_dir.glob("*.yaml")
        if not f.stem.startswith(".")
    ])


def is_compatible(persona: Persona, game_llm_key: str) -> bool:
    """페르소나가 이 game LLM과 호환되는가."""
    return game_llm_key not in persona.forbidden_game_llms
