import type { CounterfactualOptionsArtifact } from "../data/counterfactualOptionsSchemas";
import type { ActionOption, FrameState } from "../data/schemas";
import {
  buildAffordanceVolume,
  defaultVolumeConfig,
  type VolumeQuality,
  type VolumeScene,
} from "./affordanceVolume";
import {
  resolveRegeneratedCandidateEvidence,
  type RegeneratedCandidateEvidence,
} from "./volumeCounterfactualCandidates";
import {
  buildVolumeDifference,
  type VolumeDifference,
} from "./volumeDifference";
import {
  buildEarlierRunIntervention,
  type EarlierRunIntervention,
} from "./volumeIntervention";

export type StateDerivedComparisonChannel = "future_space" | "option_creation";
export type RegeneratedMenuComparisonChannel = "passing_corridors" | "menu";
export type VolumeComparisonChannel =
  | StateDerivedComparisonChannel
  | RegeneratedMenuComparisonChannel;

export type StateOnlyCandidateEvidence = {
  mode: "state_only";
  candidateOptionsIncluded: false;
  candidateOptionsRegenerated: false;
  futureObservedFramesUsed: false;
};

export type VolumeComparisonCandidateEvidence =
  | StateOnlyCandidateEvidence
  | RegeneratedCandidateEvidence;

type SharedVolumeComparisonConfig = {
  quality: VolumeQuality;
  threshold: number;
  horizonSeconds: number;
  maxVoxels: number;
  leadSeconds: number;
};

export type StateDerivedVolumeComparisonConfig = SharedVolumeComparisonConfig & {
  channel: StateDerivedComparisonChannel;
  currentScenarioOptions?: never;
  counterfactualArtifact?: never;
};

export type RegeneratedMenuVolumeComparisonConfig = SharedVolumeComparisonConfig & {
  channel: RegeneratedMenuComparisonChannel;
  currentScenarioOptions: readonly ActionOption[];
  counterfactualArtifact: CounterfactualOptionsArtifact;
};

export type VolumeComparisonConfig =
  | StateDerivedVolumeComparisonConfig
  | RegeneratedMenuVolumeComparisonConfig;

export type VolumeComparisonBundle = {
  intervention: EarlierRunIntervention;
  baselineScene: VolumeScene;
  alternativeScene: VolumeScene;
  difference: VolumeDifference;
  candidateEvidence: VolumeComparisonCandidateEvidence;
};

export function isRegeneratedMenuChannel(
  channel: VolumeComparisonChannel,
): channel is RegeneratedMenuComparisonChannel {
  return channel === "passing_corridors" || channel === "menu";
}

export function buildVolumeComparison(
  frame: FrameState,
  config: VolumeComparisonConfig,
): VolumeComparisonBundle | null {
  const intervention = buildEarlierRunIntervention(frame, config.leadSeconds);
  if (!intervention) return null;

  const baseConfig = defaultVolumeConfig(config.channel);
  const volumeConfig = {
    ...baseConfig,
    channel: config.channel,
    quality: config.quality,
    threshold: config.threshold,
    horizonSeconds: config.horizonSeconds,
    maxVoxels: config.maxVoxels,
  };

  let conditionAOptions: readonly ActionOption[] = [];
  let conditionBOptions: readonly ActionOption[] = [];
  let candidateEvidence: VolumeComparisonCandidateEvidence = {
    mode: "state_only",
    candidateOptionsIncluded: false,
    candidateOptionsRegenerated: false,
    futureObservedFramesUsed: false,
  };

  if (isRegeneratedMenuChannel(config.channel)) {
    candidateEvidence = resolveRegeneratedCandidateEvidence(
      config.counterfactualArtifact,
      frame,
      config.currentScenarioOptions,
      intervention,
    );
    conditionAOptions = candidateEvidence.conditionAOptions;
    conditionBOptions = candidateEvidence.conditionBOptions;
  }

  const baselineScene = buildAffordanceVolume(
    frame,
    [...conditionAOptions],
    volumeConfig,
  );
  const alternativeScene = buildAffordanceVolume(
    intervention.alternativeFrame,
    [...conditionBOptions],
    volumeConfig,
  );
  const sharedContract = {
    retentionScope: "full_retained_scene" as const,
    horizonSeconds: config.horizonSeconds,
    pitchLength: frame.pitch_length,
    pitchWidth: frame.pitch_width,
    threshold: config.threshold,
  };
  const difference = buildVolumeDifference(
    {
      id: "baseline",
      scene: baselineScene,
      ...sharedContract,
    },
    {
      id: intervention.id,
      scene: alternativeScene,
      ...sharedContract,
    },
  );

  return {
    intervention,
    baselineScene,
    alternativeScene,
    difference,
    candidateEvidence,
  };
}
