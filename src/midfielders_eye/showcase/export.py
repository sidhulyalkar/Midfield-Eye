from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import __version__
from ..affordance import AffordanceEngine
from ..cognition import sequence_body_summary, sequence_gaze_summary, sequence_relational_summary
from ..empirical.showcase import build_empirical_showcase
from ..io import write_frames_jsonl
from ..schema import ActionOption
from ..visualization.showcase import (
    render_body_mechanics_lab,
    render_counterfactual_uplift,
    render_gaze_lab,
    render_option_timeline,
    render_player_profile_svg,
    render_relational_control_lab,
    render_style_profile,
    render_tactical_lens,
)
from .catalog import load_player_catalog
from .metrics import scenario_summary
from .scenarios import SCENARIOS, build_scenario_frames


def _option_payload(option: ActionOption) -> dict[str, Any]:
    return {
        "sequence_id": option.sequence_id,
        "frame_id": option.frame_id,
        "option_id": option.option_id,
        "kind": option.kind,
        "actor_id": option.actor_id,
        "target_player_id": option.target_player_id,
        "target_x": option.target_x,
        "target_y": option.target_y,
        "features": option.features,
        "geometric_score": option.geometric_score,
        "learned_score": option.learned_score,
        "source_provider": option.source_provider,
        "provenance": option.provenance,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_player_atlas(output: Path, catalog) -> list[dict[str, Any]]:
    atlas: list[dict[str, Any]] = []
    for player in catalog.players:
        player_dir = output / "players" / player.id
        player_dir.mkdir(parents=True, exist_ok=True)
        profile = player.to_dict()
        profile["profile_card"] = f"players/{player.id}/profile.svg"
        profile["scenario_ids"] = [scenario.id for scenario in SCENARIOS.values() if scenario.player_id == player.id]
        _write_json(player_dir / "profile.json", profile)
        render_player_profile_svg(player, player_dir / "profile.svg")
        atlas.append(profile)
    _write_json(output / "players" / "index.json", atlas)
    cohort_summary = {
        cohort: {
            "count": len([player for player in catalog.players if player.cohort == cohort]),
            "featured_count": len([player for player in catalog.players if player.cohort == cohort and player.featured]),
            "archetype_count": len({player.primary_archetype for player in catalog.players if player.cohort == cohort}),
        }
        for cohort in catalog.cohort_balance
    }
    _write_json(output / "players" / "cohorts.json", cohort_summary)
    _write_json(
        output / "players" / "comparison_axes.json",
        {
            "axes": list(next(iter(catalog.players)).showcase_emphasis),
            "status": "illustrative_archetype_emphasis_not_player_rating",
            "comparison_rules": [
                "Do not call these ability ratings.",
                "Use these axes to select what to investigate in rights-cleared data.",
                "Measured comparisons require context normalization and uncertainty intervals.",
            ],
        },
    )
    return atlas


def build_showcase_bundle(
    output_dir: str | Path,
    *,
    catalog_path: str | Path | None = None,
    scenario_ids: list[str] | None = None,
    frame_count: int = 18,
    render_dpi: int = 200,
    include_empirical: bool = True,
    empirical_data_root: str | Path = "data/empirical",
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    catalog = load_player_catalog(catalog_path)
    selected = scenario_ids or list(SCENARIOS)
    unknown = sorted(set(selected) - set(SCENARIOS))
    if unknown:
        raise ValueError(f"unknown scenarios: {', '.join(unknown)}")
    _write_json(output / "players.json", catalog.to_dict())
    _build_player_atlas(output, catalog)

    engine = AffordanceEngine()
    scenario_index: list[dict[str, Any]] = []
    for scenario_id in selected:
        scenario = SCENARIOS[scenario_id]
        frames = build_scenario_frames(scenario_id, frame_count=frame_count)
        scenario_dir = output / "scenarios" / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        write_frames_jsonl(frames, scenario_dir / "frames.jsonl")
        options_by_frame: dict[int, list[ActionOption]] = defaultdict(list)
        options: list[ActionOption] = []
        for frame in frames:
            current = engine.generate(frame)
            options.extend(current)
            options_by_frame[frame.frame_id].extend(current)
        _write_json(scenario_dir / "options.json", [_option_payload(option) for option in options])
        summary = scenario_summary(frames, options_by_frame)
        gaze = sequence_gaze_summary(frames, options_by_frame)
        body = sequence_body_summary(frames, options_by_frame)
        relational = sequence_relational_summary(frames, options_by_frame)
        _write_json(scenario_dir / "timeline.json", summary["timeline"])
        _write_json(scenario_dir / "summary.json", summary)
        _write_json(scenario_dir / "gaze.json", gaze)
        _write_json(scenario_dir / "body_mechanics.json", body)
        _write_json(scenario_dir / "relational_control.json", relational)
        _write_json(scenario_dir / "scenario.json", scenario.to_dict())

        key_index = min(scenario.key_frame_index, len(frames) - 1)
        key_frame = frames[key_index]
        key_options = options_by_frame[key_frame.frame_id]
        visuals = scenario_dir / "visuals"
        tactical_path = visuals / "tactical-lens-4k.png"
        tactical = tactical_path if tactical_path.exists() else render_tactical_lens(
            key_frame,
            key_options,
            tactical_path,
            title=scenario.title,
            subtitle=scenario.tactical_question,
            player_name=scenario.player_name,
            dpi=render_dpi,
        )
        timeline_path = visuals / "action-menu-timeline-4k.png"
        timeline = timeline_path if timeline_path.exists() else render_option_timeline(
            summary["timeline"],
            timeline_path,
            title=f"{scenario.player_name} · {scenario.title}",
            dpi=render_dpi,
        )
        style_path = visuals / "scenario-style-profile-4k.png"
        style = style_path if style_path.exists() else render_style_profile(
            key_options,
            style_path,
            player_name=scenario.player_name,
            archetype=scenario.archetype,
            dpi=render_dpi,
        )
        counterfactual_path = visuals / "counterfactual-uplift-4k.png"
        counterfactual = counterfactual_path if counterfactual_path.exists() else render_counterfactual_uplift(
            key_frame,
            key_options,
            counterfactual_path,
            title="What earlier movement would improve the future menu?",
            player_name=scenario.player_name,
            dpi=render_dpi,
        )
        gaze_path = visuals / "gaze-lab-4k.png"
        gaze_visual = gaze_path if gaze_path.exists() else render_gaze_lab(
            key_frame,
            key_options,
            gaze,
            gaze_path,
            title="What entered view before the action?",
            player_name=scenario.player_name,
            dpi=render_dpi,
        )
        body_path = visuals / "body-mechanics-4k.png"
        body_visual = body_path if body_path.exists() else render_body_mechanics_lab(
            key_frame,
            key_options,
            body,
            body_path,
            title="One posture, several executable futures",
            player_name=scenario.player_name,
            dpi=render_dpi,
        )
        relational_path = visuals / "relational-control-4k.png"
        relational_visual = relational_path if relational_path.exists() else render_relational_control_lab(
            key_frame,
            key_options,
            relational,
            relational_path,
            title="How the collective reorganizes around the subject",
            player_name=scenario.player_name,
            dpi=render_dpi,
        )
        scenario_payload = scenario.to_dict()
        scenario_payload.update(
            {
                "summary_signals": {
                    "gaze": gaze["summary"],
                    "body_mechanics": body["summary"],
                    "relational_control": relational["summary"],
                },
                "paths": {
                    "scenario": f"scenarios/{scenario_id}/scenario.json",
                    "frames": f"scenarios/{scenario_id}/frames.jsonl",
                    "options": f"scenarios/{scenario_id}/options.json",
                    "timeline": f"scenarios/{scenario_id}/timeline.json",
                    "summary": f"scenarios/{scenario_id}/summary.json",
                    "gaze": f"scenarios/{scenario_id}/gaze.json",
                    "body_mechanics": f"scenarios/{scenario_id}/body_mechanics.json",
                    "relational_control": f"scenarios/{scenario_id}/relational_control.json",
                    "tactical_lens": str(tactical.relative_to(output)).replace("\\", "/"),
                    "action_menu_timeline": str(timeline.relative_to(output)).replace("\\", "/"),
                    "style_profile": str(style.relative_to(output)).replace("\\", "/"),
                    "counterfactual_uplift": str(counterfactual.relative_to(output)).replace("\\", "/"),
                    "gaze_lab": str(gaze_visual.relative_to(output)).replace("\\", "/"),
                    "body_mechanics_lab": str(body_visual.relative_to(output)).replace("\\", "/"),
                    "relational_control_lab": str(relational_visual.relative_to(output)).replace("\\", "/"),
                },
            }
        )
        scenario_index.append(scenario_payload)

    _write_json(output / "scenarios" / "index.json", scenario_index)
    empirical_manifest = None
    if include_empirical:
        empirical_manifest = build_empirical_showcase(
            output / "empirical",
            data_root=empirical_data_root,
            render_dpi=render_dpi,
        )
    manifest = {
        "bundle_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": "The Midfielder's Eye · Action Menu Benchmark",
        "description": "Frontend-ready 100-player hypothesis atlas plus source-pinned empirical evidence, ranked action menus, governed perception inputs, and the v0.7 decision-microscope contract.",
        "players_path": "players.json",
        "player_atlas_path": "players/index.json",
        "player_comparison_axes_path": "players/comparison_axes.json",
        "scenarios_path": "scenarios/index.json",
        "empirical_path": None if empirical_manifest is None else "empirical/manifest.json",
        "scenario_count": len(scenario_index),
        "player_count": len(catalog.players),
        "cohort_balance": catalog.cohort_balance,
        "ranking_policy": catalog.ranking_policy,
        "evidence_contract": {
            "synthetic_showcases": "illustrative only; never presented as real-player measured performance",
            "gaze": "literal gaze claims require observed gaze; pose, motion, and synthetic sources must remain labeled",
            "body_weight": "weight-transfer and balance are proxies unless pose/biomechanical sensors are present",
            "relational_control": "geometry can show response timing but cannot establish leadership intent alone",
            "real_player_analysis": "requires rights-cleared footage or licensed tracking and explicit provenance",
            "empirical_layer": "source-pinned real examples are separated from inferred proxies and synthetic demonstrations",
            "action_menu_lifecycle": "birth and extinction are retrospective visualization labels, never future-aware focal-frame features",
            "youtube": "embed-only reference lane; no downloading or pixel analysis",
        },
        "frontend_contract": {
            "coordinate_system": "105x68 metres, origin top-left, x toward home attack unless metadata states otherwise",
            "score_range": "model-dependent; rank within frame before comparing across providers",
            "responsive_targets": ["1440x900", "1920x1080", "3840x2160", "390x844"],
            "vector_player_cards": 100,
            "high_resolution_visuals_per_scenario": 7,
            "signature_instrument": "Action Menu Ribbon / Decision Microscope",
        },
    }
    _write_json(output / "manifest.json", manifest)
    return output / "manifest.json"
