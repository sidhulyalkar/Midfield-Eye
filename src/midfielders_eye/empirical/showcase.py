from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import numpy as np
import pandas as pd

from .adapters import load_statsbomb_empirical_bundle
from .capture import default_midfield_capture_protocol, validate_capture_protocol
from .provenance import write_file_manifest
from .registry import load_source_registry
from ..showcase.catalog import load_player_catalog

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _pitch(ax) -> None:
    line = "#dbeafe"
    ax.set_facecolor("#0a2f29")
    ax.add_patch(Rectangle((0, 0), PITCH_LENGTH, PITCH_WIDTH, fill=False, linewidth=2.2, edgecolor=line))
    ax.plot([PITCH_LENGTH / 2, PITCH_LENGTH / 2], [0, PITCH_WIDTH], linewidth=1.4, color=line)
    circle = plt.Circle((PITCH_LENGTH / 2, PITCH_WIDTH / 2), 9.15, fill=False, linewidth=1.2, edgecolor=line)
    ax.add_patch(circle)
    ax.add_patch(Rectangle((0, 13.84), 16.5, 40.32, fill=False, linewidth=1.2, edgecolor=line))
    ax.add_patch(Rectangle((PITCH_LENGTH - 16.5, 13.84), 16.5, 40.32, fill=False, linewidth=1.2, edgecolor=line))
    ax.set_xlim(-2, PITCH_LENGTH + 2)
    ax.set_ylim(PITCH_WIDTH + 2, -2)
    ax.set_aspect("equal")
    ax.axis("off")


