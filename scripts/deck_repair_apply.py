#!/usr/bin/env python3
"""Apply safe deterministic repair-plan actions to qiaomu-ppt project contracts.

This script does not fabricate sources, images, or final visuals. It repairs
the model contracts that drive later SVG/PPTX generation: slide layout IDs,
component types, page rhythm, image-text patterns, visual contract policies, and
pre-render spec locks.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


W = 1280
H = 720
ALLOWED_RHYTHMS = {"anchor", "dense", "breathing"}
LAYOUT_TO_COMPONENT = {
    "L01": "hero_claim",
    "L08": "comparison",
    "L13": "process_flow",
    "L18": "mechanism_loop",
    "L20": "chart_with_takeaway",
    "L24": "concept_map",
    "L31": "objection_response",
    "L34": "pull_quote",
    "L35": "closing_takeaway",
}
LAYOUT_TO_ITL = {
    "L01": "ITL03",
    "L08": "ITL13",
    "L13": "ITL16",
    "L18": "ITL17",
    "L20": "ITL20",
    "L24": "ITL17",
    "L31": "ITL12",
    "L34": "ITL11",
    "L35": "ITL11",
}
LONG_DECK_LAYOUT_SEQUENCE = ["L01", "L08", "L13", "L24", "L20", "L18", "L31", "L34", "L08", "L13", "L20", "L35"]
SHORT_DECK_LAYOUT_SEQUENCE = ["L01", "L08", "L13", "L24", "L20", "L35"]
BACKGROUND_ROLES = [
    "cover_atmosphere",
    "light_evidence",
    "diagram_focus",
    "dark_evidence",
    "quote_breathing",
    "source_spread",
    "chart_focus",
    "closing_atmosphere",
]
DEFAULT_PALETTES = [
    ["#111827", "#F4EFE4", "#C8472C"],
    ["#111827", "#E7DDCA", "#2F66D0"],
    ["#0B1628", "#FFFFFF", "#D8A642"],
    ["#111827", "#F4EFE4", "#2D7A65"],
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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, list):
        return [item for item in plan if isinstance(item, dict)]
    if isinstance(plan, dict):
        for key in ("slides", "slide_plan", "pages"):
            value = plan.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def set_slides(plan: Any, slides: list[dict[str, Any]]) -> Any:
    if isinstance(plan, list):
        return slides
    if isinstance(plan, dict):
        for key in ("slides", "slide_plan", "pages"):
            if isinstance(plan.get(key), list):
                plan[key] = slides
                return plan
        plan["slides"] = slides
        return plan
    return {"slides": slides}


def title_of(slide: dict[str, Any]) -> str:
    return str(slide.get("claim_title") or slide.get("title") or "").strip()


def concise_title(value: str, *, max_chars: int = 34) -> str:
    title = re.sub(r"\s+", " ", value).strip().rstrip(".。…")
    if len(title) <= max_chars and "..." not in title:
        return title
    for separator in ("：", ":", "；", ";", "，", ",", "。", "."):
        if separator in title:
            head = title.split(separator, 1)[0].strip()
            if 8 <= len(head) <= max_chars:
                return head
    clauses = re.split(r"[，,。；;：:\s]+", title)
    stitched = ""
    for clause in clauses:
        if not clause:
            continue
        candidate = clause if not stitched else stitched + "，" + clause
        if len(candidate) > max_chars:
            break
        stitched = candidate
    if len(stitched) >= 8:
        return stitched
    return title[: max_chars - 3].rstrip("，,。；;：: ") + "..."


def text_blob(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "claim_title",
        "title",
        "intent",
        "visual_role",
        "proof_object",
        "concrete_anchor",
        "source_anchor",
        "media_need",
        "layout_pattern",
    ):
        value = slide.get(key)
        if value:
            parts.append(str(value))
    for key in ("content_points", "points", "bullets", "content"):
        value = slide.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts).lower()


def existing_layout(slide: dict[str, Any]) -> str:
    value = str(slide.get("layout_pattern_id") or slide.get("layout_pattern") or "").upper()
    match = re.search(r"\bL\d{2}\b", value)
    return match.group(0) if match else ""


def infer_layout(slide: dict[str, Any], idx: int, total: int) -> str:
    found = existing_layout(slide)
    if found:
        return found
    blob = text_blob(slide)
    if idx == 1:
        return "L01"
    if idx == total:
        return "L35"
    if any(token in blob for token in ("before", "after", "前后", "对比", "比较", "versus", "vs", "差异")):
        return "L08"
    if any(token in blob for token in ("流程", "步骤", "process", "step", "路径", "阶段")):
        return "L13"
    if any(token in blob for token in ("机制", "循环", "飞轮", "loop", "mechanism", "因果")):
        return "L18"
    if any(token in blob for token in ("数据", "图表", "chart", "趋势", "增长", "%", "指标", "表格")):
        return "L20"
    if any(token in blob for token in ("地图", "框架", "结构", "关系", "网络", "概念")):
        return "L24"
    if any(token in blob for token in ("反对", "质疑", "回应", "objection", "risk", "风险")):
        return "L31"
    if any(token in blob for token in ("引用", "quote", "金句", "原文", "摘录")):
        return "L34"
    sequence = LONG_DECK_LAYOUT_SEQUENCE if total > 8 else SHORT_DECK_LAYOUT_SEQUENCE
    return sequence[(idx - 1) % len(sequence)]


def infer_rhythm(slide: dict[str, Any], idx: int, total: int, layout_id: str) -> str:
    raw = str(slide.get("rhythm") or "").strip().lower().replace("-", "_")
    if raw in ALLOWED_RHYTHMS:
        return raw
    blob = text_blob(slide)
    if idx in {1, total} or layout_id in {"L01", "L35"}:
        return "anchor"
    if layout_id in {"L34"} or any(token in blob for token in ("转折", "pause", "quote", "引用", "总结", "synthesis")):
        return "breathing"
    return "dense"


def coordinate_slots(layout_id: str, idx: int, total: int) -> list[dict[str, int | str]]:
    if layout_id in {"L13", "L18", "L24"}:
        return [
            {"slot_id": "title_claim", "x": 58, "y": 48, "w": 1120, "h": 112},
            {"slot_id": "proof_object", "x": 80, "y": 150, "w": 1120, "h": 430},
            {"slot_id": "takeaway", "x": 86, "y": 584, "w": 1080, "h": 64},
        ]
    if layout_id in {"L20", "L31"}:
        return [
            {"slot_id": "title_claim", "x": 58, "y": 48, "w": 1120, "h": 112},
            {"slot_id": "proof_object", "x": 80, "y": 160, "w": 720, "h": 420},
            {"slot_id": "takeaway", "x": 820, "y": 160, "w": 370, "h": 420},
        ]
    if layout_id in {"L01", "L35"} or idx in {1, total}:
        return [
            {"slot_id": "title_claim", "x": 58, "y": 70, "w": 690, "h": 190},
            {"slot_id": "proof_object", "x": 64, "y": 250, "w": 700, "h": 350},
            {"slot_id": "media_or_takeaway", "x": 720, "y": 0, "w": 560, "h": 720},
        ]
    return [
        {"slot_id": "title_claim", "x": 58, "y": 48, "w": 1120, "h": 112},
        {"slot_id": "proof_object", "x": 72, "y": 160, "w": 640, "h": 430},
        {"slot_id": "media_or_takeaway", "x": 720, "y": 104, "w": 500, "h": 500},
    ]


def group_ids(idx: int) -> list[str]:
    return [
        f"slide-{idx:02d}-background",
        f"slide-{idx:02d}-media",
        f"slide-{idx:02d}-title",
        f"slide-{idx:02d}-proof",
        f"slide-{idx:02d}-body",
        f"slide-{idx:02d}-footer",
    ]


def source_cards(project: Path) -> list[dict[str, Any]]:
    payload = load_json(project / "sources" / "source_cards.json", {})
    cards = payload.get("cards") if isinstance(payload, dict) else payload
    return [item for item in cards if isinstance(item, dict)] if isinstance(cards, list) else []


def card_score(slide: dict[str, Any], card: dict[str, Any]) -> int:
    slide_words = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", text_blob(slide)))
    text = " ".join(str(card.get(key) or "") for key in ("claim", "evidence", "quote", "title", "source_title"))
    card_words = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", text.lower()))
    return len(slide_words.intersection(card_words))


def repair_slide_plan(project: Path, *, apply_source_ids: bool) -> tuple[list[str], dict[str, Any]]:
    plan_path = project / "slide_plan.json"
    plan = load_json(plan_path)
    if plan is None:
        return [f"missing {plan_path}"], {}
    slides = iter_slides(plan)
    if not slides:
        return ["slide_plan.json contains no slides"], {}
    changes: list[str] = []
    cards = source_cards(project) if apply_source_ids else []
    card_ids = [str(card.get("id") or "").strip() for card in cards if str(card.get("id") or "").strip()]
    total = len(slides)
    used_layouts: set[str] = set()
    rhythms: list[str] = []
    for idx, slide in enumerate(slides, start=1):
        claim_title = title_of(slide)
        shortened = concise_title(claim_title) if claim_title else ""
        if shortened and shortened != claim_title:
            slide.setdefault("full_claim_title", claim_title)
            slide["claim_title"] = shortened
            slide["title"] = shortened
            changes.append(f"slide {idx}: claim_title shortened for visible title fit")
            claim_title = shortened
        if claim_title and not slide.get("title"):
            slide["title"] = claim_title
            changes.append(f"slide {idx}: title mirrored from claim_title")
        if not slide.get("slide_no"):
            slide["slide_no"] = idx
            changes.append(f"slide {idx}: slide_no filled")
        if not slide.get("intent"):
            if idx == 1:
                slide["intent"] = "open the topic with a clear audience-facing claim"
            elif idx == total:
                slide["intent"] = "close with the deck's most useful takeaway"
            else:
                slide["intent"] = "turn one source-backed point into a visible proof step"
            changes.append(f"slide {idx}: intent filled")
        if not slide.get("concrete_anchor"):
            slide["concrete_anchor"] = str(slide.get("source_anchor") or slide.get("proof_object") or claim_title or f"slide {idx} claim")
            changes.append(f"slide {idx}: concrete_anchor filled")
        if not slide.get("visual_role"):
            slide["visual_role"] = str(slide.get("proof_object") or "claim_proof")
            changes.append(f"slide {idx}: visual_role filled")
        if not slide.get("speaker_note_goal"):
            slide["speaker_note_goal"] = "explain the claim with source-backed detail, caveats, and transition to the next slide"
            changes.append(f"slide {idx}: speaker_note_goal filled")
        if not slide.get("qa_risk"):
            slide["qa_risk"] = "check source grounding, visible title fit, text overflow, and layout repetition before final export"
            changes.append(f"slide {idx}: qa_risk filled")
        layout_id = infer_layout(slide, idx, total)
        if slide.get("layout_pattern_id") != layout_id:
            slide["layout_pattern_id"] = layout_id
            changes.append(f"slide {idx}: layout_pattern_id -> {layout_id}")
        if not slide.get("layout_pattern"):
            slide["layout_pattern"] = layout_id
        component = LAYOUT_TO_COMPONENT.get(layout_id, "evidence_layout")
        component_plan = slide.get("component_plan") if isinstance(slide.get("component_plan"), dict) else {}
        if component_plan.get("component_type") != component:
            component_plan["component_type"] = component
            slide["component_plan"] = component_plan
            changes.append(f"slide {idx}: component_type -> {component}")
        if not slide.get("proof_object"):
            slide["proof_object"] = str(slide.get("visual_role") or component).strip() or component
            changes.append(f"slide {idx}: proof_object filled")
        rhythm = infer_rhythm(slide, idx, total, layout_id)
        if slide.get("rhythm") != rhythm:
            slide["rhythm"] = rhythm
            changes.append(f"slide {idx}: rhythm -> {rhythm}")
        itl = LAYOUT_TO_ITL.get(layout_id, "")
        if itl and slide.get("image_text_pattern_id") != itl:
            slide["image_text_pattern_id"] = itl
            changes.append(f"slide {idx}: image_text_pattern_id -> {itl}")
        if not slide.get("reading_path"):
            slide["reading_path"] = "title_to_proof_to_takeaway"
        if not slide.get("background_id"):
            slide["background_id"] = BACKGROUND_ROLES[(idx - 1) % len(BACKGROUND_ROLES)]
        if apply_source_ids and cards and not slide.get("source_card_ids") and idx not in {1, total}:
            best = max(cards, key=lambda card: card_score(slide, card))
            best_id = str(best.get("id") or "").strip()
            if best_id:
                slide["source_card_ids"] = [best_id]
                slide.setdefault("source_anchor", str(best.get("claim") or best.get("evidence") or "")[:160])
                changes.append(f"slide {idx}: source_card_ids -> {best_id}")
        used_layouts.add(layout_id)
        rhythms.append(rhythm)
    layout_ids = [str(slide.get("layout_pattern_id") or "") for slide in slides]
    if total > 8 and (len(set(layout_ids)) < 5 or longest_run(layout_ids) > 2):
        sequence = LONG_DECK_LAYOUT_SEQUENCE
        changes.append("slide_plan.json: repaired repetitive layout rhythm with mixed Lxx sequence")
        used_layouts = set()
        rhythms = []
        for idx, slide in enumerate(slides, start=1):
            layout_id = "L01" if idx == 1 else ("L35" if idx == total else sequence[(idx - 1) % len(sequence)])
            if slide.get("layout_pattern_id") != layout_id:
                slide["layout_pattern_id"] = layout_id
                changes.append(f"slide {idx}: layout_pattern_id rhythm repair -> {layout_id}")
            slide["layout_pattern"] = layout_id
            component = LAYOUT_TO_COMPONENT.get(layout_id, "evidence_layout")
            component_plan = slide.get("component_plan") if isinstance(slide.get("component_plan"), dict) else {}
            if component_plan.get("component_type") != component:
                component_plan["component_type"] = component
                slide["component_plan"] = component_plan
                changes.append(f"slide {idx}: component_type rhythm repair -> {component}")
            rhythm = infer_rhythm(slide, idx, total, layout_id)
            if slide.get("rhythm") != rhythm:
                slide["rhythm"] = rhythm
                changes.append(f"slide {idx}: rhythm rhythm repair -> {rhythm}")
            itl = LAYOUT_TO_ITL.get(layout_id, "")
            if itl and slide.get("image_text_pattern_id") != itl:
                slide["image_text_pattern_id"] = itl
                changes.append(f"slide {idx}: image_text_pattern_id rhythm repair -> {itl}")
            used_layouts.add(layout_id)
            rhythms.append(rhythm)
    set_slides(plan, slides)
    write_json(plan_path, plan)
    return changes, {"slide_count": total, "layout_count": len(used_layouts), "rhythms": rhythms, "source_card_count": len(card_ids)}


def slide_roles_from_plan(project: Path) -> list[dict[str, Any]]:
    plan = load_json(project / "slide_plan.json", {})
    slides = iter_slides(plan)
    roles: list[dict[str, Any]] = []
    total = len(slides)
    for idx, slide in enumerate(slides, start=1):
        layout_id = infer_layout(slide, idx, total)
        background_role = str(slide.get("background_id") or BACKGROUND_ROLES[(idx - 1) % len(BACKGROUND_ROLES)])
        roles.append(
            {
                "slide_no": idx,
                "layout_role": LAYOUT_TO_COMPONENT.get(layout_id, "evidence_layout"),
                "reading_path": str(slide.get("reading_path") or "title_to_proof_to_takeaway"),
                "background_role": background_role,
                "background_asset": f"{background_role}-{idx:02d}",
                "dominant_object": str(slide.get("proof_object") or slide.get("visual_role") or title_of(slide) or "claim_proof"),
            }
        )
    return roles


def slides_from_project(project: Path) -> list[dict[str, Any]]:
    return iter_slides(load_json(project / "slide_plan.json", {}))


def slide_palette_slots_from_plan(project: Path) -> list[dict[str, Any]]:
    slides = slides_from_project(project)
    return [
        {"slide_no": idx, "active_colors": DEFAULT_PALETTES[(idx - 1) % len(DEFAULT_PALETTES)]}
        for idx, _slide in enumerate(slides, start=1)
    ]


def background_paths_from_plan(project: Path) -> dict[str, str]:
    slides = slides_from_project(project)
    return {f"bg-{idx:02d}.svg": f"assets/backgrounds/bg-{idx:02d}.svg" for idx, _slide in enumerate(slides, start=1)}


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def longest_run(values: list[str]) -> int:
    best = 0
    current = 0
    previous = None
    for value in values:
        if value and value == previous:
            current += 1
        else:
            previous = value
            current = 1 if value else 0
        best = max(best, current)
    return best


def build_contract_slide(slide: dict[str, Any], idx: int, total: int) -> dict[str, Any]:
    layout_id = infer_layout(slide, idx, total)
    return {
        "slide_no": idx,
        "slide_id": f"slide-{idx:02d}",
        "rhythm": infer_rhythm(slide, idx, total, layout_id),
        "proof_object": str(slide.get("proof_object") or slide.get("visual_role") or "claim_proof"),
        "layout_pattern_id": layout_id,
        "component_type": LAYOUT_TO_COMPONENT.get(layout_id, "evidence_layout"),
        "image_text_pattern_id": str(slide.get("image_text_pattern_id") or LAYOUT_TO_ITL.get(layout_id, "")),
        "reading_path": str(slide.get("reading_path") or "title_to_proof_to_takeaway"),
        "coordinate_slots": coordinate_slots(layout_id, idx, total),
        "group_ids": group_ids(idx),
    }


def repair_spec_lock(project: Path) -> list[str]:
    plan = load_json(project / "slide_plan.json", {})
    slides = iter_slides(plan)
    if not slides:
        return []
    spec_path = project / "spec_lock.json"
    spec = load_json(spec_path, {})
    if not isinstance(spec, dict):
        spec = {}
    spec.setdefault("schema_version", "1.0.0")
    spec.setdefault("stage", {"width": W, "height": H, "unit": "px"})
    spec.setdefault("typography", {})
    spec["typography"].setdefault(
        "title_line_height_policy",
        "CJK multi-line page titles use 1.14-1.30 leading; cover/closing titles may tighten only after preview review.",
    )
    spec["layout_execution_contract"] = {
        "coordinate_policy": "absolute 1280x720 SVG coordinates with fixed safe margins",
        "text_fit_policy": "manual line breaks, fit checks, split slides, or shrink text before export; foreignObject is forbidden",
        "group_policy": "top-level semantic SVG groups for background, media, title, proof, body, and footer; group_ids must match rendered SVG.",
        "slides": [build_contract_slide(slide, idx, len(slides)) for idx, slide in enumerate(slides, start=1)],
    }
    write_json(spec_path, spec)
    return ["spec_lock.json layout_execution_contract refreshed"]


def repair_visual_contract(project: Path) -> list[str]:
    path = project / "visual_contract.json"
    contract = load_json(path, {})
    if not isinstance(contract, dict):
        contract = {}
    changes: list[str] = []
    defaults = {
        "visual_noise_budget": "quiet",
        "background_roles": BACKGROUND_ROLES,
        "background_asset_policy": {
            "mode": "procedural_svg_backgrounds_plus_source_or_generated_atmosphere",
            "decorative_line_policy": "forbid non-functional decorative lines; lines must be axes, connectors, separators, or chart rules",
            "atmosphere_only_policy": "generated backgrounds are atmosphere-only and must not contain slide layout objects",
            "editable_foreground_policy": "all boxes, text blocks, charts, diagrams, callouts, and image slots stay as editable foreground objects",
            "procedural_fallback_policy": "use procedural SVG, CSS, or Canvas texture fields when image generation or web assets are unavailable",
            "forbidden_generated_objects": FORBIDDEN_BACKGROUND_OBJECTS,
            "procedural_background_paths": background_paths_from_plan(project),
        },
        "background_rhythm": {
            "roles": BACKGROUND_ROLES,
            "max_consecutive_same_role": 2,
            "no_exact_background_asset_on_adjacent_slides": True,
            "thumbnail_grid_variation_required": True,
        },
        "color_budget": {
            "max_active_colors_per_slide": 3,
            "accent_policy": "neutral base + readable text + one accent; source image colors excluded",
        },
        "image_text_layout_policy": {
            "pattern_required_for_media_slides": True,
            "allowed_pattern_prefix": "ITL",
            "text_over_image_requires": ["copy_space", "scrim", "gradient", "text_panel", "local_blur"],
            "font_floor_pt": 14,
        },
        "layout_quality_policy": {
            "composition_formula": "one dominant claim, one proof object, one implication zone",
            "decorative_filler_policy": "forbid decorative filler that does not support the reading path",
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
        "evidence_layout_policy": {
            "allowed_treatments": ["full_chart", "chart_with_takeaway", "chart_crop", "chart_then_takeaway"],
            "max_consecutive_same_composition": 2,
            "right_side_policy": "one clear takeaway or one number on the right side, never competing claims",
            "rail_policy": "forbid generic rails outside timeline or process slides",
        },
        "dense_chart_policy": "crop, split, zoom, or move detail to speaker notes when a chart or diagram becomes unreadable",
        "layout_repair_policy": {
            "source": "qiaomu-ppt/scripts/deck_repair_apply.py",
            "repair_contracts_before_svg_render": True,
            "repeated_card_grid_is_failure": True,
            "layout_pattern_ids_required": True,
        },
    }
    for key, value in defaults.items():
        if key not in contract:
            contract[key] = value
            changes.append(f"visual_contract.json: added {key}")
    generated_palette_slots = slide_palette_slots_from_plan(project)
    existing_palette_slots = contract.get("slide_palette_slots")
    if generated_palette_slots and (
        not isinstance(existing_palette_slots, list) or len(existing_palette_slots) < len(generated_palette_slots)
    ):
        contract["slide_palette_slots"] = generated_palette_slots
        changes.append("visual_contract.json: refreshed slide_palette_slots from slide_plan")
    generated_slide_roles = slide_roles_from_plan(project)
    existing_slide_roles = contract.get("slide_roles")
    if generated_slide_roles and (
        not isinstance(existing_slide_roles, list) or len(existing_slide_roles) < len(generated_slide_roles)
    ):
        contract["slide_roles"] = generated_slide_roles
        changes.append("visual_contract.json: refreshed slide_roles from slide_plan")
    background_policy = contract.get("background_asset_policy")
    if isinstance(background_policy, dict):
        policy_defaults = defaults["background_asset_policy"]
        for key, value in policy_defaults.items():
            current = background_policy.get(key)
            if not current or (key == "forbidden_generated_objects" and not isinstance(current, list)):
                background_policy[key] = value
                changes.append(f"visual_contract.json: filled background_asset_policy.{key}")
        current_forbidden = background_policy.get("forbidden_generated_objects")
        if isinstance(current_forbidden, list):
            normalized = {str(item).strip().lower() for item in current_forbidden if str(item).strip()}
            missing = [item for item in FORBIDDEN_BACKGROUND_OBJECTS if item not in normalized]
            if missing:
                background_policy["forbidden_generated_objects"] = current_forbidden + missing
                changes.append("visual_contract.json: completed background_asset_policy.forbidden_generated_objects")
    policy_repairs = {
        "layout_quality_policy": {
            "composition_formula": "one dominant claim, one proof object, one implication zone",
            "decorative_filler_policy": "forbid decorative filler that does not support the reading path",
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
        "evidence_layout_policy": {
            "allowed_treatments": ["full_chart", "chart_with_takeaway", "chart_crop", "chart_then_takeaway"],
            "max_consecutive_same_composition": 2,
            "right_side_policy": "one clear takeaway or one number on the right side, never competing claims",
            "rail_policy": "forbid generic rails outside timeline or process slides",
        },
    }
    for policy_name, policy_defaults in policy_repairs.items():
        policy = contract.get(policy_name)
        if not isinstance(policy, dict):
            continue
        for key, value in policy_defaults.items():
            if not policy.get(key):
                policy[key] = value
                changes.append(f"visual_contract.json: filled {policy_name}.{key}")
    layout_policy = contract.get("layout_quality_policy")
    if isinstance(layout_policy, dict):
        try:
            max_regions = int(layout_policy.get("max_primary_regions", 0))
        except Exception:
            max_regions = 0
        if max_regions <= 0 or max_regions > 3:
            layout_policy["max_primary_regions"] = 3
            changes.append("visual_contract.json: repaired layout_quality_policy.max_primary_regions")
    typography_policy = contract.get("typography_hierarchy_policy")
    if isinstance(typography_policy, dict):
        if typography_policy.get("primary_title_dominant") is not True:
            typography_policy["primary_title_dominant"] = True
            changes.append("visual_contract.json: repaired typography_hierarchy_policy.primary_title_dominant")
        try:
            ratio = float(typography_policy.get("secondary_text_max_ratio", 0))
        except Exception:
            ratio = 0
        if ratio <= 0 or ratio > 1:
            typography_policy["secondary_text_max_ratio"] = 0.62
            changes.append("visual_contract.json: repaired typography_hierarchy_policy.secondary_text_max_ratio")
    chrome_policy = contract.get("layout_chrome_policy")
    if isinstance(chrome_policy, dict):
        max_cardlike = safe_int(chrome_policy.get("max_cardlike_containers_per_slide"))
        if max_cardlike <= 0 or max_cardlike > 4:
            chrome_policy["max_cardlike_containers_per_slide"] = 3
            changes.append("visual_contract.json: repaired layout_chrome_policy.max_cardlike_containers_per_slide")
        cover_chips = safe_int(chrome_policy.get("max_cover_metric_chips"))
        if cover_chips <= 0 or cover_chips > 3:
            chrome_policy["max_cover_metric_chips"] = 3
            changes.append("visual_contract.json: repaired layout_chrome_policy.max_cover_metric_chips")
    evidence_policy = contract.get("evidence_layout_policy")
    if isinstance(evidence_policy, dict):
        treatments = evidence_policy.get("allowed_treatments")
        if not isinstance(treatments, list):
            evidence_policy["allowed_treatments"] = ["full_chart", "chart_with_takeaway", "chart_crop", "chart_then_takeaway"]
            changes.append("visual_contract.json: repaired evidence_layout_policy.allowed_treatments")
        else:
            normalized = {str(item).strip().lower() for item in treatments if str(item).strip()}
            required = ["full_chart", "chart_with_takeaway", "chart_crop", "chart_then_takeaway"]
            missing = [item for item in required if item not in normalized]
            if missing:
                evidence_policy["allowed_treatments"] = treatments + missing
                changes.append("visual_contract.json: completed evidence_layout_policy.allowed_treatments")
        try:
            max_same = int(evidence_policy.get("max_consecutive_same_composition", 0))
        except Exception:
            max_same = 0
        if max_same <= 0 or max_same > 2:
            evidence_policy["max_consecutive_same_composition"] = 2
            changes.append("visual_contract.json: repaired evidence_layout_policy.max_consecutive_same_composition")
    shape_policy = contract.get("shape_component_policy")
    if not isinstance(shape_policy, dict):
        contract["shape_component_policy"] = {
            "safe_area_policy": "all visible text and icons stay inside component bounds with padding",
            "text_fit_policy": "visible text must fit inside shapes; if overflow appears, shorten copy, enlarge or resize the component, split the slide, or fail the preview",
            "connector_policy": "use thin simple lines or small arrowheads only; forbid chunky chevrons/block arrows; endpoints terminate on node perimeter ports/edges with padding; lines never run through node interiors or text; align connectors on a grid, axis, centerline, or equal spacing system",
            "operator_policy": "operators are standalone labels, not symbols inside arrow shapes",
            "card_density_policy": "max 4 card-like foreground containers on ordinary slides",
            "separator_policy": "lines are functional only: axes, table rules, connectors, or intentional foreground separators",
            "preview_rejection_policy": "reject if screenshot shows overflow, overlap, connector clutter, or nested cards",
        }
        changes.append("visual_contract.json: added shape_component_policy")
    else:
        shape_defaults = {
            "safe_area_policy": "all visible text and icons stay inside component bounds with safe margins and padding",
            "operator_policy": "operators are standalone labels outside arrow shapes, never inside connector geometry",
            "card_density_policy": "limit ordinary slides to max 4 card-like containers; use fewer when a chart, image, or diagram is dominant",
            "separator_policy": "separators are functional or meaningful zone boundaries only, not decorative rails",
            "preview_rejection_policy": "reject or fix rendered overflow, overlap, nested cards, connector clutter, and unreadable text before export",
        }
        for key, value in shape_defaults.items():
            if not shape_policy.get(key):
                shape_policy[key] = value
                changes.append(f"visual_contract.json: filled shape_component_policy.{key}")
        fit = str(shape_policy.get("text_fit_policy") or "").lower()
        if not (
            any(term in fit for term in ("inside", "within", "fit"))
            and any(term in fit for term in ("fail", "split", "enlarge", "shorten", "resize"))
        ):
            shape_policy["text_fit_policy"] = (
                "visible text must fit inside shapes; if overflow appears, shorten copy, enlarge or resize the "
                "component, split the slide, or fail the preview"
            )
            changes.append("visual_contract.json: strengthened shape_component_policy.text_fit_policy")
        connector = str(shape_policy.get("connector_policy") or "").lower()
        if not (
            any(term in connector for term in ("thin", "simple", "line", "arrowhead", "whitespace"))
            and any(term in connector for term in ("chevron", "block", "chunky"))
            and any(term in connector for term in ("perimeter", "edge", "port", "boundary"))
            and any(term in connector for term in ("through", "cross", "interior", "inside node", "text"))
            and any(term in connector for term in ("align", "grid", "centerline", "axis", "spacing"))
        ):
            shape_policy["connector_policy"] = (
                "use thin simple lines or small arrowheads only; forbid chunky chevrons/block arrows; endpoints "
                "terminate on node perimeter ports/edges with padding; lines never run through node interiors or "
                "text; align connectors on a grid, axis, centerline, or equal spacing system"
            )
            changes.append("visual_contract.json: strengthened shape_component_policy.connector_policy")
    write_json(path, contract)
    return changes


def default_editable_policy(item: dict[str, Any]) -> str:
    acquire_via = str(item.get("acquire_via") or "").lower()
    role = str(item.get("asset_role") or item.get("purpose") or "").lower()
    if acquire_via in {"source", "web", "user"}:
        return "raster evidence image; foreground labels, callouts, captions, and layout objects remain editable"
    if acquire_via == "ai":
        return "raster atmosphere/concept image only; titles, charts, labels, cards, and evidence remain editable foreground objects"
    if acquire_via == "formula":
        return "rendered formula/chart image with editable surrounding explanation and source spec retained"
    if "background" in role:
        return "raster background texture only; slide structure remains editable foreground objects"
    return "raster asset with editable foreground text and layout objects"


def default_visual_asset_manifest(project: Path) -> dict[str, Any]:
    slides = slides_from_project(project)
    subject = title_of(slides[0]) if slides else "presentation topic"
    rows = [
        ("cover_atmosphere", 1, "cover_atmosphere", "quiet opening atmosphere with editorial negative space"),
        ("light_evidence", 2 if len(slides) >= 2 else 1, "light_evidence", "light evidence surface for readable dense proof slides"),
        ("diagram_focus", 3 if len(slides) >= 3 else 1, "diagram_focus", "neutral conceptual field for process, loop, or mechanism diagrams"),
        ("dark_evidence", 4 if len(slides) >= 4 else 1, "dark_evidence", "restrained dark evidence background for numbers, contrast, and proof objects"),
        ("closing_atmosphere", len(slides) or 1, "closing_atmosphere", "quiet closing atmosphere with forward motion and room for the final takeaway"),
    ]
    items: list[dict[str, Any]] = []
    for asset_id, slide_no, role, purpose in rows:
        filename = f"{asset_id}.png"
        prompt = (
            f"Create a text-free 16:9 editorial presentation image for {subject}. "
            f"The asset role is {purpose}. Use a calm neutral base, one restrained accent, soft depth, clear negative space, "
            "and no logos, no letters, no numbers, no UI, no chart, no card panels, no fake screenshots, and no fake evidence. "
            "The image is atmosphere or concept support only; all titles, labels, charts, captions, and layout objects remain editable foreground elements."
        )
        items.append(
            {
                "asset_id": asset_id,
                "filename": filename,
                "path": f"assets/images/{filename}",
                "slide_no": slide_no,
                "allowed_pages": [],
                "purpose": purpose,
                "asset_role": "background",
                "acquire_via": "ai",
                "status": "Needs-Manual",
                "reference": f"Planned {role} asset for {subject}; generate or replace before claiming final visual quality.",
                "page_role": "hero_page",
                "text_policy": "none",
                "aspect_ratio": "16:9",
                "image_size": "2K",
                "visual_type": "",
                "hero_primitive": "atmospheric",
                "editable_policy": default_editable_policy({"acquire_via": "ai", "asset_role": "background"}),
                "prompt": prompt,
                "safe_area": "editable foreground text should sit in the quiet center or side field; no image detail should compete with title or body copy",
                "negative_prompt": "text, letters, numbers, logo, watermark, UI, chart, table, card, panel, frame, screenshot, document, fake evidence",
                "art_direction_brief": {
                    "art_direction": purpose,
                    "composition": "16:9 calm editorial atmosphere with safe title/caption space and no baked-in layout geometry",
                    "safe_area": "keep the center and one side quiet enough for editable foreground text",
                    "foreground_boundary": "background only; no foreground cards, labels, charts, UI, or fake evidence",
                    "negative_prompt": "text, letters, numbers, logo, watermark, UI, chart, table, card, panel, frame, screenshot, document, fake evidence",
                },
                "notes": "Auto-created as a truthful Needs-Manual planning row by deck_repair_apply.py.",
                "alt_text": purpose,
            }
        )
    return {
        "schema_version": "1.0.0",
        "generated_at": utc_now(),
        "generator": "qiaomu-ppt/scripts/deck_repair_apply.py",
        "deck_image_model": {
            "image_rendering": "source-backed editorial evidence plus text-free atmosphere/concept images",
            "image_palette_behavior": "preserve source image colors; generated assets follow the deck neutral base plus one accent",
            "color_scheme": "warm neutral editorial base with restrained blue/red accents",
            "default_provider": "codex-or-configured-image-backend",
            "recommended_model": "gpt-image-2",
            "policy": "Generated images are text-free atmosphere/concept assets; source evidence images come from source/web/user rows.",
        },
        "status_policy": {
            "pending_allowed_before_export": True,
            "needs_manual_is_truthful_gap": True,
            "file_required_for_statuses": ["Generated", "Sourced", "Existing", "Rendered"],
        },
        "items": items,
    }


def ai_prompt_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    model = manifest.get("deck_image_model", {}) if isinstance(manifest.get("deck_image_model"), dict) else {}
    items = []
    for item in manifest.get("items", []):
        if not isinstance(item, dict) or item.get("acquire_via") != "ai":
            continue
        record = {
            "asset_id": item.get("asset_id", ""),
            "filename": item.get("filename", ""),
            "purpose": item.get("purpose", ""),
            "page_role": item.get("page_role", ""),
            "text_policy": item.get("text_policy", "none"),
            "aspect_ratio": item.get("aspect_ratio", "16:9"),
            "image_size": item.get("image_size", "1K"),
            "prompt": item.get("prompt", ""),
            "negative_prompt": item.get("negative_prompt", ""),
            "safe_area": item.get("safe_area", ""),
            "status": item.get("status", "Pending"),
            "alt_text": item.get("alt_text", ""),
        }
        if item.get("hero_primitive"):
            record["hero_primitive"] = item["hero_primitive"]
        if item.get("visual_type"):
            record["type"] = item["visual_type"]
        items.append(record)
    return {
        "schema_version": "1.0.0",
        "project": manifest.get("project", ""),
        "generated_at": utc_now(),
        "deck_rendering": model.get("image_rendering", ""),
        "deck_palette": model.get("image_palette_behavior", ""),
        "color_scheme": model.get("color_scheme", {}),
        "items": items,
    }


def render_image_prompts_markdown(prompt_manifest: dict[str, Any]) -> str:
    lines = [
        "# Image Generation Prompts",
        "",
        "> Generated by `deck_repair_apply.py` from `visual_asset_manifest.json`.",
        "",
    ]
    for idx, item in enumerate(prompt_manifest.get("items", []), start=1):
        lines.extend(
            [
                f"## {idx}. {item.get('asset_id') or item.get('filename')}",
                "",
                f"- Filename: `{item.get('filename', '')}`",
                f"- Status: `{item.get('status', '')}`",
                f"- Page role: `{item.get('page_role', '')}`",
                f"- Text policy: `{item.get('text_policy', '')}`",
                f"- Safe area: {item.get('safe_area', '')}",
                "",
                "Prompt:",
                "",
                str(item.get("prompt") or ""),
                "",
                "Negative prompt:",
                "",
                str(item.get("negative_prompt") or ""),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_image_prompt_sidecars(project: Path, manifest: dict[str, Any]) -> list[str]:
    if not any(isinstance(item, dict) and item.get("acquire_via") == "ai" for item in manifest.get("items", [])):
        return []
    prompt_manifest = ai_prompt_manifest(manifest)
    out_dir = project / "assets" / "images"
    json_path = out_dir / "image_prompts.json"
    md_path = out_dir / "image_prompts.md"
    changes: list[str] = []
    write_json(json_path, prompt_manifest)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_image_prompts_markdown(prompt_manifest), encoding="utf-8")
    changes.append("assets/images/image_prompts.json: refreshed from visual_asset_manifest.json")
    changes.append("assets/images/image_prompts.md: refreshed from visual_asset_manifest.json")
    return changes


def repair_visual_asset_manifest(project: Path) -> list[str]:
    path = project / "visual_asset_manifest.json"
    manifest = load_json(path)
    if not isinstance(manifest, dict):
        slides = slides_from_project(project)
        if not slides:
            return []
        manifest = default_visual_asset_manifest(project)
        write_json(path, manifest)
        return ["visual_asset_manifest.json: created Needs-Manual planning manifest"] + write_image_prompt_sidecars(project, manifest)
    changes: list[str] = []
    if not manifest.get("deck_image_model"):
        manifest["deck_image_model"] = {
            "image_rendering": "source-backed editorial evidence plus text-free atmosphere/concept images",
            "image_palette_behavior": "preserve source image colors; generated assets follow the deck neutral base plus one accent",
            "color_scheme": "warm neutral editorial base with restrained blue/red accents",
            "default_provider": "codex-or-configured-image-backend",
            "recommended_model": "gpt-image-2",
            "policy": "Generated images are text-free atmosphere/concept assets; source evidence images come from source/web/user rows.",
        }
        changes.append("visual_asset_manifest.json: added deck_image_model")
    elif isinstance(manifest.get("deck_image_model"), dict):
        model = manifest["deck_image_model"]
        for key, value in {
            "image_rendering": "source-backed editorial evidence plus text-free atmosphere/concept images",
            "image_palette_behavior": "preserve source image colors; generated assets follow the deck neutral base plus one accent",
            "color_scheme": "warm neutral editorial base with restrained blue/red accents",
        }.items():
            if not model.get(key):
                model[key] = value
                changes.append(f"visual_asset_manifest.json: deck_image_model {key} filled")
    items = manifest.get("items")
    if isinstance(items, list):
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            if not item.get("editable_policy"):
                item["editable_policy"] = default_editable_policy(item)
                changes.append(f"visual_asset_manifest.json: asset item {idx} editable_policy filled")
            if not item.get("text_policy"):
                item["text_policy"] = "no baked-in text; editable foreground text only"
                changes.append(f"visual_asset_manifest.json: asset item {idx} text_policy filled")
            if item.get("acquire_via") == "ai":
                if not item.get("safe_area"):
                    item["safe_area"] = "editable foreground text should sit in a quiet image area with no competing detail"
                    changes.append(f"visual_asset_manifest.json: asset item {idx} safe_area filled")
                if not item.get("negative_prompt"):
                    item["negative_prompt"] = "text, letters, numbers, logo, watermark, UI, chart, table, card, panel, frame, screenshot, document, fake evidence"
                    changes.append(f"visual_asset_manifest.json: asset item {idx} negative_prompt filled")
    if changes:
        write_json(path, manifest)
    changes.extend(write_image_prompt_sidecars(project, manifest))
    return changes


def repair_content_contract(project: Path) -> list[str]:
    path = project / "content_contract.json"
    plan = load_json(project / "slide_plan.json", {})
    slides = iter_slides(plan)
    contract = load_json(path, {})
    if not isinstance(contract, dict):
        contract = {}
    changes: list[str] = []
    defaults = {
        "audience": "target audience to be confirmed; use the current deck brief and source context",
        "purpose": "move the audience from scattered awareness to a clear, usable understanding",
        "desired_action": "understand the core argument, remember the key evidence, and know the next step",
        "current_state": "the audience has partial context and needs structure, evidence, and visual explanation",
        "desired_state": "the audience can explain the topic through the deck's claim-title storyline",
        "stakes": "weak source grounding or generic copy will make the deck feel hollow even if the visuals are polished",
        "structure_framework": "storyline",
        "title_policy": "claim_titles",
        "evidence_policy": "Each mainline slide needs source_card_ids/source_anchor or a concrete user-provided anchor; generic claims are rejected.",
        "speaker_note_policy": "speaker notes carry caveats, transitions, and likely objections; visible copy carries signal.",
        "copy_density": "3-5 visible chunks on normal slides unless route is report-like or classroom-specific",
    }
    for key, value in defaults.items():
        if not contract.get(key):
            contract[key] = value
            changes.append(f"content_contract.json: added {key}")
    if slides and not contract.get("slide_claims"):
        contract["slide_claims"] = [
            {
                "slide_no": idx,
                "claim_title": title_of(slide),
                "proof_object": slide.get("proof_object") or slide.get("visual_role") or "",
                "source_card_ids": slide.get("source_card_ids") or [],
            }
            for idx, slide in enumerate(slides, start=1)
        ]
        changes.append("content_contract.json: created slide_claims from slide_plan")
    if changes:
        write_json(path, contract)
    return changes


def ensure_brief_files(project: Path) -> list[str]:
    plan = load_json(project / "slide_plan.json", {})
    slides = iter_slides(plan)
    content_contract = load_json(project / "content_contract.json", {})
    if not isinstance(content_contract, dict):
        content_contract = {}
    visual_contract = load_json(project / "visual_contract.json", {})
    if not isinstance(visual_contract, dict):
        visual_contract = {}

    changes: list[str] = []
    title = title_of(slides[0]) if slides else "Untitled deck"
    deck_brief_path = project / "deck_brief.md"
    if not deck_brief_path.exists():
        deck_brief_path.write_text(
            "\n".join(
                [
                    "# Deck Brief",
                    "",
                    f"- Title: {title}",
                    f"- Audience: {content_contract.get('audience') or 'target audience to be confirmed'}",
                    f"- Purpose: {content_contract.get('purpose') or 'shape source material into a usable presentation'}",
                    f"- Desired action: {content_contract.get('desired_action') or 'understand and act on the core argument'}",
                    "- Route: editable_pptx",
                    "- Success criteria: source-grounded claim titles, varied layouts, real visual assets, readable editable foreground objects, and verified exports.",
                    "- Assumptions: auto-created by deck_repair_apply.py from existing project contracts; review before final delivery.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        changes.append("deck_brief.md: created from project contracts")

    style_brief_path = project / "style_brief.md"
    if not style_brief_path.exists():
        background_roles = visual_contract.get("background_roles") or BACKGROUND_ROLES
        if not isinstance(background_roles, list):
            background_roles = BACKGROUND_ROLES
        style_brief_path.write_text(
            "\n".join(
                [
                    "# Style Brief",
                    "",
                    "- Visual thesis: editorial, source-backed, calm but not monotonous; foreground hierarchy carries the argument.",
                    "- Palette: neutral base, readable text, one accent per slide; source images keep their own color truth.",
                    "- Typography: CJK page titles use readable 1.14-1.30 leading; body copy stays large enough for preview review.",
                    "- Layout rhythm: mix anchor, dense, and breathing pages with named Lxx/ITLxx patterns.",
                    "- Background rhythm: " + ", ".join(str(item) for item in background_roles[:8]),
                    "- Media policy: source/user/web evidence first; generated images are text-free atmosphere or concept assets only.",
                    "- Forbidden moves: repeated card grids, decorative separators, noisy dashboard chrome, baked-in text, and connector clutter.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        changes.append("style_brief.md: created from visual contract")
    return changes


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Deck Repair Apply Report",
        "",
        f"- Project: `{report['project']}`",
        f"- Dry run: `{str(report['dry_run']).lower()}`",
        f"- Applied at: `{report['generated_at']}`",
        "",
        "## Changed Files",
        "",
    ]
    for item in report.get("changed_files", []):
        lines.append(f"- `{item}`")
    if not report.get("changed_files"):
        lines.append("- None")
    lines.extend(["", "## Changes", ""])
    for change in report.get("changes", []):
        lines.append(f"- {change}")
    if not report.get("changes"):
        lines.append("- No deterministic repair changes were needed.")
    if report.get("skipped"):
        lines.extend(["", "## Skipped", ""])
        lines.extend(f"- {item}" for item in report["skipped"])
    lines.extend(["", "## Next Checks", ""])
    for command in report.get("next_checks", []):
        lines.append(f"- `{command}`")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory.")
    parser.add_argument("--repair-plan", type=Path, help="Optional reports/deck_repair_plan.json path.")
    parser.add_argument("--output", type=Path, help="JSON report output. Default: <project>/reports/deck_repair_apply_report.json")
    parser.add_argument("--markdown", type=Path, help="Markdown report output. Default: <project>/reports/deck_repair_apply_report.md")
    parser.add_argument("--apply-source-ids", action="store_true", help="Heuristically assign source_card_ids from source_cards.json when missing.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and report changes without writing repaired contracts.")
    args = parser.parse_args()

    project = args.project.resolve()
    if not (project / "slide_plan.json").exists():
        raise SystemExit(f"slide_plan.json missing: {project / 'slide_plan.json'}")
    before: dict[str, str] = {}
    target_paths = [
        project / "deck_brief.md",
        project / "style_brief.md",
        project / "slide_plan.json",
        project / "spec_lock.json",
        project / "visual_contract.json",
        project / "visual_asset_manifest.json",
        project / "assets" / "images" / "image_prompts.json",
        project / "assets" / "images" / "image_prompts.md",
        project / "content_contract.json",
    ]
    for path in target_paths:
        if path.exists():
            before[str(path)] = path.read_text(encoding="utf-8", errors="replace")

    changes: list[str] = []
    skipped: list[str] = []
    plan_changes, evidence = repair_slide_plan(project, apply_source_ids=args.apply_source_ids)
    changes.extend(plan_changes)
    changes.extend(repair_visual_contract(project))
    changes.extend(repair_visual_asset_manifest(project))
    changes.extend(repair_content_contract(project))
    changes.extend(ensure_brief_files(project))
    changes.extend(repair_spec_lock(project))
    if not args.apply_source_ids:
        skipped.append("source_card_ids were not auto-assigned; pass --apply-source-ids for heuristic matching.")
    repair_plan_path = args.repair_plan or project / "reports" / "deck_repair_plan.json"
    if repair_plan_path.exists():
        skipped.append(f"repair plan read-only evidence: {repair_plan_path.relative_to(project) if repair_plan_path.is_relative_to(project) else repair_plan_path}")

    after_changed: list[str] = []
    if args.dry_run:
        for path in target_paths:
            raw_path = str(path)
            if raw_path in before:
                path.write_text(before[raw_path], encoding="utf-8")
            elif path.exists():
                path.unlink()
    for path in target_paths:
        if path.exists():
            old = before.get(str(path))
            new = path.read_text(encoding="utf-8", errors="replace")
            if old != new:
                try:
                    after_changed.append(str(path.relative_to(project)))
                except ValueError:
                    after_changed.append(str(path))

    report = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/deck_repair_apply.py",
        "generated_at": utc_now(),
        "project": str(project),
        "dry_run": args.dry_run,
        "evidence": evidence,
        "changed_files": [] if args.dry_run else after_changed,
        "changes": changes,
        "skipped": skipped,
        "next_checks": [
            "python3 scripts/svg_deck_from_slide_plan.py <project> --force",
            "python3 scripts/check_project.py <project>",
            "python3 scripts/deck_quality_benchmark.py <project> --min-score 75",
            "python3 scripts/deck_repair_plan.py <project>",
        ],
    }
    output = args.output or project / "reports" / "deck_repair_apply_report.json"
    markdown = args.markdown or project / "reports" / "deck_repair_apply_report.md"
    write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
