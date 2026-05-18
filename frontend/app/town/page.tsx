"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type {
  CompositionEvent,
  KeyboardEvent as ReactKeyboardEvent,
} from "react";

import { StatusBar } from "@/components/game/StatusBar";
import { TownView } from "@/components/game/TownView";
import type { StatusBarData } from "@/components/game/types";
import { DEMO_TOWN } from "@/lib/game/mockData";
import { useKeyboard } from "@/lib/hooks/useKeyboard";

const STATUS: StatusBarData = {
  mode: "town",
  hp: 100,
  hpMax: 100,
  grade: "7등급",
  mageStones: 432,
  locationLabel: "RUN 3 · 3 클리어",
  timeOfDay: "낮",
};

const TOWN_PLACEHOLDER =
  "선술집에서 한스에게 다음 던전 정보를 물어본다 / 또는 1-8 단축키...";

export default function TownPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);
  const [value, setValue] = useState("");

  const handlePoi = useCallback(
    (id: string) => {
      if (id === "rift") router.push("/game");
    },
    [router],
  );

  const handleSubmit = useCallback((text: string) => {
    void text;
    // Phase D: 자연어 town action
  }, []);

  const handleKeyDown = useCallback(
    (e: ReactKeyboardEvent<HTMLInputElement>) => {
      if (composingRef.current || e.nativeEvent.isComposing) return;
      if (e.key === "Enter") {
        e.preventDefault();
        const trimmed = value.trim();
        if (trimmed.length === 0) return;
        handleSubmit(trimmed);
        setValue("");
      }
    },
    [handleSubmit, value],
  );

  useKeyboard(
    (key) => {
      if (key === "Escape") {
        inputRef.current?.blur();
        return;
      }
      const match = DEMO_TOWN.pois.find((p) => p.key === key);
      if (match) handlePoi(match.id);
    },
    { enabled: true, ignoreWhenInput: true },
  );

  return (
    <div className="grid h-screen grid-rows-[50px_1fr_70px] overflow-hidden">
      <StatusBar data={STATUS} />

      <TownView data={DEMO_TOWN} onPoi={handlePoi} />

      <div className="relative flex h-[70px] items-center gap-4 border-t border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel px-6">
        <span className="pointer-events-none absolute inset-x-[10%] -top-px h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-40" />

        <div className="relative flex flex-1 items-center border border-border-rune bg-bg-input px-4 py-2.5 transition focus-within:border-amber focus-within:[box-shadow:0_0_0_3px_rgba(232,168,56,0.1),0_0_16px_var(--torch-glow)]">
          <span className="mr-2 animate-torch-flicker font-mono font-bold text-amber [text-shadow:0_0_6px_var(--torch-glow)]">
            &gt;
          </span>
          <input
            ref={inputRef}
            type="text"
            placeholder={TOWN_PLACEHOLDER}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onCompositionStart={(_: CompositionEvent<HTMLInputElement>) => {
              composingRef.current = true;
            }}
            onCompositionEnd={(_: CompositionEvent<HTMLInputElement>) => {
              composingRef.current = false;
            }}
            onKeyDown={handleKeyDown}
            className="flex-1 border-none bg-transparent font-sans text-[0.95rem] text-text-bright outline-none placeholder:italic placeholder:text-text-faint"
          />
        </div>

        <button
          type="button"
          onClick={() => router.push("/game")}
          className="cursor-pointer border border-amber bg-gradient-to-b from-amber/20 to-amber/[0.08] px-6 py-2.5 font-serif text-base font-bold tracking-[0.1em] text-amber-bright transition [box-shadow:0_0_16px_rgba(232,168,56,0.3)] hover:bg-gradient-to-b hover:from-amber/35 hover:to-amber/15 hover:[box-shadow:0_0_24px_rgba(232,168,56,0.5)]"
        >
          ⚔ 출발
        </button>
      </div>
    </div>
  );
}
