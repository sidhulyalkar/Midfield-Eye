from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_file_manifest(
    root: str | Path,
    *,
    source_id: str,
    metadata: dict[str, Any] | None = None,
    manifest_name: str = "MANIFEST.json",
) -> dict[str, Any]:
    directory = Path(root)
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name.casefold() != manifest_name.casefold():
            files.append({
                "path": path.relative_to(directory).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            })
    return {"source_id": source_id, "files": files, "metadata": metadata or {}}


def write_file_manifest(
    root: str | Path,
    *,
    source_id: str,
    metadata: dict[str, Any] | None = None,
    manifest_name: str = "MANIFEST.json",
) -> Path:
    directory = Path(root)
    payload = build_file_manifest(
        directory,
        source_id=source_id,
        metadata=metadata,
        manifest_name=manifest_name,
    )
    output = directory / manifest_name
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output


def verify_file_manifest(path: str | Path) -> list[str]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    failures: list[str] = []
    for item in payload["files"]:
        target = root / item["path"]
        if not target.exists():
            failures.append(f"missing:{item['path']}")
        elif sha256_file(target) != item["sha256"]:
            failures.append(f"hash:{item['path']}")
    return failures
