from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .affordance import AffordanceEngine
from .io import options_to_dataframe
from .quality import assess_frames
from .schema import FrameState


@dataclass(slots=True)
class ProviderBenchmarkRow:
    provider_id: str
    frames: int
    mean_options: float
    mean_pass_options: float
    mean_visible_players: float
    mean_carrier_pressure: float
    mean_top_score: float
    partial_visibility_fraction: float
    extrapolated_player_fraction: float | None


def benchmark_provider_frames(
    providers: dict[str, list[FrameState]],
    engine: AffordanceEngine | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = engine or AffordanceEngine()
    summary_rows: list[dict] = []
    option_frames: list[pd.DataFrame] = []
    for provider_id, frames in providers.items():
        options = [option for frame in frames for option in engine.generate(frame)]
        dataframe = options_to_dataframe(options)
        if dataframe.empty:
            continue
        option_frames.append(dataframe)
        quality = assess_frames(frames, provider_id)
        grouped = dataframe.groupby(["sequence_id", "frame_id"])
        row = ProviderBenchmarkRow(
            provider_id=provider_id,
            frames=len(frames),
            mean_options=float(grouped.size().mean()),
            mean_pass_options=float(dataframe[dataframe["kind"] == "pass"].groupby(["sequence_id", "frame_id"]).size().mean()),
            mean_visible_players=float(sum(len(frame.players) for frame in frames) / len(frames)),
            mean_carrier_pressure=float(dataframe.groupby(["sequence_id", "frame_id"])["receiver_pressure"].mean().mean()),
            mean_top_score=float(grouped["geometric_score"].max().mean()),
            partial_visibility_fraction=float(quality.metrics.get("partial_visibility_fraction") or 0.0),
            extrapolated_player_fraction=quality.metrics.get("extrapolated_player_fraction"),  # type: ignore[arg-type]
        )
        summary_rows.append(asdict(row))
    options = pd.concat(option_frames, ignore_index=True) if option_frames else pd.DataFrame()
    return pd.DataFrame(summary_rows), options
