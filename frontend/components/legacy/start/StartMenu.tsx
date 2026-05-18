"use client";

/**
 * StartMenu — 5 메뉴 (★ 신규 시작 + 이어하기 + 설정 + 갤러리 + 종료).
 *
 * 본격:
 * - 신규 시작 → resetState() POST → /main
 * - 이어하기 → /main 본격
 * - 나머지 disabled
 *
 * Phase 6 start_menu.html .menu 정합.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { resetState } from "@/lib/api/v2";

export function StartMenu() {
  const router = useRouter();
  const [resetting, setResetting] = useState(false);

  const handleNewGame = async () => {
    setResetting(true);
    try {
      await resetState();
    } catch (e) {
      // ★ fallback: reset 실패 시도 본격 그대로 진행
      // eslint-disable-next-line no-console
      console.error("Reset failed:", e);
    } finally {
      setResetting(false);
      router.push("/main");
    }
  };

  return (
    <nav className="start-menu-nav">
      <button
        type="button"
        className="start-menu-item primary"
        onClick={handleNewGame}
        disabled={resetting}
      >
        {resetting ? "시작 중..." : "▸ 신규 시작"}
      </button>
      <Link href="/main" className="start-menu-item">
        이어하기
      </Link>
      <span className="start-menu-item disabled">설정</span>
      <span className="start-menu-item disabled">갤러리 (잠김)</span>
      <span className="start-menu-item disabled small">종료</span>
    </nav>
  );
}
