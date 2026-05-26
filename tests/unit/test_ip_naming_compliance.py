"""IP 정책 정합 검증 (★ fix(ip-naming) 정합)."""
from __future__ import annotations

from pathlib import Path


def test_no_rapdonia_in_production_code() -> None:
    """production 코드 '라프도니아' 잔존 X.

    허용 예외:
    - ip_masking.py: 감지 키워드 정의
    - loop.py: IP 차단 룰 주석
    - '→ 라스카니아'가 같은 줄에 있는 주석 (변환 설명)
    - 'IP 치환'이 같은 줄에 있는 주석
    """
    service_dir = Path("service")
    allow_files = {"ip_masking", "loop"}
    hits = []
    for f in service_dir.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        if any(a in str(f) for a in allow_files):
            continue
        text = f.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "라프도니아" not in line:
                continue
            if "→ 라스카니아" in line or "IP 치환" in line:
                continue
            hits.append(f"{f}: {line.strip()}")
    assert hits == [], "라프도니아 잔존:\n" + "\n".join(hits)


def test_no_bjorn_in_user_facing_files() -> None:
    """사용자 노출 핵심 파일 '비요른' 잔존 X (ep 인용 주석 허용)."""
    user_facing = [
        "service/api/v2_freeform_router.py",
        "service/api/v2_state_router.py",
        "service/game/cities/rascania.py",
        "service/canon/scenario.py",
    ]
    for path in user_facing:
        f = Path(path)
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if "비요른" not in line:
                continue
            stripped = line.strip()
            if stripped.startswith("#") and ("ep_" in stripped or "→" in stripped):
                continue
            raise AssertionError(f"비요른 잔존: {path}: {stripped}")


def test_starting_narrative_uses_rascania() -> None:
    """starting_narrative 라스카니아 정합."""
    from service.canon.races import Race
    from service.canon.scenario import ScenarioMode, build_starting_narrative

    msg = build_starting_narrative(ScenarioMode.BJORN, Race.BARBARIAN)
    assert "라스카니아" in msg
    assert "라프도니아" not in msg


def test_force_return_uses_rascania() -> None:
    """강제 귀환 narrative 라스카니아 정합."""
    from service.api.v2_freeform_router import _force_return_narrative

    narrative = _force_return_narrative()
    assert "라스카니아" in narrative
    assert "라프도니아" not in narrative


def test_ip_masking_keywords_complete() -> None:
    """KOREAN_IP_KEYWORDS 주요 명칭 포함."""
    from service.pipeline.ip_masking import KOREAN_IP_KEYWORDS

    expected = ["라프도니아", "비요른", "에르웬", "아이나르", "에쉬드", "두모카"]
    for kw in expected:
        assert kw in KOREAN_IP_KEYWORDS, f"누락: {kw}"


def test_generic_replacements_complete() -> None:
    """GENERIC_REPLACEMENTS 변환 정합."""
    from service.pipeline.ip_masking import GENERIC_REPLACEMENTS

    assert GENERIC_REPLACEMENTS["라프도니아"] == "라스카니아"
    assert GENERIC_REPLACEMENTS["비요른"] == "투르윈"
    assert GENERIC_REPLACEMENTS["에르웬"] == "실렌"
    assert GENERIC_REPLACEMENTS["아이나르"] == "카이라"
    assert GENERIC_REPLACEMENTS["에쉬드"] == "셰인"


def test_mask_text_raphdonia() -> None:
    """mask_text 라프도니아 → 라스카니아 변환 정합."""
    from service.pipeline.ip_masking import mask_text

    result = mask_text("라프도니아 차원광장에 섰다.")
    assert "라스카니아" in result.masked
    assert "라프도니아" not in result.masked
    assert result.masking_applied is True


def test_rascania_city_name() -> None:
    """RASCANIA city_name 라스카니아 정합."""
    from service.game.cities.rascania import RASCANIA

    assert RASCANIA.city_name == "라스카니아"
    assert RASCANIA.city_id == "rascania"
