"""labeler 정제(rewrite) 품질 cross-model 채점 — best labeler 객관 선정.

각 labeler 출력(out_<labeler>.json)의 rewrite를 judge 모델들이 4축 1~5 채점:
  자기완결(앞뒤 없이 읽힘) / 문어체(1인칭 중세풍) / 메타제거(게임 용어 없음) / 충실(원작 정합).
self 채점 배제(author≠judge). 결과 /tmp/labeler_compare/judge_summary.json.

사용: python tools/finetune/judge_labelers.py --judges qwen36-27b,gemma
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import urllib.request
from pathlib import Path

OUT_DIR = Path("/tmp/labeler_compare")
ENDPOINTS = {
    "qwen36-27b": ("http://localhost:8081", "qwen3.6-27b"),
    "gemma": ("http://localhost:8085", "gemma"),
    "qwen35-122b": ("http://localhost:8089", "qwen35-122b"),
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
    ap.add_argument("--judges", default="qwen36-27b,gemma")
    args = ap.parse_args()
    judges = [j for j in args.judges.split(",") if j in ENDPOINTS]

    labeler_files = sorted(OUT_DIR.glob("out_*.json"))
    summary = []
    for lf in labeler_files:
        d = json.loads(lf.read_text(encoding="utf-8"))
        author = d["labeler"]
        axis_vals: dict[str, list[float]] = {ax: [] for ax in AXES}
        purity = [r["rewrite_purity"] for r in d["results"]]
        for r in d["results"]:
            for jk in judges:
                if jk == author:
                    continue  # self 배제
                ep, jm = ENDPOINTS[jk]
                sc = _judge(ep, jm, r["rewrite"])
                if sc:
                    for ax in AXES:
                        axis_vals[ax].append(sc[ax])
        axes = {ax: round(statistics.mean(v), 2) for ax, v in axis_vals.items() if v}
        overall = round(statistics.mean(axes.values()), 2) if axes else None
        rec = {"labeler": author, "axes": axes, "overall": overall,
               "avg_purity": round(sum(purity) / max(1, len(purity)), 1),
               "judges": [j for j in judges if j != author]}
        summary.append(rec)
        print(f"  {author}: overall={overall} {axes} purity={rec['avg_purity']}", flush=True)

    summary.sort(key=lambda x: (x["overall"] or 0), reverse=True)
    (OUT_DIR / "judge_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nBEST labeler: {summary[0]['labeler']} (overall {summary[0]['overall']})",
          flush=True)


if __name__ == "__main__":
    main()
