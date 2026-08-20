import {
  counterfactualConditionForLead,
  counterfactualFrameById,
  semanticComparisonOptionKey,
} from "../data/counterfactualOptionsContract";
import type {
  CounterfactualCandidateComparison,
  CounterfactualLead,
  CounterfactualOptionsArtifact,
} from "../data/counterfactualOptionsSchemas";
import type { ActionOption, FrameState } from "../data/schemas";
import type { EarlierRunIntervention } from "./volumeIntervention";

const FLOAT_TOLERANCE = 1e-9;

export type RegeneratedCandidateProvenance = {
  schemaVersion: "1.4.0-b";
  generatorName: "AffordanceEngine";
  generatorModule: "midfielders_eye.affordance";
  packageVersion: string;
  configSha256: string;
  candidateIdentityContract: "semantic_action_candidate_v1";
  interventionContract: "earlier_run_focal_velocity_v1";
  futureObservedFramesUsed: false;
};

export type RegeneratedCandidateEvidence = {
  mode: "regenerated_counterfactual_candidates";
  conditionAOptions: ActionOption[];
  conditionBOptions: ActionOption[];
  comparisons: CounterfactualCandidateComparison[];
  supportSummary: {
    intersection: number;
    leftOnly: number;
    rightOnly: number;
    union: number;
  };
  provenance: RegeneratedCandidateProvenance;
};

function close(left: number, right: number, label: string) {
  if (
    !Number.isFinite(left) ||
    !Number.isFinite(right) ||
    Math.abs(left - right) > FLOAT_TOLERANCE
  ) {
    throw new Error(`${label} mismatch: ${left} != ${right}.`);
  }
}

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, stableValue(item)]),
    );
  }
  return value;
}

function optionFingerprint(option: ActionOption): string {
  return JSON.stringify(stableValue(option));
}

function indexOptions(options: readonly ActionOption[], label: string) {
  const byKey = new Map<string, ActionOption>();
  for (const option of options) {
    const key = semanticComparisonOptionKey(option);
    if (byKey.has(key)) {
      throw new Error(`${label} contains duplicate semantic candidate ${key}.`);
    }
    byKey.set(key, option);
  }
  return byKey;
}

function assertBaselineParity(
  currentScenarioOptions: readonly ActionOption[],
  artifactOptions: readonly ActionOption[],
  frame: FrameState,
) {
  const current = indexOptions(
    currentScenarioOptions.filter(
      (option) =>
        option.frame_id === frame.frame_id &&
        option.actor_id === frame.ball_carrier_id,
    ),
    "Current showcase baseline",
  );
  const artifact = indexOptions(artifactOptions, "Counterfactual artifact baseline");
  if (current.size !== artifact.size) {
    throw new Error(
      `Counterfactual artifact baseline has ${artifact.size} candidates but current showcase has ${current.size}.`,
    );
  }
  for (const [key, currentOption] of current) {
    const artifactOption = artifact.get(key);
    if (!artifactOption) {
      throw new Error(`Counterfactual artifact baseline is missing candidate ${key}.`);
    }
    if (optionFingerprint(currentOption) !== optionFingerprint(artifactOption)) {
      throw new Error(
        `Counterfactual artifact baseline candidate ${key} does not exactly match the current showcase option.`,
      );
    }
  }
}

function assertInterventionParity(
  intervention: EarlierRunIntervention,
  artifact: Extract<
    ReturnType<typeof counterfactualConditionForLead>,
    { status: "available" }
  >["intervention"],
) {
  if (artifact.id !== intervention.id) {
    throw new Error(
      `Counterfactual intervention ID ${artifact.id} does not match ${intervention.id}.`,
    );
  }
  if (artifact.player_id !== intervention.playerId) {
    throw new Error("Counterfactual intervention player does not match browser intervention.");
  }
  close(artifact.lead_seconds, intervention.leadSeconds, "Intervention lead");
  close(artifact.speed_mps, intervention.speedMps, "Intervention speed");
  close(
    artifact.displacement_m,
    intervention.displacementM,
    "Intervention displacement",
  );
  close(artifact.from[0], intervention.from[0], "Intervention origin X");
  close(artifact.from[1], intervention.from[1], "Intervention origin Y");
  close(artifact.to[0], intervention.to[0], "Intervention target X");
  close(artifact.to[1], intervention.to[1], "Intervention target Y");
}

function asCounterfactualLead(value: number): CounterfactualLead {
  if (value === 0.5 || value === 0.75 || value === 1) return value;
  throw new Error(
    `Regenerated candidate comparison requires lead 0.50, 0.75, or 1.00; received ${value}.`,
  );
}

export function resolveRegeneratedCandidateEvidence(
  artifact: CounterfactualOptionsArtifact,
  frame: FrameState,
  currentScenarioOptions: readonly ActionOption[],
  intervention: EarlierRunIntervention,
): RegeneratedCandidateEvidence {
  if (artifact.scenario_id !== frame.sequence_id) {
    throw new Error(
      `Counterfactual artifact scenario ${artifact.scenario_id} does not match frame sequence ${frame.sequence_id}.`,
    );
  }
  const artifactFrame = counterfactualFrameById(artifact, frame.frame_id);
  close(artifactFrame.timestamp_s, frame.timestamp_s, "Counterfactual frame timestamp");

  const condition = counterfactualConditionForLead(
    artifactFrame,
    asCounterfactualLead(intervention.leadSeconds),
  );
  if (condition.status !== "available") {
    throw new Error(
      `Counterfactual candidate regeneration is unavailable for frame ${frame.frame_id} at lead ${intervention.leadSeconds.toFixed(2)} s: ${condition.reason}.`,
    );
  }

  assertInterventionParity(intervention, condition.intervention);
  const conditionAOptions = artifactFrame.baseline_options.map((item) => item.option);
  const conditionBOptions = condition.condition_b_options.map((item) => item.option);
  assertBaselineParity(currentScenarioOptions, conditionAOptions, frame);

  const provenance: RegeneratedCandidateProvenance = {
    schemaVersion: artifact.schema_version,
    generatorName: artifact.generator.name,
    generatorModule: artifact.generator.module,
    packageVersion: artifact.generator.package_version,
    configSha256: artifact.generator.config_sha256,
    candidateIdentityContract: artifact.generator.candidate_identity_contract,
    interventionContract: artifact.generator.intervention_contract,
    futureObservedFramesUsed: artifact.generator.future_observed_frames_used,
  };

  return {
    mode: "regenerated_counterfactual_candidates",
    conditionAOptions,
    conditionBOptions,
    comparisons: condition.candidate_comparisons,
    supportSummary: {
      intersection: condition.summary.intersection,
      leftOnly: condition.summary.left_only,
      rightOnly: condition.summary.right_only,
      union: condition.summary.union,
    },
    provenance,
  };
}
