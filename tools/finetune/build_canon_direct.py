"""원작 직접 데이터 — output=원작 chunk 원문(증류 0, 천장 돌파용). ★ 저작권: .local 전용.

v3는 원작→35B 증류(rewrite)라 35B 품질이 천장(~4.15). 원작 직접은 output=원작 prose 그대로 →
35B 손실 없음(원작 문체/고증 최고 품질). instruction만 labeler로 역생성(input — output 무손상).
9B base(4.58, v3로는 -0.50 음성)가 원작 직접으로 천장 돌파하는지 검증용.

필터: cjk=0(한자 누출 — 한국 web novel은 0.3%뿐) + 격식체/길이(is_munche). assistant-only로 학습.
출력 .local/finetune/canon_direct.jsonl (★ git 절대 금지 — .local gitignored).

사용: python tools/finetune/build_canon_direct.py --target 1500 --concurrency 8
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.eval.metrics import hangul_purity  # noqa: E402
from tools.finetune.build_dataset import chunk, is_munche, load_bodies  # noqa: E402

OUT = ROOT / ".local/finetune/canon_direct.jsonl"
# instruction 역생성 labeler — gemma(8085, 빠름). output은 raw라 labeler는 input만 영향.
ENDPOINT, MODEL = "http://localhost:8085", "gemma"

_SYS_A = (
    "당신은 한국어 던전 게임 로그 설계자다. 주어진 소설 서사 한 토막을 보고, "
    "그 서사를 끌어낼 법한 '플레이어 행동/상황'을 1문장으로 역설계하라. "
    "메타 설명 없이 행동/상황만 출력한다."
)
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _instr(chunk_text: str) -> str | None:
    user = f"서사:\n{chunk_text}\n\n플레이어 행동/상황 1문장:"
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": _SYS_A},
                     {"role": "user", "content": user}],
        "max_tokens": 80, "temperature": 0.4, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(f"{ENDPOINT}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120))
    except Exception:  # noqa: BLE001
        return None
    out = _THINK.sub("", r["choices"][0]["message"].get("content") or "").strip()
    return out or None


def make_pair(ch: str) -> dict[str, str] | None:
    """원작 chunk → {instruction(역생성), output=원작 원문}. cjk=0 필수."""
    hp = hangul_purity(ch)
    if hp["cjk"] > 0 or hp["glue_glitch"] or hp["dup_glitch"]:
        return None  # ★ 한자 누출 chunk 배제(학습 안전)
    instr = _instr(ch)
    if not instr:
        return None
    return {"instruction": instr, "output": ch}  # ★ output=원작 원문(증류 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1500)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--episodes", type=int, default=0)
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    chunks = [ch for b in load_bodies(args.episodes) for ch in chunk(b) if is_munche(ch)]
    print(f"청크 풀 {len(chunks)} → target {args.target} (동시 {args.concurrency})", flush=True)

    lock = threading.Lock()
    kept = [0]
    rej = [0]
    fout = OUT.open("w", encoding="utf-8")

    def worker(ch: str) -> None:
        if kept[0] >= args.target:
            return
        p = make_pair(ch)
        with lock:
            if p and kept[0] < args.target:
                fout.write(json.dumps(p, ensure_ascii=False) + "\n")
                fout.flush()
                kept[0] += 1
                if kept[0] % 100 == 0:
                    print(f"  {kept[0]}/{args.target} (reject {rej[0]})", flush=True)
            elif not p:
                rej[0] += 1

    with cf.ThreadPoolExecutor(args.concurrency) as ex:
        futures = [ex.submit(worker, ch) for ch in chunks[: args.target * 3]]
        for _f in cf.as_completed(futures):
            if kept[0] >= args.target:
                break
    fout.close()
    print(f"DONE {kept[0]} 쌍 (reject {rej[0]}) → {OUT}", flush=True)


if __name__ == "__main__":
    main()
