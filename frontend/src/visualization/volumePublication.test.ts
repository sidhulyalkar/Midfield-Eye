import { describe, expect, it } from "vitest";
import type { VolumeDifference, VolumeDifferenceCell } from "./volumeDifference";
import {
  assertCanonicalDifferencePublicationParams,
  assertPublicationDifferenceMatches,
  differencePublicationFigureId,
  interactiveComparisonParams,
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

const canonicalQuery =
  "scenario=aitana-overload&fi=10&cmp=earlier-run&lead=0.75&dc=future_space&dq=low&dt=0.200&tm=slice&layer=2&pub=figure";

describe("v1.3 publication helpers", () => {
  it("accepts only a fully specified canonical publication URL", () => {
    expect(() =>
      assertCanonicalDifferencePublicationParams(
        new URLSearchParams(canonicalQuery),
        18,
        7,
      ),
    ).not.toThrow();

    for (const invalid of [
      canonicalQuery.replace("dq=low", "dq=auto"),
      canonicalQuery.replace("cmp=earlier-run", "cmp=unknown"),
      canonicalQuery.replace("dt=0.200", "dt=0.213"),
      canonicalQuery.replace("tm=slice&layer=2", "tm=full&layer=2"),
      canonicalQuery.replace("fi=10", "fi=99"),
      `${canonicalQuery}&from=1`,
      `${canonicalQuery}&lead=1.00`,
    ]) {
      expect(() =>
        assertCanonicalDifferencePublicationParams(
          new URLSearchParams(invalid),
          18,
          7,
        ),
      ).toThrow();
    }
  });

  it("removes only publication mode when returning to the interactive workbench", () => {
    const interactive = interactiveComparisonParams(
      new URLSearchParams(canonicalQuery),
    );
    expect(interactive.has("pub")).toBe(false);
    expect(interactive.get("scenario")).toBe("aitana-overload");
    expect(interactive.get("layer")).toBe("2");
    expect(interactive.get("lead")).toBe("0.75");
  });

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
