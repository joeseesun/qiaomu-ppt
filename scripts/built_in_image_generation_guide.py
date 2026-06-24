#!/usr/bin/env python3
"""Create a host-native image-generation guide for Codex-style built-in tools."""

from __future__ import annotations

import argparse
import json
import re
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
    path.write_text(text, encoding="utf-8")


def slugify(value: str, fallback: str = "asset") -> str:
    value = re.sub(r"\.[a-zA-Z0-9]+$", "", str(value or "").strip().lower())
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:72] or fallback


def rel(project: Path, path: Path | str) -> str:
    raw = Path(str(path))
    try:
        return str(raw.resolve().relative_to(project.resolve()))
    except Exception:
        return str(path)


def load_queue(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"image generation queue not found: {path}")
    payload = read_json(path)
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise SystemExit(f"image generation queue needs an items list: {path}")
    return [item for item in items if isinstance(item, dict)]


def load_batch(project: Path) -> dict[str, dict[str, Any]]:
    path = project / "assets" / "images" / "generation_batch" / "manifest.json"
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        keys = [
            item.get("asset_id"),
            item.get("filename"),
            Path(str(item.get("filename") or "")).stem,
        ]
        for key in keys:
            if key:
                out[str(key)] = item
                out[slugify(str(key))] = item
    return out


def is_source_ai_fallback(item: dict[str, Any]) -> bool:
    asset_id = str(item.get("asset_id") or "").strip().lower()
    notes = str(item.get("notes") or item.get("generation_policy") or "").strip().lower()
    return asset_id.endswith("-ai-fallback") or "preview_fallback_only" in notes or "dormant fallback" in notes or (
        "ai fallback for preview/production while the remote source image remains" in notes
    )


def needs_host_generation(project: Path, item: dict[str, Any], *, only_missing: bool) -> bool:
    if str(item.get("acquire_via") or "ai").lower() not in {"", "ai"}:
        return False
    if is_source_ai_fallback(item):
        return False
    status = str(item.get("status") or "").strip()
    generator = str(item.get("generator") or "").strip()
    raw_path = str(item.get("path") or "").strip()
    file_exists = bool(raw_path and (project / raw_path).exists())
    if status == "Generated" and generator not in {"", "procedural-preview-fallback"} and file_exists:
        return False
    if status == "Generated" and generator == "procedural-preview-fallback":
        return True
    if only_missing and file_exists:
        return False
    return status in {"", "Pending", "Missing", "Failed", "Needs-Manual"} or not file_exists


def batch_lookup(batch_items: dict[str, dict[str, Any]], item: dict[str, Any]) -> dict[str, Any]:
    keys = [
        item.get("asset_id"),
        item.get("filename"),
        Path(str(item.get("filename") or "")).stem,
        slugify(str(item.get("asset_id") or "")),
        slugify(str(item.get("filename") or "")),
    ]
    for key in keys:
        if key and str(key) in batch_items:
            return batch_items[str(key)]
    return {}


