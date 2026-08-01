import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceBadge, MissingSignal } from "./Evidence";

describe("evidence language", () => {
  it("keeps synthetic evidence explicit and inspectable", () => {
    render(<EvidenceBadge kind="synthetic" source="Teaching scenario" />);
    expect(screen.getByText("Illustrative synthetic")).toBeVisible();
    expect(screen.getByTitle("Teaching scenario")).toBeVisible();
  });

  it("renders unavailable as a reason rather than a numeric zero", () => {
    render(
      <MissingSignal
        signal="Literal gaze"
        reason="No calibrated eye-gaze source."
        path="Add a consented sensor."
      />,
    );
    expect(screen.getByText("Unavailable")).toBeVisible();
    expect(screen.getByText("No calibrated eye-gaze source.")).toBeVisible();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
