import { INSTANCE_STRIDE, type VolumeVoxel } from "./affordanceVolume";
import type {
  VolumeDifferenceCell,
  VolumeDifferenceSupport,
} from "./volumeDifference";

export type VolumeDifferenceGlyph =
  | "intersection_cell"
  | "left_parallel_rails"
  | "right_parallel_rails";

export type VolumeDifferenceRenderCell = {
  key: string;
  support: VolumeDifferenceSupport;
  glyph: VolumeDifferenceGlyph;
  comparison: VolumeDifferenceCell;
  worldX: number;
  worldY: number;
  worldZ: number;
  sizeX: number;
  sizeY: number;
  sizeZ: number;
  signedDelta: number | null;
  absoluteDelta: number | null;
  instanceStart: number;
  instanceCount: number;
};

export type VolumeDifferenceRenderStats = {
  comparisonCells: number;
  intersectionCells: number;
  leftOnlyCells: number;
  rightOnlyCells: number;
  fieldInstances: number;
  maxAbsoluteDelta: number;
};

export type VolumeDifferenceRenderPayload = {
  field: Float32Array;
  cells: VolumeDifferenceRenderCell[];
  stats: VolumeDifferenceRenderStats;
};

type Rgb = readonly [number, number, number];

const POSITIVE_COLOR: Rgb = [0.35, 0.92, 0.72];
const NEGATIVE_COLOR: Rgb = [1, 0.48, 0.39];
const NEUTRAL_COLOR: Rgb = [0.75, 0.8, 0.78];
const LEFT_ONLY_COLOR: Rgb = [0.96, 0.82, 0.37];
const RIGHT_ONLY_COLOR: Rgb = [0.45, 0.75, 0.99];

function appendInstance(
  target: number[],
  position: readonly [number, number, number],
  scale: readonly [number, number, number],
  color: Rgb,
  alpha: number,
) {
  target.push(
    position[0],
    position[1],
    position[2],
    scale[0],
    scale[1],
    scale[2],
    color[0],
    color[1],
    color[2],
    alpha,
  );
}

function representativeVoxel(cell: VolumeDifferenceCell): VolumeVoxel {
  const voxel = cell.left ?? cell.right;
  if (!voxel) {
    throw new Error(`Difference cell ${cell.key} has no retained source voxel`);
  }
  return voxel;
}

function assertCellSupportContract(cell: VolumeDifferenceCell) {
  if (cell.support === "intersection") {
    if (!cell.left || !cell.right || cell.delta === null) {
      throw new Error(
        `Intersection difference cell ${cell.key} must contain A, B, and a numerical delta`,
      );
    }
    if (!Number.isFinite(cell.delta) || Math.abs(cell.delta) > 1) {
      throw new Error(
        `Intersection difference cell ${cell.key} has invalid delta ${cell.delta}`,
      );
    }
    return;
  }
  if (cell.support === "left_only") {
    if (!cell.left || cell.right || cell.delta !== null) {
      throw new Error(
        `Left-only difference cell ${cell.key} must contain only A and delta=null`,
      );
    }
    return;
  }
  if (!cell.right || cell.left || cell.delta !== null) {
    throw new Error(
      `Right-only difference cell ${cell.key} must contain only B and delta=null`,
    );
  }
}

function intersectionColor(delta: number): Rgb {
  if (delta > 0) return POSITIVE_COLOR;
  if (delta < 0) return NEGATIVE_COLOR;
  return NEUTRAL_COLOR;
}

function intersectionAlpha(delta: number) {
  return 0.24 + 0.68 * Math.sqrt(Math.min(1, Math.abs(delta)));
}

