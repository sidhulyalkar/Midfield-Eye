import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { FrameState } from "../data/schemas";
import type { VolumeDifference, VolumeDifferenceCell } from "./volumeDifference";
import { DifferencePublicationPlate } from "./DifferencePublicationPlate";
import type { VolumeVoxel } from "./affordanceVolume";
import type { EarlierRunIntervention } from "./volumeIntervention";

function voxel(id: string, value: number, x: number, y: number): VolumeVoxel {
  return {
    id,
    frameId: 10,
    channel: "future_space",
    layerIndex: 2,
    gridXIndex: Math.round(x),
    gridYIndex: Math.round(y),
    pitchX: x,
    pitchY: y,
    forecastSeconds: 0.5,
    worldX: x - 52.5,
    worldY: 6,
    worldZ: y - 34,
    sizeX: 4,
    sizeY: 0.4,
    sizeZ: 4,
    value,
    signals: {
      menu: value,
      pressure: 0.1,
      pressure_shadow: 0.2,
      future_space: value,
      passing_corridors: 0,
      option_creation: 0.2,
      visibility: 0.6,
      uncertainty: 0.1,
    },
    optionContributions: [],
    nearestDefender: null,
    nearestTeammate: null,
    evidence: {
      forecast: "focal_state_kinematics",
      sourceProvider: "synthetic",
      visibility: "unknown",
      uncertainty: "tracking_status_only",
      futureObservedFramesUsed: false,
    },
  };
}

const leftShared = voxel("a-shared", 0.3, 30, 20);
const rightSharedPositive = voxel("b-positive", 0.6, 30, 20);
const leftSharedNegative = voxel("a-negative", 0.7, 42, 20);
const rightSharedNegative = voxel("b-negative", 0.4, 42, 20);
const leftOnlyVoxel = voxel("a-only", 0.55, 50, 30);
const rightOnlyVoxel = voxel("b-only", 0.62, 58, 35);

const cells: VolumeDifferenceCell[] = [
  {
    key: "2:1:1",
    layerIndex: 2,
    gridXIndex: 1,
    gridYIndex: 1,
    support: "intersection",
    left: leftShared,
    right: rightSharedPositive,
    delta: 0.3,
  },
  {
    key: "2:2:1",
    layerIndex: 2,
    gridXIndex: 2,
    gridYIndex: 1,
    support: "intersection",
    left: leftSharedNegative,
    right: rightSharedNegative,
    delta: -0.3,
  },
  {
    key: "2:3:2",
    layerIndex: 2,
    gridXIndex: 3,
    gridYIndex: 2,
    support: "left_only",
    left: leftOnlyVoxel,
    right: null,
    delta: null,
  },
  {
    key: "2:4:2",
    layerIndex: 2,
    gridXIndex: 4,
    gridYIndex: 2,
    support: "right_only",
    left: null,
    right: rightOnlyVoxel,
    delta: null,
  },
];

const difference: VolumeDifference = {
  conditionAId: "baseline",
  conditionBId: "earlier-run:runner:0.75",
  channel: "future_space",
  signConvention: "condition_b_minus_condition_a",
  cells,
  summary: {
    intersection: 2,
    leftOnly: 1,
    rightOnly: 1,
    neither: 0,
    retainedUnion: 4,
    totalCanonicalCells: 4,
  },
};

const baselineFrame = {
  metadata: { evidence_status: "illustrative_synthetic_reconstruction" },
} as unknown as FrameState;

const intervention = {
  id: "earlier-run:runner:0.75",
  playerId: "runner",
  leadSeconds: 0.75,
  speedMps: 2,
  displacementM: 1.5,
  from: [40, 30],
  to: [41.5, 30],
  baselineFrame,
  alternativeFrame: baselineFrame,
} as EarlierRunIntervention;

describe("difference publication plate", () => {
  it("renders structural sign/support semantics and explicit claim boundaries", () => {
    const { container } = render(
      <DifferencePublicationPlate
        scenarioId="aitana-overload"
        scenarioTitle="Overload, escape, arrive"
        frameId={10}
        frameIndex={10}
        timestampSeconds={1.67}
        sourceEvidenceStatus="illustrative_synthetic_reconstruction"
        channel="future_space"
        quality="low"
        threshold={0.2}
        layerIndex={2}
        forecastSeconds={0.5}
        pitchLength={105}
        pitchWidth={68}
        intervention={intervention}
        difference={difference}
        cells={cells}
      />,
    );

    const plate = screen.getByTestId("difference-publication-plate");
    expect(plate).toHaveAttribute(
      "data-figure-id",
      "ME-DIFF-aitana-overload-f10-future-space-l2-lead075-qlow-t0200",
    );
    expect(container.querySelectorAll(".publication-intersection.is-positive")).toHaveLength(1);
    expect(container.querySelectorAll(".publication-intersection.is-negative")).toHaveLength(1);
    expect(container.querySelectorAll(".publication-left-only rect")).toHaveLength(2);
    expect(container.querySelectorAll(".publication-right-only rect")).toHaveLength(2);
    expect(screen.getByText("+")).toBeInTheDocument();
    expect(screen.getByText("−")).toBeInTheDocument();
    expect(screen.getAllByText(/no numerical delta/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("not_retained ≠ 0")).toBeInTheDocument();
    expect(screen.getByText("Candidate options included: false.")).toBeInTheDocument();
    expect(screen.getByText("Candidate options regenerated: false.")).toBeInTheDocument();
    expect(screen.getByText("Future observed frames used: false.")).toBeInTheDocument();
  });
});
