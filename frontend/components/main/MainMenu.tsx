"use client";

/**
 * MainMenu — 4 메뉴 (★ 1층 진입 / 이어하기 / 설정 / 나가기).
 *
 * Phase 6 main_screen.html .menu 정합.
 */

import Link from "next/link";

export function MainMenu() {
  return (
    <nav className="main-menu-nav">
      <Link href="/game" className="menu-item primary">
        ▸ 1층 진입
      </Link>
      <Link href="/game" className="menu-item">
        이어하기
      </Link>
      <span className="menu-item disabled">설정</span>
      <span className="menu-item disabled">나가기</span>
    </nav>
  );
}
