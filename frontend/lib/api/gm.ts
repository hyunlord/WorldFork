// AI GM 서사 슬라이스 — /api/gm 클라이언트(SSE 스트리밍 포함).
// 이름은 백엔드가 변환명으로 주고, 화면 표시는 unmaskIp(원작명)로 변환한다.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";

export interface GMChoice {
  id: string;
  label: string;
}
export interface GMMember {
  name: string;
  hp: number;
  max_hp: number;
  disposition: Record<string, number>;
}
export interface GMFoe {
  name: string;
  hp: number;
  max_hp: number;
}
export interface GMReaction {
  name: string;
  reaction: string; // comply / adapt / refuse
  action: string;
  reason: string;
  speech: string;
}
export interface GMRender {
  session_id: string;
  beat: string;
  narration: string;
  choices: GMChoice[];
  speaker: string | null;
  hp: number;
  max_hp: number;
  weapon: string;
  stones: number;
  items: string[];
  flags: Record<string, string>;
  relationships: Record<string, number>;
  party: GMMember[];
  foe: GMFoe | null;
  bleeding: boolean;
  illustration: string | null;
  companion_reaction: GMReaction | null;
}

export async function startGm(): Promise<GMRender> {
  const r = await fetch(`${API_URL}/api/gm/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`start ${r.status}`);
  return (await r.json()) as GMRender;
}

export interface GmStreamHandlers {
  onNarration?: (chunk: string) => void; // 점진 표시(흐르는 서술)
  onDone?: (r: GMRender) => void; // 최종 상태(권위)
  onError?: (detail: string) => void;
}

interface ActBody {
  session_id: string;
  choice_id?: string;
  free_text?: string;
}

// fetch + ReadableStream으로 SSE 직접 파싱. 기본 프레임(data:{narration}) → onNarration,
// event: done(data:{render}) → onDone, event: error → onError.
export async function streamGmAct(
  body: ActBody,
  h: GmStreamHandlers,
): Promise<GMRender | null> {
  const resp = await fetch(`${API_URL}/api/gm/session/act/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!resp.ok || resp.body === null) {
    throw new Error(`act/stream ${resp.status}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let final: GMRender | null = null;

  const handleFrame = (frame: string): void => {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    const data = dataLines.join("\n");
    if (data.length === 0) return;
    if (event === "message") {
      const obj = JSON.parse(data) as { narration?: string };
      if (obj.narration) h.onNarration?.(obj.narration);
    } else if (event === "done") {
      final = JSON.parse(data) as GMRender;
      h.onDone?.(final);
    } else if (event === "error") {
      const obj = JSON.parse(data) as { detail?: string };
      h.onError?.(obj.detail ?? "stream error");
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      handleFrame(buffer.slice(0, idx));
      buffer = buffer.slice(idx + 2);
    }
  }
  if (buffer.trim()) handleFrame(buffer);
  return final;
}
