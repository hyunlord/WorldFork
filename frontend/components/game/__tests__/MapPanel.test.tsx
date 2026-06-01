import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MapPanel } from "../MapPanel";

afterEach(cleanup);

describe("MapPanel", () => {
  it("성인식 마을(floor 0) 현재 위치 표시", () => {
    render(
      <MapPanel
        open
        onClose={() => {}}
        floor={0}
        subArea="성인식 마을"
        riftId={null}
        activeRifts={[]}
      />,
    );
    expect(screen.getByTestId("map-panel")).toBeTruthy();
    expect(screen.getByTestId("map-current").textContent).toContain("성지");
  });

  it("rift 4종 렌더 + 진입 균열 강조", () => {
    const { container } = render(
      <MapPanel
        open
        onClose={() => {}}
        floor={1}
        subArea="1챕터"
        riftId="bloody_castle"
        activeRifts={["bloody_castle"]}
      />,
    );
    expect(container.querySelectorAll("[data-rift-id]")).toHaveLength(4);
    const here = container.querySelector('[data-rift-id="bloody_castle"]');
    expect(here?.textContent).toContain("진입 중");
    expect(container.textContent).toContain("핏빛성채");
    expect(container.textContent).toContain("강철의 묘");
  });

  it("open=false면 렌더 안 함", () => {
    render(
      <MapPanel
        open={false}
        onClose={() => {}}
        floor={0}
        subArea={null}
        riftId={null}
        activeRifts={[]}
      />,
    );
    expect(screen.queryByTestId("map-panel")).toBeNull();
  });

  it("닫기 버튼 onClose 호출", () => {
    const onClose = vi.fn();
    render(
      <MapPanel
        open
        onClose={onClose}
        floor={0}
        subArea={null}
        riftId={null}
        activeRifts={[]}
      />,
    );
    fireEvent.click(screen.getByLabelText("지도 닫기"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
