from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd


def dcg(relevances: Iterable[float], k: int | None = None) -> float:
    values = np.asarray(list(relevances), dtype=float)
    if k is not None:
        values = values[:k]
    discounts = np.log2(np.arange(2, len(values) + 2))
    return float(np.sum((2**values - 1.0) / discounts))


def ndcg_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int = 3) -> float:
    order = np.argsort(-y_score)
    ideal = np.argsort(-y_true)
    denom = dcg(y_true[ideal], k)
    return 0.0 if denom == 0 else dcg(y_true[order], k) / denom


def recall_at_k(y_true_binary: np.ndarray, y_score: np.ndarray, k: int = 3) -> float:
    positives = int(np.sum(y_true_binary > 0))
    if positives == 0:
        return 1.0
    selected = np.argsort(-y_score)[:k]
    return float(np.sum(y_true_binary[selected] > 0) / positives)


def pairwise_ranking_accuracy(y_true: np.ndarray, y_score: np.ndarray) -> float:
    correct = 0
    total = 0
    for i in range(len(y_true)):
        for j in range(i + 1, len(y_true)):
            if math.isclose(float(y_true[i]), float(y_true[j])):
                continue
            total += 1
            correct += int((y_true[i] - y_true[j]) * (y_score[i] - y_score[j]) > 0)
    return 1.0 if total == 0 else correct / total


def expected_calibration_error(y_true: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (probability >= lower) & (probability < upper if upper < 1 else probability <= upper)
        if not np.any(mask):
            continue
        accuracy = float(np.mean(y_true[mask]))
        confidence = float(np.mean(probability[mask]))
        ece += float(np.mean(mask)) * abs(accuracy - confidence)
    return ece


def evaluate_rankings(
    dataframe: pd.DataFrame,
    score_column: str,
    value_column: str = "label_value",
    available_column: str = "label_available",
    k: int = 3,
) -> dict[str, float]:
    per_frame = []
    for _, group in dataframe.groupby(["sequence_id", "frame_id"], sort=False):
        y_true = group[value_column].fillna(0.0).to_numpy(dtype=float)
        y_available = group[available_column].fillna(False).to_numpy(dtype=bool)
        scores = group[score_column].to_numpy(dtype=float)
        per_frame.append(
            {
                "ndcg": ndcg_at_k(y_true, scores, k=k),
                "recall": recall_at_k(y_available, scores, k=k),
                "pairwise": pairwise_ranking_accuracy(y_true, scores),
            }
        )
    if not per_frame:
        return {f"ndcg@{k}": float("nan"), f"recall@{k}": float("nan"), "pairwise": float("nan")}
    return {
        f"ndcg@{k}": float(np.mean([row["ndcg"] for row in per_frame])),
        f"recall@{k}": float(np.mean([row["recall"] for row in per_frame])),
        "pairwise": float(np.mean([row["pairwise"] for row in per_frame])),
    }
