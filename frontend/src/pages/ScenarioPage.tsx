import { useEffect, useMemo } from "react";
import { Link, useParams } from "react-router";
import { EvidenceBadge, EvidenceLegend } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { PlaybackController } from "../components/PlaybackController";
import { useScenarioBundle } from "../data/hooks";
import {
  usePlaybackStore,
  type LayerId,
  type PlaybackRate,
} from "../state/playbackStore";
import { SynchronizedTimeline } from "../visualization/SynchronizedTimeline";
import { TacticalPitch } from "../visualization/TacticalPitch";

const layerLabels: Record<LayerId, string> = {
  visibility: "Visible area",
  uncertainty: "Uncertainty",
  velocity: "Movement",
  body: "Body axis",
  gaze: "View proxy",
  relations: "Relations",
};

function isEditable(target: EventTarget | null) {
  return (
    target instanceof HTMLElement &&
    ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)
  );
}

export default function ScenarioPage() {
  const { scenarioId = "aitana-overload" } = useParams();
  const bundle = useScenarioBundle(scenarioId);
  const {
    currentFrameId,
    selectedOptionId,
    lockedOptionId,
    playbackRate,
    layers,
    evidenceView,
    initialize,
    selectOption,
    lockOption,
    setPlaying,
    setRate,
    setLayers,
    setEvidenceView,
    step,
    toggleLayer,
    seek,
  } = usePlaybackStore();
  useEffect(() => {
    if (!bundle.frames?.length) return;
    const searchParams = new URLSearchParams(window.location.search);
    const requestedFrame = Number(searchParams.get("frame"));
    initialize(
      scenarioId,
      bundle.frames.map((frame) => frame.frame_id),
      Number.isFinite(requestedFrame)
        ? requestedFrame
        : bundle.frames[0]?.frame_id,
    );
    const rate = Number(searchParams.get("rate"));
    if ([0.25, 0.5, 1, 2].includes(rate)) setRate(rate as PlaybackRate);
    const option = searchParams.get("option");
    selectOption(option);
    const requestedLayers = searchParams
      .get("layers")
      ?.split(",")
      .filter(Boolean);
    if (requestedLayers?.length) {
      setLayers(
        Object.fromEntries(
          (Object.keys(layerLabels) as LayerId[]).map((layer) => [
            layer,
            requestedLayers.includes(layer),
          ]),
        ) as Record<LayerId, boolean>,
      );
    }
    setEvidenceView(
      searchParams.get("evidence") === "observed" ? "observed" : "uncertainty",
    );
  }, [
    bundle.frames,
    initialize,
    scenarioId,
    selectOption,
    setEvidenceView,
    setLayers,
    setRate,
  ]);

  useEffect(() => {
    const restore = () => {
      const searchParams = new URLSearchParams(window.location.search);
      const frameId = Number(searchParams.get("frame"));
      const rate = Number(searchParams.get("rate"));
      if (Number.isFinite(frameId)) seek(frameId);
      if ([0.25, 0.5, 1, 2].includes(rate)) setRate(rate as PlaybackRate);
      selectOption(searchParams.get("option"));
      const requestedLayers = searchParams
        .get("layers")
        ?.split(",")
        .filter(Boolean);
      if (requestedLayers?.length) {
        setLayers(
          Object.fromEntries(
            (Object.keys(layerLabels) as LayerId[]).map((layer) => [
              layer,
              requestedLayers.includes(layer),
            ]),
          ) as Record<LayerId, boolean>,
        );
      }
      setEvidenceView(
        searchParams.get("evidence") === "observed"
          ? "observed"
          : "uncertainty",
      );
      setPlaying(false);
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, [seek, selectOption, setEvidenceView, setLayers, setPlaying, setRate]);

  useEffect(() => {
    if (!bundle.frames?.length) return;
    const next = new URLSearchParams(window.location.search);
    next.set("frame", String(currentFrameId));
    next.set("rate", String(playbackRate));
    next.set(
      "layers",
      Object.entries(layers)
        .filter(([, active]) => active)
        .map(([id]) => id)
        .join(","),
    );
    next.set("evidence", evidenceView);
    if (selectedOptionId) next.set("option", selectedOptionId);
    else next.delete("option");
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}?${next.toString()}`,
    );
  }, [
    bundle.frames?.length,
    currentFrameId,
    evidenceView,
    layers,
    playbackRate,
    selectedOptionId,
  ]);

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (isEditable(event.target)) return;
      if (event.key === " ") {
        event.preventDefault();
        setPlaying(!usePlaybackStore.getState().playing);
      } else if (event.key === "ArrowLeft") step(-1);
      else if (event.key === "ArrowRight") step(1);
      else if (/^[1-6]$/u.test(event.key)) {
        const layer = Object.keys(layerLabels)[Number(event.key) - 1] as
          LayerId | undefined;
        if (layer) toggleLayer(layer);
      } else if (event.key === "Escape") selectOption(null);
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [selectOption, setPlaying, step, toggleLayer]);

  const frame = bundle.frames?.find(
    (candidate) => candidate.frame_id === currentFrameId,
  );
  const currentOptions = useMemo(
    () =>
      bundle.options?.filter((option) => option.frame_id === currentFrameId) ??
      [],
    [bundle.options, currentFrameId],
  );
  const ranked = useMemo(
    () =>
      [...currentOptions].sort((a, b) => b.geometric_score - a.geometric_score),
    [currentOptions],
  );
  const activeOption = selectedOptionId ?? ranked[0]?.option_id ?? null;
  const gazePoint = bundle.gaze?.timeline.find(
    (point) => point.frame_id === currentFrameId,
  );
  const bodyPoint = bundle.body?.timeline.find(
    (point) => point.frame_id === currentFrameId,
  );
  const relationPoint = bundle.relations?.timeline.find(
    (point) => point.frame_id === currentFrameId,
  );

  useEffect(() => {
    if (
      lockedOptionId &&
      !currentOptions.some((option) => option.option_id === lockedOptionId)
    ) {
      lockOption(null);
    }
  }, [currentOptions, lockedOptionId, lockOption]);

  if (bundle.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Synchronizing the scenario"
        message="Frames, options, perception, body, and relational layers are joining by frame ID."
      />
    );
  }
  if (
    bundle.error ||
    !bundle.scenario ||
    !bundle.frames ||
    !bundle.options ||
    !bundle.timeline ||
    !frame
  ) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The scenario bundle is incomplete"
        message={
          bundle.error?.message ??
          "A required synchronized resource is missing."
        }
        onRetry={bundle.retry}
      />
    );
  }

  const timestamps = new Map(
    bundle.frames.map((item) => [item.frame_id, item.timestamp_s]),
  );

  return (
    <div className="scenario-page">
      <header className="page-heading scenario-heading">
        <div>
          <p className="eyebrow">{bundle.scenario.archetype}</p>
          <h1>{bundle.scenario.title}</h1>
          <p>{bundle.scenario.tactical_question}</p>
        </div>
        <div className="heading-evidence">
          <EvidenceBadge kind="synthetic" source="Generated teaching state" />
          <span>Not measured player performance</span>
        </div>
      </header>
      <section className="scenario-instrument">
        <div className="pitch-stage">
          <span className="synthetic-watermark">
            Illustrative synthetic · {bundle.scenario.player_name}
          </span>
          <TacticalPitch
            frame={frame}
            options={bundle.options}
            selectedOptionId={activeOption}
            layers={layers}
            gaze={bundle.gaze}
            body={bundle.body}
            relations={bundle.relations}
            onOptionSelect={selectOption}
            title={`${bundle.scenario.title}, frame ${frame.frame_id}`}
          />
          <PlaybackController timestamps={timestamps} />
          <div className="layer-controls" aria-label="Pitch layers">
            {(Object.keys(layerLabels) as LayerId[]).map((layer, index) => (
              <button
                key={layer}
                type="button"
                aria-pressed={layers[layer]}
                onClick={() => toggleLayer(layer)}
              >
                <kbd>{index + 1}</kbd> {layerLabels[layer]}
              </button>
            ))}
          </div>
        </div>
        <aside className="action-rail">
          <div className="rail-heading">
            <div>
              <p className="eyebrow">Frame {frame.frame_id}</p>
              <h2>The action menu</h2>
            </div>
            <span>{ranked.length} candidates</span>
          </div>
          <p className="rail-note">
            Scores order this frame only. They are not probabilities.
          </p>
          <div className="option-list">
            {ranked.map((option, index) => (
              <button
                type="button"
                key={option.option_id}
                className={
                  option.option_id === activeOption
                    ? "option-card option-card-active"
                    : "option-card"
                }
                onClick={() => selectOption(option.option_id)}
              >
                <span className="option-index">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span>
                  <strong>
                    {option.kind} · {option.target_player_id ?? "space"}
                  </strong>
                  <small>
                    lane{" "}
                    {option.features.lane_clearance_m?.toFixed(1) ?? "missing"}m
                    · view proxy{" "}
                    {option.features.visibility?.toFixed(2) ?? "missing"}
                  </small>
                </span>
                <code>{option.geometric_score.toFixed(3)}</code>
              </button>
            ))}
          </div>
          {activeOption ? (
            <button
              type="button"
              className="lock-action"
              aria-pressed={lockedOptionId === activeOption}
              onClick={() =>
                lockOption(
                  lockedOptionId === activeOption ? null : activeOption,
                )
              }
            >
              {lockedOptionId === activeOption
                ? "Release option lock"
                : "Lock selected option"}
            </button>
          ) : null}
          <EvidenceLegend
            kinds={["synthetic", "inferred_proxy", "unavailable"]}
          />
        </aside>
      </section>
      <SynchronizedTimeline
        timeline={bundle.timeline}
        currentFrameId={currentFrameId}
        onSeek={seek}
      />
      <section className="evidence-details">
        <article>
          <p className="eyebrow">Perception · synthetic view model</p>
          <h3>
            {gazePoint?.top_option_in_actionable_view
              ? "Top option inside actionable field"
              : "Top option outside actionable field"}
          </h3>
          <p>
            Gaze source:{" "}
            <strong>{gazePoint?.gaze_source ?? "unavailable"}</strong>. This
            dotted cone is illustrative and is never a claim about{" "}
            {bundle.scenario.player_name}&apos;s measured gaze.
          </p>
          <span>
            {gazePoint?.gaze_confidence == null
              ? "Confidence unavailable"
              : `Source confidence ${gazePoint.gaze_confidence.toFixed(2)}`}
          </span>
        </article>
        <article>
          <p className="eyebrow">Body · kinematic proxy</p>
          <h3>Body and movement stay distinct</h3>
          <p>
            Separation{" "}
            {typeof bodyPoint?.body_movement_separation_deg === "number"
              ? `${bodyPoint.body_movement_separation_deg.toFixed(1)}°`
              : "unavailable"}
            . Weight transfer is model-derived, not a direct force measurement.
          </p>
          <span>{bodyPoint?.metric_status ?? "Missing body signal"}</span>
        </article>
        <article>
          <p className="eyebrow">Collective response · geometry</p>
          <h3>Support changes around the subject</h3>
          <p>
            Response geometry can describe timing and option enablement. It
            cannot establish communication, intent, or leadership.
          </p>
          <span>
            Option enablement{" "}
            {relationPoint?.option_enablement == null
              ? "unavailable"
              : relationPoint.option_enablement.toFixed(3)}
          </span>
        </article>
      </section>
      <section className="coaching-note">
        <span>Interpretation boundary</span>
        <div>
          <h2>Use this to ask better questions, not grade a player.</h2>
          <p>{bundle.scenario.narrative_beats.join(" ")}</p>
        </div>
        <Link to="/empirical">Compare with source-pinned evidence →</Link>
      </section>
    </div>
  );
}
