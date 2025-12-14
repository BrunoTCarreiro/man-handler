"""CLI helper to extract English-only pages using backend.manual_processing."""

import sys
from pathlib import Path

try:
    from backend.manual_processing import extract_english_sections
except ImportError as exc:  # pragma: no cover
    print("Failed to import backend.manual_processing. Ensure you're running from project root.")
    raise exc


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python extract_english_pages.py <input_pdf> [output_pdf]")
        print("Example: python extract_english_pages.py data/manuals/device/manual.pdf")
        sys.exit(1)

    input_pdf = Path(sys.argv[1])
    output_pdf = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not input_pdf.exists():
        print(f"Error: {input_pdf} not found.")
        sys.exit(1)

    pages, output_path = extract_english_sections(input_pdf, output_pdf)
    print(f"[SUCCESS] Extracted {len(pages)} English pages.")
    print(f"[SUCCESS] Saved to: {output_path}")


if __name__ == "__main__":
    main()

