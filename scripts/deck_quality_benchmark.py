#!/usr/bin/env python3
"""Benchmark a generated qiaomu-ppt deck against the ppt-master learning catalog."""

from __future__ import annotations

import argparse
import math
import json
import os
import re
import statistics
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CATALOG = SKILL_DIR / "data" / "ppt_master_examples_catalog.json"
TERMINAL_STATUSES = {"Generated", "Sourced", "Existing", "Rendered"}
BACKGROUND_ROLE_TOKENS = {
    "background",
    "atmosphere",
    "ambient",
    "texture",
    "wallpaper",
    "wash",
}
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
    "文化",
    "人物",
    "传记",
    "照片",
    "影像",
    "杂志",
    "图像",
    "图文",
    "产品",
    "品牌",
}
HTML_FORMAT_NAMES = {
    "html",
    "semantic_html",
    "semantic-html",
    "formal_html",
    "formal-html",
    "html_deck",
    "semantic_html_deck",
}
NON_HTML_DELIVERY_FORMATS = {
    "ppt",
    "pptx",
    "powerpoint",
    "pdf",
    "key",
    "keynote",
    "html-parity",
    "html_parity",
    "parity-html",
    "parity_html",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_format_name(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def semantic_html_route_info(project: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "semantic_html_manifest": False,
        "semantic_html_only": False,
        "requested_formats": [],
        "last_requested_formats": [],
        "formats": [],
        "successful_non_html_formats": [],
        "requested_non_html_formats": [],
        "non_html_outputs": [],
    }
    html_manifest = project / "html_delivery_manifest.json"
    if html_manifest.exists():
        try:
            payload = load_json(html_manifest)
            info["semantic_html_manifest"] = isinstance(payload, dict) and payload.get("mode") == "semantic_html_deck"
        except Exception:
            info["semantic_html_manifest"] = False

    export_manifest = project / "export_manifest.json"
    formats: dict[str, Any] = {}
    if export_manifest.exists():
        try:
            payload = load_json(export_manifest)
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            for key in ("requested_formats", "last_requested_formats"):
                raw = payload.get(key)
                normalized = [normalize_format_name(item) for item in raw] if isinstance(raw, list) else []
                info[key] = [item for item in normalized if item]
            raw_formats = payload.get("formats")
            formats = raw_formats if isinstance(raw_formats, dict) else {}
            info["formats"] = [normalize_format_name(name) for name in formats.keys()]

    requested_all = set(info["requested_formats"]) | set(info["last_requested_formats"])
    info["requested_non_html_formats"] = sorted(
        item for item in requested_all if item and item not in HTML_FORMAT_NAMES
    )
    for name, item in formats.items():
        normalized = normalize_format_name(name)
        if normalized not in NON_HTML_DELIVERY_FORMATS:
            continue
        status = str(item.get("status") or "").lower() if isinstance(item, dict) else ""
        if status in {"existing", "exported", "success"}:
            info["successful_non_html_formats"].append(normalized)

    export_dir = project / "exports"
    if export_dir.exists():
        for pattern in ("*.ppt", "*.pptx", "*.pdf", "*.key"):
            info["non_html_outputs"].extend(str(path.relative_to(project)) for path in export_dir.glob(pattern))

    info["semantic_html_only"] = bool(
        info["semantic_html_manifest"]
        and not info["requested_non_html_formats"]
        and not info["successful_non_html_formats"]
        and not info["non_html_outputs"]
    )
    return info


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, dict):
        slides = plan.get("slides") or plan.get("pages") or []
    else:
        slides = plan
    return [item for item in slides if isinstance(item, dict)] if isinstance(slides, list) else []


def asset_slide_numbers(item: dict[str, Any]) -> set[int]:
    slides: set[int] = set()

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, int):
            if value > 0:
                slides.add(value)
            return
        text = str(value)
        for match in re.finditer(r"\d+", text):
            try:
                number = int(match.group(0))
            except Exception:
                continue
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
    if not slides:
        for key in ("asset_id", "filename", "path"):
            text = str(item.get(key) or "")
            match = re.search(r"(?:slide|page|p|bg|visual|image)[-_ ]?0?(\d{1,3})(?:\D|$)", text, flags=re.IGNORECASE)
            if match:
                add(match.group(1))
                break
    return slides


def is_background_like_asset(item: dict[str, Any]) -> bool:
    blob = " ".join(
        str(item.get(key) or "")
        for key in ("asset_role", "purpose", "visual_type", "page_role", "reference", "filename", "asset_id")
    ).lower()
    return any(token in blob for token in BACKGROUND_ROLE_TOKENS)


def is_local_source_derived_asset(item: dict[str, Any]) -> bool:
    blob = " ".join(
        str(item.get(key) or "")
        for key in (
            "asset_id",
            "filename",
            "path",
            "purpose",
            "asset_role",
            "rights_notes",
            "generator",
            "art_direction",
        )
    ).lower()
    return any(
        token in blob
        for token in (
            "source-derived",
            "local-source-derived",
            "源资料衍生",
            "本地衍生",
            "该 png 只提供源资料衍生",
        )
    )


def is_trusted_source_asset(item: dict[str, Any]) -> bool:
    acquire_via = str(item.get("acquire_via") or "").lower()
    if is_local_source_derived_asset(item):
        return False
    if acquire_via == "user":
        return True
    if acquire_via == "web":
        return bool(item.get("source_page_url") or item.get("source_url") or item.get("url"))
    if acquire_via == "source":
        raw_path = str(item.get("path") or "")
        return bool(
            raw_path.startswith("sources/")
            or item.get("source_path")
            or item.get("source_page_url")
            or item.get("source_image_id")
            or item.get("source_page")
            or item.get("source_url")
        )
    return False


def is_primary_media_asset(item: dict[str, Any]) -> bool:
    acquire_via = str(item.get("acquire_via") or "").lower()
    if is_local_source_derived_asset(item):
        return False
    if acquire_via in {"source", "web", "user", "formula"}:
        return is_trusted_source_asset(item) or acquire_via == "formula"
    if acquire_via == "ai":
        return not is_background_like_asset(item)
    return False


