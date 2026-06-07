"""평가 지표 함수 (★ 플러그인 — 모델 무관, 확장 가능).

순수 측정 함수: 한글 순도/글리치(정량), G-Eval judge 프롬프트/파싱, 구조화 검증.
latency(TTFT/TPS)는 스트리밍 호출에서 측정하므로 run_eval가 담당.
"""

from __future__ import annotations

import json
import re
from typing import Any

# 비한국어 누출 — 한자(CJK) / 라틴 알파벳
_CJK = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[A-Za-z]")
_HANGUL = re.compile(r"[가-힣]")
# 공백 누락 글루 — 조사 직후 동사 어간(관찰된 글리치 패턴)
_GLUE = re.compile(r"(?:을|를|이|가|은|는|에)(?:내뿜|뿜어|휘두|내리|움켜|베어|찔러|울려|감싸)")
# 인접 반복 — 동굴동굴
_DUP = re.compile(r"([가-힣]{2,4})\1")


def hangul_purity(text: str) -> dict[str, Any]:
    """한글 순도 정량 — 비한국어 누출/글리치 검출.

    purity_pct: 한글 / (한글+한자+라틴) × 100. foreign_chars: 한자+라틴 수.
    glue/dup: 글리치 발생 수. clean: 글리치·누출 모두 0.
    """
    han = len(_HANGUL.findall(text))
    cjk = len(_CJK.findall(text))
    lat = len(_LATIN.findall(text))
    denom = han + cjk + lat
    purity = (han / denom * 100.0) if denom else 100.0
    glue = len(_GLUE.findall(text))
    dup = len(_DUP.findall(text))
    return {
        "purity_pct": round(purity, 2),
        "foreign_chars": cjk + lat,
        "cjk": cjk,
        "latin": lat,
        "glue_glitch": glue,
        "dup_glitch": dup,
        "clean": (cjk == 0 and lat == 0 and glue == 0 and dup == 0),
    }


# G-Eval 4축 — 1~5 정수. judge가 narrative를 평가.
JUDGE_AXES = ("문체", "persona", "고증", "시스템")

_JUDGE_SYSTEM = (
    "당신은 한국어 던전 생존 게임 GM 서사의 엄정한 평가자다. "
    "아래 서사를 4축으로 1~5 정수 채점하라(5=최상). JSON만 출력한다.\n"
    "- 문체: 1인칭('나는') 조선·중세풍 문어체 일관성\n"
    "- persona: 주인공 비요른(흑곰족 거구 바바리안, 이한수 빙의)·무기 일관\n"
    "- 고증: 제시된 세계 정보(위치/적) 정합, 근거 없는 설정 날조 없음\n"
    "- 시스템: 메타 발화·규칙 설명·AI 자칭 없음(서사 몰입 유지)\n"
    '출력 형식: {"문체":N,"persona":N,"고증":N,"시스템":N,"한줄평":"..."}'
)


def build_judge_prompt(context: str, narrative: str) -> tuple[str, str]:
    """judge 호출용 (system, user). context=세계정보/행동, narrative=평가 대상."""
    user = f"## 세계 정보·행동\n{context}\n\n## 평가 대상 서사\n{narrative}\n\nJSON 채점:"
    return _JUDGE_SYSTEM, user


def parse_judge(text: str) -> dict[str, Any] | None:
    """judge 출력에서 4축 점수 파싱. 실패 시 None."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m is None:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not all(ax in obj for ax in JUDGE_AXES):
        return None
    out: dict[str, Any] = {}
    for ax in JUDGE_AXES:
        try:
            v = int(obj[ax])
        except (ValueError, TypeError):
            return None
        out[ax] = max(1, min(5, v))
    out["한줄평"] = str(obj.get("한줄평", ""))[:200]
    return out


def aggregate_nonself(
    author: str, per_judge_list: list[dict[str, dict[str, Any] | None]],
) -> dict[str, Any]:
    """author별 다judge 평균 — 자기채점 배제(author≠judge, Cross-Model 원칙).

    per_judge_list: scenario별 {judge: {축:점수}|None}. 생성 모델 자신의 채점은 제외하고
    나머지 judge 점수를 축별 평균. judge별 편향(예: 27B harsh)은 호출자가 per_judge
    원점수로 추적·해석한다(judge_cross 측정에 정량화). 평균은 단순·검증가능하게 유지.
    """
    import statistics

    # 자기채점 제외한 유효 judge 점수만 수집(누락/None은 애초에 배제 — 0.0 대입 안 함)
    axis_vals: dict[str, list[float]] = {ax: [] for ax in JUDGE_AXES}
    judges: set[str] = set()
    for per_judge in per_judge_list:
        for judge_key, score in per_judge.items():
            if score is None or judge_key == author:
                continue
            judges.add(judge_key)
            for ax in JUDGE_AXES:
                if ax in score:
                    axis_vals[ax].append(float(score[ax]))
    # 데이터가 실재하는 축만 평균(누락 축은 결과에서 생략 — 0.0 placeholder 미사용)
    axes = {ax: round(statistics.mean(vals), 2)
            for ax, vals in axis_vals.items() if vals}
    overall = round(statistics.mean(axes.values()), 2) if axes else None
    return {"axes": axes, "overall": overall, "judges": sorted(judges)}


def validate_structured(text: str, required: list[str]) -> dict[str, Any]:
    """구조화 출력 검증 — valid JSON object + required 키 충족."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m is None:
        return {"valid": False, "reason": "no_json"}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"valid": False, "reason": "parse_fail"}
    if not isinstance(obj, dict):
        return {"valid": False, "reason": "not_object"}
    miss = [k for k in required if k not in obj]
    return {"valid": not miss, "reason": ("missing:" + ",".join(miss)) if miss else "ok",
            "parsed": obj}
