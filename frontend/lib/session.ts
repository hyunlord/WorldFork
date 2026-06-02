/**
 * Phase D step 4 — localStorage 기반 session_id 관리.
 *
 * 시작 narrative(성인식 부족장 선언)도 함께 보관 — createCharacter 응답의
 * starting_narrative를 /game 첫 화면에서 보여주기 위해(첫 턴 입력 전까지).
 */

const SESSION_KEY = "worldfork_session_id";
const START_NARRATIVE_KEY = "worldfork_start_narrative";

export function getStoredSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(SESSION_KEY);
}

export function setStoredSessionId(sessionId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SESSION_KEY, sessionId);
}

export function clearStoredSessionId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(SESSION_KEY);
}

export function getStoredStartNarrative(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(START_NARRATIVE_KEY);
}

export function setStoredStartNarrative(narrative: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(START_NARRATIVE_KEY, narrative);
}

export function clearStoredStartNarrative(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(START_NARRATIVE_KEY);
}
