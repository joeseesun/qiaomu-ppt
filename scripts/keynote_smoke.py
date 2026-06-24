#!/usr/bin/env python3
"""Run a real Keynote export smoke test for an existing qiaomu-ppt project."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def tail(value: str, limit: int = 6000) -> str:
    return value[-limit:] if len(value) > limit else value


def command_to_string(command: list[Any]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def run(command: list[Any], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    payload: dict[str, Any] = {
        "command": command_to_string(command),
        "started_at": utc_now(),
    }
    try:
        proc = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        payload.update(
            {
                "status": "passed" if proc.returncode == 0 else "failed",
                "returncode": proc.returncode,
                "duration_seconds": round(time.time() - started, 2),
                "stdout_tail": tail(proc.stdout),
                "stderr_tail": tail(proc.stderr),
            }
        )
    except subprocess.TimeoutExpired as exc:
        payload.update(
            {
                "status": "failed",
                "returncode": None,
                "duration_seconds": round(time.time() - started, 2),
                "reason": f"timed out after {timeout}s",
                "stdout_tail": tail(exc.stdout or ""),
                "stderr_tail": tail(exc.stderr or ""),
            }
        )
    return payload


def default_pptx(project: Path) -> Path | None:
    exports = project / "exports"
    if not exports.exists():
        return None
    pptx_files = sorted(exports.glob("*.pptx"), key=lambda path: path.stat().st_mtime, reverse=True)
    return pptx_files[0] if pptx_files else None


def render_markdown(report: dict[str, Any]) -> str:
    keynote = report.get("keynote_result") if isinstance(report.get("keynote_result"), dict) else {}
    lines = [
        "# Keynote Smoke Report",
        "",
        f"- OK: `{str(report.get('ok')).lower()}`",
        f"- Project: `{report.get('project', '')}`",
        f"- PPTX: `{report.get('pptx', '')}`",
        f"- Strategy: `{report.get('strategy', '')}`",
        f"- Keynote status: `{keynote.get('status', 'unknown')}`",
        f"- Keynote path: `{keynote.get('path', '')}`",
        f"- Compatibility format: `{keynote.get('compatibility_format', '')}`",
        f"- Generated at: `{report.get('generated_at', '')}`",
        "",
        "## Steps",
        "",
    ]
    for name in ("export_bundle", "project_check"):
        step = report.get("steps", {}).get(name, {})
        marker = "OK" if step.get("status") == "passed" else step.get("status", "unknown").upper()
        lines.append(f"- {marker} `{name}` ({step.get('duration_seconds', 0)}s)")
        if step.get("reason"):
            lines.append(f"  Reason: {step['reason']}")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        for failure in report["failures"]:
            lines.append(f"- {failure}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real Keynote export smoke test.")
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory.")
    parser.add_argument("--pptx", type=Path, help="PPTX source. Defaults to newest exports/*.pptx.")
    parser.add_argument("--slug", default="keynote-smoke", help="Output slug for the .key artifact.")
    parser.add_argument("--strategy", choices=["auto", "modern", "keynote09"], default="keynote09")
    parser.add_argument("--timeout", type=int, default=60, help="Keynote AppleScript timeout in seconds.")
    parser.add_argument("--output", type=Path, help="JSON report path. Default: <project>/reports/keynote_smoke.json")
    parser.add_argument("--markdown", type=Path, help="Markdown report path. Default: <project>/reports/keynote_smoke.md")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    if not project.exists():
        raise SystemExit(f"project does not exist: {project}")
    pptx = args.pptx.expanduser().resolve() if args.pptx else default_pptx(project)
    if not pptx or not pptx.exists():
        raise SystemExit("PPTX source missing; pass --pptx or create exports/*.pptx first")

    reports = project / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    output = args.output or reports / "keynote_smoke.json"
    markdown = args.markdown or reports / "keynote_smoke.md"
    check_output = reports / "keynote_smoke_project_check.json"

    export_command = [
        sys.executable,
        SCRIPT_DIR / "export_bundle.py",
        project,
        "--pptx",
        pptx,
        "--slug",
        args.slug,
        "--formats",
        "keynote",
        "--keynote-strategy",
        args.strategy,
        "--keynote-timeout",
        str(args.timeout),
        "--no-html-screenshots",
    ]
    export_step = run(export_command, cwd=project, timeout=max(args.timeout + 60, 120))

    check_command = [
        sys.executable,
        SCRIPT_DIR / "check_project.py",
        project,
        "--output",
        check_output,
    ]
    check_step = run(check_command, cwd=project, timeout=180)

    export_manifest = {}
    if (project / "export_manifest.json").exists():
        try:
            payload = read_json(project / "export_manifest.json")
            export_manifest = payload if isinstance(payload, dict) else {}
        except Exception:
            export_manifest = {}
    keynote_result = {}
    formats = export_manifest.get("formats") if isinstance(export_manifest, dict) else {}
    if isinstance(formats, dict) and isinstance(formats.get("keynote"), dict):
        keynote_result = formats["keynote"]

    failures: list[str] = []
    if export_step.get("status") != "passed":
        failures.append("export_bundle failed")
    if check_step.get("status") != "passed":
        failures.append("check_project failed")
    if keynote_result.get("status") not in {"exported", "existing"}:
        failures.append(f"Keynote export did not produce valid evidence: {keynote_result.get('status', 'missing')}")
    rel_key = str(keynote_result.get("path") or "")
    if rel_key and not (project / rel_key).exists():
        failures.append(f"Keynote output path missing: {rel_key}")

    report = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/keynote_smoke.py",
        "generated_at": utc_now(),
        "ok": not failures,
        "project": str(project),
        "pptx": str(pptx),
        "strategy": args.strategy,
        "steps": {
            "export_bundle": export_step,
            "project_check": check_step,
        },
        "keynote_result": keynote_result,
        "keynote_capability": export_manifest.get("keynote_capability") if isinstance(export_manifest, dict) else {},
        "reports": {
            "export_manifest": "export_manifest.json",
            "project_check": str(check_output.relative_to(project)) if check_output.exists() else "",
        },
        "failures": failures,
        "external_skill_dependency": "none",
    }
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
