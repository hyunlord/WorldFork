import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SurroundingsPanel } from "../SurroundingsPanel";

afterEach(cleanup);

describe("SurroundingsPanel", () => {
  it("NPC와 출구 엔티티 표시", () => {
    render(
      <SurroundingsPanel
        locationLabel="부족 성지"
        entities={[
          { kind: "npc", label: "부족장" },
          { kind: "exit", label: "미궁으로 가는 길" },
        ]}
      />,
    );
    expect(screen.getByTestId("surroundings-panel")).toBeTruthy();
    expect(screen.getByTestId("surrounding-npc").textContent).toContain("부족장");
    expect(screen.getByTestId("surrounding-exit").textContent).toContain("미궁");
    expect(screen.getByText(/부족 성지/)).toBeTruthy();
  });

  it("엔티티 없으면 안내 문구", () => {
    render(<SurroundingsPanel locationLabel="어딘가" entities={[]} />);
    expect(screen.getByText(/눈에 띄는 것이 없다/)).toBeTruthy();
    expect(screen.queryByTestId("surrounding-npc")).toBeNull();
  });
});
