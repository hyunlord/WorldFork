"""W2 D1 작업 4-6: Web search 어댑터 테스트."""

import pytest

from service.search.adapter import SearchBundle, SearchQuery, SearchResult
from service.search.anthropic_websearch import AnthropicWebSearchAdapter
from service.search.mock_adapter import MOCK_DB, MockWebSearchAdapter


class TestMockWebSearch:
    def test_known_work(self) -> None:
        adapter = MockWebSearchAdapter()
        result = adapter.search(SearchQuery(query="novice_dungeon_run"))
        assert isinstance(result, SearchBundle)
        assert len(result.results) >= 2

    def test_unknown_work_returns_empty(self) -> None:
        adapter = MockWebSearchAdapter()
        result = adapter.search(SearchQuery(query="absolutely_not_in_db"))
        assert len(result.results) == 0

    def test_source_filter(self) -> None:
        adapter = MockWebSearchAdapter()
        result = adapter.search(SearchQuery(query="novice_dungeon_run", sources=["wiki"]))
        for r in result.results:
            assert r.source == "wiki"

    def test_max_per_source(self) -> None:
        adapter = MockWebSearchAdapter()
        result = adapter.search(
            SearchQuery(
                query="novice_dungeon_run",
                sources=["wiki", "namuwiki", "fan_community"],
                max_per_source=1,
            )
        )
        by_source: dict[str, int] = {}
        for r in result.results:
            by_source[r.source] = by_source.get(r.source, 0) + 1
        for src, count in by_source.items():
            assert count <= 1, f"{src}: {count} > 1"

    def test_filter_by_classification(self) -> None:
        adapter = MockWebSearchAdapter()
        result = adapter.search(SearchQuery(query="novice_dungeon_run"))
        official = result.filter_by_classification("official")
        assert len(official) >= 1

    def test_is_available(self) -> None:
        assert MockWebSearchAdapter().is_available() is True

    def test_cost_zero(self) -> None:
        adapter = MockWebSearchAdapter()
        result = adapter.search(SearchQuery(query="novice_dungeon_run"))
        assert result.cost_usd == 0.0


class TestAnthropicWebSearch:
    def test_skeleton_not_available(self) -> None:
        assert AnthropicWebSearchAdapter().is_available() is False

    def test_skeleton_raises(self) -> None:
        adapter = AnthropicWebSearchAdapter()
        with pytest.raises(NotImplementedError, match="skeleton"):
            adapter.search(SearchQuery(query="any"))


class TestCustomMockDB:
    def test_inject_custom_db(self) -> None:
        custom: dict[str, list[SearchResult]] = {
            "test_work": [
                SearchResult(
                    source="wiki",
                    url="x",
                    title="Test",
                    snippet="Test work",
                    classification="official",
                ),
            ]
        }
        adapter = MockWebSearchAdapter(custom_db=custom)
        result = adapter.search(SearchQuery(query="test_work"))
        assert len(result.results) == 1
        assert result.results[0].title == "Test"

    def test_mock_db_not_empty(self) -> None:
        assert len(MOCK_DB) > 0
        assert "novice_dungeon_run" in MOCK_DB
