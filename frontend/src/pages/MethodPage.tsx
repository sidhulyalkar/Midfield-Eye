import { Link } from "react-router";
import { EvidenceBadge } from "../components/Evidence";

export default function MethodPage({ page }: { page: "method" | "rights" }) {
  if (page === "rights") {
    return (
      <div className="method-page page-pad prose-page">
        <p className="eyebrow">Data and rights</p>
        <h1>Access is part of the evidence.</h1>
        <p className="lead">
          A source is usable only when registration, license, consent,
          attribution, and redistribution rules permit the intended analysis.
        </p>
        <section>
          <h2>What stays out of Git</h2>
          <p>
            Gated datasets, private media, credentials, and generated release
            bundles are never committed.
          </p>
        </section>
        <section>
          <h2>What a public claim needs</h2>
          <p>
            Provider attribution, source hashes, transformation history,
            evidence tier, missing signals, and a claim boundary.
          </p>
        </section>
        <Link className="button button-primary" to="/empirical">
          Inspect registered sources
        </Link>
      </div>
    );
  }
  return (
    <div className="method-page page-pad prose-page">
      <p className="eyebrow">Scientific method</p>
      <h1>Make the action menu falsifiable.</h1>
      <p className="lead">
        Physical availability, perceptual visibility, tactical value, future
        creation, selection, and uncertainty remain distinct targets from
        annotation through presentation.
      </p>
      <section className="method-status">
        <EvidenceBadge kind="unavailable" source="Expert pilot not bundled" />
        <div>
          <h2>Reliability is a gate, not a decorative metric.</h2>
          <p>
            The current public showcase does not establish expert inter-rater
            reliability. B0–B3 progression must remain blocked until frozen
            expert labels meet the declared agreement gate or the protocol is
            revised.
          </p>
        </div>
      </section>
      <section>
        <p className="eyebrow">Evaluation sequence</p>
        <h2>Simple explanations survive.</h2>
        <ol>
          <li>B0 distance and forward progress.</li>
          <li>B1 static corridor geometry and receiver pressure.</li>
          <li>B2 causal dynamic geometry and future space.</li>
          <li>B2-V viewpoint-aware geometry.</li>
          <li>
            B3 learned tabular ranker, retaining every simpler baseline and
            ablation.
          </li>
        </ol>
      </section>
      <section>
        <h2>No adjacent-frame leakage.</h2>
        <p>
          Evaluation groups by possession sequence, then by match and provider
          where the dataset permits it. Sequence-level bootstrap intervals
          retain dependence honestly.
        </p>
      </section>
    </div>
  );
}
