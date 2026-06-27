#!/usr/bin/env python3
"""Prepare a qiaomu-ppt project from a topic, files, URLs, or source packets."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import recommend_layout as layout_mod  # noqa: E402
import recommend_style as style_mod  # noqa: E402


DEFAULT_PALETTES = [
    ["#0B1628", "#F4EFE4", "#C8472C"],
    ["#15171A", "#E7DDCA", "#D6A84F"],
    ["#F8F4EA", "#1D2633", "#2F66D0"],
    ["#111111", "#FFFFFF", "#D93025"],
]
BACKGROUND_ROLES = [
    "cover_atmosphere",
    "source_evidence_paper",
    "diagram_field",
    "comparison_stage",
    "quote_breathing_space",
    "closing_synthesis",
]
FORBIDDEN_BACKGROUND_OBJECTS = [
    "box",
    "card",
    "panel",
    "frame",
    "placeholder",
    "chart area",
    "image slot",
    "ui chrome",
    "text block",
]


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def slugify(value: str, fallback: str = "deck") -> str:
    value = re.sub(r"https?://", "", value.strip().lower())
    value = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value[:64] or fallback


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def run_json_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(
            "command failed: "
            + " ".join(command)
            + f"\nstdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command did not emit JSON: {' '.join(command)}\n{proc.stdout[:2000]}") from exc


def try_json_command(command: list[str], timeout: int | None = None) -> tuple[dict[str, Any], str]:
    try:
        proc = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {}, f"command timed out after {timeout}s: {' '.join(command)}"
    if proc.returncode not in {0, 2}:
        return {}, f"command failed {proc.returncode}: {' '.join(command)}\n{proc.stderr[-1000:]}"
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}, f"command emitted non-JSON: {' '.join(command)}\n{proc.stdout[:1000]}"
    if proc.returncode == 2 and not payload.get("ok"):
        return payload, proc.stderr.strip()[:1000] or "command completed with partial evidence"
    return payload, proc.stderr.strip()[:1000]


def infer_project(args: argparse.Namespace, inputs: list[str]) -> Path:
    if args.project:
        return args.project.expanduser().resolve()
    seed = args.slug or args.topic or (Path(inputs[0]).stem if inputs else "qiaomu-ppt")
    date = datetime.now().strftime("%Y-%m-%d")
    return (args.outputs_root.expanduser().resolve() / f"{date}-{slugify(seed)}").resolve()


def recommend_styles(query: str, route: str, audience: str, top: int = 3) -> dict[str, Any]:
    libraries = [style_mod.DEFAULT_LIBRARY, *style_mod.DEFAULT_EXTRA_LIBRARIES]
    styles = style_mod.load_styles(libraries)
    ranked: list[dict[str, Any]] = []
    for style in styles:
        score, reasons = style_mod.score_style(style, query, route, audience)
        ranked.append(
            {
                "score": score,
                "id": style["id"],
                "label": style["label"],
                "library": style.get("_library", ""),
                "archetype": style["ppt"]["archetype"],
                "qiaomu_visual_system": style["ppt"]["qiaomu_visual_system"],
                "recommended_routes": style["ppt"]["recommended_routes"],
                "palette": style["ppt"].get("palette", {}).get("swatches", [])[:5],
                "typography": style["ppt"].get("typography", {}),
                "summary": style.get("description_summary", ""),
                "reasons": reasons,
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["label"]))
    return {"query": query, "route": route, "top": ranked[:top]}


def recommend_layouts(query: str, route: str, top: int = 6) -> dict[str, Any]:
    payload = layout_mod.load_library(layout_mod.DEFAULT_LIBRARY)
    ranked: list[dict[str, Any]] = []
    for pattern in payload["patterns"]:
        score, reasons = layout_mod.score_pattern(payload, pattern, query, route)
        ranked.append(
            {
                "score": score,
                "id": pattern["id"],
                "name_zh": pattern["name_zh"],
                "name_en": pattern["name_en"],
                "master_group": pattern["master_group"],
                "structure": pattern["structure"],
                "layout_pattern_mappings": pattern.get("layout_pattern_mappings", []),
                "use_for": pattern.get("use_for", [])[:4],
                "image_role": pattern.get("image_role", [])[:4],
                "reasons": reasons,
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["id"]))
    for idx, item in enumerate(ranked, start=1):
        item["rank"] = idx
    return {"query": query, "route": route, "top": ranked[:top]}


def palette_from_style(style: dict[str, Any] | None) -> list[list[str]]:
    if not style:
        return DEFAULT_PALETTES
    swatches = [item.get("hex") for item in style.get("palette", []) if isinstance(item, dict) and item.get("hex")]
    swatches = [str(color) for color in swatches if re.match(r"^#[0-9a-fA-F]{6}$", str(color))]
    if len(swatches) < 3:
        return DEFAULT_PALETTES
    base = swatches[:6]
    palettes: list[list[str]] = []
    for idx in range(max(4, len(base))):
        first = base[idx % len(base)]
        second = base[(idx + 1) % len(base)]
        third = base[(idx + 2) % len(base)]
        palettes.append([first, second, third])
    return palettes


def build_visual_contract(slide_plan: dict[str, Any], style_recs: dict[str, Any], layout_recs: dict[str, Any]) -> dict[str, Any]:
    slides = slide_plan.get("slides", [])
    top_style = (style_recs.get("top") or [None])[0]
    palettes = palette_from_style(top_style)
    slide_palette_slots = [
        {"slide_no": idx, "active_colors": palettes[(idx - 1) % len(palettes)]}
        for idx in range(1, len(slides) + 1)
    ]
    slide_roles = []
    background_paths = {}
    for idx, slide in enumerate(slides, start=1):
        role = BACKGROUND_ROLES[(idx - 1) % len(BACKGROUND_ROLES)]
        asset = f"bg-{idx:02d}.svg"
        background_paths[asset] = f"assets/backgrounds/{asset}"
        slide_roles.append(
            {
                "slide_no": idx,
                "layout_role": slide.get("visual_role") or slide.get("intent") or "claim_proof",
                "reading_path": slide.get("reading_path") or "claim -> proof object -> implication",
                "background_role": role,
                "background_asset": asset,
                "dominant_object": slide.get("proof_object") or "source-backed claim",
                "image_text_pattern": ((layout_recs.get("top") or [{}])[(idx - 1) % max(1, len(layout_recs.get("top") or [{}]))]).get("id", ""),
            }
        )

    return {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "generator": "qiaomu-ppt/scripts/prepare_deck_project.py",
        "deck_visual_direction": (
            f"{top_style.get('label')} / {top_style.get('qiaomu_visual_system')}"
            if isinstance(top_style, dict)
            else "source-backed editorial presentation"
        ),
        "visual_noise_budget": "quiet",
        "color_budget": {
            "max_active_colors_per_slide": 3,
            "accent_policy": "one accent color per slide; neutral surfaces carry structure",
        },
        "slide_palette_slots": slide_palette_slots,
        "background_asset_policy": {
            "mode": "procedural_svg_backgrounds_plus_source_or_generated_atmosphere",
            "decorative_line_policy": "forbid non-functional decorative lines; lines must be axes, connectors, separators, or chart rules",
            "atmosphere_only_policy": "generated backgrounds are atmosphere-only and must not contain slide layout objects",
            "editable_foreground_policy": "all boxes, text blocks, charts, diagrams, callouts, and image slots stay as editable foreground objects",
            "procedural_fallback_policy": "use procedural SVG, CSS, or Canvas texture fields when image generation or web assets are unavailable",
            "forbidden_generated_objects": FORBIDDEN_BACKGROUND_OBJECTS,
            "procedural_background_paths": background_paths,
        },
        "background_roles": BACKGROUND_ROLES,
        "slide_roles": slide_roles,
        "layout_quality_policy": {
            "composition_formula": "one dominant claim, one proof object, one implication zone",
            "decorative_filler_policy": "forbid decorative filler that does not support reading path",
            "max_primary_regions": 3,
        },
        "typography_hierarchy_policy": {
            "primary_title_dominant": True,
            "secondary_text_max_ratio": 0.62,
            "promote_oversized_support_to_title": "promote oversized support text to title or split the slide instead of shrinking readable type",
            "title_line_height_policy": "CJK multi-line page titles use line-height 1.14-1.30; cover/closing titles may tighten only after screenshot review",
        },
        "layout_chrome_policy": {
            "nested_card_policy": "forbid nested visible cards",
            "parent_container_policy": "forbid giant parent containers used only for grouping",
            "bottom_card_row_policy": "allow bottom card rows only for real process or timeline structure",
            "numbered_badge_policy": "sequence badges only when the content is ordered",
            "max_cardlike_containers_per_slide": 3,
            "max_cover_metric_chips": 3,
        },
        "shape_component_policy": {
            "safe_area_policy": "keep margin and padding safe areas around every text, media, and proof object",
            "text_fit_policy": "text must fit inside visible shapes; split, shorten, resize, enlarge the shape, or fail on overflow",
            "connector_policy": "thin simple line connectors with small arrowheads; restrict chevron and chunky block arrows; endpoints attach to perimeter, edge, port, or boundary and never cross through node interiors or text; align on grid, axis, centerline, or equal spacing",
            "operator_policy": "operators such as plus, arrow, and equals stay outside or standalone, never inside arrow shapes",
            "card_density_policy": "limit cards and pills; use fewer containers and more open composition",
            "separator_policy": "separators only mark functional or meaningful zone boundaries",
            "preview_rejection_policy": "reject, fail, or fix rendered overflow, cramped titles, connector clutter, and unreadable diagrams",
        },
        "evidence_layout_policy": {
            "allowed_treatments": ["full_chart", "chart_with_takeaway", "chart_crop", "chart_then_takeaway"],
            "max_consecutive_same_composition": 2,
            "right_side_policy": "one clear takeaway or one number on the right side, never competing claims",
            "rail_policy": "forbid generic rails outside timeline or process slides",
        },
        "dense_chart_policy": "crop, split, zoom, or move detail to speaker notes when a chart or diagram becomes unreadable",
        "image_slots": [],
    }


def write_topic_research_plan(project: Path, topic: str, route: str, audience: str) -> None:
    brief = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "topic": topic,
        "assumed_audience": audience,
        "route": route,
        "research_status": "needed",
        "research_questions": [
            f"{topic} 的基本事实、时间线和关键人物/概念是什么？",
            f"{topic} 最适合讲成哪 2-3 条内容主线？",
            f"{topic} 有哪些可作为视觉证据的图片、图表、地点、原文、截图或数据？",
        ],
        "source_strategy": [
            "authoritative overview or official source",
            "academic/professional interpretation",
            "primary source or original document when relevant",
            "rights-clear visual assets with provenance notes",
        ],
        "known_risks": [
            "topic-only request has no evidence yet",
            "do not write final slide claims before source cards exist",
            "image availability and rights need early verification",
        ],
    }
    write_json(project / "sources" / "research_brief.json", brief)
    write_text(
        project / "sources" / "research_plan.md",
        f"""# Research Plan: {topic}

