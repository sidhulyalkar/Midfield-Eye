from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .action_menu import stable_option_key
from .affordance import AffordanceEngine
from .io import read_frames_jsonl
from .schema import FrameState
from .visualization import plot_affordance_frame, plot_annotation_frame

AVAILABILITY_OPTIONS = ["uncertain", "yes", "no"]
VISIBILITY_OPTIONS = ["uncertain", "yes", "no"]
FAILURE_REASONS = [
    "none",
    "corridor",
    "interception",
    "body_shape",
    "receiver_pressure",
    "offside",
    "view",
    "execution_difficulty",
    "other",
]
ASSIGNMENT_COLUMNS = {
    "annotator_id",
    "display_order",
    "sequence_id",
    "frame_id",
    "outcome_blinded",
    "model_score_blinded",
}


def _neutral_option_order(options):
    return sorted(
        options,
        key=lambda option: (
            option.kind,
            str(option.target_player_id or ""),
            round(option.target_x, 3),
            round(option.target_y, 3),
            option.option_id,
        ),
    )


def load_assignment_plan(
    path: str | Path,
    *,
    frames: list[FrameState],
    annotator_id: str,
) -> pd.DataFrame:
    """Validate and return one expert's blinded R1 assignment in display order."""

    assignments = pd.read_csv(path)
    missing = sorted(ASSIGNMENT_COLUMNS - set(assignments.columns))
    if missing:
        raise ValueError(f"R1 assignment file is missing columns: {missing}")
    if assignments.empty:
        raise ValueError("R1 assignment file is empty")
    if assignments.duplicated(["annotator_id", "sequence_id", "frame_id"]).any():
        raise ValueError("R1 assignment file contains duplicate annotator/frame rows")
    if assignments["display_order"].isna().any():
        raise ValueError("R1 assignment display_order cannot be missing")
    if not assignments["outcome_blinded"].astype(bool).all():
        raise ValueError("R1 publication assignments must be outcome blinded")
    if not assignments["model_score_blinded"].astype(bool).all():
        raise ValueError("R1 publication assignments must be model-score blinded")

    normalized_id = str(annotator_id).strip()
    selected = assignments[
        assignments["annotator_id"].astype(str).str.strip() == normalized_id
    ].copy()
    if selected.empty:
        known = sorted(assignments["annotator_id"].astype(str).unique())
        raise ValueError(
            f"Annotator {normalized_id!r} has no R1 assignment; known IDs: {known}"
        )

    valid_keys = {(str(frame.sequence_id), int(frame.frame_id)) for frame in frames}
    assigned_keys = {
        (str(row.sequence_id), int(row.frame_id))
        for row in selected.itertuples(index=False)
    }
    unknown = sorted(assigned_keys - valid_keys)
    if unknown:
        raise ValueError(
            "R1 assignment references focal frames absent from the annotation frame file: "
            f"{unknown[:5]}"
        )
    selected["display_order"] = pd.to_numeric(
        selected["display_order"], errors="raise"
    ).astype(int)
    selected = selected.sort_values(
        ["display_order", "sequence_id", "frame_id"],
        ignore_index=True,
    )
    if selected["display_order"].duplicated().any():
        raise ValueError("R1 display_order must be unique within each annotator")
    return selected


def causal_history_for_frame(
    context_frames: list[FrameState],
    focal_frame: FrameState,
    *,
    maximum_frames: int = 3,
) -> list[FrameState]:
    """Return only earlier frames from the same R1 sequence."""

    if maximum_frames < 1:
        return []
    eligible = [
        frame
        for frame in context_frames
        if frame.sequence_id == focal_frame.sequence_id
        and frame.timestamp_s < focal_frame.timestamp_s - 1e-9
    ]
    eligible.sort(key=lambda frame: (frame.timestamp_s, frame.frame_id))
    return eligible[-maximum_frames:]


def _frame_lookup(frames: list[FrameState]) -> dict[tuple[str, int], FrameState]:
    lookup: dict[tuple[str, int], FrameState] = {}
    for frame in frames:
        key = (str(frame.sequence_id), int(frame.frame_id))
        if key in lookup:
            raise ValueError(f"Duplicate annotation frame key: {key}")
        lookup[key] = frame
    return lookup


