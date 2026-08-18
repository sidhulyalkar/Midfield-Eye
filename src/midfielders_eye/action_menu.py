from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Literal, Mapping

import pandas as pd

from .schema import ActionOption

TriStateLabel = Literal["yes", "no", "uncertain"]


@dataclass(frozen=True, slots=True)
class ActionMenuAnnotation:
    """Outcome-blind annotation record for one candidate action.

    The five research targets deliberately remain separate. ``selected`` is an
    observed event label; it must not be used as a proxy for availability,
    visibility, value, or creation.
    """

    sequence_id: str
    frame_id: int
    option_key: str
    annotator_id: str
    available: TriStateLabel
    visible: TriStateLabel
    value_ordinal: int
    creation_ordinal: int
    selected: bool | None = None
    confidence: float = 1.0
    blinded_to_outcome: bool = True
    notes: str = ""
    provenance: str = "human-annotation-action-menu-v1"

    def __post_init__(self) -> None:
        if not self.sequence_id:
            raise ValueError("sequence_id must be non-empty")
        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")
        if not self.option_key:
            raise ValueError("option_key must be non-empty")
        if not self.annotator_id:
            raise ValueError("annotator_id must be non-empty")
        if self.available not in {"yes", "no", "uncertain"}:
            raise ValueError("available must be yes, no, or uncertain")
        if self.visible not in {"yes", "no", "uncertain"}:
            raise ValueError("visible must be yes, no, or uncertain")
        if not 0 <= self.value_ordinal <= 4:
            raise ValueError("value_ordinal must be in [0, 4]")
        if not 0 <= self.creation_ordinal <= 4:
            raise ValueError("creation_ordinal must be in [0, 4]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stable_option_key(option: ActionOption | Mapping[str, Any]) -> str:
    """Return an option identity that is stable across frames.

    Current affordance ``option_id`` values intentionally contain frame IDs.
    Longitudinal analysis instead keys passes by receiver, carries by their
    configured angle bucket, and hold as one persistent action.
    """

    if isinstance(option, ActionOption):
        kind = option.kind
        target_player_id = option.target_player_id
        option_id = option.option_id
    else:
        kind = str(option.get("kind", ""))
        target_player_id = option.get("target_player_id")
        option_id = str(option.get("option_id", ""))

    if kind == "pass":
        if target_player_id is None or str(target_player_id).strip() in {"", "nan", "None"}:
            raise ValueError("pass option requires target_player_id for stable identity")
        return f"pass:{target_player_id}"
    if kind == "carry":
        marker = ":carry:"
        if marker not in option_id:
            raise ValueError("carry option_id must contain ':carry:' for stable identity")
        return f"carry:{option_id.rsplit(marker, 1)[1]}"
    if kind == "hold":
        return "hold"
    raise ValueError(f"unsupported action kind {kind!r}")


def _prepare_candidates(
    dataframe: pd.DataFrame,
    *,
    score_column: str = "geometric_score",
) -> pd.DataFrame:
    required = {
        "sequence_id",
        "frame_id",
        "option_id",
        "kind",
        "target_player_id",
        score_column,
    }
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"candidate dataframe missing columns: {', '.join(missing)}")

    prepared = dataframe.copy()
    prepared["stable_option_key"] = [
        stable_option_key(row) for row in prepared.to_dict(orient="records")
    ]
    prepared[score_column] = pd.to_numeric(prepared[score_column], errors="raise")
    prepared["frame_id"] = pd.to_numeric(prepared["frame_id"], errors="raise").astype(int)

    duplicate = prepared.duplicated(
        subset=["sequence_id", "frame_id", "stable_option_key"], keep=False
    )
    if duplicate.any():
        examples = prepared.loc[
            duplicate, ["sequence_id", "frame_id", "stable_option_key"]
        ].head(5)
        raise ValueError(
            "candidate dataframe has duplicate stable options within a frame: "
            + examples.to_dict(orient="records").__repr__()
        )
    return prepared


