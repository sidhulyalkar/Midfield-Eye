export type EvidenceKind =
  | "direct_measurement"
  | "provider_observation"
  | "video_reconstruction"
  | "inferred_proxy"
  | "synthetic"
  | "unavailable";

const labels: Record<EvidenceKind, string> = {
  direct_measurement: "Measured",
  provider_observation: "Provider observed",
  video_reconstruction: "Reconstructed",
  inferred_proxy: "Proxy",
  synthetic: "Illustrative synthetic",
  unavailable: "Unavailable",
};

export function EvidenceBadge({
  kind,
  source,
}: {
  kind: EvidenceKind;
  source?: string | undefined;
}) {
  return (
    <span className={`evidence-badge evidence-${kind}`} title={source}>
      <i aria-hidden="true" />
      {labels[kind]}
      {source ? <small>{source}</small> : null}
    </span>
  );
}

export function EvidenceLegend({ kinds }: { kinds: EvidenceKind[] }) {
  return (
    <div className="evidence-legend" aria-label="Evidence legend">
      {kinds.map((kind) => (
        <EvidenceBadge key={kind} kind={kind} />
      ))}
    </div>
  );
}

export function MissingSignal({
  signal,
  reason,
  path,
}: {
  signal: string;
  reason: string;
  path: string;
}) {
  return (
    <section className="missing-signal">
      <EvidenceBadge kind="unavailable" />
      <h3>{signal}</h3>
      <p>{reason}</p>
      <small>{path}</small>
    </section>
  );
}
