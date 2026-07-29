from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


def _first_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


@dataclass(frozen=True)
class GazeSample:
    timestamp_s: float
    yaw_rad: float
    pitch_rad: float
    depth_m: float | None
    source: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def load_egoexo_gaze_csv(path: str | Path, *, source: str = "ego_exo4d_personalized") -> list[GazeSample]:
    frame = pd.read_csv(path)
    columns = list(frame.columns)
    timestamp = _first_column(columns, ("tracking_timestamp_us", "timestamp_us", "timestamp_ns", "timestamp_s", "timestamp"))
    yaw = _first_column(columns, ("yaw_rads_cpf", "yaw_rad", "yaw"))
    pitch = _first_column(columns, ("pitch_rads_cpf", "pitch_rad", "pitch"))
    depth = _first_column(columns, ("depth_m", "depth", "vergence_depth_m"))
    confidence_col = _first_column(columns, ("confidence", "quality", "gaze_confidence"))
    if timestamp is None or yaw is None or pitch is None:
        raise ValueError("gaze CSV must contain timestamp, yaw, and pitch columns")
    values: list[GazeSample] = []
    for row in frame.to_dict(orient="records"):
        raw_timestamp = float(row[timestamp])
        name = timestamp.lower()
        if "_us" in name:
            time_s = raw_timestamp / 1_000_000.0
        elif "_ns" in name:
            time_s = raw_timestamp / 1_000_000_000.0
        else:
            time_s = raw_timestamp
        values.append(GazeSample(
            timestamp_s=time_s,
            yaw_rad=float(row[yaw]),
            pitch_rad=float(row[pitch]),
            depth_m=None if depth is None or pd.isna(row[depth]) else float(row[depth]),
            source=source,
            confidence=1.0 if confidence_col is None or pd.isna(row[confidence_col]) else float(row[confidence_col]),
        ))
    return values


def load_opencap_mot(path: str | Path) -> pd.DataFrame:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    end_header = next((index for index, line in enumerate(lines) if line.strip().lower() == "endheader"), None)
    if end_header is None:
        raise ValueError("OpenSim .mot file is missing endheader")
    data_lines = [line for line in lines[end_header + 1:] if line.strip()]
    if not data_lines:
        raise ValueError("OpenSim .mot file contains no data")
    reader = csv.reader(data_lines, delimiter="	")
    rows = list(reader)
    columns = [value.strip() for value in rows[0] if value.strip()]
    records = []
    for raw in rows[1:]:
        values = [value for value in raw if value != ""]
        if len(values) < len(columns):
            continue
        records.append({name: float(value) for name, value in zip(columns, values)})
    result = pd.DataFrame(records)
    if "time" not in result.columns:
        raise ValueError("OpenSim .mot file must contain time")
    return result


def load_worldpose_export(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if "frames" not in payload:
            raise ValueError("WorldPose export JSON must contain frames")
        return payload
    if source.suffix.lower() == ".npz":
        import numpy as np
        data = np.load(source, allow_pickle=False)
        return {key: data[key].tolist() for key in data.files}
    raise ValueError("WorldPose adapter supports JSON or NPZ exports")


def load_statsbomb_empirical_bundle(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    event = json.loads((root / "event.json").read_text(encoding="utf-8"))
    freeze = json.loads((root / "three_sixty.json").read_text(encoding="utf-8"))
    if event["id"] != freeze["event_uuid"]:
        raise ValueError("event and 360 snapshot UUIDs differ")
    return {"event": event, "three_sixty": freeze}


def metrica_frame_from_excerpt(root: str | Path, frame_id: int) -> dict[str, Any]:
    directory = Path(root)
    # The three-line provider header is preserved for provenance; normalized CSV is easier to consume.
    home_n = pd.read_csv(directory / "home_normalized.csv")
    away_n = pd.read_csv(directory / "away_normalized.csv")
    h = home_n.loc[home_n["frame"] == frame_id]
    a = away_n.loc[away_n["frame"] == frame_id]
    if h.empty or a.empty:
        raise KeyError(frame_id)
    return {"home": h.to_dict(orient="records"), "away": a.to_dict(orient="records")}
