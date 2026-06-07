"""labeler 비교 — 같은 본문 청크로 여러 모델의 역설계+정제 품질 비교 (1단계 데이터 파편 해결).

고정 청크(/tmp/labeler_compare/chunks.json)에 대해 각 labeler가 두 역할 수행:
  A. instruction 역설계 — 본문 → 끌어낼 플레이어 행동/상황 1문장
  B. 청크 정제/재작성 — 원작 파편 → 자기완결 순한국어 1인칭 GM 서사(★ 음성 원인 #3 직격)
출력(/tmp/labeler_compare/out_<labeler>.json) + 한글순도 정량. ★ 본문 원본은 공유 X(저작권).

사용: python tools/finetune/compare_labelers.py --labeler qwen36-27b
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.eval.metrics import hangul_purity  # noqa: E402

CHUNKS = Path("/tmp/labeler_compare/chunks.json")
OUT_DIR = Path("/tmp/labeler_compare")

LABELERS = {
    "qwen36-27b": ("http://localhost:8081", "qwen3.6-27b"),
    "qwen35-9b": ("http://localhost:8083", "qwen35-9b-q3"),
    "gemma": ("http://localhost:8085", "gemma"),
    "qwen35-122b": ("http://localhost:8089", "qwen35-122b"),
}

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


def _call(endpoint: str, model: str, system: str, user: str, max_tokens: int) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens, "temperature": 0.4, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(f"{endpoint}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    return (r["choices"][0]["message"].get("content") or "").strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labeler", choices=list(LABELERS), required=True)
    args = ap.parse_args()
    endpoint, model = LABELERS[args.labeler]
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))

    results = []
    for c in chunks:
        instr = _call(endpoint, model, _SYS_A,
                      f"서사:\n{c['text']}\n\n플레이어 행동/상황 1문장:", 80)
        rewrite = _call(endpoint, model, _SYS_B,
                        f"원작 본문:\n{c['text']}\n\n다듬은 GM 서사:", 300)
        hp = hangul_purity(rewrite)
        results.append({
            "key": c["key"], "scene": c["scene"],
            "instruction": instr, "rewrite": rewrite,
            "rewrite_purity": hp["purity_pct"], "rewrite_foreign": hp["foreign_chars"],
            "rewrite_glitch": hp["glue_glitch"] + hp["dup_glitch"],
        })
        print(f"  [{c['key']}] purity={hp['purity_pct']} instr={instr[:40]}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"out_{args.labeler}.json"
    out.write_text(json.dumps({"labeler": args.labeler, "model": model,
                               "results": results}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    avg = sum(r["rewrite_purity"] for r in results) / max(1, len(results))
    print(f"DONE {args.labeler} → {out} (정제 평균순도 {avg:.1f}%)", flush=True)


if __name__ == "__main__":
    main()
