#!/usr/bin/env python3
"""Optional raster cleanup for NotebookLM lower-right watermarks.

This module adapts the bottom-right ROI detection and patch-healing approach
from Albonire/notebooklm-watermark-remover:
https://github.com/Albonire/notebooklm-watermark-remover

Upstream license: MIT, Copyright (c) 2025 Anderson Fabian Gonzalez Aparicio.

The implementation here is intentionally narrow: it only edits images embedded
under ppt/media when the caller explicitly asks for raster cleanup.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_INTERFACE = "internal-module"


@dataclass
class RasterWatermarkConfig:
    search_margin_x: int = 400
    search_margin_y: int = 120
    watermark_padding: int = 6
    pixel_threshold: int = 22
    dark_text_threshold: int = 210
    light_text_threshold: int = 135
    min_component_area: int = 18
    min_watermark_area: int = 350
    text_match_threshold: float = 0.45
    roi_bottom_bias: float = 0.35
    roi_right_bias: float = 0.45
    scale: float = 3.0
    inpaint_radius: int = 3
    patch_offset_x: int = -80
    patch_offset_y: int = -80
    debug_dir: str = ""


def load_optional_deps() -> tuple[Any | None, Any | None, Any | None, Any | None, Any | None, list[str]]:
    missing: list[str] = []
    try:
        import cv2  # type: ignore
    except Exception:
        cv2 = None
        missing.append("opencv-python-headless")
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None
        missing.append("numpy")
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception:
        Image = ImageDraw = ImageFont = None
        missing.append("Pillow")
    return cv2, np, Image, ImageDraw, ImageFont, missing


def missing_dependency_result(missing: list[str]) -> dict[str, Any]:
    return {
        "status": "missing_dependency",
        "missing": missing,
        "install": "python3 -m pip install opencv-python-headless numpy Pillow",
        "patched_images": 0,
        "attempted_images": 0,
    }


def debug_save(name: str, img: Any, config: RasterWatermarkConfig, cv2: Any) -> None:
    if not config.debug_dir:
        return
    try:
        path = Path(config.debug_dir)
        path.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path / name), img)
    except Exception:
        pass


def render_text_template(
    height: int,
    *,
    Image: Any,
    ImageDraw: Any,
    ImageFont: Any,
    cv2: Any,
    np: Any,
    cache: dict[int, Any],
) -> Any:
    key = max(10, int(height))
    if key in cache:
        return cache[key]

    font_size = max(12, int(key * 1.15))
    canvas_w = max(180, font_size * 14)
    canvas_h = max(40, font_size * 3)
    img = Image.new("L", (canvas_w, canvas_h), 255)
    draw = ImageDraw.Draw(img)

    font = None
    for font_path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "NotebookLM", font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    y = max(4, (canvas_h - text_h) // 2 - bbox[1])
    draw.text((8, y), "NotebookLM", fill=0, font=font)

    arr = np.array(img)
    _, binary = cv2.threshold(arr, 200, 255, cv2.THRESH_BINARY_INV)
    ys, xs = np.where(binary > 0)
    if len(xs) == 0 or len(ys) == 0:
        template = np.zeros((10, 80), dtype=np.uint8)
    else:
        template = binary[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    cache[key] = template
    return template


def template_match_text(
    roi_bgr: Any,
    *,
    config: RasterWatermarkConfig,
    cv2: Any,
    np: Any,
    Image: Any,
    ImageDraw: Any,
    ImageFont: Any,
    cache: dict[int, Any],
) -> tuple[tuple[int, int, int, int] | None, float]:
    height, width = roi_bgr.shape[:2]
    if height < 20 or width < 80:
        return None, 0.0

    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)
    best_score = 0.0
    best_box: tuple[int, int, int, int] | None = None

    start = max(14, height // 5)
    end = max(18, min(height - 2, height // 2 + 20))
    for text_h in range(start, end, 3):
        template = render_text_template(
            text_h,
            Image=Image,
            ImageDraw=ImageDraw,
            ImageFont=ImageFont,
            cv2=cv2,
            np=np,
            cache=cache,
        )
        th, tw = template.shape[:2]
        if th >= height or tw >= width:
            continue
        result = cv2.matchTemplate(gray_eq, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_score:
            x, y = max_loc
            best_score = float(max_val)
            best_box = (int(x), int(y), int(tw), int(th))

    if best_score < config.text_match_threshold:
        return None, best_score
    return best_box, best_score


def extract_dark_candidates(roi_bgr: Any, *, config: RasterWatermarkConfig, cv2: Any, np: Any) -> Any:
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    ksize = max(15, min(41, ((min(gray.shape[:2]) // 5) | 1)))
    bg = cv2.medianBlur(gray, ksize)
    diff_dark = cv2.subtract(bg, gray)
    diff_light = cv2.subtract(gray, bg)
    dark_mask = np.where(gray < config.dark_text_threshold, 255, 0).astype(np.uint8)
    light_mask = np.where(gray > config.light_text_threshold, 255, 0).astype(np.uint8)
    _, diff_mask = cv2.threshold(diff_dark, config.pixel_threshold, 255, cv2.THRESH_BINARY)
    _, light_diff_mask = cv2.threshold(diff_light, config.pixel_threshold, 255, cv2.THRESH_BINARY)
    dark_candidates = cv2.bitwise_and(dark_mask, diff_mask)
    light_candidates = cv2.bitwise_and(light_mask, light_diff_mask)
    mask = cv2.bitwise_or(dark_candidates, light_candidates)

    height, width = gray.shape[:2]
    geom = np.zeros_like(mask)
    x0 = int(width * config.roi_right_bias)
    y0 = int(height * config.roi_bottom_bias)
    geom[y0:height, x0:width] = 255
    mask = cv2.bitwise_and(mask, geom)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask


def component_boxes(mask: Any, *, config: RasterWatermarkConfig, cv2: Any) -> list[tuple[int, int, int, int, int]]:
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    height, width = mask.shape[:2]
    boxes: list[tuple[int, int, int, int, int]] = []
    for idx in range(1, count):
        x, y, w, h, area = stats[idx]
        if area < config.min_component_area:
            continue
        if area > int(height * width * 0.25):
            continue
        boxes.append((int(x), int(y), int(w), int(h), int(area)))
    return boxes


def build_watermark_mask(
    roi_bgr: Any,
    *,
    config: RasterWatermarkConfig,
    cv2: Any,
    np: Any,
    Image: Any,
    ImageDraw: Any,
    ImageFont: Any,
    cache: dict[int, Any],
) -> Any | None:
    height, width = roi_bgr.shape[:2]
    if height < 10 or width < 20:
        return None

    candidate_mask = extract_dark_candidates(roi_bgr, config=config, cv2=cv2, np=np)
    boxes = component_boxes(candidate_mask, config=config, cv2=cv2)
    if not boxes:
        return None

    text_box, _score = template_match_text(
        roi_bgr,
        config=config,
        cv2=cv2,
        np=np,
        Image=Image,
        ImageDraw=ImageDraw,
        ImageFont=ImageFont,
        cache=cache,
    )

    selected_mask = np.zeros((height, width), dtype=np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(candidate_mask, connectivity=8)

    if text_box is None:
        for idx in range(1, count):
            x, y, w, h, area = stats[idx]
            cx = x + w / 2
            cy = y + h / 2
            if cx < width * 0.60 or cy < height * 0.55:
                continue
            if h > height * 0.70 or w > width * 0.80:
                continue
            selected_mask[labels == idx] = 255
    else:
        tx, ty, tw, th = text_box
        pad = config.watermark_padding
        rx0 = max(0, tx - pad)
        ry0 = max(0, ty - pad)
        rx1 = min(width, tx + tw + pad)
        ry1 = min(height, ty + th + pad)
        for idx in range(1, count):
            x, y, w, h, area = stats[idx]
            if area < config.min_component_area:
                continue
            overlaps = not (x + w < rx0 or x > rx1 or y + h < ry0 or y > ry1)
            near = x <= rx1 + 14 and x + w >= rx0 - 18 and y <= ry1 + 10 and y + h >= ry0 - 10
            same_band_left = x < tx and x > width * 0.45 and abs((y + h / 2) - (ty + th / 2)) <= max(18, th)
            if overlaps or near or same_band_left:
                selected_mask[labels == idx] = 255

        text_band = candidate_mask[max(0, ty - 3) : min(height, ty + th + 3), max(0, tx - 4) : min(width, tx + tw + 4)]
        if cv2.countNonZero(selected_mask) < config.min_watermark_area and cv2.countNonZero(text_band) > 40:
            selected_mask[max(0, ty - 3) : min(height, ty + th + 3), max(0, tx - 4) : min(width, tx + tw + 4)] = text_band

    if cv2.countNonZero(selected_mask) < config.min_watermark_area:
        return None

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    selected_mask = cv2.morphologyEx(selected_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    selected_mask = cv2.dilate(selected_mask, kernel, iterations=2)
    debug_save("candidate_mask.png", candidate_mask, config, cv2)
    debug_save("selected_mask.png", selected_mask, config, cv2)
    return selected_mask


def patch_reconstruct(roi_bgr: Any, mask: Any, *, config: RasterWatermarkConfig, cv2: Any) -> Any:
    height, width = mask.shape[:2]
    if cv2.countNonZero(mask) == 0:
        return roi_bgr

    x, y, w, h = cv2.boundingRect(mask)
    pad = 2
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(width, x + w + pad)
    y1 = min(height, y + h + pad)
    box_w = x1 - x0
    box_h = y1 - y0
    offsets = (
        (config.patch_offset_x, 0),
        (0, config.patch_offset_y),
        (config.patch_offset_x, config.patch_offset_y),
    )

    source_patch = None
    for dx, dy in offsets:
        sx = x0 + dx
        sy = y0 + dy
        if sx < 0 or sy < 0 or sx + box_w > width or sy + box_h > height:
            continue
        if cv2.countNonZero(mask[sy : sy + box_h, sx : sx + box_w]) == 0:
            source_patch = roi_bgr[sy : sy + box_h, sx : sx + box_w].copy()
            break

    output = roi_bgr.copy()
    if source_patch is None:
        return cv2.inpaint(output, mask, config.inpaint_radius, cv2.INPAINT_TELEA)

    target = output[y0:y1, x0:x1]
    mask_roi = mask[y0:y1, x0:x1]
    alpha = cv2.GaussianBlur(mask_roi.astype(float) / 255.0, (3, 3), 0)
    for channel in range(3):
        target[:, :, channel] = (
            target[:, :, channel] * (1 - alpha) + source_patch[:, :, channel] * alpha
        ).astype(target.dtype)
    return output


def clean_roi_scaled(
    roi_bgr: Any,
    *,
    config: RasterWatermarkConfig,
    cv2: Any,
    np: Any,
    Image: Any,
    ImageDraw: Any,
    ImageFont: Any,
    cache: dict[int, Any],
) -> tuple[Any | None, int]:
    scale = max(1.0, float(config.scale))
    height, width = roi_bgr.shape[:2]
    roi_hr = cv2.resize(roi_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    scaled = RasterWatermarkConfig(**{**config.__dict__, "search_margin_x": int(config.search_margin_x * scale)})
    mask = build_watermark_mask(
        roi_hr,
        config=scaled,
        cv2=cv2,
        np=np,
        Image=Image,
        ImageDraw=ImageDraw,
        ImageFont=ImageFont,
        cache=cache,
    )
    if mask is None:
        return None, 0
    cleaned_hr = patch_reconstruct(roi_hr, mask, config=scaled, cv2=cv2)
    cleaned = cv2.resize(cleaned_hr, (width, height), interpolation=cv2.INTER_LINEAR)
    return cleaned, int(cv2.countNonZero(mask))


def clean_image_bytes(
    image_bytes: bytes,
    *,
    original_ext: str,
    config: RasterWatermarkConfig | None = None,
) -> tuple[bytes | None, dict[str, Any]]:
    config = config or RasterWatermarkConfig()
    cv2, np, Image, ImageDraw, ImageFont, missing = load_optional_deps()
    if missing:
        return None, missing_dependency_result(missing)

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None, {"status": "decode_failed"}

    height, width = img.shape[:2]
    has_alpha = len(img.shape) == 3 and img.shape[2] == 4
    if has_alpha:
        channels = cv2.split(img)
        img_bgr = cv2.merge(channels[:3])
        alpha = channels[3]
    else:
        img_bgr = img.copy()
        alpha = None

    y0 = max(0, height - config.search_margin_y)
    x0 = max(0, width - config.search_margin_x)
    roi = img_bgr[y0:height, x0:width].copy()
    cache: dict[int, Any] = {}
    cleaned_roi, mask_pixels = clean_roi_scaled(
        roi,
        config=config,
        cv2=cv2,
        np=np,
        Image=Image,
        ImageDraw=ImageDraw,
        ImageFont=ImageFont,
        cache=cache,
    )
    if cleaned_roi is None:
        return None, {
            "status": "no_watermark_detected",
            "image_size": {"width": width, "height": height},
            "roi": {"x": x0, "y": y0, "width": width - x0, "height": height - y0},
        }

    img_bgr[y0:height, x0:width] = cleaned_roi
    if has_alpha:
        img_final = cv2.merge([*cv2.split(img_bgr), alpha])
    else:
        img_final = img_bgr

    ext = original_ext.lower()
    if ext in {".jpg", ".jpeg"} and not has_alpha:
        ok, encoded = cv2.imencode(".jpg", img_final, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        output_ext = ".jpg"
    elif ext == ".webp":
        ok, encoded = cv2.imencode(".webp", img_final, [int(cv2.IMWRITE_WEBP_QUALITY), 95])
        output_ext = ".webp"
    else:
        ok, encoded = cv2.imencode(".png", img_final)
        output_ext = ".png"
    if not ok:
        return None, {"status": "encode_failed"}
    return encoded.tobytes(), {
        "status": "patched",
        "image_size": {"width": width, "height": height},
        "roi": {"x": x0, "y": y0, "width": width - x0, "height": height - y0},
        "mask_pixels_scaled": mask_pixels,
        "output_ext": output_ext,
    }


def clean_pptx_media_images(
    input_pptx: Path,
    output_pptx: Path,
    *,
    config: RasterWatermarkConfig | None = None,
) -> dict[str, Any]:
    config = config or RasterWatermarkConfig()
    cv2, np, Image, ImageDraw, ImageFont, missing = load_optional_deps()
    if missing:
        return missing_dependency_result(missing)

    input_pptx = input_pptx.resolve()
    output_pptx = output_pptx.resolve()
    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    started_output = output_pptx
    with tempfile.TemporaryDirectory(prefix="qiaomu-notebooklm-raster-") as tmpdir:
        tmp = Path(tmpdir)
        with zipfile.ZipFile(input_pptx, "r") as archive:
            archive.extractall(tmp)

        media_dir = tmp / "ppt" / "media"
        images = sorted(path for path in media_dir.glob("*") if path.suffix.lower() in image_exts) if media_dir.exists() else []
        patched: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for image_path in images:
            original = image_path.read_bytes()
            cleaned, detail = clean_image_bytes(original, original_ext=image_path.suffix, config=config)
            record = {"image": str(image_path.relative_to(tmp)), **detail}
            if cleaned is None:
                skipped.append(record)
                continue
            image_path.write_bytes(cleaned)
            patched.append(record)

        if output_pptx == input_pptx:
            out_path = input_pptx.with_suffix(input_pptx.suffix + ".raster-clean.tmp")
        else:
            out_path = output_pptx
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for root, _dirs, files in os.walk(tmp):
                for filename in files:
                    full_path = Path(root) / filename
                    zout.write(full_path, full_path.relative_to(tmp).as_posix())
        if out_path != output_pptx:
            if output_pptx.exists():
                output_pptx.unlink()
            shutil.move(str(out_path), str(output_pptx))

    return {
        "status": "completed",
        "tool": "qiaomu-ppt/scripts/notebooklm_raster_watermark.py",
        "source": "adapted from Albonire/notebooklm-watermark-remover MIT approach",
        "input": str(input_pptx),
        "output": str(started_output),
        "attempted_images": len(patched) + len(skipped),
        "patched_images": len(patched),
        "patched": patched,
        "skipped_count": len(skipped),
        "skipped_sample": skipped[:20],
    }
