from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import yaml

from .adapters import PROVIDERS
from .affordance import AffordanceEngine
from .io import (
    options_to_dataframe,
    read_frames_jsonl,
    write_frames_jsonl,
    write_options_csv,
)
from .pilot import freeze_pilot, load_annotations, sha256_file, validate_causal_frame_states
from .reliability import ReliabilityGate, reliability_report
from .schema import FrameState

R1_SCHEMA_VERSION = "r1-real-action-menu-pilot-v1"
R1_SHOWCASE_SCHEMA_VERSION = "r1-showcase-v1"

DEFAULT_TARGET_COMPOSITION = {
    "central_pressure": 3,
    "transition": 2,
    "settled_possession": 2,
    "wide_overload": 2,
    "negative_control": 1,
}

MODEL_OR_LABEL_COLUMNS = {
    "geometric_score",
    "learned_score",
    "naive_score",
    "static_score",
    "dynamic_score",
    "viewpoint_score",
    "label_available",
    "label_value",
    "label_value_ordinal",
    "label_selected",
    "label_visibility",
    "label_confidence",
    "label_creation",
    "label_creation_ordinal",
    "label_failure_reason",
    "selected",
    "available",
    "visible",
    "value_ordinal",
    "creation_ordinal",
}


@dataclass(frozen=True)
class R1PilotConfig:
    target_sequences: int = 10
    label_hz: float = 5.0
    pre_context_s: float = 1.6
    label_duration_s: float = 1.4
    minimum_control_s: float = 0.45
    minimum_window_separation_s: float = 2.0
    minimum_label_frames: int = 4
    seed: int = 17
    require_continuous_tracking: bool = True
    require_full_double_rating: bool = True
    target_composition: dict[str, int] | None = None

    def composition(self) -> dict[str, int]:
        return dict(self.target_composition or DEFAULT_TARGET_COMPOSITION)

    def validate(self) -> None:
        if self.target_sequences < 2:
            raise ValueError("R1 requires at least two independent sequences")
        if self.label_hz <= 0:
            raise ValueError("label_hz must be positive")
        if self.pre_context_s < 0 or self.label_duration_s <= 0:
            raise ValueError("context and label durations must be non-negative/positive")
        if self.minimum_control_s <= 0:
            raise ValueError("minimum_control_s must be positive")
        if self.minimum_label_frames < 2:
            raise ValueError("minimum_label_frames must be at least two")
        if sum(self.composition().values()) != self.target_sequences:
            raise ValueError(
                "R1 target composition must sum exactly to target_sequences"
            )


@dataclass(frozen=True)
class R1Window:
    sequence_id: str
    source_sequence_id: str
    source_provider: str
    source_match_id: str
    period: int
    anchor_frame_id: int
    anchor_timestamp_s: float
    carrier_id: str
    label_frames: tuple[FrameState, ...]
    context_frames: tuple[FrameState, ...]

    @property
    def source_frame_keys(self) -> set[tuple[str, str, int, int]]:
        return {
            (
                frame.source_provider,
                frame.source_match_id or self.source_match_id,
                frame.period,
                frame.frame_id,
            )
            for frame in self.context_frames
        }


def load_r1_config(path: str | Path | None = None) -> R1PilotConfig:
    if path is None:
        config = R1PilotConfig()
        config.validate()
        return config
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    allowed = {
        "target_sequences",
        "label_hz",
        "pre_context_s",
        "label_duration_s",
        "minimum_control_s",
        "minimum_window_separation_s",
        "minimum_label_frames",
        "seed",
        "require_continuous_tracking",
        "require_full_double_rating",
        "target_composition",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"Unknown R1 config fields: {unknown}")
    config = R1PilotConfig(**payload)
    config.validate()
    return config


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return cleaned or "unknown"


def _is_synthetic_provider(provider: str) -> bool:
    lowered = provider.casefold()
    return any(marker in lowered for marker in ("synthetic", "bootstrap", "demo"))


