"use client";

// V3 RTwP MVP — 자율 파티 + 일시정지 지시 + 영구 (재미 검증용 최소 플레이 화면).
// backend service/api/v3_session_router.py 의 /api/v3 엔드포인트를 직접 호출한다.
// 풀 UI 아님 — 핵심 경험(틱 진행 / 일시정지 자연어 지시 / 영구)을 브라우저로 체감.

import { useCallback, useEffect, useState } from "react";

import { DungeonView } from "@/components/game/DungeonView";
import type { DungeonViewData } from "@/components/game/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";

interface Member {
  name: string;
  pos: [number, number];
  hp: number;
  max_hp: number;
  order: string | null;
  disposition: Record<string, number>;
}
interface Enemy {
  name: string;
  pos: [number, number];
  hp: number;
}
interface Render {
  session_id: string;
  tick: number;
  party: Member[];
  enemies: Enemy[];
  flags: Record<string, string>;
  relationships: Record<string, number>;
  branch: string[];
  dungeon: DungeonViewData;
  log: string[];
}

async function call(path: string, body?: unknown): Promise<Render> {
  const resp = await fetch(`${API_URL}/api/v3${path}`, {
    method: body === undefined && path.startsWith("/session/") ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!resp.ok) throw new Error(`${resp.status}`);
  return (await resp.json()) as Render;
}

export default function V3Page() {
  const [state, setState] = useState<Render | null>(null);
  const [target, setTarget] = useState("all");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const sid = state?.session_id;

  // ★ 실패가 silent로 죽지 않게 — 모든 호출을 감싸 에러를 화면에 노출(진단 가능).
  const run = useCallback(async (fn: () => Promise<Render>) => {
    setBusy(true);
    setErr(null);
    try {
      setState(await fn());
    } catch (e) {
      setErr(`백엔드 통신 실패: ${API_URL} — ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }, []);

  const start = useCallback(() => run(() => call("/session/start", {})), [run]);

  useEffect(() => {
    void start();
  }, [start]);

  const tick = useCallback(
    (spawn: boolean) => {
      if (!sid) return;
      void run(() => call("/session/tick", { session_id: sid, steps: 1, spawn_enemy: spawn }));
    },
    [sid, run],
  );

  const sendCommand = useCallback(() => {
    if (!sid || !text.trim()) return;
    void run(() => call("/session/command", { session_id: sid, target, text })).then(() =>
      setText(""),
    );
  }, [sid, target, text, run]);

  return (
    <main style={{ fontFamily: "monospace", padding: 24, background: "#0b0b10", color: "#d8d8e0", minHeight: "100vh" }}>
      <h1 style={{ color: "#e8a838" }}>WorldFork · V3 RTwP (자율 파티 MVP)</h1>
      {err && (
        <div style={{ background: "#3a1515", color: "#ff9090", padding: 10, marginBottom: 12 }}>
          ⚠ {err}
          <button onClick={() => start()} style={{ marginLeft: 12 }}>다시 시작</button>
        </div>
      )}
      {!state ? (
        <p>{busy ? "세션 시작 중…" : <button onClick={() => start()}>세션 시작</button>}</p>
      ) : (
        <>
          <p>
            틱 {state.tick}
            {state.branch.length > 0 && (
              <span style={{ color: "#e85858" }}> · ★ 분기점: {state.branch.join(", ")} (일시정지·지시 권장)</span>
            )}
          </p>

          <div style={{ height: 320, marginBottom: 8 }}>
            <DungeonView data={state.dungeon} />
          </div>

          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <div>
              <b>파티</b>
              {state.party.map((m) => (
                <div key={m.name} style={{ margin: "4px 0" }}>
                  {m.name} HP {m.hp}/{m.max_hp}
                  {m.order && <span style={{ color: "#58a8e8" }}> [명령:{m.order}]</span>}
                  <span style={{ fontSize: 11, color: "#888" }}>
                    {" "}저돌{m.disposition["저돌"]} 지혜{m.disposition["지혜"]} 유대{m.disposition["유대"]}
                  </span>
                </div>
              ))}
            </div>
            <div>
              <b>적</b>
              {state.enemies.length === 0 ? <div style={{ color: "#888" }}>없음</div> :
                state.enemies.map((e, i) => <div key={i}>{e.name} HP {e.hp}</div>)}
              <b>영구 변화</b>
              {Object.entries(state.flags).map(([k, v]) => (
                <div key={k} style={{ color: "#e85858" }}>{k}: {v}</div>
              ))}
              {Object.entries(state.relationships).map(([k, v]) => (
                <div key={k}>{k}: 관계 {v}</div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
            <button onClick={() => tick(false)} disabled={busy}>▶ 진행(틱)</button>
            <button onClick={() => tick(true)} disabled={busy}>적 출현</button>
          </div>

          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <span>⏸ 일시정지 지시 →</span>
            <select value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="all">전원</option>
              {state.party.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
            </select>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendCommand()}
              placeholder="예: 전원 후퇴하라 / 함정을 살펴라"
              style={{ flex: 1, padding: 6, background: "#15151c", color: "#d8d8e0", border: "1px solid #333" }}
            />
            <button onClick={() => sendCommand()} disabled={busy}>지시</button>
          </div>

          <div style={{ marginTop: 16 }}>
            <b>로그</b>
            <div style={{ background: "#15151c", padding: 10, maxHeight: 200, overflow: "auto" }}>
              {state.log.map((l, i) => <div key={i} style={{ margin: "2px 0" }}>{l}</div>)}
            </div>
          </div>
        </>
      )}
    </main>
  );
}
