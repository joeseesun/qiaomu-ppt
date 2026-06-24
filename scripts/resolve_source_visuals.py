#!/usr/bin/env python3
"""Download only the source visuals already selected by the asset planner."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from url_to_markdown import fetch_url, hash_text, safe_extension, slugify  # noqa: E402


def source_image_url_variants(url: str) -> list[str]:
    variants = [url]
    parsed = urlparse(url)
    marker = "/wikipedia/commons/thumb/"
    if "upload.wikimedia.org" in parsed.netloc and marker in parsed.path:
        prefix, tail = parsed.path.split(marker, 1)
        parts = tail.split("/")
        if len(parts) >= 4:
            original_path = f"{prefix}/wikipedia/commons/{parts[0]}/{parts[1]}/{parts[2]}"
            original = urlunparse((parsed.scheme, parsed.netloc, original_path, "", parsed.query, ""))
            if original not in variants:
                variants.append(original)
    return variants


def fetch_source_image(url: str, timeout: int, retries: int, retry_sleep: float) -> tuple[Any, str, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    last_result: Any = None
    for candidate_url in source_image_url_variants(url):
        for attempt in range(1, max(1, retries) + 1):
            result = fetch_url(candidate_url, timeout=timeout)
            last_result = result
            attempts.append(
                {
                    "url": candidate_url,
                    "attempt": attempt,
                    "status": result.status,
                    "content_type": result.content_type,
                    "bytes": len(result.data or b""),
                    "warnings": result.warnings,
                }
            )
            if result.data and not (result.status and result.status >= 400):
                return result, candidate_url, attempts
            if attempt < max(1, retries) and retry_sleep > 0:
                time.sleep(retry_sleep)
    return last_result, url, attempts


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None


def source_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = manifest.get("items")
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("acquire_via") != "source":
            continue
        if item.get("status") != "Needs-Manual":
            continue
        url = str(item.get("source_page_url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        out.append(item)
    return out


def update_matching_rows(rows_payload: Any, asset_id: str, path: str, status: str, notes: str) -> bool:
    rows = rows_payload.get("rows") if isinstance(rows_payload, dict) else None
    if not isinstance(rows, list):
        return False
    changed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("asset_id") or "") == asset_id:
            row["path"] = path
            row["status"] = status
            row["notes"] = notes
            changed = True
        if str(row.get("asset_id") or "") == f"{asset_id}-ai-fallback":
            row["status"] = "Needs-Manual"
            row["notes"] = "Dormant fallback: source visual was resolved to a local file."
            changed = True
    return changed


def update_source_cards(cards_payload: Any, source_image_id: str, source_url: str, rel_to_sources: str, byte_count: int, content_type: str) -> bool:
    if not isinstance(cards_payload, dict):
        return False
    changed = False
    candidates = cards_payload.get("image_candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if str(candidate.get("id") or "") == source_image_id or str(candidate.get("url") or "") == source_url:
                candidate["path"] = rel_to_sources
                candidate["bytes"] = byte_count
                candidate["content_type"] = content_type
                changed = True
    return changed


def update_source_manifest(manifest_payload: Any, source_url: str, rel_to_sources: str, byte_count: int, content_type: str) -> bool:
    if not isinstance(manifest_payload, dict):
        return False
    sources = manifest_payload.get("sources")
    if not isinstance(sources, list):
        return False
    changed = False
    for source in sources:
        if not isinstance(source, dict):
            continue
        images = source.get("images")
        if not isinstance(images, list):
            continue
        for image in images:
            if not isinstance(image, dict):
                continue
            if str(image.get("url") or "") == source_url:
                image["path"] = rel_to_sources
                image["bytes"] = byte_count
                image["content_type"] = content_type
                changed = True
    return changed


def dormant_fallbacks(items: list[dict[str, Any]], asset_id: str) -> int:
    count = 0
    fallback_id = f"{asset_id}-ai-fallback"
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("asset_id") or "") == fallback_id:
            item["status"] = "Needs-Manual"
            item["notes"] = "Dormant fallback: source visual was resolved to a local file."
            count += 1
    return count


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.resolve()
    manifest_path = args.manifest or project / "visual_asset_manifest.json"
    rows_path = args.rows or project / "visual_asset_rows.json"
    source_cards_path = args.source_cards or project / "sources" / "source_cards.json"
    source_manifest_path = args.source_manifest or project / "sources" / "source_manifest.json"

    manifest = load_json(manifest_path, {})
    if not isinstance(manifest, dict):
        raise SystemExit(f"manifest must be a JSON object: {manifest_path}")
    items = manifest.get("items")
    if not isinstance(items, list):
        raise SystemExit(f"manifest items missing: {manifest_path}")

    rows_payload = load_json(rows_path, {})
    cards_payload = load_json(source_cards_path, {})
    source_manifest = load_json(source_manifest_path, {})
    candidates = source_items(manifest)[: max(0, args.limit)]

    output_dir = project / "sources" / "images" / "resolved-source-visuals"
    resolved: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    dormant_count = 0
    url_cache: dict[str, dict[str, Any]] = {}

    for idx, item in enumerate(candidates, start=1):
        asset_id = str(item.get("asset_id") or f"source-{idx}")
        url = str(item.get("source_page_url") or "")
        content_type = ""
        if args.dry_run:
            skipped.append({"asset_id": asset_id, "url": url, "reason": "dry_run"})
            continue

        cached = url_cache.get(url)
        if cached:
            rel_project = str(cached["path"])
            rel_sources = str(cached["source_path"])
            byte_count = int(cached["bytes"])
            content_type = str(cached.get("content_type") or "")
            dims = tuple(cached.get("dimensions") or ()) or None
            effective_url = str(cached.get("effective_url") or url)
        else:
            result, effective_url, attempts = fetch_source_image(
                url,
                timeout=args.timeout,
                retries=args.retries,
                retry_sleep=args.retry_sleep,
            )
            content_type = result.content_type or ""
            if not result.data or (result.status and result.status >= 400):
                skipped.append(
                    {
                        "asset_id": asset_id,
                        "url": url,
                        "reason": "download_failed",
                        "attempts": attempts,
                        "warnings": result.warnings,
                    }
                )
                continue
            url_suffix = Path(urlparse(effective_url).path).suffix.lower()
            if "svg" in content_type.lower() or url_suffix == ".svg":
                skipped.append({"asset_id": asset_id, "url": url, "effective_url": effective_url, "reason": f"svg_not_supported:{content_type}", "attempts": attempts})
                continue
            if content_type and "image" not in content_type.lower() and not url_suffix:
                skipped.append({"asset_id": asset_id, "url": url, "effective_url": effective_url, "reason": f"not_image:{content_type}", "attempts": attempts})
                continue

            ext = safe_extension(effective_url, content_type)
            filename = f"{idx:02d}-{slugify(asset_id, 'source-visual')}-{hash_text(effective_url, 10)}{ext}"
            output_dir.mkdir(parents=True, exist_ok=True)
            target = output_dir / filename
            target.write_bytes(result.data)
            dims = image_dimensions(target)
            if dims:
                width, height = dims
                if width < args.min_width or height < args.min_height:
                    target.unlink(missing_ok=True)
                    skipped.append({"asset_id": asset_id, "url": url, "effective_url": effective_url, "reason": f"too_small:{width}x{height}", "attempts": attempts})
                    continue

            rel_project = str(target.relative_to(project))
            rel_sources = str(target.relative_to(project / "sources"))
            byte_count = target.stat().st_size
            url_cache[url] = {
                "path": rel_project,
                "source_path": rel_sources,
                "bytes": byte_count,
                "content_type": content_type,
                "dimensions": list(dims) if dims else [],
                "effective_url": effective_url,
            }
        notes = "Resolved selected remote source visual to a local file after planner quality filtering."

        item["path"] = rel_project
        item["status"] = "Existing"
        item["notes"] = notes
        item["resolved_source_visual"] = {
            "url": url,
            "effective_url": effective_url,
            "bytes": byte_count,
            "content_type": content_type,
            "dimensions": list(dims) if dims else [],
        }
        dormant_count += dormant_fallbacks(items, asset_id)
        update_matching_rows(rows_payload, asset_id, rel_project, "Existing", notes)
        update_source_cards(cards_payload, str(item.get("source_image_id") or ""), url, rel_sources, byte_count, content_type)
        update_source_manifest(source_manifest, url, rel_sources, byte_count, content_type)
        resolved.append(
            {
                "asset_id": asset_id,
                "url": url,
                "path": rel_project,
                "bytes": byte_count,
                "content_type": content_type,
                "dimensions": list(dims) if dims else [],
            }
        )

    write_json(manifest_path, manifest)
    if isinstance(rows_payload, dict):
        write_json(rows_path, rows_payload)
    if isinstance(cards_payload, dict):
        write_json(source_cards_path, cards_payload)
    if isinstance(source_manifest, dict):
        write_json(source_manifest_path, source_manifest)

    return {
        "ok": True,
        "project": str(project),
        "candidates": len(candidates),
        "resolved": resolved,
        "skipped": skipped,
        "dormant_ai_fallbacks": dormant_count,
        "manifest": str(manifest_path),
        "rows": str(rows_path) if rows_path.exists() else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve selected remote source visuals into local source image files.")
    parser.add_argument("project", type=Path, help="Project directory.")
    parser.add_argument("--manifest", type=Path, default=None, help="visual_asset_manifest.json path.")
    parser.add_argument("--rows", type=Path, default=None, help="visual_asset_rows.json path.")
    parser.add_argument("--source-cards", type=Path, default=None, help="sources/source_cards.json path.")
    parser.add_argument("--source-manifest", type=Path, default=None, help="sources/source_manifest.json path.")
    parser.add_argument("--limit", type=int, default=4, help="Maximum selected source visuals to resolve.")
    parser.add_argument("--timeout", type=int, default=12, help="Per-image download timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Download attempts per URL variant.")
    parser.add_argument("--retry-sleep", type=float, default=0.8, help="Seconds to sleep between retry attempts.")
    parser.add_argument("--min-width", type=int, default=120, help="Minimum accepted width when dimensions can be read.")
    parser.add_argument("--min-height", type=int, default=90, help="Minimum accepted height when dimensions can be read.")
    parser.add_argument("--dry-run", action="store_true", help="Report candidates without downloading.")
    args = parser.parse_args()

    print(json.dumps(resolve(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
