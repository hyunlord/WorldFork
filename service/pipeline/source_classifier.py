"""Search 결과 분류 (★ 자료 2.2 Stage 2 step 2).

자료:
  classified = classify_sources(search_results)
  → 공식 / 팬 해석 / 팬픽 분류
"""

from dataclasses import dataclass, field

from service.search.adapter import SearchBundle, SearchResult


@dataclass
class ClassifiedSources:
    """분류된 검색 결과 묶음."""

    official: list[SearchResult] = field(default_factory=list)
    fan_interpretation: list[SearchResult] = field(default_factory=list)
    fanfic: list[SearchResult] = field(default_factory=list)
    unknown: list[SearchResult] = field(default_factory=list)

    def summary(self) -> str:
        """통계 요약."""
        parts = [
            f"official:{len(self.official)}",
            f"fan_interpretation:{len(self.fan_interpretation)}",
            f"fanfic:{len(self.fanfic)}",
            f"unknown:{len(self.unknown)}",
        ]
        return " ".join(parts)

    @property
    def total(self) -> int:
        return (
            len(self.official) + len(self.fan_interpretation)
            + len(self.fanfic) + len(self.unknown)
        )

    def all_sources(self) -> list[SearchResult]:
        """우선순위 (공식 → 팬 해석 → 팬픽 → 미상)."""
        return [
            *self.official,
            *self.fan_interpretation,
            *self.fanfic,
            *self.unknown,
        ]


def classify_sources(bundle: SearchBundle) -> ClassifiedSources:
    """Search 결과를 공식 / 팬 해석 / 팬픽 / 미상으로 분류.

    SearchResult.classification 필드 활용 (★ W2 D1 작성).
    """
    classified = ClassifiedSources()
    for result in bundle.results:
        cls = result.classification
        if cls == "official":
            classified.official.append(result)
        elif cls == "fan_interpretation":
            classified.fan_interpretation.append(result)
        elif cls == "fanfic":
            classified.fanfic.append(result)
        else:
            classified.unknown.append(result)
    return classified


def filter_high_confidence(
    classified: ClassifiedSources,
    min_confidence: float = 0.7,
) -> ClassifiedSources:
    """신뢰도 기준 필터링 (★ Plan 생성 시 사용)."""
    return ClassifiedSources(
        official=[r for r in classified.official if r.confidence >= min_confidence],
        fan_interpretation=[
            r for r in classified.fan_interpretation if r.confidence >= min_confidence
        ],
        fanfic=[r for r in classified.fanfic if r.confidence >= min_confidence],
        unknown=[r for r in classified.unknown if r.confidence >= min_confidence],
    )
