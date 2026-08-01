import { create } from "zustand";

export type LayerId =
  "visibility" | "uncertainty" | "velocity" | "body" | "gaze" | "relations";
export type PlaybackRate = 0.25 | 0.5 | 1 | 2;
export type EvidenceView = "observed" | "uncertainty";

type PlaybackState = {
  scenarioId: string;
  frameIds: number[];
  currentFrameId: number;
  selectedOptionId: string | null;
  lockedOptionId: string | null;
  playing: boolean;
  playbackRate: PlaybackRate;
  layers: Record<LayerId, boolean>;
  evidenceView: EvidenceView;
  initialize: (
    scenarioId: string,
    frameIds: number[],
    initialFrame?: number,
  ) => void;
  seek: (frameId: number) => void;
  step: (delta: number) => void;
  selectOption: (id: string | null) => void;
  lockOption: (id: string | null) => void;
  setPlaying: (playing: boolean) => void;
  setRate: (rate: PlaybackRate) => void;
  setLayers: (layers: Record<LayerId, boolean>) => void;
  toggleLayer: (layer: LayerId) => void;
  setEvidenceView: (view: EvidenceView) => void;
};

const initialLayers: Record<LayerId, boolean> = {
  visibility: true,
  uncertainty: true,
  velocity: true,
  body: true,
  gaze: true,
  relations: false,
};

export const usePlaybackStore = create<PlaybackState>((set, get) => ({
  scenarioId: "",
  frameIds: [],
  currentFrameId: 0,
  selectedOptionId: null,
  lockedOptionId: null,
  playing: false,
  playbackRate: 1,
  layers: initialLayers,
  evidenceView: "uncertainty",
  initialize: (scenarioId, frameIds, initialFrame) =>
    set((state) => {
      if (
        state.scenarioId === scenarioId &&
        state.frameIds.length === frameIds.length
      )
        return state;
      const candidate = initialFrame ?? frameIds[0] ?? 0;
      return {
        scenarioId,
        frameIds,
        currentFrameId: frameIds.includes(candidate)
          ? candidate
          : (frameIds[0] ?? 0),
        selectedOptionId: null,
        lockedOptionId: null,
        playing: false,
      };
    }),
  seek: (frameId) => {
    if (get().frameIds.includes(frameId)) set({ currentFrameId: frameId });
  },
  step: (delta) =>
    set((state) => {
      const index = state.frameIds.indexOf(state.currentFrameId);
      const next = Math.max(
        0,
        Math.min(state.frameIds.length - 1, index + delta),
      );
      return { currentFrameId: state.frameIds[next] ?? state.currentFrameId };
    }),
  selectOption: (selectedOptionId) => set({ selectedOptionId }),
  lockOption: (lockedOptionId) =>
    set({ lockedOptionId, selectedOptionId: lockedOptionId }),
  setPlaying: (playing) => set({ playing }),
  setRate: (playbackRate) => set({ playbackRate }),
  setLayers: (layers) => set({ layers }),
  toggleLayer: (layer) =>
    set((state) => ({
      layers: { ...state.layers, [layer]: !state.layers[layer] },
    })),
  setEvidenceView: (evidenceView) => set({ evidenceView }),
}));