def task_from_item(
    project: Path,
    item: dict[str, Any],
    batch_item: dict[str, Any],
    *,
    index: int,
    generated_dir: Path,
    generator_label: str,
) -> dict[str, Any]:
    asset_id = str(item.get("asset_id") or batch_item.get("asset_id") or f"asset-{index}")
    filename = str(item.get("filename") or batch_item.get("filename") or f"{slugify(asset_id)}.png")
    expected_output = Path(str(batch_item.get("expected_output") or generated_dir / filename))
    if not expected_output.is_absolute():
        expected_output = project / expected_output
    prompt_file = str(batch_item.get("prompt_file") or "")
    negative_prompt_file = str(batch_item.get("negative_prompt_file") or "")
    prompt = str(item.get("prompt") or item.get("generation_prompt") or "")
    negative_prompt = str(item.get("negative_prompt") or "")
    if prompt_file:
        prompt_path = Path(prompt_file)
        if prompt_path.exists():
            try:
                prompt = prompt_path.read_text(encoding="utf-8").strip() or prompt
            except Exception:
                pass
    if negative_prompt_file:
        negative_path = Path(negative_prompt_file)
        if negative_path.exists():
            try:
                negative_prompt = negative_path.read_text(encoding="utf-8").strip() or negative_prompt
            except Exception:
                pass
    return {
        "index": index,
        "asset_id": asset_id,
        "slide_no": item.get("slide_no") or batch_item.get("slide_no"),
        "filename": filename,
        "target_path": item.get("path") or batch_item.get("target_path"),
        "expected_output": str(expected_output),
        "expected_output_project_relative": rel(project, expected_output),
        "work_dir": batch_item.get("work_dir") or "",
        "prompt_file": prompt_file,
        "negative_prompt_file": negative_prompt_file,
        "page_role": item.get("page_role") or "",
        "text_policy": item.get("text_policy") or "none",
        "asset_role": item.get("asset_role") or item.get("visual_role") or "",
        "visual_type": item.get("visual_type") or item.get("type") or "",
        "safe_area": item.get("safe_area") or "",
        "content_link": item.get("content_link") or "",
        "background_duty": item.get("background_duty") or "",
        "semantic_anchor": item.get("semantic_anchor") or "",
        "size": item.get("size") or item.get("image_size") or "2K",
        "aspect_ratio": item.get("aspect_ratio") or "16:9",
        "generator_label": generator_label,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "status": item.get("status") or batch_item.get("status") or "needs_generation",
    }


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    size = max(1, size)
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Built-In Image Generation Guide",
        "",
        f"- Project: `{report['project']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- Generator label: `{report['generator_label']}`",
        f"- Pending host-native tasks: {report['task_count']}",
        f"- Skipped source-evidence fallback rows: {len(report['skipped_source_fallbacks'])}",
        "",
        "Use this guide when the runtime has a host-native image tool such as Codex built-in image generation. Generate the bitmap files, save each file at its expected output path, then import them into `visual_asset_manifest.json`.",
        "",
        "Hard rules:",
        "",
        "- Never mark `Generated` until the actual image file exists.",
        "- Keep body copy, titles, citations, charts, diagrams, labels, UI, cards, and data editable in SVG/PPTX/HTML foreground objects.",
        "- Do not generate fake evidence: no fake paper figures, screenshots, charts, equations, UI, documents, logos, or provenance objects.",
        "- Generate for the slide's content, not as decoration: every task's content link, background duty, and semantic anchor should be visible in the image decision.",
        "- Avoid random decorative linework, ornamental grids, glowing rails, and generic abstract wallpaper unless the slide's semantic anchor truly calls for that material.",
        "- Use the same deck-wide rendering and palette behavior implied by the prompt queue; do not restyle each image independently.",
        "- Prefer 3-4 images per generation pass, then import and inspect before continuing.",
        "",
        "Recommended setup:",
        "",
        "```bash",
        report["stage_command"],
        report["guide_command"],
        "```",
        "",
        "After generating files:",
        "",
        "```bash",
        report["import_command"],
        "```",
        "",
    ]
    if not report["batches"]:
        lines.append("No host-native image-generation tasks are pending.")
        return "\n".join(lines).rstrip() + "\n"

    for batch in report["batches"]:
        lines.extend(["---", "", f"## Batch {batch['batch_no']} ({len(batch['items'])} images)", ""])
        for item in batch["items"]:
            lines.extend(
                [
                    f"### {item['index']}. Slide {item.get('slide_no')} - {item['asset_id']}",
                    "",
                    f"- Save generated file to: `{item['expected_output_project_relative']}`",
                    f"- Target manifest path: `{item.get('target_path') or ''}`",
                    f"- Page role: `{item.get('page_role') or ''}`",
                    f"- Text policy: `{item.get('text_policy') or 'none'}`",
                    f"- Asset role: `{item.get('asset_role') or ''}`",
                    f"- Visual type: `{item.get('visual_type') or ''}`",
                    f"- Content link: {item.get('content_link') or 'not specified'}",
                    f"- Background duty: {item.get('background_duty') or 'not specified'}",
                    f"- Semantic anchor: {item.get('semantic_anchor') or 'not specified'}",
                    f"- Safe area: {item.get('safe_area') or 'not specified'}",
                    "",
                    "Prompt:",
                    "",
                    "```text",
                    str(item.get("prompt") or "").strip(),
                    "```",
                    "",
                    "Negative prompt:",
                    "",
                    "```text",
                    str(item.get("negative_prompt") or "").strip() or "Use the prompt's hard rules; avoid visible text, logos, watermarks, fake charts, fake documents, fake UI, and fake evidence.",
                    "```",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def build_guide(
    project: Path,
    *,
    queue_path: Path,
    output_json: Path,
    output_markdown: Path,
    batch_size: int,
    generator_label: str,
    only_missing: bool,
) -> dict[str, Any]:
    queue = load_queue(queue_path)
    batch_items = load_batch(project)
    generated_dir = project / "assets" / "images" / "generation_batch" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    tasks: list[dict[str, Any]] = []
    skipped_source_fallbacks: list[str] = []
    for item in queue:
        if is_source_ai_fallback(item):
            skipped_source_fallbacks.append(str(item.get("asset_id") or item.get("filename") or "unknown"))
            continue
        if not needs_host_generation(project, item, only_missing=only_missing):
            continue
        tasks.append(
            task_from_item(
                project,
                item,
                batch_lookup(batch_items, item),
                index=len(tasks) + 1,
                generated_dir=generated_dir,
                generator_label=generator_label,
            )
        )

    batches = [
        {"batch_no": idx, "items": group}
        for idx, group in enumerate(chunked(tasks, batch_size), start=1)
    ]
    script = f"python3 {SCRIPT_DIR}"
    stage_command = f"{script}/stage_image_generation.py {project} --force --only-missing"
    guide_command = f"{script}/built_in_image_generation_guide.py {project} --only-missing"
    import_command = (
        f"{script}/import_generated_assets.py {project} "
        f"--generated-dir {generated_dir} "
        f"--mapping {project / 'assets/images/generation_batch/import_mapping.template.json'} "
        f"--generator \"{generator_label}\" --force --all-ai"
    )
    report = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/built_in_image_generation_guide.py",
        "generated_at": utc_now(),
        "project": str(project),
        "queue": str(queue_path),
        "generator_label": generator_label,
        "batch_size": batch_size,
        "task_count": len(tasks),
        "skipped_source_fallbacks": skipped_source_fallbacks,
        "generated_dir": str(generated_dir),
        "mapping": str(project / "assets/images/generation_batch/import_mapping.template.json"),
        "stage_command": stage_command,
        "guide_command": guide_command,
        "import_command": import_command,
        "batches": batches,
    }
    write_json(output_json, report)
    write_text(output_markdown, render_markdown(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory.")
    parser.add_argument("--queue", type=Path, help="image_generation_queue.json path.")
    parser.add_argument("--output", type=Path, help="JSON output path.")
    parser.add_argument("--markdown", type=Path, help="Markdown output path.")
    parser.add_argument("--batch-size", type=int, default=3, help="Images per host-native generation pass. Default: 3.")
    parser.add_argument("--generator-label", default="codex-built-in-image", help="Generator label to record during import.")
    parser.add_argument("--only-missing", action="store_true", help="Skip rows whose target image file already exists unless they are procedural fallbacks.")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    if not project.exists():
        raise SystemExit(f"Project directory does not exist: {project}")
    queue_path = (args.queue or project / "assets" / "images" / "image_generation_queue.json").expanduser()
    if not queue_path.is_absolute():
        queue_path = project / queue_path
    output_json = args.output or project / "assets" / "images" / "built_in_image_generation_tasks.json"
    output_markdown = args.markdown or project / "assets" / "images" / "built_in_image_generation_guide.md"
    report = build_guide(
        project,
        queue_path=queue_path,
        output_json=output_json,
        output_markdown=output_markdown,
        batch_size=max(1, args.batch_size),
        generator_label=args.generator_label,
        only_missing=args.only_missing,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
