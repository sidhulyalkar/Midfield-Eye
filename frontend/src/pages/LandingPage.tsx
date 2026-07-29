import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { EvidenceBadge } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { useScenarioBundle, useScenarios } from "../data/hooks";
import { TacticalPitch } from "../visualization/TacticalPitch";
import type { LayerId } from "../state/playbackStore";

const heroScenario = "aitana-overload";
const heroLayers: Record<LayerId, boolean> = {
  visibility: true,
  uncertainty: true,
  velocity: true,
  body: true,
  gaze: true,
  relations: false,
};

function useHeroFrame(frameCount: number, keyFrame: number) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [index, setIndex] = useState(reduced ? keyFrame : 0);
  useEffect(() => {
    if (reduced || frameCount < 2) return;
    let handle = 0;
    const started = performance.now();
    const tick = (now: number) => {
      const elapsed = (now - started) % 10_000;
      const beat = Math.min(3, Math.floor(elapsed / 2_500));
      const next = Math.round((beat / 3) * (frameCount - 1));
      setIndex(next);
      handle = requestAnimationFrame(tick);
    };
    handle = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(handle);
  }, [frameCount, reduced]);
  return index;
}

export default function LandingPage() {
  const bundle = useScenarioBundle(heroScenario);
  const scenarios = useScenarios();
  const frameIndex = useHeroFrame(
    bundle.frames?.length ?? 0,
    bundle.scenario?.key_frame_index ?? 0,
  );
  const frame = bundle.frames?.[frameIndex];
  const frameOptions = useMemo(
    () =>
      bundle.options?.filter((option) => option.frame_id === frame?.frame_id) ??
      [],
    [bundle.options, frame?.frame_id],
  );
  const best = [...frameOptions].sort(
    (a, b) => b.geometric_score - a.geometric_score,
  )[0];
  const beat =
    bundle.scenario?.narrative_beats[
      Math.min(
        2,
        Math.floor(
          (frameIndex / Math.max(1, (bundle.frames?.length ?? 1) - 1)) * 3,
        ),
      )
    ];

  if (bundle.isPending || scenarios.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Drawing the action menu"
        message="Loading one deterministic teaching sequence."
      />
    );
  }
  if (
    bundle.error ||
    scenarios.isError ||
    !frame ||
    !bundle.scenario ||
    !bundle.frames ||
    !bundle.options
  ) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The featured sequence is unavailable"
        message={
          bundle.error?.message ??
          scenarios.error?.message ??
          "The scenario bundle is incomplete."
        }
        onRetry={bundle.retry}
      />
    );
  }

  return (
    <div className="landing-page">
      <section className="truth-banner">
        <EvidenceBadge
          kind="synthetic"
          source="Teaching scenario · not measured player performance"
        />
        <p>
          The visual teaches a scientific question. Real-source evidence is
          always shown separately.
        </p>
      </section>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Perception · geometry · creation</p>
          <h1>See the option before it exists.</h1>
          <p className="hero-deck">
            The selected pass is one trace. The real object of study is the
            changing menu a player can physically reach, perceptually access,
            value, and create.
          </p>
          <div className="hero-actions">
            <Link
              className="button button-primary"
              to={`/scenario/${heroScenario}`}
            >
              Explore the action menu
            </Link>
            <Link className="button button-secondary" to="/empirical">
              Inspect the evidence
            </Link>
          </div>
          <div className="narrative-beat" aria-live="polite">
            <span>
              0
              {Math.min(
                3,
                Math.floor(
                  (frameIndex / Math.max(1, bundle.frames.length - 1)) * 3,
                ) + 1,
              )}
            </span>
            <p>{beat}</p>
          </div>
        </div>
        <div className="hero-visual">
          <span className="synthetic-watermark">Illustrative synthetic</span>
          <TacticalPitch
            frame={frame}
            options={bundle.options}
            selectedOptionId={best?.option_id ?? null}
            layers={heroLayers}
            gaze={bundle.gaze}
            body={bundle.body}
            title="An illustrative option emerging as a teammate moves"
          />
          <div className="pitch-caption">
            <span>t {frame.timestamp_s.toFixed(2)}s</span>
            <strong>{frameOptions.length} actions modeled separately</strong>
            <span>Scores rank only this frame</span>
          </div>
        </div>
      </section>
      <section className="pillar-grid" aria-labelledby="pillars-title">
        <header>
          <p className="eyebrow">The research object</p>
          <h2 id="pillars-title">
            Five questions, kept deliberately separate.
          </h2>
        </header>
        {[
          ["Available", "Can the action physically and temporally succeed?"],
          ["Visible", "Was the relevant information plausibly in view?"],
          [
            "Valuable",
            "What could the action produce if executed competently?",
          ],
          ["Created", "Which earlier movement improved the later menu?"],
          ["Selected", "What happened—without erasing the alternatives?"],
        ].map(([label, copy], index) => (
          <article key={label}>
            <span>0{index + 1}</span>
            <h3>{label}</h3>
            <p>{copy}</p>
          </article>
        ))}
      </section>
      <section className="featured-studies">
        <header>
          <div>
            <p className="eyebrow">Teaching laboratories</p>
            <h2>Eight hypotheses. No player-performance claims.</h2>
          </div>
          <Link to="/atlas">Open the 100-profile atlas →</Link>
        </header>
        <div className="study-strip">
          {scenarios.data?.slice(0, 4).map((scenario) => (
            <Link key={scenario.id} to={`/scenario/${scenario.id}`}>
              <span>{scenario.archetype}</span>
              <h3>{scenario.title}</h3>
              <p>{scenario.tactical_question}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
