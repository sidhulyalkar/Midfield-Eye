from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from ...adapters.base import AdapterResult
from ...adapters.normalization import canonical_team
from ...schema import FrameState, PlayerState, Team
from .confidence import combine_confidences, covariance_from_confidence
from .coordinate_normalizer import SoccerNetCoordinateContract
from .schemas import PossessionSidecarRecord, TrackerStateBundle
from .tracker_state_reader import read_tracker_state


def _team(value: str, mapping: dict[str, Team]) -> Team:
    key = str(value).strip().lower()
    if key in mapping:
        return mapping[key]
    return canonical_team(key)


def _read_sidecar(path: str | Path) -> dict[int, PossessionSidecarRecord]:
    dataframe = pd.read_csv(path)
    required = {"frame_id", "ball_x", "ball_y", "possession_team", "ball_carrier_id"}
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"SoccerNet possession sidecar missing columns: {missing}")
    records: dict[int, PossessionSidecarRecord] = {}
    for row in dataframe.to_dict(orient="records"):
        frame_id = int(row["frame_id"])
        records[frame_id] = PossessionSidecarRecord(
            frame_id=frame_id,
            ball_x=float(row["ball_x"]),
            ball_y=float(row["ball_y"]),
            possession_team=str(row["possession_team"]),
            ball_carrier_id=str(row["ball_carrier_id"]),
            period=int(row.get("period", 1)),
            timestamp_s=None if pd.isna(row.get("timestamp_s")) else float(row["timestamp_s"]),
            ball_vx=0.0 if pd.isna(row.get("ball_vx")) else float(row["ball_vx"]),
            ball_vy=0.0 if pd.isna(row.get("ball_vy")) else float(row["ball_vy"]),
            ball_confidence=(
                None if pd.isna(row.get("ball_confidence")) else float(row["ball_confidence"])
            ),
            possession_confidence=(
                None
                if pd.isna(row.get("possession_confidence"))
                else float(row["possession_confidence"])
            ),
            ball_status=str(row.get("ball_status", "sidecar")),
        )
    return records


