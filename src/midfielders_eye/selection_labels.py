from __future__ import annotations

from typing import Any

import pandas as pd

from .action_menu import annotation_contract_summary, validate_annotation_dataframe

FRAME_COLUMNS = ["sequence_id", "frame_id"]


def join_selected_outcomes(
    annotations: pd.DataFrame,
    selections: pd.DataFrame,
    *,
    require_complete_frames: bool = True,
) -> pd.DataFrame:
    """Join one post-hoc selected option per frame onto blinded expert ratings.

    ``selections`` must contain ``sequence_id``, ``frame_id``, and
    ``selected_option_key``. The selected key may be null when no candidate in
    the annotated menu corresponds to the observed action.
    """

    validate_annotation_dataframe(annotations)
    summary = annotation_contract_summary(annotations)
    if summary["outcome_blinded_fraction"] != 1.0:
        raise ValueError(
            "Publication selection join requires every source rating to be outcome-blinded"
        )

    required = {*FRAME_COLUMNS, "selected_option_key"}
    missing = sorted(required - set(selections.columns))
    if missing:
        raise ValueError(f"selection table missing columns: {', '.join(missing)}")
    if selections.duplicated(FRAME_COLUMNS).any():
        raise ValueError("selection table must contain at most one row per decision frame")

    annotation_frames = annotations[FRAME_COLUMNS].drop_duplicates().copy()
    selection_frames = selections[FRAME_COLUMNS].drop_duplicates().copy()
    merged_frames = annotation_frames.merge(
        selection_frames,
        on=FRAME_COLUMNS,
        how="left",
        indicator=True,
    )
    missing_frames = merged_frames[merged_frames["_merge"] == "left_only"]
    if require_complete_frames and not missing_frames.empty:
        examples = missing_frames[FRAME_COLUMNS].head(5).to_dict(orient="records")
        raise ValueError(
            "selection table does not cover every annotated decision frame: "
            f"{examples}"
        )

    extras = selection_frames.merge(
        annotation_frames,
        on=FRAME_COLUMNS,
        how="left",
        indicator=True,
    )
    extra_frames = extras[extras["_merge"] == "left_only"]
    if not extra_frames.empty:
        examples = extra_frames[FRAME_COLUMNS].head(5).to_dict(orient="records")
        raise ValueError(
            "selection table contains frames absent from annotations: "
            f"{examples}"
        )

    candidate_keys = annotations[[*FRAME_COLUMNS, "option_key"]].drop_duplicates()
    for selection in selections.to_dict(orient="records"):
        selected_key = selection.get("selected_option_key")
        if pd.isna(selected_key) or str(selected_key).strip() == "":
            continue
        frame_mask = (
            (candidate_keys["sequence_id"].astype(str) == str(selection["sequence_id"]))
            & (candidate_keys["frame_id"] == selection["frame_id"])
        )
        allowed = set(candidate_keys.loc[frame_mask, "option_key"].astype(str))
        if str(selected_key) not in allowed:
            raise ValueError(
                "selected_option_key is not an annotated candidate for frame "
                f"{selection['sequence_id']}:{selection['frame_id']}: {selected_key!r}"
            )

    selection_columns = [*FRAME_COLUMNS, "selected_option_key"]
    if "selection_provenance" in selections.columns:
        selection_columns.append("selection_provenance")
    selection_payload = selections[selection_columns].copy()
    selection_payload["selection_record_present"] = True
    joined = annotations.copy().merge(
        selection_payload,
        on=FRAME_COLUMNS,
        how="left",
        validate="many_to_one",
    )
    record_present = joined["selection_record_present"].fillna(False).astype(bool)
    selected_key = joined["selected_option_key"]
    has_observed_candidate = (
        record_present
        & selected_key.notna()
        & selected_key.astype(str).str.strip().ne("")
    )
    joined["selected"] = has_observed_candidate & (
        joined["option_key"].astype(str) == selected_key.astype(str)
    )
    joined["label_selected"] = joined["selected"]
    joined["selection_join_status"] = "selection_record_missing"
    joined.loc[
        record_present & ~has_observed_candidate,
        "selection_join_status",
    ] = "no_candidate_selected"
    joined.loc[
        has_observed_candidate,
        "selection_join_status",
    ] = "observed_candidate_selected"
    return joined


def selection_join_summary(dataframe: pd.DataFrame) -> dict[str, Any]:
    required = {*FRAME_COLUMNS, "option_key", "selected", "selection_join_status"}
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"joined selection dataframe missing columns: {missing}")
    frame_groups = dataframe.groupby(FRAME_COLUMNS, sort=False)
    selected_counts = frame_groups["selected"].sum()
    if (selected_counts > 1).any():
        raise ValueError(
            "joined selection output has more than one selected candidate in a frame"
        )
    frame_status = frame_groups["selection_join_status"].first()
    missing_records = frame_status.eq("selection_record_missing")
    valid_frames = ~missing_records
    selected_valid = (selected_counts == 1) & valid_frames
    no_candidate_valid = (selected_counts == 0) & valid_frames
    return {
        "schema_version": "action-menu-selection-join-v1",
        "frames": int(len(selected_counts)),
        "frames_with_selection_record": int(valid_frames.sum()),
        "frames_missing_selection_record": int(missing_records.sum()),
        "frames_with_selected_candidate": int(selected_valid.sum()),
        "frames_without_selected_candidate": int(no_candidate_valid.sum()),
        "selected_candidate_rate": (
            float(selected_valid.sum() / valid_frames.sum())
            if valid_frames.any()
            else 0.0
        ),
    }
