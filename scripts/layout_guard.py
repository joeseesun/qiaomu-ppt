#!/usr/bin/env python3
"""Run the qiaomu-ppt PPTX layout guard.

This is a focused entry point for geometry QA. It uses the same implementation
as pptx_text_check.py so production checks stay consistent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pptx_text_check import check, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PPTX text fit, title spacing, and image collisions.")
    parser.add_argument("pptx", help="PPTX file to inspect")
    parser.add_argument("--slide-plan", help="Optional slide_plan.json for title/slide-count parity")
    parser.add_argument("--output", "-o", help="Optional JSON report path")
    parser.add_argument(
        "--allow-image-backed",
        action="store_true",
        help="Allow whole-slide raster PPTX exports for explicitly labelled parity/social-image artifacts.",
    )
    args = parser.parse_args()
    result = check(
        Path(args.pptx).resolve(),
        Path(args.slide_plan).resolve() if args.slide_plan else None,
        allow_image_backed=args.allow_image_backed,
    )
    layout_result = {
        "ok": not result["layout"]["failures"],
        "pptx": result["pptx"],
        "slide_count": result["slide_count"],
        "layout": result["layout"],
        "failures": result["layout"]["failures"],
        "warnings": result["layout"]["warnings"],
    }
    if args.output:
        write_json(Path(args.output), layout_result)
    print(json.dumps(layout_result, ensure_ascii=False, indent=2))
    return 0 if layout_result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
