from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ..affordance import AffordanceEngine
from ..counterfactual import positioning_uplift
from ..schema import FrameState
from .pitch import draw_pitch


def plot_positioning_uplift(
    frame: FrameState,
    player_id: str,
    output_path: str | Path | None = None,
    radius_m: float = 8.0,
    grid_size: int = 11,
    engine: AffordanceEngine | None = None,
):
    """Render how alternate player positions change the carrier's top-three option-set value."""
    engine = engine or AffordanceEngine()
    player = frame.player(player_id)
    xs = np.linspace(max(0.0, player.x - radius_m), min(frame.pitch_length, player.x + radius_m), grid_size)
    ys = np.linspace(max(0.0, player.y - radius_m), min(frame.pitch_width, player.y + radius_m), grid_size)
    candidates = [np.array([x, y]) for y in ys for x in xs]
    results = positioning_uplift(frame, player_id, candidates, engine=engine)
    uplift = np.array([row["uplift"] for row in results]).reshape(len(ys), len(xs))

    fig, ax = plt.subplots(figsize=(13, 8))
    draw_pitch(ax, frame.pitch_length, frame.pitch_width)
    contour = ax.contourf(xs, ys, uplift, levels=15, alpha=0.65)
    fig.colorbar(contour, ax=ax, label="Top-three option-set value uplift")

    for state in frame.players:
        marker = "o" if state.team == "home" else "s"
        size = 110 if state.player_id == player_id else 45
        ax.scatter(state.x, state.y, marker=marker, s=size, edgecolors="black", linewidths=0.5)
        ax.text(state.x + 0.6, state.y + 0.6, state.player_id, fontsize=7)
    ax.scatter(frame.ball_x, frame.ball_y, marker="*", s=170, zorder=6)
    ax.set_title(
        f"Counterfactual positioning | move {player_id} earlier | "
        "change in the carrier's future option menu"
    )
    fig.tight_layout()
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=170, bbox_inches="tight")
    return fig, ax, uplift
