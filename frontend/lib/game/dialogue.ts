/**
 * NPC dialogue 파싱 — handle_dialogue(action_handlers.py) narrative 정합.
 *
 * 27B dialogue narrative는 NPC 발화를 큰따옴표("..." 또는 "...")로 표기한다
 * (dialogue_27b.py SYSTEM prompt). 전용 dialogue UI(DialogueView)가 발화를
 * 지문(narration)과 분리해 보여주도록 narrative 텍스트를 segment로 쪼갠다.
 */

export type DialogueSegmentKind = "speech" | "narration";

export interface DialogueSegment {
  kind: DialogueSegmentKind;
  text: string;
}

export interface ParsedDialogue {
  /** 큰따옴표 발화가 하나라도 있으면 dialogue로 판정. */
  isDialogue: boolean;
  /** 첫 발화 직전 지문에서 추정한 화자. 실패 시 "대화 상대". */
  speaker: string;
  segments: DialogueSegment[];
}

// ASCII " 와 한글 스마트쿼트 "" 양쪽 지원 (27B 출력 변동 대응).
const QUOTE_RE = /(["“][^"”]+["”])/g;
// 화자 추정 — 발화 앞 지문의 "<이름>(역할)에게/은/는/이/가" 패턴.
const SPEAKER_RE =
  /([가-힣]{2,6}|[A-Za-z][A-Za-z·]+)\s*(?:\([^)]*\))?\s*(?:에게|이라고|라고|이|가|은|는)/;

const FALLBACK_SPEAKER = "대화 상대";

function isQuoted(text: string): boolean {
  const head = text[0];
  const tail = text[text.length - 1];
  return (head === '"' || head === "“") && (tail === '"' || tail === "”");
}

function stripQuotes(text: string): string {
  return text.replace(/^["“]/, "").replace(/["”]$/, "").trim();
}

/** narrative 텍스트를 dialogue segment로 파싱. */
export function parseDialogue(narrative: string): ParsedDialogue {
  const parts = narrative.split(QUOTE_RE).filter((p) => p.length > 0);
  const segments: DialogueSegment[] = [];
  let firstNarration = "";
  let sawSpeech = false;

  for (const part of parts) {
    if (isQuoted(part)) {
      const inner = stripQuotes(part);
      if (inner.length > 0) {
        segments.push({ kind: "speech", text: inner });
        sawSpeech = true;
      }
    } else {
      const trimmed = part.trim();
      if (trimmed.length > 0) {
        if (!sawSpeech && firstNarration === "") firstNarration = trimmed;
        segments.push({ kind: "narration", text: trimmed });
      }
    }
  }

  let speaker = FALLBACK_SPEAKER;
  const m = firstNarration.match(SPEAKER_RE);
  if (m && m[1] && m[1] !== "나") speaker = m[1];

  return { isDialogue: sawSpeech, speaker, segments };
}
