"""Build topic ↔ episode mapping INDEX.md for canon audit.

본 commit (Phase 9.19-a):
- 740 episodes scan, keyword 본격 keyword → episode list 본격
- audit + 본격 본격 본격 본격 본격 본격 navigation 본격
- 본격 본격 본격 본격 keyword 본격 본격 본격 KEYWORDS dict 본격 본격

사용:
  python scripts/build_canon_index.py
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

# 핵심 keyword: audit 본격 본격 + game design 본격 정합 검증 본격
KEYWORDS: dict[str, list[str]] = {
    # ─── System: 정수 / 마석 / 등급 ───
    "정수": ["정수", "흡수", "정수 슬롯", "슬롯"],
    "마석": ["마석", "정화석", "8등급 마석", "9등급 마석"],
    "등급": ["9등급", "8등급", "7등급", "6등급", "5등급", "4등급",
            "3등급", "2등급", "1등급", "0등급", "계층군주"],
    "스킬": ["고유 능력", "고유능력", "액티브", "패시브"],
    "장비": ["하프 아머", "검", "활", "방어구", "넘버스"],
    "시간": ["7일", "168시간", "174시간", "재진입"],
    "균열": ["균열", "수호자", "변종"],
    "신성력": ["신성력", "삼신교", "신전", "사제"],
    # ─── Floor / Region ───
    "1층": ["1층", "수정 동굴", "수정동굴", "비석 공동", "포탈"],
    "2층": ["2층", "안개", "망자의 땅"],
    "균열 4종": ["핏빛성채", "빙하굴", "녹색탄광", "강철의 묘"],
    # ─── Town (Rapdonia) ───
    "라프도니아": ["라프도니아", "차원광장", "7구역"],
    "노아르크": ["노아르크"],
    "카루이": ["카루이"],
    # ─── Game mechanics ───
    "약탈자": ["약탈자", "수정 연합", "현상금"],
    "밤친구": ["밤친구", "임시 협력"],
    "불침번": ["불침번"],
    "혼자선잠": ["선잠"],
    "맹세": ["맹세"],
    "절친": ["절친", "친구"],
    "호감도": ["호감도"],
    "메시지스톤": ["메시지 스톤", "메시지스톤"],
    "도서관": ["도서관", "라비기온", "파르시티에브"],
    # ─── 주요 인물 (1-2층) ───
    "비요른": ["비요른"],
    "에르웬": ["에르웬"],
    "한스": ["한스"],
    "아이나르": ["아이나르"],
    "미샤": ["미샤"],
    "라그나": ["라그나"],
    # ─── 종족 ───
    "바바리안": ["바바리안"],
    "요정": ["요정"],
    "드워프": ["드워프"],
    "수인": ["수인"],
    "용인족": ["용인족", "용인"],
    # ─── 부상 / 회복 (★ 9.3/9.6/9.10) ───
    "부상": ["부상", "상처"],
    "흉터": ["흉터", "흔적"],
    "절단": ["절단"],
    # ─── 마을 시간 (★ 9 mechanism) ───
    "월차": ["매월 1일", "30일"],
}


def main() -> int:
    ep_dir = Path(".local/canon/episodes")
    out_path = Path(".local/canon/INDEX.md")
    upload_path = Path(".local/canon/upload_ready/INDEX.md")

    eps = sorted(ep_dir.glob("episode_*.txt"))
    if not eps:
        print(f"❌ No episodes in {ep_dir}")
        return 1

    print(f"scanning {len(eps)} episodes for {len(KEYWORDS)} topics...")

    mapping: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for ep_path in eps:
        ep_num = ep_path.stem.split("_")[1].lstrip("0") or "0"
        content = ep_path.read_text(encoding="utf-8")
        for topic, keys in KEYWORDS.items():
            for k in keys:
                if k in content:
                    mapping[topic][k].append(ep_num)

    lines: list[str] = [
        "# Canon INDEX — Topic ↔ Episode Mapping",
        "",
        "본 INDEX 본격 audit + canon 본격 본격 빠른 navigation 본격.",
        "740 episodes scan 결과 본격 keyword 본격 episode 번호 list.",
        "",
        f"- 총 episodes: {len(eps)}",
        f"- 총 topics: {len(KEYWORDS)}",
        "",
    ]

    for topic in sorted(mapping.keys()):
        lines.append(f"## {topic}")
        lines.append("")
        keys = sorted(mapping[topic].items(), key=lambda x: -len(x[1]))
        for k, ep_nums in keys:
            if not ep_nums:
                continue
            preview = ", ".join(ep_nums[:25])
            tail = (
                f" ... (+{len(ep_nums) - 25})"
                if len(ep_nums) > 25
                else ""
            )
            lines.append(f"- **{k}** ({len(ep_nums)}건): {preview}{tail}")
        lines.append("")

    out_text = "\n".join(lines)
    out_path.write_text(out_text, encoding="utf-8")
    # Also copy to upload_ready/
    upload_path.write_text(out_text, encoding="utf-8")
    print(f"✓ {out_path} ({len(out_text)} chars)")
    print(f"✓ {upload_path} (★ Claude.ai upload)")

    # Summary
    total_hits = sum(
        sum(len(v) for v in t.values()) for t in mapping.values()
    )
    print(f"\nsummary: {total_hits} keyword hits across {len(eps)} episodes")
    for topic, keys in mapping.items():
        topic_hits = sum(len(v) for v in keys.values())
        print(f"  {topic:15s}: {topic_hits} hits")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
