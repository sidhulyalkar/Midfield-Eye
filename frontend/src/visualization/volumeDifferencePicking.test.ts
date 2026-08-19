import { describe, expect, it } from "vitest";
import type { VolumeDifferenceCell } from "./volumeDifference";
import type { VolumeDifferenceRenderCell } from "./volumeDifferenceRender";
import {
  pickDifferenceCell,
  projectDifferenceCellToScreen,
} from "./volumeDifferencePicking";
import type { OrbitCamera } from "./voxelRenderer";

const camera: OrbitCamera = {
  azimuth: -0.72,
  elevation: 0.58,
  distance: 118,
  targetY: 5.5,
};

function renderCell(
  key: string,
  layerIndex: number,
  gridXIndex: number,
  gridYIndex: number,
  worldX = 0,
  worldY = 5,
  worldZ = 0,
): VolumeDifferenceRenderCell {
  const comparison: VolumeDifferenceCell = {
    key,
    layerIndex,
    gridXIndex,
    gridYIndex,
    support: "left_only",
    left: null as never,
    right: null,
    delta: null,
  };
  return {
    key,
    support: "left_only",
    glyph: "left_parallel_rails",
    comparison,
    worldX,
    worldY,
    worldZ,
    sizeX: 4,
    sizeY: 0.3,
    sizeZ: 3,
    signedDelta: null,
    absoluteDelta: null,
    instanceStart: 0,
    instanceCount: 2,
  };
}

describe("difference CPU picking", () => {
  it("round-trips a projected comparison cell to the same stable key", () => {
    const cell = renderCell("2:3:4", 2, 3, 4);
    const projected = projectDifferenceCellToScreen(
      cell,
      camera,
      1280,
      720,
    );
    expect(projected).not.toBeNull();
    const picked = pickDifferenceCell(
      [cell],
      camera,
      1280,
      720,
      projected?.screenX ?? 0,
      projected?.screenY ?? 0,
    );
    expect(picked?.cell).toBe(cell);
  });

  it("breaks exact projection ties by integer layer/X/Y identity", () => {
    const later = renderCell("10:0:0", 10, 0, 0);
    const earlier = renderCell("2:0:0", 2, 0, 0);
    const projected = projectDifferenceCellToScreen(
      earlier,
      camera,
      1280,
      720,
    );
    expect(projected).not.toBeNull();
    const picked = pickDifferenceCell(
      [later, earlier],
      camera,
      1280,
      720,
      projected?.screenX ?? 0,
      projected?.screenY ?? 0,
    );
    expect(picked?.cell).toBe(earlier);
  });
});
