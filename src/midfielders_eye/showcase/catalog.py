from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

EMPHASIS_AXES = {
    "scanning",
    "gaze_timing",
    "body_mechanics",
    "adaptation",
    "tempo_direction",
    "orchestration",
    "manipulation",
    "off_ball",
    "physical_execution",
    "final_action",
}


@dataclass(slots=True)
class PlayerStudy:
    id: str
    name: str
    cohort: str
    display_role: str
    primary_archetype: str
    signature: str
    talent_lenses: list[str] = field(default_factory=list)
    adaptation_lenses: list[str] = field(default_factory=list)
    gaze_lenses: list[str] = field(default_factory=list)
    body_mechanics_lenses: list[str] = field(default_factory=list)
    orchestration_lenses: list[str] = field(default_factory=list)
    physical_lenses: list[str] = field(default_factory=list)
    study_questions: list[str] = field(default_factory=list)
    showcase_emphasis: dict[str, float] = field(default_factory=dict)
    secondary_archetypes: list[str] = field(default_factory=list)
    featured: bool = False
    official_profile: str | None = None
    evidence_status: str = "hypothesis_only"
    profile_status: str = "editorial_research_hypothesis"
    selection_basis: str = "elite_midfield_study_cohort_2025_26"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlayerStudy":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            cohort=str(payload.get("cohort", "unspecified")),
            display_role=str(payload["display_role"]),
            primary_archetype=str(payload["primary_archetype"]),
            signature=str(payload.get("signature", "Research profile awaiting evidence.")),
            talent_lenses=[str(value) for value in payload.get("talent_lenses", [])],
            adaptation_lenses=[str(value) for value in payload.get("adaptation_lenses", [])],
            gaze_lenses=[str(value) for value in payload.get("gaze_lenses", [])],
            body_mechanics_lenses=[str(value) for value in payload.get("body_mechanics_lenses", [])],
            orchestration_lenses=[str(value) for value in payload.get("orchestration_lenses", [])],
            physical_lenses=[str(value) for value in payload.get("physical_lenses", [])],
            study_questions=[str(value) for value in payload.get("study_questions", [])],
            showcase_emphasis={str(key): float(value) for key, value in payload.get("showcase_emphasis", {}).items()},
            secondary_archetypes=[str(value) for value in payload.get("secondary_archetypes", [])],
            featured=bool(payload.get("featured", False)),
            official_profile=(None if payload.get("official_profile") in {None, ""} else str(payload["official_profile"])),
            evidence_status=str(payload.get("evidence_status", "hypothesis_only")),
            profile_status=str(payload.get("profile_status", "editorial_research_hypothesis")),
            selection_basis=str(payload.get("selection_basis", "elite_midfield_study_cohort_2025_26")),
        )

    def validate(self) -> None:
        if self.cohort not in {"men's game", "women's game"}:
            raise ValueError(f"invalid cohort for {self.id}: {self.cohort}")
        if self.evidence_status not in {"hypothesis_only", "measured", "mixed"}:
            raise ValueError(f"invalid evidence_status for {self.id}")
        if not self.signature.strip():
            raise ValueError(f"player {self.id} needs a signature")
        if len(self.talent_lenses) < 3:
            raise ValueError(f"player {self.id} needs at least three talent lenses")
        if not self.study_questions:
            raise ValueError(f"player {self.id} needs at least one study question")
        missing = EMPHASIS_AXES - set(self.showcase_emphasis)
        if missing:
            raise ValueError(f"player {self.id} missing showcase-emphasis axes: {sorted(missing)}")
        for axis, value in self.showcase_emphasis.items():
            if axis not in EMPHASIS_AXES:
                raise ValueError(f"unknown showcase-emphasis axis {axis!r} for {self.id}")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"showcase-emphasis value for {self.id}/{axis} must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cohort": self.cohort,
            "display_role": self.display_role,
            "primary_archetype": self.primary_archetype,
            "secondary_archetypes": self.secondary_archetypes,
            "signature": self.signature,
            "talent_lenses": self.talent_lenses,
            "adaptation_lenses": self.adaptation_lenses,
            "gaze_lenses": self.gaze_lenses,
            "body_mechanics_lenses": self.body_mechanics_lenses,
            "orchestration_lenses": self.orchestration_lenses,
            "physical_lenses": self.physical_lenses,
            "study_questions": self.study_questions,
            "showcase_emphasis": self.showcase_emphasis,
            "showcase_emphasis_status": "illustrative_archetype_emphasis_not_player_rating",
            "featured": self.featured,
            "official_profile": self.official_profile,
            "evidence_status": self.evidence_status,
            "profile_status": self.profile_status,
            "selection_basis": self.selection_basis,
        }


