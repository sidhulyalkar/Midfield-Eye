import { Link, useParams } from "react-router";
import { EvidenceBadge, EvidenceLegend } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { useScenarioBundle } from "../data/hooks";

/**
 * Thin coach-facing view on top of the same scenario evidence stack.
 * Does not invent metrics; points to the full Decision Microscope for analysis.
 */
export default function CoachViewPage() {
  const { scenarioId = "aitana-overload" } = useParams();
  const bundle = useScenarioBundle(scenarioId);

  if (bundle.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Opening coach view"
        message="Loading the synchronized scenario evidence…"
      />
    );
  }

  if (bundle.error || !bundle.scenario) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="Coach view could not load"
        message={bundle.error?.message ?? "Scenario evidence is missing."}
        onRetry={bundle.retry}
      />
    );
  }

  const beats = bundle.scenario.narrative_beats ?? [];
  const cues = beats.slice(0, 3);

  return (
    <div className="simplified-view coach-view">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Coach view · illustrative</p>
          <h1>{bundle.scenario.title}</h1>
          <p>{bundle.scenario.tactical_question}</p>
        </div>
        <div className="heading-evidence">
          <EvidenceBadge kind="synthetic" source="Generated teaching state" />
          <span>Not measured player performance</span>
        </div>
      </header>

      <section className="simplified-card">
        <p className="eyebrow">What to rehearse</p>
        <h2>Session cues from this possession</h2>
        {cues.length > 0 ? (
          <ol className="cue-list">
            {cues.map((cue) => (
              <li key={cue}>{cue}</li>
            ))}
          </ol>
        ) : (
          <p>
            Narrative cues are not available for this scenario. Open the Decision
            Microscope to inspect the action menu directly.
          </p>
        )}
        <p className="simplified-note">
          These cues are teaching language derived from the illustrative scenario
          narrative. They are not expert-annotated R1 labels and must not be read
          as empirical model output.
        </p>
      </section>

      <section className="simplified-card">
        <p className="eyebrow">Evidence boundary</p>
        <h2>Same stack, simpler language</h2>
        <p>
          Coach view reuses the scenario bundle used by the Decision Microscope.
          It does not add ranks, probabilities, or player grades. When real R1
          evidence exists, practice cues will be gated on measured or
          reconstructed evidence types only.
        </p>
        <EvidenceLegend kinds={["synthetic", "inferred_proxy", "unavailable"]} />
      </section>

      <section className="simplified-actions">
        <Link className="text-link" to={`/scenario/${scenarioId}`}>
          Open full Decision Microscope →
        </Link>
        <Link className="text-link" to={`/player/${scenarioId}`}>
          Switch to player view →
        </Link>
        <Link className="text-link" to="/pilot">
          R1 evidence cockpit →
        </Link>
      </section>
    </div>
  );
}
