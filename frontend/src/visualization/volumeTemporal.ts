import {
  INSTANCE_STRIDE,
  type VolumeScene,
  type VolumeVoxel,
} from "./affordanceVolume";

export type TemporalLayerIndex = number;

export type VolumeTemporalFilter =
  | { mode: "full" }
  | { mode: "slice"; layerIndex: TemporalLayerIndex }
  | {
      mode: "band";
      startLayerIndex: TemporalLayerIndex;
      endLayerIndex: TemporalLayerIndex;
    };

export type VolumeTrajectoryPoint = {
  layerIndex: TemporalLayerIndex;
  forecastSeconds: number;
  status: "retained" | "not_retained";
  voxel: VolumeVoxel | null;
  voxelId: string | null;
  value: number | null;
};

export const FULL_TEMPORAL_FILTER: VolumeTemporalFilter = { mode: "full" };

function assertLayerIndex(value: number, label: string): void {
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative integer layer index.`);
  }
}

export function validateTemporalFilter(
  filter: VolumeTemporalFilter,
  horizonSteps?: number,
): void {
  if (filter.mode === "full") return;

  if (filter.mode === "slice") {
    assertLayerIndex(filter.layerIndex, "layerIndex");
    if (horizonSteps !== undefined && filter.layerIndex >= horizonSteps) {
      throw new Error("layerIndex is outside the configured temporal horizon.");
    }
    return;
  }

  assertLayerIndex(filter.startLayerIndex, "startLayerIndex");
  assertLayerIndex(filter.endLayerIndex, "endLayerIndex");
  if (filter.startLayerIndex > filter.endLayerIndex) {
    throw new Error(
      "startLayerIndex must be less than or equal to endLayerIndex.",
    );
  }
  if (horizonSteps !== undefined && filter.endLayerIndex >= horizonSteps) {
    throw new Error(
      "Temporal band is outside the configured temporal horizon.",
    );
  }
}

export function temporalLayerSet(
  filter: VolumeTemporalFilter,
  horizonSteps: number,
): ReadonlySet<TemporalLayerIndex> {
  if (!Number.isInteger(horizonSteps) || horizonSteps < 1) {
    throw new Error("horizonSteps must be a positive integer.");
  }
  validateTemporalFilter(filter, horizonSteps);

  if (filter.mode === "full") {
    return new Set(Array.from({ length: horizonSteps }, (_, index) => index));
  }
  if (filter.mode === "slice") return new Set([filter.layerIndex]);

  return new Set(
    Array.from(
      { length: filter.endLayerIndex - filter.startLayerIndex + 1 },
      (_, offset) => filter.startLayerIndex + offset,
    ),
  );
}

export function filterRetainedVoxels(
  fullRetainedVoxels: readonly VolumeVoxel[],
  filter: VolumeTemporalFilter,
  horizonSteps: number,
): VolumeVoxel[] {
  const selectedLayerSet = temporalLayerSet(filter, horizonSteps);
  return fullRetainedVoxels.filter((voxel) =>
    selectedLayerSet.has(voxel.layerIndex),
  );
}

export function filterVolumeScene(
  fullScene: VolumeScene,
  filter: VolumeTemporalFilter,
): VolumeScene {
  if (filter.mode === "full") return fullScene;

  const selectedLayerSet = temporalLayerSet(
    filter,
    fullScene.stats.horizonSteps,
  );
  const selectedIndices: number[] = [];
  fullScene.voxels.forEach((voxel, index) => {
    if (selectedLayerSet.has(voxel.layerIndex)) selectedIndices.push(index);
  });

  const voxels = selectedIndices.map((index) => fullScene.voxels[index]!);
  const field = new Float32Array(voxels.length * INSTANCE_STRIDE);
  selectedIndices.forEach((sourceIndex, targetIndex) => {
    field.set(
      fullScene.field.subarray(
        sourceIndex * INSTANCE_STRIDE,
        (sourceIndex + 1) * INSTANCE_STRIDE,
      ),
      targetIndex * INSTANCE_STRIDE,
    );
  });

  return {
    ...fullScene,
    field,
    voxels,
    stats: {
      ...fullScene.stats,
      renderedVoxels: voxels.length,
    },
  };
}

export function volumeSpatialCellKey(voxel: VolumeVoxel): string {
  return [
    voxel.frameId,
    voxel.channel,
    voxel.gridXIndex,
    voxel.gridYIndex,
  ].join(":");
}

export function volumeVoxelLayerKey(voxel: VolumeVoxel): string {
  return `${volumeSpatialCellKey(voxel)}:${voxel.layerIndex}`;
}

export function horizonSecondsForLayer(
  layerIndex: TemporalLayerIndex,
  horizonSteps: number,
  horizonSeconds: number,
): number {
  assertLayerIndex(layerIndex, "layerIndex");
  if (!Number.isInteger(horizonSteps) || horizonSteps < 1) {
    throw new Error("horizonSteps must be a positive integer.");
  }
  if (layerIndex >= horizonSteps) {
    throw new Error("layerIndex is outside the configured temporal horizon.");
  }
  if (!Number.isFinite(horizonSeconds) || horizonSeconds < 0) {
    throw new Error("horizonSeconds must be finite and non-negative.");
  }
  return horizonSteps === 1
    ? 0
    : (layerIndex / (horizonSteps - 1)) * horizonSeconds;
}

export function buildRetainedVoxelTrajectory(
  fullRetainedVoxels: readonly VolumeVoxel[],
  inspectedVoxel: VolumeVoxel,
  horizonSteps: number,
  horizonSeconds: number,
): VolumeTrajectoryPoint[] {
  if (!Number.isInteger(horizonSteps) || horizonSteps < 1) {
    throw new Error("horizonSteps must be a positive integer.");
  }

  const spatialKey = volumeSpatialCellKey(inspectedVoxel);
  const byLayer = new Map<TemporalLayerIndex, VolumeVoxel>();
  for (const voxel of fullRetainedVoxels) {
    if (volumeSpatialCellKey(voxel) !== spatialKey) continue;
    const existing = byLayer.get(voxel.layerIndex);
    if (!existing || voxel.id.localeCompare(existing.id) < 0) {
      byLayer.set(voxel.layerIndex, voxel);
    }
  }

  return Array.from({ length: horizonSteps }, (_, layerIndex) => {
    const voxel = byLayer.get(layerIndex) ?? null;
    return {
      layerIndex,
      forecastSeconds:
        voxel?.forecastSeconds ??
        horizonSecondsForLayer(layerIndex, horizonSteps, horizonSeconds),
      status: voxel ? "retained" : "not_retained",
      voxel,
      voxelId: voxel?.id ?? null,
      value: voxel?.value ?? null,
    };
  });
}

export function temporalFilterLabel(
  filter: VolumeTemporalFilter,
  horizonSteps: number,
  horizonSeconds: number,
): string {
  validateTemporalFilter(filter, horizonSteps);
  if (filter.mode === "full")
    return `Full · 0.00–+${horizonSeconds.toFixed(2)} s`;
  if (filter.mode === "slice") {
    return `Slice · +${horizonSecondsForLayer(
      filter.layerIndex,
      horizonSteps,
      horizonSeconds,
    ).toFixed(2)} s`;
  }
  return `Band · +${horizonSecondsForLayer(
    filter.startLayerIndex,
    horizonSteps,
    horizonSeconds,
  ).toFixed(2)}–+${horizonSecondsForLayer(
    filter.endLayerIndex,
    horizonSteps,
    horizonSeconds,
  ).toFixed(2)} s`;
}
