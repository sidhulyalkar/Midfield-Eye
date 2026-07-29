from midfielders_eye.io import options_to_dataframe
from midfielders_eye.models import add_baseline_scores
from midfielders_eye.synthetic import build_bootstrap_options, generate_dataset


def test_baseline_columns_are_added():
    frames = generate_dataset(sequences=2, frames=2)
    data = options_to_dataframe(build_bootstrap_options(frames))
    result = add_baseline_scores(data)
    assert result["naive_score"].notna().all()
    assert result["static_score"].notna().all()
