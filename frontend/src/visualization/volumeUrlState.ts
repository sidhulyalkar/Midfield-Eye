import {
  FULL_TEMPORAL_FILTER,
  validateTemporalFilter,
  type VolumeTemporalFilter,
} from "./volumeTemporal";

function parseInteger(value: string | null): number | null {
  if (value === null || !/^\d+$/u.test(value)) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

export function parseTemporalFilterFromSearchParams(
  searchParams: URLSearchParams,
  horizonSteps: number,
): VolumeTemporalFilter {
  const mode = searchParams.get("tm");
  if (!mode || mode === "full") return FULL_TEMPORAL_FILTER;

  if (mode === "slice") {
    const layerIndex = parseInteger(searchParams.get("layer"));
    if (layerIndex === null) return FULL_TEMPORAL_FILTER;
    const filter: VolumeTemporalFilter = { mode: "slice", layerIndex };
    try {
      validateTemporalFilter(filter, horizonSteps);
      return filter;
    } catch {
      return FULL_TEMPORAL_FILTER;
    }
  }

  if (mode === "band") {
    const startLayerIndex = parseInteger(searchParams.get("from"));
    const endLayerIndex = parseInteger(searchParams.get("to"));
    if (startLayerIndex === null || endLayerIndex === null) {
      return FULL_TEMPORAL_FILTER;
    }
    const filter: VolumeTemporalFilter = {
      mode: "band",
      startLayerIndex,
      endLayerIndex,
    };
    try {
      validateTemporalFilter(filter, horizonSteps);
      return filter;
    } catch {
      return FULL_TEMPORAL_FILTER;
    }
  }

  return FULL_TEMPORAL_FILTER;
}

export function writeTemporalFilterToSearchParams(
  current: URLSearchParams,
  filter: VolumeTemporalFilter,
): URLSearchParams {
  const next = new URLSearchParams(current);
  next.delete("layer");
  next.delete("from");
  next.delete("to");

  next.set("tm", filter.mode);
  if (filter.mode === "slice") {
    next.set("layer", String(filter.layerIndex));
  } else if (filter.mode === "band") {
    next.set("from", String(filter.startLayerIndex));
    next.set("to", String(filter.endLayerIndex));
  }
  return next;
}

export function temporalFiltersEqual(
  left: VolumeTemporalFilter,
  right: VolumeTemporalFilter,
): boolean {
  if (left.mode !== right.mode) return false;
  if (left.mode === "full" && right.mode === "full") return true;
  if (left.mode === "slice" && right.mode === "slice") {
    return left.layerIndex === right.layerIndex;
  }
  if (left.mode === "band" && right.mode === "band") {
    return (
      left.startLayerIndex === right.startLayerIndex &&
      left.endLayerIndex === right.endLayerIndex
    );
  }
  return false;
}
