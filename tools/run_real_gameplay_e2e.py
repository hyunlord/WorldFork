"""실 게임 E2E — 실질적 플레이 작동 검증 (★ harness 재설계, 검증 갭 해소).

run_browser_e2e(흐름: 클릭→페이지전환→input 존재→freeform 200)와 달리, 실 게임
'작동'을 검증한다 — 게임 화면이 무엇을 보여주는가.

검증 항목:
  - scenario_origin_naming: 게임 화면 원작 명칭 (비요른 — 투르윈 노출 X)
  - no_starting_party: 시작 시 파티원 0 (실렌·한스 노출 X)
  - session_scenario_reflected: 생성 시나리오가 화면 반영 (바바리안 HP 120)
  - chat_freeform_works: 채팅 입력 → freeform_action 200 (hard)

★ xfail 메커니즘 (검증 갭 핵심 해소):
  현재 알려진 결함(frontend↔session 단절 → v2_state_router global default
  '투르윈+실렌+던전' — project_manual_play_diagnosis) 항목은 is_xfail=True로
  예상된 실패 처리(점수 만점). 검증은 존재하되 ship을 막지 않는다.
  재검토가 결함을 해소하면 is_xfail=False로 전환해 실제 통과를 강제한다.
  xfail 항목이 예상외로 통과하면 XPASS 경고 — is_xfail 해제 신호.

출력: GAMEPLAY_E2E_SCORE=<0-30> + XFAIL / XPASS / HARD_FAIL 리스트.
Exit: 0 = hard 항목 전부 통과(ship 가능), 1 = hard fail(ship 불가).

사용:
  python tools/run_real_gameplay_e2e.py
  python tools/run_real_gameplay_e2e.py --frontend-url http://100.70.109.50:4000
  python tools/run_real_gameplay_e2e.py --no-headless   # 디버깅
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    """실 게임 검증 항목."""

    name: str
    points: int
    is_xfail: bool  # True = 현재 알려진 결함(재검토 대기), 예상 실패 → 만점
    desc: str


CHECKS: tuple[Check, ...] = (
    # ★ 화면 내용 검증 재설계 (합 30) — HTTP 200/렌더가 아니라 사용자가 보는 텍스트.
    #   manual play 결함(성인식 미표시/IP 노출/데모 placeholder/추천 부재) 정면 검증.
    Check("scenario_origin_naming", 2, False, "게임 화면 원작 명칭 (투르윈 노출 X)"),
    Check("session_scenario_reflected", 2, False, "생성 시나리오 화면 반영 (바바리안 HP 120)"),
    Check("no_starting_party", 3, False, "시작 파티원 0 (실렌·한스 X — 성인식 마을)"),
    Check("chat_freeform_works", 5, False, "채팅 → narrative 화면 렌더 + IP 미노출 (라스카니아 X)"),
    Check("background_rendered", 1, False, "배경 이미지 렌더링 (ComfyUI PNG, ASCII 단독 X)"),
    Check("progression_displayed", 2, False, "진행 표시 (영혼력 10/LV 1 — 어댑터 연결, 0 고정 X)"),
    Check("weapon_choice_reflected", 3, False, "성인식 무기 선택 → 장착 반영 (방패 고정 X)"),
    Check("menu_map_works", 2, False, "메뉴 지도 onClick → MapPanel (floor/rift 4종)"),
    Check("menu_help_works", 2, False, "메뉴 도움말 onClick → HelpPanel (조작/시스템)"),
    Check("time_limit_consistent", 1, False, "시간 한도 168h 표시 (174 불일치 X — 7일 정합)"),
    Check("character_scrollable", 1, False, "character 긴 콘텐츠 스크롤 가능 (생성 버튼 도달)"),
    # ★ 신규 — manual play 결함 화면 내용 검증 (검증 갭 닫기)
    Check("start_narrative_shown", 3, False, "첫 화면 성인식 narrative 노출 (generic 안내 X)"),
    Check("no_demo_placeholder", 1, False, "placeholder 데모(한스·WASD) 부재"),
    Check("suggested_actions_shown", 2, False, "추천 행동 버튼 노출 (placeholder만 X)"),
)
MAX_SCORE = sum(c.points for c in CHECKS)


async def _measure(frontend_url: str, headless: bool) -> dict[str, bool]:
    """playwright로 실 게임 화면 측정 → 항목별 통과 여부."""
    from playwright.async_api import async_playwright

    results: dict[str, bool] = {}
    freeform: dict[str, int | None] = {"code": None}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await (await browser.new_context()).new_page()
        page.on(
            "response",
            lambda r: (
                freeform.__setitem__("code", r.status)
                if "/api/v2/freeform_action" in r.url
                else None
            ),
        )
        try:
            await page.goto(frontend_url, timeout=15000, wait_until="domcontentloaded")
            link = await page.wait_for_selector(
                "a:has-text('새 게임')", timeout=10000, state="visible"
            )
            assert link is not None
            await link.click()
            await page.wait_for_url("**/character", timeout=10000)
            # ★ character 스크롤 도달 (manual play 결함) — 작은 viewport에서 무기 10종으로
            #   콘텐츠가 넘칠 때 생성 버튼까지 스크롤 가능한지. body overflow:hidden이면
            #   scrollTo 무효(after==before)이면서 콘텐츠는 넘쳐(scrollHeight>clientHeight)
            #   생성 버튼 도달 불가 = 게임 시작 차단.
            await page.set_viewport_size({"width": 768, "height": 600})
            await page.wait_for_timeout(300)
            results["character_scrollable"] = await page.evaluate(
                """() => {
                    const el = document.scrollingElement || document.documentElement;
                    const overflowing = el.scrollHeight > el.clientHeight + 1;
                    if (!overflowing) return true;  // 콘텐츠가 한 화면 — 막힘 아님
                    const before = el.scrollTop;
                    el.scrollTo(0, el.scrollHeight);
                    const moved = el.scrollTop > before;
                    el.scrollTo(0, before);
                    return moved;  // 넘치면 실제 스크롤 이동해야 통과
                }"""
            )
            await page.set_viewport_size({"width": 1280, "height": 720})
            await page.wait_for_timeout(200)
            # ★ 성인식 무기 선택 (★ ep_0002) — 양손 도끼 (방패 default 아님 → 반영 검증)
            try:
                weapon_btn = await page.wait_for_selector(
                    '[data-testid="weapon-option-양손 도끼"]',
                    timeout=8000,
                    state="visible",
                )
                if weapon_btn is not None:
                    await weapon_btn.click()
            except Exception:
                pass  # WeaponSelector 미표시 시 default 방패 진행
            btn = await page.wait_for_selector(
                "button:has-text('미궁으로')", timeout=10000, state="visible"
            )
            assert btn is not None
            await btn.click()
            await page.wait_for_url("**/game", timeout=20000)
            await page.wait_for_selector("input", timeout=15000, state="visible")
            await page.wait_for_timeout(1800)  # hydration + state fetch 안정화

            body = await page.locator("body").inner_text()
            results["scenario_origin_naming"] = "투르윈" not in body
            results["no_starting_party"] = ("실렌" not in body) and ("한스" not in body)
            results["session_scenario_reflected"] = "120" in body
            # ★ 첫 화면 성인식 narrative 노출 (createCharacter starting_narrative 표시).
            #   BJORN 성인식 = 부족장 선언 → "부족장/성지/성년/전사" 중 하나 노출 +
            #   generic 안내("행동을 입력해 모험을 시작하세요") 부재.
            results["start_narrative_shown"] = (
                any(kw in body for kw in ("부족장", "성지", "성년", "전사"))
                and "행동을 입력해 모험을 시작하세요" not in body
            )
            # ★ placeholder 데모(한스·WASD) 부재 — session 정합 placeholder.
            ph = await page.locator("input").first.get_attribute("placeholder")
            results["no_demo_placeholder"] = (
                ph is not None and "한스" not in ph and "WASD" not in ph
            )
            # ★ 추천 행동 버튼 노출 (placeholder 힌트만 X → 클릭 가능 3항목).
            sa_count = await page.locator('[data-testid="suggested-action"]').count()
            results["suggested_actions_shown"] = sa_count >= 3
            # ★ 시간 한도 정합 (끊김 4) — 7일=168h (backend dungeon_clock 기준).
            #   StatusBar 시간 표시에 168h 노출 + 옛 174h 불일치 부재 검증.
            results["time_limit_consistent"] = ("168h" in body) and ("174h" not in body)
            # ★ 배경 이미지 — ComfyUI PNG 렌더링 (성인식 마을 floor 0 → ui_main_bg)
            bg_style = await page.locator(
                '[data-testid="game-background"]'
            ).first.get_attribute("style")
            results["background_rendered"] = (
                bg_style is not None and "ui_main_bg" in bg_style
            )
            # ★ 성인식 무기 선택 반영 (★ ep_0002) — 선택 무기(양손 도끼)가 장착/소지 표시.
            #   방패 default 아닌 무기 선택 → 어댑터 equipment + inventory 반영 검증.
            results["weapon_choice_reflected"] = "양손 도끼" in body
            # ★ 진행 시스템 — 어댑터 연결 (영혼력/LV, 0 고정 해소).
            #   어댑터 누락 시 soul_power undefined → Number(?? 0) → "0".
            #   연결 시 바바리안 soul_power_base = 10. level은 누락이어도
            #   default 1이라 영혼력 10이 어댑터 연결 핵심 지표.
            try:
                soul = (
                    await page.locator(
                        '[data-testid="status-soul-power"]'
                    ).first.inner_text()
                ).strip()
                lv = (
                    await page.locator(
                        '[data-testid="status-level"]'
                    ).first.inner_text()
                ).strip()
                results["progression_displayed"] = soul == "10" and lv == "1"
            except Exception:
                results["progression_displayed"] = False

            # ★ 메뉴 지도/도움말 onClick → 패널 (재검증 끊김 3)
            #   ≡ MENU 토글 → 항목 클릭 → 패널 표시. Esc로 닫아 chat 검증 비간섭.
            try:
                await page.click('[data-testid="menu-toggle"]')
                await page.click('[data-testid="menu-map"]')
                await page.wait_for_selector(
                    '[data-testid="map-panel"]', timeout=5000, state="visible"
                )
                results["menu_map_works"] = True
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(250)
            except Exception:
                results["menu_map_works"] = False
            try:
                await page.click('[data-testid="menu-toggle"]')
                await page.click('[data-testid="menu-help"]')
                await page.wait_for_selector(
                    '[data-testid="help-panel"]', timeout=5000, state="visible"
                )
                results["menu_help_works"] = True
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(250)
            except Exception:
                results["menu_help_works"] = False

            try:
                inp = page.locator("input").first
                await inp.click()
                async with page.expect_response(
                    # ★ verify gate가 27B를 다중 호출(Mechanical/debate/chat)해 큐 적체 시
                    #   freeform 응답이 느려질 수 있어 timeout 여유 (27B 13 t/s 대응)
                    lambda r: "/api/v2/freeform_action" in r.url, timeout=60000
                ):
                    await page.keyboard.type("주변을 살펴본다")
                    await page.keyboard.press("Enter")
                # ★ 응답이 화면 NarrativePanel에 렌더되도록 대기 (TURN 증가)
                await page.wait_for_timeout(1200)
                post_body = await page.locator("body").inner_text()
                # HTTP 200 + IP 미노출(narrative 본문 라스카니아 → 라프도니아 unmaskIp)
                #  — HTTP 200만 보던 검증 갭을 화면 내용까지 확장.
                results["chat_freeform_works"] = (
                    freeform["code"] == 200 and "라스카니아" not in post_body
                )
            except Exception:
                results["chat_freeform_works"] = False
        finally:
            await browser.close()

    return results


def _score(
    results: dict[str, bool],
) -> tuple[int, int, int, list[str], list[str], list[str]]:
    """항목별 결과 → (측정 점수, 측정 만점, deferred, xfail/xpass/hard_fail).

    ★ xfail 항목은 만점이 아니라 deferred(분모 제외) — 측정 결과와 무관하게
      만점 부여하면 score inflation(실제 결함을 만점으로 위장). 대신 점수·분모
      양쪽에서 빼서 '아직 미측정'으로 정직 처리. 재검토가 is_xfail 해제 시 분모 복원.
    """
    score = 0
    measured_max = 0  # hard 항목 총점 (실제 채점 대상)
    deferred = 0  # xfail 항목 총점 (분모 제외 — 재검토 대기)
    xfail: list[str] = []
    xpass: list[str] = []
    hard_fail: list[str] = []
    for c in CHECKS:
        ok = results.get(c.name, False)
        if c.is_xfail:
            deferred += c.points
            (xpass if ok else xfail).append(c.name)
        else:
            measured_max += c.points
            if ok:
                score += c.points
            else:
                hard_fail.append(c.name)
    return score, measured_max, deferred, xfail, xpass, hard_fail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", default="http://localhost:4000")
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--skip", action="store_true", help="CI — frontend 없음")
    args = parser.parse_args()

    hard_max = sum(c.points for c in CHECKS if not c.is_xfail)
    deferred_max = sum(c.points for c in CHECKS if c.is_xfail)

    if args.skip:
        # ★ CI — frontend 없음: 측정 불가 → 만점 X, 전체 deferred(분모 제외).
        #   측정 없이 hard_max 만점은 검증 우회 (codex 피드백). 전부 미측정 처리.
        print("GAMEPLAY_E2E_SCORE=0/0")
        print(f"GAMEPLAY_E2E_DEFERRED={hard_max + deferred_max}")
        print("XFAIL=[] XPASS=[] HARD_FAIL=[] (skip — CI 측정 불가, 전체 deferred)")
        return 0

    try:
        results = asyncio.run(_measure(args.frontend_url, not args.no_headless))
    except Exception as e:
        print(f"GAMEPLAY_E2E_SCORE=0/{hard_max}")
        print(f"GAMEPLAY_E2E_DEFERRED={deferred_max}")
        print(f"HARD_FAIL=['e2e_setup: {e}']")
        return 1

    score, measured_max, deferred, xfail, xpass, hard_fail = _score(results)
    print(f"GAMEPLAY_E2E_SCORE={score}/{measured_max}")
    print(f"GAMEPLAY_E2E_DEFERRED={deferred}  (★ xfail — 분모 제외, 재검토 대기)")
    print(f"XFAIL={xfail}  (★ 재검토 체크리스트 — 현재 알려진 결함)")
    if xpass:
        print(f"XPASS={xpass}  (★ 예상외 통과 — is_xfail 해제 권장)")
    print(f"HARD_FAIL={hard_fail}")
    for c in CHECKS:
        mark = "xfail" if c.is_xfail else "HARD"
        ok = "✅" if results.get(c.name) else "❌"
        print(f"  [{mark}] {ok} {c.name} — {c.desc}")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
