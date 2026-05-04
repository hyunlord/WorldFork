/**
 * EndSession 컴포넌트 (★ Tier 2 D10).
 *
 * 세션 종료 흐름: Fun rating + Findings + 저장.
 */

"use client";

import { useState } from "react";
import { endSession, APIError } from "@/lib/api";
import type {
  Finding,
  FunRating as FunRatingType,
  EndSessionResponse,
} from "@/lib/types";
import FunRatingComponent from "./FunRating";
import FindingsInputComponent from "./FindingsInput";

interface EndSessionProps {
  sessionId: string;
  totalTurns: number;
  onComplete: (response: EndSessionResponse) => void;
  onCancel: () => void;
}

export default function EndSession({
  sessionId,
  totalTurns,
  onComplete,
  onCancel,
}: EndSessionProps) {
  const [funRating, setFunRating] = useState<FunRatingType | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const response = await endSession({
        session_id: sessionId,
        fun_rating: funRating,
        findings,
        comment: comment.trim() || null,
      });
      onComplete(response);
    } catch (err) {
      const msg =
        err instanceof APIError
          ? `${err.message}: ${err.detail || ""}`
          : String(err);
      setError(`저장 실패: ${msg}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-800 border border-cyan-500 rounded-md p-6 space-y-5">
      <header>
        <h2 className="text-xl font-bold text-cyan-400 mb-2">
          세션 종료 — 검증 결과
        </h2>
        <p className="text-sm text-slate-400">
          세션: {sessionId.slice(0, 8)} | 총 턴: {totalTurns}
        </p>
      </header>

      <FunRatingComponent value={funRating} onChange={setFunRating} />

      <FindingsInputComponent findings={findings} onChange={setFindings} />

      <div>
        <label className="block text-sm text-slate-400 mb-2">전체 코멘트</label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="전체 플레이 경험에 대한 의견 (선택)"
          rows={3}
          className="w-full bg-slate-900 text-slate-100 border border-slate-700 px-3 py-2 rounded-md focus:outline-none focus:border-cyan-400 text-sm"
        />
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500 text-red-300 p-3 rounded-md text-sm">
          {error}
        </div>
      )}

      <div className="flex gap-3 justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-100 px-4 py-2 rounded-md transition"
        >
          취소
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={submitting}
          className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-900 font-semibold px-4 py-2 rounded-md transition"
        >
          {submitting ? "저장 중..." : "세션 저장"}
        </button>
      </div>
    </div>
  );
}
