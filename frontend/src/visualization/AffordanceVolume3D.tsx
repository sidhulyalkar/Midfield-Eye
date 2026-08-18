import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ActionOption, FrameState } from "../data/schemas";
import {
  buildAffordanceVolume,
  defaultVolumeConfig,
  type VolumeChannel,
  type VolumeQuality,
  type VolumeScene,
  type VolumeStats,
  type VolumeVoxel,
} from "./affordanceVolume";
import {
  addTemporalGuideRails,
  buildRetainedVoxelTrajectory,
  filterVolumeScene,
  FULL_TEMPORAL_FILTER,
  horizonSecondsForLayer,
  temporalFilterLabel,
  type VolumeTemporalFilter,
} from "./volumeTemporal";
import {
  pickVolumeVoxel,
  projectVoxelToScreen,
  strongestVisibleVoxel,
} from "./voxelInspector";
import {
  AdaptiveVoxelRenderer,
  type OrbitCamera,
  type RendererSnapshot,
  type VoxelBackend,
} from "./voxelRenderer";

export type AffordanceVolumeRuntime = {
  backend: VoxelBackend;
  renderer: RendererSnapshot;
  field: VolumeStats;
  fullField: VolumeStats;
  temporalFilter: VolumeTemporalFilter;
};

export type AffordanceVolumeSceneState = {
  fullScene: VolumeScene;
  visibleScene: VolumeScene;
  temporalFilter: VolumeTemporalFilter;
};

export type AffordanceVolumeHandle = {
  inspectStrongest(): void;
  selectVoxelById(id: string): void;
  clearSelection(): void;
  resetCamera(): void;
};

type Props = {
  frame: FrameState;
  options: ActionOption[];
  channel: VolumeChannel;
  quality: VolumeQuality;
  threshold: number;
  horizonSeconds?: number | undefined;
  maxVoxels?: number | undefined;
  temporalFilter?: VolumeTemporalFilter | undefined;
  onTemporalFilterChange?: ((filter: VolumeTemporalFilter) => void) | undefined;
  onRuntime?: ((runtime: AffordanceVolumeRuntime) => void) | undefined;
  onScene?: ((state: AffordanceVolumeSceneState) => void) | undefined;
  onInspect?: ((voxel: VolumeVoxel | null) => void) | undefined;
};

type PointerState = {
  id: number;
  startX: number;
  startY: number;
  lastX: number;
  lastY: number;
  moved: boolean;
};

type SelectionMarker = {
  id: string;
  left: number;
  top: number;
};

const initialCamera: OrbitCamera = {
  azimuth: -0.72,
  elevation: 0.58,
  distance: 118,
  targetY: 5.5,
};

function defaultSliceLayer(horizonSteps: number): number {
  return Math.min(2, Math.max(0, horizonSteps - 1));
}

function defaultBand(horizonSteps: number): VolumeTemporalFilter {
  return {
    mode: "band",
    startLayerIndex: Math.min(1, Math.max(0, horizonSteps - 1)),
    endLayerIndex: Math.min(4, Math.max(0, horizonSteps - 1)),
  };
}

