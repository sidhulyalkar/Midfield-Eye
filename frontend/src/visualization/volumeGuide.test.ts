import { describe, expect, it } from "vitest";
import {
  INSTANCE_STRIDE,
  type VolumeScene,
  type VolumeVoxel,
} from "./affordanceVolume";
import {
  addTemporalGuideRails,
  filterVolumeScene,
  temporalLayerWorldY,
} from "./volumeTemporal";

const voxel: VolumeVoxel = {
  id: "cell",
  frameId: 1,
  channel: "menu",
  layerIndex: 2,
  gridXIndex: 3,
  gridYIndex: 4,
  pitchX: 50,
  pitchY: 30,
  forecastSeconds: 0.5,
  worldX: 0,
  worldY: 6,
  worldZ: 0,
  sizeX: 1,
  sizeY: 0.2,
  sizeZ: 1,
  value: 0.8,
  signals: {
    menu: 0.8,
    pressure: 0,
    pressure_shadow: 0,
    future_space: 0.8,
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

const scene: VolumeScene = {
  field: new Float32Array([0, 6, 0, 1, 0.2, 1, 1, 0.8, 0.4, 0.6]),
  solids: new Float32Array(INSTANCE_STRIDE),
  voxels: [voxel],
  timeScaleMetres: 16,
  stats: {
    channel: "menu",
    gridX: 20,
    gridY: 13,
    horizonSteps: 7,
    candidateVoxels: 1,
    renderedVoxels: 1,
    maxVoxels: 100,
    meanValue: 0.8,
    maxValue: 0.8,
  },
};

describe("v1.2 cutting-plane guide", () => {
  it("maps integer temporal layers to deterministic render-space height", () => {
    expect(temporalLayerWorldY(0, scene)).toBeCloseTo(0.7);
    expect(temporalLayerWorldY(3, scene)).toBeCloseTo(8.7);
    expect(temporalLayerWorldY(6, scene)).toBeCloseTo(16.7);
  });

  it("adds four solid rails for a slice without touching field or voxel identity", () => {
    const filtered = filterVolumeScene(scene, { mode: "slice", layerIndex: 2 });
    const guided = addTemporalGuideRails(
      filtered,
      { mode: "slice", layerIndex: 2 },
      105,
      68,
    );

    expect(guided.field).toBe(filtered.field);
    expect(guided.voxels).toBe(filtered.voxels);
    expect(guided.solids.length).toBe(
      filtered.solids.length + 4 * INSTANCE_STRIDE,
    );
  });

  it("adds two rail rectangles for a temporal band", () => {
    const guided = addTemporalGuideRails(
      scene,
      { mode: "band", startLayerIndex: 1, endLayerIndex: 4 },
      105,
      68,
    );
    expect(guided.solids.length).toBe(
      scene.solids.length + 8 * INSTANCE_STRIDE,
    );
  });
});
