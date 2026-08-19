import type { VolumeQuality } from "./affordanceVolume";
import type { VolumeComparisonChannel } from "./volumeComparison";

export const DEFAULT_COMPARISON_CHANNEL: VolumeComparisonChannel =
  "future_space";
export const EARLIER_RUN_COMPARISON_ID = "earlier-run";
export const EARLIER_RUN_LEAD_PRESETS = [0.5, 0.75, 1] as const;
export type EarlierRunLeadSeconds = (typeof EARLIER_RUN_LEAD_PRESETS)[number];
export type DeterministicComparisonQuality = Exclude<VolumeQuality, "auto">;

export type VolumeComparisonUrlState = {
  comparisonId: typeof EARLIER_RUN_COMPARISON_ID;
  channel: VolumeComparisonChannel;
  leadSeconds: EarlierRunLeadSeconds;
  quality: DeterministicComparisonQuality;
  threshold: number;
};

function parseLead(value: string | null): EarlierRunLeadSeconds {
  const parsed = Number(value);
  return EARLIER_RUN_LEAD_PRESETS.find((preset) => preset === parsed) ?? 0.75;
}

function parseQuality(value: string | null): DeterministicComparisonQuality {
  return value === "low" || value === "high" ? value : "medium";
}

function parseThreshold(value: string | null) {
  if (value === null) return 0.2;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0.05 || parsed > 0.65) return 0.2;
  const snapped = Math.round(parsed / 0.025) * 0.025;
  return Math.min(0.65, Math.max(0.05, Number(snapped.toFixed(3))));
}

export function parseVolumeComparisonUrl(
  params: URLSearchParams,
): VolumeComparisonUrlState {
  const channel = params.get("dc");
  return {
    comparisonId: EARLIER_RUN_COMPARISON_ID,
    channel:
      channel === "option_creation" || channel === "future_space"
        ? channel
        : DEFAULT_COMPARISON_CHANNEL,
    leadSeconds: parseLead(params.get("lead")),
    quality: parseQuality(params.get("dq")),
    threshold: parseThreshold(params.get("dt")),
  };
}

export function parseComparisonFrameIndex(
  params: URLSearchParams,
  frameCount: number,
  defaultIndex: number,
): number {
  if (!Number.isInteger(frameCount) || frameCount < 1) return 0;
  const raw = params.get("fi");
  if (raw !== null && /^\d+$/u.test(raw)) {
    const parsed = Number(raw);
    if (Number.isSafeInteger(parsed) && parsed >= 0 && parsed < frameCount) {
      return parsed;
    }
  }
  return Math.min(Math.max(0, defaultIndex), frameCount - 1);
}

export function writeVolumeComparisonUrl(
  params: URLSearchParams,
  state: VolumeComparisonUrlState,
): URLSearchParams {
  const next = new URLSearchParams(params);
  next.set("cmp", state.comparisonId);
  next.set("dc", state.channel);
  next.set("lead", state.leadSeconds.toFixed(2));
  next.set("dq", state.quality);
  next.set("dt", state.threshold.toFixed(3));
  return next;
}

export function writeComparisonFrameIndex(
  params: URLSearchParams,
  frameIndex: number,
): URLSearchParams {
  if (!Number.isInteger(frameIndex) || frameIndex < 0) {
    throw new Error("frameIndex must be a non-negative integer.");
  }
  const next = new URLSearchParams(params);
  next.set("fi", String(frameIndex));
  return next;
}
