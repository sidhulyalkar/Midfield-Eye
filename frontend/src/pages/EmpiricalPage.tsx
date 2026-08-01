import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { useDataSource } from "../app/providers";
import { EvidenceBadge } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { queryKeys } from "../data/queryKeys";

export default function EmpiricalPage() {
  const source = useDataSource();
  const experiments = useQuery({
    queryKey: queryKeys.empiricalExperiments,
    queryFn: () => source.listEmpiricalExperiments(),
  });
  const sources = useQuery({
    queryKey: queryKeys.empiricalSources,
    queryFn: () => source.listEmpiricalSources(),
  });

  if (experiments.isPending || sources.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Opening the evidence room"
        message="Checking source records, rights, and claim boundaries."
      />
    );
  }
  if (experiments.isError || sources.isError) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="Empirical evidence is unavailable"
        message={
          experiments.error?.message ??
          sources.error?.message ??
          "A governed source failed to load."
        }
      />
    );
  }

  return (
    <div className="empirical-index page-pad">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Source-pinned studies</p>
          <h1>The evidence room.</h1>
          <p>
            Real provider geometry enters here with its rights, missing signals,
            identities, and claim limits intact.
          </p>
        </div>
        <EvidenceBadge
          kind="provider_observation"
          source={`${sources.data.length} registered sources`}
        />
      </header>
      <section className="empirical-cards">
        {experiments.data.map((experiment) => {
          const experimentSource = sources.data.find(
            (candidate) => candidate.id === experiment.source_id,
          );
          return (
            <Link
              key={experiment.id}
              to={`/empirical/experiments/${experiment.id}`}
              className="empirical-card"
            >
              <div className="empirical-card-visual">
                <img
                  src={source.assetUrl(`empirical/${experiment.visual}`)}
                  alt=""
                  loading="lazy"
                  width="960"
                  height="540"
                />
                <EvidenceBadge
                  kind="provider_observation"
                  source={experimentSource?.name}
                />
              </div>
              <div>
                <span>
                  {experiment.modalities.join(" · ").replaceAll("_", " ")}
                </span>
                <h2>{experiment.title}</h2>
                <p>{experiment.claim_boundary}</p>
                <strong>Inspect provenance →</strong>
              </div>
            </Link>
          );
        })}
      </section>
      <section className="source-matrix">
        <header>
          <p className="eyebrow">Registered access</p>
          <h2>What each source can—and cannot—show.</h2>
        </header>
        <div>
          {sources.data.slice(0, 5).map((item) => (
            <article key={item.id}>
              <span>{item.access.replaceAll("_", " ")}</span>
              <h3>{item.name}</h3>
              <p>{item.best_for.slice(0, 2).join(" · ")}</p>
              <small>{item.caveats[0]}</small>
              <a href={item.official_url} rel="noreferrer" target="_blank">
                Official source ↗
              </a>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