Status: needs source collection before final slide claims.

## Search Lanes

- Authoritative overview and chronology
- Primary works, documents, papers, product pages, or original references
- Context and interpretation from credible secondary sources
- Visual evidence: source images, charts, figures, screenshots, maps, portraits, artifacts, or rights-clear public images

## Required Before Final Outline

- `sources/source_manifest.json`
- `sources/source_notes.md`
- `sources/source_cards.json`
- image candidates or an explicit generated-image strategy

Do not treat this file as evidence. It is only the research brief.
""",
    )


def write_pending_preview_gate(project: Path, slide_count: int) -> None:
    if slide_count <= 7:
        return
    selected = [1, max(2, slide_count // 3), max(3, (slide_count * 2) // 3), slide_count]
    selected = sorted(dict.fromkeys(min(slide_count, max(1, item)) for item in selected))
    while len(selected) < 4:
        candidate = min(slide_count, len(selected) + 1)
        if candidate not in selected:
            selected.append(candidate)
        else:
            break
    gate = {
        "schema_version": "1.0.0",
        "mode": "four_slide_preview",
        "status": "pending_generation",
        "user_decision": "pending",
        "selected_slides": selected[:4],
        "outputs": [],
        "qa_focus": ["typography", "background", "connector geometry", "html readability"],
        "known_risks": [
            "prepare stage has not rendered preview artifacts",
            "full generation must not proceed until preview is approved or explicitly skipped",
        ],
    }
    write_json(project / "preview_gate.json", gate)


def mirror_research_plan_to_root(project: Path) -> None:
    source_plan = project / "sources" / "research_plan.md"
    if source_plan.exists():
        target = project / "research_plan.md"
        target.write_text(source_plan.read_text(encoding="utf-8"), encoding="utf-8")


def read_text_if_exists(path: Path, max_chars: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if max_chars and len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n\n...(truncated for dossier; see source file)"
    return text


def load_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def compact_cell(value: Any, max_chars: int = 120) -> str:
    if isinstance(value, list):
        value = " / ".join(str(item) for item in value[:4])
    if isinstance(value, dict):
        value = " / ".join(f"{key}: {val}" for key, val in list(value.items())[:4])
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_chars].rstrip() + ("..." if len(text) > max_chars else "")


def slide_plan_confirmation_table(project: Path) -> str:
    plan_path = project / "slide_plan.json"
    if not plan_path.exists():
        plan_path = project / "slide_plan_seed.json"
    payload = load_json_if_exists(plan_path)
    slides = payload.get("slides") if isinstance(payload, dict) else None
    if not isinstance(slides, list) or not slides:
        return "- Slide plan is pending. Generate/refine `slide_plan.json` before rendering."

    rows = [
        "| Page | Title/claim | Visible content | Source anchor | Layout | Background/image | QA risk |",
        "|---|---|---|---|---|---|---|",
    ]
    for idx, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        page = slide.get("page") or slide.get("slide_no") or f"P{idx:02d}"
        title = slide.get("claim_title") or slide.get("title") or ""
        content = (
            slide.get("visible_content")
            or slide.get("content")
            or slide.get("content_chunks")
            or slide.get("body")
            or ""
        )
        source_anchor = slide.get("source_anchor") or slide.get("source_card_ids") or ""
        layout = slide.get("layout_pattern") or slide.get("layout_pattern_id") or slide.get("component_plan") or ""
        background = (
            slide.get("image_or_background_plan")
            or slide.get("background_id")
            or slide.get("visual_role")
            or slide.get("proof_object")
            or ""
        )
        qa_risk = slide.get("qa_risk") or slide.get("copy_risk") or ""
        rows.append(
            "| "
            + " | ".join(
                compact_cell(item).replace("|", "/")
                for item in [page, title, content, source_anchor, layout, background, qa_risk]
            )
            + " |"
        )
    return "\n".join(rows)


def write_research_dossier(
    project: Path,
    topic: str,
    route: str,
    audience: str,
    status: str,
    inputs: list[str],
    warning: str = "",
) -> None:
    sources_dir = project / "sources"
    source_notes = read_text_if_exists(sources_dir / "source_notes.md", max_chars=12000)
    research_plan = read_text_if_exists(project / "research_plan.md", max_chars=4000) or read_text_if_exists(
        sources_dir / "research_plan.md",
        max_chars=4000,
    )
    manifest = load_json_if_exists(sources_dir / "source_manifest.json")
    cards_payload = load_json_if_exists(sources_dir / "source_cards.json")

    source_lines: list[str] = []
    if isinstance(manifest, dict):
        for idx, item in enumerate(manifest.get("sources") or [], start=1):
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("source") or item.get("url") or item.get("path") or f"source {idx}"
            source_type = item.get("source_type") or item.get("type") or ""
            route_name = item.get("fetch_route") or item.get("route") or ""
            missing = item.get("missing_evidence") or []
            source_lines.append(
                f"- s{idx:02d}: {title} ({source_type or 'source'}; {route_name or 'route recorded'})"
                + (f"; missing: {', '.join(str(x) for x in missing)}" if missing else "")
            )

    card_lines: list[str] = []
    image_lines: list[str] = []
    if isinstance(cards_payload, dict):
        for card in (cards_payload.get("cards") or [])[:16]:
            if not isinstance(card, dict):
                continue
            card_lines.append(
                f"- `{card.get('id', '')}` {compact_cell(card.get('claim'), 180)}"
                + (f" [{card.get('confidence')}]" if card.get("confidence") else "")
            )
        for item in (cards_payload.get("image_candidates") or [])[:16]:
            if not isinstance(item, dict):
                continue
            image_lines.append(
                f"- `{item.get('id', '')}` {item.get('role') or item.get('usable_pages') or 'image'}: "
                f"{compact_cell(item.get('path_or_url') or item.get('path') or item.get('url'), 160)}"
            )

    write_text(
        project / "research_dossier.md",
        f"""# Research Dossier: {topic or "source-backed deck"}

