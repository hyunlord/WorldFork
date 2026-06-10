"""평가 오케스트레이터 — 모델 × 지표 자동 산출 → results.json.

확장: models.yaml에 모델 줄 추가 / prompts.yaml에 시나리오 추가 / metrics.py에 지표 추가.
지표: 성능(cross-model G-Eval) · latency(TTFT/TPS) · 메모리(size_gb) · 한글순도(정량) ·
태스크(종합 judge) · 구조화 출력(json_schema 준수율). 비결정 다회 평균/분산.

사용: python tools/eval/run_eval.py [--out tools/eval/results.json]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from service.canon.context import set_canon_facts, set_entity_index  # noqa: E402
from service.canon.entity_index import EntityIndex  # noqa: E402
from service.canon.loader import load_canon_facts  # noqa: E402
from service.sim.gm_narrator import _GM_SYSTEM, _GM_USER, build_gm_canon  # noqa: E402
from tools.eval import metrics  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent


def _post(endpoint: str, body: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{endpoint}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=timeout))  # type: ignore[no-any-return]


def _stream_call(
    endpoint: str, model: str, system: str, user: str, sampling: dict[str, Any]
) -> dict[str, Any]:
    """스트리밍 호출 → TTFT/TPS/출력 측정."""
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": sampling["max_tokens"], "temperature": sampling["temperature"],
        "top_k": sampling["top_k"], "top_p": sampling["top_p"],
        "repeat_penalty": sampling["repeat_penalty"], "stream": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        f"{endpoint}/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    ttft = 0.0
    pieces: list[str] = []
    ntok = 0
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            delta = obj.get("choices", [{}])[0].get("delta", {}).get("content") or ""
            if delta:
                if ttft == 0.0:
                    ttft = time.time() - t0
                pieces.append(delta)
                ntok += 1
    total = time.time() - t0
    text = "".join(pieces).strip()
    # ★ thinking 텍스트는 서사가 아님 — 채점 전 <think> 제거(공정: think-on 모델 부풀림 차단)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"^.*?</think>", "", text, flags=re.DOTALL)  # 닫힘만 있는 경우
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()  # 미완 think
    tps = (ntok / total) if total > 0 else 0.0
    return {"text": text, "ttft": ttft, "tps": tps, "tokens": ntok, "total_s": total}


def _judge(models_by_key: dict[str, dict[str, Any]], judge_key: str,
           context: str, narrative: str) -> dict[str, Any] | None:
    j = models_by_key.get(judge_key)
    if j is None:
        return None
    system, user = metrics.build_judge_prompt(context, narrative)
    try:
        r = _post(j["endpoint"], {
            "model": j["model"],
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": 220, "temperature": 0.0, "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        })
    except Exception:  # noqa: BLE001
        return None
    txt = (r["choices"][0]["message"].get("content") or "")
    return metrics.parse_judge(txt)


def _mean(xs: list[float]) -> float:
    return round(statistics.mean(xs), 2) if xs else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EVAL_DIR / "results.json"))
    args = ap.parse_args()

    cfg = yaml.safe_load((EVAL_DIR / "models.yaml").read_text(encoding="utf-8"))
    prm = yaml.safe_load((EVAL_DIR / "prompts.yaml").read_text(encoding="utf-8"))
    sampling = cfg["sampling"]
    models = cfg["models"]
    by_key = {m["key"]: m for m in models}

    facts = load_canon_facts()
    set_canon_facts(facts)
    set_entity_index(EntityIndex(facts))

    results: dict[str, Any] = {"sampling": sampling, "models": []}
    # author별 scenario별 per_judge 원점수 — 루프 후 self제외+보정 집계(metrics)
    author_per_judge: dict[str, list[dict[str, Any]]] = {}
    for m in models:
        print(f"=== {m['key']} ({m['label']}) ===", flush=True)
        tps_all: list[float] = []
        ttft_all: list[float] = []
        purity_all: list[float] = []
        glue_tot = dup_tot = foreign_tot = 0
        samples: list[dict[str, Any]] = []
        per_judge_list: list[dict[str, Any]] = []

        for scen in prm["narrative"]:
            canon = build_gm_canon(scen["user"], scen["location"], scen["surroundings"],
                                   scen["hostiles"], scen["weapon"])
            system = _GM_SYSTEM.format(canon=canon)
            user = _GM_USER.format(history="(없음 — 첫 행동)", phase=scen["phase"],
                                   location=scen["location"], surroundings=scen["surroundings"],
                                   fact=scen["fact"], action=scen["user"])
            best_text = ""
            for _ in range(sampling["runs"]):
                try:
                    r = _stream_call(m["endpoint"], m["model"], system, user, sampling)
                except Exception as e:  # noqa: BLE001
                    print(f"  [{scen['key']}] ERR {e}", flush=True)
                    continue
                tps_all.append(r["tps"])
                ttft_all.append(r["ttft"])
                hp = metrics.hangul_purity(r["text"])
                purity_all.append(hp["purity_pct"])
                glue_tot += hp["glue_glitch"]
                dup_tot += hp["dup_glitch"]
                foreign_tot += hp["foreign_chars"]
                best_text = r["text"]
            # ★ 다judge 채점 — author≠judge(자기채점 배제, Cross-Model 원칙).
            #   judge harshness 보정·집계는 전 모델 수집 후 일괄(metrics.calibrate_aggregate).
            ctx = f"위치: {scen['location']} / 주변: {scen['surroundings']} / 행동: {scen['user']}"
            per_judge: dict[str, Any] = {}
            if best_text:
                for jk in by_key:
                    if jk == m["key"]:
                        continue  # 자기채점 배제
                    per_judge[jk] = _judge(by_key, jk, ctx, best_text)
            per_judge_list.append(per_judge)
            samples.append({"scenario": scen["key"], "text": best_text,
                            "per_judge": per_judge})
            print(f"  [{scen['key']}] tps={_mean(tps_all)} judges={list(per_judge)}",
                  flush=True)
        author_per_judge[m["key"]] = per_judge_list

        # 구조화 출력 준수율
        sch = prm["structured"]["schema"]
        req_keys = sch["required"]
        ok = 0
        cases = prm["structured"]["cases"]
        struct_samples: list[dict[str, Any]] = []
        sys_intent = "플레이어 입력을 게임 행동으로 분류해 JSON으로만 답하라."
        for case in cases:
            try:
                r = _post(m["endpoint"], {
                    "model": m["model"],
                    "messages": [{"role": "system", "content": sys_intent},
                                 {"role": "user", "content": case}],
                    "max_tokens": 200, "temperature": 0.2, "stream": False,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "response_format": {"type": "json_schema", "json_schema":
                                        {"name": "Intent", "schema": sch, "strict": True}},
                })
                txt = r["choices"][0]["message"].get("content") or ""
            except Exception:  # noqa: BLE001
                txt = ""
            v = metrics.validate_structured(txt, req_keys)
            ok += 1 if v["valid"] else 0
            struct_samples.append({"case": case, "valid": v["valid"],
                                   "parsed": v.get("parsed")})

        results["models"].append({
            "key": m["key"], "label": m["label"], "role": m["role"],
            "size_gb": m["size_gb"], "judge_by": "calibrated non-self",
            "latency": {"tps": _mean(tps_all), "ttft": _mean(ttft_all),
                        "tps_runs": len(tps_all)},
            "hangul": {"purity_pct": _mean(purity_all), "glue_glitch": glue_tot,
                       "dup_glitch": dup_tot, "foreign_chars": foreign_tot},
            "judge": {"axes": {}, "overall": 0.0},  # 사후 보정 집계로 채움
            "structured": {"pass": ok, "total": len(cases),
                           "pct": round(ok / len(cases) * 100, 1) if cases else 0.0},
            "samples": samples, "structured_samples": struct_samples,
        })

    # ★ author별 다judge 평균 — 자기채점 배제(per_judge 원점수는 샘플에 유지·투명)
    for entry in results["models"]:
        agg = metrics.aggregate_nonself(entry["key"],
                                        author_per_judge.get(entry["key"], []))
        entry["judge"] = {"axes": agg["axes"], "overall": agg["overall"]}
        entry["judge_by"] = "non-self mean (" + "/".join(agg["judges"]) + ")"

    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(f"DONE → {args.out}", flush=True)


if __name__ == "__main__":
    main()
