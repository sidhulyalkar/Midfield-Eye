import type {
  VolumeDifference,
  VolumeDifferenceCell,
} from "./volumeDifference";
import type { DeterministicComparisonQuality } from "./volumeComparisonUrl";
import type { EarlierRunIntervention } from "./volumeIntervention";
import {
  assertPublicationDifferenceMatches,
  differencePublicationFigureId,
  selectDifferenceFailureGallery,
  summarizeDifferencePublication,
} from "./volumePublication";

export type DifferencePublicationPlateProps = {
  scenarioId: string;
  scenarioTitle: string;
  frameId: number;
  frameIndex: number;
  timestampSeconds: number;
  sourceEvidenceStatus: string;
  channel: "future_space" | "option_creation";
  quality: DeterministicComparisonQuality;
  threshold: number;
  layerIndex: number;
  forecastSeconds: number;
  pitchLength: number;
  pitchWidth: number;
  intervention: EarlierRunIntervention;
  difference: VolumeDifference;
  cells: readonly VolumeDifferenceCell[];
};

function sourceVoxel(cell: VolumeDifferenceCell) {
  return cell.left ?? cell.right;
}

function formatDelta(value: number | null, digits = 4) {
  if (value === null) return "not defined";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function supportLabel(cell: VolumeDifferenceCell) {
  if (cell.support === "intersection") {
    if (cell.delta === null) return "Shared support · malformed delta";
    if (cell.delta > 0) {
      return `Shared support · B−A ${formatDelta(cell.delta)}`;
    }
    if (cell.delta < 0) {
      return `Shared support · B−A ${formatDelta(cell.delta)}`;
    }
    return "Shared support · B−A 0.0000";
  }
  return cell.support === "left_only"
    ? "A-only retained evidence · no numerical delta"
    : "B-only retained evidence · no numerical delta";
}

function DifferenceSliceGlyph({ cell }: { cell: VolumeDifferenceCell }) {
  const voxel = sourceVoxel(cell);
  if (!voxel) return null;
  const x = voxel.pitchX - voxel.sizeX / 2;
  const y = voxel.pitchY - voxel.sizeZ / 2;
  const marker =
    cell.support !== "intersection"
      ? null
      : cell.delta === null
        ? "?"
        : cell.delta > 0
          ? "+"
          : cell.delta < 0
            ? "−"
            : "0";

  if (cell.support === "left_only") {
    const rail = Math.max(0.18, voxel.sizeX * 0.13);
    return (
      <g
        className="publication-cell publication-left-only"
        aria-label={supportLabel(cell)}
      >
        <rect
          x={voxel.pitchX - voxel.sizeX * 0.28 - rail / 2}
          y={y + voxel.sizeZ * 0.08}
          width={rail}
          height={voxel.sizeZ * 0.84}
        />
        <rect
          x={voxel.pitchX + voxel.sizeX * 0.28 - rail / 2}
          y={y + voxel.sizeZ * 0.08}
          width={rail}
          height={voxel.sizeZ * 0.84}
        />
      </g>
    );
  }

  if (cell.support === "right_only") {
    const rail = Math.max(0.18, voxel.sizeZ * 0.13);
    return (
      <g
        className="publication-cell publication-right-only"
        aria-label={supportLabel(cell)}
      >
        <rect
          x={x + voxel.sizeX * 0.08}
          y={voxel.pitchY - voxel.sizeZ * 0.28 - rail / 2}
          width={voxel.sizeX * 0.84}
          height={rail}
        />
        <rect
          x={x + voxel.sizeX * 0.08}
          y={voxel.pitchY + voxel.sizeZ * 0.28 - rail / 2}
          width={voxel.sizeX * 0.84}
          height={rail}
        />
      </g>
    );
  }

  const signClass =
    (cell.delta ?? 0) > 0
      ? "is-positive"
      : (cell.delta ?? 0) < 0
        ? "is-negative"
        : "is-zero";
  return (
    <g
      className={`publication-cell publication-intersection ${signClass}`}
      aria-label={supportLabel(cell)}
    >
      <rect
        x={x + voxel.sizeX * 0.08}
        y={y + voxel.sizeZ * 0.08}
        width={voxel.sizeX * 0.84}
        height={voxel.sizeZ * 0.84}
      />
      <text
        x={voxel.pitchX}
        y={voxel.pitchY}
        textAnchor="middle"
        dominantBaseline="central"
      >
        {marker}
      </text>
    </g>
  );
}

function FailureCard({
  title,
  cell,
}: {
  title: string;
  cell: VolumeDifferenceCell | null;
}) {
  if (!cell) {
    return (
      <article className="publication-failure-card is-empty">
        <strong>{title}</strong>
        <p>No representative one-sided cell exists in this exact slice.</p>
      </article>
    );
  }
  const retained = cell.left ?? cell.right;
  return (
    <article className="publication-failure-card">
      <strong>{title}</strong>
      <code>{cell.key}</code>
      <dl>
        <div>
          <dt>Support</dt>
          <dd>{cell.support.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>Retained value</dt>
          <dd>{retained?.value.toFixed(4) ?? "unavailable"}</dd>
        </div>
        <div>
          <dt>B−A</dt>
          <dd>not defined</dd>
        </div>
      </dl>
      <p>
        No numerical delta. This condition retained evidence here while the
        other did not.
      </p>
    </article>
  );
}

export function DifferencePublicationPlate({
  scenarioId,
  scenarioTitle,
  frameId,
  frameIndex,
  timestampSeconds,
  sourceEvidenceStatus,
  channel,
  quality,
  threshold,
  layerIndex,
  forecastSeconds,
  pitchLength,
  pitchWidth,
  intervention,
  difference,
  cells,
}: DifferencePublicationPlateProps) {
  assertPublicationDifferenceMatches(difference, cells);
  if (cells.some((cell) => cell.layerIndex !== layerIndex)) {
    throw new Error(
      "Publication plate received cells outside its exact temporal slice.",
    );
  }
  const figureId = differencePublicationFigureId({
    scenarioId,
    frameIndex,
    channel,
    layerIndex,
    leadSeconds: intervention.leadSeconds,
    quality,
    threshold,
  });
  const summary = summarizeDifferencePublication(cells);
  const failures = selectDifferenceFailureGallery(cells);
  const channelLabel =
    channel === "future_space" ? "Future Space" : "Option Creation";

  return (
    <article
      className="difference-publication-plate"
      data-testid="difference-publication-plate"
      data-figure-id={figureId}
    >
      <header className="publication-header">
        <div>
          <p className="publication-kicker">
            THE MIDFIELDER&apos;S EYE · TEMPORAL AFFORDANCE DIFFERENCE VOLUME
          </p>
          <h1>{channelLabel}: what changes when the run starts earlier?</h1>
          <p>
            {scenarioTitle} · frame {frameId} · {timestampSeconds.toFixed(2)} s ·
            exact slice +{forecastSeconds.toFixed(2)} s
          </p>
        </div>
        <div className="publication-id-block">
          <span>Figure ID</span>
          <code>{figureId}</code>
          <span>Source evidence</span>
          <strong>{sourceEvidenceStatus.replaceAll("_", " ")}</strong>
        </div>
      </header>

      <div className="publication-panel-grid">
        <section className="publication-panel publication-intervention-panel">
          <header>
            <span aria-hidden="true">1</span>
            <div>
              <strong>Teaching intervention</strong>
              <small>Same focal state, one earlier positional arrival</small>
            </div>
          </header>
          <svg
            viewBox={`0 0 ${pitchLength} ${pitchWidth}`}
            role="img"
            aria-label={`${intervention.playerId} moved ${intervention.displacementM.toFixed(2)} metres along existing focal-state velocity`}
          >
            <rect
              className="publication-pitch"
              x={0}
              y={0}
              width={pitchLength}
              height={pitchWidth}
            />
            <line
              className="publication-midline"
              x1={pitchLength / 2}
              y1={0}
              x2={pitchLength / 2}
              y2={pitchWidth}
            />
            <line
              className="publication-intervention-vector"
              x1={intervention.from[0]}
              y1={intervention.from[1]}
              x2={intervention.to[0]}
              y2={intervention.to[1]}
            />
            <circle
              className="publication-before"
              cx={intervention.from[0]}
              cy={intervention.from[1]}
              r={1.6}
            />
            <circle
              className="publication-after"
              cx={intervention.to[0]}
              cy={intervention.to[1]}
              r={1.9}
            />
          </svg>
          <dl className="publication-compact-dl">
            <div>
              <dt>Player</dt>
              <dd>{intervention.playerId}</dd>
            </div>
            <div>
              <dt>Lead</dt>
              <dd>{intervention.leadSeconds.toFixed(2)} s</dd>
            </div>
            <div>
              <dt>Speed</dt>
              <dd>{intervention.speedMps.toFixed(2)} m/s</dd>
            </div>
            <div>
              <dt>Displacement</dt>
              <dd>{intervention.displacementM.toFixed(2)} m</dd>
            </div>
          </dl>
        </section>

        <section className="publication-panel publication-slice-panel">
          <header>
            <span aria-hidden="true">2</span>
            <div>
              <strong>Evidence-aware difference slice</strong>
              <small>
                B−A exists only where both conditions retained the same canonical
                cell
              </small>
            </div>
          </header>
          <svg
            className="publication-difference-slice"
            viewBox={`0 0 ${pitchLength} ${pitchWidth}`}
            role="img"
            aria-label={`${channelLabel} evidence-aware difference at +${forecastSeconds.toFixed(2)} seconds`}
          >
            <defs>
              <pattern
                id="publication-positive-hatch"
                width="2.2"
                height="2.2"
                patternUnits="userSpaceOnUse"
                patternTransform="rotate(35)"
              >
                <line x1="0" y1="0" x2="0" y2="2.2" />
              </pattern>
              <pattern
                id="publication-negative-hatch"
                width="2.2"
                height="2.2"
                patternUnits="userSpaceOnUse"
                patternTransform="rotate(-35)"
              >
                <line x1="0" y1="0" x2="0" y2="2.2" />
              </pattern>
            </defs>
            <rect
              className="publication-pitch"
              x={0}
              y={0}
              width={pitchLength}
              height={pitchWidth}
            />
            <line
              className="publication-midline"
              x1={pitchLength / 2}
              y1={0}
              x2={pitchLength / 2}
              y2={pitchWidth}
            />
            <circle
              className="publication-centre-circle"
              cx={pitchLength / 2}
              cy={pitchWidth / 2}
              r={9.15}
            />
            {cells.map((cell) => (
              <DifferenceSliceGlyph key={cell.key} cell={cell} />
            ))}
          </svg>
        </section>

        <section className="publication-panel publication-summary-panel">
          <header>
            <span aria-hidden="true">3</span>
            <div>
              <strong>Retained-support accounting</strong>
              <small>
                Summary is computed only from the exact records drawn in panel 2
              </small>
            </div>
          </header>
          <dl className="publication-stat-grid">
            <div>
              <dt>Shared support</dt>
              <dd>{summary.sharedSupport}</dd>
            </div>
            <div>
              <dt>A-only</dt>
              <dd>{summary.leftOnly}</dd>
            </div>
            <div>
              <dt>B-only</dt>
              <dd>{summary.rightOnly}</dd>
            </div>
            <div>
              <dt>Overlap</dt>
              <dd>{(summary.supportOverlap * 100).toFixed(1)}%</dd>
            </div>
            <div>
              <dt>Mean B−A</dt>
              <dd>{formatDelta(summary.meanSignedDelta)}</dd>
            </div>
            <div>
              <dt>Mean |Δ|</dt>
              <dd>{summary.meanAbsoluteDelta?.toFixed(4) ?? "not defined"}</dd>
            </div>
            <div>
              <dt>Max |Δ|</dt>
              <dd>{summary.maxAbsoluteDelta?.toFixed(4) ?? "not defined"}</dd>
            </div>
            <div>
              <dt>Visible union</dt>
              <dd>{summary.visibleCells}</dd>
            </div>
          </dl>
          <div className="publication-state-line">
            <span>{quality} grid</span>
            <span>threshold {threshold.toFixed(3)}</span>
            <span>layer {layerIndex}</span>
            <span>lead {intervention.leadSeconds.toFixed(2)} s</span>
          </div>
        </section>
      </div>

      <section
        className="publication-legend"
        aria-label="Grayscale-safe support legend"
      >
        <div className="publication-legend-item">
          <i className="legend-publication positive">+</i>
          <span>
            <strong>Shared, positive</strong>
            <small>filled + forward hatch + plus marker</small>
          </span>
        </div>
        <div className="publication-legend-item">
          <i className="legend-publication negative">−</i>
          <span>
            <strong>Shared, negative</strong>
            <small>filled + backward hatch + minus marker</small>
          </span>
        </div>
        <div className="publication-legend-item">
          <i className="legend-publication zero">0</i>
          <span>
            <strong>Shared, zero</strong>
            <small>filled + zero marker</small>
          </span>
        </div>
        <div className="publication-legend-item">
          <i className="legend-publication rails-a" />
          <span>
            <strong>A-only</strong>
            <small>vertical rails · no numerical delta</small>
          </span>
        </div>
        <div className="publication-legend-item">
          <i className="legend-publication rails-b" />
          <span>
            <strong>B-only</strong>
            <small>horizontal rails · no numerical delta</small>
          </span>
        </div>
      </section>

      <section className="publication-failure-gallery">
        <header>
          <p>WHY NOT ZERO-FILL?</p>
          <h2>
            One-sided support is evidence about retention, not a signed effect.
          </h2>
        </header>
        <div>
          <FailureCard
            title="Representative A-only cell"
            cell={failures.leftOnly}
          />
          <FailureCard
            title="Representative B-only cell"
            cell={failures.rightOnly}
          />
        </div>
      </section>

      <footer className="publication-claim-footer">
        <strong>B−A is defined only on retained intersection.</strong>
        <span>not_retained ≠ 0</span>
        <span>Missing support is not interpolated.</span>
        <span>
          Condition A source: {sourceEvidenceStatus.replaceAll("_", " ")}.
        </span>
        <span>
          Condition B: synthetic teaching intervention, not observed future truth
          or causal evidence.
        </span>
        <span>Candidate options included: false.</span>
        <span>Candidate options regenerated: false.</span>
        <span>Future observed frames used: false.</span>
        <span>
          Current comparison channels: state-derived Future Space / Option
          Creation only.
        </span>
      </footer>
    </article>
  );
}
