"""SGLang MTP 한국어 benchmark (★ Phase A.3-a).

한국어 prompt 5개 × 본문 어조 generation 측정.

OpenAI-compatible /v1/chat/completions endpoint 호출.
container log 의 "Decode batch ... accept len ... accept rate ..." 행을 파싱하여
spec decode 통계 평균을 함께 기록.

Output: JSON file (★ docs/phase_a/*.json 보관용)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

# 한국어 prompt 5개 (★ 본문 어조 정합).
PROMPTS: list[str] = [
    "비요른이 횃불을 켜자 어둠이 걷히며",
    "한스가 천천히 다가왔다. 그의 눈빛은",
    "균열 너머에서 들리는 그르렁대는 소리. 비요른은",
    "마석 거래소의 노인은 본인을 보더니",
    "에르웬의 손길이 비석을 어루만지자",
]

SYSTEM_PROMPT = (
    "당신은 한국어 던전 탐험 소설의 narrator 입니다. "
    "이어지는 문장을 본문 어조 (조선·중세·서사) 로 100-300자 범위에서 자연스럽게 이어가십시오. "
    "표 / 코드 / 영어 / 메타 설명 금지."
)

DECODE_RE = re.compile(
    r"accept len:\s*(?P<acc_len>\d+\.\d+).*?"
    r"accept rate:\s*(?P<acc_rate>\d+\.\d+).*?"
    r"gen throughput \(token/s\):\s*(?P<throughput>\d+\.\d+)"
)

TIMESTAMP_RE = re.compile(r"\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")


@dataclass
class PromptResult:
    prompt: str
    elapsed_s: float
    completion_tokens: int
    prompt_tokens: int
    tok_per_s: float
    text_head: str


@dataclass
class BenchResult:
    label: str
    endpoint: str
    model: str
    max_tokens: int
    temperature: float
    runs: list[PromptResult] = field(default_factory=list)
    spec_accept_rate_avg: float | None = None
    spec_accept_len_avg: float | None = None
    spec_throughput_avg: float | None = None
    spec_sample_count: int = 0
    started_at: str = ""
    finished_at: str = ""

    def summary(self) -> dict[str, Any]:
        elapsed = [r.elapsed_s for r in self.runs]
        tokens = [r.completion_tokens for r in self.runs]
        tok_s = [r.tok_per_s for r in self.runs if r.tok_per_s > 0]
        return {
            "label": self.label,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "endpoint": self.endpoint,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "elapsed_total_s": sum(elapsed),
            "elapsed_avg_s": sum(elapsed) / max(1, len(elapsed)),
            "tokens_total": sum(tokens),
            "tokens_avg": sum(tokens) / max(1, len(tokens)),
            "tok_per_s_avg": sum(tok_s) / max(1, len(tok_s)),
            "tok_per_s_min": min(tok_s) if tok_s else 0,
            "tok_per_s_max": max(tok_s) if tok_s else 0,
            "spec_accept_rate_avg": self.spec_accept_rate_avg,
            "spec_accept_len_avg": self.spec_accept_len_avg,
            "spec_throughput_avg": self.spec_throughput_avg,
            "spec_sample_count": self.spec_sample_count,
            "per_prompt": [
                {
                    "prompt": r.prompt,
                    "elapsed_s": r.elapsed_s,
                    "completion_tokens": r.completion_tokens,
                    "prompt_tokens": r.prompt_tokens,
                    "tok_per_s": r.tok_per_s,
                    "text_head": r.text_head,
                }
                for r in self.runs
            ],
        }


def run_one(
    client: httpx.Client,
    endpoint: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> PromptResult:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    t0 = time.perf_counter()
    resp = client.post(
        f"{endpoint}/v1/chat/completions",
        json=body,
        timeout=600.0,
    )
    elapsed = time.perf_counter() - t0
    resp.raise_for_status()
    payload = resp.json()
    choice = payload["choices"][0]
    text = choice["message"].get("content") or ""
    usage = payload.get("usage", {})
    comp = int(usage.get("completion_tokens", 0))
    pt = int(usage.get("prompt_tokens", 0))
    tok_s = (comp / elapsed) if elapsed > 0 else 0.0
    return PromptResult(
        prompt=prompt,
        elapsed_s=elapsed,
        completion_tokens=comp,
        prompt_tokens=pt,
        tok_per_s=tok_s,
        text_head=text[:120],
    )


def parse_container_decode_lines(
    container: str,
    since_iso: str,
) -> tuple[list[float], list[float], list[float]]:
    """`docker logs --since ISO` 출력에서 Decode batch 행을 파싱."""
    try:
        out = subprocess.run(
            [
                "docker",
                "logs",
                container,
                "--since",
                since_iso,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], [], []
    lines = (out.stdout + out.stderr).splitlines()
    acc_rates: list[float] = []
    acc_lens: list[float] = []
    throughputs: list[float] = []
    for ln in lines:
        if "Decode batch" not in ln:
            continue
        m = DECODE_RE.search(ln)
        if not m:
            continue
        acc_lens.append(float(m.group("acc_len")))
        acc_rates.append(float(m.group("acc_rate")))
        throughputs.append(float(m.group("throughput")))
    return acc_rates, acc_lens, throughputs


def main() -> int:
    parser = argparse.ArgumentParser(description="SGLang MTP 한국어 bench")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8081",
        help="SGLang endpoint base",
    )
    parser.add_argument(
        "--model",
        default="qwen3.6-27b",
        help="--served-model-name 일치",
    )
    parser.add_argument(
        "--container",
        default="sglang-narrative-27b-fp8-mtp",
        help="docker container name (★ spec stats 추출용)",
    )
    parser.add_argument(
        "--label",
        default="baseline",
        help="이 측정의 식별 라벨 (★ 결과 JSON 의 label field)",
    )
    parser.add_argument("--max-tokens", type=int, default=400)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="각 prompt 반복 횟수 (★ default 1 → 5 generation)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="결과 JSON 출력 경로",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="prompt 1회 warmup (★ measurement 제외)",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    since_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 5))

    result = BenchResult(
        label=args.label,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        started_at=started,
    )

    with httpx.Client(headers={"Content-Type": "application/json"}) as client:
        if args.warmup:
            print("[warmup] 1 prompt …", flush=True)
            _ = run_one(
                client,
                args.endpoint,
                args.model,
                PROMPTS[0],
                args.max_tokens,
                args.temperature,
            )
        for run_idx in range(args.runs):
            for i, prompt in enumerate(PROMPTS):
                print(
                    f"[run {run_idx + 1}/{args.runs}] prompt {i + 1}/5 …",
                    flush=True,
                )
                pr = run_one(
                    client,
                    args.endpoint,
                    args.model,
                    prompt,
                    args.max_tokens,
                    args.temperature,
                )
                print(
                    f"  elapsed={pr.elapsed_s:.2f}s  tok={pr.completion_tokens}"
                    f"  tok/s={pr.tok_per_s:.2f}",
                    flush=True,
                )
                result.runs.append(pr)

    acc_rates, acc_lens, throughputs = parse_container_decode_lines(
        args.container, since_iso
    )
    if acc_rates:
        result.spec_accept_rate_avg = sum(acc_rates) / len(acc_rates)
        result.spec_accept_len_avg = sum(acc_lens) / len(acc_lens)
        result.spec_throughput_avg = sum(throughputs) / len(throughputs)
        result.spec_sample_count = len(acc_rates)

    result.finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    summary = result.summary()
    out_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"=== {args.label} ===")
    print(f"runs:              {len(result.runs)}")
    print(f"elapsed avg:       {summary['elapsed_avg_s']:.2f} s")
    print(f"tok avg:           {summary['tokens_avg']:.1f}")
    print(f"tok/s avg:         {summary['tok_per_s_avg']:.2f}")
    if result.spec_sample_count:
        print(
            f"spec accept_rate:  {result.spec_accept_rate_avg:.3f}  "
            f"(n={result.spec_sample_count})"
        )
        print(f"spec accept_len:   {result.spec_accept_len_avg:.3f}")
        print(f"spec throughput:   {result.spec_throughput_avg:.2f} tok/s")
    else:
        print("spec stats:        n/a (★ MTP off 또는 log 없음)")
    print(f"\noutput: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
