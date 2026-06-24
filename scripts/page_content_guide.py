#!/usr/bin/env python3
"""Create a human-readable per-page content guide for a qiaomu-ppt project."""

from __future__ import annotations

import argparse
import json
import re
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


def iter_slides(payload: Any) -> list[dict[str, Any]]:
    slides = payload.get("slides") if isinstance(payload, dict) else payload
    return [item for item in slides if isinstance(item, dict)] if isinstance(slides, list) else []


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(path)


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "-", value.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:64] or "page"


def load_source_cards(project: Path) -> dict[str, dict[str, Any]]:
    path = project / "sources" / "source_cards.json"
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    cards = payload.get("cards") if isinstance(payload, dict) else []
    out: dict[str, dict[str, Any]] = {}
    if isinstance(cards, list):
        for item in cards:
            if not isinstance(item, dict):
                continue
            card_id = clean_text(item.get("id"))
            if card_id:
                out[card_id] = item
    return out


def load_visual_assets(project: Path) -> dict[int, list[dict[str, Any]]]:
    path = project / "visual_asset_manifest.json"
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    items = payload.get("items") if isinstance(payload, dict) else []
    by_slide: dict[int, list[dict[str, Any]]] = {}
    if not isinstance(items, list):
        return by_slide
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            slide_no = int(item.get("slide_no") or 0)
        except (TypeError, ValueError):
            slide_no = 0
        if slide_no <= 0:
            continue
        by_slide.setdefault(slide_no, []).append(item)
    return by_slide


def load_qa_summary(project: Path) -> dict[str, Any]:
    checks = {
        "source_adequacy": project / "reports" / "source_adequacy.json",
        "content_outline_audit": project / "reports" / "content_outline_audit.json",
        "element_plan_audit": project / "reports" / "element_plan_audit.json",
        "style_fit_audit": project / "reports" / "style_fit_audit.json",
        "style_execution_audit": project / "reports" / "style_execution_audit.json",
        "deck_quality_benchmark": project / "reports" / "deck_quality_benchmark.json",
        "deck_repair_plan": project / "reports" / "deck_repair_plan.json",
        "pptx_text_check": project / "pptx_text_check.json",
        "project_check": project / "project_check.json",
        "export_manifest": project / "export_manifest.json",
    }
    summary: dict[str, Any] = {}
    for name, path in checks.items():
        if not path.exists():
            summary[name] = {"exists": False}
            continue
        try:
            data = read_json(path)
        except Exception as exc:
            summary[name] = {"exists": True, "error": str(exc)}
            continue
        item: dict[str, Any] = {"exists": True}
        if isinstance(data, dict):
            if "ok" in data:
                item["ok"] = bool(data.get("ok"))
            if "score" in data:
                item["score"] = data.get("score")
            if "readiness" in data:
                item["readiness"] = data.get("readiness")
            if "status" in data:
                item["status"] = data.get("status")
            failures = data.get("failures")
            warnings = data.get("warnings")
            if isinstance(failures, list):
                item["failure_count"] = len(failures)
            if isinstance(warnings, list):
                item["warning_count"] = len(warnings)
            if name == "deck_repair_plan":
                summary_data = data.get("summary") if isinstance(data.get("summary"), dict) else {}
                item["action_count"] = summary_data.get("action_count")
                item["critical_count"] = summary_data.get("critical_count")
        summary[name] = item
    return summary


def find_note_file(project: Path, slide_no: int) -> Path | None:
    notes_dir = project / "notes"
    if not notes_dir.exists():
        return None
    prefix = f"{slide_no:02d}_"
    matches = sorted(path for path in notes_dir.glob("*.md") if path.name.startswith(prefix))
    return matches[0] if matches else None


