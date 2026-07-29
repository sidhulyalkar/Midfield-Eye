from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, Polygon, Rectangle

from ..geometry import local_pressure
from ..schema import ActionOption, FrameState


def draw_pitch(ax, length: float = 105.0, width: float = 68.0) -> None:
    ax.add_patch(Rectangle((0, 0), length, width, fill=False, linewidth=1.5))
    ax.plot([length / 2, length / 2], [0, width], linewidth=1.0)
    ax.add_patch(Circle((length / 2, width / 2), 9.15, fill=False, linewidth=1.0))
    ax.add_patch(Circle((length / 2, width / 2), 0.35))
    for x, direction in ((0, 1), (length, -1)):
        box_x = x if direction > 0 else x - 16.5
        six_x = x if direction > 0 else x - 5.5
        ax.add_patch(Rectangle((box_x, width / 2 - 20.16), 16.5, 40.32, fill=False))
        ax.add_patch(Rectangle((six_x, width / 2 - 9.16), 5.5, 18.32, fill=False))
        spot_x = x + direction * 11.0
        ax.add_patch(Circle((spot_x, width / 2), 0.25))
        theta1, theta2 = (-53, 53) if direction > 0 else (127, 233)
        ax.add_patch(Arc((spot_x, width / 2), 18.3, 18.3, theta1=theta1, theta2=theta2))
    ax.set_xlim(-2, length + 2)
    ax.set_ylim(-2, width + 2)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def pressure_grid(frame: FrameState, resolution: tuple[int, int] = (80, 52)):
    xs = np.linspace(0, frame.pitch_length, resolution[0])
    ys = np.linspace(0, frame.pitch_width, resolution[1])
    grid = np.zeros((len(ys), len(xs)))
    defenders = frame.opponents()
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            grid[iy, ix] = local_pressure(np.array([x, y]), defenders, horizon_s=0.5)
    return xs, ys, grid


def plot_affordance_frame(
    frame: FrameState,
    options: list[ActionOption],
    output_path: str | Path | None = None,
    top_k: int = 5,
):
    fig, ax = plt.subplots(figsize=(13, 8))
    draw_pitch(ax, frame.pitch_length, frame.pitch_width)
    xs, ys, grid = pressure_grid(frame)
    ax.contourf(xs, ys, grid, levels=12, alpha=0.30)

    for player in frame.players:
        marker = "o" if player.team == "home" else "s"
        ax.scatter(player.x, player.y, marker=marker, s=55, edgecolors="black", linewidths=0.5)
        ax.text(player.x + 0.7, player.y + 0.7, player.player_id, fontsize=7)
        direction = np.array([math.cos(player.body_angle), math.sin(player.body_angle)])
        ax.arrow(player.x, player.y, direction[0] * 1.8, direction[1] * 1.8, width=0.04)

    carrier = frame.carrier
    half_fov = math.radians(55)
    radius = 18
    wedge_points = [carrier.position]
    for angle in np.linspace(carrier.view_angle - half_fov, carrier.view_angle + half_fov, 24):
        wedge_points.append(carrier.position + radius * np.array([math.cos(angle), math.sin(angle)]))
    ax.add_patch(Polygon(wedge_points, closed=True, alpha=0.12))
    ax.scatter(frame.ball_x, frame.ball_y, marker="*", s=180, zorder=6)

    ranked = sorted(options, key=lambda option: option.geometric_score, reverse=True)[:top_k]
    if ranked:
        min_score = min(option.geometric_score for option in ranked)
        max_score = max(option.geometric_score for option in ranked)
    else:
        min_score = max_score = 0.0
    for rank, option in enumerate(ranked, start=1):
        normalized = (option.geometric_score - min_score) / max(max_score - min_score, 1e-8)
        linewidth = 1.2 + 4.0 * normalized
        ax.annotate(
            "",
            xy=(option.target_x, option.target_y),
            xytext=(carrier.x, carrier.y),
            arrowprops={"arrowstyle": "->", "linewidth": linewidth, "alpha": 0.85},
        )
        ax.text(option.target_x, option.target_y - 1.2, f"#{rank} {option.kind}", fontsize=8)

    ax.set_title(
        f"The Midfielder's Eye | {frame.sequence_id} frame {frame.frame_id} | "
        "pressure, viewpoint, and ranked affordances"
    )
    fig.tight_layout()
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=170, bbox_inches="tight")
    return fig, ax
