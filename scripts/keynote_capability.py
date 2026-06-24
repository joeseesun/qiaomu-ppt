#!/usr/bin/env python3
"""Report whether this machine can attempt Keynote export automation."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_osascript(script: str, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        return {
            "status": "ok" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
        }


def capability(timeout: int, *, check_version: bool) -> dict[str, Any]:
    system = platform.system()
    osascript = shutil.which("osascript") or ""
    keynote_app = Path("/Applications/Keynote.app")
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/keynote_capability.py",
        "generated_at": now_iso(),
        "platform": platform.platform(),
        "system": system,
        "osascript": osascript,
        "keynote_app": str(keynote_app),
        "keynote_app_exists": keynote_app.exists(),
        "can_attempt_keynote_export": False,
        "reason": "",
        "checks": {},
    }
    if system != "Darwin":
        report["reason"] = "Keynote export is macOS-only"
        return report
    if not osascript:
        report["reason"] = "osascript not found"
        return report
    if not keynote_app.exists():
        report["reason"] = "Keynote.app not found"
        return report
    report["can_attempt_keynote_export"] = True
    report["reason"] = "macOS, osascript, and Keynote.app are present"
    if check_version:
        version = run_osascript('tell application "Keynote" to get version', timeout)
        report["checks"]["version"] = version
        if version.get("status") != "ok":
            report["can_attempt_keynote_export"] = False
            report["reason"] = "Keynote version check failed; automation may be blocked"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument("--timeout", type=int, default=15, help="osascript timeout for version check.")
    parser.add_argument("--check-version", action="store_true", help="Ask Keynote for its version to verify basic automation.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when Keynote export cannot be attempted.")
    args = parser.parse_args()

    report = capability(max(1, args.timeout), check_version=args.check_version)
    if args.output:
        write_json(args.output.expanduser(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("can_attempt_keynote_export") or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
