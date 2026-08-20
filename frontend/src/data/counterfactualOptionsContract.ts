import type { ActionOption } from "./schemas";
import type {
  CounterfactualCondition,
  CounterfactualFrameOptions,
  CounterfactualLead,
  CounterfactualOptionWithIdentity,
  CounterfactualOptionsArtifact,
} from "./counterfactualOptionsSchemas";

const SCORE_TOLERANCE = 1e-10;

function formattedCarryOffset(value: number) {
  if (!Number.isFinite(value)) {
    throw new Error("Carry semantic angle must be finite.");
  }
  const normalized = Object.is(value, -0) || Math.abs(value) < 1e-12 ? 0 : value;
  let token = Math.abs(normalized).toFixed(12).replace(/0+$/u, "").replace(/\.$/u, "");
  if (!token.includes(".")) token = `${token}.0`;
  return `${normalized < 0 ? "-" : "+"}${token}`;
}

export function semanticComparisonOptionKey(option: ActionOption): string {
  if (option.kind === "pass") {
    if (!option.target_player_id) {
      throw new Error(`Pass option ${option.option_id} is missing target_player_id.`);
    }
    return `pass:${option.target_player_id}`;
  }
  if (option.kind === "carry") {
    if (option.target_player_id !== null && option.target_player_id !== undefined) {
      throw new Error(`Carry option ${option.option_id} must not target a player.`);
    }
    const angle = option.features.carry_angle_offset_deg;
    if (angle === undefined) {
      throw new Error(
        `Carry option ${option.option_id} is missing carry_angle_offset_deg.`,
      );
    }
    return `carry:${formattedCarryOffset(angle)}`;
  }
  if (option.target_player_id !== null && option.target_player_id !== undefined) {
    throw new Error(`Hold option ${option.option_id} must not target a player.`);
  }
  return "hold";
}

function indexOptions(
  items: readonly CounterfactualOptionWithIdentity[],
  label: string,
): Map<string, CounterfactualOptionWithIdentity> {
  const byKey = new Map<string, CounterfactualOptionWithIdentity>();
  const optionIds = new Set<string>();
  for (const item of items) {
    const semanticKey = semanticComparisonOptionKey(item.option);
    if (semanticKey !== item.comparison_option_key) {
      throw new Error(
        `${label} ${item.option.option_id} declares ${item.comparison_option_key} but recomputes to ${semanticKey}.`,
      );
    }
    if (byKey.has(semanticKey)) {
      throw new Error(`${label} contains duplicate semantic key ${semanticKey}.`);
    }
    if (optionIds.has(item.option.option_id)) {
      throw new Error(`${label} contains duplicate option ID ${item.option.option_id}.`);
    }
    byKey.set(semanticKey, item);
    optionIds.add(item.option.option_id);
  }
  return byKey;
}

function validateOptionContext(
  frame: CounterfactualFrameOptions,
  items: readonly CounterfactualOptionWithIdentity[],
  scenarioId: string,
  actorId: string | null,
  label: string,
): string | null {
  let resolvedActor = actorId;
  for (const item of items) {
    const option = item.option;
    if (option.sequence_id !== scenarioId) {
      throw new Error(`${label} option ${option.option_id} has wrong sequence_id.`);
    }
    if (option.frame_id !== frame.frame_id) {
      throw new Error(`${label} option ${option.option_id} has wrong frame_id.`);
    }
    if (resolvedActor === null) resolvedActor = option.actor_id;
    if (option.actor_id !== resolvedActor) {
      throw new Error(`${label} mixes actor IDs within frame ${frame.frame_id}.`);
    }
  }
  return resolvedActor;
}

