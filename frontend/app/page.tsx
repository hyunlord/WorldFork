/**
 * Main page (★ Tier 2 D10).
 *
 * Chat + Metrics + EndSession 통합.
 */

"use client";

import { useState } from "react";
import Chat from "@/components/Chat";
import Metrics from "@/components/Metrics";
import EndSession from "@/components/EndSession";
import type { TurnResponse, EndSessionResponse } from "@/lib/types";

type AppPhase = "playing" | "ending" | "completed";

export default function HomePage() {
  const [phase, setPhase] = useState<AppPhase>("playing");
  const [metrics, setMetrics] = useState<TurnResponse | null>(null);
  const [location, setLocation] = useState<string>("-");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [totalTurns, setTotalTurns] = useState(0);
  const [completedResponse, setCompletedResponse] =
    useState<EndSessionResponse | null>(null);

  const handleSessionStart = (sid: string) => {
    setSessionId(sid);
    setPhase("playing");
  };

  const handleTurnsLimitReached = (_sid: string, turns: number) => {
    setTotalTurns(turns);
    setPhase("ending");
  };

  const handleEndSessionComplete = (response: EndSessionResponse) => {
    setCompletedResponse(response);
    setPhase("completed");
  };

  const handleEndCancel = () => {
    setPhase("playing");
  };

  const handleRestart = () => {
    setPhase("playing");
    setMetrics(null);
    setLocation("-");
    setSessionId(null);
    setTotalTurns(0);
    setCompletedResponse(null);
    // 페이지 리로드로 Chat 컴포넌트 재초기화
    window.location.reload();
  };

  const requestEndEarly = () => {
    if (sessionId && metrics) {
      setTotalTurns(metrics.turn_n);
      setPhase("ending");
    }
  };

  return (
    <div className="container mx-auto max-w-6xl p-5">
      <header className="bg-slate-800 border border-slate-700 rounded-md p-5 mb-5">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-cyan-400 text-2xl font-bold mb-2">WorldFork</h1>
            <p className="text-slate-400 text-sm">
              한국어 텍스트 어드벤처 (★ Tier 2 D10 — 사람 검증 UX)
            </p>
          </div>
          {phase === "playing" && sessionId && (
            <button
              type="button"
              onClick={requestEndEarly}
              className="text-sm text-slate-400 hover:text-yellow-400 transition"
            >
              세션 종료
            </button>
          )}
        </div>
      </header>

      {phase === "playing" && (
        <main className="grid grid-cols-1 md:grid-cols-[1fr_300px] gap-5">
          <div className="bg-slate-800 border border-slate-700 rounded-md p-5">
            <Chat
              onMetricsUpdate={setMetrics}
              onLocationUpdate={setLocation}
              onSessionStart={handleSessionStart}
              onTurnsLimitReached={handleTurnsLimitReached}
            />
          </div>
          <Metrics metrics={metrics} location={location} />
        </main>
      )}

      {phase === "ending" && sessionId && (
        <EndSession
          sessionId={sessionId}
          totalTurns={totalTurns}
          onComplete={handleEndSessionComplete}
          onCancel={handleEndCancel}
        />
      )}

      {phase === "completed" && completedResponse && (
        <div className="bg-slate-800 border border-emerald-500 rounded-md p-6 text-center space-y-4">
          <h2 className="text-2xl font-bold text-emerald-400">
            ✅ 세션 저장 완료
          </h2>
          <div className="text-slate-300 space-y-2 text-sm">
            <p>
              저장 경로:{" "}
              <code className="text-cyan-400">
                {completedResponse.saved_path}
              </code>
            </p>
            <p>총 턴: {completedResponse.total_turns}</p>
            {completedResponse.summary.fun_score && (
              <p>재미 점수: {completedResponse.summary.fun_score}/5</p>
            )}
            <p>발견 이슈: {completedResponse.summary.findings_count}개</p>
          </div>
          <button
            type="button"
            onClick={handleRestart}
            className="bg-cyan-500 hover:bg-cyan-400 text-slate-900 font-semibold px-5 py-2 rounded-md transition"
          >
            새 세션 시작
          </button>
        </div>
      )}

      <footer className="mt-10 p-4 bg-yellow-900/5 border border-dashed border-yellow-600 rounded-md text-center">
        <p className="text-yellow-400 text-sm">
          ★ Tier 2 D10 — 사람 검증 UX. 본인 #16 정공법: Web UI 거의 완성 ✅. ★
          ★ 본인 + 친구 사람 검증 가능 시점!
        </p>
      </footer>
    </div>
  );
}
