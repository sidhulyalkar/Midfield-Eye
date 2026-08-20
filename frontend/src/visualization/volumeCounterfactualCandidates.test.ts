import { describe, expect, it } from "vitest";
import type { CounterfactualOptionsArtifact } from "../data/counterfactualOptionsSchemas";
import type { ActionOption, FrameState, PlayerState } from "../data/schemas";
import { resolveRegeneratedCandidateEvidence } from "./volumeCounterfactualCandidates";
import { buildEarlierRunIntervention } from "./volumeIntervention";

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
    ],
    pitch_length: 105,
    pitch_width: 68,
    source_provider: "synthetic",
    quality_flags: [],
    state_version: "test",
    metadata: {},
  };
}

function option(
  optionId: string,
  targetX: number,
  targetY: number,
  score: number,
): ActionOption {
  return {
    sequence_id: "compare",
    frame_id: 9,
    option_id: optionId,
    kind: "pass",
    actor_id: "carrier",
    target_player_id: "runner",
    target_x: targetX,
    target_y: targetY,
    features: { distance: Math.hypot(targetX - 35, targetY - 28) },
    geometric_score: score,
    learned_score: null,
    source_provider: "synthetic",
    provenance: "test",
    label_available: null,
    label_visible: null,
    label_selected: null,
    label_value: null,
    failure_reason: null,
  };
}

function artifact(
  baseline: ActionOption,
  alternative: ActionOption,
  leadStatus: "available" | "unavailable" = "available",
): CounterfactualOptionsArtifact {
  const intervention = buildEarlierRunIntervention(frame(), 0.75);
  if (!intervention) throw new Error("fixture intervention unavailable");
  const available = {
    lead_seconds: 0.75 as const,
    status: "available" as const,
    reason: null,
    intervention: {
      id: intervention.id,
      player_id: intervention.playerId,
      lead_seconds: 0.75 as const,
      speed_mps: intervention.speedMps,
      displacement_m: intervention.displacementM,
      from: [intervention.from[0], intervention.from[1]] as [number, number],
      to: [intervention.to[0], intervention.to[1]] as [number, number],
      status: "synthetic_teaching_intervention_not_observed_or_causal" as const,
    },
    condition_b_options: [
      { comparison_option_key: "pass:runner", option: alternative },
    ],
    candidate_comparisons: [
      {
        comparison_option_key: "pass:runner",
        support: "intersection" as const,
        left_option_id: baseline.option_id,
        right_option_id: alternative.option_id,
        geometric_score_delta:
          alternative.geometric_score - baseline.geometric_score,
      },
    ],
    summary: { intersection: 1, left_only: 0, right_only: 0, union: 1 },
  };
  const unavailable = {
    lead_seconds: 0.75 as const,
    status: "unavailable" as const,
    reason: "no_feasible_earlier_run_intervention" as const,
    intervention: null,
    condition_b_options: [],
    candidate_comparisons: [],
    summary: null,
  };
  return {
    schema_version: "1.4.0-b",
    scenario_id: "compare",
    generator: {
      name: "AffordanceEngine",
      module: "midfielders_eye.affordance",
      package_version: "1.4.0",
      config: {
        carry_distance_m: 6,
        carry_angle_offsets_deg: [-30, 0, 30],
        include_hold: true,
        ball_speed_mps: 15,
        visibility_half_fov_deg: 55,
        weights: { forward_progress: 0.2 },
      },
      config_sha256: "a".repeat(64),
      candidate_identity_contract: "semantic_action_candidate_v1",
      intervention_contract: "earlier_run_focal_velocity_v1",
      future_observed_frames_used: false,
    },
    lead_presets: [0.5, 0.75, 1],
    frames: [
      {
        frame_id: 9,
        timestamp_s: 2.25,
        baseline_options: [
          { comparison_option_key: "pass:runner", option: baseline },
        ],
        conditions: [
          {
            lead_seconds: 0.5,
            status: "unavailable",
            reason: "no_feasible_earlier_run_intervention",
            intervention: null,
            condition_b_options: [],
            candidate_comparisons: [],
            summary: null,
          },
          leadStatus === "available" ? available : unavailable,
          {
            lead_seconds: 1,
            status: "unavailable",
            reason: "no_feasible_earlier_run_intervention",
            intervention: null,
            condition_b_options: [],
            candidate_comparisons: [],
            summary: null,
          },
        ],
      },
    ],
  };
}

describe("v1.4 regenerated candidate evidence", () => {
  it("returns exact authoritative A/B options and generator provenance after parity passes", () => {
    const baseline = option("a-pass", 48, 30, 0.55);
    const alternative = option("b-pass", 49.5, 30.3, 0.68);
    const focal = frame();
    const intervention = buildEarlierRunIntervention(focal, 0.75);
    if (!intervention) throw new Error("fixture intervention unavailable");
    const evidence = resolveRegeneratedCandidateEvidence(
      artifact(baseline, alternative),
      focal,
      [baseline],
      intervention,
    );
    expect(evidence.candidateOptionsIncluded).toBe(true);
    expect(evidence.candidateOptionsRegenerated).toBe(true);
    expect(evidence.conditionAOptions[0]).toBe(baseline);
    expect(evidence.conditionBOptions[0]).toBe(alternative);
    expect(evidence.supportSummary).toEqual({
      intersection: 1,
      leftOnly: 0,
      rightOnly: 0,
      union: 1,
    });
    expect(evidence.provenance).toMatchObject({
      generatorName: "AffordanceEngine",
      configSha256: "a".repeat(64),
      futureObservedFramesUsed: false,
    });
  });

  it("fails closed if the frozen artifact baseline differs from the current showcase menu", () => {
    const baseline = option("a-pass", 48, 30, 0.55);
    const alternative = option("b-pass", 49.5, 30.3, 0.68);
    const focal = frame();
    const intervention = buildEarlierRunIntervention(focal, 0.75);
    if (!intervention) throw new Error("fixture intervention unavailable");
    expect(() =>
      resolveRegeneratedCandidateEvidence(
        artifact(baseline, alternative),
        focal,
        [{ ...baseline, geometric_score: 0.54 }],
        intervention,
      ),
    ).toThrow(/does not exactly match/u);
  });

  it("fails closed if the artifact intervention geometry does not match the browser intervention", () => {
    const baseline = option("a-pass", 48, 30, 0.55);
    const alternative = option("b-pass", 49.5, 30.3, 0.68);
    const focal = frame();
    const intervention = buildEarlierRunIntervention(focal, 0.75);
    if (!intervention) throw new Error("fixture intervention unavailable");
    const mismatched = artifact(baseline, alternative);
    const condition = mismatched.frames[0]?.conditions[1];
    if (!condition || condition.status !== "available") {
      throw new Error("fixture condition unavailable");
    }
    condition.intervention.to[0] += 0.2;
    expect(() =>
      resolveRegeneratedCandidateEvidence(
        mismatched,
        focal,
        [baseline],
        intervention,
      ),
    ).toThrow(/target X mismatch/u);
  });

  it("fails closed when the requested regenerated lead is unavailable", () => {
    const baseline = option("a-pass", 48, 30, 0.55);
    const alternative = option("b-pass", 49.5, 30.3, 0.68);
    const focal = frame();
    const intervention = buildEarlierRunIntervention(focal, 0.75);
    if (!intervention) throw new Error("fixture intervention unavailable");
    expect(() =>
      resolveRegeneratedCandidateEvidence(
        artifact(baseline, alternative, "unavailable"),
        focal,
        [baseline],
        intervention,
      ),
    ).toThrow(/regeneration is unavailable/u);
  });
});
