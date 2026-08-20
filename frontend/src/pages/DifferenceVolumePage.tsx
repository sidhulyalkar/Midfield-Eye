import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { FeedbackState } from "../components/FeedbackState";
import { useScenarioBundle } from "../data/hooks";
import { defaultVolumeConfig } from "../visualization/affordanceVolume";
import { DifferenceCandidateEvidencePanel } from "../visualization/DifferenceCandidateEvidencePanel";
import {
  DifferenceVolume3D,
  type DifferenceVolumeRuntime,
} from "../visualization/DifferenceVolume3D";
import { LinkedDifferenceSlice } from "../visualization/LinkedDifferenceSlice";
import type { VolumeComparisonChannel } from "../visualization/volumeComparison";
import {
  EARLIER_RUN_LEAD_PRESETS,
  parseComparisonFrameIndex,
  parseVolumeComparisonUrl,
  writeComparisonFrameIndex,
  writeVolumeComparisonUrl,
  type DeterministicComparisonQuality,
  type EarlierRunLeadSeconds,
} from "../visualization/volumeComparisonUrl";
import { inspectVolumeDifferenceCell } from "../visualization/volumeDifferenceInspector";
import { buildVolumeDifferenceRenderPayload } from "../visualization/volumeDifferenceRender";
import {
  differenceInspectionFilename,
  serializeDifferenceInspection,
} from "../visualization/volumeDifferenceSerialization";
import { filterVolumeDifferenceCells } from "../visualization/volumeDifferenceView";
import {
  addTemporalGuideRails,
  horizonSecondsForLayer,
  temporalFilterLabel,
  type VolumeTemporalFilter,
} from "../visualization/volumeTemporal";
import {
  parseTemporalFilterFromSearchParams,
  writeTemporalFilterToSearchParams,
} from "../visualization/volumeUrlState";
import { useVolumeComparisonBundle } from "../visualization/useVolumeComparisonBundle";

const HORIZON_SECONDS = 1.5;
const comparisonChannels: readonly VolumeComparisonChannel[] = [
  "future_space",
  "option_creation",
  "passing_corridors",
  "menu",
];
const deterministicQualities: readonly DeterministicComparisonQuality[] = [
  "low",
  "medium",
  "high",
];

const channelCopy: Record<
  VolumeComparisonChannel,
  {
    label: string;
    short: string;
    explanation: string;
    evidence: "STATE" | "REGENERATED";
  }
> = {
  future_space: {
    label: "Future space",
    short: "SPACE",
    evidence: "STATE",
    explanation:
      "How openness changes under focal-state motion when one off-ball teammate is placed farther along the run they are already making.",
  },
  option_creation: {
    label: "Option creation",
    short: "CREATE",
    evidence: "STATE",
    explanation:
      "Where future openness improves relative to the focal slice after the same earlier-run teaching intervention.",
  },
  passing_corridors: {
    label: "Passing corridors",
    short: "CORRIDORS",
    evidence: "REGENERATED",
    explanation:
      "How candidate-aligned pass/carry tubes change when Condition B uses a Python AffordanceEngine menu regenerated from the alternative frame.",
  },
  menu: {
    label: "Action menu composite",
    short: "MENU",
    evidence: "REGENERATED",
    explanation:
      "How the composite tactical field changes when A uses the frozen authoritative menu and B uses independently regenerated counterfactual candidates.",
  },
};

type ComparisonSelection = {
  key: string;
  fingerprint: string;
};

function maxVoxelsForQuality(quality: DeterministicComparisonQuality) {
  if (quality === "low") return 1200;
  if (quality === "high") return 4200;
  return 2800;
}

function formatDelta(value: number | null) {
  if (value === null) return "not defined";
  return `${value >= 0 ? "+" : ""}${value.toFixed(4)}`;
}

