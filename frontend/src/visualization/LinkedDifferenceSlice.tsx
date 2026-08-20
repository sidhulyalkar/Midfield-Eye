import type { KeyboardEvent } from "react";
import type { VolumeDifferenceRenderCell } from "./volumeDifferenceRender";

export type LinkedDifferenceSliceProps = {
  cells: readonly VolumeDifferenceRenderCell[];
  pitchLength: number;
  pitchWidth: number;
  layerIndex: number;
  forecastSeconds: number;
  selectedKey: string | null;
  onSelectKey: (key: string) => void;
};

function representative(cell: VolumeDifferenceRenderCell) {
  return cell.comparison.left ?? cell.comparison.right;
}

function cellLabel(cell: VolumeDifferenceRenderCell) {
  if (cell.support === "intersection") {
    const delta = cell.signedDelta ?? 0;
    return `${cell.key}, retained in both conditions, B minus A ${delta >= 0 ? "+" : ""}${delta.toFixed(3)}`;
  }
  return `${cell.key}, retained only in condition ${cell.support === "left_only" ? "A" : "B"}, no numerical difference`;
}

export function LinkedDifferenceSlice({
  cells,
  pitchLength,
  pitchWidth,
  layerIndex,
  forecastSeconds,
  selectedKey,
  onSelectKey,
}: LinkedDifferenceSliceProps) {
  const selectedVisible =
    selectedKey !== null && cells.some((cell) => cell.key === selectedKey);
  const keyboardAnchor = selectedVisible ? selectedKey : (cells[0]?.key ?? null);

  return (
    <section className="linked-difference-slice" data-testid="linked-difference-slice">
      <header>
        <div>
          <span>LINKED DIFFERENCE SLICE</span>
          <strong>
            Layer {layerIndex} · +{forecastSeconds.toFixed(2)} s
          </strong>
        </div>
        <p>{cells.length.toLocaleString()} retained-union cells</p>
      </header>
      <svg
        viewBox={`0 0 ${pitchLength} ${pitchWidth}`}
        role="img"
        aria-label={`Top-down evidence-aware difference slice at +${forecastSeconds.toFixed(2)} seconds`}
      >
        <rect
          className="difference-slice-pitch"
          x={0}
          y={0}
          width={pitchLength}
          height={pitchWidth}
        />
        <line
          className="difference-slice-line"
          x1={pitchLength / 2}
          y1={0}
          x2={pitchLength / 2}
          y2={pitchWidth}
        />
        <circle
          className="difference-slice-line"
          cx={pitchLength / 2}
          cy={pitchWidth / 2}
          r={9.15}
        />
        {cells.map((cell) => {
          const voxel = representative(cell);
          if (!voxel) return null;
          const x = voxel.pitchX - voxel.sizeX / 2;
          const y = voxel.pitchY - voxel.sizeZ / 2;
          const selected = cell.key === selectedKey;
          const tabIndex = cell.key === keyboardAnchor ? 0 : -1;
          const label = cellLabel(cell);

          if (cell.support === "intersection") {
            const delta = cell.signedDelta ?? 0;
            const magnitude = Math.abs(delta);
            return (
              <rect
                key={cell.key}
                role="button"
                tabIndex={tabIndex}
                aria-label={label}
                data-comparison-key={cell.key}
                data-support={cell.support}
                className={`difference-slice-intersection ${delta > 0 ? "is-positive" : delta < 0 ? "is-negative" : "is-neutral"} ${selected ? "is-selected" : ""}`}
                x={x + voxel.sizeX * 0.09}
                y={y + voxel.sizeZ * 0.09}
                width={voxel.sizeX * 0.82}
                height={voxel.sizeZ * 0.82}
                opacity={0.24 + 0.68 * Math.sqrt(Math.min(1, magnitude))}
                onClick={() => onSelectKey(cell.key)}
                onKeyDown={(event: KeyboardEvent<SVGRectElement>) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectKey(cell.key);
                  }
                }}
              />
            );
          }

          const railThickness = Math.max(
            0.16,
            Math.min(voxel.sizeX, voxel.sizeZ) * 0.13,
          );
          return (
            <g
              key={cell.key}
              role="button"
              tabIndex={tabIndex}
              aria-label={label}
              data-comparison-key={cell.key}
              data-support={cell.support}
              className={`difference-slice-one-sided ${cell.support === "left_only" ? "is-left-only" : "is-right-only"} ${selected ? "is-selected" : ""}`}
              onClick={() => onSelectKey(cell.key)}
              onKeyDown={(event: KeyboardEvent<SVGGElement>) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectKey(cell.key);
                }
              }}
            >
              {cell.support === "left_only" ? (
                <>
                  <rect
                    x={
                      voxel.pitchX -
                      voxel.sizeX * 0.28 -
                      railThickness / 2
                    }
                    y={y + voxel.sizeZ * 0.08}
                    width={railThickness}
                    height={voxel.sizeZ * 0.84}
                  />
                  <rect
                    x={
                      voxel.pitchX +
                      voxel.sizeX * 0.28 -
                      railThickness / 2
                    }
                    y={y + voxel.sizeZ * 0.08}
                    width={railThickness}
                    height={voxel.sizeZ * 0.84}
                  />
                </>
              ) : (
                <>
                  <rect
                    x={x + voxel.sizeX * 0.08}
                    y={
                      voxel.pitchY -
                      voxel.sizeZ * 0.28 -
                      railThickness / 2
                    }
                    width={voxel.sizeX * 0.84}
                    height={railThickness}
                  />
                  <rect
                    x={x + voxel.sizeX * 0.08}
                    y={
                      voxel.pitchY +
                      voxel.sizeZ * 0.28 -
                      railThickness / 2
                    }
                    width={voxel.sizeX * 0.84}
                    height={railThickness}
                  />
                </>
              )}
            </g>
          );
        })}
      </svg>
      <p>
        Filled cells support a numerical B−A difference. Parallel rails mark
        one-sided retained evidence and are never treated as zero.
      </p>
    </section>
  );
}
