"""테스트 공통 픽스처 — A1.2 이후 엔진이 활성 콘텐츠팩을 require하므로 전 테스트에 WorldFork 주입.

프로덕션은 app.py lifespan이 set_active_pack을 호출한다. 유닛/통합 테스트는 app을 거치지
않고 엔진 함수를 직접 부르므로, 여기 오토유즈 픽스처가 WORLDFORK_PACK을 설정/해제한다.
"""

from collections.abc import Iterator

import pytest

from service.content.worldfork import WORLDFORK_PACK
from service.engine.content_pack import clear_active_pack, set_active_pack


@pytest.fixture(autouse=True)
def _active_worldfork_pack() -> Iterator[None]:
    set_active_pack(WORLDFORK_PACK)
    yield
    clear_active_pack()