def build_page_entry(
    project: Path,
    slide: dict[str, Any],
    source_cards: dict[str, dict[str, Any]],
    assets_by_slide: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    try:
        slide_no = int(slide.get("slide_no") or slide.get("page") or 0)
    except (TypeError, ValueError):
        slide_no = 0
    source_card_ids = [clean_text(item) for item in slide.get("source_card_ids", []) if clean_text(item)]
    source_entries = []
    for card_id in source_card_ids:
        card = source_cards.get(card_id, {})
        source_entries.append(
            {
                "card_id": card_id,
                "source_ids": card.get("source_ids", []),
                "source_title": card.get("source_title") or card.get("title") or "",
                "claim": card.get("claim") or "",
                "evidence": card.get("evidence") or "",
            }
        )
    asset_entries = []
    for item in assets_by_slide.get(slide_no, []):
        raw_path = clean_text(item.get("path"))
        asset_entries.append(
            {
                "asset_id": item.get("asset_id") or "",
                "purpose": item.get("purpose") or "",
                "asset_role": item.get("asset_role") or "",
                "acquire_via": item.get("acquire_via") or "",
                "status": item.get("status") or "",
                "path": raw_path,
                "exists": bool(raw_path and (project / raw_path).exists()),
                "source_page_url": item.get("source_page_url") or "",
                "rights_notes": item.get("rights_notes") or "",
                "notes": item.get("notes") or "",
            }
        )
    note_file = find_note_file(project, slide_no)
    note_text = note_file.read_text(encoding="utf-8", errors="replace").strip() if note_file else ""
    component_plan = slide.get("component_plan") if isinstance(slide.get("component_plan"), dict) else {}
    return {
        "page": slide_no,
        "title": slide.get("claim_title") or slide.get("title") or "",
        "content": {
            "intent": slide.get("intent") or "",
            "audience_before": slide.get("audience_or_learning_state_before") or "",
            "audience_after": slide.get("audience_or_learning_state_after") or "",
            "visible_points": slide.get("content_points") if isinstance(slide.get("content_points"), list) else [],
            "concrete_anchor": slide.get("concrete_anchor") or "",
            "source_anchor": slide.get("source_anchor") or "",
            "raw_source_evidence": slide.get("source_evidence_raw") or "",
        },
        "source_evidence": source_entries,
        "visual_plan": {
            "visual_role": slide.get("visual_role") or "",
            "proof_object": slide.get("proof_object") or "",
            "layout_pattern": slide.get("layout_pattern_id") or slide.get("layout_pattern") or "",
            "component_type": component_plan.get("component_type") or slide.get("component_type") or "",
            "reading_path": slide.get("reading_path") or "",
            "media_need": slide.get("media_need") or "",
            "qa_risk": slide.get("qa_risk") or "",
        },
        "visual_assets": asset_entries,
        "speaker_notes": {
            "goal": slide.get("speaker_note_goal") or "",
            "file": rel(project, note_file) if note_file else "",
            "text": note_text,
        },
    }


def render_page_markdown(project: Path, page: dict[str, Any]) -> str:
    lines = [
        f"# Page {int(page['page']):02d} — {page['title']}",
        "",
        "## Content",
        "",
        f"- Intent: {page['content']['intent'] or 'Not recorded'}",
        f"- Audience before: {page['content']['audience_before'] or 'Not recorded'}",
        f"- Audience after: {page['content']['audience_after'] or 'Not recorded'}",
        f"- Concrete anchor: {page['content']['concrete_anchor'] or 'Not recorded'}",
        "",
        "Visible points:",
    ]
    points = page["content"].get("visible_points") or []
    if points:
        lines.extend(f"- {point}" for point in points)
    else:
        lines.append("- Not recorded")
    lines.extend(["", "## Source Evidence", ""])
    if page["source_evidence"]:
        for source in page["source_evidence"]:
            lines.append(f"- `{source['card_id']}` {source.get('claim') or source.get('evidence') or 'No claim text'}")
            if source.get("source_title"):
                lines.append(f"  Source: {source['source_title']}")
    else:
        lines.append("- No source card linked")
    lines.extend(["", "## Visual Plan", ""])
    for key, label in (
        ("visual_role", "Visual role"),
        ("proof_object", "Proof object"),
        ("layout_pattern", "Layout pattern"),
        ("component_type", "Component type"),
        ("reading_path", "Reading path"),
        ("media_need", "Media need"),
        ("qa_risk", "QA risk"),
    ):
        lines.append(f"- {label}: {page['visual_plan'].get(key) or 'Not recorded'}")
    lines.extend(["", "## Visual Assets", ""])
    if page["visual_assets"]:
        for asset in page["visual_assets"]:
            status = asset.get("status") or "unknown"
            via = asset.get("acquire_via") or "unknown"
            path = asset.get("path") or ""
            exists = "exists" if asset.get("exists") else "missing file"
            lines.append(f"- `{asset.get('asset_id')}` ({via}, {status}, {exists})")
            if asset.get("purpose"):
                lines.append(f"  Purpose: {asset['purpose']}")
            if path:
                lines.append(f"  Path: `{path}`")
            if asset.get("source_page_url"):
                lines.append(f"  Source URL: {asset['source_page_url']}")
            if asset.get("rights_notes"):
                lines.append(f"  Rights: {asset['rights_notes']}")
    else:
        lines.append("- No visual asset row linked")
    lines.extend(["", "## Speaker Notes", ""])
    if page["speaker_notes"].get("file"):
        lines.append(f"- File: `{page['speaker_notes']['file']}`")
    if page["speaker_notes"].get("goal"):
        lines.append(f"- Goal: {page['speaker_notes']['goal']}")
    if page["speaker_notes"].get("text"):
        lines.extend(["", page["speaker_notes"]["text"]])
    else:
        lines.append("- No notes text found")
    lines.append("")
    return "\n".join(lines)


def render_guide_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Page Content Guide",
        "",
        f"- Project: `{report['project']}`",
        f"- Page count: `{report['page_count']}`",
        f"- Generated at: `{report['generated_at']}`",
        "",
        "This guide gathers each page's outline, source evidence, visual plan, visual assets, speaker notes, and QA signals in one place.",
        "",
        "## Project QA Summary",
        "",
    ]
    for key, item in report.get("qa_summary", {}).items():
        if not isinstance(item, dict):
            continue
        pieces = [f"exists={str(item.get('exists')).lower()}"]
        for field in ("ok", "score", "readiness", "status", "failure_count", "warning_count", "action_count", "critical_count"):
            if field in item:
                pieces.append(f"{field}={item[field]}")
        lines.append(f"- `{key}`: " + ", ".join(pieces))
    lines.extend(["", "## Pages", ""])
    for page in report.get("pages", []):
        page_no = int(page["page"])
        lines.append(f"### Page {page_no:02d} — {page['title']}")
        lines.append("")
        lines.append(f"- Content file: `{page.get('content_file', '')}`")
        lines.append(f"- Intent: {page['content'].get('intent') or 'Not recorded'}")
        lines.append(f"- Source cards: {', '.join(source['card_id'] for source in page.get('source_evidence', [])) or 'none'}")
        lines.append(f"- Visual plan: {page['visual_plan'].get('component_type') or 'unknown'} / {page['visual_plan'].get('layout_pattern') or 'unknown'}")
        lines.append(f"- Visual assets: {len(page.get('visual_assets', []))}")
        lines.append(f"- Speaker notes: {page['speaker_notes'].get('file') or 'missing'}")
        lines.append("")
    return "\n".join(lines)