def _save(fig, path: Path, dpi: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path


def render_statsbomb_pedri(bundle_dir: Path, output: Path, *, dpi: int = 200) -> Path:
    bundle = load_statsbomb_empirical_bundle(bundle_dir)
    event = bundle["event"]
    snapshot = bundle["three_sixty"]
    fig, ax = plt.subplots(figsize=(19.2, 10.8))
    fig.patch.set_facecolor("#07111f")
    fig.subplots_adjust(top=0.82, bottom=0.17, left=0.07, right=0.93)
    _pitch(ax)

    visible = np.asarray(snapshot["visible_area"], dtype=float).reshape(-1, 2)
    visible[:, 0] *= PITCH_LENGTH / 120.0
    visible[:, 1] *= PITCH_WIDTH / 80.0
    ax.add_patch(Polygon(visible, closed=True, alpha=0.18, hatch="//", linewidth=1.8, facecolor="#7dd3fc", edgecolor="#bae6fd", label="provider-visible area"))

    actor_xy = None
    for index, player in enumerate(snapshot["freeze_frame"]):
        x = player["location"][0] * PITCH_LENGTH / 120.0
        y = player["location"][1] * PITCH_WIDTH / 80.0
        marker = "*" if player["actor"] else "o"
        size = 520 if player["actor"] else 170
        label = "Pedri, event actor" if player["actor"] else ("Spain teammate" if player["teammate"] else "Germany opponent")
        color = "#fbbf24" if player["actor"] else ("#38bdf8" if player["teammate"] else "#fb7185")
        ax.scatter([x], [y], s=size, marker=marker, c=color, edgecolors="#07111f", linewidths=1.6, label=label if label not in ax.get_legend_handles_labels()[1] else None)
        if player["actor"]:
            actor_xy = (x, y)
            ax.text(x + 1.2, y - 1.5, "Pedri", fontsize=15, weight="bold", color="white")

    end_x = event["pass"]["end_location"][0] * PITCH_LENGTH / 120.0
    end_y = event["pass"]["end_location"][1] * PITCH_WIDTH / 80.0
    if actor_xy:
        ax.annotate("", xy=(end_x, end_y), xytext=actor_xy, arrowprops={"arrowstyle": "->", "lw": 4, "color": "#fbbf24"})
        ax.text(end_x + 1.0, end_y, "to Aymeric Laporte", fontsize=14, color="white")

    fig.text(0.07, 0.94, "PEDRI · REAL EVENT-CENTERED 360 SNAPSHOT", fontsize=28, weight="bold", color="white")
    fig.text(0.07, 0.895, "Spain 1–1 Germany · FIFA World Cup · 27 Nov 2022 · 01:10.618", fontsize=16, color="#bae6fd")
    fig.text(0.07, 0.075,
             "MEASURED  actor identity · event location · pass target · visible area · freeze-frame geometry",
             fontsize=14, color="#a7f3d0", weight="bold")
    fig.text(0.07, 0.042,
             "UNAVAILABLE  literal gaze · head pose · body weight · joint force · continuous velocity",
             fontsize=14, color="#fda4af")
    legend = ax.legend(loc="upper right", frameon=True, fontsize=12)
    legend.get_frame().set_facecolor("#0f172a")
    legend.get_frame().set_edgecolor("#475569")
    for text in legend.get_texts():
        text.set_color("white")
    return _save(fig, output, dpi)


def _load_metrica_long(bundle_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_csv(bundle_dir / "home_normalized.csv"),
        pd.read_csv(bundle_dir / "away_normalized.csv"),
    )


def render_metrica_excerpt(bundle_dir: Path, output: Path, *, dpi: int = 200) -> Path:
    home, away = _load_metrica_long(bundle_dir)
    key = 1226
    fig, ax = plt.subplots(figsize=(19.2, 10.8))
    fig.patch.set_facecolor("#07111f")
    fig.subplots_adjust(top=0.82, bottom=0.17, left=0.07, right=0.93)
    _pitch(ax)
    for frame, group in home.groupby("frame"):
        if frame > key:
            continue
        alpha = max(0.08, 0.12 + 0.09 * (frame - home.frame.min()))
        for _, row in group[group.player_id != "Ball"].iterrows():
            if row.player_id in {"Player10", "Player8"}:
                ax.scatter(row.x_norm * PITCH_LENGTH, row.y_norm * PITCH_WIDTH, s=28, alpha=alpha, c="#38bdf8")
    h = home[home.frame == key]
    a = away[away.frame == key]
    for _, row in h[h.player_id != "Ball"].iterrows():
        ax.scatter(row.x_norm * PITCH_LENGTH, row.y_norm * PITCH_WIDTH, s=175, marker="o", c="#38bdf8", edgecolors="#07111f", linewidths=1.4)
        if row.player_id in {"Player10", "Player8"}:
            ax.text(row.x_norm * PITCH_LENGTH + 0.8, row.y_norm * PITCH_WIDTH - 1.0, row.player_id, fontsize=13, weight="bold", color="white")
    for _, row in a[a.player_id != "Ball"].iterrows():
        ax.scatter(row.x_norm * PITCH_LENGTH, row.y_norm * PITCH_WIDTH, s=175, marker="s", c="#fb7185", edgecolors="#07111f", linewidths=1.4)
    ball = h[h.player_id == "Ball"].iloc[0]
    ax.scatter(ball.x_norm * PITCH_LENGTH, ball.y_norm * PITCH_WIDTH, s=90, marker="o", facecolors="white", edgecolors="#07111f", linewidths=2)
    actor = h[h.player_id == "Player10"].iloc[0]
    receiver = h[h.player_id == "Player8"].iloc[0]
    ax.annotate("", xy=(receiver.x_norm * PITCH_LENGTH, receiver.y_norm * PITCH_WIDTH),
                xytext=(actor.x_norm * PITCH_LENGTH, actor.y_norm * PITCH_WIDTH),
                arrowprops={"arrowstyle": "->", "lw": 4, "color": "#fbbf24"})
    fig.text(0.07, 0.94, "METRICA · REAL SYNCHRONIZED TRACKING EXCERPT", fontsize=28, weight="bold", color="white")
    fig.text(0.07, 0.895, "Sample Game 1 · frame 1226 · 49.04 s · anonymous Player10 → Player8", fontsize=16, color="#bae6fd")
    fig.text(0.07, 0.075,
             "MEASURED  synchronized player and ball coordinates at 25 Hz · pass event",
             fontsize=14, color="#a7f3d0", weight="bold")
    fig.text(0.07, 0.042,
             "IDENTITY BOUNDARY  anonymous players · no named-player gaze, pose, or force claims",
             fontsize=14, color="#fda4af")
    return _save(fig, output, dpi)


def render_source_landscape(output: Path, *, dpi: int = 200) -> Path:
    registry = load_source_registry()
    modalities = ["eye_gaze", "head_pose", "body_pose_3d", "kinematics", "kinetics", "full_tracking", "partial_tracking", "event_360", "video"]
    sources = sorted(registry.sources, key=lambda item: (item.priority, item.name))
    matrix = np.array([[int(any(mod.value == name for mod in source.modalities)) for name in modalities] for source in sources])
    fig, ax = plt.subplots(figsize=(19.2, 10.8))
    ax.imshow(matrix, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(len(modalities)), [value.replace("_", " ").title() for value in modalities], rotation=32, ha="right", fontsize=13)
    ax.set_yticks(range(len(sources)), [source.name for source in sources], fontsize=12)
    for y, source in enumerate(sources):
        for x, value in enumerate(matrix[y]):
            if value:
                ax.text(x, y, "●", ha="center", va="center", fontsize=15)
        ax.text(len(modalities) - 0.35, y, f"  {source.access.value}", va="center", fontsize=10, alpha=0.8)
    ax.set_title("Empirical source landscape · what each dataset can actually support", fontsize=28, loc="left", pad=22, weight="bold")
    ax.text(0, 1.035,
            "A source can provide direct gaze, pose, tracking, or video. No single dataset currently provides every signal for elite named midfielders.",
            transform=ax.transAxes, fontsize=15)
    fig.tight_layout()
    return _save(fig, output, dpi)


def render_evidence_ladder(output: Path, *, dpi: int = 200) -> Path:
    tiers = [
        ("DIRECT MEASUREMENT", "Eye tracker, calibrated motion capture, force or IMU sensor", "May support literal measured-signal language"),
        ("PROVIDER TRACKING", "Licensed or open player/ball coordinates and event geometry", "Supports spatial and temporal state claims"),
        ("VIDEO RECONSTRUCTION", "Pose, tracking, calibration, and identity inferred from pixels", "Supports estimates with model uncertainty"),
        ("INFERRED PROXY", "Motion heading, torso proxy, synthetic visibility cone", "Must remain explicitly labeled as a proxy"),
        ("SYNTHETIC", "Controlled illustration or simulation", "Demonstrates software behavior, not player performance"),
        ("EDITORIAL HYPOTHESIS", "Scouting question or tactical interpretation", "A research prompt, never a measurement"),
    ]
    fig, ax = plt.subplots(figsize=(19.2, 10.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(tiers))
    ax.axis("off")
    for i, (name, evidence, claim) in enumerate(tiers):
        y = len(tiers) - i - 1
        ax.add_patch(Rectangle((0.03, y + 0.08), 0.94, 0.78, fill=False, linewidth=2.0))
        ax.text(0.06, y + 0.62, name, fontsize=19, weight="bold")
        ax.text(0.32, y + 0.62, evidence, fontsize=15)
        ax.text(0.32, y + 0.30, claim, fontsize=13, alpha=0.82)
    ax.set_title("Evidence ladder · the frontend must never climb without data", fontsize=30, loc="left", pad=20, weight="bold")
    ax.text(0.03, -0.22, "Every metric carries source, tier, measured fields, inferred fields, confidence, license, and citation.", fontsize=16)
    fig.tight_layout()
    return _save(fig, output, dpi)


def build_empirical_showcase(
    output_dir: str | Path,
    *,
    data_root: str | Path = "data/empirical",
    render_dpi: int = 200,
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data = Path(data_root)
    registry = load_source_registry()
    metrica_dir = data / "open" / "metrica_game1_pass_1226"
    statsbomb_dir = data / "open" / "statsbomb_3857263_pedri"

    visuals = output / "visuals"
    pedri = render_statsbomb_pedri(statsbomb_dir, visuals / "statsbomb-pedri-360-4k.png", dpi=render_dpi)
    metrica = render_metrica_excerpt(metrica_dir, visuals / "metrica-tracking-pass-4k.png", dpi=render_dpi)
    landscape = render_source_landscape(visuals / "empirical-source-landscape-4k.png", dpi=render_dpi)
    ladder = render_evidence_ladder(visuals / "evidence-ladder-4k.png", dpi=render_dpi)

    experiments = [
        {
            "id": "statsbomb-pedri-3857263-28ff205e",
            "title": "Pedri event-centered visible state",
            "subject": "Pedro González López",
            "source_id": "statsbomb_open_data",
            "evidence_tier": "provider_tracking",
            "modalities": ["event_360"],
            "measured": ["actor_identity", "event_location", "pass_target", "visible_area", "freeze_frame_geometry"],
            "inferred": ["candidate_action_menu", "pressure_geometry", "visibility_limits"],
            "unavailable": ["literal_gaze", "head_pose", "body_weight", "joint_force", "continuous_velocity"],
            "visual": pedri.relative_to(output).as_posix(),
            "source_bundle": "data/empirical/open/statsbomb_3857263_pedri",
            "claim_boundary": "Named-player geometry is real; gaze and biomechanics are unavailable in this source.",
        },
        {
            "id": "metrica-game1-frame1226",
            "title": "Continuous oracle-state pass geometry",
            "subject": None,
            "source_id": "metrica_sample_data",
            "evidence_tier": "provider_tracking",
            "modalities": ["full_tracking", "ball"],
            "measured": ["player_xy", "ball_xy", "event_start", "event_end"],
            "inferred": ["velocity", "pressure", "passing_corridor", "action_menu"],
            "unavailable": ["named_player_identity", "literal_gaze", "body_pose", "forces"],
            "visual": metrica.relative_to(output).as_posix(),
            "source_bundle": "data/empirical/open/metrica_game1_pass_1226",
            "claim_boundary": "The spatial state is real but anonymous; it cannot validate named-player style claims.",
        },
    ]
    _write_json(output / "experiments.json", experiments)
    catalog = load_player_catalog()
    player_ledger = []
    for player in catalog.players:
        real_evidence = []
        status = "no_source_pinned_player_measurement"
        if player.id == "pedri":
            status = "source_pinned_event_360"
            real_evidence.append("statsbomb-pedri-3857263-28ff205e")
        player_ledger.append({
            "player_id": player.id,
            "player_name": player.name,
            "status": status,
            "real_evidence_ids": real_evidence,
            "direct_gaze": False,
            "direct_biomechanics": False,
            "continuous_named_tracking": False,
            "next_sources": [
                "licensed_provider_tracking_or_rights_cleared_video",
                "Ego-Exo4D_for_gaze_representation_pretraining",
                "consented_OpenCap_or_Pose2Sim_for_biomechanics",
            ],
            "frontend_rule": "Show absence as absence; do not inherit measurements from an archetype or another player.",
        })
    _write_json(output / "player_evidence_ledger.json", player_ledger)
    _write_json(output / "sources.json", registry.to_dict())
    _write_json(output / "citation_index.json", {
        source.id: {"citation": source.citation, "official_url": source.official_url, "license": source.license_name}
        for source in registry.sources
    })
    capture_protocol = default_midfield_capture_protocol()
    _write_json(output / "capture_protocol.json", {
        "protocol": capture_protocol.to_dict(),
        "valid": not validate_capture_protocol(capture_protocol),
        "errors": validate_capture_protocol(capture_protocol),
    })
    _write_json(output / "alignment_contract.json", {
        "clock_model": "canonical_time_s = offset_s + scale * sensor_time_s",
        "minimum_anchor_count": 2,
        "recommended_anchor_count_per_block": 3,
        "alignment_policy": "nearest sample within explicit tolerance; otherwise preserve missingness",
        "required_output_fields": [
            "frame_timestamp_s",
            "sensor_timestamp_s",
            "canonical_sensor_timestamp_s",
            "delta_ms",
            "source",
            "confidence",
            "status",
        ],
        "scan_event_policy": "transparent angular-velocity threshold baseline; human validation required",
    })
    _write_json(output / "claim_contract.json", {
        "required_fields": ["source_id", "evidence_tier", "measured", "inferred", "unavailable", "confidence", "citation"],
        "rules": [
            "Literal gaze requires a calibrated eye-gaze source.",
            "Body-weight and force language requires direct kinetics or a clearly labeled model estimate.",
            "StatsBomb 360 is an event snapshot, not continuous tracking.",
            "Metrica Sample Game identities are anonymous.",
            "Pose or motion direction is never silently relabeled as gaze.",
            "Named-player evidence requires a source that actually identifies the player.",
        ],
    })
    manifest = {
        "version": "0.6.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": "The Midfielder's Eye · Empirical Evidence Studio",
        "source_count": len(registry.sources),
        "real_source_experiment_count": len(experiments),
        "direct_gaze_downloaded": False,
        "named_player_biomechanics_downloaded": False,
        "experiments_path": "experiments.json",
        "sources_path": "sources.json",
        "citations_path": "citation_index.json",
        "player_evidence_ledger_path": "player_evidence_ledger.json",
        "claim_contract_path": "claim_contract.json",
        "capture_protocol_path": "capture_protocol.json",
        "alignment_contract_path": "alignment_contract.json",
        "visuals": [pedri.relative_to(output).as_posix(), metrica.relative_to(output).as_posix(), landscape.relative_to(output).as_posix(), ladder.relative_to(output).as_posix()],
        "next_empirical_gates": [
            "Accept the Ego-Exo4D license and download soccer gaze takes.",
            "Register for WorldPose and ingest approved 3D soccer pose sequences.",
            "Run a consented OpenCap or Pose2Sim receiving-and-turning protocol.",
            "Acquire rights-cleared named-player footage or licensed provider tracking before publishing player-specific measurements.",
        ],
    }
    _write_json(output / "manifest.json", manifest)
    write_file_manifest(
        output,
        source_id="midfielders_eye_empirical_showcase",
        metadata={"version": "0.6.0"},
        manifest_name="FILE_MANIFEST.json",
    )
    return output / "manifest.json"
