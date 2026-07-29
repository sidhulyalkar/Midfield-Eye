from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Iterable

import yaml

from .schemas import AccessMode, DatasetSource, SignalModality


@dataclass(frozen=True)
class SourceRegistry:
    version: str
    sources: tuple[DatasetSource, ...]

    def get(self, source_id: str) -> DatasetSource:
        for source in self.sources:
            if source.id == source_id:
                return source
        raise KeyError(source_id)

    def filter(
        self,
        *,
        modality: SignalModality | None = None,
        access: AccessMode | None = None,
        auto_download_only: bool = False,
    ) -> tuple[DatasetSource, ...]:
        selected: Iterable[DatasetSource] = self.sources
        if modality is not None:
            selected = (source for source in selected if modality in source.modalities)
        if access is not None:
            selected = (source for source in selected if source.access == access)
        if auto_download_only:
            selected = (source for source in selected if source.can_auto_download)
        return tuple(sorted(selected, key=lambda source: (source.priority, source.name.lower())))

    def to_dict(self) -> dict:
        return {"version": self.version, "sources": [source.to_dict() for source in self.sources]}


def _default_registry_path() -> Path:
    return Path(str(files("midfielders_eye.empirical").joinpath("source_registry.yaml")))


def load_source_registry(path: str | Path | None = None) -> SourceRegistry:
    source_path = Path(path) if path is not None else _default_registry_path()
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    registry = SourceRegistry(
        version=str(payload["version"]),
        sources=tuple(DatasetSource.from_dict(item) for item in payload["sources"]),
    )
    ids = [source.id for source in registry.sources]
    if len(ids) != len(set(ids)):
        raise ValueError("source registry contains duplicate ids")
    return registry
