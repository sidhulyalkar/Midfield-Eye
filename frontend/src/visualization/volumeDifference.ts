import type {
  VolumeChannel,
  VolumeScene,
  VolumeVoxel,
} from "./affordanceVolume";

export type VolumeDifferenceSupport =
  | "intersection"
  | "left_only"
  | "right_only";

export type VolumeDifferenceCell = {
  key: string;
  layerIndex: number;
  gridXIndex: number;
  gridYIndex: number;
  support: VolumeDifferenceSupport;
  left: VolumeVoxel | null;
  right: VolumeVoxel | null;
  delta: number | null;
};

export type VolumeDifferenceSummary = {
  intersection: number;
  leftOnly: number;
  rightOnly: number;
  neither: number;
  retainedUnion: number;
  totalCanonicalCells: number;
};

export type VolumeDifference = {
  channel: VolumeChannel;
  signConvention: "condition_b_minus_condition_a";
  cells: VolumeDifferenceCell[];
  summary: VolumeDifferenceSummary;
};

type IndexedScene = {
  byKey: Map<string, VolumeVoxel>;
  layerForecastSeconds: Map<number, number>;
};

const GEOMETRY_EPSILON = 1e-6;
const TIME_EPSILON = 1e-9;

export function comparisonCellKey(
  layerIndex: number,
  gridXIndex: number,
  gridYIndex: number,
): string {
  return `${layerIndex}:${gridXIndex}:${gridYIndex}`;
}

function approximatelyEqual(left: number, right: number, epsilon: number) {
  return Math.abs(left - right) <= epsilon;
}

function assertSceneCompatibility(left: VolumeScene, right: VolumeScene) {
  if (left.stats.channel !== right.stats.channel) {
    throw new Error(
      `Difference scenes must use the same channel: ${left.stats.channel} != ${right.stats.channel}`,
    );
  }
  if (left.stats.gridX !== right.stats.gridX) {
    throw new Error(
      `Difference scenes must use the same gridX: ${left.stats.gridX} != ${right.stats.gridX}`,
    );
  }
  if (left.stats.gridY !== right.stats.gridY) {
    throw new Error(
      `Difference scenes must use the same gridY: ${left.stats.gridY} != ${right.stats.gridY}`,
    );
  }
  if (left.stats.horizonSteps !== right.stats.horizonSteps) {
    throw new Error(
      `Difference scenes must use the same horizonSteps: ${left.stats.horizonSteps} != ${right.stats.horizonSteps}`,
    );
  }
  if (left.stats.maxVoxels !== right.stats.maxVoxels) {
    throw new Error(
      `Difference scenes must use the same voxel budget: ${left.stats.maxVoxels} != ${right.stats.maxVoxels}`,
    );
  }
  if (
    !approximatelyEqual(
      left.timeScaleMetres,
      right.timeScaleMetres,
      GEOMETRY_EPSILON,
    )
  ) {
    throw new Error(
      `Difference scenes must use the same temporal render scale: ${left.timeScaleMetres} != ${right.timeScaleMetres}`,
    );
  }
}

function indexScene(scene: VolumeScene, side: "left" | "right"): IndexedScene {
  const byKey = new Map<string, VolumeVoxel>();
  const layerForecastSeconds = new Map<number, number>();

  for (const voxel of scene.voxels) {
    if (voxel.channel !== scene.stats.channel) {
      throw new Error(
        `${side} scene contains voxel ${voxel.id} from channel ${voxel.channel}, expected ${scene.stats.channel}`,
      );
    }
    if (
      voxel.layerIndex < 0 ||
      voxel.layerIndex >= scene.stats.horizonSteps ||
      voxel.gridXIndex < 0 ||
      voxel.gridXIndex >= scene.stats.gridX ||
      voxel.gridYIndex < 0 ||
      voxel.gridYIndex >= scene.stats.gridY
    ) {
      throw new Error(
        `${side} scene contains out-of-range voxel ${voxel.id} at ${voxel.layerIndex}:${voxel.gridXIndex}:${voxel.gridYIndex}`,
      );
    }

    const key = comparisonCellKey(
      voxel.layerIndex,
      voxel.gridXIndex,
      voxel.gridYIndex,
    );
    if (byKey.has(key)) {
      throw new Error(
        `${side} scene contains duplicate canonical comparison cell ${key}`,
      );
    }
    byKey.set(key, voxel);

    const knownLayerTime = layerForecastSeconds.get(voxel.layerIndex);
    if (
      knownLayerTime !== undefined &&
      !approximatelyEqual(
        knownLayerTime,
        voxel.forecastSeconds,
        TIME_EPSILON,
      )
    ) {
      throw new Error(
        `${side} scene contains inconsistent forecast timestamps for layer ${voxel.layerIndex}`,
      );
    }
    layerForecastSeconds.set(voxel.layerIndex, voxel.forecastSeconds);
  }

  return { byKey, layerForecastSeconds };
}

