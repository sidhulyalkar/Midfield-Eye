import type { VolumeVoxel } from "./affordanceVolume";
import {
  buildRetainedVoxelTrajectory,
  type VolumeTemporalFilter,
  type VolumeTrajectoryPoint,
} from "./volumeTemporal";

export type SerializedVoxelInspection = {
  schemaVersion: "1.2.0";
  voxel: VolumeVoxel;
  temporalFilter: VolumeTemporalFilter;
  trajectory: Array<{
    layerIndex: number;
    forecastSeconds: number;
    status: VolumeTrajectoryPoint["status"];
    voxelId: string | null;
    value: number | null;
  }>;
  claimBoundary: {
    futureObservedFramesUsed: false;
    missingLayerSemantics: "not_retained_not_zero";
    calibratedProbability: false;
  };
};

export function serializeVoxelInspection(
  voxel: VolumeVoxel,
  fullRetainedVoxels: readonly VolumeVoxel[],
  temporalFilter: VolumeTemporalFilter,
  horizonSteps: number,
  horizonSeconds: number,
): SerializedVoxelInspection {
  const trajectory = buildRetainedVoxelTrajectory(
    fullRetainedVoxels,
    voxel,
    horizonSteps,
    horizonSeconds,
  ).map((point) => ({
    layerIndex: point.layerIndex,
    forecastSeconds: point.forecastSeconds,
    status: point.status,
    voxelId: point.voxelId,
    value: point.value,
  }));

  return {
    schemaVersion: "1.2.0",
    voxel,
    temporalFilter,
    trajectory,
    claimBoundary: {
      futureObservedFramesUsed: false,
      missingLayerSemantics: "not_retained_not_zero",
      calibratedProbability: false,
    },
  };
}

export function serializedVoxelFilename(voxel: VolumeVoxel): string {
  return `midfielders-eye-frame-${voxel.frameId}-${voxel.channel}-layer-${voxel.layerIndex}.json`;
}
