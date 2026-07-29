from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SensorSpec:
    sensor_id: str
    modality: str
    sampling_rate_hz: float
    clock_domain: str
    calibration_required: bool
    required: bool = True
    notes: str = ""


@dataclass(frozen=True)
class TaskBlock:
    block_id: str
    name: str
    repetitions: int
    active_pressure: bool
    intended_measurements: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class ConsentScope:
    participant_id: str
    research_analysis: bool
    model_training: bool
    public_derived_visuals: bool
    public_identifiable_media: bool
    withdrawal_process_documented: bool
    retention_days: int


@dataclass(frozen=True)
class CaptureProtocol:
    protocol_id: str
    title: str
    version: str
    sensors: tuple[SensorSpec, ...]
    task_blocks: tuple[TaskBlock, ...]
    synchronization_method: str
    synchronization_anchor_count: int
    pre_block_calibration: bool
    post_block_drift_check: bool
    direct_measurements: tuple[str, ...]
    derived_measurements: tuple[str, ...]
    prohibited_claims: tuple[str, ...]
    consent: ConsentScope
    preregistered_metrics: tuple[str, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_midfield_capture_protocol(participant_id: str = "participant-placeholder") -> CaptureProtocol:
    return CaptureProtocol(
        protocol_id="midfielder-eye-direct-gaze-biomechanics-pilot",
        title="Direct gaze, receiving mechanics, and relational-control football pilot",
        version="0.6.0",
        sensors=(
            SensorSpec("eye-tracker", "binocular_eye_gaze", 100.0, "wearable", True, notes="Retain calibration quality and dropout flags."),
            SensorSpec("head-imu", "head_pose_imu", 200.0, "wearable", True),
            SensorSpec("tactical-camera-a", "video", 60.0, "camera", True),
            SensorSpec("tactical-camera-b", "video", 60.0, "camera", True),
            SensorSpec("body-camera-array", "multiview_pose", 120.0, "camera", True, notes="Two cameras minimum; four preferred for turning and occlusion."),
            SensorSpec("ball-tracker", "ball_tracking", 50.0, "tracking", True),
            SensorSpec("player-tracker", "full_tracking", 25.0, "tracking", True),
            SensorSpec("force-reference", "force_plate_or_instrumented_insole", 1000.0, "force", True, required=False, notes="Needed only for direct force validation."),
        ),
        task_blocks=(
            TaskBlock(
                "half-turn-reception",
                "Half-turn reception under rear pressure",
                12,
                True,
                ("pre_reception_scan", "open_body_angle", "first_touch_direction", "option_retention"),
                "Receive from a defender-facing starting posture and play either side under randomized pressure.",
            ),
            TaskBlock(
                "attract-and-switch",
                "Attract pressure and switch play",
                10,
                True,
                ("gaze_acquisition", "pressure_attraction", "weak_side_access", "release_timing"),
                "Delay or release immediately after an approaching presser, with randomized weak-side support.",
            ),
            TaskBlock(
                "third-player",
                "Third-player combination",
                10,
                True,
                ("scan_sequence", "support_reactivity", "body_dissociation", "third_player_value"),
                "Use a bounce player to access a runner whose availability changes between repetitions.",
            ),
            TaskBlock(
                "brake-turn-disguise",
                "Brake, turn, disguise, and redirect",
                12,
                True,
                ("braking_acceleration", "pelvis_rotation", "head_torso_dissociation", "action_direction_spread"),
                "Approach on a curved run, decelerate, and choose among pass, carry, or shot cues.",
            ),
            TaskBlock(
                "off-ball-reposition",
                "Off-ball repositioning and second reception",
                10,
                True,
                ("co_adaptation_lag", "network_brokerage", "future_option_uplift", "reacquisition_time"),
                "Move after release to alter teammate and opponent geometry before a second reception.",
            ),
        ),
        synchronization_method="shared_hardware_pulse_plus_visible_audio_clap_backup",
        synchronization_anchor_count=3,
        pre_block_calibration=True,
        post_block_drift_check=True,
        direct_measurements=(
            "eye_gaze_ray",
            "head_imu",
            "camera_pixels",
            "player_positions_when_tracking_is_direct",
            "ball_position_when_tracking_is_direct",
            "force_only_when_force_reference_is_present",
        ),
        derived_measurements=(
            "scan_events",
            "body_pose_3d",
            "joint_kinematics",
            "center_of_mass",
            "braking_load_proxy",
            "field_of_view_projection",
            "affordance_options",
            "relational_control_metrics",
        ),
        prohibited_claims=(
            "Do not call head direction literal gaze.",
            "Do not call model-derived ground reaction force a direct force measurement.",
            "Do not infer leadership intent from teammate displacement alone.",
            "Do not publish identifiable footage without explicit public-identifiable-media consent.",
        ),
        consent=ConsentScope(
            participant_id=participant_id,
            research_analysis=True,
            model_training=False,
            public_derived_visuals=True,
            public_identifiable_media=False,
            withdrawal_process_documented=True,
            retention_days=365,
        ),
        preregistered_metrics=(
            "scan_rate_before_reception",
            "first_best_option_acquisition_s",
            "visible_option_recall",
            "scan_to_action_latency_s",
            "head_gaze_dissociation_deg",
            "open_body_angle_deg",
            "braking_acceleration_mps2",
            "action_direction_spread_deg",
            "option_enablement_delta",
            "co_adaptation_lag_s",
            "test_retest_icc",
        ),
        notes=(
            "Participant-held-out and task-form-held-out splits are mandatory.",
            "Retain raw clocks and synchronization anchors; never overwrite them with aligned time.",
            "Public examples should default to de-identified pitch-space reconstructions.",
        ),
    )


def validate_capture_protocol(protocol: CaptureProtocol) -> list[str]:
    errors: list[str] = []
    if protocol.synchronization_anchor_count < 2:
        errors.append("At least two synchronization anchors are required to estimate clock drift.")
    if not protocol.pre_block_calibration:
        errors.append("Pre-block calibration is required.")
    if not protocol.post_block_drift_check:
        errors.append("A post-block calibration drift check is required.")
    if not protocol.consent.research_analysis:
        errors.append("Research-analysis consent is required before capture.")
    if not protocol.consent.withdrawal_process_documented:
        errors.append("The participant withdrawal process must be documented.")
    if protocol.consent.retention_days <= 0:
        errors.append("Retention duration must be positive.")
    if protocol.consent.public_identifiable_media and not protocol.consent.public_derived_visuals:
        errors.append("Identifiable-public-media consent cannot be broader than derived-visual consent.")
    if not any(sensor.modality == "binocular_eye_gaze" and sensor.required for sensor in protocol.sensors):
        errors.append("A required direct eye-gaze sensor is missing.")
    if not any(sensor.modality == "full_tracking" and sensor.required for sensor in protocol.sensors):
        errors.append("A required player-tracking source is missing.")
    if not any(sensor.modality == "ball_tracking" and sensor.required for sensor in protocol.sensors):
        errors.append("A required ball-tracking source is missing.")
    if not protocol.task_blocks:
        errors.append("At least one task block is required.")
    for sensor in protocol.sensors:
        if sensor.sampling_rate_hz <= 0:
            errors.append(f"Sensor {sensor.sensor_id} must have a positive sampling rate.")
    for block in protocol.task_blocks:
        if block.repetitions < 2:
            errors.append(f"Task block {block.block_id} needs at least two repetitions.")
    return errors


def protocol_from_dict(payload: dict[str, Any]) -> CaptureProtocol:
    sensors = tuple(SensorSpec(**item) for item in payload.get("sensors", []))
    task_blocks = tuple(
        TaskBlock(
            block_id=item["block_id"],
            name=item["name"],
            repetitions=int(item["repetitions"]),
            active_pressure=bool(item["active_pressure"]),
            intended_measurements=tuple(item.get("intended_measurements", [])),
            description=item["description"],
        )
        for item in payload.get("task_blocks", [])
    )
    consent = ConsentScope(**payload["consent"])
    return CaptureProtocol(
        protocol_id=payload["protocol_id"],
        title=payload["title"],
        version=payload["version"],
        sensors=sensors,
        task_blocks=task_blocks,
        synchronization_method=payload["synchronization_method"],
        synchronization_anchor_count=int(payload["synchronization_anchor_count"]),
        pre_block_calibration=bool(payload["pre_block_calibration"]),
        post_block_drift_check=bool(payload["post_block_drift_check"]),
        direct_measurements=tuple(payload.get("direct_measurements", [])),
        derived_measurements=tuple(payload.get("derived_measurements", [])),
        prohibited_claims=tuple(payload.get("prohibited_claims", [])),
        consent=consent,
        preregistered_metrics=tuple(payload.get("preregistered_metrics", [])),
        notes=tuple(payload.get("notes", [])),
    )


def write_capture_protocol(
    output_path: str | Path,
    *,
    participant_id: str = "participant-placeholder",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    protocol = default_midfield_capture_protocol(participant_id)
    path.write_text(json.dumps(protocol.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path
