import type {
  VolumeChannel,
  VolumeScene,
  VolumeVoxel,
} from "./affordanceVolume";

export type VolumeDifferenceSupport =
  | "intersection"
  | "left_only"
  | "right_only";

export type VolumeDifferenceCondition = {
  id: string;
  scene: VolumeScene;
  horizonSeconds: number;
  pitchLength: number;
  pitchWidth: number;
  threshold: number;
};

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
  conditionAId: string;
  conditionBId: string;
  channel: VolumeChannel;
  signConvention: "condition_b_minus_condition_a";
  cells: VolumeDifferenceCell[];
  summary: VolumeDifferenceSummary;
};

type IndexedScene = {
  byKey: Map<string, VolumeVoxel>;
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

function parseComparisonCellKey(key: string): [number, number, number] {
  const parts = key.split(":");
  const layerText = parts[0];
  const xText = parts[1];
  const yText = parts[2];
  if (
    parts.length !== 3 ||
    layerText === undefined ||
    xText === undefined ||
    yText === undefined
  ) {
    throw new Error(`Invalid canonical comparison cell key ${key}`);
  }
  const layerIndex = Number(layerText);
  const gridXIndex = Number(xText);
  const gridYIndex = Number(yText);
  if (
    !Number.isInteger(layerIndex) ||
    !Number.isInteger(gridXIndex) ||
    !Number.isInteger(gridYIndex)
  ) {
    throw new Error(`Invalid canonical comparison cell key ${key}`);
  }
  return [layerIndex, gridXIndex, gridYIndex];
}

function approximatelyEqual(left: number, right: number, epsilon: number) {
  return Math.abs(left - right) <= epsilon;
}

function expectedLayerForecastSeconds(
  layerIndex: number,
  horizonSteps: number,
  horizonSeconds: number,
) {
  if (horizonSteps <= 1) return 0;
  return (layerIndex / (horizonSteps - 1)) * horizonSeconds;
}

function assertConditionContract(
  condition: VolumeDifferenceCondition,
  side: "left" | "right",
) {
  if (!condition.id.trim()) {
    throw new Error(`${side} comparison condition must have a non-empty id`);
  }
  if (!Number.isFinite(condition.horizonSeconds) || condition.horizonSeconds < 0) {
    throw new Error(
      `${side} comparison condition has invalid horizonSeconds ${condition.horizonSeconds}`,
    );
  }
  if (!Number.isFinite(condition.pitchLength) || condition.pitchLength <= 0) {
    throw new Error(
      `${side} comparison condition has invalid pitchLength ${condition.pitchLength}`,
    );
  }
  if (!Number.isFinite(condition.pitchWidth) || condition.pitchWidth <= 0) {
    throw new Error(
      `${side} comparison condition has invalid pitchWidth ${condition.pitchWidth}`,
    );
  }
  if (
    !Number.isFinite(condition.threshold) ||
    condition.threshold < 0 ||
    condition.threshold > 1
  ) {
    throw new Error(
      `${side} comparison condition has invalid threshold ${condition.threshold}`,
    );
  }
}

function assertSceneCompatibility(
  left: VolumeDifferenceCondition,
  right: VolumeDifferenceCondition,
) {
  assertConditionContract(left, "left");
  assertConditionContract(right, "right");

  if (!approximatelyEqual(left.horizonSeconds, right.horizonSeconds, TIME_EPSILON)) {
    throw new Error(
      `Difference conditions must use the same horizonSeconds: ${left.horizonSeconds} != ${right.horizonSeconds}`,
    );
  }
  if (!approximatelyEqual(left.pitchLength, right.pitchLength, GEOMETRY_EPSILON)) {
    throw new Error(
      `Difference conditions must use the same pitchLength: ${left.pitchLength} != ${right.pitchLength}`,
    );
  }
  if (!approximatelyEqual(left.pitchWidth, right.pitchWidth, GEOMETRY_EPSILON)) {
    throw new Error(
      `Difference conditions must use the same pitchWidth: ${left.pitchWidth} != ${right.pitchWidth}`,
    );
  }
  if (!approximatelyEqual(left.threshold, right.threshold, GEOMETRY_EPSILON)) {
    throw new Error(
      `Difference conditions must use the same retention threshold: ${left.threshold} != ${right.threshold}`,
    );
  }

  const leftScene = left.scene;
  const rightScene = right.scene;
  if (leftScene.stats.channel !== rightScene.stats.channel) {
    throw new Error(
      `Difference scenes must use the same channel: ${leftScene.stats.channel} != ${rightScene.stats.channel}`,
    );
  }
  if (leftScene.stats.gridX !== rightScene.stats.gridX) {
    throw new Error(
      `Difference scenes must use the same gridX: ${leftScene.stats.gridX} != ${rightScene.stats.gridX}`,
    );
  }
  if (leftScene.stats.gridY !== rightScene.stats.gridY) {
    throw new Error(
      `Difference scenes must use the same gridY: ${leftScene.stats.gridY} != ${rightScene.stats.gridY}`,
    );
  }
  if (leftScene.stats.horizonSteps !== rightScene.stats.horizonSteps) {
    throw new Error(
      `Difference scenes must use the same horizonSteps: ${leftScene.stats.horizonSteps} != ${rightScene.stats.horizonSteps}`,
    );
  }
  if (leftScene.stats.maxVoxels !== rightScene.stats.maxVoxels) {
    throw new Error(
      `Difference scenes must use the same voxel budget: ${leftScene.stats.maxVoxels} != ${rightScene.stats.maxVoxels}`,
    );
  }
  if (
    !approximatelyEqual(
      leftScene.timeScaleMetres,
      rightScene.timeScaleMetres,
      GEOMETRY_EPSILON,
    )
  ) {
    throw new Error(
      `Difference scenes must use the same temporal render scale: ${leftScene.timeScaleMetres} != ${rightScene.timeScaleMetres}`,
    );
  }
}

function indexScene(
  condition: VolumeDifferenceCondition,
  side: "left" | "right",
): IndexedScene {
  const scene = condition.scene;
  const byKey = new Map<string, VolumeVoxel>();

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

    const expectedForecastSeconds = expectedLayerForecastSeconds(
      voxel.layerIndex,
      scene.stats.horizonSteps,
      condition.horizonSeconds,
    );
    if (
      !approximatelyEqual(
        voxel.forecastSeconds,
        expectedForecastSeconds,
        TIME_EPSILON,
      )
    ) {
      throw new Error(
        `${side} scene voxel ${voxel.id} has forecastSeconds ${voxel.forecastSeconds}, expected ${expectedForecastSeconds} for layer ${voxel.layerIndex}`,
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
  }

  return { byKey };
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
  const [leftLayer, leftX, leftY] = parseComparisonCellKey(left);
  const [rightLayer, rightX, rightY] = parseComparisonCellKey(right);
  return leftLayer - rightLayer || leftX - rightX || leftY - rightY;
}

export function buildVolumeDifference(
  conditionA: VolumeDifferenceCondition,
  conditionB: VolumeDifferenceCondition,
): VolumeDifference {
  assertSceneCompatibility(conditionA, conditionB);
  const left = indexScene(conditionA, "left");
  const right = indexScene(conditionB, "right");

  const keys = new Set<string>([...left.byKey.keys(), ...right.byKey.keys()]);
  const sortedKeys = [...keys].sort(compareCellKeys);
  const cells: VolumeDifferenceCell[] = [];
  let intersection = 0;
  let leftOnly = 0;
  let rightOnly = 0;

  for (const key of sortedKeys) {
    const leftVoxel = left.byKey.get(key) ?? null;
    const rightVoxel = right.byKey.get(key) ?? null;
    const [layerIndex, gridXIndex, gridYIndex] = parseComparisonCellKey(key);

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
    conditionA.scene.stats.gridX *
    conditionA.scene.stats.gridY *
    conditionA.scene.stats.horizonSteps;
  const retainedUnion = cells.length;

  return {
    conditionAId: conditionA.id,
    conditionBId: conditionB.id,
    channel: conditionA.scene.stats.channel,
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
