from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .metrics import evaluate_rankings
from .models import LearnedOptionModel, add_baseline_scores


def _evaluate_fold(train: pd.DataFrame, test: pd.DataFrame, fold: int, target: str) -> tuple[np.ndarray, dict]:
    model = LearnedOptionModel(random_state=fold).fit(train, target=target)
    score = model.predict(test)
    metrics = {
        "learned": evaluate_rankings(test.assign(learned_score=score), "learned_score"),
        "dynamic": evaluate_rankings(test, "geometric_score"),
        "static": evaluate_rankings(test, "static_score"),
        "naive": evaluate_rankings(test, "naive_score"),
    }
    return score, metrics


def cross_validate(
    dataframe: pd.DataFrame,
    splits: int = 5,
    target: str = "label_value",
) -> dict:
    dataframe = add_baseline_scores(dataframe)
    groups = dataframe["sequence_id"].astype(str)
    unique_groups = groups.nunique()
    n_splits = min(splits, unique_groups)
    if n_splits < 2:
        raise ValueError("At least two sequences are required for group cross-validation")

    fold_rows = []
    predictions = dataframe.copy()
    predictions["learned_score"] = float("nan")
    splitter = GroupKFold(n_splits=n_splits)

    for fold, (train_index, test_index) in enumerate(
        splitter.split(dataframe, groups=groups), start=1
    ):
        train = dataframe.iloc[train_index]
        test = dataframe.iloc[test_index]
        score, metrics = _evaluate_fold(train, test, fold, target)
        predictions.loc[test.index, "learned_score"] = score
        fold_rows.append({"fold": fold, **metrics})

    aggregate = {
        "learned": evaluate_rankings(predictions, "learned_score"),
        "dynamic": evaluate_rankings(predictions, "geometric_score"),
        "static": evaluate_rankings(predictions, "static_score"),
        "naive": evaluate_rankings(predictions, "naive_score"),
        "folds": fold_rows,
    }
    return {"metrics": aggregate, "predictions": predictions}


def leave_one_provider_out(
    dataframe: pd.DataFrame,
    provider_column: str = "source_provider",
    target: str = "label_value",
) -> dict:
    """Train on every provider except one and evaluate transfer to the held-out provider."""
    dataframe = add_baseline_scores(dataframe)
    providers = [value for value in dataframe[provider_column].dropna().unique()]
    if len(providers) < 2:
        raise ValueError("At least two providers are required")
    predictions = dataframe.copy()
    predictions["learned_score"] = float("nan")
    rows = []
    for fold, provider in enumerate(providers, start=1):
        train = dataframe[dataframe[provider_column] != provider]
        test = dataframe[dataframe[provider_column] == provider]
        if train[target].notna().sum() == 0 or test.empty:
            continue
        score, metrics = _evaluate_fold(train, test, fold, target)
        predictions.loc[test.index, "learned_score"] = score
        rows.append({"held_out_provider": provider, "rows": len(test), **metrics})
    return {"providers": rows, "predictions": predictions}


def sequence_bootstrap_interval(
    dataframe: pd.DataFrame,
    score_column: str,
    metric_key: str = "ndcg@3",
    iterations: int = 1000,
    seed: int = 7,
) -> dict[str, float]:
    sequences = dataframe["sequence_id"].dropna().unique()
    if len(sequences) < 2:
        raise ValueError("At least two sequences are required for sequence bootstrap")
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(iterations):
        selected = rng.choice(sequences, size=len(sequences), replace=True)
        pieces = []
        for replicate_index, sequence_id in enumerate(selected):
            piece = dataframe[dataframe["sequence_id"] == sequence_id].copy()
            piece["sequence_id"] = f"bootstrap:{replicate_index}:{sequence_id}"
            pieces.append(piece)
        sampled = pd.concat(pieces, ignore_index=True)
        samples.append(evaluate_rankings(sampled, score_column)[metric_key])
    point = evaluate_rankings(dataframe, score_column)[metric_key]
    return {
        "point": float(point),
        "lower_95": float(np.quantile(samples, 0.025)),
        "upper_95": float(np.quantile(samples, 0.975)),
        "iterations": iterations,
    }


def write_report(result: dict, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result["metrics"], indent=2), encoding="utf-8")
    return output