function assertLayerTimesCompatible(left: IndexedScene, right: IndexedScene) {
  for (const [layerIndex, leftSeconds] of left.layerForecastSeconds) {
    const rightSeconds = right.layerForecastSeconds.get(layerIndex);
    if (
      rightSeconds !== undefined &&
      !approximatelyEqual(leftSeconds, rightSeconds, TIME_EPSILON)
    ) {
      throw new Error(
        `Difference scenes disagree on forecast time for layer ${layerIndex}: ${leftSeconds} != ${rightSeconds}`,
      );
    }
  }
}

function assertIntersectionGeometryCompatible(
  left: VolumeVoxel,
  right: VolumeVoxel,
  key: string,
) {
  const comparisons: Array<[string, number, number]> = [
    ["pitchX", left.pitchX, right.pitchX],
    ["pitchY", left.pitchY, right.pitchY],
    ["forecastSeconds", left.forecastSeconds, right.forecastSeconds],
    ["sizeX", left.sizeX, right.sizeX],
    ["sizeY", left.sizeY, right.sizeY],
    ["sizeZ", left.sizeZ, right.sizeZ],
    ["worldX", left.worldX, right.worldX],
    ["worldY", left.worldY, right.worldY],
    ["worldZ", left.worldZ, right.worldZ],
  ];

  for (const [name, leftValue, rightValue] of comparisons) {
    const epsilon = name === "forecastSeconds" ? TIME_EPSILON : GEOMETRY_EPSILON;
    if (!approximatelyEqual(leftValue, rightValue, epsilon)) {
      throw new Error(
        `Difference intersection ${key} has incompatible ${name}: ${leftValue} != ${rightValue}`,
      );
    }
  }
}

function compareCellKeys(left: string, right: string) {
  const [leftLayer, leftX, leftY] = left.split(":").map(Number);
  const [rightLayer, rightX, rightY] = right.split(":").map(Number);
  return (
    leftLayer - rightLayer ||
    leftX - rightX ||
    leftY - rightY
  );
}

export function buildVolumeDifference(
  conditionA: VolumeScene,
  conditionB: VolumeScene,
): VolumeDifference {
  assertSceneCompatibility(conditionA, conditionB);
  const left = indexScene(conditionA, "left");
  const right = indexScene(conditionB, "right");
  assertLayerTimesCompatible(left, right);

  const keys = new Set<string>([...left.byKey.keys(), ...right.byKey.keys()]);
  const sortedKeys = [...keys].sort(compareCellKeys);
  const cells: VolumeDifferenceCell[] = [];
  let intersection = 0;
  let leftOnly = 0;
  let rightOnly = 0;

  for (const key of sortedKeys) {
    const leftVoxel = left.byKey.get(key) ?? null;
    const rightVoxel = right.byKey.get(key) ?? null;
    const [layerIndex, gridXIndex, gridYIndex] = key.split(":").map(Number);

    if (leftVoxel && rightVoxel) {
      assertIntersectionGeometryCompatible(leftVoxel, rightVoxel, key);
      intersection += 1;
      cells.push({
        key,
        layerIndex,
        gridXIndex,
        gridYIndex,
        support: "intersection",
        left: leftVoxel,
        right: rightVoxel,
        delta: rightVoxel.value - leftVoxel.value,
      });
      continue;
    }

    if (leftVoxel) {
      leftOnly += 1;
      cells.push({
        key,
        layerIndex,
        gridXIndex,
        gridYIndex,
        support: "left_only",
        left: leftVoxel,
        right: null,
        delta: null,
      });
      continue;
    }

    if (rightVoxel) {
      rightOnly += 1;
      cells.push({
        key,
        layerIndex,
        gridXIndex,
        gridYIndex,
        support: "right_only",
        left: null,
        right: rightVoxel,
        delta: null,
      });
    }
  }

  const totalCanonicalCells =
    conditionA.stats.gridX *
    conditionA.stats.gridY *
    conditionA.stats.horizonSteps;
  const retainedUnion = cells.length;

  return {
    channel: conditionA.stats.channel,
    signConvention: "condition_b_minus_condition_a",
    cells,
    summary: {
      intersection,
      leftOnly,
      rightOnly,
      neither: totalCanonicalCells - retainedUnion,
      retainedUnion,
      totalCanonicalCells,
    },
  };
}