generated_at: {now_iso()}  
route: {route}  
audience: {audience}  
status: {status}

## Context

- Inputs: {", ".join(inputs) if inputs else "topic-only request"}
- This dossier is the reviewable material base before slide planning.
- Model prior knowledge may inform search lanes and synthesis, but slide claims should be anchored to supplied or ingested sources.

## Source Coverage

{chr(10).join(source_lines) if source_lines else "- No ingested source manifest yet. Use this dossier as a research brief, not as evidence."}

## Research Plan

{research_plan or "No separate research plan was generated."}

## Source Notes

{source_notes or "No source notes were generated yet."}

## Evidence Cards

{chr(10).join(card_lines) if card_lines else "- No source cards were generated yet."}

## Visual Assets And Image Candidates

{chr(10).join(image_lines) if image_lines else "- No image candidates were found yet; record source-image gaps or generated-image policy before rendering."}

## Gaps And Warnings

{warning.strip() if warning.strip() else "- No additional warnings recorded at preparation time."}

## Next Required Confirmation

Review `design_proposal.md` and the page-by-page `slide_plan.json` summary before rendering any PPT pages.
""",
    )


def build_outline_and_visuals(
    project: Path,
    topic: str,
    audience: str,
    purpose: str,
    desired_action: str,
    slides: int,
    no_slide_plan: bool,
    force: bool,
    style_recs: dict[str, Any],
    layout_recs: dict[str, Any],
    research_required: bool = False,
) -> dict[str, Any]:
    outline_command = [
        sys.executable,
        str(SCRIPT_DIR / "outline_from_source_cards.py"),
        str(project),
        "--title",
        topic,
        "--audience",
        audience,
        "--purpose",
        purpose,
        "--desired-action",
        desired_action,
        "--slides",
        str(slides),
    ]
    if research_required:
        outline_command.append("--research-required")
    if not no_slide_plan:
        outline_command.append("--write-slide-plan")
    if force:
        outline_command.append("--force")
    outline_result = run_json_command(outline_command)
    slide_plan_path = project / ("slide_plan_seed.json" if no_slide_plan else "slide_plan.json")
    if slide_plan_path.exists():
        slide_plan = read_json(slide_plan_path)
        visual_contract = build_visual_contract(slide_plan, style_recs, layout_recs)
        write_json(project / "visual_contract.json", visual_contract)
        write_pending_preview_gate(project, len(slide_plan.get("slides", [])))
    return outline_result


def build_visual_asset_plan(
    project: Path,
    topic: str,
    route: str,
    style_recs: dict[str, Any],
    *,
    resolve_source_visuals: bool = True,
    source_visual_limit: int = 3,
    source_visual_timeout: int = 8,
) -> dict[str, Any]:
    slide_plan = project / "slide_plan.json"
    if not slide_plan.exists():
        return {}

    rows_result = run_json_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "plan_visual_assets.py"),
            str(project),
            "--plan",
            str(slide_plan),
            "--subject",
            topic,
            "--output",
            str(project / "visual_asset_rows.json"),
        ]
    )

    top_style = (style_recs.get("top") or [{}])[0]
    palette = top_style.get("palette") if isinstance(top_style, dict) else []
    colors = [str(item.get("hex")) for item in palette if isinstance(item, dict) and item.get("hex")]
    primary = colors[0] if len(colors) > 0 else "#1E3A5F"
    secondary = colors[1] if len(colors) > 1 else "#F8F9FA"
    accent = colors[2] if len(colors) > 2 else "#D4AF37"

    manifest_result = run_json_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "visual_asset_manifest.py"),
            "init",
            "--project",
            str(project),
            "--subject",
            topic,
            "--route",
            route,
            "--rows",
            str(project / "visual_asset_rows.json"),
            "--rendering",
            "editorial",
            "--palette",
            "warm-stone",
            "--primary",
            primary,
            "--secondary",
            secondary,
            "--accent",
            accent,
        ]
    )
    source_visual_result: dict[str, Any] = {}
    if resolve_source_visuals:
        source_visual_result = run_json_command(
            [
                sys.executable,
                str(SCRIPT_DIR / "resolve_source_visuals.py"),
                str(project),
                "--limit",
                str(source_visual_limit),
                "--timeout",
                str(source_visual_timeout),
            ]
        )
    return {
        "rows": rows_result,
        "manifest": manifest_result,
        "source_visuals": source_visual_result,
    }


def build_image_art_direction(project: Path, topic: str) -> dict[str, Any]:
    manifest_path = project / "visual_asset_manifest.json"
    slide_plan = project / "slide_plan.json"
    if not manifest_path.exists() or not slide_plan.exists():
        return {}
    return run_json_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "image_art_direction.py"),
            str(project),
            "--manifest",
            str(manifest_path),
            "--slide-plan",
            str(slide_plan),
            "--subject",
            topic,
            "--provider",
            "gpt-image-2",
            "--model",
            "gpt-image-2",
            "--update-prompts",
        ]
    )


def build_style_direction(project: Path) -> dict[str, Any]:
    if not (project / "style_recommendations.json").exists() or not (project / "layout_recommendations.json").exists():
        return {}
    return run_json_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "style_direction.py"),
            str(project),
            "--output",
            str(project / "style_direction.json"),
            "--markdown",
            str(project / "style_direction.md"),
        ]
    )


def build_source_adequacy(project: Path, slides: int) -> dict[str, Any]:
    return run_json_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "source_adequacy.py"),
            str(project),
            "--slides",
            str(slides),
            "--output",
            str(project / "reports" / "source_adequacy.json"),
            "--markdown",
            str(project / "reports" / "source_adequacy.md"),
        ]
    )


def supplemental_depth(depth: str) -> str:
    if depth == "fast":
        return "balanced"
    return depth


def supplement_sources(
    project: Path,
    topic: str,
    route: str,
    audience: str,
    *,
    provider: str,
    depth: str,
    max_pages: int,
    max_cards_per_source: int,
    per_url_timeout: int,
    max_images: int,
    download_images: bool,
) -> tuple[dict[str, Any], str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "topic_research.py"),
        topic,
        "--output-dir",
        str(project / "sources"),
        "--provider",
        provider,
        "--depth",
        supplemental_depth(depth),
        "--audience",
        audience,
        "--route",
        route,
        "--max-pages",
        str(max(3, max_pages)),
        "--max-cards-per-source",
        str(max_cards_per_source),
        "--per-url-timeout",
        str(per_url_timeout),
        "--max-images",
        str(max_images),
    ]
    if download_images:
        command.append("--download-images")
    return try_json_command(command, timeout=max(60, max(3, max_pages) * per_url_timeout + 60))


def materialize_visual_assets(project: Path, *, force: bool) -> dict[str, Any]:
    manifest_path = project / "visual_asset_manifest.json"
    if not manifest_path.exists():
        return {}
    command = [
        sys.executable,
        str(SCRIPT_DIR / "materialize_visual_assets.py"),
        str(project),
    ]
    if force:
        command.append("--force")
    return run_json_command(command)


def maybe_generate_four_slide_preview(
    project: Path,
    enabled: bool,
    decision: str,
    approval_note: str,
) -> tuple[dict[str, Any], str]:
    if not enabled:
        return {}, ""
    command = [
        sys.executable,
        str(SCRIPT_DIR / "four_slide_preview.py"),
        str(project),
        "--decision",
        decision,
        "--force",
    ]
    if approval_note:
        command.extend(["--approval-note", approval_note])
    payload, warning = try_json_command(command, timeout=240)
    return payload, warning


def write_briefs(
    project: Path,
    topic: str,
    route: str,
    final_delivery: str,
    audience: str,
    purpose: str,
    desired_action: str,
    inputs: list[str],
    style_recs: dict[str, Any],
    layout_recs: dict[str, Any],
    status: str,
) -> None:
    top_style = (style_recs.get("top") or [{}])[0]
    top_patterns = layout_recs.get("top") or []

    def style_candidate_lines() -> str:
        lines: list[str] = []
        for idx, item in enumerate(style_recs.get("top", [])[:3], start=1):
            palette = ", ".join(
                f"{swatch.get('role','color')} {swatch.get('hex','')}"
                for swatch in item.get("palette", [])[:4]
                if isinstance(swatch, dict)
            )
            typo = item.get("typography", {}) if isinstance(item.get("typography"), dict) else {}
            reasons = "; ".join(str(reason) for reason in item.get("reasons", [])[:4])
            lines.append(
                "\n".join(
                    [
                        f"{idx}. **{item.get('label', '')}** `{item.get('id', '')}`",
                        f"   - score: {item.get('score', '')}; library: `{item.get('library', '')}`; archetype: `{item.get('archetype', '')}`",
                        f"   - why: {reasons or 'general fit'}",
                        f"   - palette: {palette or 'see style_recommendations.json'}",
                        f"   - typography: display `{typo.get('display', '')}`, body `{typo.get('body', '')}`",
                        f"   - use/risk: {item.get('summary', '')}",
                    ]
                )
            )
        return "\n\n".join(lines) or "- no style candidates generated"

    style_candidate_md = style_candidate_lines()
    slide_plan_md = slide_plan_confirmation_table(project)
    write_text(
        project / "deck_brief.md",
        f"""# Deck Brief

