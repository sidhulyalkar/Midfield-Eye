import type { VolumeDifferenceCell } from "./volumeDifference";
import { temporalLayerSet, type VolumeTemporalFilter } from "./volumeTemporal";

export function filterVolumeDifferenceCells(
  cells: readonly VolumeDifferenceCell[],
  filter: VolumeTemporalFilter,
  horizonSteps: number,
): VolumeDifferenceCell[] {
  const layers = temporalLayerSet(filter, horizonSteps);
  return cells.filter((cell) => layers.has(cell.layerIndex));
}
