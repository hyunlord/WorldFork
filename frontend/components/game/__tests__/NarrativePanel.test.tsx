import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NarrativePanel } from "../NarrativePanel";
import type { NarrativePanelData } from "../types";

function makeData(text: string): NarrativePanelData {
  return {
    turn: 1,
    paragraphs: [{ spans: [{ kind: "plain", text }] }],
  };
}

function makeEssenceData(text: string): NarrativePanelData {
  // Pre-split with essence span (simulates what narrativeStringToData produces)
  return {
    turn: 1,
    paragraphs: [
      {
        spans: [
          { kind: "plain", text: "나는 정수를 들었다. " },
          { kind: "essence", text },
          { kind: "plain", text: " 강해졌다." },
        ],
      },
    ],
  };
}

describe("NarrativePanel", () => {
  it("renders plain text", () => {
    const { container } = render(<NarrativePanel data={makeData("평범한 텍스트")} />);
    expect(container.textContent).toContain("평범한 텍스트");
  });

  it("renders essence span with amber highlight class", () => {
    const essenceText = "「캐릭터의 영혼에 '고블린의 정수'이(가) 스며듭니다.」";
    const { container } = render(
      <NarrativePanel data={makeEssenceData(essenceText)} />,
    );
    // essence span has bg-amber/10 class — find all amber spans and check content
    const amberSpans = Array.from(container.querySelectorAll(".text-amber"));
    const essenceSpan = amberSpans.find((el) =>
      el.textContent?.includes("고블린의 정수"),
    );
    expect(essenceSpan).not.toBeUndefined();
  });

  it("renders turn number", () => {
    const { container } = render(<NarrativePanel data={makeData("text")} />);
    expect(container.textContent).toContain("TURN 1");
  });
});
