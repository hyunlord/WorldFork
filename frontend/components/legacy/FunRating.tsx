/**
 * FunRating 컴포넌트 (★ Tier 2 D10).
 *
 * 1-5 별점 + 자유 코멘트.
 */

"use client";

import { useState } from "react";
import type React from "react";
import type { FunRating as FunRatingType } from "@/lib/types";

interface FunRatingProps {
  value: FunRatingType | null;
  onChange: (rating: FunRatingType | null) => void;
}

export default function FunRating({ value, onChange }: FunRatingProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const score = value?.score ?? 0;
  const display = hovered ?? score;

  const handleScoreChange = (newScore: number) => {
    onChange({
      score: newScore,
      comment: value?.comment ?? null,
    });
  };

  const handleCommentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({
      score: score || 1,
      comment: e.target.value || null,
    });
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm text-slate-400 mb-2">재미 점수</label>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onMouseEnter={() => setHovered(n)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => handleScoreChange(n)}
              className={`text-3xl transition-transform hover:scale-110 ${
                n <= display ? "text-yellow-400" : "text-slate-600"
              }`}
              aria-label={`${n}점`}
            >
              ★
            </button>
          ))}
          {score > 0 && (
            <span className="ml-2 self-center text-sm text-slate-400">
              {score}/5
            </span>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm text-slate-400 mb-2">
          코멘트 (선택)
        </label>
        <textarea
          value={value?.comment ?? ""}
          onChange={handleCommentChange}
          placeholder="자유롭게 의견을 남겨주세요"
          rows={3}
          className="w-full bg-slate-900 text-slate-100 border border-slate-700 px-3 py-2 rounded-md focus:outline-none focus:border-cyan-400 text-sm"
        />
      </div>
    </div>
  );
}
