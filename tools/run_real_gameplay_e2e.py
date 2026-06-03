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
import json
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
    Check("scenario_origin_naming", 1, False, "게임 화면 원작 명칭 (투르윈 노출 X)"),
    Check("session_scenario_reflected", 1, False, "생성 시나리오 화면 반영 (바바리안 HP 120)"),
    Check("no_starting_party", 1, False, "시작 파티원 0 (실렌·한스 X — 성인식 마을)"),
    Check("chat_freeform_works", 3, False, "채팅 → narrative 화면 렌더 + IP 미노출 (라스카니아 X)"),
    Check("background_rendered", 1, False, "배경 이미지 렌더링 (ComfyUI PNG, ASCII 단독 X)"),
    Check("progression_displayed", 2, False, "진행 표시 (영혼력 10/LV 1 — 어댑터 연결, 0 고정 X)"),
    Check("weapon_choice_reflected", 1, False, "성인식 무기 선택 → 장착 반영 (방패 고정 X)"),
    Check("menu_map_works", 2, False, "메뉴 지도 onClick → MapPanel (floor/rift 4종)"),
    Check("menu_help_works", 2, False, "메뉴 도움말 onClick → HelpPanel (조작/시스템)"),
    Check("time_limit_consistent", 1, False, "시간 한도 168h 표시 (174 불일치 X — 7일 정합)"),
    Check("character_scrollable", 1, False, "character 긴 콘텐츠 스크롤 가능 (생성 버튼 도달)"),
    # ★ 화면 내용 검증 (검증 갭 닫기)
    Check("start_narrative_shown", 1, False, "첫 화면 성인식 narrative 노출 (generic 안내 X)"),
    Check("no_demo_placeholder", 1, False, "placeholder 데모(한스·WASD) 부재"),
    Check("suggested_actions_shown", 1, False, "추천 행동 버튼 노출 (placeholder만 X)"),
    Check("dialogue_npc_works", 1, False, "NPC 대화 작동 (부족장 → '대화할 상대 없다' 부재)"),
    # ★ 히스토리 누적 + 주변 엔티티 (manual play 4)
    Check("history_accumulates", 1, False, "narrative 히스토리 누적 (시작+행동 둘 다 잔존)"),
    Check("surroundings_shown", 1, False, "주변 엔티티 패널 (부족장 NPC 표시)"),
    # ★ 인물 초상 연결 (하이브리드 1단계)
    Check("sheet_portrait_shown", 1, False, "캐릭터 시트 전신 일러스트 (ui_character)"),
    # ★ GM 루프 (게임 진행 엔진 1단계): 같은 행동 → 다른 응답
    Check("meaningful_progression", 2, False, "같은 행동 2회 → 다른 narrative (GM 맥락)"),
    # ★ 서빙 1단계 — SSE 스트리밍: GM narrative가 토큰 점진(통째 blob X)
    Check("streaming_progressive", 1, False, "SSE 토큰 점진 노출 (단일 blob X — 체감 즉효)"),
    # ★ 상태 진전 (2단계): 행동이 스토리 단계를 전진시킴
    Check("story_phase_advances", 1, False, "부족장 대화 → 단계 전진(추천 무기 선택으로 변화)"),
    # ★ 서빙 3단계 — 하이브리드 라우팅: 성년식 27B(품질) / 던전 진입 9B(빠름)
    Check("hybrid_routing", 1, False, "하이브리드 9B/27B 라우팅 (성년식 27b / 던전 9b)"),
    # ★ 던전 진입 안정 (intent 정확도): departure → 던전 진입 + 마을 NPC 미잔존
    Check("dungeon_entry_stable", 1, False, "departure → 던전 진입(1층) + 부족장 미잔존"),
    # ★ 서빙 2단계 — 던전 진입 GM 서사: 고정 한 줄 X, GM 토큰 점진 전환 서사
    Check("dungeon_entry_narrated", 1, False, "던전 진입 GM 서사 (고정 한 줄 X — 입성 전환)"),
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
            # ★ 무기는 character에서 미리 선택하지 않는다 (게임 엔진 3단계 —
            #   성인식 weapon_choice 단계에서 게임 내 선택, ep_0002 고증).
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
            # ★ 첫 화면 도입부 + 성인식 narrative 노출 (4단계 — ep_0001 빙의 발단).
            #   게임 빙의 발단('빙의'/'게임') + 성인식(부족장/성지/성년/전사) 둘 다 +
            #   generic 안내("행동을 입력해 모험을 시작하세요") 부재.
            results["start_narrative_shown"] = (
                ("빙의" in body or "게임" in body)
                and any(kw in body for kw in ("부족장", "성지", "성년", "전사"))
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
            # ★ weapon_choice_reflected는 게임 내 무기 선택(부족장 대화→weapon_choice→
            #   선택) 흐름 뒤 chat 블록에서 측정 — character 미리 선택 폐지(ep_0002).
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
            # ★ 캐릭터 시트 전신 일러스트 — 메뉴 캐릭터 → CharacterSheetModal
            #   (바바리안이면 ui_character_bjorn 전신 노출, 현 FLUX 자산 활용)
            try:
                await page.click('[data-testid="menu-toggle"]')
                await page.click('[data-testid="menu-character"]')
                sheet = page.locator('[data-testid="sheet-portrait"]')
                await sheet.first.wait_for(timeout=5000, state="visible")
                src = await sheet.first.get_attribute("src")
                results["sheet_portrait_shown"] = (
                    src is not None and "ui_character" in src
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(250)
            except Exception:
                results["sheet_portrait_shown"] = False

            try:
                inp = page.locator("input").first
                # ★ 서빙 1단계 — SSE token 이벤트(점진 노출 증거): 전체 최대치 + 직전 턴
                stream_info = {"max_tokens": 0, "last_tokens": 0}
                # ★ 서빙 3단계 — 직전 턴 gm_model 라우팅(9b/27b) 관측
                route_info = {"last_model": ""}

                async def _turn(text: str) -> str:
                    # 한 행동 제출 → SSE 스트림 파싱 → canonical narrative 반환.
                    #   frontend는 /freeform_action/stream을 호출(토큰 점진). E2E는 응답
                    #   본문(SSE)을 받아 event:token 수 + event:complete narrative를 추출.
                    await inp.click()
                    async with page.expect_response(
                        # ★ verify gate가 27B를 다중 호출(Mechanical/Browser/debate +
                        #   E2E GM)해 큐 적체 시 GM 응답이 크게 느려질 수 있어 timeout
                        #   여유(정상 28s/turn, 최악 큐 적체 대비). meaningful flaky 방지.
                        lambda r: "/api/v2/freeform_action/stream" in r.url,
                        timeout=240000,
                    ) as ri:
                        await page.keyboard.type(text)
                        await page.keyboard.press("Enter")
                    resp = await ri.value
                    freeform["code"] = resp.status
                    try:
                        raw = await resp.text()
                    except Exception:
                        return ""
                    # SSE 파싱 — event:token 누적(점진 증거) + event:complete narrative
                    narrative = ""
                    tokens = 0
                    event = ""
                    for line in raw.splitlines():
                        if line.startswith("event:"):
                            event = line[len("event:"):].strip()
                        elif line.startswith("data:"):
                            data = line[len("data:"):].strip()
                            if not data:
                                continue
                            if event == "token":
                                tokens += 1
                            elif event == "complete":
                                try:
                                    obj = json.loads(data)
                                    narrative = str(obj.get("narrative", ""))
                                    route_info["last_model"] = str(
                                        obj.get("gm_model") or ""
                                    )
                                except Exception:
                                    pass
                    stream_info["max_tokens"] = max(
                        stream_info["max_tokens"], tokens
                    )
                    stream_info["last_tokens"] = tokens
                    return narrative

                # ★ 같은 행동 2회 — GM 누적 맥락이면 서로 다른 narrative.
                narr_a = await _turn("부족장에게 말을 건다")
                # ★ 서빙 3단계 — 성년식 대화(declaration)는 pivotal → 27B 라우팅.
                route_dialogue = route_info["last_model"]
                await page.wait_for_timeout(1000)
                narr_b = await _turn("부족장에게 말을 건다")
                await page.wait_for_timeout(1200)
                post_body = await page.locator("body").inner_text()
                # ★ SSE 토큰 점진 — GM narrative가 여러 token 이벤트로 흘렀는가(단일 blob X).
                #   3+ token = 점진 노출 작동(체감 ~0.2초 시작). 단일/0 = 스트리밍 단절.
                results["streaming_progressive"] = stream_info["max_tokens"] >= 3

                results["chat_freeform_works"] = (
                    freeform["code"] == 200 and "라스카니아" not in post_body
                )
                # ★ NPC seed → 대화 작동 (막다른 '대화할 상대가 없다' 부재)
                results["dialogue_npc_works"] = "대화할 상대가 없다" not in narr_a
                # ★ GM 루프 — 같은 행동 2회가 서로 다른 narrative(template 반복 X).
                #   GM 비활성/fallback이면 동일 template → 실패(정직한 검출).
                results["meaningful_progression"] = (
                    len(narr_a) > 15 and len(narr_b) > 15 and narr_a != narr_b
                )
                # ★ 히스토리 누적 — 시작 narrative 잔존 + 행동 구분선(▸) 2개(2턴 누적).
                results["history_accumulates"] = (
                    any(kw in post_body for kw in ("성년", "전사", "성지"))
                    and post_body.count("▸") >= 2
                )
                # ★ 주변 엔티티 패널 — 마을 부족장 NPC 표시(EncounterPanel 대안)
                surr = page.locator('[data-testid="surroundings-panel"]')
                if await surr.count() > 0:
                    surr_text = await surr.first.inner_text()
                    results["surroundings_shown"] = "부족장" in surr_text
                else:
                    results["surroundings_shown"] = False
                # ★ 상태 진전 — 부족장 대화 후 추천이 weapon_choice 단계로 전진.
                #   추천 버튼이 곧 무기 선택지(도끼/검/창)로 바뀜.
                sugg = page.locator('[data-testid="suggested-action"]')
                sugg_text = ""
                for i in range(await sugg.count()):
                    sugg_text += await sugg.nth(i).inner_text()
                results["story_phase_advances"] = any(
                    w in sugg_text for w in ("도끼", "검", "창")
                )
                # ★ 성인식 무기 선택 (게임 내 — ep_0002) → 장착 + departure 전진.
                #   character 미리 선택 폐지, weapon_choice 단계에서 선택.
                narr_weapon = await _turn("양손 도끼를 고른다")
                await page.wait_for_timeout(1200)
                final_body = await page.locator("body").inner_text()
                results["weapon_choice_reflected"] = (
                    "양손 도끼" in narr_weapon or "양손 도끼" in final_body
                )
                # ★ departure 단계 → 던전 진입 안정 (9B intent flaky 회피, 단계 기반).
                #   '미궁으로 향한다' → floor 0→1: 위치 '1층' 표시 + 마을 SurroundingsPanel
                #   사라짐(부족장 등 마을 NPC 미잔존 — encounters는 단위 검증, 화면은 패널).
                #   ('부족장' 텍스트는 히스토리 narrative에 남으므로 패널 기준으로 판정)
                entry_narr = await _turn("미궁으로 향한다")
                # ★ 서빙 3단계 — 던전 진입(departure, 비전투)은 단순 → 9B 라우팅.
                route_entry = route_info["last_model"]
                await page.wait_for_timeout(1500)
                dungeon_body = await page.locator("body").inner_text()
                surr_gone = (
                    await page.locator('[data-testid="surroundings-panel"]').count() == 0
                )
                results["dungeon_entry_stable"] = "1층" in dungeon_body and surr_gone
                # ★ 서빙 2단계 — 진입 GM 서사: ENTER_DUNGEON이 GM_NARRATE_ACTIONS에
                #   편입돼 고정 한 줄 대신 GM 입성 전환을 토큰 점진 생성. 진입 턴이
                #   3+ token 스트림 + 옛 고정 한 줄과 불일치 = GM 주도(결정적).
                #   (일반 조우 등장 라인은 spawn rate 0.30 확률이라 RNG flaky 회피 —
                #    결선은 test_post_apply_spawn_encounter로 결정적 검증.)
                _fixed_entry = "자정이 지났다. 나는 던전 1층 입구 앞에 섰다. 새 달의 시작이다."
                results["dungeon_entry_narrated"] = (
                    stream_info["last_tokens"] >= 3
                    and entry_narr.strip() != _fixed_entry
                    and len(entry_narr) > 15
                )
                # ★ 서빙 3단계 — 하이브리드 라우팅: 성년식 대화 = 27B(품질),
                #   던전 진입(비전투 단순) = 9B(빠름). 둘이 갈리면 라우팅 작동(결정적).
                results["hybrid_routing"] = (
                    route_dialogue == "27b" and route_entry == "9b"
                )
            except Exception:
                results["chat_freeform_works"] = False
                results["dialogue_npc_works"] = False
                results["meaningful_progression"] = False
                results["streaming_progressive"] = False
                results["history_accumulates"] = False
                results["story_phase_advances"] = False
                results["weapon_choice_reflected"] = False
                results["story_phase_advances"] = False
                results["surroundings_shown"] = False
                results["dungeon_entry_stable"] = False
                results["dungeon_entry_narrated"] = False
                results["hybrid_routing"] = False
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
