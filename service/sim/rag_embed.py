"""bge-m3 임베딩 공유 모듈 — 인덱싱(build_index)과 검색(rag_retrieval)이 ★ 동일 경로 사용.

쿼리·문서 임베딩이 같은 모델·같은 방식(CLS pooling + L2 정규화, bge-m3)이어야 cosine이
유효하다. 그 단일 출처를 여기 둔다. 모델은 lazy 싱글톤(첫 호출 시 .local/hf_cache에서 로드).
신규 패키지 0(torch/transformers/numpy). 모델 가중치·캐시는 .local(공개 MIT bge-m3, git 밖).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

_MODEL_NAME = "BAAI/bge-m3"
_CACHE_DIR = Path(".local/hf_cache")
_MAX_LEN = 512
_BATCH = 64

_state: dict[str, Any] = {}


def _load() -> tuple[Any, Any, torch.device]:
    """lazy 로드 — (model, tokenizer, device) 싱글톤."""
    if not _state:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
            _MODEL_NAME, cache_dir=str(_CACHE_DIR)
        )
        model = AutoModel.from_pretrained(_MODEL_NAME, cache_dir=str(_CACHE_DIR)).to(device)
        model.eval()
        _state.update(model=model, tokenizer=tokenizer, device=device)
    return _state["model"], _state["tokenizer"], _state["device"]


def get_tokenizer() -> Any:
    """bge-m3 토크나이저(청킹용 — build_index가 사용)."""
    return _load()[1]


def warm() -> None:
    """모델 사전 로드 — 첫 검색의 콜드 23s를 백엔드 기동 시 미리 흡수(A2.4)."""
    embed(["워밍업"])


def embed(texts: list[str]) -> np.ndarray:
    """bge-m3 dense 임베딩 — CLS 토큰 + L2 정규화(GPU는 bf16 autocast). float32 [N, 1024].

    ★ 인덱싱·검색이 이 함수를 공유 — 임베딩 방식 단일 출처(cosine 유효 보장).
    """
    model, tokenizer, device = _load()
    use_cuda = device.type == "cuda"
    out: list[np.ndarray] = []
    for i in range(0, len(texts), _BATCH):
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
        normed = torch.nn.functional.normalize(hidden[:, 0].float(), p=2, dim=1)
        out.append(normed.cpu().numpy())
    return np.vstack(out)
