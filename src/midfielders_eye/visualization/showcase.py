from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Polygon, Rectangle

from ..counterfactual import positioning_uplift
from ..schema import ActionOption, FrameState
from ..showcase.metrics import frame_showcase_metrics

BG = "#07110f"
PANEL = "#0d1b18"
PITCH = "#102b24"
LINE = "#d9f7e9"
HOME = "#f4d35e"
AWAY = "#ff6b6b"
ACCENT = "#63e6be"
ACCENT_2 = "#74c0fc"
MUTED = "#9ab7ac"
WHITE = "#f5fbf8"


def _draw_dark_pitch(ax, length: float, width: float) -> None:
    ax.set_facecolor(PITCH)
    ax.add_patch(Rectangle((0, 0), length, width, fill=False, linewidth=2.0, edgecolor=LINE))
    ax.plot([length / 2, length / 2], [0, width], linewidth=1.1, color=LINE, alpha=0.8)
    ax.add_patch(Circle((length / 2, width / 2), 9.15, fill=False, linewidth=1.1, edgecolor=LINE))
    ax.add_patch(Circle((length / 2, width / 2), 0.35, color=LINE))
    for x, direction in ((0, 1), (length, -1)):
        box_x = x if direction > 0 else x - 16.5
        six_x = x if direction > 0 else x - 5.5
        ax.add_patch(Rectangle((box_x, width / 2 - 20.16), 16.5, 40.32, fill=False, edgecolor=LINE))
        ax.add_patch(Rectangle((six_x, width / 2 - 9.16), 5.5, 18.32, fill=False, edgecolor=LINE))
        spot_x = x + direction * 11.0
        ax.add_patch(Circle((spot_x, width / 2), 0.25, color=LINE))
        theta1, theta2 = (-53, 53) if direction > 0 else (127, 233)
        ax.add_patch(Arc((spot_x, width / 2), 18.3, 18.3, theta1=theta1, theta2=theta2, edgecolor=LINE))
    ax.set_xlim(-2, length + 2)
    ax.set_ylim(-2, width + 2)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _pressure_grid(frame: FrameState, nx: int = 90, ny: int = 58) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs = np.linspace(0, frame.pitch_length, nx)
    ys = np.linspace(0, frame.pitch_width, ny)
    xx, yy = np.meshgrid(xs, ys)
    grid = np.zeros_like(xx)
    for defender in frame.opponents():
        horizon_x = defender.x + 0.55 * defender.vx
        horizon_y = defender.y + 0.55 * defender.vy
        sigma = 3.2 + min(defender.speed, 5.0) * 0.35 + defender.uncertainty_radius_m * 0.25
        grid += np.exp(-((xx - horizon_x) ** 2 + (yy - horizon_y) ** 2) / (2 * sigma**2))
    return xs, ys, grid


def _style_axes(options: list[ActionOption]) -> dict[str, float]:
    passes = [option for option in options if option.kind == "pass"]
    source = passes or options
    if not source:
        return {key: 0.0 for key in ["Vision", "Progression", "Safety", "Creation", "Space", "Disguise"]}
    return {
        "Vision": float(np.mean([row.features.get("visibility", 0.0) for row in source])),
        "Progression": float(np.clip(0.5 + 3.0 * max([row.features.get("xt_gain", 0.0) for row in source], default=0.0), 0.0, 1.0)),
        "Safety": float(np.mean([row.features.get("state_confidence", 0.5) for row in source])),
        "Creation": float(np.clip(0.5 + max([row.features.get("option_creation", 0.0) for row in source], default=0.0), 0.0, 1.0)),
        "Space": float(np.mean([row.features.get("future_space", 0.0) for row in source])),
        "Disguise": float(np.mean([1.0 - abs(row.features.get("body_orientation", 0.5) - row.features.get("visibility", 0.5)) for row in source])),
    }


