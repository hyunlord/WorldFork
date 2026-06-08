"""Unsloth LoRA SFT — peft⊥transformers5.x 갭 우회(최신 arch: Qwen3.5/3.6, Gemma 4).

★ peft 0.19.1은 transformers 5.x 미지원(PreTrainedModel export 제거) → Qwen3.5/Gemma4 LoRA 불가.
Unsloth(자체 transformers 5.5 호환 + FastLanguageModel)로 우회. 같은 v3 + 2차 레시피(r16/lr5e-5/
assistant-only). GB10: .venv의 torch 2.9.1+cu128 복사 필요(unsloth 기본 torch는 cpu).

사용: python tools/finetune/train_unsloth.py --base <경로> --out <경로>
★ 외부 패키지(unsloth) — 사용자 승인(DGX). 본문 데이터 .local(git 금지). 별도 unsloth_venv.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import Dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel  # noqa: I001 — unsloth must import first

DATA = Path(".local/finetune/gm_narrative_v3.jsonl")
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
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--max-seq", type=int, default=1024)
    args = ap.parse_args()

    model, tok = FastLanguageModel.from_pretrained(
        args.base, max_seq_length=args.max_seq, load_in_4bit=True, dtype=None,
    )
    # ★ Unsloth 네이티브 ChatML 설정(eos·템플릿·pad 일괄 — base 모델 placeholder eos 교정).
    from unsloth.chat_templates import get_chat_template
    tok = get_chat_template(tok, chat_template="chatml")
    # ★ Unsloth가 trl SFTConfig.eos_token에 '<EOS_TOKEN>' placeholder를 강제 주입 →
    #   trl 0.24가 vocab 검증 실패. placeholder를 실제 토큰으로 등록해 검증 통과(데이터엔 미사용).
    _ph = [t for t in ("<EOS_TOKEN>", "<PAD_TOKEN>") if t not in tok.get_vocab()]
    if _ph:
        tok.add_special_tokens({"additional_special_tokens": _ph})
        model.resize_token_embeddings(len(tok))
    model = FastLanguageModel.get_peft_model(
        model, r=args.r, lora_alpha=args.r * 2, lora_dropout=0.0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        use_gradient_checkpointing="unsloth",
    )
    rows = load_pairs()
    n_eval = max(20, len(rows) // 20)
    train_ds = Dataset.from_list(rows[:-n_eval])
    eval_ds = Dataset.from_list(rows[-n_eval:])
    print(f"train {len(train_ds)} / eval {len(eval_ds)} 쌍 (Unsloth, r={args.r}, lr={args.lr})",
          flush=True)

    cfg = SFTConfig(
        output_dir=args.out, num_train_epochs=args.epochs,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=args.lr, warmup_ratio=0.05, lr_scheduler_type="cosine",
        logging_steps=5, bf16=True, max_length=args.max_seq, packing=False, report_to=[],
        dataset_num_proc=1,  # ★ 멀티프로세싱 pickle(torch config) 회피
        eos_token="<|im_end|>",  # ★ ChatML 종결 — SFTConfig 기본 '<EOS_TOKEN>' placeholder 교정
        eval_strategy="steps", eval_steps=20, save_strategy="steps", save_steps=20,
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, save_total_limit=2,
    )
    cfg.eos_token = "<|im_end|>"  # ★ Unsloth 패치가 덮은 '<EOS_TOKEN>' placeholder 재교정
    trainer = SFTTrainer(
        model=model, args=cfg, train_dataset=train_ds, eval_dataset=eval_ds,
        processing_class=tok,
    )
    # ★ assistant-only loss(원인2): ChatML user/assistant 경계로 응답만 학습(프롬프트 마스킹).
    from unsloth.chat_templates import train_on_responses_only
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n",
    )
    trainer.train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print(f"DONE Unsloth LoRA → {args.out}", flush=True)


if __name__ == "__main__":
    main()
