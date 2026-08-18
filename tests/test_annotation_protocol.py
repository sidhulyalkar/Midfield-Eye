from __future__ import annotations

from midfielders_eye.annotation_app import (
    AVAILABILITY_OPTIONS,
    VISIBILITY_OPTIONS,
    _neutral_option_order,
)
from midfielders_eye.io import options_to_dataframe
from midfielders_eye.synthetic import build_bootstrap_options, generate_dataset
from midfielders_eye.visualization import plot_annotation_frame


def test_publication_annotation_choices_match_frozen_contract() -> None:
    assert AVAILABILITY_OPTIONS == ["uncertain", "yes", "no"]
    assert VISIBILITY_OPTIONS == ["uncertain", "yes", "no"]


def test_neutral_candidate_order_does_not_depend_on_model_score() -> None:
    frames = generate_dataset(sequences=1, frames=1, seed=41)
    options = build_bootstrap_options(frames)
    ordered = _neutral_option_order(options)
    reversed_scores = []
    for index, option in enumerate(options):
        option.geometric_score = float(len(options) - index)
        reversed_scores.append(option)

    reordered = _neutral_option_order(reversed_scores)

    assert [option.option_id for option in ordered] == [
        option.option_id for option in reordered
    ]


def test_annotation_pitch_uses_neutral_candidate_labels() -> None:
    frames = generate_dataset(sequences=1, frames=1, seed=43)
    options = _neutral_option_order(build_bootstrap_options(frames))[:3]

    figure, axis = plot_annotation_frame(frames[0], options)
    text = [item.get_text() for item in axis.texts]

    assert any(label.startswith("A01 ") for label in text)
    assert "outcome-blind candidate state" in axis.get_title()
    assert "ranked affordances" not in axis.get_title()
    figure.clear()


def test_neutral_order_stays_available_in_flat_candidate_data() -> None:
    frames = generate_dataset(sequences=1, frames=1, seed=47)
    dataframe = options_to_dataframe(
        _neutral_option_order(build_bootstrap_options(frames))
    )

    assert not dataframe.empty
