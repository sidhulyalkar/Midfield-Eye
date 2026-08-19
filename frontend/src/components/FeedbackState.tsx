type FeedbackKind =
  | "loading"
  | "recoverable_error"
  | "not_found"
  | "empty"
  | "empty_filter_result"
  | "missing_signal"
  | "source_gated"
  | "unsupported_comparison"
  | "version_mismatch"
  | "offline_static_validation"
  | "partial_data_warning";

type Props = {
  kind: FeedbackKind;
  title: string;
  message: string;
  onRetry?: () => void;
};

export function FeedbackState({ kind, title, message, onRetry }: Props) {
  return (
    <section
      className={`feedback-state feedback-${kind}`}
      role={kind === "loading" ? "status" : "alert"}
    >
      <span className="feedback-symbol" aria-hidden="true">
        {kind === "loading" ? "···" : "!"}
      </span>
      <div>
        <p className="eyebrow">{kind.replaceAll("_", " ")}</p>
        <h2>{title}</h2>
        <p>{message}</p>
        {onRetry ? (
          <button
            className="button button-secondary"
            type="button"
            onClick={onRetry}
          >
            Retry resource
          </button>
        ) : null}
      </div>
    </section>
  );
}
