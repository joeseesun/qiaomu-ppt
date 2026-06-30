#!/usr/bin/env python3
"""Audit whether slide elements are planned from proof needs, not decoration."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RICH_COMPONENTS = {
    "hero_claim",
    "comparison",
    "process_flow",
    "mechanism_loop",
    "chart_with_takeaway",
    "concept_map",
    "objection_response",
    "pull_quote",
    "closing_takeaway",
    "timeline",
    "screenshot_annotation",
    "source_evidence",
    "source_image_comparison",
    "data_context",
    "cover",
    "context",
    "core_text",
    "mechanism",
    "conflict",
    "closing",
}
PROOF_OBJECT_TOKENS = {
    "chart",
    "table",
    "diagram",
    "timeline",
    "process",
    "mechanism",
    "comparison",
    "quote",
    "screenshot",
    "source",
    "formula",
    "map",
    "model",
    "artifact",
    "cover",
    "context",
    "core_text",
    "conflict",
    "closing",
}
TERMINAL_STATUS = {"Generated", "Sourced", "Existing", "Rendered"}


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


def pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def norm(value: Any) -> str:
    return str(value or "").strip()


def load_manifest_stats(project: Path) -> dict[str, Any]:
    path = project / "visual_asset_manifest.json"
    stats: dict[str, Any] = {
        "exists": path.exists(),
        "asset_count": 0,
        "terminal_count": 0,
        "slide_asset_count": 0,
        "source_web_user_count": 0,
        "source_web_user_slide_count": 0,
        "ai_count": 0,
        "ai_slide_count": 0,
        "formula_count": 0,
        "pending_count": 0,
        "slides_with_assets": [],
        "acquire_via": {},
    }
    if not path.exists():
        return stats
    try:
        payload = read_json(path)
    except Exception as exc:
        stats["error"] = str(exc)
        return stats
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        stats["error"] = "items must be a list"
        return stats
    slides: set[int] = set()
    source_web_user_slides: set[int] = set()
    ai_slides: set[int] = set()
    acquire = Counter()
    for item in items:
        if not isinstance(item, dict):
            continue
        stats["asset_count"] += 1
        via = norm(item.get("acquire_via")).lower()
        status = norm(item.get("status"))
        acquire[via] += 1
        if via in {"source", "web", "user"}:
            stats["source_web_user_count"] += 1
        if via == "ai":
            stats["ai_count"] += 1
        if via == "formula":
            stats["formula_count"] += 1
        if status in TERMINAL_STATUS:
            stats["terminal_count"] += 1
            try:
                slide_no = int(item.get("slide_no") or 0)
            except Exception:
                slide_no = 0
            if slide_no > 0:
                slides.add(slide_no)
                if via in {"source", "web", "user"}:
                    source_web_user_slides.add(slide_no)
                if via == "ai":
                    ai_slides.add(slide_no)
        else:
            stats["pending_count"] += 1
    stats["slide_asset_count"] = len(slides)
    stats["source_web_user_slide_count"] = len(source_web_user_slides)
    stats["ai_slide_count"] = len(ai_slides)
    stats["slides_with_assets"] = sorted(slides)
    stats["acquire_via"] = dict(sorted(acquire.items()))
    return stats


def load_source_image_count(project: Path) -> int:
    path = project / "sources" / "source_cards.json"
    if not path.exists():
        return 0
    try:
        payload = read_json(path)
    except Exception:
        return 0
    candidates = payload.get("image_candidates") if isinstance(payload, dict) else []
    return len(candidates) if isinstance(candidates, list) else 0


def score_project(project: Path, min_score: int) -> dict[str, Any]:
    project = project.resolve()
    slides = iter_slides(read_json(project / "slide_plan.json"))
    failures: list[str] = []
    warnings: list[str] = []
    component_counter: Counter[str] = Counter()
    proof_counter: Counter[str] = Counter()
    layout_count = 0
    planned_count = 0
    proof_count = 0
    media_need_count = 0
    weak_element_slides: list[int] = []
    component_sequence: list[str] = []
    for slide in slides:
        component_plan = slide.get("component_plan") if isinstance(slide.get("component_plan"), dict) else {}
        component = norm(component_plan.get("component_type") or slide.get("component_type") or slide.get("visual_role"))
        proof = norm(slide.get("proof_object") or component_plan.get("narrative_role") or slide.get("visual_role"))
        layout = norm(slide.get("layout_pattern_id") or slide.get("layout_pattern") or component_plan.get("layout_pattern"))
        media_need = norm(slide.get("media_need"))
        if component:
            planned_count += 1
            component_counter[component] += 1
            component_sequence.append(component)
        if proof:
            proof_count += 1
            proof_counter[proof] += 1
        if layout:
            layout_count += 1
        if media_need:
            media_need_count += 1
        proof_text = f"{component} {proof} {layout} {media_need}".lower()
        if not any(token in proof_text for token in PROOF_OBJECT_TOKENS) and component not in RICH_COMPONENTS:
            weak_element_slides.append(int(slide.get("slide_no") or 0))

    manifest_stats = load_manifest_stats(project)
    source_image_count = load_source_image_count(project)
    slide_count = len(slides)
    min_component_target = max(3, min(slide_count, 6))
    min_proof_target = max(3, min(slide_count, 6))
    asset_target = max(1, round(slide_count * (0.55 if slide_count > 8 else 0.45)))
    generated_target = max(3, round(slide_count * 0.2)) if slide_count > 8 else 0
    max_component_reuse = max(component_counter.values()) if component_counter else 0
    component_reuse_limit = max(2, round(slide_count * 0.22))
    adjacent_component_repeats = sum(
        1 for idx in range(1, len(component_sequence)) if component_sequence[idx] == component_sequence[idx - 1]
    )
    if slide_count > 8 and not manifest_stats["exists"]:
        failures.append("visual_asset_manifest.json is required for decks over 8 slides")
    if source_image_count and manifest_stats["source_web_user_count"] == 0:
        warnings.append("source image candidates exist but no source/web/user assets are planned")

    categories = [
        {
            "id": "proof_object_coverage",
            "weight": 24,
            "score": pct(ratio(proof_count, slide_count)),
            "evidence": f"{proof_count}/{slide_count} slides have proof_object/visual_role",
        },
        {
            "id": "component_plan_coverage",
            "weight": 22,
            "score": pct(ratio(planned_count, slide_count)),
            "evidence": f"{planned_count}/{slide_count} slides have component plans",
        },
        {
            "id": "layout_and_media_intent",
            "weight": 16,
            "score": pct(min(ratio(layout_count, slide_count), ratio(media_need_count, slide_count))),
            "evidence": f"{layout_count}/{slide_count} layouts; {media_need_count}/{slide_count} media_need entries",
        },
        {
            "id": "element_diversity",
            "weight": 16,
            "score": pct(
                min(
                    ratio(len(component_counter), min_component_target),
                    ratio(len(proof_counter), min_proof_target),
                    1.0 - min(0.7, ratio(len(weak_element_slides), max(1, slide_count))),
                    1.0 - min(0.7, ratio(max(0, max_component_reuse - component_reuse_limit), max(1, slide_count))),
                )
            ),
            "evidence": (
                f"{len(component_counter)} component types, {len(proof_counter)} proof objects; "
                f"max component reuse {max_component_reuse}/{component_reuse_limit}; "
                f"adjacent repeats {adjacent_component_repeats}; weak slides {weak_element_slides[:8]}"
            ),
        },
        {
            "id": "asset_queue_readiness",
            "weight": 16,
            "score": pct(
                1.0
                if slide_count <= 4 and not manifest_stats["exists"]
                else min(ratio(manifest_stats["terminal_count"], asset_target), ratio(manifest_stats["slide_asset_count"], asset_target))
            ),
            "evidence": (
                f"{manifest_stats['terminal_count']} terminal assets; "
                f"{manifest_stats['slide_asset_count']} slides with assets; target {asset_target}"
            ),
        },
        {
            "id": "generative_visual_plan",
            "weight": 10,
            "score": pct(
                1.0
                if slide_count <= 8
                else min(
                    ratio(manifest_stats["ai_slide_count"], generated_target),
                    ratio(manifest_stats["ai_count"], generated_target),
                )
            ),
            "evidence": (
                f"{manifest_stats['ai_count']} AI rows on {manifest_stats['ai_slide_count']} slide(s); "
                f"generated target {generated_target}; total asset slides {manifest_stats['slide_asset_count']}/{asset_target}"
            ),
        },
        {
            "id": "source_visual_priority",
            "weight": 6,
            "score": pct(
                1.0
                if not source_image_count
                else min(
                    ratio(manifest_stats["source_web_user_count"], min(source_image_count, max(1, slide_count))),
                    ratio(manifest_stats["source_web_user_slide_count"], min(source_image_count, max(1, slide_count))),
                )
            ),
            "evidence": (
                f"{manifest_stats['source_web_user_count']} source/web/user assets on "
                f"{manifest_stats['source_web_user_slide_count']} slide(s); {source_image_count} source image candidates"
            ),
        },
    ]
    total_weight = sum(int(item["weight"]) for item in categories)
    score = round(sum(int(item["score"]) * int(item["weight"]) for item in categories) / total_weight)
    if score < min_score:
        failures.append(f"element plan score {score} below target {min_score}")
    if weak_element_slides:
        warnings.append("slides with weak/non-semantic element planning: " + ", ".join(map(str, weak_element_slides[:8])))
    if manifest_stats.get("pending_count"):
        warnings.append(f"{manifest_stats['pending_count']} visual asset rows are not terminal")
    if slide_count > 8 and manifest_stats.get("ai_count", 0) < generated_target:
        failures.append(
            f"long deck needs AI visual rows for key pages: {manifest_stats.get('ai_count', 0)}/{generated_target}. "
            "Downloaded/source images can support evidence pages but do not replace generated key-page visuals."
        )
    if max_component_reuse > component_reuse_limit:
        warnings.append(f"one component family is reused too often: {max_component_reuse} uses, limit {component_reuse_limit}")

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/element_plan_audit.py",
        "generated_at": utc_now(),
        "project": str(project),
        "ok": not failures,
        "score": score,
        "target_score": min_score,
        "slide_count": slide_count,
        "component_types": dict(sorted(component_counter.items())),
        "proof_objects": dict(sorted(proof_counter.items())),
        "component_repetition": {
            "max_component_reuse": max_component_reuse,
            "component_reuse_limit": component_reuse_limit,
            "adjacent_component_repeats": adjacent_component_repeats,
        },
        "visual_asset_stats": manifest_stats,
        "source_image_candidate_count": source_image_count,
        "categories": categories,
        "failures": failures,
        "warnings": warnings,
        "boundary": "This gate checks whether visuals, charts, diagrams, images, and source objects are planned as proof elements before rendering.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Element Plan Audit",
        "",
        f"- OK: `{str(report['ok']).lower()}`",
        f"- Score: `{report['score']}` / 100",
        f"- Target: `{report['target_score']}`",
        f"- Slides: `{report['slide_count']}`",
        "",
        "## Categories",
        "",
    ]
    for item in report["categories"]:
        lines.append(f"- `{item['id']}`: {item['score']} ({item['evidence']})")
    if report.get("component_types"):
        lines.extend(["", "## Component Types", ""])
        for key, value in report["component_types"].items():
            lines.append(f"- `{key}`: {value}")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    lines.extend(["", f"> {report['boundary']}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--min-score", type=int, default=75)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    project = args.project.resolve()
    report = score_project(project, args.min_score)
    output = args.output or project / "reports" / "element_plan_audit.json"
    markdown = args.markdown or project / "reports" / "element_plan_audit.md"
    write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.enforce and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
