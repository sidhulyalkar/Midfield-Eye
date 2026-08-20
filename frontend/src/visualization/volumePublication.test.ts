import { describe, expect, it } from "vitest";
import type { VolumeDifference, VolumeDifferenceCell } from "./volumeDifference";
import {
  assertPublicationDifferenceMatches,
  differencePublicationFigureId,
  requirePublicationSlice,
  selectDifferenceFailureGallery,
  summarizeDifferencePublication,
} from "./volumePublication";

function cell(
  key: string,
  layerIndex: number,
  gridXIndex: number,
  gridYIndex: number,
  support: VolumeDifferenceCell["support"],
  delta: number | null,
): VolumeDifferenceCell {
  return {
    key,
    layerIndex,
    gridXIndex,
    gridYIndex,
    support,
    left: null,
    right: null,
    delta,
  };
}

function sourceDifference(cells: VolumeDifferenceCell[]): VolumeDifference {
  return {
    conditionAId: "baseline",
    conditionBId: "earlier-run:p:0.75",
    channel: "future_space",
    signConvention: "condition_b_minus_condition_a",
    cells,
    summary: {
      intersection: cells.filter((item) => item.support === "intersection").length,
      leftOnly: cells.filter((item) => item.support === "left_only").length,
      rightOnly: cells.filter((item) => item.support === "right_only").length,
      neither: 0,
      retainedUnion: cells.length,
      totalCanonicalCells: cells.length,
    },
  };
}

describe("v1.3 publication helpers", () => {
  it("builds a stable readable figure id from scientific state only", () => {
    expect(
      differencePublicationFigureId({
        scenarioId: "Aitana Overload",
        frameIndex: 10,
        channel: "future_space",
        layerIndex: 2,
        leadSeconds: 0.75,
        quality: "low",
        threshold: 0.2,
      }),
    ).toBe("ME-DIFF-aitana-overload-f10-future-space-l2-lead075-qlow-t0200");
  });

  it("requires exact Slice mode for publication figure choreography", () => {
    expect(requirePublicationSlice({ mode: "slice", layerIndex: 3 })).toBe(3);
    expect(() => requirePublicationSlice({ mode: "full" })).toThrow(/exact integer temporal slice/u);
    expect(() =>
      requirePublicationSlice({ mode: "band", startLayerIndex: 1, endLayerIndex: 2 }),
    ).toThrow(/exact integer temporal slice/u);
  });

  it("chooses one-sided failure examples by integer identity, never magnitude", () => {
    const laterA = cell("2:0:0", 2, 0, 0, "left_only", null);
    const earlyA = cell("0:4:4", 0, 4, 4, "left_only", null);
    const laterB = cell("3:0:0", 3, 0, 0, "right_only", null);
    const earlyB = cell("1:9:9", 1, 9, 9, "right_only", null);
    const gallery = selectDifferenceFailureGallery([
      laterA,
      laterB,
      earlyB,
      earlyA,
    ]);
    expect(gallery.leftOnly).toBe(earlyA);
    expect(gallery.rightOnly).toBe(earlyB);
  });

  it("summarizes numerical deltas only over retained intersections", () => {
    const cells = [
      cell("0:0:0", 0, 0, 0, "intersection", 0.3),
      cell("0:0:1", 0, 0, 1, "intersection", -0.1),
      cell("0:1:0", 0, 1, 0, "left_only", null),
      cell("0:1:1", 0, 1, 1, "right_only", null),
    ];
    expect(summarizeDifferencePublication(cells)).toEqual({
      visibleCells: 4,
      sharedSupport: 2,
      leftOnly: 1,
      rightOnly: 1,
      supportOverlap: 0.5,
      meanSignedDelta: 0.1,
      meanAbsoluteDelta: 0.2,
      maxAbsoluteDelta: 0.3,
    });
  });

  it("refuses copied or publication-only comparison records", () => {
    const retained = cell("0:0:0", 0, 0, 0, "intersection", 0.2);
    const source = sourceDifference([retained]);
    expect(() => assertPublicationDifferenceMatches(source, [retained])).not.toThrow();
    expect(() =>
      assertPublicationDifferenceMatches(source, [{ ...retained }]),
    ).toThrow(/not an exact record/u);
  });
});