def build_action_menu_tables(
    dataframe: pd.DataFrame,
    *,
    score_column: str = "geometric_score",
    selection_column: str = "label_selected",
    top_k: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build lifecycle and frame-level action-menu tables from candidate rows.

    This is descriptive, causal-safe bookkeeping. It never looks ahead to
    construct features or scores; future frames are used only to summarize an
    option's *retrospective* lifespan for visualization and analysis.
    """

    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    prepared = _prepare_candidates(dataframe, score_column=score_column)
    if prepared.empty:
        empty_lifecycle = pd.DataFrame(
            columns=[
                "sequence_id",
                "stable_option_key",
                "kind",
                "target_player_id",
                "birth_frame_id",
                "death_frame_id",
                "frames_seen",
                "peak_score",
                "mean_score",
                "selected_frames",
            ]
        )
        empty_timeline = pd.DataFrame(
            columns=[
                "sequence_id",
                "frame_id",
                "menu_breadth",
                "top_option_key",
                "top_option_score",
                "top_keys",
                "births",
                "extinctions",
                "top_k_jaccard_previous",
            ]
        )
        return empty_lifecycle, empty_timeline, {
            "schema_version": "action-menu-report-v1",
            "sequence_count": 0,
            "frame_count": 0,
            "candidate_count": 0,
            "stable_option_count": 0,
            "score_column": score_column,
            "top_k": top_k,
        }

    lifecycle_rows: list[dict[str, Any]] = []
    for (sequence_id, key), group in prepared.groupby(
        ["sequence_id", "stable_option_key"], sort=True
    ):
        ordered = group.sort_values("frame_id")
        selected_frames: list[int] = []
        if selection_column in ordered.columns:
            selected_mask = ordered[selection_column].fillna(False).astype(bool)
            selected_frames = ordered.loc[selected_mask, "frame_id"].astype(int).tolist()
        first = ordered.iloc[0]
        lifecycle_rows.append(
            {
                "sequence_id": sequence_id,
                "stable_option_key": key,
                "kind": first["kind"],
                "target_player_id": first.get("target_player_id"),
                "birth_frame_id": int(ordered["frame_id"].min()),
                "death_frame_id": int(ordered["frame_id"].max()),
                "frames_seen": int(ordered["frame_id"].nunique()),
                "peak_score": float(ordered[score_column].max()),
                "mean_score": float(ordered[score_column].mean()),
                "selected_frames": ";".join(str(frame) for frame in selected_frames),
            }
        )

    timeline_rows: list[dict[str, Any]] = []
    for sequence_id, sequence in prepared.groupby("sequence_id", sort=True):
        previous_keys: set[str] = set()
        previous_top: set[str] = set()
        for frame_id, frame in sequence.groupby("frame_id", sort=True):
            ranked = frame.sort_values(score_column, ascending=False)
            keys = set(frame["stable_option_key"].astype(str))
            top_keys = ranked["stable_option_key"].astype(str).head(top_k).tolist()
            top_set = set(top_keys)
            union = previous_top | top_set
            jaccard = None if not previous_top else len(previous_top & top_set) / max(len(union), 1)
            top = ranked.iloc[0]
            timeline_rows.append(
                {
                    "sequence_id": sequence_id,
                    "frame_id": int(frame_id),
                    "menu_breadth": int(len(frame)),
                    "top_option_key": str(top["stable_option_key"]),
                    "top_option_score": float(top[score_column]),
                    "top_keys": ";".join(top_keys),
                    "births": ";".join(sorted(keys - previous_keys)),
                    "extinctions": ";".join(sorted(previous_keys - keys)),
                    "top_k_jaccard_previous": jaccard,
                }
            )
            previous_keys = keys
            previous_top = top_set

    lifecycles = pd.DataFrame(lifecycle_rows).sort_values(
        ["sequence_id", "birth_frame_id", "stable_option_key"]
    )
    timeline = pd.DataFrame(timeline_rows).sort_values(["sequence_id", "frame_id"])
    summary = {
        "schema_version": "action-menu-report-v1",
        "sequence_count": int(prepared["sequence_id"].nunique()),
        "frame_count": int(prepared[["sequence_id", "frame_id"]].drop_duplicates().shape[0]),
        "candidate_count": int(len(prepared)),
        "stable_option_count": int(
            prepared[["sequence_id", "stable_option_key"]].drop_duplicates().shape[0]
        ),
        "score_column": score_column,
        "top_k": top_k,
        "retrospective_lifecycle_warning": (
            "Birth/death summaries use later frames only for retrospective visualization; "
            "they are not causal model inputs."
        ),
    }
    return lifecycles.reset_index(drop=True), timeline.reset_index(drop=True), summary


def annotations_to_dataframe(
    annotations: Iterable[ActionMenuAnnotation],
) -> pd.DataFrame:
    rows = [annotation.to_dict() for annotation in annotations]
    return pd.DataFrame(rows)


def validate_annotation_dataframe(dataframe: pd.DataFrame) -> None:
    required = {
        "sequence_id",
        "frame_id",
        "option_key",
        "annotator_id",
        "available",
        "visible",
        "value_ordinal",
        "creation_ordinal",
        "confidence",
        "blinded_to_outcome",
    }
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"annotation dataframe missing columns: {', '.join(missing)}")
    if dataframe.duplicated(
        subset=["sequence_id", "frame_id", "option_key", "annotator_id"]
    ).any():
        raise ValueError("annotation dataframe contains duplicate annotator-option rows")
    allowed = {"yes", "no", "uncertain"}
    for column in ("available", "visible"):
        values = set(dataframe[column].dropna().astype(str))
        if not values <= allowed:
            raise ValueError(f"{column} contains unsupported labels: {sorted(values - allowed)}")
    for column in ("value_ordinal", "creation_ordinal"):
        numeric = pd.to_numeric(dataframe[column], errors="raise")
        if not numeric.between(0, 4).all():
            raise ValueError(f"{column} must be in [0, 4]")
    confidence = pd.to_numeric(dataframe["confidence"], errors="raise")
    if not confidence.between(0, 1).all():
        raise ValueError("confidence must be in [0, 1]")


def annotation_contract_summary(dataframe: pd.DataFrame) -> dict[str, Any]:
    validate_annotation_dataframe(dataframe)
    keys = ["sequence_id", "frame_id", "option_key"]
    counts = dataframe.groupby(keys)["annotator_id"].nunique()
    return {
        "schema_version": "action-menu-annotation-v1",
        "annotation_rows": int(len(dataframe)),
        "decision_items": int(len(counts)),
        "sequence_count": int(dataframe["sequence_id"].nunique()),
        "annotator_count": int(dataframe["annotator_id"].nunique()),
        "double_rated_fraction": float((counts >= 2).mean()) if len(counts) else 0.0,
        "outcome_blinded_fraction": float(dataframe["blinded_to_outcome"].astype(bool).mean()),
        "uncertain_availability_fraction": float((dataframe["available"] == "uncertain").mean()),
        "uncertain_visibility_fraction": float((dataframe["visible"] == "uncertain").mean()),
    }