class SoccernetGSRAdapter:
    """Convert frozen SoccerNet/TrackLab perception state into canonical tactical frames.

    The adapter does not import TrackLab and never infers a ball carrier from player detections.
    A possession sidecar is therefore mandatory for frames entering the affordance engine.
    """

    def __init__(
        self,
        *,
        pitch_length: float = 105.0,
        pitch_width: float = 68.0,
        team_map: dict[str, Team] | None = None,
        coordinates: str = "soccernet_center",
    ) -> None:
        self.pitch_length = pitch_length
        self.pitch_width = pitch_width
        self.team_map = team_map or {"left": "home", "right": "away", "home": "home", "away": "away"}
        self.coordinates = coordinates
        self.contract = SoccerNetCoordinateContract(pitch_length, pitch_width)

    def _point(self, x: float, y: float) -> tuple[float, float]:
        if self.coordinates == "canonical":
            return float(x), float(y)
        if self.coordinates == "soccernet_center":
            return self.contract.point(x, y)
        raise ValueError(f"Unknown SoccerNet coordinate mode {self.coordinates!r}")

    def convert(
        self,
        bundle: TrackerStateBundle,
        possession_sidecar_path: str | Path,
        *,
        sequence_id: str | None = None,
        attacking_direction: dict[str, int] | None = None,
    ) -> AdapterResult:
        sidecar = _read_sidecar(possession_sidecar_path)
        sequence = sequence_id or f"soccernet_gsr:{bundle.match_id}"
        warnings = list(bundle.warnings)
        frames: list[FrameState] = []

        for perception in bundle.frames:
            possession = sidecar.get(perception.frame_id)
            if possession is None:
                warnings.append(f"frame {perception.frame_id} has no possession sidecar row; skipped")
                continue
            players: list[PlayerState] = []
            for observation in perception.observations:
                role = (observation.role or "player").lower()
                if role not in {"player", "goalkeeper"} or observation.team is None:
                    continue
                try:
                    team = _team(observation.team, self.team_map)
                except ValueError:
                    warnings.append(
                        f"frame {perception.frame_id} track {observation.track_id} has unknown team {observation.team!r}; skipped"
                    )
                    continue
                x, y = self._point(observation.pitch_x, observation.pitch_y)
                x = float(np.clip(x, 0.0, self.pitch_length))
                y = float(np.clip(y, 0.0, self.pitch_width))
                combined = combine_confidences(
                    observation.detection_confidence,
                    observation.tracking_confidence,
                    observation.calibration_confidence,
                )
                player_id = f"sngs:{observation.track_id}"
                players.append(
                    PlayerState(
                        player_id=player_id,
                        observation_id=f"{bundle.match_id}:{perception.frame_id}:{observation.track_id}",
                        track_id=str(observation.track_id),
                        source_player_id=str(observation.track_id),
                        team=team,
                        x=x,
                        y=y,
                        role=role,
                        jersey_number=observation.jersey_number,
                        tracking_status="observed",
                        confidence=combined,
                        trajectory_confidence=observation.tracking_confidence,
                        calibration_confidence=(
                            observation.calibration_confidence or perception.camera_confidence
                        ),
                        position_covariance=covariance_from_confidence(
                            observation.detection_confidence,
                            observation.tracking_confidence,
                            observation.calibration_confidence or perception.camera_confidence,
                        ),
                        visible=True,
                        visibility="visible",
                        image_bbox=observation.image_bbox,
                        metadata={
                            "raw_team": observation.team,
                            "embedding_ref": observation.embedding_ref,
                            "attributes": observation.attributes,
                        },
                        provenance_flags=["soccernet_gsr", "pitch_projection"],
                    )
                )

            carrier_id = possession.ball_carrier_id
            if not carrier_id.startswith("sngs:"):
                carrier_id = f"sngs:{carrier_id}"
            player_ids = {player.player_id for player in players}
            if carrier_id not in player_ids:
                warnings.append(
                    f"carrier {carrier_id} absent from frame {perception.frame_id}; frame skipped"
                )
                continue
            possession_team = _team(possession.possession_team, self.team_map)
            frame = FrameState(
                sequence_id=sequence,
                frame_id=perception.frame_id,
                timestamp_s=(
                    possession.timestamp_s
                    if possession.timestamp_s is not None
                    else perception.timestamp_s
                ),
                possession_team=possession_team,
                ball_x=possession.ball_x,
                ball_y=possession.ball_y,
                ball_vx=possession.ball_vx,
                ball_vy=possession.ball_vy,
                ball_carrier_id=carrier_id,
                players=players,
                pitch_length=self.pitch_length,
                pitch_width=self.pitch_width,
                attacking_direction=attacking_direction or {"home": 1, "away": -1},
                period=possession.period or perception.period,
                frame_rate_hz=bundle.fps,
                visibility_polygon=perception.visible_pitch_polygon,
                source_provider="soccernet_gsr",
                source_match_id=bundle.match_id,
                ball_confidence=possession.ball_confidence,
                ball_status=possession.ball_status,  # type: ignore[arg-type]
                possession_confidence=possession.possession_confidence,
                calibration_confidence=perception.camera_confidence,
                camera_id=perception.camera_id,
                quality_flags=["partial_visibility", "external_possession_sidecar", "frozen_tracker_state"],
                metadata={
                    "partial_visibility": True,
                    "tracker_state_source": bundle.source_path,
                    "tracker_state_metadata": bundle.metadata,
                    "sidecar_record": asdict(possession),
                },
            )
            frame.validate()
            frames.append(frame)

        return AdapterResult(
            frames=frames,
            provider_id="soccernet_gsr",
            source_match_id=bundle.match_id,
            warnings=sorted(set(warnings)),
            metadata={
                "sidecar": str(possession_sidecar_path),
                "fps": bundle.fps,
                "tracker_state": bundle.source_path,
                "coordinates": self.coordinates,
            },
        )


def load_tracker_state_gsr(
    tracker_state_path: str | Path,
    possession_sidecar_path: str | Path,
    *,
    visibility_path: str | Path | None = None,
    match_id: str | None = None,
    sequence_id: str | None = None,
    fps: float = 25.0,
    coordinates: str = "soccernet_center",
    team_map: dict[str, Team] | None = None,
) -> AdapterResult:
    bundle = read_tracker_state(
        tracker_state_path,
        match_id=match_id,
        fps=fps,
        visibility_path=visibility_path,
    )
    adapter = SoccernetGSRAdapter(team_map=team_map, coordinates=coordinates)
    return adapter.convert(bundle, possession_sidecar_path, sequence_id=sequence_id)
