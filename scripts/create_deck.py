#!/usr/bin/env python3
"""One-command qiaomu-ppt project creation and optional production."""

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
DEFAULT_FORMATS = "pptx,pdf,html,html-parity"
DEFAULT_OUTPUTS_ROOT = Path.home() / "Downloads" / "Qiaomu PPT"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def tail(value: str, limit: int = 6000) -> str:
    return value[-limit:] if len(value) > limit else value


def command_to_string(command: list[Any]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def run_step(name: str, command: list[Any], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    payload: dict[str, Any] = {
        "name": name,
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


def infer_project_from_prepare(step: dict[str, Any]) -> Path | None:
    stdout = str(step.get("stdout_tail") or "")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        start = stdout.find("{")
        end = stdout.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            payload = json.loads(stdout[start : end + 1])
        except json.JSONDecodeError:
            return None
    project = payload.get("project") if isinstance(payload, dict) else ""
    return Path(project).expanduser().resolve() if project else None


def load_project_report(project: Path) -> dict[str, Any]:
    path = project / "project_prepare_report.json"
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def render_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# Qiaomu PPT Create Report",
        "",
        f"- OK: `{str(manifest.get('ok')).lower()}`",
        f"- Project: `{manifest.get('project', '')}`",
        f"- Topic: {manifest.get('topic', '')}",
        f"- Produce requested: `{str(manifest.get('produce_requested')).lower()}`",
        f"- Quality profile: `{manifest.get('quality_profile', '')}`",
        f"- Generated at: `{manifest.get('generated_at', '')}`",
        "",
        "## Steps",
        "",
    ]
    for step in manifest.get("steps", []):
        marker = "OK" if step.get("status") == "passed" else step.get("status", "unknown").upper()
        lines.append(f"- {marker} `{step.get('name')}` ({step.get('duration_seconds', 0)}s)")
        if step.get("reason"):
            lines.append(f"  Reason: {step['reason']}")
    if manifest.get("artifacts"):
        lines.extend(["", "## Artifacts", ""])
        for key, value in manifest["artifacts"].items():
            if value:
                lines.append(f"- `{key}`: `{value}`")
    if manifest.get("failures"):
        lines.extend(["", "## Failures", ""])
        for failure in manifest["failures"]:
            lines.append(f"- {failure}")
    if manifest.get("next_step"):
        lines.extend(["", "## Next Step", "", manifest["next_step"]])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a qiaomu-ppt deck from topic/files/links, then optionally produce deliverables.")
    parser.add_argument("inputs", nargs="*", help="URLs, files, folders, or ZIP archives to ingest.")
    parser.add_argument("--input", dest="extra_inputs", action="append", default=[], help="Additional input. Can be repeated.")
    parser.add_argument("--topic", default="", help="Deck topic/title. Required when no inputs are supplied.")
    parser.add_argument("--project", type=Path, help="Output project directory. Defaults to ~/Downloads/Qiaomu PPT/<date>-<slug>.")
    parser.add_argument("--outputs-root", type=Path, default=DEFAULT_OUTPUTS_ROOT, help="Root used when --project is omitted.")
    parser.add_argument("--slug", default="", help="Project/output slug.")
    parser.add_argument("--title", default="", help="Deck title for production. Defaults to --topic or prepared title.")
    parser.add_argument("--slides", type=int, default=10, help="Target slide count.")
    parser.add_argument("--audience", default="general Chinese-speaking audience", help="Target audience.")
    parser.add_argument("--purpose", default="turn source material into a clear, sourced presentation argument", help="Deck purpose.")
    parser.add_argument("--desired-action", default="记住核心判断，并知道下一步该回到哪些来源继续核查", help="Desired audience action.")
    parser.add_argument("--route", default="", help="qiaomu-ppt route override.")
    parser.add_argument("--style-query", default="", help="Optional style recommendation query.")
    parser.add_argument("--formats", default=DEFAULT_FORMATS, help=f"Production formats. Default: {DEFAULT_FORMATS}.")
    parser.add_argument("--quality-profile", choices=["draft", "professional", "final"], default="final")
    parser.add_argument("--produce", action="store_true", help="Run produce_deck.py after preparation.")
    parser.add_argument("--review-first", action="store_true", help="Prepare only, even if --produce was supplied by a wrapper.")
    parser.add_argument(
        "--generate-images",
        dest="generate_images",
        action="store_true",
        default=True,
        help="Pass --generate-images to production. Enabled by default for complete-deck quality.",
    )
    parser.add_argument(
        "--no-generate-images",
        dest="generate_images",
        action="store_false",
        help="Disable real image generation; use only for explicit draft/offline runs.",
    )
    parser.add_argument("--image-provider", default="openai", help="Image provider for production.")
    parser.add_argument("--image-model", default="", help="Image model override for production.")
    parser.add_argument("--image-api-key-env", default="", help="Image provider API key env var.")
    parser.add_argument("--download-images", action="store_true", help="Download source URL images during intake/research.")
    parser.add_argument("--max-images", type=int, default=12)
    parser.add_argument("--max-files", type=int, default=80)
    parser.add_argument("--max-cards-per-source", type=int, default=4)
    parser.add_argument("--skip-auto-research", action="store_true", help="For topic-only requests, write a research brief but do not fetch sources.")
    parser.add_argument("--no-auto-supplement-sources", action="store_true", help="Disable supplemental topic research when provided sources are too thin.")
    parser.add_argument("--research-provider", choices=["auto", "wikipedia", "duckduckgo", "openalex"], default="auto")
    parser.add_argument("--research-depth", choices=["fast", "balanced", "deep"], default="fast")
    parser.add_argument("--research-max-pages", type=int, default=3)
    parser.add_argument("--research-per-url-timeout", type=int, default=25)
    parser.add_argument("--source-visual-limit", type=int, default=3)
    parser.add_argument("--source-visual-timeout", type=int, default=8)
    parser.add_argument("--skip-source-visual-resolve", action="store_true")
    parser.add_argument("--generate-preview", action="store_true", help="Generate the isolated four-slide preview during preparation.")
    parser.add_argument("--preview-decision", choices=["pending", "approved", "skipped"], default="pending")
    parser.add_argument("--preview-note", default="", help="Preview approval/skip note.")
    parser.add_argument("--materialize-assets", action="store_true", help="Create procedural preview assets during preparation.")
    parser.add_argument("--auto-apply-repairs", action="store_true", help="Pass --auto-apply-repairs to production.")
    parser.add_argument("--apply-source-ids", action="store_true", help="Pass --apply-source-ids with --auto-apply-repairs.")
    parser.add_argument("--allow-missing-formats", action="store_true", help="Pass --allow-missing-formats to production.")
    parser.add_argument("--keynote-strategy", choices=["auto", "modern", "keynote09"], default="auto")
    parser.add_argument("--keynote-timeout", type=int, default=90)
    parser.add_argument("--force", action="store_true", help="Overwrite generated contracts and SVGs where supported.")
    parser.add_argument("--timeout", type=int, default=420, help="Per-step timeout for production.")
    args = parser.parse_args()

    inputs = [*args.inputs, *args.extra_inputs]
    if not inputs and not args.topic:
        raise SystemExit("provide at least one input or --topic")

    prepare_command: list[Any] = [
        sys.executable,
        SCRIPT_DIR / "prepare_deck_project.py",
        *inputs,
        "--slides",
        str(args.slides),
        "--audience",
        args.audience,
        "--purpose",
        args.purpose,
        "--desired-action",
        args.desired_action,
        "--final-delivery",
        "pptx_plus_semantic_html",
        "--max-images",
        str(args.max_images),
        "--max-files",
        str(args.max_files),
        "--max-cards-per-source",
        str(args.max_cards_per_source),
        "--research-provider",
        args.research_provider,
        "--research-depth",
        args.research_depth,
        "--research-max-pages",
        str(args.research_max_pages),
        "--research-per-url-timeout",
        str(args.research_per_url_timeout),
        "--source-visual-limit",
        str(args.source_visual_limit),
        "--source-visual-timeout",
        str(args.source_visual_timeout),
        "--preview-decision",
        args.preview_decision,
    ]
    if args.topic:
        prepare_command.extend(["--topic", args.topic])
    if args.project:
        prepare_command.extend(["--project", args.project])
    else:
        prepare_command.extend(["--outputs-root", args.outputs_root])
    if args.slug:
        prepare_command.extend(["--slug", args.slug])
    if args.route:
        prepare_command.extend(["--route", args.route])
    if args.style_query:
        prepare_command.extend(["--style-query", args.style_query])
    if args.download_images:
        prepare_command.append("--download-images")
    if args.skip_auto_research:
        prepare_command.append("--skip-auto-research")
    if args.no_auto_supplement_sources:
        prepare_command.append("--no-auto-supplement-sources")
    if args.skip_source_visual_resolve:
        prepare_command.append("--skip-source-visual-resolve")
    if args.generate_preview:
        prepare_command.append("--generate-preview")
    if args.preview_note:
        prepare_command.extend(["--preview-approval-note", args.preview_note])
    if args.materialize_assets or args.quality_profile == "draft":
        prepare_command.append("--materialize-assets")
    if args.force:
        prepare_command.append("--force")

    cwd = Path.cwd()
    steps = [run_step("prepare_deck_project", prepare_command, cwd=cwd, timeout=max(60, args.research_max_pages * args.research_per_url_timeout + 120))]
    project = args.project.expanduser().resolve() if args.project else infer_project_from_prepare(steps[0])
    prepare_report = load_project_report(project) if project else {}

    failures: list[str] = []
    if steps[0].get("status") != "passed":
        failures.append("prepare_deck_project failed")
    if not project:
        failures.append("could not determine project directory from preparation output")

    produce_requested = bool(args.produce and not args.review_first)
    if produce_requested and project and not failures:
        if prepare_report.get("status") != "ready_for_design_review":
            failures.append(f"project is not ready for production: {prepare_report.get('status', 'unknown')}")
        elif not (project / "slide_plan.json").exists():
            failures.append("slide_plan.json missing after preparation")
        else:
            title = args.title or args.topic or prepare_report.get("topic") or project.name
            slug = args.slug or project.name
            produce_command: list[Any] = [
                sys.executable,
                SCRIPT_DIR / "produce_deck.py",
                project,
                "--slug",
                slug,
                "--title",
                title,
                "--formats",
                args.formats,
                "--quality-profile",
                args.quality_profile,
                "--preview-decision",
                "skipped",
                "--preview-note",
                "Skipped by create_deck.py --produce one-command run.",
                "--keynote-strategy",
                args.keynote_strategy,
                "--keynote-timeout",
                str(args.keynote_timeout),
                "--timeout",
                str(args.timeout),
            ]
            if args.generate_images:
                produce_command.extend(["--generate-images", "--image-provider", args.image_provider])
                if args.image_model:
                    produce_command.extend(["--image-model", args.image_model])
                if args.image_api_key_env:
                    produce_command.extend(["--image-api-key-env", args.image_api_key_env])
            if args.auto_apply_repairs:
                produce_command.append("--auto-apply-repairs")
            if args.apply_source_ids:
                produce_command.append("--apply-source-ids")
            if args.allow_missing_formats:
                produce_command.append("--allow-missing-formats")
            if args.force:
                produce_command.append("--force")
            steps.append(run_step("produce_deck", produce_command, cwd=cwd, timeout=max(args.timeout * 8, 900)))
            if steps[-1].get("status") != "passed":
                failures.append("produce_deck failed")

    artifacts: dict[str, str] = {}
    if project:
        candidates = {
            "project_prepare_report": project / "project_prepare_report.json",
            "production_manifest": project / "production_manifest.json",
            "design_proposal": project / "design_proposal.md",
            "slide_plan": project / "slide_plan.json",
            "visual_asset_manifest": project / "visual_asset_manifest.json",
            "export_manifest": project / "export_manifest.json",
        }
        for key, path in candidates.items():
            if path.exists():
                try:
                    artifacts[key] = str(path.relative_to(project))
                except ValueError:
                    artifacts[key] = str(path)
        artifacts["deck_create_manifest"] = "deck_create_manifest.json"
        artifacts["deck_create_report"] = "deck_create_report.md"

    ok = not failures
    next_step = ""
    if not ok:
        next_step = "Inspect deck_create_manifest.json plus the failed step tails, then rerun with the missing evidence fixed."
    elif not produce_requested:
        next_step = "Review design_proposal.md, then rerun create_deck.py with --produce when the direction is approved."
    else:
        next_step = "Inspect production_manifest.json, export_manifest.json, and rendered previews before calling the deck final."

    manifest = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/create_deck.py",
        "generated_at": utc_now(),
        "ok": ok,
        "project": str(project) if project else "",
        "topic": args.topic or prepare_report.get("topic", ""),
        "inputs": inputs,
        "produce_requested": produce_requested,
        "quality_profile": args.quality_profile,
        "formats": args.formats,
        "steps": steps,
        "prepare_status": prepare_report.get("status", ""),
        "artifacts": artifacts,
        "failures": failures,
        "next_step": next_step,
        "external_skill_dependency": "none",
    }
    if project:
        write_json(project / "deck_create_manifest.json", manifest)
        write_text(project / "deck_create_report.md", render_report(manifest))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
