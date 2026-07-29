from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


NON_FEATURE_COLUMNS = {
    "sequence_id",
    "frame_id",
    "option_id",
    "kind",
    "actor_id",
    "target_player_id",
    "target_x",
    "target_y",
    "geometric_score",
    "naive_score",
    "static_score",
    "learned_score",
    "label_available",
    "label_value",
    "label_selected",
    "label_visibility",
    "label_confidence",
    "label_failure_reason",
    "annotator_id",
    "source_provider",
    "source_match_id",
    "provenance",
}


class LearnedOptionModel:
    """A compact learned baseline over interpretable affordance features.

    This is intentionally small enough for the first ten-sequence experiment. It tests whether
    nonlinear combinations improve option ranking before introducing video or graph encoders.
    """

    def __init__(self, random_state: int = 7):
        self.random_state = random_state
        self.feature_columns: list[str] = []
        self.pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=180,
                        learning_rate=0.06,
                        max_leaf_nodes=15,
                        l2_regularization=0.2,
                        random_state=random_state,
                    ),
                ),
            ]
        )

    @staticmethod
    def infer_feature_columns(dataframe: pd.DataFrame) -> list[str]:
        columns = [
            column
            for column in dataframe.columns
            if column not in NON_FEATURE_COLUMNS and pd.api.types.is_numeric_dtype(dataframe[column])
        ]
        if not columns:
            raise ValueError("No numeric feature columns found")
        return sorted(columns)

    def fit(self, dataframe: pd.DataFrame, target: str = "label_value") -> "LearnedOptionModel":
        training = dataframe.dropna(subset=[target]).copy()
        if training.empty:
            raise ValueError("No labeled rows available for training")
        self.feature_columns = self.infer_feature_columns(training)
        self.pipeline.fit(training[self.feature_columns], training[target].to_numpy(dtype=float))
        return self

    def predict(self, dataframe: pd.DataFrame) -> np.ndarray:
        if not self.feature_columns:
            raise RuntimeError("Model has not been fitted")
        missing = sorted(set(self.feature_columns) - set(dataframe.columns))
        if missing:
            raise ValueError(f"Missing model features: {missing}")
        return self.pipeline.predict(dataframe[self.feature_columns])

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "random_state": self.random_state,
                "feature_columns": self.feature_columns,
                "pipeline": self.pipeline,
            },
            output,
        )
        return output

    @classmethod
    def load(cls, path: str | Path) -> "LearnedOptionModel":
        payload = joblib.load(path)
        model = cls(random_state=payload["random_state"])
        model.feature_columns = payload["feature_columns"]
        model.pipeline = payload["pipeline"]
        return model
