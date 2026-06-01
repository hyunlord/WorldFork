import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { RaceDetailPanel } from "../RaceDetailPanel";

afterEach(cleanup);

describe("RaceDetailPanel", () => {
  it("shows placeholder when race is null", () => {
    render(<RaceDetailPanel race={null} />);
    expect(screen.getByText(/종족을 선택하면/)).toBeDefined();
  });

  it("shows barbarian stats", () => {
    render(<RaceDetailPanel race="barbarian" />);
    expect(screen.getByText("바바리안")).toBeDefined();
    expect(screen.getByText("120")).toBeDefined();
    expect(screen.getByText("근력 +5")).toBeDefined();
  });

  it("shows fairy stats with soul power 20 and 2 slots", () => {
    render(<RaceDetailPanel race="fairy" />);
    expect(screen.getByText("요정")).toBeDefined();
    expect(screen.getByText("20")).toBeDefined();
    expect(screen.getByText("정수 슬롯 +1")).toBeDefined();
  });

  it("종족 설명에 원작 명칭 노출 (라스카니아 X → 라프도니아)", () => {
    const { container } = render(<RaceDetailPanel race="human" />);
    expect(container.textContent).toContain("라프도니아");
    expect(container.textContent).not.toContain("라스카니아");
  });
});
