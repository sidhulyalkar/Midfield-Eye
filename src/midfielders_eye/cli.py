from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from .adapters import (
    PROVIDERS,
    load_metrica_csv,
    load_skillcorner_open,
    load_soccernet_gsr,
    load_soccertrack_v2,
    load_sportec_open,
    load_statsbomb_360,
)
from .affordance import AffordanceEngine
from .dataset_shift import provider_shift_report
from .experiment import cross_validate, sequence_bootstrap_interval, write_report
from .io import (
    options_to_dataframe,
    read_frames_jsonl,
    write_frames_jsonl,
    write_frames_parquet,
    write_options_csv,
)
from .models import LearnedOptionModel
from .integrations.soccernet_gsr import (
    load_tracker_state_gsr,
    read_tracker_state,
    write_tracker_state_manifest,
)
from .multisource_demo import generate_provider_views
from .provider_benchmark import benchmark_provider_frames
from .quality import assess_frames
from .robustness import benchmark_degradation, default_degradation_suite
from .state.camera import detect_camera_cuts
from .state.possession import write_possession_sidecar_template
from .state.temporal_smoothing import interpolate_short_gaps, reconstruct_trajectories
from .synthetic import build_bootstrap_options, generate_dataset
from .temporal import temporal_rank_metrics
from .visualization import plot_affordance_frame, plot_positioning_uplift
from .showcase import build_showcase_bundle, load_player_catalog
from .showcase.media import (
    MediaManifest,
    create_media_template,
    discover_youtube_videos,
    load_media_manifest,
    write_media_manifest,
)
from .showcase.openapi import write_frontend_contract
from .empirical.capture import write_capture_protocol
from .empirical.downloads import AccessGateError, download_open_source, source_plan
from .empirical.provenance import verify_file_manifest
from .empirical.registry import load_source_registry
from .empirical.schemas import AccessMode, SignalModality
from .empirical.showcase import build_empirical_showcase

app = typer.Typer(no_args_is_help=True, help="Dynamic soccer affordance field toolkit.")
console = Console()


