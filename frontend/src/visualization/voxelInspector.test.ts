import { describe, expect, it } from "vitest";
import type { ActionOption, FrameState } from "../data/schemas";
import {
  buildAffordanceVolume,
  defaultVolumeConfig,
  INSTANCE_STRIDE,
} from "./affordanceVolume";
import {
  pickVolumeVoxel,
  projectVoxelToScreen,
  strongestVisibleVoxel,
} from "./voxelInspector";

const frame: FrameState = {
  sequence_id: "inspector-test",
  frame_id: 42,
  timestamp_s: 2.4,
  possession_team: "home",
  ball_x: 52,
  ball_y: 34,
  ball_carrier_id: "home-6",
  pitch_length: 105,
  pitch_width: 68,
  source_provider: "synthetic",
  quality_flags: [],
  state_version: "0.5",
  metadata: {},
  players: [
    {
      player_id: "home-6",
      team: "home",
      x: 52,
      y: 34,
      vx: 1.2,
      vy: 0.1,
      body_angle: 0,
      tracking_status: "observed",
      metadata: {},
    },
    {
      player_id: "home-8",
      team: "home",
      x: 66,
      y: 29,
      vx: 2,
      vy: -0.3,
      tracking_status: "observed",
      metadata: {},
    },
    {
      player_id: "away-4",
      team: "away",
      x: 59,
      y: 34,
      vx: -1,
      vy: 0,
      confidence: 0.82,
      position_covariance: [
        [0.36, 0],
        [0, 0.25],
      ],
      tracking_status: "observed",
      metadata: {},
    },
    {
      player_id: "away-5",
      team: "away",
      x: 71,
      y: 25,
      vx: -0.7,
      vy: 0.5,
      tracking_status: "interpolated",
      metadata: {},
    },
  ],
};

const options: ActionOption[] = [
  {
    sequence_id: frame.sequence_id,
    frame_id: frame.frame_id,
    option_id: "pass:home-8",
    kind: "pass",
    actor_id: "home-6",
    target_player_id: "home-8",
    target_x: 66,
    target_y: 29,
    features: {},
    geometric_score: 0.86,
    provenance: "test",
  },
];

const camera = {
  azimuth: -0.72,
  elevation: 0.58,
  distance: 118,
  targetY: 5.5,
};

describe("voxel inspector metadata", () => {
  it("keeps one forensic record aligned with every retained GPU instance", () => {
    const scene = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("menu"),
      quality: "low",
      threshold: 0.05,
      maxVoxels: 180,
    });

    expect(scene.voxels).toHaveLength(scene.stats.renderedVoxels);
    expect(scene.field.length).toBe(scene.voxels.length * INSTANCE_STRIDE);
    expect(scene.voxels.length).toBeGreaterThan(0);

    const voxel = scene.voxels[0];
    expect(voxel).toBeDefined();
    if (!voxel) return;
    expect(voxel.value).toBeCloseTo(voxel.signals.menu);
    expect(voxel.forecastSeconds).toBeGreaterThanOrEqual(0);
    expect(voxel.forecastSeconds).toBeLessThanOrEqual(1.5);
    expect(voxel.evidence.forecast).toBe("focal_state_kinematics");
    expect(voxel.evidence.futureObservedFramesUsed).toBe(false);
    expect(voxel.evidence.visibility).toBe("orientation_proxy");
    expect(voxel.evidence.uncertainty).toBe("covariance_confidence_tracking");
  });

  it("preserves local candidate contributions instead of only the final glow", () => {
    const scene = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("passing_corridors"),
      quality: "low",
      threshold: 0.01,
      maxVoxels: 800,
    });
    const contributingVoxel = scene.voxels.find((voxel) =>
      voxel.optionContributions.some(
        (contribution) => contribution.optionId === "pass:home-8",
      ),
    );

    expect(contributingVoxel).toBeDefined();
    const contribution = contributingVoxel?.optionContributions.find(
      (item) => item.optionId === "pass:home-8",
    );
    expect(contribution?.localContribution).toBeGreaterThan(0);
    expect(contribution?.geometricScore).toBeCloseTo(0.86);
  });

  it("distinguishes a focal visibility polygon from an orientation proxy", () => {
    const polygonFrame: FrameState = {
      ...frame,
      visibility_polygon: [
        [45, 20],
        [90, 20],
        [90, 50],
        [45, 50],
      ],
    };
    const scene = buildAffordanceVolume(polygonFrame, options, {
      ...defaultVolumeConfig("visibility"),
      quality: "low",
      threshold: 0.05,
      maxVoxels: 100,
    });

    expect(scene.voxels[0]?.evidence.visibility).toBe("visibility_polygon");
  });
});

describe("deterministic screen-space voxel picking", () => {
  it("round-trips a projected voxel center back to the same forensic cell", () => {
    const scene = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("menu"),
      quality: "low",
      threshold: 0.05,
      maxVoxels: 300,
    });
    const projected = strongestVisibleVoxel(scene.voxels, camera, 1200, 700);
    expect(projected).not.toBeNull();
    if (!projected) return;

    const picked = pickVolumeVoxel(
      scene.voxels,
      camera,
      1200,
      700,
      projected.screenX,
      projected.screenY,
    );
    expect(picked?.voxel.id).toBe(projected.voxel.id);
    expect(picked?.distancePx).toBeCloseTo(0);
  });

  it("projects the same cell deterministically and rejects empty screen space", () => {
    const scene = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("pressure"),
      quality: "low",
      threshold: 0.08,
      maxVoxels: 120,
    });
    const voxel = scene.voxels[0];
    expect(voxel).toBeDefined();
    if (!voxel) return;

    const first = projectVoxelToScreen(voxel, camera, 1000, 600);
    const second = projectVoxelToScreen(voxel, camera, 1000, 600);
    expect(first?.screenX).toBeCloseTo(second?.screenX ?? 0);
    expect(first?.screenY).toBeCloseTo(second?.screenY ?? 0);
    expect(
      pickVolumeVoxel(scene.voxels, camera, 1000, 600, -500, -500),
    ).toBeNull();
  });
});
