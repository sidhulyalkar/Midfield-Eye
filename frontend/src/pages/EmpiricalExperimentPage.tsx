import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import { useDataSource } from "../app/providers";
import { EvidenceBadge, MissingSignal } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { queryKeys } from "../data/queryKeys";
import { EmpiricalScenePitch } from "../visualization/EmpiricalScenePitch";

function FieldList({
  title,
  fields,
  kind,
}: {
  title: string;
  fields: string[];
  kind: "measured" | "inferred";
}) {
  return (
    <section className={`evidence-field-list field-${kind}`}>
      <p className="eyebrow">
        {kind === "measured" ? "Provider observed" : "Model-derived"}
      </p>
      <h3>{title}</h3>
      <ul>
        {fields.map((field) => (
          <li key={field}>{field.replaceAll("_", " ")}</li>
        ))}
      </ul>
    </section>
  );
}

export default function EmpiricalExperimentPage() {
  const { experimentId = "" } = useParams();
  const source = useDataSource();
  const experiment = useQuery({
    queryKey: queryKeys.empiricalExperiment(experimentId),
    queryFn: () => source.getEmpiricalExperiment(experimentId),
  });
  const sources = useQuery({
    queryKey: queryKeys.empiricalSources,
    queryFn: () => source.listEmpiricalSources(),
  });
  const citations = useQuery({
    queryKey: queryKeys.citations,
    queryFn: () => source.getCitations(),
  });

  if (experiment.isPending || sources.isPending || citations.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Verifying the study"
        message="Loading provider geometry, citation, provenance, and missing-signal rules."
      />
    );
  }
  if (experiment.isError || sources.isError || citations.isError) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The empirical study could not be verified"
        message={
          experiment.error?.message ??
          sources.error?.message ??
          citations.error?.message ??
          "Unknown evidence error"
        }
      />
    );
  }

  const item = experiment.data;
  const itemSource = sources.data.find(
    (candidate) => candidate.id === item.source_id,
  );
  const citation = citations.data.find(
    (candidate) => candidate.id === item.source_id,
  );
  const isStatsBomb = item.source_id === "statsbomb_open_data";
  const isMetrica = item.source_id === "metrica_sample_data";

  return (
    <div className="empirical-detail page-pad">
      <header className="page-heading empirical-heading">
        <div>
          <p className="eyebrow">{itemSource?.name ?? item.source_id}</p>
          <h1>{item.title}</h1>
          <p>{item.subject ?? "Anonymous provider sample"}</p>
        </div>
        <EvidenceBadge
          kind="provider_observation"
          source={item.evidence_tier.replaceAll("_", " ")}
        />
      </header>
      <section className="empirical-truth-line">
        <strong>
          {isStatsBomb
            ? "Event-centered snapshot"
            : "Continuous provider frame"}
        </strong>
        <span>{item.modalities.join(" · ").replaceAll("_", " ")}</span>
        <span>
          {isStatsBomb
            ? "No temporal playback or velocity claim"
            : "Anonymous match-local identities"}
        </span>
      </section>
      <section className="empirical-instrument">
        <div className="empirical-canvas">
          {item.scene ? (
            <EmpiricalScenePitch scene={item.scene} title={item.title} />
          ) : (
            <img
              src={source.assetUrl(`empirical/${item.visual}`)}
              alt={`Provider-supplied study visual for ${item.title}`}
              width="3840"
              height="2160"
            />
          )}
          {item.scene ? (
            <details className="reference-visual">
              <summary>Open the generated 4K reference visual</summary>
              <img
                src={source.assetUrl(`empirical/${item.visual}`)}
                alt={`Generated evidence reference for ${item.title}`}
                loading="lazy"
                width="3840"
                height="2160"
              />
            </details>
          ) : null}
        </div>
        <aside className="empirical-evidence-rail">
          <EvidenceBadge
            kind="provider_observation"
            source={itemSource?.name}
          />
          <FieldList
            title="Directly present in this source"
            fields={item.measured}
            kind="measured"
          />
          <FieldList
            title="Computed under explicit assumptions"
            fields={item.inferred}
            kind="inferred"
          />
          <div className="evidence-limit">
            <p className="eyebrow">Claim boundary</p>
            <p>{item.claim_boundary}</p>
          </div>
        </aside>
      </section>
      {item.scene ? (
        <section className="scene-contract">
          <div>
            <p className="eyebrow">Canonical scene</p>
            <h2>
              {item.scene.players.length} observations · t{" "}
              {item.scene.timestamp_s.toFixed(2)}s
            </h2>
          </div>
          <p>{item.scene.identity_warning}</p>
          <dl>
            <div>
              <dt>Availability labels</dt>
              <dd>Unavailable</dd>
            </div>
            <div>
              <dt>Selected action</dt>
              <dd>Retrospective event label</dd>
            </div>
            <div>
              <dt>Coordinates</dt>
              <dd>{item.scene.coordinate_system.normalization}</dd>
            </div>
          </dl>
        </section>
      ) : null}
      <section className="missing-grid">
        {item.unavailable.map((signal) => (
          <MissingSignal
            key={signal}
            signal={signal.replaceAll("_", " ")}
            reason={
              isStatsBomb
                ? "This event snapshot does not contain that modality."
                : "This tracking sample does not record that signal."
            }
            path={
              signal.includes("gaze")
                ? "Requires calibrated eye-gaze capture."
                : "Requires a registered, rights-cleared sensor source."
            }
          />
        ))}
      </section>
      <section className="provenance-panel">
        <div>
          <p className="eyebrow">Source & rights</p>
          <h2>{citation?.citation ?? itemSource?.citation}</h2>
          <p>{itemSource?.redistribution}</p>
        </div>
        <dl>
          <div>
            <dt>Evidence tier</dt>
            <dd>{item.evidence_tier.replaceAll("_", " ")}</dd>
          </div>
          <div>
            <dt>Source bundle</dt>
            <dd>
              <code>{item.source_bundle}</code>
            </dd>
          </div>
          <div>
            <dt>License</dt>
            <dd>{citation?.license ?? itemSource?.license_name}</dd>
          </div>
        </dl>
        {citation ? (
          <a href={citation.official_url} rel="noreferrer" target="_blank">
            Open official source ↗
          </a>
        ) : null}
      </section>
      {isMetrica ? (
        <p className="identity-warning">
          The Metrica sample&apos;s player labels are anonymous. This view does
          not attach them to named player profiles.
        </p>
      ) : null}
    </div>
  );
}