function appendLeftOnlyGlyph(instances: number[], voxel: VolumeVoxel) {
  const railWidth = Math.max(0.18, voxel.sizeX * 0.13);
  const railLength = voxel.sizeZ * 0.84;
  const offset = voxel.sizeX * 0.28;
  appendInstance(
    instances,
    [voxel.worldX - offset, voxel.worldY, voxel.worldZ],
    [railWidth, voxel.sizeY, railLength],
    LEFT_ONLY_COLOR,
    0.7,
  );
  appendInstance(
    instances,
    [voxel.worldX + offset, voxel.worldY, voxel.worldZ],
    [railWidth, voxel.sizeY, railLength],
    LEFT_ONLY_COLOR,
    0.7,
  );
}

function appendRightOnlyGlyph(instances: number[], voxel: VolumeVoxel) {
  const railLength = voxel.sizeX * 0.84;
  const railWidth = Math.max(0.18, voxel.sizeZ * 0.13);
  const offset = voxel.sizeZ * 0.28;
  appendInstance(
    instances,
    [voxel.worldX, voxel.worldY, voxel.worldZ - offset],
    [railLength, voxel.sizeY, railWidth],
    RIGHT_ONLY_COLOR,
    0.7,
  );
  appendInstance(
    instances,
    [voxel.worldX, voxel.worldY, voxel.worldZ + offset],
    [railLength, voxel.sizeY, railWidth],
    RIGHT_ONLY_COLOR,
    0.7,
  );
}

export function buildVolumeDifferenceRenderPayload(
  cellsToRender: readonly VolumeDifferenceCell[],
): VolumeDifferenceRenderPayload {
  const instances: number[] = [];
  const cells: VolumeDifferenceRenderCell[] = [];
  let intersectionCells = 0;
  let leftOnlyCells = 0;
  let rightOnlyCells = 0;
  let maxAbsoluteDelta = 0;

  for (const cell of cellsToRender) {
    assertCellSupportContract(cell);
    const voxel = representativeVoxel(cell);
    const instanceStart = instances.length / INSTANCE_STRIDE;
    let glyph: VolumeDifferenceGlyph;
    let signedDelta: number | null = null;
    let absoluteDelta: number | null = null;

    if (cell.support === "intersection") {
      const delta = cell.delta;
      if (delta === null) {
        throw new Error(`Intersection difference cell ${cell.key} lost its delta`);
      }
      signedDelta = delta;
      absoluteDelta = Math.abs(delta);
      maxAbsoluteDelta = Math.max(maxAbsoluteDelta, absoluteDelta);
      intersectionCells += 1;
      glyph = "intersection_cell";
      appendInstance(
        instances,
        [voxel.worldX, voxel.worldY, voxel.worldZ],
        [voxel.sizeX * 0.82, voxel.sizeY, voxel.sizeZ * 0.82],
        intersectionColor(delta),
        intersectionAlpha(delta),
      );
    } else if (cell.support === "left_only") {
      leftOnlyCells += 1;
      glyph = "left_parallel_rails";
      appendLeftOnlyGlyph(instances, voxel);
    } else {
      rightOnlyCells += 1;
      glyph = "right_parallel_rails";
      appendRightOnlyGlyph(instances, voxel);
    }

    const instanceCount = instances.length / INSTANCE_STRIDE - instanceStart;
    cells.push({
      key: cell.key,
      support: cell.support,
      glyph,
      comparison: cell,
      worldX: voxel.worldX,
      worldY: voxel.worldY,
      worldZ: voxel.worldZ,
      sizeX: voxel.sizeX,
      sizeY: voxel.sizeY,
      sizeZ: voxel.sizeZ,
      signedDelta,
      absoluteDelta,
      instanceStart,
      instanceCount,
    });
  }

  const field = new Float32Array(instances);
  if (field.length % INSTANCE_STRIDE !== 0) {
    throw new Error("Difference field buffer is not aligned to INSTANCE_STRIDE");
  }

  return {
    field,
    cells,
    stats: {
      comparisonCells: cells.length,
      intersectionCells,
      leftOnlyCells,
      rightOnlyCells,
      fieldInstances: field.length / INSTANCE_STRIDE,
      maxAbsoluteDelta,
    },
  };
}
