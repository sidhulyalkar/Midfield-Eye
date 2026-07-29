import { z } from "zod";

export const EvidenceStatusSchema = z.enum([
  "hypothesis_only",
  "measured",
  "mixed",
]);
export const TrackingStatusSchema = z.enum([
  "observed",
  "extrapolated",
  "inferred",
  "interpolated",
  "unknown",
]);
export const TeamSchema = z.enum(["home", "away"]);
export const ActionKindSchema = z.enum(["pass", "carry", "hold"]);
export const GazeSourceSchema = z.enum([
  "observed",
  "pose_inferred",
  "motion_proxy",
  "synthetic",
  "unknown",
]);

export const ManifestSchema = z
  .object({
    bundle_version: z.string(),
    generated_at: z.string().optional(),
    title: z.string().optional(),
    description: z.string().optional(),
    player_count: z.number().int(),
    scenario_count: z.number().int(),
    cohort_balance: z.record(z.string(), z.number().int()).optional(),
    ranking_policy: z.string(),
    evidence_contract: z.record(z.string(), z.string()),
    frontend_contract: z.record(z.string(), z.unknown()),
  })
  .passthrough();

export const PlayerStudySchema = z
  .object({
    id: z.string(),
    name: z.string(),
    cohort: z.string(),
    display_role: z.string(),
    primary_archetype: z.string(),
    secondary_archetypes: z.array(z.string()).default([]),
    signature: z.string(),
    study_questions: z.array(z.string()),
    showcase_emphasis: z.record(z.string(), z.number()),
    showcase_emphasis_status: z.literal(
      "illustrative_archetype_emphasis_not_player_rating",
    ),
    evidence_status: EvidenceStatusSchema,
    profile_status: z.string(),
    profile_card: z.string().optional(),
    scenario_ids: z.array(z.string()).default([]),
    featured: z.boolean().optional(),
    talent_lenses: z.array(z.string()).optional(),
    gaze_lenses: z.array(z.string()).optional(),
    body_mechanics_lenses: z.array(z.string()).optional(),
    orchestration_lenses: z.array(z.string()).optional(),
  })
  .passthrough();

export const ScenarioSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    player_id: z.string(),
    player_name: z.string(),
    archetype: z.string(),
    tactical_question: z.string(),
    narrative_beats: z.array(z.string()),
    focus_metrics: z.array(z.string()),
    key_frame_index: z.number().int(),
    evidence_status: z.string(),
    gaze_status: z.string(),
    body_mechanics_status: z.string(),
    relation_pattern: z.string(),
  })
  .passthrough();

export const ScenarioSummarySchema = ScenarioSchema.extend({
  paths: z.record(z.string(), z.string()),
}).passthrough();

