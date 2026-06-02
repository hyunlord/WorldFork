import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SuggestedActions } from "../SuggestedActions";

afterEach(cleanup);

describe("SuggestedActions", () => {
  it("행동 3항목 버튼 렌더", () => {
    render(
      <SuggestedActions
        actions={["주변을 둘러본다", "부족장에게 말을 건다", "무기를 점검한다"]}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByTestId("suggested-actions")).toBeTruthy();
    expect(screen.getAllByTestId("suggested-action")).toHaveLength(3);
  });

  it("클릭 시 해당 문구로 onSelect 호출", () => {
    const onSelect = vi.fn();
    render(
      <SuggestedActions actions={["주변을 둘러본다", "쉰다"]} onSelect={onSelect} />,
    );
    fireEvent.click(screen.getByText("주변을 둘러본다"));
    expect(onSelect).toHaveBeenCalledWith("주변을 둘러본다");
  });

  it("actions 비면 렌더 안 함", () => {
    render(<SuggestedActions actions={[]} onSelect={() => {}} />);
    expect(screen.queryByTestId("suggested-actions")).toBeNull();
  });

  it("disabled면 버튼 비활성화", () => {
    const onSelect = vi.fn();
    render(
      <SuggestedActions actions={["쉰다"]} onSelect={onSelect} disabled />,
    );
    const btn = screen.getByTestId("suggested-action") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });
});