def _validate_provider(
    frame: FrameState,
    *,
    allow_synthetic: bool,
    require_tracking: bool,
) -> None:
    provider = frame.source_provider
    if _is_synthetic_provider(provider):
        if not allow_synthetic:
            raise ValueError(
                f"R1 real pilot refuses synthetic provider {provider!r}; "
                "use allow_synthetic_software_validation only in tests."
            )
        return
    if not require_tracking:
        return
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise ValueError(
            f"R1 requires a registered continuous-tracking provider; {provider!r} is unknown."
        )
    if not spec.capabilities.tracking:
        raise ValueError(
            f"Provider {provider!r} is not registered as tracking-capable and cannot support R1."
        )
    coverage = str(spec.coverage).casefold()
    if "snapshot" in coverage or "event" in coverage and "tracking" not in coverage:
        raise ValueError(
            f"Provider {provider!r} is event/snapshot-oriented and cannot support the dynamic R1 pilot."
        )


def _downsample_label_frames(
    frames: Sequence[FrameState],
    *,
    start_s: float,
    end_s: float,
    label_hz: float,
    carrier_id: str,
    possession_team: str,
) -> list[FrameState]:
    eligible = [
        frame
        for frame in frames
        if start_s <= frame.timestamp_s <= end_s
        and frame.ball_carrier_id == carrier_id
        and frame.possession_team == possession_team
    ]
    if not eligible:
        return []
    eligible.sort(key=lambda frame: (frame.timestamp_s, frame.frame_id))
    period_s = 1.0 / label_hz
    selected: list[FrameState] = []
    next_target = eligible[0].timestamp_s
    for frame in eligible:
        if not selected or frame.timestamp_s + 1e-9 >= next_target:
            selected.append(frame)
            next_target = frame.timestamp_s + period_s
    return selected