def render_tactical_lens(
    frame: FrameState,
    options: list[ActionOption],
    output_path: str | Path,
    *,
    title: str,
    subtitle: str,
    player_name: str,
    top_k: int = 5,
    dpi: int = 200,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(19.2, 10.8), dpi=dpi, facecolor=BG)
    grid = fig.add_gridspec(12, 20, left=0.035, right=0.975, top=0.90, bottom=0.06, wspace=0.45, hspace=0.45)
    pitch_ax = fig.add_subplot(grid[:, :15])
    metrics_ax = fig.add_subplot(grid[:6, 15:])
    options_ax = fig.add_subplot(grid[6:, 15:])
    _draw_dark_pitch(pitch_ax, frame.pitch_length, frame.pitch_width)

    xs, ys, pressure = _pressure_grid(frame)
    pitch_ax.contourf(xs, ys, pressure, levels=16, cmap="magma", alpha=0.38)

    carrier = frame.carrier
    half_fov = math.radians(55)
    radius = 22
    wedge = [carrier.position]
    for angle in np.linspace(carrier.view_angle - half_fov, carrier.view_angle + half_fov, 36):
        wedge.append(carrier.position + radius * np.array([math.cos(angle), math.sin(angle)]))
    pitch_ax.add_patch(Polygon(wedge, closed=True, facecolor=ACCENT_2, edgecolor=ACCENT_2, alpha=0.12))

    for player in frame.players:
        color = HOME if player.team == frame.possession_team else AWAY
        size = 310 if player.player_id == frame.ball_carrier_id else 170
        edge = WHITE if player.player_id == frame.ball_carrier_id else BG
        pitch_ax.scatter(player.x, player.y, s=size, c=color, edgecolors=edge, linewidths=1.8, zorder=5)
        label = player.metadata.get("showcase_player_name", player.player_id) if player.player_id == "SUBJECT" else player.player_id
        pitch_ax.text(player.x, player.y - 2.1, str(label), color=WHITE, fontsize=8, ha="center", va="top", zorder=7)
        speed_scale = min(4.0, 1.2 + player.speed)
        pitch_ax.arrow(
            player.x,
            player.y,
            math.cos(player.body_angle) * speed_scale,
            math.sin(player.body_angle) * speed_scale,
            color=color,
            width=0.06,
            head_width=0.75,
            length_includes_head=True,
            alpha=0.9,
            zorder=6,
        )
    pitch_ax.scatter(frame.ball_x, frame.ball_y, marker="*", s=330, c=WHITE, edgecolors=BG, linewidths=1.5, zorder=8)

    ranked = sorted(options, key=lambda option: option.geometric_score, reverse=True)[:top_k]
    if ranked:
        score_min = min(option.geometric_score for option in ranked)
        score_max = max(option.geometric_score for option in ranked)
    else:
        score_min = score_max = 0.0
    for rank, option in enumerate(ranked, start=1):
        value = (option.geometric_score - score_min) / max(score_max - score_min, 1e-9)
        color = ACCENT if rank == 1 else ACCENT_2
        pitch_ax.annotate(
            "",
            xy=(option.target_x, option.target_y),
            xytext=(carrier.x, carrier.y),
            arrowprops={
                "arrowstyle": "-|>",
                "linewidth": 2.2 + 5.0 * value,
                "color": color,
                "alpha": 0.95 if rank == 1 else 0.68,
                "connectionstyle": "arc3,rad=0.02",
            },
            zorder=9,
        )
        pitch_ax.text(
            option.target_x,
            option.target_y + 2.0,
            f"#{rank} {option.kind.upper()}",
            color=WHITE,
            fontsize=9,
            ha="center",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": BG, "edgecolor": color, "alpha": 0.9},
            zorder=10,
        )

    fig.text(0.04, 0.955, title, fontsize=28, color=WHITE, weight="bold", ha="left")
    fig.text(0.04, 0.92, subtitle, fontsize=13, color=MUTED, ha="left")
    fig.text(0.97, 0.955, "MIDFIELDER'S EYE", fontsize=13, color=ACCENT, weight="bold", ha="right")

    metrics_ax.set_facecolor(PANEL)
    metrics_ax.axis("off")
    card = FancyBboxPatch((0.0, 0.0), 1.0, 1.0, boxstyle="round,pad=0.025,rounding_size=0.035", transform=metrics_ax.transAxes, facecolor=PANEL, edgecolor="#21483d", linewidth=1.5)
    metrics_ax.add_patch(card)
    metrics_ax.text(0.06, 0.90, player_name, color=WHITE, fontsize=18, weight="bold", transform=metrics_ax.transAxes)
    metrics_ax.text(0.06, 0.81, "LIVE ACTION MENU", color=ACCENT, fontsize=10, weight="bold", transform=metrics_ax.transAxes)
    metric_values = frame_showcase_metrics(frame, options)
    display = [
        ("Visible options", f"{int(metric_values['visible_options'])}"),
        ("Menu breadth", f"{int(metric_values['menu_breadth'])}"),
        ("Best value", f"{float(metric_values['best_option_value']):.3f}"),
        ("Interception margin", f"{float(metric_values['best_interception_margin_s']):+.2f}s"),
        ("State confidence", f"{float(metric_values['state_confidence']):.0%}"),
    ]
    y = 0.69
    for label, value in display:
        metrics_ax.text(0.07, y, label, color=MUTED, fontsize=10, transform=metrics_ax.transAxes)
        metrics_ax.text(0.93, y, value, color=WHITE, fontsize=16, weight="bold", ha="right", transform=metrics_ax.transAxes)
        metrics_ax.plot([0.07, 0.93], [y - 0.055, y - 0.055], color="#1f3b34", linewidth=1.0, transform=metrics_ax.transAxes)
        y -= 0.13

    options_ax.set_facecolor(PANEL)
    options_ax.axis("off")
    card2 = FancyBboxPatch((0.0, 0.0), 1.0, 1.0, boxstyle="round,pad=0.025,rounding_size=0.035", transform=options_ax.transAxes, facecolor=PANEL, edgecolor="#21483d", linewidth=1.5)
    options_ax.add_patch(card2)
    options_ax.text(0.06, 0.91, "RANKED OPTIONS", color=WHITE, fontsize=14, weight="bold", transform=options_ax.transAxes)
    y = 0.78
    for rank, option in enumerate(ranked, start=1):
        receiver = option.target_player_id or "space"
        options_ax.text(0.07, y, f"{rank:02d}", color=ACCENT if rank == 1 else ACCENT_2, fontsize=16, weight="bold", transform=options_ax.transAxes)
        options_ax.text(0.18, y + 0.018, f"{option.kind.title()} → {receiver}", color=WHITE, fontsize=11, weight="bold", transform=options_ax.transAxes)
        options_ax.text(
            0.18,
            y - 0.045,
            f"clearance {option.features.get('uncertainty_adjusted_clearance_m', 0.0):+.1f}m  •  xT Δ {option.features.get('xt_gain', 0.0):+.3f}",
            color=MUTED,
            fontsize=8.5,
            transform=options_ax.transAxes,
        )
        options_ax.text(0.93, y, f"{option.geometric_score:.3f}", color=WHITE, fontsize=13, ha="right", weight="bold", transform=options_ax.transAxes)
        y -= 0.15

    fig.savefig(output, facecolor=fig.get_facecolor(), pil_kwargs={"compress_level": 2})
    plt.close(fig)
    return output


