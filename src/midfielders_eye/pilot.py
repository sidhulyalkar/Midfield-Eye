from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

from .affordance import AffordanceEngine
from .io import options_to_dataframe, read_frames_jsonl

ITEM_COLUMNS = ["sequence_id", "frame_id", "option_id"]
AVAILABILITY_VALUES = {"yes", "no", "uncertain"}
VISIBILITY_VALUES = {"yes", "partial", "no", "uncertain"}
FAILURE_REASONS = {
    "corridor",
    "interception",
    "body_shape",
    "receiver_pressure",
    "offside",
    "view",
    "execution_difficulty",
    "other",
}
ALLOWED_CAUSAL_TIMINGS = {
    "focal_frame",
    "causal_history",
    "forecast_from_focal_state",
    "derived_from_declared_causal_features",
}
FORBIDDEN_CAUSAL_MARKERS = {
    "retrospective",
    "future_observed",
    "future_frame",
    "post_action",
    "selected_action",
    "label_available",
    "label_value",
    "label_selected",
    "outcome_label",
}
FUTURE_DERIVED_STATE_MARKERS = {
    *FORBIDDEN_CAUSAL_MARKERS,
    "acausal",
    "bidirectional_smoothing",
    "future_endpoint",
    "noncausal",
    "offline_interpolation",
    "smoothed_with_future",
    "uses_future_endpoint",
}
FUTURE_DERIVED_QUALITY_FLAGS = {
    "contains_interpolated_players",
}
CANDIDATE_GENERATOR_SOURCE_PATHS = (
    "src/midfielders_eye/affordance.py",
    "src/midfielders_eye/geometry.py",
    "src/midfielders_eye/schema.py",
    "src/midfielders_eye/state/state_completion.py",
    "src/midfielders_eye/io.py",
)


class AnnotationValidationError(ValueError):
    """Raised when annotation records cannot satisfy the frozen label contract."""


@dataclass(frozen=True)
class AnnotationImportReport:
    files: int
    rows: int
    items: int
    sequences: int
    frames: int
    annotators: int
    genuine_human_rows: int
    non_human_rows: int
    duplicate_ratings: int
    unknown_candidate_rows: int
    candidate_coverage: float | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnnotationImport:
    dataframe: pd.DataFrame
    report: AnnotationImportReport


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dataframe_semantic_sha256(dataframe: pd.DataFrame) -> str:
    ordered = dataframe.reindex(sorted(dataframe.columns), axis=1)
    if set(ITEM_COLUMNS).issubset(ordered.columns):
        ordered = ordered.sort_values(ITEM_COLUMNS).reset_index(drop=True)
    return canonical_sha256(ordered.to_dict("records"))


