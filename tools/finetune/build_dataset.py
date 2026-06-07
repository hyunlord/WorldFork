"""파인튜닝 데이터 — 원작 본문 → [게임로그→본문] instruction-output 쌍 (LLM-as-labeler).

원작 본문(.local/novel_bodies/ — ★ 저작권: gitignored, 산출물도 .local)을 3-4문장 청킹,
27B labeler로 instruction(플레이어 행동/상황) 역설계, output=본문 원문(문체 학습). 함정 회피:
격식체(챗봇 말투) 필터 + 짧은/대화과다 청크 제외. 출력 .local/finetune/gm_narrative.jsonl.

사용: python tools/finetune/build_dataset.py --limit 5   (--limit 0 = 전체)
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

BODIES = Path(".local/novel_bodies/ntk01_novel_20_bodies")
OUT = Path(".local/finetune/gm_narrative.jsonl")
# labeler 엔드포인트 — 27B(품질) / gemma(8085, ~5배 빠름, 대량 생성용).
LABELERS = {
    "27b": ("http://localhost:8081", "qwen3.6-27b"),
    "gemma": ("http://localhost:8085", "gemma"),
    "9b": ("http://localhost:8083", "qwen35-9b-q3"),
}
LABELER = LABELERS["27b"]

# 격식체(챗봇 말투) 종결 — 문어체 GM 데이터에서 배제
_CHATTY = re.compile(r"(해요|예요|에요|네요|거든요|더라고요|습니다만요)[.!?\"']")
_SENT = re.compile(r"(?<=[다요죠])\.\s+|(?<=[.!?])\s+")


def load_bodies(limit: int) -> list[str]:
    files = sorted(BODIES.glob("episode_*.txt"))
    # 도입부(현대 배경) 편중 회피 — 5화 이후를 전 구간 고르게 샘플(문체 다양).
    files = files[4:]
    if limit and limit < len(files):
        stride = max(1, len(files) // limit)
        files = files[::stride][:limit]
    out: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        # 헤더/저작권/메타 줄 제거(제목·URL·ⓒ·화수 표기) — 서사 본문만
        lines = [
            ln for ln in text.splitlines()
            if ln.strip()
            and "ⓒ" not in ln
            and "http" not in ln
            and not re.match(r".{0,40}\d+\s*화\b", ln)
        ]
        out.append("\n".join(lines))
    return out


def chunk(body: str, lo: int = 3, hi: int = 4) -> list[str]:
    sents = [s.strip() for s in _SENT.split(body) if len(s.strip()) > 8]
    out: list[str] = []
    for i in range(0, len(sents), hi):
        grp = sents[i:i + hi]
        if len(grp) >= lo:
            out.append(" ".join(grp))
    return out


def is_munche(text: str) -> bool:
    """문어체(서사)인가 — 격식체(챗봇) 종결 과다면 제외."""
    return len(_CHATTY.findall(text)) == 0 and len(text) >= 40


def label(chunk_text: str) -> str | None:
    """본문 청크 → 플레이어 행동/상황(instruction) 역설계. 실패 시 None."""
    system = (
        "당신은 한국어 던전 게임 로그 설계자다. 주어진 소설 서사 한 토막을 보고, "
        "그 서사를 끌어낼 법한 '플레이어 행동/상황'을 1문장으로 역설계하라. "
        "메타 설명 없이 행동/상황만 출력한다."
    )
    user = f"서사:\n{chunk_text}\n\n플레이어 행동/상황 1문장:"
    body = json.dumps({
        "model": LABELER[1],
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": 80, "temperature": 0.4, "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(f"{LABELER[0]}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=60))
    except Exception:  # noqa: BLE001
        return None
    out = (r["choices"][0]["message"].get("content") or "").strip()
    return out or None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="에피소드 수(0=전체)")
    ap.add_argument("--max-pairs", type=int, default=20, help="생성 쌍 상한(검증용)")
    ap.add_argument("--labeler", choices=list(LABELERS), default="27b",
                    help="역설계 labeler — 27b(품질)/gemma(빠름)/9b")
    args = ap.parse_args()
    global LABELER
    LABELER = LABELERS[args.labeler]
    OUT.parent.mkdir(parents=True, exist_ok=True)

    pairs: list[dict[str, str]] = []
    kept = filtered = 0
    for body in load_bodies(args.limit):
        for ch in chunk(body):
            if len(pairs) >= args.max_pairs:
                break
            if not is_munche(ch):
                filtered += 1
                continue
            instr = label(ch)
            if instr is None:
                continue
            pairs.append({"instruction": instr, "output": ch})
            kept += 1
            print(f"[{kept}] instr={instr[:40]} | out={ch[:40]}...", flush=True)
        if len(pairs) >= args.max_pairs:
            break

    with OUT.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"DONE: {kept} 쌍 (격식 필터 제외 {filtered}) → {OUT}", flush=True)


if __name__ == "__main__":
    main()
