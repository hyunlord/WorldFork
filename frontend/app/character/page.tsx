"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { RaceDetailPanel } from "@/components/character/RaceDetailPanel";
import { RaceSelector } from "@/components/character/RaceSelector";
import { ScenarioSelector } from "@/components/character/ScenarioSelector";
import { createCharacter } from "@/lib/api/character";
import {
  clearStoredStartNarrative,
  setStoredSessionId,
  setStoredStartNarrative,
} from "@/lib/session";
import type { Race, ScenarioMode } from "@/lib/types/character";
import { unmaskIp } from "@/lib/api/v2";

export default function CharacterPage() {
  const router = useRouter();
  const [scenario, setScenario] = useState<ScenarioMode>("bjorn");
  const [race, setRace] = useState<Race | null>("barbarian");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const raceDisabled = scenario === "bjorn";
  const effectiveRace: Race = raceDisabled ? "barbarian" : (race ?? "human");

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      // ★ 무기는 성인식(weapon_choice 단계)에서 게임 내 선택 — 미리 선택 X (ep_0002)
      const resp = await createCharacter({
        scenario_mode: scenario,
        race: raceDisabled ? undefined : effectiveRace,
      });
      // ★ 새 세션으로 교체 — 옛 session_id 잔재(던전 상태) 덮어쓰기
      setStoredSessionId(resp.session_id);
      // ★ 성인식 시작 narrative를 /game 첫 화면에서 표시 (generic 안내 대체)
      if (resp.starting_narrative) {
        setStoredStartNarrative(resp.starting_narrative);
      } else {
        clearStoredStartNarrative();
      }
      router.push("/game");
    } catch (err) {
      setError(err instanceof Error ? err.message : "캐릭터 생성에 실패했다.");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg-void text-text-bright">
      <div className="mx-auto max-w-3xl px-6 py-12 space-y-10">
        <header className="space-y-2">
          <h1 className="font-serif text-4xl tracking-[0.2em] text-amber">
            캐릭터 생성
          </h1>
          <p className="font-narrative text-sm italic tracking-[0.15em] text-text-mute">
            {unmaskIp("라스카니아 차원광장")}에 발을 들이기 전, 나는 누구인지 정해야 한다.
          </p>
        </header>

        <ScenarioSelector value={scenario} onChange={setScenario} />
        <RaceSelector value={effectiveRace} onChange={setRace} disabled={raceDisabled} />
        <RaceDetailPanel race={effectiveRace} />

        {error != null && (
          <div className="rounded border border-crimson/40 bg-crimson-dim/20 p-4 text-sm text-crimson">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => { router.push("/"); }}
            className="font-mono text-sm tracking-[0.1em] text-text-mute transition hover:text-text-mid"
          >
            ← 돌아가기
          </button>
          <button
            type="button"
            onClick={() => { void handleStart(); }}
            disabled={loading}
            className="border border-amber bg-gradient-to-br from-crimson/40 to-bg-deep px-8 py-3 font-serif text-lg tracking-[0.3em] text-amber transition hover:from-crimson/60 hover:tracking-[0.4em] hover:[text-shadow:0_0_20px_var(--color-amber)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "생성 중..." : "미궁으로"}
          </button>
        </div>
      </div>
    </main>
  );
}
