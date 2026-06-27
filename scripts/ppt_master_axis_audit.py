#!/usr/bin/env python3
"""Audit whether a deck contract learned the real ppt-master execution axes."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CATALOG = SKILL_DIR / "data" / "ppt_master_axis_catalog.json"
TERMINAL_STATUSES = {"Generated", "Sourced", "Existing", "Rendered"}
MEDIA_EXPECTATION_TOKENS = {
    "album",
    "music",
    "musician",
    "singer",
    "song",
    "cover art",
    "architecture",
    "architect",
    "fashion",
    "design",
    "culture",
    "biography",
    "portrait",
    "product",
    "brand",
    "museum",
    "editorial",
    "magazine",
    "photo essay",
    "image-rich",
    "visual essay",
    "专辑",
    "唱片",
    "音乐",
    "歌手",
    "歌曲",
    "封面",
    "艺人",
    "建筑",
    "建筑师",
    "时尚",
    "设计",
    "文化",
    "人物",
    "传记",
    "照片",
    "影像",
    "杂志",
    "图像",
    "图文",
    "产品",
    "品牌"
}
BACKGROUND_TOKENS = {
    "background",
    "atmosphere",
    "ambient",
    "texture",
    "surface",
    "wallpaper",
    "wash",
    "背景",
    "氛围",
    "纹理",
}
PROMPT_SIDECAR_CANDIDATES = (
    "assets/images/image_prompts.json",
    "assets/images/image_prompts.md",
    "images/image_prompts.json",
    "images/image_prompts.md",
    "image_prompts.json",
    "image_prompts.md",
)
NOTES_CANDIDATES = (
    "notes/total.md",
    "speaker_notes.md",
    "page_content_guide.md",
)
ANIMATION_CANDIDATES = (
    "animations.json",
    "animation_manifest.json",
    "motion_manifest.json",
)
COMPONENT_RATIONALE_TOKENS = (
    "Visualization Reference List",
    "component_rationale",
    "component_selection",
    "chart_rationale",
    "rejected",
    "为什么",
    "拒绝",
    "备选",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_text(path: Path, limit: int = 60000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def iter_slides(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        raw = payload.get("slides") or payload.get("pages") or payload.get("slide_plan") or []
    elif isinstance(payload, list):
        raw = payload
    else:
        raw = []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def iter_asset_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("items") or payload.get("assets") or payload.get("rows") or []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def nested_get(payload: Any, path: tuple[str, ...]) -> Any:
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def first_value(payloads: list[Any], paths: list[tuple[str, ...]]) -> str:
    for payload in payloads:
        for path in paths:
            value = nested_get(payload, path)
            if isinstance(value, dict):
                for key in ("id", "name", "value"):
                    if value.get(key):
                        return norm(value[key])
            elif isinstance(value, str) and value.strip():
                return norm(value)
    return ""


def text_axis_value(text: str, keys: list[str]) -> str:
    for key in keys:
        pattern = re.compile(rf"(?im)^\s*[-\"']?\s*{re.escape(key)}\s*[:=]\s*[`\"']?([^`\"'\n,]+)")
        match = pattern.search(text)
        if match:
            return norm(match.group(1))
    return ""


def text_contains_any(text: str, tokens: set[str]) -> list[str]:
    lowered = text.lower()
    return sorted(token for token in tokens if token.lower() in lowered)


def is_background_like(item: dict[str, Any]) -> bool:
    blob = " ".join(
        norm(item.get(key)).lower()
        for key in ("asset_role", "purpose", "visual_type", "page_role", "reference", "filename", "asset_id")
    )
    return any(token in blob for token in BACKGROUND_TOKENS)


def existing_relpaths(project: Path, candidates: tuple[str, ...]) -> list[str]:
    return [candidate for candidate in candidates if (project / candidate).exists()]


def item_has_any(item: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(bool(norm(item.get(key))) for key in keys)


def allowed_or_custom(value: str, allowed_values: set[str], behavior: str = "") -> bool:
    if not value:
        return False
    if value in allowed_values:
        return True
    return value == "custom" and bool(behavior)


def asset_slide_numbers(item: dict[str, Any]) -> set[int]:
    slides: set[int] = set()

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, int):
            if value > 0:
                slides.add(value)
            return
        for match in re.finditer(r"\d+", str(value)):
            number = int(match.group(0))
            if 0 < number < 200:
                slides.add(number)

    for key in ("slide_no", "slide", "page", "page_no"):
        add(item.get(key))
    for key in ("allowed_pages", "slides", "pages", "usage", "used_on"):
        raw = item.get(key)
        if isinstance(raw, list):
            for value in raw:
                add(value)
        else:
            add(raw)
    return slides


def collect_artifact_text(project: Path, slides: list[dict[str, Any]]) -> str:
    pieces = []
    for name in (
        "deck_brief.md",
        "design_proposal.md",
        "design_spec.md",
        "style_brief.md",
        "route_card.md",
        "content_contract.json",
        "slide_plan.json",
    ):
        pieces.append(read_text(project / name))
    for slide in slides:
        pieces.append(
            " ".join(
                norm(slide.get(key))
                for key in ("title", "claim_title", "intent", "visual_role", "proof_object", "source_anchor")
            )
        )
    return "\n".join(pieces)


def score_project(project: Path, min_score: int = 75, catalog_path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    project = project.resolve()
    catalog = load_json(catalog_path)
    allowed = catalog.get("axes", {}) if isinstance(catalog, dict) else {}
    warnings: list[str] = []
    failures: list[str] = []

    slide_plan = load_json(project / "slide_plan.json") if (project / "slide_plan.json").exists() else {}
    slides = iter_slides(slide_plan)
    spec_lock_json = load_json(project / "spec_lock.json") if (project / "spec_lock.json").exists() else {}
    style_direction = load_json(project / "style_direction.json") if (project / "style_direction.json").exists() else {}
    visual_contract = load_json(project / "visual_contract.json") if (project / "visual_contract.json").exists() else {}
    manifest = load_json(project / "visual_asset_manifest.json") if (project / "visual_asset_manifest.json").exists() else {}
    items = iter_asset_items(manifest)

    text_blob = collect_artifact_text(project, slides)
    spec_lock_text = "\n".join([read_text(project / "spec_lock.md"), read_text(project / "spec_lock.json")])

    mode = first_value(
        [spec_lock_json, visual_contract, slide_plan],
        [
            ("mode",),
            ("narrative_mode",),
            ("deck_mode",),
            ("communication_mode",),
            ("content_contract", "structure_framework"),
        ],
    ) or text_axis_value(spec_lock_text, ["mode", "narrative_mode", "deck_mode"])
    visual_style = first_value(
        [style_direction, spec_lock_json, visual_contract],
        [
            ("selected_style", "id"),
            ("selected_preset",),
            ("visual_style",),
            ("render_style",),
            ("style", "visual_style"),
            ("style", "id"),
        ],
    ) or text_axis_value(spec_lock_text, ["visual_style", "render_style", "selected_preset"])
    deck_model = manifest.get("deck_image_model") if isinstance(manifest, dict) else {}
    image_rendering = first_value(
        [deck_model, spec_lock_json, visual_contract],
        [
            ("image_rendering",),
            ("rendering",),
            ("deck_rendering",),
            ("image_generation_model", "image_rendering"),
            ("image_generation_model", "rendering"),
        ],
    ) or text_axis_value(spec_lock_text, ["image_rendering", "deck_rendering"])
    image_palette = first_value(
        [deck_model, spec_lock_json, visual_contract],
        [
            ("image_palette_behavior",),
            ("image_palette",),
            ("deck_palette",),
            ("palette_behavior",),
            ("image_generation_model", "image_palette_behavior"),
            ("image_generation_model", "palette_behavior"),
        ],
    ) or text_axis_value(spec_lock_text, ["image_palette_behavior", "image_palette", "deck_palette"])
    mode_behavior = first_value([spec_lock_json, visual_contract], [("mode_behavior",)])
    visual_style_behavior = first_value([spec_lock_json, visual_contract], [("visual_style_behavior",)])
    image_rendering_behavior = first_value(
        [deck_model, spec_lock_json, visual_contract],
        [("image_rendering_behavior",), ("rendering_behavior",), ("image_generation_model", "image_rendering_behavior")],
    )
    image_palette_behavior = first_value(
        [deck_model, spec_lock_json, visual_contract],
        [("image_palette_behavior",), ("palette_behavior",), ("image_generation_model", "image_palette_behavior")],
    )

    acquire_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    page_role_counts: dict[str, int] = {}
    asset_role_counts: dict[str, int] = {}
    local_types: set[str] = set()
    hero_primitives: set[str] = set()
    ai_rows = 0
    ai_rows_with_text_policy = 0
    ai_local_rows = 0
    ai_local_with_type = 0
    ai_local_with_valid_type = 0
    ai_hero_rows = 0
    ai_hero_with_primitive = 0
    ai_hero_with_valid_primitive = 0
    rows_with_page_binding = 0
    inspectable_primary = 0
    needs_manual_primary = 0
    terminal_background = 0
    ai_prompt_rows = 0
    ai_composition_rows = 0
    ai_safe_area_rows = 0
    ai_foreground_boundary_rows = 0

    for item in items:
        acquire_via = norm(item.get("acquire_via")).lower()
        status = norm(item.get("status"))
        page_role = norm(item.get("page_role"))
        asset_role = norm(item.get("asset_role"))
        visual_type = norm(item.get("visual_type") or item.get("type"))
        primitive = norm(item.get("hero_primitive"))
        acquire_counts[acquire_via] = acquire_counts.get(acquire_via, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        if page_role:
            page_role_counts[page_role] = page_role_counts.get(page_role, 0) + 1
        if asset_role:
            asset_role_counts[asset_role] = asset_role_counts.get(asset_role, 0) + 1
        if visual_type:
            local_types.add(visual_type)
        if primitive:
            hero_primitives.add(primitive)
        if asset_slide_numbers(item):
            rows_with_page_binding += 1
        if acquire_via == "ai":
            ai_rows += 1
            if item_has_any(item, ("prompt", "positive_prompt", "image_prompt", "prompt_ref", "prompt_path")):
                ai_prompt_rows += 1
            if item_has_any(item, ("composition", "layout_pattern", "image_text_pattern_id", "camera", "reference")):
                ai_composition_rows += 1
            if item_has_any(item, ("safe_area", "text_safe_area", "safe_text_area", "copy_space", "overlay_reservation")):
                ai_safe_area_rows += 1
            if item_has_any(item, ("foreground_boundary", "editable_foreground", "foreground_role")):
                ai_foreground_boundary_rows += 1
            if item.get("text_policy") in {"none", "embedded"}:
                ai_rows_with_text_policy += 1
            if page_role == "local":
                ai_local_rows += 1
                if visual_type:
                    ai_local_with_type += 1
                    if visual_type in set(allowed.get("image_type_templates", [])) or visual_type == "custom":
                        ai_local_with_valid_type += 1
            if page_role == "hero_page":
                ai_hero_rows += 1
                if primitive:
                    ai_hero_with_primitive += 1
                    if primitive in set(allowed.get("hero_primitives", [])) or primitive == "custom":
                        ai_hero_with_valid_primitive += 1
        if acquire_via in {"source", "web", "user", "formula"}:
            if status in TERMINAL_STATUSES:
                inspectable_primary += 1
            elif status == "Needs-Manual":
                needs_manual_primary += 1
        elif acquire_via == "ai" and is_background_like(item) and status in TERMINAL_STATUSES:
            terminal_background += 1

    matched_media_tokens = text_contains_any(text_blob, MEDIA_EXPECTATION_TOKENS)
    media_expected = bool(matched_media_tokens)
    prompt_sidecars = existing_relpaths(project, PROMPT_SIDECAR_CANDIDATES)
    notes_sidecars = existing_relpaths(project, NOTES_CANDIDATES)
    animation_sidecars = existing_relpaths(project, ANIMATION_CANDIDATES)

    rhythm_count = 0
    layout_count = 0
    component_count = 0
    for slide in slides:
        if slide.get("rhythm") or slide.get("page_rhythm"):
            rhythm_count += 1
        if slide.get("layout_pattern_id") or slide.get("layout_pattern"):
            layout_count += 1
        if slide.get("component_type") or slide.get("chart_type") or slide.get("diagram_type") or slide.get("proof_object"):
            component_count += 1
    lock_contract = spec_lock_json.get("layout_execution_contract") if isinstance(spec_lock_json, dict) else {}
    if isinstance(lock_contract, dict):
        contract_slides = lock_contract.get("slides")
        if isinstance(contract_slides, list):
            layout_count = max(layout_count, len([item for item in contract_slides if isinstance(item, dict)]))

    axis_present = {
        "mode": bool(mode),
        "visual_style": bool(visual_style),
        "image_rendering": bool(image_rendering),
        "image_palette": bool(image_palette),
    }
    axis_valid = {
        "mode": allowed_or_custom(mode, set(allowed.get("modes", [])), mode_behavior),
        "visual_style": (
            allowed_or_custom(visual_style, set(allowed.get("visual_styles", [])), visual_style_behavior)
            or visual_style.startswith("pptmaster-case-")
        ),
        "image_rendering": allowed_or_custom(
            image_rendering,
            set(allowed.get("image_renderings", [])),
            image_rendering_behavior,
        ),
        "image_palette": allowed_or_custom(
            image_palette,
            set(allowed.get("image_palettes", [])),
            image_palette_behavior,
        ),
    }
    mode_style_separate = bool(mode and visual_style and mode != visual_style)
    if not mode:
        failures.append("missing narrative mode / communication mode lock")
    if not visual_style:
        failures.append("missing visual_style lock")
    if not image_rendering:
        failures.append("missing deck-wide image_rendering lock")
    if not image_palette:
        failures.append("missing deck-wide image_palette_behavior / image_palette lock")
    if mode and not axis_valid["mode"]:
        failures.append(f"mode `{mode}` is not a valid axis value; use a catalog id or `custom` with mode_behavior")
    if visual_style and not axis_valid["visual_style"]:
        warnings.append(f"visual_style `{visual_style}` is outside the current catalog; use a catalog id, `pptmaster-case-*`, or custom behavior prose")
    if image_rendering and not axis_valid["image_rendering"]:
        warnings.append(f"image_rendering `{image_rendering}` is outside the current catalog; use a catalog id or custom behavior prose")
    if image_palette and not axis_valid["image_palette"]:
        warnings.append(f"image_palette `{image_palette}` is outside the current catalog; use a catalog id or custom behavior prose")

    item_role_score = 1.0
    if items:
        fields = 0
        possible = len(items) * 3
        for item in items:
            fields += 1 if item.get("acquire_via") else 0
            fields += 1 if item.get("asset_role") else 0
            fields += 1 if item.get("page_role") else 0
        item_role_score = ratio(fields, possible)
    elif len(slides) > 8:
        item_role_score = 0.0
        failures.append("missing visual_asset_manifest items for long or high-design deck")

    ai_policy_score = 1.0 if ai_rows == 0 else ratio(ai_rows_with_text_policy, ai_rows)
    ai_prompt_score = 1.0 if ai_rows == 0 else max(ratio(ai_prompt_rows, ai_rows), 1.0 if prompt_sidecars else 0.0)
    ai_art_direction_score = 1.0 if ai_rows == 0 else (
        ratio(ai_composition_rows, ai_rows)
        + ratio(ai_safe_area_rows, ai_rows)
        + ratio(ai_foreground_boundary_rows, ai_rows)
    ) / 3
    local_type_score = 1.0 if ai_local_rows == 0 else ratio(ai_local_with_valid_type, ai_local_rows)
    hero_primitive_score = 1.0 if ai_hero_rows == 0 else ratio(ai_hero_with_valid_primitive, ai_hero_rows)
    page_binding_score = 1.0 if not items else ratio(rows_with_page_binding, len(items))
    if ai_rows and ai_policy_score < 1:
        failures.append("some AI image rows lack text_policy none/embedded")
    if ai_rows and ai_prompt_score < 1:
        failures.append("AI image rows lack row prompts or an image_prompts sidecar")
    if ai_rows and ai_art_direction_score < 0.75:
        failures.append("AI image rows lack composition, safe-area, or editable-foreground boundaries")
    if ai_local_rows and local_type_score < 1:
        failures.append("some local AI image rows lack a catalog visual_type")
    if ai_hero_rows and hero_primitive_score < 1:
        warnings.append("some hero_page AI rows lack a catalog hero_primitive")
    if items and page_binding_score < 0.8:
        warnings.append("many visual asset rows are not bound to slide_no/allowed_pages")

    if media_expected and inspectable_primary + needs_manual_primary == 0:
        failures.append("image-rich subject detected but no source/web/user/formula or Needs-Manual primary media rows exist")
    if media_expected and inspectable_primary == 0 and terminal_background > 0:
        warnings.append("deck has terminal atmosphere/background assets but no terminal inspectable primary media")

    component_contract_text = "\n".join([text_blob, spec_lock_text])
    page_charts_declared = bool(
        re.search(r"(?im)\b(page_charts|component_plan|component_type|chart_type|diagram_type)\b", component_contract_text)
        or component_count
    )
    component_rationale_present = any(token in component_contract_text for token in COMPONENT_RATIONALE_TOKENS)
    component_rationale_score = 1.0 if not page_charts_declared else (1.0 if component_rationale_present else 0.0)
    if page_charts_declared and not component_rationale_present:
        warnings.append("component/chart selections lack rationale or rejected-alternative notes")

    notes_score = 1.0 if notes_sidecars else (0.5 if any("speaker" in norm(slide).lower() for slide in slides) else 0.0)
    animation_score = 1.0 if animation_sidecars else 0.5
    if len(slides) > 7 and not notes_sidecars:
        warnings.append("long deck lacks notes/total.md or equivalent speaker-notes sidecar")
    if len(slides) > 7 and not animation_sidecars:
        warnings.append("long deck lacks animations.json or equivalent object-level motion sidecar")

    categories = [
        {
            "id": "axis_catalog_lock",
            "weight": 25,
            "score": pct(ratio(sum(1 for ok in axis_valid.values() if ok), len(axis_valid))),
            "evidence": {"present": axis_present, "valid": axis_valid},
        },
        {
            "id": "mode_style_separation",
            "weight": 10,
            "score": pct(1.0 if mode_style_separate else 0.0),
            "evidence": {"mode": mode, "visual_style": visual_style},
        },
        {
            "id": "image_role_contract",
            "weight": 20,
            "score": pct((item_role_score + ai_policy_score + page_binding_score) / 3),
            "evidence": {
                "items": len(items),
                "ai_rows": ai_rows,
                "item_role_score": round(item_role_score, 3),
                "ai_text_policy_score": round(ai_policy_score, 3),
                "page_binding_score": round(page_binding_score, 3),
            },
        },
        {
            "id": "image_prompt_contract",
            "weight": 10,
            "score": pct((ai_prompt_score + ai_art_direction_score) / 2),
            "evidence": {
                "prompt_sidecars": prompt_sidecars,
                "ai_prompt_rows": ai_prompt_rows,
                "ai_composition_rows": ai_composition_rows,
                "ai_safe_area_rows": ai_safe_area_rows,
                "ai_foreground_boundary_rows": ai_foreground_boundary_rows,
                "ai_prompt_score": round(ai_prompt_score, 3),
                "ai_art_direction_score": round(ai_art_direction_score, 3),
            },
        },
        {
            "id": "image_type_strategy",
            "weight": 15,
            "score": pct((local_type_score + hero_primitive_score) / 2),
            "evidence": {
                "local_types": sorted(local_types),
                "hero_primitives": sorted(hero_primitives),
                "local_type_score": round(local_type_score, 3),
                "hero_primitive_score": round(hero_primitive_score, 3),
            },
        },
        {
            "id": "primary_media_boundary",
            "weight": 15,
            "score": pct(1.0 if not media_expected else min(1.0, ratio(inspectable_primary + needs_manual_primary, 1))),
            "evidence": {
                "media_expected": media_expected,
                "matched_tokens": matched_media_tokens[:20],
                "inspectable_primary_count": inspectable_primary,
                "needs_manual_primary_count": needs_manual_primary,
                "terminal_background_count": terminal_background,
            },
        },
        {
            "id": "slide_execution_lock",
            "weight": 15,
            "score": pct((ratio(rhythm_count, len(slides)) + ratio(layout_count, len(slides))) / 2 if slides else 0.0),
            "evidence": {
                "slide_count": len(slides),
                "rhythm_rows": rhythm_count,
                "layout_rows": layout_count,
            },
        },
        {
            "id": "component_selection_contract",
            "weight": 5,
            "score": pct(component_rationale_score),
            "evidence": {
                "page_charts_declared": page_charts_declared,
                "component_rows": component_count,
                "component_rationale_present": component_rationale_present,
            },
        },
        {
            "id": "presentation_sidecars",
            "weight": 5,
            "score": pct((notes_score + animation_score) / 2),
            "evidence": {
                "notes_sidecars": notes_sidecars,
                "animation_sidecars": animation_sidecars,
                "notes_score": notes_score,
                "animation_score": animation_score,
            },
        },
    ]
    total_weight = sum(int(item["weight"]) for item in categories)
    score = round(sum(int(item["score"]) * int(item["weight"]) for item in categories) / total_weight)
    if score < min_score:
        failures.append(f"ppt-master axis score {score} below target {min_score}")

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/ppt_master_axis_audit.py",
        "generated_at": utc_now(),
        "project": str(project),
        "catalog": str(catalog_path),
        "ok": not failures,
        "score": score,
        "target_score": min_score,
        "ppt_master_ready": score >= min_score and not failures,
        "axes": {
            "mode": mode,
            "visual_style": visual_style,
            "image_rendering": image_rendering,
            "image_palette": image_palette,
            "local_image_types": sorted(local_types),
            "hero_primitives": sorted(hero_primitives),
        },
        "asset_counts": {
            "acquire_via": acquire_counts,
            "status": status_counts,
            "page_role": page_role_counts,
            "asset_role": asset_role_counts,
        },
        "categories": categories,
        "failures": failures,
        "warnings": warnings,
        "boundary": "This gate checks whether ppt-master was absorbed as execution axes and asset-role contracts, not copied as visual decoration.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    axes = report.get("axes", {})
    lines = [
        "# PPT Master Axis Audit",
        "",
        f"- OK: `{str(report.get('ok')).lower()}`",
        f"- Score: `{report.get('score')}` / 100",
        f"- Target: `{report.get('target_score')}`",
        f"- Mode: `{axes.get('mode', '')}`",
        f"- Visual style: `{axes.get('visual_style', '')}`",
        f"- Image rendering: `{axes.get('image_rendering', '')}`",
        f"- Image palette: `{axes.get('image_palette', '')}`",
        f"- Local image types: `{', '.join(axes.get('local_image_types') or [])}`",
        f"- Hero primitives: `{', '.join(axes.get('hero_primitives') or [])}`",
        "",
        "## Categories",
        "",
    ]
    for item in report.get("categories", []):
        lines.append(f"- `{item['id']}`: {item['score']} ({json.dumps(item['evidence'], ensure_ascii=False)})")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    lines.extend(["", f"> {report.get('boundary', '')}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--min-score", type=int, default=75)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    project = args.project.resolve()
    report = score_project(project, args.min_score, args.catalog)
    output = args.output or project / "reports" / "ppt_master_axis_audit.json"
    markdown = args.markdown or project / "reports" / "ppt_master_axis_audit.md"
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.enforce and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