export const PlayerStateSchema = z
  .object({
    player_id: z.string(),
    source_player_id: z.string().nullable().optional(),
    team: TeamSchema,
    x: z.number(),
    y: z.number(),
    vx: z.number().nullable().optional(),
    vy: z.number().nullable().optional(),
    body_angle: z.number().nullable().optional(),
    head_angle: z.number().nullable().optional(),
    gaze_angle: z.number().nullable().optional(),
    tracking_status: TrackingStatusSchema,
    visibility: z.string().optional(),
    visible: z.boolean().nullable().optional(),
    confidence: z.number().nullable().optional(),
    position_covariance: z.array(z.array(z.number())).nullable().optional(),
    metadata: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

export const FrameStateSchema = z
  .object({
    sequence_id: z.string(),
    frame_id: z.number().int(),
    timestamp_s: z.number(),
    possession_team: TeamSchema,
    ball_x: z.number(),
    ball_y: z.number(),
    ball_carrier_id: z.string(),
    players: z.array(PlayerStateSchema),
    pitch_length: z.number().positive(),
    pitch_width: z.number().positive(),
    source_provider: z.string(),
    source_match_id: z.string().nullable().optional(),
    quality_flags: z.array(z.string()),
    state_version: z.string(),
    visibility_polygon: z
      .array(z.tuple([z.number(), z.number()]))
      .nullable()
      .optional(),
    metadata: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

export const ActionOptionSchema = z
  .object({
    sequence_id: z.string(),
    frame_id: z.number().int(),
    option_id: z.string(),
    kind: ActionKindSchema,
    actor_id: z.string(),
    target_player_id: z.string().nullable().optional(),
    target_x: z.number(),
    target_y: z.number(),
    features: z.record(z.string(), z.number()),
    geometric_score: z.number(),
    learned_score: z.number().nullable().optional(),
    source_provider: z.string().optional(),
    provenance: z.string(),
    label_available: z.boolean().nullable().optional(),
    label_visible: z.boolean().nullable().optional(),
    label_selected: z.boolean().nullable().optional(),
    label_value: z.number().nullable().optional(),
    failure_reason: z.string().nullable().optional(),
  })
  .passthrough();

export const TimelinePointSchema = z
  .object({
    frame_id: z.number().int(),
    timestamp_s: z.number(),
    menu_breadth: z.number(),
    visible_options: z.number(),
    best_option_value: z.number(),
    state_confidence: z.number(),
  })
  .passthrough();

const ViewConeSchema = z
  .object({
    half_width_deg: z.number(),
    radius_m: z.number(),
    polygon: z.array(z.tuple([z.number(), z.number()])),
    source: z.string(),
    confidence: z.number(),
  })
  .passthrough();

export const GazeTimelinePointSchema = z
  .object({
    frame_id: z.number().int(),
    timestamp_s: z.number(),
    gaze_angle_rad: z.number().nullable(),
    head_angle_rad: z.number().nullable(),
    body_angle_rad: z.number().nullable(),
    gaze_source: GazeSourceSchema,
    gaze_confidence: z.number().nullable(),
    view_cones: z.record(z.string(), ViewConeSchema),
    metric_status: z.string(),
  })
  .passthrough();

export const GazePayloadSchema = z
  .object({
    timeline: z.array(GazeTimelinePointSchema),
    scan_events: z.array(z.unknown()),
    summary: z.record(z.string(), z.unknown()),
    interpretation_guardrail: z.string(),
  })
  .passthrough();

export const BodyTimelinePointSchema = z
  .object({
    frame_id: z.number().int(),
    timestamp_s: z.number(),
    source: z.string(),
    body_angle_rad: z.number().nullable(),
    movement_heading_rad: z.number().nullable(),
    weight_transfer_vector: z.tuple([z.number(), z.number()]).nullable(),
    metric_status: z.string(),
  })
  .passthrough();

export const BodyPayloadSchema = z
  .object({
    timeline: z.array(BodyTimelinePointSchema),
    summary: z.record(z.string(), z.unknown()),
    interpretation_guardrail: z.string(),
  })
  .passthrough();

export const RelationTimelinePointSchema = z
  .object({
    frame_id: z.number().int(),
    timestamp_s: z.number(),
    pressure_attraction: z.number().nullable(),
    support_reactivity: z.number().nullable(),
    option_enablement: z.number().nullable(),
    metric_status: z.string(),
  })
  .passthrough();

export const RelationsPayloadSchema = z
  .object({
    timeline: z.array(RelationTimelinePointSchema),
    summary: z.record(z.string(), z.unknown()),
    interpretation_guardrail: z.string(),
  })
  .passthrough();

export const EmpiricalExperimentSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    subject: z.string().nullable(),
    source_id: z.string(),
    evidence_tier: z.string(),
    modalities: z.array(z.string()),
    measured: z.array(z.string()),
    inferred: z.array(z.string()),
    unavailable: z.array(z.string()),
    visual: z.string(),
    source_bundle: z.string(),
    claim_boundary: z.string(),
    scene: z
      .object({
        kind: z.enum(["event_snapshot", "continuous_tracking_frame"]),
        frame_id: z.union([z.string(), z.number()]),
        period: z.number().int(),
        timestamp_s: z.number(),
        coordinate_system: z
          .object({
            origin: z.literal("top_left"),
            units: z.literal("metres"),
            pitch_length: z.number().positive(),
            pitch_width: z.number().positive(),
            normalization: z.string(),
          })
          .passthrough(),
        players: z.array(
          z
            .object({
              id: z.string(),
              group: z.string(),
              location_m: z.tuple([z.number(), z.number()]),
              identity_scope: z.string(),
              tracking_status: z.string(),
              keeper: z.boolean().optional(),
            })
            .passthrough(),
        ),
        ball: z
          .object({
            location_m: z.tuple([z.number(), z.number()]),
            state: z.string(),
          })
          .passthrough(),
        visible_area_m: z.array(z.tuple([z.number(), z.number()])).nullable(),
        selected_action: z
          .object({
            kind: z.string(),
            target_m: z.tuple([z.number(), z.number()]),
            timing_semantics: z.literal("retrospective_selected_event_label"),
          })
          .passthrough(),
        availability_labels: z.null(),
        velocity: z.null().optional(),
        identity_warning: z.string(),
      })
      .passthrough()
      .optional(),
  })
  .passthrough();

export const EmpiricalSourceSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    access: z.string(),
    modalities: z.array(z.string()),
    official_url: z.string().url(),
    license_name: z.string(),
    redistribution: z.string(),
    citation: z.string(),
    best_for: z.array(z.string()),
    caveats: z.array(z.string()),
    priority: z.number().optional(),
  })
  .passthrough();

