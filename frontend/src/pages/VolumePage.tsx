import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { EvidenceBadge } from "../components/Evidence";
import { FeedbackState } from "../components/FeedbackState";
import { useScenarioBundle } from "../data/hooks";
import {
  volumeChannelCopy,
  type VolumeChannel,
  type VolumeQuality,
} from "../visualization/affordanceVolume";
import {
  AffordanceVolume3D,
  type AffordanceVolumeRuntime,
} from "../visualization/AffordanceVolume3D";

const channels = Object.keys(volumeChannelCopy) as VolumeChannel[];
const qualities: VolumeQuality[] = ["auto", "low", "medium", "high"];

export default function VolumePage() {
  const [searchParams] = useSearchParams();
  const scenarioId = searchParams.get("scenario") ?? "aitana-overload";
  const bundle = useScenarioBundle(scenarioId);
  const [frameIndex, setFrameIndex] = useState(10);
  const [channel, setChannel] = useState<VolumeChannel>("menu");
  const [quality, setQuality] = useState<VolumeQuality>("auto");
  const [threshold, setThreshold] = useState(0.2);
  const [runtime, setRuntime] = useState<AffordanceVolumeRuntime | null>(null);

  const frame = bundle.frames?.[
    Math.min(frameIndex, Math.max(0, (bundle.frames?.length ?? 1) - 1))
  ];
  const currentOptions = useMemo(
    () =>
      bundle.options?.filter((option) => option.frame_id === frame?.frame_id) ?? [],
    [bundle.options, frame?.frame_id],
  );

  if (bundle.isPending) {
    return (
      <FeedbackState
        kind="loading"
        title="Building the temporal affordance lattice"
        message="Joining the canonical frame, action candidates, motion state, and evidence boundaries."
      />
    );
  }
  if (bundle.error || !frame || !bundle.frames || !bundle.options) {
    return (
      <FeedbackState
        kind="recoverable_error"
        title="The 3D affordance volume could not be built"
        message={bundle.error?.message ?? "Scenario state is unavailable."}
        onRetry={bundle.retry}
      />
    );
  }

  const channelCopy = volumeChannelCopy[channel];
  const horizonSeconds = 1.5;

  return (
    <div className="volume-page page-pad">
      <header className="volume-page-heading">
        <div>
          <p className="eyebrow">TEMPORAL AFFORDANCE VOLUME · 3D RESEARCH INSTRUMENT</p>
          <h1>See the next second of football as a field you can move through.</h1>
          <p>
            X and Y remain the real pitch. The vertical axis is <strong>future time</strong>, not
            physical height. Pressure fronts, screened space, passing corridors, visibility, and
            opening options become one inspectable voxel lattice above the focal frame.
          </p>
        </div>
        <div className="volume-heading-evidence">
          <EvidenceBadge kind="synthetic" source="Scenario teaching bundle" />
          <span>Forecast geometry is derived from focal-state kinematics only.</span>
        </div>
      </header>

      <section className="volume-workbench" aria-label="3D affordance volume workbench">
        <div className="volume-stage">
          <div className="volume-stage-topline">
            <div>
              <span>{bundle.scenario?.title ?? scenarioId}</span>
              <strong>{channelCopy.label}</strong>
            </div>
            <div className="volume-frame-readout">
              <span>Frame {frame.frame_id}</span>
              <strong>{frame.timestamp_s.toFixed(2)}s</strong>
            </div>
          </div>
          <AffordanceVolume3D
            frame={frame}
            options={currentOptions}
            channel={channel}
            quality={quality}
            threshold={threshold}
            horizonSeconds={horizonSeconds}
            maxVoxels={quality === "high" ? 4200 : quality === "low" ? 1200 : 2800}
            onRuntime={setRuntime}
          />
          <label className="volume-frame-scrubber">
            <span>Decision timeline</span>
            <input
              type="range"
              min={0}
              max={bundle.frames.length - 1}
              value={Math.min(frameIndex, bundle.frames.length - 1)}
              onChange={(event) => setFrameIndex(Number(event.target.value))}
            />
            <output>
              {frame.frame_id} · {frame.timestamp_s.toFixed(2)}s
            </output>
          </label>
        </div>

        <aside className="volume-controls">
          <div className="volume-control-block">
            <p className="eyebrow">FIELD CHANNEL</p>
            <div className="volume-channel-grid">
              {channels.map((id) => (
                <button
                  key={id}
                  type="button"
                  className={id === channel ? "is-active" : undefined}
                  aria-pressed={id === channel}
                  onClick={() => setChannel(id)}
                >
                  <strong>{volumeChannelCopy[id].short}</strong>
                  <span>{volumeChannelCopy[id].label}</span>
                </button>
              ))}
            </div>
            <p className="volume-channel-explanation">{channelCopy.explanation}</p>
          </div>

          <div className="volume-control-block volume-threshold-control">
            <div>
              <p className="eyebrow">SPARSE VOXEL GATE</p>
              <strong>{threshold.toFixed(2)}</strong>
            </div>
            <input
              aria-label="Voxel signal threshold"
              type="range"
              min={0.05}
              max={0.65}
              step={0.025}
              value={threshold}
              onChange={(event) => setThreshold(Number(event.target.value))}
            />
            <p>
              Raising the gate removes weak cells before upload. The renderer spends its budget on
              the most informative parts of the tactical field.
            </p>
          </div>

          <div className="volume-control-block">
            <p className="eyebrow">ADAPTIVE LOD</p>
            <div className="volume-quality-picker">
              {qualities.map((id) => (
                <button
                  type="button"
                  key={id}
                  className={quality === id ? "is-active" : undefined}
                  aria-pressed={quality === id}
                  onClick={() => setQuality(id)}
                >
                  {id}
                </button>
              ))}
            </div>
          </div>

          <div className="volume-runtime-card" aria-live="polite">
            <p className="eyebrow">LIVE RENDER CONTRACT</p>
            <dl>
              <div>
                <dt>Backend</dt>
                <dd>{runtime?.backend.toUpperCase() ?? "initializing"}</dd>
              </div>
              <div>
                <dt>GPU draw calls</dt>
                <dd>{runtime?.renderer.drawCalls ?? 0}</dd>
              </div>
              <div>
                <dt>Field voxels</dt>
                <dd>{runtime?.field.renderedVoxels.toLocaleString() ?? "—"}</dd>
              </div>
              <div>
                <dt>Grid</dt>
                <dd>
                  {runtime
                    ? `${runtime.field.gridX}×${runtime.field.gridY}×${runtime.field.horizonSteps}`
                    : "—"}
                </dd>
              </div>
              <div>
                <dt>Current options</dt>
                <dd>{currentOptions.length}</dd>
              </div>
              <div>
                <dt>Horizon</dt>
                <dd>+{horizonSeconds.toFixed(1)}s</dd>
              </div>
            </dl>
          </div>
        </aside>
      </section>

      <section className="volume-interpretation-grid">
        <article>
          <p className="eyebrow">WHY THE THIRD AXIS EXISTS</p>
          <h2>Height means when, not where.</h2>
          <p>
            The bottom slice is the focal state. Every higher layer advances the same causal
            kinematic state toward +{horizonSeconds.toFixed(1)} seconds. A pressure ridge leaning
            forward is therefore a defender arriving, not a decorative mountain.
          </p>
        </article>
        <article>
          <p className="eyebrow">WHY VOXELS</p>
          <h2>Discrete enough to compare. Dense enough to feel continuous.</h2>
          <p>
            Each cell has a known pitch footprint, horizon slice, channel, value, and provenance.
            That makes screenshots dramatic while keeping every glowing block auditable back to a
            deterministic field computation.
          </p>
        </article>
        <article>
          <p className="eyebrow">WHAT THIS DOES NOT CLAIM</p>
          <h2>A beautiful forecast is still a forecast.</h2>
          <p>
            Future layers are generated from focal-state motion and frozen visualization formulas.
            They are not later observed tracking frames, calibrated probabilities, or expert
            labels. R1 benchmark evidence remains separate.
          </p>
        </article>
      </section>

      <section className="volume-showcase-strip">
        <div>
          <p className="eyebrow">SHOWCASE SEQUENCE</p>
          <h2>Start with Menu. Peel the field apart. Return to the decision.</h2>
        </div>
        <ol>
          <li>
            <span>01</span>
            <strong>Composite</strong>
            <p>Open on the full action-menu volume so the idea lands instantly.</p>
          </li>
          <li>
            <span>02</span>
            <strong>Pressure → shadow</strong>
            <p>Reveal the moving defensive front, then the space it screens behind itself.</p>
          </li>
          <li>
            <span>03</span>
            <strong>Space → creation</strong>
            <p>Show the difference between space that exists and space that is becoming available.</p>
          </li>
          <li>
            <span>04</span>
            <strong>Corridor → visibility</strong>
            <p>Finish by separating a physically available route from a perceptually accessible one.</p>
          </li>
        </ol>
        <Link className="text-link" to={`/scenario/${scenarioId}`}>
          Return to the 2D Decision Microscope →
        </Link>
      </section>
    </div>
  );
}
