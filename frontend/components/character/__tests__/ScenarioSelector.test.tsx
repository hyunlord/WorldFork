import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ScenarioSelector } from "../ScenarioSelector";

afterEach(cleanup);

describe("ScenarioSelector", () => {
  it("두 시나리오 표시", () => {
    render(<ScenarioSelector value="bjorn" onChange={() => {}} />);
    expect(screen.getByText("비요른 시나리오")).toBeDefined();
    expect(screen.getByText("신규 탐험가")).toBeDefined();
  });

  it("설명에 원작 명칭 노출 (투르윈/라스카니아 X → 비요른/라프도니아)", () => {
    const { container } = render(<ScenarioSelector value="bjorn" onChange={() => {}} />);
    expect(container.textContent).not.toContain("투르윈");
    expect(container.textContent).not.toContain("라스카니아");
    expect(container.textContent).toContain("비요른");
    expect(container.textContent).toContain("라프도니아");
  });

  it("클릭 시 onChange 호출", () => {
    const onChange = vi.fn();
    render(<ScenarioSelector value="bjorn" onChange={onChange} />);
    fireEvent.click(screen.getByText("신규 탐험가"));
    expect(onChange).toHaveBeenCalledWith("new_explorer");
  });
});
