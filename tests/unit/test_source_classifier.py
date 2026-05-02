"""W2 D3 작업 1: Source Classifier 테스트."""

from service.pipeline.source_classifier import (
    classify_sources,
    filter_high_confidence,
)
from service.search.adapter import SearchBundle, SearchResult


def _make_result(
    classification: str = "unknown",
    confidence: float = 1.0,
) -> SearchResult:
    return SearchResult(
        source="wiki", url="x", title="t", snippet="s",
        classification=classification,  # type: ignore[arg-type]
        confidence=confidence,
    )


class TestClassifySources:
    def test_empty_bundle(self) -> None:
        bundle = SearchBundle(query="x", results=[])
        c = classify_sources(bundle)
        assert c.total == 0

    def test_official_results(self) -> None:
        bundle = SearchBundle(query="x", results=[
            _make_result(classification="official"),
            _make_result(classification="official"),
        ])
        c = classify_sources(bundle)
        assert len(c.official) == 2
        assert c.total == 2

    def test_mixed_classifications(self) -> None:
        bundle = SearchBundle(query="x", results=[
            _make_result(classification="official"),
            _make_result(classification="fan_interpretation"),
            _make_result(classification="fanfic"),
            _make_result(classification="unknown"),
        ])
        c = classify_sources(bundle)
        assert len(c.official) == 1
        assert len(c.fan_interpretation) == 1
        assert len(c.fanfic) == 1
        assert len(c.unknown) == 1

    def test_summary_format(self) -> None:
        bundle = SearchBundle(query="x", results=[
            _make_result(classification="official"),
            _make_result(classification="fan_interpretation"),
        ])
        c = classify_sources(bundle)
        s = c.summary()
        assert "official:1" in s
        assert "fan_interpretation:1" in s


class TestFilterHighConfidence:
    def test_filter_below_threshold(self) -> None:
        bundle = SearchBundle(query="x", results=[
            _make_result(classification="official", confidence=0.95),
            _make_result(classification="official", confidence=0.5),
            _make_result(classification="fan_interpretation", confidence=0.8),
        ])
        c = classify_sources(bundle)
        high = filter_high_confidence(c, min_confidence=0.7)
        assert len(high.official) == 1  # 0.5 제외
        assert len(high.fan_interpretation) == 1

    def test_priority_order_in_all_sources(self) -> None:
        bundle = SearchBundle(query="x", results=[
            _make_result(classification="fanfic"),
            _make_result(classification="official"),
            _make_result(classification="fan_interpretation"),
        ])
        c = classify_sources(bundle)
        # all_sources는 우선순위 (공식 → 해석 → 팬픽 → 미상)
        all_results = c.all_sources()
        assert all_results[0].classification == "official"
        assert all_results[-1].classification in ("fanfic", "unknown")
