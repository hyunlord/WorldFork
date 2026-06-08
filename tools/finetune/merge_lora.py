"""LoRA 어댑터 → base 병합 후 merged safetensors 저장 (GGUF 변환 전 단계).

학습된 어댑터(/home/hyunlord/models/finetune/qwen3-4b-gm-lora-v2)를 base에 merge_and_unload,
/home/hyunlord/models/finetune/qwen3-4b-gm-v2-merged 로 저장. 이후 llama.cpp로 GGUF화.

사용: python tools/finetune/merge_lora.py
"""

from __future__ import annotations

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "/home/hyunlord/models/finetune/Qwen3-4B-Instruct-2507"
ADAPTER = "/home/hyunlord/models/finetune/qwen3-4b-gm-lora-v2"
MERGED = "/home/hyunlord/models/finetune/qwen3-4b-gm-v2-merged"


def main() -> None:
    tok = AutoTokenizer.from_pretrained(ADAPTER)
    base = AutoModelForCausalLM.from_pretrained(
        BASE, torch_dtype=torch.bfloat16, device_map="cpu",
    )
    model = PeftModel.from_pretrained(base, ADAPTER)
    merged = model.merge_and_unload()
    merged.save_pretrained(MERGED, safe_serialization=True)
    tok.save_pretrained(MERGED)
    print(f"DONE merged → {MERGED}", flush=True)


if __name__ == "__main__":
    main()
