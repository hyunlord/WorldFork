/**
 * WorldFork API client (★ Tier 2 D9 W3).
 *
 * FastAPI 백엔드와 통신.
 * 환경변수 NEXT_PUBLIC_API_URL (★ default: http://localhost:8090).
 */

import type {
  GameStateResponse,
  StartGameResponse,
  TurnRequest,
  TurnResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";

class APIError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errBody = await response.json();
      detail = errBody.detail;
    } catch {
      // JSON 파싱 실패 = 무시
    }
    throw new APIError(
      `API error (${response.status})`,
      response.status,
      detail,
    );
  }
  return (await response.json()) as T;
}

export async function startGame(): Promise<StartGameResponse> {
  const response = await fetch(`${API_URL}/game/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return handleResponse<StartGameResponse>(response);
}

export async function processTurn(
  request: TurnRequest,
): Promise<TurnResponse> {
  const response = await fetch(`${API_URL}/game/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handleResponse<TurnResponse>(response);
}

export async function getState(
  sessionId: string,
): Promise<GameStateResponse> {
  const response = await fetch(`${API_URL}/game/state/${sessionId}`);
  return handleResponse<GameStateResponse>(response);
}

export { APIError };