export default function DifferenceVolumePage() {
  const [searchParams, setSearchParams] = useSearchParams();
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
  const frameCount = data.frames?.length ?? 0;
  const defaultFrameIndex = data.scenario?.key_frame_index ?? 10;
  const frameIndex = parseComparisonFrameIndex(
    new URLSearchParams(searchKey),
    frameCount,
    defaultFrameIndex,
  );
  const frame = data.frames?.[frameIndex];
  const [selection, setSelection] = useState<ComparisonSelection | null>(null);
  const [runtime, setRuntime] = useState<DifferenceVolumeRuntime | null>(null);
  const comparisonResult = useVolumeComparisonBundle({
    scenarioId,
    frame,
    scenarioOptions: data.options,
    channel: comparisonUrl.channel,
    quality: comparisonUrl.quality,
    threshold: comparisonUrl.threshold,
    horizonSeconds: HORIZON_SECONDS,
    maxVoxels: maxVoxelsForQuality(comparisonUrl.quality),
    leadSeconds: comparisonUrl.leadSeconds,
  });

  useEffect(() => {
    if (!frameCount) return;
    let next = writeVolumeComparisonUrl(
      new URLSearchParams(searchKey),
      comparisonUrl,
    );
    next = writeComparisonFrameIndex(next, frameIndex);
    next = writeTemporalFilterToSearchParams(next, temporalFilter);
    next.set("scenario", scenarioId);
    if (next.toString() !== searchKey) {
      setSearchParams(next, { replace: true });
    }
  }, [
    comparisonUrl,
    frameCount,
    frameIndex,
    scenarioId,
    searchKey,
    setSearchParams,
    temporalFilter,
  ]);

  const visibleCells = useMemo(
    () =>
      comparisonResult.bundle
        ? filterVolumeDifferenceCells(
            comparisonResult.bundle.difference.cells,
            temporalFilter,
            horizonSteps,
          )
        : [],
    [comparisonResult.bundle, horizonSteps, temporalFilter],
  );
  const renderPayload = useMemo(
    () => buildVolumeDifferenceRenderPayload(visibleCells),
    [visibleCells],
  );
  const candidateFingerprint =
    comparisonResult.bundle?.candidateEvidence.mode ===
    "regenerated_counterfactual_candidates"
      ? comparisonResult.bundle.candidateEvidence.provenance.configSha256
      : "state-only";
  const comparisonFingerprint = [
    scenarioId,
    frame?.frame_id ?? "no-frame",
    comparisonUrl.channel,
    comparisonUrl.leadSeconds.toFixed(2),
    comparisonUrl.quality,
    comparisonUrl.threshold.toFixed(3),
    HORIZON_SECONDS.toFixed(2),
    horizonSteps,
    maxVoxelsForQuality(comparisonUrl.quality),
    candidateFingerprint,
  ].join("|");
  const activeSelectedKey =
    selection?.fingerprint === comparisonFingerprint &&
    visibleCells.some((cell) => cell.key === selection.key)
      ? selection.key
      : null;
  const inspection =
    activeSelectedKey && comparisonResult.bundle
      ? inspectVolumeDifferenceCell(
          comparisonResult.bundle.difference,
          activeSelectedKey,
        )
      : null;
  const sliceSeconds =
    temporalFilter.mode === "slice"
      ? horizonSecondsForLayer(
          temporalFilter.layerIndex,
          horizonSteps,
          HORIZON_SECONDS,
        )
      : null;
  const renderSolids = comparisonResult.bundle
    ? addTemporalGuideRails(
        comparisonResult.bundle.baselineScene,
        temporalFilter,
        frame?.pitch_length ?? 105,
        frame?.pitch_width ?? 68,
      ).solids
    : new Float32Array();

  const intersectionDeltas = visibleCells.flatMap((cell) =>
    cell.support === "intersection" && cell.delta !== null ? [cell.delta] : [],
  );
  const meanSignedDelta = intersectionDeltas.length
    ? intersectionDeltas.reduce((sum, value) => sum + value, 0) /
      intersectionDeltas.length
    : null;
  const meanAbsoluteDelta = intersectionDeltas.length
    ? intersectionDeltas.reduce((sum, value) => sum + Math.abs(value), 0) /
      intersectionDeltas.length
    : null;
  const supportOverlap = visibleCells.length
    ? renderPayload.stats.intersectionCells / visibleCells.length
    : 0;

  const selectKey = (key: string | null) => {
    setSelection(key ? { key, fingerprint: comparisonFingerprint } : null);
  };

  const writeComparisonState = (
    patch: Partial<{
      channel: VolumeComparisonChannel;
      leadSeconds: EarlierRunLeadSeconds;
      quality: DeterministicComparisonQuality;
      threshold: number;
    }>,
  ) => {
    const next = writeVolumeComparisonUrl(searchParams, {
      ...comparisonUrl,
      ...patch,
    });
    setSelection(null);
    setSearchParams(next, { replace: true });
  };

  const writeTemporalFilter = (nextFilter: VolumeTemporalFilter) => {
    setSearchParams(
      writeTemporalFilterToSearchParams(searchParams, nextFilter),
      { replace: true },
    );
  };

  const writeFrameIndex = (nextFrameIndex: number) => {
    setSelection(null);
    setSearchParams(writeComparisonFrameIndex(searchParams, nextFrameIndex), {
      replace: true,
    });
  };

  const exportInspection = () => {
    if (!inspection || !comparisonResult.bundle || !frame) return;
    const record = serializeDifferenceInspection(
      scenarioId,
      frame.frame_id,
      comparisonUrl.channel,
      temporalFilter,
      inspection,
      comparisonResult.bundle.intervention,
      comparisonResult.bundle.candidateEvidence,
    );
    const blob = new Blob([`${JSON.stringify(record, null, 2)}\n`], {
      type: "application/json",
    });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = differenceInspectionFilename(
      scenarioId,
      frame.frame_id,
      comparisonUrl.channel,
      inspection.key,
    );
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(href), 0);
  };

  if (data.isPending || comparisonResult.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title={
          comparisonResult.requiresRegeneratedCandidates
            ? "Validating regenerated candidate evidence"
            : "Building the evidence-aware comparison"
        }
        message={
          comparisonResult.requiresRegeneratedCandidates
            ? "Loading the frozen Python A/B candidate artifact, validating semantic identity and intervention parity, then constructing matched retained scenes."
            : "Constructing two matched retained scenes from the same focal state."
        }
      />
    );
  }
  if (data.error || !frame || !data.frames) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The comparison workbench could not open"
        message={data.error?.message ?? "Scenario frame data is unavailable."}
        onRetry={data.retry}
      />
    );
  }
  if (comparisonResult.error) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title={
          comparisonResult.requiresRegeneratedCandidates
            ? "Regenerated candidate comparison failed closed"
            : "The two retained scenes are not comparable"
        }
        message={comparisonResult.error.message}
      />
    );
  }
  if (!comparisonResult.bundle) {
    return (
      <FeedbackState
        kind="empty"
        title="No earlier-run intervention is available at this frame"
        message="No off-ball possession teammate has enough finite focal-state motion to construct the teaching intervention without inventing a direction. Choose another frame."
      />
    );
  }

  const { intervention, difference, candidateEvidence } = comparisonResult.bundle;
  const layerIndices = Array.from({ length: horizonSteps }, (_, index) => index);
  const copy = channelCopy[comparisonUrl.channel];
  const regenerated =
    candidateEvidence.mode === "regenerated_counterfactual_candidates";

  return (
    <div className="difference-page page-pad">
      <header className="difference-page-heading">
        <div>
          <p className="eyebrow">V1.4 · EVIDENCE-AWARE DIFFERENCE VOLUME</p>
          <h1>Compare what changed without turning missing evidence into zero.</h1>
          <p>
            Condition A is the focal frame. Condition B places one off-ball
            teammate where their existing velocity would put them if the same
            run had begun {intervention.leadSeconds.toFixed(2)} seconds earlier.
            The two conditions use the same grid, threshold, voxel budget, and
            forecast contract.
          </p>
        </div>
        <div className="difference-claim-card">
          <strong>
            {regenerated
              ? "Regenerated candidates, not causal evidence"
              : "Teaching intervention, not causal evidence"}
          </strong>
          <span>
            {regenerated
              ? "A uses the frozen authoritative showcase candidates. B uses Python AffordanceEngine candidates regenerated from the matched alternative frame. No later observed frame is used; these remain model-derived geometric option scores, not observed availability or causal effects."
              : "B is synthetic. No later observed frame is used. Future Space and Option Creation remain state-derived and omit candidate pass scores on both sides."}
          </span>
        </div>
      </header>

      <section className="difference-intervention-card">
        <div className="difference-intervention-copy">
          <p className="eyebrow">CONDITION B · EARLIER ARRIVAL</p>
          <h2>{intervention.playerId}</h2>
          <dl>
            <div>
              <dt>Current speed</dt>
              <dd>{intervention.speedMps.toFixed(2)} m/s</dd>
            </div>
            <div>
              <dt>Earlier by</dt>
              <dd>{intervention.leadSeconds.toFixed(2)} s</dd>
            </div>
            <div>
              <dt>Moved now</dt>
              <dd>{intervention.displacementM.toFixed(2)} m</dd>
            </div>
            <div>
              <dt>Position</dt>
              <dd>
                ({intervention.from[0].toFixed(1)}, {intervention.from[1].toFixed(1)})
                → ({intervention.to[0].toFixed(1)}, {intervention.to[1].toFixed(1)})
              </dd>
            </div>
          </dl>
        </div>
        <svg
          className="difference-intervention-pitch"
          viewBox={`0 0 ${frame.pitch_length} ${frame.pitch_width}`}
          role="img"
          aria-label={`${intervention.playerId} moves ${intervention.displacementM.toFixed(2)} metres along their focal-state velocity`}
        >
          <rect x={0} y={0} width={frame.pitch_length} height={frame.pitch_width} />
          <line
            x1={intervention.from[0]}
            y1={intervention.from[1]}
            x2={intervention.to[0]}
            y2={intervention.to[1]}
          />
          <circle
            className="is-before"
            cx={intervention.from[0]}
            cy={intervention.from[1]}
            r={1.5}
          />
          <circle
            className="is-after"
            cx={intervention.to[0]}
            cy={intervention.to[1]}
            r={1.8}
          />
        </svg>
      </section>

      <section className="difference-workbench">
        <div className="difference-stage">
          <div className="difference-stage-topline">
            <div>
              <span>{data.scenario?.title ?? scenarioId}</span>
              <strong>{copy.label}</strong>
            </div>
            <div>
              <span>Frame {frame.frame_id}</span>
              <strong>{frame.timestamp_s.toFixed(2)} s</strong>
            </div>
          </div>
          <DifferenceVolume3D
            solids={renderSolids}
            payload={renderPayload}
            selectedKey={activeSelectedKey}
            onSelectKey={selectKey}
            onRuntime={setRuntime}
          />
          {temporalFilter.mode === "slice" && sliceSeconds !== null ? (
            <LinkedDifferenceSlice
              cells={renderPayload.cells}
              pitchLength={frame.pitch_length}
              pitchWidth={frame.pitch_width}
              layerIndex={temporalFilter.layerIndex}
              forecastSeconds={sliceSeconds}
              selectedKey={activeSelectedKey}
              onSelectKey={(key) => selectKey(key)}
            />
          ) : null}
          <label className="difference-frame-scrubber">
            <span>Focal frame</span>
            <input
              type="range"
              min={0}
              max={Math.max(0, data.frames.length - 1)}
              value={frameIndex}
              onChange={(event) => writeFrameIndex(Number(event.target.value))}
            />
            <output>
              {frame.frame_id} · {frame.timestamp_s.toFixed(2)} s
            </output>
          </label>
        </div>

        <aside className="difference-controls">
          <section className="difference-control-card">
            <p className="eyebrow">COMPARISON FIELD</p>
            <div className="difference-button-grid">
              {comparisonChannels.map((channel) => (
                <button
                  type="button"
                  key={channel}
                  aria-pressed={comparisonUrl.channel === channel}
                  onClick={() => writeComparisonState({ channel })}
                >
                  <strong>{channelCopy[channel].short}</strong>
                  <span>{channelCopy[channel].label}</span>
                  <small>{channelCopy[channel].evidence}</small>
                </button>
              ))}
            </div>
            <p>{copy.explanation}</p>
            <p className="difference-evidence-mode">
              {regenerated
                ? "Validated regenerated A/B candidate tables are active."
                : "State-only comparison: candidate options are absent from both sides."}
            </p>
          </section>

          <section className="difference-control-card">
            <p className="eyebrow">EARLIER-RUN LEAD</p>
            <div className="difference-inline-buttons">
              {EARLIER_RUN_LEAD_PRESETS.map((leadSeconds) => (
                <button
                  type="button"
                  key={leadSeconds}
                  aria-pressed={comparisonUrl.leadSeconds === leadSeconds}
                  onClick={() => writeComparisonState({ leadSeconds })}
                >
                  {leadSeconds.toFixed(2)} s
                </button>
              ))}
            </div>
          </section>

          <section className="difference-control-card">
            <p className="eyebrow">DETERMINISTIC LOD</p>
            <div className="difference-inline-buttons">
              {deterministicQualities.map((quality) => (
                <button
                  type="button"
                  key={quality}
                  aria-pressed={comparisonUrl.quality === quality}
                  onClick={() => writeComparisonState({ quality })}
                >
                  {quality}
                </button>
              ))}
            </div>
            <label className="difference-threshold">
              <span>Retention threshold {comparisonUrl.threshold.toFixed(3)}</span>
              <input
                aria-label="Difference retention threshold"
                type="range"
                min={0.05}
                max={0.65}
                step={0.025}
                value={comparisonUrl.threshold}
                onChange={(event) =>
                  writeComparisonState({ threshold: Number(event.target.value) })
                }
              />
            </label>
          </section>

          <section
            className="difference-control-card"
            data-testid="difference-temporal-controls"
          >
            <p className="eyebrow">TEMPORAL CUT</p>
            <strong>
              {temporalFilterLabel(
                temporalFilter,
                horizonSteps,
                HORIZON_SECONDS,
              )}
            </strong>
            <div className="difference-inline-buttons">
              <button
                type="button"
                aria-pressed={temporalFilter.mode === "full"}
                onClick={() => writeTemporalFilter({ mode: "full" })}
              >
                Full
              </button>
              <button
                type="button"
                aria-pressed={temporalFilter.mode === "slice"}
                onClick={() =>
                  writeTemporalFilter({ mode: "slice", layerIndex: 2 })
                }
              >
                Slice
              </button>
              <button
                type="button"
                aria-pressed={temporalFilter.mode === "band"}
                onClick={() =>
                  writeTemporalFilter({
                    mode: "band",
                    startLayerIndex: 1,
                    endLayerIndex: 4,
                  })
                }
              >
                Band
              </button>
            </div>
            {temporalFilter.mode === "slice" ? (
              <div className="difference-layer-grid">
                {layerIndices.map((layerIndex) => (
                  <button
                    type="button"
                    key={layerIndex}
                    aria-pressed={temporalFilter.layerIndex === layerIndex}
                    onClick={() =>
                      writeTemporalFilter({ mode: "slice", layerIndex })
                    }
                  >
                    +
                    {horizonSecondsForLayer(
                      layerIndex,
                      horizonSteps,
                      HORIZON_SECONDS,
                    ).toFixed(2)}
                  </button>
                ))}
              </div>
            ) : null}
            {temporalFilter.mode === "band" ? (
              <div className="difference-band-grid">
                <label>
                  Start
                  <select
                    aria-label="Difference band start layer"
                    value={temporalFilter.startLayerIndex}
                    onChange={(event) => {
                      const startLayerIndex = Number(event.target.value);
                      writeTemporalFilter({
                        mode: "band",
                        startLayerIndex,
                        endLayerIndex: Math.max(
                          startLayerIndex,
                          temporalFilter.endLayerIndex,
                        ),
                      });
                    }}
                  >
                    {layerIndices.map((layerIndex) => (
                      <option key={layerIndex} value={layerIndex}>
                        +
                        {horizonSecondsForLayer(
                          layerIndex,
                          horizonSteps,
                          HORIZON_SECONDS,
                        ).toFixed(2)}{" "}
                        s
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  End
                  <select
                    aria-label="Difference band end layer"
                    value={temporalFilter.endLayerIndex}
                    onChange={(event) => {
                      const endLayerIndex = Number(event.target.value);
                      writeTemporalFilter({
                        mode: "band",
                        startLayerIndex: Math.min(
                          temporalFilter.startLayerIndex,
                          endLayerIndex,
                        ),
                        endLayerIndex,
                      });
                    }}
                  >
                    {layerIndices.map((layerIndex) => (
                      <option key={layerIndex} value={layerIndex}>
                        +
                        {horizonSecondsForLayer(
                          layerIndex,
                          horizonSteps,
                          HORIZON_SECONDS,
                        ).toFixed(2)}{" "}
                        s
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : null}
          </section>

          <section className="difference-summary-card" aria-live="polite">
            <p className="eyebrow">VISIBLE SUPPORT</p>
            <dl>
              <div>
                <dt>Shared support</dt>
                <dd>{renderPayload.stats.intersectionCells}</dd>
              </div>
              <div>
                <dt>A-only rails</dt>
                <dd>{renderPayload.stats.leftOnlyCells}</dd>
              </div>
              <div>
                <dt>B-only rails</dt>
                <dd>{renderPayload.stats.rightOnlyCells}</dd>
              </div>
              <div>
                <dt>Support overlap</dt>
                <dd>{(supportOverlap * 100).toFixed(1)}%</dd>
              </div>
              <div>
                <dt>Mean B−A</dt>
                <dd>{formatDelta(meanSignedDelta)}</dd>
              </div>
              <div>
                <dt>Mean |Δ|</dt>
                <dd>{meanAbsoluteDelta?.toFixed(4) ?? "not defined"}</dd>
              </div>
              <div>
                <dt>GPU field instances</dt>
                <dd>{runtime?.renderer.fieldInstances ?? 0}</dd>
              </div>
              <div>
                <dt>Draw calls</dt>
                <dd>{runtime?.renderer.drawCalls ?? 0}</dd>
              </div>
              {regenerated ? (
                <>
                  <div>
                    <dt>Candidate union</dt>
                    <dd>{candidateEvidence.supportSummary.union}</dd>
                  </div>
                  <div>
                    <dt>Generator config</dt>
                    <dd>{candidateEvidence.provenance.configSha256.slice(0, 12)}…</dd>
                  </div>
                </>
              ) : null}
            </dl>
          </section>
        </aside>
      </section>

      <section className="difference-lower-grid">
        <article className="difference-legend-card">
          <p className="eyebrow">SUPPORT GRAMMAR</p>
          <h2>Color says direction. Shape says whether a number exists.</h2>
          <ul>
            <li>
              <i className="legend-filled positive" /> Filled mint: shared
              support, B−A &gt; 0.
            </li>
            <li>
              <i className="legend-filled negative" /> Filled coral: shared
              support, B−A &lt; 0.
            </li>
            <li>
              <i className="legend-rails vertical" /> Vertical gold rails:
              retained only in A, no numeric Δ.
            </li>
            <li>
              <i className="legend-rails horizontal" /> Horizontal blue rails:
              retained only in B, no numeric Δ.
            </li>
          </ul>
        </article>

        <article
          className={`difference-inspector-card ${inspection ? "has-selection" : "is-empty"}`}
          data-testid="difference-inspector"
        >
          <p className="eyebrow">DIFFERENCE FORENSICS</p>
          {inspection ? (
            <>
              <div className="difference-inspector-title">
                <h2>{inspection.key}</h2>
                <strong>{inspection.support.replaceAll("_", " ")}</strong>
              </div>
              <dl>
                <div>
                  <dt>Condition A</dt>
                  <dd>
                    {inspection.conditionA.retained
                      ? `${inspection.conditionA.value?.toFixed(4)} · ${inspection.conditionA.voxelId}`
                      : "not retained"}
                  </dd>
                </div>
                <div>
                  <dt>Condition B</dt>
                  <dd>
                    {inspection.conditionB.retained
                      ? `${inspection.conditionB.value?.toFixed(4)} · ${inspection.conditionB.voxelId}`
                      : "not retained"}
                  </dd>
                </div>
                <div>
                  <dt>B−A</dt>
                  <dd>{formatDelta(inspection.delta)}</dd>
                </div>
                <div>
                  <dt>Numerical comparison</dt>
                  <dd>
                    {inspection.numericComparisonAvailable
                      ? "valid on retained intersection"
                      : "not defined for one-sided support"}
                  </dd>
                </div>
              </dl>
              <p>
                One-sided presence is not zero. Missing support is not
                interpolated. Intensity is not calibrated probability, and no
                future observed frame is used.
              </p>
              <div className="difference-inspector-actions">
                <button type="button" onClick={() => selectKey(null)}>
                  Clear
                </button>
                <button
                  type="button"
                  onClick={exportInspection}
                  data-testid="export-difference-json"
                >
                  Export comparison JSON
                </button>
              </div>
            </>
          ) : (
            <p>
              Click a 3D cell, use the linked slice, or choose the most
              informative visible cell. A comparison number appears only when
              both conditions retained the same canonical cell.
            </p>
          )}
        </article>
      </section>

      <DifferenceCandidateEvidencePanel
        evidence={candidateEvidence}
        inspection={inspection}
      />

      <section className="difference-publication-strip">
        <div>
          <p className="eyebrow">REPRODUCIBLE STATE</p>
          <h2>
            One URL now identifies the frame, intervention, field, lattice, and
            temporal cut.
          </h2>
        </div>
        <code>{`scenario=${scenarioId} · fi=${frameIndex} · cmp=earlier-run · lead=${comparisonUrl.leadSeconds.toFixed(2)} · dc=${comparisonUrl.channel} · dq=${comparisonUrl.quality} · dt=${comparisonUrl.threshold.toFixed(3)}`}</code>
        <p>
          Full difference summary: {difference.summary.intersection} shared, {" "}
          {difference.summary.leftOnly} A-only, {difference.summary.rightOnly}{" "}
          B-only, {difference.summary.neither} retained in neither condition.
        </p>
        {regenerated ? (
          <p>
            Regenerated candidate provenance: {candidateEvidence.provenance.generatorName}{" "}
            {candidateEvidence.provenance.packageVersion} · config {" "}
            {candidateEvidence.provenance.configSha256}.
          </p>
        ) : null}
        <Link className="text-link" to={`/volume?scenario=${scenarioId}`}>
          Return to the single-condition Temporal Affordance Volume →
        </Link>
      </section>
    </div>
  );
}
