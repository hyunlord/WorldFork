"""LoRA 어댑터 → base 병합 후 merged safetensors 저장 (GGUF 변환 전 단계).

학습된 어댑터(/home/hyunlord/models/finetune/qwen3-4b-gm-lora-v2)를 base에 merge_and_unload,
/home/hyunlord/models/finetune/qwen3-4b-gm-v2-merged 로 저장. 이후 llama.cpp로 GGUF화.

사용: python tools/finetune/merge_lora.py [--base B --adapter A --merged M]
"""

from __future__ import annotations

import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "/home/hyunlord/models/finetune/Qwen3-4B-Instruct-2507"
ADAPTER = "/home/hyunlord/models/finetune/qwen3-4b-gm-lora-v2"
MERGED = "/home/hyunlord/models/finetune/qwen3-4b-gm-v2-merged"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", default=ADAPTER)
    ap.add_argument("--merged", default=MERGED)
    args = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(args.adapter)
    base = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, device_map="cpu",
    )
    model = PeftModel.from_pretrained(base, args.adapter)
    merged = model.merge_and_unload()
    merged.save_pretrained(args.merged, safe_serialization=True)
    tok.save_pretrained(args.merged)
    print(f"DONE merged → {args.merged}", flush=True)


if __name__ == "__main__":
    main()
