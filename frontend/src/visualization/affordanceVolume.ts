import type { ActionOption, FrameState, PlayerState } from "../data/schemas";

export type VolumeChannel =
  | "menu"
  | "pressure"
  | "pressure_shadow"
  | "future_space"
  | "passing_corridors"
  | "option_creation"
  | "visibility"
  | "uncertainty";

export type VolumeQuality = "auto" | "low" | "medium" | "high";

export type VolumeConfig = {
  channel: VolumeChannel;
  quality: VolumeQuality;
  threshold: number;
  horizonSeconds: number;
  horizonSteps: number;
  maxVoxels: number;
};

export type VolumeStats = {
  channel: VolumeChannel;
  gridX: number;
  gridY: number;
  horizonSteps: number;
  candidateVoxels: number;
  renderedVoxels: number;
  maxVoxels: number;
  meanValue: number;
  maxValue: number;
};

export type VolumeScene = {
  field: Float32Array;
  solids: Float32Array;
  stats: VolumeStats;
  timeScaleMetres: number;
};

export const INSTANCE_STRIDE = 10;

export const volumeChannelCopy: Record<
  VolumeChannel,
  { label: string; short: string; explanation: string }
> = {
  menu: {
    label: "Action menu composite",
    short: "Menu",
    explanation:
      "A fused view of space, corridor quality, option creation, visibility, and pressure. It is a visualization layer, not a learned probability.",
  },
  pressure: {
    label: "Pressure fronts",
    short: "Pressure",
    explanation:
      "Opponent influence propagated through measured or proxy velocity. Rising layers show where pressure is moving next.",
  },
  pressure_shadow: {
    label: "Pressure shadows",
    short: "Shadows",
    explanation:
      "Space screened behind defenders relative to the carrier. This is geometric occlusion pressure, not literal visual occlusion.",
  },
  future_space: {
    label: "Future space",
    short: "Space",
    explanation:
      "Open-space potential after propagating nearby player motion forward from the focal state.",
  },
  passing_corridors: {
    label: "Passing corridors",
    short: "Corridors",
    explanation:
      "Candidate-aligned tubes weighted by the frozen geometric option score. They show where current options travel through space.",
  },
  option_creation: {
    label: "Option creation",
    short: "Creation",
    explanation:
      "Places whose openness improves relative to the focal frame. It visualizes emerging geometry, not a causal effect estimate.",
  },
  visibility: {
    label: "Perceptual access",
    short: "Visible",
    explanation:
      "Provider visibility polygons when present, otherwise a clearly labeled body/head/gaze-direction proxy around the carrier.",
  },
  uncertainty: {
    label: "State uncertainty",
    short: "Uncertainty",
    explanation:
      "Spatial uncertainty accumulated from tracking status, confidence, and player covariance when those fields are available.",
  },
};

const palettes: Record<VolumeChannel, readonly [number, number, number]> = {
  menu: [0.96, 0.82, 0.37],
  pressure: [1, 0.42, 0.42],
  pressure_shadow: [0.69, 0.59, 0.99],
  future_space: [0.39, 0.9, 0.75],
  passing_corridors: [0.45, 0.75, 0.99],
  option_creation: [1, 0.66, 0.3],
  visibility: [0.55, 0.94, 0.98],
  uncertainty: [0.78, 0.68, 1],
};

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const sq = (value: number) => value * value;

function gaussian(distance: number, sigma: number): number {
  return Math.exp(-sq(distance) / (2 * sq(sigma)));
}

function predictedPlayer(player: PlayerState, t: number): [number, number] {
  return [player.x + (player.vx ?? 0) * t, player.y + (player.vy ?? 0) * t];
}

function playerPotential(
  players: PlayerState[],
  x: number,
  y: number,
  t: number,
  sigma: number,
): number {
  let sum = 0;
  for (const player of players) {
    const [px, py] = predictedPlayer(player, t);
    sum += gaussian(Math.hypot(px - x, py - y), sigma);
  }
  return clamp01(1 - Math.exp(-sum));
}

function nearestDistance(
  players: PlayerState[],
  x: number,
  y: number,
  t: number,
): number {
  let nearest = Number.POSITIVE_INFINITY;
  for (const player of players) {
    const [px, py] = predictedPlayer(player, t);
    nearest = Math.min(nearest, Math.hypot(px - x, py - y));
  }
  return Number.isFinite(nearest) ? nearest : 30;
}

