import type { VolumeChannel } from "./affordanceVolume";
import type {
  VolumeComparisonCandidateEvidence,
  VolumeComparisonChannel,
} from "./volumeComparison";
import type { VolumeDifferenceInspection } from "./volumeDifferenceInspector";
import type { VolumeTemporalFilter } from "./volumeTemporal";
import type { EarlierRunIntervention } from "./volumeIntervention";

export type SerializedDifferenceInspection = {
  schemaVersion: "1.4.0-d";
  instrument: "Temporal Affordance Difference Volume";
  scenarioId: string;
  frameId: number;
  sourceEvidenceStatus: string;
  channel: VolumeChannel;
  temporalFilter: VolumeTemporalFilter;
  comparison: {
    signConvention: "condition_b_minus_condition_a";
    support: VolumeDifferenceInspection["support"];
    numericComparisonAvailable: boolean;
    delta: number | null;
    absoluteDelta: number | null;
    conditionA: VolumeDifferenceInspection["conditionA"];
    conditionB: VolumeDifferenceInspection["conditionB"];
  };
  intervention: {
    id: string;
    playerId: string;
    leadSeconds: number;
    speedMps: number;
    displacementM: number;
    from: readonly [number, number];
    to: readonly [number, number];
    status: "synthetic_teaching_intervention_not_observed_or_causal";
  };
  candidateEvidence:
    | {
        mode: "state_only";
        generator: null;
        supportSummary: null;
      }
    | {
        mode: "regenerated_counterfactual_candidates";
        generator: {
          name: "AffordanceEngine";
          module: "midfielders_eye.affordance";
          packageVersion: string;
          configSha256: string;
          candidateIdentityContract: "semantic_action_candidate_v1";
          interventionContract: "earlier_run_focal_velocity_v1";
          schemaVersion: "1.4.0-b";
        };
        supportSummary: {
          intersection: number;
          leftOnly: number;
          rightOnly: number;
          union: number;
        };
      };
  claimBoundary: VolumeDifferenceInspection["claimBoundary"] & {
    activeChannels:
      | "state_derived_future_space_or_option_creation_only"
      | "regenerated_passing_corridors_or_action_menu";
    candidateOptionsIncluded: boolean;
    candidateOptionsRegenerated: boolean;
  };
};

function baselineEvidenceStatus(intervention: EarlierRunIntervention) {
  const status = intervention.baselineFrame.metadata.evidence_status;
  return typeof status === "string" && status.length > 0 ? status : "unknown";
}

function serializedCandidateEvidence(
  evidence: VolumeComparisonCandidateEvidence,
): SerializedDifferenceInspection["candidateEvidence"] {
  if (evidence.mode === "state_only") {
    return { mode: "state_only", generator: null, supportSummary: null };
  }
  return {
    mode: evidence.mode,
    generator: {
      name: evidence.provenance.generatorName,
      module: evidence.provenance.generatorModule,
      packageVersion: evidence.provenance.packageVersion,
      configSha256: evidence.provenance.configSha256,
      candidateIdentityContract: evidence.provenance.candidateIdentityContract,
      interventionContract: evidence.provenance.interventionContract,
      schemaVersion: evidence.provenance.schemaVersion,
    },
    supportSummary: evidence.supportSummary,
  };
}

function assertCandidateEvidenceMatchesChannel(
  channel: VolumeComparisonChannel,
  candidateEvidence: VolumeComparisonCandidateEvidence,
) {
  const regeneratedChannel =
    channel === "passing_corridors" || channel === "menu";
  const regeneratedEvidence =
    candidateEvidence.mode === "regenerated_counterfactual_candidates";

  if (regeneratedChannel !== regeneratedEvidence) {
    throw new Error(
      regeneratedChannel
        ? `Channel ${channel} requires regenerated counterfactual candidate evidence.`
        : `Channel ${channel} requires state-only candidate evidence.`,
    );
  }
}

export function serializeDifferenceInspection(
  scenarioId: string,
  frameId: number,
  channel: VolumeComparisonChannel,
  temporalFilter: VolumeTemporalFilter,
  inspection: VolumeDifferenceInspection,
  intervention: EarlierRunIntervention,
  candidateEvidence: VolumeComparisonCandidateEvidence,
): SerializedDifferenceInspection {
  assertCandidateEvidenceMatchesChannel(channel, candidateEvidence);
  const regenerated =
    candidateEvidence.mode === "regenerated_counterfactual_candidates";
  return {
    schemaVersion: "1.4.0-d",
    instrument: "Temporal Affordance Difference Volume",
    scenarioId,
    frameId,
    sourceEvidenceStatus: baselineEvidenceStatus(intervention),
    channel,
    temporalFilter,
    comparison: {
      signConvention: inspection.signConvention,
      support: inspection.support,
      numericComparisonAvailable: inspection.numericComparisonAvailable,
      delta: inspection.delta,
      absoluteDelta: inspection.absoluteDelta,
      conditionA: inspection.conditionA,
      conditionB: inspection.conditionB,
    },
    intervention: {
      id: intervention.id,
      playerId: intervention.playerId,
      leadSeconds: intervention.leadSeconds,
      speedMps: intervention.speedMps,
      displacementM: intervention.displacementM,
      from: intervention.from,
      to: intervention.to,
      status: "synthetic_teaching_intervention_not_observed_or_causal",
    },
    candidateEvidence: serializedCandidateEvidence(candidateEvidence),
    claimBoundary: {
      ...inspection.claimBoundary,
      activeChannels: regenerated
        ? "regenerated_passing_corridors_or_action_menu"
        : "state_derived_future_space_or_option_creation_only",
      candidateOptionsIncluded: candidateEvidence.candidateOptionsIncluded,
      candidateOptionsRegenerated: candidateEvidence.candidateOptionsRegenerated,
    },
  };
}

export function differenceInspectionFilename(
  scenarioId: string,
  frameId: number,
  channel: VolumeChannel,
  key: string,
) {
  const safe = key.replaceAll(":", "-");
  return `midfield-eye-difference-${scenarioId}-f${frameId}-${channel}-${safe}.json`;
}
