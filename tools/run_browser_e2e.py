"""Browser E2E — 진짜 사람 클릭 흐름 자동 검증 (★ Tier 2 D11+).

Mechanical E2E (curl) ≠ 사람 클릭 흐름.
Next.js 빌드 JS가 진짜 실행 + 링크 클릭 + fetch 진짜 발생 검증.

playwright headless chromium:
  1. http://<frontend-url> 접속 (domcontentloaded)
  2. '새 게임' 링크 대기 + 클릭 → /game 페이지 진입
  3. 입력창 (placeholder text) 대기 — JS hydration 완료 확인
  4. 텍스트 입력 + Enter → /api/v2/freeform_action 요청 발생 + 응답 200
  5. Console / Network 에러 (HMR 무시)

사용:
  python tools/run_browser_e2e.py
  python tools/run_browser_e2e.py --frontend-url http://100.70.109.50:4000
  python tools/run_browser_e2e.py --skip   # CI 환경 frontend 없음
  python tools/run_browser_e2e.py --no-headless  # 디버깅 (★ 진짜 브라우저)

Exit: 0=pass, 1=fail
"""

from __future__ import annotations

import argparse
import asyncio
import sys


async def run_check(
    frontend_url: str,
    headless: bool = True,
) -> tuple[bool, list[str]]:
    """playwright로 진짜 사람 흐름 시뮬."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return False, ["playwright import 실패 (★ uv pip install playwright)"]

    failures: list[str] = []
    console_errors: list[str] = []
    network_failures: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )
        page.on(
            "requestfailed",
            lambda req: network_failures.append(
                f"{req.method} {req.url}: {req.failure}"
            ),
        )

        try:
            print(f"[1/5] Loading {frontend_url}...")
            response = await page.goto(
                frontend_url, timeout=15000, wait_until="domcontentloaded"
            )
            if response and response.status != 200:
                failures.append(f"frontend HTTP {response.status}")
                return False, failures
            print("  ✅ loaded")

            print("[2/5] Waiting for '새 게임' link...")
            try:
                link = await page.wait_for_selector(
                    "a:has-text('새 게임')",
                    timeout=10000,
                    state="visible",
                )
                if not link:
                    failures.append("'새 게임' 링크 X")
                    return False, failures
                print("  ✅ link visible")
                await link.click()
            except Exception as e:
                failures.append(f"'새 게임' 링크 대기 실패: {e}")
                return False, failures

            print("[3/5] Waiting for game input (JS hydration)...")
            try:
                await page.wait_for_selector(
                    "input",
                    timeout=15000,
                    state="visible",
                )
                print("  ✅ input ready")
            except Exception as e:
                failures.append(f"입력창 대기 실패: {e}")
                return False, failures

            print("[4/5] Type + Enter → /api/v2/freeform_action...")
            try:
                async with page.expect_response(
                    lambda r: "/api/v2/freeform_action" in r.url,
                    timeout=20000,
                ) as response_info:
                    await page.keyboard.type("주변을 살펴본다")
                    await page.keyboard.press("Enter")

                resp = await response_info.value
                print(f"  ✅ /api/v2/freeform_action: {resp.status}")
                if resp.status != 200:
                    failures.append(f"/api/v2/freeform_action: HTTP {resp.status}")
            except Exception as e:
                failures.append(
                    f"/api/v2/freeform_action 요청 X: {e} "
                    "(★ fetch 발화 X 또는 차단)"
                )
                if console_errors:
                    failures.append(f"Console 에러: {console_errors[:3]}")
                if network_failures:
                    failures.append(f"Network 실패: {network_failures[:3]}")
                return False, failures

            print("[5/5] Console / Network 에러...")
            real_errors = [
                e for e in console_errors
                if "WebSocket" not in e and "_next/webpack-hmr" not in e
            ]
            if real_errors:
                failures.append(
                    f"Console 에러 {len(real_errors)}건: {real_errors[:3]}"
                )
            elif console_errors:
                print(
                    f"  ✅ HMR 외 에러 0건 "
                    f"(HMR {len(console_errors)}건 무시)"
                )
            else:
                print("  ✅ Console clean")

            real_net = [
                f for f in network_failures
                if "webpack-hmr" not in f and "_next/static" not in f
            ]
            if real_net:
                failures.append(f"Network 실패: {real_net[:3]}")

        finally:
            await browser.close()

    return len(failures) == 0, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:4000",
        help="Frontend URL to test",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="브라우저 진짜 띄움 (★ 디버깅)",
    )
    parser.add_argument(
        "--skip",
        action="store_true",
        help="검증 스킵 (★ CI 환경 frontend 없음)",
    )
    args = parser.parse_args()

    if args.skip:
        print("★ Browser E2E skipped (--skip)")
        return 0

    ok, failures = asyncio.run(
        run_check(args.frontend_url, headless=not args.no_headless)
    )

    print()
    if ok:
        print("✅ Browser E2E PASS — 사람 클릭 흐름 진짜 작동")
        return 0
    print(f"❌ Browser E2E FAIL ({len(failures)}건):")
    for f in failures:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
