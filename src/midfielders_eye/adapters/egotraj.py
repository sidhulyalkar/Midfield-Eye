from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(slots=True)
class EgoTrajRecord:
    timestamp_s: float
    position_xyz: np.ndarray
    quaternion_xyzw: np.ndarray
    gaze_origin_xyz: np.ndarray
    gaze_direction_xyz: np.ndarray
    image_path: str | None = None


def load_egotraj_csv(path: str | Path) -> list[EgoTrajRecord]:
    """Load a normalized EgoTraj export.

    The upstream project may revise concrete filenames or field names. Use
    `scripts/normalize_egotraj.py` to map the downloaded release into this stable contract.
    Required columns are documented in docs/DATASETS.md.
    """
    frame = pd.read_csv(path)
    required = {
        "timestamp_s",
        "head_x",
        "head_y",
        "head_z",
        "quat_x",
        "quat_y",
        "quat_z",
        "quat_w",
        "gaze_origin_x",
        "gaze_origin_y",
        "gaze_origin_z",
        "gaze_dir_x",
        "gaze_dir_y",
        "gaze_dir_z",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Normalized EgoTraj CSV is missing columns: {missing}")
    records = []
    for row in frame.itertuples(index=False):
        records.append(
            EgoTrajRecord(
                timestamp_s=float(row.timestamp_s),
                position_xyz=np.array([row.head_x, row.head_y, row.head_z], dtype=float),
                quaternion_xyzw=np.array([row.quat_x, row.quat_y, row.quat_z, row.quat_w], dtype=float),
                gaze_origin_xyz=np.array(
                    [row.gaze_origin_x, row.gaze_origin_y, row.gaze_origin_z], dtype=float
                ),
                gaze_direction_xyz=np.array([row.gaze_dir_x, row.gaze_dir_y, row.gaze_dir_z], dtype=float),
                image_path=getattr(row, "image_path", None),
            )
        )
    return records
