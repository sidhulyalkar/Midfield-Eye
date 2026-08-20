import { afterEach, describe, expect, it, vi } from "vitest";
import type { CounterfactualOptionsArtifact } from "./counterfactualOptionsSchemas";
import {
  counterfactualOptionsAssetPath,
  loadCounterfactualOptionsArtifact,
} from "./counterfactualOptionsLoader";

function holdOption() {
  return {
    sequence_id: "scenario-x",
    frame_id: 1,
    option_id: "scenario-x:1:carrier:hold",
    kind: "hold" as const,
    actor_id: "carrier",
    target_player_id: null,
    target_x: 20,
    target_y: 10,
    features: {},
    geometric_score: 0.4,
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

function artifact(scenarioId = "scenario-x"): CounterfactualOptionsArtifact {
  const unavailable = (lead: 0.5 | 0.75 | 1) => ({
    lead_seconds: lead,
    status: "unavailable" as const,
    reason: "no_feasible_earlier_run_intervention" as const,
    intervention: null,
    condition_b_options: [],
    candidate_comparisons: [],
    summary: null,
  });
  return {
    schema_version: "1.4.0-b",
    scenario_id: scenarioId,
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
        frame_id: 1,
        timestamp_s: 0.25,
        baseline_options: [
          { comparison_option_key: "hold", option: holdOption() },
        ],
        conditions: [unavailable(0.5), unavailable(0.75), unavailable(1)],
      },
    ],
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("counterfactual artifact loader", () => {
  it("uses the governed scenario artifact path and returns a semantically validated artifact", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(artifact()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const source = {
      assetUrl: (path: string) => `https://example.test/api/assets/${path}`,
    };
    const loaded = await loadCounterfactualOptionsArtifact(source, "scenario-x");
    expect(loaded.scenario_id).toBe("scenario-x");
    expect(fetchMock).toHaveBeenCalledWith(
      "https://example.test/api/assets/scenarios/scenario-x/counterfactual_options.json",
      { headers: { Accept: "application/json" } },
    );
  });

  it("rejects a valid-shaped artifact for the wrong scenario", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(artifact("other-scenario")), { status: 200 }),
      ),
    );
    await expect(
      loadCounterfactualOptionsArtifact(
        { assetUrl: (path: string) => path },
        "scenario-x",
      ),
    ).rejects.toThrow(/does not match expected scenario/u);
  });

  it("fails closed on missing assets and invalid scenario IDs", async () => {
    expect(() => counterfactualOptionsAssetPath("   ")).toThrow(/non-empty/u);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("missing", { status: 404 })),
    );
    await expect(
      loadCounterfactualOptionsArtifact(
        { assetUrl: (path: string) => path },
        "scenario-x",
      ),
    ).rejects.toThrow(/404/u);
  });
});
