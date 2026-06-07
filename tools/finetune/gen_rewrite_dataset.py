"""2차 LoRA 데이터 — best labeler(27B)로 [instruction → 정제 rewrite] 쌍 대량 생성.

★ 1단계 음성 원인#3(데이터 파편) 직격: output을 원작 원문이 아니라 '자기완결 순한국어 GM
서사'로 정제. 청킹→역설계(instruction)+정제(rewrite, 출력 타깃)을 27B 동시 8 병렬로 생성.
순도·문맥 필터 통과분만 채택. 본문 .local(저작권). 출력 .local/finetune/gm_narrative_v2.jsonl.

사용: python tools/finetune/gen_rewrite_dataset.py --target 1500 --concurrency 8
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

ENDPOINT, MODEL = "http://localhost:8081", "qwen3.6-27b"
OUT = ROOT / ".local/finetune/gm_narrative_v2.jsonl"

_SYS_A = (
    "당신은 한국어 던전 게임 로그 설계자다. 주어진 소설 서사 한 토막을 보고, "
    "그 서사를 끌어낼 법한 '플레이어 행동/상황'을 1문장으로 역설계하라. "
    "메타 설명 없이 행동/상황만 출력한다."
)
_SYS_B = (
    "당신은 한국 web novel 던전 생존 소설의 게임 마스터(GM)다. 주어진 원작 본문 토막을 "
    "1인칭('나는') 조선·중세풍 문어체의 자기완결 서사로 다듬어라. 규칙: "
    "①한자·영어·게임 메타 용어 제거(순한국어) ②앞뒤 문맥 없이도 읽히는 완결 단락 "
    "③원작 고유명사는 유지 ④3~5문장. 메타·시스템 설명 금지, 서사만 출력."
)
_THINK_TAG = re.compile(r"<think>.*?</think>", re.DOTALL)
# ★ output(학습 타깃)에서만 게임 메타 누출 배제 — instruction(입력)은 무관
_META = re.compile(r"(NPC|플레이어|스킬|레벨|던전\s*앤\s*스톤|시스템|퀘스트|\bHP\b|\bMP\b)")


def _call(system: str, user: str, max_tokens: int) -> str | None:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens, "temperature": 0.5, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(f"{ENDPOINT}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
    except Exception:  # noqa: BLE001
        return None
    txt = (r["choices"][0]["message"].get("content") or "")
    return _THINK_TAG.sub("", txt).strip() or None


def make_pair(ch: str) -> dict[str, str] | None:
    """청크 → {instruction, output=정제}. 품질 필터(순도95+/길이) 통과분만."""
    instr = _call(_SYS_A, f"서사:\n{ch}\n\n플레이어 행동/상황 1문장:", 80)
    if not instr:
        return None
    rewrite = _call(_SYS_B, f"원작 본문:\n{ch}\n\n다듬은 GM 서사:", 320)
    if not rewrite or len(rewrite) < 40:
        return None
    hp = hangul_purity(rewrite)
    if hp["purity_pct"] < 95.0 or hp["glue_glitch"] or hp["dup_glitch"]:
        return None
    if _META.search(rewrite):  # output 메타 누출 배제(GM 자칭/게임명 금지)
        return None
    return {"instruction": instr, "output": rewrite}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1500)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--episodes", type=int, default=0, help="0=전체")
    ap.add_argument("--offset", type=int, default=0, help="청크 풀 시작 오프셋(보충용)")
    ap.add_argument("--append", action="store_true", help="기존 파일에 이어쓰기")
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # 청크 풀 — 전 구간 고르게, 문어체 필터
    chunks: list[str] = []
    for body in load_bodies(args.episodes):
        for ch in chunk(body):
            if is_munche(ch):
                chunks.append(ch)
    print(f"청크 풀 {len(chunks)}개 → target {args.target} 쌍 "
          f"(동시 {args.concurrency})", flush=True)

    chunks = chunks[args.offset:]
    lock = threading.Lock()
    kept = [0]
    rejected = [0]
    fout = OUT.open("a" if args.append else "w", encoding="utf-8")

    def worker(ch: str) -> None:
        if kept[0] >= args.target:
            return
        p = make_pair(ch)
        with lock:
            if p and kept[0] < args.target:
                fout.write(json.dumps(p, ensure_ascii=False) + "\n")
                fout.flush()
                kept[0] += 1
                if kept[0] % 50 == 0:
                    print(f"  {kept[0]}/{args.target} (reject {rejected[0]})", flush=True)
            elif not p:
                rejected[0] += 1

    with cf.ThreadPoolExecutor(args.concurrency) as ex:
        futures = [ex.submit(worker, ch) for ch in chunks[: args.target * 3]]
        for _f in cf.as_completed(futures):
            if kept[0] >= args.target:
                break
    fout.close()
    print(f"DONE {kept[0]} 쌍 (reject {rejected[0]}) → {OUT}", flush=True)


if __name__ == "__main__":
    main()
