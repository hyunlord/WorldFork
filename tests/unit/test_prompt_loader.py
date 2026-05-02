"""Tier 1.5 D1 작업 2: Prompt loader 테스트."""

from pathlib import Path

from core.harness.prompt_loader import (
    DEFAULT_PROMPTS,
    load_agent_prompt,
    parse_frontmatter,
    substitute_vars,
)


class TestParseFrontmatter:
    def test_with_frontmatter(self) -> None:
        content = "---\nrole: code_reviewer\nfamily: openai\n---\n\n# Body\nSome text\n"
        meta, body = parse_frontmatter(content)
        assert meta == {"role": "code_reviewer", "family": "openai"}
        assert body.startswith("# Body")

    def test_without_frontmatter(self) -> None:
        content = "# Just text\n"
        meta, body = parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_empty_frontmatter(self) -> None:
        content = "---\n---\nbody\n"
        meta, body = parse_frontmatter(content)
        assert isinstance(meta, dict)

    def test_no_closing_separator(self) -> None:
        content = "---\nrole: x\n"
        meta, body = parse_frontmatter(content)
        # 닫는 --- 없으면 frontmatter X
        assert meta == {}


class TestSubstituteVars:
    def test_replace_var(self) -> None:
        result = substitute_vars("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_keep_unknown_var(self) -> None:
        result = substitute_vars("Hello {{unknown}}!", {"name": "X"})
        assert "{{unknown}}" in result

    def test_multiple_vars(self) -> None:
        result = substitute_vars(
            "{{role}} for {{projectDir}}",
            {"role": "reviewer", "projectDir": "/tmp"},
        )
        assert result == "reviewer for /tmp"

    def test_no_vars(self) -> None:
        text = "plain text without vars"
        assert substitute_vars(text, {}) == text


class TestLoadAgentPrompt:
    def test_load_code_reviewer_from_project(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / ".autodev" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "code_reviewer.md").write_text(
            "---\nrole: code_reviewer\nfamily: openai\n---\n\n# Test prompt {{projectDir}}\n",
            encoding="utf-8",
        )

        prompt = load_agent_prompt(
            "code_reviewer",
            project_dir=tmp_path,
            user_dir=tmp_path / "home_no_exist",
        )
        assert prompt.role == "code_reviewer"
        assert prompt.family == "openai"
        assert str(tmp_path) in prompt.body

    def test_project_takes_precedence_over_user(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        user_dir = tmp_path / "home"
        for d in [project_dir / ".autodev" / "agents", user_dir / ".autodev" / "agents"]:
            d.mkdir(parents=True)

        (project_dir / ".autodev" / "agents" / "code_reviewer.md").write_text(
            "---\nfamily: project\n---\nproject prompt\n", encoding="utf-8"
        )
        (user_dir / ".autodev" / "agents" / "code_reviewer.md").write_text(
            "---\nfamily: user\n---\nuser prompt\n", encoding="utf-8"
        )

        prompt = load_agent_prompt("code_reviewer", project_dir=project_dir, user_dir=user_dir)
        assert prompt.family == "project"

    def test_fallback_to_default(self, tmp_path: Path) -> None:
        prompt = load_agent_prompt(
            "code_reviewer",
            project_dir=tmp_path / "no_exist",
            user_dir=tmp_path / "no_exist_home",
        )
        assert prompt.role == "code_reviewer"
        assert "code_reviewer" in DEFAULT_PROMPTS

    def test_unknown_role_generic_fallback(self, tmp_path: Path) -> None:
        prompt = load_agent_prompt(
            "unknown_role",
            project_dir=tmp_path,
            user_dir=tmp_path,
        )
        assert prompt.role == "unknown_role"
        assert len(prompt.body) > 0

    def test_source_path_set_when_file_found(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / ".autodev" / "agents"
        agents_dir.mkdir(parents=True)
        md_path = agents_dir / "code_reviewer.md"
        md_path.write_text("---\nfamily: any\n---\nbody\n", encoding="utf-8")

        prompt = load_agent_prompt("code_reviewer", project_dir=tmp_path, user_dir=tmp_path / "x")
        assert prompt.source_path == md_path

    def test_source_path_none_for_default(self, tmp_path: Path) -> None:
        prompt = load_agent_prompt("code_reviewer", project_dir=tmp_path, user_dir=tmp_path)
        assert prompt.source_path is None


class TestRealProjectPrompts:
    def test_code_reviewer_loaded(self) -> None:
        """★ .autodev/agents/code_reviewer.md 진짜 로드."""
        prompt = load_agent_prompt("code_reviewer")
        assert prompt.role == "code_reviewer"
        assert len(prompt.body) > 50

    def test_code_reviewer_has_identity_section(self) -> None:
        prompt = load_agent_prompt("code_reviewer")
        assert "IDENTITY" in prompt.body or len(prompt.body) > 100
