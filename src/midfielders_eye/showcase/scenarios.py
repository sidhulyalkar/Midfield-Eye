from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from ..schema import FrameState, PlayerState
from ..synthetic import generate_sequence


@dataclass(frozen=True, slots=True)
class ShowcaseScenario:
    id: str
    title: str
    player_id: str
    player_name: str
    archetype: str
    tactical_question: str
    narrative_beats: tuple[str, ...]
    focus_metrics: tuple[str, ...]
    key_frame_index: int
    seed: int
    body_start_rad: float
    body_end_rad: float
    head_scan_amplitude_rad: float
    head_scan_cycles: float
    gaze_lead_rad: float
    relation_pattern: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "archetype": self.archetype,
            "tactical_question": self.tactical_question,
            "narrative_beats": list(self.narrative_beats),
            "focus_metrics": list(self.focus_metrics),
            "key_frame_index": self.key_frame_index,
            "evidence_status": "illustrative_synthetic_reconstruction",
            "gaze_status": "synthetic_visualization_not_measured_player_gaze",
            "body_mechanics_status": "kinematic_proxy_not_force_measurement",
            "relation_pattern": self.relation_pattern,
        }


SCENARIOS: dict[str, ShowcaseScenario] = {
    "olise-half-space": ShowcaseScenario(
        id="olise-half-space",
        title="The pause that moves two defenders",
        player_id="michael-olise",
        player_name="Michael Olise",
        archetype="right half-space creator",
        tactical_question="Does delaying the release widen the weak-side passing menu?",
        narrative_beats=(
            "Receive facing the touchline with the inside corridor still hidden.",
            "Carry half a step inward and hold the defender's hips.",
            "Acquire the far-side runner before the release becomes visible to the block.",
        ),
        focus_metrics=("gaze_to_action", "defender_commitment", "weak_side_access", "multi_action_readiness"),
        key_frame_index=8,
        seed=101,
        body_start_rad=-0.20,
        body_end_rad=0.38,
        head_scan_amplitude_rad=0.34,
        head_scan_cycles=1.6,
        gaze_lead_rad=0.18,
        relation_pattern="attract_and_release",
    ),
    "rodri-pivot": ShowcaseScenario(
        id="rodri-pivot",
        title="Two exits before the first touch",
        player_id="rodri",
        player_name="Rodri",
        archetype="press-resistant single pivot",
        tactical_question="How does pre-reception orientation preserve progression and rest defense?",
        narrative_beats=(
            "Start outside the nearest cover shadow.",
            "Scan both shoulders before the ball arrives.",
            "Use the first touch to keep the switch and vertical pass alive.",
        ),
        focus_metrics=("scan_rate", "open_body_score", "transition_security", "directive_influence"),
        key_frame_index=7,
        seed=202,
        body_start_rad=-0.48,
        body_end_rad=0.46,
        head_scan_amplitude_rad=0.56,
        head_scan_cycles=2.4,
        gaze_lead_rad=0.06,
        relation_pattern="organize_both_sides",
    ),
    "pedri-third-man": ShowcaseScenario(
        id="pedri-third-man",
        title="Arrive in the pocket, do not camp in it",
        player_id="pedri",
        player_name="Pedri",
        archetype="third-player pocket connector",
        tactical_question="Which scans and small movements create a line-breaking third-player route?",
        narrative_beats=(
            "Vacate the pocket while the defender can see both player and ball.",
            "Re-enter on the blind side as the first pass travels.",
            "Play one touch into the runner before the block can reset.",
        ),
        focus_metrics=("option_emergence", "head_body_dissociation", "coadaptation_lag", "line_breaking_access"),
        key_frame_index=9,
        seed=303,
        body_start_rad=-0.05,
        body_end_rad=0.22,
        head_scan_amplitude_rad=0.44,
        head_scan_cycles=3.0,
        gaze_lead_rad=0.12,
        relation_pattern="third_player_exchange",
    ),
    "aitana-overload": ShowcaseScenario(
        id="aitana-overload",
        title="Overload, escape, arrive",
        player_id="aitana-bonmati",
        player_name="Aitana Bonmatí",
        archetype="dynamic half-space controller",
        tactical_question="Can an off-ball rotation create both a local overload and a late box entry?",
        narrative_beats=(
            "Drop toward the ball to pull a midfielder out of the line.",
            "Bounce the pass and continue beyond the opponent's shoulder.",
            "Arrive late enough to preserve the cutback and finishing lane.",
        ),
        focus_metrics=("off_ball_option_creation", "support_reactivity", "balance_reserve", "counterfactual_uplift"),
        key_frame_index=10,
        seed=404,
        body_start_rad=-0.25,
        body_end_rad=0.55,
        head_scan_amplitude_rad=0.38,
        head_scan_cycles=2.1,
        gaze_lead_rad=0.10,
        relation_pattern="overload_escape_arrive",
    ),
    "vitinha-orchestration": ShowcaseScenario(
        id="vitinha-orchestration",
        title="Move the receivers, then move the ball",
        player_id="vitinha",
        player_name="Vitinha",
        archetype="circulation conductor",
        tactical_question="How does repeated repositioning direct teammate spacing before penetration?",
        narrative_beats=(
            "Offer a short angle that draws the nearest marker inward.",
            "Shift behind the passing lane while the next receiver widens.",
            "Accelerate only when the block's lateral spacing fractures.",
        ),
        focus_metrics=("network_brokerage", "support_reactivity", "tempo_direction", "option_enablement"),
        key_frame_index=9,
        seed=505,
        body_start_rad=-0.34,
        body_end_rad=0.30,
        head_scan_amplitude_rad=0.50,
        head_scan_cycles=2.8,
        gaze_lead_rad=0.08,
        relation_pattern="circulation_to_penetration",
    ),
    "musiala-pressure-magnet": ShowcaseScenario(
        id="musiala-pressure-magnet",
        title="Carry until the shape folds",
        player_id="jamal-musiala",
        player_name="Jamal Musiala",
        archetype="pressure magnet",
        tactical_question="How does body control under contact create a superior release after the first defender commits?",
        narrative_beats=(
            "Receive with a defender close enough to invite the duel.",
            "Shift weight across the defender's front foot and keep the ball inside the frame.",
            "Release once the second defender narrows the next passing lane.",
        ),
        focus_metrics=("pressure_attraction", "lateral_load", "balance_reserve", "option_enablement"),
        key_frame_index=8,
        seed=606,
        body_start_rad=-0.18,
        body_end_rad=0.72,
        head_scan_amplitude_rad=0.25,
        head_scan_cycles=1.8,
        gaze_lead_rad=0.16,
        relation_pattern="carry_and_collapse",
    ),
    "alexia-central-control": ShowcaseScenario(
        id="alexia-central-control",
        title="Leave the lane to reopen it",
        player_id="alexia-putellas",
        player_name="Alexia Putellas",
        archetype="central creator",
        tactical_question="How does moving away from the ball reorganize the final action menu?",
        narrative_beats=(
            "Occupy the central lane long enough to pin the holding midfielder.",
            "Drift away as the wide player receives and create a new defender reference.",
            "Return into the reopened lane with pass and shot access preserved.",
        ),
        focus_metrics=("off_ball_option_creation", "blind_side_options", "multi_action_readiness", "directive_influence"),
        key_frame_index=10,
        seed=707,
        body_start_rad=0.30,
        body_end_rad=-0.30,
        head_scan_amplitude_rad=0.42,
        head_scan_cycles=2.2,
        gaze_lead_rad=-0.12,
        relation_pattern="vacate_and_reoccupy",
    ),
    "hasegawa-micro-angles": ShowcaseScenario(
        id="hasegawa-micro-angles",
        title="A new angle every two steps",
        player_id="yui-hasegawa",
        player_name="Yui Hasegawa",
        archetype="micro-angle conductor",
        tactical_question="How do small support movements keep multiple teammates playable under pressure?",
        narrative_beats=(
            "Move outside the cover shadow before the first pass arrives.",
            "Receive on an open shoulder and immediately reconnect the opposite side.",
            "Shift again before the return pass closes the angle.",
        ),
        focus_metrics=("support_reactivity", "scan_rate", "open_body_score", "menu_stability"),
        key_frame_index=9,
        seed=808,
        body_start_rad=-0.42,
        body_end_rad=0.36,
        head_scan_amplitude_rad=0.58,
        head_scan_cycles=3.2,
        gaze_lead_rad=0.05,
        relation_pattern="micro_angle_support",
    ),
}


