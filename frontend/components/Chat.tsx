/**
 * Chat 컴포넌트 (★ Tier 2 D9 W3).
 *
 * 한국어 어드벤처 chat UI.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import type React from "react";
import { startGame, processTurn, APIError } from "@/lib/api";
import type { Message, TurnResponse } from "@/lib/types";

interface ChatProps {
  onMetricsUpdate?: (metrics: TurnResponse | null) => void;
  onLocationUpdate?: (location: string) => void;
}

let messageIdCounter = 0;

function makeMessage(type: Message["type"], content: string): Message {
  messageIdCounter += 1;
  return {
    id: `msg-${Date.now()}-${messageIdCounter}`,
    type,
    content,
    timestamp: Date.now(),
  };
}

function MessageBubble({ message }: { message: Message }) {
  const styles: Record<Message["type"], string> = {
    user: "bg-slate-800 border-l-4 border-cyan-400",
    gm: "bg-slate-900 border-l-4 border-emerald-400",
    system:
      "bg-yellow-900/20 border-l-4 border-yellow-400 text-yellow-200 text-sm",
    error: "bg-red-900/20 border-l-4 border-red-400 text-red-300",
  };

  const labels: Record<Message["type"], string> = {
    user: "플레이어",
    gm: "GM",
    system: "시스템",
    error: "오류",
  };

  return (
    <div className={`p-3 rounded-md ${styles[message.type]}`}>
      <div className="text-xs uppercase text-slate-400 mb-1">
        {labels[message.type]}
      </div>
      <div className="whitespace-pre-wrap break-words">{message.content}</div>
    </div>
  );
}

export default function Chat({
  onMetricsUpdate,
  onLocationUpdate,
}: ChatProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (type: Message["type"], content: string) => {
    setMessages((prev) => [...prev, makeMessage(type, content)]);
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      const data = await startGame();
      setSessionId(data.session_id);
      onLocationUpdate?.(data.initial_state.location || "-");
      addMessage(
        "system",
        `게임이 시작되었습니다. ` +
          `작품: ${data.plan.work_name || "?"}. ` +
          `배경: ${data.plan.world_setting || "?"}.`,
      );
    } catch (err) {
      const msg =
        err instanceof APIError
          ? `${err.message}: ${err.detail || ""}`
          : String(err);
      addMessage("error", `게임 시작 실패: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    const action = input.trim();
    if (!action || !sessionId) return;

    addMessage("user", action);
    setInput("");
    setLoading(true);

    try {
      const data = await processTurn({
        session_id: sessionId,
        user_action: action,
      });
      addMessage("gm", data.response);
      onMetricsUpdate?.(data);
      if (data.truncated) {
        addMessage("system", "⚠️ 응답이 잘렸을 가능성이 있습니다.");
      }
    } catch (err) {
      const msg =
        err instanceof APIError
          ? `${err.message}: ${err.detail || ""}`
          : String(err);
      addMessage("error", `턴 처리 실패: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] p-12 text-center">
        <h2 className="text-2xl font-bold text-cyan-400 mb-4">
          모험을 시작하세요
        </h2>
        <p className="text-slate-400 mb-6">
          아래 &ldquo;게임 시작&rdquo; 버튼을 누르면 새 세션이 만들어집니다.
        </p>
        <button
          type="button"
          onClick={handleStart}
          disabled={loading}
          className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-900 font-semibold px-6 py-2 rounded-md transition"
        >
          {loading ? "시작 중..." : "게임 시작"}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[500px]">
      <div className="flex-1 overflow-y-auto py-4 space-y-3">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex gap-2 pt-4 border-t border-slate-700">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          placeholder="행동을 입력하세요 (예: 주변을 살펴봅니다)"
          autoComplete="off"
          className="flex-1 bg-slate-900 text-slate-100 border border-slate-700 px-3 py-2 rounded-md focus:outline-none focus:border-cyan-400 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-900 font-semibold px-4 py-2 rounded-md transition"
        >
          {loading ? "..." : "전송"}
        </button>
      </div>
    </div>
  );
}
