import { describe, expect, it } from "vitest";
import { INSTANCE_STRIDE, type VolumeVoxel } from "./affordanceVolume";
import type {
  VolumeDifference,
  VolumeDifferenceCell,
} from "./volumeDifference";
import { buildVolumeDifferenceRenderPayload } from "./volumeDifferenceRender";

function voxel(id: string, value: number, x = 12, z = -8): VolumeVoxel {
  return {
    id,
    frameId: 1,
    channel: "menu",
    layerIndex: 2,
    gridXIndex: 3,
    gridYIndex: 4,
    pitchX: 42,
    pitchY: 24,
    forecastSeconds: 0.5,
    worldX: x,
    worldY: 6.25,
    worldZ: z,
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
    conditionAId: "A",
    conditionBId: "B",
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

function readInstance(field: Float32Array, index: number) {
  const start = index * INSTANCE_STRIDE;
  return Array.from(field.slice(start, start + INSTANCE_STRIDE));
}

describe("v1.3 difference render payload", () => {
  it("uses one filled intersection cell and two orthogonal rails for each one-sided support state", () => {
    const aShared = voxel("a-shared", 0.25);
    const bShared = voxel("b-shared", 0.61);
    const aOnly = voxel("a-only", 0.7, -4, 5);
    const bOnly = voxel("b-only", 0.8, 18, 9);
    const intersection: VolumeDifferenceCell = {
      key: "2:3:4",
      layerIndex: 2,
      gridXIndex: 3,
      gridYIndex: 4,
      support: "intersection",
      left: aShared,
      right: bShared,
      delta: 0.36,
    };
    const leftOnly: VolumeDifferenceCell = {
      key: "2:4:4",
      layerIndex: 2,
      gridXIndex: 4,
      gridYIndex: 4,
      support: "left_only",
      left: aOnly,
      right: null,
      delta: null,
    };
    const rightOnly: VolumeDifferenceCell = {
      key: "2:5:4",
      layerIndex: 2,
      gridXIndex: 5,
      gridYIndex: 4,
      support: "right_only",
      left: null,
      right: bOnly,
      delta: null,
    };

    const payload = buildVolumeDifferenceRenderPayload(
      difference([intersection, leftOnly, rightOnly]),
    );

    expect(payload.stats).toEqual({
      comparisonCells: 3,
      intersectionCells: 1,
      leftOnlyCells: 1,
      rightOnlyCells: 1,
      fieldInstances: 5,
      maxAbsoluteDelta: 0.36,
    });
    expect(payload.field).toHaveLength(5 * INSTANCE_STRIDE);
    expect(payload.cells[0]).toMatchObject({
      glyph: "intersection_cell",
      instanceStart: 0,
      instanceCount: 1,
      signedDelta: 0.36,
      absoluteDelta: 0.36,
    });
    expect(payload.cells[0]?.comparison).toBe(intersection);
    expect(payload.cells[1]).toMatchObject({
      glyph: "left_parallel_rails",
      instanceStart: 1,
      instanceCount: 2,
      signedDelta: null,
      absoluteDelta: null,
    });
    expect(payload.cells[2]).toMatchObject({
      glyph: "right_parallel_rails",
      instanceStart: 3,
      instanceCount: 2,
      signedDelta: null,
      absoluteDelta: null,
    });

    const filled = readInstance(payload.field, 0);
    const leftRailA = readInstance(payload.field, 1);
    const leftRailB = readInstance(payload.field, 2);
    const rightRailA = readInstance(payload.field, 3);
    const rightRailB = readInstance(payload.field, 4);

    expect(filled[1]).toBeCloseTo(aShared.worldY);
    expect(leftRailA[1]).toBeCloseTo(aOnly.worldY);
    expect(leftRailB[1]).toBeCloseTo(aOnly.worldY);
    expect(rightRailA[1]).toBeCloseTo(bOnly.worldY);
    expect(rightRailB[1]).toBeCloseTo(bOnly.worldY);

    expect(leftRailA[0]).not.toBeCloseTo(leftRailB[0] ?? 0);
    expect(leftRailA[2]).toBeCloseTo(leftRailB[2] ?? 0);
    expect((leftRailA[3] ?? 0) < (leftRailA[5] ?? 0)).toBe(true);

    expect(rightRailA[0]).toBeCloseTo(rightRailB[0] ?? 0);
    expect(rightRailA[2]).not.toBeCloseTo(rightRailB[2] ?? 0);
    expect((rightRailA[3] ?? 0) > (rightRailA[5] ?? 0)).toBe(true);
  });

  it("keeps zero-delta intersections visible without inventing magnitude", () => {
    const left = voxel("a", 0.4);
    const right = voxel("b", 0.4);
    const cell: VolumeDifferenceCell = {
      key: "2:3:4",
      layerIndex: 2,
      gridXIndex: 3,
      gridYIndex: 4,
      support: "intersection",
      left,
      right,
      delta: 0,
    };
    const payload = buildVolumeDifferenceRenderPayload(difference([cell]));
    expect(payload.cells[0]?.signedDelta).toBe(0);
    expect(payload.cells[0]?.absoluteDelta).toBe(0);
    expect(payload.stats.maxAbsoluteDelta).toBe(0);
    expect(readInstance(payload.field, 0)[9]).toBeCloseTo(0.24);
  });

  it("fails closed when support metadata would imply a fake numerical difference", () => {
    const left = voxel("a", 0.5);
    const malformed: VolumeDifferenceCell = {
      key: "2:3:4",
      layerIndex: 2,
      gridXIndex: 3,
      gridYIndex: 4,
      support: "left_only",
      left,
      right: null,
      delta: 0,
    };
    expect(() =>
      buildVolumeDifferenceRenderPayload(difference([malformed])),
    ).toThrow(/delta=null/u);
  });
});
