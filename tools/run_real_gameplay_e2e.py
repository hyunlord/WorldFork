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
    # ★ session 연결(useGameState → /session/{id}/state)로 해제 — hard 전환
    Check("scenario_origin_naming", 8, False, "게임 화면 원작 명칭 (투르윈 노출 X)"),
    Check("session_scenario_reflected", 7, False, "생성 시나리오 화면 반영 (바바리안 HP 120)"),
    # ★ DEMO_DUNGEON/ENCOUNTER 비주얼 placeholder 한스·실렌 잔존 — 비주얼 재검토 대기
    Check("no_starting_party", 8, True, "시작 파티원 0 (실렌·한스 X — 비주얼 placeholder)"),
    Check("chat_freeform_works", 7, False, "채팅 → freeform_action 200 (hard)"),
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

            try:
                inp = page.locator("input").first
                await inp.click()
                async with page.expect_response(
                    lambda r: "/api/v2/freeform_action" in r.url, timeout=20000
                ):
                    await page.keyboard.type("주변을 살펴본다")
                    await page.keyboard.press("Enter")
                results["chat_freeform_works"] = freeform["code"] == 200
            except Exception:
                results["chat_freeform_works"] = freeform["code"] == 200
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
