#!/usr/bin/env python3
"""Turn style/layout recommendations into an executable art-direction contract."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
STYLE_LIBRARIES = [
    DATA_DIR / "design_style_presets.json",
    DATA_DIR / "magazine_art_styles.json",
    DATA_DIR / "ppt_master_case_styles.json",
]


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


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


def load_styles() -> dict[str, dict[str, Any]]:
    styles: dict[str, dict[str, Any]] = {}
    for library in STYLE_LIBRARIES:
        if not library.exists():
            continue
        payload = read_json(library)
        for item in payload.get("styles", []):
            if isinstance(item, dict) and item.get("id"):
                item = dict(item)
                item["_library"] = library.name
                styles[str(item["id"])] = item
    return styles


def load_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return read_json(path)


def selected_style(style_recs: dict[str, Any]) -> dict[str, Any]:
    top = style_recs.get("top")
    if isinstance(top, list) and top and isinstance(top[0], dict):
        return top[0]
    return {}


def style_payload(style_id: str, fallback: dict[str, Any]) -> dict[str, Any]:
    full = load_styles().get(style_id)
    if full:
        return full
    return {
        "id": style_id or fallback.get("id", "source-backed-editorial"),
        "label": fallback.get("label", "Source-backed Editorial"),
        "description_summary": fallback.get("summary", ""),
        "ppt": {
            "archetype": fallback.get("archetype", "editorial_argument"),
            "qiaomu_visual_system": fallback.get("qiaomu_visual_system", "Qiaomu editorial"),
            "density": "medium",
            "palette": {"swatches": fallback.get("palette", [])},
            "typography": fallback.get("typography", {}),
            "slide_patterns": [],
            "layout_rules": [],
            "media_policy": "Use source/user/web evidence first; generated images only support atmosphere or concept imagery.",
            "chart_policy": "Use readable native charts and direct takeaways.",
            "image_asset_strategy": {"asset_density": "medium", "image_rendering": "editorial"},
        },
    }


def slides_from_plan(path: Path) -> list[dict[str, Any]]:
    payload = load_json_if_exists(path)
    if isinstance(payload, dict) and isinstance(payload.get("slides"), list):
        return [item for item in payload["slides"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def visual_counts(project: Path) -> dict[str, Any]:
    manifest = load_json_if_exists(project / "visual_asset_manifest.json")
    counts = {
        "source": 0,
        "web": 0,
        "user": 0,
        "ai": 0,
        "formula": 0,
        "placeholder": 0,
        "generated_ai": 0,
        "procedural_fallback_ai": 0,
    }
    items = manifest.get("items") if isinstance(manifest, dict) else []
    if not isinstance(items, list):
        return counts
    for item in items:
        if not isinstance(item, dict):
            continue
        via = str(item.get("acquire_via") or "placeholder").lower()
        counts[via] = counts.get(via, 0) + 1
        if via == "ai" and str(item.get("status") or "") == "Generated":
            if str(item.get("generator") or "") == "procedural-preview-fallback":
                counts["procedural_fallback_ai"] += 1
            else:
                counts["generated_ai"] += 1
    return counts


def density_targets(density: str, slide_count: int) -> dict[str, Any]:
    normalized = str(density or "medium").lower()
    if "high" in normalized or "dense" in normalized:
        source_ratio = 0.45
        image_ratio = 0.65
        max_same = 2
    elif "low" in normalized or "sparse" in normalized:
        source_ratio = 0.20
        image_ratio = 0.35
        max_same = 3
    else:
        source_ratio = 0.30
        image_ratio = 0.50
        max_same = 2
    return {
        "style_density": normalized,
        "target_visual_pages": max(1, round(slide_count * image_ratio)),
        "target_source_evidence_pages": max(1 if slide_count >= 6 else 0, round(slide_count * source_ratio)),
        "max_consecutive_same_layout": max_same,
        "max_active_colors_per_slide": 3,
    }


def layout_program(layout_recs: dict[str, Any], slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns = [item for item in layout_recs.get("top", []) if isinstance(item, dict)]
    if not slides or not patterns:
        return []
    program: list[dict[str, Any]] = []
    for idx, slide in enumerate(slides, start=1):
        pattern = patterns[(idx - 1) % len(patterns)]
        mappings = pattern.get("layout_pattern_mappings") or []
        program.append(
            {
                "slide_no": idx,
                "claim_title": slide.get("claim_title") or slide.get("title") or "",
                "proof_object": slide.get("proof_object") or "",
                "recommended_itl": pattern.get("id", ""),
                "recommended_structure": pattern.get("structure", ""),
                "layout_pattern_candidates": mappings[:4],
                "execution_note": "Map the slide proof object into this image/text structure; avoid generic card grids when a source image, chart, quote, or process object exists.",
            }
        )
    return program


def build_direction(project: Path) -> dict[str, Any]:
    style_recs = load_json_if_exists(project / "style_recommendations.json") or {}
    layout_recs = load_json_if_exists(project / "layout_recommendations.json") or {}
    slides = slides_from_plan(project / "slide_plan.json")
    style_seed = selected_style(style_recs)
    style = style_payload(str(style_seed.get("id") or ""), style_seed)
    ppt = style.get("ppt", {})
    strategy = ppt.get("image_asset_strategy") if isinstance(ppt.get("image_asset_strategy"), dict) else {}
    targets = density_targets(str(ppt.get("density") or strategy.get("asset_density") or "medium"), len(slides))
    counts = visual_counts(project)
    source_like_count = counts.get("source", 0) + counts.get("web", 0) + counts.get("user", 0)
    warnings: list[str] = []
    if slides and source_like_count < targets["target_source_evidence_pages"]:
        warnings.append(
            f"source/web/user visual assets {source_like_count} below target {targets['target_source_evidence_pages']} for selected style density"
        )
    if counts.get("procedural_fallback_ai", 0):
        warnings.append(f"{counts['procedural_fallback_ai']} AI assets are still procedural preview fallbacks")

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/style_direction.py",
        "generated_at": now_iso(),
        "project": str(project),
        "selected_style": {
            "id": style.get("id"),
            "label": style.get("label"),
            "library": style.get("_library", ""),
            "archetype": ppt.get("archetype"),
            "visual_system": ppt.get("qiaomu_visual_system"),
            "density": ppt.get("density") or strategy.get("asset_density") or "medium",
            "summary": style.get("description_summary", ""),
        },
        "style_contract": {
            "palette": ppt.get("palette", {}),
            "typography": ppt.get("typography", {}),
            "slide_patterns": ppt.get("slide_patterns", []),
            "layout_rules": ppt.get("layout_rules", []),
            "media_policy": ppt.get("media_policy", ""),
            "chart_policy": ppt.get("chart_policy", ""),
            "animation_hint": ppt.get("animation_hint", ""),
            "image_asset_strategy": strategy,
        },
        "density_targets": targets,
        "asset_counts": counts,
        "layout_program": layout_program(layout_recs, slides),
        "non_negotiables": [
            "Use source/user/web images as evidence before decorative generated images.",
            "Generated images must not contain readable Chinese text, fake charts, fake citations, logos, UI chrome, or slide layout objects.",
            "Each slide needs one dominant proof object and no more than three active colors.",
            "Avoid repeated card-grid pages; alternate image-led, evidence, quote, process, comparison, diagram, and data pages according to the claim.",
            "CJK multiline titles should keep readable line-height around 1.14-1.30 unless a rendered screenshot proves tighter leading is safe.",
        ],
        "failure_signals": [
            "low source visual count for a source-heavy topic",
            "procedural-preview-fallback assets in professional/final runs",
            "more than two adjacent slides with the same component_type or visual rhythm",
            "style selected only changes colors but does not affect image density, chart policy, and page rhythm",
        ],
        "warnings": warnings,
        "artifacts": {
            "style_recommendations": rel(project, project / "style_recommendations.json"),
            "layout_recommendations": rel(project, project / "layout_recommendations.json"),
            "slide_plan": rel(project, project / "slide_plan.json") if (project / "slide_plan.json").exists() else "",
            "visual_asset_manifest": rel(project, project / "visual_asset_manifest.json") if (project / "visual_asset_manifest.json").exists() else "",
        },
    }


def render_markdown(direction: dict[str, Any]) -> str:
    style = direction["selected_style"]
    lines = [
        "# Style Direction",
        "",
        f"- Selected style: `{style.get('label')}` (`{style.get('id')}`)",
        f"- Visual system: `{style.get('visual_system')}`",
        f"- Density: `{style.get('density')}`",
        f"- Target visual pages: `{direction['density_targets']['target_visual_pages']}`",
        f"- Target source evidence pages: `{direction['density_targets']['target_source_evidence_pages']}`",
        "",
        "## Media Policy",
        "",
        direction["style_contract"].get("media_policy") or "Use source evidence first; generated images support atmosphere only.",
        "",
        "## Chart Policy",
        "",
        direction["style_contract"].get("chart_policy") or "Use readable native charts with direct takeaways.",
        "",
        "## Non-Negotiables",
        "",
    ]
    lines.extend(f"- {item}" for item in direction["non_negotiables"])
    if direction.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in direction["warnings"])
    program = direction.get("layout_program") or []
    if program:
        lines.extend(["", "## Slide Layout Program", ""])
        for item in program:
            candidates = ", ".join(item.get("layout_pattern_candidates") or [])
            lines.append(
                f"- P{int(item['slide_no']):02d}: `{item.get('recommended_itl')}` "
                f"{item.get('recommended_structure')} | candidates: {candidates}"
            )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an executable style/art-direction contract for a qiaomu-ppt project.")
    parser.add_argument("project", type=Path, help="Prepared qiaomu-ppt project directory.")
    parser.add_argument("--output", type=Path, default=None, help="JSON output path. Defaults to style_direction.json.")
    parser.add_argument("--markdown", type=Path, default=None, help="Markdown output path. Defaults to style_direction.md.")
    args = parser.parse_args()
    project = args.project.resolve()
    if not project.exists():
        raise SystemExit(f"Project directory does not exist: {project}")
    direction = build_direction(project)
    output = args.output or project / "style_direction.json"
    markdown = args.markdown or project / "style_direction.md"
    write_json(output, direction)
    write_text(markdown, render_markdown(direction))
    print(json.dumps(direction, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
