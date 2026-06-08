"""labeler rewrite 채점 — 단일 judge 원점수를 judge_raw.jsonl에 append (순차 수집용).

메모리 제약(122B 72GB)으로 judge를 동시 로드 못 함 → judge별로 따로 실행해 누적.
이후 merge_judges.py가 self-제외+평균 집계. 한 judge가 모든 labeler의 모든 rewrite 채점.

사용: python tools/finetune/judge_raw.py --judge qwen35-122b
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

OUT_DIR = Path("/tmp/labeler_compare")
RAW = OUT_DIR / "judge_raw.jsonl"
ENDPOINTS = {
    "qwen36-27b": ("http://localhost:8081", "qwen3.6-27b"),
    "gemma": ("http://localhost:8085", "gemma"),
    "qwen35-122b": ("http://localhost:8089", "qwen35-122b"),
    "qwen36-35b": ("http://localhost:8089", "qwen36-35b"),
    "gemma31b": ("http://localhost:8092", "gemma31b"),
}
AXES = ("자기완결", "문어체", "메타제거", "충실")
_SYS = (
    "당신은 한국어 게임 GM 서사 데이터의 엄정한 평가자다. 주어진 '다듬은 서사'를 4축으로 "
    "1~5 정수 채점하라(5=최상). JSON만 출력.\n"
    "- 자기완결: 앞뒤 문맥 없이도 읽히는 완결 단락인가\n"
    "- 문어체: 1인칭('나는') 조선·중세풍 문어체 일관성\n"
    "- 메타제거: 한자·영어·게임 시스템 용어 없이 순한국어 서사인가\n"
    "- 충실: 원작 사건/고유명사 정합(날조 없음)\n"
    '출력: {"자기완결":N,"문어체":N,"메타제거":N,"충실":N}'
)


def _judge(endpoint: str, model: str, text: str) -> dict[str, int] | None:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": _SYS},
                     {"role": "user", "content": f"## 다듬은 서사\n{text}\n\nJSON 채점:"}],
        "max_tokens": 120, "temperature": 0.2, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(f"{endpoint}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
    except Exception:  # noqa: BLE001
        return None
    txt = (r["choices"][0]["message"].get("content") or "")
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return {ax: max(1, min(5, int(obj[ax]))) for ax in AXES}
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", choices=list(ENDPOINTS), required=True)
    args = ap.parse_args()
    ep, jm = ENDPOINTS[args.judge]

    with RAW.open("a", encoding="utf-8") as out:
        for lf in sorted(OUT_DIR.glob("out_*.json")):
            d = json.loads(lf.read_text(encoding="utf-8"))
            author = d["labeler"]
            if author == args.judge:
                continue  # self 배제
            for r in d["results"]:
                sc = _judge(ep, jm, r["rewrite"])
                rec = {"labeler": author, "judge": args.judge,
                       "chunk": r["key"], "score": sc}
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"  {author}/{r['key']} by {args.judge}: {sc}", flush=True)
    print(f"DONE judge={args.judge} → {RAW}", flush=True)


if __name__ == "__main__":
    main()
