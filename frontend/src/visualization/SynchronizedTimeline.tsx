import type { TimelinePoint } from "../data/schemas";

export function SynchronizedTimeline({
  timeline,
  currentFrameId,
  onSeek,
}: {
  timeline: TimelinePoint[];
  currentFrameId: number;
  onSeek: (frameId: number) => void;
}) {
  const maxBreadth = Math.max(
    ...timeline.map((point) => point.menu_breadth),
    1,
  );
  const currentIndex = Math.max(
    0,
    timeline.findIndex((point) => point.frame_id === currentFrameId),
  );
  return (
    <section
      className="timeline-panel"
      aria-label="Synchronized action-menu timeline"
    >
      <header>
        <div>
          <p className="eyebrow">One clock · all evidence</p>
          <h2>How the menu changes</h2>
        </div>
        <span>
          {timeline[currentIndex]?.menu_breadth ?? 0} modeled available actions
        </span>
      </header>
      <div className="timeline-chart" aria-hidden="true">
        {timeline.map((point) => (
          <button
            type="button"
            key={point.frame_id}
            className={
              point.frame_id === currentFrameId ? "timeline-current" : ""
            }
            style={{
              height: `${Math.max(8, (point.menu_breadth / maxBreadth) * 100)}%`,
            }}
            onClick={() => onSeek(point.frame_id)}
            tabIndex={-1}
          />
        ))}
      </div>
      <label className="timeline-scrubber">
        <span className="sr-only">Current frame</span>
        <input
          type="range"
          min={0}
          max={Math.max(0, timeline.length - 1)}
          value={currentIndex}
          onChange={(event) => {
            const point = timeline[Number(event.target.value)];
            if (point) onSeek(point.frame_id);
          }}
        />
        <span>
          {timeline[currentIndex]?.timestamp_s.toFixed(2) ?? "0.00"} seconds
        </span>
      </label>
    </section>
  );
}
