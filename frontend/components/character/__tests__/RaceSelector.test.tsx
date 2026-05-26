import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RACES } from "@/lib/types/character";

import { RaceSelector } from "../RaceSelector";

describe("RaceSelector", () => {
  it("renders all 5 races", () => {
    render(<RaceSelector value={null} onChange={() => {}} />);
    for (const race of RACES) {
      expect(screen.getAllByText(race.nameKo).length).toBeGreaterThan(0);
    }
  });

  it("disables all race buttons when disabled prop is true", () => {
    const onChange = vi.fn();
    render(<RaceSelector value={null} onChange={onChange} disabled />);
    const buttons = screen.getAllByRole("button") as HTMLButtonElement[];
    for (const btn of buttons) {
      fireEvent.click(btn);
    }
    expect(onChange).not.toHaveBeenCalled();
  });

  it("calls onChange with correct race id when button is clicked", () => {
    const onChange = vi.fn();
    const { container } = render(<RaceSelector value={null} onChange={onChange} />);
    const buttons = container.querySelectorAll("button");
    // RACES order: barbarian, human, dwarf, beastkin, fairy → index 4 = fairy
    const fairyBtn = buttons.item(4);
    if (fairyBtn) fireEvent.click(fairyBtn);
    expect(onChange).toHaveBeenCalledWith("fairy");
  });

  it("marks selected race button with amber border class", () => {
    const { container } = render(
      <RaceSelector value="dwarf" onChange={() => {}} />,
    );
    const buttons = container.querySelectorAll("button");
    // RACES order: barbarian, human, dwarf → index 2
    const dwarfBtn = buttons.item(2);
    expect(dwarfBtn?.className).toContain("border-amber");
  });
});
