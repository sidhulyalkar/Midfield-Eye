import { useEffect, useMemo, useRef, useState } from "react";
import type { ActionOption, FrameState } from "../data/schemas";
import {
  buildAffordanceVolume,
  defaultVolumeConfig,
  type VolumeChannel,
  type VolumeQuality,
  type VolumeStats,
} from "./affordanceVolume";
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
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<AdaptiveVoxelRenderer | null>(null);
  const cameraRef = useRef<OrbitCamera>({ ...initialCamera });
  const pointerRef = useRef<{ id: number; x: number; y: number } | null>(null);
  const [backend, setBackend] = useState<VoxelBackend | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const publish = () => {
    const renderer = rendererRef.current;
    if (!renderer || !onRuntime) return;
    onRuntime({
      backend: renderer.kind,
      renderer: renderer.snapshot(),
      field: scene.stats,
    });
  };

  const render = () => {
    rendererRef.current?.render(cameraRef.current);
    publish();
  };

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
        renderer.update(scene);
        observer = new ResizeObserver((entries) => {
          const entry = entries[0];
          if (!entry) return;
          const ratio = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
          renderer.resize(
            entry.contentRect.width,
            entry.contentRect.height,
            ratio,
          );
          render();
        });
        observer.observe(canvas);
        const rect = canvas.getBoundingClientRect();
        renderer.resize(
          Math.max(1, rect.width),
          Math.max(1, rect.height),
          Math.min(2, Math.max(1, window.devicePixelRatio || 1)),
        );
        render();
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
    // Renderer lifecycle is tied to the canvas, not every scene mutation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    renderer.update(scene);
    renderer.render(cameraRef.current);
    publish();
    // publish is intentionally derived from the current renderer + scene.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene]);

  const pointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    pointerRef.current = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
    };
  };

  const pointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const pointer = pointerRef.current;
    if (!pointer || pointer.id !== event.pointerId) return;
    const dx = event.clientX - pointer.x;
    const dy = event.clientY - pointer.y;
    pointer.x = event.clientX;
    pointer.y = event.clientY;
    cameraRef.current.azimuth -= dx * 0.006;
    cameraRef.current.elevation = Math.max(
      0.16,
      Math.min(1.18, cameraRef.current.elevation + dy * 0.0045),
    );
    render();
  };

  const pointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
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
    render();
  };

  const resetCamera = () => {
    cameraRef.current = { ...initialCamera };
    render();
  };

  return (
    <div className="affordance-volume-shell">
      <canvas
        ref={canvasRef}
        className="affordance-volume-canvas"
        aria-label={`3D temporal affordance volume for frame ${frame.frame_id}`}
        onPointerDown={pointerDown}
        onPointerMove={pointerMove}
        onPointerUp={pointerUp}
        onPointerCancel={pointerUp}
        onWheel={wheel}
      />
      <div className="volume-canvas-hud" aria-live="polite">
        <span>{backend ? backend.toUpperCase() : "GPU init"}</span>
        <span>{scene.stats.renderedVoxels.toLocaleString()} voxels</span>
        <span>2-pass instancing</span>
      </div>
      <button
        className="volume-camera-reset"
        type="button"
        onClick={resetCamera}
      >
        Reset view
      </button>
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
  );
}