function distanceToSegment(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): { distance: number; progress: number } {
  const dx = bx - ax;
  const dy = by - ay;
  const lengthSq = dx * dx + dy * dy;
  if (lengthSq < 1e-9) {
    return { distance: Math.hypot(px - ax, py - ay), progress: 0 };
  }
  const progress = clamp01(((px - ax) * dx + (py - ay) * dy) / lengthSq);
  const qx = ax + progress * dx;
  const qy = ay + progress * dy;
  return { distance: Math.hypot(px - qx, py - qy), progress };
}

function pointInPolygon(
  point: [number, number],
  vertices: [number, number][],
): boolean {
  let inside = false;
  for (
    let index = 0, previous = vertices.length - 1;
    index < vertices.length;
    previous = index++
  ) {
    const current = vertices[index];
    const prior = vertices[previous];
    if (!current || !prior) continue;
    const [x, y] = current;
    const [px, py] = prior;
    const crosses =
      y > point[1] !== py > point[1] &&
      point[0] < ((px - x) * (point[1] - y)) / (py - y + 1e-12) + x;
    if (crosses) inside = !inside;
  }
  return inside;
}

function angularDifference(a: number, b: number): number {
  let delta = a - b;
  while (delta > Math.PI) delta -= 2 * Math.PI;
  while (delta < -Math.PI) delta += 2 * Math.PI;
  return Math.abs(delta);
}

function visibilityAt(frame: FrameState, x: number, y: number): number {
  if (frame.visibility_polygon?.length) {
    return pointInPolygon([x, y], frame.visibility_polygon) ? 1 : 0.04;
  }
  const carrier = frame.players.find(
    (player) => player.player_id === frame.ball_carrier_id,
  );
  if (!carrier) return 0.35;
  const heading =
    carrier.gaze_angle ?? carrier.head_angle ?? carrier.body_angle;
  if (heading === null || heading === undefined) return 0.35;
  const dx = x - carrier.x;
  const dy = y - carrier.y;
  const distance = Math.hypot(dx, dy);
  if (distance < 1) return 1;
  if (distance > 38) return 0.08;
  const angle = Math.atan2(dy, dx);
  const difference = angularDifference(angle, heading);
  const halfCone = (55 * Math.PI) / 180;
  return clamp01(
    1 - Math.max(0, difference - halfCone * 0.6) / (halfCone * 0.5),
  );
}

function corridorAt(
  frame: FrameState,
  options: ActionOption[],
  x: number,
  y: number,
): number {
  const actor = frame.players.find(
    (player) => player.player_id === frame.ball_carrier_id,
  );
  if (!actor) return 0;
  let best = 0;
  for (const option of options) {
    if (option.frame_id !== frame.frame_id || option.kind === "hold") continue;
    const { distance, progress } = distanceToSegment(
      x,
      y,
      actor.x,
      actor.y,
      option.target_x,
      option.target_y,
    );
    const score = clamp01(option.geometric_score);
    const corridor = gaussian(distance, option.kind === "pass" ? 2.8 : 3.8);
    const targetGlow = gaussian(
      Math.hypot(option.target_x - x, option.target_y - y),
      option.kind === "pass" ? 4.5 : 6,
    );
    best = Math.max(
      best,
      score * (0.75 * corridor * (0.35 + 0.65 * progress) + 0.25 * targetGlow),
    );
  }
  return clamp01(best);
}

function pressureShadowAt(
  frame: FrameState,
  defenders: PlayerState[],
  x: number,
  y: number,
  t: number,
): number {
  const carrier = frame.players.find(
    (player) => player.player_id === frame.ball_carrier_id,
  );
  if (!carrier) return 0;
  let best = 0;
  for (const defender of defenders) {
    const [dx, dy] = predictedPlayer(defender, t);
    const vx = dx - carrier.x;
    const vy = dy - carrier.y;
    const length = Math.hypot(vx, vy);
    if (length < 1) continue;
    const ux = vx / length;
    const uy = vy / length;
    const relX = x - dx;
    const relY = y - dy;
    const behind = relX * ux + relY * uy;
    if (behind <= 0) continue;
    const lateral = Math.abs(relX * -uy + relY * ux);
    const width = 1.5 + 0.09 * behind;
    best = Math.max(
      best,
      gaussian(lateral, width) * Math.exp(-behind / 18) * clamp01(length / 18),
    );
  }
  return clamp01(best);
}