def run(
    frame_path: str,
    annotation_path: str,
    *,
    outcome_blinded: bool = True,
    model_score_blinded: bool = True,
    context_frame_path: str | None = None,
    assignment_path: str | None = None,
    annotator_id_default: str = "annotator_01",
    lock_annotator_id: bool = False,
) -> None:
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install the annotation extra: pip install -e '.[annotation]'"
        ) from exc

    frames = read_frames_jsonl(frame_path)
    if not frames:
        raise ValueError("Annotation frame file is empty")
    frame_by_key = _frame_lookup(frames)
    context_frames = (
        read_frames_jsonl(context_frame_path)
        if context_frame_path is not None
        else frames
    )
    engine = AffordanceEngine()
    st.set_page_config(
        page_title="The Midfielder's Eye Action Menu Annotator",
        layout="wide",
    )
    st.title("The Midfielder's Eye · Action Menu Annotator")
    st.caption(
        "Rate availability, perceptual access, value, and creation separately. "
        "The publication protocol hides selected outcomes and model scores by default."
    )

    assignment: pd.DataFrame | None = None
    with st.sidebar:
        annotator_id = st.text_input(
            "Annotator ID",
            value=annotator_id_default,
            disabled=lock_annotator_id,
        )
        if assignment_path is not None:
            try:
                assignment = load_assignment_plan(
                    assignment_path,
                    frames=frames,
                    annotator_id=annotator_id,
                )
            except ValueError as exc:
                st.error(str(exc))
                st.stop()
            position = st.slider(
                "Assigned decision frame",
                0,
                len(assignment) - 1,
                0,
            )
            assigned = assignment.iloc[position]
            frame = frame_by_key[
                (str(assigned["sequence_id"]), int(assigned["frame_id"]))
            ]
            st.write(f"Assignment: `{position + 1}/{len(assignment)}`")
            st.write(f"Sequence: `{frame.sequence_id}`")
        else:
            sequence_ids = sorted({frame.sequence_id for frame in frames})
            sequence_id = st.selectbox("Sequence", sequence_ids)
            sequence_frames = [
                frame for frame in frames if frame.sequence_id == sequence_id
            ]
            sequence_frames.sort(key=lambda item: (item.timestamp_s, item.frame_id))
            index = st.slider(
                "Frame within sequence",
                0,
                len(sequence_frames) - 1,
                0,
            )
            frame = sequence_frames[index]
        st.write(f"Provider: `{frame.source_provider}`")
        st.write(f"Quality flags: {', '.join(frame.quality_flags) or 'none'}")
        st.divider()
        st.write(
            "Outcome status: "
            + ("`BLINDED`" if outcome_blinded else "`UNBLINDED EXPLORATORY`")
        )
        st.write(
            "Model score status: "
            + ("`BLINDED`" if model_score_blinded else "`VISIBLE EXPLORATORY`")
        )
        if assignment_path is not None:
            st.success("R1 assignment mode · randomized order · full double rating")
        if not outcome_blinded or not model_score_blinded:
            st.warning(
                "Exploratory unblinded annotations must not be mixed into the "
                "publication reliability or benchmark freeze."
            )

    generated_options = engine.generate(frame)
    options = (
        _neutral_option_order(generated_options)
        if model_score_blinded
        else sorted(
            generated_options,
            key=lambda item: item.geometric_score,
            reverse=True,
        )
    )

    history_frames = causal_history_for_frame(context_frames, frame, maximum_frames=3)
    with st.expander(
        "Causal history for creation labels",
        expanded=False,
    ):
        st.caption(
            "Only earlier frames from the same frozen R1 sequence are shown. Context is "
            "view-only: it is not part of the focal candidate table or benchmark feature matrix."
        )
        if not history_frames:
            st.info("No earlier causal context is available inside this sequence.")
        else:
            history_columns = st.columns(len(history_frames))
            for history_column, history_frame in zip(
                history_columns,
                history_frames,
                strict=True,
            ):
                history_options = _neutral_option_order(engine.generate(history_frame))
                history_figure, _ = plot_annotation_frame(
                    history_frame,
                    history_options,
                )
                history_column.pyplot(
                    history_figure,
                    use_container_width=True,
                )
                history_column.caption(
                    f"t={history_frame.timestamp_s:.2f}s · frame {history_frame.frame_id}"
                )

    if model_score_blinded:
        figure, _ = plot_annotation_frame(frame, options)
    else:
        figure, _ = plot_affordance_frame(
            frame,
            options,
            top_k=min(8, len(options)),
        )
    st.pyplot(figure, use_container_width=True)
    st.caption(
        "Candidate labels A01, A02, … match the panels below. Neutral mode does "
        "not display model rank or score. Body axes are state evidence, not literal gaze."
    )

    rows: list[dict[str, Any]] = []
    for option_index, option in enumerate(options, start=1):
        target = option.target_player_id or (
            f"({option.target_x:.1f}, {option.target_y:.1f})"
        )
        with st.expander(
            f"A{option_index:02d} · {option.kind} → {target}",
            expanded=option_index <= 3,
        ):
            column_a, column_b, column_c, column_d = st.columns(4)
            key = option.option_id.replace(":", "_")
            availability = column_a.selectbox(
                "Available?",
                AVAILABILITY_OPTIONS,
                index=0,
                key=f"available_{key}",
            )
            visibility = column_b.selectbox(
                "Perceptually accessible?",
                VISIBILITY_OPTIONS,
                index=0,
                key=f"visibility_{key}",
                help=(
                    "Use uncertain when the source cannot support a player-view judgment. "
                    "Do not infer literal gaze from movement direction alone."
                ),
            )
            ordinal_value = column_c.slider(
                "Tactical value (0–4)",
                0,
                4,
                2,
                key=f"value_{key}",
            )
            creation_ordinal = column_d.slider(
                "Created by earlier movement (0–4)",
                0,
                4,
                2,
                key=f"creation_{key}",
                help=(
                    "Rate how much earlier movement improved this option relative to its "
                    "recent baseline. Use only the causal history shown above."
                ),
            )
            confidence = column_a.slider(
                "Label confidence",
                0.0,
                1.0,
                0.5,
                0.05,
                key=f"confidence_{key}",
            )
            failure_reason = column_b.selectbox(
                "Primary failure reason",
                FAILURE_REASONS,
                key=f"failure_{key}",
            )
            selected: bool | None = None
            if not outcome_blinded:
                selected = column_c.checkbox(
                    "Selected action · exploratory only",
                    key=f"selected_{key}",
                )
            tactical_note = st.text_input(
                "Tactical note",
                key=f"note_{key}",
            )

        option_key = stable_option_key(option)
        rows.append(
            {
                **option.to_flat_dict(),
                "option_key": option_key,
                "available": availability,
                "visible": visibility,
                "value_ordinal": ordinal_value,
                "creation_ordinal": creation_ordinal,
                "selected": selected,
                "confidence": confidence,
                "blinded_to_outcome": outcome_blinded,
                "model_score_blinded": model_score_blinded,
                "notes": tactical_note,
                "label_available": availability,
                "label_value": ordinal_value / 4.0,
                "label_value_ordinal": ordinal_value,
                "label_selected": selected,
                "label_visibility": visibility,
                "label_confidence": confidence,
                "label_creation": creation_ordinal / 4.0,
                "label_creation_ordinal": creation_ordinal,
                "label_failure_reason": (
                    None if failure_reason == "none" else failure_reason
                ),
                "annotator_id": annotator_id,
                "tactical_note": tactical_note,
                "provenance": "human-annotation-action-menu-v1",
            }
        )

    if st.button("Save this frame", type="primary"):
        if not annotator_id.strip():
            st.error("Annotator ID is required before saving.")
            return
        output = Path(annotation_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        existing = pd.read_csv(output) if output.exists() else pd.DataFrame()
        current = pd.DataFrame(rows)
        if not existing.empty:
            mask = ~(
                (existing["sequence_id"].astype(str) == str(frame.sequence_id))
                & (existing["frame_id"] == frame.frame_id)
                & (
                    existing.get(
                        "annotator_id",
                        pd.Series("", index=existing.index),
                    ).astype(str)
                    == annotator_id
                )
            )
            existing = existing[mask]
        pd.concat([existing, current], ignore_index=True).to_csv(
            output,
            index=False,
        )
        st.success(f"Saved {len(rows)} candidate ratings to {output}")


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", required=True)
    parser.add_argument(
        "--annotations",
        default="data/annotations/action_menu.csv",
    )
    parser.add_argument(
        "--context-frames",
        help="Optional R1 causal-context JSONL. Only earlier frames from the same sequence are shown.",
    )
    parser.add_argument(
        "--assignment",
        help="Optional R1 rater assignment CSV. Restricts the annotator to assigned focal frames.",
    )
    parser.add_argument(
        "--annotator-id",
        default="annotator_01",
    )
    parser.add_argument(
        "--lock-annotator-id",
        action="store_true",
        help="Prevent accidental annotation under another rater identity.",
    )
    parser.add_argument(
        "--unblinded-exploratory",
        action="store_true",
        help="Show selected-action controls. Never use these ratings in the publication freeze.",
    )
    parser.add_argument(
        "--show-model-scores",
        action="store_true",
        help="Show model-ranked affordances. Never use these ratings in the publication freeze.",
    )
    args = parser.parse_args()
    run(
        args.frames,
        args.annotations,
        outcome_blinded=not args.unblinded_exploratory,
        model_score_blinded=not args.show_model_scores,
        context_frame_path=args.context_frames,
        assignment_path=args.assignment,
        annotator_id_default=args.annotator_id,
        lock_annotator_id=args.lock_annotator_id,
    )