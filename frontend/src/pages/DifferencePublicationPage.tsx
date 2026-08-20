import { useMemo } from "react";
import { Link, useSearchParams } from "react-router";
import { FeedbackState } from "../components/FeedbackState";
import { useScenarioBundle } from "../data/hooks";
import { defaultVolumeConfig } from "../visualization/affordanceVolume";
import { DifferencePublicationPlate } from "../visualization/DifferencePublicationPlate";
import { buildVolumeComparison } from "../visualization/volumeComparison";
import {
  parseComparisonFrameIndex,
  parseVolumeComparisonUrl,
  type DeterministicComparisonQuality,
} from "../visualization/volumeComparisonUrl";
import { filterVolumeDifferenceCells } from "../visualization/volumeDifferenceView";
import {
  horizonSecondsForLayer,
  type VolumeTemporalFilter,
} from "../visualization/volumeTemporal";
import { requirePublicationSlice } from "../visualization/volumePublication";
import { parseTemporalFilterFromSearchParams } from "../visualization/volumeUrlState";

const HORIZON_SECONDS = 1.5;

function maxVoxelsForQuality(quality: DeterministicComparisonQuality) {
  if (quality === "low") return 1200;
  if (quality === "high") return 4200;
  return 2800;
}

function sourceEvidenceStatus(
  frameMetadata: Record<string, unknown>,
  scenarioEvidenceStatus: string | undefined,
) {
  const frameStatus = frameMetadata.evidence_status;
  if (typeof frameStatus === "string" && frameStatus.length > 0) return frameStatus;
  return scenarioEvidenceStatus ?? "unknown";
}

function publicationLayer(
  filter: VolumeTemporalFilter,
): { layerIndex: number; error: Error | null } {
  try {
    return { layerIndex: requirePublicationSlice(filter), error: null };
  } catch (reason: unknown) {
    return {
      layerIndex: 0,
      error:
        reason instanceof Error
          ? reason
          : new Error("Publication mode requires an exact temporal slice."),
    };
  }
}

export default function DifferencePublicationPage() {
  const [searchParams] = useSearchParams();
  const searchKey = searchParams.toString();
  const scenarioId = searchParams.get("scenario") ?? "aitana-overload";
  const data = useScenarioBundle(scenarioId);
  const comparisonUrl = useMemo(
    () => parseVolumeComparisonUrl(new URLSearchParams(searchKey)),
    [searchKey],
  );
  const horizonSteps = defaultVolumeConfig(comparisonUrl.channel).horizonSteps;
  const temporalFilter = useMemo(
    () =>
      parseTemporalFilterFromSearchParams(
        new URLSearchParams(searchKey),
        horizonSteps,
      ),
    [horizonSteps, searchKey],
  );
  const layer = publicationLayer(temporalFilter);
  const frameCount = data.frames?.length ?? 0;
  const frameIndex = parseComparisonFrameIndex(
    new URLSearchParams(searchKey),
    frameCount,
    data.scenario?.key_frame_index ?? 10,
  );
  const frame = data.frames?.[frameIndex];

  const comparisonResult = useMemo(() => {
    if (!frame) return { bundle: null, error: null as Error | null };
    try {
      return {
        bundle: buildVolumeComparison(frame, {
          channel: comparisonUrl.channel,
          quality: comparisonUrl.quality,
          threshold: comparisonUrl.threshold,
          horizonSeconds: HORIZON_SECONDS,
          maxVoxels: maxVoxelsForQuality(comparisonUrl.quality),
          leadSeconds: comparisonUrl.leadSeconds,
        }),
        error: null as Error | null,
      };
    } catch (reason: unknown) {
      return {
        bundle: null,
        error:
          reason instanceof Error
            ? reason
            : new Error("The publication comparison could not be evaluated."),
      };
    }
  }, [comparisonUrl, frame]);

  const cells = useMemo(
    () =>
      comparisonResult.bundle && !layer.error
        ? filterVolumeDifferenceCells(
            comparisonResult.bundle.difference.cells,
            temporalFilter,
            horizonSteps,
          )
        : [],
    [comparisonResult.bundle, horizonSteps, layer.error, temporalFilter],
  );

  if (data.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Preparing the publication plate"
        message="Reconstructing the exact evidence-aware comparison encoded in the URL."
      />
    );
  }
  if (data.error || !data.frames || !frame) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The publication source could not be loaded"
        message={data.error?.message ?? "Scenario frame data is unavailable."}
        onRetry={data.retry}
      />
    );
  }
  if (layer.error) {
    return (
      <div className="page-pad">
        <FeedbackState
          kind="unsupported_comparison"
          title="Publication figure mode requires an exact temporal slice"
          message={`${layer.error.message} Use tm=slice&layer=<integer> so the paper figure has one unambiguous forecast time.`}
        />
        <Link className="text-link" to={`/volume/compare?${searchKey}`}>
          Return to the interactive comparison workbench →
        </Link>
      </div>
    );
  }
  if (comparisonResult.error) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The publication comparison failed closed"
        message={comparisonResult.error.message}
      />
    );
  }
  if (!comparisonResult.bundle) {
    return (
      <FeedbackState
        kind="empty"
        title="No feasible earlier-run intervention exists at this frame"
        message="Publication mode will not invent a movement direction or substitute another comparison condition."
      />
    );
  }

  const forecastSeconds = horizonSecondsForLayer(
    layer.layerIndex,
    horizonSteps,
    HORIZON_SECONDS,
  );
  const evidenceStatus = sourceEvidenceStatus(
    frame.metadata,
    data.scenario?.evidence_status,
  );

  return (
    <div className="difference-publication-page" data-publication-mode="figure">
      <DifferencePublicationPlate
        scenarioId={scenarioId}
        scenarioTitle={data.scenario?.title ?? scenarioId}
        frameId={frame.frame_id}
        frameIndex={frameIndex}
        timestampSeconds={frame.timestamp_s}
        sourceEvidenceStatus={evidenceStatus}
        channel={comparisonUrl.channel}
        quality={comparisonUrl.quality}
        threshold={comparisonUrl.threshold}
        layerIndex={layer.layerIndex}
        forecastSeconds={forecastSeconds}
        pitchLength={frame.pitch_length}
        pitchWidth={frame.pitch_width}
        intervention={comparisonResult.bundle.intervention}
        difference={comparisonResult.bundle.difference}
        cells={cells}
      />
      <div className="publication-screen-actions">
        <Link className="text-link" to={`/volume/compare?${new URLSearchParams([...searchParams].filter(([key]) => key !== "pub")).toString()}`}>
          Return to interactive workbench →
        </Link>
      </div>
    </div>
  );
}
