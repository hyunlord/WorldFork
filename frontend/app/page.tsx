/**
 * Main page (★ Tier 2 D9 W3).
 *
 * Chat + Metrics 통합.
 */

"use client";

import { useState } from "react";
import Chat from "@/components/Chat";
import Metrics from "@/components/Metrics";
import type { TurnResponse } from "@/lib/types";

export default function HomePage() {
  const [metrics, setMetrics] = useState<TurnResponse | null>(null);
  const [location, setLocation] = useState<string>("-");

  return (
    <div className="container mx-auto max-w-6xl p-5">
      <header className="bg-slate-800 border border-slate-700 rounded-md p-5 mb-5">
        <h1 className="text-cyan-400 text-2xl font-bold mb-2">WorldFork</h1>
        <p className="text-slate-400 text-sm mb-3">
          한국어 텍스트 어드벤처 (★ Tier 2 D9 W3 — Next.js)
        </p>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-[1fr_300px] gap-5">
        <div className="bg-slate-800 border border-slate-700 rounded-md p-5">
          <Chat
            onMetricsUpdate={setMetrics}
            onLocationUpdate={setLocation}
          />
        </div>
        <Metrics metrics={metrics} location={location} />
      </main>

      <footer className="mt-10 p-4 bg-yellow-900/5 border border-dashed border-yellow-600 rounded-md text-center">
        <p className="text-yellow-400 text-sm">
          ★ 본인 #16 정공법: 이 UI는 시각적 디버깅용. 사람 검증 X. Web UI
          거의 완성 (D10 UX) 후만 진짜 사람 검증.
        </p>
      </footer>
    </div>
  );
}
