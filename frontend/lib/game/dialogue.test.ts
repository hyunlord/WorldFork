import { describe, expect, it } from "vitest";

import { parseDialogue } from "./dialogue";

describe("parseDialogue", () => {
  it("큰따옴표 발화를 dialogue로 판정", () => {
    const out = parseDialogue('한스에게 다가갔다. "어서 오게, 젊은이." 그가 웃었다.');
    expect(out.isDialogue).toBe(true);
    const speech = out.segments.filter((s) => s.kind === "speech");
    expect(speech).toHaveLength(1);
    expect(speech[0].text).toBe("어서 오게, 젊은이.");
  });

  it("발화 없는 지문은 dialogue 아님", () => {
    const out = parseDialogue("나는 주변을 살펴보았다. 아무도 없었다.");
    expect(out.isDialogue).toBe(false);
  });

  it("화자를 지문에서 추정 (에게 패턴)", () => {
    const out = parseDialogue('셰인에게 말을 건넸다. "무슨 일이지?"');
    expect(out.speaker).toBe("셰인");
  });

  it("화자 추정 실패 시 기본값", () => {
    const out = parseDialogue('"누구냐!" 목소리가 울렸다.');
    expect(out.speaker).toBe("대화 상대");
    expect(out.isDialogue).toBe(true);
  });

  it("한글 스마트쿼트 발화도 인식", () => {
    const out = parseDialogue("투르윈이 고개를 들었다. “준비됐나?”");
    expect(out.isDialogue).toBe(true);
    const speech = out.segments.filter((s) => s.kind === "speech");
    expect(speech[0].text).toBe("준비됐나?");
  });
});
