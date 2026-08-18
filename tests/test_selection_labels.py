from __future__ import annotations

import pandas as pd
import pytest

from midfielders_eye.action_menu import ActionMenuAnnotation, annotations_to_dataframe
from midfielders_eye.selection_labels import (
    join_selected_outcomes,
    selection_join_summary,
)


def _annotations() -> pd.DataFrame:
    return annotations_to_dataframe(
        [
            ActionMenuAnnotation(
                sequence_id="seq-1",
                frame_id=4,
                option_key="pass:p8",
                annotator_id="expert-a",
                available="yes",
                visible="uncertain",
                value_ordinal=4,
                creation_ordinal=3,
            ),
            ActionMenuAnnotation(
                sequence_id="seq-1",
                frame_id=4,
                option_key="hold",
                annotator_id="expert-a",
                available="yes",
                visible="yes",
                value_ordinal=2,
                creation_ordinal=1,
            ),
        ]
    )


def test_selected_outcome_is_joined_after_blinded_labels() -> None:
    annotations = _annotations()
    selections = pd.DataFrame(
        [
            {
                "sequence_id": "seq-1",
                "frame_id": 4,
                "selected_option_key": "pass:p8",
                "selection_provenance": "provider-event",
            }
        ]
    )

    joined = join_selected_outcomes(annotations, selections)

    assert bool(
        joined.loc[joined["option_key"] == "pass:p8", "selected"].item()
    )
    assert not bool(
        joined.loc[joined["option_key"] == "hold", "selected"].item()
    )
    assert set(joined["selection_join_status"]) == {"observed_candidate_selected"}
    summary = selection_join_summary(joined)
    assert summary["frames_with_selected_candidate"] == 1
    assert summary["frames_missing_selection_record"] == 0


def test_selection_join_rejects_unblinded_source_ratings() -> None:
    annotations = _annotations()
    annotations["blinded_to_outcome"] = False
    selections = pd.DataFrame(
        [
            {
                "sequence_id": "seq-1",
                "frame_id": 4,
                "selected_option_key": "pass:p8",
            }
        ]
    )

    with pytest.raises(ValueError, match="outcome-blinded"):
        join_selected_outcomes(annotations, selections)


def test_selection_join_rejects_unknown_candidate() -> None:
    annotations = _annotations()
    selections = pd.DataFrame(
        [
            {
                "sequence_id": "seq-1",
                "frame_id": 4,
                "selected_option_key": "pass:p99",
            }
        ]
    )

    with pytest.raises(ValueError, match="not an annotated candidate"):
        join_selected_outcomes(annotations, selections)


def test_missing_selection_record_is_distinct_from_no_candidate_selected() -> None:
    annotations = pd.concat(
        [
            _annotations(),
            _annotations().assign(frame_id=5),
        ],
        ignore_index=True,
    )
    selections = pd.DataFrame(
        [
            {
                "sequence_id": "seq-1",
                "frame_id": 4,
                "selected_option_key": None,
            }
        ]
    )

    joined = join_selected_outcomes(
        annotations,
        selections,
        require_complete_frames=False,
    )
    status_by_frame = joined.groupby("frame_id")["selection_join_status"].first()

    assert status_by_frame.loc[4] == "no_candidate_selected"
    assert status_by_frame.loc[5] == "selection_record_missing"
    assert joined.loc[joined["frame_id"] == 5, "selected"].isna().all()
    summary = selection_join_summary(joined)
    assert summary["frames_without_selected_candidate"] == 1
    assert summary["frames_missing_selection_record"] == 1
