"""A2.2 — RAG 검색 로직 단위 테스트(GPU/bge-m3 없이 결정적).

cosine top-k 랭킹·episode 범위 필터·★ 마스킹(원작명→변환명)을 가짜 인덱스 + mock 임베딩으로
검증. 실제 임베딩/인덱스(.local) 통합 검증은 데모 스크립트(보고)에서 별도 수행.
"""

from unittest.mock import patch

import numpy as np

from service.sim import rag_retrieval as rag


def _fake_index() -> None:
    # 4 청크 — 단위벡터로 cosine 예측 가능하게. 텍스트에 원작명(비요른) 포함 → 마스킹 검증.
    emb = np.array(
        [
            [1.0, 0.0, 0.0],  # ep1 — 쿼리와 동일(최고 cosine)
            [0.0, 1.0, 0.0],  # ep1 — 무관
            [0.9, 0.1, 0.0],  # ep5 — 쿼리와 유사
            [0.8, 0.0, 0.0],  # ep50 — 유사하나 범위 밖
        ],
        dtype=np.float32,
    )
    chunks = [
        {"id": "a", "episode": 1, "chunk_idx": 0, "text": "비요른이 도끼를 들었다"},
        {"id": "b", "episode": 1, "chunk_idx": 1, "text": "무관한 장면"},
        {"id": "c", "episode": 5, "chunk_idx": 0, "text": "비요른과 에르웬"},
        {"id": "d", "episode": 50, "chunk_idx": 0, "text": "후반 스포일러"},
    ]
    rag._index.clear()
    rag._index.update(
        emb=emb, chunks=chunks, episodes=np.array([1, 1, 5, 50], dtype=np.int64)
    )


def test_topk_ranked_by_cosine() -> None:
    _fake_index()
    with patch.object(rag, "index_available", return_value=True), patch.object(
        rag, "embed", return_value=np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    ):
        res = rag.get_grounding("쿼리", episode_range=(1, 10), top_k=3)
    # ep1(1.0) > ep5(0.9) > ep1무관(0.0). ep50은 범위 밖 제외.
    assert [p.episode for p in res] == [1, 5, 1]
    assert res[0].score > res[1].score > res[2].score


def test_episode_range_filter() -> None:
    _fake_index()
    with patch.object(rag, "index_available", return_value=True), patch.object(
        rag, "embed", return_value=np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    ):
        res = rag.get_grounding("쿼리", episode_range=(40, 60), top_k=4)
    # 범위(40~60)엔 ep50만
    assert len(res) == 1 and res[0].episode == 50


def test_masking_applied() -> None:
    _fake_index()
    with patch.object(rag, "index_available", return_value=True), patch.object(
        rag, "embed", return_value=np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    ):
        res = rag.get_grounding("쿼리", episode_range=(1, 10), top_k=3)
    blob = " ".join(p.text for p in res)
    # ★ 원작명(비요른/에르웬) 0, 변환명(투르윈/실렌)으로 치환
    assert "비요른" not in blob and "에르웬" not in blob
    assert "투르윈" in blob


def test_no_index_returns_empty() -> None:
    with patch.object(rag, "index_available", return_value=False):
        assert rag.get_grounding("쿼리") == []
