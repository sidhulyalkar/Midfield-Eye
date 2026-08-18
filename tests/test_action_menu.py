from __future__ import annotations

import pandas as pd
import pytest

from midfielders_eye.action_menu import (
    ActionMenuAnnotation,
    annotation_contract_summary,
    annotations_to_dataframe,
    build_action_menu_tables,
    stable_option_key,
    validate_annotation_dataframe,
)
from midfielders_eye.schema import ActionOption


def _option(frame_id: int, kind: str, target: str | None, score: float, suffix: str) -> ActionOption:
    return ActionOption(
        sequence_id="seq-1",
        frame_id=frame_id,
        option_id=f"seq-1:{frame_id}:{suffix}",
        kind=kind,  # type: ignore[arg-type]
        actor_id="p1",
        target_player_id=target,
        target_x=50.0,
        target_y=30.0,
        features={},
        geometric_score=score,
    )


def test_stable_option_keys_ignore_frame_identity() -> None:
    first = _option(10, "pass", "p8", 0.4, "pass:p8")
    second = _option(11, "pass", "p8", 0.7, "pass:p8")
    carry = _option(11, "carry", None, 0.2, "carry:+22.5")
    hold = _option(11, "hold", None, 0.1, "hold")

    assert stable_option_key(first) == stable_option_key(second) == "pass:p8"
    assert stable_option_key(carry) == "carry:+22.5"
    assert stable_option_key(hold) == "hold"


def test_action_menu_tables_capture_birth_extinction_and_topk_stability() -> None:
    rows = [
        _option(1, "pass", "p8", 0.8, "pass:p8").to_flat_dict(),
        _option(1, "hold", None, 0.2, "hold").to_flat_dict(),
        _option(2, "pass", "p8", 0.5, "pass:p8").to_flat_dict(),
        _option(2, "carry", None, 0.9, "carry:+0.0").to_flat_dict(),
        _option(3, "carry", None, 0.7, "carry:+0.0").to_flat_dict(),
    ]
    dataframe = pd.DataFrame(rows)
    lifecycles, timeline, summary = build_action_menu_tables(dataframe, top_k=2)

    pass_lifecycle = lifecycles[lifecycles["stable_option_key"] == "pass:p8"].iloc[0]
    assert pass_lifecycle["birth_frame_id"] == 1
    assert pass_lifecycle["death_frame_id"] == 2
    assert pass_lifecycle["frames_seen"] == 2

    frame_two = timeline[timeline["frame_id"] == 2].iloc[0]
    assert frame_two["births"] == "carry:+0.0"
    assert frame_two["extinctions"] == "hold"
    assert frame_two["top_option_key"] == "carry:+0.0"
    assert frame_two["top_k_jaccard_previous"] == pytest.approx(1 / 3)

    frame_three = timeline[timeline["frame_id"] == 3].iloc[0]
    assert frame_three["extinctions"] == "pass:p8"
    assert summary["sequence_count"] == 1
    assert summary["candidate_count"] == 5
    assert "retrospective" in summary["retrospective_lifecycle_warning"].lower()


def test_duplicate_stable_candidate_within_frame_is_rejected() -> None:
    row = _option(1, "pass", "p8", 0.8, "pass:p8").to_flat_dict()
    with pytest.raises(ValueError, match="duplicate stable options"):
        build_action_menu_tables(pd.DataFrame([row, dict(row)]))


def test_annotation_contract_keeps_targets_separate_and_validated() -> None:
    annotations = [
        ActionMenuAnnotation(
            sequence_id="seq-1",
            frame_id=2,
            option_key="pass:p8",
            annotator_id="expert-a",
            available="yes",
            visible="uncertain",
            value_ordinal=3,
            creation_ordinal=2,
            selected=False,
            confidence=0.8,
        ),
        ActionMenuAnnotation(
            sequence_id="seq-1",
            frame_id=2,
            option_key="pass:p8",
            annotator_id="expert-b",
            available="yes",
            visible="yes",
            value_ordinal=4,
            creation_ordinal=2,
            selected=False,
            confidence=0.9,
        ),
    ]
    dataframe = annotations_to_dataframe(annotations)
    validate_annotation_dataframe(dataframe)
    summary = annotation_contract_summary(dataframe)

    assert summary["decision_items"] == 1
    assert summary["double_rated_fraction"] == 1.0
    assert summary["outcome_blinded_fraction"] == 1.0
    assert summary["uncertain_visibility_fraction"] == 0.5


def test_annotation_contract_refuses_invalid_scales() -> None:
    with pytest.raises(ValueError, match="creation_ordinal"):
        ActionMenuAnnotation(
            sequence_id="seq-1",
            frame_id=2,
            option_key="hold",
            annotator_id="expert-a",
            available="yes",
            visible="yes",
            value_ordinal=2,
            creation_ordinal=5,
        )