function validateAvailableCondition(
  frame: CounterfactualFrameOptions,
  condition: Extract<CounterfactualCondition, { status: "available" }>,
  baseline: Map<string, CounterfactualOptionWithIdentity>,
  scenarioId: string,
  baselineActorId: string,
) {
  if (condition.intervention.lead_seconds !== condition.lead_seconds) {
    throw new Error("Intervention lead does not match its condition lead.");
  }
  const right = indexOptions(
    condition.condition_b_options,
    `Condition B frame ${frame.frame_id} lead ${condition.lead_seconds}`,
  );
  validateOptionContext(
    frame,
    condition.condition_b_options,
    scenarioId,
    baselineActorId,
    "Condition B",
  );

  const comparisonByKey = new Map(
    condition.candidate_comparisons.map((comparison) => [
      comparison.comparison_option_key,
      comparison,
    ]),
  );
  if (comparisonByKey.size !== condition.candidate_comparisons.length) {
    throw new Error("Candidate comparison keys must be unique.");
  }
  const union = new Set([...baseline.keys(), ...right.keys()]);
  if (comparisonByKey.size !== union.size) {
    throw new Error("Candidate comparisons must cover the complete A/B semantic union.");
  }

  let intersection = 0;
  let leftOnly = 0;
  let rightOnly = 0;
  for (const key of union) {
    const leftItem = baseline.get(key) ?? null;
    const rightItem = right.get(key) ?? null;
    const comparison = comparisonByKey.get(key);
    if (!comparison) {
      throw new Error(`Missing candidate comparison for semantic key ${key}.`);
    }
    if (leftItem && rightItem) {
      intersection += 1;
      if (comparison.support !== "intersection") {
        throw new Error(`Shared candidate ${key} must use intersection support.`);
      }
      if (
        comparison.left_option_id !== leftItem.option.option_id ||
        comparison.right_option_id !== rightItem.option.option_id
      ) {
        throw new Error(`Shared candidate ${key} references the wrong A/B option IDs.`);
      }
      const expectedDelta =
        rightItem.option.geometric_score - leftItem.option.geometric_score;
      if (
        comparison.geometric_score_delta === null ||
        Math.abs(comparison.geometric_score_delta - expectedDelta) > SCORE_TOLERANCE
      ) {
        throw new Error(`Shared candidate ${key} has an inconsistent score delta.`);
      }
    } else if (leftItem) {
      leftOnly += 1;
      if (
        comparison.support !== "left_only" ||
        comparison.left_option_id !== leftItem.option.option_id ||
        comparison.right_option_id !== null ||
        comparison.geometric_score_delta !== null
      ) {
        throw new Error(`A-only candidate ${key} has inconsistent support metadata.`);
      }
    } else if (rightItem) {
      rightOnly += 1;
      if (
        comparison.support !== "right_only" ||
        comparison.right_option_id !== rightItem.option.option_id ||
        comparison.left_option_id !== null ||
        comparison.geometric_score_delta !== null
      ) {
        throw new Error(`B-only candidate ${key} has inconsistent support metadata.`);
      }
    }
  }

  const summary = condition.summary;
  if (
    summary.intersection !== intersection ||
    summary.left_only !== leftOnly ||
    summary.right_only !== rightOnly ||
    summary.union !== union.size
  ) {
    throw new Error("Candidate support summary does not match comparison records.");
  }
}

function validateFrame(frame: CounterfactualFrameOptions, scenarioId: string) {
  const baseline = indexOptions(
    frame.baseline_options,
    `Condition A frame ${frame.frame_id}`,
  );
  const baselineActorId = validateOptionContext(
    frame,
    frame.baseline_options,
    scenarioId,
    null,
    "Condition A",
  );
  if (!baselineActorId) {
    throw new Error(`Condition A frame ${frame.frame_id} has no actor context.`);
  }
  for (const condition of frame.conditions) {
    if (condition.status === "available") {
      validateAvailableCondition(
        frame,
        condition,
        baseline,
        scenarioId,
        baselineActorId,
      );
    }
  }
}

export function validateCounterfactualOptionsArtifact(
  artifact: CounterfactualOptionsArtifact,
  expectedScenarioId?: string,
): CounterfactualOptionsArtifact {
  if (
    expectedScenarioId !== undefined &&
    artifact.scenario_id !== expectedScenarioId
  ) {
    throw new Error(
      `Counterfactual artifact scenario ${artifact.scenario_id} does not match ${expectedScenarioId}.`,
    );
  }
  for (const frame of artifact.frames) validateFrame(frame, artifact.scenario_id);
  return artifact;
}

export function counterfactualFrameById(
  artifact: CounterfactualOptionsArtifact,
  frameId: number,
): CounterfactualFrameOptions {
  const frame = artifact.frames.find((candidate) => candidate.frame_id === frameId);
  if (!frame) {
    throw new Error(`Counterfactual artifact does not contain frame ${frameId}.`);
  }
  return frame;
}

export function counterfactualConditionForLead(
  frame: CounterfactualFrameOptions,
  lead: CounterfactualLead,
): CounterfactualCondition {
  const condition = frame.conditions.find(
    (candidate) => candidate.lead_seconds === lead,
  );
  if (!condition) {
    throw new Error(
      `Counterfactual frame ${frame.frame_id} does not contain lead ${lead}.`,
    );
  }
  return condition;
}
