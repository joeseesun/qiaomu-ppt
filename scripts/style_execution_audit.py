#!/usr/bin/env python3
"""Audit whether the selected style direction was actually executed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {"Generated", "Sourced", "Existing", "Rendered"}
GENERIC_COMPONENTS = {"", "context", "body", "content", "card_grid", "cards", "generic"}
RICH_COMPONENTS = {
    "hero_claim",
    "source_evidence",
    "source_process_flow",
    "screenshot_annotation",
    "process_flow",
    "mechanism_loop",
    "chart_with_takeaway",
    "concept_map",
    "objection_response",
    "pull_quote",
    "comparison",
    "closing_takeaway",
}
PROOF_COMPONENTS = {
    "comparison",
    "source_evidence",
    "source_process_flow",
    "source_concept_map",
    "source_data_context",
    "screenshot_annotation",
    "process_flow",
    "mechanism_loop",
    "chart_with_takeaway",
    "concept_map",
}
PROOF_MARKERS_BY_MATERIAL = {
    "blueprint-grid": ("GRID-", "GRID P", "blueprint-formula-rails"),
    "brutalist-newsprint": ("EVIDENCE", "newspaper-proof-columns"),
    "risograph-zine": ("PROOF", "riso-proof-collage"),
    "eastern-rice-paper": ("source artifact", "ink-artifact-proof", ">证<"),
    "luxury-editorial-paper": ("PROOF SPREAD", "folio-proof-spread"),
    "nvidia-terminal": ("CUDA TRACE", "gpu-metric-console"),
    "verge-neon-editorial": ("SIGNAL STACK", "neon-argument-stack"),
    "opencode-manpage": ("$ proof", "cli-proof-transcript"),
    "bento-tech": ("EVIDENCE TILE", "tile-evidence-system"),
    "architecture-catalog": ("ARCHIVE PLATE", "museum-archive-plate"),
    "wired-tech-magazine": ("PROOF INDEX", "index-proof-system"),
    "editorial-paper": ("PROOF", "editorial-proof-objects"),
}
STYLE_MARKERS_BY_COMPONENT_LANGUAGE = {
    "blueprint-annotation": ("GRID SYSTEM", "GRID P", "ANNOTATION", "GRID-"),
    "newspaper-rulebox": ("NEWS FIELD", "PAGE ", "FIELD NOTE", "EVIDENCE"),
    "riso-overprint": ("RISO PRINT", "RISO P", "PROOF", "riso-proof-collage"),
    "ink-seal-paper": ("纸本", ">乔<", ">印<", ">记<", "source artifact"),
    "folio-hairline": ("LUXE FOLIO", "FOLIO", "EDITORIAL NOTE", "PROOF SPREAD"),
    "gpu-control-panel": ("GPU CONSOLE", "GPU ", "KERNEL", "CUDA TRACE"),
    "neon-news-module": ("EDGE SIGNAL", "EDGE ", "SIGNAL", "SIGNAL STACK"),
    "terminal-manpage-block": ("MANPAGE", "SYNOPSIS", "SECTION", "$ proof"),
    "bento-product-tile": ("BENTO SYSTEM", "BENTO VIEW", "EVIDENCE TILE"),
    "museum-caption-frame": ("ARCHIVE PLATE", "PLATE ", "CATALOG NOTE"),
    "wired-index-card": ("WIRED INDEX", "FIELD INDEX", "PROOF INDEX"),
    "editorial-hairline": ("EDITORIAL FOLIO", "PROOF", "EDITORIAL NOTE"),
}
PROOF_OBJECT_COMPONENTS = {
    "cover": {"hero_claim"},
    "context": {"context", "source_evidence", "source_process_flow", "source_concept_map"},
    "core_text": {"source_evidence", "comparison", "concept_map", "source_concept_map"},
    "mechanism": {"mechanism_loop", "process_flow", "source_process_flow", "concept_map"},
    "conflict": {"objection_response", "comparison", "concept_map", "source_concept_map"},
    "comparison": {"comparison", "source_evidence"},
    "evidence": {"source_evidence", "screenshot_annotation", "source_data_context"},
    "data": {"chart_with_takeaway", "source_data_context"},
    "chart": {"chart_with_takeaway", "source_data_context"},
    "quote": {"pull_quote", "closing_takeaway"},
    "closing": {"closing_takeaway", "pull_quote"},
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def load_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, dict):
        raw = plan.get("slides") or plan.get("pages") or []
    else:
        raw = plan
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def contract_slides(project: Path) -> list[dict[str, Any]]:
    payload = load_json_if_exists(project / "spec_lock.json")
    if not isinstance(payload, dict):
        return []
    contract = payload.get("layout_execution_contract")
    raw = contract.get("slides") if isinstance(contract, dict) else []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def spec_lock_payload(project: Path) -> dict[str, Any]:
    payload = load_json_if_exists(project / "spec_lock.json")
    return payload if isinstance(payload, dict) else {}


def max_run(values: list[str]) -> tuple[str, int]:
    best_value = ""
    best_len = 0
    current = ""
    current_len = 0
    for value in values:
        if value == current:
            current_len += 1
        else:
            current = value
            current_len = 1
        if current_len > best_len:
            best_value = current
            best_len = current_len
    return best_value, best_len


def extract_lxx(value: Any) -> set[str]:
    values = value if isinstance(value, list) else [value]
    out: set[str] = set()
    for item in values:
        text = str(item or "").upper().replace("/", " ")
        for token in text.split():
            token = token.strip(" ,;:()[]{}")
            if len(token) == 3 and token.startswith("L") and token[1:].isdigit():
                out.add(token)
    return out


def layout_program_stats(layout_program: list[Any], contract: list[dict[str, Any]], slide_count: int) -> dict[str, Any]:
    contract_by_slide: dict[int, dict[str, Any]] = {}
    for idx, item in enumerate(contract, start=1):
        try:
            slide_no = int(item.get("slide_no") or idx)
        except Exception:
            slide_no = idx
        contract_by_slide[slide_no] = item

    program_itls: set[str] = set()
    executed_itls: set[str] = set()
    program_layouts: set[str] = set()
    executed_layouts: set[str] = set()
    details: list[dict[str, Any]] = []
    matched_program_itls = 0
    matched_program_layouts = 0
    matched_program_slides = 0

    for item in contract:
        itl = str(item.get("image_text_pattern_id") or "")
        if itl:
            executed_itls.add(itl)
        executed_layouts.update(extract_lxx(item.get("layout_pattern_id")))

    for raw in layout_program:
        if not isinstance(raw, dict):
            continue
        try:
            slide_no = int(raw.get("slide_no") or 0)
        except Exception:
            slide_no = 0
        target = contract_by_slide.get(slide_no, {})
        recommended_itl = str(raw.get("recommended_itl") or "")
        if recommended_itl:
            program_itls.add(recommended_itl)
        candidate_layouts = extract_lxx(raw.get("layout_pattern_candidates"))
        program_layouts.update(candidate_layouts)

        executed_itl = str(target.get("image_text_pattern_id") or "")
        executed_layout = extract_lxx(target.get("layout_pattern_id"))
        executed_component = str(target.get("component_type") or "")
        art_direction = str(target.get("art_direction") or "")
        proof_object = str(raw.get("proof_object") or "").lower()
        acceptable_components = PROOF_OBJECT_COMPONENTS.get(proof_object, set())

        itl_match = bool(recommended_itl and (recommended_itl == executed_itl or recommended_itl.lower() in art_direction.lower()))
        layout_match = bool(candidate_layouts.intersection(executed_layout))
        component_match = bool(executed_component and (executed_component in acceptable_components or proof_object and proof_object in executed_component))
        if itl_match:
            matched_program_itls += 1
        if layout_match:
            matched_program_layouts += 1
        methods = []
        if itl_match:
            methods.append("itl")
        if layout_match:
            methods.append("layout")
        if component_match:
            methods.append("component")
        if methods:
            matched_program_slides += 1
        details.append(
            {
                "slide_no": slide_no,
                "proof_object": proof_object,
                "recommended_itl": recommended_itl,
                "candidate_layouts": sorted(candidate_layouts),
                "executed_itl": executed_itl,
                "executed_layouts": sorted(executed_layout),
                "executed_component": executed_component,
                "match_methods": methods,
            }
        )

    target = max(1, min(len(details), max(3, round(slide_count * 0.35)))) if details else 1
    return {
        "program_itls": sorted(program_itls),
        "executed_itls": sorted(executed_itls),
        "program_layouts": sorted(program_layouts),
        "executed_layouts": sorted(executed_layouts),
        "matched_program_itls": matched_program_itls,
        "matched_program_layouts": matched_program_layouts,
        "matched_program_slides": matched_program_slides,
        "program_target": target,
        "details": details,
    }


def visual_asset_stats(project: Path) -> dict[str, Any]:
    payload = load_json_if_exists(project / "visual_asset_manifest.json")
    items = payload.get("items") if isinstance(payload, dict) else []
    stats: dict[str, Any] = {
        "terminal_image_count": 0,
        "terminal_image_slides": 0,
        "source_like_count": 0,
        "source_like_slides": 0,
        "ai_terminal_count": 0,
        "procedural_fallback_count": 0,
    }
    image_slides: set[int] = set()
    source_slides: set[int] = set()
    if not isinstance(items, list):
        return stats
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status not in TERMINAL_STATUSES:
            continue
        rel = str(item.get("path") or "").strip()
        if not rel or not (project / rel).exists():
            continue
        via = str(item.get("acquire_via") or "").lower()
        stats["terminal_image_count"] += 1
        try:
            slide_no = int(item.get("slide_no") or 0)
        except Exception:
            slide_no = 0
        if slide_no > 0:
            image_slides.add(slide_no)
        if via in {"source", "web", "user"}:
            stats["source_like_count"] += 1
            if slide_no > 0:
                source_slides.add(slide_no)
        if via == "ai":
            stats["ai_terminal_count"] += 1
            if str(item.get("generator") or "") == "procedural-preview-fallback":
                stats["procedural_fallback_count"] += 1
    stats["terminal_image_slides"] = len(image_slides)
    stats["source_like_slides"] = len(source_slides)
    return stats


def proof_canvas_stats(
    project: Path,
    proof_language: str,
    render_material: str,
    contract: list[dict[str, Any]],
    slide_count: int,
) -> dict[str, Any]:
    svg_dir = project / "svg_output"
    svg_files = sorted(svg_dir.glob("*.svg")) if svg_dir.exists() else []
    eligible = [
        item for item in contract
        if str(item.get("component_type") or "") in PROOF_COMPONENTS
    ]
    expected = len(eligible)
    if not expected and slide_count:
        expected = min(3, slide_count)
    expected = max(1, expected) if slide_count else 0

    markers = PROOF_MARKERS_BY_MATERIAL.get(render_material, PROOF_MARKERS_BY_MATERIAL["editorial-paper"])
    proof_language_files: list[str] = []
    marker_files: list[str] = []
    group_files: list[str] = []
    unreadable = 0
    for svg in svg_files:
        try:
            body = svg.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            unreadable += 1
            continue
        visible_body = "\n".join(body.splitlines()[1:])
        if proof_language and proof_language in visible_body:
            proof_language_files.append(svg.name)
        if any(marker in visible_body for marker in markers):
            marker_files.append(svg.name)
        if "-proof" in visible_body:
            group_files.append(svg.name)
    proof_hits = len(set(proof_language_files))
    marker_hits = len(set(marker_files))
    group_hits = len(set(group_files))
    if not svg_files or not expected:
        score = 0
    else:
        score = pct(
            min(
                ratio(float(proof_hits), float(expected)),
                ratio(float(marker_hits), float(expected)),
                ratio(float(group_hits), max(1.0, float(round(slide_count * 0.5) or 1))),
            )
        )
    return {
        "svg_file_count": len(svg_files),
        "expected_proof_pages": expected,
        "proof_language_hits": proof_hits,
        "style_marker_hits": marker_hits,
        "proof_group_hits": group_hits,
        "markers": list(markers),
        "proof_language_examples": proof_language_files[:8],
        "style_marker_examples": marker_files[:8],
        "unreadable_svg_count": unreadable,
        "score": score,
    }


def style_canvas_stats(
    project: Path,
    component_language: str,
    render_material: str,
    slide_count: int,
) -> dict[str, Any]:
    svg_dir = project / "svg_output"
    svg_files = sorted(svg_dir.glob("*.svg")) if svg_dir.exists() else []
    markers = STYLE_MARKERS_BY_COMPONENT_LANGUAGE.get(
        component_language,
        STYLE_MARKERS_BY_COMPONENT_LANGUAGE["editorial-hairline"],
    )
    marker_files: list[str] = []
    material_files: list[str] = []
    title_group_files: list[str] = []
    background_group_files: list[str] = []
    unreadable = 0
    for svg in svg_files:
        try:
            body = svg.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            unreadable += 1
            continue
        visible_body = "\n".join(body.splitlines()[1:])
        if any(marker in visible_body for marker in markers):
            marker_files.append(svg.name)
        if render_material and (render_material in visible_body or any(marker in visible_body for marker in markers)):
            material_files.append(svg.name)
        if "-title" in visible_body:
            title_group_files.append(svg.name)
        if "-background" in visible_body:
            background_group_files.append(svg.name)

    expected = max(1, round(slide_count * 0.5)) if slide_count else 0
    marker_hits = len(set(marker_files))
    material_hits = len(set(material_files))
    title_group_hits = len(set(title_group_files))
    background_group_hits = len(set(background_group_files))
    if not svg_files or not expected:
        score = 0
    else:
        score = pct(
            min(
                ratio(float(marker_hits), float(expected)),
                ratio(float(material_hits), float(expected)),
                ratio(float(title_group_hits), max(1.0, float(round(slide_count * 0.7) or 1))),
                ratio(float(background_group_hits), max(1.0, float(slide_count))),
            )
        )
    return {
        "svg_file_count": len(svg_files),
        "expected_style_pages": expected,
        "component_language": component_language,
        "render_material": render_material,
        "style_marker_hits": marker_hits,
        "material_marker_hits": material_hits,
        "title_group_hits": title_group_hits,
        "background_group_hits": background_group_hits,
        "markers": list(markers),
        "style_marker_examples": marker_files[:8],
        "material_marker_examples": material_files[:8],
        "unreadable_svg_count": unreadable,
        "score": score,
    }


def rhythm_summary(project: Path) -> dict[str, Any]:
    payload = load_json_if_exists(project / "reports" / "visual_rhythm_report.json")
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    return summary if isinstance(summary, dict) else {}


def style_direction(project: Path) -> dict[str, Any]:
    payload = load_json_if_exists(project / "style_direction.json")
    return payload if isinstance(payload, dict) else {}


def score_project(project: Path, min_score: int) -> dict[str, Any]:
    project = project.resolve()
    slides = iter_slides(load_json_if_exists(project / "slide_plan.json") or [])
    slide_count = len(slides)
    direction = style_direction(project)
    selected = direction.get("selected_style") if isinstance(direction.get("selected_style"), dict) else {}
    style_contract = direction.get("style_contract") if isinstance(direction.get("style_contract"), dict) else {}
    targets = direction.get("density_targets") if isinstance(direction.get("density_targets"), dict) else {}
    layout_program = direction.get("layout_program") if isinstance(direction.get("layout_program"), list) else []
    spec_lock = spec_lock_payload(project)
    render_style = spec_lock.get("render_style") if isinstance(spec_lock.get("render_style"), dict) else {}
    contract = contract_slides(project)
    rhythm = rhythm_summary(project)
    assets = visual_asset_stats(project)

    target_visual_pages = int(targets.get("target_visual_pages") or max(1, round(slide_count * 0.5)))
    target_source_pages = int(targets.get("target_source_evidence_pages") or (1 if slide_count >= 6 else 0))
    max_consecutive = int(targets.get("max_consecutive_same_layout") or 2)

    components = [str(item.get("component_type") or "") for item in contract]
    art_directions = [str(item.get("art_direction") or "") for item in contract]
    rhythms = [str(item.get("rhythm") or "") for item in contract]
    itl_ids = [str(item.get("image_text_pattern_id") or "") for item in contract]
    rich_count = len({item for item in components if item in RICH_COMPONENTS})
    non_generic_count = sum(1 for item in components if item not in GENERIC_COMPONENTS)
    repeated_component, repeated_component_len = max_run(components)
    repeated_art, repeated_art_len = max_run(art_directions)

    program_stats = layout_program_stats(layout_program, contract, slide_count)

    contract_fields = [
        bool(selected.get("id")),
        bool(style_contract.get("palette")),
        bool(style_contract.get("typography")),
        bool(style_contract.get("media_policy")),
        bool(style_contract.get("layout_rules")),
        bool(targets),
    ]
    selected_id = str(selected.get("id") or "")
    render_style_id = str(render_style.get("style_id") or "")
    render_material = str(render_style.get("material") or "")
    component_language = str(render_style.get("component_language") or "")
    proof_language = str(render_style.get("proof_language") or "")
    style_canvas = style_canvas_stats(project, component_language, render_material, slide_count)
    proof_canvas = proof_canvas_stats(project, proof_language, render_material, contract, slide_count)
    render_token_fields = [
        bool(render_style_id),
        bool(render_material),
        bool(component_language),
        bool(proof_language),
        bool(render_style.get("palette_behavior")),
        bool(render_style_id and (render_style_id == selected_id or selected_id in render_style_id or render_style_id in selected_id)),
    ]
    contract_score = pct(sum(1 for item in contract_fields if item) / len(contract_fields))
    render_token_score = pct(sum(1 for item in render_token_fields if item) / len(render_token_fields))
    style_canvas_score = int(style_canvas.get("score") or 0)
    proof_canvas_score = int(proof_canvas.get("score") or 0)
    layout_program_score = pct(
        min(
            ratio(float(len(layout_program)), max(1.0, float(slide_count))),
            ratio(float(program_stats["matched_program_slides"]), float(program_stats["program_target"])),
        )
    )
    component_score = pct(
        min(
            ratio(float(non_generic_count), max(1.0, float(slide_count) * 0.72)),
            ratio(float(rich_count), max(2.0, min(5.0, float(slide_count) * 0.45))),
        )
    )
    density_score = pct(
        min(
            ratio(float(assets["terminal_image_slides"]), max(1.0, float(target_visual_pages))),
            ratio(float(assets["source_like_slides"]), max(1.0, float(target_source_pages))) if target_source_pages else 1.0,
        )
    )
    rhythm_score = pct(
        min(
            ratio(float(len({item for item in art_directions if item})), max(3.0, min(float(slide_count), float(round(slide_count * 0.55) or 1)))),
            ratio(float(len({item for item in rhythms if item})), 3.0 if slide_count >= 8 else 2.0),
        )
    )
    repetition_penalty = 0
    if repeated_component and repeated_component_len > max_consecutive + 1:
        repetition_penalty += min(35, (repeated_component_len - max_consecutive) * 10)
    if repeated_art and repeated_art_len > max_consecutive + 1:
        repetition_penalty += min(35, (repeated_art_len - max_consecutive) * 10)
    if assets["procedural_fallback_count"]:
        repetition_penalty += 15

    categories = [
        {
            "id": "style_contract",
            "weight": 16,
            "score": contract_score,
            "evidence": f"selected={selected.get('id') or ''}; contract fields {sum(1 for item in contract_fields if item)}/{len(contract_fields)}",
        },
        {
            "id": "render_style_token",
            "weight": 10,
            "score": render_token_score,
            "evidence": f"render_style={render_style_id}; material={render_material}; component_language={component_language}; proof_language={proof_language}; token fields {sum(1 for item in render_token_fields if item)}/{len(render_token_fields)}",
        },
        {
            "id": "style_canvas_execution",
            "weight": 12,
            "score": style_canvas_score,
            "evidence": (
                f"style marker hits {style_canvas['style_marker_hits']}/{style_canvas['expected_style_pages']}; "
                f"material hits {style_canvas['material_marker_hits']}/{style_canvas['expected_style_pages']}; "
                f"title groups {style_canvas['title_group_hits']}/{slide_count}; "
                f"background groups {style_canvas['background_group_hits']}/{slide_count}"
            ),
        },
        {
            "id": "proof_canvas_execution",
            "weight": 12,
            "score": proof_canvas_score,
            "evidence": (
                f"proof_language hits {proof_canvas['proof_language_hits']}/{proof_canvas['expected_proof_pages']}; "
                f"style marker hits {proof_canvas['style_marker_hits']}/{proof_canvas['expected_proof_pages']}; "
                f"proof groups {proof_canvas['proof_group_hits']}/{slide_count}"
            ),
        },
        {
            "id": "layout_program_execution",
            "weight": 20,
            "score": layout_program_score,
            "evidence": (
                f"layout program {len(layout_program)}/{slide_count}; "
                f"matched slides {program_stats['matched_program_slides']}/{program_stats['program_target']}; "
                f"matched ITL {program_stats['matched_program_itls']}; "
                f"matched Lxx {program_stats['matched_program_layouts']}"
            ),
        },
        {
            "id": "component_specificity",
            "weight": 22,
            "score": component_score,
            "evidence": f"non-generic components {non_generic_count}/{slide_count}; rich families {rich_count}",
        },
        {
            "id": "visual_density_alignment",
            "weight": 20,
            "score": density_score,
            "evidence": (
                f"terminal visual slides {assets['terminal_image_slides']}/{target_visual_pages}; "
                f"source-like visual slides {assets['source_like_slides']}/{target_source_pages}"
            ),
        },
        {
            "id": "art_direction_rhythm",
            "weight": 14,
            "score": rhythm_score,
            "evidence": (
                f"unique art directions {len({item for item in art_directions if item})}; "
                f"unique rhythms {len({item for item in rhythms if item})}; "
                f"visual rhythm SVG images {rhythm.get('svg_image_slides', 0)}"
            ),
        },
        {
            "id": "repetition_control",
            "weight": 8,
            "score": max(0, 100 - repetition_penalty),
            "evidence": (
                f"max component run {repeated_component_len} ({repeated_component}); "
                f"max art run {repeated_art_len} ({repeated_art}); "
                f"procedural fallbacks {assets['procedural_fallback_count']}"
            ),
        },
    ]
    total = int(round(sum(item["weight"] * item["score"] for item in categories) / sum(item["weight"] for item in categories)))

    failures: list[str] = []
    warnings: list[str] = []
    if total < min_score:
        failures.append(f"style execution score {total} below target {min_score}")
    if not selected.get("id"):
        failures.append("style_direction.json is missing a selected style")
    if selected_id and not render_style_id:
        failures.append("spec_lock.json is missing render_style evidence from the SVG renderer")
    if selected_id and render_style_id and not (render_style_id == selected_id or selected_id in render_style_id or render_style_id in selected_id):
        warnings.append(f"render style token `{render_style_id}` does not match selected style `{selected_id}`")
    if selected_id and slide_count and not proof_canvas["svg_file_count"]:
        failures.append("SVG output is missing, so style/proof canvas execution cannot be verified")
    if selected_id and component_language and style_canvas_score < 60:
        failures.append(
            f"SVG style canvas execution is weak: style marker hits {style_canvas['style_marker_hits']}/"
            f"{style_canvas['expected_style_pages']}, material hits {style_canvas['material_marker_hits']}/"
            f"{style_canvas['expected_style_pages']}"
        )
    if selected_id and proof_language and proof_canvas_score < 60:
        failures.append(
            f"SVG proof canvas execution is weak: proof_language hits {proof_canvas['proof_language_hits']}/"
            f"{proof_canvas['expected_proof_pages']}, marker hits {proof_canvas['style_marker_hits']}/"
            f"{proof_canvas['expected_proof_pages']}"
        )
    if slide_count and len(contract) < slide_count:
        failures.append(f"spec_lock layout contract covers {len(contract)}/{slide_count} slide(s)")
    if layout_program_score < 70:
        warnings.append("selected style layout program is weakly reflected in executed ITL patterns")
    if component_score < 70:
        warnings.append("too many slides still look like generic content components")
    if density_score < 70:
        warnings.append("selected style visual/source density targets are not met")
    if repeated_component_len > max_consecutive + 1:
        warnings.append(f"component type repeats {repeated_component_len} slides in a row: {repeated_component}")
    if repeated_art_len > max_consecutive + 1:
        warnings.append(f"art direction repeats {repeated_art_len} slides in a row: {repeated_art}")

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/style_execution_audit.py",
        "ok": not failures,
        "score": total,
        "target_score": min_score,
        "project": str(project),
        "slide_count": slide_count,
        "selected_style": selected,
        "categories": categories,
        "stats": {
            "target_visual_pages": target_visual_pages,
            "target_source_evidence_pages": target_source_pages,
            "max_consecutive_same_layout": max_consecutive,
            "layout_program_count": len(layout_program),
            "render_style": render_style,
            "program_itls": program_stats["program_itls"],
            "executed_itls": program_stats["executed_itls"],
            "program_layouts": program_stats["program_layouts"],
            "executed_layouts": program_stats["executed_layouts"],
            "layout_program_matches": program_stats["details"],
            "component_types": components,
            "art_directions": art_directions,
            "rhythms": rhythms,
            "asset_stats": assets,
            "visual_rhythm_summary": rhythm,
            "style_canvas": style_canvas,
            "proof_canvas": proof_canvas,
        },
        "failures": failures,
        "warnings": warnings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    style = report.get("selected_style") if isinstance(report.get("selected_style"), dict) else {}
    lines = [
        "# Style Execution Audit",
        "",
        f"- Score: `{report['score']}` / 100",
        f"- Target: `{report['target_score']}`",
        f"- OK: `{str(report['ok']).lower()}`",
        f"- Selected style: `{style.get('label') or ''}` (`{style.get('id') or ''}`)",
        f"- Project: `{report['project']}`",
        "",
        "## Categories",
        "",
    ]
    for item in report.get("categories", []):
        lines.append(f"- `{item['id']}`: {item['score']} / 100, weight {item['weight']} - {item['evidence']}")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Prepared/generated qiaomu-ppt project directory.")
    parser.add_argument("--output", type=Path, help="JSON output path. Default: <project>/reports/style_execution_audit.json")
    parser.add_argument("--markdown", type=Path, help="Markdown output path. Default: <project>/reports/style_execution_audit.md")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum score for ok=true.")
    parser.add_argument("--enforce", action="store_true", help="Exit non-zero when audit fails.")
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output or project / "reports" / "style_execution_audit.json"
    markdown = args.markdown or project / "reports" / "style_execution_audit.md"
    report = score_project(project, args.min_score)
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.enforce and not report["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
