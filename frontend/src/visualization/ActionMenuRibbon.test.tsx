import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ActionOption, FrameState } from "../data/schemas";
import { ActionMenuRibbon, stableActionKey } from "./ActionMenuRibbon";

const frames = [
  { frame_id: 1, timestamp_s: 1.0 },
  { frame_id: 2, timestamp_s: 1.2 },
] as FrameState[];

const options = [
  {
    sequence_id: "s",
    frame_id: 1,
    option_id: "s:1:pass:p8",
    kind: "pass",
    actor_id: "p1",
    target_player_id: "p8",
    target_x: 55,
    target_y: 30,
    features: {},
    geometric_score: 0.4,
    provenance: "synthetic",
  },
  {
    sequence_id: "s",
    frame_id: 2,
    option_id: "s:2:pass:p8",
    kind: "pass",
    actor_id: "p1",
    target_player_id: "p8",
    target_x: 56,
    target_y: 30,
    features: {},
    geometric_score: 0.8,
    provenance: "synthetic",
    label_selected: true,
  },
] as ActionOption[];

describe("ActionMenuRibbon", () => {
  it("keeps receiver identity stable across frames", () => {
    expect(stableActionKey(options[0]!)).toBe("pass:p8");
    expect(stableActionKey(options[1]!)).toBe("pass:p8");
  });

  it("renders the longitudinal option row", () => {
    render(
      <ActionMenuRibbon
        frames={frames}
        options={options}
        currentFrameId={1}
        selectedOptionId={null}
        onSeek={vi.fn()}
        onOptionSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("Pass · p8")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Pass · p8, frame 2, score 0.800" }),
    ).toBeVisible();
  });
});
