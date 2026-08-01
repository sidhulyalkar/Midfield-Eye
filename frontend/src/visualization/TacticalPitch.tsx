import { useId } from "react";
import type {
  ActionOption,
  BodyPayload,
  FrameState,
  GazePayload,
  RelationsPayload,
} from "../data/schemas";
import type { LayerId } from "../state/playbackStore";

type Props = {
  frame: FrameState;
  options: ActionOption[];
  selectedOptionId: string | null;
  layers: Record<LayerId, boolean>;
  gaze?: GazePayload | undefined;
  body?: BodyPayload | undefined;
  relations?: RelationsPayload | undefined;
  onOptionSelect?: ((optionId: string) => void) | undefined;
  title?: string | undefined;
};

function polygon(points: [number, number][]): string {
  return points.map(([x, y]) => `${x},${y}`).join(" ");
}

export function pointInPolygon(
  point: [number, number],
  vertices: [number, number][],
): boolean {
  let inside = false;
  for (
    let index = 0, previous = vertices.length - 1;
    index < vertices.length;
    previous = index++
  ) {
    const [x, y] = vertices[index] ?? [0, 0];
    const [previousX, previousY] = vertices[previous] ?? [0, 0];
    const intersects =
      y > point[1] !== previousY > point[1] &&
      point[0] <
        ((previousX - x) * (point[1] - y)) / (previousY - y || Number.EPSILON) +
          x;
    if (intersects) inside = !inside;
  }
  return inside;
}

function vectorEnd(
  x: number,
  y: number,
  angle: number | null | undefined,
  length: number,
) {
  if (angle == null) return null;
  return { x: x + Math.cos(angle) * length, y: y + Math.sin(angle) * length };
}

