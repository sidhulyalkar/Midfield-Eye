import type { ActionOption, FrameState } from "../data/schemas";
import { ActionMenuRibbon } from "./ActionMenuRibbon";

export function DecisionMicroscope({
  frames,
  options,
  currentFrameId,
  selectedOptionId,
  onSeek,
  onOptionSelect,
}: {
  frames: FrameState[];
  options: ActionOption[];
  currentFrameId: number;
  selectedOptionId: string | null;
  onSeek: (frameId: number) => void;
  onOptionSelect: (optionId: string) => void;
}) {
  return (
    <section
      className="decision-microscope"
      aria-labelledby="decision-microscope-title"
    >
      <header>
        <div>
          <p className="eyebrow">Decision microscope · one clock</p>
          <h2 id="decision-microscope-title">
            Watch the menu reorganize around the player.
          </h2>
        </div>
        <p>
          The ribbon tracks stable candidate identities across frames. It is
          retrospective visualization, not a future-aware model input: option
          birth and extinction are only named after the sequence is observed.
        </p>
      </header>
      <ActionMenuRibbon
        frames={frames}
        options={options}
        currentFrameId={currentFrameId}
        selectedOptionId={selectedOptionId}
        onSeek={onSeek}
        onOptionSelect={onOptionSelect}
      />
    </section>
  );
}
