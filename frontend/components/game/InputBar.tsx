"use client";

import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useRef,
  useState,
  type CompositionEvent,
  type KeyboardEvent,
} from "react";

interface Shortcut {
  key: string;
  label: string;
}

interface Props {
  placeholder?: string;
  shortcuts?: Shortcut[];
  onSubmit?: (value: string) => void;
  onShortcut?: (key: string) => void;
  disabled?: boolean;
}

export interface InputBarHandle {
  focus: () => void;
  blur: () => void;
  isFocused: () => boolean;
}

const DEFAULT_PLACEHOLDER =
  "한스에게 다가가 인사한다  ·  WASD 무빙  ·  'a' 공격...";

const DEFAULT_SHORTCUTS: Shortcut[] = [
  { key: "i", label: "인벤토리" },
  { key: "c", label: "캐릭터" },
  { key: "M", label: "지도" },
  { key: "?", label: "도움말" },
];

export const InputBar = forwardRef<InputBarHandle, Props>(function InputBar(
  {
    placeholder = DEFAULT_PLACEHOLDER,
    shortcuts = DEFAULT_SHORTCUTS,
    onSubmit,
    onShortcut,
    disabled,
  },
  ref,
) {
  const [value, setValue] = useState("");
  const composingRef = useRef(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useImperativeHandle(
    ref,
    () => ({
      focus: () => inputRef.current?.focus(),
      blur: () => inputRef.current?.blur(),
      isFocused: () =>
        typeof document !== "undefined" &&
        document.activeElement === inputRef.current,
    }),
    [],
  );

  const handleStart = useCallback((_e: CompositionEvent<HTMLInputElement>) => {
    composingRef.current = true;
  }, []);

  const handleEnd = useCallback((_e: CompositionEvent<HTMLInputElement>) => {
    composingRef.current = false;
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      // IME 조합 중 Enter 는 무시 (★ 한국어 안전)
      if (composingRef.current || e.nativeEvent.isComposing) return;
      if (e.key === "Enter") {
        e.preventDefault();
        const trimmed = value.trim();
        if (trimmed.length === 0) return;
        onSubmit?.(trimmed);
        setValue("");
      }
    },
    [onSubmit, value],
  );

  return (
    <div className="relative flex h-[70px] items-center gap-4 border-t border-border-rune bg-gradient-to-b from-bg-deep to-bg-panel px-6">
      <span className="pointer-events-none absolute inset-x-[10%] -top-px h-px bg-gradient-to-r from-transparent via-amber to-transparent opacity-40" />

      <div className="relative flex flex-1 items-center border border-border-rune bg-bg-input px-4 py-2.5 transition focus-within:border-amber focus-within:[box-shadow:0_0_0_3px_rgba(232,168,56,0.1),0_0_16px_var(--torch-glow)]">
        <span className="mr-2 animate-torch-flicker font-mono font-bold text-amber [text-shadow:0_0_6px_var(--torch-glow)]">
          &gt;
        </span>
        <input
          ref={inputRef}
          type="text"
          autoFocus
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 border-none bg-transparent font-sans text-[0.95rem] text-text-bright outline-none placeholder:italic placeholder:text-text-faint"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onCompositionStart={handleStart}
          onCompositionEnd={handleEnd}
          onKeyDown={handleKeyDown}
        />
      </div>

      <div className="flex gap-1.5">
        {shortcuts.map((s) => (
          <button
            key={s.key}
            type="button"
            onClick={onShortcut ? () => onShortcut(s.key) : undefined}
            className="flex cursor-pointer items-center gap-1.5 border border-border-rune bg-bg-elev px-3 py-2 font-mono text-[0.7rem] text-text-mid transition hover:border-amber hover:bg-amber/5 hover:text-amber hover:[box-shadow:0_0_8px_var(--torch-glow)]"
          >
            <span className="rounded-[1px] border border-amber/20 bg-amber/10 px-1.5 py-0.5 font-bold text-amber">
              {s.key}
            </span>
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
});
