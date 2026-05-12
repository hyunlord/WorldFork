"use client";

/**
 * GameLayout — shared layout for Phase 7b screens.
 *
 * - top nav with 7 screen links + Chat (legacy)
 * - useGameState hook (★ /api/v2/state)
 * - footer: turn + location 본격
 */

import Link from "next/link";
import type { ReactNode } from "react";

import { useGameState } from "@/lib/hooks/useGameState";

const NAV_ITEMS: ReadonlyArray<{ href: string; label: string }> = [
  { href: "/start", label: "Start" },
  { href: "/main", label: "Main" },
  { href: "/game", label: "Game" },
  { href: "/character", label: "Character" },
  { href: "/rift", label: "Rift" },
  { href: "/combat", label: "Combat" },
  { href: "/dialogue", label: "Dialogue" },
  { href: "/", label: "Chat (legacy)" },
];

interface GameLayoutProps {
  children: ReactNode;
}

export function GameLayout({ children }: GameLayoutProps) {
  const { data, loading, error } = useGameState();

  const subArea = data?.state.location.sub_area ?? "unknown";
  const realm = data?.state.location.realm ?? "?";

  return (
    <div className="game-layout">
      <nav className="game-nav">
        {NAV_ITEMS.map((item) => (
          <Link key={item.href} href={item.href} className="game-nav-link">
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="game-content">
        {loading && (
          <div className="loading">상태 본격 불러오는 중...</div>
        )}
        {error && (
          <div className="error">
            상태 API 본격 X: {error.message}
          </div>
        )}
        {children}
      </div>
      <footer className="game-footer">
        {data ? (
          <span>
            Turn: {data.turn} · {realm} · {subArea}
          </span>
        ) : (
          <span>WorldFork — Phase 7b</span>
        )}
      </footer>
    </div>
  );
}
