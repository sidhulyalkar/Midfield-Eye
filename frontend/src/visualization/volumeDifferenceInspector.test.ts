import { describe, expect, it } from "vitest";
import type { VolumeVoxel } from "./affordanceVolume";
import type {
  VolumeDifference,
  VolumeDifferenceCell,
} from "./volumeDifference";
import {
  inspectVolumeDifferenceCell,
  mostInformativeDifferenceCell,
} from "./volumeDifferenceInspector";

function voxel(id: string, value: number): VolumeVoxel {
  return {
    id,
    frameId: 1,
    channel: "menu",
    layerIndex: 1,
    gridXIndex: 0,
    gridYIndex: 0,
    pitchX: 20,
    pitchY: 10,
    forecastSeconds: 0.25,
    worldX: -20,
    worldY: 3.5,
    worldZ: -10,
    sizeX: 4,
    sizeY: 0.4,
    sizeZ: 3,
    value,
    signals: {
      menu: value,
      pressure: 0.1,
      pressure_shadow: 0.2,
      future_space: 0.3,
      passing_corridors: 0.4,
      option_creation: 0.5,
      visibility: 0.6,
      uncertainty: 0.1,
    },
    optionContributions: [],
    nearestDefender: null,
    nearestTeammate: null,
    evidence: {
      forecast: "focal_state_kinematics",
      sourceProvider: "test",
      visibility: "unknown",
      uncertainty: "tracking_status_only",
      futureObservedFramesUsed: false,
    },
  };
}

function difference(cells: VolumeDifferenceCell[]): VolumeDifference {
  return {
    conditionAId: "baseline",
    conditionBId: "counterfactual",
    channel: "menu",
    signConvention: "condition_b_minus_condition_a",
    cells,
    summary: {
      intersection: cells.filter((cell) => cell.support === "intersection")
        .length,
      leftOnly: cells.filter((cell) => cell.support === "left_only").length,
      rightOnly: cells.filter((cell) => cell.support === "right_only").length,
      neither: 0,
      retainedUnion: cells.length,
      totalCanonicalCells: cells.length,
    },
  };
}

describe("v1.3 difference forensic inspection", () => {
  it("exposes both original records and a numerical delta only for intersections", () => {
    const left = voxel("a", 0.3);
    const right = voxel("b", 0.72);
    const cell: VolumeDifferenceCell = {
      key: "1:0:0",
      layerIndex: 1,
      gridXIndex: 0,
      gridYIndex: 0,
      support: "intersection",
      left,
      right,
      delta: 0.42,
    };
    const record = inspectVolumeDifferenceCell(difference([cell]), cell.key);

    expect(record).not.toBeNull();
    expect(record?.numericComparisonAvailable).toBe(true);
    expect(record?.delta).toBeCloseTo(0.42);
    expect(record?.absoluteDelta).toBeCloseTo(0.42);
    expect(record?.conditionA.voxel).toBe(left);
    expect(record?.conditionB.voxel).toBe(right);
    expect(record?.conditionA.value).toBe(0.3);
    expect(record?.conditionB.value).toBe(0.72);
    expect(record?.signConvention).toBe("condition_b_minus_condition_a");
  });

  it("keeps one-sided support categorical with an explicit absent side", () => {
    const left = voxel("a-only", 0.66);
    const cell: VolumeDifferenceCell = {
      key: "1:0:0",
      layerIndex: 1,
      gridXIndex: 0,
      gridYIndex: 0,
      support: "left_only",
      left,
      right: null,
      delta: null,
    };
    const record = inspectVolumeDifferenceCell(difference([cell]), cell.key);

    expect(record?.numericComparisonAvailable).toBe(false);
    expect(record?.delta).toBeNull();
    expect(record?.absoluteDelta).toBeNull();
    expect(record?.conditionA).toMatchObject({
      retained: true,
      voxelId: "a-only",
      value: 0.66,
    });
    expect(record?.conditionB).toMatchObject({
      retained: false,
      voxelId: null,
      value: null,
      voxel: null,
    });
    expect(record?.claimBoundary).toEqual({
      oneSidedPresenceIsNumericalZero: false,
      missingSupportInterpolated: false,
      calibratedProbability: false,
      futureObservedFramesUsed: false,
    });
  });

  it("selects the largest absolute intersection delta, then stable key for ties", () => {
    const a = voxel("a", 0.4);
    const b = voxel("b", 0.8);
    const first: VolumeDifferenceCell = {
      key: "0:0:0",
      layerIndex: 0,
      gridXIndex: 0,
      gridYIndex: 0,
      support: "intersection",
      left: a,
      right: b,
      delta: 0.4,
    };
    const second: VolumeDifferenceCell = {
      ...first,
      key: "1:0:0",
      layerIndex: 1,
      delta: -0.4,
    };
    const categorical: VolumeDifferenceCell = {
      key: "0:1:0",
      layerIndex: 0,
      gridXIndex: 1,
      gridYIndex: 0,
      support: "right_only",
      left: null,
      right: b,
      delta: null,
    };

    expect(
      mostInformativeDifferenceCell(
        difference([categorical, second, first]),
      )?.key,
    ).toBe("0:0:0");
  });

  it("falls back deterministically to the smallest categorical key when no numerical delta exists", () => {
    const a = voxel("a", 0.5);
    const b = voxel("b", 0.6);
    const later: VolumeDifferenceCell = {
      key: "2:1:1",
      layerIndex: 2,
      gridXIndex: 1,
      gridYIndex: 1,
      support: "left_only",
      left: a,
      right: null,
      delta: null,
    };
    const earlier: VolumeDifferenceCell = {
      key: "0:1:1",
      layerIndex: 0,
      gridXIndex: 1,
      gridYIndex: 1,
      support: "right_only",
      left: null,
      right: b,
      delta: null,
    };

    expect(mostInformativeDifferenceCell(difference([later, earlier]))?.key).toBe(
      "0:1:1",
    );
    expect(inspectVolumeDifferenceCell(difference([later]), "missing")).toBeNull();
  });

  it("fails closed when a categorical cell contains a fake numerical delta", () => {
    const left = voxel("a", 0.5);
    const malformed: VolumeDifferenceCell = {
      key: "1:0:0",
      layerIndex: 1,
      gridXIndex: 0,
      gridYIndex: 0,
      support: "left_only",
      left,
      right: null,
      delta: 0,
    };
    expect(() =>
      inspectVolumeDifferenceCell(difference([malformed]), malformed.key),
    ).toThrow(/invalid forensic state/u);
  });
});