def is_codex_runtime() -> bool:
    return any(os.environ.get(name) for name in ("CODEX_THREAD_ID", "CODEX_SHELL", "CODEX_CI"))


def is_codex_native_image_asset(item: dict[str, Any]) -> bool:
    blob = " ".join(
        str(item.get(key) or "")
        for key in (
            "asset_id",
            "filename",
            "path",
            "source",
            "source_path",
            "generated_asset_source",
            "original_source",
            "generator",
            "provider",
            "notes",
            "generation_note",
            "rights_notes",
        )
    ).lower()
    return any(
        token in blob
        for token in (
            "codex-native",
            "codex-imagegen",
            "codex_imagegen",
            "codex image_gen",
            "image_gen",
            ".codex/generated_images",
            "/.codex/generated_images/",
        )
    )


def media_expectation_stats(project: Path, slides: list[dict[str, Any]]) -> dict[str, Any]:
    snippets: list[str] = []
    for name in (
        "deck_brief.md",
        "design_proposal.md",
        "style_brief.md",
        "design_spec.md",
        "content_contract.json",
        "slide_plan.json",
    ):
        path = project / name
        if path.exists():
            try:
                snippets.append(path.read_text(encoding="utf-8", errors="replace")[:50000])
            except Exception:
                continue
    for slide in slides:
        snippets.append(
            " ".join(
                str(slide.get(key) or "")
                for key in ("title", "claim_title", "intent", "visual_role", "proof_object", "source_anchor")
            )
        )
    blob = "\n".join(snippets).lower()
    matched = sorted(token for token in MEDIA_EXPECTATION_TOKENS if token.lower() in blob)
    return {
        "expected": bool(matched),
        "matched_tokens": matched[:20],
    }