def render_option_timeline(
    timeline: list[dict[str, Any]],
    output_path: str | Path,
    *,
    title: str,
    dpi: int = 200,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=dpi, facecolor=BG)
    ax.set_facecolor(PANEL)
    t = np.array([row["timestamp_s"] for row in timeline], dtype=float)
    series = [
        ("Best option value", "best_option_value", ACCENT),
        ("Progressive access", "max_progressive_gain", ACCENT_2),
        ("Pressure resilience", "pressure_resilience", HOME),
        ("State confidence", "state_confidence", WHITE),
    ]

    def within_scenario(values: np.ndarray) -> np.ndarray:
        low = float(np.min(values))
        high = float(np.max(values))
        if high - low < 1e-8:
            return np.full_like(values, 0.5)
        return 0.12 + 0.76 * (values - low) / (high - low)

    for label, key, color in series:
        raw = np.array([row[key] for row in timeline], dtype=float)
        values = within_scenario(raw)
        ax.plot(t, values, linewidth=4.0, label=label, color=color)
        ax.fill_between(t, values, alpha=0.08, color=color)
    breadth_raw = np.array([row["menu_breadth"] for row in timeline], dtype=float)
    breadth = within_scenario(breadth_raw)
    ax.plot(t, breadth, linestyle="--", linewidth=3.0, color=AWAY, label="Menu breadth")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Seconds", color=MUTED, fontsize=14)
    ax.set_ylabel("Within-scenario normalized signal", color=MUTED, fontsize=14)
    ax.tick_params(colors=MUTED, labelsize=11)
    for spine in ax.spines.values():
        spine.set_color("#315c4f")
    ax.grid(alpha=0.16, color=LINE)
    ax.legend(loc="upper left", frameon=False, labelcolor=WHITE, fontsize=13, ncol=3)
    fig.text(0.055, 0.95, title, color=WHITE, fontsize=28, weight="bold")
    fig.text(0.055, 0.91, "Within-scenario view of how the action menu appears, stabilizes, and disappears", color=MUTED, fontsize=13)
    fig.savefig(output, facecolor=fig.get_facecolor(), pil_kwargs={"compress_level": 2})
    plt.close(fig)
    return output


