from midfielders_eye.experiment import cross_validate
from midfielders_eye.io import options_to_dataframe
from midfielders_eye.synthetic import build_bootstrap_options, generate_dataset


def test_grouped_cross_validation_runs():
    frames = generate_dataset(sequences=4, frames=3, seed=11)
    options = build_bootstrap_options(frames)
    result = cross_validate(options_to_dataframe(options), splits=2)
    assert set(result["metrics"]) == {"learned", "dynamic", "static", "naive", "folds"}
    assert result["predictions"]["learned_score"].notna().all()
