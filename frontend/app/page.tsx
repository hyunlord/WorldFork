"use client";

import Link from "next/link";

export default function StartScreen() {
  return (
    <main className="relative grid min-h-screen grid-rows-[1fr_auto] overflow-hidden">
      <span
        className="pointer-events-none absolute inset-0 z-[1]"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at center, rgba(232,168,56,0.08) 0%, transparent 70%)",
        }}
      />

      <span className="pointer-events-none absolute left-1/2 top-[28%] z-[2] h-2 w-2 -translate-x-[260px] animate-torch-flicker rounded-full bg-amber-bright [box-shadow:0_0_24px_var(--color-amber),0_0_60px_rgba(232,168,56,0.4)]" />
      <span className="pointer-events-none absolute left-1/2 top-[28%] z-[2] h-2 w-2 translate-x-[260px] animate-torch-flicker rounded-full bg-amber-bright [box-shadow:0_0_24px_var(--color-amber),0_0_60px_rgba(232,168,56,0.4)] [animation-delay:1.2s]" />

      <section className="relative z-[3] flex flex-col items-center justify-center px-6 pt-12">
        <div className="text-center">
          <h1 className="font-serif text-7xl font-bold tracking-[0.24em] text-amber [text-shadow:0_0_40px_rgba(214,59,59,0.5),0_0_80px_rgba(232,168,56,0.3)] md:text-[6rem]">
            WORLDFORK
          </h1>
          <p className="mt-3 font-narrative text-base tracking-[0.5em] text-text-mid md:text-lg">
            ◆ 한국어 인터랙티브 게임 ◆
          </p>
          <p className="mt-8 font-narrative text-sm italic tracking-[0.3em] text-text-faint">
            좋아하는 작품 세계관에 들어가, 한 인물로 살아본다.
          </p>
        </div>

        <nav className="mt-20 flex w-[360px] flex-col gap-3.5">
          <Link
            href="/game"
            className="block cursor-pointer border border-amber bg-gradient-to-br from-crimson/50 to-bg-deep px-8 py-4 text-center font-serif text-2xl font-bold tracking-[0.4em] text-amber transition hover:bg-gradient-to-br hover:from-crimson/80 hover:to-bg-deep hover:tracking-[0.5em] hover:[text-shadow:0_0_20px_var(--color-amber)]"
          >
            새 게임
          </Link>
          <button
            type="button"
            disabled
            className="block cursor-not-allowed border border-border-rune bg-bg-deep/60 px-8 py-4 text-center font-serif text-2xl tracking-[0.4em] text-amber/35 opacity-50"
          >
            이어하기
          </button>
          <Link
            href="/town"
            className="block cursor-pointer border border-border-rune bg-bg-deep/60 px-8 py-4 text-center font-serif text-2xl tracking-[0.4em] text-amber/80 transition hover:border-amber hover:bg-crimson/30 hover:text-white hover:tracking-[0.5em] hover:[text-shadow:0_0_20px_var(--color-amber)]"
          >
            마을
          </Link>
          <button
            type="button"
            disabled
            className="mt-4 block cursor-not-allowed border border-border-rune bg-bg-deep/60 px-4 py-3 text-center font-serif text-lg tracking-[0.3em] text-amber/35 opacity-50"
          >
            설정
          </button>
        </nav>

        <div className="pointer-events-none absolute bottom-24 right-12 max-w-[400px] text-right">
          <p className="font-narrative text-sm italic leading-[1.8] tracking-[0.2em] text-text-mute">
            ~ 어느 작품의 한 페이지로,
            <br />
            <span className="font-bold text-crimson">한 인물</span>이 되어 들어선다 ~
          </p>
        </div>

        <div className="pointer-events-none absolute bottom-24 left-12 font-mono text-xs tracking-[0.2em] leading-[2] text-text-faint">
          <div>
            <kbd className="mr-1.5 border border-amber/30 bg-bg-elev/80 px-2 py-0.5 font-bold text-amber">
              ↵
            </kbd>
            선택
          </div>
          <div>
            <kbd className="mr-1.5 border border-amber/30 bg-bg-elev/80 px-2 py-0.5 font-bold text-amber">
              ESC
            </kbd>
            취소
          </div>
        </div>
      </section>

      <footer className="z-[3] flex justify-between bg-gradient-to-b from-transparent to-bg-void/85 px-8 py-4 font-mono text-xs tracking-[0.2em] text-text-faint">
        <span>Phase B — Frontend Wireframe</span>
        <span>DGX Spark · LLM-CRPG</span>
        <span>© 2026 WorldFork</span>
      </footer>
    </main>
  );
}