function uncertaintyAt(
  frame: FrameState,
  x: number,
  y: number,
  t: number,
): number {
  let value = 0;
  for (const player of frame.players) {
    const [px, py] = predictedPlayer(player, t);
    const covariance = player.position_covariance;
    const variance = covariance
      ? Math.max(covariance[0]?.[0] ?? 0, covariance[1]?.[1] ?? 0)
      : 0;
    const covarianceRadius = Math.sqrt(Math.max(0, variance));
    const confidencePenalty =
      player.confidence === null || player.confidence === undefined
        ? 0
        : 1 - player.confidence;
    const statusPenalty =
      player.tracking_status === "observed"
        ? 0
        : player.tracking_status === "interpolated"
          ? 0.65
          : 0.85;
    const weight = clamp01(
      0.08 * covarianceRadius + confidencePenalty + statusPenalty,
    );
    if (weight <= 0) continue;
    value = Math.max(
      value,
      weight * gaussian(Math.hypot(px - x, py - y), 2.5 + covarianceRadius),
    );
  }
  return clamp01(value);
}

function fieldSignals(
  frame: FrameState,
  options: ActionOption[],
  x: number,
  y: number,
  t: number,
): Record<Exclude<VolumeChannel, "menu">, number> {
  const carrier = frame.players.find(
    (player) => player.player_id === frame.ball_carrier_id,
  );
  const teammates = frame.players.filter(
    (player) =>
      player.team === frame.possession_team &&
      player.player_id !== frame.ball_carrier_id,
  );
  const defenders = frame.players.filter(
    (player) => player.team !== frame.possession_team,
  );
  const pressure = playerPotential(defenders, x, y, t, 5.2);
  const support = playerPotential(teammates, x, y, t, 6.5);
  const nearestDefender = nearestDistance(defenders, x, y, t);
  const futureSpace = clamp01(
    0.72 * clamp01((nearestDefender - 2) / 13) +
      0.18 * support +
      0.1 * (1 - pressure),
  );
  const initialNearest = nearestDistance(defenders, x, y, 0);
  const initialSpace = clamp01((initialNearest - 2) / 13);
  const creation = clamp01(
    Math.max(0, futureSpace - initialSpace) * 2.4 + 0.12 * support,
  );
  const corridor = corridorAt(frame, options, x, y);
  const visibility = visibilityAt(frame, x, y);
  const uncertainty = uncertaintyAt(frame, x, y, t);
  const pressureShadow = pressureShadowAt(frame, defenders, x, y, t);
  const carrierDistance = carrier
    ? Math.hypot(carrier.x - x, carrier.y - y)
    : 0;
  return {
    pressure: clamp01(pressure * (0.9 + 0.1 * clamp01(carrierDistance / 25))),
    pressure_shadow: pressureShadow,
    future_space: futureSpace,
    passing_corridors: corridor,
    option_creation: creation,
    visibility,
    uncertainty,
  };
}

function channelValue(
  channel: VolumeChannel,
  signals: Record<Exclude<VolumeChannel, "menu">, number>,
): number {
  if (channel !== "menu") return signals[channel];
  return clamp01(
    0.34 * signals.future_space +
      0.3 * signals.passing_corridors +
      0.24 * signals.option_creation +
      0.12 * signals.visibility -
      0.22 * signals.pressure -
      0.08 * signals.uncertainty,
  );
}

function qualityGrid(quality: VolumeQuality): [number, number] {
  if (quality === "low") return [20, 13];
  if (quality === "medium") return [28, 18];
  if (quality === "high") return [38, 25];
  if (typeof window === "undefined") return [28, 18];
  if (window.innerWidth < 720) return [20, 13];
  if (window.devicePixelRatio > 1.75) return [28, 18];
  return window.innerWidth >= 1500 ? [38, 25] : [28, 18];
}

function pushInstance(
  target: number[],
  x: number,
  y: number,
  z: number,
  sx: number,
  sy: number,
  sz: number,
  color: readonly [number, number, number],
  alpha: number,
) {
  target.push(x, y, z, sx, sy, sz, color[0], color[1], color[2], alpha);
}

