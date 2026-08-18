import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ActionOption, FrameState } from "../data/schemas";
import {
  buildAffordanceVolume,
  defaultVolumeConfig,
  type VolumeChannel,
  type VolumeQuality,
  type VolumeStats,
  type VolumeVoxel,
} from "./affordanceVolume";
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
};

type Props = {
  frame: FrameState;
  options: ActionOption[];
  channel: VolumeChannel;
  quality: VolumeQuality;
  threshold: number;
  horizonSeconds?: number | undefined;
  maxVoxels?: number | undefined;
  onRuntime?: ((runtime: AffordanceVolumeRuntime) => void) | undefined;
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

export function AffordanceVolume3D({
  frame,
  options,
  channel,
  quality,
  threshold,
  horizonSeconds = 1.5,
  maxVoxels = 2600,
  onRuntime,
  onInspect,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<AdaptiveVoxelRenderer | null>(null);
  const cameraRef = useRef<OrbitCamera>({ ...initialCamera });
  const pointerRef = useRef<PointerState | null>(null);
  const selectedVoxelIdRef = useRef<string | null>(null);
  const onRuntimeRef = useRef(onRuntime);
  const onInspectRef = useRef(onInspect);
  const [backend, setBackend] = useState<VoxelBackend | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectionMarker, setSelectionMarker] =
    useState<SelectionMarker | null>(null);

  const scene = useMemo(() => {
    const config = defaultVolumeConfig(channel);
    return buildAffordanceVolume(frame, options, {
      ...config,
      channel,
      quality,
      threshold,
      horizonSeconds,
      maxVoxels,
    });
  }, [channel, frame, horizonSeconds, maxVoxels, options, quality, threshold]);
  const sceneRef = useRef(scene);

  useEffect(() => {
    onRuntimeRef.current = onRuntime;
  }, [onRuntime]);

  useEffect(() => {
    onInspectRef.current = onInspect;
  }, [onInspect]);

  const publishCurrent = useCallback(() => {
    const renderer = rendererRef.current;
    if (!renderer || !onRuntimeRef.current) return;
    onRuntimeRef.current({
      backend: renderer.kind,
      renderer: renderer.snapshot(),
      field: sceneRef.current.stats,
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
    onInspectRef.current?.(null);
  }, []);

  const selectVoxel = useCallback(
    (voxel: VolumeVoxel, left?: number, top?: number) => {
      selectedVoxelIdRef.current = voxel.id;
      onInspectRef.current?.(voxel);
      if (left !== undefined && top !== undefined) {
        setSelectionMarker({ id: voxel.id, left, top });
      } else {
        updateSelectionMarker();
      }
    },
    [updateSelectionMarker],
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
          const ratio = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
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
          reason instanceof Error ? reason.message : "3D renderer unavailable.",
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
    const selectedId = selectedVoxelIdRef.current;
    if (selectedId && !scene.voxels.some((voxel) => voxel.id === selectedId)) {
      clearSelection();
    }
    const renderer = rendererRef.current;
    if (!renderer) return;
    renderer.update(scene);
    renderCurrent();
  }, [clearSelection, renderCurrent, scene]);

  const inspectAt = (clientX: number, clientY: number) => {
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
  };

  const inspectStrongest = () => {
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
  };

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

  const resetCamera = () => {
    cameraRef.current = { ...initialCamera };
    renderCurrent();
  };

  return (
    <div className="affordance-volume-shell">
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
          <span>{scene.stats.renderedVoxels.toLocaleString()} voxels</span>
          <span>2-pass instancing</span>
          <span>Inspector v1.1</span>
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
        <button type="button" onClick={inspectStrongest}>
          Inspect strongest voxel
        </button>
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
}
