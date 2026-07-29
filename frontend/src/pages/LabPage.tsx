import { useMemo, useState } from "react";
import {
  EvidenceBadge,
  EvidenceLegend,
  MissingSignal,
} from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { useScenarioBundle } from "../data/hooks";
import type { FrameState } from "../data/schemas";
import type { LayerId } from "../state/playbackStore";
import { TacticalPitch } from "../visualization/TacticalPitch";

type Lab = "gaze" | "body" | "orchestration" | "perception";

const copy: Record<Lab, { eyebrow: string; title: string; deck: string }> = {
  gaze: {
    eyebrow: "Perception source ladder",
    title: "Separate where the player looks from where the body points.",
    deck: "Direct gaze, pose inference, motion proxies, and synthetic demonstrations never share a label or line style.",
  },
  body: {
    eyebrow: "Execution envelope",
    title: "Keep posture, movement, and load claims apart.",
    deck: "Body orientation and movement heading are geometric. Weight transfer, balance, braking, and turning remain proxies without sensor data.",
  },
  orchestration: {
    eyebrow: "Relational geometry",
    title: "Study who moves when—not who intended what.",
    deck: "Support response, pressure attraction, and option enablement can be timed. Geometry alone cannot establish speech, intent, or leadership.",
  },
  perception: {
    eyebrow: "Controlled observation loss",
    title: "Watch uncertainty change the action-menu conclusion.",
    deck: "The same synthetic base frame is shown with and without an explicit 20-metre right-side visibility mask.",
  },
};

const baseLayers: Record<LayerId, boolean> = {
  visibility: true,
  uncertainty: true,
  velocity: true,
  body: false,
  gaze: false,
  relations: false,
};

function maskedFrame(frame: FrameState): FrameState {
  const boundary = frame.pitch_length - 20;
  return {
    ...frame,
    visibility_polygon: [
      [0, 0],
      [boundary, 0],
      [boundary, frame.pitch_width],
      [0, frame.pitch_width],
    ],
    quality_flags: [...frame.quality_flags, "controlled_right_side_mask_20m"],
  };
}

export default function LabPage({ lab }: { lab: Lab }) {
  const bundle = useScenarioBundle("aitana-overload");
  const [frameIndex, setFrameIndex] = useState(10);
  const frame =
    bundle.frames?.[Math.min(frameIndex, (bundle.frames?.length ?? 1) - 1)];
  const currentOptions = useMemo(
    () =>
      bundle.options?.filter((option) => option.frame_id === frame?.frame_id) ??
      [],
    [bundle.options, frame?.frame_id],
  );
  const top = [...currentOptions].sort(
    (a, b) => b.geometric_score - a.geometric_score,
  )[0];
  const layers = {
    ...baseLayers,
    gaze: lab === "gaze",
    body: lab === "body",
    relations: lab === "orchestration",
  };

  if (bundle.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Preparing the specialist laboratory"
        message="Joining the same canonical frame to its evidence-specific layer."
      />
    );
  }
  if (bundle.error || !frame || !bundle.options || !bundle.frames) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="Laboratory state unavailable"
        message={bundle.error?.message ?? "Scenario frame missing"}
      />
    );
  }

  return (
    <div className="lab-page page-pad">
      <header className="page-heading">
        <div>
          <p className="eyebrow">{copy[lab].eyebrow}</p>
          <h1>{copy[lab].title}</h1>
          <p>{copy[lab].deck}</p>
        </div>
        <EvidenceBadge kind="synthetic" source="Teaching laboratory" />
      </header>
      {lab === "perception" ? (
        <section className="comparison-pitches">
          <article>
            <header>
              <span>Complete synthetic observation</span>
              <strong>{currentOptions.length} physical candidates</strong>
            </header>
            <TacticalPitch
              frame={frame}
              options={bundle.options}
              selectedOptionId={top?.option_id ?? null}
              layers={baseLayers}
              title="Complete synthetic base state"
            />
          </article>
          <article>
            <header>
              <span>Controlled 20m observation mask</span>
              <strong>
                {currentOptions.length} physical ·{" "}
                {
                  currentOptions.filter(
                    (option) => option.target_x <= frame.pitch_length - 20,
                  ).length
                }{" "}
                observed
              </strong>
            </header>
            <TacticalPitch
              frame={maskedFrame(frame)}
              options={bundle.options}
              selectedOptionId={top?.option_id ?? null}
              layers={{ ...baseLayers, visibility: true }}
              title="The same synthetic frame with a controlled visibility mask"
            />
            <p className="mask-note">
              Dashed, dimmed marks remain physical candidates; only their
              observation is unavailable under this controlled mask.
            </p>
          </article>
        </section>
      ) : (
        <section className="lab-instrument">
          <div>
            <span className="synthetic-watermark">Illustrative synthetic</span>
            <TacticalPitch
              frame={frame}
              options={bundle.options}
              selectedOptionId={top?.option_id ?? null}
              layers={layers}
              gaze={bundle.gaze}
              body={bundle.body}
              relations={bundle.relations}
              title={`${lab} laboratory at frame ${frame.frame_id}`}
            />
            <label className="lab-scrubber">
              <span>Frame {frame.frame_id}</span>
              <input
                type="range"
                min={0}
                max={bundle.frames.length - 1}
                value={frameIndex}
                onChange={(event) => setFrameIndex(Number(event.target.value))}
              />
              <span>{frame.timestamp_s.toFixed(2)}s</span>
            </label>
          </div>
          <aside>
            {lab === "gaze" ? (
              <>
                <p className="eyebrow">Source ladder</p>
                <h2>Dotted means synthetic.</h2>
                <EvidenceLegend
                  kinds={[
                    "direct_measurement",
                    "inferred_proxy",
                    "synthetic",
                    "unavailable",
                  ]}
                />
                <p>
                  Body axis is gold; head direction is dashed; the three nested
                  fields have distinct outlines.
                </p>
                <MissingSignal
                  signal="Literal eye gaze"
                  reason="This named-player teaching scenario contains synthetic direction only."
                  path="Requires calibrated eye-gaze capture and alignment."
                />
              </>
            ) : null}
            {lab === "body" ? (
              <>
                <p className="eyebrow">Proxy boundary</p>
                <h2>No force claim without sensors.</h2>
                <p>
                  Gold body axis and pale movement vector remain distinct at
                  every frame.
                </p>
                <EvidenceBadge
                  kind="inferred_proxy"
                  source="Synthetic kinematic model"
                />
                <MissingSignal
                  signal="Direct kinetics"
                  reason="No force plate or biomechanics sensor is attached."
                  path="Requires consented kinetics capture."
                />
              </>
            ) : null}
            {lab === "orchestration" ? (
              <>
                <p className="eyebrow">Response timing</p>
                <h2>Links show geometry, not intent.</h2>
                <p>
                  Line opacity reflects option enablement at this frame, while
                  every teammate remains an observed synthetic state.
                </p>
                <EvidenceBadge
                  kind="inferred_proxy"
                  source="Relational geometry"
                />
              </>
            ) : null}
          </aside>
        </section>
      )}
      <section className="lab-guardrail">
        <strong>Interpretation guardrail</strong>
        <p>
          This laboratory demonstrates an analysis contract. It is not a
          measured assessment of the named player in the illustrative scenario.
        </p>
      </section>
    </div>
  );
}