function buildPitchAndActors(frame: FrameState): Float32Array {
  const instances: number[] = [];
  const line: readonly [number, number, number] = [0.73, 0.9, 0.82];
  const halfL = frame.pitch_length / 2;
  const halfW = frame.pitch_width / 2;
  const thickness = 0.16;
  const y = 0.04;
  const horizontal = (x: number, z: number, sx: number, sz: number) =>
    pushInstance(instances, x, y, z, sx, 0.06, sz, line, 0.5);
  horizontal(0, -halfW, frame.pitch_length, thickness);
  horizontal(0, halfW, frame.pitch_length, thickness);
  horizontal(-halfL, 0, thickness, frame.pitch_width);
  horizontal(halfL, 0, thickness, frame.pitch_width);
  horizontal(0, 0, thickness, frame.pitch_width);
  for (let index = 0; index < 32; index += 1) {
    const angle = (index / 32) * Math.PI * 2;
    horizontal(Math.cos(angle) * 9.15, Math.sin(angle) * 9.15, 0.28, 0.28);
  }
  const homeColor: readonly [number, number, number] = [0.39, 0.9, 0.75];
  const awayColor: readonly [number, number, number] = [1, 0.42, 0.42];
  const carrierColor: readonly [number, number, number] = [0.96, 0.82, 0.37];
  for (const player of frame.players) {
    const isCarrier = player.player_id === frame.ball_carrier_id;
    pushInstance(
      instances,
      player.x - halfL,
      isCarrier ? 0.9 : 0.72,
      player.y - halfW,
      isCarrier ? 1.15 : 0.86,
      isCarrier ? 1.8 : 1.35,
      isCarrier ? 1.15 : 0.86,
      isCarrier ? carrierColor : player.team === "home" ? homeColor : awayColor,
      1,
    );
  }
  pushInstance(
    instances,
    frame.ball_x - halfL,
    0.45,
    frame.ball_y - halfW,
    0.46,
    0.46,
    0.46,
    [1, 1, 1],
    1,
  );
  return new Float32Array(instances);
}

export function defaultVolumeConfig(
  channel: VolumeChannel = "menu",
): VolumeConfig {
  return {
    channel,
    quality: "auto",
    threshold: 0.2,
    horizonSeconds: 1.5,
    horizonSteps: 7,
    maxVoxels: 2600,
  };
}

export function buildAffordanceVolume(
  frame: FrameState,
  options: ActionOption[],
  config: VolumeConfig,
): VolumeScene {
  const [gridX, gridY] = qualityGrid(config.quality);
  const cellX = frame.pitch_length / gridX;
  const cellY = frame.pitch_width / gridY;
  const timeScaleMetres = 16;
  const layerThickness = Math.max(
    0.16,
    timeScaleMetres / config.horizonSteps / 8,
  );
  const candidates: Array<{ value: number; data: number[] }> = [];
  let sum = 0;
  let maxValue = 0;

  for (let layer = 0; layer < config.horizonSteps; layer += 1) {
    const fraction =
      config.horizonSteps <= 1 ? 0 : layer / (config.horizonSteps - 1);
    const t = fraction * config.horizonSeconds;
    const worldY = 0.7 + fraction * timeScaleMetres;
    for (let ix = 0; ix < gridX; ix += 1) {
      const x = (ix + 0.5) * cellX;
      for (let iy = 0; iy < gridY; iy += 1) {
        const y = (iy + 0.5) * cellY;
        const signals = fieldSignals(frame, options, x, y, t);
        const value = channelValue(config.channel, signals);
        if (value < config.threshold) continue;
        const alpha = 0.08 + 0.62 * Math.pow(value, 1.35);
        const color = palettes[config.channel];
        const data = [
          x - frame.pitch_length / 2,
          worldY,
          y - frame.pitch_width / 2,
          cellX * 0.82,
          layerThickness,
          cellY * 0.82,
          color[0],
          color[1],
          color[2],
          alpha,
        ];
        candidates.push({ value, data });
        sum += value;
        maxValue = Math.max(maxValue, value);
      }
    }
  }

  candidates.sort((a, b) => b.value - a.value);
  const retained = candidates.slice(0, Math.max(1, config.maxVoxels));
  const field = new Float32Array(retained.length * INSTANCE_STRIDE);
  retained.forEach((voxel, index) => {
    field.set(voxel.data, index * INSTANCE_STRIDE);
  });
  return {
    field,
    solids: buildPitchAndActors(frame),
    timeScaleMetres,
    stats: {
      channel: config.channel,
      gridX,
      gridY,
      horizonSteps: config.horizonSteps,
      candidateVoxels: candidates.length,
      renderedVoxels: retained.length,
      maxVoxels: config.maxVoxels,
      meanValue: candidates.length ? sum / candidates.length : 0,
      maxValue,
    },
  };
}
