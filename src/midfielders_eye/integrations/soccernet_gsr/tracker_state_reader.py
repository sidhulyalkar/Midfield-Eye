from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .schemas import PerceptionFrame, TrackerObservation, TrackerStateBundle


def _first(record: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in record and record[key] is not None and not (isinstance(record[key], float) and np.isnan(record[key])):
            return record[key]
    return default


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _as_list(value: Any) -> list[float] | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return None


def _pitch_point(record: dict[str, Any]) -> tuple[float, float]:
    bbox_pitch = _as_dict(_first(record, "bbox_pitch", "pitch_bbox"))
    x = _first(
        record,
        "x_bottom_middle",
        "bbox_pitch.x_bottom_middle",
        "pitch_x",
        "x_pitch",
        "pitch_position_x",
    )
    y = _first(
        record,
        "y_bottom_middle",
        "bbox_pitch.y_bottom_middle",
        "pitch_y",
        "y_pitch",
        "pitch_position_y",
    )
    if x is None:
        x = _first(bbox_pitch, "x_bottom_middle", "x")
    if y is None:
        y = _first(bbox_pitch, "y_bottom_middle", "y")
    if x is None or y is None:
        raise ValueError("tracker observation has no pitch coordinate")
    return float(x), float(y)


def _records_from_json(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload, {}
    if not isinstance(payload, dict):
        raise ValueError("Tracker-state JSON must be a list or object")
    for key in ("predictions", "annotations", "detections", "observations", "records"):
        if isinstance(payload.get(key), list):
            return payload[key], {key: value for key, value in payload.items() if key not in {"predictions", "annotations", "detections", "observations", "records"}}
    raise ValueError("Tracker-state JSON needs predictions, annotations, detections, observations, or records")


def _load_records(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _records_from_json(path)
    if suffix == ".jsonl":
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return records, {}
    if suffix == ".csv":
        return pd.read_csv(path).to_dict(orient="records"), {}
    if suffix in {".parquet", ".pq"}:
        try:
            return pd.read_parquet(path).to_dict(orient="records"), {}
        except ImportError as exc:  # pragma: no cover - optional engine
            raise RuntimeError("Reading Parquet tracker state requires `pip install -e '.[parquet]'`") from exc
    if suffix in {".pkl", ".pickle"}:
        # Pickle is intentionally supported only for trusted local TrackLab outputs.
        dataframe = pd.read_pickle(path)
        if not isinstance(dataframe, pd.DataFrame):
            raise ValueError("Pickled tracker state must contain a pandas DataFrame")
        return dataframe.to_dict(orient="records"), {"unsafe_pickle": True}
    raise ValueError(f"Unsupported tracker-state extension: {suffix}")


def _normalise_record(record: dict[str, Any]) -> TrackerObservation:
    attributes = _as_dict(_first(record, "attributes", default={}))
    x, y = _pitch_point(record)
    frame_id = int(_first(record, "image_id", "frame_id", "frame", "frame_idx"))
    track_id = str(_first(record, "track_id", "tracklet_id", "id"))
    if track_id in {"None", "nan"}:
        raise ValueError("tracker observation has no track_id")
    role = _first(record, "role", default=attributes.get("role"))
    team = _first(record, "team", "team_id", "team_cluster", default=attributes.get("team"))
    jersey = _first(record, "jersey_number", "jersey", default=attributes.get("jersey"))
    bbox = _as_list(_first(record, "bbox", "bbox_ltwh", "bbox_xywh", "image_bbox"))
    return TrackerObservation(
        frame_id=frame_id,
        track_id=track_id,
        pitch_x=x,
        pitch_y=y,
        role=None if role is None else str(role),
        team=None if team is None else str(team),
        jersey_number=None if jersey is None or str(jersey).lower() in {"nan", "none", "null"} else int(float(jersey)),
        detection_confidence=(
            None
            if _first(record, "confidence", "detection_confidence", "bbox_confidence") is None
            else float(_first(record, "confidence", "detection_confidence", "bbox_confidence"))
        ),
        tracking_confidence=(
            None
            if _first(record, "tracking_confidence", "track_confidence") is None
            else float(_first(record, "tracking_confidence", "track_confidence"))
        ),
        calibration_confidence=(
            None
            if _first(record, "calibration_confidence", "camera_confidence", "pitch_confidence") is None
            else float(_first(record, "calibration_confidence", "camera_confidence", "pitch_confidence"))
        ),
        image_bbox=bbox,
        embedding_ref=(
            None
            if _first(record, "embedding_ref", "reid_embedding_path") is None
            else str(_first(record, "embedding_ref", "reid_embedding_path"))
        ),
        attributes=attributes,
    )


def read_tracker_state(
    path: str | Path,
    *,
    match_id: str | None = None,
    fps: float = 25.0,
    period: int = 1,
    visibility_path: str | Path | None = None,
) -> TrackerStateBundle:
    """Read a frozen SoccerNet/TrackLab state into a dependency-free perception bundle.

    The reader accepts official prediction JSON plus dataframe exports in CSV, JSONL, Parquet,
    or trusted pickle form. Column aliases are deliberately explicit; unknown records are skipped
    with warnings rather than silently assigned fabricated coordinates or identities.
    """
    source = Path(path)
    records, metadata = _load_records(source)
    warnings: list[str] = []
    grouped: dict[int, list[TrackerObservation]] = defaultdict(list)
    for index, record in enumerate(records):
        try:
            observation = _normalise_record(dict(record))
        except Exception as exc:
            warnings.append(f"record {index} skipped: {exc}")
            continue
        grouped[observation.frame_id].append(observation)

    visibility: dict[int, dict[str, Any]] = {}
    if visibility_path is not None:
        visibility_records, _ = _load_records(Path(visibility_path))
        for record in visibility_records:
            frame_id = int(_first(record, "image_id", "frame_id", "frame", "frame_idx"))
            visibility[frame_id] = record

    frames = []
    for frame_id in sorted(grouped):
        camera_record = visibility.get(frame_id, {})
        polygon = _first(camera_record, "visible_pitch_polygon", "visibility_polygon", "image_corners_projection")
        if isinstance(polygon, str):
            try:
                polygon = json.loads(polygon)
            except json.JSONDecodeError:
                polygon = None
        confidence_values = [
            obs.calibration_confidence
            for obs in grouped[frame_id]
            if obs.calibration_confidence is not None
        ]
        camera_confidence = _first(camera_record, "camera_confidence", "calibration_confidence")
        if camera_confidence is None and confidence_values:
            camera_confidence = float(np.median(confidence_values))
        frames.append(
            PerceptionFrame(
                frame_id=frame_id,
                timestamp_s=float(_first(camera_record, "timestamp_s", default=frame_id / fps)),
                observations=grouped[frame_id],
                period=int(_first(camera_record, "period", default=period)),
                visible_pitch_polygon=polygon,
                camera_confidence=None if camera_confidence is None else float(camera_confidence),
                camera_id=None if _first(camera_record, "camera_id") is None else str(_first(camera_record, "camera_id")),
                metadata={"source_record_count": len(grouped[frame_id])},
            )
        )
    resolved_match_id = match_id or source.stem
    metadata.update({"format": source.suffix.lower(), "record_count": len(records)})
    return TrackerStateBundle(
        frames=frames,
        source_path=str(source),
        match_id=resolved_match_id,
        fps=fps,
        warnings=sorted(set(warnings)),
        metadata=metadata,
    )


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(repository: str | Path | None) -> str | None:
    if repository is None:
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_tracker_state_manifest(
    state_path: str | Path,
    output_path: str | Path,
    *,
    repository_path: str | Path | None = None,
    dataset_version: str | None = None,
    model_versions: dict[str, str] | None = None,
    hydra_overrides: list[str] | None = None,
) -> Path:
    state = Path(state_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state_path": str(state),
        "state_sha256": sha256_file(state),
        "state_bytes": state.stat().st_size,
        "sn_gamestate_commit": _git_revision(repository_path),
        "dataset_version": dataset_version,
        "model_versions": model_versions or {},
        "hydra_overrides": hydra_overrides or [],
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output
