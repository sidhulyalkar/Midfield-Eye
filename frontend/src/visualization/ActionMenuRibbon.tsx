import { useMemo } from "react";
import type { ActionOption, FrameState } from "../data/schemas";

type RibbonSeries = {
  key: string;
  label: string;
  optionsByFrame: Map<number, ActionOption>;
  peakScore: number;
};

export function stableActionKey(option: ActionOption): string {
  if (option.kind === "pass")
    return `pass:${option.target_player_id ?? "unknown"}`;
  if (option.kind === "hold") return "hold";
  const marker = ":carry:";
  const suffix = option.option_id.includes(marker)
    ? option.option_id.split(marker).at(-1)
    : "unknown";
  return `carry:${suffix}`;
}

function actionLabel(option: ActionOption): string {
  if (option.kind === "pass")
    return `Pass · ${option.target_player_id ?? "unknown"}`;
  if (option.kind === "hold") return "Hold";
  const key = stableActionKey(option).replace("carry:", "");
  return `Carry · ${key}°`;
}

export function ActionMenuRibbon({
  frames,
  options,
  currentFrameId,
  selectedOptionId,
  onSeek,
  onOptionSelect,
  maxRows = 9,
}: {
  frames: FrameState[];
  options: ActionOption[];
  currentFrameId: number;
  selectedOptionId: string | null;
  onSeek: (frameId: number) => void;
  onOptionSelect: (optionId: string) => void;
  maxRows?: number;
}) {
  const orderedFrames = useMemo(
    () => [...frames].sort((a, b) => a.frame_id - b.frame_id),
    [frames],
  );
  const series = useMemo(() => {
    const grouped = new Map<string, RibbonSeries>();
    for (const option of options) {
      const key = stableActionKey(option);
      const existing = grouped.get(key);
      if (existing) {
        existing.optionsByFrame.set(option.frame_id, option);
        existing.peakScore = Math.max(
          existing.peakScore,
          option.geometric_score,
        );
      } else {
        grouped.set(key, {
          key,
          label: actionLabel(option),
          optionsByFrame: new Map([[option.frame_id, option]]),
          peakScore: option.geometric_score,
        });
      }
    }
    return [...grouped.values()]
      .sort(
        (a, b) => b.peakScore - a.peakScore || a.label.localeCompare(b.label),
      )
      .slice(0, maxRows);
  }, [maxRows, options]);

  const scores = options.map((option) => option.geometric_score);
  const minimum = Math.min(...scores, 0);
  const maximum = Math.max(...scores, 1);
  const currentIndex = Math.max(
    0,
    orderedFrames.findIndex((frame) => frame.frame_id === currentFrameId),
  );

  return (
    <section className="action-menu-ribbon" aria-label="Action menu ribbon">
      <header className="ribbon-heading">
        <div>
          <p className="eyebrow">Option persistence · retrospective view</p>
          <h2>Action Menu Ribbon</h2>
        </div>
        <p>
          Brightness follows this scenario&apos;s frame score. Gaps mean the
          candidate is absent; they are not model predictions of impossibility.
        </p>
      </header>
      <div className="ribbon-clock" aria-hidden="true">
        <span>earlier</span>
        <strong>
          t {orderedFrames[currentIndex]?.timestamp_s.toFixed(2) ?? "0.00"}s
        </strong>
        <span>later</span>
      </div>
      <div className="ribbon-table">
        {series.map((row) => (
          <div className="ribbon-row" key={row.key}>
            <div className="ribbon-label">
              <strong>{row.label}</strong>
              <small>{row.optionsByFrame.size} frames observed</small>
            </div>
            <div
              className="ribbon-track"
              style={{
                gridTemplateColumns: `repeat(${Math.max(
                  orderedFrames.length,
                  1,
                )}, minmax(8px, 1fr))`,
              }}
            >
              {orderedFrames.map((frame) => {
                const option = row.optionsByFrame.get(frame.frame_id);
                if (!option) {
                  return (
                    <span
                      className={
                        frame.frame_id === currentFrameId
                          ? "ribbon-gap ribbon-current"
                          : "ribbon-gap"
                      }
                      key={frame.frame_id}
                    />
                  );
                }
                const normalized =
                  (option.geometric_score - minimum) /
                  Math.max(0.001, maximum - minimum);
                const selected = option.option_id === selectedOptionId;
                return (
                  <button
                    type="button"
                    key={frame.frame_id}
                    className={[
                      "ribbon-cell",
                      frame.frame_id === currentFrameId ? "ribbon-current" : "",
                      selected ? "ribbon-selected" : "",
                      option.label_selected === true
                        ? "ribbon-observed-selection"
                        : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    style={{ opacity: 0.25 + normalized * 0.75 }}
                    aria-label={`${row.label}, frame ${frame.frame_id}, score ${option.geometric_score.toFixed(3)}`}
                    aria-pressed={selected}
                    title={`${row.label} · t ${frame.timestamp_s.toFixed(2)}s · score ${option.geometric_score.toFixed(3)}`}
                    onClick={() => {
                      onSeek(frame.frame_id);
                      onOptionSelect(option.option_id);
                    }}
                  >
                    {option.label_selected === true ? (
                      <span className="selection-tick">●</span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {series.length < new Set(options.map(stableActionKey)).size ? (
        <p className="ribbon-overflow">
          Showing the {series.length} highest-peaking options for legibility.
        </p>
      ) : null}
    </section>
  );
}
