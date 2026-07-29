from __future__ import annotations

from midfielders_eye.synthetic import generate_dataset


def test_canonical_contract_aliases_and_nested_export() -> None:
    frame = generate_dataset(sequences=1, frames=1, seed=14)[0]
    payload = frame.to_canonical_dict()
    assert payload["match_id"] == frame.match_id
    assert payload["pitch_length_m"] == 105.0
    assert payload["ball"]["carrier_id"] == frame.ball_carrier_id
    assert frame.carrier.x_m == frame.carrier.x
    assert frame.carrier.team_id == frame.carrier.team