export const AffordanceVolume3D = forwardRef<AffordanceVolumeHandle, Props>(
  function AffordanceVolume3D(
    {
      frame,
      options,
      channel,
      quality,
      threshold,
      horizonSeconds = 1.5,
      maxVoxels = 2600,
      temporalFilter,
      onTemporalFilterChange,
      onRuntime,
      onScene,
      onInspect,
    },
    ref,
  ) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rendererRef = useRef<AdaptiveVoxelRenderer | null>(null);
    const cameraRef = useRef<OrbitCamera>({ ...initialCamera });
    const pointerRef = useRef<PointerState | null>(null);
    const selectedVoxelIdRef = useRef<string | null>(null);
    const onRuntimeRef = useRef(onRuntime);
    const onSceneRef = useRef(onScene);
    const onInspectRef = useRef(onInspect);
    const onTemporalFilterChangeRef = useRef(onTemporalFilterChange);
    const [backend, setBackend] = useState<VoxelBackend | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [selectionMarker, setSelectionMarker] =
      useState<SelectionMarker | null>(null);
    const [selectedVoxel, setSelectedVoxel] = useState<VolumeVoxel | null>(null);
    const [internalTemporalFilter, setInternalTemporalFilter] =
      useState<VolumeTemporalFilter>(FULL_TEMPORAL_FILTER);

    const activeTemporalFilter = temporalFilter ?? internalTemporalFilter;

    const fullScene = useMemo(() => {
      const config = defaultVolumeConfig(channel);
      return buildAffordanceVolume(frame, options, {
        ...config,
        channel,
        quality,
        threshold,
        horizonSeconds,
        maxVoxels,
      });
    }, [
      channel,
      frame,
      horizonSeconds,
      maxVoxels,
      options,
      quality,
      threshold,
    ]);

    const scene = useMemo(() => {
      const filtered = filterVolumeScene(fullScene, activeTemporalFilter);
      return addTemporalGuideRails(
        filtered,
        activeTemporalFilter,
        frame.pitch_length,
        frame.pitch_width,
      );
    }, [activeTemporalFilter, frame.pitch_length, frame.pitch_width, fullScene]);

    const sceneRef = useRef(scene);
    const fullSceneRef = useRef(fullScene);
    const temporalFilterRef = useRef(activeTemporalFilter);

    const trajectory = useMemo(
      () =>
        selectedVoxel
          ? buildRetainedVoxelTrajectory(
              fullScene.voxels,
              selectedVoxel,
              fullScene.stats.horizonSteps,
              horizonSeconds,
            )
          : null,
      [fullScene, horizonSeconds, selectedVoxel],
    );

    useEffect(() => {
      onRuntimeRef.current = onRuntime;
    }, [onRuntime]);

    useEffect(() => {
      onSceneRef.current = onScene;
    }, [onScene]);

    useEffect(() => {
      onInspectRef.current = onInspect;
    }, [onInspect]);

    useEffect(() => {
      onTemporalFilterChangeRef.current = onTemporalFilterChange;
    }, [onTemporalFilterChange]);

    const publishCurrent = useCallback(() => {
      const renderer = rendererRef.current;
      if (!renderer || !onRuntimeRef.current) return;
      onRuntimeRef.current({
        backend: renderer.kind,
        renderer: renderer.snapshot(),
        field: sceneRef.current.stats,
        fullField: fullSceneRef.current.stats,
        temporalFilter: temporalFilterRef.current,
      });
    }, []);

    const updateSelectionMarker = useCallback(() => {
      const canvas = canvasRef.current;
      const selectedId = selectedVoxelIdRef.current;
      if (!canvas || !selectedId) {
        setSelectionMarker(null);
        return;
      }
      const voxel = sceneRef.current.voxels.find(
        (item) => item.id === selectedId,
      );
      if (!voxel) {
        setSelectionMarker(null);
        return;
      }
      const rect = canvas.getBoundingClientRect();
      const projected = projectVoxelToScreen(
        voxel,
        cameraRef.current,
        rect.width,
        rect.height,
      );
      if (!projected) {
        setSelectionMarker(null);
        return;
      }
      setSelectionMarker({
        id: selectedId,
        left: projected.screenX,
        top: projected.screenY,
      });
    }, []);

    const renderCurrent = useCallback(() => {
      rendererRef.current?.render(cameraRef.current);
      publishCurrent();
      updateSelectionMarker();
    }, [publishCurrent, updateSelectionMarker]);

    const clearSelection = useCallback(() => {
      selectedVoxelIdRef.current = null;
      setSelectionMarker(null);
      setSelectedVoxel(null);
      onInspectRef.current?.(null);
    }, []);

    const selectVoxel = useCallback(
      (voxel: VolumeVoxel, left?: number, top?: number) => {
        selectedVoxelIdRef.current = voxel.id;
        setSelectedVoxel(voxel);
        onInspectRef.current?.(voxel);
        if (left !== undefined && top !== undefined) {
          setSelectionMarker({ id: voxel.id, left, top });
        } else {
          updateSelectionMarker();
        }
      },
      [updateSelectionMarker],
    );

    const selectVoxelById = useCallback(
      (id: string) => {
        const voxel = sceneRef.current.voxels.find((item) => item.id === id);
        if (!voxel) {
          clearSelection();
          return;
        }
        selectVoxel(voxel);
      },
      [clearSelection, selectVoxel],
    );

    const changeTemporalFilter = useCallback(
      (next: VolumeTemporalFilter) => {
        if (temporalFilter === undefined) setInternalTemporalFilter(next);
        onTemporalFilterChangeRef.current?.(next);
      },
      [temporalFilter],
    );

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      let cancelled = false;
      let observer: ResizeObserver | null = null;
      void AdaptiveVoxelRenderer.create(canvas)
        .then((renderer) => {
          if (cancelled) {
            renderer.dispose();
            return;
          }
          rendererRef.current = renderer;
          setBackend(renderer.kind);
          renderer.update(sceneRef.current);
          observer = new ResizeObserver((entries) => {
            const entry = entries[0];
            if (!entry) return;
            const ratio = Math.min(
              2,
              Math.max(1, window.devicePixelRatio || 1),
            );
            renderer.resize(
              entry.contentRect.width,
              entry.contentRect.height,
              ratio,
            );
            renderCurrent();
          });
          observer.observe(canvas);
          const rect = canvas.getBoundingClientRect();
          renderer.resize(
            Math.max(1, rect.width),
            Math.max(1, rect.height),
            Math.min(2, Math.max(1, window.devicePixelRatio || 1)),
          );
          renderCurrent();
        })
        .catch((reason: unknown) => {
          if (cancelled) return;
          setError(
            reason instanceof Error
              ? reason.message
              : "3D renderer unavailable.",
          );
        });
      return () => {
        cancelled = true;
        observer?.disconnect();
        rendererRef.current?.dispose();
        rendererRef.current = null;
      };
    }, [renderCurrent]);

    useEffect(() => {
      sceneRef.current = scene;
      fullSceneRef.current = fullScene;
      temporalFilterRef.current = activeTemporalFilter;
      onSceneRef.current?.({
        fullScene,
        visibleScene: scene,
        temporalFilter: activeTemporalFilter,
      });
      const selectedId = selectedVoxelIdRef.current;
      if (
        selectedId &&
        !scene.voxels.some((voxel) => voxel.id === selectedId)
      ) {
        clearSelection();
      }
      const renderer = rendererRef.current;
      if (!renderer) return;
      renderer.update(scene);
      renderCurrent();
    }, [activeTemporalFilter, clearSelection, fullScene, renderCurrent, scene]);

    const inspectAt = useCallback(
      (clientX: number, clientY: number) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const localX = clientX - rect.left;
        const localY = clientY - rect.top;
        const pick = pickVolumeVoxel(
          sceneRef.current.voxels,
          cameraRef.current,
          rect.width,
          rect.height,
          localX,
          localY,
        );
        if (!pick) {
          clearSelection();
          return;
        }
        selectVoxel(pick.voxel, pick.screenX, pick.screenY);
      },
      [clearSelection, selectVoxel],
    );

    const inspectStrongest = useCallback(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const projected = strongestVisibleVoxel(
        sceneRef.current.voxels,
        cameraRef.current,
        rect.width,
        rect.height,
      );
      if (!projected) {
        clearSelection();
        return;
      }
      selectVoxel(projected.voxel, projected.screenX, projected.screenY);
    }, [clearSelection, selectVoxel]);

    const resetCamera = useCallback(() => {
      cameraRef.current = { ...initialCamera };
      renderCurrent();
    }, [renderCurrent]);

    useImperativeHandle(
      ref,
      () => ({
        inspectStrongest,
        selectVoxelById,
        clearSelection,
        resetCamera,
      }),
      [clearSelection, inspectStrongest, resetCamera, selectVoxelById],
    );

    const pointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      pointerRef.current = {
        id: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        lastX: event.clientX,
        lastY: event.clientY,
        moved: false,
      };
    };

    const pointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
      const pointer = pointerRef.current;
      if (!pointer || pointer.id !== event.pointerId) return;
      const dx = event.clientX - pointer.lastX;
      const dy = event.clientY - pointer.lastY;
      pointer.lastX = event.clientX;
      pointer.lastY = event.clientY;
      if (
        Math.hypot(
          event.clientX - pointer.startX,
          event.clientY - pointer.startY,
        ) > 5
      ) {
        pointer.moved = true;
      }
      cameraRef.current.azimuth -= dx * 0.006;
      cameraRef.current.elevation = Math.max(
        0.16,
        Math.min(1.18, cameraRef.current.elevation + dy * 0.0045),
      );
      renderCurrent();
    };

    const pointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
      const pointer = pointerRef.current;
      if (!pointer || pointer.id !== event.pointerId) return;
      pointerRef.current = null;
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      if (!pointer.moved) inspectAt(event.clientX, event.clientY);
    };

    const pointerCancel = (event: React.PointerEvent<HTMLCanvasElement>) => {
      if (pointerRef.current?.id === event.pointerId) pointerRef.current = null;
    };

    const wheel = (event: React.WheelEvent<HTMLCanvasElement>) => {
      event.preventDefault();
      cameraRef.current.distance = Math.max(
        70,
        Math.min(
          190,
          cameraRef.current.distance * Math.exp(event.deltaY * 0.0012),
        ),
      );
      renderCurrent();
    };

    const filterLabel = temporalFilterLabel(
      activeTemporalFilter,
      fullScene.stats.horizonSteps,
      horizonSeconds,
    );
    const layerIndices = Array.from(
      { length: fullScene.stats.horizonSteps },
      (_, index) => index,
    );

    return (
      <div className="affordance-volume-shell">
        <div className="volume-temporal-surgery" data-testid="temporal-surgery">
          <div className="volume-temporal-heading">
            <div>
              <span>TIME SLICE SURGERY · V1.2</span>
              <strong>{filterLabel}</strong>
            </div>
            <p>
              View-only filtering over retained voxels. Missing layers remain
              missing; values are never recomputed.
            </p>
          </div>
          <div className="volume-temporal-modes" aria-label="Temporal view mode">
            <button
              type="button"
              aria-pressed={activeTemporalFilter.mode === "full"}
              onClick={() => changeTemporalFilter(FULL_TEMPORAL_FILTER)}
            >
              Full
            </button>
            <button
              type="button"
              aria-pressed={activeTemporalFilter.mode === "slice"}
              onClick={() =>
                changeTemporalFilter({
                  mode: "slice",
                  layerIndex:
                    activeTemporalFilter.mode === "slice"
                      ? activeTemporalFilter.layerIndex
                      : defaultSliceLayer(fullScene.stats.horizonSteps),
                })
              }
            >
              Slice
            </button>
            <button
              type="button"
              aria-pressed={activeTemporalFilter.mode === "band"}
              onClick={() =>
                changeTemporalFilter(
                  activeTemporalFilter.mode === "band"
                    ? activeTemporalFilter
                    : defaultBand(fullScene.stats.horizonSteps),
                )
              }
            >
              Band
            </button>
          </div>
          {activeTemporalFilter.mode === "slice" ? (
            <div className="volume-layer-picker" aria-label="Slice horizon">
              {layerIndices.map((layerIndex) => {
                const seconds = horizonSecondsForLayer(
                  layerIndex,
                  fullScene.stats.horizonSteps,
                  horizonSeconds,
                );
                return (
                  <button
                    type="button"
                    key={layerIndex}
                    aria-pressed={activeTemporalFilter.layerIndex === layerIndex}
                    onClick={() =>
                      changeTemporalFilter({ mode: "slice", layerIndex })
                    }
                  >
                    +{seconds.toFixed(2)} s
                  </button>
                );
              })}
            </div>
          ) : null}
          {activeTemporalFilter.mode === "band" ? (
            <div className="volume-band-picker">
              <label>
                <span>From</span>
                <select
                  aria-label="Band start layer"
                  value={activeTemporalFilter.startLayerIndex}
                  onChange={(event) => {
                    const startLayerIndex = Number(event.target.value);
                    changeTemporalFilter({
                      mode: "band",
                      startLayerIndex,
                      endLayerIndex: Math.max(
                        startLayerIndex,
                        activeTemporalFilter.endLayerIndex,
                      ),
                    });
                  }}
                >
                  {layerIndices.map((layerIndex) => (
                    <option key={layerIndex} value={layerIndex}>
                      +
                      {horizonSecondsForLayer(
                        layerIndex,
                        fullScene.stats.horizonSteps,
                        horizonSeconds,
                      ).toFixed(2)}{" "}
                      s
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>To</span>
                <select
                  aria-label="Band end layer"
                  value={activeTemporalFilter.endLayerIndex}
                  onChange={(event) => {
                    const endLayerIndex = Number(event.target.value);
                    changeTemporalFilter({
                      mode: "band",
                      startLayerIndex: Math.min(
                        activeTemporalFilter.startLayerIndex,
                        endLayerIndex,
                      ),
                      endLayerIndex,
                    });
                  }}
                >
                  {layerIndices.map((layerIndex) => (
                    <option key={layerIndex} value={layerIndex}>
                      +
                      {horizonSecondsForLayer(
                        layerIndex,
                        fullScene.stats.horizonSteps,
                        horizonSeconds,
                      ).toFixed(2)}{" "}
                      s
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : null}
        </div>
        <div
          className="volume-canvas-stage"
          style={{ position: "relative", minHeight: "inherit" }}
        >
          <canvas
            ref={canvasRef}
            className="affordance-volume-canvas"
            aria-label={`3D temporal affordance volume for frame ${frame.frame_id}. Click a voxel to inspect it; drag to orbit and scroll to zoom.`}
            onPointerDown={pointerDown}
            onPointerMove={pointerMove}
            onPointerUp={pointerUp}
            onPointerCancel={pointerCancel}
            onWheel={wheel}
          />
          <div className="volume-canvas-hud" aria-live="polite">
            <span>{backend ? backend.toUpperCase() : "GPU init"}</span>
            <span>
              {scene.stats.renderedVoxels.toLocaleString()} /{" "}
              {fullScene.stats.renderedVoxels.toLocaleString()} voxels
            </span>
            <span>2-pass instancing</span>
            <span>Inspector v1.2</span>
            <span data-testid="temporal-filter-hud">{filterLabel}</span>
          </div>
          {selectionMarker ? (
            <div
              className="volume-selection-marker"
              data-testid="voxel-selection-marker"
              style={{ left: selectionMarker.left, top: selectionMarker.top }}
              aria-hidden="true"
            >
              <i />
            </div>
          ) : null}
          <div className="volume-time-axis" aria-hidden="true">
            <span>+{horizonSeconds.toFixed(1)}s</span>
            <i />
            <span>Now</span>
          </div>
          {error ? (
            <div className="volume-render-error" role="status">
              <strong>3D acceleration unavailable</strong>
              <span>{error}</span>
            </div>
          ) : null}
        </div>
        {trajectory ? (
          <div className="volume-trajectory" data-testid="voxel-trajectory">
            <div>
              <span>SAME PITCH CELL</span>
              <strong>
                {selectedVoxel?.gridXIndex},{selectedVoxel?.gridYIndex}
              </strong>
            </div>
            <ol>
              {trajectory.map((point) => (
                <li
                  key={point.layerIndex}
                  className={
                    point.layerIndex === selectedVoxel?.layerIndex
                      ? "is-selected"
                      : undefined
                  }
                  data-status={point.status}
                >
                  <span>+{point.forecastSeconds.toFixed(2)} s</span>
                  <strong>
                    {point.status === "retained"
                      ? point.value?.toFixed(3)
                      : "gap"}
                  </strong>
                </li>
              ))}
            </ol>
            <p>
              Gaps mean no retained voxel survived threshold/LOD at this cell and
              layer. They are not zeros and are never interpolated.
            </p>
          </div>
        ) : null}
        <div
          className="volume-camera-actions"
          style={{
            position: "static",
            maxWidth: "none",
            padding: "0.55rem 0.75rem",
            borderTop: "1px solid var(--color-border)",
            background: "rgba(4, 13, 11, 0.78)",
            justifyContent: "flex-start",
          }}
        >
          {selectionMarker ? (
            <button type="button" onClick={clearSelection}>
              Clear selection
            </button>
          ) : null}
          <button type="button" onClick={resetCamera}>
            Reset view
          </button>
        </div>
      </div>
    );
  },
);
