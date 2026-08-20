import { useMemo } from "react";
import { useScenarioCounterfactualOptions } from "../data/hooks";
import type { ActionOption, FrameState } from "../data/schemas";
import {
  buildVolumeComparison,
  isRegeneratedMenuChannel,
  type VolumeComparisonBundle,
  type VolumeComparisonChannel,
} from "./volumeComparison";
import type { DeterministicComparisonQuality } from "./volumeComparisonUrl";

export type VolumeComparisonBuildState = {
  bundle: VolumeComparisonBundle | null;
  error: Error | null;
  isPending: boolean;
  requiresRegeneratedCandidates: boolean;
};

type UseVolumeComparisonBundleArgs = {
  scenarioId: string;
  frame: FrameState | undefined;
  scenarioOptions: readonly ActionOption[] | undefined;
  channel: VolumeComparisonChannel;
  quality: DeterministicComparisonQuality;
  threshold: number;
  horizonSeconds: number;
  maxVoxels: number;
  leadSeconds: number;
};

export function useVolumeComparisonBundle({
  scenarioId,
  frame,
  scenarioOptions,
  channel,
  quality,
  threshold,
  horizonSeconds,
  maxVoxels,
  leadSeconds,
}: UseVolumeComparisonBundleArgs): VolumeComparisonBuildState {
  const requiresRegeneratedCandidates = isRegeneratedMenuChannel(channel);
  const counterfactual = useScenarioCounterfactualOptions(
    scenarioId,
    requiresRegeneratedCandidates,
  );

  return useMemo(() => {
    if (!frame) {
      return {
        bundle: null,
        error: null,
        isPending: false,
        requiresRegeneratedCandidates,
      };
    }
    if (requiresRegeneratedCandidates && counterfactual.isPending) {
      return {
        bundle: null,
        error: null,
        isPending: true,
        requiresRegeneratedCandidates,
      };
    }
    if (requiresRegeneratedCandidates && counterfactual.error) {
      return {
        bundle: null,
        error:
          counterfactual.error instanceof Error
            ? counterfactual.error
            : new Error("Counterfactual candidate artifact could not be loaded."),
        isPending: false,
        requiresRegeneratedCandidates,
      };
    }

    try {
      let bundle: VolumeComparisonBundle | null;
      if (isRegeneratedMenuChannel(channel)) {
        if (!counterfactual.data) {
          throw new Error(
            "Regenerated candidate comparison requires a validated counterfactual-options artifact.",
          );
        }
        if (!scenarioOptions) {
          throw new Error(
            "Regenerated candidate comparison requires the current authoritative showcase baseline options.",
          );
        }
        bundle = buildVolumeComparison(frame, {
          channel,
          quality,
          threshold,
          horizonSeconds,
          maxVoxels,
          leadSeconds,
          currentScenarioOptions: scenarioOptions,
          counterfactualArtifact: counterfactual.data,
        });
      } else {
        bundle = buildVolumeComparison(frame, {
          channel,
          quality,
          threshold,
          horizonSeconds,
          maxVoxels,
          leadSeconds,
        });
      }
      return {
        bundle,
        error: null,
        isPending: false,
        requiresRegeneratedCandidates,
      };
    } catch (reason: unknown) {
      return {
        bundle: null,
        error:
          reason instanceof Error
            ? reason
            : new Error("The comparison contract could not be evaluated."),
        isPending: false,
        requiresRegeneratedCandidates,
      };
    }
  }, [
    channel,
    counterfactual.data,
    counterfactual.error,
    counterfactual.isPending,
    frame,
    horizonSeconds,
    leadSeconds,
    maxVoxels,
    quality,
    requiresRegeneratedCandidates,
    scenarioOptions,
    threshold,
  ]);
}
