import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBar } from "../StatusBar";
import type { StatusBarData } from "../types";

const base: StatusBarData = {
  mode: "dungeon",
  hp: 100,
  hpMax: 120,
  soulPower: 15,
  soulPowerMax: 20,
  essenceCount: 1,
  essenceMax: 2,
  playerLevel: 3,
  hoursInDungeon: 0,
  hoursMax: 174,
  locationLabel: "1층 · 진입점",
  timeOfDay: "밤",
  floorNumber: 0,
};

describe("StatusBar", () => {
  it("renders HP value", () => {
    const { container } = render(<StatusBar data={base} />);
    expect(container.textContent).toContain("100");
    expect(container.textContent).toContain("120");
  });

  it("renders 영혼력 when soulPower is set", () => {
    const { container } = render(<StatusBar data={base} />);
    expect(container.textContent).toContain("영혼력");
    expect(container.textContent).toContain("15");
  });

  it("renders 정수 슬롯 count", () => {
    const { container } = render(<StatusBar data={base} />);
    expect(container.textContent).toContain("정수");
    expect(container.textContent).toContain("1");
  });

  it("renders player level", () => {
    const { container } = render(<StatusBar data={base} />);
    expect(container.textContent).toContain("Lv");
    expect(container.textContent).toContain("3");
  });

  it("shows cycle bar when floorNumber > 0", () => {
    const data: StatusBarData = { ...base, floorNumber: 1, hoursInDungeon: 50 };
    const { container } = render(<StatusBar data={data} />);
    expect(container.textContent).toContain("168h");
    expect(container.textContent).toContain("잔여");
  });

  it("hides cycle bar when floor=0", () => {
    const { container } = render(<StatusBar data={base} />);
    expect(container.textContent).not.toContain("168h");
  });

  it("shows amber time text when hoursLeft <= 24", () => {
    // 150h in dungeon → 18h left → warning
    const data: StatusBarData = { ...base, floorNumber: 1, hoursInDungeon: 150 };
    render(<StatusBar data={data} />);
    // 18h remaining
    const spans = document.querySelectorAll(".text-amber");
    expect(spans.length).toBeGreaterThan(0);
  });
});
