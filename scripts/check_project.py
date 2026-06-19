#!/usr/bin/env python3
"""Check qiaomu-ppt project artifacts without depending on upstream skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_ROOT = ["deck_brief.md", "slide_plan.json", "style_brief.md"]
SLIDE_FIELDS = [
    "slide_no",
    "title",
    "intent",
    "visual_role",
    "speaker_note_goal",
    "qa_risk",
]
PLACEHOLDERS = [
    r"\[必填\]",
    r"SLIDES_HERE",
    r"lorem ipsum",
    r"\bTODO\b",
    r"\bTBD\b",
]
SVG_BANNED = [
    r"<style\b",
    r"\bclass=",
    r"<foreignObject\b",
    r"<mask\b",
    r"<symbol\b",
    r"<use\b",
    r"textPath",
    r"@font-face",
    r"<animate",
    r"<script\b",
    r"\bon[a-zA-Z]+=",
    r"<iframe\b",
]
VISUAL_BACKGROUND_ROLES_MIN = 4
VISUAL_BACKGROUND_MAX_REPEAT = 2
ALLOWED_VISUAL_NOISE_BUDGETS = {"quiet", "moderate", "expressive"}
DEFAULT_MAX_ACTIVE_COLORS = 3
IMAGE_SLOT_FIELDS = [
    "slot_id",
    "slide_no",
    "x",
    "y",
    "w",
    "h",
    "fit",
    "mask",
    "padding",
    "overflow_policy",
]
CONTENT_CONTRACT_FIELDS = [
    "audience",
    "purpose",
    "desired_action",
    "current_state",
    "desired_state",
    "stakes",
    "structure_framework",
    "title_policy",
    "copy_density",
    "evidence_policy",
    "speaker_note_policy",
    "slide_claims",
]
ALLOWED_STRUCTURE_FRAMEWORKS = {
    "pyramid",
    "scqa",
    "mece",
    "storyline",
    "teaching_arc",
    "hybrid",
}
WEAK_TITLE_LABELS = {
    "agenda",
    "overview",
    "background",
    "problem",
    "solution",
    "data",
    "summary",
    "conclusion",
    "目录",
    "概览",
    "背景",
    "现状",
    "问题",
    "方案",
    "数据",
    "总结",
    "结论",
}
VISIBLE_INTERNAL_METADATA = [
    ("fetched via", r"\bfetched\s+via\b"),
    ("generated with", r"\bgenerated\s+with\b"),
    ("qiaomu-markdown-proxy", r"qiaomu-markdown-proxy"),
    ("speaker cue", r"Speaker\s+cue\s*:"),
]
URL_PATTERN = re.compile(r"https?://[^\s)>\"]+", flags=re.IGNORECASE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, list):
        return [item for item in plan if isinstance(item, dict)]
    if isinstance(plan, dict):
        for key in ("slides", "slide_plan", "pages"):
            value = plan.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def iter_image_slots(contract: Any) -> list[dict[str, Any]]:
    if not isinstance(contract, dict):
        return []
    slots = contract.get("image_slots")
    if isinstance(slots, list):
        return [slot for slot in slots if isinstance(slot, dict)]
    return []


def iter_slide_palette_slots(contract: Any) -> list[dict[str, Any]]:
    if not isinstance(contract, dict):
        return []
    slots = contract.get("slide_palette_slots")
    if isinstance(slots, list):
        return [slot for slot in slots if isinstance(slot, dict)]
    return []


def iter_slide_claims(contract: Any) -> list[dict[str, Any]]:
    if not isinstance(contract, dict):
        return []
    claims = contract.get("slide_claims")
    if isinstance(claims, list):
        return [claim for claim in claims if isinstance(claim, dict)]
    return []


def normalize_frameworks(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.lower()]
    if isinstance(value, list):
        return [str(item).lower() for item in value]
    return []


def slide_title(slide: dict[str, Any]) -> str:
    return str(slide.get("claim_title") or slide.get("title") or "").strip()


def slide_points(slide: dict[str, Any]) -> list[Any]:
    for key in ("bullets", "content_points", "points", "content"):
        value = slide.get(key)
        if isinstance(value, list):
            return value
    return []


def is_weak_title(title: str) -> bool:
    normalized = re.sub(r"[\s:：\-—–_]+", "", title.strip().lower())
    if normalized in WEAK_TITLE_LABELS:
        return True
    if title.strip().lower() in WEAK_TITLE_LABELS:
        return True
    return False


def check_content_contract(path: Path, slides: list[dict[str, Any]]) -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {}
    try:
        contract = load_json(path)
    except Exception as exc:
        return [f"invalid content_contract.json: {exc}"], warnings, evidence

    if not isinstance(contract, dict):
        return ["content_contract.json must be an object"], warnings, evidence

    missing = [field for field in CONTENT_CONTRACT_FIELDS if not contract.get(field)]
    if missing:
        failures.append(f"content_contract.json missing fields: {', '.join(missing)}")

    frameworks = normalize_frameworks(contract.get("structure_framework"))
    evidence["structure_framework"] = frameworks
    unknown = [item for item in frameworks if item not in ALLOWED_STRUCTURE_FRAMEWORKS]
    if unknown:
        warnings.append(f"content_contract.json has unknown structure framework: {', '.join(unknown)}")

    title_policy = str(contract.get("title_policy") or "").lower()
    if "claim" not in title_policy:
        warnings.append("content_contract.json should use claim_titles as title_policy")

    claims = iter_slide_claims(contract)
    evidence["slide_claim_count"] = len(claims)
    if slides and len(claims) < len(slides):
        failures.append("content_contract.json needs slide_claims for every slide")

    weak_titles: list[str] = []
    dense_slides: list[str] = []
    for slide in slides:
        title = slide_title(slide)
        slide_no = slide.get("slide_no", "?")
        if not title:
            failures.append(f"slide {slide_no} has no title or claim_title")
        elif is_weak_title(title):
            weak_titles.append(f"slide {slide_no}: {title}")
        points = slide_points(slide)
        if len(points) > 5:
            dense_slides.append(f"slide {slide_no}: {len(points)} visible chunks")

    if weak_titles:
        failures.append(
            "slides use weak label titles instead of claim titles: " + "; ".join(weak_titles[:8])
        )
    if dense_slides:
        warnings.append(
            "slides may exceed 3-5 visible support chunks: " + "; ".join(dense_slides[:8])
        )

    return failures, warnings, evidence


def check_visual_contract(path: Path, slide_count: int) -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {}
    try:
        contract = load_json(path)
    except Exception as exc:
        return [f"invalid visual_contract.json: {exc}"], warnings, evidence
    if not isinstance(contract, dict):
        return ["visual_contract.json must be an object"], warnings, evidence

    visual_noise_budget = contract.get("visual_noise_budget")
    evidence["visual_noise_budget"] = visual_noise_budget
    if slide_count > 8 and not visual_noise_budget:
        failures.append("visual_contract.json needs visual_noise_budget for decks over 8 slides")
    if visual_noise_budget and str(visual_noise_budget) not in ALLOWED_VISUAL_NOISE_BUDGETS:
        failures.append(
            "visual_contract.json visual_noise_budget must be one of: "
            + ", ".join(sorted(ALLOWED_VISUAL_NOISE_BUDGETS))
        )
    if visual_noise_budget and str(visual_noise_budget) != "quiet":
        warnings.append("visual_noise_budget is not quiet; verify this is intentional and content-led")

    color_budget = contract.get("color_budget")
    max_active_colors = DEFAULT_MAX_ACTIVE_COLORS
    if slide_count > 8 and not isinstance(color_budget, dict):
        failures.append("visual_contract.json needs color_budget for decks over 8 slides")
    if isinstance(color_budget, dict):
        declared_max = color_budget.get("max_active_colors_per_slide")
        try:
            max_active_colors = int(declared_max)
        except Exception:
            failures.append("color_budget.max_active_colors_per_slide must be an integer")
        if max_active_colors > DEFAULT_MAX_ACTIVE_COLORS:
            failures.append(
                f"color_budget.max_active_colors_per_slide must be <= {DEFAULT_MAX_ACTIVE_COLORS}"
            )
        accent_policy = str(color_budget.get("accent_policy") or color_budget.get("default_formula") or "").lower()
        if "one" not in accent_policy and "1" not in accent_policy:
            warnings.append("color_budget should declare a one-accent-per-slide policy")
    evidence["max_active_colors_per_slide"] = max_active_colors

    palette_slots = iter_slide_palette_slots(contract)
    evidence["slide_palette_slot_count"] = len(palette_slots)
    if slide_count > 8 and len(palette_slots) < slide_count:
        failures.append("visual_contract.json needs slide_palette_slots for every slide")
    for idx, slot in enumerate(palette_slots, start=1):
        colors = slot.get("active_colors")
        if not isinstance(colors, list) or not colors:
            failures.append(f"slide_palette_slot {idx} needs non-empty active_colors")
            continue
        unique_colors = {str(color).strip().lower() for color in colors if str(color).strip()}
        if len(unique_colors) > max_active_colors:
            failures.append(
                f"slide {slot.get('slide_no', idx)} uses {len(unique_colors)} active colors; max is {max_active_colors}"
            )

    background_policy = contract.get("background_asset_policy")
    if slide_count > 8 and not isinstance(background_policy, dict):
        failures.append("visual_contract.json needs background_asset_policy for decks over 8 slides")
    if isinstance(background_policy, dict):
        mode = str(background_policy.get("mode") or background_policy.get("generated_backgrounds") or "")
        evidence["background_asset_policy"] = mode
        line_policy = str(background_policy.get("decorative_line_policy") or "").lower()
        if "functional" not in line_policy and "forbid" not in line_policy and "no decorative" not in line_policy:
            failures.append(
                "background_asset_policy.decorative_line_policy must forbid non-functional decorative lines"
            )

    roles = contract.get("background_roles")
    if not isinstance(roles, list) or len(roles) < VISUAL_BACKGROUND_ROLES_MIN:
        failures.append(
            f"visual_contract.json needs at least {VISUAL_BACKGROUND_ROLES_MIN} background_roles"
        )
    evidence["background_role_count"] = len(roles) if isinstance(roles, list) else 0

    slide_roles = contract.get("slide_roles")
    if slide_count > 0:
        if not isinstance(slide_roles, list) or len(slide_roles) < slide_count:
            failures.append("visual_contract.json needs per-slide slide_roles for every slide")
        else:
            previous = None
            run_length = 0
            used_roles: set[str] = set()
            for idx, item in enumerate(slide_roles, start=1):
                missing_role_fields = [
                    field
                    for field in ("slide_no", "layout_role", "background_role", "dominant_object")
                    if not item.get(field)
                ]
                if missing_role_fields:
                    failures.append(
                        f"slide_role {idx} missing fields: {', '.join(missing_role_fields)}"
                    )
                role = str(item.get("background_role") or "")
                if role:
                    used_roles.add(role)
                if role and role == previous:
                    run_length += 1
                else:
                    previous = role
                    run_length = 1
                if role and run_length > VISUAL_BACKGROUND_MAX_REPEAT:
                    failures.append(
                        f"background_role `{role}` repeats more than {VISUAL_BACKGROUND_MAX_REPEAT} consecutive slides"
                    )
                    break
            if slide_count > 8 and len(used_roles) < VISUAL_BACKGROUND_ROLES_MIN:
                failures.append(
                    f"deck has {slide_count} slides but uses only {len(used_roles)} background roles"
                )

    layout_policy = contract.get("layout_quality_policy")
    if slide_count > 8 and not isinstance(layout_policy, dict):
        failures.append("visual_contract.json needs layout_quality_policy for decks over 8 slides")
    if isinstance(layout_policy, dict):
        evidence["layout_quality_policy"] = layout_policy.get("composition_formula", "")
        filler_policy = str(layout_policy.get("decorative_filler_policy") or "").lower()
        if "forbid" not in filler_policy and "no" not in filler_policy:
            failures.append("layout_quality_policy.decorative_filler_policy must forbid decorative filler")
        try:
            max_regions = int(layout_policy.get("max_primary_regions", 0))
        except Exception:
            max_regions = 0
        if max_regions <= 0 or max_regions > 3:
            failures.append("layout_quality_policy.max_primary_regions must be between 1 and 3")

    slots = iter_image_slots(contract)
    evidence["image_slot_count"] = len(slots)
    for idx, slot in enumerate(slots, start=1):
        missing = [field for field in IMAGE_SLOT_FIELDS if field not in slot or slot.get(field) in ("", None)]
        if missing:
            failures.append(f"image slot {idx} missing fields: {', '.join(missing)}")
        if slot.get("overflow_policy") != "clip_or_fail":
            warnings.append(f"image slot {idx} should use overflow_policy: clip_or_fail")
        if slot.get("mask") == "rounded_rect" and not slot.get("clip_method"):
            warnings.append(
                f"image slot {idx} uses rounded_rect mask; include clip_method to prove real clipping/compositing"
            )
    return failures, warnings, evidence


def check_source_manifest(root: Path, deck_brief_text: str) -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {}
    urls = URL_PATTERN.findall(deck_brief_text)
    sources_dir = root / "sources"
    manifest_path = sources_dir / "source_manifest.json"
    evidence["deck_brief_url_count"] = len(urls)
    evidence["source_manifest"] = str(manifest_path.relative_to(root)) if manifest_path.exists() else ""

    if urls and not manifest_path.exists():
        failures.append("deck_brief.md references URLs but sources/source_manifest.json is missing")
        return failures, warnings, evidence
    if not manifest_path.exists():
        if sources_dir.exists() and list(sources_dir.glob("*.md")):
            warnings.append("sources/ contains Markdown files but no source_manifest.json")
        return failures, warnings, evidence

    try:
        manifest = load_json(manifest_path)
    except Exception as exc:
        return [f"invalid sources/source_manifest.json: {exc}"], warnings, evidence

    source_records = manifest.get("sources")
    if not isinstance(source_records, list) or not source_records:
        failures.append("sources/source_manifest.json needs a non-empty sources list")
        return failures, warnings, evidence

    evidence["source_count"] = len(source_records)
    for idx, item in enumerate(source_records, start=1):
        if not isinstance(item, dict):
            failures.append(f"source_manifest source {idx} must be an object")
            continue
        for field in ("input", "title", "source_type", "fetch_route", "markdown_path"):
            if not item.get(field):
                failures.append(f"source_manifest source {idx} missing {field}")
        markdown_path = item.get("markdown_path")
        if markdown_path and not (sources_dir / str(markdown_path)).exists():
            failures.append(f"source_manifest source {idx} markdown_path does not exist: {markdown_path}")
        if item.get("missing_evidence"):
            warnings.append(f"source_manifest source {idx} has missing evidence: {item.get('missing_evidence')}")
    return failures, warnings, evidence


def scan_text(path: Path, patterns: list[str]) -> list[str]:
    text = read_text(path)
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def scan_visible_metadata_text(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in VISIBLE_INTERNAL_METADATA:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(label)
    return hits


def iter_pptx_visible_text(path: Path) -> tuple[list[tuple[int, str]], str | None]:
    try:
        from pptx import Presentation as PptxPresentation
    except Exception as exc:
        return [], f"python-pptx unavailable; cannot inspect visible text in {path.name}: {exc}"

    try:
        presentation = PptxPresentation(str(path))
    except Exception as exc:
        return [], f"cannot inspect visible text in {path.name}: {exc}"

    visible_text: list[tuple[int, str]] = []
    for slide_idx, slide in enumerate(presentation.slides, start=1):
        for shape in slide.shapes:
            text = getattr(shape, "text", "")
            if text:
                visible_text.append((slide_idx, text))
    return visible_text, None


def check_project(root: Path) -> dict[str, Any]:
    root = root.resolve()
    failures: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {"root": str(root)}

    for name in REQUIRED_ROOT:
        if not (root / name).exists():
            failures.append(f"missing required artifact: {name}")

    deck_brief_text = read_text(root / "deck_brief.md") if (root / "deck_brief.md").exists() else ""
    source_failures, source_warnings, source_evidence = check_source_manifest(root, deck_brief_text)
    failures.extend(source_failures)
    warnings.extend(source_warnings)
    evidence["source_manifest"] = source_evidence

    recommendations_path = root / "style_recommendations.json"
    if recommendations_path.exists():
        try:
            recommendations = load_json(recommendations_path)
            top = recommendations.get("top", []) if isinstance(recommendations, dict) else []
            if not top:
                warnings.append("style_recommendations.json exists but has no top recommendations")
            style_brief = root / "style_brief.md"
            spec_lock = root / "spec_lock.json"
            if style_brief.exists() and "selected_preset" not in read_text(style_brief):
                warnings.append("style recommendations exist but style_brief.md does not mention selected_preset")
            if spec_lock.exists() and "selected_preset" not in read_text(spec_lock):
                warnings.append("style recommendations exist but spec_lock.json does not mention selected_preset")
        except Exception as exc:
            failures.append(f"invalid style_recommendations.json: {exc}")

    plan_path = root / "slide_plan.json"
    slides: list[dict[str, Any]] = []
    if plan_path.exists():
        try:
            slides = iter_slides(load_json(plan_path))
        except Exception as exc:
            failures.append(f"invalid slide_plan.json: {exc}")
        if not slides:
            failures.append("slide_plan.json has no slides")
        for idx, slide in enumerate(slides, start=1):
            missing = [field for field in SLIDE_FIELDS if not slide.get(field)]
            if missing:
                failures.append(f"slide {idx} missing fields: {', '.join(missing)}")
    evidence["slide_count"] = len(slides)

    visual_contract_path = root / "visual_contract.json"
    if len(slides) > 8 and not visual_contract_path.exists():
        failures.append("missing visual_contract.json for deck with more than 8 slides")
    if visual_contract_path.exists():
        contract_failures, contract_warnings, contract_evidence = check_visual_contract(
            visual_contract_path, len(slides)
        )
        failures.extend(contract_failures)
        warnings.extend(contract_warnings)
        evidence["visual_contract"] = contract_evidence

    content_contract_path = root / "content_contract.json"
    if len(slides) > 8 and not content_contract_path.exists():
        failures.append("missing content_contract.json for deck with more than 8 slides")
    if content_contract_path.exists():
        content_failures, content_warnings, content_evidence = check_content_contract(
            content_contract_path, slides
        )
        failures.extend(content_failures)
        warnings.extend(content_warnings)
        evidence["content_contract"] = content_evidence

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".md", ".json", ".html", ".svg"}:
            placeholder_hits = scan_text(path, PLACEHOLDERS)
            if placeholder_hits:
                failures.append(f"{path.relative_to(root)} has placeholder residue: {', '.join(placeholder_hits)}")
        if path.suffix.lower() == ".svg":
            banned_hits = scan_text(path, SVG_BANNED)
            if banned_hits:
                failures.append(f"{path.relative_to(root)} has SVG/PPTX risky features: {', '.join(banned_hits)}")
            text = read_text(path)
            if "viewBox" not in text:
                warnings.append(f"{path.relative_to(root)} missing viewBox")
        if path.suffix.lower() == ".html":
            text = read_text(path)
            if "1920" not in text or "1080" not in text:
                warnings.append(f"{path.relative_to(root)} may not declare a fixed 1920x1080 stage")
            metadata_hits = scan_visible_metadata_text(text)
            if metadata_hits:
                failures.append(
                    f"{path.relative_to(root)} contains visible internal provenance: {', '.join(metadata_hits)}"
                )
        if path.suffix.lower() == ".svg":
            metadata_hits = scan_visible_metadata_text(read_text(path))
            if metadata_hits:
                failures.append(
                    f"{path.relative_to(root)} contains visible internal provenance: {', '.join(metadata_hits)}"
                )

    exports = list((root / "exports").glob("*.pptx")) if (root / "exports").exists() else []
    evidence["pptx_exports"] = [str(path.relative_to(root)) for path in exports]
    if not exports:
        warnings.append("no PPTX export found; mark editable PPTX export as missing evidence if required")
    if exports:
        preview_candidates = list((root / "previews").rglob("*.jpg")) + list((root / "previews").rglob("*.png")) + list((root / "previews").rglob("*.pdf"))
        evidence["preview_artifacts"] = [str(path.relative_to(root)) for path in preview_candidates[:20]]
        if not preview_candidates:
            warnings.append("PPTX export exists but no preview render found under previews/")
        visible_metadata_hits: list[str] = []
        for export in exports:
            visible_text, inspection_warning = iter_pptx_visible_text(export)
            if inspection_warning:
                warnings.append(inspection_warning)
                continue
            for slide_no, text in visible_text:
                metadata_hits = scan_visible_metadata_text(text)
                if metadata_hits:
                    visible_metadata_hits.append(
                        f"{export.relative_to(root)} slide {slide_no}: {', '.join(metadata_hits)}"
                    )
        evidence["visible_metadata_hits"] = visible_metadata_hits
        if visible_metadata_hits:
            failures.append(
                "PPTX contains visible internal provenance; move generation/source toolchain metadata to reports or notes"
            )

    return {
        "ok": not failures,
        "failures": failures,
        "warnings": warnings,
        "evidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check qiaomu-ppt project artifacts.")
    parser.add_argument("project_dir", help="Generated qiaomu-ppt project directory.")
    parser.add_argument("--output", "-o", help="Write JSON report to this path.")
    args = parser.parse_args()

    result = check_project(Path(args.project_dir))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    if not result["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