def _dataframes_semantically_equal(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    if set(left.columns) != set(right.columns) or len(left) != len(right):
        return False
    left = left.reindex(sorted(left.columns), axis=1)
    right = right.reindex(sorted(right.columns), axis=1)
    if set(ITEM_COLUMNS).issubset(left.columns):
        left = left.sort_values(ITEM_COLUMNS).reset_index(drop=True)
        right = right.sort_values(ITEM_COLUMNS).reset_index(drop=True)
    for column in left.columns:
        left_column = left[column]
        right_column = right[column]
        if pd.api.types.is_numeric_dtype(left_column) or pd.api.types.is_numeric_dtype(
            right_column
        ):
            left_numeric = pd.to_numeric(left_column, errors="coerce").to_numpy(float)
            right_numeric = pd.to_numeric(right_column, errors="coerce").to_numpy(float)
            if not np.allclose(
                left_numeric,
                right_numeric,
                rtol=1e-10,
                atol=1e-12,
                equal_nan=True,
            ):
                return False
        else:
            left_text = left_column.fillna("<NULL>").astype(str).to_numpy()
            right_text = right_column.fillna("<NULL>").astype(str).to_numpy()
            if not np.array_equal(left_text, right_text):
                return False
    return True


def validate_causal_feature_contract(
    payload: dict[str, Any],
    *,
    candidate_sha256: str,
    required_features: Iterable[str],
) -> dict[str, Any]:
    if payload.get("schema_version") != "causal-feature-contract-v1":
        raise ValueError("Causal feature contract has an unsupported schema_version")
    if payload.get("candidate_sha256") != candidate_sha256:
        raise ValueError("Causal feature contract does not bind the frozen candidate file")
    if not str(payload.get("reviewed_by", "")).strip():
        raise ValueError("Causal feature contract needs a non-empty reviewed_by")
    features = payload.get("features")
    if not isinstance(features, dict):
        raise ValueError("Causal feature contract needs a features mapping")
    required = {"geometric_score", *required_features}
    missing = sorted(required - set(features))
    if missing:
        raise ValueError(f"Causal feature contract is missing required features: {missing}")
    validated: dict[str, Any] = {}
    for feature in sorted(features):
        declaration = features[feature]
        if not isinstance(declaration, dict):
            raise ValueError(f"Causal declaration for {feature!r} must be a mapping")
        timing = str(declaration.get("timing", "")).strip()
        if timing not in ALLOWED_CAUSAL_TIMINGS:
            raise ValueError(f"Feature {feature!r} has prohibited timing {timing!r}")
        dependencies = [str(value) for value in declaration.get("dependencies", [])]
        evidence = " ".join([feature, timing, *dependencies]).casefold()
        markers = sorted(marker for marker in FORBIDDEN_CAUSAL_MARKERS if marker in evidence)
        if markers:
            raise ValueError(
                f"Feature {feature!r} uses label-derived or retrospective evidence: {markers}"
            )
        if not str(declaration.get("justification", "")).strip():
            raise ValueError(f"Feature {feature!r} needs an explicit causal justification")
        validated[feature] = {
            "timing": timing,
            "dependencies": dependencies,
            "justification": str(declaration["justification"]).strip(),
        }
    score_dependencies = set(validated["geometric_score"]["dependencies"])
    if not score_dependencies or not score_dependencies.issubset(features):
        raise ValueError(
            "geometric_score must declare non-empty dependencies present in the contract"
        )
    return validated


def candidate_generator_source_records() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    records: list[dict[str, Any]] = []
    for relative_path in CANDIDATE_GENERATOR_SOURCE_PATHS:
        path = root / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Candidate generator dependency is missing: {path}")
        records.append(
            {
                "path": relative_path,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return records


def validate_candidate_generator_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    declared = payload.get("generator_sources")
    if not isinstance(declared, list):
        raise ValueError("Causal feature contract needs generator_sources")
    actual = candidate_generator_source_records()
    declared_by_path = {str(record.get("path")): record for record in declared}
    actual_by_path = {record["path"]: record for record in actual}
    if set(declared_by_path) != set(actual_by_path):
        raise ValueError("Causal contract generator source coverage is incomplete or has extras")
    for path, record in actual_by_path.items():
        if declared_by_path[path].get("sha256") != record["sha256"]:
            raise ValueError(f"Candidate generator source hash mismatch: {path}")
    return actual


def _normalized_state_marker(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().casefold()).strip("_")


def _find_future_derived_markers(value: Any, *, path: str) -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            normalized_key = _normalized_state_marker(key)
            key_markers = sorted(
                marker
                for marker in FUTURE_DERIVED_STATE_MARKERS
                if marker in normalized_key
            )
            findings.extend(f"{key_path}={marker}" for marker in key_markers)
            findings.extend(_find_future_derived_markers(item, path=key_path))
    elif isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            findings.extend(
                _find_future_derived_markers(item, path=f"{path}[{index}]")
            )
    elif isinstance(value, str):
        normalized_value = _normalized_state_marker(value)
        value_markers = sorted(
            marker
            for marker in FUTURE_DERIVED_STATE_MARKERS
            if marker in normalized_value
        )
        findings.extend(f"{path}={marker}" for marker in value_markers)
    return findings


def validate_causal_frame_states(frames: Iterable[Any]) -> dict[str, Any]:
    """Reject frame state that cannot be known causally at the focal timestamp.

    The causal benchmark deliberately fails closed: offline interpolation and any
    equivalent future-endpoint marker are prohibited even if the current feature
    generator does not appear to consume the flagged field.
    """

    frame_list = list(frames)
    findings: list[str] = []
    player_count = 0
    for frame in frame_list:
        frame_path = f"{frame.sequence_id}:{frame.frame_id}"
        normalized_quality_flags = {
            _normalized_state_marker(flag) for flag in frame.quality_flags
        }
        forbidden_flags = sorted(
            normalized_quality_flags & FUTURE_DERIVED_QUALITY_FLAGS
        )
        findings.extend(
            f"{frame_path}.quality_flags={flag}" for flag in forbidden_flags
        )
        findings.extend(
            _find_future_derived_markers(
                frame.quality_flags,
                path=f"{frame_path}.quality_flags",
            )
        )
        findings.extend(
            _find_future_derived_markers(
                frame.metadata,
                path=f"{frame_path}.metadata",
            )
        )
        for player in frame.players:
            player_count += 1
            player_path = f"{frame_path}.players[{player.player_id}]"
            if player.tracking_status == "interpolated":
                findings.append(f"{player_path}.tracking_status=interpolated")
            if player.visibility == "interpolated":
                findings.append(f"{player_path}.visibility=interpolated")
            findings.extend(
                _find_future_derived_markers(
                    player.provenance_flags,
                    path=f"{player_path}.provenance_flags",
                )
            )
            findings.extend(
                _find_future_derived_markers(
                    player.metadata,
                    path=f"{player_path}.metadata",
                )
            )
    unique_findings = sorted(set(findings))
    if unique_findings:
        raise ValueError(
            "Causal pilot frames contain future-derived state; offline or "
            "future-endpoint interpolation is prohibited. First findings: "
            f"{unique_findings[:8]}"
        )
    return {
        "policy": "fail_closed_no_future_derived_frame_or_player_state",
        "frame_count": len(frame_list),
        "player_state_count": player_count,
        "forbidden_state_markers": sorted(FUTURE_DERIVED_STATE_MARKERS),
        "forbidden_quality_flags": sorted(FUTURE_DERIVED_QUALITY_FLAGS),
        "interpolated_tracking_status_allowed": False,
        "interpolated_visibility_allowed": False,
        "status": "passed",
    }


def validate_regenerated_candidates(
    *,
    frames_path: str | Path,
    candidates: pd.DataFrame,
    causal_features: Iterable[str],
) -> dict[str, Any]:
    """Replay the frozen generator and compare candidate identity, scores, and features."""

    frames = read_frames_jsonl(frames_path)
    causal_frame_state_audit = validate_causal_frame_states(frames)
    engine = AffordanceEngine()
    regenerated = options_to_dataframe(
        option
        for frame in frames
        for option in engine.generate(frame)
    )
    if regenerated.empty:
        raise ValueError("Candidate regeneration produced no options")
    if candidates.duplicated(ITEM_COLUMNS).any() or regenerated.duplicated(
        ITEM_COLUMNS
    ).any():
        raise ValueError("Candidate lineage requires unique option keys")
    candidate_keys = set(
        map(tuple, candidates[ITEM_COLUMNS].itertuples(index=False, name=None))
    )
    regenerated_keys = set(
        map(tuple, regenerated[ITEM_COLUMNS].itertuples(index=False, name=None))
    )
    if candidate_keys != regenerated_keys:
        missing = sorted(regenerated_keys - candidate_keys)
        extra = sorted(candidate_keys - regenerated_keys)
        raise ValueError(
            "Frozen candidate keys do not exactly regenerate: "
            f"missing={missing[:5]}, extra={extra[:5]}"
        )

    declared_features = set(causal_features)
    required_features = {"geometric_score", *AffordanceEngine.feature_names}
    if not required_features.issubset(declared_features):
        missing_features = sorted(required_features - declared_features)
        raise ValueError(
            f"Causal contract omits generated B2 features: {missing_features}"
        )
    numeric_columns = sorted(
        {
            "target_x",
            "target_y",
            "geometric_score",
            *declared_features,
        }
    )
    missing_columns = sorted(
        column
        for column in numeric_columns
        if column not in candidates.columns or column not in regenerated.columns
    )
    if missing_columns:
        raise ValueError(
            f"Frozen or regenerated candidates are missing causal values: {missing_columns}"
        )
    identity_columns = [
        "kind",
        "actor_id",
        "target_player_id",
        "source_provider",
        "source_match_id",
    ]
    missing_identity = sorted(
        column
        for column in identity_columns
        if column not in candidates.columns or column not in regenerated.columns
    )
    if missing_identity:
        raise ValueError(f"Candidate identity columns are missing: {missing_identity}")

    left = candidates.sort_values(ITEM_COLUMNS).reset_index(drop=True)
    right = regenerated.sort_values(ITEM_COLUMNS).reset_index(drop=True)
    for column in identity_columns:
        left_values = left[column].fillna("<NULL>").astype(str).to_numpy()
        right_values = right[column].fillna("<NULL>").astype(str).to_numpy()
        if not np.array_equal(left_values, right_values):
            raise ValueError(f"Candidate identity mismatch in {column!r}")
    maximum_absolute_error = 0.0
    for column in numeric_columns:
        left_values = pd.to_numeric(left[column], errors="raise").to_numpy(float)
        right_values = pd.to_numeric(right[column], errors="raise").to_numpy(float)
        if not np.isfinite(left_values).all() or not np.isfinite(right_values).all():
            raise ValueError(f"Candidate feature {column!r} contains a non-finite value")
        errors = np.abs(left_values - right_values)
        maximum_absolute_error = max(maximum_absolute_error, float(errors.max(initial=0.0)))
        if not np.allclose(
            left_values,
            right_values,
            rtol=1e-10,
            atol=1e-12,
        ):
            mismatch = int(np.flatnonzero(~np.isclose(
                left_values,
                right_values,
                rtol=1e-10,
                atol=1e-12,
            ))[0])
            raise ValueError(
                f"Candidate feature {column!r} does not regenerate for "
                f"{tuple(left.loc[mismatch, ITEM_COLUMNS])!r}"
            )
    return {
        "generator": "midfielders_eye.affordance.AffordanceEngine",
        "generator_config": asdict(engine.config),
        "generator_weights": engine.weights,
        "frame_count": len(frames),
        "candidate_count": len(regenerated),
        "compared_numeric_columns": numeric_columns,
        "compared_identity_columns": identity_columns,
        "rtol": 1e-10,
        "atol": 1e-12,
        "maximum_absolute_error": maximum_absolute_error,
        "causal_frame_state_audit": causal_frame_state_audit,
        "regenerated_candidates_semantic_sha256": _dataframe_semantic_sha256(
            regenerated[ITEM_COLUMNS + identity_columns + numeric_columns]
        ),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def _normalize_availability(value: Any) -> str:
    if isinstance(value, (bool, np.bool_)):
        return "yes" if bool(value) else "no"
    if pd.isna(value):
        raise AnnotationValidationError("label_available is missing")
    normalized = str(value).strip().casefold()
    aliases = {"true": "yes", "1": "yes", "false": "no", "0": "no"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in AVAILABILITY_VALUES:
        raise AnnotationValidationError(
            f"label_available must be one of {sorted(AVAILABILITY_VALUES)}, got {value!r}"
        )
    return normalized


def _normalize_visibility(value: Any) -> str:
    if pd.isna(value):
        raise AnnotationValidationError("label_visibility is missing")
    normalized = str(value).strip().casefold()
    if normalized not in VISIBILITY_VALUES:
        raise AnnotationValidationError(
            f"label_visibility must be one of {sorted(VISIBILITY_VALUES)}, got {value!r}"
        )
    return normalized


def _normalize_ordinal_value(row: pd.Series) -> int:
    ordinal = row.get("label_value_ordinal")
    if ordinal is not None and not pd.isna(ordinal):
        numeric = float(ordinal)
    else:
        normalized = row.get("label_value")
        if normalized is None or pd.isna(normalized):
            raise AnnotationValidationError(
                "Each row needs label_value_ordinal or normalized label_value"
            )
        normalized_float = float(normalized)
        if not 0.0 <= normalized_float <= 1.0:
            raise AnnotationValidationError("label_value must be in [0, 1]")
        numeric = normalized_float * 4.0
    rounded = round(numeric)
    if not np.isclose(numeric, rounded, atol=1e-8) or not 0 <= rounded <= 4:
        raise AnnotationValidationError("Tactical value must be an integer on the 0-4 scale")
    return int(rounded)


def is_genuine_human_annotation(row: pd.Series | dict[str, Any]) -> bool:
    provenance = str(row.get("provenance", "")).strip().casefold()
    provider = str(row.get("source_provider", "")).strip().casefold()
    forbidden_markers = ("synthetic", "pseudo", "bootstrap", "generated")
    return (
        provenance.startswith("human-annotation")
        and not any(marker in provenance for marker in forbidden_markers)
        and provider not in {"", "synthetic", "unknown", "none", "nan"}
    )


def _read_annotation_files(paths: Iterable[str | Path]) -> pd.DataFrame:
    tables: list[pd.DataFrame] = []
    for path_like in paths:
        path = Path(path_like)
        if not path.exists():
            raise FileNotFoundError(path)
        if path.suffix.casefold() == ".csv":
            table = pd.read_csv(path)
        elif path.suffix.casefold() in {".jsonl", ".ndjson"}:
            table = pd.read_json(path, lines=True)
        else:
            raise AnnotationValidationError(
                f"Unsupported annotation format {path.suffix!r}; use CSV or JSONL"
            )
        table["_annotation_file"] = path.as_posix()
        tables.append(table)
    if not tables:
        raise AnnotationValidationError("At least one annotation file is required")
    return pd.concat(tables, ignore_index=True, sort=False)


def load_annotations(
    paths: Iterable[str | Path],
    *,
    candidates: pd.DataFrame | None = None,
    require_genuine_human: bool = True,
) -> AnnotationImport:
    """Load annotations into a strict, audit-ready representation.

    Original value and availability columns are preserved under ``raw_*`` names. The normalized
    columns use categorical availability and an integer 0-4 value so agreement statistics never
    silently reinterpret ``uncertain`` as ``no``.
    """

    path_list = [Path(path) for path in paths]
    dataframe = _read_annotation_files(path_list)
    required = {
        *ITEM_COLUMNS,
        "annotator_id",
        "label_available",
        "label_visibility",
        "label_confidence",
        "provenance",
        "source_provider",
    }
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise AnnotationValidationError(f"Missing annotation columns: {missing}")
    if "label_value_ordinal" not in dataframe and "label_value" not in dataframe:
        raise AnnotationValidationError("Missing label_value_ordinal or label_value")

    dataframe = dataframe.copy()
    dataframe["sequence_id"] = dataframe["sequence_id"].astype(str).str.strip()
    dataframe["option_id"] = dataframe["option_id"].astype(str).str.strip()
    dataframe["frame_id"] = pd.to_numeric(dataframe["frame_id"], errors="raise").astype(int)
    dataframe["annotator_id"] = dataframe["annotator_id"].astype(str).str.strip()
    if dataframe["sequence_id"].eq("").any() or dataframe["option_id"].eq("").any():
        raise AnnotationValidationError("Sequence and option IDs cannot be empty")
    if dataframe["annotator_id"].isin({"", "nan", "None"}).any():
        raise AnnotationValidationError("Every rating needs a non-empty annotator_id")

    dataframe["raw_label_available"] = dataframe["label_available"]
    if "label_value" in dataframe:
        dataframe["raw_label_value"] = dataframe["label_value"]
    dataframe["label_available"] = dataframe["label_available"].map(_normalize_availability)
    dataframe["label_visibility"] = dataframe["label_visibility"].map(_normalize_visibility)
    dataframe["label_value_ordinal"] = dataframe.apply(_normalize_ordinal_value, axis=1)
    dataframe["label_value"] = dataframe["label_value_ordinal"] / 4.0
    dataframe["label_confidence"] = pd.to_numeric(
        dataframe["label_confidence"], errors="raise"
    )
    invalid_confidence = ~dataframe["label_confidence"].between(0.0, 1.0)
    if invalid_confidence.any():
        raise AnnotationValidationError("label_confidence must be in [0, 1]")

    if "label_failure_reason" in dataframe:
        reasons = dataframe["label_failure_reason"].dropna().astype(str).str.strip().str.casefold()
        invalid_reasons = sorted(set(reasons) - FAILURE_REASONS - {"", "none"})
        if invalid_reasons:
            raise AnnotationValidationError(f"Unknown failure reasons: {invalid_reasons}")

    duplicate_mask = dataframe.duplicated(ITEM_COLUMNS + ["annotator_id"], keep=False)
    duplicate_count = int(duplicate_mask.sum())
    if duplicate_count:
        example = dataframe.loc[
            duplicate_mask, ITEM_COLUMNS + ["annotator_id"]
        ].head(3).to_dict("records")
        raise AnnotationValidationError(
            f"Duplicate item/rater records are not allowed ({duplicate_count} rows): {example}"
        )

    dataframe["is_genuine_human"] = dataframe.apply(is_genuine_human_annotation, axis=1)
    genuine_rows = int(dataframe["is_genuine_human"].sum())
    non_human_rows = len(dataframe) - genuine_rows
    if require_genuine_human and non_human_rows:
        provenance = sorted(dataframe.loc[~dataframe["is_genuine_human"], "provenance"].unique())
        raise AnnotationValidationError(
            "Non-human or synthetic labels cannot enter an expert pilot freeze: "
            f"{non_human_rows} rows with provenance {provenance}"
        )

    unknown_candidate_rows = 0
    candidate_coverage: float | None = None
    warnings: list[str] = []
    if candidates is not None:
        missing_candidate_columns = sorted(set(ITEM_COLUMNS) - set(candidates.columns))
        if missing_candidate_columns:
            raise AnnotationValidationError(
                f"Candidate table is missing columns: {missing_candidate_columns}"
            )
        candidate_keys = candidates[ITEM_COLUMNS].drop_duplicates()
        annotated_keys = dataframe[ITEM_COLUMNS].drop_duplicates()
        membership = annotated_keys.merge(candidate_keys, on=ITEM_COLUMNS, how="left", indicator=True)
        unknown_candidate_rows = int((membership["_merge"] == "left_only").sum())
        if unknown_candidate_rows:
            raise AnnotationValidationError(
                f"{unknown_candidate_rows} annotated items are absent from the candidate freeze"
            )
        if "source_provider" in candidates:
            candidate_providers = candidates[
                ITEM_COLUMNS + ["source_provider"]
            ].drop_duplicates(ITEM_COLUMNS)
            provider_check = dataframe.merge(
                candidate_providers,
                on=ITEM_COLUMNS,
                how="left",
                suffixes=("_annotation", "_candidate"),
            )
            mismatch = (
                provider_check["source_provider_annotation"].astype(str)
                != provider_check["source_provider_candidate"].astype(str)
            )
            if mismatch.any():
                raise AnnotationValidationError(
                    f"{int(mismatch.sum())} annotation rows disagree with candidate provider provenance"
                )
        candidate_coverage = len(annotated_keys) / len(candidate_keys) if len(candidate_keys) else None
        if candidate_coverage is not None and candidate_coverage < 1.0:
            warnings.append(
                f"Only {candidate_coverage:.1%} of frozen candidates have at least one rating"
            )

    report = AnnotationImportReport(
        files=len(path_list),
        rows=len(dataframe),
        items=int(dataframe[ITEM_COLUMNS].drop_duplicates().shape[0]),
        sequences=int(dataframe["sequence_id"].nunique()),
        frames=int(dataframe[["sequence_id", "frame_id"]].drop_duplicates().shape[0]),
        annotators=int(dataframe["annotator_id"].nunique()),
        genuine_human_rows=genuine_rows,
        non_human_rows=non_human_rows,
        duplicate_ratings=duplicate_count,
        unknown_candidate_rows=unknown_candidate_rows,
        candidate_coverage=candidate_coverage,
        warnings=tuple(warnings),
    )
    return AnnotationImport(dataframe=dataframe, report=report)


def build_adjudication_queue(annotations: pd.DataFrame) -> pd.DataFrame:
    """Return only overlapping items with availability or ordinal-value disagreement."""

    rows: list[dict[str, Any]] = []
    for item_key, group in annotations.groupby(ITEM_COLUMNS, sort=True, dropna=False):
        if group["annotator_id"].nunique() < 2:
            continue
        availability = sorted(group["label_available"].astype(str).unique())
        values = sorted(int(value) for value in group["label_value_ordinal"].unique())
        if len(availability) == 1 and len(values) == 1:
            continue
        row = dict(zip(ITEM_COLUMNS, item_key, strict=True))
        row.update(
            {
                "kind": group["kind"].iloc[0] if "kind" in group else None,
                "rater_count": int(group["annotator_id"].nunique()),
                "availability_disagreement": len(availability) > 1,
                "value_disagreement": len(values) > 1,
                "ratings_json": json.dumps(
                    [
                        {
                            "annotator_id": record["annotator_id"],
                            "availability": record["label_available"],
                            "value_ordinal": int(record["label_value_ordinal"]),
                            "visibility": record["label_visibility"],
                            "confidence": float(record["label_confidence"]),
                        }
                        for record in group.to_dict("records")
                    ],
                    sort_keys=True,
                ),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def apply_adjudication(
    annotations: pd.DataFrame,
    decisions: pd.DataFrame,
) -> pd.DataFrame:
    """Attach explicit adjudication without mutating or replacing original ratings."""

    required = {
        *ITEM_COLUMNS,
        "adjudicator_id",
        "adjudicated_available",
        "adjudicated_value_ordinal",
        "adjudication_rationale",
    }
    missing = sorted(required - set(decisions.columns))
    if missing:
        raise AnnotationValidationError(f"Adjudication decisions are missing columns: {missing}")
    if decisions.duplicated(ITEM_COLUMNS).any():
        raise AnnotationValidationError("Only one adjudication decision is allowed per item")

    queue = build_adjudication_queue(annotations)
    queue_keys = set(map(tuple, queue[ITEM_COLUMNS].itertuples(index=False, name=None)))
    decision_keys = set(map(tuple, decisions[ITEM_COLUMNS].itertuples(index=False, name=None)))
    unexpected = decision_keys - queue_keys
    if unexpected:
        raise AnnotationValidationError(
            f"Adjudication contains {len(unexpected)} items without a recorded disagreement"
        )

    normalized = decisions.copy()
    normalized["adjudicated_available"] = normalized["adjudicated_available"].map(
        _normalize_availability
    )
    ordinal = pd.to_numeric(normalized["adjudicated_value_ordinal"], errors="raise")
    if (
        ordinal.isna().any()
        or not ordinal.between(0, 4).all()
        or not np.isclose(ordinal.to_numpy(float), np.round(ordinal.to_numpy(float))).all()
    ):
        raise AnnotationValidationError(
            "adjudicated_value_ordinal must be an integer in [0, 4]"
        )
    normalized["adjudicated_value_ordinal"] = ordinal.astype(int)
    if (
        normalized["adjudicator_id"].isna()
        | normalized["adjudicator_id"].astype(str).str.strip().eq("")
    ).any():
        raise AnnotationValidationError("Every adjudication needs an adjudicator_id")
    if (
        normalized["adjudication_rationale"].isna()
        | normalized["adjudication_rationale"].astype(str).str.strip().eq("")
    ).any():
        raise AnnotationValidationError("Every adjudication needs a rationale")
    normalized["adjudicated_value"] = normalized["adjudicated_value_ordinal"] / 4.0
    normalized["adjudication_provenance"] = "human-adjudication-v1"
    return normalized


def build_consensus_labels(
    annotations: pd.DataFrame,
    candidates: pd.DataFrame,
    adjudications: pd.DataFrame | None = None,
    *,
    min_candidate_coverage: float = 1.0,
) -> pd.DataFrame:
    """Collapse raters only after unanimous agreement or a separately recorded adjudication."""

    if "is_genuine_human" not in annotations:
        raise AnnotationValidationError(
            "Consensus labels require normalized provenance validation first"
        )
    if not annotations["is_genuine_human"].astype(bool).all():
        raise AnnotationValidationError(
            "Synthetic, pseudo, generated, or unknown-provider ratings cannot enter consensus"
        )
    if candidates.duplicated(ITEM_COLUMNS).any():
        raise AnnotationValidationError("Candidates must contain one row per option")
    candidate_keys = set(
        map(tuple, candidates[ITEM_COLUMNS].itertuples(index=False, name=None))
    )
    annotation_keys = set(
        map(tuple, annotations[ITEM_COLUMNS].drop_duplicates().itertuples(index=False, name=None))
    )
    unknown_keys = annotation_keys - candidate_keys
    if unknown_keys:
        raise AnnotationValidationError(
            "Consensus contains ratings outside the frozen candidate set"
        )
    candidate_coverage = len(annotation_keys) / len(candidate_keys) if candidate_keys else 0.0
    if candidate_coverage < min_candidate_coverage:
        raise AnnotationValidationError(
            f"Consensus candidate coverage {candidate_coverage:.3f} is below the frozen "
            f"threshold {min_candidate_coverage:.3f}"
        )
    decisions = (
        apply_adjudication(annotations, adjudications)
        if adjudications is not None and not adjudications.empty
        else pd.DataFrame()
    )
    decision_lookup = {
        tuple(row[column] for column in ITEM_COLUMNS): row
        for row in decisions.to_dict("records")
    }
    rows: list[dict[str, Any]] = []
    unresolved: list[tuple[Any, ...]] = []
    for item_key, group in annotations.groupby(ITEM_COLUMNS, sort=True, dropna=False):
        if group["annotator_id"].nunique() < 2:
            raise AnnotationValidationError(
                f"Consensus requires at least two genuine raters for item {tuple(item_key)!r}"
            )
        availability = sorted(group["label_available"].unique())
        values = sorted(int(value) for value in group["label_value_ordinal"].unique())
        decision = decision_lookup.get(tuple(item_key))
        disagrees = len(availability) > 1 or len(values) > 1
        if disagrees and decision is None:
            unresolved.append(tuple(item_key))
            continue

        candidate_match = candidates
        for column, value in zip(ITEM_COLUMNS, item_key, strict=True):
            candidate_match = candidate_match[candidate_match[column] == value]
        if len(candidate_match) != 1:
            raise AnnotationValidationError(
                f"Could not resolve exactly one frozen candidate for {tuple(item_key)!r}"
            )
        row = candidate_match.iloc[0].to_dict()
        if decision is not None:
            row["label_available"] = decision["adjudicated_available"]
            row["label_value_ordinal"] = int(decision["adjudicated_value_ordinal"])
            row["label_value"] = float(decision["adjudicated_value"])
            row["annotator_id"] = f"adjudicated:{decision['adjudicator_id']}"
            row["provenance"] = "human-adjudication-v1"
            row["adjudication_rationale"] = decision["adjudication_rationale"]
        else:
            row["label_available"] = availability[0]
            row["label_value_ordinal"] = values[0]
            row["label_value"] = values[0] / 4.0
            row["annotator_id"] = "consensus:" + ",".join(sorted(group["annotator_id"].unique()))
            row["provenance"] = "human-consensus-v1"
            row["adjudication_rationale"] = None
        visibility = sorted(group["label_visibility"].unique())
        row["label_visibility"] = visibility[0] if len(visibility) == 1 else "uncertain"
        row["label_confidence"] = float(group["label_confidence"].mean())
        row["raw_ratings_json"] = json.dumps(
            [
                {
                    "annotator_id": record["annotator_id"],
                    "label_available": record["label_available"],
                    "label_value_ordinal": int(record["label_value_ordinal"]),
                    "label_visibility": record["label_visibility"],
                    "label_confidence": float(record["label_confidence"]),
                    "provenance": record["provenance"],
                }
                for record in group.to_dict("records")
            ],
            sort_keys=True,
        )
        row["adjudicated"] = decision is not None
        rows.append(row)
    if unresolved:
        raise AnnotationValidationError(
            f"{len(unresolved)} disagreements remain unresolved; first items: {unresolved[:3]}"
        )
    return pd.DataFrame(rows)


def _frame_sequence_summary(
    frames_path: Path,
    candidates: pd.DataFrame,
    annotations: pd.DataFrame | None,
) -> list[dict[str, Any]]:
    frames = read_frames_jsonl(frames_path)
    frame_keys = {(frame.sequence_id, frame.frame_id) for frame in frames}
    candidate_frame_keys = set(
        map(
            tuple,
            candidates[["sequence_id", "frame_id"]].itertuples(index=False, name=None),
        )
    )
    missing_frame_keys = sorted(candidate_frame_keys - frame_keys)
    if missing_frame_keys:
        raise ValueError(
            "Candidate rows reference sequence/frame pairs absent from canonical frames: "
            f"{missing_frame_keys[:5]}"
        )
    summaries: list[dict[str, Any]] = []
    for sequence_id in sorted({frame.sequence_id for frame in frames}):
        sequence_frames = sorted(
            (frame for frame in frames if frame.sequence_id == sequence_id),
            key=lambda frame: (frame.period, frame.timestamp_s, frame.frame_id),
        )
        providers = sorted({frame.source_provider for frame in sequence_frames})
        matches = sorted(
            {frame.source_match_id for frame in sequence_frames if frame.source_match_id}
        )
        if len(providers) != 1:
            raise ValueError(
                f"Sequence {sequence_id!r} maps to multiple providers: {providers}"
            )
        candidate_rows = candidates[candidates["sequence_id"].astype(str) == sequence_id]
        if candidate_rows.empty:
            raise ValueError(f"Sequence {sequence_id!r} has no frozen action candidates")
        if "source_provider" in candidate_rows:
            candidate_providers = sorted(candidate_rows["source_provider"].dropna().unique())
            if candidate_providers != providers:
                raise ValueError(
                    f"Sequence {sequence_id!r} candidate provider {candidate_providers} "
                    f"does not match frame provider {providers}"
                )
        annotation_rows = (
            annotations[annotations["sequence_id"] == sequence_id]
            if annotations is not None
            else pd.DataFrame()
        )
        state_semantics = sorted(
            {
                str(frame.metadata.get("state_semantics"))
                for frame in sequence_frames
                if frame.metadata.get("state_semantics")
            }
        )
        quality_flags = sorted(
            {flag for frame in sequence_frames for flag in frame.quality_flags}
        )
        summary = {
            "sequence_id": sequence_id,
            "source_provider": providers[0],
            "source_match_ids": matches,
            "frame_count": len(sequence_frames),
            "frame_ids": [frame.frame_id for frame in sequence_frames],
            "periods": sorted({frame.period for frame in sequence_frames}),
            "start_timestamp_s": min(frame.timestamp_s for frame in sequence_frames),
            "end_timestamp_s": max(frame.timestamp_s for frame in sequence_frames),
            "frame_rates_hz": sorted(
                {frame.frame_rate_hz for frame in sequence_frames if frame.frame_rate_hz}
            ),
            "state_semantics": state_semantics or ["not_declared"],
            "quality_flags": quality_flags,
            "candidate_count": len(candidate_rows),
            "annotation_count": len(annotation_rows),
            "annotator_ids": (
                sorted(annotation_rows["annotator_id"].unique()) if not annotation_rows.empty else []
            ),
            "frames_sha256": canonical_sha256(
                [frame.to_dict() for frame in sequence_frames]
            ),
            "candidates_sha256": canonical_sha256(
                candidate_rows.sort_values(ITEM_COLUMNS).to_dict("records")
            ),
            "annotations_sha256": (
                canonical_sha256(
                    annotation_rows.sort_values(ITEM_COLUMNS + ["annotator_id"]).to_dict(
                        "records"
                    )
                )
                if not annotation_rows.empty
                else None
            ),
        }
        summaries.append(summary)

    frame_sequences = {summary["sequence_id"] for summary in summaries}
    candidate_sequences = set(candidates["sequence_id"].astype(str))
    extras = sorted(candidate_sequences - frame_sequences)
    if extras:
        raise ValueError(f"Candidate table contains sequences absent from frames: {extras}")
    return summaries


def freeze_pilot(
    *,
    frames_path: str | Path,
    candidates_path: str | Path,
    output_path: str | Path,
    annotation_paths: Iterable[str | Path] = (),
    protocol_path: str | Path | None = None,
    reliability_report_path: str | Path | None = None,
    adjudication_path: str | Path | None = None,
    consensus_path: str | Path | None = None,
    causal_feature_contract_path: str | Path | None = None,
    benchmark_config_path: str | Path | None = None,
) -> Path:
    """Write an immutable pilot manifest and refuse to overwrite an existing freeze."""

    frame_file = Path(frames_path)
    candidate_file = Path(candidates_path)
    output = Path(output_path)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite immutable pilot freeze: {output}")
    candidates = pd.read_csv(candidate_file)
    missing_candidates = sorted(set(ITEM_COLUMNS) - set(candidates.columns))
    if missing_candidates:
        raise ValueError(f"Candidate table is missing columns: {missing_candidates}")
    if candidates.duplicated(ITEM_COLUMNS).any():
        raise ValueError("Frozen candidate table must contain one row per action option")
    candidates["sequence_id"] = candidates["sequence_id"].astype(str)
    candidates["frame_id"] = pd.to_numeric(candidates["frame_id"], errors="raise").astype(int)
    causal_frame_state_audit = validate_causal_frame_states(
        read_frames_jsonl(frame_file)
    )

    annotations_list = list(annotation_paths)
    imported = (
        load_annotations(
            annotations_list,
            candidates=candidates,
            require_genuine_human=True,
        )
        if annotations_list
        else None
    )
    annotations = imported.dataframe if imported is not None else None
    sequences = _frame_sequence_summary(frame_file, candidates, annotations)

    reliability_payload: dict[str, Any] | None = None
    regenerated_consensus: pd.DataFrame | None = None
    validated_causal_features: dict[str, Any] | None = None
    generator_sources: list[dict[str, Any]] | None = None
    candidate_lineage: dict[str, Any] | None = None
    if annotations is not None:
        assert imported is not None
        required_paths = {
            "protocol_path": protocol_path,
            "reliability_report_path": reliability_report_path,
            "consensus_path": consensus_path,
            "causal_feature_contract_path": causal_feature_contract_path,
            "benchmark_config_path": benchmark_config_path,
        }
        missing_paths = sorted(name for name, value in required_paths.items() if value is None)
        if missing_paths:
            raise ValueError(
                "An expert pilot freeze requires complete evidence bindings: "
                f"{missing_paths}"
            )

        from .reliability import ReliabilityGate, reliability_report

        reliability_payload = json.loads(
            Path(reliability_report_path).read_text(encoding="utf-8")  # type: ignore[arg-type]
        )
        if reliability_payload.get("schema_version") != "inter-rater-reliability-v1":
            raise ValueError("Reliability report has an unsupported schema_version")
        report_annotation_hashes = sorted(
            record.get("sha256")
            for record in reliability_payload.get("annotation_inputs", [])
        )
        frozen_annotation_hashes = sorted(
            sha256_file(Path(path)) for path in annotations_list
        )
        if report_annotation_hashes != frozen_annotation_hashes:
            raise ValueError(
                "Reliability report annotation hashes do not exactly match the files being frozen"
            )
        candidate_input = reliability_payload.get("candidate_input")
        if not isinstance(candidate_input, dict) or candidate_input.get(
            "sha256"
        ) != sha256_file(candidate_file):
            raise ValueError(
                "Reliability report candidate hash does not match the candidate freeze"
            )
        if canonical_sha256(
            reliability_payload.get("annotation_import")
        ) != canonical_sha256(imported.report.to_dict()):
            raise ValueError("Reliability report annotation-import audit does not recompute")
        gate = ReliabilityGate(**reliability_payload.get("gate", {}))
        bootstrap_iterations = int(
            reliability_payload.get("bootstrap", {})
            .get("availability_alpha", {})
            .get("iterations", 0)
        )
        if bootstrap_iterations <= 0:
            raise ValueError("Reliability report has no valid bootstrap iteration count")
        bootstrap_seed = int(reliability_payload.get("bootstrap_seed", 7))
        recomputed_reliability = reliability_report(
            annotations,
            candidates=candidates,
            gate=gate,
            bootstrap_iterations=bootstrap_iterations,
            seed=bootstrap_seed,
        )
        for key, value in recomputed_reliability.items():
            if canonical_sha256(reliability_payload.get(key)) != canonical_sha256(value):
                raise ValueError(f"Reliability report field {key!r} does not recompute")
        if recomputed_reliability["status"] != "established":
            raise ValueError("Expert pilot freeze requires established inter-rater reliability")

        decisions = (
            pd.read_csv(adjudication_path)
            if adjudication_path is not None
            else pd.DataFrame()
        )
        regenerated_consensus = build_consensus_labels(
            annotations,
            candidates,
            decisions,
            min_candidate_coverage=gate.min_candidate_coverage,
        )
        provided_consensus = pd.read_csv(consensus_path)  # type: ignore[arg-type]
        if not _dataframes_semantically_equal(
            regenerated_consensus,
            provided_consensus,
        ):
            raise ValueError(
                "Consensus labels do not regenerate from frozen candidates, ratings, and "
                "adjudication decisions"
            )

        benchmark_config = yaml.safe_load(
            Path(benchmark_config_path).read_text(encoding="utf-8")  # type: ignore[arg-type]
        ) or {}
        required_features = benchmark_config.get("b3_features")
        if not isinstance(required_features, list) or not required_features:
            raise ValueError("Frozen benchmark config needs a non-empty b3_features list")
        causal_payload = json.loads(
            Path(causal_feature_contract_path).read_text(encoding="utf-8")  # type: ignore[arg-type]
        )
        if causal_payload.get("benchmark_config_sha256") != sha256_file(
            Path(benchmark_config_path)  # type: ignore[arg-type]
        ):
            raise ValueError(
                "Causal feature contract does not bind the frozen benchmark config"
            )
        validated_causal_features = validate_causal_feature_contract(
            causal_payload,
            candidate_sha256=sha256_file(candidate_file),
            required_features={
                *required_features,
                *AffordanceEngine.feature_names,
            },
        )
        generator_sources = validate_candidate_generator_sources(causal_payload)
        score_dependencies = set(
            validated_causal_features["geometric_score"]["dependencies"]
        )
        if not set(AffordanceEngine.feature_names).issubset(score_dependencies):
            raise ValueError(
                "geometric_score declaration omits AffordanceEngine feature dependencies"
            )
        candidate_lineage = validate_regenerated_candidates(
            frames_path=frame_file,
            candidates=candidates,
            causal_features=validated_causal_features,
        )

    input_files = [
        {
            "kind": "canonical_frames",
            "path": frame_file.as_posix(),
            "sha256": sha256_file(frame_file),
            "bytes": frame_file.stat().st_size,
        },
        {
            "kind": "action_candidates",
            "path": candidate_file.as_posix(),
            "sha256": sha256_file(candidate_file),
            "bytes": candidate_file.stat().st_size,
        },
    ]
    for annotation_path in annotations_list:
        path = Path(annotation_path)
        input_files.append(
            {
                "kind": "expert_annotations",
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    if protocol_path is not None:
        path = Path(protocol_path)
        input_files.append(
            {
                "kind": "annotation_protocol",
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    supplementary_inputs = [
        ("reliability_report", reliability_report_path),
        ("adjudication_decisions", adjudication_path),
        ("consensus_labels", consensus_path),
        ("causal_feature_contract", causal_feature_contract_path),
        ("benchmark_config", benchmark_config_path),
    ]
    for kind, path_like in supplementary_inputs:
        if path_like is None:
            continue
        path = Path(path_like)
        input_files.append(
            {
                "kind": kind,
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    if generator_sources is not None:
        root = Path(__file__).resolve().parents[2]
        for record in generator_sources:
            source_path = root / record["path"]
            input_files.append(
                {
                    "kind": "candidate_generator_source",
                    "path": source_path.as_posix(),
                    "logical_path": record["path"],
                    "sha256": record["sha256"],
                    "bytes": record["bytes"],
                }
            )

    if annotations is None:
        status = "candidate_sequences_frozen_awaiting_expert_annotations"
    else:
        status = "expert_annotations_frozen_reliability_established"

    body = {
        "schema_version": "pilot-freeze-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "scientific_contract": {
            "split_unit": "possession_sequence",
            "future_information": (
                "No future observed frame may be used by a causal feature; any retrospective "
                "feature must be explicitly labeled."
            ),
            "targets_remain_distinct": [
                "physical_availability",
                "perceptual_visibility",
                "tactical_value",
                "future_option_creation",
                "selected_action",
                "label_uncertainty",
            ],
            "value_scale": {"type": "ordinal", "minimum": 0, "maximum": 4},
            "availability_values": sorted(AVAILABILITY_VALUES),
            "visibility_values": sorted(VISIBILITY_VALUES),
            "genuine_annotation_rule": (
                "provenance starts with human-annotation; provider is non-synthetic; "
                "pseudo-labels are prohibited"
            ),
            "causality_claim": (
                "Feature timing is validated against a frozen declaration; causality is not "
                "inferred from feature names or observed outcomes."
            ),
        },
        "causal_frame_state_audit": causal_frame_state_audit,
        "sequence_count": len(sequences),
        "provider_count": len({row["source_provider"] for row in sequences}),
        "inputs": input_files,
        "annotation_import": imported.report.to_dict() if imported is not None else None,
        "evidence_bindings": (
            {
                "candidate_file_sha256": sha256_file(candidate_file),
                "consensus_file_sha256": sha256_file(Path(consensus_path)),  # type: ignore[arg-type]
                "consensus_semantic_sha256": _dataframe_semantic_sha256(
                    regenerated_consensus  # type: ignore[arg-type]
                ),
                "consensus_candidate_coverage": reliability_payload["coverage"][  # type: ignore[index]
                    "candidate_coverage"
                ],
                "benchmark_config_file_sha256": sha256_file(
                    Path(benchmark_config_path)  # type: ignore[arg-type]
                ),
                "causal_feature_contract_file_sha256": sha256_file(
                    Path(causal_feature_contract_path)  # type: ignore[arg-type]
                ),
                "causal_feature_contract_content_sha256": canonical_sha256(
                    json.loads(
                        Path(causal_feature_contract_path).read_text(encoding="utf-8")  # type: ignore[arg-type]
                    )
                ),
                "validated_causal_features": validated_causal_features,
                "candidate_generator_sources": generator_sources,
                "candidate_lineage": candidate_lineage,
                "reliability_report_file_sha256": sha256_file(
                    Path(reliability_report_path)  # type: ignore[arg-type]
                ),
            }
            if annotations is not None
            else None
        ),
        "sequences": sequences,
    }
    body["freeze_content_sha256"] = canonical_sha256(body)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_json_safe(body), indent=2), encoding="utf-8")
    return output


def verify_pilot_freeze(path: str | Path) -> list[str]:
    """Verify content, inputs, and the fail-closed causal frame-state policy."""

    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    expected_content_hash = payload.pop("freeze_content_sha256", None)
    actual_content_hash = canonical_sha256(payload)
    if expected_content_hash != actual_content_hash:
        failures.append(
            f"manifest content hash mismatch: expected {expected_content_hash}, got {actual_content_hash}"
        )
    recorded_state_audit = payload.get("causal_frame_state_audit")
    if not isinstance(recorded_state_audit, dict):
        failures.append("pilot freeze missing causal_frame_state_audit")
    kinds = [record.get("kind") for record in payload.get("inputs", [])]
    if payload.get("status") == "expert_annotations_frozen_reliability_established":
        required_kinds = {
            "canonical_frames",
            "action_candidates",
            "expert_annotations",
            "annotation_protocol",
            "reliability_report",
            "consensus_labels",
            "causal_feature_contract",
            "benchmark_config",
            "candidate_generator_source",
        }
        missing_kinds = sorted(required_kinds - set(kinds))
        if missing_kinds:
            failures.append(f"established freeze missing input kinds: {missing_kinds}")
        if not payload.get("evidence_bindings"):
            failures.append("established freeze missing evidence_bindings")
        source_records = [
            record
            for record in payload.get("inputs", [])
            if record.get("kind") == "candidate_generator_source"
        ]
        expected_paths = set(CANDIDATE_GENERATOR_SOURCE_PATHS)
        observed_paths = {record.get("logical_path") for record in source_records}
        if observed_paths != expected_paths:
            failures.append("candidate generator source dependency coverage mismatch")
        bindings = payload.get("evidence_bindings") or {}
        if not bindings.get("candidate_lineage"):
            failures.append("established freeze missing candidate_lineage evidence")
    for record in payload.get("inputs", []):
        input_path = Path(record["path"])
        if not input_path.is_absolute():
            candidates = [input_path, manifest_path.parent / input_path]
            input_path = next((candidate for candidate in candidates if candidate.exists()), input_path)
        if not input_path.exists():
            failures.append(f"missing input: {record['path']}")
            continue
        actual = sha256_file(input_path)
        if actual != record["sha256"]:
            failures.append(
                f"input hash mismatch for {record['path']}: expected {record['sha256']}, got {actual}"
            )
        if record.get("kind") == "canonical_frames":
            try:
                recomputed_state_audit = validate_causal_frame_states(
                    read_frames_jsonl(input_path)
                )
                if canonical_sha256(recomputed_state_audit) != canonical_sha256(
                    recorded_state_audit
                ):
                    failures.append("causal frame-state audit does not recompute")
            except ValueError as exc:
                failures.append(f"causal frame-state policy violation: {exc}")
    return failures