def discover_receipt_windows(
    frames: Iterable[FrameState],
    *,
    config: R1PilotConfig | None = None,
    allow_synthetic_software_validation: bool = False,
) -> list[R1Window]:
    """Discover non-overlapping carrier-control windows from canonical tracking.

    A window starts when a carrier first appears in an input sequence or when the
    carrier changes while possession remains with the same team. R1 uses the
    window only to define independent annotation units. It does not infer the
    selected action or use future observations as focal-frame model features.
    """

    config = config or R1PilotConfig()
    config.validate()
    frame_list = list(frames)
    if not frame_list:
        raise ValueError("R1 requires at least one canonical frame")
    validate_causal_frame_states(frame_list)
    for frame in frame_list:
        _validate_provider(
            frame,
            allow_synthetic=allow_synthetic_software_validation,
            require_tracking=config.require_continuous_tracking,
        )

    grouped: dict[tuple[str, str, int, str], list[FrameState]] = {}
    for frame in frame_list:
        key = (
            frame.source_provider,
            frame.source_match_id or frame.sequence_id,
            frame.period,
            frame.sequence_id,
        )
        grouped.setdefault(key, []).append(frame)

    windows: list[R1Window] = []
    occupied_source_frames: set[tuple[str, str, int, int]] = set()
    last_anchor_by_stream: dict[tuple[str, str, int, str], float] = {}

    for stream_key in sorted(grouped):
        stream = sorted(
            grouped[stream_key],
            key=lambda frame: (frame.timestamp_s, frame.frame_id),
        )
        if len(stream) < config.minimum_label_frames:
            continue
        anchors: list[int] = [0]
        for index in range(1, len(stream)):
            previous = stream[index - 1]
            current = stream[index]
            if (
                current.ball_carrier_id != previous.ball_carrier_id
                or current.possession_team != previous.possession_team
            ):
                anchors.append(index)

        for anchor_index in anchors:
            anchor = stream[anchor_index]
            previous_anchor = last_anchor_by_stream.get(stream_key)
            if (
                previous_anchor is not None
                and anchor.timestamp_s - previous_anchor
                < config.minimum_window_separation_s
            ):
                continue

            control_end = anchor.timestamp_s
            for frame in stream[anchor_index:]:
                if (
                    frame.ball_carrier_id != anchor.ball_carrier_id
                    or frame.possession_team != anchor.possession_team
                ):
                    break
                control_end = frame.timestamp_s
            if control_end - anchor.timestamp_s < config.minimum_control_s:
                continue

            label_end = min(
                control_end,
                anchor.timestamp_s + config.label_duration_s,
            )
            label_frames = _downsample_label_frames(
                stream,
                start_s=anchor.timestamp_s,
                end_s=label_end,
                label_hz=config.label_hz,
                carrier_id=anchor.ball_carrier_id,
                possession_team=anchor.possession_team,
            )
            if len(label_frames) < config.minimum_label_frames:
                continue

            context_start = anchor.timestamp_s - config.pre_context_s
            context_end = label_frames[-1].timestamp_s
            context_frames = [
                frame
                for frame in stream
                if context_start <= frame.timestamp_s <= context_end
            ]
            match_id = anchor.source_match_id or anchor.sequence_id
            source_keys = {
                (
                    frame.source_provider,
                    frame.source_match_id or match_id,
                    frame.period,
                    frame.frame_id,
                )
                for frame in context_frames
            }
            if source_keys & occupied_source_frames:
                continue

            sequence_id = (
                f"r1-{_slug(anchor.source_provider)}-{_slug(match_id)}-"
                f"p{anchor.period}-f{anchor.frame_id}"
            )
            source_sequence_id = anchor.sequence_id

            def relabel(frame: FrameState, role: str) -> FrameState:
                metadata = dict(frame.metadata)
                metadata.update(
                    {
                        "r1_source_sequence_id": source_sequence_id,
                        "r1_anchor_frame_id": anchor.frame_id,
                        "r1_anchor_timestamp_s": anchor.timestamp_s,
                        "r1_window_role": role,
                    }
                )
                return replace(frame, sequence_id=sequence_id, metadata=metadata)

            relabeled_label = tuple(relabel(frame, "label") for frame in label_frames)
            label_keys = {(frame.period, frame.frame_id) for frame in label_frames}
            relabeled_context = tuple(
                relabel(
                    frame,
                    "label"
                    if (frame.period, frame.frame_id) in label_keys
                    else "causal_context",
                )
                for frame in context_frames
            )
            windows.append(
                R1Window(
                    sequence_id=sequence_id,
                    source_sequence_id=source_sequence_id,
                    source_provider=anchor.source_provider,
                    source_match_id=match_id,
                    period=anchor.period,
                    anchor_frame_id=anchor.frame_id,
                    anchor_timestamp_s=anchor.timestamp_s,
                    carrier_id=anchor.ball_carrier_id,
                    label_frames=relabeled_label,
                    context_frames=relabeled_context,
                )
            )
            occupied_source_frames.update(source_keys)
            last_anchor_by_stream[stream_key] = anchor.timestamp_s

    return windows


def _window_state_features(window: R1Window) -> dict[str, float]:
    frame = window.label_frames[0]
    carrier = frame.carrier
    opponents = frame.opponents()
    teammates = frame.teammates()
    opponent_distances = [
        math.hypot(player.x - carrier.x, player.y - carrier.y)
        for player in opponents
    ]
    teammate_distances = [
        math.hypot(player.x - carrier.x, player.y - carrier.y)
        for player in teammates
    ]
    min_opponent = min(opponent_distances) if opponent_distances else frame.pitch_length
    near_opponents = sum(distance <= 7.0 for distance in opponent_distances)
    near_teammates = sum(distance <= 12.0 for distance in teammate_distances)
    normalized_lateral = abs(carrier.y / frame.pitch_width - 0.5) * 2.0
    centrality = max(0.0, 1.0 - normalized_lateral)
    pressure = math.exp(-min_opponent / 4.5)
    carrier_speed = carrier.speed
    ball_speed = math.hypot(frame.ball_vx, frame.ball_vy)
    local_density = min((near_opponents + near_teammates) / 8.0, 1.0)
    support = min(near_teammates / 4.0, 1.0)
    return {
        "carrier_speed_mps": carrier_speed,
        "ball_speed_mps": ball_speed,
        "min_opponent_distance_m": min_opponent,
        "opponents_within_7m": float(near_opponents),
        "teammates_within_12m": float(near_teammates),
        "centrality": centrality,
        "wide_index": normalized_lateral,
        "local_density": local_density,
        "support_index": support,
        "central_pressure_score": centrality
        * min(1.0, pressure + near_opponents / 5.0),
        "transition_score": min(1.0, carrier_speed / 6.5) * 0.65
        + min(1.0, ball_speed / 12.0) * 0.35,
        "settled_possession_score": max(0.0, 1.0 - carrier_speed / 5.0)
        * local_density,
        "wide_overload_score": normalized_lateral * local_density,
        "negative_control_score": pressure * max(0.0, 1.0 - support),
    }


