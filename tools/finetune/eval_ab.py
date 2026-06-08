"""LoRA 전후 A/B 평가 — base(Llama-3.2-3B) vs GM-LoRA, 동일 Q8·동일 시나리오.

run_eval 헬퍼(_stream_call/_judge)·metrics(hangul_purity/aggregate_nonself) 재사용.
author = llama32-base(8088) / llama32-gm(8087). judge = gemma(8085)+27b(8081)
(둘 다 author와 다름 → Cross-Model 자기채점 무관). 문체·persona G-Eval + 한글순도(망각 체크).

사용: python tools/finetune/eval_ab.py --out .local/finetune/ab_results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from service.sim.gm_narrator import _GM_SYSTEM, _GM_USER, build_gm_canon  # noqa: E402
from tools.eval import metrics  # noqa: E402
from tools.eval.run_eval import _judge, _stream_call  # noqa: E402

EVAL_DIR = ROOT / "tools" / "eval"

_DEF_AUTHORS = [
    {"key": "qwen3-4b-base", "endpoint": "http://127.0.0.1:8088", "model": "qwen3-4b-base"},
    {"key": "qwen3-4b-gm", "endpoint": "http://127.0.0.1:8087", "model": "qwen3-4b-gm"},
]
JUDGES = {
    "gemma": {"key": "gemma", "endpoint": "http://127.0.0.1:8085", "model": "gemma"},
    "qwen36-27b": {"key": "qwen36-27b", "endpoint": "http://127.0.0.1:8081",
                   "model": "qwen3.6-27b"},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / ".local/finetune/ab_results.json"))
    ap.add_argument("--name", help="base 이름(예: smollm3) — base/gm 페어 자동 구성")
    ap.add_argument("--base-ep", default="http://127.0.0.1:8088")
    ap.add_argument("--gm-ep", default="http://127.0.0.1:8087")
    args = ap.parse_args()

    if args.name:
        authors = [
            {"key": f"{args.name}-base", "endpoint": args.base_ep, "model": f"{args.name}-base"},
            {"key": f"{args.name}-gm", "endpoint": args.gm_ep, "model": f"{args.name}-gm"},
        ]
    else:
        authors = _DEF_AUTHORS

    prm = yaml.safe_load((EVAL_DIR / "prompts.yaml").read_text(encoding="utf-8"))
    cfg = yaml.safe_load((EVAL_DIR / "models.yaml").read_text(encoding="utf-8"))
    sampling = cfg["sampling"]

    out: dict[str, Any] = {"sampling": sampling, "models": []}
    for m in authors:
        print(f"=== {m['key']} ===", flush=True)
        tps: list[float] = []
        purity: list[float] = []
        glue = dup = foreign = 0
        per_judge_list: list[dict[str, Any]] = []
        samples: list[dict[str, Any]] = []
        for scen in prm["narrative"]:
            canon = build_gm_canon(scen["user"], scen["location"], scen["surroundings"],
                                   scen["hostiles"], scen["weapon"])
            system = _GM_SYSTEM.format(canon=canon)
            user = _GM_USER.format(history="(없음 — 첫 행동)", phase=scen["phase"],
                                   location=scen["location"], surroundings=scen["surroundings"],
                                   fact=scen["fact"], action=scen["user"])
            best = ""
            for _ in range(sampling["runs"]):
                try:
                    r = _stream_call(m["endpoint"], m["model"], system, user, sampling)
                except Exception as e:  # noqa: BLE001
                    print(f"  [{scen['key']}] ERR {e}", flush=True)
                    continue
                tps.append(r["tps"])
                hp = metrics.hangul_purity(r["text"])
                purity.append(hp["purity_pct"])
                glue += hp["glue_glitch"]
                dup += hp["dup_glitch"]
                foreign += hp["foreign_chars"]
                best = r["text"]
            ctx = f"위치: {scen['location']} / 주변: {scen['surroundings']} / 행동: {scen['user']}"
            per_judge: dict[str, Any] = {}
            if best:
                for jk, jm in JUDGES.items():
                    per_judge[jk] = _judge({jk: jm}, jk, ctx, best)
            per_judge_list.append(per_judge)
            samples.append({"scenario": scen["key"], "text": best, "per_judge": per_judge})
            print(f"  [{scen['key']}] judges={list(per_judge)}", flush=True)

        agg = metrics.aggregate_nonself(m["key"], per_judge_list)
        n = max(1, len(purity))
        out["models"].append({
            "key": m["key"],
            "hangul": {"purity_pct": round(sum(purity) / n, 2),
                       "glue_glitch": glue, "dup_glitch": dup, "foreign_chars": foreign},
            "judge": agg,
            "samples": samples,
        })
        print(f"  → {m['key']} judge={agg['overall']} purity={round(sum(purity)/n,2)}",
              flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE → {args.out}", flush=True)


if __name__ == "__main__":
    main()
