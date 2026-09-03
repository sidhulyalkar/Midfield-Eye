#!/usr/bin/env python3
"""Package a static demo bundle suitable for GitHub Pages / Cloudflare Pages.

Prerequisites:
  midfielders-eye showcase-build --output-dir artifacts/showcase
  cd frontend && npm ci && npm run build

Usage:
  python scripts/package_static_demo.py
  python scripts/package_static_demo.py --showcase artifacts/showcase --frontend-dist frontend/dist --output artifacts/static-demo
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy frontend production build + showcase data into a static hosting folder."
    )
    parser.add_argument(
        "--showcase",
        type=Path,
        default=Path("artifacts/showcase"),
        help="Built showcase bundle directory",
    )
    parser.add_argument(
        "--frontend-dist",
        type=Path,
        default=Path("frontend/dist"),
        help="Vite production build output",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/static-demo"),
        help="Destination directory for the static site",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output directory",
    )
    args = parser.parse_args()

    if not args.showcase.exists():
        print(
            f"Missing showcase bundle at {args.showcase}. Run:\n"
            f"  midfielders-eye showcase-build --output-dir {args.showcase}"
        )
        return 1
    if not args.frontend_dist.exists():
        print(
            f"Missing frontend dist at {args.frontend_dist}. Run:\n"
            f"  cd frontend && npm ci && npm run build"
        )
        return 1

    if args.output.exists():
        if not args.force:
            print(f"Output {args.output} already exists. Pass --force to overwrite.")
            return 1
        shutil.rmtree(args.output)

    args.output.mkdir(parents=True)

    # Copy SPA assets
    for item in args.frontend_dist.iterdir():
        dest = args.output / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Place showcase data where the static data source expects it
    data_dest = args.output / "showcase-data"
    shutil.copytree(args.showcase, data_dest)

    # Write a small deployment manifest
    manifest = {
        "schema": "midfielders-eye-static-demo-v1",
        "showcase_source": str(args.showcase),
        "frontend_dist": str(args.frontend_dist),
        "notes": [
            "Serve this directory as a static site (GitHub Pages, Cloudflare Pages, nginx).",
            "Configure the frontend static data base path to ./showcase-data/ if required.",
            "Synthetic and empirical evidence labels must remain visible in the UI.",
            "Do not present this package as completed R1 empirical results unless pilot evidence is present.",
        ],
    }
    (args.output / "STATIC_DEMO_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    # Helpful index note for operators
    readme = args.output / "DEPLOY.md"
    readme.write_text(
        "# Static demo deploy\n\n"
        "1. Point your static host document root at this folder.\n"
        "2. Ensure SPA fallback routes all paths to `index.html`.\n"
        "3. Confirm Decision Microscope scenarios load and evidence labels are visible.\n"
        "4. Keep claim boundary honest: software + illustrative scenarios ≠ empirical R1.\n",
        encoding="utf-8",
    )

    print(f"Static demo packaged → {args.output}")
    print(f"  SPA assets from {args.frontend_dist}")
    print(f"  Showcase data → {data_dest}")
    print("  Next: deploy with GitHub Pages / Cloudflare Pages / any static host")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
