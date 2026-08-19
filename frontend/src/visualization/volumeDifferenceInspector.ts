import type { VolumeVoxel } from "./affordanceVolume";
import type {
  VolumeDifference,
  VolumeDifferenceCell,
  VolumeDifferenceSupport,
} from "./volumeDifference";

export type VolumeDifferenceInspectionSide = {
  conditionId: string;
  retained: boolean;
  voxelId: string | null;
  value: number | null;
  voxel: VolumeVoxel | null;
};

export type VolumeDifferenceInspection = {
  key: string;
  support: VolumeDifferenceSupport;
  numericComparisonAvailable: boolean;
  signConvention: "condition_b_minus_condition_a";
  delta: number | null;
  absoluteDelta: number | null;
  conditionA: VolumeDifferenceInspectionSide;
  conditionB: VolumeDifferenceInspectionSide;
  claimBoundary: {
    oneSidedPresenceIsNumericalZero: false;
    missingSupportInterpolated: false;
    calibratedProbability: false;
    futureObservedFramesUsed: false;
  };
};

function inspectionSide(
  conditionId: string,
  voxel: VolumeVoxel | null,
): VolumeDifferenceInspectionSide {
  return {
    conditionId,
    retained: voxel !== null,
    voxelId: voxel?.id ?? null,
    value: voxel?.value ?? null,
    voxel,
  };
}

function assertInspectionCell(cell: VolumeDifferenceCell) {
  if (cell.support === "intersection") {
    if (!cell.left || !cell.right || cell.delta === null) {
      throw new Error(
        `Intersection difference cell ${cell.key} is missing forensic evidence`,
      );
    }
    return;
  }
  if (cell.support === "left_only") {
    if (!cell.left || cell.right || cell.delta !== null) {
      throw new Error(
        `Left-only difference cell ${cell.key} has an invalid forensic state`,
      );
    }
    return;
  }
  if (!cell.right || cell.left || cell.delta !== null) {
    throw new Error(
      `Right-only difference cell ${cell.key} has an invalid forensic state`,
    );
  }
}

export function inspectVolumeDifferenceCell(
  difference: VolumeDifference,
  key: string,
): VolumeDifferenceInspection | null {
  const cell = difference.cells.find((candidate) => candidate.key === key);
  if (!cell) return null;
  assertInspectionCell(cell);
  const numericComparisonAvailable = cell.support === "intersection";
  return {
    key: cell.key,
    support: cell.support,
    numericComparisonAvailable,
    signConvention: difference.signConvention,
    delta: numericComparisonAvailable ? cell.delta : null,
    absoluteDelta:
      numericComparisonAvailable && cell.delta !== null
        ? Math.abs(cell.delta)
        : null,
    conditionA: inspectionSide(difference.conditionAId, cell.left),
    conditionB: inspectionSide(difference.conditionBId, cell.right),
    claimBoundary: {
      oneSidedPresenceIsNumericalZero: false,
      missingSupportInterpolated: false,
      calibratedProbability: false,
      futureObservedFramesUsed: false,
    },
  };
}

export function mostInformativeDifferenceCell(
  difference: VolumeDifference,
): VolumeDifferenceCell | null {
  let bestIntersection: VolumeDifferenceCell | null = null;
  for (const cell of difference.cells) {
    if (cell.support !== "intersection" || cell.delta === null) continue;
    if (!bestIntersection || bestIntersection.delta === null) {
      bestIntersection = cell;
      continue;
    }
    const candidateMagnitude = Math.abs(cell.delta);
    const bestMagnitude = Math.abs(bestIntersection.delta);
    if (
      candidateMagnitude > bestMagnitude ||
      (candidateMagnitude === bestMagnitude &&
        cell.key.localeCompare(bestIntersection.key) < 0)
    ) {
      bestIntersection = cell;
    }
  }
  if (bestIntersection) return bestIntersection;

  let categorical: VolumeDifferenceCell | null = null;
  for (const cell of difference.cells) {
    if (!categorical || cell.key.localeCompare(categorical.key) < 0) {
      categorical = cell;
    }
  }
  return categorical;
}
