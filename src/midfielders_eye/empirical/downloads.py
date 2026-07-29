from __future__ import annotations

import json
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .provenance import sha256_file
from .registry import SourceRegistry, load_source_registry


class AccessGateError(PermissionError):
    """Raised when a source requires a license, registration, or human approval."""


@dataclass(frozen=True)
class DownloadResult:
    source_id: str
    output_dir: Path
    files: tuple[Path, ...]


def source_plan(source_id: str, registry: SourceRegistry | None = None) -> dict:
    source = (registry or load_source_registry()).get(source_id)
    return {
        "source": source.to_dict(),
        "automatic_download_permitted": source.can_auto_download,
        "required_human_steps": source.download.get("human_steps", []),
        "commands": source.download.get("commands", []),
        "files": source.download.get("files", []),
    }


def download_open_source(
    source_id: str,
    output_dir: str | Path,
    *,
    registry: SourceRegistry | None = None,
    overwrite: bool = False,
) -> DownloadResult:
    source = (registry or load_source_registry()).get(source_id)
    if not source.can_auto_download:
        raise AccessGateError(
            f"{source.name} requires {source.access.value}; review its license and follow the human steps"
        )
    output = Path(output_dir) / source_id
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for item in source.download.get("files", []):
        target = output / item["path"]
        if target.exists() and not overwrite:
            written.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(item["url"], timeout=120) as response, target.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        expected = item.get("sha256")
        if expected and sha256_file(target) != expected:
            target.unlink(missing_ok=True)
            raise ValueError(f"checksum mismatch for {item['path']}")
        written.append(target)
    (output / "SOURCE_PLAN.json").write_text(json.dumps(source_plan(source_id, registry), indent=2), encoding="utf-8")
    return DownloadResult(source_id=source_id, output_dir=output, files=tuple(written))
