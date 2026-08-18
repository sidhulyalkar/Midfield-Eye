import type { VolumeVoxel } from "./affordanceVolume";
import { orbitViewProjection, type OrbitCamera } from "./voxelRenderer";

export type ProjectedVoxel = {
  voxel: VolumeVoxel;
  screenX: number;
  screenY: number;
  ndcDepth: number;
  radiusPx: number;
};

export type VoxelPick = ProjectedVoxel & {
  distancePx: number;
};

type ProjectedPoint = {
  screenX: number;
  screenY: number;
  ndcDepth: number;
};

function projectPoint(
  matrix: Float32Array,
  worldX: number,
  worldY: number,
  worldZ: number,
  width: number,
  height: number,
): ProjectedPoint | null {
  const clipX =
    (matrix[0] ?? 0) * worldX +
    (matrix[4] ?? 0) * worldY +
    (matrix[8] ?? 0) * worldZ +
    (matrix[12] ?? 0);
  const clipY =
    (matrix[1] ?? 0) * worldX +
    (matrix[5] ?? 0) * worldY +
    (matrix[9] ?? 0) * worldZ +
    (matrix[13] ?? 0);
  const clipZ =
    (matrix[2] ?? 0) * worldX +
    (matrix[6] ?? 0) * worldY +
    (matrix[10] ?? 0) * worldZ +
    (matrix[14] ?? 0);
  const clipW =
    (matrix[3] ?? 0) * worldX +
    (matrix[7] ?? 0) * worldY +
    (matrix[11] ?? 0) * worldZ +
    (matrix[15] ?? 0);

  if (!Number.isFinite(clipW) || clipW <= 1e-6) return null;
  const ndcX = clipX / clipW;
  const ndcY = clipY / clipW;
  const ndcDepth = clipZ / clipW;
  if (!Number.isFinite(ndcX) || !Number.isFinite(ndcY)) return null;
  return {
    screenX: (ndcX * 0.5 + 0.5) * width,
    screenY: (1 - (ndcY * 0.5 + 0.5)) * height,
    ndcDepth,
  };
}

export function projectVoxelToScreen(
  voxel: VolumeVoxel,
  camera: OrbitCamera,
  width: number,
  height: number,
): ProjectedVoxel | null {
  if (width <= 0 || height <= 0) return null;
  const matrix = orbitViewProjection(camera, width / height);
  const center = projectPoint(
    matrix,
    voxel.worldX,
    voxel.worldY,
    voxel.worldZ,
    width,
    height,
  );
  if (!center) return null;

  const xEdge = projectPoint(
    matrix,
    voxel.worldX + voxel.sizeX / 2,
    voxel.worldY,
    voxel.worldZ,
    width,
    height,
  );
  const zEdge = projectPoint(
    matrix,
    voxel.worldX,
    voxel.worldY,
    voxel.worldZ + voxel.sizeZ / 2,
    width,
    height,
  );
  const projectedHalfSize = Math.max(
    xEdge ? Math.hypot(xEdge.screenX - center.screenX, xEdge.screenY - center.screenY) : 0,
    zEdge ? Math.hypot(zEdge.screenX - center.screenX, zEdge.screenY - center.screenY) : 0,
  );
  return {
    voxel,
    ...center,
    radiusPx: Math.max(10, Math.min(34, projectedHalfSize + 7)),
  };
}

export function pickVolumeVoxel(
  voxels: VolumeVoxel[],
  camera: OrbitCamera,
  width: number,
  height: number,
  screenX: number,
  screenY: number,
  minimumHitRadiusPx = 18,
): VoxelPick | null {
  let best: VoxelPick | null = null;
  let bestScore = Number.POSITIVE_INFINITY;

  for (const voxel of voxels) {
    const projected = projectVoxelToScreen(voxel, camera, width, height);
    if (!projected) continue;
    if (
      projected.screenX < -projected.radiusPx ||
      projected.screenX > width + projected.radiusPx ||
      projected.screenY < -projected.radiusPx ||
      projected.screenY > height + projected.radiusPx
    ) {
      continue;
    }
    const distancePx = Math.hypot(
      projected.screenX - screenX,
      projected.screenY - screenY,
    );
    const hitRadius = Math.max(minimumHitRadiusPx, projected.radiusPx);
    if (distancePx > hitRadius) continue;

    const normalizedDistance = distancePx / hitRadius;
    const valueTieBreaker = (1 - voxel.value) * 0.02;
    const score = normalizedDistance + valueTieBreaker;
    if (score < bestScore) {
      bestScore = score;
      best = {
        ...projected,
        distancePx,
      };
    }
  }
  return best;
}

export function strongestVisibleVoxel(
  voxels: VolumeVoxel[],
  camera: OrbitCamera,
  width: number,
  height: number,
): ProjectedVoxel | null {
  for (const voxel of voxels) {
    const projected = projectVoxelToScreen(voxel, camera, width, height);
    if (!projected) continue;
    if (
      projected.screenX >= 0 &&
      projected.screenX <= width &&
      projected.screenY >= 0 &&
      projected.screenY <= height
    ) {
      return projected;
    }
  }
  return null;
}
