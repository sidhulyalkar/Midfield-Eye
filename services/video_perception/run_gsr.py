#!/usr/bin/env python3
"""Dry-run-first process boundary around the GPL-licensed SoccerNet GSR application.

The wrapper never imports SoccerNet or TrackLab. It records the exact command, pinned repository,
input hash, and Hydra overrides, then optionally executes the official TrackLab CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload)
    if "REQUIRED_" in serialized or "PIN_ME" in serialized:
        raise ValueError("model manifest still contains unresolved required placeholders")
    required = {"sn_gamestate_commit", "tracklab_version", "dataset_version", "models"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"model manifest missing required fields: {missing}")
    return payload


def build_command(
    output_dir: Path,
    overrides: list[str],
    *,
    config_name: str = "soccernet",
    use_uv: bool = True,
) -> list[str]:
    """Build the official `tracklab -cn soccernet` command plus explicit overrides."""
    command = ["tracklab", "-cn", config_name, f"hydra.run.dir={output_dir}"]
    command.extend(overrides)
    return (["uv", "run"] + command) if use_uv else command


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True, help="Pinned sn-gamestate checkout")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--video", type=Path, help="Optional input recorded in the manifest")
    parser.add_argument("--config-name", default="soccernet")
    parser.add_argument("--override", action="append", default=[])
    parser.add_argument("--no-uv", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Execute instead of dry-run")
    parser.add_argument("--dataset-version")
    parser.add_argument(
        "--model-manifest",
        type=Path,
        help="Resolved model/version manifest. Required for --execute.",
    )
    args = parser.parse_args()
    if args.execute and args.model_manifest is None:
        parser.error("--model-manifest is required with --execute")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    command = build_command(
        args.output_dir,
        args.override,
        config_name=args.config_name,
        use_uv=not args.no_uv,
    )
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(args.repo), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    model_manifest = None
    if args.model_manifest is not None:
        try:
            model_manifest = load_model_manifest(args.model_manifest)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            parser.error(str(error))
    manifest = {
        "command": command,
        "working_directory": str(args.repo),
        "video": None if args.video is None else str(args.video),
        "video_sha256": (
            sha256_file(args.video) if args.video is not None and args.video.exists() else None
        ),
        "sn_gamestate_commit": commit,
        "dataset_version": args.dataset_version,
        "model_manifest_path": (
            None if args.model_manifest is None else str(args.model_manifest)
        ),
        "model_manifest_sha256": (
            None if args.model_manifest is None else sha256_file(args.model_manifest)
        ),
        "model_manifest": model_manifest,
        "config_name": args.config_name,
        "overrides": args.override,
        "environment": {
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "PYTHON": sys.version,
        },
        "executed": bool(args.execute),
    }
    manifest_path = args.output_dir / "perception_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"command": command, "manifest": str(manifest_path)}, indent=2))
    if args.execute:
        subprocess.run(command, cwd=args.repo, check=True)


if __name__ == "__main__":
    main()
