from __future__ import annotations

from .base import ProviderCapabilities, ProviderSpec

PROVIDERS: dict[str, ProviderSpec] = {
    "metrica": ProviderSpec(
        provider_id="metrica",
        display_name="Metrica Sports Sample Data",
        access="open",
        coverage="full_tracking",
        native_rate_hz=25.0,
        capabilities=ProviderCapabilities(True, True, True, True, True, True, False),
        license_note="External data terms apply; code does not redistribute match data.",
        homepage="https://github.com/metrica-sports/sample-data",
        recommended_use="First full-tracking affordance benchmark and synchronized event validation.",
        limitations=("Anonymized teams and players", "Small number of sample matches"),
    ),
    "skillcorner": ProviderSpec(
        provider_id="skillcorner",
        display_name="SkillCorner Open Data",
        access="open",
        coverage="partial_tracking",
        native_rate_hz=10.0,
        capabilities=ProviderCapabilities(True, True, True, True, True, False, True),
        license_note="External data terms apply; cite SkillCorner when publishing analyses.",
        homepage="https://github.com/SkillCorner/opendata",
        recommended_use="Broadcast-view visibility, extrapolation uncertainty, and off-ball movement tests.",
        limitations=("Broadcast coverage is partial", "Identity and extrapolation errors require QC"),
    ),
    "statsbomb360": ProviderSpec(
        provider_id="statsbomb360",
        display_name="StatsBomb Open Data + 360",
        access="open",
        coverage="event_snapshot",
        native_rate_hz=None,
        capabilities=ProviderCapabilities(False, True, False, False, True, False, True),
        license_note="StatsBomb attribution requirements apply.",
        homepage="https://github.com/hudl/open-data",
        recommended_use="Large event-centered option-set supervision and visible-area studies.",
        limitations=("Sparse event snapshots", "No temporal velocity", "Only visible players are included"),
    ),
    "sportec_open": ProviderSpec(
        provider_id="sportec_open",
        display_name="Sportec Open DFL Tracking and Event Data",
        access="open",
        coverage="full_tracking",
        native_rate_hz=25.0,
        capabilities=ProviderCapabilities(True, True, True, True, True, True, False),
        license_note="External dataset terms apply; loaded through optional Kloppy integration.",
        homepage="https://kloppy.pysport.org/user-guide/loading-data/sportec/",
        recommended_use="High-quality cross-provider replication on seven German professional matches.",
        limitations=("Optional dependency", "Provider metadata must be preserved"),
    ),
    "soccertrack_v2": ProviderSpec(
        provider_id="soccertrack_v2",
        display_name="SoccerTrack v2",
        access="open",
        coverage="video_gsr",
        native_rate_hz=25.0,
        capabilities=ProviderCapabilities(True, True, True, False, False, True, True),
        license_note="Dataset is CC BY 4.0; code is MIT according to the project repository.",
        homepage="https://github.com/AtomScott/SoccerTrack-v2",
        recommended_use="Full-pitch panoramic game-state reconstruction and event-aligned affordance snapshots.",
        limitations=("Ball state is not present in GSR records", "Possession must come from BAS or a sidecar"),
    ),
    "soccernet_gsr": ProviderSpec(
        provider_id="soccernet_gsr",
        display_name="SoccerNet Game State Reconstruction",
        access="registration",
        coverage="video_gsr",
        native_rate_hz=25.0,
        capabilities=ProviderCapabilities(True, False, True, False, False, False, True),
        license_note="SoccerNet data terms apply; sn-gamestate is GPLv3 and remains an external process.",
        homepage="https://github.com/SoccerNet/sn-gamestate",
        recommended_use="Broadcast ingestion, perception benchmarking, controlled degradation, and partial-state research.",
        limitations=("Camera view is partial", "Ball and possession sidecars are required for affordance scoring", "Tactical errors can amplify sub-metre localization errors"),
    ),
    "kloppy": ProviderSpec(
        provider_id="kloppy",
        display_name="Kloppy Provider Bridge",
        access="owned",
        coverage="full_tracking",
        native_rate_hz=None,
        capabilities=ProviderCapabilities(True, True, True, True, False, True, False),
        license_note="Each upstream provider retains its own data rights and terms.",
        homepage="https://kloppy.pysport.org/",
        recommended_use="Bring licensed or owned vendor feeds into the canonical Midfielder's Eye contract.",
        limitations=("Capabilities vary by vendor", "Event-tracking alignment may need provider-specific logic"),
    ),
    "egotraj": ProviderSpec(
        provider_id="egotraj",
        display_name="EgoTraj",
        access="registration",
        coverage="auxiliary",
        native_rate_hz=None,
        capabilities=ProviderCapabilities(False, False, True, False, False, False, True, True, True),
        license_note="External dataset terms apply.",
        homepage="https://arxiv.org/abs/2605.19004",
        recommended_use="Pretrain egocentric gaze-motion and future-trajectory representations before soccer transfer.",
        limitations=("Not a soccer dataset", "Cannot validate football tactics directly"),
    ),
}


def get_provider(provider_id: str) -> ProviderSpec:
    try:
        return PROVIDERS[provider_id]
    except KeyError as exc:
        raise KeyError(f"Unknown provider {provider_id!r}; choose from {sorted(PROVIDERS)}") from exc


def provider_rows() -> list[dict]:
    return [PROVIDERS[key].to_dict() for key in sorted(PROVIDERS)]
