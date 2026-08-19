import type { VolumeDifferenceRenderCell } from "./volumeDifferenceRender";
import { orbitViewProjection, type OrbitCamera } from "./voxelRenderer";

export type ProjectedDifferenceCell = {
  cell: VolumeDifferenceRenderCell;
  screenX: number;
  screenY: number;
  ndcZ: number;
  radiusPx: number;
};

function projectPoint(
  matrix: Float32Array,
  x: number,
  y: number,
  z: number,
): [number, number, number, number] {
  return [
    (matrix[0] ?? 0) * x +
      (matrix[4] ?? 0) * y +
      (matrix[8] ?? 0) * z +
      (matrix[12] ?? 0),
    (matrix[1] ?? 0) * x +
      (matrix[5] ?? 0) * y +
      (matrix[9] ?? 0) * z +
      (matrix[13] ?? 0),
    (matrix[2] ?? 0) * x +
      (matrix[6] ?? 0) * y +
      (matrix[10] ?? 0) * z +
      (matrix[14] ?? 0),
    (matrix[3] ?? 0) * x +
      (matrix[7] ?? 0) * y +
      (matrix[11] ?? 0) * z +
      (matrix[15] ?? 0),
  ];
}

function compareIdentity(
  left: VolumeDifferenceRenderCell,
  right: VolumeDifferenceRenderCell,
) {
  return (
    left.comparison.layerIndex - right.comparison.layerIndex ||
    left.comparison.gridXIndex - right.comparison.gridXIndex ||
    left.comparison.gridYIndex - right.comparison.gridYIndex
  );
}

export function projectDifferenceCellToScreen(
  cell: VolumeDifferenceRenderCell,
  camera: OrbitCamera,
  width: number,
  height: number,
): ProjectedDifferenceCell | null {
  if (width <= 0 || height <= 0) return null;
  const matrix = orbitViewProjection(camera, width / height);
  const [clipX, clipY, clipZ, clipW] = projectPoint(
    matrix,
    cell.worldX,
    cell.worldY,
    cell.worldZ,
  );
  if (!Number.isFinite(clipW) || clipW <= 1e-6) return null;
  const ndcX = clipX / clipW;
  const ndcY = clipY / clipW;
  const ndcZ = clipZ / clipW;
  if (ndcZ < -1.2 || ndcZ > 1.2) return null;
  const screenX = ((ndcX + 1) / 2) * width;
  const screenY = ((1 - ndcY) / 2) * height;
  const radiusPx = Math.max(
    8,
    Math.min(24, ((cell.sizeX + cell.sizeZ) * 0.5 * height) / (clipW * 1.8)),
  );
  return { cell, screenX, screenY, ndcZ, radiusPx };
}

export function pickDifferenceCell(
  cells: readonly VolumeDifferenceRenderCell[],
  camera: OrbitCamera,
  width: number,
  height: number,
  pointerX: number,
  pointerY: number,
): ProjectedDifferenceCell | null {
  let best: ProjectedDifferenceCell | null = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const cell of cells) {
    const projected = projectDifferenceCellToScreen(
      cell,
      camera,
      width,
      height,
    );
    if (!projected) continue;
    const distance = Math.hypot(
      projected.screenX - pointerX,
      projected.screenY - pointerY,
    );
    if (distance > projected.radiusPx) continue;
    if (
      !best ||
      distance < bestDistance - 1e-9 ||
      (Math.abs(distance - bestDistance) <= 1e-9 &&
        (projected.ndcZ < best.ndcZ - 1e-9 ||
          (Math.abs(projected.ndcZ - best.ndcZ) <= 1e-9 &&
            compareIdentity(projected.cell, best.cell) < 0)))
    ) {
      best = projected;
      bestDistance = distance;
    }
  }
  return best;
}
