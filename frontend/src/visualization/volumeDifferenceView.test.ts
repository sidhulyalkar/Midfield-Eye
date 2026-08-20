import { describe, expect, it } from "vitest";
import type { VolumeDifferenceCell } from "./volumeDifference";
import { filterVolumeDifferenceCells } from "./volumeDifferenceView";

function cell(layerIndex: number, gridXIndex: number): VolumeDifferenceCell {
  return {
    key: `${layerIndex}:${gridXIndex}:0`,
    layerIndex,
    gridXIndex,
    gridYIndex: 0,
    support: "left_only",
    left: null as never,
    right: null,
    delta: null,
  };
}

describe("difference temporal views", () => {
  const cells = [cell(0, 0), cell(1, 0), cell(2, 0), cell(4, 0), cell(6, 0)];

  it("keeps the original comparison-cell objects in full mode", () => {
    const visible = filterVolumeDifferenceCells(cells, { mode: "full" }, 7);
    expect(visible).toEqual(cells);
    expect(visible[2]).toBe(cells[2]);
  });

  it("filters by integer slice membership without interpolation", () => {
    const visible = filterVolumeDifferenceCells(
      cells,
      { mode: "slice", layerIndex: 2 },
      7,
    );
    expect(visible).toHaveLength(1);
    expect(visible[0]).toBe(cells[2]);
  });

  it("uses inclusive integer bands", () => {
    const visible = filterVolumeDifferenceCells(
      cells,
      { mode: "band", startLayerIndex: 1, endLayerIndex: 4 },
      7,
    );
    expect(visible.map((item) => item.layerIndex)).toEqual([1, 2, 4]);
  });
});
