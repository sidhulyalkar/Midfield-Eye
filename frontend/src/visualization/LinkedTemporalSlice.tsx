import type { VolumeVoxel } from "./affordanceVolume";

export type LinkedTemporalSliceProps = {
  voxels: readonly VolumeVoxel[];
  pitchLength: number;
  pitchWidth: number;
  layerIndex: number;
  forecastSeconds: number;
  selectedVoxelId: string | null;
  onSelectVoxel: (voxelId: string) => void;
};

export function LinkedTemporalSlice({
  voxels,
  pitchLength,
  pitchWidth,
  layerIndex,
  forecastSeconds,
  selectedVoxelId,
  onSelectVoxel,
}: LinkedTemporalSliceProps) {
  const selectedIsVisible =
    selectedVoxelId !== null &&
    voxels.some((voxel) => voxel.id === selectedVoxelId);
  const keyboardAnchorId = selectedIsVisible
    ? selectedVoxelId
    : (voxels[0]?.id ?? null);

  return (
    <section
      className="linked-temporal-slice"
      data-testid="linked-temporal-slice"
      aria-label={`Linked top-down retained voxel slice at +${forecastSeconds.toFixed(2)} seconds`}
    >
      <header>
        <div>
          <span>LINKED TOP-DOWN SLICE</span>
          <strong>
            Layer {layerIndex} · +{forecastSeconds.toFixed(2)} s
          </strong>
        </div>
        <p>
          {voxels.length.toLocaleString()} retained cells · identical IDs and
          values
        </p>
      </header>
      <svg
        viewBox={`0 0 ${pitchLength} ${pitchWidth}`}
        role="img"
        aria-label="Top-down pitch slice using the same retained voxels as the 3D volume"
      >
        <rect
          className="linked-slice-pitch"
          x={0}
          y={0}
          width={pitchLength}
          height={pitchWidth}
        />
        <line
          x1={pitchLength / 2}
          y1={0}
          x2={pitchLength / 2}
          y2={pitchWidth}
        />
        <circle
          cx={pitchLength / 2}
          cy={pitchWidth / 2}
          r={9.15}
          className="linked-slice-centre"
        />
        {voxels.map((voxel) => (
          <rect
            key={voxel.id}
            className={`linked-slice-voxel ${voxel.id === selectedVoxelId ? "is-selected" : ""}`}
            data-voxel-id={voxel.id}
            data-voxel-value={voxel.value.toFixed(6)}
            x={voxel.pitchX - voxel.sizeX / 2}
            y={voxel.pitchY - voxel.sizeZ / 2}
            width={Math.max(0.25, voxel.sizeX)}
            height={Math.max(0.25, voxel.sizeZ)}
            opacity={Math.max(0.2, Math.min(0.92, voxel.value))}
            role="button"
            tabIndex={voxel.id === keyboardAnchorId ? 0 : -1}
            aria-label={`Inspect voxel ${voxel.id}, value ${voxel.value.toFixed(3)}`}
            onClick={() => onSelectVoxel(voxel.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectVoxel(voxel.id);
              }
            }}
          />
        ))}
      </svg>
      <p>
        This is a second view of the filtered retained array, not a separately
        computed heatmap. Missing cells remain absent rather than becoming zero.
      </p>
    </section>
  );
}
