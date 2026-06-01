import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GameMenu } from "../GameMenu";

afterEach(cleanup);

function setup(overrides: Partial<Parameters<typeof GameMenu>[0]> = {}) {
  const props = {
    open: true,
    onClose: vi.fn(),
    onCharacter: vi.fn(),
    onMap: vi.fn(),
    onHelp: vi.fn(),
    ...overrides,
  };
  render(<GameMenu {...props} />);
  return props;
}

describe("GameMenu", () => {
  it("캐릭터/지도/도움말 항목 렌더", () => {
    setup();
    expect(screen.getByTestId("menu-character")).toBeTruthy();
    expect(screen.getByTestId("menu-map")).toBeTruthy();
    expect(screen.getByTestId("menu-help")).toBeTruthy();
  });

  it("지도 클릭 → onMap + onClose", () => {
    const props = setup();
    fireEvent.click(screen.getByTestId("menu-map"));
    expect(props.onMap).toHaveBeenCalledOnce();
    expect(props.onClose).toHaveBeenCalledOnce();
  });

  it("도움말 클릭 → onHelp", () => {
    const props = setup();
    fireEvent.click(screen.getByTestId("menu-help"));
    expect(props.onHelp).toHaveBeenCalledOnce();
  });

  it("open=false면 렌더 안 함", () => {
    setup({ open: false });
    expect(screen.queryByTestId("game-menu")).toBeNull();
  });
});
