import type { VolumeDifference, VolumeDifferenceCell } from "./volumeDifference";
import type { DeterministicComparisonQuality } from "./volumeComparisonUrl";
import type { VolumeTemporalFilter } from "./volumeTemporal";

export type DifferencePublicationState = {
  scenarioId: string;
  frameIndex: number;
  channel: "future_space" | "option_creation";
  layerIndex: number;
  leadSeconds: number;
  quality: DeterministicComparisonQuality;
  threshold: number;
};

export type DifferencePublicationSummary = {
  visibleCells: number;
  sharedSupport: number;
  leftOnly: number;
  rightOnly: number;
  supportOverlap: number;
  meanSignedDelta: number | null;
  meanAbsoluteDelta: number | null;
  maxAbsoluteDelta: number | null;
};

export type DifferenceFailureGallery = {
  leftOnly: VolumeDifferenceCell | null;
  rightOnly: VolumeDifferenceCell | null;
};

function slug(value: string) {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/gu, "-")
    .replace(/^-+|-+$/gu, "");
  return normalized || "unknown";
}

function fixedInteger(value: number, scale: number, width: number) {
  if (!Number.isFinite(value)) {
    throw new Error("Publication identity values must be finite.");
  }
  return String(Math.round(value * scale)).padStart(width, "0");
}

export function requirePublicationSlice(
  filter: VolumeTemporalFilter,
): number {
  if (filter.mode !== "slice") {
    throw new Error(
      "Publication figure mode requires an exact integer temporal slice.",
    );
  }
  if (!Number.isInteger(filter.layerIndex) || filter.layerIndex < 0) {
    throw new Error("Publication layerIndex must be a non-negative integer.");
  }
  return filter.layerIndex;
}

export function differencePublicationFigureId(
  state: DifferencePublicationState,
): string {
  if (!Number.isInteger(state.frameIndex) || state.frameIndex < 0) {
    throw new Error("Publication frameIndex must be a non-negative integer.");
  }
  if (!Number.isInteger(state.layerIndex) || state.layerIndex < 0) {
    throw new Error("Publication layerIndex must be a non-negative integer.");
  }
  if (!Number.isFinite(state.threshold) || state.threshold < 0 || state.threshold > 1) {
    throw new Error("Publication threshold must be finite and within [0, 1].");
  }
  if (!Number.isFinite(state.leadSeconds) || state.leadSeconds <= 0) {
    throw new Error("Publication leadSeconds must be positive and finite.");
  }
  return [
    "ME-DIFF",
    slug(state.scenarioId),
    `f${state.frameIndex}`,
    slug(state.channel),
    `l${state.layerIndex}`,
    `lead${fixedInteger(state.leadSeconds, 100, 3)}`,
    `q${state.quality}`,
    `t${fixedInteger(state.threshold, 1000, 4)}`,
  ].join("-");
}

function compareIdentity(left: VolumeDifferenceCell, right: VolumeDifferenceCell) {
  return (
    left.layerIndex - right.layerIndex ||
    left.gridXIndex - right.gridXIndex ||
    left.gridYIndex - right.gridYIndex
  );
}

export function selectDifferenceFailureGallery(
  cells: readonly VolumeDifferenceCell[],
): DifferenceFailureGallery {
  let leftOnly: VolumeDifferenceCell | null = null;
  let rightOnly: VolumeDifferenceCell | null = null;
  for (const cell of cells) {
    if (
      cell.support === "left_only" &&
      (!leftOnly || compareIdentity(cell, leftOnly) < 0)
    ) {
      leftOnly = cell;
    }
    if (
      cell.support === "right_only" &&
      (!rightOnly || compareIdentity(cell, rightOnly) < 0)
    ) {
      rightOnly = cell;
    }
  }
  return { leftOnly, rightOnly };
}

export function summarizeDifferencePublication(
  cells: readonly VolumeDifferenceCell[],
): DifferencePublicationSummary {
  let sharedSupport = 0;
  let leftOnly = 0;
  let rightOnly = 0;
  let signedTotal = 0;
  let absoluteTotal = 0;
  let maxAbsoluteDelta = 0;

  for (const cell of cells) {
    if (cell.support === "left_only") {
      leftOnly += 1;
      continue;
    }
    if (cell.support === "right_only") {
      rightOnly += 1;
      continue;
    }
    if (cell.delta === null || !Number.isFinite(cell.delta)) {
      throw new Error(
        `Publication intersection ${cell.key} is missing a finite numerical delta.`,
      );
    }
    sharedSupport += 1;
    signedTotal += cell.delta;
    absoluteTotal += Math.abs(cell.delta);
    maxAbsoluteDelta = Math.max(maxAbsoluteDelta, Math.abs(cell.delta));
  }

  const visibleCells = cells.length;
  return {
    visibleCells,
    sharedSupport,
    leftOnly,
    rightOnly,
    supportOverlap: visibleCells ? sharedSupport / visibleCells : 0,
    meanSignedDelta: sharedSupport ? signedTotal / sharedSupport : null,
    meanAbsoluteDelta: sharedSupport ? absoluteTotal / sharedSupport : null,
    maxAbsoluteDelta: sharedSupport ? maxAbsoluteDelta : null,
  };
}

export function assertPublicationDifferenceMatches(
  difference: VolumeDifference,
  cells: readonly VolumeDifferenceCell[],
) {
  const source = new Set(difference.cells);
  for (const cell of cells) {
    if (!source.has(cell)) {
      throw new Error(
        `Publication cell ${cell.key} is not an exact record from the source difference.`,
      );
    }
  }
}
