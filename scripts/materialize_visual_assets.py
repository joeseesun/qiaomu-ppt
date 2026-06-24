#!/usr/bin/env python3
"""Materialize qiaomu-ppt visual assets for preview and fallback workflows.

The default mode is a procedural preview fallback. It creates real PNG files
for pending AI rows so the renderer can exercise image slots before a configured
image model is available. The manifest records the generator explicitly; these
files can be replaced later by gpt-image/Codex-generated assets.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


WIDE_SIZE = (1600, 900)
LOCAL_SIZE = (1600, 900)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_hex(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    value = str(value or "").strip()
    match = re.match(r"^#?([0-9a-fA-F]{6})$", value)
    if not match:
        return fallback
    raw = match.group(1)
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(a[i] * (1 - t) + b[i] * t))) for i in range(3))


def safe_text(value: str, limit: int = 22) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    # Generated assets are text-free; this is only used to seed geometry.
    return value[:limit]


def item_seed(item: dict[str, Any]) -> int:
    text = "|".join(str(item.get(key) or "") for key in ("asset_id", "purpose", "reference", "slide_no"))
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate(text)) % 2_000_000_000


def color_model(manifest: dict[str, Any]) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    model = manifest.get("deck_image_model") if isinstance(manifest, dict) else {}
    scheme = model.get("color_scheme") if isinstance(model, dict) else {}
    primary = parse_hex(scheme.get("primary", ""), (20, 35, 54))
    secondary = parse_hex(scheme.get("secondary", ""), (242, 236, 224))
    accent = parse_hex(scheme.get("accent", ""), (196, 71, 44))
    return primary, secondary, accent


def add_noise(image: Image.Image, rng: random.Random, opacity: int = 22) -> Image.Image:
    noise = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pix = noise.load()
    width, height = image.size
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            v = rng.randint(0, opacity)
            pix[x, y] = (255, 255, 255, v)
    return Image.alpha_composite(image.convert("RGBA"), noise)


def draw_gradient(draw: ImageDraw.ImageDraw, size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    width, height = size
    for y in range(height):
        t = y / max(1, height - 1)
        row = mix(top, bottom, t)
        draw.line([(0, y), (width, y)], fill=row + (255,))


def draw_vignette(base: Image.Image, color: tuple[int, int, int], strength: int = 120) -> Image.Image:
    width, height = base.size
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    pix = layer.load()
    cx, cy = width * 0.5, height * 0.52
    max_d = math.hypot(cx, cy)
    for y in range(height):
        for x in range(width):
            d = math.hypot(x - cx, y - cy) / max_d
            alpha = int(max(0, min(strength, (d - 0.25) * strength * 1.55)))
            if alpha:
                pix[x, y] = color + (alpha,)
    return Image.alpha_composite(base.convert("RGBA"), layer)


def draw_thread_bound_book(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    cover: tuple[int, int, int],
    paper: tuple[int, int, int],
    accent: tuple[int, int, int],
) -> None:
    shadow = (0, 0, 0, 72)
    draw.rounded_rectangle((x + 16, y + 18, x + w + 16, y + h + 18), radius=10, fill=shadow)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=9, fill=paper + (246,), outline=cover + (160,), width=3)
    draw.rectangle((x, y, x + int(w * 0.16), y + h), fill=cover + (238,))
    for idx in range(4):
        yy = y + int(h * (0.18 + idx * 0.18))
        draw.ellipse((x + int(w * 0.055), yy - 8, x + int(w * 0.105), yy + 8), outline=accent + (210,), width=3)
    for idx in range(7):
        yy = y + int(h * (0.16 + idx * 0.1))
        draw.line((x + int(w * 0.26), yy, x + int(w * 0.88), yy + 3), fill=cover + (34,), width=2)
    draw.line((x + int(w * 0.18), y + 18, x + int(w * 0.18), y + h - 18), fill=accent + (150,), width=2)


def draw_brush(draw: ImageDraw.ImageDraw, x: int, y: int, length: int, *, angle: float, color: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    dx = math.cos(angle) * length
    dy = math.sin(angle) * length
    x2 = x + dx
    y2 = y + dy
    draw.line((x, y, x2, y2), fill=color + (230,), width=14)
    ferrule_x = x + dx * 0.75
    ferrule_y = y + dy * 0.75
    draw.line((ferrule_x, ferrule_y, x2, y2), fill=accent + (235,), width=18)
    tip_x = x2 + math.cos(angle) * 42
    tip_y = y2 + math.sin(angle) * 42
    draw.polygon([(x2 - 12, y2 - 8), (x2 + 12, y2 + 8), (tip_x, tip_y)], fill=(42, 32, 24, 235))


def draw_inkstone(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    draw.ellipse((x + 18, y + 20, x + w + 18, y + h + 20), fill=(0, 0, 0, 70))
    draw.ellipse((x, y, x + w, y + h), fill=(31, 36, 42, 245), outline=(160, 150, 130, 90), width=3)
    draw.ellipse((x + int(w * 0.22), y + int(h * 0.22), x + int(w * 0.78), y + int(h * 0.74)), fill=(11, 15, 19, 245))
    draw.ellipse((x + int(w * 0.34), y + int(h * 0.34), x + int(w * 0.52), y + int(h * 0.48)), fill=(255, 255, 255, 35))


def draw_candle(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    w = int(42 * scale)
    h = int(150 * scale)
    draw.ellipse((x - 75, y - 118, x + 98, y + 54), fill=(214, 138, 58, 38))
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=(226, 207, 170, 240), outline=(120, 80, 44, 110), width=2)
    draw.polygon([(x + w // 2, y - int(58 * scale)), (x + int(w * 0.82), y - int(12 * scale)), (x + w // 2, y + 10), (x + int(w * 0.18), y - int(12 * scale))], fill=(214, 82, 44, 235))
    draw.ellipse((x + int(w * 0.28), y - int(42 * scale), x + int(w * 0.72), y + int(2 * scale)), fill=(255, 214, 114, 245))
    for idx in range(3):
        off = idx * 24
        draw.arc((x - 15 + off, y - 120 - idx * 24, x + 120 + off, y + 40 - idx * 8), 200, 286, fill=(236, 228, 205, 65), width=3)


def draw_archival_papers(draw: ImageDraw.ImageDraw, rng: random.Random, box: tuple[int, int, int, int], paper: tuple[int, int, int], ink: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = box
    for idx in range(5):
        w = rng.randint(260, 430)
        h = rng.randint(145, 250)
        x = rng.randint(x0, max(x0, x1 - w))
        y = rng.randint(y0, max(y0, y1 - h))
        tint = mix(paper, (255, 255, 255), rng.random() * 0.16)
        draw.rounded_rectangle((x + 12, y + 14, x + w + 12, y + h + 14), radius=8, fill=(0, 0, 0, 38))
        draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=tint + (232,), outline=ink + (42,), width=2)
        for line_idx in range(rng.randint(3, 6)):
            yy = y + 32 + line_idx * rng.randint(18, 25)
            draw.line((x + 32, yy, x + w - rng.randint(64, 128), yy), fill=ink + (22,), width=2)


def is_pusongling_item(item: dict[str, Any], manifest: dict[str, Any]) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            manifest.get("subject"),
            item.get("asset_id"),
            item.get("purpose"),
            item.get("reference"),
            item.get("prompt"),
        ]
    )
    return any(token in text for token in ("蒲松龄", "聊斋", "志异", "狐鬼"))


def render_pusongling_asset(item: dict[str, Any], manifest: dict[str, Any], output: Path) -> None:
    rng = random.Random(item_seed(item))
    width, height = WIDE_SIZE
    role = str((item.get("art_direction_brief") or {}).get("slide_role") or "")
    primary, secondary, accent = color_model(manifest)
    ink = mix(primary, (8, 14, 22), 0.35)
    paper = mix(secondary, (248, 239, 216), 0.44)
    vermilion = mix(accent, (178, 48, 38), 0.34)

    dark_roles = {"cover", "closing", "comparison"}
    if role in dark_roles:
        top = mix(ink, (1, 7, 18), 0.45)
        bottom = mix(primary, (24, 18, 28), 0.35)
    else:
        top = mix(paper, (255, 250, 238), 0.35)
        bottom = mix(paper, primary, 0.14)
    base = Image.new("RGBA", (width, height), top + (255,))
    draw = ImageDraw.Draw(base, "RGBA")
    draw_gradient(draw, (width, height), top, bottom)

    # Intentional subject matter: Qing literati desk, no visible text.
    if role == "cover":
        draw.ellipse((1120, 34, 1440, 354), fill=(234, 226, 205, 42))
        draw.rectangle((760, 500, 1660, 940), fill=(31, 21, 19, 178))
        draw_thread_bound_book(draw, 910, 360, 360, 238, cover=ink, paper=paper, accent=vermilion)
        draw_inkstone(draw, 1260, 520, 190, 110)
        draw_brush(draw, 1120, 628, 420, angle=-0.26, color=(96, 55, 34), accent=vermilion)
        draw_candle(draw, 1338, 278, 1.05)
    elif role == "source":
        draw_archival_papers(draw, rng, (720, 90, 1535, 760), paper, ink)
        draw_thread_bound_book(draw, 980, 290, 315, 210, cover=ink, paper=paper, accent=vermilion)
        draw_brush(draw, 880, 710, 460, angle=-0.42, color=(86, 48, 31), accent=vermilion)
    elif role == "closing":
        draw.ellipse((1010, 120, 1460, 570), fill=(192, 65, 50, 48))
        draw_thread_bound_book(draw, 940, 350, 420, 260, cover=ink, paper=paper, accent=vermilion)
        draw_candle(draw, 1370, 310, 0.92)
        for idx in range(5):
            x = 1060 + idx * 92
            draw.arc((x, 180 - idx * 24, x + 240, 500 - idx * 18), 188, 280, fill=(235, 226, 205, 42), width=4)
    else:
        draw_archival_papers(draw, rng, (60, 80, 1480, 790), paper, ink)
        draw_thread_bound_book(draw, 900, 210, 360, 245, cover=ink, paper=paper, accent=vermilion)
        draw_inkstone(draw, 1215, 542, 220, 118)
        draw_brush(draw, 800, 638, 520, angle=-0.18, color=(88, 48, 30), accent=vermilion)

    # Low-detail safe area wash, matching the art-direction brief.
    if role in {"cover", "closing"}:
        draw.rectangle((0, 0, int(width * 0.48), height), fill=top + (118,))
    elif role == "source":
        draw.rectangle((0, 0, int(width * 0.36), height), fill=paper + (148,))
    else:
        draw.rectangle((0, 0, width, int(height * 0.22)), fill=paper + (78,))

    final = draw_vignette(add_noise(base, rng, opacity=16), ink, strength=80).convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    final.save(output, quality=94)


def render_asset(item: dict[str, Any], manifest: dict[str, Any], output: Path) -> None:
    if is_pusongling_item(item, manifest):
        render_pusongling_asset(item, manifest, output)
        return

    rng = random.Random(item_seed(item))
    primary, secondary, accent = color_model(manifest)
    page_role = str(item.get("page_role") or "local")
    visual_type = str(item.get("visual_type") or item.get("hero_primitive") or "scene")
    size = WIDE_SIZE if page_role == "hero_page" else LOCAL_SIZE
    width, height = size

    base = Image.new("RGBA", size, secondary + (255,))
    draw = ImageDraw.Draw(base, "RGBA")
    for y in range(height):
        t = y / max(1, height - 1)
        row = mix(secondary, primary, 0.08 + 0.22 * t)
        draw.line([(0, y), (width, y)], fill=row + (255,))

    # Large quiet atmosphere fields.
    for _ in range(5):
        cx = rng.randint(-width // 8, width + width // 8)
        cy = rng.randint(-height // 8, height + height // 8)
        r = rng.randint(width // 8, width // 3)
        color = accent if rng.random() < 0.45 else primary
        alpha = rng.randint(20, 54)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (alpha,))

    if visual_type in {"timeline", "flowchart", "framework", "comparison", "cycle"}:
        line_y = int(height * 0.55)
        draw.line((int(width * 0.12), line_y, int(width * 0.88), line_y), fill=primary + (80,), width=4)
        nodes = 4 if visual_type != "comparison" else 2
        for idx in range(nodes):
            x = int(width * (0.16 + idx * (0.68 / max(1, nodes - 1))))
            y = line_y + int(math.sin(idx + rng.random()) * height * 0.05)
            fill = accent if idx % 2 else primary
            draw.rounded_rectangle((x - 52, y - 52, x + 52, y + 52), radius=18, outline=fill + (130,), width=4, fill=secondary + (120,))
    elif visual_type in {"scene", "atmospheric"}:
        for idx in range(9):
            x0 = int(width * (0.1 + idx * 0.09))
            y0 = rng.randint(int(height * 0.18), int(height * 0.78))
            draw.line((x0, y0, x0 + rng.randint(80, 220), y0 + rng.randint(-80, 80)), fill=primary + (32,), width=2)
    else:
        for idx in range(6):
            x = rng.randint(int(width * 0.12), int(width * 0.78))
            y = rng.randint(int(height * 0.18), int(height * 0.72))
            draw.rectangle((x, y, x + rng.randint(80, 180), y + rng.randint(45, 120)), outline=primary + (52,), width=2)

    # A subtle blank label rail, deliberately without text.
    if page_role != "hero_page":
        draw.rounded_rectangle((int(width * 0.08), int(height * 0.08), int(width * 0.42), int(height * 0.16)), radius=18, fill=primary + (34,))

    blurred = base.filter(ImageFilter.GaussianBlur(radius=0.45))
    final = add_noise(blurred, rng).convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    final.save(output, quality=94)


def materialize(project: Path, manifest_path: Path, *, force: bool) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise SystemExit("visual_asset_manifest.json must be an object")
    items = manifest.get("items")
    if not isinstance(items, list):
        raise SystemExit("visual_asset_manifest.json needs an items list")

    generated: list[str] = []
    skipped: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        acquire_via = str(item.get("acquire_via") or "")
        status = str(item.get("status") or "")
        generator = str(item.get("generator") or "")
        can_regenerate = force and status == "Generated" and generator in {"procedural-preview-fallback", "existing-file"}
        if acquire_via != "ai" or (status not in {"Pending", "Missing", "Failed"} and not can_regenerate):
            skipped.append(str(item.get("asset_id") or ""))
            continue
        rel_path = str(item.get("path") or "")
        if not rel_path:
            skipped.append(str(item.get("asset_id") or ""))
            continue
        output = project / rel_path
        if output.exists() and not force:
            item["status"] = "Generated"
            item.setdefault("generator", "existing-file")
            generated.append(rel_path)
            continue
        render_asset(item, manifest, output)
        item["status"] = "Generated"
        item["generator"] = "procedural-preview-fallback"
        item["generated_at"] = now_iso()
        item["generation_note"] = (
            "Procedural local preview asset. Replace with configured image-generation output "
            "for final-quality delivery when available."
        )
        item["dimensions"] = list(Image.open(output).size)
        generated.append(rel_path)

    status_summary: dict[str, int] = {}
    for item in items:
        if isinstance(item, dict):
            status = str(item.get("status") or "")
            status_summary[status] = status_summary.get(status, 0) + 1
    manifest["status_summary"] = status_summary
    manifest["materialized_at"] = now_iso()
    manifest["materialization_mode"] = "procedural-preview-fallback"
    write_json(manifest_path, manifest)
    return {"ok": True, "generated": generated, "skipped": skipped, "status_summary": status_summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize pending visual assets as local procedural preview PNGs.")
    parser.add_argument("project", type=Path, help="Project directory.")
    parser.add_argument("--manifest", type=Path, default=None, help="visual_asset_manifest.json path.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated asset files.")
    args = parser.parse_args()

    project = args.project.resolve()
    manifest_path = args.manifest or project / "visual_asset_manifest.json"
    result = materialize(project, manifest_path, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
