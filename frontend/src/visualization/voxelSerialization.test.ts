import { describe, expect, it } from "vitest";
import type { VolumeVoxel } from "./affordanceVolume";
import {
  serializeVoxelInspection,
  serializedVoxelFilename,
} from "./voxelSerialization";

function voxel(id: string, layerIndex: number, value: number): VolumeVoxel {
  return {
    id,
    frameId: 12,
    channel: "menu",
    layerIndex,
    gridXIndex: 3,
    gridYIndex: 5,
    pitchX: 42,
    pitchY: 21,
    forecastSeconds: layerIndex * 0.25,
    worldX: 0,
    worldY: layerIndex,
    worldZ: 0,
    sizeX: 1,
    sizeY: 0.2,
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

describe("v1.2 citable voxel serialization", () => {
  it("exports the forensic record, filter, stable ids, and explicit trajectory gaps", () => {
    const selected = voxel("stable:1", 1, 0.8);
    const later = voxel("stable:3", 3, 0.5);
    const record = serializeVoxelInspection(
      selected,
      [selected, later],
      { mode: "slice", layerIndex: 1 },
      4,
      0.75,
    );

    expect(record.schemaVersion).toBe("1.2.0");
    expect(record.voxel).toBe(selected);
    expect(record.temporalFilter).toEqual({ mode: "slice", layerIndex: 1 });
    expect(record.trajectory.map((point) => point.value)).toEqual([
      null,
      0.8,
      null,
      0.5,
    ]);
    expect(record.trajectory[0]?.status).toBe("not_retained");
    expect(record.claimBoundary.missingLayerSemantics).toBe(
      "not_retained_not_zero",
    );
    expect(record.claimBoundary.futureObservedFramesUsed).toBe(false);
  });

  it("uses stable scientific coordinates in the export filename", () => {
    expect(serializedVoxelFilename(voxel("stable", 2, 0.9))).toBe(
      "midfielders-eye-frame-12-menu-layer-2.json",
    );
  });
});
