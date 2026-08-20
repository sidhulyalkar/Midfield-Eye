import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { VolumeVoxel } from "./affordanceVolume";
import type { VolumeDifferenceCell } from "./volumeDifference";
import type { VolumeDifferenceRenderCell } from "./volumeDifferenceRender";
import { LinkedDifferenceSlice } from "./LinkedDifferenceSlice";

function voxel(id: string, value: number, x: number): VolumeVoxel {
  return {
    id,
    frameId: 1,
    channel: "future_space",
    layerIndex: 2,
    gridXIndex: x,
    gridYIndex: 1,
    pitchX: 30 + x * 4,
    pitchY: 20,
    forecastSeconds: 0.5,
    worldX: 0,
    worldY: 5,
    worldZ: 0,
    sizeX: 4,
    sizeY: 0.3,
    sizeZ: 3,
    value,
    signals: {
      menu: 0,
      pressure: 0,
      pressure_shadow: 0,
      future_space: value,
      passing_corridors: 0,
      option_creation: 0,
      visibility: 1,
      uncertainty: 0,
    },
    optionContributions: [],
    nearestDefender: null,
    nearestTeammate: null,
    evidence: {
      forecast: "focal_state_kinematics",
      sourceProvider: "test",
      visibility: "unknown",
      uncertainty: "tracking_status_only",
      futureObservedFramesUsed: false,
    },
  };
}

function renderCell(
  comparison: VolumeDifferenceCell,
  glyph: VolumeDifferenceRenderCell["glyph"],
): VolumeDifferenceRenderCell {
  const source = comparison.left ?? comparison.right!;
  return {
    key: comparison.key,
    support: comparison.support,
    glyph,
    comparison,
    worldX: source.worldX,
    worldY: source.worldY,
    worldZ: source.worldZ,
    sizeX: source.sizeX,
    sizeY: source.sizeY,
    sizeZ: source.sizeZ,
    signedDelta: comparison.delta,
    absoluteDelta:
      comparison.delta === null ? null : Math.abs(comparison.delta),
    instanceStart: 0,
    instanceCount: comparison.support === "intersection" ? 1 : 2,
  };
}

describe("linked difference slice", () => {
  it("renders shared support and orthogonal one-sided support with exact keys", () => {
    const sharedA = voxel("a", 0.3, 1);
    const sharedB = voxel("b", 0.7, 1);
    const aOnly = voxel("a-only", 0.6, 2);
    const bOnly = voxel("b-only", 0.8, 3);
    const cells = [
      renderCell(
        {
          key: "2:1:1",
          layerIndex: 2,
          gridXIndex: 1,
          gridYIndex: 1,
          support: "intersection",
          left: sharedA,
          right: sharedB,
          delta: 0.4,
        },
        "intersection_cell",
      ),
      renderCell(
        {
          key: "2:2:1",
          layerIndex: 2,
          gridXIndex: 2,
          gridYIndex: 1,
          support: "left_only",
          left: aOnly,
          right: null,
          delta: null,
        },
        "left_parallel_rails",
      ),
      renderCell(
        {
          key: "2:3:1",
          layerIndex: 2,
          gridXIndex: 3,
          gridYIndex: 1,
          support: "right_only",
          left: null,
          right: bOnly,
          delta: null,
        },
        "right_parallel_rails",
      ),
    ];
    const onSelectKey = vi.fn();
    const { container } = render(
      <LinkedDifferenceSlice
        cells={cells}
        pitchLength={105}
        pitchWidth={68}
        layerIndex={2}
        forecastSeconds={0.5}
        selectedKey="2:2:1"
        onSelectKey={onSelectKey}
      />,
    );

    expect(container.querySelector('[data-comparison-key="2:1:1"]')).toHaveAttribute(
      "data-support",
      "intersection",
    );
    expect(container.querySelector('[data-comparison-key="2:2:1"]')).toHaveAttribute(
      "data-support",
      "left_only",
    );
    expect(container.querySelector('[data-comparison-key="2:3:1"]')).toHaveAttribute(
      "data-support",
      "right_only",
    );
    expect(container.querySelectorAll('[tabindex="0"]')).toHaveLength(1);
    expect(container.querySelector('[data-comparison-key="2:2:1"]')).toHaveAttribute(
      "tabindex",
      "0",
    );

    fireEvent.click(container.querySelector('[data-comparison-key="2:3:1"]')!);
    expect(onSelectKey).toHaveBeenCalledWith("2:3:1");
  });
});
