#!/usr/bin/env python3
"""Run the formal qiaomu-ppt deck production pipeline."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from production_support import (
    DEFAULT_FORMATS,
    as_list,
    can_attempt_keynote_export,
    collect_artifacts,
    critical_step_failures,
    parse_formats,
    quality_policy,
    render_report,
    required_step_failures,
    summarize_export_formats,
)

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


def resolve_image_limit(args: argparse.Namespace) -> int:
    if args.image_limit is not None:
        return max(0, args.image_limit)
    if args.quality_profile == "draft":
        return max(0, args.draft_image_limit)
    return 0


def is_unresolved_source_ai_fallback(item: dict[str, Any]) -> bool:
    asset_id = str(item.get("asset_id") or "").lower()
    notes = str(item.get("notes") or "").lower()
    return asset_id.endswith("-ai-fallback") or (
        "ai fallback for preview/production while the remote source image remains" in notes
    )


def is_codex_runtime() -> bool:
    return any(os.environ.get(name) for name in ("CODEX_THREAD_ID", "CODEX_SHELL", "CODEX_CI"))


def is_codex_native_image_asset(item: dict[str, Any]) -> bool:
    blob = " ".join(
        str(item.get(key) or "")
        for key in (
            "asset_id",
            "filename",
            "path",
            "source",
            "source_path",
            "generated_asset_source",
            "original_source",
            "generator",
            "provider",
            "notes",
            "generation_note",
            "rights_notes",
        )
    ).lower()
    return any(
        token in blob
        for token in (
            "codex-native",
            "codex-imagegen",
            "codex_imagegen",
            "codex image_gen",
            "image_gen",
            ".codex/generated_images",
            "/.codex/generated_images/",
        )
    )


def analyze_ai_asset_readiness(project: Path) -> dict[str, Any]:
    manifest_path = project / "visual_asset_manifest.json"
    evidence: dict[str, Any] = {
        "visual_asset_manifest": rel(project, manifest_path),
        "ai_count": 0,
        "procedural_fallback_count": 0,
        "non_terminal_ai_count": 0,
        "real_imagegen_count": 0,
        "codex_native_imagegen_count": 0,
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
            if is_codex_native_image_asset(item):
                evidence["codex_native_imagegen_count"] += 1
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
        "trusted_source_web_user_count": 0,
        "local_source_derived_count": 0,
        "missing_file_count": 0,
        "examples": [],
        "missing_file_examples": [],
        "local_source_derived_examples": [],
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
            if is_trusted_source_visual(item):
                evidence["trusted_source_web_user_count"] += 1
            else:
                evidence["local_source_derived_count"] += 1
                if len(evidence["local_source_derived_examples"]) < 5:
                    evidence["local_source_derived_examples"].append(label)
            continue
        evidence["unresolved_source_count"] += 1
        if len(evidence["examples"]) < 5:
            evidence["examples"].append(label)
        if raw_path and not file_exists:
            evidence["missing_file_count"] += 1
            if len(evidence["missing_file_examples"]) < 5:
                evidence["missing_file_examples"].append(label)
    return evidence


def is_local_source_derived_visual(item: dict[str, Any]) -> bool:
    blob = " ".join(
        str(item.get(key) or "")
        for key in (
            "asset_id",
            "filename",
            "path",
            "purpose",
            "asset_role",
            "rights_notes",
            "generator",
            "art_direction",
        )
    ).lower()
    return any(
        token in blob
        for token in (
            "source-derived",
            "local-source-derived",
            "源资料衍生",
            "本地衍生",
            "该 png 只提供源资料衍生",
        )
    )


def is_trusted_source_visual(item: dict[str, Any]) -> bool:
    via = str(item.get("acquire_via") or "").lower()
    if is_local_source_derived_visual(item):
        return False
    if via == "user":
        return True
    if via == "web":
        return bool(item.get("source_page_url") or item.get("source_url") or item.get("url"))
    if via == "source":
        raw_path = str(item.get("path") or "")
        has_source_file = raw_path.startswith("sources/")
        return bool(
            has_source_file
            or item.get("source_path")
            or item.get("source_page_url")
            or item.get("source_image_id")
            or item.get("source_page")
            or item.get("source_url")
        )
    return False


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
        key_ai_floor = max(3, round(slide_count * 0.2)) if slide_count > 8 else (1 if slide_count >= 4 else 0)
        real_ai_count = int(ai_evidence.get("real_imagegen_count") or 0)
        planned_ai_count = int(ai_evidence.get("ai_count") or 0)
        has_key_ai_path = real_ai_count >= key_ai_floor or (generate_images and planned_ai_count >= key_ai_floor)
        evidence["key_real_imagegen_target"] = key_ai_floor
        codex_runtime = is_codex_runtime()
        codex_ai_count = int(ai_evidence.get("codex_native_imagegen_count") or 0)
        evidence["codex_runtime"] = codex_runtime
        evidence["codex_native_imagegen_target"] = key_ai_floor if codex_runtime else 0
        trusted_source_visual_count = int(source_visual_evidence.get("trusted_source_web_user_count") or 0)
        source_visual_ready = trusted_source_visual_count >= source_visual_floor
        if slide_count > 8 and not has_key_ai_path:
            message = (
                f"{profile} profile needs real generated images on key pages: target {key_ai_floor}, "
                f"currently {real_ai_count} real generated asset(s) and {planned_ai_count} AI asset row(s). "
                "Downloaded/source images can be used as evidence, but they do not replace key-page generation. "
                "Add AI rows for cover/opening, major proof/framework pages, and closing, then run --generate-images; "
                "or downgrade to --quality-profile draft."
            )
            if profile == "final":
                failures.append(message)
            else:
                warnings.append(message)
        if codex_runtime and key_ai_floor and codex_ai_count < key_ai_floor:
            message = (
                f"{profile} profile is running in Codex and requires Codex-native image_gen assets on key pages: "
                f"{codex_ai_count}/{key_ai_floor}. Use the Codex image generation tool, copy the generated files "
                "from ~/.codex/generated_images into project assets, and record each row with acquire_via=ai, "
                "status=Generated, generator=codex-native-image_gen, plus generated_asset_source. "
                "Content-only slides, external-provider-only images, source-derived graphics, SVG, or shapes are failure "
                "for final/professional production unless the user explicitly downgrades the run to draft/no generation."
            )
            if profile == "final":
                failures.append(message)
            else:
                warnings.append(message)
        if slide_count > 8 and not has_key_ai_path and not source_visual_ready:
            message = (
                f"{profile} profile also has only {trusted_source_visual_count} trusted source/web/user visual(s) "
                f"({source_visual_evidence.get('local_source_derived_count', 0)} local source-derived visual(s) do not count as source evidence); "
                f"target at least {source_visual_floor} trusted source visuals when source evidence is part of the deck."
            )
            if profile == "final":
                failures.append(message)
            else:
                warnings.append(message)
        if slide_count > 8 and not generate_images and real_ai_count < key_ai_floor:
            failures.append(
                f"{profile} profile was run with --no-generate-images but has only "
                f"{real_ai_count}/{key_ai_floor} real generated key-page image(s). "
                "This is a draft/offline path, not a final-production path."
            )
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


def artifact_mtime(path: Path) -> float:
    if path.is_dir():
        newest = path.stat().st_mtime
        for child in path.rglob("*"):
            try:
                newest = max(newest, child.stat().st_mtime)
            except OSError:
                continue
        return newest
    return path.stat().st_mtime


def existing_paths(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def newest_mtime(paths: list[Path]) -> float:
    existing = existing_paths(paths)
    if not existing:
        return 0.0
    return max(artifact_mtime(path) for path in existing)


def outputs_fresh(outputs: list[Path], inputs: list[Path]) -> bool:
    if not outputs or any(not output.exists() for output in outputs):
        return False
    input_mtime = newest_mtime(inputs)
    try:
        return min(artifact_mtime(output) for output in outputs) >= input_mtime
    except OSError:
        return False


def directory_fresh(directory: Path, inputs: list[Path], *, pattern: str, min_count: int) -> bool:
    if not directory.is_dir():
        return False
    outputs = sorted(directory.glob(pattern))
    if len(outputs) < min_count:
        return False
    return outputs_fresh(outputs, inputs)


def files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return [child for child in path.rglob("*") if child.is_file()]


def terminal_asset_paths(project: Path) -> list[Path]:
    manifest = project / "visual_asset_manifest.json"
    if not manifest.exists():
        return []
    try:
        payload = read_json(manifest)
    except Exception:
        return []
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []
    terminal = {"Generated", "Sourced", "Existing", "Rendered"}
    paths: list[Path] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") not in terminal:
            continue
        raw_path = str(item.get("path") or "").strip()
        if not raw_path:
            continue
        path = Path(raw_path)
        paths.append(path if path.is_absolute() else project / path)
    return existing_paths(paths)


def svg_generation_inputs(project: Path) -> list[Path]:
    candidates = [
        project / "slide_plan.json",
        project / "content_contract.json",
        project / "style_direction.json",
        project / "style_brief.md",
        project / "visual_contract.json",
        project / "visual_asset_manifest.json",
        project / "image_art_direction.json",
        project / "assets" / "images" / "image_sources.json",
        project / "assets" / "images" / "image_prompts.json",
        project / "assets" / "images" / "image_generation_queue.json",
        SCRIPT_DIR / "svg_deck_from_slide_plan.py",
    ]
    return existing_paths(candidates) + terminal_asset_paths(project)


def report_ok(path: Path, *, min_score: int | None = None, allow_non_json: bool = False) -> bool:
    if allow_non_json and path.exists():
        return True
    try:
        payload = read_json(path)
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    if "ok" in payload and not bool(payload.get("ok")):
        return False
    if min_score is not None:
        try:
            if float(payload.get("score", 0)) < min_score:
                return False
        except (TypeError, ValueError):
            return False
    return True


def cached_step(
    name: str,
    reason: str,
    *,
    command: list[str] | None = None,
    required: bool = True,
    outputs: list[Path] | None = None,
    project: Path | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "required": required,
        "command": command_to_string(command or []),
        "status": "passed",
        "cache": "reused",
        "reason": reason,
        "started_at": utc_now(),
        "duration_seconds": 0,
    }
    if outputs and project:
        payload["outputs"] = [rel(project, path) for path in outputs if path.exists()]
    return payload


def cached_report_step(
    name: str,
    output: Path,
    inputs: list[Path],
    *,
    command: list[str],
    project: Path,
    required: bool = True,
    markdown: Path | None = None,
    min_score: int | None = None,
    allow_non_json: bool = False,
) -> dict[str, Any] | None:
    outputs = [output] + ([markdown] if markdown else [])
    if outputs_fresh(outputs, inputs) and report_ok(output, min_score=min_score, allow_non_json=allow_non_json):
        return cached_step(
            name,
            f"{rel(project, output)} is fresh for unchanged inputs",
            command=command,
            required=required,
            outputs=outputs,
            project=project,
        )
    return None


def previous_step_passed(project: Path, name: str, command: list[str]) -> bool:
    manifest = project / "production_manifest.json"
    if not manifest.exists():
        return False
    try:
        payload = read_json(manifest)
    except Exception:
        return False
    steps = payload.get("steps") if isinstance(payload, dict) else []
    if not isinstance(steps, list):
        return False
    command_text = command_to_string(command)
    for step in reversed(steps):
        if not isinstance(step, dict):
            continue
        if step.get("name") == name and step.get("status") == "passed" and step.get("command") == command_text:
            return True
    return False


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
        help="Disable real image generation; use only for explicit offline/text-structure smoke tests.",
    )
    parser.add_argument("--image-provider", default="openai", help="Image generation provider for --generate-images. Default: openai.")
    parser.add_argument("--image-model", default="", help="Image generation model for --generate-images. Defaults to the provider preset.")
    parser.add_argument("--image-limit", type=int, default=None, help="Maximum real images to generate. Use 0 for all queued items. Defaults to --draft-image-limit for draft and all for professional/final.")
    parser.add_argument("--draft-image-limit", type=int, default=4, help="Default real image count for --quality-profile draft when --image-limit is omitted.")
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
    effective_image_limit = resolve_image_limit(args)
    policy = quality_policy(args.quality_profile, args)
    policy["effective_image_limit"] = effective_image_limit
    policy["image_limit_reason"] = (
        "draft profile defaults to a small real-image set for visual review"
        if args.image_limit is None and args.quality_profile == "draft"
        else "explicit --image-limit" if args.image_limit is not None else "generate all queued images"
    )
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
    source_adequacy_inputs = existing_paths(
        [
            project / "slide_plan.json",
            project / "sources" / "source_manifest.json",
            project / "sources" / "source_cards.json",
            project / "visual_asset_manifest.json",
            project / "style_direction.json",
            SCRIPT_DIR / "source_adequacy.py",
        ]
    )
    cached = None if args.force else cached_report_step(
        "source_adequacy",
        reports / "source_adequacy.json",
        source_adequacy_inputs,
        command=source_adequacy_command,
        project=project,
        required=args.quality_profile in {"professional", "final"},
        markdown=reports / "source_adequacy.md",
    )
    steps.append(
        cached
        or run_step(
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
        (
            "ppt_master_axis_audit",
            "ppt_master_axis_audit.py",
            reports / "ppt_master_axis_audit.json",
            reports / "ppt_master_axis_audit.md",
        ),
    ]
    upstream_inputs = existing_paths(
        [
            project / "slide_plan.json",
            project / "content_contract.json",
            project / "sources" / "source_cards.json",
            project / "sources" / "source_manifest.json",
            project / "visual_asset_manifest.json",
            project / "style_direction.json",
            project / "visual_contract.json",
            project / "spec_lock.json",
        ]
    ) + terminal_asset_paths(project)
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
        audit_inputs = upstream_inputs + [SCRIPT_DIR / script_name]
        cached = None if args.force else cached_report_step(
            step_name,
            output_path,
            audit_inputs,
            command=audit_command,
            project=project,
            required=upstream_required,
            markdown=markdown_path,
            min_score=upstream_min_score,
        )
        steps.append(
            cached
            or run_step(
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
        if effective_image_limit > 0:
            image_command.extend(["--limit", str(effective_image_limit)])
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
    svg_inputs = svg_generation_inputs(project)
    if not args.force and directory_fresh(svg_output, svg_inputs, pattern="*.svg", min_count=max(1, len(slides))):
        steps.append(
            cached_step(
                "svg_generate",
                "svg_output is fresh for unchanged slide/style/asset inputs",
                command=command,
                outputs=sorted(svg_output.glob("*.svg")),
                project=project,
            )
        )
    else:
        if args.force or svg_output.exists():
            command.append("--force")
        steps.append(run_step("svg_generate", command, cwd=project, timeout=args.timeout, env=env))

    if svg_output.exists():
        svg_files = sorted(svg_output.glob("*.svg"))
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
        rhythm_command = [
            sys.executable,
            SCRIPT_DIR / "visual_rhythm_check.py",
            project,
            "--source",
            "svg_output",
            "--output",
            reports / "visual_rhythm_report.json",
        ]
        cached = None if args.force else cached_report_step(
            "visual_rhythm_check",
            reports / "visual_rhythm_report.json",
            svg_files + [SCRIPT_DIR / "visual_rhythm_check.py"],
            command=rhythm_command,
            project=project,
        )
        steps.append(
            cached
            or run_step(
                "visual_rhythm_check",
                rhythm_command,
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
        style_audit_inputs = svg_files + existing_paths(
            [
                reports / "visual_rhythm_report.json",
                project / "style_direction.json",
                project / "visual_asset_manifest.json",
                project / "slide_plan.json",
                SCRIPT_DIR / "style_execution_audit.py",
            ]
        )
        cached = None if args.force else cached_report_step(
            "style_execution_audit",
            reports / "style_execution_audit.json",
            style_audit_inputs,
            command=style_audit_command,
            project=project,
            required=args.quality_profile in {"professional", "final"},
            markdown=reports / "style_execution_audit.md",
            min_score=75 if args.quality_profile in {"professional", "final"} else 60,
        )
        steps.append(
            cached
            or run_step(
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
    svg_final = project / "svg_final"
    finalize_inputs = sorted(svg_output.glob("*.svg")) + [SCRIPT_DIR / "finalize_svg.py"] + files_under(SCRIPT_DIR / "svg_finalize")
    if (
        not args.force
        and directory_fresh(svg_final, finalize_inputs, pattern="*.svg", min_count=max(1, len(slides)))
        and previous_step_passed(project, "svg_finalize", finalize_command)
    ):
        steps.append(
            cached_step(
                "svg_finalize",
                "svg_final is fresh for unchanged svg_output and finalize options",
                command=finalize_command,
                outputs=sorted(svg_final.glob("*.svg")),
                project=project,
            )
        )
    else:
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
    pptx_svg_dir = project / ("svg_final" if args.svg_source == "final" else "svg_output")
    pptx_inputs = sorted(pptx_svg_dir.glob("*.svg")) + [SCRIPT_DIR / "svg_to_pptx.py"] + files_under(SCRIPT_DIR / "svg_to_pptx")
    pptx_trace = exports / f"{slug}.pptx.trace.json"
    if (
        not args.force
        and outputs_fresh([pptx_path, pptx_trace], pptx_inputs)
        and previous_step_passed(project, "pptx_export", pptx_command)
    ):
        steps.append(
            cached_step(
                "pptx_export",
                "PPTX and conversion trace are fresh for unchanged SVG source and export options",
                command=pptx_command,
                outputs=[pptx_path, pptx_trace],
                project=project,
            )
        )
    else:
        steps.append(run_step("pptx_export", pptx_command, cwd=project, timeout=args.timeout, env=env))

    if pptx_path.exists():
        text_check_command = [
            sys.executable,
            SCRIPT_DIR / "pptx_text_check.py",
            pptx_path,
            "--slide-plan",
            project / "slide_plan.json",
            "--output",
            project / "pptx_text_check.json",
        ]
        cached = None if args.force else cached_report_step(
            "pptx_text_check",
            project / "pptx_text_check.json",
            [pptx_path, project / "slide_plan.json", SCRIPT_DIR / "pptx_text_check.py"],
            command=text_check_command,
            project=project,
        )
        steps.append(
            cached
            or run_step(
                "pptx_text_check",
                text_check_command,
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

    project_check_command = [
        sys.executable,
        SCRIPT_DIR / "check_project.py",
        project,
        "--output",
        project / "project_check.json",
        *(["--require-real-imagegen"] if policy["require_real_imagegen"] else []),
    ]
    project_check_inputs = existing_paths(
        [
            project / "slide_plan.json",
            project / "spec_lock.json",
            project / "visual_asset_manifest.json",
            project / "pptx_text_check.json",
            project / "export_manifest.json",
            pptx_path,
            SCRIPT_DIR / "check_project.py",
        ]
    ) + sorted(svg_final.glob("*.svg"))
    cached = None
    if not args.force and previous_step_passed(project, "project_check", project_check_command):
        cached = cached_report_step(
            "project_check",
            project / "project_check.json",
            project_check_inputs,
            command=project_check_command,
            project=project,
        )
    steps.append(
        cached
        or run_step(
            "project_check",
            project_check_command,
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
    run_benchmark = (
        args.quality_profile != "draft"
        or policy["enforce_quality_benchmark"]
        or policy["fail_on_critical_repairs"]
    )
    if run_benchmark:
        benchmark_inputs = project_check_inputs + existing_paths(
            [
                reports / "visual_rhythm_report.json",
                reports / "style_execution_audit.json",
                project / "export_manifest.json",
                SCRIPT_DIR / "deck_quality_benchmark.py",
            ]
        )
        cached = None if args.force else cached_report_step(
            "deck_quality_benchmark",
            project / "reports" / "deck_quality_benchmark.json",
            benchmark_inputs,
            command=benchmark_command,
            project=project,
            required=policy["enforce_quality_benchmark"],
            markdown=project / "reports" / "deck_quality_benchmark.md",
            min_score=policy["benchmark_min_score"],
        )
        steps.append(
            cached
            or run_step(
                "deck_quality_benchmark",
                benchmark_command,
                cwd=project,
                required=policy["enforce_quality_benchmark"],
                timeout=120,
                env=env,
            )
        )
    else:
        steps.append(skip_step("deck_quality_benchmark", "draft profile skips final-quality benchmark by default", required=False))
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
    run_repair_plan = args.quality_profile != "draft" or policy["fail_on_critical_repairs"]
    if run_repair_plan:
        repair_inputs = existing_paths(
            [
                project / "reports" / "deck_quality_benchmark.json",
                project / "reports" / "visual_rhythm_report.json",
                project / "reports" / "style_execution_audit.json",
                project / "export_manifest.json",
                SCRIPT_DIR / "deck_repair_plan.py",
            ]
        )
        cached = None if args.force else cached_report_step(
            "deck_repair_plan",
            project / "reports" / "deck_repair_plan.json",
            repair_inputs,
            command=repair_command,
            project=project,
            required=policy["fail_on_critical_repairs"],
            markdown=project / "reports" / "deck_repair_plan.md",
            allow_non_json=False,
        )
        if cached:
            try:
                repair_payload = read_json(project / "reports" / "deck_repair_plan.json")
                if policy["fail_on_critical_repairs"] and int(repair_payload.get("summary", {}).get("critical_count", 0)) > 0:
                    cached = None
            except Exception:
                cached = None
        steps.append(
            cached
            or run_step(
                "deck_repair_plan",
                repair_command,
                cwd=project,
                required=policy["fail_on_critical_repairs"],
                timeout=120,
                env=env,
            )
        )
    else:
        steps.append(skip_step("deck_repair_plan", "draft profile skips final-quality repair planning by default", required=False))
    page_guide_command = [
        sys.executable,
        SCRIPT_DIR / "page_content_guide.py",
        project,
        "--output",
        project / "page_content_guide.json",
        "--markdown",
        project / "page_content_guide.md",
    ]
    cached = None if args.force else cached_report_step(
        "page_content_guide",
        project / "page_content_guide.json",
        existing_paths(
            [
                project / "slide_plan.json",
                project / "visual_asset_manifest.json",
                project / "reports" / "deck_repair_plan.json",
                SCRIPT_DIR / "page_content_guide.py",
            ]
        ),
        command=page_guide_command,
        project=project,
        markdown=project / "page_content_guide.md",
        allow_non_json=False,
    )
    steps.append(
        cached
        or run_step(
            "page_content_guide",
            page_guide_command,
            cwd=project,
            timeout=120,
            env=env,
        )
    )
    export_formats, format_failures = summarize_export_formats(project, requested_formats)

    step_failures = required_step_failures(steps)
    critical_failed = critical_step_failures(steps)
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

    final_status_command = [
        sys.executable,
        SCRIPT_DIR / "final_status.py",
        project,
        "--output",
        project / "final_status.json",
        "--markdown",
        project / "交付检查.md",
        "--report-only",
    ]
    steps.append(
        run_step(
            "final_status",
            final_status_command,
            cwd=project,
            required=True,
            timeout=60,
            env=env,
        )
    )
    final_status_payload: dict[str, Any] = {}
    final_status_failures: list[str] = []
    if (project / "final_status.json").exists():
        try:
            loaded = read_json(project / "final_status.json")
            if isinstance(loaded, dict):
                final_status_payload = loaded
        except Exception as exc:
            final_status_failures.append(f"cannot read final_status.json: {exc}")
    else:
        final_status_failures.append("final_status.json missing")
    if final_status_payload:
        manifest["final_status"] = {
            "ok": bool(final_status_payload.get("ok")),
            "status": final_status_payload.get("status"),
            "json": "final_status.json",
            "markdown": "交付检查.md",
        }
        if not final_status_payload.get("ok"):
            final_status_failures.extend(as_list(final_status_payload.get("blocking_failures")))
    else:
        manifest["final_status"] = {
            "ok": False,
            "status": "missing",
            "json": "final_status.json",
            "markdown": "交付检查.md",
        }
    step_failures = required_step_failures(steps)
    critical_failed = critical_step_failures(steps)
    ok = (
        not critical_failed
        and (not requested_format_failed or args.allow_missing_formats)
        and bool(final_status_payload.get("ok"))
        and not final_status_failures
    )
    manifest["ok"] = ok
    manifest["steps"] = steps
    manifest["failures"] = step_failures + ([] if args.allow_missing_formats else format_failures) + final_status_failures
    manifest["warnings"] = warnings + as_list(final_status_payload.get("warnings"))
    manifest["artifacts"] = collect_artifacts(project, slug)
    write_json(project / "production_manifest.json", manifest)
    write_text(project / "production_report.md", render_report(manifest))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
