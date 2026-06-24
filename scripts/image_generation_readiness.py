#!/usr/bin/env python3
"""Report real image-generation readiness for a qiaomu-ppt project.

This script is intentionally non-generative. It inspects the project contracts,
provider preset, queue, staging batch, and latest run report, then writes a
human-actionable checklist. Secrets are never printed; only env var names and
presence are reported.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROVIDER_CONFIG = SCRIPT_DIR.parent / "data" / "image_generation_providers.json"


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
    except Exception:
        return str(path)


def load_json_or_none(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception as exc:
        return {"_read_error": str(exc)}


def is_unresolved_source_ai_fallback(item: dict[str, Any]) -> bool:
    asset_id = str(item.get("asset_id") or "").lower()
    notes = str(item.get("notes") or "").lower()
    return asset_id.endswith("-ai-fallback") or (
        "ai fallback for preview/production while the remote source image remains" in notes
    )


def resolve_provider(provider: str, provider_config: Path, api_key_env: str = "") -> dict[str, Any]:
    payload = load_json_or_none(provider_config)
    providers = payload.get("providers", {}) if isinstance(payload, dict) else {}
    preset = dict(providers.get(provider, {})) if isinstance(providers, dict) else {}
    if not preset and provider in {"openai", "gpt-image-2"}:
        preset = {
            "display_name": "OpenAI Images SDK",
            "request_format": "openai-sdk",
            "model": "gpt-image-2",
            "api_key_env": "OPENAI_API_KEY",
            "auth_scheme": "bearer",
        }
    preset.setdefault("display_name", provider)
    preset.setdefault("request_format", "openai-sdk" if provider in {"openai", "gpt-image-2"} else "openai-images-http")
    preset.setdefault("model", "gpt-image-2")
    preset.setdefault("api_key_env", "OPENAI_API_KEY")
    preset.setdefault("auth_scheme", "bearer")
    if api_key_env:
        preset["api_key_env"] = api_key_env
    return preset


def summarize_visual_manifest(project: Path) -> dict[str, Any]:
    path = project / "visual_asset_manifest.json"
    result: dict[str, Any] = {
        "path": rel(project, path),
        "exists": path.exists(),
        "ai_asset_count": 0,
        "procedural_fallback_count": 0,
        "real_imagegen_count": 0,
        "non_terminal_ai_count": 0,
        "source_unresolved_fallback_count": 0,
        "missing_file_count": 0,
        "pending_examples": [],
        "source_unresolved_fallback_examples": [],
        "procedural_examples": [],
        "missing_file_examples": [],
    }
    payload = load_json_or_none(path)
    if payload is None:
        return result
    if isinstance(payload, dict) and payload.get("_read_error"):
        result["error"] = payload["_read_error"]
        return result
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        result["error"] = "visual_asset_manifest.json items must be a list"
        return result

    for item in items:
        if not isinstance(item, dict) or str(item.get("acquire_via") or "").lower() != "ai":
            continue
        notes = str(item.get("notes") or "").lower()
        if "dormant fallback" in notes:
            continue
        label = str(item.get("asset_id") or item.get("filename") or item.get("path") or "unknown")
        if is_unresolved_source_ai_fallback(item):
            result["source_unresolved_fallback_count"] += 1
            if len(result["source_unresolved_fallback_examples"]) < 8:
                result["source_unresolved_fallback_examples"].append(label)
            continue
        result["ai_asset_count"] += 1
        status = str(item.get("status") or "")
        generator = str(item.get("generator") or "")
        raw_asset_path = str(item.get("path") or "").strip()
        asset_path = Path(raw_asset_path) if raw_asset_path else None
        if status == "Generated" and generator == "procedural-preview-fallback":
            result["procedural_fallback_count"] += 1
            if len(result["procedural_examples"]) < 8:
                result["procedural_examples"].append(label)
        elif status == "Generated" and generator:
            result["real_imagegen_count"] += 1
        elif status in {"Pending", "Needs-Manual", "Missing", "Failed", ""}:
            result["non_terminal_ai_count"] += 1
            if len(result["pending_examples"]) < 8:
                result["pending_examples"].append(label)
        if asset_path is not None and not (project / asset_path).exists():
            result["missing_file_count"] += 1
            if len(result["missing_file_examples"]) < 8:
                result["missing_file_examples"].append(label)
    return result


def summarize_queue(project: Path) -> dict[str, Any]:
    path = project / "assets" / "images" / "image_generation_queue.json"
    result: dict[str, Any] = {
        "path": rel(project, path),
        "exists": path.exists(),
        "queued_count": 0,
        "source_fallback_queued_count": 0,
        "missing_expected_output_count": 0,
        "empty_prompt_count": 0,
        "examples": [],
        "source_fallback_examples": [],
    }
    payload = load_json_or_none(path)
    if payload is None:
        return result
    if isinstance(payload, dict) and payload.get("_read_error"):
        result["error"] = payload["_read_error"]
        return result
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        result["error"] = "image_generation_queue.json items must be a list or contain items"
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        if is_unresolved_source_ai_fallback(item):
            result["source_fallback_queued_count"] += 1
            if len(result["source_fallback_examples"]) < 8:
                result["source_fallback_examples"].append(
                    str(item.get("asset_id") or item.get("filename") or item.get("path") or "unknown")
                )
            continue
        result["queued_count"] += 1
        label = str(item.get("asset_id") or item.get("filename") or item.get("path") or "unknown")
        raw_expected = str(item.get("expected_output") or item.get("output") or item.get("path") or "").strip()
        expected = Path(raw_expected) if raw_expected else None
        if expected is not None and not expected.is_absolute():
            expected = project / expected
        if expected is not None and not expected.exists():
            result["missing_expected_output_count"] += 1
        prompt = str(item.get("prompt") or item.get("generation_prompt") or "").strip()
        raw_prompt_file = str(item.get("prompt_file") or "").strip()
        prompt_file = Path(raw_prompt_file) if raw_prompt_file else None
        if prompt_file is not None and not prompt_file.is_absolute():
            prompt_file = project / prompt_file
        prompt_file_text = ""
        if prompt_file is not None and prompt_file.is_file():
            prompt_file_text = prompt_file.read_text(encoding="utf-8").strip()
        if not prompt and not prompt_file_text:
            result["empty_prompt_count"] += 1
        if len(result["examples"]) < 8:
            result["examples"].append(label)
    return result


def summarize_batch(project: Path) -> dict[str, Any]:
    path = project / "assets" / "images" / "generation_batch" / "manifest.json"
    result: dict[str, Any] = {
        "path": rel(project, path),
        "exists": path.exists(),
        "item_count": 0,
        "missing_expected_output_count": 0,
        "requests_jsonl": rel(project, path.parent / "requests.jsonl"),
        "requests_jsonl_exists": (path.parent / "requests.jsonl").exists(),
        "generated_dir": rel(project, path.parent / "generated"),
        "examples": [],
    }
    payload = load_json_or_none(path)
    if payload is None:
        return result
    if isinstance(payload, dict) and payload.get("_read_error"):
        result["error"] = payload["_read_error"]
        return result
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        result["error"] = "generation_batch/manifest.json items must be a list"
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        result["item_count"] += 1
        label = str(item.get("asset_id") or item.get("filename") or item.get("expected_output") or "unknown")
        raw_expected = str(item.get("expected_output") or "").strip()
        expected = Path(raw_expected) if raw_expected else None
        if expected is not None and not expected.exists():
            result["missing_expected_output_count"] += 1
        if len(result["examples"]) < 8:
            result["examples"].append(label)
    return result


def summarize_built_in_guide(project: Path) -> dict[str, Any]:
    path = project / "assets" / "images" / "built_in_image_generation_tasks.json"
    markdown = project / "assets" / "images" / "built_in_image_generation_guide.md"
    result: dict[str, Any] = {
        "path": rel(project, path),
        "exists": path.exists(),
        "markdown": rel(project, markdown),
        "markdown_exists": markdown.exists(),
        "task_count": 0,
        "batch_count": 0,
        "generated_dir": rel(project, project / "assets" / "images" / "generation_batch" / "generated"),
        "examples": [],
    }
    payload = load_json_or_none(path)
    if payload is None:
        return result
    if isinstance(payload, dict) and payload.get("_read_error"):
        result["error"] = payload["_read_error"]
        return result
    if not isinstance(payload, dict):
        result["error"] = "built_in_image_generation_tasks.json must be an object"
        return result
    result["task_count"] = int(payload.get("task_count") or 0)
    batches = payload.get("batches")
    if isinstance(batches, list):
        result["batch_count"] = len(batches)
        for batch in batches:
            if not isinstance(batch, dict) or not isinstance(batch.get("items"), list):
                continue
            for item in batch["items"]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("asset_id") or item.get("filename") or "unknown")
                if len(result["examples"]) < 8:
                    result["examples"].append(label)
    return result


def summarize_latest_run(project: Path) -> dict[str, Any]:
    path = project / "assets" / "images" / "image_generation_run.json"
    result = {"path": rel(project, path), "exists": path.exists()}
    payload = load_json_or_none(path)
    if payload is None:
        return result
    if isinstance(payload, dict) and payload.get("_read_error"):
        result["error"] = payload["_read_error"]
        return result
    if isinstance(payload, dict):
        for key in ("ok", "status", "provider", "model", "selected_count", "generated_count", "failed_count", "preflight"):
            if key in payload:
                result[key] = payload[key]
        if isinstance(payload.get("failures"), list):
            result["failures"] = payload["failures"][:8]
    return result


def build_commands(project: Path, provider: str, provider_config: Path, api_key_env: str) -> list[str]:
    base = f"python3 {SCRIPT_DIR}"
    project_arg = str(project)
    provider_config_arg = str(provider_config)
    api_env_arg = f" --api-key-env {api_key_env}" if api_key_env else ""
    return [
        f"{base}/image_art_direction.py {project_arg} --update-prompts",
        f"{base}/stage_image_generation.py {project_arg} --force",
        (
            f"{base}/run_image_generation.py {project_arg} --provider {provider} "
            f"--provider-config {provider_config_arg}{api_env_arg} --stage --only-missing --preflight"
        ),
        (
            f"{base}/run_image_generation.py {project_arg} --provider {provider} "
            f"--provider-config {provider_config_arg}{api_env_arg} --stage --only-missing "
            "--execute --import-results"
        ),
    ]


def build_built_in_commands(project: Path) -> list[str]:
    base = f"python3 {SCRIPT_DIR}"
    project_arg = str(project)
    return [
        f"{base}/image_art_direction.py {project_arg} --update-prompts",
        f"{base}/stage_image_generation.py {project_arg} --force --only-missing",
        f"{base}/built_in_image_generation_guide.py {project_arg} --only-missing",
        (
            f"{base}/import_generated_assets.py {project_arg} "
            f"--generated-dir {project_arg}/assets/images/generation_batch/generated "
            f"--mapping {project_arg}/assets/images/generation_batch/import_mapping.template.json "
            '--generator "codex-built-in-image" --force --all-ai'
        ),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    provider = report["provider"]
    visual = report["visual_assets"]
    queue = report["queue"]
    batch = report["batch"]
    built_in = report["built_in_image_generation"]
    lines = [
        "# Image Generation Readiness",
        "",
        f"- OK: `{report['ok']}`",
        f"- Provider: `{provider['name']}` / `{provider['request_format']}` / `{provider['model']}`",
        f"- API key env: `{provider['api_key_env']}` present=`{provider['api_key_env_present']}`",
        f"- AI assets: {visual['ai_asset_count']} total, {visual['real_imagegen_count']} real, "
        f"{visual['procedural_fallback_count']} procedural fallback, {visual['non_terminal_ai_count']} pending",
        f"- Source-image AI fallbacks: {visual.get('source_unresolved_fallback_count', 0)} tracked separately",
        f"- Queue: {queue['queued_count']} queued, {queue['missing_expected_output_count']} missing outputs",
        f"- Queue source-image fallbacks skipped: {queue.get('source_fallback_queued_count', 0)}",
        f"- Batch: {batch['item_count']} staged, requests_jsonl_exists=`{batch['requests_jsonl_exists']}`",
        f"- Built-in image guide: exists=`{built_in['exists']}`, tasks={built_in['task_count']}, batches={built_in['batch_count']}",
    ]
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    if (
        visual.get("procedural_examples")
        or visual.get("pending_examples")
        or visual.get("source_unresolved_fallback_examples")
    ):
        lines.extend(["", "## Asset Examples", ""])
        for label in visual.get("procedural_examples", []):
            lines.append(f"- procedural fallback: `{label}`")
        for label in visual.get("pending_examples", []):
            lines.append(f"- pending/non-terminal: `{label}`")
        for label in visual.get("source_unresolved_fallback_examples", []):
            lines.append(f"- source-image fallback: `{label}`")
    lines.extend(["", "## Recommended Commands", ""])
    if report["recommended_commands"]:
        for command in report["recommended_commands"]:
            lines.extend(["```bash", command, "```", ""])
    else:
        lines.append("No real image-generation commands are required for this project.")
    if report.get("built_in_image_generation_commands"):
        lines.extend(["", "## Built-In Image Generation Route", ""])
        lines.append(
            "Use this route when Codex or another host-native image tool is available, or when the API key/provider is not configured."
        )
        lines.append("")
        for command in report["built_in_image_generation_commands"]:
            lines.extend(["```bash", command, "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def build_report(
    project: Path,
    *,
    provider_name: str,
    provider_config: Path,
    api_key_env: str,
    strict: bool,
) -> dict[str, Any]:
    resolved = resolve_provider(provider_name, provider_config, api_key_env)
    effective_api_key_env = str(resolved.get("api_key_env") or api_key_env or "OPENAI_API_KEY")
    auth_scheme = str(resolved.get("auth_scheme") or "bearer").lower()
    provider = {
        "name": provider_name,
        "display_name": str(resolved.get("display_name") or provider_name),
        "request_format": str(resolved.get("request_format") or ""),
        "model": str(resolved.get("model") or ""),
        "provider_config": str(provider_config),
        "provider_config_exists": provider_config.exists(),
        "api_key_env": effective_api_key_env,
        "api_key_env_present": bool(os.environ.get(effective_api_key_env, "")),
        "auth_scheme": auth_scheme,
        "base_url": str(resolved.get("base_url") or "").split("?", 1)[0],
    }
    visual = summarize_visual_manifest(project)
    queue = summarize_queue(project)
    batch = summarize_batch(project)
    built_in = summarize_built_in_guide(project)
    latest_run = summarize_latest_run(project)
    real_imagegen_required = visual.get("ai_asset_count", 0) > 0

    failures: list[str] = []
    warnings: list[str] = []
    if not visual["exists"]:
        failures.append("visual_asset_manifest.json is missing; prepare the deck project before production.")
    if not provider["provider_config_exists"]:
        failures.append(f"provider config is missing: {provider_config}")
    if real_imagegen_required and auth_scheme not in {"none", "no-auth"} and not provider["api_key_env_present"]:
        failures.append(f"{effective_api_key_env} is not set; real image generation cannot run.")
    if real_imagegen_required and visual.get("procedural_fallback_count", 0) > 0:
        failures.append(f"{visual['procedural_fallback_count']} AI assets still use procedural-preview-fallback.")
    if real_imagegen_required and visual.get("non_terminal_ai_count", 0) > 0:
        failures.append(f"{visual['non_terminal_ai_count']} AI assets are not terminal Generated assets.")
    if visual.get("source_unresolved_fallback_count", 0) > 0:
        warnings.append(
            f"{visual['source_unresolved_fallback_count']} AI fallback rows are tied to unresolved source visuals; "
            "resolve the source images instead of treating these as primary image-generation work."
        )
    if visual.get("ai_asset_count", 0) > 0 and not queue["exists"]:
        warnings.append("image_generation_queue.json is missing; run image_art_direction.py --update-prompts.")
    if real_imagegen_required and queue["exists"] and queue.get("empty_prompt_count", 0) > 0:
        failures.append(f"{queue['empty_prompt_count']} queued image assets have empty prompts.")
    if queue["exists"] and not batch["exists"]:
        warnings.append("generation_batch/manifest.json is missing; run stage_image_generation.py --force.")
    if real_imagegen_required and queue["exists"] and not built_in["exists"]:
        warnings.append(
            "built_in_image_generation_guide.md is missing; run built_in_image_generation_guide.py when using Codex/host-native image generation."
        )
    if not real_imagegen_required and (queue.get("queued_count", 0) > 0 or batch.get("item_count", 0) > 0):
        warnings.append(
            "stale image-generation queue or batch files exist but are ignored because visual_asset_manifest.json "
            "contains no primary AI assets."
        )
    if queue.get("source_fallback_queued_count", 0) > 0:
        warnings.append(
            f"{queue['source_fallback_queued_count']} source fallback queue rows are excluded from real image generation; "
            "resolve source visuals instead."
        )

    ok = not failures
    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/image_generation_readiness.py",
        "generated_at": utc_now(),
        "project": str(project),
        "strict": strict,
        "ok": ok,
        "provider": provider,
        "visual_assets": visual,
        "queue": queue,
        "batch": batch,
        "built_in_image_generation": built_in,
        "latest_run": latest_run,
        "recommended_commands": build_commands(project, provider_name, provider_config, effective_api_key_env)
        if real_imagegen_required
        else [],
        "built_in_image_generation_commands": build_built_in_commands(project) if real_imagegen_required else [],
        "failures": failures,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect qiaomu-ppt real image-generation readiness.")
    parser.add_argument("project", type=Path, help="Prepared qiaomu-ppt project directory.")
    parser.add_argument("--provider", default="openai", help="Image generation provider preset. Default: openai.")
    parser.add_argument("--provider-config", type=Path, default=DEFAULT_PROVIDER_CONFIG, help="Provider preset JSON.")
    parser.add_argument("--api-key-env", default="", help="Override API key environment variable name.")
    parser.add_argument("--output", type=Path, default=None, help="JSON report path. Defaults to reports/image_generation_readiness.json.")
    parser.add_argument("--markdown", type=Path, default=None, help="Markdown report path. Defaults to reports/image_generation_readiness.md.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when real-image readiness has failures.")
    args = parser.parse_args()

    project = args.project.resolve()
    if not project.exists():
        raise SystemExit(f"Project directory does not exist: {project}")
    output = args.output or project / "reports" / "image_generation_readiness.json"
    markdown = args.markdown or project / "reports" / "image_generation_readiness.md"
    report = build_report(
        project,
        provider_name=args.provider,
        provider_config=args.provider_config,
        api_key_env=args.api_key_env,
        strict=args.strict,
    )
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
