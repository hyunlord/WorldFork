"""A2.2 RAG 검색 점검 CLI — get_grounding 결과(마스킹 top-k)를 출력(운영 점검용).

원작 정합·관련성을 사람이 눈으로 확인하는 실사용 도구. 원작명은 mask_text로 변환명만 출력(IP).
인덱스 .local/rag 필요. 실행: python -m tools.rag.query "성인식 무기 선택" [--lo 1 --hi 20 --k 4]
"""

from __future__ import annotations

import argparse

from service.sim.rag_retrieval import get_grounding, index_available


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 검색 점검(마스킹 top-k 출력)")
    parser.add_argument("query", help="검색 쿼리(장면 컨텍스트)")
    parser.add_argument("--lo", type=int, default=1, help="episode 범위 하한")
    parser.add_argument("--hi", type=int, default=20, help="episode 범위 상한")
    parser.add_argument("--k", type=int, default=4, help="top-k")
    args = parser.parse_args()

    if not index_available():
        print("인덱스 없음(.local/rag) — 먼저 `python -m tools.rag.build_index` 실행.")
        return
    passages = get_grounding(args.query, episode_range=(args.lo, args.hi), top_k=args.k)
    if not passages:
        print("검색 결과 없음(범위 내 매칭 X).")
        return
    for p in passages:
        snippet = p.text[:100].replace("\n", " ")
        print(f"[ep{p.episode:04d} score={p.score:.3f}] {snippet}")


if __name__ == "__main__":
    main()
