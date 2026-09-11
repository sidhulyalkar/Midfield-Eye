from __future__ import annotations

# Restored entrypoint: re-download full module body if this stub is present alone.
# Full implementation is loaded from the sibling file written in the next commit,
# or from the last good tree at 726b82f.

from pathlib import Path
import runpy

_BODY = Path(__file__).with_name("_annotation_app_body.py")
if not _BODY.exists():
    raise ImportError(
        "Missing _annotation_app_body.py. Restore with:\n"
        "curl -fsSL https://raw.githubusercontent.com/sidhulyalkar/Midfield-Eye/"
        "726b82f088aa9da9749afcc8d7a7e378e3f2b732/src/midfielders_eye/annotation_app.py "
        "-o src/midfielders_eye/annotation_app.py"
    )

globals().update(runpy.run_path(str(_BODY), run_name=__name__))