def build_sequence_inventory(windows: Sequence[R1Window]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for window in windows:
        features = _window_state_features(window)
        rows.append(
            {
                "sequence_id": window.sequence_id,
                "source_sequence_id": window.source_sequence_id,
                "source_provider": window.source_provider,
                "source_match_id": window.source_match_id,
                "period": window.period,
                "anchor_frame_id": window.anchor_frame_id,
                "anchor_timestamp_s": window.anchor_timestamp_s,
                "carrier_id": window.carrier_id,
                "label_frames": len(window.label_frames),
                "context_frames": len(window.context_frames),
                **features,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["source_provider", "source_match_id", "period", "anchor_timestamp_s"],
        ignore_index=True,
    )


def propose_balanced_sample(
    inventory: pd.DataFrame,
    *,
    config: R1PilotConfig | None = None,
) -> pd.DataFrame:
    """Create a deterministic, reviewable ten-sequence proposal.

    The stratum labels are sampling heuristics derived from focal tracking state.
    They are not tactical ground truth and are never used as model labels.
    """

    config = config or R1PilotConfig()
    config.validate()
    if len(inventory) < config.target_sequences:
        raise ValueError(
            f"R1 needs {config.target_sequences} eligible non-overlapping windows; "
            f"found {len(inventory)}."
        )
    score_columns = {
        "central_pressure": "central_pressure_score",
        "transition": "transition_score",
        "settled_possession": "settled_possession_score",
        "wide_overload": "wide_overload_score",
        "negative_control": "negative_control_score",
    }
    missing = sorted(set(score_columns.values()) - set(inventory.columns))
    if missing:
        raise ValueError(f"R1 inventory is missing sampling scores: {missing}")

    selected_rows: list[pd.Series] = []
    used: set[str] = set()
    rng = np.random.default_rng(config.seed)
    jitter = {
        str(sequence_id): float(value)
        for sequence_id, value in zip(
            inventory["sequence_id"].astype(str),
            rng.uniform(0.0, 1e-9, size=len(inventory)),
            strict=True,
        )
    }

    for stratum, count in config.composition().items():
        score_column = score_columns[stratum]
        candidates = inventory[~inventory["sequence_id"].astype(str).isin(used)].copy()
        candidates["_jitter"] = candidates["sequence_id"].astype(str).map(jitter)
        candidates["_selection_score"] = candidates[score_column] + candidates["_jitter"]
        candidates = candidates.sort_values(
            ["_selection_score", "sequence_id"],
            ascending=[False, True],
        )
        if len(candidates) < count:
            raise ValueError(f"Not enough unused sequences to fill R1 stratum {stratum!r}")
        for _, row in candidates.head(count).iterrows():
            row = row.copy()
            row["sampling_stratum"] = stratum
            row["sampling_score"] = float(row[score_column])
            selected_rows.append(row)
            used.add(str(row["sequence_id"]))

    selected = pd.DataFrame(selected_rows).drop(
        columns=["_jitter", "_selection_score"],
        errors="ignore",
    )
    selected["sampling_label_status"] = "heuristic_for_diversity_not_ground_truth"
    selected["sample_order"] = np.arange(1, len(selected) + 1)
    return selected.sort_values("sample_order", ignore_index=True)


def build_rater_assignments(
    label_frames: Sequence[FrameState],
    *,
    rater_ids: Sequence[str],
    seed: int = 17,
) -> pd.DataFrame:
    raters = [str(value).strip() for value in rater_ids if str(value).strip()]
    if len(set(raters)) < 2:
        raise ValueError("R1 requires at least two distinct rater IDs")
    frame_rows = pd.DataFrame(
        [
            {
                "sequence_id": frame.sequence_id,
                "frame_id": frame.frame_id,
                "timestamp_s": frame.timestamp_s,
                "source_provider": frame.source_provider,
                "source_match_id": frame.source_match_id,
            }
            for frame in label_frames
        ]
    ).drop_duplicates(["sequence_id", "frame_id"])
    if frame_rows.empty:
        raise ValueError("R1 cannot assign an empty label-frame set")

    rows: list[dict[str, Any]] = []
    for rater_id in sorted(set(raters)):
        digest = hashlib.sha256(f"{seed}:{rater_id}".encode("utf-8")).digest()
        local_seed = int.from_bytes(digest[:8], "little", signed=False)
        rng = np.random.default_rng(local_seed)
        order = rng.permutation(len(frame_rows))
        for display_order, row_index in enumerate(order, start=1):
            row = frame_rows.iloc[int(row_index)]
            rows.append(
                {
                    "annotator_id": rater_id,
                    "display_order": display_order,
                    "sequence_id": row["sequence_id"],
                    "frame_id": int(row["frame_id"]),
                    "timestamp_s": float(row["timestamp_s"]),
                    "source_provider": row["source_provider"],
                    "source_match_id": row["source_match_id"],
                    "outcome_blinded": True,
                    "model_score_blinded": True,
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["annotator_id", "display_order"],
        ignore_index=True,
    )


def _safe_candidate_export(candidates: pd.DataFrame) -> pd.DataFrame:
    identity = [
        "sequence_id",
        "frame_id",
        "option_id",
        "kind",
        "actor_id",
        "target_player_id",
        "target_x",
        "target_y",
        "source_provider",
        "source_match_id",
        "provenance",
    ]
    available = [column for column in identity if column in candidates.columns]
    safe = candidates[available].copy()
    forbidden = sorted(set(safe.columns) & MODEL_OR_LABEL_COLUMNS)
    if forbidden:
        raise ValueError(f"R1 blinded candidate export leaked forbidden columns: {forbidden}")
    return safe


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return path


def prepare_real_pilot(
    frames_path: str | Path,
    output_dir: str | Path,
    *,
    rater_ids: Sequence[str],
    reviewed_by: str | None = None,
    config: R1PilotConfig | None = None,
    protocol_path: str | Path = "docs/ANNOTATION_GUIDE.md",
    allow_synthetic_software_validation: bool = False,
) -> Path:
    """Prepare the immutable R1 sampling and double-annotation package."""

    config = config or R1PilotConfig()
    config.validate()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    frames_path = Path(frames_path)
    frames = read_frames_jsonl(frames_path)
    windows = discover_receipt_windows(
        frames,
        config=config,
        allow_synthetic_software_validation=allow_synthetic_software_validation,
    )
    inventory = build_sequence_inventory(windows)
    proposal = propose_balanced_sample(inventory, config=config)
    selected_ids = set(proposal["sequence_id"].astype(str))
    selected_windows = [window for window in windows if window.sequence_id in selected_ids]
    selected_windows.sort(
        key=lambda window: int(
            proposal.loc[
                proposal["sequence_id"] == window.sequence_id,
                "sample_order",
            ].iloc[0]
        )
    )

    label_frames = [frame for window in selected_windows for frame in window.label_frames]
    context_frames = [frame for window in selected_windows for frame in window.context_frames]
    source_keys: list[tuple[str, str, int, int]] = []
    for window in selected_windows:
        source_keys.extend(sorted(window.source_frame_keys))
    if len(source_keys) != len(set(source_keys)):
        raise ValueError("R1 selected windows overlap in source frames; sequence leakage risk")

    label_frames_path = write_frames_jsonl(
        label_frames,
        root / "pilot_label_frames.jsonl",
    )
    context_frames_path = write_frames_jsonl(
        context_frames,
        root / "pilot_causal_context_frames.jsonl",
    )
    engine = AffordanceEngine()
    options = [option for frame in label_frames for option in engine.generate(frame)]
    if not options:
        raise ValueError("R1 candidate generation produced no options")
    candidates_path = write_options_csv(options, root / "pilot_candidates.csv")
    candidates = options_to_dataframe(options)
    _safe_candidate_export(candidates).to_csv(
        root / "pilot_candidates_blinded.csv",
        index=False,
    )
    inventory.to_csv(root / "sequence_inventory.csv", index=False)
    proposal["reviewed_by"] = reviewed_by or ""
    proposal["review_status"] = (
        "accepted_for_pilot" if reviewed_by else "pending_human_review"
    )
    proposal.to_csv(root / "sample_plan.csv", index=False)

    assignments = build_rater_assignments(
        label_frames,
        rater_ids=rater_ids,
        seed=config.seed,
    )
    assignments.to_csv(root / "rater_assignments.csv", index=False)
    for rater_id, group in assignments.groupby("annotator_id", sort=True):
        safe_rater = _slug(str(rater_id))
        group.to_csv(root / f"assignment_{safe_rater}.csv", index=False)

    outcomes = (
        assignments[
            [
                "sequence_id",
                "frame_id",
                "timestamp_s",
                "source_provider",
                "source_match_id",
            ]
        ]
        .drop_duplicates(["sequence_id", "frame_id"])
        .sort_values(["sequence_id", "frame_id"])
    )
    outcomes["selected_option_id"] = ""
    outcomes["selection_evidence_source"] = ""
    outcomes["selection_note"] = ""
    outcomes.to_csv(root / "selection_outcomes_template.csv", index=False)

    candidate_freeze_path = root / "pilot_candidates_freeze.json"
    freeze_pilot(
        frames_path=label_frames_path,
        candidates_path=candidates_path,
        annotation_paths=[],
        protocol_path=protocol_path,
        output_path=candidate_freeze_path,
    )

    reviewer = (reviewed_by or "").strip() or None
    stage = "sample_frozen" if reviewer else "needs_sequence_review"
    payload = {
        "schema_version": R1_SCHEMA_VERSION,
        "stage": stage,
        "claim_state": "sampling_and_annotation_protocol_only_no_empirical_model_claim",
        "reviewed_by": reviewer,
        "config": {
            **asdict(config),
            "target_composition": config.composition(),
        },
        "source": {
            "frames_path": str(frames_path),
            "frames_sha256": sha256_file(frames_path),
            "providers": sorted({frame.source_provider for frame in label_frames}),
            "matches": sorted(
                {
                    frame.source_match_id
                    or frame.metadata.get("r1_source_sequence_id", "")
                    for frame in label_frames
                }
            ),
        },
        "sample": {
            "eligible_windows": len(windows),
            "selected_sequences": len(selected_windows),
            "label_frames": len(label_frames),
            "context_frames": len(context_frames),
            "candidates": len(candidates),
            "composition": {
                str(key): int(value)
                for key, value in proposal["sampling_stratum"]
                .value_counts()
                .sort_index()
                .items()
            },
            "source_frame_overlap": False,
            "sampling_label_status": "heuristic_for_diversity_not_ground_truth",
        },
        "annotation": {
            "rater_ids": sorted(set(str(value).strip() for value in rater_ids)),
            "full_double_rating": config.require_full_double_rating,
            "outcome_blinded": True,
            "model_score_blinded": True,
            "causal_history_only": True,
        },
        "paths": {
            "label_frames": str(label_frames_path),
            "causal_context_frames": str(context_frames_path),
            "candidates": str(candidates_path),
            "blinded_candidates": str(root / "pilot_candidates_blinded.csv"),
            "candidate_freeze": str(candidate_freeze_path),
            "inventory": str(root / "sequence_inventory.csv"),
            "sample_plan": str(root / "sample_plan.csv"),
            "assignments": str(root / "rater_assignments.csv"),
            "selection_template": str(root / "selection_outcomes_template.csv"),
        },
        "advancement_gate": {
            "minimum_availability_alpha": 0.60,
            "requires_established_reliability": True,
            "requires_frozen_consensus": True,
            "requires_B2_vs_B1_result": True,
            "requires_sequence_bootstrap": True,
            "requires_provider_quality_review": True,
        },
    }
    return _write_json(root / "r1_manifest.json", payload)


def _read_metrics_summary(metrics_path: Path) -> dict[str, Any]:
    metrics = pd.read_csv(metrics_path)
    if metrics.empty:
        return {}
    aggregate = metrics[
        metrics.get("scope", pd.Series("", index=metrics.index)) == "aggregate"
    ]
    if aggregate.empty:
        return {}
    preferred = aggregate[
        aggregate["evaluation_protocol"].astype(str).eq("sequence_grouped")
    ]
    if preferred.empty:
        preferred = aggregate
    rows: dict[str, Any] = {}
    for _, row in preferred.iterrows():
        model = str(row.get("model", "unknown"))
        rows[model] = {
            key: None if pd.isna(row.get(key)) else float(row.get(key))
            for key in (
                "ndcg@3",
                "recall@3",
                "pairwise",
                "top_3_jaccard_stability",
            )
            if key in row.index
        }
    return rows


def build_r1_status(
    r1_dir: str | Path,
    *,
    annotation_paths: Sequence[str | Path] | None = None,
    bootstrap_iterations: int = 250,
    seed: int = 17,
) -> dict[str, Any]:
    root = Path(r1_dir)
    manifest_path = root / "r1_manifest.json"
    if not manifest_path.exists():
        return protocol_ready_showcase_payload()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates_path = Path(manifest["paths"]["candidates"])
    if not candidates_path.exists():
        candidates_path = root / "pilot_candidates.csv"
    candidates = pd.read_csv(candidates_path)

    resolved_annotations = [Path(path) for path in (annotation_paths or [])]
    if not resolved_annotations:
        annotation_dir = root / "annotations"
        if annotation_dir.exists():
            resolved_annotations = sorted(annotation_dir.glob("*.csv"))

    status = str(manifest.get("stage", "sample_frozen"))
    reliability: dict[str, Any] | None = None
    annotation_progress: dict[str, Any] = {
        "files": len(resolved_annotations),
        "candidate_coverage": 0.0,
        "annotators": 0,
        "rows": 0,
    }
    if resolved_annotations:
        imported = load_annotations(
            resolved_annotations,
            candidates=candidates,
            require_genuine_human=False,
        )
        annotation_progress = {
            "files": len(resolved_annotations),
            "candidate_coverage": imported.report.candidate_coverage,
            "annotators": imported.report.annotators,
            "rows": imported.report.rows,
            "genuine_human_rows": imported.report.genuine_human_rows,
        }
        gate = ReliabilityGate(
            min_genuine_raters=2,
            min_sequences=manifest["config"]["target_sequences"],
            min_overlap_frame_fraction=(
                1.0 if manifest["config"]["require_full_double_rating"] else 0.25
            ),
            min_overlap_items=20,
            min_availability_alpha=0.60,
            min_candidate_coverage=1.0,
        )
        reliability = reliability_report(
            imported.dataframe,
            candidates=candidates,
            gate=gate,
            bootstrap_iterations=bootstrap_iterations,
            seed=seed,
        )
        status = (
            "reliability_established"
            if reliability["established"]
            else "annotation_in_progress"
        )

    benchmark_dir = root / "benchmark"
    benchmark_manifest = benchmark_dir / "benchmark_manifest.json"
    metrics_path = benchmark_dir / "metrics.csv"
    metrics: dict[str, Any] = {}
    if benchmark_manifest.exists() and metrics_path.exists():
        metrics = _read_metrics_summary(metrics_path)
        status = "benchmark_complete"

    return {
        "schema_version": R1_SHOWCASE_SCHEMA_VERSION,
        "stage": status,
        "title": "R1 · Real Action Menu Pilot",
        "question": (
            "Does dynamic geometry rank expert-labeled options better than static geometry "
            "on independent possession sequences?"
        ),
        "claim_state": (
            "empirical_benchmark_complete"
            if status == "benchmark_complete"
            else "no_empirical_model_claim_yet"
        ),
        "sample": manifest.get("sample", {}),
        "annotation": {
            **manifest.get("annotation", {}),
            "progress": annotation_progress,
        },
        "reliability": reliability,
        "benchmark": {
            "complete": status == "benchmark_complete",
            "metrics": metrics,
        },
        "evidence_ladder": [
            {
                "id": "protocol",
                "label": "Protocol",
                "complete": True,
                "detail": "Targets and leakage rules frozen.",
            },
            {
                "id": "sample",
                "label": "10-sequence sample",
                "complete": status not in {"protocol_ready", "needs_sequence_review"},
                "detail": (
                    "Non-overlapping receipt/control windows with reviewable diversity strata."
                ),
            },
            {
                "id": "annotation",
                "label": "Double annotation",
                "complete": bool(
                    annotation_progress.get("candidate_coverage") == 1.0
                    and annotation_progress.get("annotators", 0) >= 2
                ),
                "detail": (
                    "Outcome-blind, model-score-blind, causal-history-only expert ratings."
                ),
            },
            {
                "id": "reliability",
                "label": "Reliability gate",
                "complete": bool(reliability and reliability.get("established")),
                "detail": (
                    "Availability Krippendorff α ≥ 0.60 plus full candidate coverage."
                ),
            },
            {
                "id": "benchmark",
                "label": "B0 → B3 benchmark",
                "complete": status == "benchmark_complete",
                "detail": (
                    "Sequence-held-out ranking, bootstrap intervals, and retained null results."
                ),
            },
        ],
        "guardrails": [
            "Sampling strata are diversity heuristics, not tactical ground truth.",
            "Selected actions are joined only after blinded ratings.",
            "Context frames are view-only; focal model features remain causal.",
            "No temporal graph or video model advances before the R1 gate is satisfied.",
        ],
    }


def protocol_ready_showcase_payload() -> dict[str, Any]:
    config = R1PilotConfig()
    return {
        "schema_version": R1_SHOWCASE_SCHEMA_VERSION,
        "stage": "protocol_ready",
        "title": "R1 · Real Action Menu Pilot",
        "question": (
            "Does dynamic geometry rank expert-labeled options better than static geometry "
            "on independent possession sequences?"
        ),
        "claim_state": "no_empirical_model_claim_yet",
        "sample": {
            "selected_sequences": 0,
            "target_sequences": config.target_sequences,
            "composition": config.composition(),
            "sampling_label_status": "heuristic_for_diversity_not_ground_truth",
        },
        "annotation": {
            "rater_ids": [],
            "full_double_rating": True,
            "outcome_blinded": True,
            "model_score_blinded": True,
            "causal_history_only": True,
            "progress": {
                "files": 0,
                "candidate_coverage": 0.0,
                "annotators": 0,
                "rows": 0,
            },
        },
        "reliability": None,
        "benchmark": {"complete": False, "metrics": {}},
        "evidence_ladder": [
            {
                "id": "protocol",
                "label": "Protocol",
                "complete": True,
                "detail": "Targets and leakage rules frozen.",
            },
            {
                "id": "sample",
                "label": "10-sequence sample",
                "complete": False,
                "detail": "Awaiting reviewed real tracking windows.",
            },
            {
                "id": "annotation",
                "label": "Double annotation",
                "complete": False,
                "detail": "Awaiting two genuine expert raters.",
            },
            {
                "id": "reliability",
                "label": "Reliability gate",
                "complete": False,
                "detail": "Availability Krippendorff α ≥ 0.60 required.",
            },
            {
                "id": "benchmark",
                "label": "B0 → B3 benchmark",
                "complete": False,
                "detail": "No benchmark claim until expert reliability is established.",
            },
        ],
        "guardrails": [
            "No synthetic metric is substituted for missing expert evidence.",
            "Selected action is not treated as the complete action menu.",
            "Future observed frames are excluded from causal focal-frame features.",
            "R1 is a pilot: effect sizes and failure modes matter more than p-values.",
        ],
    }


def write_r1_showcase(
    output_path: str | Path,
    *,
    r1_dir: str | Path | None = None,
    annotation_paths: Sequence[str | Path] | None = None,
) -> Path:
    payload = (
        protocol_ready_showcase_payload()
        if r1_dir is None
        else build_r1_status(r1_dir, annotation_paths=annotation_paths)
    )
    return _write_json(Path(output_path), payload)
