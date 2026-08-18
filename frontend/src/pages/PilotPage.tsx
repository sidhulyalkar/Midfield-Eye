import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { useDataSource } from "../app/providers";
import { FeedbackState } from "../components/FeedbackState";
import { PilotSchema, type PilotPayload } from "../data/pilotSchema";

const stageLabels: Record<PilotPayload["stage"], string> = {
  protocol_ready: "Protocol ready",
  needs_sequence_review: "Sequence review needed",
  sample_frozen: "Sample frozen",
  annotation_in_progress: "Annotation in progress",
  reliability_established: "Reliability established",
  reliability_not_established: "Reliability not established",
  needs_adjudication: "Adjudication needed",
  expert_pilot_frozen_needs_provider_review: "Expert pilot frozen",
  benchmark_ready: "Benchmark ready",
  benchmark_complete: "Benchmark complete",
};

const stratumLabels: Record<string, string> = {
  central_pressure: "Receipts under pressure",
  transition: "Transition",
  settled_possession: "Settled possession",
  wide_overload: "Wide / half-space",
  negative_control: "Negative control",
};

const modelLabels: Record<string, string> = {
  B0_naive: "B0 · Naive",
  B1_static: "B1 · Static geometry",
  B2_dynamic: "B2 · Dynamic geometry",
  "B2-V_viewpoint": "B2-V · Viewpoint",
  B3_learned: "B3 · Learned ranker",
};

async function fetchPilot(
  source: ReturnType<typeof useDataSource>,
): Promise<PilotPayload> {
  const manifest = await source.getManifest();
  const path =
    typeof manifest.pilot_path === "string"
      ? manifest.pilot_path
      : "pilot/index.json";
  const response = await fetch(source.assetUrl(path), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(
      `${response.status} ${response.statusText} while loading the R1 pilot`,
    );
  }
  return PilotSchema.parse(await response.json());
}

function formatMetric(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : value.toFixed(3);
}

function nextGate(pilot: PilotPayload): string {
  const incomplete = pilot.evidence_ladder.find((step) => !step.complete);
  return incomplete?.label ?? "R1 complete";
}

