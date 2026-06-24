#!/usr/bin/env python3
"""Import externally generated visual assets into a qiaomu-ppt project.

Use this after Codex/gpt-image/another image backend has produced files for
rows in visual_asset_manifest.json. The script copies the files into the
manifest-declared paths, updates status/provenance/dimensions, and keeps the
image prompt queue in sync.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(value: str) -> str:
    value = re.sub(r"\.[a-zA-Z0-9]+$", "", str(value or "").strip().lower())
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def scan_images(directory: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    if not directory.exists():
        return out
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        out[path.name.lower()] = path
        out[path.stem.lower()] = path
        out[slug(path.name)] = path
        out[slug(path.stem)] = path
    return out


def load_mapping(path: Path | None) -> dict[str, Path]:
    if not path:
        return {}
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit("--mapping must be a JSON object")
    out: dict[str, Path] = {}
    for key, value in payload.items():
        out[str(key)] = Path(str(value)).expanduser()
    return out


def find_source_for_item(item: dict[str, Any], scanned: dict[str, Path], mapping: dict[str, Path]) -> Path | None:
    asset_id = str(item.get("asset_id") or "")
    filename = str(item.get("filename") or "")
    candidates = [
        asset_id,
        filename,
        Path(filename).stem,
        slug(asset_id),
        slug(filename),
        slug(Path(filename).stem),
    ]
    for candidate in candidates:
        if candidate in mapping:
            return mapping[candidate]
    lowered = [candidate.lower() for candidate in candidates if candidate]
    for candidate in lowered:
        if candidate in scanned:
            return scanned[candidate]
    return None


def image_size(path: Path) -> list[int]:
    with Image.open(path) as image:
        return [int(image.width), int(image.height)]


def copy_image(source: Path, target: Path, *, force: bool) -> None:
    if not source.exists():
        raise SystemExit(f"generated asset file not found: {source}")
    if target.exists() and not force:
        raise SystemExit(f"target exists; use --force to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def update_prompt_queue(project: Path, imported_asset_ids: set[str], generator: str) -> None:
    prompts_path = project / "assets" / "images" / "image_prompts.json"
    if not prompts_path.exists():
        return
    payload = load_json(prompts_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return
    for item in payload["items"]:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename") or "")
        item_id = slug(Path(filename).stem)
        if item_id in imported_asset_ids or filename in imported_asset_ids:
            item["status"] = "Generated"
            item["generator"] = generator
            item["imported_at"] = now_iso()
    write_json(prompts_path, payload)


def update_generation_queue(project: Path, imported_asset_ids: set[str], generator: str) -> None:
    queue_path = project / "assets" / "images" / "image_generation_queue.json"
    if not queue_path.exists():
        return
    payload = load_json(queue_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return
    imported_at = now_iso()
    for item in payload["items"]:
        if not isinstance(item, dict):
            continue
        asset_id = str(item.get("asset_id") or "")
        filename = str(item.get("filename") or "")
        candidates = {asset_id, filename, slug(asset_id), slug(filename), slug(Path(filename).stem)}
        if candidates & imported_asset_ids:
            item["status"] = "Generated"
            item["generator"] = generator
            item["imported_at"] = imported_at
    payload["last_import"] = {
        "imported_at": imported_at,
        "generator": generator,
        "imported_count": sum(
            1
            for item in payload["items"]
            if isinstance(item, dict) and str(item.get("generator") or "") == generator
        ),
    }
    write_json(queue_path, payload)


def update_stage_manifest(project: Path, generated_dir: Path, imported_asset_ids: set[str], generator: str) -> None:
    candidates = [
        generated_dir.parent / "manifest.json",
        project / "assets" / "images" / "generation_batch" / "manifest.json",
    ]
    imported_at = now_iso()
    for manifest_path in candidates:
        if not manifest_path.exists():
            continue
        try:
            payload = load_json(manifest_path)
        except Exception:
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            continue
        for item in payload["items"]:
            if not isinstance(item, dict):
                continue
            asset_id = str(item.get("asset_id") or "")
            filename = str(item.get("filename") or "")
            candidates_for_item = {asset_id, filename, slug(asset_id), slug(filename), slug(Path(filename).stem)}
            if candidates_for_item & imported_asset_ids:
                item["status"] = "imported"
                item["generator"] = generator
                item["imported_at"] = imported_at
        payload["last_import"] = {
            "imported_at": imported_at,
            "generator": generator,
        }
        write_json(manifest_path, payload)


def import_assets(
    project: Path,
    manifest_path: Path,
    generated_dir: Path,
    mapping_path: Path | None,
    *,
    generator: str,
    force: bool,
    only_pending: bool,
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise SystemExit("visual_asset_manifest.json must be an object")
    items = manifest.get("items")
    if not isinstance(items, list):
        raise SystemExit("visual_asset_manifest.json needs an items list")

    scanned = scan_images(generated_dir)
    mapping = load_mapping(mapping_path)
    imported: list[dict[str, Any]] = []
    missing: list[str] = []
    imported_prompt_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("acquire_via") or "") != "ai":
            continue
        if only_pending and str(item.get("status") or "") not in {"Pending", "Missing", "Failed"}:
            continue
        source = find_source_for_item(item, scanned, mapping)
        if not source:
            missing.append(str(item.get("asset_id") or item.get("filename") or "unknown"))
            continue
        rel_path = str(item.get("path") or "")
        if not rel_path:
            missing.append(str(item.get("asset_id") or item.get("filename") or "missing_path"))
            continue
        target = project / rel_path
        copy_image(source, target, force=force)
        item["status"] = "Generated"
        item["generator"] = generator
        item["generated_asset_source"] = str(source)
        item["imported_at"] = now_iso()
        item["dimensions"] = image_size(target)
        item["generation_note"] = "Imported from externally generated image file."
        imported.append({"asset_id": item.get("asset_id"), "source": str(source), "path": rel_path})
        imported_prompt_ids.add(str(item.get("asset_id") or ""))
        imported_prompt_ids.add(slug(str(item.get("asset_id") or "")))
        imported_prompt_ids.add(slug(Path(str(item.get("filename") or "")).stem))
        imported_prompt_ids.add(str(item.get("filename") or ""))

    status_summary: dict[str, int] = {}
    for item in items:
        if isinstance(item, dict):
            status = str(item.get("status") or "")
            status_summary[status] = status_summary.get(status, 0) + 1
    manifest["status_summary"] = status_summary
    manifest["last_asset_import"] = {
        "imported_at": now_iso(),
        "generator": generator,
        "generated_dir": str(generated_dir),
        "imported_count": len(imported),
        "missing_count": len(missing),
    }
    write_json(manifest_path, manifest)
    update_prompt_queue(project, imported_prompt_ids, generator)
    update_generation_queue(project, imported_prompt_ids, generator)
    update_stage_manifest(project, generated_dir, imported_prompt_ids, generator)
    return {"ok": True, "imported": imported, "missing": missing, "status_summary": status_summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Import generated image files into visual_asset_manifest.json.")
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory.")
    parser.add_argument("--generated-dir", type=Path, required=True, help="Directory containing generated image files.")
    parser.add_argument("--manifest", type=Path, default=None, help="visual_asset_manifest.json path.")
    parser.add_argument("--mapping", type=Path, default=None, help="Optional JSON mapping asset_id/filename to generated file path.")
    parser.add_argument("--generator", default="external-image-generation", help="Generator label to record in the manifest.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing target files.")
    parser.add_argument("--all-ai", action="store_true", help="Import for all AI rows, not only Pending/Missing/Failed rows.")
    args = parser.parse_args()

    project = args.project.resolve()
    manifest_path = args.manifest or project / "visual_asset_manifest.json"
    result = import_assets(
        project,
        manifest_path,
        args.generated_dir.expanduser().resolve(),
        args.mapping,
        generator=args.generator,
        force=args.force,
        only_pending=not args.all_ai,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
