"""GM 서사 LoRA SFT (PEFT+TRL, GB10 호환 검증됨) — 2차: 음성 4원인 수정.

1단계 음성(base 2.92→LoRA 2.25) 4원인을 모두 교정:
  ①base 교체: Llama-3.2-3B(영어중심) → Qwen3-4B-Instruct-2507(한국어 강·qwen3 arch 인식)
  ②assistant-only loss: 템플릿 {% generation %} 마커 활용 → 프롬프트 마스킹(메타 누출 차단)
  ③데이터: 100쌍 파편 → v3 1500쌍(best 35B 정제, 한자 0)
  ④lr 2e-4 3ep → lr 5e-5 + early-stop(과적합 회피, eval holdout)

사용: python tools/finetune/train_lora.py --epochs 3 --lr 5e-5
★ 외부 패키지(peft/trl) — 사용자 승인(DGX 소유자). 본문 데이터 .local(git 금지).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, EarlyStoppingCallback
from trl import SFTConfig, SFTTrainer

# ★ 2차 base = Qwen3-4B-Instruct-2507(qwen3 arch — transformers 4.57.1 인식 확인).
#   선호 Qwen3.5-4B(qwen3_5)는 transformers 5.x 필요(.venv 위험)이라 동급 Qwen3-4B로.
#   Instruct 템플릿에 {% generation %} 있어 assistant-only loss 가능(원인2 해소).
BASE = "/home/hyunlord/models/finetune/Qwen3-4B-Instruct-2507"
DATA = Path(".local/finetune/gm_narrative_v3.jsonl")
OUT = "/home/hyunlord/models/finetune/qwen3-4b-gm-lora-v2"

_SYS = (
    "당신은 한국 web novel 던전 생존 소설의 게임 마스터(GM)다. "
    "플레이어 행동을 받아 1인칭('나는')·조선·중세풍 문어체로 서사를 이어간다. "
    "메타·시스템·규칙 설명, AI 자칭은 금지한다."
)


def load_pairs() -> list[dict[str, list[dict[str, str]]]]:
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
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--lr", type=float, default=5e-5)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForCausalLM.from_pretrained(
        BASE, torch_dtype=torch.bfloat16, device_map="cuda",
    )
    rows = load_pairs()
    # ★ early-stop용 holdout 5%(과적합 조기 감지) — 결정적 분할(섞기 없이 뒤 5%)
    n_eval = max(20, len(rows) // 20)
    train_ds = Dataset.from_list(rows[:-n_eval])
    eval_ds = Dataset.from_list(rows[-n_eval:])
    print(f"train {len(train_ds)} / eval {len(eval_ds)} 쌍, "
          f"LoRA r={args.r}, lr={args.lr}, epochs={args.epochs}", flush=True)

    peft_cfg = LoraConfig(
        r=args.r, lora_alpha=args.r * 2, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    cfg = SFTConfig(
        output_dir=OUT, num_train_epochs=args.epochs,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=args.lr, warmup_ratio=0.05, lr_scheduler_type="cosine",
        logging_steps=5, bf16=True, max_length=1024, packing=False, report_to=[],
        # ★ 원인2 수정: assistant-only loss — 프롬프트(시스템+유저) 토큰 loss 제외.
        assistant_only_loss=True,
        # ★ 원인4 수정: eval + early-stop으로 과적합 조기 중단.
        eval_strategy="steps", eval_steps=20, save_strategy="steps", save_steps=20,
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, save_total_limit=2,
    )
    trainer = SFTTrainer(
        model=model, args=cfg, train_dataset=train_ds, eval_dataset=eval_ds,
        peft_config=peft_cfg,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )
    trainer.train()
    trainer.save_model(OUT)
    tok.save_pretrained(OUT)
    print(f"DONE LoRA → {OUT}", flush=True)


if __name__ == "__main__":
    main()