def build_report(project: Path) -> dict[str, Any]:
    slide_plan_path = project / "slide_plan.json"
    if not slide_plan_path.exists():
        raise SystemExit(f"slide_plan.json missing: {slide_plan_path}")
    slide_plan = read_json(slide_plan_path)
    slides = iter_slides(slide_plan)
    source_cards = load_source_cards(project)
    assets_by_slide = load_visual_assets(project)
    qa_summary = load_qa_summary(project)
    page_dir = project / "page_content"
    page_dir.mkdir(parents=True, exist_ok=True)

    pages: list[dict[str, Any]] = []
    for slide in slides:
        page = build_page_entry(project, slide, source_cards, assets_by_slide)
        page_no = int(page["page"])
        page_file = page_dir / f"{page_no:02d}-{slugify(str(page['title']))}.md"
        page_file.write_text(render_page_markdown(project, page), encoding="utf-8")
        page["content_file"] = rel(project, page_file)
        pages.append(page)

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/page_content_guide.py",
        "generated_at": utc_now(),
        "project": str(project),
        "page_count": len(pages),
        "pages": pages,
        "qa_summary": qa_summary,
        "outputs": {
            "markdown": "page_content_guide.md",
            "json": "page_content_guide.json",
            "per_page_dir": "page_content/",
        },
        "naming_policy": "Use page_content_guide for the deck-level guide and page_content/ for per-page editable content files.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory.")
    parser.add_argument("--output", type=Path, help="JSON output. Default: <project>/page_content_guide.json")
    parser.add_argument("--markdown", type=Path, help="Markdown output. Default: <project>/page_content_guide.md")
    args = parser.parse_args()

    project = args.project.resolve()
    report = build_report(project)
    output = args.output or project / "page_content_guide.json"
    markdown = args.markdown or project / "page_content_guide.md"
    write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_guide_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
