import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HelpPanel } from "../HelpPanel";

afterEach(cleanup);

describe("HelpPanel", () => {
  it("조작/시스템 섹션 표시", () => {
    const { container } = render(<HelpPanel open onClose={() => {}} />);
    expect(screen.getByTestId("help-panel")).toBeTruthy();
    expect(container.textContent).toContain("조작");
    expect(container.textContent).toContain("시스템");
    expect(container.textContent).toContain("정수 흡수");
  });

  it("open=false면 렌더 안 함", () => {
    render(<HelpPanel open={false} onClose={() => {}} />);
    expect(screen.queryByTestId("help-panel")).toBeNull();
  });

  it("닫기 버튼 onClose 호출", () => {
    const onClose = vi.fn();
    render(<HelpPanel open onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("도움말 닫기"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
