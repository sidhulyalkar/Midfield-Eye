from __future__ import annotations

from pathlib import Path

import pandas as pd

from .action_menu import stable_option_key
from .affordance import AffordanceEngine
from .io import read_frames_jsonl
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


def run(
    frame_path: str,
    annotation_path: str,
    *,
    outcome_blinded: bool = True,
    model_score_blinded: bool = True,
) -> None:
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install the annotation extra: pip install -e '.[annotation]'"
        ) from exc

    frames = read_frames_jsonl(frame_path)
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

    with st.sidebar:
        annotator_id = st.text_input("Annotator ID", value="annotator_01")
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
        st.write(f"Provider: `{sequence_frames[index].source_provider}`")
        st.write(
            "Quality flags: "
            f"{', '.join(sequence_frames[index].quality_flags) or 'none'}"
        )
        st.divider()
        st.write(
            "Outcome status: "
            + ("`BLINDED`" if outcome_blinded else "`UNBLINDED EXPLORATORY`")
        )
        st.write(
            "Model score status: "
            + ("`BLINDED`" if model_score_blinded else "`VISIBLE EXPLORATORY`")
        )
        if not outcome_blinded or not model_score_blinded:
            st.warning(
                "Exploratory unblinded annotations must not be mixed into the "
                "publication reliability or benchmark freeze."
            )

    frame = sequence_frames[index]
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

    history_frames = sequence_frames[max(0, index - 3) : index]
    with st.expander(
        "Causal history for creation labels",
        expanded=False,
    ):
        st.caption(
            "Only earlier frames are shown. Future frames and selected outcomes are never "
            "introduced into the publication annotation view."
        )
        if not history_frames:
            st.info("No earlier frame is available inside this sequence.")
        else:
            history_columns = st.columns(len(history_frames))
            for history_column, history_frame in zip(
                history_columns,
                history_frames,
                strict=True,
            ):
                history_options = _neutral_option_order(
                    engine.generate(history_frame)
                )
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

    rows = []
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
    )