- topic: {topic or "source packet"}
- route: {route}
- final_delivery: {final_delivery}
- audience: {audience}
- purpose: {purpose}
- desired_action: {desired_action}
- prepare_status: {status}

## Inputs

{chr(10).join(f"- {item}" for item in inputs) if inputs else "- topic-only; research required before sourced slide claims"}

## Production Rule

Use source-backed claim titles, keep visible copy concise, and keep provenance in sidecar files or speaker notes unless visible citations are requested.
""",
    )
    write_text(
        project / "style_brief.md",
        f"""# Style Brief

selected_preset: {top_style.get("id", "source-backed-editorial")}
Recommended direction: {top_style.get("label", "source-backed editorial")}  
Visual system: {top_style.get("qiaomu_visual_system", "Qiaomu editorial")}  
Archetype: {top_style.get("archetype", "editorial_argument")}

## Style Candidates

{style_candidate_md}

## Image/Text Layout Candidates

{chr(10).join(f"- {item['id']} {item['name_zh']}: {item['structure']}" for item in top_patterns)}

## Non-Negotiables

- Backgrounds are atmosphere only; editable foreground owns layout.
- CJK multi-line page titles use readable leading around 1.14-1.30.
- No nested cards, no decorative rails, no fake evidence images.
""",
    )
    write_text(
        project / "design_proposal.md",
        f"""# PPT Design Proposal

