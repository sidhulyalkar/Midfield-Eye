from __future__ import annotations


def test_provider_and_state_modules_import_in_any_order() -> None:
    import midfielders_eye.integrations.soccernet_gsr as gsr
    import midfielders_eye.robustness as robustness
    import midfielders_eye.state as state
    from midfielders_eye.adapters import load_metrica_csv, load_soccernet_gsr

    assert gsr.load_tracker_state_gsr
    assert robustness.benchmark_degradation
    assert state.reconstruct_trajectories
    assert load_metrica_csv
    assert load_soccernet_gsr
