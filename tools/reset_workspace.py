"""
Reset utility to clean generated artifacts (reference/debug markdown, images, temp uploads, vector DB).

Usage:
    # destructive by default
    python tools/reset_workspace.py

    # preview only
    python tools/reset_workspace.py --dry-run

What it removes:
- data/_uploads/ (temp tokens)
- data/vectordb/ (Chroma store)
- Generated reference/debug markdown:
    - *_reference.md and *_extraction_debug.md under data/manuals/**
    - top-level *_reference.md / *_extraction_debug.md in repo root
- Images directories under data/manuals/**/images
- ALL manuals under data/manuals/** (PDFs and subfolders)
- data/catalog/devices.json (reset to empty list)

What it preserves:
- Code and catalog JSON files (devices.json, etc.)
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MANUALS = DATA / "manuals"


def remove_path(path: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    if dry_run:
        print(f"[DRY-RUN] Would remove: {path}")
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    print(f"Removed: {path}")


def find_generated_files() -> list[Path]:
    paths: list[Path] = []
    # Top-level generated reference/debug files (if any)
    paths.extend(ROOT.glob("*_reference.md"))
    paths.extend(ROOT.glob("*_extraction_debug.md"))
    # Under manuals
    for md in MANUALS.rglob("*_reference.md"):
        paths.append(md)
    for md in MANUALS.rglob("*_extraction_debug.md"):
        paths.append(md)
    return paths


def find_images_dirs() -> list[Path]:
    return [p for p in MANUALS.rglob("images") if p.is_dir()]


def find_manual_dirs() -> list[Path]:
    """Return all subdirectories inside data/manuals (each device)."""
    if not MANUALS.exists():
        return []
    return [p for p in MANUALS.iterdir() if p.is_dir()]


def reset_devices_json(dry_run: bool) -> None:
    devices_path = DATA / "catalog" / "devices.json"
    if not devices_path.exists():
        return
    if dry_run:
        print(f"[DRY-RUN] Would reset: {devices_path}")
        return
    devices_path.write_text("[]\n", encoding="utf-8")
    print(f"Reset: {devices_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset generated artifacts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only; do not delete anything.",
    )
    args = parser.parse_args()
    dry_run = args.dry_run

    print(f"Running in {'DRY-RUN' if dry_run else 'DESTRUCTIVE'} mode\n")

    # Temp uploads
    remove_path(DATA / "_uploads", dry_run=dry_run)

    # Vector DB
    remove_path(DATA / "vectordb", dry_run=dry_run)

    # Generated references/debug md
    for p in find_generated_files():
        remove_path(p, dry_run=dry_run)

    # Images directories
    for img_dir in find_images_dirs():
        remove_path(img_dir, dry_run=dry_run)

    # All manual directories (includes PDFs and generated files)
    for manual_dir in find_manual_dirs():
        remove_path(manual_dir, dry_run=dry_run)

    # Reset devices.json to empty list
    reset_devices_json(dry_run=dry_run)

    print("\nDone.")
    if dry_run:
        print("Dry-run only. Re-run without --dry-run to apply.")


if __name__ == "__main__":
    main()

