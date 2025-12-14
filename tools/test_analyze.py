"""
Quick test harness for analyze_extracted_manual to iterate on the prompt/output.

Usage:
  # Use the most recent token under data/_uploads
  python tools/test_analyze.py

  # Use a specific token
  python tools/test_analyze.py --token <token>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

UPLOADS_DIR = ROOT / "data" / "_uploads"

try:
    from backend.manual_processing import analyze_extracted_manual  # type: ignore
except Exception as exc:
    print("Failed to import backend.manual_processing. Are you running from the repo root?")
    raise exc


def latest_token() -> Optional[str]:
    if not UPLOADS_DIR.exists():
        return None
    dirs = [d for d in UPLOADS_DIR.iterdir() if d.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0].name


def main() -> None:
    parser = argparse.ArgumentParser(description="Test analyze_extracted_manual.")
    parser.add_argument("--token", type=str, help="Token under data/_uploads/<token>")
    args = parser.parse_args()

    token = args.token or latest_token()
    if not token:
        print("No token provided and no uploads found in data/_uploads.")
        sys.exit(1)

    print(f"Using token: {token}")

    try:
        result = analyze_extracted_manual(token)
    except Exception as exc:
        print(f"Error running analyze_extracted_manual: {exc}")
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

