import { describe, expect, it } from "vitest";
import {
  INSTANCE_STRIDE,
  type VolumeScene,
  type VolumeVoxel,
} from "./affordanceVolume";
import {
  buildRetainedVoxelTrajectory,
  filterRetainedVoxels,
  filterVolumeScene,
  horizonSecondsForLayer,
  temporalFilterLabel,
  temporalLayerSet,
  volumeSpatialCellKey,
} from "./volumeTemporal";

function voxel(
  id: string,
  layerIndex: number,
  gridXIndex: number,
  gridYIndex: number,
  value: number,
): VolumeVoxel {
  return {
    id,
    frameId: 7,
    channel: "menu",
    layerIndex,
    gridXIndex,
    gridYIndex,
    pitchX: 10 + gridXIndex,
    pitchY: 20 + gridYIndex,
    forecastSeconds: layerIndex * 0.25,
    worldX: gridXIndex,
    worldY: layerIndex,
    worldZ: gridYIndex,
    sizeX: 1,
    sizeY: 1,
    sizeZ: 1,
    value,
    signals: {
      menu: value,
      pressure: 0,
      pressure_shadow: 0,
      future_space: value,
      passing_corridors: 0,
      option_creation: 0,
      visibility: 1,
      uncertainty: 0,
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

function scene(): VolumeScene {
  const voxels = [
    voxel("v0", 0, 1, 1, 0.9),
    voxel("v1", 1, 1, 1, 0.8),
    voxel("v2", 2, 2, 1, 0.7),
    voxel("v3", 3, 1, 1, 0.6),
  ];
  const field = new Float32Array(voxels.length * INSTANCE_STRIDE);
  voxels.forEach((item, index) => {
    field.set(
      [
        index + 0.1,
        index + 0.2,
        index + 0.3,
        1,
        1,
        1,
        0.9,
        0.8,
        0.7,
        item.value,
      ],
      index * INSTANCE_STRIDE,
    );
  });
  return {
    field,
    solids: new Float32Array(),
    voxels,
    timeScaleMetres: 16,
    stats: {
      channel: "menu",
      gridX: 4,
      gridY: 3,
      horizonSteps: 4,
      candidateVoxels: 4,
      renderedVoxels: 4,
      maxVoxels: 20,
      meanValue: 0.75,
      maxValue: 0.9,
    },
  };
}

describe("v1.2 temporal filter", () => {
  it("uses integer temporal layer membership with no float equality", () => {
    expect([...temporalLayerSet({ mode: "slice", layerIndex: 2 }, 4)]).toEqual([
      2,
    ]);
    expect([
      ...temporalLayerSet(
        { mode: "band", startLayerIndex: 1, endLayerIndex: 3 },
        4,
      ),
    ]).toEqual([1, 2, 3]);
    expect(() =>
      temporalLayerSet({ mode: "slice", layerIndex: 0.5 }, 4),
    ).toThrow(/integer layer index/u);
  });

  it("filters the retained voxel objects directly and never recomputes them", () => {
    const full = scene();
    const visible = filterRetainedVoxels(
      full.voxels,
      { mode: "slice", layerIndex: 1 },
      full.stats.horizonSteps,
    );

    expect(visible).toHaveLength(1);
    expect(visible[0]).toBe(full.voxels[1]);
    expect(visible[0]?.value).toBe(0.8);
  });

  it("copies the exact GPU instance records for a slice", () => {
    const full = scene();
    const filtered = filterVolumeScene(full, { mode: "slice", layerIndex: 2 });

    expect(filtered.voxels).toHaveLength(1);
    expect(filtered.voxels[0]).toBe(full.voxels[2]);
    expect(Array.from(filtered.field)).toEqual(
      Array.from(full.field.slice(2 * INSTANCE_STRIDE, 3 * INSTANCE_STRIDE)),
    );
    expect(filtered.stats.renderedVoxels).toBe(1);
    expect(filtered.stats.candidateVoxels).toBe(full.stats.candidateVoxels);
  });

  it("returns the original scientific scene unchanged in full mode", () => {
    const full = scene();
    expect(filterVolumeScene(full, { mode: "full" })).toBe(full);
  });

  it("uses inclusive band bounds and never zero-fills clipped layers", () => {
    const full = scene();
    const filtered = filterVolumeScene(full, {
      mode: "band",
      startLayerIndex: 1,
      endLayerIndex: 2,
    });

    expect(filtered.voxels.map((item) => item.id)).toEqual(["v1", "v2"]);
    expect(filtered.field.length).toBe(2 * INSTANCE_STRIDE);
  });
});

describe("same-cell temporal trajectory", () => {
  it("uses grid identity across layers and exposes pruned layers as explicit gaps", () => {
    const full = scene();
    const inspected = full.voxels[1]!;
    const trajectory = buildRetainedVoxelTrajectory(
      full.voxels,
      inspected,
      4,
      0.75,
    );

    expect(volumeSpatialCellKey(full.voxels[0]!)).toBe(
      volumeSpatialCellKey(inspected),
    );
    expect(trajectory.map((point) => point.status)).toEqual([
      "retained",
      "retained",
      "not_retained",
      "retained",
    ]);
    expect(trajectory.map((point) => point.value)).toEqual([
      0.9,
      0.8,
      null,
      0.6,
    ]);
    expect(trajectory[2]?.voxelId).toBeNull();
  });

  it("derives horizon labels from integer indices only", () => {
    expect(horizonSecondsForLayer(0, 7, 1.5)).toBe(0);
    expect(horizonSecondsForLayer(1, 7, 1.5)).toBeCloseTo(0.25);
    expect(horizonSecondsForLayer(6, 7, 1.5)).toBeCloseTo(1.5);
    expect(temporalFilterLabel({ mode: "slice", layerIndex: 2 }, 7, 1.5)).toBe(
      "Slice · +0.50 s",
    );
  });
});
