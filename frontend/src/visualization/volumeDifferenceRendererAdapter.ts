import type { VolumeScene } from "./affordanceVolume";
import type { AdaptiveVoxelRenderer } from "./voxelRenderer";

export type DifferenceRenderArrays = {
  solids: Float32Array;
  field: Float32Array;
};

export function updateDifferenceRenderer(
  renderer: Pick<AdaptiveVoxelRenderer, "update">,
  arrays: DifferenceRenderArrays,
) {
  // The current renderer backends read only `solids` and `field` from the
  // structural scene passed to update(). Keep this cast quarantined here so
  // comparison metadata never needs to masquerade as ordinary VolumeVoxel data.
  renderer.update(arrays as VolumeScene);
}
