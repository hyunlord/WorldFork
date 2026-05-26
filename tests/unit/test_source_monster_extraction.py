"""I-G3 source_monster 추출 로직 단위 테스트."""
from scripts.extract_source_monster import extract_source_monster


def test_essence_pattern_simple() -> None:
    assert extract_source_monster("고블린 정수") == "고블린"
    assert extract_source_monster("오크 정수") == "오크"
    assert extract_source_monster("서리늑대 정수") == "서리늑대"


def test_essence_pattern_multiword() -> None:
    assert extract_source_monster("고블린 궁수 정수") == "고블린 궁수"
    assert extract_source_monster("화염 마법사 정수") == "화염 마법사"


def test_essence_pattern_ui_josa() -> None:
    """'X의 정수' → 말미 '의' 제거."""
    assert extract_source_monster("서리늑대의 정수") == "서리늑대"
    assert extract_source_monster("히프라마전트의 정수") == "히프라마전트"
    assert extract_source_monster("눈물의 군주의 정수") == "눈물의 군주"
    assert extract_source_monster("오우거의 정수") == "오우거"


def test_monster_name_self() -> None:
    assert extract_source_monster("고블린 궁수") == "고블린 궁수"
    assert extract_source_monster("서리늑대") == "서리늑대"
    assert extract_source_monster("오크") == "오크"


def test_exception_maseok() -> None:
    assert extract_source_monster("9등급 마석") is None
    assert extract_source_monster("7등급 마석") is None
    assert extract_source_monster("마석") is None


def test_exception_currency_stone() -> None:
    assert extract_source_monster("7천만 스톤") is None
    assert extract_source_monster("스톤") is None


def test_exception_numbers_prefix() -> None:
    assert extract_source_monster("넘버스") is None
    assert extract_source_monster("넘버스 아이템") is None
    assert extract_source_monster("No.7777 가르파스 목걸이") is None


def test_exception_exact() -> None:
    assert extract_source_monster("정수 결정") is None
    assert extract_source_monster("던전앤스톤") is None


def test_empty_name() -> None:
    assert extract_source_monster("") is None
    assert extract_source_monster("   ") is None


def test_whitespace_stripped() -> None:
    assert extract_source_monster("  고블린 정수  ") == "고블린"
    assert extract_source_monster("  서리늑대  ") == "서리늑대"
