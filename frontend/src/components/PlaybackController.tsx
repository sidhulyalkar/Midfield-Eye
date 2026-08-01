import { useEffect, useRef } from "react";
import { usePlaybackStore, type PlaybackRate } from "../state/playbackStore";

export function PlaybackController({
  timestamps,
}: {
  timestamps: Map<number, number>;
}) {
  const {
    currentFrameId,
    frameIds,
    playing,
    playbackRate,
    setPlaying,
    setRate,
    step,
  } = usePlaybackStore();
  const elapsedRef = useRef({ at: 0, accumulated: 0 });
  const wasPlayingBeforeHidden = useRef(false);

  useEffect(() => {
    if (!playing) {
      elapsedRef.current = { at: 0, accumulated: 0 };
      return;
    }
    let animationFrame = 0;
    const tick = (now: number) => {
      if (!elapsedRef.current.at) elapsedRef.current.at = now;
      const elapsed = ((now - elapsedRef.current.at) / 1000) * playbackRate;
      const index = frameIds.indexOf(
        usePlaybackStore.getState().currentFrameId,
      );
      const current = frameIds[index];
      const next = frameIds[index + 1];
      if (current == null || next == null) {
        setPlaying(false);
        return;
      }
      const frameDuration = Math.max(
        1 / 60,
        (timestamps.get(next) ?? 0) - (timestamps.get(current) ?? 0),
      );
      if (elapsed >= frameDuration) {
        elapsedRef.current.at = now;
        usePlaybackStore.getState().step(1);
      }
      animationFrame = requestAnimationFrame(tick);
    };
    animationFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrame);
  }, [frameIds, playbackRate, playing, setPlaying, timestamps]);

  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) {
        wasPlayingBeforeHidden.current = usePlaybackStore.getState().playing;
        setPlaying(false);
      } else if (wasPlayingBeforeHidden.current) {
        wasPlayingBeforeHidden.current = false;
        setPlaying(true);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [setPlaying]);

  return (
    <div className="playback-controls" aria-label="Playback controls">
      <button
        type="button"
        onClick={() => step(-1)}
        aria-label="Previous frame"
      >
        ←
      </button>
      <button
        className="play-button"
        type="button"
        onClick={() => setPlaying(!playing)}
      >
        {playing ? "Pause" : "Play"}
      </button>
      <button type="button" onClick={() => step(1)} aria-label="Next frame">
        →
      </button>
      <span className="time-readout">
        {timestamps.get(currentFrameId)?.toFixed(2) ?? "0.00"}s
      </span>
      <label>
        <span className="sr-only">Playback rate</span>
        <select
          value={playbackRate}
          onChange={(event) =>
            setRate(Number(event.target.value) as PlaybackRate)
          }
        >
          {[0.25, 0.5, 1, 2].map((rate) => (
            <option key={rate} value={rate}>
              {rate}×
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
