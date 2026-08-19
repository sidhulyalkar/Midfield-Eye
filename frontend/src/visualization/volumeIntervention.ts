import type { FrameState, PlayerState } from "../data/schemas";

export type EarlierRunIntervention = {
  id: string;
  playerId: string;
  leadSeconds: number;
  speedMps: number;
  displacementM: number;
  from: readonly [number, number];
  to: readonly [number, number];
  baselineFrame: FrameState;
  alternativeFrame: FrameState;
};

const MIN_SPEED_MPS = 0.25;
export const DEFAULT_EARLIER_RUN_SECONDS = 0.75;

function velocity(player: PlayerState): readonly [number, number] | null {
  const vx = player.vx;
  const vy = player.vy;
  if (vx === null || vx === undefined || vy === null || vy === undefined) {
    return null;
  }
  if (!Number.isFinite(vx) || !Number.isFinite(vy)) return null;
  return [vx, vy];
}

function clonePlayer(player: PlayerState): PlayerState {
  return {
    ...player,
    metadata: { ...player.metadata },
    position_covariance: player.position_covariance
      ? player.position_covariance.map((row) => [...row])
      : player.position_covariance,
  };
}

function clip(value: number, maximum: number) {
  return Math.max(0, Math.min(maximum, value));
}

export function buildEarlierRunIntervention(
  frame: FrameState,
  leadSeconds = DEFAULT_EARLIER_RUN_SECONDS,
): EarlierRunIntervention | null {
  if (!Number.isFinite(leadSeconds) || leadSeconds <= 0 || leadSeconds > 2) {
    throw new Error("leadSeconds must be finite and within (0, 2].");
  }

  const candidates = frame.players
    .filter(
      (player) =>
        player.team === frame.possession_team &&
        player.player_id !== frame.ball_carrier_id,
    )
    .flatMap((player) => {
      const currentVelocity = velocity(player);
      if (!currentVelocity) return [];
      const speedMps = Math.hypot(currentVelocity[0], currentVelocity[1]);
      return speedMps >= MIN_SPEED_MPS
        ? [{ player, currentVelocity, speedMps }]
        : [];
    })
    .sort(
      (left, right) =>
        right.speedMps - left.speedMps ||
        left.player.player_id.localeCompare(right.player.player_id),
    );

  const candidate = candidates[0];
  if (!candidate) return null;

  const from: readonly [number, number] = [
    candidate.player.x,
    candidate.player.y,
  ];
  const to: readonly [number, number] = [
    clip(
      from[0] + candidate.currentVelocity[0] * leadSeconds,
      frame.pitch_length,
    ),
    clip(
      from[1] + candidate.currentVelocity[1] * leadSeconds,
      frame.pitch_width,
    ),
  ];
  const displacementM = Math.hypot(to[0] - from[0], to[1] - from[1]);
  if (displacementM < 1e-6) return null;

  const players = frame.players.map((player) => {
    const cloned = clonePlayer(player);
    return player.player_id === candidate.player.player_id
      ? { ...cloned, x: to[0], y: to[1] }
      : cloned;
  });
  const alternativeFrame: FrameState = {
    ...frame,
    players,
    quality_flags: [...frame.quality_flags, "teaching_position_intervention"],
    metadata: {
      ...frame.metadata,
      teaching_intervention: "earlier_run",
      teaching_intervention_player: candidate.player.player_id,
      teaching_intervention_seconds: leadSeconds,
    },
  };

  return {
    id: `earlier-run:${candidate.player.player_id}:${leadSeconds.toFixed(2)}`,
    playerId: candidate.player.player_id,
    leadSeconds,
    speedMps: candidate.speedMps,
    displacementM,
    from,
    to,
    baselineFrame: frame,
    alternativeFrame,
  };
}
