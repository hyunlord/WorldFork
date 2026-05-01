"""Web search 어댑터 인터페이스 (★ 자료 HARNESS_LAYER2 2.2 Stage 2).

원칙:
  1. Abstract 인터페이스 정의 (어댑터 패턴)
  2. Mock 구현 우선 (Tier 1-2 본격 호출 X)
  3. 실제 구현은 Tier 2+ (W3 베타 이후)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SearchResult:
    """단일 검색 결과."""

    source: str
    url: str
    title: str
    snippet: str
    classification: Literal[
        "official", "fan_interpretation", "fanfic", "unknown"
    ] = "unknown"
    confidence: float = 1.0


@dataclass
class SearchQuery:
    """검색 요청."""

    query: str
    sources: list[str] = field(default_factory=lambda: ["wiki", "namuwiki"])
    max_per_source: int = 5
    parallel: bool = True


@dataclass
class SearchBundle:
    """병렬 검색 결과 묶음."""

    query: str
    results: list[SearchResult]
    cost_usd: float = 0.0
    error: str | None = None

    def filter_by_source(self, source: str) -> list[SearchResult]:
        return [r for r in self.results if r.source == source]

    def filter_by_classification(self, classification: str) -> list[SearchResult]:
        return [r for r in self.results if r.classification == classification]


class WebSearchAdapter(ABC):
    """Web search 어댑터 인터페이스."""

    @abstractmethod
    def search(self, query: SearchQuery) -> SearchBundle:
        """단일 / 병렬 검색."""

    @abstractmethod
    def is_available(self) -> bool:
        """어댑터 사용 가능?"""
