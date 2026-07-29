from midfielders_eye.counterfactual import positioning_uplift, radial_candidate_positions
from midfielders_eye.synthetic import generate_sequence


def test_positioning_uplift_returns_candidate_results():
    frame = generate_sequence(0, frames=1)[0]
    teammate = frame.teammates()[0]
    candidates = radial_candidate_positions(teammate, radii=(2.0,), angles=4)
    result = positioning_uplift(frame, teammate.player_id, candidates)
    assert len(result) == 4
    assert all("uplift" in row for row in result)


def test_counterfactual_plot_runs(tmp_path):
    from midfielders_eye.visualization import plot_positioning_uplift

    frame = generate_sequence(0, frames=1)[0]
    output = tmp_path / "uplift.png"
    _, _, uplift = plot_positioning_uplift(
        frame, frame.teammates()[0].player_id, output, grid_size=4
    )
    assert output.exists()
    assert uplift.shape == (4, 4)
