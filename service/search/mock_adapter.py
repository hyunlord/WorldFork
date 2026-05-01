"""Mock WebSearchAdapter (★ Tier 1-2 본격 호출 X).

용도:
  - 테스트
  - Tier 1 W2-3 개발 시 (실제 호출 X)
  - 본인 1회 풀 플레이 (Mock으로 시뮬)

★ 외부 패키지 0건.
"""

from .adapter import SearchBundle, SearchQuery, SearchResult, WebSearchAdapter

MOCK_DB: dict[str, list[SearchResult]] = {
    "novice_dungeon_run": [
        SearchResult(
            source="wiki",
            url="https://example.com/novice_dungeon_run",
            title="신참 던전 모험 시리즈",
            snippet=(
                "주인공 투르윈이 신참 모험가로 시작하여 던전을 탐험하는 "
                "판타지 모험 시리즈. 인기 웹소설."
            ),
            classification="official",
            confidence=0.95,
        ),
        SearchResult(
            source="namuwiki",
            url="https://example.com/wiki/투르윈",
            title="투르윈 (캐릭터)",
            snippet=(
                "신참 던전 모험 시리즈의 주인공. 처음에는 약했지만 "
                "점점 강해지는 캐릭터 성장 서사."
            ),
            classification="official",
            confidence=0.9,
        ),
        SearchResult(
            source="fan_community",
            url="https://example.com/fan/dungeon",
            title="신참 던전 팬덤 분석",
            snippet="팬들 사이에서 인기 있는 캐릭터는 투르윈의 멘토 캐릭터...",
            classification="fan_interpretation",
            confidence=0.6,
        ),
    ],
    "test_unknown_work": [],
}


class MockWebSearchAdapter(WebSearchAdapter):
    """미리 정의된 mock 데이터 반환."""

    def __init__(
        self, custom_db: dict[str, list[SearchResult]] | None = None
    ) -> None:
        self._db = custom_db if custom_db is not None else MOCK_DB

    def search(self, query: SearchQuery) -> SearchBundle:
        normalized = query.query.lower().strip()
        results = self._db.get(normalized, [])

        filtered = [r for r in results if r.source in query.sources]

        by_source: dict[str, list[SearchResult]] = {}
        for r in filtered:
            by_source.setdefault(r.source, []).append(r)

        final: list[SearchResult] = []
        for src_results in by_source.values():
            final.extend(src_results[: query.max_per_source])

        return SearchBundle(query=query.query, results=final, cost_usd=0.0)

    def is_available(self) -> bool:
        return True
