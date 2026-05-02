"""3-tier 프롬프트 로딩 (★ 자료 LAYER1 + 본인 자료 정합).

우선순위:
  1. {projectDir}/.autodev/agents/{role}.md
  2. ~/.autodev/agents/{role}.md (전역)
  3. DEFAULT_{ROLE}_PROMPT 상수 (코드 내)

YAML frontmatter 지원: ---role: x---
템플릿 변수: {{projectDir}}, {{role}} 치환
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class AgentPrompt:
    """로드된 agent prompt."""

    role: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None

    @property
    def family(self) -> str:
        return str(self.metadata.get("family", "any"))


# Default prompts (3순위 fallback)
DEFAULT_PROMPTS: dict[str, str] = {
    "code_reviewer": """\
# IDENTITY
You are a code reviewer.

# TASK
Review the git diff. Output JSON: {"score": 0-25, "verdict": "pass|warn|fail", "issues": [...]}
""",
}


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """YAML frontmatter 파싱.

    Returns:
        (metadata, body)
    """
    if not content.startswith("---\n"):
        return {}, content

    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return {}, content

    try:
        metadata = yaml.safe_load(parts[1]) or {}
        if not isinstance(metadata, dict):
            return {}, content
    except yaml.YAMLError:
        return {}, content

    body = parts[2].lstrip("\n")
    return metadata, body


def substitute_vars(text: str, variables: dict[str, str]) -> str:
    """{{var}} 템플릿 치환."""

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1).strip()
        return variables.get(var_name, match.group(0))

    return re.sub(r"\{\{(\w+)\}\}", replace, text)


def load_agent_prompt(
    role: str,
    project_dir: Path | None = None,
    user_dir: Path | None = None,
) -> AgentPrompt:
    """3-tier 우선순위로 prompt 로드.

    Args:
        role: "code_reviewer" / "coder" / "planner" 등
        project_dir: 프로젝트 .autodev/agents/ (default: REPO_ROOT)
        user_dir: 전역 ~/.autodev/agents/ (default: ~)
    """
    project_dir = project_dir or REPO_ROOT
    user_dir = user_dir or Path.home()

    candidates = [
        project_dir / ".autodev" / "agents" / f"{role}.md",
        user_dir / ".autodev" / "agents" / f"{role}.md",
    ]

    template_vars = {
        "projectDir": str(project_dir),
        "role": role,
    }

    for path in candidates:
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8")
            metadata, body = parse_frontmatter(content)
            body = substitute_vars(body, template_vars)

            return AgentPrompt(
                role=role,
                body=body,
                metadata=metadata,
                source_path=path,
            )
        except OSError:
            continue

    # Fallback: default
    default = DEFAULT_PROMPTS.get(role, f"# {role}\n\nNo prompt defined.\n")
    return AgentPrompt(
        role=role,
        body=substitute_vars(default, template_vars),
        metadata={"source": "default"},
    )
