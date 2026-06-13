"""A2.1 — 원작 RAG 인덱스 빌드(오프라인 1회).

.local/canon/episodes/episode_*.txt(740화) → 토큰 청킹(~300 + overlap ~50, episode 번호 메타
보존) → bge-m3 임베딩(transformers, CLS pooling + L2 정규화) → .local/rag/ 에 저장:
  - embeddings.npy : float32 [N, 1024]
  - chunks.jsonl   : 줄당 {id, episode, chunk_idx, text}
  - meta.json      : {model, dim, count, chunk_tokens, overlap, built_at_unix}

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
import torch
from transformers import AutoModel, AutoTokenizer

_EPISODES_DIR = Path(".local/canon/episodes")
_OUT_DIR = Path(".local/rag")
_MODEL_NAME = "BAAI/bge-m3"
_CACHE_DIR = Path(".local/hf_cache")
_CHUNK_TOKENS = 300
_OVERLAP_TOKENS = 50
_MAX_LEN = 512  # bge-m3 dense 인코딩 길이
_BATCH = 64
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


def chunk_episode(
    tokenizer: Any, episode: int, text: str
) -> list[Chunk]:
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
        if len(piece) < 10:
            continue
        chunks.append(Chunk(f"ep{episode:04d}_{ci:03d}", episode, ci, piece))
        if start + _CHUNK_TOKENS >= len(ids):
            break
    return chunks


def embed_texts(
    model: Any, tokenizer: Any, texts: list[str], device: torch.device
) -> np.ndarray:
    """bge-m3 dense 임베딩 — CLS 토큰 + L2 정규화(GPU는 bf16 autocast). float32 [N, 1024]."""
    out: list[np.ndarray] = []
    use_cuda = device.type == "cuda"
    total = len(texts)
    for i in range(0, total, _BATCH):
        batch = texts[i : i + _BATCH]
        enc = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=_MAX_LEN,
            return_tensors="pt",
        ).to(device)
        autocast = torch.autocast(
            device_type="cuda", dtype=torch.bfloat16, enabled=use_cuda
        )
        with torch.no_grad(), autocast:
            hidden = model(**enc).last_hidden_state  # [B, L, H]
        cls = hidden[:, 0]  # bge dense = CLS
        normed = torch.nn.functional.normalize(cls.float(), p=2, dim=1)
        out.append(normed.cpu().numpy())
        if (i // _BATCH) % 20 == 0:
            print(f"  임베딩 {min(i + _BATCH, total)}/{total}", flush=True)
    return np.vstack(out)


def main() -> None:
    if not _EPISODES_DIR.is_dir():
        print(f"원작 episodes 없음: {_EPISODES_DIR}", file=sys.stderr)
        sys.exit(1)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[build_index] device={device} model={_MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
        _MODEL_NAME, cache_dir=str(_CACHE_DIR)
    )
    model = AutoModel.from_pretrained(_MODEL_NAME, cache_dir=str(_CACHE_DIR)).to(device)
    model.eval()

    episodes = sorted(_EPISODES_DIR.glob("episode_*.txt"), key=_episode_num)
    print(f"[build_index] 에피소드 {len(episodes)}개 청킹…", flush=True)
    all_chunks: list[Chunk] = []
    for path in episodes:
        ep = _episode_num(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        all_chunks.extend(chunk_episode(tokenizer, ep, text))
    print(f"[build_index] 청크 {len(all_chunks)}개 → 임베딩…", flush=True)

    t0 = time.time()
    embeddings = embed_texts(model, tokenizer, [c.text for c in all_chunks], device)
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
