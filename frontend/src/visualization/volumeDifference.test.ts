import { describe, expect, it } from "vitest";
import {
  INSTANCE_STRIDE,
  type VolumeChannel,
  type VolumeScene,
  type VolumeVoxel,
} from "./affordanceVolume";
import {
  buildVolumeDifference,
  comparisonCellKey,
  type VolumeDifferenceCondition,
} from "./volumeDifference";

const HORIZON_SECONDS = 0.5;
const HORIZON_STEPS = 3;
const GRID_X = 2;
const GRID_Y = 2;
const TIME_SCALE_METRES = 16;
const PITCH_LENGTH = 105;
const PITCH_WIDTH = 68;
const THRESHOLD = 0.2;

type ConditionContractOverrides = Partial<
  Pick<
    VolumeDifferenceCondition,
    "horizonSeconds" | "pitchLength" | "pitchWidth" | "threshold"
  >
>;

const incompatibleSceneCases: Array<
  [string, Partial<VolumeScene["stats"]>, RegExp]
> = [
  ["channel", { channel: "pressure" as VolumeChannel }, /same channel/u],
  ["grid x", { gridX: 3 }, /same gridX/u],
  ["grid y", { gridY: 3 }, /same gridY/u],
  ["horizon steps", { horizonSteps: 4 }, /same horizonSteps/u],
  ["voxel budget", { maxVoxels: 99 }, /same voxel budget/u],
];

function forecastSeconds(layerIndex: number) {
  return (layerIndex / (HORIZON_STEPS - 1)) * HORIZON_SECONDS;
}

