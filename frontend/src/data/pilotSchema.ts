import { z } from "zod";

export const PilotEvidenceStepSchema = z
  .object({
    id: z.string(),
    label: z.string(),
    complete: z.boolean(),
    detail: z.string(),
  })
  .passthrough();

const AnnotationProgressSchema = z
  .object({
    files: z.number().int().nonnegative(),
    candidate_coverage: z.number().nullable().optional(),
    annotators: z.number().int().nonnegative(),
    rows: z.number().int().nonnegative(),
    genuine_human_rows: z.number().int().nonnegative().optional(),
  })
  .passthrough();

export const PilotSchema = z
  .object({
    schema_version: z.literal("r1-showcase-v1"),
    stage: z.enum([
      "protocol_ready",
      "needs_sequence_review",
      "sample_frozen",
      "annotation_in_progress",
      "reliability_established",
      "reliability_not_established",
      "needs_adjudication",
      "expert_pilot_frozen_needs_provider_review",
      "benchmark_ready",
      "benchmark_complete",
    ]),
    title: z.string(),
    question: z.string(),
    claim_state: z.enum([
      "no_empirical_model_claim_yet",
      "empirical_benchmark_complete",
    ]),
    sample: z
      .object({
        selected_sequences: z.number().int().nonnegative().optional(),
        target_sequences: z.number().int().positive().optional(),
        label_frames: z.number().int().nonnegative().optional(),
        context_frames: z.number().int().nonnegative().optional(),
        candidates: z.number().int().nonnegative().optional(),
        composition: z.record(z.string(), z.number().int().nonnegative()),
        sampling_label_status: z.string(),
      })
      .passthrough(),
    annotation: z
      .object({
        rater_ids: z.array(z.string()),
        full_double_rating: z.boolean(),
        outcome_blinded: z.boolean(),
        model_score_blinded: z.boolean(),
        causal_history_only: z.boolean(),
        progress: AnnotationProgressSchema,
      })
      .passthrough(),
    reliability: z.record(z.string(), z.unknown()).nullable(),
    benchmark: z
      .object({
        complete: z.boolean(),
        metrics: z.record(
          z.string(),
          z.record(z.string(), z.number().nullable()),
        ),
      })
      .passthrough(),
    evidence_ladder: z.array(PilotEvidenceStepSchema).length(5),
    guardrails: z.array(z.string()).min(1),
  })
  .passthrough();

export type PilotPayload = z.infer<typeof PilotSchema>;
