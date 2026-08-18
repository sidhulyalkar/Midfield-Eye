import { describe, expect, it } from "vitest";
import type { ActionOption, FrameState } from "../data/schemas";
import {
  buildAffordanceVolume,
  defaultVolumeConfig,
  INSTANCE_STRIDE,
} from "./affordanceVolume";
import { orbitViewProjection } from "./voxelRenderer";

const frame: FrameState = {
  sequence_id: "volume-test",
  frame_id: 10,
  timestamp_s: 1.2,
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
      vx: 1.4,
      vy: 0.2,
      body_angle: 0,
      tracking_status: "observed",
      metadata: {},
    },
    {
      player_id: "home-8",
      team: "home",
      x: 66,
      y: 29,
      vx: 2.1,
      vy: -0.4,
      tracking_status: "observed",
      metadata: {},
    },
    {
      player_id: "away-4",
      team: "away",
      x: 59,
      y: 34,
      vx: -1.2,
      vy: 0.1,
      tracking_status: "observed",
      metadata: {},
    },
    {
      player_id: "away-5",
      team: "away",
      x: 71,
      y: 25,
      vx: -0.8,
      vy: 0.6,
      tracking_status: "observed",
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

describe("buildAffordanceVolume", () => {
  it("keeps the field sparse, bounded, and GPU-instance aligned", () => {
    const scene = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("menu"),
      quality: "high",
      threshold: 0.05,
      maxVoxels: 120,
    });

    expect(scene.field.length % INSTANCE_STRIDE).toBe(0);
    expect(scene.solids.length % INSTANCE_STRIDE).toBe(0);
    expect(scene.stats.renderedVoxels).toBeLessThanOrEqual(120);
    expect(scene.stats.candidateVoxels).toBeGreaterThanOrEqual(
      scene.stats.renderedVoxels,
    );
    expect(scene.stats.horizonSteps).toBe(7);
    expect(scene.timeScaleMetres).toBeGreaterThan(0);
  });

  it("produces distinct scientific channels from the same focal state", () => {
    const pressure = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("pressure"),
      quality: "low",
      threshold: 0.08,
      maxVoxels: 400,
    });
    const corridors = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("passing_corridors"),
      quality: "low",
      threshold: 0.08,
      maxVoxels: 400,
    });

    expect(pressure.stats.renderedVoxels).toBeGreaterThan(0);
    expect(corridors.stats.renderedVoxels).toBeGreaterThan(0);
    expect(Array.from(pressure.field.slice(0, 40))).not.toEqual(
      Array.from(corridors.field.slice(0, 40)),
    );
  });

  it("can aggressively prune weak signal without inventing voxels", () => {
    const scene = buildAffordanceVolume(frame, options, {
      ...defaultVolumeConfig("uncertainty"),
      quality: "low",
      threshold: 0.99,
      maxVoxels: 100,
    });

    expect(scene.stats.renderedVoxels).toBe(0);
    expect(scene.field.length).toBe(0);
  });
});

describe("orbitViewProjection", () => {
  it("returns a finite deterministic camera matrix", () => {
    const camera = {
      azimuth: -0.7,
      elevation: 0.58,
      distance: 118,
      targetY: 5.5,
    };
    const first = orbitViewProjection(camera, 16 / 9);
    const second = orbitViewProjection(camera, 16 / 9);
    expect(first).toHaveLength(16);
    expect(Array.from(first).every(Number.isFinite)).toBe(true);
    expect(Array.from(first)).toEqual(Array.from(second));
  });
});
