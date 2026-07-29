from __future__ import annotations

from pathlib import Path

import pandas as pd

from .affordance import AffordanceEngine
from .io import read_frames_jsonl
from .visualization import plot_affordance_frame

AVAILABILITY_OPTIONS = ["yes", "no", "uncertain"]
VISIBILITY_OPTIONS = ["yes", "partial", "no", "uncertain"]
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


def run(frame_path: str, annotation_path: str) -> None:
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the annotation extra: pip install -e '.[annotation]'") from exc

    frames = read_frames_jsonl(frame_path)
    engine = AffordanceEngine()
    st.set_page_config(page_title="The Midfielder's Eye Annotator", layout="wide")
    st.title("The Midfielder's Eye")
    st.caption("Annotate the changing action menu, including uncertainty and viewpoint.")

    with st.sidebar:
        annotator_id = st.text_input("Annotator ID", value="annotator_01")
        sequence_ids = sorted({frame.sequence_id for frame in frames})
        sequence_id = st.selectbox("Sequence", sequence_ids)
        sequence_frames = [frame for frame in frames if frame.sequence_id == sequence_id]
        index = st.slider("Frame within sequence", 0, len(sequence_frames) - 1, 0)
        st.write(f"Provider: `{sequence_frames[index].source_provider}`")
        st.write(f"Quality flags: {', '.join(sequence_frames[index].quality_flags) or 'none'}")

    frame = sequence_frames[index]
    options = engine.generate(frame)
    figure, _ = plot_affordance_frame(frame, options, top_k=min(8, len(options)))
    st.pyplot(figure, use_container_width=True)

    rows = []
    sorted_options = sorted(options, key=lambda item: item.geometric_score, reverse=True)
    for option_index, option in enumerate(sorted_options, start=1):
        label = option.target_player_id or f"({option.target_x:.1f}, {option.target_y:.1f})"
        with st.expander(f"{option_index}. {option.kind} → {label}", expanded=option_index <= 3):
            column_a, column_b, column_c = st.columns(3)
            key = option.option_id.replace(":", "_")
            availability = column_a.selectbox(
                "Available?",
                AVAILABILITY_OPTIONS,
                index=0 if option.geometric_score > 0.20 else 2,
                key=f"available_{key}",
            )
            visibility = column_b.selectbox(
                "Visible to carrier?",
                VISIBILITY_OPTIONS,
                index=0,
                key=f"visibility_{key}",
            )
            ordinal_value = column_c.slider(
                "Tactical value (0–4)",
                0,
                4,
                int(max(0, min(4, round((option.geometric_score + 0.35) * 4)))),
                key=f"value_{key}",
            )
            confidence = column_a.slider(
                "Label confidence",
                0.0,
                1.0,
                0.8,
                0.05,
                key=f"confidence_{key}",
            )
            failure_reason = column_b.selectbox(
                "Primary failure reason",
                FAILURE_REASONS,
                key=f"failure_{key}",
            )
            selected = column_c.checkbox("Selected action", key=f"selected_{key}")
            tactical_note = st.text_input("Tactical note", key=f"note_{key}")

        available_value = True if availability == "yes" else False if availability == "no" else None
        rows.append(
            {
                **option.to_flat_dict(),
                "label_available": available_value,
                "label_value": ordinal_value / 4.0,
                "label_value_ordinal": ordinal_value,
                "label_selected": selected,
                "label_visibility": visibility,
                "label_confidence": confidence,
                "label_failure_reason": None if failure_reason == "none" else failure_reason,
                "annotator_id": annotator_id,
                "tactical_note": tactical_note,
                "provenance": "human-annotation-v2",
            }
        )

    if st.button("Save this frame", type="primary"):
        output = Path(annotation_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        existing = pd.read_csv(output) if output.exists() else pd.DataFrame()
        current = pd.DataFrame(rows)
        if not existing.empty:
            mask = ~(
                (existing["sequence_id"] == frame.sequence_id)
                & (existing["frame_id"] == frame.frame_id)
                & (existing.get("annotator_id", "") == annotator_id)
            )
            existing = existing[mask]
        pd.concat([existing, current], ignore_index=True).to_csv(output, index=False)
        st.success(f"Saved {len(rows)} options to {output}")


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", required=True)
    parser.add_argument("--annotations", default="data/annotations/options.csv")
    args = parser.parse_args()
    run(args.frames, args.annotations)
