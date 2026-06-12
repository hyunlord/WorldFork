"use client";

// V3 RTwP MVP — 자율 파티 + 실시간 자동 진행(속도배율/일시정지) + 일시정지 지시.
// backend service/api/v3_session_router.py 의 /api/v3 엔드포인트를 직접 호출한다.
// 핵심 경험: 개입 안 하면 자동 진행, 분기점(적 출현/충돌)에선 자동 일시정지(발더스식).

import { useCallback, useEffect, useRef, useState } from "react";

import { DungeonView } from "@/components/game/DungeonView";
import type { DungeonViewData } from "@/components/game/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";
const SPEEDS = [0.5, 1, 2, 4] as const;
const BASE_INTERVAL_MS = 1200; // 1× 기준 한 틱 간격(속도배율로 나눔)

interface Member {
  name: string;
  pos: [number, number];
  hp: number;
  max_hp: number;
  order: string | null;
  disposition: Record<string, number>;
  downed: boolean;
  bleeding: boolean;
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
  player_hp: number;
  player_max_hp: number;
  defeat: boolean;
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
  const [running, setRunning] = useState(false); // 자동 진행 on/off
  const [speed, setSpeed] = useState<number>(1);
  const sid = state?.session_id;

  // 자동 루프가 참조할 최신값(리렌더로 루프를 재시작하지 않게 ref로).
  const runningRef = useRef(false);
  const speedRef = useRef(1);
  const branchRef = useRef<string[]>([]); // 직전 분기점(상승엣지 자동정지 판정)
  const inFlightRef = useRef(false); // ★ 요청 비중첩 — 진행 중이면 추가 tick 차단
  useEffect(() => {
    runningRef.current = running;
  }, [running]);
  useEffect(() => {
    speedRef.current = speed;
  }, [speed]);

  // 상태 반영 — branchRef 동기화(자동정지 엣지 판정의 단일 출처).
  const apply = useCallback((r: Render) => {
    branchRef.current = r.branch;
    setState(r);
  }, []);

  const run = useCallback(
    async (fn: () => Promise<Render>) => {
      setBusy(true);
      setErr(null);
      try {
        apply(await fn());
      } catch (e) {
        setErr(`백엔드 통신 실패: ${API_URL} — ${String(e)}`);
      } finally {
        setBusy(false);
      }
    },
    [apply],
  );

  const start = useCallback(() => {
    setRunning(false);
    return run(() => call("/session/start", {}));
  }, [run]);

  useEffect(() => {
    void start();
  }, [start]);

  // 한 틱 — 결과를 반환(자동 루프가 분기점/패배를 직접 판정). 비중첩의 단위.
  const tickOnce = useCallback(
    async (spawn: boolean): Promise<Render | null> => {
      if (!sid || inFlightRef.current) return null; // 비중첩 — 직전 tick 진행 중이면 무시
      inFlightRef.current = true;
      setBusy(true);
      setErr(null);
      try {
        const r = await call("/session/tick", { session_id: sid, steps: 1, spawn_enemy: spawn });
        apply(r);
        return r;
      } catch (e) {
        setErr(`백엔드 통신 실패: ${API_URL} — ${String(e)}`);
        return null;
      } finally {
        inFlightRef.current = false;
        setBusy(false);
      }
    },
    [sid, apply],
  );

  // ★ RTwP 자동 진행 — 직전 tick await 후 다음(비중첩). 분기점 상승엣지/패배/에러 시 자동 정지.
  useEffect(() => {
    if (!running || !sid) return;
    let cancelled = false;
    let prevBranch = branchRef.current;
    void (async () => {
      while (!cancelled && runningRef.current) {
        const r = await tickOnce(false);
        if (cancelled) return;
        if (!r || r.defeat) {
          setRunning(false);
          return;
        }
        if (r.branch.length > 0 && prevBranch.length === 0) {
          setRunning(false); // 분기점(적 출현/충돌) → 자동 일시정지
          return;
        }
        prevBranch = r.branch;
        await new Promise((res) => setTimeout(res, BASE_INTERVAL_MS / speedRef.current));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [running, sid, tickOnce]);

  const sendCommand = useCallback(() => {
    if (!sid || !text.trim()) return;
    setRunning(false); // 지시 전 일시정지
    void run(() => call("/session/command", { session_id: sid, target, text })).then(() =>
      setText(""),
    );
  }, [sid, target, text, run]);

  const defeat = state?.defeat ?? false;

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
            {running && <span style={{ color: "#58e88a" }}> · ▶ 진행 중({speed}×)</span>}
            {!running && !defeat && <span style={{ color: "#888" }}> · ⏸ 일시정지</span>}
            {state.branch.length > 0 && (
              <span style={{ color: "#e85858" }}> · ★ 분기점: {state.branch.join(", ")} (지시 권장)</span>
            )}
            {defeat && <span style={{ color: "#ff5050" }}> · ☠ 패배 — 비요른 쓰러짐</span>}
          </p>

          <div style={{ height: 320, marginBottom: 8 }}>
            <DungeonView data={state.dungeon} />
          </div>

          {/* ★ RTwP 컨트롤 — 자동 진행/일시정지 + 속도배율 */}
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
            <button
              onClick={() => setRunning((v) => !v)}
              disabled={defeat}
              style={{ background: running ? "#3a2a15" : "#15301c", color: "#d8d8e0", padding: "6px 12px", border: "1px solid #444" }}
            >
              {running ? "⏸ 일시정지" : "▶ 자동 진행"}
            </button>
            <span style={{ color: "#888" }}>속도</span>
            {SPEEDS.map((sp) => (
              <button
                key={sp}
                onClick={() => setSpeed(sp)}
                style={{
                  background: speed === sp ? "#2a3a55" : "#15151c",
                  color: "#d8d8e0",
                  padding: "4px 8px",
                  border: "1px solid #333",
                }}
              >
                {sp}×
              </button>
            ))}
            <button onClick={() => tickOnce(false)} disabled={busy || running || defeat}>↦ 한 틱</button>
            <button onClick={() => tickOnce(true)} disabled={busy || defeat}>적 출현</button>
          </div>

          {/* 비요른(플레이어) HP */}
          <div style={{ marginBottom: 8 }}>
            <b style={{ color: defeat ? "#ff5050" : "#e8a838" }}>비요른</b> HP {state.player_hp}/{state.player_max_hp}
          </div>

          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <div>
              <b>파티</b>
              {state.party.map((m) => (
                <div key={m.name} style={{ margin: "4px 0", opacity: m.downed ? 0.5 : 1 }}>
                  {m.name} HP {m.hp}/{m.max_hp}
                  {m.downed && <span style={{ color: "#ff5050" }}> [쓰러짐]</span>}
                  {m.bleeding && <span style={{ color: "#e85858" }}> 🩸출혈</span>}
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
