import { useCallback, useEffect, useRef, useState } from "react";
import type { RendererSnapshot, VoxelBackend } from "./voxelRenderer";
import { AdaptiveVoxelRenderer, type OrbitCamera } from "./voxelRenderer";
import type {
  VolumeDifferenceRenderCell,
  VolumeDifferenceRenderPayload,
} from "./volumeDifferenceRender";
import {
  pickDifferenceCell,
  projectDifferenceCellToScreen,
} from "./volumeDifferencePicking";
import { updateDifferenceRenderer } from "./volumeDifferenceRendererAdapter";

type PointerState = {
  id: number;
  startX: number;
  startY: number;
  lastX: number;
  lastY: number;
  moved: boolean;
};

export type DifferenceVolumeRuntime = {
  backend: VoxelBackend;
  renderer: RendererSnapshot;
};

export type DifferenceVolume3DProps = {
  solids: Float32Array;
  payload: VolumeDifferenceRenderPayload;
  selectedKey: string | null;
  onSelectKey: (key: string | null) => void;
  onRuntime?: ((runtime: DifferenceVolumeRuntime) => void) | undefined;
};

const initialCamera: OrbitCamera = {
  azimuth: -0.72,
  elevation: 0.58,
  distance: 118,
  targetY: 5.5,
};

function compareIdentity(
  left: VolumeDifferenceRenderCell,
  right: VolumeDifferenceRenderCell,
) {
  return (
    left.comparison.layerIndex - right.comparison.layerIndex ||
    left.comparison.gridXIndex - right.comparison.gridXIndex ||
    left.comparison.gridYIndex - right.comparison.gridYIndex
  );
}

function mostInformativeVisibleCell(
  cells: readonly VolumeDifferenceRenderCell[],
): VolumeDifferenceRenderCell | null {
  let bestIntersection: VolumeDifferenceRenderCell | null = null;
  for (const cell of cells) {
    if (cell.absoluteDelta === null) continue;
    if (
      !bestIntersection ||
      bestIntersection.absoluteDelta === null ||
      cell.absoluteDelta > bestIntersection.absoluteDelta ||
      (cell.absoluteDelta === bestIntersection.absoluteDelta &&
        compareIdentity(cell, bestIntersection) < 0)
    ) {
      bestIntersection = cell;
    }
  }
  if (bestIntersection) return bestIntersection;
  return [...cells].sort(compareIdentity)[0] ?? null;
}

export function DifferenceVolume3D({
  solids,
  payload,
  selectedKey,
  onSelectKey,
  onRuntime,
}: DifferenceVolume3DProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<AdaptiveVoxelRenderer | null>(null);
  const cameraRef = useRef<OrbitCamera>({ ...initialCamera });
  const pointerRef = useRef<PointerState | null>(null);
  const payloadRef = useRef(payload);
  const solidsRef = useRef(solids);
  const selectedKeyRef = useRef(selectedKey);
  const onSelectKeyRef = useRef(onSelectKey);
  const onRuntimeRef = useRef(onRuntime);
  const [backend, setBackend] = useState<VoxelBackend | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [marker, setMarker] = useState<{
    key: string;
    left: number;
    top: number;
  } | null>(null);

  useEffect(() => {
    payloadRef.current = payload;
    solidsRef.current = solids;
    selectedKeyRef.current = selectedKey;
    onSelectKeyRef.current = onSelectKey;
    onRuntimeRef.current = onRuntime;
  }, [onRuntime, onSelectKey, payload, selectedKey, solids]);

  const publishRuntime = useCallback(() => {
    const renderer = rendererRef.current;
    if (!renderer || !onRuntimeRef.current) return;
    onRuntimeRef.current({ backend: renderer.kind, renderer: renderer.snapshot() });
  }, []);

  const updateMarker = useCallback(() => {
    const canvas = canvasRef.current;
    const key = selectedKeyRef.current;
    if (!canvas || !key) {
      setMarker(null);
      return;
    }
    const cell = payloadRef.current.cells.find((candidate) => candidate.key === key);
    if (!cell) {
      setMarker(null);
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const projected = projectDifferenceCellToScreen(
      cell,
      cameraRef.current,
      rect.width,
      rect.height,
    );
    setMarker(
      projected
        ? { key, left: projected.screenX, top: projected.screenY }
        : null,
    );
  }, []);

  const renderCurrent = useCallback(() => {
    rendererRef.current?.render(cameraRef.current);
    publishRuntime();
    updateMarker();
  }, [publishRuntime, updateMarker]);

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
        updateDifferenceRenderer(renderer, {
          solids: solidsRef.current,
          field: payloadRef.current.field,
        });
        observer = new ResizeObserver((entries) => {
          const entry = entries[0];
          if (!entry) return;
          const ratio = Math.min(2, Math.max(1, window.devicePixelRatio || 1));
          renderer.resize(
            Math.max(1, entry.contentRect.width),
            Math.max(1, entry.contentRect.height),
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
    const renderer = rendererRef.current;
    if (!renderer) return;
    updateDifferenceRenderer(renderer, { solids, field: payload.field });
    renderCurrent();
  }, [payload, renderCurrent, solids]);

  useEffect(() => {
    selectedKeyRef.current = selectedKey;
    updateMarker();
  }, [selectedKey, updateMarker]);

  const inspectAt = useCallback(
    (clientX: number, clientY: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const picked = pickDifferenceCell(
        payloadRef.current.cells,
        cameraRef.current,
        rect.width,
        rect.height,
        clientX - rect.left,
        clientY - rect.top,
      );
      onSelectKeyRef.current(picked?.cell.key ?? null);
    },
    [],
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

  const inspectMostInformative = () => {
    const cell = mostInformativeVisibleCell(payloadRef.current.cells);
    onSelectKeyRef.current(cell?.key ?? null);
  };

  const resetCamera = () => {
    cameraRef.current = { ...initialCamera };
    renderCurrent();
  };

  return (
    <section className="difference-volume-shell" data-testid="difference-volume-3d">
      <div className="difference-volume-toolbar">
        <div>
          <span>3D DIFFERENCE FIELD</span>
          <strong>{backend?.toUpperCase() ?? "initializing"}</strong>
        </div>
        <div>
          <button type="button" onClick={inspectMostInformative}>
            Inspect most informative visible cell
          </button>
          <button type="button" onClick={resetCamera}>
            Reset camera
          </button>
        </div>
      </div>
      <div className="difference-canvas-wrap">
        <canvas
          ref={canvasRef}
          aria-label="Interactive evidence-aware 3D difference volume. Drag to orbit, wheel to zoom, click a comparison cell to inspect it."
          onPointerDown={pointerDown}
          onPointerMove={pointerMove}
          onPointerUp={pointerUp}
          onPointerCancel={() => {
            pointerRef.current = null;
          }}
          onWheel={wheel}
        />
        {marker ? (
          <span
            className="difference-selection-marker"
            data-testid="difference-selection-marker"
            style={{ left: marker.left, top: marker.top }}
            aria-hidden="true"
          />
        ) : null}
        {error ? <p className="difference-render-error">{error}</p> : null}
      </div>
    </section>
  );
}
