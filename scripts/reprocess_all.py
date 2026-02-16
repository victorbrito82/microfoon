#!/usr/bin/env python3
"""
Reprocess all recordings in the database and regenerate Obsidian notes.
This updates existing DB rows only (no new recording entries are created).
"""

import argparse
import sys
from pathlib import Path

# Allow importing sibling script module.
sys.path.append(str(Path(__file__).resolve().parent))

from regenerate_exports import regenerate


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reprocess all existing recordings and regenerate Obsidian exports."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt."
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Skip Gemini reprocessing and only re-export current DB content."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    regenerate(
        recording_id=None,
        original_filename=None,
        auto_confirm=args.yes,
        export_only=args.export_only,
    )
