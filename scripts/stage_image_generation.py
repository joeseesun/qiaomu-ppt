#!/usr/bin/env python3
"""Stage image-generation work items for Codex, gpt-image, or external tools."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(value: str, fallback: str = "asset") -> str:
    value = re.sub(r"\.[a-zA-Z0-9]+$", "", str(value or "").strip().lower())
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:72] or fallback


def read_queue(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise SystemExit(f"image generation queue needs an items list: {path}")
    return [item for item in items if isinstance(item, dict)]


def is_source_ai_fallback(item: dict[str, Any]) -> bool:
    asset_id = str(item.get("asset_id") or "").strip().lower()
    notes = str(item.get("notes") or item.get("generation_policy") or "").strip().lower()
    return asset_id.endswith("-ai-fallback") or "preview_fallback_only" in notes or "dormant fallback" in notes or (
        "ai fallback for preview/production while the remote source image remains" in notes
    )


def infer_status(project: Path, item: dict[str, Any]) -> str:
    path = str(item.get("path") or "")
    if path and (project / path).exists():
        return "target_exists"
    return "needs_generation"


def render_operator_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Staged Image Generation Batch",
        "",
        f"> Project: {manifest.get('project', '')}",
        f"> Generated: {manifest.get('generated_at', '')}",
        f"> Provider hint: {manifest.get('provider', '')}",
        f"> Model hint: {manifest.get('model', '')}",
        f"> Source-image fallback rows skipped: {len(manifest.get('skipped_source_fallbacks', []))}",
        "",
        "Generate one 16:9 image for each item, save it using the expected filename, then run:",
        "",
        "```bash",
        "python3 scripts/import_generated_assets.py <project> --generated-dir <batch-output-dir> --mapping <batch>/import_mapping.template.json --generator \"<backend-name>\" --force --all-ai",
        "```",
        "",
        "Rules:",
        "",
        "- Do not generate visible text, labels, logos, charts, screenshots, fake documents, or fake evidence unless the prompt explicitly permits embedded marks.",
        "- Keep titles, body copy, citations, charts, diagrams, labels, and data editable in the slide foreground.",
        "- Respect the safe area in each item; the generated image should support the layout, not redraw it.",
        "",
        "---",
        "",
    ]
    for item in manifest.get("items", []):
        lines.extend(
            [
                f"## {item.get('index')}. Slide {item.get('slide_no')} - {item.get('asset_id')}",
                "",
                f"- Work dir: `{item.get('work_dir')}`",
                f"- Expected output: `{item.get('expected_output')}`",
                f"- Target import path: `{item.get('target_path')}`",
                f"- Safe area: {item.get('safe_area')}",
                f"- Status: `{item.get('status')}`",
                "",
                "Prompt file:",
                "",
                f"`{item.get('prompt_file')}`",
                "",
                "Negative prompt file:",
                "",
                f"`{item.get('negative_prompt_file')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def stage_batch(
    project: Path,
    queue_path: Path,
    output_dir: Path,
    *,
    provider: str,
    model: str,
    force: bool,
    only_missing: bool,
    limit: int,
) -> dict[str, Any]:
    items = read_queue(queue_path)
    if force and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_dir = output_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    staged_items: list[dict[str, Any]] = []
    mapping: dict[str, str] = {}
    requests: list[dict[str, Any]] = []
    skipped_source_fallbacks: list[str] = []
    for raw_idx, item in enumerate(items, start=1):
        if is_source_ai_fallback(item):
            skipped_source_fallbacks.append(str(item.get("asset_id") or item.get("filename") or raw_idx))
            continue
        status = infer_status(project, item)
        if only_missing and status == "target_exists":
            continue
        if limit and len(staged_items) >= limit:
            break
        asset_id = str(item.get("asset_id") or f"asset-{raw_idx}")
        filename = str(item.get("filename") or f"{slugify(asset_id)}.png")
        stem = slugify(asset_id or filename, fallback=f"asset-{raw_idx}")
        work_dir = output_dir / f"{len(staged_items) + 1:02d}-{stem}"
        work_dir.mkdir(parents=True, exist_ok=True)

        expected_output = generated_dir / filename
        prompt_file = work_dir / "prompt.txt"
        negative_file = work_dir / "negative_prompt.txt"
        metadata_file = work_dir / "metadata.json"
        prompt = str(item.get("prompt") or "")
        negative = str(item.get("negative_prompt") or "")
        prompt_file.write_text(prompt.rstrip() + "\n", encoding="utf-8")
        negative_file.write_text(negative.rstrip() + "\n", encoding="utf-8")

        metadata = {
            "schema_version": "1.0.0",
            "asset_id": asset_id,
            "slide_no": item.get("slide_no"),
            "filename": filename,
            "target_path": item.get("path"),
            "expected_output": str(expected_output),
            "provider": provider or item.get("provider") or "",
            "model": model or item.get("model") or "",
            "size": item.get("size") or item.get("image_size") or "2K",
            "aspect_ratio": item.get("aspect_ratio") or "16:9",
            "safe_area": item.get("safe_area") or "",
            "prompt_file": str(prompt_file),
            "negative_prompt_file": str(negative_file),
            "prompt": prompt,
            "negative_prompt": negative,
            "generation_policy": item.get("generation_policy") or "real_image_generation",
        }
        write_json(metadata_file, metadata)

        mapping[asset_id] = str(expected_output)
        mapping[filename] = str(expected_output)
        mapping[Path(filename).stem] = str(expected_output)
        requests.append(
            {
                "custom_id": asset_id,
                "task": "image_generation",
                "provider": provider or item.get("provider") or "",
                "model": model or item.get("model") or "",
                "size": item.get("size") or item.get("image_size") or "2K",
                "aspect_ratio": item.get("aspect_ratio") or "16:9",
                "output": str(expected_output),
                "prompt": prompt,
                "negative_prompt": negative,
            }
        )
        staged_items.append(
            {
                "index": len(staged_items) + 1,
                "asset_id": asset_id,
                "slide_no": item.get("slide_no"),
                "filename": filename,
                "target_path": item.get("path"),
                "expected_output": str(expected_output),
                "work_dir": str(work_dir),
                "prompt_file": str(prompt_file),
                "negative_prompt_file": str(negative_file),
                "metadata_file": str(metadata_file),
                "safe_area": item.get("safe_area") or "",
                "generation_policy": item.get("generation_policy") or "real_image_generation",
                "status": status,
            }
        )

    generated_at = utc_now()
    manifest = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "project": project.name,
        "project_path": str(project),
        "queue": str(queue_path),
        "provider": provider,
        "model": model,
        "skipped_source_fallbacks": skipped_source_fallbacks,
        "batch_dir": str(output_dir),
        "generated_dir": str(generated_dir),
        "items": staged_items,
        "next_import_command": (
            f"python3 scripts/import_generated_assets.py {project} "
            f"--generated-dir {generated_dir} --mapping {output_dir / 'import_mapping.template.json'} "
            f"--generator \"{provider or 'external-image-generation'}\" --force --all-ai"
        ),
    }
    write_json(output_dir / "manifest.json", manifest)
    write_json(output_dir / "import_mapping.template.json", mapping)
    with (output_dir / "requests.jsonl").open("w", encoding="utf-8") as fh:
        for request in requests:
            fh.write(json.dumps(request, ensure_ascii=False) + "\n")
    (output_dir / "README.md").write_text(render_operator_markdown(manifest), encoding="utf-8")
    return {
        "ok": True,
        "items": len(staged_items),
        "skipped_source_fallbacks": len(skipped_source_fallbacks),
        "batch_dir": str(output_dir),
        "generated_dir": str(generated_dir),
        "manifest": str(output_dir / "manifest.json"),
        "requests_jsonl": str(output_dir / "requests.jsonl"),
        "mapping": str(output_dir / "import_mapping.template.json"),
        "readme": str(output_dir / "README.md"),
        "next_import_command": manifest["next_import_command"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory.")
    parser.add_argument("--queue", type=Path, help="image_generation_queue.json path.")
    parser.add_argument("--output-dir", type=Path, help="Batch output directory.")
    parser.add_argument("--provider", default="gpt-image-2", help="Provider hint to record in metadata.")
    parser.add_argument("--model", default="gpt-image-2", help="Model hint to record in metadata.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing batch directory.")
    parser.add_argument("--only-missing", action="store_true", help="Stage only items whose target image file does not exist.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum items to stage. 0 means all.")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    queue_path = args.queue or project / "assets" / "images" / "image_generation_queue.json"
    output_dir = args.output_dir or project / "assets" / "images" / "generation_batch"
    result = stage_batch(
        project,
        queue_path,
        output_dir,
        provider=args.provider,
        model=args.model,
        force=args.force,
        only_missing=args.only_missing,
        limit=max(0, args.limit),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
