import type { CharacterCreateRequest, CharacterCreateResponse } from "@/lib/types/character";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";

export async function createCharacter(
  req: CharacterCreateRequest,
): Promise<CharacterCreateResponse> {
  const response = await fetch(`${API_BASE}/api/v2/character/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = typeof data?.detail === "string" ? data.detail : JSON.stringify(data);
    } catch {
      detail = await response.text();
    }
    throw new Error(`캐릭터 생성 실패: ${response.status} ${detail}`);
  }

  return response.json() as Promise<CharacterCreateResponse>;
}
