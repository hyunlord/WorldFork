"""Canon facts pydantic schema (★ Phase C).

본 module 본:
- LLM extraction 산출물의 strict shape
- Phase D import (★ game state 본 entity hydrate) base
- Phase F retrieval (★ canon-aware RAG) 본 structured DB

source priority (★ retain conflict resolution):
  canon > inferred > wiki > dc > guess
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class CharacterRole(StrEnum):
    """I-E2 character role taxonomy (★ 6 categories)."""

    PROTAGONIST = "주인공"
    COMPANION = "동료"
    MAJOR_NPC = "주요 NPC"
    RESIDENT = "주민"
    EXTRA = "엑스트라"
    META = "메타"


class Source(StrEnum):
    """fact 출처."""

    CANON = "canon"        # 본문 직접 명시
    INFERRED = "inferred"  # 본문 강한 추론
    WIKI = "wiki"          # 나무위키
    DC = "dc"              # DC 게시판
    GUESS = "guess"        # 추측 (★ 본인 manual review 필요)


class Confidence(StrEnum):
    """fact 신뢰도."""

    HIGH = "high"      # 본문 직접 quote
    MEDIUM = "medium"  # 본문 추론 / wiki 1차 정합
    LOW = "low"        # DC / 추측


class Citation(BaseModel):
    """fact 본 출처 명시. extraction 시 항상 같이 기록."""

    source: Source
    confidence: Confidence
    ep_number: int | None = None
    wiki_page: str | None = Field(default=None, max_length=200)
    dc_post_id: str | None = Field(default=None, max_length=20)
    quote: str | None = Field(default=None, max_length=300)


class AbilityTier(StrEnum):
    """I-G1 ability 등급 (★ 본문 정합 — 상/중/하)."""

    HIGH = "상"
    MID = "중"
    LOW = "하"


class AbilityEntry(BaseModel):
    """I-G1 parsed ability 1개 — name + tier."""

    name: str = Field(..., max_length=100)
    tier: AbilityTier


class EssenceAbilities(BaseModel):
    """I-G1 essence abilities — text + parsed (★ 혼합 schema)."""

    text: str = Field(default="", max_length=2000)
    parsed: list[AbilityEntry] = Field(default_factory=list)


class Essence(BaseModel):
    """정수 fact (★ 본문 387 reference + 나무위키 '설정/정수')."""

    name: str = Field(..., max_length=100)
    grade: int | None = Field(default=None, ge=1, le=9)
    abilities: EssenceAbilities = Field(default_factory=EssenceAbilities)
    skills_granted: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    absorption_mechanism: str | None = Field(default=None, max_length=500)
    citations: list[Citation] = Field(default_factory=list)
    source_monster: str | None = Field(default=None, max_length=100)


class Character(BaseModel):
    """캐릭터 fact (★ 비요른 / 에르웬 / 미샤 / 아이나르 / 한스 / 등)."""

    name: str = Field(..., max_length=100)
    aliases: list[str] = Field(default_factory=list)
    role: str | None = Field(default=None, max_length=200)
    grade: int | None = Field(default=None, ge=1, le=9)
    race: str | None = Field(default=None, max_length=50)
    skills: list[str] = Field(default_factory=list)
    essences_absorbed: list[str] = Field(default_factory=list)
    background: str | None = Field(default=None, max_length=2000)
    relationships: dict[str, str] = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)


LocationType = Literal[
    "city",        # 도시 (★ 라스카니아 / 노아르크)
    "dungeon",     # 던전 (★ 미궁 본체 + sub_area)
    "rift",        # 균열 (★ 핏빛성채 / 빙하굴 / 강철의 묘 / 녹색탄광)
    "facility",    # 시설 (★ 길드 / 신전 / 거래소)
    "wilderness",  # 황야 / 야외
    "district",    # 구역 (★ 7구역)
]


class Location(BaseModel):
    """위치 fact."""

    name: str = Field(..., max_length=100)
    location_type: LocationType
    description: str | None = Field(default=None, max_length=2000)
    sub_locations: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class Race(BaseModel):
    """종족 fact (★ namuwiki '설정/종족')."""

    name: str = Field(..., max_length=80)
    description: str | None = Field(default=None, max_length=1500)
    abilities: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


MechanismCategory = Literal[
    "progression",  # 등급 / 성장
    "economy",      # 마석 / 거래
    "time",         # 174h / 미궁 시간
    "combat",       # 전투 mechanic
    "social",       # 길드 / 관계
    "magic",        # 마법 / 정수 흡수
    "skill",        # 스킬 / 능동/수동
]


class Mechanism(BaseModel):
    """본문 정합 mechanism (★ 등급 / 마석 / 174h / 정수 흡수 / 신성력)."""

    name: str = Field(..., max_length=100)
    category: MechanismCategory
    description: str = Field(..., max_length=2000)
    rules: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


ReviewStatus = Literal["draft", "reviewed", "final"]


class CanonFacts(BaseModel):
    """canon_facts.json root."""

    essences: list[Essence] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    races: list[Race] = Field(default_factory=list)
    mechanisms: list[Mechanism] = Field(default_factory=list)

    version: str = "1.0.0"
    last_updated: str = ""
    review_status: ReviewStatus = "draft"

    # 추출 source 별 entity count (★ canon=N, wiki=M, dc=K)
    source_stats: dict[str, int] = Field(default_factory=dict)


SOURCE_PRIORITY: dict[Source, int] = {
    Source.CANON: 4,
    Source.INFERRED: 3,
    Source.WIKI: 2,
    Source.DC: 1,
    Source.GUESS: 0,
}


def citation_priority(c: Citation) -> int:
    """source-based ordering — higher = stronger fact."""
    return SOURCE_PRIORITY[c.source]
