#!/usr/bin/env python3
"""Shared production manifest helpers for qiaomu-ppt."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
from pathlib import Path
from typing import Any


DEFAULT_FORMATS = "pptx,pdf,html,html-parity"

CRITICAL_STEPS = {
    "source_adequacy",
    "content_outline_audit",
    "element_plan_audit",
    "style_fit_audit",
    "ppt_master_axis_audit",
    "quality_profile_preflight",
    "image_art_direction",
    "image_generation_readiness",
    "deck_repair_apply",
    "image_generation_preflight",
    "image_generation",
    "visual_asset_manifest_validate",
    "svg_generate",
    "svg_quality",
    "visual_rhythm_check",
    "style_execution_audit",
    "svg_preview",
    "preview_gate_update",
    "svg_finalize",
    "pptx_export",
    "pptx_text_check",
    "page_content_guide",
    "export_bundle",
    "project_check",
    "deck_repair_plan",
}


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value:
        return [str(value)]
    return []


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def latest_existing(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def parse_formats(value: str) -> list[str]:
    known = {"pptx", "pdf", "html", "html-parity", "keynote"}
    formats = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in formats if item not in known]
    if unknown:
        raise SystemExit(f"Unknown export format(s): {', '.join(unknown)}")
    result: list[str] = []
    for item in formats:
        if item not in result:
            result.append(item)
    return result


def can_attempt_keynote_export() -> bool:
    return (
        platform.system() == "Darwin"
        and bool(shutil.which("osascript"))
        and Path("/Applications/Keynote.app").exists()
    )


def quality_policy(profile: str, args: argparse.Namespace) -> dict[str, Any]:
    enforce = profile in {"professional", "final"}
    min_score = args.benchmark_min_score
    if profile == "professional":
        min_score = max(min_score, 75)
    elif profile == "final":
        min_score = max(min_score, 85)
    return {
        "profile": profile,
        "require_real_imagegen": args.require_real_imagegen or enforce,
        "enforce_quality_benchmark": args.enforce_quality_benchmark or enforce,
        "fail_on_critical_repairs": args.fail_on_critical_repairs or enforce,
        "benchmark_min_score": min_score,
        "repair_ready_score": max(args.repair_ready_score, 90 if profile == "final" else args.repair_ready_score),
    }


def collect_artifacts(project: Path, slug: str) -> dict[str, Any]:
    exports = project / "exports"
    previews = project / "previews"
    artifacts: dict[str, Any] = {}
    candidates = {
        "slide_plan": project / "slide_plan.json",
        "source_adequacy": project / "reports" / "source_adequacy.json",
        "source_adequacy_md": project / "reports" / "source_adequacy.md",
        "style_direction": project / "style_direction.json",
        "style_direction_md": project / "style_direction.md",
        "visual_asset_manifest": project / "visual_asset_manifest.json",
        "image_art_direction": project / "image_art_direction.json",
        "image_generation_queue": project / "assets" / "images" / "image_generation_queue.json",
        "image_generation_queue_md": project / "assets" / "images" / "image_generation_queue.md",
        "image_generation_readiness": project / "reports" / "image_generation_readiness.json",
        "image_generation_readiness_md": project / "reports" / "image_generation_readiness.md",
        "built_in_image_generation_tasks": project / "assets" / "images" / "built_in_image_generation_tasks.json",
        "built_in_image_generation_guide": project / "assets" / "images" / "built_in_image_generation_guide.md",
        "image_generation_batch": project / "assets" / "images" / "generation_batch" / "manifest.json",
        "image_generation_requests": project / "assets" / "images" / "generation_batch" / "requests.jsonl",
        "image_generation_import_mapping": project / "assets" / "images" / "generation_batch" / "import_mapping.template.json",
        "image_generation_run": project / "assets" / "images" / "image_generation_run.json",
        "image_prompts": project / "image_prompts.md",
        "image_prompts_json": project / "assets" / "images" / "image_prompts.json",
        "image_prompts_md": project / "assets" / "images" / "image_prompts.md",
        "svg_quality_report": project / "reports" / "svg_quality_report.txt",
        "visual_rhythm_report": project / "reports" / "visual_rhythm_report.json",
        "style_execution_audit": project / "reports" / "style_execution_audit.json",
        "style_execution_audit_md": project / "reports" / "style_execution_audit.md",
        "content_outline_audit": project / "reports" / "content_outline_audit.json",
        "content_outline_audit_md": project / "reports" / "content_outline_audit.md",
        "element_plan_audit": project / "reports" / "element_plan_audit.json",
        "element_plan_audit_md": project / "reports" / "element_plan_audit.md",
        "style_fit_audit": project / "reports" / "style_fit_audit.json",
        "style_fit_audit_md": project / "reports" / "style_fit_audit.md",
        "ppt_master_axis_audit": project / "reports" / "ppt_master_axis_audit.json",
        "ppt_master_axis_audit_md": project / "reports" / "ppt_master_axis_audit.md",
        "deck_quality_benchmark": project / "reports" / "deck_quality_benchmark.json",
        "deck_quality_benchmark_md": project / "reports" / "deck_quality_benchmark.md",
        "deck_repair_plan": project / "reports" / "deck_repair_plan.json",
        "deck_repair_plan_md": project / "reports" / "deck_repair_plan.md",
        "deck_repair_apply_report": project / "reports" / "deck_repair_apply_report.json",
        "deck_repair_apply_report_md": project / "reports" / "deck_repair_apply_report.md",
        "pptx_text_check": project / "pptx_text_check.json",
        "page_content_guide": project / "page_content_guide.json",
        "page_content_guide_md": project / "page_content_guide.md",
        "project_check": project / "project_check.json",
        "export_manifest": project / "export_manifest.json",
        "production_manifest": project / "production_manifest.json",
        "production_report": project / "production_report.md",
        "final_status": project / "final_status.json",
        "final_status_md": project / "交付检查.md",
        "svg_preview_grid": previews / "svg_output" / "thumbnail-grid.jpg",
        "html_preview_grid": previews / "html" / "slide-01-1280x720.png",
        "pptx": exports / f"{slug}.pptx",
        "pdf": exports / f"{slug}.pdf",
        "html": exports / f"{slug}.html",
        "html_parity": exports / f"{slug}-preview.html",
        "keynote": exports / f"{slug}.key",
        "pptx_trace": exports / f"{slug}.pptx.trace.json",
    }
    for key, path in candidates.items():
        if path.exists():
            artifacts[key] = rel(project, path)
    if "pptx" not in artifacts:
        pptx = latest_existing(sorted(exports.glob("*.pptx")) if exports.exists() else [])
        if pptx:
            artifacts["pptx"] = rel(project, pptx)
    return artifacts


def summarize_export_formats(project: Path, requested_formats: list[str]) -> tuple[dict[str, Any], list[str]]:
    manifest_path = project / "export_manifest.json"
    if not manifest_path.exists():
        return {}, [f"export_manifest.json missing after requesting: {', '.join(requested_formats)}"]
    try:
        manifest = read_json(manifest_path)
    except Exception as exc:
        return {}, [f"cannot read export_manifest.json: {exc}"]
    formats = manifest.get("formats", {}) if isinstance(manifest, dict) else {}
    failures: list[str] = []
    for name in requested_formats:
        item = formats.get(name)
        if not isinstance(item, dict):
            failures.append(f"{name}: missing from export_manifest.json")
            continue
        if item.get("status") in {"missing", "failed"}:
            reason = item.get("reason") or item.get("warning") or "no reason recorded"
            failures.append(f"{name}: {item.get('status')} ({reason})")
    return formats if isinstance(formats, dict) else {}, failures


def required_step_failures(steps: list[dict[str, Any]]) -> list[str]:
    return [
        f"{step['name']}: {step.get('reason') or 'returncode ' + str(step.get('returncode'))}"
        for step in steps
        if step.get("required", True) and step.get("status") not in {"passed"}
    ]


def critical_step_failures(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        step
        for step in steps
        if step.get("name") in CRITICAL_STEPS
        and step.get("required", True)
        and step.get("status") != "passed"
    ]


def render_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# Qiaomu PPT Production Report",
        "",
        f"- Project: `{manifest['project']}`",
        f"- Title: {manifest['title']}",
        f"- Slug: `{manifest['slug']}`",
        f"- OK: `{str(manifest['ok']).lower()}`",
        f"- Quality profile: `{manifest.get('quality_policy', {}).get('profile', 'unknown')}`",
        f"- Generated at: `{manifest['generated_at']}`",
        "",
        "## Steps",
        "",
    ]
    for step in manifest.get("steps", []):
        marker = "OK" if step.get("status") == "passed" else step.get("status", "unknown").upper()
        required = "required" if step.get("required") else "optional"
        lines.append(f"- {marker} `{step.get('name')}` ({required}, {step.get('duration_seconds', 0)}s)")
        if step.get("reason"):
            lines.append(f"  Reason: {step['reason']}")
    lines.extend(["", "## Export Formats", ""])
    export_formats = manifest.get("export_formats", {})
    if export_formats:
        for name, item in export_formats.items():
            status = item.get("status") if isinstance(item, dict) else "unknown"
            path = item.get("path") if isinstance(item, dict) else ""
            reason = item.get("reason") if isinstance(item, dict) else ""
            suffix = f" -> `{path}`" if path else ""
            if reason:
                suffix += f" ({reason})"
            lines.append(f"- `{name}`: {status}{suffix}")
    else:
        lines.append("- No export manifest available.")
    lines.extend(["", "## Artifacts", ""])
    for key, value in manifest.get("artifacts", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    if manifest.get("failures"):
        lines.extend(["", "## Failures", ""])
        for failure in manifest["failures"]:
            lines.append(f"- {failure}")
    if manifest.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for warning in manifest["warnings"]:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)
