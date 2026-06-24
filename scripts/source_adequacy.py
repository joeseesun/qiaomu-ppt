#!/usr/bin/env python3
"""Check whether collected sources are adequate for a qiaomu-ppt deck."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve()))
    except Exception:
        return str(path)


def load_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return read_json(path)


def slide_count(project: Path, explicit: int) -> int:
    if explicit > 0:
        return explicit
    payload = load_json_if_exists(project / "slide_plan.json")
    slides = payload.get("slides") if isinstance(payload, dict) else payload
    return len(slides) if isinstance(slides, list) else 0


def list_sources(project: Path) -> list[dict[str, Any]]:
    payload = load_json_if_exists(project / "sources" / "source_manifest.json")
    sources = payload.get("sources") if isinstance(payload, dict) else []
    return [item for item in sources if isinstance(item, dict)]


def list_cards(project: Path) -> list[dict[str, Any]]:
    payload = load_json_if_exists(project / "sources" / "source_cards.json")
    if not isinstance(payload, dict):
        return []
    cards = payload.get("cards") or payload.get("items") or payload.get("source_cards") or []
    return [item for item in cards if isinstance(item, dict)]


def image_candidates_from_cards(project: Path) -> list[dict[str, Any]]:
    payload = load_json_if_exists(project / "sources" / "source_cards.json")
    candidates = payload.get("image_candidates") if isinstance(payload, dict) else []
    return [item for item in candidates if isinstance(item, dict)]


def manifest_image_count(sources: list[dict[str, Any]]) -> int:
    total = 0
    for source in sources:
        images = source.get("images")
        if isinstance(images, list):
            total += len(images)
    return total


def visual_asset_counts(project: Path) -> dict[str, int]:
    payload = load_json_if_exists(project / "visual_asset_manifest.json")
    items = payload.get("items") if isinstance(payload, dict) else []
    counts = {"source": 0, "web": 0, "user": 0, "ai": 0, "formula": 0, "placeholder": 0}
    if not isinstance(items, list):
        return counts
    for item in items:
        if not isinstance(item, dict):
            continue
        via = str(item.get("acquire_via") or "placeholder").lower()
        counts[via] = counts.get(via, 0) + 1
    return counts


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def style_targets(project: Path, slides: int) -> dict[str, Any]:
    payload = load_json_if_exists(project / "style_direction.json")
    targets = payload.get("density_targets") if isinstance(payload, dict) else None
    if isinstance(targets, dict):
        return targets
    return {
        "target_source_evidence_pages": max(1 if slides >= 6 else 0, round(slides * 0.3)),
        "target_visual_pages": max(1, round(slides * 0.5)) if slides else 0,
    }


def build_report(project: Path, *, slides: int, strict: bool) -> dict[str, Any]:
    sources = list_sources(project)
    cards = list_cards(project)
    image_candidates = image_candidates_from_cards(project)
    visual_counts = visual_asset_counts(project)
    targets = style_targets(project, slides)
    source_types = sorted({str(item.get("source_type") or item.get("fetch_route") or "unknown") for item in sources})
    total_text_chars = sum(as_int(item.get("text_chars")) for item in sources)
    unique_ids: set[str] = set()
    for card in cards:
        source_ids = card.get("source_ids", [])
        if isinstance(source_ids, str):
            source_ids = [source_ids]
        if isinstance(source_ids, list):
            unique_ids.update(source_id for source_id in source_ids if isinstance(source_id, str))
    unique_card_sources = sorted(unique_ids)
    manifest_images = manifest_image_count(sources)
    source_like_visuals = visual_counts.get("source", 0) + visual_counts.get("web", 0) + visual_counts.get("user", 0)
    target_evidence_pages = int(targets.get("target_source_evidence_pages") or 0)

    min_cards = max(3, min(slides or 6, round((slides or 6) * 0.65)))
    min_text_chars = max(600, (slides or 6) * 160)
    min_sources = 2 if (slides or 0) >= 8 else 1

    failures: list[str] = []
    warnings: list[str] = []
    if not sources:
        failures.append("sources/source_manifest.json has no sources; collect source material before professional production.")
    if len(sources) < min_sources:
        warnings.append(f"only {len(sources)} source(s); target at least {min_sources} for {slides or 'unknown'} slides")
    if total_text_chars < min_text_chars:
        failures.append(f"source text is too thin: {total_text_chars} chars; target at least {min_text_chars}")
    if len(cards) < min_cards:
        failures.append(f"source cards are too few: {len(cards)} cards; target at least {min_cards}")
    if cards and len(unique_card_sources) < min(len(sources), min_sources):
        warnings.append("source cards do not cover enough distinct sources")
    if target_evidence_pages and source_like_visuals < target_evidence_pages:
        warnings.append(
            f"source/web/user visual assets {source_like_visuals} below style target {target_evidence_pages}; "
            "resolve source images or add rights-clear user/web visuals"
        )
    if target_evidence_pages and (len(image_candidates) + manifest_images) < target_evidence_pages:
        warnings.append(
            f"image candidates {len(image_candidates) + manifest_images} below source evidence target {target_evidence_pages}"
        )

    ok = not failures
    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/source_adequacy.py",
        "generated_at": utc_now(),
        "project": str(project),
        "strict": strict,
        "ok": ok,
        "slide_count": slides,
        "thresholds": {
            "min_sources": min_sources,
            "min_cards": min_cards,
            "min_text_chars": min_text_chars,
            "target_source_evidence_pages": target_evidence_pages,
        },
        "metrics": {
            "source_count": len(sources),
            "source_types": source_types,
            "total_text_chars": total_text_chars,
            "source_card_count": len(cards),
            "unique_card_source_count": len(unique_card_sources),
            "image_candidate_count": len(image_candidates),
            "manifest_image_count": manifest_images,
            "source_like_visual_asset_count": source_like_visuals,
            "visual_asset_counts": visual_counts,
        },
        "failures": failures,
        "warnings": warnings,
        "recommended_next_steps": [
            "Run topic_research.py with --research-depth balanced or deep when the deck starts from a broad topic.",
            "Add primary/authoritative sources, not only a short user note, before final outline generation.",
            "Resolve source visuals selected by visual_asset_manifest.json before substituting generated atmosphere images.",
            "Keep evidence in source_cards.json and provenance in visual_asset_manifest.json; do not fake charts, screenshots, or historical images with AI.",
        ],
        "artifacts": {
            "source_manifest": rel(project, project / "sources" / "source_manifest.json"),
            "source_cards": rel(project, project / "sources" / "source_cards.json"),
            "style_direction": rel(project, project / "style_direction.json") if (project / "style_direction.json").exists() else "",
            "visual_asset_manifest": rel(project, project / "visual_asset_manifest.json") if (project / "visual_asset_manifest.json").exists() else "",
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Source Adequacy",
        "",
        f"- OK: `{report['ok']}`",
        f"- Slides: `{report['slide_count']}`",
        f"- Sources: `{metrics['source_count']}` ({', '.join(metrics['source_types'])})",
        f"- Source text chars: `{metrics['total_text_chars']}`",
        f"- Source cards: `{metrics['source_card_count']}`",
        f"- Image candidates: `{metrics['image_candidate_count'] + metrics['manifest_image_count']}`",
        f"- Source-like visual assets: `{metrics['source_like_visual_asset_count']}`",
    ]
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    lines.extend(["", "## Recommended Next Steps", ""])
    lines.extend(f"- {item}" for item in report["recommended_next_steps"])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check source adequacy for qiaomu-ppt professional production.")
    parser.add_argument("project", type=Path, help="Prepared qiaomu-ppt project directory.")
    parser.add_argument("--slides", type=int, default=0, help="Expected slide count. Defaults to slide_plan length.")
    parser.add_argument("--output", type=Path, default=None, help="JSON report path. Defaults to reports/source_adequacy.json.")
    parser.add_argument("--markdown", type=Path, default=None, help="Markdown report path. Defaults to reports/source_adequacy.md.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when source adequacy has failures.")
    args = parser.parse_args()
    project = args.project.resolve()
    if not project.exists():
        raise SystemExit(f"Project directory does not exist: {project}")
    slides = slide_count(project, args.slides)
    report = build_report(project, slides=slides, strict=args.strict)
    output = args.output or project / "reports" / "source_adequacy.json"
    markdown = args.markdown or project / "reports" / "source_adequacy.md"
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