export function TacticalPitch({
  frame,
  options,
  selectedOptionId,
  layers,
  gaze,
  body,
  relations,
  onOptionSelect,
  title = "Canonical tactical pitch",
}: Props) {
  const id = useId().replaceAll(":", "");
  const marker = `arrow-${id}`;
  const carrier = frame.players.find(
    (player) => player.player_id === frame.ball_carrier_id,
  );
  const frameOptions = options.filter(
    (option) => option.frame_id === frame.frame_id,
  );
  const scores = frameOptions.map((option) => option.geometric_score);
  const scoreMin = Math.min(...scores, 0);
  const scoreMax = Math.max(...scores, 1);
  const gazePoint = gaze?.timeline.find(
    (point) => point.frame_id === frame.frame_id,
  );
  const bodyPoint = body?.timeline.find(
    (point) => point.frame_id === frame.frame_id,
  );
  const relationPoint = relations?.timeline.find(
    (point) => point.frame_id === frame.frame_id,
  );
  const summary = `${frame.possession_team} possession at ${frame.timestamp_s.toFixed(2)} seconds. ${frameOptions.length} modeled actions. ${selectedOptionId ? "One option selected." : "No option selected."}`;

  return (
    <figure className="tactical-pitch">
      <svg
        viewBox={`0 0 ${frame.pitch_length} ${frame.pitch_width}`}
        role="img"
        aria-labelledby={`${id}-title ${id}-desc`}
        preserveAspectRatio="xMidYMid meet"
      >
        <title id={`${id}-title`}>{title}</title>
        <desc id={`${id}-desc`}>{summary}</desc>
        <defs>
          <clipPath id={`pitch-${id}`}>
            <rect
              width={frame.pitch_length}
              height={frame.pitch_width}
              rx="1.1"
            />
          </clipPath>
          <marker
            id={marker}
            markerWidth="3"
            markerHeight="3"
            refX="2.6"
            refY="1.5"
            orient="auto"
          >
            <path d="M0,0 L3,1.5 L0,3 z" />
          </marker>
          <pattern
            id={`uncertain-${id}`}
            width="2"
            height="2"
            patternUnits="userSpaceOnUse"
          >
            <path d="M0 2 L2 0" className="uncertainty-hatch" />
          </pattern>
        </defs>

        <g className="pitch-surface">
          <rect
            width={frame.pitch_length}
            height={frame.pitch_width}
            rx="1.1"
          />
          <path d={`M ${frame.pitch_length / 2} 0 V ${frame.pitch_width}`} />
          <circle
            cx={frame.pitch_length / 2}
            cy={frame.pitch_width / 2}
            r="9.15"
          />
          <circle
            cx={frame.pitch_length / 2}
            cy={frame.pitch_width / 2}
            r=".35"
            className="pitch-dot"
          />
          <path d="M 0 13.84 H 16.5 V 54.16 H 0 M 105 13.84 H 88.5 V 54.16 H 105" />
          <path d="M 0 24.84 H 5.5 V 43.16 H 0 M 105 24.84 H 99.5 V 43.16 H 105" />
          <circle cx="11" cy="34" r=".35" className="pitch-dot" />
          <circle cx="94" cy="34" r=".35" className="pitch-dot" />
        </g>

        <g clipPath={`url(#pitch-${id})`}>
          {layers.visibility && frame.visibility_polygon ? (
            <polygon
              className="visible-polygon"
              points={polygon(frame.visibility_polygon)}
            />
          ) : null}

          {layers.uncertainty && frame.quality_flags.length ? (
            <rect
              className="uncertainty-region"
              width={frame.pitch_length}
              height={frame.pitch_width}
              fill={`url(#uncertain-${id})`}
            />
          ) : null}

          {layers.gaze && carrier && gazePoint
            ? Object.entries(gazePoint.view_cones)
                .reverse()
                .map(([name, cone]) => (
                  <polygon
                    key={name}
                    className={`gaze-cone gaze-${name} gaze-source-${gazePoint.gaze_source}`}
                    points={polygon(cone.polygon)}
                  />
                ))
            : null}

          {layers.relations && carrier && relationPoint
            ? frame.players
                .filter(
                  (player) =>
                    player.team === carrier.team &&
                    player.player_id !== carrier.player_id,
                )
                .map((player) => (
                  <line
                    key={player.player_id}
                    className="relation-link"
                    x1={carrier.x}
                    y1={carrier.y}
                    x2={player.x}
                    y2={player.y}
                    opacity={
                      0.15 + 0.5 * (relationPoint.option_enablement ?? 0)
                    }
                  />
                ))
            : null}

          {frame.players.map((player) => {
            const isCarrier = player.player_id === frame.ball_carrier_id;
            const covariance = player.position_covariance?.[0]?.[0];
            const radius =
              layers.uncertainty && covariance
                ? Math.max(1.3, Math.sqrt(covariance) * 1.8)
                : 0;
            const velocityLength = Math.min(
              4,
              Math.hypot(player.vx ?? 0, player.vy ?? 0) * 1.3,
            );
            const bodyAngle =
              isCarrier && bodyPoint?.body_angle_rad != null
                ? bodyPoint.body_angle_rad
                : player.body_angle;
            const bodyEnd = vectorEnd(player.x, player.y, bodyAngle, 3.2);
            const headEnd = vectorEnd(
              player.x,
              player.y,
              player.head_angle,
              3.8,
            );
            const outsideObservation =
              layers.visibility &&
              frame.visibility_polygon != null &&
              !pointInPolygon([player.x, player.y], frame.visibility_polygon);
            return (
              <g
                key={player.player_id}
                className={`player player-${player.team}${isCarrier ? " player-carrier" : ""}${outsideObservation ? " outside-observation" : ""}`}
              >
                {radius ? (
                  <circle
                    className="position-uncertainty"
                    cx={player.x}
                    cy={player.y}
                    r={radius}
                  />
                ) : null}
                {layers.velocity && velocityLength > 0 ? (
                  <line
                    className="velocity-vector"
                    x1={player.x}
                    y1={player.y}
                    x2={player.x + (player.vx ?? 0) * 1.3}
                    y2={player.y + (player.vy ?? 0) * 1.3}
                  />
                ) : null}
                {layers.body && bodyEnd ? (
                  <line
                    className="body-axis"
                    x1={player.x}
                    y1={player.y}
                    x2={bodyEnd.x}
                    y2={bodyEnd.y}
                  />
                ) : null}
                {layers.gaze && headEnd ? (
                  <line
                    className="head-axis"
                    x1={player.x}
                    y1={player.y}
                    x2={headEnd.x}
                    y2={headEnd.y}
                  />
                ) : null}
                <circle
                  cx={player.x}
                  cy={player.y}
                  r={isCarrier ? 1.3 : 1}
                  className={
                    player.tracking_status === "observed" ? "" : "non-observed"
                  }
                />
                {isCarrier ? (
                  <circle
                    cx={player.x}
                    cy={player.y}
                    r="1.9"
                    className="carrier-ring"
                  />
                ) : null}
                <text x={player.x} y={player.y - 1.7} textAnchor="middle">
                  {player.player_id === "SUBJECT"
                    ? "Subject"
                    : player.player_id}
                </text>
              </g>
            );
          })}

          {frameOptions.map((option) => {
            if (!carrier) return null;
            const selected = option.option_id === selectedOptionId;
            const normalized =
              (option.geometric_score - scoreMin) /
              Math.max(0.001, scoreMax - scoreMin);
            const outsideObservation =
              layers.visibility &&
              frame.visibility_polygon != null &&
              !pointInPolygon(
                [option.target_x, option.target_y],
                frame.visibility_polygon,
              );
            return (
              <g
                key={option.option_id}
                role="button"
                tabIndex={0}
                aria-label={`${option.kind} to ${option.target_player_id ?? "space"}, model score ${option.geometric_score.toFixed(3)}${outsideObservation ? ", outside current observation area; physical candidate retained" : ""}`}
                aria-pressed={selected}
                onClick={() => onOptionSelect?.(option.option_id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onOptionSelect?.(option.option_id);
                  }
                }}
                className={`option-corridor${selected ? " option-selected" : ""}${outsideObservation ? " outside-observation" : ""}`}
                style={{ opacity: selected ? 1 : 0.35 + normalized * 0.45 }}
              >
                <line
                  x1={carrier.x}
                  y1={carrier.y}
                  x2={option.target_x}
                  y2={option.target_y}
                  markerEnd={`url(#${marker})`}
                />
                <circle
                  cx={option.target_x}
                  cy={option.target_y}
                  r={selected ? 1.4 : 0.85}
                />
              </g>
            );
          })}

          <g className="ball">
            <circle cx={frame.ball_x} cy={frame.ball_y} r=".55" />
          </g>
        </g>
      </svg>
      <figcaption className="sr-only" aria-live="polite">
        {summary}
      </figcaption>
    </figure>
  );
}
