from __future__ import annotations

from dataclasses import dataclass

from ...adapters.normalization import CoordinateTransformer


@dataclass(frozen=True, slots=True)
class SoccerNetCoordinateContract:
    pitch_length: float = 105.0
    pitch_width: float = 68.0
    origin: str = "center"
    units: str = "meters"
    y_axis: str = "up"

    def transformer(self) -> CoordinateTransformer:
        return CoordinateTransformer(
            pitch_length=self.pitch_length,
            pitch_width=self.pitch_width,
            origin=self.origin,
            units=self.units,
            y_axis=self.y_axis,
        )

    def point(self, x: float, y: float) -> tuple[float, float]:
        return self.transformer().point(x, y)
