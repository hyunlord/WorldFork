"""A2.2 — 런타임 RAG 검색.

장면 컨텍스트 → bge-m3 쿼리 임베딩(rag_embed 공유) → numpy cosine top-k → episode 범위 필터
→ ★ 주입·로그 전 마스킹(mask_text) → 변환명 passages. A2.3 GM 주입이 get_grounding을 호출.

★ IP: 인덱스(.local/rag)는 원작명을 담지만, 반환·로그는 mask_text로 변환명만(원작명 git/로그 0).
신규 패키지 0(numpy + rag_embed). 인덱스는 lazy 로드(메모리·지연 관리).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from service.pipeline.ip_masking import mask_text
from service.sim.rag_embed import embed

_RAG_DIR = Path(".local/rag")
# 오프닝 기본 episode 범위(후반 스포일러 차단). 호출자가 override.
_OPENING_RANGE = (1, 20)
_TOP_K = 4


@dataclass(frozen=True)
class Passage:
    """검색된 원작 대목 — ★ text는 마스킹된 변환명(원작명 누출 0)."""

    episode: int
    text: str
    score: float


_index: dict[str, Any] = {}


def _load_index() -> tuple[np.ndarray, list[dict[str, Any]], np.ndarray]:
    """lazy 인덱스 로드 — (embeddings [N,1024], chunks, episode 배열). 싱글톤."""
    if not _index:
        emb = np.load(_RAG_DIR / "embeddings.npy")
        chunks: list[dict[str, Any]] = []
        with (_RAG_DIR / "chunks.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                chunks.append(json.loads(line))
        episodes = np.array([int(c["episode"]) for c in chunks], dtype=np.int64)
        _index.update(emb=emb, chunks=chunks, episodes=episodes)
    return _index["emb"], _index["chunks"], _index["episodes"]


def index_available() -> bool:
    """인덱스 산출물 존재 여부(서빙/CI에서 RAG 가용성 게이트용)."""
    return (_RAG_DIR / "embeddings.npy").exists() and (_RAG_DIR / "chunks.jsonl").exists()


def get_grounding(
    scene_context: str,
    *,
    episode_range: tuple[int, int] = _OPENING_RANGE,
    top_k: int = _TOP_K,
) -> list[Passage]:
    """장면 컨텍스트 → 관련 원작 passages(마스킹). cosine top-k + episode 범위 필터.

    scene_context: 위치·등장인물·사건·플레이어 행동 등을 합친 검색 쿼리 문자열.
    반환 text는 mask_text 적용 후(변환명) — 호출부·로그·git엔 원작명이 들어가지 않는다.
    """
    if not index_available():
        return []
    emb, chunks, episodes = _load_index()
    query = embed([scene_context])[0]  # [1024], L2 정규화됨
    sims = emb @ query  # 둘 다 정규화 → cosine 유사도
    lo, hi = episode_range
    in_range = (episodes >= lo) & (episodes <= hi)
    sims = np.where(in_range, sims, -1.0)  # 범위 밖 제외
    order = np.argsort(-sims)[:top_k]
    out: list[Passage] = []
    for i in order:
        score = float(sims[int(i)])
        if score < 0:
            break  # 범위 내 후보 소진
        chunk = chunks[int(i)]
        masked = mask_text(str(chunk["text"])).masked  # ★ 마스킹(변환명)
        out.append(Passage(episode=int(chunk["episode"]), text=masked, score=score))
    return out
