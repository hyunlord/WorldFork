import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { LoadingIndicator } from "../LoadingIndicator";

afterEach(cleanup);

describe("LoadingIndicator", () => {
  it("visible이면 '이야기를 짓는 중' 표시", () => {
    render(<LoadingIndicator visible />);
    expect(screen.getByTestId("loading-indicator")).toBeTruthy();
    expect(screen.getByText(/이야기를 짓는 중/)).toBeTruthy();
  });

  it("visible=false면 렌더 안 함", () => {
    render(<LoadingIndicator visible={false} />);
    expect(screen.queryByTestId("loading-indicator")).toBeNull();
  });
});
