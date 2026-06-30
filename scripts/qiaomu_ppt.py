#!/usr/bin/env python3
"""Small command facade for the qiaomu-ppt workflow."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

COMMANDS = {
    "plan": "plan_run.py",
    "prepare": "prepare_deck_project.py",
    "preview": "four_slide_preview.py",
    "build": "produce_deck.py",
    "check": "final_status.py",
    "project-check": "check_project.py",
    "repair": "deck_repair_plan.py",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Route common qiaomu-ppt actions through one stable entrypoint.",
        epilog=(
            "Examples:\n"
            "  qiaomu_ppt.py plan --prompt \"生成一个10页PPT介绍...\"\n"
            "  qiaomu_ppt.py prepare --topic \"...\" --slides 10\n"
            "  qiaomu_ppt.py build /path/to/project --quality-profile final\n"
            "  qiaomu_ppt.py check /path/to/project"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=sorted(COMMANDS), help="Workflow command to run.")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the underlying script.")
    parsed = parser.parse_args()

    script = SCRIPT_DIR / COMMANDS[parsed.command]
    return subprocess.call([sys.executable, str(script), *parsed.args])


if __name__ == "__main__":
    raise SystemExit(main())
