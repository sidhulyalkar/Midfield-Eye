import { describe, expect, it } from "vitest";
import type { VolumeVoxel } from "./affordanceVolume";
import {
  pickVolumeVoxel,
  projectVoxelToScreen,
  strongestVisibleVoxel,
} from "./voxelInspector";

const camera = {
  azimuth: -0.72,
  elevation: 0.58,
  distance: 118,
  targetY: 5.5,
};

function voxel(id: string, value: number): VolumeVoxel {
  return {
    id,
    frameId: 1,
    channel: "menu",
    layerIndex: 2,
    gridXIndex: 4,
    gridYIndex: 5,
    pitchX: 52,
    pitchY: 34,
    forecastSeconds: 0.5,
    worldX: 0,
    worldY: 6,
    worldZ: 0,
    sizeX: 2,
    sizeY: 0.2,
    sizeZ: 2,
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

describe("v1.2 deterministic voxel priority", () => {
  it("chooses highest value, then lexicographically smallest stable voxel id", () => {
    const sameValueZ = voxel("z-cell", 0.8);
    const sameValueA = voxel("a-cell", 0.8);
    const weaker = voxel("00-weaker", 0.7);

    const strongest = strongestVisibleVoxel(
      [sameValueZ, weaker, sameValueA],
      camera,
      1200,
      700,
    );
    expect(strongest?.voxel.id).toBe("a-cell");
  });

  it("uses the same id tie-break when overlapping cells are clicked", () => {
    const z = voxel("z-cell", 0.8);
    const a = voxel("a-cell", 0.8);
    const projected = projectVoxelToScreen(a, camera, 1200, 700);
    expect(projected).not.toBeNull();
    if (!projected) return;

    const picked = pickVolumeVoxel(
      [z, a],
      camera,
      1200,
      700,
      projected.screenX,
      projected.screenY,
    );
    expect(picked?.voxel.id).toBe("a-cell");
  });
});