def list_scenarios() -> list[ShowcaseScenario]:
    return list(SCENARIOS.values())


def _rename_subject(frame: FrameState, scenario: ShowcaseScenario) -> FrameState:
    carrier_id = frame.ball_carrier_id
    renamed: list[PlayerState] = []
    for player in frame.players:
        if player.player_id == carrier_id:
            metadata = dict(player.metadata)
            metadata.update(
                {
                    "showcase_player_id": scenario.player_id,
                    "showcase_player_name": scenario.player_name,
                    "synthetic_subject": True,
                    "gaze_source": "synthetic",
                    "gaze_confidence": 1.0,
                    "body_mechanics_source": "synthetic",
                }
            )
            renamed.append(replace(player, player_id="SUBJECT", source_player_id=carrier_id, metadata=metadata))
        else:
            renamed.append(player)
    metadata = dict(frame.metadata)
    metadata.update(
        {
            "showcase_scenario_id": scenario.id,
            "showcase_player_id": scenario.player_id,
            "showcase_player_name": scenario.player_name,
            "evidence_status": "illustrative_synthetic_reconstruction",
            "disclaimer": "Not real match footage, measured gaze, or measured player performance.",
        }
    )
    return replace(
        frame,
        sequence_id=scenario.id,
        source_match_id=scenario.id,
        ball_carrier_id="SUBJECT",
        players=renamed,
        metadata=metadata,
        state_version="0.5",
    )