def render_style_profile(
    options: list[ActionOption],
    output_path: str | Path,
    *,
    player_name: str,
    archetype: str,
    dpi: int = 200,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    axes = _style_axes(options)
    labels = list(axes)
    values = np.array([axes[label] for label in labels], dtype=float)
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    values = np.concatenate([values, values[:1]])
    angles = np.concatenate([angles, angles[:1]])
    fig = plt.figure(figsize=(19.2, 10.8), dpi=dpi, facecolor=BG)
    radar = fig.add_axes([0.08, 0.10, 0.50, 0.78], polar=True, facecolor=PANEL)
    radar.plot(angles, values, color=ACCENT, linewidth=4)
    radar.fill(angles, values, color=ACCENT, alpha=0.2)
    radar.set_ylim(0, 1)
    radar.set_xticks(angles[:-1])
    radar.set_xticklabels(labels, color=WHITE, fontsize=13)
    radar.set_yticklabels([])
    radar.grid(color=LINE, alpha=0.18)
    radar.spines["polar"].set_color("#315c4f")
    info = fig.add_axes([0.63, 0.16, 0.31, 0.67], facecolor=PANEL)
    info.axis("off")
    info.text(0.06, 0.88, player_name, color=WHITE, fontsize=28, weight="bold", transform=info.transAxes)
    info.text(0.06, 0.80, archetype.upper(), color=ACCENT, fontsize=12, weight="bold", transform=info.transAxes)
    info.text(0.06, 0.69, "ILLUSTRATIVE MODEL PROFILE", color=MUTED, fontsize=10, transform=info.transAxes)
    y = 0.58
    for label in labels:
        info.text(0.06, y, label, color=MUTED, fontsize=11, transform=info.transAxes)
        info.text(0.92, y, f"{axes[label]:.0%}", color=WHITE, fontsize=18, ha="right", weight="bold", transform=info.transAxes)
        y -= 0.09
    info.text(
        0.06,
        0.04,
        "These values describe the included synthetic scenario, not the real player's career performance.",
        color=MUTED,
        fontsize=9,
        wrap=True,
        transform=info.transAxes,
    )
    fig.savefig(output, facecolor=fig.get_facecolor(), pil_kwargs={"compress_level": 2})
    plt.close(fig)
    return output


def render_counterfactual_uplift(
    frame: FrameState,
    options: list[ActionOption],
    output_path: str | Path,
    *,
    title: str,
    player_name: str,
    dpi: int = 200,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    target_options = [option for option in options if option.kind == "pass" and option.target_player_id]
    target = max(target_options, key=lambda option: option.geometric_score).target_player_id if target_options else frame.teammates()[0].player_id
    player = frame.player(target)
    xs = np.linspace(max(0.0, player.x - 9.0), min(frame.pitch_length, player.x + 9.0), 11)
    ys = np.linspace(max(0.0, player.y - 9.0), min(frame.pitch_width, player.y + 9.0), 11)
    candidates = [np.array([x, y]) for y in ys for x in xs]
    rows = positioning_uplift(frame, target, candidates)
    uplift = np.array([row["uplift"] for row in rows]).reshape(len(ys), len(xs))

    fig = plt.figure(figsize=(19.2, 10.8), dpi=dpi, facecolor=BG)
    ax = fig.add_axes([0.04, 0.09, 0.72, 0.80], facecolor=PITCH)
    _draw_dark_pitch(ax, frame.pitch_length, frame.pitch_width)
    contour = ax.contourf(xs, ys, uplift, levels=18, cmap="viridis", alpha=0.78)
    for state in frame.players:
        color = HOME if state.team == frame.possession_team else AWAY
        size = 280 if state.player_id == target else 145
        ax.scatter(state.x, state.y, s=size, c=color, edgecolors=BG, linewidths=1.5, zorder=5)
        ax.text(state.x, state.y - 2.0, state.player_id, color=WHITE, fontsize=8, ha="center", zorder=6)
    ax.scatter(frame.ball_x, frame.ball_y, marker="*", s=300, c=WHITE, edgecolors=BG, linewidths=1.2, zorder=7)
    side = fig.add_axes([0.79, 0.16, 0.18, 0.64], facecolor=PANEL)
    side.axis("off")
    side.text(0.05, 0.90, "MOVE EARLIER", color=ACCENT, fontsize=11, weight="bold", transform=side.transAxes)
    side.text(0.05, 0.78, target, color=WHITE, fontsize=25, weight="bold", transform=side.transAxes)
    side.text(0.05, 0.66, "Counterfactual question", color=MUTED, fontsize=10, transform=side.transAxes)
    side.text(0.05, 0.57, "Where should the supporting player move to improve the carrier's top-three future options?", color=WHITE, fontsize=12, wrap=True, transform=side.transAxes)
    side.text(0.05, 0.30, "Hotter regions increase\nfuture menu value.", color=MUTED, fontsize=11, transform=side.transAxes)
    fig.text(0.045, 0.95, title, color=WHITE, fontsize=28, weight="bold")
    fig.text(0.965, 0.95, player_name, color=ACCENT, fontsize=14, weight="bold", ha="right")
    cbar = fig.colorbar(contour, ax=ax, fraction=0.025, pad=0.018)
    cbar.ax.tick_params(colors=MUTED)
    cbar.set_label("Top-three option-menu uplift", color=MUTED)
    fig.savefig(output, facecolor=fig.get_facecolor(), pil_kwargs={"compress_level": 2})
    plt.close(fig)
    return output


def render_gaze_lab(
    frame: FrameState,
    options: list[ActionOption],
    gaze_payload: dict[str, Any],
    output_path: str | Path,
    *,
    title: str,
    player_name: str,
    dpi: int = 200,
) -> Path:
    """Render nested view fields, head/body separation, and scan timing."""
    from ..cognition.gaze import frame_gaze_metrics

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = frame_gaze_metrics(frame, options)
    fig = plt.figure(figsize=(19.2, 10.8), dpi=dpi, facecolor=BG)
    pitch_ax = fig.add_axes([0.035, 0.10, 0.70, 0.80], facecolor=PITCH)
    _draw_dark_pitch(pitch_ax, frame.pitch_length, frame.pitch_width)
    carrier = frame.carrier
    cone_colors = {"peripheral": "#b197fc", "actionable": ACCENT_2, "foveal": ACCENT}
    alphas = {"peripheral": 0.08, "actionable": 0.12, "foveal": 0.18}
    for band in ("peripheral", "actionable", "foveal"):
        points = np.asarray(metrics["view_cones"][band]["polygon"], dtype=float)
        pitch_ax.add_patch(
            Polygon(points, closed=True, facecolor=cone_colors[band], edgecolor=cone_colors[band], alpha=alphas[band], linewidth=1.3)
        )
    for player in frame.players:
        color = HOME if player.team == frame.possession_team else AWAY
        pitch_ax.scatter(player.x, player.y, s=300 if player.player_id == frame.ball_carrier_id else 150, c=color, edgecolors=WHITE if player.player_id == frame.ball_carrier_id else BG, linewidths=1.4, zorder=5)
    ranked = sorted([option for option in options if option.kind == "pass"], key=lambda row: row.geometric_score, reverse=True)
    for rank, option in enumerate(ranked[:7], start=1):
        target = np.array([option.target_x, option.target_y])
        angle = math.atan2(target[1] - carrier.y, target[0] - carrier.x)
        error = abs((angle - carrier.view_angle + math.pi) % (2 * math.pi) - math.pi)
        visible = error <= math.radians(55)
        color = ACCENT if visible else "#b197fc"
        pitch_ax.plot([carrier.x, target[0]], [carrier.y, target[1]], color=color, linewidth=3.2 if rank == 1 else 1.5, linestyle="-" if visible else "--", alpha=0.9 if visible else 0.55, zorder=7)
        pitch_ax.text(target[0], target[1] + 1.5, f"#{rank}", color=color, fontsize=10, weight="bold", ha="center", zorder=8)
    for angle, color, label in [
        (carrier.body_angle, HOME, "BODY"),
        (carrier.head_angle if carrier.head_angle is not None else carrier.body_angle, ACCENT_2, "HEAD"),
        (carrier.view_angle, ACCENT, "GAZE"),
    ]:
        pitch_ax.arrow(carrier.x, carrier.y, 7.0 * math.cos(angle), 7.0 * math.sin(angle), color=color, width=0.07, head_width=0.9, length_includes_head=True, zorder=9)
        pitch_ax.text(carrier.x + 8.3 * math.cos(angle), carrier.y + 8.3 * math.sin(angle), label, color=color, fontsize=8, weight="bold", ha="center")

    panel = fig.add_axes([0.765, 0.10, 0.205, 0.80], facecolor=PANEL)
    panel.axis("off")
    panel.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02,rounding_size=0.03", facecolor=PANEL, edgecolor="#315c4f", transform=panel.transAxes))
    panel.text(0.07, 0.92, "GAZE LAB", color=ACCENT, fontsize=11, weight="bold", transform=panel.transAxes)
    panel.text(0.07, 0.85, player_name, color=WHITE, fontsize=20, weight="bold", transform=panel.transAxes)
    values = [
        ("Source", str(metrics["gaze_source"]).replace("_", " ")),
        ("Confidence", f"{metrics['gaze_confidence']:.0%}"),
        ("Visible options", str(metrics["actionable_visible_option_count"])),
        ("Blind-side options", str(metrics["blind_side_option_count"])),
        ("Head/body split", f"{metrics['head_body_dissociation_deg']:.1f}°"),
        ("Top-option error", "n/a" if metrics["top_option_angle_error_deg"] is None else f"{metrics['top_option_angle_error_deg']:.1f}°"),
        ("Scan rate", f"{gaze_payload['summary']['scan_rate_hz']:.2f}/s"),
        ("Visible-option recall", f"{gaze_payload['summary']['mean_visible_option_recall']:.0%}"),
    ]
    y = 0.73
    for label, value in values:
        panel.text(0.07, y, label, color=MUTED, fontsize=9, transform=panel.transAxes)
        panel.text(0.93, y, value, color=WHITE, fontsize=13, weight="bold", ha="right", transform=panel.transAxes)
        y -= 0.08
    panel.text(0.07, 0.06, "Nested cones are geometric communication bands. Only an observed gaze source supports literal eye-direction claims.", color=MUTED, fontsize=8.5, wrap=True, transform=panel.transAxes)
    fig.text(0.04, 0.955, title, color=WHITE, fontsize=28, weight="bold")
    fig.text(0.04, 0.92, "What enters view, when it enters view, and which options remain behind the player", color=MUTED, fontsize=13)
    fig.savefig(output, facecolor=fig.get_facecolor(), pil_kwargs={"compress_level": 2})
    plt.close(fig)
    return output


def render_body_mechanics_lab(
    frame: FrameState,
    options: list[ActionOption],
    body_payload: dict[str, Any],
    output_path: str | Path,
    *,
    title: str,
    player_name: str,
    dpi: int = 200,
) -> Path:
    from ..cognition.body import frame_body_mechanics

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = frame_body_mechanics(frame, options)
    fig = plt.figure(figsize=(19.2, 10.8), dpi=dpi, facecolor=BG)
    pitch_ax = fig.add_axes([0.035, 0.10, 0.63, 0.80], facecolor=PITCH)
    _draw_dark_pitch(pitch_ax, frame.pitch_length, frame.pitch_width)
    carrier = frame.carrier
    for player in frame.players:
        color = HOME if player.team == frame.possession_team else AWAY
        pitch_ax.scatter(player.x, player.y, s=330 if player.player_id == frame.ball_carrier_id else 135, c=color, edgecolors=WHITE if player.player_id == frame.ball_carrier_id else BG, linewidths=1.4, zorder=5)
    vectors = [
        (carrier.body_angle, 8.0, HOME, "BODY ACCESS"),
        (metrics["movement_heading_rad"], 6.3, ACCENT_2, "MOTION"),
    ]
    for angle, length, color, label in vectors:
        pitch_ax.arrow(carrier.x, carrier.y, length * math.cos(angle), length * math.sin(angle), color=color, width=0.08, head_width=1.0, length_includes_head=True, zorder=7)
        pitch_ax.text(carrier.x + (length + 1.7) * math.cos(angle), carrier.y + (length + 1.7) * math.sin(angle), label, color=color, fontsize=8, weight="bold", ha="center")
    transfer = np.asarray(metrics["weight_transfer_vector"], dtype=float)
    norm = max(float(np.linalg.norm(transfer)), 1e-6)
    transfer = transfer / norm * 5.5
    pitch_ax.arrow(carrier.x, carrier.y, transfer[0], transfer[1], color=ACCENT, width=0.09, head_width=1.05, length_includes_head=True, zorder=8)
    pitch_ax.text(carrier.x + transfer[0] * 1.3, carrier.y + transfer[1] * 1.3, "WEIGHT-SHIFT PROXY", color=ACCENT, fontsize=8, weight="bold", ha="center")
    ranked = sorted(options, key=lambda row: row.geometric_score, reverse=True)[:5]
    for option in ranked:
        pitch_ax.plot([carrier.x, option.target_x], [carrier.y, option.target_y], color=ACCENT_2, alpha=0.35, linewidth=1.4, linestyle=":" if option.kind != "pass" else "-")

    panel = fig.add_axes([0.695, 0.10, 0.275, 0.80], facecolor=PANEL)
    panel.axis("off")
    panel.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02,rounding_size=0.03", facecolor=PANEL, edgecolor="#315c4f", transform=panel.transAxes))
    panel.text(0.06, 0.92, "BODY MECHANICS", color=ACCENT, fontsize=11, weight="bold", transform=panel.transAxes)
    panel.text(0.06, 0.85, player_name, color=WHITE, fontsize=21, weight="bold", transform=panel.transAxes)
    cards = [
        ("Open-body access", metrics["open_body_score"]),
        ("Multi-action readiness", metrics["multi_action_readiness"]),
        ("Balance reserve", metrics["balance_reserve_proxy"]),
        ("Turning load", metrics["turning_load_proxy"]),
        ("Lateral load", metrics["lateral_load_proxy"]),
        ("Braking load", metrics["braking_load_proxy"]),
    ]
    y = 0.72
    for label, value in cards:
        panel.text(0.06, y + 0.035, label, color=MUTED, fontsize=9, transform=panel.transAxes)
        panel.add_patch(Rectangle((0.06, y - 0.01), 0.72, 0.022, color="#19352e", transform=panel.transAxes))
        panel.add_patch(Rectangle((0.06, y - 0.01), 0.72 * float(value), 0.022, color=ACCENT if "load" not in label.lower() else ACCENT_2, transform=panel.transAxes))
        panel.text(0.93, y, f"{float(value):.0%}", color=WHITE, fontsize=13, weight="bold", ha="right", transform=panel.transAxes)
        y -= 0.095
    panel.text(0.06, 0.08, f"Body/movement separation: {metrics['body_movement_separation_deg']:.1f}°", color=WHITE, fontsize=10, transform=panel.transAxes)
    panel.text(0.06, 0.035, "No force or center-of-pressure claim is made without pose or biomechanical sensors.", color=MUTED, fontsize=8.5, wrap=True, transform=panel.transAxes)
    fig.text(0.04, 0.955, title, color=WHITE, fontsize=28, weight="bold")
    fig.text(0.04, 0.92, "Can the receiving posture preserve pass, carry, and shot access while the body is still moving?", color=MUTED, fontsize=13)
    fig.savefig(output, facecolor=fig.get_facecolor(), pil_kwargs={"compress_level": 2})
    plt.close(fig)
    return output


def render_relational_control_lab(
    frame: FrameState,
    options: list[ActionOption],
    relational_payload: dict[str, Any],
    output_path: str | Path,
    *,
    title: str,
    player_name: str,
    dpi: int = 200,
) -> Path:
    from ..cognition.adaptation import frame_relational_metrics

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = frame_relational_metrics(frame, options)
    fig = plt.figure(figsize=(19.2, 10.8), dpi=dpi, facecolor=BG)
    pitch_ax = fig.add_axes([0.035, 0.10, 0.68, 0.80], facecolor=PITCH)
    _draw_dark_pitch(pitch_ax, frame.pitch_length, frame.pitch_width)
    carrier = frame.carrier
    for teammate in frame.teammates():
        distance = float(np.linalg.norm(teammate.position - carrier.position))
        strength = max(0.15, 1.0 - distance / 55.0)
        pitch_ax.plot([carrier.x, teammate.x], [carrier.y, teammate.y], color=ACCENT, linewidth=1.0 + 5.0 * strength, alpha=0.18 + 0.5 * strength, zorder=3)
    for opponent in frame.opponents():
        distance = float(np.linalg.norm(opponent.position - carrier.position))
        if distance <= 14.0:
            pitch_ax.plot([opponent.x, carrier.x], [opponent.y, carrier.y], color=AWAY, linewidth=max(1.0, 5.0 - distance / 3.0), alpha=0.5, linestyle="--", zorder=3)
    for player in frame.players:
        color = HOME if player.team == frame.possession_team else AWAY
        pitch_ax.scatter(player.x, player.y, s=330 if player.player_id == frame.ball_carrier_id else 160, c=color, edgecolors=WHITE if player.player_id == frame.ball_carrier_id else BG, linewidths=1.4, zorder=5)
        if player.team == frame.possession_team:
            pitch_ax.arrow(player.x, player.y, player.vx * 0.8, player.vy * 0.8, color=ACCENT_2, width=0.04, head_width=0.55, alpha=0.75, zorder=6)
    ranked = sorted([option for option in options if option.kind == "pass"], key=lambda row: row.geometric_score, reverse=True)[:5]
    for rank, option in enumerate(ranked, start=1):
        pitch_ax.annotate("", xy=(option.target_x, option.target_y), xytext=(carrier.x, carrier.y), arrowprops={"arrowstyle": "-|>", "linewidth": 4.0 if rank == 1 else 2.0, "color": ACCENT if rank == 1 else ACCENT_2, "alpha": 0.9})

    panel = fig.add_axes([0.745, 0.10, 0.225, 0.80], facecolor=PANEL)
    panel.axis("off")
    panel.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02,rounding_size=0.03", facecolor=PANEL, edgecolor="#315c4f", transform=panel.transAxes))
    panel.text(0.07, 0.92, "RELATIONAL CONTROL", color=ACCENT, fontsize=11, weight="bold", transform=panel.transAxes)
    panel.text(0.07, 0.85, player_name, color=WHITE, fontsize=20, weight="bold", transform=panel.transAxes)
    values = [
        ("Directive influence", metrics["directive_influence"]),
        ("Support reactivity", metrics["support_reactivity"]),
        ("Pressure attraction", metrics["pressure_attraction"]),
        ("Network brokerage", metrics["network_brokerage"]),
        ("Option enablement", metrics["option_enablement"]),
        ("Role adaptability", metrics["role_adaptability"]),
    ]
    y = 0.72
    for label, value in values:
        panel.text(0.07, y + 0.025, label, color=MUTED, fontsize=9, transform=panel.transAxes)
        panel.text(0.93, y + 0.025, f"{float(value):.0%}", color=WHITE, fontsize=13, weight="bold", ha="right", transform=panel.transAxes)
        panel.add_patch(Rectangle((0.07, y - 0.012), 0.86, 0.018, color="#19352e", transform=panel.transAxes))
        panel.add_patch(Rectangle((0.07, y - 0.012), 0.86 * float(value), 0.018, color=ACCENT, transform=panel.transAxes))
        y -= 0.095
    summary = relational_payload["summary"]
    panel.text(0.07, 0.12, f"Co-adaptation lag: {summary['coadaptation_lag_s']:+.2f}s", color=WHITE, fontsize=10, transform=panel.transAxes)
    panel.text(0.07, 0.06, "Geometry can reveal response timing, but not leadership intent without corroborating evidence.", color=MUTED, fontsize=8.5, wrap=True, transform=panel.transAxes)
    fig.text(0.04, 0.955, title, color=WHITE, fontsize=28, weight="bold")
    fig.text(0.04, 0.92, "How the subject changes teammate options, opponent movement, and the rhythm of the collective", color=MUTED, fontsize=13)
    fig.savefig(output, facecolor=fig.get_facecolor(), pil_kwargs={"compress_level": 2})
    plt.close(fig)
    return output


def render_player_profile_svg(player: Any, output_path: str | Path) -> Path:
    """Create a scalable, frontend-ready player study card without unlicensed photography."""
    import html

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    axes = list(player.showcase_emphasis)
    values = [float(player.showcase_emphasis[key]) for key in axes]
    cx, cy, radius = 1090.0, 390.0, 235.0
    points = []
    grid_points = []
    for index, value in enumerate(values):
        angle = -math.pi / 2 + 2 * math.pi * index / len(values)
        points.append((cx + radius * value * math.cos(angle), cy + radius * value * math.sin(angle)))
        grid_points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    grid = " ".join(f"{x:.1f},{y:.1f}" for x, y in grid_points)
    labels = []
    for index, axis in enumerate(axes):
        angle = -math.pi / 2 + 2 * math.pi * index / len(axes)
        x = cx + (radius + 42) * math.cos(angle)
        y = cy + (radius + 42) * math.sin(angle)
        labels.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="#9ab7ac" font-size="15" text-anchor="middle">{html.escape(axis.replace("_", " "))}</text>')
    tags = " · ".join(player.talent_lenses)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(player.name)} Midfielder's Eye research profile</title>
<desc id="desc">Illustrative archetype emphasis card, not a measured player rating.</desc>
<rect width="1600" height="900" fill="#07110f"/>
<rect x="45" y="45" width="1510" height="810" rx="34" fill="#0d1b18" stroke="#315c4f" stroke-width="2"/>
<text x="90" y="105" fill="#63e6be" font-size="22" font-family="Inter,Arial" font-weight="700">MIDFIELDER'S EYE · 100 PLAYER ATLAS</text>
<text x="90" y="190" fill="#f5fbf8" font-size="58" font-family="Inter,Arial" font-weight="800">{html.escape(player.name)}</text>
<text x="90" y="242" fill="#74c0fc" font-size="24" font-family="Inter,Arial">{html.escape(player.display_role)}</text>
<text x="90" y="302" fill="#f4d35e" font-size="19" font-family="IBM Plex Mono,monospace">{html.escape(player.primary_archetype.replace('_',' ').upper())}</text>
<foreignObject x="90" y="345" width="690" height="180"><div xmlns="http://www.w3.org/1999/xhtml" style="color:#f5fbf8;font:28px/1.35 Inter,Arial;">{html.escape(player.signature)}</div></foreignObject>
<foreignObject x="90" y="575" width="720" height="90"><div xmlns="http://www.w3.org/1999/xhtml" style="color:#9ab7ac;font:18px/1.4 Inter,Arial;">{html.escape(tags)}</div></foreignObject>
<text x="90" y="760" fill="#9ab7ac" font-size="17" font-family="Inter,Arial">COHORT · {html.escape(player.cohort.upper())}</text>
<text x="90" y="806" fill="#9ab7ac" font-size="15" font-family="Inter,Arial">Editorial research hypothesis. Emphasis shape is not a performance rating.</text>
<polygon points="{grid}" fill="none" stroke="#315c4f" stroke-width="2"/>
<polygon points="{polygon}" fill="#63e6be" fill-opacity="0.18" stroke="#63e6be" stroke-width="4"/>
{''.join(labels)}
</svg>'''
    output.write_text(svg, encoding="utf-8")
    return output
