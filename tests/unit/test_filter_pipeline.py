"""Day 5: Filter Pipeline 단위 테스트."""

from core.eval.filter_pipeline import (
    STANDARD_FILTER_PIPELINE,
    FilterPipeline,
    FirstJsonObjectFilter,
    GBNFNativeFilter,
    MarkdownFenceFilter,
)


class TestGBNFNativeFilter:
    f = GBNFNativeFilter()

    def test_valid_json(self) -> None:
        r = self.f.apply('{"score": 90}', {})
        assert r.succeeded
        assert r.parsed == {"score": 90}
        assert r.filter_used == "gbnf_native"

    def test_invalid_json(self) -> None:
        r = self.f.apply("not json", {})
        assert not r.succeeded

    def test_array_not_object(self) -> None:
        r = self.f.apply("[1, 2, 3]", {})
        assert not r.succeeded


class TestMarkdownFenceFilter:
    f = MarkdownFenceFilter()

    def test_with_label(self) -> None:
        text = 'Here:\n```json\n{"score": 80}\n```'
        r = self.f.apply(text, {})
        assert r.succeeded
        assert r.parsed == {"score": 80}

    def test_without_label(self) -> None:
        text = 'Here:\n```\n{"x": 1}\n```'
        r = self.f.apply(text, {})
        assert r.succeeded
        assert r.parsed == {"x": 1}

    def test_no_fence(self) -> None:
        r = self.f.apply("plain text", {})
        assert not r.succeeded


class TestFirstJsonObjectFilter:
    f = FirstJsonObjectFilter()

    def test_simple(self) -> None:
        r = self.f.apply('Some text {"score": 70} more', {})
        assert r.succeeded
        assert r.parsed == {"score": 70}

    def test_nested(self) -> None:
        r = self.f.apply('text {"a": {"b": 1}} done', {})
        assert r.succeeded
        assert r.parsed == {"a": {"b": 1}}

    def test_no_object(self) -> None:
        r = self.f.apply("no braces", {})
        assert not r.succeeded


class TestFilterPipeline:
    def test_chain_native_first(self) -> None:
        r = STANDARD_FILTER_PIPELINE.extract('{"x": 1}')
        assert r.succeeded
        assert r.filter_used == "gbnf_native"

    def test_chain_falls_to_markdown(self) -> None:
        text = 'preamble\n```json\n{"x": 2}\n```'
        r = STANDARD_FILTER_PIPELINE.extract(text)
        assert r.succeeded
        assert r.filter_used == "markdown_fence"

    def test_chain_falls_to_first_object(self) -> None:
        r = STANDARD_FILTER_PIPELINE.extract('Result: {"x": 3} END')
        assert r.succeeded
        assert r.filter_used == "first_json_object"

    def test_chain_all_fail(self) -> None:
        r = STANDARD_FILTER_PIPELINE.extract("no JSON anywhere")
        assert not r.succeeded
        assert "All filters failed" in (r.error or "")

    def test_custom_pipeline(self) -> None:
        p = FilterPipeline(filters=[GBNFNativeFilter()])
        r = p.extract('{"ok": true}')
        assert r.succeeded
