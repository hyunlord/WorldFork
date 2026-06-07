"""소형 태스크 LoRA SFT — Qwen3.5-4B GM 서사 (PEFT+TRL, GB10 호환 검증됨).

데이터(.local/finetune/gm_narrative.jsonl [instruction→output])를 GM contract chat로
포맷, LoRA(r16/alpha32/attention) SFT. assistant-only loss(가능 시)로 문체만 학습.
어댑터 → /home/hyunlord/models/finetune/qwen35-4b-gm-lora/.

사용: python tools/finetune/train_lora.py --epochs 3
★ 외부 패키지(peft/trl) — 사용자 승인(DGX 소유자). 본문 데이터 .local(git 금지).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

# ★ stage-1 파이프라인 검증 base = Llama-3.2-3B(llama arch — transformers 4.57.1 로드 확실).
#   선호 base Qwen3.5-4B는 transformers가 qwen3_5 arch 미인식이라 보류(업그레이드 후속).
BASE = "/home/hyunlord/models/finetune/Llama-3.2-3B"
DATA = Path(".local/finetune/gm_narrative.jsonl")
OUT = "/home/hyunlord/models/finetune/llama32-3b-gm-lora"

_SYS = (
    "당신은 한국 web novel 던전 생존 소설의 게임 마스터(GM)다. "
    "플레이어 행동을 받아 1인칭('나는')·조선·중세풍 문어체로 서사를 이어간다. "
    "메타·시스템·규칙 설명, AI 자칭은 금지한다."
)


def load_pairs() -> Dataset:
    rows = []
    with DATA.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rows.append({"messages": [
                {"role": "system", "content": _SYS},
                {"role": "user", "content": d["instruction"]},
                {"role": "assistant", "content": d["output"]},
            ]})
    return Dataset.from_list(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--r", type=int, default=16)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForCausalLM.from_pretrained(
        BASE, torch_dtype=torch.bfloat16, device_map="cuda",
    )
    ds = load_pairs()
    print(f"데이터 {len(ds)} 쌍, LoRA r={args.r}, epochs={args.epochs}", flush=True)

    peft_cfg = LoraConfig(
        r=args.r, lora_alpha=args.r * 2, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    cfg = SFTConfig(
        output_dir=OUT, num_train_epochs=args.epochs,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=2e-4, warmup_ratio=0.05, lr_scheduler_type="cosine",
        logging_steps=5, save_strategy="epoch", bf16=True,
        max_length=1024, packing=False, report_to=[],
        # assistant_only_loss는 Llama 템플릿에 {% generation %} 마커 부재로 미지원 →
        # 전체 SFT(프롬프트 포함)로 문체 학습. 짧은 instruction이라 영향 작음.
    )
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, peft_config=peft_cfg)
    trainer.train()
    trainer.save_model(OUT)
    tok.save_pretrained(OUT)
    print(f"DONE LoRA → {OUT}", flush=True)


if __name__ == "__main__":
    main()
