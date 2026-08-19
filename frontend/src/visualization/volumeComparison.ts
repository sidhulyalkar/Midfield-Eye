import type { FrameState } from "../data/schemas";
import {
  buildAffordanceVolume,
  defaultVolumeConfig,
  type VolumeQuality,
  type VolumeScene,
} from "./affordanceVolume";
import {
  buildVolumeDifference,
  type VolumeDifference,
} from "./volumeDifference";
import {
  buildEarlierRunIntervention,
  type EarlierRunIntervention,
} from "./volumeIntervention";

export type VolumeComparisonChannel = "future_space" | "option_creation";

export type VolumeComparisonConfig = {
  channel: VolumeComparisonChannel;
  quality: VolumeQuality;
  threshold: number;
  horizonSeconds: number;
  maxVoxels: number;
  leadSeconds: number;
};

export type VolumeComparisonBundle = {
  intervention: EarlierRunIntervention;
  baselineScene: VolumeScene;
  alternativeScene: VolumeScene;
  difference: VolumeDifference;
};

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

  // Comparison v1.3.0-c is intentionally state-derived only. Candidate options
  // are omitted on both sides so no baseline pass score is reused after the
  // positional intervention.
  const baselineScene = buildAffordanceVolume(frame, [], volumeConfig);
  const alternativeScene = buildAffordanceVolume(
    intervention.alternativeFrame,
    [],
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

  return { intervention, baselineScene, alternativeScene, difference };
}
