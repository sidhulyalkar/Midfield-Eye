import { Link, useParams } from "react-router";
import { EvidenceBadge, EvidenceLegend } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { useScenarioBundle } from "../data/hooks";

/**
 * Thin player-facing view: one teachable moment, no overwhelm, no invented grades.
 */
export default function PlayerViewPage() {
  const { scenarioId = "aitana-overload" } = useParams();
  const bundle = useScenarioBundle(scenarioId);

  if (bundle.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Opening player view"
        message="Loading the synchronized scenario evidence…"
      />
    );
  }

  if (bundle.error || !bundle.scenario) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="Player view could not load"
        message={bundle.error?.message ?? "Scenario evidence is missing."}
        onRetry={bundle.retry}
      />
    );
  }

  const moment =
    bundle.scenario.narrative_beats?.[0] ??
    bundle.scenario.tactical_question ??
    "Inspect the action menu in the Decision Microscope.";

  return (
    <div className="simplified-view player-view">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Player view · illustrative</p>
          <h1>One teachable moment</h1>
          <p>{bundle.scenario.title}</p>
        </div>
        <div className="heading-evidence">
          <EvidenceBadge kind="synthetic" source="Generated teaching state" />
          <span>Not a personal performance grade</span>
        </div>
      </header>

      <section className="simplified-card highlight-card">
        <p className="eyebrow">Focus</p>
        <h2>{moment}</h2>
        <p className="simplified-note">
          Prefer one clear idea per clip. This view never claims access to your
          internal perception without direct gaze or body evidence.
        </p>
      </section>

      <section className="simplified-card">
        <p className="eyebrow">Practice cue</p>
        <h2>Ask a better question next time</h2>
        <p>
          When the full Decision Microscope is available, use it to see which
          options were emerging, which closed, and which movement would have
          improved the menu — without treating the selected action as the only
          truth.
        </p>
        <EvidenceLegend kinds={["synthetic", "unavailable"]} />
      </section>

      <section className="simplified-actions">
        <Link className="text-link" to={`/scenario/${scenarioId}`}>
          Open full Decision Microscope →
        </Link>
        <Link className="text-link" to={`/coach/${scenarioId}`}>
          Switch to coach view →
        </Link>
      </section>
    </div>
  );
}
