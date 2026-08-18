import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { VolumeVoxel } from "./affordanceVolume";
import { LinkedTemporalSlice } from "./LinkedTemporalSlice";

function voxel(id: string, value: number, x: number): VolumeVoxel {
  return {
    id,
    frameId: 2,
    channel: "menu",
    layerIndex: 2,
    gridXIndex: x,
    gridYIndex: 4,
    pitchX: 40 + x,
    pitchY: 24,
    forecastSeconds: 0.5,
    worldX: 0,
    worldY: 5,
    worldZ: 0,
    sizeX: 2,
    sizeY: 0.2,
    sizeZ: 2,
    value,
    signals: {
      menu: value,
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

describe("linked temporal slice", () => {
  it("renders exact retained ids/values and selects by the same stable id", () => {
    const first = voxel("frame:menu:2:3:4", 0.812345, 3);
    const second = voxel("frame:menu:2:5:4", 0.612345, 5);
    const onSelectVoxel = vi.fn();
    const { container } = render(
      <LinkedTemporalSlice
        voxels={[first, second]}
        pitchLength={105}
        pitchWidth={68}
        layerIndex={2}
        forecastSeconds={0.5}
        selectedVoxelId={second.id}
        onSelectVoxel={onSelectVoxel}
      />,
    );

    const firstCell = container.querySelector(`[data-voxel-id="${first.id}"]`);
    const secondCell = container.querySelector(
      `[data-voxel-id="${second.id}"]`,
    );
    expect(firstCell).toHaveAttribute("data-voxel-value", "0.812345");
    expect(secondCell).toHaveAttribute("data-voxel-value", "0.612345");
    expect(secondCell).toHaveClass("is-selected");

    fireEvent.click(firstCell!);
    expect(onSelectVoxel).toHaveBeenCalledWith(first.id);
    expect(screen.getByText(/not a separately computed heatmap/u)).toBeVisible();
  });
});
