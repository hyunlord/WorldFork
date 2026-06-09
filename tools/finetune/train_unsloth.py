"""Unsloth LoRA SFT — peft⊥transformers5.x 갭 우회(최신 arch: Qwen3.5/3.6, Gemma 4).

★ peft 0.19.1은 transformers 5.x 미지원(PreTrainedModel export 제거) → Qwen3.5/Gemma4 LoRA 불가.
Unsloth(자체 transformers 5.5 호환 + FastLanguageModel)로 우회. 같은 v3 + 2차 레시피(r16/lr5e-5/
assistant-only). GB10: .venv의 torch 2.9.1+cu128 복사 필요(unsloth 기본 torch는 cpu).

사용(★ GB10 필수 env — 이거 없으면 학습 진입 실패):
  TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas \\  # ★ CUDA13.0 ptxas(sm_121a — 번들12.8 미지원)
  UNSLOTH_COMPILE_DISABLE=1 TORCHDYNAMO_DISABLE=1 \\  # ★ dill pickle(ConfigModuleInstance) 회피
  HF_DATASETS_DISABLE_CACHING=1 \\
  /home/hyunlord/unsloth_venv/bin/python tools/finetune/train_unsloth.py --base <경로> --out <경로>
★ 외부 패키지(unsloth) — 사용자 승인(DGX). 본문 데이터 .local(git 금지). 별도 unsloth_venv.
★ unsloth_venv는 기본 cpu torch → .venv torch2.9.1+cu128/nvidia/triton 복사 필요(torchvision 제거).
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
    ap.add_argument("--no-4bit", action="store_true", help="bf16 로드(임베딩 resize 안정 — gemma4)")
    args = ap.parse_args()

    model, tok = FastLanguageModel.from_pretrained(
        args.base, max_seq_length=args.max_seq, load_in_4bit=not args.no_4bit, dtype=None,
    )
    # ★ ChatML generation 템플릿 설정. Unsloth get_chat_template은 기존 turn 토큰 리맵을
    #   전제 → gemma4(템플릿 부재/비표준)에서 실패. 실패 시 ChatML 토큰 직접 등록+템플릿 주입 폴백.
    from unsloth.chat_templates import get_chat_template
    _chatml = (
        '{% for message in messages %}'
        '{% if message["role"] == "assistant" %}'
        '{{ "<|im_start|>assistant\n" }}{% generation %}{{ message["content"] }}'
        '{{ "<|im_end|>\n" }}{% endgeneration %}'
        '{% else %}'
        '{{ "<|im_start|>" + message["role"] + "\n" + message["content"] + "<|im_end|>\n" }}'
        '{% endif %}{% endfor %}'
        '{% if add_generation_prompt %}{{ "<|im_start|>assistant\n" }}{% endif %}'
    )
    # ★ 네이티브 템플릿 우선: generation 마커가 이미 있으면 그대로 사용(토큰 주입·resize 불필요
    #   → gemma4 elastic arch device assert 회피). 마커 부재 시에만 ChatML 폴백.
    native_ct = tok.chat_template or ""
    if "{% generation %}" in native_ct or "{%- generation" in native_ct:
        # 모델 자체 turn 마커 감지(gemma: <|turn>user/<|turn>model, chatml: <|im_start|>...)
        rendered = tok.apply_chat_template(
            [{"role": "user", "content": "U"}, {"role": "assistant", "content": "A"}],
            tokenize=False, add_generation_prompt=False)
        if "<|turn>model" in rendered:
            instr_part, resp_part, eos_tok = "<|turn>user\n", "<|turn>model\n", "<turn|>"
        else:
            instr_part, resp_part = "<|im_start|>user\n", "<|im_start|>assistant\n"
            eos_tok = "<|im_end|>"
        if eos_tok not in tok.get_vocab():
            eos_tok = tok.eos_token  # 폴백: 토크나이저 기존 eos
        print(f"[template] {args.base} — 네이티브 템플릿 사용(마커 {resp_part!r}, eos {eos_tok!r})",
              flush=True)
    else:
        instr_part, resp_part = "<|im_start|>user\n", "<|im_start|>assistant\n"
        eos_tok = "<|im_end|>"
        try:
            tok = get_chat_template(tok, chat_template="chatml")
        except Exception:  # noqa: BLE001 — base 등: ChatML 토큰 직접 등록 + 템플릿 주입
            new = [t for t in ("<|im_start|>", "<|im_end|>") if t not in tok.get_vocab()]
            if new:
                tok.add_special_tokens({"additional_special_tokens": new})
            tok.chat_template = _chatml
            tok.eos_token = "<|im_end|>"
            print(f"[template] {args.base} — ChatML 직접 주입(토큰 {len(new)} 등록)", flush=True)
    # ★ Unsloth가 trl SFTConfig.eos_token에 '<EOS_TOKEN>' placeholder 강제 주입 →
    #   trl 0.24 vocab 검증 실패. placeholder를 실제 토큰으로 등록해 통과(데이터엔 미사용).
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
        eos_token=eos_tok,  # ★ 종결 — SFTConfig 기본 '<EOS_TOKEN>' placeholder 교정
        eval_strategy="steps", eval_steps=20, save_strategy="steps", save_steps=20,
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, save_total_limit=2,
    )
    cfg.eos_token = eos_tok  # ★ Unsloth 패치가 덮은 '<EOS_TOKEN>' placeholder 재교정
    trainer = SFTTrainer(
        model=model, args=cfg, train_dataset=train_ds, eval_dataset=eval_ds,
        processing_class=tok,
    )
    # ★ assistant-only loss(원인2): ChatML user/assistant 경계로 응답만 학습(프롬프트 마스킹).
    from unsloth.chat_templates import train_on_responses_only
    trainer = train_on_responses_only(
        trainer,
        instruction_part=instr_part,
        response_part=resp_part,
    )
    trainer.train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print(f"DONE Unsloth LoRA → {args.out}", flush=True)


if __name__ == "__main__":
    main()
