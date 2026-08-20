import { z } from "zod";
import { ActionOptionSchema } from "./schemas";

export const CounterfactualLeadSchema = z.union([
  z.literal(0.5),
  z.literal(0.75),
  z.literal(1),
]);

export const CounterfactualOptionWithIdentitySchema = z
  .object({
    comparison_option_key: z.string().min(1),
    option: ActionOptionSchema,
  })
  .strict();

export const CounterfactualCandidateComparisonSchema = z
  .object({
    comparison_option_key: z.string().min(1),
    support: z.enum(["intersection", "left_only", "right_only"]),
    left_option_id: z.string().nullable(),
    right_option_id: z.string().nullable(),
    geometric_score_delta: z.number().finite().nullable(),
  })
  .strict()
  .superRefine((value, context) => {
    if (value.support === "intersection") {
      if (
        value.left_option_id === null ||
        value.right_option_id === null ||
        value.geometric_score_delta === null
      ) {
        context.addIssue({
          code: "custom",
          message:
            "Intersection candidate comparisons require A/B option IDs and a numerical delta.",
        });
      }
      return;
    }
    if (value.geometric_score_delta !== null) {
      context.addIssue({
        code: "custom",
        message: "One-sided candidate comparisons must keep delta=null.",
      });
    }
    if (
      value.support === "left_only" &&
      (value.left_option_id === null || value.right_option_id !== null)
    ) {
      context.addIssue({
        code: "custom",
        message: "left_only requires only the Condition A option ID.",
      });
    }
    if (
      value.support === "right_only" &&
      (value.right_option_id === null || value.left_option_id !== null)
    ) {
      context.addIssue({
        code: "custom",
        message: "right_only requires only the Condition B option ID.",
      });
    }
  });

export const EarlierRunArtifactInterventionSchema = z
  .object({
    id: z.string().min(1),
    player_id: z.string().min(1),
    lead_seconds: CounterfactualLeadSchema,
    speed_mps: z.number().finite().nonnegative(),
    displacement_m: z.number().finite().positive(),
    from: z.tuple([z.number().finite(), z.number().finite()]),
    to: z.tuple([z.number().finite(), z.number().finite()]),
    status: z.literal(
      "synthetic_teaching_intervention_not_observed_or_causal",
    ),
  })
  .strict();

export const CounterfactualCandidateSummarySchema = z
  .object({
    intersection: z.number().int().nonnegative(),
    left_only: z.number().int().nonnegative(),
    right_only: z.number().int().nonnegative(),
    union: z.number().int().nonnegative(),
  })
  .strict()
  .superRefine((value, context) => {
    if (
      value.intersection + value.left_only + value.right_only !==
      value.union
    ) {
      context.addIssue({
        code: "custom",
        message: "Candidate support counts must sum to union.",
      });
    }
  });

const AvailableConditionSchema = z
  .object({
    lead_seconds: CounterfactualLeadSchema,
    status: z.literal("available"),
    reason: z.null(),
    intervention: EarlierRunArtifactInterventionSchema,
    condition_b_options: z.array(CounterfactualOptionWithIdentitySchema),
    candidate_comparisons: z.array(CounterfactualCandidateComparisonSchema),
    summary: CounterfactualCandidateSummarySchema,
  })
  .strict();

const UnavailableConditionSchema = z
  .object({
    lead_seconds: CounterfactualLeadSchema,
    status: z.literal("unavailable"),
    reason: z.literal("no_feasible_earlier_run_intervention"),
    intervention: z.null(),
    condition_b_options: z.array(z.never()).length(0),
    candidate_comparisons: z.array(z.never()).length(0),
    summary: z.null(),
  })
  .strict();

export const CounterfactualConditionSchema = z.discriminatedUnion("status", [
  AvailableConditionSchema,
  UnavailableConditionSchema,
]);

export const CounterfactualFrameOptionsSchema = z
  .object({
    frame_id: z.number().int().nonnegative(),
    timestamp_s: z.number().finite().nonnegative(),
    baseline_options: z.array(CounterfactualOptionWithIdentitySchema).min(1),
    conditions: z.array(CounterfactualConditionSchema).length(3),
  })
  .strict()
  .superRefine((value, context) => {
    const leads = value.conditions.map((condition) => condition.lead_seconds);
    if (leads[0] !== 0.5 || leads[1] !== 0.75 || leads[2] !== 1) {
      context.addIssue({
        code: "custom",
        message: "Frame conditions must be ordered 0.50, 0.75, 1.00 seconds.",
      });
    }
    const keys = value.baseline_options.map((item) => item.comparison_option_key);
    if (new Set(keys).size !== keys.length) {
      context.addIssue({
        code: "custom",
        message: "Baseline semantic candidate keys must be unique within a frame.",
      });
    }
  });

export const CounterfactualGeneratorSchema = z
  .object({
    name: z.literal("AffordanceEngine"),
    module: z.literal("midfielders_eye.affordance"),
    package_version: z.string().min(1),
    config: z
      .object({
        carry_distance_m: z.number().finite().positive(),
        carry_angle_offsets_deg: z.array(z.number().finite()).min(1),
        include_hold: z.boolean(),
        ball_speed_mps: z.number().finite().positive(),
        visibility_half_fov_deg: z.number().finite().positive(),
        weights: z.record(z.string(), z.number().finite()),
      })
      .strict(),
    config_sha256: z.string().regex(/^[0-9a-f]{64}$/u),
    candidate_identity_contract: z.literal("semantic_action_candidate_v1"),
    intervention_contract: z.literal("earlier_run_focal_velocity_v1"),
    future_observed_frames_used: z.literal(false),
  })
  .strict();

export const CounterfactualOptionsArtifactSchema = z
  .object({
    schema_version: z.literal("1.4.0-b"),
    scenario_id: z.string().min(1),
    generator: CounterfactualGeneratorSchema,
    lead_presets: z.tuple([
      z.literal(0.5),
      z.literal(0.75),
      z.literal(1),
    ]),
    frames: z.array(CounterfactualFrameOptionsSchema).min(1),
  })
  .strict()
  .superRefine((value, context) => {
    let previousFrameId = -1;
    const frameIds = new Set<number>();
    for (const frame of value.frames) {
      if (frame.frame_id <= previousFrameId) {
        context.addIssue({
          code: "custom",
          message: "Counterfactual artifact frames must be strictly ordered.",
        });
        break;
      }
      if (frameIds.has(frame.frame_id)) {
        context.addIssue({
          code: "custom",
          message: "Counterfactual artifact frame IDs must be unique.",
        });
        break;
      }
      previousFrameId = frame.frame_id;
      frameIds.add(frame.frame_id);
    }
  });

export type CounterfactualLead = z.infer<typeof CounterfactualLeadSchema>;
export type CounterfactualOptionWithIdentity = z.infer<
  typeof CounterfactualOptionWithIdentitySchema
>;
export type CounterfactualCandidateComparison = z.infer<
  typeof CounterfactualCandidateComparisonSchema
>;
export type CounterfactualCondition = z.infer<
  typeof CounterfactualConditionSchema
>;
export type CounterfactualFrameOptions = z.infer<
  typeof CounterfactualFrameOptionsSchema
>;
export type CounterfactualOptionsArtifact = z.infer<
  typeof CounterfactualOptionsArtifactSchema
>;
