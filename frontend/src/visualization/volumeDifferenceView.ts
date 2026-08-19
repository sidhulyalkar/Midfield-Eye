import type { VolumeDifference, VolumeDifferenceCell } from "./volumeDifference";
import { temporalLayerSet, type VolumeTemporalFilter } from "./volumeTemporal";

export function filterVolumeDifferenceCells(
  cells: readonly VolumeDifferenceCell[],
  filter: VolumeTemporalFilter,
  horizonSteps: number,
): VolumeDifferenceCell[] {
  const layers = temporalLayerSet(filter, horizonSteps);
  return cells.filter((cell) => layers.has(cell.layerIndex));
}

export function differenceView(
  difference: VolumeDifference,
  filter: VolumeTemporalFilter,
  horizonSteps: number,
): VolumeDifference {
  const cells = filterVolumeDifferenceCells(
    difference.cells,
    filter,
    horizonSteps,
  );
  return {
    ...difference,
    cells,
    summary: {
      ...difference.summary,
      intersection: cells.filter((cell) => cell.support === "intersection")
        .length,
      leftOnly: cells.filter((cell) => cell.support === "left_only").length,
      rightOnly: cells.filter((cell) => cell.support === "right_only").length,
      retainedUnion: cells.length,
    },
  };
}
