from midfielders_eye.showcase.catalog import EMPHASIS_AXES, load_player_catalog


def test_player_catalog_has_100_balanced_candidates_and_featured_core():
    catalog = load_player_catalog()
    assert len(catalog.players) == 100
    assert catalog.cohort_balance == {"men's game": 50, "women's game": 50}
    assert {"michael-olise", "rodri", "pedri", "aitana-bonmati", "yui-hasegawa"}.issubset(
        {player.id for player in catalog.players if player.featured}
    )
    assert all(player.evidence_status == "hypothesis_only" for player in catalog.players)
    assert all(set(player.showcase_emphasis) == EMPHASIS_AXES for player in catalog.players)
    assert "not an objective ordinal ranking" in catalog.ranking_policy.lower()
