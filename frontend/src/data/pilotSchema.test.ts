import { describe, expect, it } from "vitest";
import { PilotSchema } from "./pilotSchema";

const protocolReady = {
  schema_version: "r1-showcase-v1",
  stage: "protocol_ready",
  title: "R1 · Real Action Menu Pilot",
  question: "Does dynamic geometry rank expert-labeled options better?",
  claim_state: "no_empirical_model_claim_yet",
  sample: {
    selected_sequences: 0,
    target_sequences: 10,
    composition: {
      central_pressure: 3,
      transition: 2,
      settled_possession: 2,
      wide_overload: 2,
      negative_control: 1,
    },
    sampling_label_status: "heuristic_for_diversity_not_ground_truth",
  },
  annotation: {
    rater_ids: [],
    full_double_rating: true,
    outcome_blinded: true,
    model_score_blinded: true,
    causal_history_only: true,
    progress: { files: 0, candidate_coverage: 0, annotators: 0, rows: 0 },
  },
  reliability: null,
  benchmark: { complete: false, metrics: {} },
  evidence_ladder: [
    { id: "protocol", label: "Protocol", complete: true, detail: "Frozen." },
    { id: "sample", label: "Sample", complete: false, detail: "Pending." },
    { id: "annotation", label: "Annotation", complete: false, detail: "Pending." },
    { id: "reliability", label: "Reliability", complete: false, detail: "Pending." },
    { id: "benchmark", label: "Benchmark", complete: false, detail: "Pending." },
  ],
  guardrails: ["No synthetic metric substitutes for missing expert evidence."],
};

describe("PilotSchema", () => {
  it("accepts the protocol-ready state without benchmark numbers", () => {
    const parsed = PilotSchema.parse(protocolReady);
    expect(parsed.benchmark.complete).toBe(false);
    expect(Object.keys(parsed.benchmark.metrics)).toHaveLength(0);
    expect(parsed.claim_state).toBe("no_empirical_model_claim_yet");
  });

  it("requires exactly five evidence gates", () => {
    expect(() =>
      PilotSchema.parse({ ...protocolReady, evidence_ladder: protocolReady.evidence_ladder.slice(0, 4) }),
    ).toThrow();
  });
});