export const EmpiricalSourcesEnvelopeSchema = z
  .object({
    version: z.string(),
    sources: z.array(EmpiricalSourceSchema),
  })
  .passthrough();

export const CitationSchema = z
  .object({
    id: z.string(),
    citation: z.string(),
    official_url: z.string().url(),
    license: z.string(),
  })
  .passthrough();

export const HealthSchema = z
  .object({
    status: z.string(),
    bundle_version: z.string(),
  })
  .passthrough();

export const ApiHealthSchema = z
  .object({
    status: z.string(),
    bundle_version: z.string().optional(),
    version: z.string().optional(),
  })
  .passthrough()
  .refine((value) => Boolean(value.bundle_version ?? value.version), {
    message: "Health response requires bundle_version or version.",
  })
  .transform((value) => ({
    ...value,
    bundle_version: value.bundle_version ?? value.version ?? "",
  }));

export const GenericObjectSchema = z.record(z.string(), z.unknown());

export type ShowcaseManifest = z.infer<typeof ManifestSchema>;
export type PlayerStudy = z.infer<typeof PlayerStudySchema>;
export type Scenario = z.infer<typeof ScenarioSchema>;
export type ScenarioSummary = z.infer<typeof ScenarioSummarySchema>;
export type PlayerState = z.infer<typeof PlayerStateSchema>;
export type FrameState = z.infer<typeof FrameStateSchema>;
export type ActionOption = z.infer<typeof ActionOptionSchema>;
export type TimelinePoint = z.infer<typeof TimelinePointSchema>;
export type GazeTimelinePoint = z.infer<typeof GazeTimelinePointSchema>;
export type GazePayload = z.infer<typeof GazePayloadSchema>;
export type BodyPayload = z.infer<typeof BodyPayloadSchema>;
export type RelationsPayload = z.infer<typeof RelationsPayloadSchema>;
export type EmpiricalExperiment = z.infer<typeof EmpiricalExperimentSchema>;
export type EmpiricalSource = z.infer<typeof EmpiricalSourceSchema>;
export type Citation = z.infer<typeof CitationSchema>;
export type Health = z.infer<typeof HealthSchema>;
