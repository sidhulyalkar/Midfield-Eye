from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..affordance import AffordanceEngine
from ..schema import FrameState
from .catalog import load_player_catalog
from .scenarios import SCENARIOS


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[Any]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def create_app(bundle_dir: str | Path = "artifacts/showcase"):
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import FileResponse
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Install frontend dependencies with `pip install -e '.[showcase]'`") from exc

    root = Path(bundle_dir).resolve()
    app = FastAPI(
        title="The Midfielder's Eye Showcase API",
        version="0.6.0",
        description="100-player perception atlas, empirical evidence studio, governed gaze/pose/biomechanics sources, and canonical-frame affordance endpoint.",
    )
    configured_origins = os.getenv(
        "MIDFIELDERS_EYE_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    )
    allowed_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=os.getenv("MIDFIELDERS_EYE_CORS_ORIGIN_REGEX"),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": "0.6.0", "bundle_exists": (root / "manifest.json").exists()}

    @app.get("/api/showcase/manifest")
    def manifest() -> Any:
        path = root / "manifest.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the showcase bundle first")
        return _read_json(path)

    @app.get("/api/atlas")
    def atlas() -> Any:
        path = root / "players" / "index.json"
        return _read_json(path) if path.exists() else [player.to_dict() for player in load_player_catalog().players]

    @app.get("/api/archetypes")
    def archetypes() -> Any:
        catalog = load_player_catalog()
        return {
            "archetypes": catalog.get_archetypes(),
            "comparison_axes": sorted(next(iter(catalog.players)).showcase_emphasis),
            "comparison_status": "illustrative_archetype_emphasis_not_player_rating",
        }

    @app.get("/api/players")
    def players(
        cohort: str | None = Query(default=None),
        archetype: str | None = Query(default=None),
        featured_only: bool = Query(default=False),
    ) -> Any:
        catalog = load_player_catalog()
        selected = catalog.filter(cohort=cohort, archetype=archetype, featured_only=featured_only)
        return {
            "title": catalog.title,
            "ranking_policy": catalog.ranking_policy,
            "count": len(selected),
            "players": [player.to_dict() for player in selected],
        }

    @app.get("/api/players/{player_id}")
    def player(player_id: str) -> Any:
        path = root / "players" / player_id / "profile.json"
        if path.exists():
            return _read_json(path)
        try:
            return load_player_catalog().get(player_id).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown player") from exc

    @app.get("/api/players/{player_id}/profile-card")
    def player_profile_card(player_id: str):
        path = (root / "players" / player_id / "profile.svg").resolve()
        if root not in path.parents or not path.exists():
            raise HTTPException(status_code=404, detail="Build the showcase bundle first")
        return FileResponse(path, media_type="image/svg+xml")

    @app.get("/api/scenarios")
    def scenarios() -> Any:
        path = root / "scenarios" / "index.json"
        return _read_json(path) if path.exists() else [scenario.to_dict() for scenario in SCENARIOS.values()]

    @app.get("/api/scenarios/{scenario_id}")
    def scenario(scenario_id: str) -> Any:
        path = root / "scenarios" / scenario_id / "scenario.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Unknown or unbuilt scenario")
        return _read_json(path)

    @app.get("/api/scenarios/{scenario_id}/frames")
    def frames(scenario_id: str) -> Any:
        path = root / "scenarios" / scenario_id / "frames.jsonl"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Unknown or unbuilt scenario")
        return _read_jsonl(path)

    def _scenario_payload(scenario_id: str, filename: str) -> Any:
        path = root / "scenarios" / scenario_id / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Unknown or unbuilt scenario")
        return _read_json(path)

    @app.get("/api/scenarios/{scenario_id}/timeline")
    def timeline(scenario_id: str) -> Any:
        return _scenario_payload(scenario_id, "timeline.json")

    @app.get("/api/scenarios/{scenario_id}/options")
    def options(scenario_id: str) -> Any:
        return _scenario_payload(scenario_id, "options.json")

    @app.get("/api/scenarios/{scenario_id}/gaze")
    def gaze(scenario_id: str) -> Any:
        return _scenario_payload(scenario_id, "gaze.json")

    @app.get("/api/scenarios/{scenario_id}/body-mechanics")
    def body_mechanics(scenario_id: str) -> Any:
        return _scenario_payload(scenario_id, "body_mechanics.json")

    @app.get("/api/scenarios/{scenario_id}/relational-control")
    def relational_control(scenario_id: str) -> Any:
        return _scenario_payload(scenario_id, "relational_control.json")

    @app.get("/api/empirical")
    def empirical_manifest() -> Any:
        path = root / "empirical" / "manifest.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the empirical showcase first")
        return _read_json(path)

    @app.get("/api/empirical/sources")
    def empirical_sources() -> Any:
        path = root / "empirical" / "sources.json"
        if not path.exists():
            from ..empirical.registry import load_source_registry
            return load_source_registry().to_dict()
        return _read_json(path)

    @app.get("/api/empirical/experiments")
    def empirical_experiments() -> Any:
        path = root / "empirical" / "experiments.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the empirical showcase first")
        return _read_json(path)

    @app.get("/api/empirical/experiments/{experiment_id}")
    def empirical_experiment(experiment_id: str) -> Any:
        path = root / "empirical" / "experiments.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the empirical showcase first")
        for experiment in _read_json(path):
            if experiment["id"] == experiment_id:
                return experiment
        raise HTTPException(status_code=404, detail="Unknown empirical experiment")

    @app.get("/api/empirical/player-ledger")
    def empirical_player_ledger() -> Any:
        path = root / "empirical" / "player_evidence_ledger.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the empirical showcase first")
        return _read_json(path)

    @app.get("/api/empirical/claim-contract")
    def empirical_claim_contract() -> Any:
        path = root / "empirical" / "claim_contract.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the empirical showcase first")
        return _read_json(path)

    @app.get("/api/empirical/citations")
    def empirical_citations() -> Any:
        path = root / "empirical" / "citation_index.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the empirical showcase first")
        return _read_json(path)

    @app.get("/api/empirical/alignment-contract")
    def empirical_alignment_contract() -> Any:
        path = root / "empirical" / "alignment_contract.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Build the empirical showcase first")
        return _read_json(path)

    @app.get("/api/capture-protocol/default")
    def default_capture_protocol() -> Any:
        from ..empirical.capture import default_midfield_capture_protocol, validate_capture_protocol

        protocol = default_midfield_capture_protocol()
        return {
            "protocol": protocol.to_dict(),
            "valid": not validate_capture_protocol(protocol),
            "errors": validate_capture_protocol(protocol),
        }

    @app.post("/api/capture-protocol/validate")
    def validate_capture_protocol_payload(payload: dict[str, Any]) -> Any:
        from ..empirical.capture import protocol_from_dict, validate_capture_protocol

        try:
            protocol = protocol_from_dict(payload)
            errors = validate_capture_protocol(protocol)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"valid": not errors, "errors": errors, "protocol_id": protocol.protocol_id}

    @app.get("/api/assets/{asset_path:path}")
    def asset(asset_path: str):
        path = (root / asset_path).resolve()
        if root not in path.parents or not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Asset not found")
        return FileResponse(path)

    @app.post("/api/analyze-frame")
    def analyze_frame(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            frame = FrameState.from_dict(payload)
            frame.validate()
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        options = AffordanceEngine().generate(frame)
        ranked = sorted(options, key=lambda option: option.geometric_score, reverse=True)
        return {
            "frame_id": frame.frame_id,
            "sequence_id": frame.sequence_id,
            "options": [
                {
                    "rank": rank,
                    "option_id": option.option_id,
                    "kind": option.kind,
                    "target_player_id": option.target_player_id,
                    "target": [option.target_x, option.target_y],
                    "score": option.geometric_score,
                    "features": option.features,
                }
                for rank, option in enumerate(ranked, start=1)
            ],
        }

    return app
