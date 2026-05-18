/**
 * FindingsInput (★ Tier 2 D10).
 *
 * 게임 플레이 중 발견한 이슈 입력.
 */

"use client";

import { useState } from "react";
import type { Finding } from "@/lib/types";

interface FindingsInputProps {
  findings: Finding[];
  onChange: (findings: Finding[]) => void;
}

const CATEGORIES = [
  { value: "truncation", label: "응답 잘림" },
  { value: "character", label: "캐릭터 일관성" },
  { value: "world", label: "세계관" },
  { value: "style", label: "문체" },
  { value: "other", label: "기타" },
] as const;

const SEVERITIES = [
  { value: "minor", label: "minor", color: "text-yellow-400" },
  { value: "major", label: "major", color: "text-orange-400" },
  { value: "critical", label: "critical", color: "text-red-400" },
] as const;

function severityColor(s: Finding["severity"]): string {
  return SEVERITIES.find((x) => x.value === s)?.color || "text-slate-400";
}

function categoryLabel(c: string): string {
  return CATEGORIES.find((x) => x.value === c)?.label || c;
}

export default function FindingsInput({
  findings,
  onChange,
}: FindingsInputProps) {
  const [category, setCategory] = useState("other");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<Finding["severity"]>("minor");

  const handleAdd = () => {
    if (!description.trim()) return;
    onChange([
      ...findings,
      {
        category,
        description: description.trim(),
        severity,
      },
    ]);
    setDescription("");
    setSeverity("minor");
  };

  const handleRemove = (idx: number) => {
    onChange(findings.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm text-slate-400">
        발견 이슈 ({findings.length})
      </label>

      {/* 기존 findings */}
      {findings.length > 0 && (
        <ul className="space-y-2">
          {findings.map((f, idx) => (
            <li
              key={`finding-${idx}-${f.category}`}
              className="bg-slate-900 border border-slate-700 rounded-md p-3 flex items-start justify-between gap-2"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1 text-xs">
                  <span className={severityColor(f.severity)}>
                    [{f.severity}]
                  </span>
                  <span className="text-slate-400">
                    {categoryLabel(f.category)}
                  </span>
                </div>
                <div className="text-sm">{f.description}</div>
              </div>
              <button
                type="button"
                onClick={() => handleRemove(idx)}
                className="text-slate-500 hover:text-red-400 transition"
                aria-label="제거"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* 입력 폼 */}
      <div className="bg-slate-900 border border-slate-700 rounded-md p-3 space-y-2">
        <div className="flex gap-2">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-slate-800 text-slate-100 border border-slate-700 rounded px-2 py-1 text-sm"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <select
            value={severity}
            onChange={(e) =>
              setSeverity(e.target.value as Finding["severity"])
            }
            className="bg-slate-800 text-slate-100 border border-slate-700 rounded px-2 py-1 text-sm"
          >
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleAdd();
            }
          }}
          placeholder="이슈 설명"
          className="w-full bg-slate-800 text-slate-100 border border-slate-700 px-2 py-1 rounded text-sm focus:outline-none focus:border-cyan-400"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={!description.trim()}
          className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-900 text-sm font-medium px-3 py-1 rounded transition"
        >
          추가
        </button>
      </div>
    </div>
  );
}
