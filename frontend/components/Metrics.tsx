/**
 * Metrics 컴포넌트 (★ Tier 2 D9 W3).
 *
 * 턴별 검증 결과 시각화.
 */

import type { TurnResponse } from "@/lib/types";

interface MetricsProps {
  metrics: TurnResponse | null;
  location?: string;
}

export default function Metrics({ metrics, location }: MetricsProps) {
  return (
    <aside className="bg-slate-800 border border-slate-700 rounded-md p-5 h-fit">
      <h3 className="text-cyan-400 text-sm font-semibold mb-3">턴 정보</h3>

      {metrics ? (
        <dl className="grid grid-cols-[100px_1fr] gap-2 text-sm">
          <dt className="text-slate-400">Mechanical:</dt>
          <dd
            className={
              metrics.mechanical_passed ? "text-emerald-400" : "text-red-400"
            }
          >
            {metrics.mechanical_passed ? "✅ 통과" : "❌ 실패"}
          </dd>

          <dt className="text-slate-400">잘림:</dt>
          <dd
            className={
              metrics.truncated ? "text-yellow-400" : "text-emerald-400"
            }
          >
            {metrics.truncated ? "⚠️ 잘림" : "✅ 정상"}
          </dd>

          <dt className="text-slate-400">점수:</dt>
          <dd
            className={
              metrics.total_score >= 80
                ? "text-emerald-400"
                : metrics.total_score >= 60
                  ? "text-yellow-400"
                  : "text-red-400"
            }
          >
            {metrics.total_score.toFixed(0)}/100
          </dd>

          <dt className="text-slate-400">Verify:</dt>
          <dd
            className={
              metrics.verify_passed ? "text-emerald-400" : "text-red-400"
            }
          >
            {metrics.verify_passed ? "✅ 통과" : "❌ 실패"}
          </dd>
        </dl>
      ) : (
        <p className="text-slate-500 text-sm">
          아직 턴 정보가 없습니다. 게임을 시작하세요.
        </p>
      )}

      <h3 className="text-cyan-400 text-sm font-semibold mb-3 mt-5">위치</h3>
      <p className="text-sm">{location || "-"}</p>
    </aside>
  );
}
