import { describe, expect, it, vi } from "vitest";
import type { CounterfactualOptionsArtifact } from "../data/counterfactualOptionsSchemas";
import type { ActionOption, FrameState, PlayerState } from "../data/schemas";

const conditionAOption: ActionOption = {
  sequence_id: "compare",
  frame_id: 9,
  option_id: "a-pass",
  kind: "pass",
  actor_id: "carrier",
  target_player_id: "runner",
  target_x: 48,
  target_y: 30,
  features: { distance: 13.15 },
  geometric_score: 0.55,
  learned_score: null,
  source_provider: "synthetic",
  provenance: "test",
  label_available: null,
  label_visible: null,
  label_selected: null,
  label_value: null,
  failure_reason: null,
};

const conditionBOption: ActionOption = {
  ...conditionAOption,
  option_id: "b-pass",
  target_x: 49.5,
  target_y: 30.3,
  features: { distance: 14.68 },
  geometric_score: 0.72,
};

vi.mock("./volumeCounterfactualCandidates", () => ({
  resolveRegeneratedCandidateEvidence: () => ({
    mode: "regenerated_counterfactual_candidates",
    candidateOptionsIncluded: true,
    candidateOptionsRegenerated: true,
    conditionAOptions: [conditionAOption],
    conditionBOptions: [conditionBOption],
    comparisons: [
      {
        comparison_option_key: "pass:runner",
        support: "intersection",
        left_option_id: "a-pass",
        right_option_id: "b-pass",
        geometric_score_delta: 0.17,
      },
    ],
    supportSummary: { intersection: 1, leftOnly: 0, rightOnly: 0, union: 1 },
    provenance: {
      schemaVersion: "1.4.0-b",
      generatorName: "AffordanceEngine",
      generatorModule: "midfielders_eye.affordance",
      packageVersion: "1.4.0",
      configSha256: "a".repeat(64),
      candidateIdentityContract: "semantic_action_candidate_v1",
      interventionContract: "earlier_run_focal_velocity_v1",
      futureObservedFramesUsed: false,
    },
  }),
}));

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

const artifact = {} as CounterfactualOptionsArtifact;

describe("v1.4 regenerated menu volume wiring", () => {
  it.each(["passing_corridors", "menu"] as const)(
    "feeds distinct authoritative A/B candidate tables into %s",
    (channel) => {
      const bundle = buildVolumeComparison(frame(), {
        channel,
        quality: "low",
        threshold: 0.01,
        horizonSeconds: 1.5,
        maxVoxels: 5000,
        leadSeconds: 0.75,
        currentScenarioOptions: [conditionAOption],
        counterfactualArtifact: artifact,
      });
      expect(bundle).not.toBeNull();
      expect(bundle?.candidateEvidence).toMatchObject({
        mode: "regenerated_counterfactual_candidates",
        candidateOptionsIncluded: true,
        candidateOptionsRegenerated: true,
      });
      expect(bundle?.baselineScene.stats.channel).toBe(channel);
      expect(bundle?.alternativeScene.stats.channel).toBe(channel);
      expect(
        bundle?.baselineScene.voxels.some((voxel) =>
          voxel.optionContributions.some((item) => item.optionId === "a-pass"),
        ),
      ).toBe(true);
      expect(
        bundle?.alternativeScene.voxels.some((voxel) =>
          voxel.optionContributions.some((item) => item.optionId === "b-pass"),
        ),
      ).toBe(true);
      expect(
        bundle?.alternativeScene.voxels.some((voxel) =>
          voxel.optionContributions.some((item) => item.optionId === "a-pass"),
        ),
      ).toBe(false);
    },
  );
});
