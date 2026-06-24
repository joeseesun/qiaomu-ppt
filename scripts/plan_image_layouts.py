#!/usr/bin/env python3
"""Plan image/text slots from source image aspect ratios and target canvas formats."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception as exc:  # pragma: no cover - reported at runtime
    Image = None  # type: ignore[assignment]
    PIL_IMPORT_ERROR = exc
else:
    PIL_IMPORT_ERROR = None


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
DATA_FORMATS_PATH = Path(__file__).resolve().parent.parent / "data" / "canvas_format_specs.json"

CANVAS_FORMATS: dict[str, dict[str, Any]] = {
    "ppt169": {
        "label": "PPT 16:9",
        "width": 1280,
        "height": 720,
        "ratio": "16:9",
        "use_case": "business presentations, meetings, modern screens",
        "margins": {"left": 60, "right": 60, "top": 60, "bottom": 60},
        "content": {"x": 60, "y": 80, "w": 1160, "h": 600},
        "title_height": 60,
        "gap": 20,
        "min_text_top_bottom": 150,
        "min_text_left_right": 280,
    },
    "ppt43": {
        "label": "PPT 4:3",
        "width": 1024,
        "height": 768,
        "ratio": "4:3",
        "use_case": "traditional projectors, academic talks",
        "margins": {"left": 50, "right": 50, "top": 50, "bottom": 50},
        "content": {"x": 50, "y": 70, "w": 924, "h": 608},
        "title_height": 60,
        "gap": 20,
        "min_text_top_bottom": 150,
        "min_text_left_right": 280,
    },
    "xiaohongshu": {
        "label": "Xiaohongshu / RED 3:4",
        "width": 1242,
        "height": 1660,
        "ratio": "3:4",
        "use_case": "image-text sharing, knowledge posts",
        "margins": {"left": 60, "right": 60, "top": 80, "bottom": 80},
        "content": {"x": 60, "y": 100, "w": 1122, "h": 1500},
        "title_height": 80,
        "gap": 30,
        "min_text_top_bottom": 260,
        "min_text_left_right": 300,
    },
    "moments": {
        "label": "WeChat Moments / Instagram 1:1",
        "width": 1080,
        "height": 1080,
        "ratio": "1:1",
        "use_case": "square posters, brand showcases",
        "margins": {"left": 60, "right": 60, "top": 60, "bottom": 60},
        "content": {"x": 60, "y": 80, "w": 960, "h": 960},
        "title_height": 60,
        "gap": 30,
        "min_text_top_bottom": 220,
        "min_text_left_right": 280,
    },
    "story": {
        "label": "Story / TikTok 9:16",
        "width": 1080,
        "height": 1920,
        "ratio": "9:16",
        "use_case": "vertical stories, short-video covers, phone screens",
        "margins": {"left": 60, "right": 60, "top": 120, "bottom": 180},
        "content": {"x": 60, "y": 140, "w": 960, "h": 1620},
        "title_height": 80,
        "gap": 30,
        "min_text_top_bottom": 300,
        "min_text_left_right": 300,
    },
    "wechat": {
        "label": "WeChat Article Header",
        "width": 900,
        "height": 383,
        "ratio": "2.35:1",
        "use_case": "WeChat article cover images",
        "margins": {"left": 40, "right": 40, "top": 40, "bottom": 40},
        "content": {"x": 40, "y": 50, "w": 820, "h": 303},
        "title_height": 40,
        "gap": 18,
        "min_text_top_bottom": 90,
        "min_text_left_right": 220,
    },
    "banner": {
        "label": "Landscape Banner",
        "width": 1920,
        "height": 1080,
        "ratio": "16:9",
        "use_case": "web banners, digital screens",
        "margins": {"left": 96, "right": 96, "top": 90, "bottom": 90},
        "content": {"x": 96, "y": 120, "w": 1728, "h": 870},
        "title_height": 90,
        "gap": 36,
        "min_text_top_bottom": 220,
        "min_text_left_right": 360,
    },
    "a4": {
        "label": "A4 Print",
        "width": 1240,
        "height": 1754,
        "ratio": "1:sqrt(2)",
        "use_case": "print posters, flyers",
        "margins": {"left": 80, "right": 80, "top": 100, "bottom": 110},
        "content": {"x": 80, "y": 130, "w": 1080, "h": 1514},
        "title_height": 90,
        "gap": 30,
        "min_text_top_bottom": 300,
        "min_text_left_right": 300,
    },
}

CANVAS_ALIASES = {
    "16:9": "ppt169",
    "ppt16:9": "ppt169",
    "ppt-16-9": "ppt169",
    "wide": "ppt169",
    "4:3": "ppt43",
    "ppt4:3": "ppt43",
    "ppt-4-3": "ppt43",
    "xhs": "xiaohongshu",
    "red": "xiaohongshu",
    "小红书": "xiaohongshu",
    "wechat-moments": "moments",
    "wechat_moments": "moments",
    "instagram": "moments",
    "ig": "moments",
    "square": "moments",
    "tiktok": "story",
    "portrait": "story",
    "vertical": "story",
    "wechat-header": "wechat",
    "wechat_article": "wechat",
}


def normalize_loaded_format(item: dict[str, Any]) -> dict[str, Any]:
    width = int(item["width"])
    height = int(item["height"])
    content = item.get("content") or item.get("content_area") or {}
    x = int(content.get("x", 0))
    y = int(content.get("y", 0))
    w = int(content.get("w", width))
    h = int(content.get("h", height))
    return {
        "label": item.get("label") or f"{width}x{height}",
        "width": width,
        "height": height,
        "ratio": item.get("ratio") or f"{width}:{height}",
        "use_case": item.get("use_case", ""),
        "margins": item.get("margins")
        or {"left": x, "right": max(0, width - x - w), "top": y, "bottom": max(0, height - y - h)},
        "content": {"x": x, "y": y, "w": w, "h": h},
        "title_height": int(item.get("title_height") or max(40, round(height * 0.08))),
        "gap": int(item.get("gap") or 20),
        "min_text_top_bottom": int(item.get("min_text_top_bottom") or max(120, round(height * 0.18))),
        "min_text_left_right": int(item.get("min_text_left_right") or max(240, round(width * 0.22))),
    }


def available_canvas_formats() -> dict[str, dict[str, Any]]:
    if DATA_FORMATS_PATH.exists():
        try:
            payload = json.loads(DATA_FORMATS_PATH.read_text(encoding="utf-8"))
            formats = payload.get("formats") if isinstance(payload, dict) else None
            if isinstance(formats, dict):
                return {
                    str(key): normalize_loaded_format(value)
                    for key, value in formats.items()
                    if isinstance(value, dict) and "width" in value and "height" in value
                }
        except Exception:
            pass
    return CANVAS_FORMATS


def parse_canvas(value: str) -> tuple[int, int]:
    normalized = value.lower().replace("x", ",").replace(":", ",")
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("canvas must look like 1920x1080")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("canvas values must be integers") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("canvas values must be positive")
    return width, height


def normalize_format(value: str) -> str:
    key = str(value or "").strip().lower()
    return CANVAS_ALIASES.get(key, key)


def custom_canvas_spec(canvas: tuple[int, int], margins: tuple[int, int, int, int], gap: int) -> dict[str, Any]:
    width, height = canvas
    left, top, right, bottom = margins
    content = {"x": left, "y": top, "w": width - left - right, "h": height - top - bottom}
    if content["w"] <= 0 or content["h"] <= 0:
        raise ValueError("margins leave no usable canvas area")
    return {
        "label": f"Custom {width}x{height}",
        "width": width,
        "height": height,
        "ratio": f"{width}:{height}",
        "use_case": "custom canvas",
        "margins": {"left": left, "right": right, "top": top, "bottom": bottom},
        "content": content,
        "title_height": max(40, round(height * 0.08)),
        "gap": gap,
        "min_text_top_bottom": max(120, round(height * 0.18)),
        "min_text_left_right": max(240, round(width * 0.22)),
    }


def get_canvas_spec(format_key: str, canvas: tuple[int, int] | None, margins: tuple[int, int, int, int], gap: int) -> tuple[str, dict[str, Any]]:
    normalized = normalize_format(format_key)
    if canvas:
        return "custom", custom_canvas_spec(canvas, margins, gap)
    formats = available_canvas_formats()
    if normalized not in formats:
        known = ", ".join(sorted(formats))
        raise argparse.ArgumentTypeError(f"unknown canvas format `{format_key}`; known formats: {known}")
    spec = json.loads(json.dumps(formats[normalized]))
    return normalized, spec


def parse_margin(value: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) == 1:
        margins = [int(parts[0])] * 4
    elif len(parts) == 2:
        vertical, horizontal = int(parts[0]), int(parts[1])
        margins = [horizontal, vertical, horizontal, vertical]
    elif len(parts) == 4:
        margins = [int(part) for part in parts]
    else:
        raise argparse.ArgumentTypeError("margin must be one, two, or four comma-separated integers")
    if any(item < 0 for item in margins):
        raise argparse.ArgumentTypeError("margins must be non-negative")
    return tuple(margins)  # type: ignore[return-value]


def image_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() in IMAGE_EXTENSIONS else []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def image_size(path: Path) -> tuple[int, int]:
    if Image is None:
        raise RuntimeError(f"Pillow is unavailable: {PIL_IMPORT_ERROR}")
    with Image.open(path) as img:
        return int(img.width), int(img.height)


def rect(x: int, y: int, w: int, h: int) -> dict[str, int]:
    return {"x": x, "y": y, "w": w, "h": h}


def canvas_orientation(spec: dict[str, Any]) -> str:
    width = int(spec["width"])
    height = int(spec["height"])
    if math.isclose(width / height, 1.0, rel_tol=0.03):
        return "square"
    return "portrait" if height > width else "landscape"


def choose_layout(ratio: float, spec: dict[str, Any], text_volume: str) -> tuple[str, str, list[str]]:
    orientation = canvas_orientation(spec)
    if orientation == "portrait":
        if ratio >= 0.8:
            return (
                "top_image_bottom_text",
                "portrait canvas keeps side-by-side columns too narrow; use top image and stacked text",
                ["portrait_override", "complete_image_display"],
            )
        return (
            "left_image_right_text",
            "portrait or extreme-portrait source image can share a tall canvas with a narrow text rail",
            ["portrait_canvas_extreme_image", "complete_image_display"],
        )
    if ratio > 2.0:
        return (
            "top_image_bottom_text",
            "ultra-wide images need width; top-bottom preserves the full image without a square container",
            ["ultra_wide_source", "complete_image_display"],
        )
    if ratio >= 1.5:
        if text_volume == "high":
            return (
                "left_image_right_text",
                "wide boundary image but text volume is high; switch to side-by-side with constrained image width",
                ["wide_boundary", "text_volume_override"],
            )
        return (
            "top_image_bottom_text",
            "wide images need width; use a horizontal image band and text below",
            ["wide_source", "complete_image_display"],
        )
    if ratio >= 1.2:
        return (
            "left_image_right_text",
            "standard landscape images can share the canvas with a readable text column",
            ["standard_landscape_source", "complete_image_display"],
        )
    if ratio >= 0.8:
        return (
            "left_image_right_text",
            "near-square images work well as a large left proof object",
            ["squareish_source", "complete_image_display"],
        )
    return (
        "left_image_right_text",
        "portrait images need height; keep the image tall and move text to the side",
        ["portrait_source", "complete_image_display"],
    )


def slot_plan(
    width: int,
    height: int,
    spec: dict[str, Any],
    *,
    text_volume: str,
    narrative_intent: str,
) -> dict[str, Any]:
    content = spec["content"]
    safe_x = int(content["x"])
    safe_y = int(content["y"])
    safe_w = int(content["w"])
    safe_h = int(content["h"])
    gap = int(spec["gap"])
    min_tb = int(spec["min_text_top_bottom"])
    min_lr = int(spec["min_text_left_right"])
    ratio = width / height
    orientation = canvas_orientation(spec)

    if narrative_intent != "side-by-side":
        image_area = rect(0, 0, int(spec["width"]), int(spec["height"]))
        if narrative_intent == "accent":
            image_area = rect(safe_x, safe_y, round(safe_w * 0.28), round(safe_h * 0.28))
        return {
            "source_width": width,
            "source_height": height,
            "aspect_ratio": round(ratio, 4),
            "canvas_orientation": orientation,
            "narrative_intent": narrative_intent,
            "recommended_layout": f"{narrative_intent}_image",
            "layout_type": "intent_driven",
            "rationale": "ratio-to-split calculation applies only to side-by-side intent; this image should be composed by narrative role",
            "image_area": image_area,
            "text_area": rect(safe_x, safe_y, safe_w, safe_h),
            "fit": "cover" if narrative_intent in {"hero", "atmosphere"} else "contain",
            "preserve_aspect_ratio": "xMidYMid slice" if narrative_intent in {"hero", "atmosphere"} else "xMidYMid meet",
            "overflow_policy": "hero/atmosphere may crop; editable text remains in safe area",
            "reading_path": "image as canvas -> editable foreground",
            "pattern_candidates": [
                "image_layout_01_full_bleed_background",
                "image_layout_38_image_as_canvas_annotations",
                "ITL03",
            ],
            "decision_signals": ["intent_not_side_by_side"],
            "native_overlay_policy": "keep labels, charts, tables, Chinese text, callouts, and numeric proof in editable SVG/PPTX objects",
        }

    layout, rationale, signals = choose_layout(ratio, spec, text_volume)

    if layout == "top_image_bottom_text":
        image_w = safe_w
        image_h = round(image_w / ratio)
        if safe_h - image_h - gap < min_tb:
            max_image_h = safe_h - gap - min_tb
            if max_image_h > min_tb:
                image_h = max_image_h
                image_w = min(safe_w, round(image_h * ratio))
                signals.append("top_bottom_image_width_reduced_for_text")
            else:
                layout = "left_image_right_text"
                signals.append("top_bottom_failed_min_text_height")
        else:
            signals.append("top_bottom_validated")

    if layout == "top_image_bottom_text":
        text_h = safe_h - image_h - gap
        image_x = safe_x + round((safe_w - image_w) / 2)
        image_area = rect(image_x, safe_y, image_w, image_h)
        text_area = rect(safe_x, safe_y + image_h + gap, safe_w, text_h)
        reading_path = "image -> title/text below -> annotations"
        pattern_candidates = [
            "image_layout_05_top_band_image_bottom_columns",
            "image_layout_14_horizontal_banner",
            "ITL05",
            "ITL07",
            "L03",
            "L20",
        ]
        layout_type = "top_bottom_split"
    else:
        if ratio >= 1.5:
            image_w = min(round(safe_w * 0.70), safe_w - gap - min_lr)
            image_h = round(image_w / ratio)
            image_y = safe_y + round((safe_h - image_h) / 2)
            signals.append("left_right_width_constrained")
        else:
            image_h = safe_h
            image_w = round(image_h * ratio)
            if safe_w - image_w - gap < min_lr:
                image_w = safe_w - gap - min_lr
                image_h = round(image_w / ratio)
                signals.append("left_right_image_reduced_for_text")
            else:
                signals.append("left_right_height_first")
            image_y = safe_y + round((safe_h - image_h) / 2)
        text_w = safe_w - image_w - gap
        image_area = rect(safe_x, image_y, image_w, image_h)
        text_area = rect(safe_x + image_w + gap, safe_y, text_w, safe_h)
        reading_path = "image proof -> right title/takeaway -> supporting points"
        pattern_candidates = [
            "image_layout_02_left_third_or_left_proof",
            "image_layout_38_image_as_canvas_annotations",
            "image_layout_45_hotspots_sidebar_legend",
            "ITL01",
            "ITL10",
            "L05",
            "L33",
        ]
        layout_type = "left_right_split"

    return {
        "source_width": width,
        "source_height": height,
        "aspect_ratio": round(ratio, 4),
        "canvas_orientation": orientation,
        "narrative_intent": narrative_intent,
        "recommended_layout": layout,
        "layout_type": layout_type,
        "rationale": rationale,
        "image_area": image_area,
        "text_area": text_area,
        "fit": "contain",
        "preserve_aspect_ratio": "xMidYMid meet",
        "overflow_policy": "clip_or_fail",
        "reading_path": reading_path,
        "pattern_candidates": pattern_candidates,
        "decision_signals": signals,
        "validation": {
            "text_area_min_height_px": min_tb,
            "text_area_min_width_px": min_lr,
            "top_bottom_text_height_ok": text_area["h"] >= min_tb if layout_type == "top_bottom_split" else None,
            "left_right_text_width_ok": text_area["w"] >= min_lr if layout_type == "left_right_split" else None,
            "image_whitespace_policy": "image should display completely with <=10% avoidable slot whitespace; recalculate or switch layout if violated",
        },
        "native_overlay_policy": "keep labels, charts, tables, Chinese text, callouts, and numeric proof in editable SVG/PPTX objects",
    }


def multi_image_plan(records: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    count = len(records)
    content = spec["content"]
    safe_x = int(content["x"])
    safe_y = int(content["y"])
    safe_w = int(content["w"])
    safe_h = int(content["h"])
    gap = int(spec["gap"])
    ratios = [float(item["aspect_ratio"]) for item in records]
    if count < 2:
        return {"applies": False, "reason": "Need at least two images for a multi-image plan."}
    if count == 2:
        both_portrait = all(ratio < 0.8 for ratio in ratios)
        layout = "stacked_1x2" if both_portrait else "side_by_side_2x1"
        rows, cols = (2, 1) if both_portrait else (1, 2)
    elif count == 3:
        layout = "one_large_plus_two_small"
        rows, cols = 2, 2
    else:
        cols = 2 if count <= 4 else 3
        rows = math.ceil(min(count, 6) / cols)
        layout = f"grid_{cols}x{rows}"
    if layout == "one_large_plus_two_small":
        large_w = round((safe_w - gap) * 0.55)
        small_w = safe_w - large_w - gap
        small_h = round((safe_h - gap) / 2)
        cells = [
            {"slot_id": "image_1_large", **rect(safe_x, safe_y, large_w, safe_h)},
            {"slot_id": "image_2_small", **rect(safe_x + large_w + gap, safe_y, small_w, small_h)},
            {"slot_id": "image_3_small", **rect(safe_x + large_w + gap, safe_y + small_h + gap, small_w, small_h)},
        ]
    else:
        cell_w = round((safe_w - (cols - 1) * gap) / cols)
        cell_h = round((safe_h - (rows - 1) * gap) / rows)
        cells = []
        for idx in range(min(count, rows * cols)):
            row = idx // cols
            col = idx % cols
            cells.append({"slot_id": f"image_{idx + 1}", **rect(safe_x + col * (cell_w + gap), safe_y + row * (cell_h + gap), cell_w, cell_h)})
    return {
        "applies": True,
        "image_count": count,
        "layout": layout,
        "cells": cells,
        "preserve_aspect_ratio": "xMidYMid meet",
        "pattern_candidates": ["image_layout_47_small_multiples", "image_layout_48_side_by_side_comparison", "image_layout_49_asymmetric_collage", "image_layout_50_tiled_grid"],
        "policy": "Use identical crop/fit logic within image groups; keep captions and comparison labels editable.",
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Image Layout Plan",
        "",
        f"- Input: `{plan['input']}`",
        f"- Format: `{plan['canvas_format']}` / {plan['canvas']['label']} / `{plan['canvas']['width']}x{plan['canvas']['height']}`",
        f"- Content area: `{plan['content_area']['x']},{plan['content_area']['y']} {plan['content_area']['w']}x{plan['content_area']['h']}`",
        f"- Narrative intent: `{plan['narrative_intent']}`",
        f"- Images inspected: {plan['image_count']}",
        "",
        "| Image | Ratio | Layout | Image area | Text area | Fit | Notes |",
        "|---|---:|---|---|---|---|---|",
    ]
    for item in plan["images"]:
        image_area = item["image_area"]
        text_area = item["text_area"]
        lines.append(
            "| "
            + f"`{Path(item['path']).name}` | {item['aspect_ratio']} | `{item['recommended_layout']}` | "
            + f"`{image_area['x']},{image_area['y']} {image_area['w']}x{image_area['h']}` | "
            + f"`{text_area['x']},{text_area['y']} {text_area['w']}x{text_area['h']}` | "
            + f"`{item['preserve_aspect_ratio']}` | {item['rationale']} |"
        )
    multi = plan.get("multi_image_plan", {})
    if multi.get("applies"):
        lines.extend(["", "## Multi-Image Plan", "", f"- Layout: `{multi['layout']}`", f"- Preserve aspect ratio: `{multi['preserve_aspect_ratio']}`", "", "| Slot | Rect |", "|---|---|"])
        for cell in multi.get("cells", []):
            lines.append(f"| `{cell['slot_id']}` | `{cell['x']},{cell['y']} {cell['w']}x{cell['h']}` |")
    lines.extend(
        [
            "",
            "## Handoff",
            "",
            "- Copy `image_area`, `text_area`, `recommended_layout`, and `preserve_aspect_ratio` into `visual_contract.json`, `spec_lock.json`, or the relevant `visual_asset_manifest.json` rows.",
            "- Use `xMidYMid meet` for source evidence, side-by-side images, formula renders, and multi-image cells.",
            "- Use crop-to-fill only for hero/background/atmosphere images where cropping is intentional.",
            "- Keep titles, captions, labels, data, Chinese text, and callouts editable in foreground SVG/PPTX objects.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def create_plan(
    root: Path,
    *,
    canvas_format: str,
    spec: dict[str, Any],
    text_volume: str,
    narrative_intent: str,
) -> dict[str, Any]:
    paths = image_paths(root)
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in paths:
        try:
            width, height = image_size(path)
            record = slot_plan(width, height, spec, text_volume=text_volume, narrative_intent=narrative_intent)
            record.update(
                {
                    "image_id": path.stem,
                    "path": path.as_posix(),
                    "layout_pattern": record["pattern_candidates"][0],
                }
            )
            records.append(record)
        except Exception as exc:
            errors.append({"path": path.as_posix(), "error": str(exc)})
    return {
        "schema_version": "1.0.0",
        "input": root.as_posix(),
        "canvas_format": canvas_format,
        "canvas": {
            "label": spec["label"],
            "width": spec["width"],
            "height": spec["height"],
            "ratio": spec["ratio"],
            "orientation": canvas_orientation(spec),
            "use_case": spec.get("use_case", ""),
            "viewBox": f"0 0 {spec['width']} {spec['height']}",
        },
        "content_area": spec["content"],
        "safe_margin": spec["margins"],
        "gap": spec["gap"],
        "narrative_intent": narrative_intent,
        "text_volume": text_volume,
        "image_count": len(records),
        "images": records,
        "multi_image_plan": multi_image_plan(records, spec),
        "errors": errors,
        "use_policy": "Copy image_area/text_area into visual_contract.image_slots, visual_asset_manifest rows, or spec_lock.layout_execution_contract.coordinate_slots before rendering.",
        "source_learning": "Inspired by ppt-master's image-layout-spec/canvas-formats split, adapted into Qiaomu-owned format and handoff fields.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan qiaomu-ppt image/text layout slots from image aspect ratios.")
    parser.add_argument("input", help="Image file or directory.")
    parser.add_argument(
        "--format",
        default="ppt169",
        help="Named canvas format: ppt169, ppt43, xiaohongshu/xhs, moments, story, wechat, banner, a4. Default: ppt169.",
    )
    parser.add_argument("--canvas", type=parse_canvas, default=None, help="Custom canvas size such as 1920x1080; overrides --format.")
    parser.add_argument(
        "--safe-margin",
        type=parse_margin,
        default=parse_margin("96,80,96,80"),
        help="Custom safe margins as left,top,right,bottom; used only with --canvas. Default 96,80,96,80.",
    )
    parser.add_argument("--gap", type=int, default=48, help="Custom gap between image and text slots; used only with --canvas. Default 48.")
    parser.add_argument(
        "--intent",
        choices=["side-by-side", "hero", "atmosphere", "accent"],
        default="side-by-side",
        help="Narrative image intent. Ratio-to-split formulas apply to side-by-side only.",
    )
    parser.add_argument("--text-volume", choices=["low", "medium", "high"], default="medium", help="Text volume used for boundary-ratio decisions.")
    parser.add_argument("--output", "-o", help="Write JSON plan to this path.")
    parser.add_argument("--markdown", help="Optional Markdown handoff table path.")
    parser.add_argument("--list-formats", action="store_true", help="Print available canvas formats and exit.")
    args = parser.parse_args()

    if args.list_formats:
        print(json.dumps(available_canvas_formats(), ensure_ascii=False, indent=2))
        return

    canvas_format, spec = get_canvas_spec(args.format, args.canvas, args.safe_margin, args.gap)
    plan = create_plan(
        Path(args.input),
        canvas_format=canvas_format,
        spec=spec,
        text_volume=args.text_volume,
        narrative_intent=args.intent,
    )
    rendered = json.dumps(plan, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    if args.markdown:
        markdown = Path(args.markdown)
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(plan), encoding="utf-8")


if __name__ == "__main__":
    main()
