from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance


def numeric_feature_columns(dataframe: pd.DataFrame) -> list[str]:
    excluded = {
        "frame_id",
        "target_x",
        "target_y",
        "label_value",
        "label_available",
        "label_selected",
        "geometric_score",
        "static_score",
        "naive_score",
        "learned_score",
    }
    return [
        column
        for column in dataframe.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(dataframe[column])
    ]


def provider_shift_report(
    dataframe: pd.DataFrame,
    provider_column: str = "source_provider",
    feature_columns: list[str] | None = None,
) -> pd.DataFrame:
    providers = [value for value in dataframe[provider_column].dropna().unique()]
    feature_columns = feature_columns or numeric_feature_columns(dataframe)
    rows = []
    for left_index, left_provider in enumerate(providers):
        left = dataframe[dataframe[provider_column] == left_provider]
        for right_provider in providers[left_index + 1 :]:
            right = dataframe[dataframe[provider_column] == right_provider]
            for feature in feature_columns:
                a = left[feature].dropna().to_numpy(dtype=float)
                b = right[feature].dropna().to_numpy(dtype=float)
                if not len(a) or not len(b):
                    continue
                pooled_std = float(np.std(np.concatenate([a, b])))
                distance = float(wasserstein_distance(a, b))
                rows.append(
                    {
                        "provider_a": left_provider,
                        "provider_b": right_provider,
                        "feature": feature,
                        "wasserstein": distance,
                        "normalized_wasserstein": distance / pooled_std if pooled_std > 1e-12 else 0.0,
                        "mean_a": float(np.mean(a)),
                        "mean_b": float(np.mean(b)),
                    }
                )
    return pd.DataFrame(rows).sort_values("normalized_wasserstein", ascending=False) if rows else pd.DataFrame()
