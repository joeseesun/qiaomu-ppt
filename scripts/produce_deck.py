#!/usr/bin/env python3
"""Run the formal qiaomu-ppt deck production pipeline."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_FORMATS = "pptx,pdf,html,html-parity"
CRITICAL_STEPS = {
    "source_adequacy",
    "content_outline_audit",
    "element_plan_audit",
    "style_fit_audit",
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
    path.write_text(text, encoding="utf-8")


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(path)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "deck"


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


def is_unresolved_source_ai_fallback(item: dict[str, Any]) -> bool:
    asset_id = str(item.get("asset_id") or "").lower()
    notes = str(item.get("notes") or "").lower()
    return asset_id.endswith("-ai-fallback") or (
        "ai fallback for preview/production while the remote source image remains" in notes
    )


def analyze_ai_asset_readiness(project: Path) -> dict[str, Any]:
    manifest_path = project / "visual_asset_manifest.json"
    evidence: dict[str, Any] = {
        "visual_asset_manifest": rel(project, manifest_path),
        "ai_count": 0,
        "procedural_fallback_count": 0,
        "non_terminal_ai_count": 0,
        "real_imagegen_count": 0,
        "source_unresolved_fallback_count": 0,
        "examples": [],
        "source_unresolved_fallback_examples": [],
    }
    if not manifest_path.exists():
        evidence["visual_asset_manifest_exists"] = False
        return evidence
    evidence["visual_asset_manifest_exists"] = True
    try:
        payload = read_json(manifest_path)
    except Exception as exc:
        evidence["error"] = f"cannot read visual_asset_manifest.json: {exc}"
        return evidence
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        evidence["error"] = "visual_asset_manifest.json items must be a list"
        return evidence
    for item in items:
        if not isinstance(item, dict) or str(item.get("acquire_via") or "").lower() != "ai":
            continue
        notes = str(item.get("notes") or "").lower()
        if "dormant fallback" in notes:
            continue
        if is_unresolved_source_ai_fallback(item):
            evidence["source_unresolved_fallback_count"] += 1
            if len(evidence["source_unresolved_fallback_examples"]) < 5:
                evidence["source_unresolved_fallback_examples"].append(
                    item.get("filename") or item.get("asset_id") or item.get("path")
                )
            continue
        evidence["ai_count"] += 1
        status = str(item.get("status") or "")
        generator = str(item.get("generator") or "")
        if status == "Generated" and generator == "procedural-preview-fallback":
            evidence["procedural_fallback_count"] += 1
            if len(evidence["examples"]) < 5:
                evidence["examples"].append(item.get("filename") or item.get("asset_id") or item.get("path"))
        elif status == "Generated" and generator:
            evidence["real_imagegen_count"] += 1
        elif status in {"Pending", "Needs-Manual", "Missing", "Failed"}:
            evidence["non_terminal_ai_count"] += 1
            if len(evidence["examples"]) < 5:
                evidence["examples"].append(item.get("filename") or item.get("asset_id") or item.get("path"))
    return evidence


def analyze_source_visual_readiness(project: Path) -> dict[str, Any]:
    manifest_path = project / "visual_asset_manifest.json"
    evidence: dict[str, Any] = {
        "visual_asset_manifest": rel(project, manifest_path),
        "source_count": 0,
        "existing_source_count": 0,
        "unresolved_source_count": 0,
        "source_web_user_count": 0,
        "existing_source_web_user_count": 0,
        "missing_file_count": 0,
        "examples": [],
        "missing_file_examples": [],
    }
    if not manifest_path.exists():
        evidence["visual_asset_manifest_exists"] = False
        return evidence
    evidence["visual_asset_manifest_exists"] = True
    try:
        payload = read_json(manifest_path)
    except Exception as exc:
        evidence["error"] = f"cannot read visual_asset_manifest.json: {exc}"
        return evidence
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        evidence["error"] = "visual_asset_manifest.json items must be a list"
        return evidence
    terminal_statuses = {"Existing", "Sourced"}
    for item in items:
        if not isinstance(item, dict):
            continue
        via = str(item.get("acquire_via") or "").lower()
        if via not in {"source", "web", "user"}:
            continue
        if via == "source":
            evidence["source_count"] += 1
        evidence["source_web_user_count"] += 1
        label = item.get("filename") or item.get("asset_id") or item.get("path")
        status = str(item.get("status") or "")
        raw_path = str(item.get("path") or "").strip()
        file_exists = bool(raw_path and (project / raw_path).exists())
        if status in terminal_statuses and file_exists:
            if via == "source":
                evidence["existing_source_count"] += 1
            evidence["existing_source_web_user_count"] += 1
            continue
        evidence["unresolved_source_count"] += 1
        if len(evidence["examples"]) < 5:
            evidence["examples"].append(label)
        if raw_path and not file_exists:
            evidence["missing_file_count"] += 1
            if len(evidence["missing_file_examples"]) < 5:
                evidence["missing_file_examples"].append(label)
    return evidence


def quality_profile_preflight(
    project: Path,
    profile: str,
    requested_formats: list[str],
    *,
    generate_images: bool,
    no_html_screenshots: bool,
) -> dict[str, Any]:
    started = time.time()
    failures: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {
        "requested_formats": requested_formats,
        "generate_images": generate_images,
        "no_html_screenshots": no_html_screenshots,
    }
    if profile in {"professional", "final"}:
        required_formats = {"pptx", "pdf", "html"}
        missing_formats = sorted(required_formats - set(requested_formats))
        if missing_formats:
            failures.append(
                f"{profile} profile requires requested formats: {', '.join(sorted(required_formats))}; "
                f"missing {', '.join(missing_formats)}"
            )
        if no_html_screenshots and "html" in requested_formats:
            message = "formal HTML requested but --no-html-screenshots removes browser readability evidence"
            if profile == "final":
                failures.append(message)
            else:
                warnings.append(message)
        ai_evidence = analyze_ai_asset_readiness(project)
        evidence["ai_assets"] = ai_evidence
        source_visual_evidence = analyze_source_visual_readiness(project)
        evidence["source_visuals"] = source_visual_evidence
        unresolved_sources = int(source_visual_evidence.get("unresolved_source_count") or 0)
        if unresolved_sources:
            failures.append(
                f"{profile} profile found unresolved source visual assets ({unresolved_sources}); "
                "run resolve_source_visuals.py, add/copy real source images, or lower to --quality-profile draft. "
                "Do not use AI fallback as evidence imagery."
            )
        slide_count = 0
        try:
            plan = read_json(project / "slide_plan.json")
            raw_slides = plan.get("slides") if isinstance(plan, dict) else plan
            slide_count = len(raw_slides) if isinstance(raw_slides, list) else 0
        except Exception:
            slide_count = 0
        source_visual_floor = max(3, round(slide_count * 0.25)) if slide_count > 8 else 0
        has_real_ai = int(ai_evidence.get("real_imagegen_count") or 0) > 0
        source_visual_ready = int(source_visual_evidence.get("existing_source_web_user_count") or 0) >= source_visual_floor
        if slide_count > 8 and not has_real_ai and not source_visual_ready:
            message = (
                f"{profile} profile has no real generated images and only "
                f"{source_visual_evidence.get('existing_source_web_user_count', 0)} ready source/web/user visual(s); "
                f"target at least {source_visual_floor} source visuals or add AI atmosphere/concept assets. "
                "Use --generate-images, built-in image-generation handoff, or downgrade to --quality-profile draft."
            )
            if profile == "final":
                failures.append(message)
            else:
                warnings.append(message)
        needs_real_images = bool(
            ai_evidence.get("procedural_fallback_count") or ai_evidence.get("non_terminal_ai_count")
        )
        if needs_real_images and not generate_images:
            failures.append(
                f"{profile} profile found AI visual assets without real generated outputs "
                f"({ai_evidence.get('procedural_fallback_count', 0)} procedural fallback, "
                f"{ai_evidence.get('non_terminal_ai_count', 0)} non-terminal); rerun with --generate-images "
                "for a configured API backend, use assets/images/built_in_image_generation_guide.md "
                "for Codex/host-native image generation, or use --quality-profile draft for a clearly labeled rough preview. "
                "See reports/image_generation_readiness.md for provider/key/queue/built-in recovery commands."
            )
    else:
        evidence["ai_assets"] = analyze_ai_asset_readiness(project)
    status = "failed" if failures else "passed"
    result: dict[str, Any] = {
        "name": "quality_profile_preflight",
        "required": profile in {"professional", "final"},
        "command": "",
        "status": status,
        "started_at": utc_now(),
        "duration_seconds": round(time.time() - started, 2),
        "quality_profile": profile,
        "evidence": evidence,
    }
    if failures:
        result["reason"] = "; ".join(failures)
        result["failures"] = failures
    if warnings:
        result["warnings"] = warnings
    return result


def load_title(project: Path, explicit: str) -> str:
    if explicit:
        return explicit
    plan_path = project / "slide_plan.json"
    if plan_path.exists():
        try:
            plan = read_json(plan_path)
            slides = plan.get("slides") if isinstance(plan, dict) else plan
            if isinstance(slides, list) and slides:
                first = slides[0] if isinstance(slides[0], dict) else {}
                title = str(first.get("claim_title") or first.get("title") or "").strip()
                if title:
                    return title
        except Exception:
            pass
    return project.name


def load_slides(project: Path) -> list[dict[str, Any]]:
    plan_path = project / "slide_plan.json"
    plan = read_json(plan_path)
    slides = plan.get("slides") if isinstance(plan, dict) else plan
    if not isinstance(slides, list):
        return []
    return [item for item in slides if isinstance(item, dict)]


def command_to_string(command: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def tail(value: str, limit: int = 6000) -> str:
    return value[-limit:] if len(value) > limit else value


def run_step(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    required: bool = True,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.time()
    payload: dict[str, Any] = {
        "name": name,
        "required": required,
        "command": command_to_string(command),
        "started_at": utc_now(),
    }
    try:
        proc = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
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


def skip_step(name: str, reason: str, *, required: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "required": required,
        "command": "",
        "status": "skipped",
        "reason": reason,
        "started_at": utc_now(),
        "duration_seconds": 0,
    }


def step_ok(step: dict[str, Any]) -> bool:
    return step.get("status") in {"passed", "skipped_optional"}


def latest_existing(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


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


def report_lists(path: Path) -> tuple[list[str], list[str]]:
    if not path.exists():
        return [], []
    try:
        payload = read_json(path)
    except Exception:
        return [], []
    failures = payload.get("failures") if isinstance(payload, dict) else []
    warnings = payload.get("warnings") if isinstance(payload, dict) else []
    return (
        [str(item) for item in failures] if isinstance(failures, list) else [],
        [str(item) for item in warnings] if isinstance(warnings, list) else [],
    )


def selected_preview_slides(slide_count: int) -> list[int]:
    if slide_count <= 0:
        return []
    selected = [1, max(2, slide_count // 3), max(3, (slide_count * 2) // 3), slide_count]
    selected = sorted(dict.fromkeys(min(slide_count, max(1, item)) for item in selected))
    candidate = 1
    while len(selected) < min(4, slide_count):
        if candidate not in selected:
            selected.append(candidate)
        candidate += 1
    return selected[:4]


def upsert_preview_gate(
    project: Path,
    slide_count: int,
    *,
    decision: str,
    approval_note: str,
) -> dict[str, Any]:
    started = time.time()
    gate_path = project / "preview_gate.json"
    if slide_count <= 7:
        return {
            "name": "preview_gate_update",
            "required": False,
            "command": "",
            "status": "passed",
            "reason": "preview gate not required for decks with 7 or fewer slides",
            "started_at": utc_now(),
            "duration_seconds": 0,
        }
    gate: dict[str, Any] = {}
    if gate_path.exists():
        try:
            loaded = read_json(gate_path)
            if isinstance(loaded, dict):
                gate = loaded
        except Exception:
            gate = {}
    selected = gate.get("selected_slides")
    if not isinstance(selected, list) or len(selected) != 4:
        selected = selected_preview_slides(slide_count)
    outputs = []
    for item in selected[:4]:
        try:
            slide_no = int(item)
        except (TypeError, ValueError):
            continue
        rel_path = f"previews/svg_output/slide-{slide_no:02d}.png"
        if (project / rel_path).exists():
            outputs.append(rel_path)
    grid = "previews/svg_output/thumbnail-grid.jpg"
    if (project / grid).exists():
        outputs.append(grid)
    gate.update(
        {
            "schema_version": "1.0.0",
            "mode": "four_slide_preview",
            "status": "approved_for_full_generation" if decision == "approved" else "skipped_by_operator",
            "user_decision": "approved" if decision == "approved" else "pending",
            "selected_slides": selected[:4],
            "outputs": outputs,
            "qa_focus": gate.get("qa_focus")
            if isinstance(gate.get("qa_focus"), list)
            else ["typography", "background", "connector geometry", "html readability"],
            "updated_at": utc_now(),
            "updated_by": "qiaomu-ppt/scripts/produce_deck.py",
        }
    )
    if decision == "approved":
        gate["approval_note"] = approval_note or "Approved by formal production invocation after SVG preview render."
        gate.pop("skipped_by_user", None)
        gate.pop("skip_instruction", None)
    else:
        gate["skipped_by_user"] = True
        gate["skip_instruction"] = approval_note or "Operator explicitly skipped four-slide preview approval during production run."
    write_json(gate_path, gate)
    status = "passed" if outputs else "failed"
    result: dict[str, Any] = {
        "name": "preview_gate_update",
        "required": True,
        "command": "",
        "status": status,
        "started_at": utc_now(),
        "duration_seconds": round(time.time() - started, 2),
        "outputs": outputs,
    }
    if not outputs:
        result["reason"] = "no SVG preview outputs found for selected preview slides"
    return result


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


def render_report(manifest: dict[str, Any]) -> str:
    lines = [
        f"# Qiaomu PPT Production Report",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a formal qiaomu-ppt production pipeline.")
    parser.add_argument("project", type=Path, help="Prepared project directory containing slide_plan.json.")
    parser.add_argument("--slug", default="", help="Output basename. Defaults to project name.")
    parser.add_argument("--title", default="", help="Deck title used in export metadata.")
    parser.add_argument("--formats", default=DEFAULT_FORMATS, help=f"Comma-separated export formats. Default: {DEFAULT_FORMATS}.")
    parser.add_argument("--no-auto-keynote", action="store_true", help="Do not auto-add Keynote on macOS professional/final runs.")
    parser.add_argument("--svg-source", default="final", choices=["output", "final"], help="PPTX/HTML SVG source after generation.")
    parser.add_argument("--materialize-assets", action="store_true", help="Generate procedural local preview assets for pending AI rows.")
    parser.add_argument(
        "--generate-images",
        dest="generate_images",
        action="store_true",
        default=True,
        help="Call a configured real image-generation backend and import results before rendering. Enabled by default for production.",
    )
    parser.add_argument(
        "--no-generate-images",
        dest="generate_images",
        action="store_false",
        help="Disable real image generation; use only for explicit draft/offline runs.",
    )
    parser.add_argument("--image-provider", default="openai", help="Image generation provider for --generate-images. Default: openai.")
    parser.add_argument("--image-model", default="", help="Image generation model for --generate-images. Defaults to the provider preset.")
    parser.add_argument("--image-limit", type=int, default=0, help="Maximum real images to generate. 0 means all queued items.")
    parser.add_argument("--image-size", default="", help="Provider image size override for --generate-images.")
    parser.add_argument("--image-quality", default="auto", help="Provider image quality for --generate-images.")
    parser.add_argument("--image-api-key-env", default="", help="Environment variable holding the image provider API key. Defaults to the provider preset.")
    parser.add_argument("--image-base-url", default="", help="Optional OpenAI-compatible image provider base URL.")
    parser.add_argument("--image-provider-config", type=Path, default=SCRIPT_DIR.parent / "data" / "image_generation_providers.json", help="Image provider preset JSON.")
    parser.add_argument("--image-request-format", default="", choices=["", "openai-sdk", "openai-images-http", "async-task"], help="Image provider request format override.")
    parser.add_argument("--image-auth-scheme", default="", help="Image provider auth scheme override: bearer, x-api-key, none, or custom header name.")
    parser.add_argument("--image-endpoint-path", default="", help="HTTP image generation endpoint path override.")
    parser.add_argument("--image-submit-path", default="", help="Async image task submit endpoint path override.")
    parser.add_argument("--image-status-path-template", default="", help="Async image task status path template.")
    parser.add_argument("--image-poll-interval", type=float, default=0.0, help="Async image task poll interval seconds.")
    parser.add_argument("--image-poll-timeout", type=float, default=0.0, help="Async image task poll timeout seconds.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing SVG output and regenerated assets where supported.")
    parser.add_argument("--auto-apply-repairs", action="store_true", help="Apply safe deterministic contract repairs before SVG generation.")
    parser.add_argument("--apply-source-ids", action="store_true", help="With --auto-apply-repairs, heuristically fill missing source_card_ids from source_cards.json.")
    parser.add_argument("--allow-missing-formats", action="store_true", help="Exit 0 when only requested export formats are missing/failed.")
    parser.add_argument("--no-html-screenshots", action="store_true", help="Skip Playwright screenshots for formal HTML QA.")
    parser.add_argument(
        "--quality-profile",
        choices=["draft", "professional", "final"],
        default="final",
        help=(
            "Quality enforcement profile. final is the default and enforces real imagegen evidence, "
            "PPTX/PDF/formal HTML, benchmark score >=85, browser HTML evidence, and critical repair failure; "
            "professional is an explicit lower bar at >=75; draft keeps fast preview behavior."
        ),
    )
    parser.add_argument("--preview-decision", choices=["approved", "skipped"], default="approved", help="How to close the four-slide preview gate during production.")
    parser.add_argument("--preview-note", default="", help="Approval or skip note written into preview_gate.json.")
    parser.add_argument("--timeout", type=int, default=420, help="Per-step timeout in seconds for heavy generation/export steps.")
    parser.add_argument("--keynote-timeout", type=int, default=90, help="AppleScript Keynote export timeout.")
    parser.add_argument(
        "--keynote-strategy",
        choices=["auto", "modern", "keynote09"],
        default="keynote09",
        help="Keynote export strategy passed to export_bundle.py.",
    )
    parser.add_argument("--transition", default="fade", help="PPTX transition effect. Use none to disable.")
    parser.add_argument("--animation", default="none", help="PPTX element animation mode.")
    parser.add_argument("--workers", type=int, default=0, help="SVG-to-PPTX worker count. 0 lets the converter decide.")
    parser.add_argument("--no-auto-downsample-images", action="store_true", help="Disable finalize-time image downsampling based on SVG display size.")
    parser.add_argument("--downsample-scale", type=float, default=2.5, help="Image downsample multiplier over visible SVG display size.")
    parser.add_argument("--downsample-min-dimension", type=int, default=960, help="Minimum long edge for finalize-time image downsampling.")
    parser.add_argument(
        "--require-real-imagegen",
        action="store_true",
        help="Fail project_check when AI images still use procedural-preview-fallback.",
    )
    parser.add_argument("--benchmark-min-score", type=int, default=70, help="Minimum deck quality benchmark score.")
    parser.add_argument("--repair-ready-score", type=int, default=85, help="Score expected before the repair plan treats a deck as ppt-master-ready.")
    parser.add_argument(
        "--enforce-quality-benchmark",
        action="store_true",
        help="Fail production when deck_quality_benchmark.py scores below --benchmark-min-score.",
    )
    parser.add_argument(
        "--fail-on-critical-repairs",
        action="store_true",
        help="Fail production when deck_repair_plan.py generates critical repair actions.",
    )
    args = parser.parse_args()

    project = args.project.resolve()
    if not project.exists():
        raise SystemExit(f"Project directory does not exist: {project}")
    if not (project / "slide_plan.json").exists():
        raise SystemExit(f"slide_plan.json missing: {project / 'slide_plan.json'}")

    requested_formats = parse_formats(args.formats)
    auto_keynote_added = False
    if (
        args.quality_profile in {"professional", "final"}
        and not args.no_auto_keynote
        and "keynote" not in requested_formats
        and can_attempt_keynote_export()
    ):
        requested_formats.append("keynote")
        auto_keynote_added = True
    policy = quality_policy(args.quality_profile, args)
    policy["auto_keynote_added"] = auto_keynote_added
    policy["auto_keynote_reason"] = (
        "macOS Keynote automation detected; added keynote to professional/final formats"
        if auto_keynote_added
        else "not added"
    )
    slug = slugify(args.slug or project.name)
    title = load_title(project, args.title)
    slides = load_slides(project)
    reports = project / "reports"
    exports = project / "exports"
    reports.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SCRIPT_DIR) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    steps: list[dict[str, Any]] = []
    source_adequacy_command = [
        sys.executable,
        SCRIPT_DIR / "source_adequacy.py",
        project,
        "--slides",
        str(len(slides)),
        "--output",
        reports / "source_adequacy.json",
        "--markdown",
        reports / "source_adequacy.md",
    ]
    if args.quality_profile in {"professional", "final"}:
        source_adequacy_command.append("--strict")
    steps.append(
        run_step(
            "source_adequacy",
            source_adequacy_command,
            cwd=project,
            required=args.quality_profile in {"professional", "final"},
            timeout=120,
            env=env,
        )
    )
    if steps[-1].get("required", True) and steps[-1].get("status") != "passed":
        source_failures, source_warnings = report_lists(reports / "source_adequacy.json")
        manifest = {
            "schema_version": "1.0.0",
            "tool": "qiaomu-ppt/scripts/produce_deck.py",
            "generated_at": utc_now(),
            "project": str(project),
            "slug": slug,
            "title": title,
            "requested_formats": requested_formats,
            "ok": False,
            "quality_policy": policy,
            "exit_policy": {
                "allow_missing_formats": args.allow_missing_formats,
                "missing_requested_formats_affect_ok": not args.allow_missing_formats,
                "early_exit": "source_adequacy",
            },
            "steps": steps,
            "export_formats": {},
            "artifacts": collect_artifacts(project, slug),
            "failures": source_failures or [steps[-1].get("reason") or "source_adequacy failed"],
            "warnings": source_warnings or steps[-1].get("warnings", []),
            "external_skill_dependency": "none",
        }
        write_json(project / "production_manifest.json", manifest)
        write_text(project / "production_report.md", render_report(manifest))
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 2

    upstream_required = args.quality_profile in {"professional", "final"}
    upstream_min_score = 82 if args.quality_profile == "final" else 75 if args.quality_profile == "professional" else 65
    upstream_audits = [
        (
            "content_outline_audit",
            "content_outline_audit.py",
            reports / "content_outline_audit.json",
            reports / "content_outline_audit.md",
        ),
        (
            "element_plan_audit",
            "element_plan_audit.py",
            reports / "element_plan_audit.json",
            reports / "element_plan_audit.md",
        ),
        (
            "style_fit_audit",
            "style_fit_audit.py",
            reports / "style_fit_audit.json",
            reports / "style_fit_audit.md",
        ),
    ]
    for step_name, script_name, output_path, markdown_path in upstream_audits:
        audit_command = [
            sys.executable,
            SCRIPT_DIR / script_name,
            project,
            "--output",
            output_path,
            "--markdown",
            markdown_path,
            "--min-score",
            str(upstream_min_score),
        ]
        if upstream_required:
            audit_command.append("--enforce")
        steps.append(
            run_step(
                step_name,
                audit_command,
                cwd=project,
                required=upstream_required,
                timeout=120,
                env=env,
            )
        )

    failed_upstream = [step for step in steps[-len(upstream_audits):] if step.get("required", True) and step.get("status") != "passed"]
    if failed_upstream:
        failures: list[str] = []
        warnings: list[str] = []
        for step_name, _script_name, output_path, _markdown_path in upstream_audits:
            step_failures, step_warnings = report_lists(output_path)
            failures.extend(f"{step_name}: {item}" for item in step_failures)
            warnings.extend(f"{step_name}: {item}" for item in step_warnings)
        if not failures:
            failures = [step.get("reason") or f"{step.get('name')} failed" for step in failed_upstream]
        manifest = {
            "schema_version": "1.0.0",
            "tool": "qiaomu-ppt/scripts/produce_deck.py",
            "generated_at": utc_now(),
            "project": str(project),
            "slug": slug,
            "title": title,
            "requested_formats": requested_formats,
            "ok": False,
            "quality_policy": policy,
            "exit_policy": {
                "allow_missing_formats": args.allow_missing_formats,
                "missing_requested_formats_affect_ok": not args.allow_missing_formats,
                "early_exit": "upstream_quality_audit",
            },
            "steps": steps,
            "export_formats": {},
            "artifacts": collect_artifacts(project, slug),
            "failures": failures,
            "warnings": warnings,
            "external_skill_dependency": "none",
        }
        write_json(project / "production_manifest.json", manifest)
        write_text(project / "production_report.md", render_report(manifest))
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 2
    visual_manifest = project / "visual_asset_manifest.json"
    image_readiness_needed = args.quality_profile in {"professional", "final"} or args.generate_images
    if image_readiness_needed and visual_manifest.exists():
        image_art_preflight_command = [
            sys.executable,
            SCRIPT_DIR / "image_art_direction.py",
            project,
            "--manifest",
            visual_manifest,
            "--slide-plan",
            project / "slide_plan.json",
            "--subject",
            title,
            "--provider",
            "gpt-image-2",
            "--model",
            "gpt-image-2",
            "--update-prompts",
        ]
        steps.append(
            run_step(
                "image_art_direction_preflight",
                image_art_preflight_command,
                cwd=project,
                required=False,
                timeout=120,
                env=env,
            )
        )
        steps.append(
            run_step(
                "image_generation_stage_preflight",
                [
                    sys.executable,
                    SCRIPT_DIR / "stage_image_generation.py",
                    project,
                    "--force",
                    "--only-missing",
                ],
                cwd=project,
                required=False,
                timeout=120,
                env=env,
            )
        )
        steps.append(
            run_step(
                "built_in_image_generation_guide",
                [
                    sys.executable,
                    SCRIPT_DIR / "built_in_image_generation_guide.py",
                    project,
                    "--only-missing",
                ],
                cwd=project,
                required=False,
                timeout=120,
                env=env,
            )
        )

    readiness_command = [
        sys.executable,
        SCRIPT_DIR / "image_generation_readiness.py",
        project,
        "--provider",
        args.image_provider,
        "--provider-config",
        args.image_provider_config,
        "--output",
        reports / "image_generation_readiness.json",
        "--markdown",
        reports / "image_generation_readiness.md",
    ]
    if args.image_api_key_env:
        readiness_command.extend(["--api-key-env", args.image_api_key_env])
    if args.generate_images:
        readiness_command.append("--strict")
    if image_readiness_needed:
        steps.append(run_step("image_generation_readiness", readiness_command, cwd=project, required=False, timeout=120, env=env))
    steps.append(
        quality_profile_preflight(
            project,
            args.quality_profile,
            requested_formats,
            generate_images=args.generate_images,
            no_html_screenshots=args.no_html_screenshots,
        )
    )
    if steps[-1].get("required", True) and steps[-1].get("status") != "passed":
        manifest = {
            "schema_version": "1.0.0",
            "tool": "qiaomu-ppt/scripts/produce_deck.py",
            "generated_at": utc_now(),
            "project": str(project),
            "slug": slug,
            "title": title,
            "requested_formats": requested_formats,
            "ok": False,
            "quality_policy": policy,
            "exit_policy": {
                "allow_missing_formats": args.allow_missing_formats,
                "missing_requested_formats_affect_ok": not args.allow_missing_formats,
                "early_exit": "quality_profile_preflight",
            },
            "steps": steps,
            "export_formats": {},
            "artifacts": collect_artifacts(project, slug),
            "failures": [steps[-1].get("reason") or "quality_profile_preflight failed"],
            "warnings": steps[-1].get("warnings", []),
            "external_skill_dependency": "none",
        }
        write_json(project / "production_manifest.json", manifest)
        write_text(project / "production_report.md", render_report(manifest))
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 2

    if args.auto_apply_repairs:
        repair_apply_command = [
            sys.executable,
            SCRIPT_DIR / "deck_repair_apply.py",
            project,
            "--output",
            project / "reports" / "deck_repair_apply_report.json",
            "--markdown",
            project / "reports" / "deck_repair_apply_report.md",
        ]
        if args.apply_source_ids:
            repair_apply_command.append("--apply-source-ids")
        steps.append(run_step("deck_repair_apply", repair_apply_command, cwd=project, timeout=120, env=env))
    else:
        steps.append(skip_step("deck_repair_apply", "safe contract repair preflight not requested", required=False))

    visual_manifest = project / "visual_asset_manifest.json"
    if visual_manifest.exists():
        steps.append(
            run_step(
                "image_art_direction",
                [
                    sys.executable,
                    SCRIPT_DIR / "image_art_direction.py",
                    project,
                    "--manifest",
                    visual_manifest,
                    "--slide-plan",
                    project / "slide_plan.json",
                    "--subject",
                    title,
                    "--provider",
                    "gpt-image-2",
                    "--model",
                    "gpt-image-2",
                    "--update-prompts",
                ],
                cwd=project,
                timeout=120,
                env=env,
            )
        )
    else:
        steps.append(skip_step("image_art_direction", "visual_asset_manifest.json not found"))

    if args.generate_images:
        image_command = [
            sys.executable,
            SCRIPT_DIR / "run_image_generation.py",
            project,
            "--provider",
            args.image_provider,
            "--provider-config",
            args.image_provider_config,
            "--stage",
            "--only-missing",
            "--execute",
            "--import-results",
            "--quality",
            args.image_quality,
        ]
        if args.image_model:
            image_command.extend(["--model", args.image_model])
        if args.image_api_key_env:
            image_command.extend(["--api-key-env", args.image_api_key_env])
        if args.image_limit > 0:
            image_command.extend(["--limit", str(args.image_limit)])
        if args.image_size:
            image_command.extend(["--size", args.image_size])
        if args.image_base_url:
            image_command.extend(["--base-url", args.image_base_url])
        if args.image_request_format:
            image_command.extend(["--request-format", args.image_request_format])
        if args.image_auth_scheme:
            image_command.extend(["--auth-scheme", args.image_auth_scheme])
        if args.image_endpoint_path:
            image_command.extend(["--endpoint-path", args.image_endpoint_path])
        if args.image_submit_path:
            image_command.extend(["--submit-path", args.image_submit_path])
        if args.image_status_path_template:
            image_command.extend(["--status-path-template", args.image_status_path_template])
        if args.image_poll_interval > 0:
            image_command.extend(["--poll-interval", str(args.image_poll_interval)])
        if args.image_poll_timeout > 0:
            image_command.extend(["--poll-timeout", str(args.image_poll_timeout)])
        preflight_command = [
            part
            for part in image_command
            if str(part) not in {"--execute", "--import-results"}
        ]
        preflight_command.append("--preflight")
        steps.append(run_step("image_generation_preflight", preflight_command, cwd=project, timeout=120, env=env))
        steps.append(run_step("image_generation", image_command, cwd=project, timeout=args.timeout, env=env))
    else:
        steps.append(skip_step("image_generation", "real image generation not requested", required=False))

    if args.materialize_assets:
        if args.generate_images:
            steps.append(skip_step("visual_asset_materialize", "--generate-images was requested; procedural fallback materialization skipped", required=False))
        else:
            command = [sys.executable, SCRIPT_DIR / "materialize_visual_assets.py", project]
            if args.force:
                command.append("--force")
            steps.append(run_step("visual_asset_materialize", command, cwd=project, required=False, timeout=args.timeout, env=env))

    if visual_manifest.exists():
        steps.append(
            run_step(
                "visual_asset_manifest_validate",
                [
                    sys.executable,
                    SCRIPT_DIR / "visual_asset_manifest.py",
                    "validate",
                    "--manifest",
                    visual_manifest,
                    "--project",
                    project,
                    "--require-terminal",
                ],
                cwd=project,
                timeout=120,
                env=env,
            )
        )
    else:
        steps.append(skip_step("visual_asset_manifest_validate", "visual_asset_manifest.json not found"))

    svg_output = project / "svg_output"
    command = [sys.executable, SCRIPT_DIR / "svg_deck_from_slide_plan.py", project]
    command.append("--force")
    steps.append(run_step("svg_generate", command, cwd=project, timeout=args.timeout, env=env))

    if svg_output.exists():
        steps.append(
            run_step(
                "svg_quality",
                [
                    sys.executable,
                    SCRIPT_DIR / "svg_quality_checker.py",
                    svg_output,
                    "--export",
                    "--output",
                    reports / "svg_quality_report.txt",
                ],
                cwd=project,
                timeout=180,
                env=env,
            )
        )
        steps.append(
            run_step(
                "visual_rhythm_check",
                [
                    sys.executable,
                    SCRIPT_DIR / "visual_rhythm_check.py",
                    project,
                    "--source",
                    "svg_output",
                    "--output",
                    reports / "visual_rhythm_report.json",
                ],
                cwd=project,
                timeout=120,
                env=env,
            )
        )
        style_audit_command = [
            sys.executable,
            SCRIPT_DIR / "style_execution_audit.py",
            project,
            "--output",
            reports / "style_execution_audit.json",
            "--markdown",
            reports / "style_execution_audit.md",
            "--min-score",
            str(75 if args.quality_profile in {"professional", "final"} else 60),
        ]
        if args.quality_profile in {"professional", "final"}:
            style_audit_command.append("--enforce")
        steps.append(
            run_step(
                "style_execution_audit",
                style_audit_command,
                cwd=project,
                required=args.quality_profile in {"professional", "final"},
                timeout=120,
                env=env,
            )
        )
        steps.append(
            run_step(
                "svg_preview",
                [sys.executable, SCRIPT_DIR / "svg_preview.py", project, "--source", "svg_output"],
                cwd=project,
                timeout=args.timeout,
                env=env,
            )
        )
    else:
        steps.append(skip_step("svg_quality", "svg_output directory missing"))
        steps.append(skip_step("visual_rhythm_check", "svg_output directory missing"))
        steps.append(skip_step("style_execution_audit", "svg_output directory missing"))
        steps.append(skip_step("svg_preview", "svg_output directory missing"))

    steps.append(
        upsert_preview_gate(
            project,
            len(slides),
            decision=args.preview_decision,
            approval_note=args.preview_note,
        )
    )

    finalize_command = [
        sys.executable,
        SCRIPT_DIR / "finalize_svg.py",
        project,
        "--quiet",
        "--downsample-scale",
        str(args.downsample_scale),
        "--downsample-min-dimension",
        str(args.downsample_min_dimension),
    ]
    if args.no_auto_downsample_images:
        finalize_command.append("--no-auto-downsample-images")
    steps.append(run_step("svg_finalize", finalize_command, cwd=project, timeout=args.timeout, env=env))

    pptx_path = exports / f"{slug}.pptx"
    pptx_command = [
        sys.executable,
        SCRIPT_DIR / "svg_to_pptx.py",
        project,
        "-s",
        args.svg_source,
        "--no-compat",
        "-o",
        pptx_path,
        "--conversion-trace",
        "-t",
        args.transition,
        "-a",
        args.animation,
    ]
    if args.workers > 0:
        pptx_command.extend(["--workers", str(args.workers)])
    steps.append(run_step("pptx_export", pptx_command, cwd=project, timeout=args.timeout, env=env))

    if pptx_path.exists():
        steps.append(
            run_step(
                "pptx_text_check",
                [
                    sys.executable,
                    SCRIPT_DIR / "pptx_text_check.py",
                    pptx_path,
                    "--slide-plan",
                    project / "slide_plan.json",
                    "--output",
                    project / "pptx_text_check.json",
                ],
                cwd=project,
                timeout=180,
                env=env,
            )
        )
    else:
        steps.append(skip_step("pptx_text_check", f"PPTX not found: {pptx_path}"))

    export_command = [
        sys.executable,
        SCRIPT_DIR / "export_bundle.py",
        project,
        "--pptx",
        pptx_path,
        "--slug",
        slug,
        "--title",
        title,
        "--formats",
        ",".join(requested_formats),
        "--svg-source",
        args.svg_source,
        "--keynote-timeout",
        str(args.keynote_timeout),
        "--keynote-strategy",
        args.keynote_strategy,
    ]
    if args.no_html_screenshots:
        export_command.append("--no-html-screenshots")
    steps.append(run_step("export_bundle", export_command, cwd=project, timeout=max(args.timeout, args.keynote_timeout + 60), env=env))

    steps.append(
        run_step(
            "project_check",
            [
                sys.executable,
                SCRIPT_DIR / "check_project.py",
                project,
                "--output",
                project / "project_check.json",
                *(["--require-real-imagegen"] if policy["require_real_imagegen"] else []),
            ],
            cwd=project,
            timeout=180,
            env=env,
        )
    )
    benchmark_command = [
        sys.executable,
        SCRIPT_DIR / "deck_quality_benchmark.py",
        project,
        "--output",
        project / "reports" / "deck_quality_benchmark.json",
        "--markdown",
        project / "reports" / "deck_quality_benchmark.md",
        "--min-score",
        str(policy["benchmark_min_score"]),
    ]
    if policy["enforce_quality_benchmark"]:
        benchmark_command.append("--enforce")
    steps.append(
        run_step(
            "deck_quality_benchmark",
            benchmark_command,
            cwd=project,
            required=policy["enforce_quality_benchmark"],
            timeout=120,
            env=env,
        )
    )
    repair_command = [
        sys.executable,
        SCRIPT_DIR / "deck_repair_plan.py",
        project,
        "--benchmark",
        project / "reports" / "deck_quality_benchmark.json",
        "--output",
        project / "reports" / "deck_repair_plan.json",
        "--markdown",
        project / "reports" / "deck_repair_plan.md",
        "--min-score",
        str(policy["benchmark_min_score"]),
        "--ready-score",
        str(policy["repair_ready_score"]),
    ]
    if policy["fail_on_critical_repairs"]:
        repair_command.append("--fail-on-critical")
    steps.append(
        run_step(
            "deck_repair_plan",
            repair_command,
            cwd=project,
            required=policy["fail_on_critical_repairs"],
            timeout=120,
            env=env,
        )
    )
    steps.append(
        run_step(
            "page_content_guide",
            [
                sys.executable,
                SCRIPT_DIR / "page_content_guide.py",
                project,
                "--output",
                project / "page_content_guide.json",
                "--markdown",
                project / "page_content_guide.md",
            ],
            cwd=project,
            timeout=120,
            env=env,
        )
    )
    export_formats, format_failures = summarize_export_formats(project, requested_formats)
    step_failures = [
        f"{step['name']}: {step.get('reason') or 'returncode ' + str(step.get('returncode'))}"
        for step in steps
        if step.get("required", True) and step.get("status") not in {"passed"}
    ]
    critical_failed = [
        step
        for step in steps
        if step.get("name") in CRITICAL_STEPS
        and step.get("required", True)
        and step.get("status") != "passed"
    ]
    requested_format_failed = bool(format_failures)
    ok = not critical_failed and (not requested_format_failed or args.allow_missing_formats)
    warnings = []
    if requested_format_failed and args.allow_missing_formats:
        warnings.extend([f"allowed missing/failed requested format: {failure}" for failure in format_failures])

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/produce_deck.py",
        "generated_at": utc_now(),
        "project": str(project),
        "slug": slug,
        "title": title,
        "requested_formats": requested_formats,
        "ok": ok,
        "quality_policy": policy,
        "exit_policy": {
            "allow_missing_formats": args.allow_missing_formats,
            "missing_requested_formats_affect_ok": not args.allow_missing_formats,
        },
        "steps": steps,
        "export_formats": export_formats,
        "artifacts": collect_artifacts(project, slug),
        "failures": step_failures + ([] if args.allow_missing_formats else format_failures),
        "warnings": warnings,
        "external_skill_dependency": "none",
    }
    write_json(project / "production_manifest.json", manifest)
    write_text(project / "production_report.md", render_report(manifest))
    manifest["artifacts"] = collect_artifacts(project, slug)
    write_json(project / "production_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
