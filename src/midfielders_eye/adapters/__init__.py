"""Provider adapter namespace with lazy imports.

Lazy loading keeps optional provider dependencies and the SoccerNet integration boundary from
creating import cycles or making every adapter a mandatory import-time dependency.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

from .base import AdapterResult, ProviderCapabilities, ProviderSpec
from .catalog import PROVIDERS, get_provider, provider_rows

_LAZY_EXPORTS = {
    "load_metrica_csv": (".metrica", "load_metrica_csv"),
    "load_skillcorner_open": (".skillcorner", "load_skillcorner_open"),
    "load_statsbomb_360": (".statsbomb", "load_statsbomb_360"),
    "load_soccertrack_v2": (".soccertrack", "load_soccertrack_v2"),
    "load_soccernet_gsr": (".soccernet", "load_soccernet_gsr"),
    "frames_from_kloppy_dataframe": (".kloppy_bridge", "frames_from_kloppy_dataframe"),
    "load_sportec_open": (".kloppy_bridge", "load_sportec_open"),
    "load_egotraj_csv": (".egotraj", "load_egotraj_csv"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module = import_module(target[0], __name__)
    value = getattr(module, target[1])
    globals()[name] = value
    return value


__all__ = [
    "AdapterResult",
    "ProviderCapabilities",
    "ProviderSpec",
    "PROVIDERS",
    "get_provider",
    "provider_rows",
    *_LAZY_EXPORTS,
]
