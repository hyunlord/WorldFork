"use client";

/**
 * Start Menu — Phase 7i implement (★ Phase 6 start_menu.html → React).
 *
 * 본 page 본격:
 * - 4 components: StartLogo / StartMenu / StartAtmosphere / KeyHints
 * - 신규 시작 본격 resetState() API + router.push('/main')
 * - 기존 7b skeleton 본격 overwrite (★ /start route 본격 유지)
 *
 * Phase 7 화면 8/8 마무리.
 */

import { GameLayout } from "@/components/GameLayout";
import { KeyHints } from "@/components/start/KeyHints";
import { StartAtmosphere } from "@/components/start/StartAtmosphere";
import { StartLogo } from "@/components/start/StartLogo";
import { StartMenu } from "@/components/start/StartMenu";

export default function StartPage() {
  return (
    <GameLayout>
      <div className="screen start-menu-bg">
        {/* 좌상단 알림 */}
        <div className="start-notification">
          <span className="new-tag">NEW</span>
          v0.8.0 — Phase 7 화면 8/8 마무리
        </div>

        {/* 우상단 도움말 */}
        <div className="start-top-actions">
          <div className="start-top-action" title="언어">
            KO
          </div>
          <div className="start-top-action" title="도움말">
            ?
          </div>
        </div>

        {/* 중앙 상 로고 */}
        <StartLogo />

        {/* 중앙 메뉴 */}
        <StartMenu />

        {/* 우 하단 분위기 */}
        <StartAtmosphere />

        {/* 좌 하단 키 안내 */}
        <KeyHints />

        {/* 하단 정보 */}
        <div className="start-bottom-bar">
          <div className="version">v0.8.0 (Phase 7 — 8/8 화면)</div>
          <div className="credits">DGX Spark · LLM-CRPG</div>
          <div className="copyright">© 2026 WorldFork</div>
        </div>
      </div>
    </GameLayout>
  );
}