@app.command("capture-protocol")
def capture_protocol(
    output_path: Path = typer.Option(
        Path("data/empirical/capture_protocol.json"), "--output"
    ),
    participant_id: str = typer.Option("participant-placeholder", "--participant-id"),
) -> None:
    """Write a validated direct-gaze and biomechanics pilot protocol."""
    from .empirical.capture import protocol_from_dict, validate_capture_protocol

    path = write_capture_protocol(output_path, participant_id=participant_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_capture_protocol(protocol_from_dict(payload))
    console.print_json(
        json.dumps(
            {
                "path": str(path),
                "valid": not errors,
                "errors": errors,
                "participant_id": participant_id,
            }
        )
    )
    if errors:
        raise typer.Exit(code=1)


@app.command("empirical-sources")
def empirical_sources(
    modality: str | None = typer.Option(None, "--modality"),
    access: str | None = typer.Option(None, "--access"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List authoritative empirical sources and the claims each can support."""
    registry = load_source_registry()
    selected = registry.filter(
        modality=None if modality is None else SignalModality(modality),
        access=None if access is None else AccessMode(access),
    )
    if as_json:
        console.print_json(json.dumps([source.to_dict() for source in selected]))
        return
    table = Table(title="Midfielder's Eye · empirical source registry")
    table.add_column("Source")
    table.add_column("Access")
    table.add_column("Signals")
    table.add_column("Best use")
    table.add_column("Auto")
    for source in selected:
        table.add_row(
            source.name,
            source.access.value,
            ", ".join(modality.value for modality in source.modalities),
            source.best_for[0] if source.best_for else "",
            "yes" if source.can_auto_download else "human gate",
        )
    console.print(table)


@app.command("empirical-plan")
def empirical_plan(source_id: str) -> None:
    """Print the access, license, commands, and human steps for one dataset."""
    console.print_json(json.dumps(source_plan(source_id)))


@app.command("empirical-download")
def empirical_download(
    source_id: str,
    output_dir: Path = typer.Option(Path("data/raw"), "--output-dir"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Download only sources whose registry permits unattended open retrieval."""
    try:
        result = download_open_source(source_id, output_dir, overwrite=overwrite)
    except AccessGateError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(json.dumps({"source_id": result.source_id, "output_dir": str(result.output_dir), "files": [str(path) for path in result.files]}))


@app.command("empirical-validate")
def empirical_validate(manifest_path: Path) -> None:
    """Verify the hashes in an empirical bundle manifest."""
    failures = verify_file_manifest(manifest_path)
    if failures:
        console.print_json(json.dumps({"valid": False, "failures": failures}))
        raise typer.Exit(code=1)
    console.print_json(json.dumps({"valid": True, "manifest": str(manifest_path)}))


@app.command("empirical-build")
def empirical_build(
    output_dir: Path = typer.Option(Path("artifacts/showcase/empirical"), "--output-dir"),
    data_root: Path = typer.Option(Path("data/empirical"), "--data-root"),
    render_dpi: int = typer.Option(200, min=100, max=300),
) -> None:
    """Build real-source showcase views, evidence ledgers, citations, and claim boundaries."""
    manifest = build_empirical_showcase(output_dir, data_root=data_root, render_dpi=render_dpi)
    console.print_json(manifest.read_text(encoding="utf-8"))


@app.command("showcase-build")
def showcase_build(
    output_dir: Path = typer.Option(Path("artifacts/showcase"), "--output-dir"),
    scenario: list[str] | None = typer.Option(None, "--scenario", help="Repeat to build selected scenarios."),
    frame_count: int = typer.Option(18, min=8, max=120),
    render_dpi: int = typer.Option(200, min=80, max=300),
) -> None:
    """Build the frontend-ready player catalog, scenarios, JSON, and 4K tactical visuals."""
    manifest = build_showcase_bundle(
        output_dir,
        scenario_ids=scenario or None,
        frame_count=frame_count,
        render_dpi=render_dpi,
    )
    contract = write_frontend_contract(Path("frontend_contract") / "openapi.json")
    console.print_json(manifest.read_text(encoding="utf-8"))
    console.print(f"Frontend API contract: {contract}")


@app.command("showcase-serve")
def showcase_serve(
    bundle_dir: Path = typer.Option(Path("artifacts/showcase"), "--bundle-dir"),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000, min=1, max=65535),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Serve the read-only showcase API for a Gemini-generated frontend."""
    try:
        import uvicorn
    except ImportError as exc:
        raise typer.BadParameter("Install `pip install -e '.[showcase]'`") from exc
    from .showcase.api import create_app

    uvicorn.run(create_app(bundle_dir), host=host, port=port, reload=reload)


@app.command("player-catalog")
def player_catalog(
    featured_only: bool = typer.Option(False, "--featured-only"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Inspect the 100-player elite midfielder study atlas. It is not an ordinal ranking."""
    catalog = load_player_catalog()
    players = [player for player in catalog.players if player.featured or not featured_only]
    if as_json:
        console.print_json(json.dumps([player.to_dict() for player in players]))
        return
    table = Table(title="Midfielder's Eye · 100-player study atlas · not an ordinal ranking")
    table.add_column("Player")
    table.add_column("Cohort")
    table.add_column("Role")
    table.add_column("Archetype")
    table.add_column("Evidence")
    for player in players:
        table.add_row(player.name, player.cohort, player.display_role, player.primary_archetype, player.evidence_status)
    console.print(table)


@app.command("media-template")
def media_template(
    output_path: Path = typer.Option(Path("data/showcase/media_manifest.json"), "--output"),
) -> None:
    """Create a rights-aware media registry template."""
    console.print(f"Wrote {create_media_template(output_path)}")


@app.command("media-validate")
def media_validate(manifest_path: Path) -> None:
    """Reject analysis media without an explicit, verifiable rights status."""
    manifest = load_media_manifest(manifest_path, validate=True)
    console.print_json(json.dumps({"valid": True, "assets": len(manifest.assets), "policy": manifest.policy}))


@app.command("youtube-discover")
def youtube_discover(
    query: str,
    player_id: str = typer.Option(..., "--player-id"),
    output_path: Path = typer.Option(Path("artifacts/youtube_references.json"), "--output"),
    max_results: int = typer.Option(10, min=1, max=50),
    creative_commons_only: bool = typer.Option(False, "--creative-commons-only"),
    region_code: str = typer.Option("US", "--region-code"),
) -> None:
    """Find embeddable YouTube references through the official API; never download video."""
    assets = discover_youtube_videos(
        query,
        max_results=max_results,
        creative_commons_only=creative_commons_only,
        region_code=region_code,
    )
    for asset in assets:
        asset.player_ids = [player_id]
    manifest = MediaManifest(version=1, assets=assets)
    write_media_manifest(manifest, output_path)
    console.print(f"Wrote {len(assets)} embed-only references to {output_path}")


@app.command("frontend-contract")
def frontend_contract(
    output_path: Path = typer.Option(Path("frontend_contract/openapi.json"), "--output"),
) -> None:
    """Write the stable frontend API contract for Gemini AI Studio."""
    console.print(f"Wrote {write_frontend_contract(output_path)}")



@app.command("gsr-inspect")
def gsr_inspect(
    tracker_state_path: Path,
    fps: float = typer.Option(25.0, min=0.1),
    match_id: str | None = typer.Option(None),
    visibility_path: Path | None = typer.Option(None),
) -> None:
    """Inspect a frozen SoccerNet/TrackLab state without importing its dependency stack."""
    bundle = read_tracker_state(
        tracker_state_path,
        match_id=match_id,
        fps=fps,
        visibility_path=visibility_path,
    )
    console.print_json(json.dumps(bundle.summary()))


@app.command("gsr-ingest")
def gsr_ingest(
    tracker_state_path: Path,
    possession_sidecar_path: Path,
    output_path: Path = typer.Option(Path("artifacts/soccernet_gsr_frames.jsonl"), "--output"),
    parquet_path: Path | None = typer.Option(None, help="Optional lossless Parquet mirror."),
    visibility_path: Path | None = typer.Option(None),
    match_id: str | None = typer.Option(None),
    sequence_id: str | None = typer.Option(None),
    fps: float = typer.Option(25.0, min=0.1),
    coordinates: str = typer.Option("soccernet_center", help="soccernet_center or canonical"),
) -> None:
    """Convert frozen GSR state plus explicit possession into canonical tactical frames."""
    result = load_tracker_state_gsr(
        tracker_state_path,
        possession_sidecar_path,
        visibility_path=visibility_path,
        match_id=match_id,
        sequence_id=sequence_id,
        fps=fps,
        coordinates=coordinates,
    )
    write_frames_jsonl(result.frames, output_path)
    if parquet_path is not None:
        write_frames_parquet(result.frames, parquet_path)
    payload = {
        "adapter": result.summary(),
        "quality": assess_frames(result.frames, "soccernet_gsr").to_dict(),
        "jsonl": str(output_path),
        "parquet": None if parquet_path is None else str(parquet_path),
    }
    console.print_json(json.dumps(payload))


@app.command("gsr-manifest")
def gsr_manifest(
    tracker_state_path: Path,
    output_path: Path = typer.Option(Path("artifacts/tracker_state_manifest.json"), "--output"),
    repository_path: Path | None = typer.Option(None),
    dataset_version: str | None = typer.Option(None),
    model_manifest_path: Path | None = typer.Option(None),
) -> None:
    """Hash an immutable tracker state and record exact perception provenance."""
    models = None
    if model_manifest_path is not None:
        models = json.loads(model_manifest_path.read_text(encoding="utf-8")).get("models", {})
    path = write_tracker_state_manifest(
        tracker_state_path,
        output_path,
        repository_path=repository_path,
        dataset_version=dataset_version,
        model_versions=models,
    )
    console.print(f"Wrote {path}")


@app.command("possession-template")
def possession_template(
    tracker_state_path: Path,
    output_path: Path = typer.Option(Path("artifacts/possession_sidecar.csv"), "--output"),
    fps: float = typer.Option(25.0, min=0.1),
) -> None:
    """Create a sidecar template instead of silently inventing ball state or possession."""
    bundle = read_tracker_state(tracker_state_path, fps=fps)
    path = write_possession_sidecar_template(
        [frame.frame_id for frame in bundle.frames], output_path, fps=fps
    )
    console.print(f"Wrote {path}")


@app.command("reconstruct-state")
def reconstruct_state(
    frames_path: Path,
    output_path: Path = typer.Option(Path("artifacts/reconstructed_frames.jsonl"), "--output"),
    interpolate_gaps: bool = typer.Option(False, "--interpolate-gaps"),
    max_gap_frames: int = typer.Option(3, min=1),
) -> None:
    """Run causal kinematic reconstruction and optional explicitly non-causal gap filling."""
    frames = reconstruct_trajectories(read_frames_jsonl(frames_path))
    cuts = detect_camera_cuts(frames)
    if interpolate_gaps:
        frames = interpolate_short_gaps(frames, max_gap_frames=max_gap_frames)
    write_frames_jsonl(frames, output_path)
    console.print_json(
        json.dumps(
            {
                "output": str(output_path),
                "frames": len(frames),
                "camera_cut_frame_ids": cuts,
                "offline_interpolation": interpolate_gaps,
            }
        )
    )


@app.command("degradation-benchmark")
def degradation_benchmark(
    frames_path: Path | None = typer.Argument(None),
    output_dir: Path = typer.Option(Path("artifacts/degradation_benchmark"), "--output-dir"),
    seed: int = typer.Option(7),
    synthetic_sequences: int = typer.Option(3, min=1),
    synthetic_frames: int = typer.Option(10, min=2),
) -> None:
    """Compare oracle affordances with controlled perception failures."""
    frames = (
        read_frames_jsonl(frames_path)
        if frames_path is not None
        else generate_dataset(synthetic_sequences, synthetic_frames, seed)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics, results = benchmark_degradation(frames, default_degradation_suite(seed))
    metrics.to_csv(output_dir / "frame_metrics.csv", index=False)
    summary = (
        metrics.drop(columns=["frame_id"], errors="ignore")
        .groupby("degradation", as_index=False)
        .mean(numeric_only=True)
    )
    summary.to_csv(output_dir / "summary.csv", index=False)
    (output_dir / "degradation_counts.json").write_text(
        json.dumps({name: result.summary() for name, result in results.items()}, indent=2),
        encoding="utf-8",
    )
    console.print(summary)
    console.print(f"Robustness outputs: {output_dir}")


@app.command()
def providers(as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON.")) -> None:
    """List supported soccer and auxiliary data integrations."""
    if as_json:
        console.print_json(json.dumps({key: value.to_dict() for key, value in PROVIDERS.items()}))
        return
    table = Table(title="Midfielder's Eye provider integrations")
    table.add_column("Provider")
    table.add_column("Coverage")
    table.add_column("Access")
    table.add_column("Tracking")
    table.add_column("Events")
    table.add_column("Best use")
    for key in sorted(PROVIDERS):
        spec = PROVIDERS[key]
        table.add_row(
            key,
            spec.coverage,
            spec.access,
            "yes" if spec.capabilities.tracking else "no",
            "yes" if spec.capabilities.events else "no",
            spec.recommended_use,
        )
    console.print(table)


@app.command("ingest")
def ingest_provider(
    provider: str = typer.Argument(help="metrica, skillcorner, statsbomb360, soccertrack_v2, soccernet_gsr"),
    primary: Path = typer.Argument(help="Primary provider file."),
    output_path: Path = typer.Option(Path("artifacts/normalized_frames.jsonl"), "--output"),
    secondary: Path | None = typer.Option(None, help="Second required file, such as 360/BAS/sidecar."),
    tertiary: Path | None = typer.Option(None, help="Optional event file."),
    match_id: str | None = typer.Option(None),
    half: int = typer.Option(1, min=1, max=2),
) -> None:
    """Normalize a provider feed into canonical FrameState JSONL."""
    if provider == "metrica":
        frames = load_metrica_csv(primary, sequence_id=match_id or primary.stem)
        result_summary = {"provider_id": provider, "frames": len(frames), "warnings": []}
    elif provider == "skillcorner":
        result = load_skillcorner_open(primary, match_path=secondary, dynamic_events_path=tertiary, match_id=match_id)
        frames = result.frames
        result_summary = result.summary()
    elif provider == "statsbomb360":
        if secondary is None:
            raise typer.BadParameter("statsbomb360 requires --secondary THREE_SIXTY.json")
        result = load_statsbomb_360(primary, secondary, match_id=match_id)
        frames = result.frames
        result_summary = result.summary()
    elif provider == "soccertrack_v2":
        if secondary is None:
            raise typer.BadParameter("soccertrack_v2 requires --secondary BAS.json")
        result = load_soccertrack_v2(primary, secondary, match_id=match_id, half=half)
        frames = result.frames
        result_summary = result.summary()
    elif provider == "soccernet_gsr":
        if secondary is None:
            raise typer.BadParameter("soccernet_gsr requires --secondary possession_sidecar.csv")
        result = load_soccernet_gsr(primary, secondary, match_id=match_id)
        frames = result.frames
        result_summary = result.summary()
    else:
        raise typer.BadParameter(f"Unsupported direct adapter {provider!r}")
    write_frames_jsonl(frames, output_path)
    quality = assess_frames(frames, provider).to_dict()
    console.print_json(json.dumps({"adapter": result_summary, "quality": quality, "output": str(output_path)}))


@app.command("sportec-open")
def sportec_open(
    match_id: str = typer.Argument(help="One of the documented Sportec open match IDs."),
    output_path: Path = typer.Option(Path("artifacts/sportec_frames.jsonl"), "--output"),
    limit: int | None = typer.Option(None, min=1),
    sample_rate: float | None = typer.Option(None, min=0.1),
) -> None:
    """Load an open Sportec/DFL match through optional Kloppy support."""
    result = load_sportec_open(match_id, limit=limit, sample_rate=sample_rate)
    write_frames_jsonl(result.frames, output_path)
    console.print_json(json.dumps({"adapter": result.summary(), "output": str(output_path)}))


@app.command("quality")
def quality_report(
    frames_path: Path,
    output_path: Path | None = typer.Option(None),
) -> None:
    """Audit normalized tracking coverage before modeling."""
    frames = read_frames_jsonl(frames_path)
    report = assess_frames(frames).to_dict()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    console.print_json(json.dumps(report))


@app.command("demo-v2")
def demo_v2(
    output_dir: Path = typer.Option(Path("artifacts/v2_demo")),
    sequences: int = typer.Option(4, min=2),
    frames_per_sequence: int = typer.Option(12, min=4),
    seed: int = typer.Option(7),
) -> None:
    """Run the provider-aware modality stress test."""
    output_dir.mkdir(parents=True, exist_ok=True)
    providers_data = generate_provider_views(sequences, frames_per_sequence, seed)
    quality_payload = {}
    for provider_id, frames in providers_data.items():
        write_frames_jsonl(frames, output_dir / f"{provider_id}_frames.jsonl")
        quality_payload[provider_id] = assess_frames(frames, provider_id).to_dict()
    summary, options = benchmark_provider_frames(providers_data)
    summary.to_csv(output_dir / "provider_summary.csv", index=False)
    options.to_csv(output_dir / "provider_options.csv", index=False)
    shift = provider_shift_report(options)
    shift.to_csv(output_dir / "provider_shift.csv", index=False)
    (output_dir / "quality_reports.json").write_text(json.dumps(quality_payload, indent=2), encoding="utf-8")
    temporal = {
        provider: temporal_rank_metrics(options[options["source_provider"] == provider])
        for provider in options["source_provider"].dropna().unique()
    }
    (output_dir / "temporal_metrics.json").write_text(json.dumps(temporal, indent=2), encoding="utf-8")
    console.print(summary)
    console.print(f"Provider-aware outputs: {output_dir}")


@app.command()
def demo(
    output_dir: Path = typer.Option(Path("artifacts/demo"), help="Output directory."),
    sequences: int = typer.Option(10, min=2),
    frames_per_sequence: int = typer.Option(16, min=2),
    seed: int = typer.Option(7),
) -> None:
    """Run the complete synthetic bootstrap experiment."""
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = generate_dataset(sequences=sequences, frames=frames_per_sequence, seed=seed)
    frame_path = write_frames_jsonl(frames, output_dir / "frames.jsonl")
    options = build_bootstrap_options(frames)
    option_path = write_options_csv(options, output_dir / "options.csv")
    dataframe = options_to_dataframe(options)
    result = cross_validate(dataframe)
    report_path = write_report(result, output_dir / "metrics.json")
    result["predictions"].to_csv(output_dir / "predictions.csv", index=False)
    intervals = {
        name: sequence_bootstrap_interval(result["predictions"], column, iterations=250)
        for name, column in {
            "naive": "naive_score",
            "static": "static_score",
            "dynamic": "geometric_score",
            "learned": "learned_score",
        }.items()
    }
    (output_dir / "bootstrap_intervals.json").write_text(json.dumps(intervals, indent=2), encoding="utf-8")
    first_frame = frames[0]
    first_options = [o for o in options if o.frame_id == first_frame.frame_id and o.sequence_id == first_frame.sequence_id]
    plot_affordance_frame(first_frame, first_options, output_dir / "affordance_demo.png")
    top_pass = max((option for option in first_options if option.kind == "pass"), key=lambda option: option.geometric_score)
    plot_positioning_uplift(first_frame, top_pass.target_player_id, output_dir / "counterfactual_demo.png")

    table = Table(title="Bootstrap benchmark")
    table.add_column("Model")
    table.add_column("NDCG@3")
    table.add_column("Recall@3")
    table.add_column("Pairwise")
    for name in ("naive", "static", "dynamic", "learned"):
        metrics = result["metrics"][name]
        table.add_row(name, f"{metrics['ndcg@3']:.3f}", f"{metrics['recall@3']:.3f}", f"{metrics['pairwise']:.3f}")
    console.print(table)
    console.print(f"Frames: {frame_path}")
    console.print(f"Options: {option_path}")
    console.print(f"Metrics: {report_path}")


@app.command()
def extract(
    frames_path: Path,
    output_path: Path = typer.Option(Path("artifacts/options.csv")),
) -> None:
    """Generate affordance options from normalized frame states."""
    frames = read_frames_jsonl(frames_path)
    engine = AffordanceEngine()
    options = [option for frame in frames for option in engine.generate(frame)]
    write_options_csv(options, output_path)
    console.print(f"Wrote {len(options)} options to {output_path}")


@app.command()
def evaluate(
    options_path: Path,
    output_path: Path = typer.Option(Path("artifacts/metrics.json")),
    splits: int = typer.Option(5, min=2),
) -> None:
    """Compare geometric and learned baselines with sequence-grouped CV."""
    dataframe = pd.read_csv(options_path)
    result = cross_validate(dataframe, splits=splits)
    write_report(result, output_path)
    result["predictions"].to_csv(output_path.with_name("predictions.csv"), index=False)
    console.print_json(json.dumps(result["metrics"]))


@app.command()
def train(
    options_path: Path,
    model_path: Path = typer.Option(Path("artifacts/option_model.joblib")),
) -> None:
    dataframe = pd.read_csv(options_path)
    model = LearnedOptionModel().fit(dataframe)
    model.save(model_path)
    console.print(f"Saved model to {model_path}")


@app.command()
def render(
    frames_path: Path,
    frame_index: int = typer.Option(0, min=0),
    output_path: Path = typer.Option(Path("artifacts/frame.png")),
) -> None:
    frames = read_frames_jsonl(frames_path)
    if frame_index >= len(frames):
        raise typer.BadParameter(f"frame_index must be below {len(frames)}")
    frame = frames[frame_index]
    options = AffordanceEngine().generate(frame)
    plot_affordance_frame(frame, options, output_path)
    console.print(f"Rendered {output_path}")


@app.command()
def validate(frames_path: Path) -> None:
    frames = read_frames_jsonl(frames_path)
    console.print(f"Validated {len(frames)} frames across {len(set(f.sequence_id for f in frames))} sequences")


if __name__ == "__main__":
    app()
