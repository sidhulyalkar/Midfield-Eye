
from midfielders_eye.affordance import AffordanceEngine
from midfielders_eye.io import options_to_dataframe
from midfielders_eye.multisource_demo import generate_provider_views
from midfielders_eye.provider_benchmark import benchmark_provider_frames
from midfielders_eye.quality import assess_frames
from midfielders_eye.temporal import option_lifetimes, temporal_rank_metrics


def test_quality_detects_partial_and_extrapolated_data() -> None:
    providers = generate_provider_views(sequences=2, frames_per_sequence=6)
    report = assess_frames(providers["skillcorner_demo"], "skillcorner_demo")
    assert report.metrics["partial_visibility_fraction"] == 1.0
    assert report.metrics["extrapolated_player_fraction"] > 0


def test_provider_benchmark_combines_modalities() -> None:
    providers = generate_provider_views(sequences=2, frames_per_sequence=6)
    summary, options = benchmark_provider_frames(providers)
    assert set(summary["provider_id"]) == set(providers)
    assert options["source_provider"].nunique() == 4


def test_temporal_metrics_and_lifetimes() -> None:
    frames = generate_provider_views(sequences=2, frames_per_sequence=6)["metrica_demo"]
    engine = AffordanceEngine()
    options = options_to_dataframe([option for frame in frames for option in engine.generate(frame)])
    metrics = temporal_rank_metrics(options)
    assert 0 <= metrics["top3_jaccard"] <= 1
    lifetimes = option_lifetimes(options)
    assert not lifetimes.empty
    assert lifetimes["lifetime_frames"].max() >= 2