export default function PilotPage() {
  const source = useDataSource();
  const pilot = useQuery({
    queryKey: ["r1-pilot"],
    queryFn: () => fetchPilot(source),
  });

  if (pilot.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Opening the R1 evidence ledger"
        message="Checking which scientific gates have actually been satisfied…"
      />
    );
  }
  if (pilot.isError) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The R1 pilot could not be loaded"
        message={pilot.error.message}
        onRetry={() => void pilot.refetch()}
      />
    );
  }

  const data = pilot.data;
  const selectedSequences = data.sample.selected_sequences ?? 0;
  const targetSequences = data.sample.target_sequences ?? 10;
  const coverage = data.annotation.progress.candidate_coverage ?? 0;
  const modelRows = Object.entries(data.benchmark.metrics);

  return (
    <div className="pilot-page">
      <section className="pilot-hero">
        <div className="pilot-hero-copy">
          <p className="eyebrow">R1 · FIRST REAL-EVIDENCE GATE</p>
          <h1>Can we predict the menu, not just the move?</h1>
          <p className="pilot-question">{data.question}</p>
          <div className="pilot-status-row">
            <span className={`pilot-stage pilot-stage-${data.stage}`}>
              {stageLabels[data.stage]}
            </span>
            <span className="pilot-next-gate">
              Next gate · {nextGate(data)}
            </span>
          </div>
        </div>
        <aside className="pilot-claim-card" aria-label="Current claim boundary">
          <p className="eyebrow">CURRENT CLAIM BOUNDARY</p>
          <strong>
            {data.claim_state === "empirical_benchmark_complete"
              ? "Real benchmark evidence is available."
              : "No empirical model result yet."}
          </strong>
          <p>
            Missing evidence stays missing. Synthetic showcase scenarios never
            fill a blank reliability score or benchmark metric.
          </p>
        </aside>
      </section>

      <section className="pilot-ladder" aria-labelledby="pilot-ladder-title">
        <header>
          <div>
            <p className="eyebrow">THE EVIDENCE LADDER</p>
            <h2 id="pilot-ladder-title">
              Five locks between an idea and a claim.
            </h2>
          </div>
          <p>
            Each rung must be satisfied in order. A failed reliability result is
            a result, not an invitation to tune the threshold.
          </p>
        </header>
        <ol>
          {data.evidence_ladder.map((step, index) => (
            <li
              className={step.complete ? "is-complete" : "is-pending"}
              key={step.id}
            >
              <span className="pilot-step-number">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <strong>{step.label}</strong>
                <p>{step.detail}</p>
              </div>
              <span className="pilot-step-state">
                {step.complete ? "locked" : "open"}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="pilot-design-grid">
        <article className="pilot-panel pilot-sample-panel">
          <p className="eyebrow">FROZEN PILOT SHAPE</p>
          <div className="pilot-panel-heading">
            <h2>{selectedSequences || targetSequences} decision windows</h2>
            <span>
              {selectedSequences}/{targetSequences} selected
            </span>
          </div>
          <div className="pilot-composition">
            {Object.entries(data.sample.composition).map(([key, count]) => (
              <div key={key}>
                <strong>{count}</strong>
                <span>{stratumLabels[key] ?? key.replaceAll("_", " ")}</span>
              </div>
            ))}
          </div>
          <p className="pilot-fine-print">
            These strata are sampling heuristics for diversity. They are never
            tactical labels and never enter the model feature matrix.
          </p>
        </article>

        <article className="pilot-panel pilot-blinding-panel">
          <p className="eyebrow">WHAT EACH EXPERT SEES</p>
          <h2>Football geometry, with the answer key removed.</h2>
          <div className="pilot-locks">
            <div>
              <span aria-hidden="true">01</span>
              <strong>Outcome blind</strong>
              <p>The eventual selected action is joined only after rating.</p>
            </div>
            <div>
              <span aria-hidden="true">02</span>
              <strong>Model-score blind</strong>
              <p>
                No rank, brightness, or model score can whisper a preferred
                option.
              </p>
            </div>
            <div>
              <span aria-hidden="true">03</span>
              <strong>Causal history only</strong>
              <p>
                Earlier frames can explain creation. Later observed frames
                remain invisible.
              </p>
            </div>
          </div>
          <div className="pilot-progress-line">
            <span>Candidate coverage</span>
            <strong>{Math.round(coverage * 100)}%</strong>
            <div aria-hidden="true">
              <i
                style={{
                  width: `${Math.min(100, Math.max(0, coverage * 100))}%`,
                }}
              />
            </div>
          </div>
        </article>
      </section>

      <section
        className="pilot-benchmark"
        aria-labelledby="pilot-benchmark-title"
      >
        <header>
          <div>
            <p className="eyebrow">THE FALSIFIABLE TEST</p>
            <h2 id="pilot-benchmark-title">Does motion buy us anything?</h2>
          </div>
          <p>
            R1 is sequence-held-out Tier A. Provider-held-out replication is
            intentionally deferred until an independent full-tracking Tier B
            dataset is annotated.
          </p>
        </header>
        {data.benchmark.complete && modelRows.length > 0 ? (
          <div
            className="pilot-metric-table"
            role="table"
            aria-label="R1 benchmark metrics"
          >
            <div className="pilot-metric-row pilot-metric-header" role="row">
              <span role="columnheader">Model</span>
              <span role="columnheader">NDCG@3</span>
              <span role="columnheader">Recall@3</span>
              <span role="columnheader">Pairwise</span>
              <span role="columnheader">Top-3 stability</span>
            </div>
            {modelRows.map(([model, metrics]) => (
              <div className="pilot-metric-row" role="row" key={model}>
                <strong role="cell">{modelLabels[model] ?? model}</strong>
                <span role="cell">{formatMetric(metrics["ndcg@3"])}</span>
                <span role="cell">{formatMetric(metrics["recall@3"])}</span>
                <span role="cell">{formatMetric(metrics.pairwise)}</span>
                <span role="cell">
                  {formatMetric(metrics.top_3_jaccard_stability)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="pilot-empty-result">
            <span aria-hidden="true">∅</span>
            <div>
              <strong>No benchmark number is allowed here yet.</strong>
              <p>
                The interface will populate this table only after double
                annotation, reliability, adjudication, causal-feature review,
                provider-quality review, and the frozen sequence-held-out run
                all succeed.
              </p>
            </div>
          </div>
        )}
      </section>

      <section className="pilot-roadmap" aria-labelledby="pilot-roadmap-title">
        <header>
          <p className="eyebrow">HOW THE IDEA EARNS COMPLEXITY</p>
          <h2 id="pilot-roadmap-title">
            Build outward only when the current representation breaks.
          </h2>
        </header>
        <div className="pilot-roadmap-grid">
          <article>
            <span>R1</span>
            <strong>Real action-menu pilot</strong>
            <p>Metrica, ten decision windows, two experts, B0 through B3.</p>
          </article>
          <article>
            <span>R2</span>
            <strong>Independent replication</strong>
            <p>
              Freeze the method and repeat on Sportec or another full-tracking
              source.
            </p>
          </article>
          <article>
            <span>R3</span>
            <strong>Observation stress test</strong>
            <p>
              SkillCorner and masking experiments ask what disappears when the
              pitch disappears.
            </p>
          </article>
          <article>
            <span>R4</span>
            <strong>Representation upgrade</strong>
            <p>
              Only then earn temporal graphs, video uncertainty, or egocentric
              perception.
            </p>
          </article>
        </div>
      </section>

      <section className="pilot-guardrails">
        <div>
          <p className="eyebrow">NON-NEGOTIABLES</p>
          <h2>
            The fastest path is the one that survives contact with bad results.
          </h2>
        </div>
        <ul>
          {data.guardrails.map((guardrail) => (
            <li key={guardrail}>{guardrail}</li>
          ))}
        </ul>
        <Link to="/method" className="text-link">
          Read the full method contract →
        </Link>
      </section>
    </div>
  );
}