- page_count: generated from requested slide count or source-card coverage.
- source_research_summary: see `research_dossier.md`, `sources/source_notes.md`, and `sources/source_cards.json`; status `{status}`.
- audience_state_change: from raw material or broad topic to a memorable source-backed argument.
- story_arc: claim-title outline in `slide_plan_seed.json` / `slide_plan.json` when available.
- slide_plan_for_confirmation:

{slide_plan_md}

- reference_model: {top_style.get("label", "source-backed editorial")} with source-backed proof objects and concrete image/text layouts.
- style_candidates:

{style_candidate_md}

- selected_direction: recommend **{top_style.get("label", "source-backed editorial")}** because its score/reasons best match the route, topic, audience, and available source/media structure. The user may choose another listed candidate before the four-slide preview.
- layout_mix: recorded in `layout_recommendations.json`.
- image_text_layout_plan: choose from the recommended ITL patterns and source image availability.
- visual_components: charts, diagrams, quote pages, source screenshots, and generated atmosphere only when they serve the claim.
- visual_asset_acquisition_plan: source/user/web/formula assets for evidence; Codex/host-native AI generation by default when available for atmosphere, chapter art, scenario, concept metaphor, quiet texture, or closing visuals.
- image_generation_decision: recommended default is Codex/host-native image generation when available; use configured API second; never use AI for fake evidence, charts, screenshots, logos, source/product objects, or layout objects.
- recommended_generation_stack: strongest suitable reasoning/layout/code model plus Codex built-in image generation as the first-choice bitmap route in Codex environments; gpt-image-2 or another verified provider as API-backed second route for backgrounds/concept images when host-native generation is unavailable or declined.
- background_plan: per-slide background roles are locked in `visual_contract.json` after slide plan exists.
- deliverables: PPTX, semantic HTML, parity HTML preview, PDF, Keynote when feasible, speaker notes, and sidecar contracts.
- model_contract: yes; use `content_contract.json`, `slide_plan.json`, `visual_contract.json`, `visual_asset_manifest.json`, and export manifests.
""",
    )
    write_json(project / "style_recommendations.json", style_recs)
    write_json(project / "layout_recommendations.json", layout_recs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a qiaomu-ppt project from topic, file, URL, folder, or ZIP inputs.")
    parser.add_argument("inputs", nargs="*", help="URLs, files, folders, or ZIP archives to ingest.")
    parser.add_argument("--input", dest="extra_inputs", action="append", default=[], help="Additional input. Can be repeated.")
    parser.add_argument("--topic", default="", help="Deck topic/title. Required when no inputs are supplied.")
    parser.add_argument("--project", type=Path, help="Output project directory. Defaults to outputs/<date>-<slug>.")
    parser.add_argument("--outputs-root", type=Path, default=Path("outputs"), help="Root used when --project is omitted.")
    parser.add_argument("--slug", default="", help="Project slug when --project is omitted.")
    parser.add_argument("--slides", type=int, default=10, help="Target slide count for the seeded outline.")
    parser.add_argument("--audience", default="general Chinese-speaking audience", help="Target audience.")
    parser.add_argument("--purpose", default="turn source material into a clear, sourced presentation argument", help="Deck purpose.")
    parser.add_argument("--desired-action", default="记住核心判断，并知道下一步该回到哪些来源继续核查", help="Desired audience action.")
    parser.add_argument("--route", default="", help="qiaomu-ppt route override.")
    parser.add_argument("--final-delivery", default="pptx_plus_semantic_html", help="Target delivery mode.")
    parser.add_argument("--style-query", default="", help="Optional style recommendation query.")
    parser.add_argument("--download-images", action="store_true", help="Download URL images during source intake.")
    parser.add_argument("--max-images", type=int, default=12, help="Maximum URL images to record/download.")
    parser.add_argument("--skip-source-visual-resolve", action="store_true", help="Skip targeted download of source visuals selected by the visual asset planner.")
    parser.add_argument("--source-visual-limit", type=int, default=3, help="Maximum selected remote source visuals to resolve after asset planning.")
    parser.add_argument("--source-visual-timeout", type=int, default=8, help="Per-source-visual download timeout in seconds.")
    parser.add_argument("--max-files", type=int, default=80, help="Maximum folder/ZIP files to ingest.")
    parser.add_argument("--max-cards-per-source", type=int, default=4, help="Source cards per source.")
    parser.add_argument("--skip-auto-research", action="store_true", help="For topic-only requests, write a research brief but do not fetch sources.")
    parser.add_argument("--no-auto-supplement-sources", action="store_true", help="Disable supplemental topic research when provided sources are too thin.")
    parser.add_argument("--research-provider", choices=["auto", "brave", "wikipedia", "duckduckgo", "openalex"], default="auto")
    parser.add_argument("--research-depth", choices=["fast", "balanced", "deep"], default="fast", help="Topic-only research breadth.")
    parser.add_argument("--research-max-pages", type=int, default=3, help="Topic-only research pages to ingest.")
    parser.add_argument("--research-per-url-timeout", type=int, default=25, help="Topic-only research per-URL timeout in seconds.")
    parser.add_argument("--generate-preview", action="store_true", help="Generate an isolated four-slide SVG/PNG preview package after slide_plan exists.")
    parser.add_argument("--materialize-assets", action="store_true", help="Create local procedural preview PNGs for pending AI visual assets before preview/render checks.")
    parser.add_argument("--preview-decision", choices=["pending", "approved", "skipped"], default="pending")
    parser.add_argument("--preview-approval-note", default="", help="Required when --preview-decision approved or skipped.")
    parser.add_argument("--no-slide-plan", action="store_true", help="Write only slide_plan_seed.json, not slide_plan.json.")
    parser.add_argument("--force", action="store_true", help="Overwrite generated contracts when needed.")
    args = parser.parse_args()
    if args.generate_preview and args.preview_decision in {"approved", "skipped"} and not args.preview_approval_note.strip():
        raise SystemExit("--preview-approval-note is required when --preview-decision is approved or skipped")

    inputs = [*args.inputs, *args.extra_inputs]
    if not inputs and not args.topic:
        raise SystemExit("provide at least one input or --topic")
    topic = args.topic or (Path(inputs[0]).stem if inputs and not re.match(r"https?://", inputs[0]) else "source-backed deck")
    route = args.route or style_mod.infer_route(" ".join([topic, *inputs])) or "talk_deck"
    project = infer_project(args, inputs)
    project.mkdir(parents=True, exist_ok=True)

    query = args.style_query or " ".join([topic, route, args.audience, *inputs])
    style_recs = recommend_styles(query, route, args.audience)
    layout_recs = recommend_layouts(query, route)

    source_result: dict[str, Any] = {}
    outline_result: dict[str, Any] = {}
    visual_asset_result: dict[str, Any] = {}
    image_art_direction_result: dict[str, Any] = {}
    materialize_result: dict[str, Any] = {}
    style_direction_result: dict[str, Any] = {}
    source_adequacy_result: dict[str, Any] = {}
    source_supplement_result: dict[str, Any] = {}
    research_result: dict[str, Any] = {}
    preview_result: dict[str, Any] = {}
    research_warning = ""
    source_supplement_warning = ""
    preview_warning = ""
    status = "needs_research"
    if inputs:
        command = [
            sys.executable,
            str(SCRIPT_DIR / "source_to_markdown.py"),
            *inputs,
            "--output-dir",
            str(project / "sources"),
            "--max-images",
            str(args.max_images),
            "--max-files",
            str(args.max_files),
            "--max-cards-per-source",
            str(args.max_cards_per_source),
        ]
        if args.download_images:
            command.append("--download-images")
        source_result = run_json_command(command)
        outline_result = build_outline_and_visuals(
            project=project,
            topic=topic,
            audience=args.audience,
            purpose=args.purpose,
            desired_action=args.desired_action,
            slides=args.slides,
            no_slide_plan=args.no_slide_plan,
            force=args.force,
            style_recs=style_recs,
            layout_recs=layout_recs,
            research_required=False,
        )
        if not args.no_slide_plan:
            visual_asset_result = build_visual_asset_plan(
                project,
                topic,
                route,
                style_recs,
                resolve_source_visuals=not args.skip_source_visual_resolve,
                source_visual_limit=args.source_visual_limit,
                source_visual_timeout=args.source_visual_timeout,
            )
            image_art_direction_result = build_image_art_direction(project, topic)
            if args.materialize_assets:
                materialize_result = materialize_visual_assets(project, force=args.force)
        status = "ready_for_design_review"
    else:
        if args.skip_auto_research:
            write_topic_research_plan(project, topic, route, args.audience)
        else:
            research_command = [
                sys.executable,
                str(SCRIPT_DIR / "topic_research.py"),
                topic,
                "--output-dir",
                str(project / "sources"),
                "--provider",
                args.research_provider,
                "--depth",
                args.research_depth,
                "--audience",
                args.audience,
                "--route",
                route,
                "--max-pages",
                str(args.research_max_pages),
                "--max-cards-per-source",
                str(args.max_cards_per_source),
                "--per-url-timeout",
                str(args.research_per_url_timeout),
                "--max-images",
                str(args.max_images),
            ]
            if args.download_images:
                research_command.append("--download-images")
            research_result, research_warning = try_json_command(
                research_command,
                timeout=max(45, args.research_max_pages * args.research_per_url_timeout + 45),
            )
            mirror_research_plan_to_root(project)
            source_result = research_result.get("source_result", {}) if research_result else {}
            if (project / "sources" / "source_cards.json").exists():
                try:
                    outline_result = build_outline_and_visuals(
                        project=project,
                        topic=topic,
                        audience=args.audience,
                        purpose=args.purpose,
                        desired_action=args.desired_action,
                        slides=args.slides,
                        no_slide_plan=args.no_slide_plan,
                        force=args.force,
                        style_recs=style_recs,
                        layout_recs=layout_recs,
                        research_required=True,
                    )
                    if not args.no_slide_plan:
                        visual_asset_result = build_visual_asset_plan(
                            project,
                            topic,
                            route,
                            style_recs,
                            resolve_source_visuals=not args.skip_source_visual_resolve,
                            source_visual_limit=args.source_visual_limit,
                            source_visual_timeout=args.source_visual_timeout,
                        )
                        image_art_direction_result = build_image_art_direction(project, topic)
                        if args.materialize_assets:
                            materialize_result = materialize_visual_assets(project, force=args.force)
                    status = "ready_for_design_review"
                except Exception as exc:
                    research_warning = (research_warning + "\n" if research_warning else "") + f"outline after research failed: {exc}"
                    status = "research_partial"
            else:
                write_topic_research_plan(project, topic, route, args.audience)

    mirror_research_plan_to_root(project)
    write_research_dossier(
        project=project,
        topic=topic,
        route=route,
        audience=args.audience,
        status=status,
        inputs=inputs,
        warning="\n".join(item for item in [research_warning, source_supplement_warning] if item),
    )
    write_briefs(
        project=project,
        topic=topic,
        route=route,
        final_delivery=args.final_delivery,
        audience=args.audience,
        purpose=args.purpose,
        desired_action=args.desired_action,
        inputs=inputs,
        style_recs=style_recs,
        layout_recs=layout_recs,
        status=status,
    )
    style_direction_result = build_style_direction(project)
    source_adequacy_result = build_source_adequacy(project, args.slides)
    if (
        status == "ready_for_design_review"
        and not args.no_slide_plan
        and not args.no_auto_supplement_sources
        and not args.skip_auto_research
        and topic
        and not source_adequacy_result.get("ok")
    ):
        source_supplement_result, source_supplement_warning = supplement_sources(
            project,
            topic,
            route,
            args.audience,
            provider=args.research_provider,
            depth=args.research_depth,
            max_pages=args.research_max_pages,
            max_cards_per_source=args.max_cards_per_source,
            per_url_timeout=args.research_per_url_timeout,
            max_images=args.max_images,
            download_images=args.download_images,
        )
        if (project / "sources" / "source_cards.json").exists():
            try:
                outline_result = build_outline_and_visuals(
                    project=project,
                    topic=topic,
                    audience=args.audience,
                    purpose=args.purpose,
                    desired_action=args.desired_action,
                    slides=args.slides,
                    no_slide_plan=args.no_slide_plan,
                    force=True,
                    style_recs=style_recs,
                    layout_recs=layout_recs,
                    research_required=True,
                )
                visual_asset_result = build_visual_asset_plan(
                    project,
                    topic,
                    route,
                    style_recs,
                    resolve_source_visuals=not args.skip_source_visual_resolve,
                    source_visual_limit=args.source_visual_limit,
                    source_visual_timeout=args.source_visual_timeout,
                )
                image_art_direction_result = build_image_art_direction(project, topic)
                if args.materialize_assets:
                    materialize_result = materialize_visual_assets(project, force=args.force)
                write_research_dossier(
                    project=project,
                    topic=topic,
                    route=route,
                    audience=args.audience,
                    status=status,
                    inputs=inputs,
                    warning="\n".join(item for item in [research_warning, source_supplement_warning] if item),
                )
                write_briefs(
                    project=project,
                    topic=topic,
                    route=route,
                    final_delivery=args.final_delivery,
                    audience=args.audience,
                    purpose=args.purpose,
                    desired_action=args.desired_action,
                    inputs=inputs,
                    style_recs=style_recs,
                    layout_recs=layout_recs,
                    status=status,
                )
                style_direction_result = build_style_direction(project)
                source_adequacy_result = build_source_adequacy(project, args.slides)
            except Exception as exc:
                source_supplement_warning = (
                    source_supplement_warning + "\n" if source_supplement_warning else ""
                ) + f"rebuild after supplemental research failed: {exc}"
    if status == "ready_for_design_review" and not args.no_slide_plan:
        preview_result, preview_warning = maybe_generate_four_slide_preview(
            project=project,
            enabled=args.generate_preview,
            decision=args.preview_decision,
            approval_note=args.preview_approval_note,
        )
    report = {
        "schema_version": "1.0.0",
        "ok": True,
        "generated_at": now_iso(),
        "project": str(project),
        "topic": topic,
        "route": route,
        "final_delivery": args.final_delivery,
        "status": status,
        "inputs": inputs,
        "research_result": research_result,
        "source_supplement_result": source_supplement_result,
        "preview_result": preview_result,
        "research_warning": research_warning,
        "source_supplement_warning": source_supplement_warning,
        "preview_warning": preview_warning,
        "source_result": source_result,
        "outline_result": outline_result,
        "visual_asset_result": visual_asset_result,
        "image_art_direction_result": image_art_direction_result,
        "style_direction_result": style_direction_result,
        "source_adequacy_result": source_adequacy_result,
        "materialize_result": materialize_result,
        "artifacts": {
            "deck_brief": "deck_brief.md",
            "research_dossier": "research_dossier.md" if (project / "research_dossier.md").exists() else "",
            "style_brief": "style_brief.md",
            "design_proposal": "design_proposal.md",
            "style_recommendations": "style_recommendations.json",
            "layout_recommendations": "layout_recommendations.json",
            "style_direction": "style_direction.json" if (project / "style_direction.json").exists() else "",
            "style_direction_md": "style_direction.md" if (project / "style_direction.md").exists() else "",
            "source_adequacy": "reports/source_adequacy.json" if (project / "reports" / "source_adequacy.json").exists() else "",
            "source_adequacy_md": "reports/source_adequacy.md" if (project / "reports" / "source_adequacy.md").exists() else "",
            "content_contract": "content_contract.json" if (project / "content_contract.json").exists() else "",
            "slide_plan_seed": "slide_plan_seed.json" if (project / "slide_plan_seed.json").exists() else "",
            "slide_plan": "slide_plan.json" if (project / "slide_plan.json").exists() else "",
            "visual_contract": "visual_contract.json" if (project / "visual_contract.json").exists() else "",
            "visual_asset_rows": "visual_asset_rows.json" if (project / "visual_asset_rows.json").exists() else "",
            "visual_asset_manifest": "visual_asset_manifest.json" if (project / "visual_asset_manifest.json").exists() else "",
            "image_prompts": "assets/images/image_prompts.json" if (project / "assets" / "images" / "image_prompts.json").exists() else "",
            "image_art_direction": "image_art_direction.json" if (project / "image_art_direction.json").exists() else "",
            "image_generation_queue": "assets/images/image_generation_queue.json" if (project / "assets" / "images" / "image_generation_queue.json").exists() else "",
            "preview_gate": "preview_gate.json" if (project / "preview_gate.json").exists() else "",
            "four_slide_preview_manifest": "previews/four_slide/four_slide_preview_manifest.json" if (project / "previews" / "four_slide" / "four_slide_preview_manifest.json").exists() else "",
            "topic_research_report": "sources/topic_research_report.json" if (project / "sources" / "topic_research_report.json").exists() else "",
            "research_brief": "sources/research_brief.json" if (project / "sources" / "research_brief.json").exists() else "",
        },
        "next_step": (
            "collect web/source research, then rerun with inputs"
            if status == "needs_research"
            else "review design_proposal.md, refine slide_plan.json, then run SVG/PPTX production"
        ),
    }
    write_json(project / "project_prepare_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
