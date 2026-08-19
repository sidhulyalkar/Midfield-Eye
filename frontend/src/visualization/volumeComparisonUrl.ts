import type { VolumeComparisonChannel } from "./volumeComparison";

export const DEFAULT_COMPARISON_CHANNEL: VolumeComparisonChannel =
  "future_space";
export const EARLIER_RUN_COMPARISON_ID = "earlier-run";

export type VolumeComparisonUrlState = {
  comparisonId: typeof EARLIER_RUN_COMPARISON_ID;
  channel: VolumeComparisonChannel;
};

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
  };
}

export function writeVolumeComparisonUrl(
  params: URLSearchParams,
  state: VolumeComparisonUrlState,
): URLSearchParams {
  const next = new URLSearchParams(params);
  next.set("cmp", state.comparisonId);
  next.set("dc", state.channel);
  return next;
}
