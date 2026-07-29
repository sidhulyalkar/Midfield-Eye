from midfielders_eye.experiment import leave_one_provider_out, sequence_bootstrap_interval
from midfielders_eye.io import options_to_dataframe
from midfielders_eye.synthetic import build_bootstrap_options, generate_dataset


def test_sequence_bootstrap_returns_interval() -> None:
    frames = generate_dataset(sequences=4, frames=5)
    dataframe = options_to_dataframe(build_bootstrap_options(frames))
    result = sequence_bootstrap_interval(dataframe, "geometric_score", iterations=30)
    assert result["lower_95"] <= result["point"] <= result["upper_95"]


def test_leave_one_provider_out() -> None:
    frames = generate_dataset(sequences=6, frames=5)
    dataframe = options_to_dataframe(build_bootstrap_options(frames))
    dataframe.loc[dataframe["sequence_id"].isin(["synthetic_00", "synthetic_01", "synthetic_02"]), "source_provider"] = "provider_a"
    dataframe.loc[dataframe["source_provider"] != "provider_a", "source_provider"] = "provider_b"
    result = leave_one_provider_out(dataframe)
    assert len(result["providers"]) == 2