def catalog_baseline(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    projects = payload.get("projects", []) if isinstance(payload, dict) else []
    image_ratios: list[float] = []
    note_ratios: list[float] = []
    export_ratios: list[float] = []
    spec_image_ratios: list[float] = []
    slide_counts: list[int] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        slide_count = int(project.get("slide_count") or 0)
        counts = project.get("asset_counts") if isinstance(project.get("asset_counts"), dict) else {}
        if slide_count <= 0:
            continue
        slide_counts.append(slide_count)
        image_ratios.append(ratio(float(counts.get("image_files") or 0), slide_count))
        spec_image_ratios.append(ratio(float(counts.get("spec_image_refs") or 0), slide_count))
        note_ratios.append(ratio(float(counts.get("notes_files") or 0), slide_count))
        export_ratios.append(float(counts.get("export_files") or 0))
    def median(values: list[float], default: float = 0.0) -> float:
        return float(statistics.median(values)) if values else default
    return {
        "catalog": str(path),
        "project_count": len(projects),
        "median_slide_count": median([float(item) for item in slide_counts]),
        "median_image_files_per_slide": round(median(image_ratios), 3),
        "median_spec_image_refs_per_slide": round(median(spec_image_ratios), 3),
        "median_notes_files_per_slide": round(median(note_ratios), 3),
        "median_export_files": round(median(export_ratios), 3),
        "learning_boundary": "Learning statistics only; do not copy upstream templates, images, exact wording, or copyrighted slide designs.",
    }


def visual_asset_stats(project: Path) -> dict[str, Any]:
    path = project / "visual_asset_manifest.json"
    if not path.exists():
        return {
            "ai_count": 0,
            "terminal_count": 0,
            "terminal_slide_count": 0,
            "real_imagegen_count": 0,
            "codex_native_imagegen_count": 0,
            "procedural_fallback_count": 0,
            "source_or_web_count": 0,
            "source_or_web_slide_count": 0,
            "trusted_source_or_web_count": 0,
            "trusted_source_or_web_slide_count": 0,
            "local_source_derived_count": 0,
            "primary_media_count": 0,
            "primary_media_slide_count": 0,
            "background_terminal_count": 0,
        }
    data = load_json(path)
    items = data.get("items") if isinstance(data, dict) else []
    stats = {
        "ai_count": 0,
        "terminal_count": 0,
        "terminal_slide_count": 0,
        "real_imagegen_count": 0,
        "codex_native_imagegen_count": 0,
        "procedural_fallback_count": 0,
        "source_or_web_count": 0,
        "source_or_web_slide_count": 0,
        "trusted_source_or_web_count": 0,
        "trusted_source_or_web_slide_count": 0,
        "local_source_derived_count": 0,
        "primary_media_count": 0,
        "primary_media_slide_count": 0,
        "background_terminal_count": 0,
    }
    slides: set[int] = set()
    source_or_web_slides: set[int] = set()
    trusted_source_or_web_slides: set[int] = set()
    primary_media_slides: set[int] = set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        acquire_via = str(item.get("acquire_via") or "")
        status = str(item.get("status") or "")
        generator = str(item.get("generator") or "")
        if acquire_via == "ai":
            stats["ai_count"] += 1
        if status in {"Generated", "Sourced", "Existing", "Rendered"}:
            rel = str(item.get("path") or "")
            if rel and (project / rel).exists():
                stats["terminal_count"] += 1
                slide_numbers = asset_slide_numbers(item)
                slides.update(slide_numbers)
                if acquire_via in {"web", "source", "user"} and status in {"Sourced", "Existing"} and is_trusted_source_asset(item):
                    stats["source_or_web_count"] += 1
                    source_or_web_slides.update(slide_numbers)
                    stats["trusted_source_or_web_count"] += 1
                    trusted_source_or_web_slides.update(slide_numbers)
                elif acquire_via in {"web", "source", "user"} and status in {"Sourced", "Existing"} and is_local_source_derived_asset(item):
                    stats["local_source_derived_count"] += 1
                if is_primary_media_asset(item):
                    stats["primary_media_count"] += 1
                    primary_media_slides.update(slide_numbers)
                elif is_background_like_asset(item):
                    stats["background_terminal_count"] += 1
                if acquire_via == "ai" and status == "Generated":
                    if generator == "procedural-preview-fallback":
                        stats["procedural_fallback_count"] += 1
                    elif generator:
                        stats["real_imagegen_count"] += 1
                        if is_codex_native_image_asset(item):
                            stats["codex_native_imagegen_count"] += 1
    stats["terminal_slide_count"] = len(slides)
    stats["source_or_web_slide_count"] = len(source_or_web_slides)
    stats["trusted_source_or_web_slide_count"] = len(trusted_source_or_web_slides)
    stats["primary_media_slide_count"] = len(primary_media_slides)
    return stats


def image_diversity_stats(project: Path, slide_count: int) -> dict[str, Any]:
    path = project / "visual_asset_manifest.json"
    result: dict[str, Any] = {
        "terminal_image_count": 0,
        "slide_image_count": 0,
        "unique_image_count": 0,
        "target_unique_count": 0,
        "unique_ratio": 1.0,
        "adjacent_repeat_count": 0,
        "max_reuse_count": 0,
        "overused_count": 0,
        "examples": [],
    }
    if not path.exists():
        return result
    try:
        data = load_json(path)
    except Exception:
        return result
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return result

    slide_paths: dict[int, str] = {}
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status not in TERMINAL_STATUSES:
            continue
        rel = str(item.get("path") or "").strip()
        if not rel or not (project / rel).exists():
            continue
        result["terminal_image_count"] += 1
        for slide_no in sorted(asset_slide_numbers(item)):
            # Count one primary visual fingerprint per slide; extra ITL comparison rows
            # still matter elsewhere, but thumbnail diversity is slide-level.
            slide_paths.setdefault(slide_no, rel)

    ordered = [slide_paths[idx] for idx in sorted(slide_paths)]
    counts = {rel: ordered.count(rel) for rel in set(ordered)}
    result["slide_image_count"] = len(ordered)
    result["unique_image_count"] = len(counts)
    if slide_count <= 0:
        target_unique = 0
    elif slide_count <= 6:
        target_unique = min(slide_count, max(1, math.ceil(slide_count * 0.5)))
    elif slide_count <= 12:
        target_unique = min(slide_count, max(5, math.ceil(slide_count * 0.65)))
    else:
        target_unique = min(slide_count, max(8, math.ceil(slide_count * 0.60)))
    result["target_unique_count"] = target_unique
    result["unique_ratio"] = round(ratio(float(result["unique_image_count"]), max(1.0, float(target_unique))), 3)
    adjacent = 0
    adjacent_examples: list[str] = []
    for idx in range(1, len(ordered)):
        if ordered[idx] == ordered[idx - 1]:
            adjacent += 1
            if len(adjacent_examples) < 5:
                adjacent_examples.append(f"slides {idx}-{idx + 1}: {ordered[idx]}")
    result["adjacent_repeat_count"] = adjacent
    max_reuse = max(counts.values()) if counts else 0
    result["max_reuse_count"] = max_reuse
    allowed_reuse = 2 if slide_count <= 12 else 3
    result["overused_count"] = sum(1 for value in counts.values() if value > allowed_reuse)
    examples = [
        {"path": rel, "count": count}
        for rel, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count > 1
    ][:8]
    if adjacent_examples:
        examples.extend({"adjacent_repeat": item} for item in adjacent_examples)
    result["examples"] = examples[:8]
    return result


def source_stats(project: Path, slides: list[dict[str, Any]]) -> dict[str, Any]:
    cards_path = project / "sources" / "source_cards.json"
    source_cards = 0
    image_candidates = 0
    if cards_path.exists():
        try:
            payload = load_json(cards_path)
            cards = payload.get("cards") if isinstance(payload, dict) else payload
            source_cards = len(cards) if isinstance(cards, list) else 0
            candidates = payload.get("image_candidates") if isinstance(payload, dict) else []
            image_candidates = len(candidates) if isinstance(candidates, list) else 0
        except Exception:
            source_cards = 0
            image_candidates = 0
    source_visual_slides: set[int] = set()
    manifest_path = project / "visual_asset_manifest.json"
    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
            items = manifest.get("items") if isinstance(manifest, dict) else []
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if str(item.get("acquire_via") or "").lower() not in {"source", "web", "user"}:
                        continue
                    if str(item.get("status") or "") not in TERMINAL_STATUSES:
                        continue
                    try:
                        slide_no = int(item.get("slide_no"))
                    except (TypeError, ValueError):
                        slide_no = 0
                    if slide_no > 0:
                        source_visual_slides.add(slide_no)
        except Exception:
            source_visual_slides = set()
    cited_slides = 0
    for idx, slide in enumerate(slides, start=1):
        if slide.get("source_card_ids") or slide.get("source_anchor") or idx in source_visual_slides:
            cited_slides += 1
    return {
        "source_cards": source_cards,
        "image_candidates": image_candidates,
        "source_visual_slides": len(source_visual_slides),
        "cited_slides": cited_slides,
        "cited_slide_ratio": round(ratio(cited_slides, len(slides)), 3),
    }


def export_stats(project: Path) -> dict[str, Any]:
    path = project / "export_manifest.json"
    formats: dict[str, Any] = {}
    keynote_capability: dict[str, Any] = {}
    requested_formats: list[str] = []
    if path.exists():
        try:
            data = load_json(path)
            formats = data.get("formats") if isinstance(data, dict) and isinstance(data.get("formats"), dict) else {}
            keynote_capability = data.get("keynote_capability") if isinstance(data, dict) and isinstance(data.get("keynote_capability"), dict) else {}
            raw_requested = data.get("requested_formats") if isinstance(data, dict) else []
            requested_formats = [normalize_format_name(item) for item in raw_requested] if isinstance(raw_requested, list) else []
        except Exception:
            formats = {}
            keynote_capability = {}
            requested_formats = []
    successful = [
        name
        for name, item in formats.items()
        if isinstance(item, dict) and item.get("status") in {"existing", "exported", "success"}
    ]
    if not formats:
        discovered: list[str] = []
        if (project / "exports").exists() and list((project / "exports").glob("*.pptx")):
            discovered.append("pptx")
        if (
            (project / "exports").exists()
            and list((project / "exports").glob("*.pdf"))
        ) or ((project / "previews").exists() and list((project / "previews").glob("*.pdf"))):
            discovered.append("pdf")
        if (
            (project / "html" / "index.html").exists()
            or ((project / "exports").exists() and list((project / "exports").glob("*.html")))
        ):
            discovered.append("html")
        successful = discovered
        formats = {name: {"status": "existing", "discovered_without_export_manifest": True} for name in discovered}
    keynote_feasible = bool(keynote_capability.get("can_attempt_keynote_export"))
    requested_set = {item for item in requested_formats if item}
    html_only_requested = bool(requested_set) and requested_set.issubset(HTML_FORMAT_NAMES)
    keynote_targeted = (not html_only_requested and keynote_feasible) or "keynote" in requested_set or "keynote" in formats
    if requested_set:
        target_format_count = len(requested_set)
    else:
        target_format_count = 4 if keynote_targeted else 3
    return {
        "formats": sorted(formats.keys()),
        "requested_formats": sorted(requested_set),
        "html_only_requested": html_only_requested,
        "successful_formats": sorted(successful),
        "successful_format_count": len(successful),
        "target_format_count": target_format_count,
        "keynote_feasible": keynote_feasible,
        "keynote_targeted": keynote_targeted,
        "has_pptx": "pptx" in successful,
        "has_html": "html" in successful,
        "has_pdf": "pdf" in successful,
        "has_keynote": "keynote" in successful,
    }


def rhythm_stats(project: Path) -> dict[str, Any]:
    path = project / "reports" / "visual_rhythm_report.json"
    if not path.exists() and (project / "svg_output").exists():
        try:
            from visual_rhythm_check import check as check_visual_rhythm

            data = check_visual_rhythm(project, "svg_output")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return data.get("summary") if isinstance(data.get("summary"), dict) else {}
        except Exception:
            return {}
    if not path.exists():
        return {}
    try:
        data = load_json(path)
    except Exception:
        return {}
    return data.get("summary") if isinstance(data, dict) and isinstance(data.get("summary"), dict) else {}


def style_execution_stats(project: Path) -> dict[str, Any]:
    path = project / "reports" / "style_execution_audit.json"
    if not path.exists() and (project / "style_direction.json").exists():
        try:
            from style_execution_audit import score_project as score_style_execution

            data = score_style_execution(project, 70)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return {
                "score": int(data.get("score") or 0),
                "ok": bool(data.get("ok")),
                "selected_style": data.get("selected_style") or {},
                "categories": data.get("categories") or [],
                "warnings": data.get("warnings") or [],
                "failures": data.get("failures") or [],
                "stats": data.get("stats") if isinstance(data.get("stats"), dict) else {},
            }
        except Exception:
            return {"score": 0, "ok": False, "selected_style": {}, "categories": [], "warnings": [], "failures": []}
    if not path.exists():
        return {"score": 0, "ok": False, "selected_style": {}, "categories": [], "warnings": [], "failures": []}
    try:
        data = load_json(path)
    except Exception:
        return {"score": 0, "ok": False, "selected_style": {}, "categories": [], "warnings": [], "failures": []}
    return {
        "score": int(data.get("score") or 0),
        "ok": bool(data.get("ok")),
        "selected_style": data.get("selected_style") if isinstance(data.get("selected_style"), dict) else {},
        "categories": data.get("categories") if isinstance(data.get("categories"), list) else [],
        "warnings": data.get("warnings") if isinstance(data.get("warnings"), list) else [],
        "failures": data.get("failures") if isinstance(data.get("failures"), list) else [],
        "stats": data.get("stats") if isinstance(data.get("stats"), dict) else {},
    }


def upstream_creation_stats(project: Path) -> dict[str, Any]:
    audits = [
        ("content_outline", project / "reports" / "content_outline_audit.json"),
        ("element_plan", project / "reports" / "element_plan_audit.json"),
        ("style_fit", project / "reports" / "style_fit_audit.json"),
    ]
    scores: dict[str, int] = {}
    ok: dict[str, bool] = {}
    missing: list[str] = []
    warnings: list[str] = []
    failures: list[str] = []
    for name, path in audits:
        if not path.exists():
            fallback_path = None
            fallback_score_key = "overall_score"
            if name == "content_outline":
                fallback_path = project / "reports" / "content-preflight.json"
            elif name == "element_plan":
                fallback_path = project / "reports" / "top-quality-plan.json"
            if fallback_path and fallback_path.exists():
                try:
                    fallback = load_json(fallback_path)
                    score = int(fallback.get(fallback_score_key) or fallback.get("score") or 0) if isinstance(fallback, dict) else 0
                    scores[name] = score
                    ok[name] = bool(fallback.get("ok") or fallback.get("gate_ready")) if isinstance(fallback, dict) else score >= 75
                    warnings.extend(f"{name}: using {fallback_path.name} as upstream quality evidence")
                    continue
                except Exception as exc:
                    failures.append(f"{name}: cannot read fallback audit report {fallback_path.name}: {exc}")
            scores[name] = 0
            ok[name] = False
            missing.append(name)
            continue
        try:
            data = load_json(path)
        except Exception as exc:
            scores[name] = 0
            ok[name] = False
            failures.append(f"{name}: cannot read audit report: {exc}")
            continue
        scores[name] = int(data.get("score") or 0) if isinstance(data, dict) else 0
        ok[name] = bool(data.get("ok")) if isinstance(data, dict) else False
        if isinstance(data, dict):
            warnings.extend(f"{name}: {item}" for item in data.get("warnings", [])[:3])
            failures.extend(f"{name}: {item}" for item in data.get("failures", [])[:3])
    average = int(round(sum(scores.values()) / len(audits))) if audits else 0
    return {
        "score": average,
        "ok": all(ok.values()) if ok else False,
        "scores": scores,
        "missing": missing,
        "warnings": warnings,
        "failures": failures,
    }


def layout_execution_stats(project: Path, slides: list[dict[str, Any]]) -> dict[str, Any]:
    path = project / "spec_lock.json"
    contract_slides: list[dict[str, Any]] = []
    if path.exists():
        try:
            data = load_json(path)
            contract = data.get("layout_execution_contract") if isinstance(data, dict) else {}
            raw = contract.get("slides") if isinstance(contract, dict) else []
            contract_slides = [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
        except Exception:
            contract_slides = []
    if not contract_slides and (project / "html_layout_intent.json").exists():
        try:
            data = load_json(project / "html_layout_intent.json")
            raw = data.get("slides") if isinstance(data, dict) else []
            if isinstance(raw, list):
                contract_slides = [
                    {
                        "layout_pattern_id": item.get("layout_pattern_id") or item.get("layout_id") or "",
                        "component_type": item.get("component_type") or item.get("semantic_role") or item.get("component_family") or "",
                    }
                    for item in raw
                    if isinstance(item, dict)
                ]
        except Exception:
            contract_slides = []
    plan_layouts: set[str] = set()
    for slide in slides:
        value = str(slide.get("layout_pattern_id") or slide.get("layout_pattern") or "").upper()
        if value:
            for token in value.replace("/", " ").split():
                if len(token) == 3 and token.startswith("L") and token[1:].isdigit():
                    plan_layouts.add(token)
    contract_layouts = {
        str(item.get("layout_pattern_id") or "").upper()
        for item in contract_slides
        if str(item.get("layout_pattern_id") or "").strip()
    }
    component_types = {
        str(item.get("component_type") or "")
        for item in contract_slides
        if str(item.get("component_type") or "").strip()
    }
    rich_components = {
        "process_flow",
        "mechanism_loop",
        "chart_with_takeaway",
        "concept_map",
        "objection_response",
        "pull_quote",
        "comparison",
        "closing_takeaway",
        "hero_claim",
    }
    layout_to_component = {
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
    layout_components = {
        layout_to_component[layout_id]
        for layout_id in contract_layouts.union(plan_layouts)
        if layout_id in layout_to_component
    }
    executed_components = component_types.union(layout_components)
    executed_rich = len(executed_components.intersection(rich_components))
    return {
        "plan_layout_count": len(plan_layouts),
        "contract_layout_count": len(contract_layouts),
        "component_type_count": len(component_types),
        "rich_component_count": executed_rich,
        "executed_component_count": len(executed_components),
        "contract_slide_count": len(contract_slides),
        "contract_layouts": sorted(contract_layouts),
        "component_types": sorted(component_types),
        "executed_components": sorted(executed_components),
    }


def svg_image_resolution_stats(project: Path) -> dict[str, Any]:
    svg_dir = project / "svg_output"
    stats: dict[str, Any] = {
        "image_count": 0,
        "checked_count": 0,
        "underresolved_count": 0,
        "severe_underresolved_count": 0,
        "examples": [],
    }
    if not svg_dir.exists():
        return stats
    try:
        from PIL import Image  # type: ignore
    except Exception:
        stats["warning"] = "Pillow unavailable; image resolution fit not checked"
        return stats

    for svg_path in sorted(svg_dir.glob("*.svg")):
        text = svg_path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"<image\b([^>]*)/?>", text, flags=re.IGNORECASE):
            attrs = match.group(1)
            href_match = re.search(r'\bhref="(?!data:)([^"]+)"', attrs) or re.search(
                r'\bxlink:href="(?!data:)([^"]+)"', attrs
            )
            if not href_match:
                continue
            stats["image_count"] += 1
            href = href_match.group(1)
            w_match = re.search(r'\bwidth="([^"]+)"', attrs)
            h_match = re.search(r'\bheight="([^"]+)"', attrs)
            if not w_match or not h_match:
                continue
            try:
                display_w = float(w_match.group(1))
                display_h = float(h_match.group(1))
            except (TypeError, ValueError):
                continue
            img_path = (svg_path.parent / href).resolve()
            if not img_path.exists():
                continue
            try:
                with Image.open(img_path) as image:
                    actual_w, actual_h = image.size
            except Exception:
                continue
            stats["checked_count"] += 1
            scale = max(display_w / max(1, actual_w), display_h / max(1, actual_h))
            if scale > 1.35:
                stats["underresolved_count"] += 1
                severe = scale > 2.0 or (display_w >= 1180 and display_h >= 660)
                if severe:
                    stats["severe_underresolved_count"] += 1
                if len(stats["examples"]) < 8:
                    stats["examples"].append(
                        {
                            "svg": str(svg_path.relative_to(project)),
                            "href": href,
                            "actual": [actual_w, actual_h],
                            "display": [int(display_w), int(display_h)],
                            "scale": round(scale, 2),
                            "severity": "severe" if severe else "warning",
                        }
                    )
    return stats


def score_project(project: Path, catalog: Path, min_score: int) -> dict[str, Any]:
    project = project.resolve()
    baseline = catalog_baseline(catalog)
    plan_path = project / "slide_plan.json"
    slides = iter_slides(load_json(plan_path)) if plan_path.exists() else []
    slide_count = len(slides)
    rhythm = rhythm_stats(project)
    assets = visual_asset_stats(project)
    sources = source_stats(project, slides)
    exports = export_stats(project)
    layout_exec = layout_execution_stats(project, slides)
    image_resolution = svg_image_resolution_stats(project)
    image_diversity = image_diversity_stats(project, slide_count)
    style_exec = style_execution_stats(project)
    upstream_creation = upstream_creation_stats(project)
    media_expectation = media_expectation_stats(project, slides)
    route_info = semantic_html_route_info(project)
    html_only = bool(route_info.get("semantic_html_only"))
    route_adjustments: list[str] = []

    art_target = max(3, min(slide_count, round(slide_count * 0.55)))
    fp_target = max(3, min(slide_count, round(slide_count * 0.55)))
    image_ratio_target = max(0.45, min(0.9, float(baseline["median_spec_image_refs_per_slide"])))
    terminal_image_ratio = ratio(float(assets["terminal_slide_count"]), slide_count)
    svg_image_ratio = ratio(float(rhythm.get("svg_image_slides") or 0), slide_count)
    key_ai_target = max(3, round(slide_count * 0.2)) if slide_count > 8 else (1 if slide_count >= 4 else 0)
    if html_only:
        key_ai_target = 0
        route_adjustments.extend(
            [
                "semantic_html_only: requested formats are HTML-only, so export coverage targets only requested HTML outputs",
                "semantic_html_only: no editable PPTX/PDF/Keynote score caps",
                "semantic_html_only: Codex image_gen is optional unless the project explicitly requests image-led visuals",
                "semantic_html_only: SVG image-slide ratio is not required for DOM/CSS-native decks",
            ]
        )
    codex_runtime = is_codex_runtime()
    codex_native_count = int(assets.get("codex_native_imagegen_count") or 0)
    required_key_image_count = codex_native_count if codex_runtime else int(assets["real_imagegen_count"])
    key_image_requirement_label = "Codex-native image_gen assets" if codex_runtime else "real generated assets"
    real_image_ratio = ratio(float(required_key_image_count), max(1.0, float(key_ai_target or 1)))
    non_ai_terminal_visual_ratio = ratio(float(assets["source_or_web_count"]), max(1.0, float(slide_count or 1)))
    primary_media_target = min(slide_count, max(3, round(slide_count * 0.35))) if media_expectation["expected"] else 0
    primary_media_score = 100 if not media_expectation["expected"] else pct(
        ratio(float(assets["primary_media_slide_count"]), float(primary_media_target or 1))
    )
    source_ratio = float(sources["cited_slide_ratio"])
    source_visual_ratio = 1.0
    if sources["image_candidates"]:
        source_visual_ratio = ratio(
            float(assets["source_or_web_count"]),
            max(1.0, min(float(sources["image_candidates"]), float(slide_count or 1))),
        )
    diversity_base = min(1.0, float(image_diversity.get("unique_ratio") or 0.0))
    diversity_penalty = min(
        0.65,
        0.18 * float(image_diversity.get("adjacent_repeat_count") or 0)
        + 0.10 * float(image_diversity.get("overused_count") or 0),
    )
    image_diversity_score = pct(max(0.0, diversity_base - diversity_penalty))
    structural_variety_score = pct(ratio(float(rhythm.get("unique_structural_fingerprints") or 0), fp_target))
    structural_variety_evidence = (
        f"{rhythm.get('unique_structural_fingerprints', 0)} unique SVG fingerprints; target {fp_target}"
    )
    image_presence_score = pct(min(terminal_image_ratio, svg_image_ratio) / image_ratio_target if image_ratio_target else 0)
    image_presence_evidence = (
        f"terminal image slides {assets['terminal_slide_count']}/{slide_count}, "
        f"SVG image slides {rhythm.get('svg_image_slides', 0)}/{slide_count}, "
        f"baseline target ratio {image_ratio_target:.2f}"
    )
    real_image_generation_score = pct(real_image_ratio)
    real_image_generation_evidence = (
        f"{key_image_requirement_label} {required_key_image_count}/{key_ai_target}; "
        f"real generated total {assets['real_imagegen_count']}; "
        f"Codex-native {codex_native_count}; "
        f"AI asset rows {assets['ai_count']}; procedural fallback {assets['procedural_fallback_count']}; "
        f"trusted source/web/user visuals {assets['trusted_source_or_web_count']}/{slide_count}; "
        f"local source-derived visuals {assets['local_source_derived_count']}"
    )
    if html_only:
        structural_variety_score = pct(
            ratio(float(max(layout_exec["contract_layout_count"], layout_exec["plan_layout_count"])), fp_target)
        )
        structural_variety_evidence = (
            f"semantic HTML layout ids {max(layout_exec['contract_layout_count'], layout_exec['plan_layout_count'])}; "
            f"SVG fingerprints are optional for this route; target {fp_target}"
        )
        if media_expectation["expected"]:
            image_presence_score = pct(min(1.0, terminal_image_ratio / image_ratio_target if image_ratio_target else 1.0))
            image_presence_evidence = (
                f"HTML-only image-rich subject: terminal image slides {assets['terminal_slide_count']}/{slide_count}; "
                f"baseline target ratio {image_ratio_target:.2f}"
            )
        else:
            image_presence_score = 100 if (project / "html_delivery_manifest.json").exists() else 0
            image_presence_evidence = (
                "semantic HTML-only route uses DOM/CSS visual system; image density is advisory unless the subject is image-rich"
            )
        real_image_generation_score = 100
        real_image_generation_evidence = (
            "semantic HTML-only route does not require AI image generation unless visual_asset_manifest explicitly requests it"
        )
        if not media_expectation["expected"]:
            image_diversity_score = 100

    visual_rhythm_score = pct(ratio(float(rhythm.get("unique_art_directions") or 0), art_target))
    visual_rhythm_evidence = f"{rhythm.get('unique_art_directions', 0)} unique art directions; target {art_target}"
    style_execution_score = int(style_exec.get("score") or 0)
    style_execution_evidence = (
        f"style {style_exec.get('selected_style', {}).get('id', '')}; "
        f"audit score {style_exec.get('score', 0)}"
    )
    if html_only:
        html_layout_signal = max(layout_exec["contract_layout_count"], layout_exec["plan_layout_count"])
        visual_rhythm_score = max(visual_rhythm_score, pct(ratio(float(html_layout_signal), art_target)))
        visual_rhythm_evidence = (
            f"semantic HTML layout rhythm {html_layout_signal} layout ids; "
            f"SVG art-direction report is optional for this route; target {art_target}"
        )
        upstream_style_fit = int(upstream_creation.get("scores", {}).get("style_fit") or 0)
        if upstream_style_fit > style_execution_score:
            style_execution_score = upstream_style_fit
            style_execution_evidence = (
                f"semantic HTML route uses style_fit_audit as primary style evidence; score {upstream_style_fit}"
            )
            route_adjustments.append(
                "semantic_html_only: style execution category uses style_fit_audit when SVG-specific style_execution_audit is weaker"
            )

    categories = [
        {
            "id": "visual_rhythm",
            "weight": 18,
            "score": visual_rhythm_score,
            "evidence": visual_rhythm_evidence,
        },
        {
            "id": "structural_variety",
            "weight": 12,
            "score": structural_variety_score,
            "evidence": structural_variety_evidence,
        },
        {
            "id": "layout_pattern_execution",
            "weight": 12,
            "score": pct(
                min(
                    ratio(float(layout_exec["contract_layout_count"]), max(3.0, min(float(slide_count), 6.0))),
                    ratio(float(layout_exec["rich_component_count"]), max(2.0, min(float(slide_count), 5.0))),
                )
            ),
            "evidence": (
                f"{layout_exec['contract_layout_count']} layout ids, "
                f"{layout_exec['rich_component_count']} rich component types; "
                f"components: {', '.join(layout_exec['component_types'][:8])}"
            ),
        },
        {
            "id": "style_execution",
            "weight": 10,
            "score": style_execution_score,
            "evidence": style_execution_evidence,
        },
        {
            "id": "upstream_creation_quality",
            "weight": 12,
            "score": int(upstream_creation.get("score") or 0),
            "evidence": (
                "content outline {content_outline}, element plan {element_plan}, style fit {style_fit}; "
                "missing: {missing}"
            ).format(
                content_outline=upstream_creation.get("scores", {}).get("content_outline", 0),
                element_plan=upstream_creation.get("scores", {}).get("element_plan", 0),
                style_fit=upstream_creation.get("scores", {}).get("style_fit", 0),
                missing=", ".join(upstream_creation.get("missing", [])),
            ),
        },
        {
            "id": "image_presence",
            "weight": 16,
            "score": image_presence_score,
            "evidence": image_presence_evidence,
        },
        {
            "id": "primary_media_evidence",
            "weight": 12,
            "score": primary_media_score,
            "evidence": (
                (
                    f"primary media slides {assets['primary_media_slide_count']}/{primary_media_target} target; "
                    f"primary media assets {assets['primary_media_count']}; "
                    f"background-only assets {assets['background_terminal_count']}; "
                    "media expectation tokens: " + ", ".join(media_expectation["matched_tokens"][:8])
                )
                if media_expectation["expected"]
                else "no image-rich subject signal detected"
            ),
        },
        {
            "id": "image_diversity",
            "weight": 8,
            "score": image_diversity_score,
            "evidence": (
                f"unique images {image_diversity.get('unique_image_count', 0)}/"
                f"{image_diversity.get('target_unique_count', 0)} target; "
                f"adjacent repeats {image_diversity.get('adjacent_repeat_count', 0)}; "
                f"max reuse {image_diversity.get('max_reuse_count', 0)}"
            ),
        },
        {
            "id": "real_image_generation",
            "weight": 16,
            "score": real_image_generation_score,
            "evidence": real_image_generation_evidence,
        },
        {
            "id": "source_grounding",
            "weight": 14,
            "score": pct(min(1.0, source_ratio)),
            "evidence": f"source-backed slides {sources['cited_slides']}/{slide_count}; source cards {sources['source_cards']}",
        },
        {
            "id": "source_visual_usage",
            "weight": 8,
            "score": pct(min(1.0, source_visual_ratio)),
            "evidence": (
                f"source/web/user visual assets {assets['source_or_web_count']}; "
                f"source image candidates {sources['image_candidates']}"
            ),
        },
        {
            "id": "image_resolution_fit",
            "weight": 10,
            "score": pct(
                1.0
                - min(
                    1.0,
                    (
                        float(image_resolution.get("underresolved_count") or 0)
                        + float(image_resolution.get("severe_underresolved_count") or 0)
                    )
                    / max(1.0, float(image_resolution.get("checked_count") or slide_count or 1)),
                )
            ),
            "evidence": (
                f"{image_resolution.get('underresolved_count', 0)} underresolved image placements; "
                f"{image_resolution.get('severe_underresolved_count', 0)} severe; "
                f"checked {image_resolution.get('checked_count', 0)}"
            ),
        },
        {
            "id": "export_coverage",
            "weight": 12,
            "score": pct(min(1.0, exports["successful_format_count"] / max(1.0, float(exports["target_format_count"])))),
            "evidence": (
                "successful formats: "
                + ", ".join(exports["successful_formats"])
                + f"; target {exports['target_format_count']}"
            ),
        },
        {
            "id": "speaker_notes_and_contracts",
            "weight": 12,
            "score": pct(
                (
                    int((project / "content_contract.json").exists())
                    + int((project / "visual_contract.json").exists())
                    + int((project / "spec_lock.json").exists())
                    + int((project / "image_art_direction.json").exists())
                )
                / 4.0
            ),
            "evidence": "content_contract, visual_contract, spec_lock, image_art_direction presence",
        },
    ]
    weighted = sum(item["weight"] * item["score"] for item in categories) / sum(item["weight"] for item in categories)
    raw_total = int(round(weighted))
    score_caps: list[str] = []
    total = raw_total
    if assets["procedural_fallback_count"] and not html_only:
        total = min(total, 79)
        score_caps.append("procedural fallback assets cap score at 79")
    if key_ai_target and required_key_image_count < key_ai_target:
        total = min(total, 82 if required_key_image_count else 69)
        score_caps.append(f"{key_image_requirement_label} {required_key_image_count}/{key_ai_target} cap score")
    if image_resolution.get("severe_underresolved_count", 0):
        total = min(total, 88)
        score_caps.append("severe image upscaling caps score at 88")
    if image_diversity.get("adjacent_repeat_count", 0):
        total = min(total, 90)
        score_caps.append("adjacent repeated image assets cap score at 90")
    if media_expectation["expected"] and primary_media_target and assets["primary_media_slide_count"] < min(3, primary_media_target):
        total = min(total, 82)
        score_caps.append("image-rich subject with insufficient primary media assets caps score at 82")
    if slide_count >= 8 and not exports["has_pdf"] and not html_only:
        total = min(total, 89)
        score_caps.append("missing PDF export caps score at 89")
    if slide_count >= 8 and not exports["has_pptx"] and not html_only:
        total = min(total, 69)
        score_caps.append("missing editable PPTX caps score at 69")
    failures = []
    warnings = []
    if total < min_score:
        failures.append(f"benchmark score {total} below target {min_score}")
    if assets["procedural_fallback_count"] and not html_only:
        warnings.append(
            f"{assets['procedural_fallback_count']} AI image asset(s) are procedural fallback, not final-quality image generation"
        )
    if key_ai_target and required_key_image_count < key_ai_target:
        if codex_runtime:
            warnings.append(
                f"Codex-native key-page images are insufficient: {codex_native_count}/{key_ai_target}; "
                "use Codex image_gen and record generator=codex-native-image_gen with generated_asset_source. "
                "Content-only slides, external-provider-only images, source/downloaded images, SVG, and shapes do not satisfy this gate"
            )
        else:
            warnings.append(
                f"real generated key-page images are insufficient: {assets['real_imagegen_count']}/{key_ai_target}; "
                "source/downloaded images may support evidence pages but do not replace key-page image generation"
            )
    if sources["image_candidates"] and not assets["source_or_web_count"]:
        warnings.append("source image candidates exist but no source/web/user visual assets are used")
    if image_resolution.get("underresolved_count", 0):
        warnings.append(
            f"{image_resolution['underresolved_count']} image placement(s) upscale source pixels beyond the quality threshold"
        )
    if image_diversity_score < 80:
        warnings.append(
            "image diversity is weak: "
            f"{image_diversity.get('unique_image_count', 0)} unique image(s), "
            f"{image_diversity.get('adjacent_repeat_count', 0)} adjacent repeat(s), "
            f"{image_diversity.get('overused_count', 0)} overused asset(s)"
        )
    if media_expectation["expected"] and primary_media_score < 80:
        warnings.append(
            "primary media evidence is weak for an image-rich subject: "
            f"{assets['primary_media_slide_count']} primary-media slide(s), "
            f"{assets['background_terminal_count']} background-only asset(s)"
        )
    if style_execution_score < 75:
        warnings.append(f"style execution audit is weak: score {style_execution_score}")
    if int(upstream_creation.get("score") or 0) < 75:
        warnings.append(f"upstream creation audit is weak: score {upstream_creation.get('score', 0)}")
    if not exports["has_pdf"] and not html_only:
        warnings.append("PDF export missing; full multi-format target includes PDF")
    if exports.get("keynote_targeted") and not exports["has_keynote"] and not html_only:
        warnings.append("Keynote export missing; full multi-format target includes Keynote where feasible")
    ppt_master_ready = (
        not html_only
        and
        total >= max(85, min_score)
        and not assets["procedural_fallback_count"]
        and exports["has_pptx"]
        and exports["has_html"]
        and exports["has_pdf"]
        and (exports["has_keynote"] or not exports.get("keynote_targeted"))
        and int(upstream_creation.get("score") or 0) >= 75
        and int(style_exec.get("score") or 0) >= 75
        and ratio(float(rhythm.get("unique_art_directions") or 0), art_target) >= 1.0
        and (not media_expectation["expected"] or primary_media_score >= 80)
        and (not key_ai_target or required_key_image_count >= key_ai_target)
    )
    html_ready = html_only and total >= min_score and exports["has_html"]
    if ppt_master_ready:
        readiness = "ppt_master_ready"
    elif html_ready:
        readiness = "semantic_html_ready"
    elif total >= min_score:
        readiness = "production_candidate"
    else:
        readiness = "draft_or_incomplete"
    return {
        "schema_version": "1.0.0",
        "ok": not failures,
        "score": total,
        "raw_score": raw_total,
        "score_caps": score_caps,
        "route_adjustments": route_adjustments,
        "target_score": min_score,
        "readiness": readiness,
        "ppt_master_ready": ppt_master_ready,
        "project": str(project),
        "slide_count": slide_count,
        "baseline": baseline,
        "categories": categories,
        "stats": {
            "rhythm": rhythm,
            "layout_execution": layout_exec,
            "assets": assets,
            "sources": sources,
            "exports": exports,
            "image_resolution": image_resolution,
            "image_diversity": image_diversity,
            "media_expectation": media_expectation,
            "style_execution": style_exec,
            "upstream_creation": upstream_creation,
            "codex_runtime": codex_runtime,
            "delivery_route": route_info,
        },
        "failures": failures,
        "warnings": warnings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Deck Quality Benchmark",
        "",
        f"- Score: `{report['score']}` / 100",
        f"- Raw score: `{report.get('raw_score', report['score'])}` / 100",
        f"- Target: `{report['target_score']}`",
        f"- Readiness: `{report.get('readiness', '')}`",
        f"- OK: `{str(report['ok']).lower()}`",
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
    if report.get("score_caps"):
        lines.extend(["", "## Score Caps", ""])
        lines.extend(f"- {item}" for item in report["score_caps"])
    if report.get("route_adjustments"):
        lines.extend(["", "## Route Adjustments", ""])
        lines.extend(f"- {item}" for item in report["route_adjustments"])
    baseline = report.get("baseline", {})
    lines.extend(
        [
            "",
            "## Baseline",
            "",
            f"- Catalog: `{baseline.get('catalog', '')}`",
            f"- Projects: `{baseline.get('project_count', '')}`",
            f"- Median image refs per slide: `{baseline.get('median_spec_image_refs_per_slide', '')}`",
            "",
            "> This benchmark uses learning statistics only. It does not copy upstream templates, images, wording, or slide designs.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Generated qiaomu-ppt project directory.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG, help="ppt-master learning catalog path.")
    parser.add_argument("--output", type=Path, help="JSON report output. Default: <project>/reports/deck_quality_benchmark.json")
    parser.add_argument("--markdown", type=Path, help="Markdown report output. Default: <project>/reports/deck_quality_benchmark.md")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum score for ok=true.")
    parser.add_argument("--enforce", action="store_true", help="Exit non-zero when score is below --min-score.")
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output or project / "reports" / "deck_quality_benchmark.json"
    markdown = args.markdown or project / "reports" / "deck_quality_benchmark.md"
    report = score_project(project, args.catalog, args.min_score)
    write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.enforce and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
