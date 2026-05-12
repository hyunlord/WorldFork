"use client";

/**
 * Start Menu — Phase 7b skeleton.
 *
 * Phase 6 start_menu.html 본격 reference (★ 실제 component 본격 7c+).
 */

import Link from "next/link";

import { GameLayout } from "@/components/GameLayout";

export default function StartPage() {
  return (
    <GameLayout>
      <div className="screen start-menu">
        <h1 className="start-logo">WORLDFORK</h1>
        <div className="start-subtitle">DUNGEON OF DARKNESS</div>
        <nav className="main-menu">
          <Link href="/main" className="main-menu-item">▸ 신규 시작</Link>
          <Link href="/main" className="main-menu-item">이어하기</Link>
          <span className="main-menu-item disabled">설정</span>
          <span className="main-menu-item disabled">종료</span>
        </nav>
      </div>
    </GameLayout>
  );
}
