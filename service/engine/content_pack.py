"""ContentPack — 엔진이 소비하는 작품 데이터 인터페이스(A1 콘텐츠팩 분리).

★ YAGNI: frozen 데이터 묶음 + 영역별 sub-spec뿐. 동적 로더·플러그인·SDK 없음.
타입(메커니즘)은 엔진에 두고, 팩(service/content/<work>/)이 이 타입으로 데이터를 조립한다.
엔진 모듈은 require_active_pack() 싱글톤으로만 소비한다. 단방향: 팩→엔진 타입.

★ 모든 필드는 실소비처를 가진다(미소비 필드 0 — made-but-never-used 회피). 소비처가 생기는
단계(A1.2b: 캐논 인덱스·RAG·IP)에 맞춰 필드를 추가한다. 싱글톤은 canon/context.py 컨벤션.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from service.sim.disposition import Disposition

if TYPE_CHECKING:
    # 캐논 타입(메커니즘)은 엔진(opening_canon) 소유 — 데이터만 팩에. 런타임 미import(순환 회피).
    from service.sim.opening_canon import Beat, BeatAnchor, BeatChoice, SceneDetail, WeaponChoice


@dataclass(frozen=True)
class FoeSpec:
    """첫 조우 적 스폰 사양 — gm_session_router의 Foe(...) 생성 인자."""

    name: str
    hp: int
    attack: int
    essence_drop: str


@dataclass(frozen=True)
class CompanionSpec:
    """동행 동료 사양 — Companion(name, disposition, hp, attack) 생성 인자."""

    name: str
    disposition: Disposition
    hp: int
    attack: int


@dataclass(frozen=True)
class RagConfig:
    """RAG 원작 인덱스 설정 — rag_retrieval/rag_embed가 쓰는 경로·모델·기본 범위."""

    index_dir: str
    cache_dir: str
    model_name: str
    episode_range: tuple[int, int]
    top_k: int


@dataclass(frozen=True)
class ContentPack:
    """작품 콘텐츠팩 — 엔진이 소비하는 작품별 데이터(작품 무관 메커니즘은 엔진 소유).

    현 소비처: narrative_gm(gm_system_persona·illustration_keys·grounding_*),
    gm_session_router(first_foe·companion). 캐논 인덱스·RAG·IP는 A1.2b에서 소비처와 함께 추가.
    """

    pack_id: str
    # 세계·톤 (GM 시스템 프롬프트 — 현재 페르소나+출력계약 블렌드, 바이트 보존 위해 통째)
    gm_system_persona: str
    # 캐릭터·전투
    first_foe: FoeSpec
    companion: CompanionSpec
    # RAG grounding 캡 (narrative_gm._grounding_block)
    grounding_episode_range: tuple[int, int]
    grounding_top_k: int
    grounding_char_budget: int
    # 비주얼 (narrative_gm GM 출력 일러스트 화이트리스트)
    illustration_keys: frozenset[str]
    # RAG 원작 인덱스 (rag_retrieval/rag_embed)
    rag: RagConfig
    rag_chapter_header_pattern: str  # narrative_gm._clean_passage — 작품 회차 헤더 제거 정규식
    # IP 마스킹 (ip_masking — 원작명→변환명). 코드·git=변환명 규율의 데이터 소유.
    ip_replacements: dict[str, str]
    ip_keywords: tuple[str, ...]
    ip_fallback_name: str
    # 캐논 인덱스 (opening_canon 로직이 소비 — 데이터만 팩 소유)
    beats: tuple[Beat, ...]
    anchors: dict[Beat, BeatAnchor]
    scene_details: dict[Beat, tuple[SceneDetail, ...]]
    weapons: tuple[WeaponChoice, ...]
    weapon_aliases: tuple[tuple[str, str], ...]  # 자유 텍스트 무기 약칭(부분어→무기 label)
    beat_choices: dict[Beat, tuple[BeatChoice, ...]]  # 성인식은 weapons에서 동적 생성
    beat_thresholds: dict[Beat, int]  # scene_effect/_beat_done — progress 끌개 임계
    pull_flavors: tuple[str, str, str]  # pull_flavor 견인 텍스트(low/mid/high)
    companion_present_beats: frozenset[Beat]  # kaira_present
    player_name: str
    player_brief: str  # build_anchor_prompt [주인공] 설명
    companion_brief: str  # build_anchor_prompt [동료] 설명
    first_foe_names: tuple[str, ...]
    first_foe_desc: str  # build_anchor_prompt [적] 설명


# ─── active 싱글톤 (canon/context.py 컨벤션 — app.py lifespan이 set) ────────────────
_active_pack: ContentPack | None = None


def get_active_pack() -> ContentPack | None:
    """현재 활성 콘텐츠팩(미설정이면 None)."""
    return _active_pack


def require_active_pack() -> ContentPack:
    """활성 콘텐츠팩(필수) — 엔진 소비처가 쓴다. 미설정이면 명확한 오류(배선 누락 조기 발견).

    프로덕션은 app.py lifespan, 테스트는 tests/conftest.py 오토유즈 픽스처가 설정한다.
    """
    if _active_pack is None:
        raise RuntimeError(
            "활성 콘텐츠팩 미설정 — app lifespan 또는 테스트 픽스처의 set_active_pack 필요"
        )
    return _active_pack


def set_active_pack(pack: ContentPack) -> None:
    """활성 콘텐츠팩 설정(app.py lifespan에서 1회). 동적 디스커버리 없음 — 명시 주입."""
    global _active_pack
    _active_pack = pack


def clear_active_pack() -> None:
    """활성 콘텐츠팩 해제(테스트·종료용)."""
    global _active_pack
    _active_pack = None
