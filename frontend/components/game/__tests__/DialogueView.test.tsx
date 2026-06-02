import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DialogueView } from "../DialogueView";
import { parseDialogue } from "@/lib/game/dialogue";

afterEach(cleanup);

describe("DialogueView", () => {
  const data = parseDialogue('한스에게 다가갔다. "어서 오게." 그가 웃었다.');

  it("발화와 화자를 표시", () => {
    render(<DialogueView data={data} open onClose={() => {}} />);
    expect(screen.getByTestId("dialogue-view")).toBeTruthy();
    expect(screen.getByTestId("dialogue-speaker").textContent).toContain("한스");
    expect(screen.getByTestId("dialogue-speech").textContent).toContain("어서 오게.");
  });

  it("화자 초상 표시 (남성 기본 → other_male)", () => {
    render(<DialogueView data={data} open onClose={() => {}} />);
    const portrait = screen.getByTestId("dialogue-portrait");
    expect(portrait.getAttribute("src")).toContain("ui_dialogue_other_male");
  });

  it("여성 단서 화자 → other_female 초상", () => {
    const f = parseDialogue('실렌이 말했다. "조심해."');
    render(<DialogueView data={f} open onClose={() => {}} />);
    expect(
      screen.getByTestId("dialogue-portrait").getAttribute("src"),
    ).toContain("ui_dialogue_other_female");
  });

  it("open=false면 렌더 안 함", () => {
    render(<DialogueView data={data} open={false} onClose={() => {}} />);
    expect(screen.queryByTestId("dialogue-view")).toBeNull();
  });

  it("dialogue 아니면 렌더 안 함", () => {
    const plain = parseDialogue("주변을 살펴보았다.");
    render(<DialogueView data={plain} open onClose={() => {}} />);
    expect(screen.queryByTestId("dialogue-view")).toBeNull();
  });

  it("닫기 버튼 onClose 호출", () => {
    const onClose = vi.fn();
    render(<DialogueView data={data} open onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("대화 닫기"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
