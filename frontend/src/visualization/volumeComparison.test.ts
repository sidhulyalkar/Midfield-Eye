import { describe, expect, it } from "vitest";
import type { FrameState, PlayerState } from "../data/schemas";
import { buildVolumeComparison } from "./volumeComparison";

function player(
  playerId: string,
  team: "home" | "away",
  x: number,
  y: number,
  vx: number,
  vy: number,
): PlayerState {
  return {
    player_id: playerId,
    team,
    x,
    y,
    vx,
    vy,
    tracking_status: "observed",
    metadata: {},
  };
}

function frame(): FrameState {
  return {
    sequence_id: "compare",
    frame_id: 9,
    timestamp_s: 2.25,
    possession_team: "home",
    ball_x: 35,
    ball_y: 28,
    ball_carrier_id: "carrier",
    players: [
      player("carrier", "home", 35, 28, 0.4, 0.1),
      player("runner", "home", 48, 30, 2, 0.4),
      player("support", "home", 43, 40, 0.5, -0.2),
      player("def-a", "away", 54, 30, -0.2, 0),
      player("def-b", "away", 58, 40, -0.4, -0.1),
    ],
    pitch_length: 105,
    pitch_width: 68,
    source_provider: "synthetic",
    quality_flags: [],
    state_version: "test",
    metadata: {},
  };
}

describe("matched state-derived volume comparison", () => {
  it.each(["future_space", "option_creation"] as const)(
    "builds %s from the same deterministic lattice without candidate options",
    (channel) => {
      const baseline = frame();
      const bundle = buildVolumeComparison(baseline, {
        channel,
        quality: "low",
        threshold: 0.05,
        horizonSeconds: 1.5,
        maxVoxels: 5000,
        leadSeconds: 0.75,
      });

      expect(bundle).not.toBeNull();
      expect(bundle?.intervention.playerId).toBe("runner");
      expect(bundle?.intervention.baselineFrame).toBe(baseline);
      expect(bundle?.baselineScene.stats.channel).toBe(channel);
      expect(bundle?.alternativeScene.stats.channel).toBe(channel);
      expect(bundle?.baselineScene.stats.gridX).toBe(
        bundle?.alternativeScene.stats.gridX,
      );
      expect(bundle?.baselineScene.stats.gridY).toBe(
        bundle?.alternativeScene.stats.gridY,
      );
      expect(bundle?.baselineScene.stats.horizonSteps).toBe(
        bundle?.alternativeScene.stats.horizonSteps,
      );
      expect(bundle?.baselineScene.stats.maxVoxels).toBe(5000);
      expect(bundle?.alternativeScene.stats.maxVoxels).toBe(5000);
      expect(bundle?.difference.signConvention).toBe(
        "condition_b_minus_condition_a",
      );
      expect(bundle?.difference.conditionAId).toBe("baseline");
      expect(bundle?.difference.conditionBId).toBe(
        bundle?.intervention.id,
      );

      for (const voxel of bundle?.baselineScene.voxels ?? []) {
        expect(voxel.optionContributions).toEqual([]);
      }
      for (const voxel of bundle?.alternativeScene.voxels ?? []) {
        expect(voxel.optionContributions).toEqual([]);
      }
    },
  );

  it("fails closed when the focal frame has no eligible off-ball motion", () => {
    const input = frame();
    input.players = input.players.map((candidate) =>
      candidate.team === "home" && candidate.player_id !== "carrier"
        ? { ...candidate, vx: 0, vy: 0 }
        : candidate,
    );
    expect(
      buildVolumeComparison(input, {
        channel: "future_space",
        quality: "low",
        threshold: 0.2,
        horizonSeconds: 1.5,
        maxVoxels: 1200,
        leadSeconds: 0.75,
      }),
    ).toBeNull();
  });
});