@dataclass(slots=True)
class PlayerCatalog:
    version: int
    updated_at: str
    title: str
    purpose: str
    ranking_policy: str
    cohort_balance: dict[str, int]
    source_anchors: list[dict[str, str]]
    players: list[PlayerStudy]

    def validate(self) -> None:
        if len(self.players) != 100:
            raise ValueError(f"showcase catalog must include exactly 100 study candidates; got {len(self.players)}")
        ids = [player.id for player in self.players]
        if len(ids) != len(set(ids)):
            raise ValueError("player catalog IDs must be unique")
        names = [player.name for player in self.players]
        if len(names) != len(set(names)):
            raise ValueError("player catalog names must be unique")
        if not any(player.featured for player in self.players):
            raise ValueError("at least one player must be featured")
        cohort_counts: dict[str, int] = {}
        signatures: set[str] = set()
        for player in self.players:
            player.validate()
            cohort_counts[player.cohort] = cohort_counts.get(player.cohort, 0) + 1
            if player.signature in signatures:
                raise ValueError(f"duplicate player signature: {player.signature}")
            signatures.add(player.signature)
        if cohort_counts != self.cohort_balance:
            raise ValueError(f"cohort counts {cohort_counts} do not match declared balance {self.cohort_balance}")
        if set(cohort_counts) != {"men's game", "women's game"}:
            raise ValueError("catalog must represent both men's and women's game cohorts")

    def get(self, player_id: str) -> PlayerStudy:
        for player in self.players:
            if player.id == player_id:
                return player
        raise KeyError(player_id)

    def filter(
        self,
        *,
        cohort: str | None = None,
        archetype: str | None = None,
        featured_only: bool = False,
    ) -> list[PlayerStudy]:
        players = self.players
        if cohort is not None:
            players = [player for player in players if player.cohort == cohort]
        if archetype is not None:
            players = [player for player in players if player.primary_archetype == archetype]
        if featured_only:
            players = [player for player in players if player.featured]
        return players

    def get_archetypes(self) -> list[str]:
        return sorted({player.primary_archetype for player in self.players})

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "title": self.title,
            "purpose": self.purpose,
            "ranking_policy": self.ranking_policy,
            "cohort_balance": self.cohort_balance,
            "source_anchors": self.source_anchors,
            "player_count": len(self.players),
            "archetypes": self.get_archetypes(),
            "players": [player.to_dict() for player in self.players],
        }


def default_catalog_path() -> Path:
    return Path(__file__).resolve().with_name("player_catalog.yaml")


def load_player_catalog(path: str | Path | None = None) -> PlayerCatalog:
    catalog_path = Path(path) if path is not None else default_catalog_path()
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    catalog = PlayerCatalog(
        version=int(payload["version"]),
        updated_at=str(payload["updated_at"]),
        title=str(payload.get("title", "100 Elite Midfielder Study Atlas")),
        purpose=str(payload["purpose"]),
        ranking_policy=str(payload.get("ranking_policy", "Not an ordinal ranking.")),
        cohort_balance={str(key): int(value) for key, value in payload.get("cohort_balance", {}).items()},
        source_anchors=[{str(key): str(value) for key, value in row.items()} for row in payload.get("source_anchors", [])],
        players=[PlayerStudy.from_dict(row) for row in payload["players"]],
    )
    catalog.validate()
    return catalog
