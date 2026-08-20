import type { VolumeChannel } from "./affordanceVolume";
import type { VolumeDifferenceInspection } from "./volumeDifferenceInspector";
import type { VolumeTemporalFilter } from "./volumeTemporal";
import type { EarlierRunIntervention } from "./volumeIntervention";

export type SerializedDifferenceInspection = {
  schemaVersion: "1.3.0";
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
  claimBoundary: VolumeDifferenceInspection["claimBoundary"] & {
    activeChannels: "state_derived_future_space_or_option_creation_only";
    candidateOptionsIncluded: false;
    candidateOptionsRegenerated: false;
  };
};

function baselineEvidenceStatus(intervention: EarlierRunIntervention) {
  const status = intervention.baselineFrame.metadata.evidence_status;
  return typeof status === "string" && status.length > 0 ? status : "unknown";
}

export function serializeDifferenceInspection(
  scenarioId: string,
  frameId: number,
  channel: VolumeChannel,
  temporalFilter: VolumeTemporalFilter,
  inspection: VolumeDifferenceInspection,
  intervention: EarlierRunIntervention,
): SerializedDifferenceInspection {
  return {
    schemaVersion: "1.3.0",
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
    claimBoundary: {
      ...inspection.claimBoundary,
      activeChannels: "state_derived_future_space_or_option_creation_only",
      candidateOptionsIncluded: false,
      candidateOptionsRegenerated: false,
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
