"""A2.1 — 원작 RAG 인덱스 빌드(오프라인 1회).

.local/canon/episodes/episode_*.txt(740화) → 토큰 청킹(~300 + overlap ~50, episode 번호 메타
보존) → bge-m3 임베딩(★ service.sim.rag_embed 공유 — 검색과 동일 경로) → .local/rag/ 에 저장:
  - embeddings.npy : float32 [N, 1024]
  - chunks.jsonl   : 줄당 {id, episode, chunk_idx, text}
  - meta.json      : {model, dim, count, chunk_tokens, overlap, embed_seconds}

★ 원작 파생물 — 산출물 전부 .local(git 금지). 신규 패키지 0(torch/transformers/numpy만).
모델 가중치도 .local/hf_cache(공개 MIT bge-m3, repo 밖). 실행: python -m tools.rag.build_index
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from service.sim.rag_embed import embed, get_tokenizer

_EPISODES_DIR = Path(".local/canon/episodes")
_OUT_DIR = Path(".local/rag")
_MODEL_NAME = "BAAI/bge-m3"
_CHUNK_TOKENS = 300
_OVERLAP_TOKENS = 50
_PROGRESS_EVERY = 1280  # 진행 출력 주기(청크)
_EP_RE = re.compile(r"episode_(\d+)\.txt$")


@dataclass(frozen=True)
class Chunk:
    """청크 1개 — 원작 텍스트 + episode 메타(검색 필터용)."""

    id: str
    episode: int
    chunk_idx: int
    text: str


def _episode_num(path: Path) -> int:
    m = _EP_RE.search(path.name)
    return int(m.group(1)) if m else -1


def chunk_episode(tokenizer: Any, episode: int, text: str) -> list[Chunk]:
    """한 화를 토큰 슬라이딩 윈도우(_CHUNK_TOKENS, overlap _OVERLAP_TOKENS)로 분할."""
    ids: list[int] = tokenizer.encode(text, add_special_tokens=False)
    if not ids:
        return []
    step = _CHUNK_TOKENS - _OVERLAP_TOKENS
    chunks: list[Chunk] = []
    for ci, start in enumerate(range(0, len(ids), step)):
        window = ids[start : start + _CHUNK_TOKENS]
        if not window:
            break
        piece = tokenizer.decode(window, skip_special_tokens=True).strip()
        if len(piece) >= 10:
            chunks.append(Chunk(f"ep{episode:04d}_{ci:03d}", episode, ci, piece))
        if start + _CHUNK_TOKENS >= len(ids):
            break
    return chunks


def main() -> None:
    # ★ A1.2b: 오프라인 툴 — app lifespan 밖이라 활성 콘텐츠팩을 직접 주입(rag_embed가 require).
    from service.content.worldfork import WORLDFORK_PACK
    from service.engine.content_pack import set_active_pack

    set_active_pack(WORLDFORK_PACK)
    if not _EPISODES_DIR.is_dir():
        print(f"원작 episodes 없음: {_EPISODES_DIR}", file=sys.stderr)
        sys.exit(1)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = get_tokenizer()
    episodes = sorted(_EPISODES_DIR.glob("episode_*.txt"), key=_episode_num)
    print(f"[build_index] 에피소드 {len(episodes)}개 청킹…", flush=True)
    all_chunks: list[Chunk] = []
    for path in episodes:
        ep = _episode_num(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        all_chunks.extend(chunk_episode(tokenizer, ep, text))
    print(f"[build_index] 청크 {len(all_chunks)}개 → 임베딩(rag_embed 공유)…", flush=True)

    t0 = time.time()
    vectors: list[np.ndarray] = []
    for i in range(0, len(all_chunks), _PROGRESS_EVERY):
        block = [c.text for c in all_chunks[i : i + _PROGRESS_EVERY]]
        vectors.append(embed(block))
        print(f"  임베딩 {min(i + _PROGRESS_EVERY, len(all_chunks))}/{len(all_chunks)}", flush=True)
    embeddings = np.vstack(vectors)
    elapsed = time.time() - t0

    np.save(_OUT_DIR / "embeddings.npy", embeddings)
    with (_OUT_DIR / "chunks.jsonl").open("w", encoding="utf-8") as fh:
        for c in all_chunks:
            fh.write(
                json.dumps(
                    {"id": c.id, "episode": c.episode, "chunk_idx": c.chunk_idx, "text": c.text},
                    ensure_ascii=False,
                )
                + "\n"
            )
    meta = {
        "model": _MODEL_NAME,
        "dim": int(embeddings.shape[1]),
        "count": int(embeddings.shape[0]),
        "chunk_tokens": _CHUNK_TOKENS,
        "overlap": _OVERLAP_TOKENS,
        "embed_seconds": round(elapsed, 1),
    }
    (_OUT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[build_index] 완료 — {meta}")


if __name__ == "__main__":
    main()
