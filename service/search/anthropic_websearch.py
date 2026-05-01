"""Anthropic SDK web_search 어댑터 (★ skeleton, Tier 2+ 본격 사용).

이유 (★ 본인 인사이트 #14):
  - Tier 1-2는 Mock으로 충분
  - 실제 API 호출은 게임 성숙 후 (W3 베타)
  - 비용 / debugging 어려움 회피
"""

from .adapter import SearchBundle, SearchQuery, WebSearchAdapter


class AnthropicWebSearchAdapter(WebSearchAdapter):
    """Anthropic API web_search 어댑터.

    ★ Skeleton — Tier 2+에서 본격 구현.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        # ★ Tier 2+: from anthropic import Anthropic; self._client = Anthropic(...)

    def search(self, query: SearchQuery) -> SearchBundle:
        raise NotImplementedError(
            "AnthropicWebSearchAdapter is skeleton in Tier 1. "
            "Use MockWebSearchAdapter instead. "
            "See HARNESS_LAYER2_SERVICE.md Stage 2."
        )

    def is_available(self) -> bool:
        return False
