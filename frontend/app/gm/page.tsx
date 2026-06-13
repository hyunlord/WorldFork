"use client";

// AI GM 오프닝 슬라이스 — 서사 플레이 페이지(/gm).
// 서술(스트리밍) + 선택지 + 자유 입력 + 배경 아트 + 포트레이트 + 일러스트 + 파티/적 상태.
// 화면 표시명은 unmaskIp(원작명: 아이나르·비요른). 백엔드/코드는 변환명.

import { useCallback, useEffect, useRef, useState } from "react";

import { InputBar } from "@/components/game/InputBar";
import { SuggestedActions } from "@/components/game/SuggestedActions";
import { unmaskIp } from "@/lib/api/v2";
import { type GMRender, startGm, streamGmAct } from "@/lib/api/gm";

const ART = "/assets/worldfork";

function art(key: string | null | undefined): string | null {
  return key ? `${ART}/${key}.png` : null;
}

// 동료 변환명 → 포트레이트 자산(카이라 전투/포트레이트 스틸 부재 → null fallback).
function portrait(name: string): string | null {
  if (name === "투르윈") return `${ART}/ui_character_bjorn.png`;
  return null; // 카이라(아이나르) 포트레이트 부족분
}

export default function GMPage() {
  const [state, setState] = useState<GMRender | null>(null);
  const [narration, setNarration] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const streaming = useRef(false);

  const begin = useCallback(async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await startGm();
      setState(r);
      setNarration(r.narration);
    } catch (e) {
      setErr(`GM 시작 실패: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void begin();
  }, [begin]);

  const act = useCallback(
    async (body: { choice_id?: string; free_text?: string }) => {
      if (!state || busy || streaming.current) return;
      streaming.current = true;
      setBusy(true);
      setErr(null);
      setNarration(""); // 새 비트 — 흐르며 채워진다
      try {
        await streamGmAct(
          { session_id: state.session_id, ...body },
          {
            onNarration: (chunk) => setNarration((prev) => prev + chunk),
            onDone: (r) => {
              setState(r);
              setNarration(r.narration); // 정본으로 교체
            },
            onError: (d) => setErr(`스트림 오류: ${d}`),
          },
        );
      } catch (e) {
        setErr(`행동 실패: ${String(e)}`);
      } finally {
        streaming.current = false;
        setBusy(false);
        setText("");
      }
    },
    [state, busy],
  );

  const cr = state?.companion_reaction;
  const bg = art("ui_gameplay_bg_crystal");
  const illus = art(state?.illustration);

  return (
    <main
      style={{
        fontFamily: "ui-serif, serif",
        minHeight: "100vh",
        color: "#e6e6ea",
        background: bg
          ? `linear-gradient(rgba(8,8,14,0.78), rgba(8,8,14,0.92)), url(${bg}) center/cover fixed`
          : "#0b0b10",
        padding: 20,
      }}
    >
      <div style={{ maxWidth: 980, margin: "0 auto" }}>
        <h1 style={{ color: "#e8a838", fontFamily: "monospace" }}>
          WorldFork · 게임 속 바바리안으로 살아남기
        </h1>
        {err && (
          <div style={{ background: "#3a1515", color: "#ff9090", padding: 10, marginBottom: 12 }}>
            ⚠ {err} <button onClick={() => begin()} style={{ marginLeft: 12 }}>다시 시작</button>
          </div>
        )}

        {!state ? (
          <p style={{ fontFamily: "monospace" }}>{busy ? "성지로 들어서는 중…" : "세션 준비"}</p>
        ) : (
          <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
            {/* 좌: 일러스트 + 서술 */}
            <section style={{ flex: "1 1 560px", minWidth: 320 }}>
              {illus && (
                <img
                  src={illus}
                  alt=""
                  style={{
                    width: "100%",
                    maxHeight: 280,
                    objectFit: "cover",
                    borderRadius: 6,
                    border: "1px solid #2a2a3a",
                    marginBottom: 12,
                  }}
                />
              )}
              <div style={{ fontSize: 12, color: "#888", fontFamily: "monospace", marginBottom: 6 }}>
                비트 {state.beat}
                {busy && <span style={{ color: "#58e88a" }}> · GM 서술 중…</span>}
              </div>
              <div
                style={{
                  background: "rgba(12,12,20,0.7)",
                  padding: 16,
                  borderRadius: 6,
                  lineHeight: 1.8,
                  minHeight: 120,
                  whiteSpace: "pre-wrap",
                }}
              >
                {state.speaker && (
                  <b style={{ color: "#e8a838" }}>{unmaskIp(state.speaker)}: </b>
                )}
                {unmaskIp(narration) || (busy ? "…" : "")}
              </div>

              {/* 선택지 + 자유 입력 */}
              <div style={{ marginTop: 14 }}>
                <SuggestedActions
                  actions={state.choices.map((c) => unmaskIp(c.label))}
                  onSelect={(label) => {
                    const idx = state.choices.findIndex((c) => unmaskIp(c.label) === label);
                    const choice = state.choices[idx];
                    if (choice) void act({ choice_id: choice.id });
                  }}
                  disabled={busy}
                />
              </div>
              <div style={{ marginTop: 10 }}>
                <InputBar
                  placeholder="자유롭게 행동하세요 (예: 도끼로 돌격한다 / 신중히 살핀다)"
                  shortcuts={[]}
                  onSubmit={(v) => {
                    setText(v);
                    void act({ free_text: v });
                  }}
                  disabled={busy}
                />
              </div>
            </section>

            {/* 우: 상태(비요른/카이라/적/소지금) */}
            <aside style={{ flex: "0 0 300px", fontFamily: "monospace", fontSize: 14 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                {portrait("투르윈") && (
                  <img src={portrait("투르윈")!} alt="" style={{ width: 56, height: 56, objectFit: "cover", borderRadius: 4 }} />
                )}
                <div>
                  <b style={{ color: "#e8a838" }}>{unmaskIp("투르윈")}</b>
                  <div>HP {state.hp}/{state.max_hp} {state.bleeding && <span style={{ color: "#e85858" }}>🩸출혈</span>}</div>
                  <div style={{ color: "#e8c838" }}>💰 {state.stones} 스톤 · {state.weapon || "맨손"}</div>
                </div>
              </div>

              {state.party.map((m) => (
                <div key={m.name} style={{ marginTop: 12, borderTop: "1px solid #2a2a3a", paddingTop: 8 }}>
                  <b style={{ color: "#a8c8e8" }}>{unmaskIp(m.name)}</b> HP {m.hp}/{m.max_hp}
                  <div style={{ fontSize: 11, color: "#888" }}>
                    저돌{m.disposition["저돌"]} 지혜{m.disposition["지혜"]} 유대{m.disposition["유대"]}
                  </div>
                  {cr && cr.name === m.name && (
                    <div style={{ marginTop: 4, background: "rgba(40,30,60,0.6)", padding: 8, borderRadius: 4 }}>
                      <span style={{ color: cr.reaction === "refuse" ? "#ff7070" : cr.reaction === "adapt" ? "#e8c838" : "#70d070" }}>
                        「{cr.reaction}」
                      </span>{" "}
                      <span style={{ fontStyle: "italic" }}>{unmaskIp(cr.speech)}</span>
                      <div style={{ fontSize: 11, color: "#999", marginTop: 2 }}>— {unmaskIp(cr.reason)}</div>
                    </div>
                  )}
                </div>
              ))}

              {state.foe && (
                <div style={{ marginTop: 12, borderTop: "1px solid #5a2a2a", paddingTop: 8 }}>
                  <b style={{ color: "#e85858" }}>⚔ {unmaskIp(state.foe.name)}</b> HP {state.foe.hp}/{state.foe.max_hp}
                </div>
              )}

              {(Object.keys(state.flags).length > 0 || state.items.length > 0) && (
                <div style={{ marginTop: 12, borderTop: "1px solid #2a2a3a", paddingTop: 8, fontSize: 11, color: "#999" }}>
                  {state.items.length > 0 && <div>소지품: {state.items.map(unmaskIp).join(", ")}</div>}
                  {Object.entries(state.flags).map(([k, v]) => (
                    <div key={k}>{unmaskIp(k)}: {unmaskIp(v)}</div>
                  ))}
                </div>
              )}
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