def _shape_relations(frame: FrameState, scenario: ShowcaseScenario, phase: float) -> None:
    carrier = frame.carrier
    teammates = frame.teammates()
    opponents = sorted(frame.opponents(), key=lambda player: float(np.linalg.norm(player.position - carrier.position)))
    wave = float(np.sin(phase * np.pi))
    if teammates:
        teammates[0].y = float(np.clip(teammates[0].y - 3.5 * wave, 1.0, frame.pitch_width - 1.0))
        teammates[0].vx += 0.8 * wave
    if len(teammates) > 1:
        teammates[1].x = float(np.clip(teammates[1].x + 4.0 * wave, 1.0, frame.pitch_length - 1.0))
        teammates[1].vy -= 0.6 * wave
    if scenario.relation_pattern in {"attract_and_release", "carry_and_collapse"}:
        for idx, opponent in enumerate(opponents[:2]):
            direction = carrier.position - opponent.position
            norm = max(float(np.linalg.norm(direction)), 1e-6)
            opponent.x += float(direction[0] / norm * (1.5 + idx * 0.6) * wave)
            opponent.y += float(direction[1] / norm * (1.5 + idx * 0.6) * wave)
            opponent.vx += float(direction[0] / norm * 1.2 * wave)
            opponent.vy += float(direction[1] / norm * 1.2 * wave)
    elif scenario.relation_pattern in {"organize_both_sides", "circulation_to_penetration", "micro_angle_support"}:
        for idx, teammate in enumerate(teammates[:3]):
            teammate.y += float(((-1) ** idx) * 1.2 * wave)
    elif scenario.relation_pattern in {"third_player_exchange", "overload_escape_arrive", "vacate_and_reoccupy"}:
        if len(teammates) > 2:
            teammates[2].x += float(5.0 * wave)
            teammates[2].y -= float(2.0 * wave)


def _shape_scenario(frames: list[FrameState], scenario: ShowcaseScenario) -> list[FrameState]:
    shaped: list[FrameState] = []
    previous_velocity: np.ndarray | None = None
    for index, frame in enumerate(frames):
        current = _rename_subject(frame, scenario)
        carrier = current.carrier
        phase = index / max(len(frames) - 1, 1)
        carrier.body_angle = float(scenario.body_start_rad + (scenario.body_end_rad - scenario.body_start_rad) * phase)
        carrier.head_angle = float(
            carrier.body_angle
            + scenario.head_scan_amplitude_rad * np.sin(phase * scenario.head_scan_cycles * 2.0 * np.pi)
        )
        carrier.gaze_angle = float(carrier.head_angle + scenario.gaze_lead_rad * np.cos(phase * 2.0 * np.pi))
        carrier.turning_rate = float(
            (scenario.body_end_rad - scenario.body_start_rad)
            * (current.frame_rate_hz or 6.0)
            / max(len(frames) - 1, 1)
        )
        velocity = carrier.velocity.copy()
        if previous_velocity is not None:
            dt = 1.0 / max(current.frame_rate_hz or 6.0, 1e-6)
            acceleration = (velocity - previous_velocity) / dt
            carrier.ax = float(acceleration[0])
            carrier.ay = float(acceleration[1])
        previous_velocity = velocity
        _shape_relations(current, scenario, phase)
        current.ball_x = carrier.x
        current.ball_y = carrier.y
        shaped.append(current)
    return shaped


def build_scenario_frames(scenario_id: str, frame_count: int = 18, fps: float = 6.0) -> list[FrameState]:
    try:
        scenario = SCENARIOS[scenario_id]
    except KeyError as exc:
        raise KeyError(f"unknown showcase scenario {scenario_id!r}") from exc
    base = generate_sequence(
        sequence_index=scenario.seed % 97,
        frames=frame_count,
        fps=fps,
        seed=scenario.seed,
    )
    # Synthetic showcase frames must retain their real sampling cadence.
    # Temporal cognition metrics use this field to convert frame lag into seconds.
    for frame in base:
        frame.frame_rate_hz = fps
    return _shape_scenario(base, scenario)
