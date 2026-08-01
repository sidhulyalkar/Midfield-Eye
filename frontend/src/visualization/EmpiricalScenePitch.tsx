import { useId } from "react";
import type { EmpiricalExperiment } from "../data/schemas";

type Scene = NonNullable<EmpiricalExperiment["scene"]>;

function points(values: [number, number][]) {
  return values.map(([x, y]) => `${x},${y}`).join(" ");
}

export function EmpiricalScenePitch({
  scene,
  title,
}: {
  scene: Scene;
  title: string;
}) {
  const id = useId().replaceAll(":", "");
  const { pitch_length: length, pitch_width: width } = scene.coordinate_system;
  const actor =
    scene.players.find(
      (player) => player.id === scene.selected_action.actor_id,
    ) ?? scene.players.find((player) => player.group === "subject");
  const start = actor?.location_m ?? scene.ball.location_m;
  return (
    <figure className="tactical-pitch empirical-scene-pitch">
      <svg
        viewBox={`0 0 ${length} ${width}`}
        role="img"
        aria-labelledby={`${id}-title ${id}-desc`}
      >
        <title id={`${id}-title`}>{title}</title>
        <desc id={`${id}-desc`}>
          Provider-observed {scene.kind.replaceAll("_", " ")} with{" "}
          {scene.players.length} player observations. The selected action is
          shown retrospectively; action availability has not been expert
          labeled.
        </desc>
        <defs>
          <clipPath id={`scene-${id}`}>
            <rect width={length} height={width} rx="1" />
          </clipPath>
          <marker
            id={`emp-arrow-${id}`}
            markerWidth="3"
            markerHeight="3"
            refX="2.6"
            refY="1.5"
            orient="auto"
          >
            <path d="M0,0 L3,1.5 L0,3 z" />
          </marker>
        </defs>
        <g className="pitch-surface">
          <rect width={length} height={width} rx="1" />
          <path d={`M ${length / 2} 0 V ${width}`} />
          <circle cx={length / 2} cy={width / 2} r="9.15" />
          <path
            d={`M 0 13.84 H 16.5 V ${width - 13.84} H 0 M ${length} 13.84 H ${length - 16.5} V ${width - 13.84} H ${length}`}
          />
        </g>
        <g clipPath={`url(#scene-${id})`}>
          {scene.visible_area_m ? (
            <polygon
              className="visible-polygon provider-visible"
              points={points(scene.visible_area_m)}
            />
          ) : null}
          {scene.players.map((player) => {
            const [x, y] = player.location_m;
            const subject =
              player.group === "subject" ||
              player.id === scene.selected_action.actor_id;
            const teammate = ["teammate", "home"].includes(player.group);
            return (
              <g
                key={player.id}
                className={`player ${teammate || subject ? "player-home" : "player-away"}${subject ? " player-carrier" : ""}`}
              >
                <circle cx={x} cy={y} r={subject ? 1.35 : 1} />
                {subject ? (
                  <circle cx={x} cy={y} r="1.9" className="carrier-ring" />
                ) : null}
                {subject ? (
                  <text x={x} y={y - 1.8} textAnchor="middle">
                    Event actor
                  </text>
                ) : null}
              </g>
            );
          })}
          <line
            className="retrospective-action"
            x1={start[0]}
            y1={start[1]}
            x2={scene.selected_action.target_m[0]}
            y2={scene.selected_action.target_m[1]}
            markerEnd={`url(#emp-arrow-${id})`}
          />
          <g className="ball">
            <circle
              cx={scene.ball.location_m[0]}
              cy={scene.ball.location_m[1]}
              r=".55"
            />
          </g>
        </g>
      </svg>
      <figcaption>
        <span>Provider coordinates · metres · top-left origin</span>
        <span>Selected action: retrospective event label</span>
      </figcaption>
    </figure>
  );
}