function voxel(
  id: string,
  layerIndex: number,
  gridXIndex: number,
  gridYIndex: number,
  value: number,
  overrides: Partial<VolumeVoxel> = {},
): VolumeVoxel {
  const seconds = forecastSeconds(layerIndex);
  return {
    id,
    frameId: 10,
    channel: "menu",
    layerIndex,
    gridXIndex,
    gridYIndex,
    pitchX: 10 + gridXIndex * 5,
    pitchY: 8 + gridYIndex * 4,
    forecastSeconds: seconds,
    worldX: -40 + gridXIndex * 5,
    worldY: 0.7 + (layerIndex / (HORIZON_STEPS - 1)) * TIME_SCALE_METRES,
    worldZ: -25 + gridYIndex * 4,
    sizeX: 5,
    sizeY: 0.3,
    sizeZ: 4,
    value,
    signals: {
      menu: value,
      pressure: 0.1,
      pressure_shadow: 0.2,
      future_space: 0.3,
      passing_corridors: 0.4,
      option_creation: 0.5,
      visibility: 0.6,
      uncertainty: 0.1,
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
    ...overrides,
  };
}

function scene(
  voxels: VolumeVoxel[],
  overrides: Partial<VolumeScene["stats"]> = {},
): VolumeScene {
  const maxValue = voxels.reduce(
    (current, item) => Math.max(current, item.value),
    0,
  );
  const meanValue = voxels.length
    ? voxels.reduce((total, item) => total + item.value, 0) / voxels.length
    : 0;
  const channel = overrides.channel ?? "menu";
  return {
    field: new Float32Array(voxels.length * INSTANCE_STRIDE),
    solids: new Float32Array(),
    voxels,
    timeScaleMetres: TIME_SCALE_METRES,
    stats: {
      channel,
      gridX: GRID_X,
      gridY: GRID_Y,
      horizonSteps: HORIZON_STEPS,
      candidateVoxels: voxels.length,
      renderedVoxels: voxels.length,
      maxVoxels: 20,
      meanValue,
      maxValue,
      ...overrides,
    },
  };
}

function condition(
  id: string,
  voxels: VolumeVoxel[],
  sceneOverrides: Partial<VolumeScene["stats"]> = {},
  contractOverrides: ConditionContractOverrides = {},
): VolumeDifferenceCondition {
  return {
    id,
    retentionScope: "full_retained_scene",
    scene: scene(voxels, sceneOverrides),
    horizonSeconds: HORIZON_SECONDS,
    pitchLength: PITCH_LENGTH,
    pitchWidth: PITCH_WIDTH,
    threshold: THRESHOLD,
    ...contractOverrides,
  };
}

describe("v1.3 evidence-aware difference support", () => {
  it("computes B - A only on retained intersections and preserves one-sided absence", () => {
    const sharedA = voxel("a-shared", 0, 0, 0, 0.2);
    const leftOnly = voxel("a-only", 1, 1, 0, 0.4);
    const sharedB = voxel("b-shared", 0, 0, 0, 0.55, { frameId: 11 });
    const rightOnly = voxel("b-only", 2, 1, 1, 0.8, { frameId: 11 });

    const difference = buildVolumeDifference(
      condition("baseline", [leftOnly, sharedA]),
      condition("counterfactual", [rightOnly, sharedB]),
    );

    expect(difference.conditionAId).toBe("baseline");
    expect(difference.conditionBId).toBe("counterfactual");
    expect(difference.signConvention).toBe("condition_b_minus_condition_a");
    expect(difference.cells.map((cell) => cell.key)).toEqual([
      "0:0:0",
      "1:1:0",
      "2:1:1",
    ]);

    const intersection = difference.cells[0];
    const onlyA = difference.cells[1];
    const onlyB = difference.cells[2];
    expect(intersection?.support).toBe("intersection");
    expect(intersection?.left).toBe(sharedA);
    expect(intersection?.right).toBe(sharedB);
    expect(intersection?.delta).toBeCloseTo(0.35);
    expect(onlyA?.support).toBe("left_only");
    expect(onlyA?.left).toBe(leftOnly);
    expect(onlyA?.right).toBeNull();
    expect(onlyA?.delta).toBeNull();
    expect(onlyB?.support).toBe("right_only");
    expect(onlyB?.left).toBeNull();
    expect(onlyB?.right).toBe(rightOnly);
    expect(onlyB?.delta).toBeNull();

    expect(difference.summary).toEqual({
      intersection: 1,
      leftOnly: 1,
      rightOnly: 1,
      neither: 9,
      retainedUnion: 3,
      totalCanonicalCells: 12,
    });
  });

  it("orders canonical cells by integer layer, grid x, then grid y", () => {
    const difference = buildVolumeDifference(
      condition("a", [
        voxel("a-2", 2, 1, 0, 0.6),
        voxel("a-0b", 0, 1, 1, 0.5),
        voxel("a-0a", 0, 0, 1, 0.4),
      ]),
      condition("b", []),
    );

    expect(difference.cells.map((cell) => cell.key)).toEqual([
      "0:0:1",
      "0:1:1",
      "2:1:0",
    ]);
    expect(comparisonCellKey(2, 1, 0)).toBe("2:1:0");
    expect(() => comparisonCellKey(0.5, 1, 0)).toThrow(
      /non-negative integers/u,
    );
  });

  it("fails closed on duplicate canonical cells rather than choosing one silently", () => {
    expect(() =>
      buildVolumeDifference(
        condition("a", [
          voxel("duplicate-a", 1, 0, 0, 0.2),
          voxel("duplicate-b", 1, 0, 0, 0.7),
        ]),
        condition("b", []),
      ),
    ).toThrow(/duplicate canonical comparison cell 1:0:0/u);
  });

  it("rejects a retained voxel whose timestamp disagrees with its integer layer", () => {
    const malformed = voxel("bad-time", 1, 0, 0, 0.5, {
      forecastSeconds: 0.3,
    });
    expect(() =>
      buildVolumeDifference(
        condition("a", [malformed]),
        condition("b", []),
      ),
    ).toThrow(/expected 0.25 for layer 1/u);
  });

  it("rejects disjoint sparse scenes when their horizon contracts differ", () => {
    expect(() =>
      buildVolumeDifference(
        condition("a", [voxel("a", 0, 0, 0, 0.2)]),
        condition(
          "b",
          [voxel("b", 2, 1, 1, 0.8)],
          {},
          { horizonSeconds: 0.75 },
        ),
      ),
    ).toThrow(/same horizonSeconds/u);
  });

  it("rejects pitch or threshold mismatches even when sparse supports do not overlap", () => {
    expect(() =>
      buildVolumeDifference(
        condition("a", [voxel("a", 0, 0, 0, 0.2)]),
        condition(
          "b",
          [voxel("b", 2, 1, 1, 0.8)],
          {},
          { pitchLength: 100 },
        ),
      ),
    ).toThrow(/same pitchLength/u);

    expect(() =>
      buildVolumeDifference(
        condition("a", []),
        condition("b", [], {}, { threshold: 0.35 }),
      ),
    ).toThrow(/same retention threshold/u);
  });

  it.each(incompatibleSceneCases)(
    "rejects incompatible %s contracts",
    (_label, rightOverrides, message) => {
      expect(() =>
        buildVolumeDifference(
          condition("a", []),
          condition("b", [], rightOverrides),
        ),
      ).toThrow(message);
    },
  );

  it("rejects a mismatched temporal render scale", () => {
    const left = condition("a", []);
    const right = condition("b", []);
    right.scene.timeScaleMetres = 17;
    expect(() => buildVolumeDifference(left, right)).toThrow(
      /same temporal render scale/u,
    );
  });

  it("rejects incompatible intersection geometry instead of calculating a false delta", () => {
    const left = voxel("a", 1, 1, 1, 0.3);
    const right = voxel("b", 1, 1, 1, 0.6, {
      frameId: 11,
      pitchX: left.pitchX + 0.05,
    });
    expect(() =>
      buildVolumeDifference(
        condition("a", [left]),
        condition("b", [right]),
      ),
    ).toThrow(/incompatible pitchX/u);
  });

  it("rejects malformed retained scene metadata and GPU/forensic misalignment", () => {
    const badCount = condition("a", [voxel("a", 0, 0, 0, 0.4)]);
    badCount.scene.stats.renderedVoxels = 0;
    expect(() => buildVolumeDifference(badCount, condition("b", []))).toThrow(
      /does not match retained voxel count/u,
    );

    const badBuffer = condition("a", [voxel("a", 0, 0, 0, 0.4)]);
    badBuffer.scene.field = new Float32Array(INSTANCE_STRIDE - 1);
    expect(() => buildVolumeDifference(badBuffer, condition("b", []))).toThrow(
      /field buffer is not index-aligned/u,
    );
  });

  it("rejects malformed condition metadata and malformed retained voxels", () => {
    expect(() =>
      buildVolumeDifference(condition("", []), condition("b", [])),
    ).toThrow(/non-empty id/u);

    expect(() =>
      buildVolumeDifference(
        condition("a", [], {}, { threshold: 1.5 }),
        condition("b", []),
      ),
    ).toThrow(/invalid threshold/u);

    expect(() =>
      buildVolumeDifference(
        condition("a", [voxel("outside-grid", 1, 2, 0, 0.4)]),
        condition("b", []),
      ),
    ).toThrow(/out-of-range voxel/u);

    expect(() =>
      buildVolumeDifference(
        condition("a", [voxel("below-threshold", 1, 1, 1, 0.1)]),
        condition("b", []),
      ),
    ).toThrow(/below retention threshold/u);

    expect(() =>
      buildVolumeDifference(
        condition("a", [
          voxel("outside-pitch", 1, 1, 1, 0.4, { pitchX: 106 }),
        ]),
        condition("b", []),
      ),
    ).toThrow(/outside the declared pitch/u);
  });
});
