#!/usr/bin/env python3
"""Render qiaomu-ppt SVG-first decks to PNG previews with Playwright."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_fresh(output: Path, source: Path) -> bool:
    return output.exists() and output.stat().st_mtime >= source.stat().st_mtime


def render_svgs(project: Path, source: str = "svg_output", *, force: bool = False) -> tuple[list[Path], dict[str, int]]:
    svg_dir = project / source
    if not svg_dir.is_dir():
        raise SystemExit(f"SVG source directory not found: {svg_dir}")
    svgs = sorted(svg_dir.glob("*.svg"))
    if not svgs:
        raise SystemExit(f"No SVG files found in {svg_dir}")

    out_dir = project / "previews" / source
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs_by_index: dict[int, Path] = {}
    jobs: list[tuple[int, Path, Path]] = []
    reused = 0

    for idx, svg in enumerate(svgs, start=1):
        out = out_dir / f"slide-{idx:02d}.png"
        outputs_by_index[idx] = out
        if not force and is_fresh(out, svg):
            reused += 1
            continue
        jobs.append((idx, svg, out))

    if jobs:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise SystemExit(
                "Playwright is required for SVG previews. Install with: "
                "python3 -m pip install playwright && python3 -m playwright install chromium"
            ) from exc

        with sync_playwright() as p:
            candidates = [
                Path(p.chromium.executable_path),
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
            cache_root = Path.home() / "Library/Caches/ms-playwright"
            if cache_root.exists():
                candidates.extend(cache_root.glob("chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
                candidates.extend(cache_root.glob("chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"))
            executable = next((path for path in candidates if path.exists()), None)
            launch_kwargs = {"executable_path": str(executable)} if executable else {}
            browser = p.chromium.launch(**launch_kwargs)
            try:
                context = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
                page = context.new_page()
                for _idx, svg, out in jobs:
                    page.goto(svg.resolve().as_uri(), wait_until="load")
                    page.wait_for_timeout(120)
                    page.screenshot(path=str(out), full_page=False)
                page.close()
                context.close()
            finally:
                browser.close()
    outputs = [outputs_by_index[idx] for idx in range(1, len(svgs) + 1)]
    return outputs, {"rendered": len(jobs), "reused": reused}


def build_grid(images: list[Path], out_path: Path, cols: int = 5, thumb_w: int = 320) -> Path:
    thumbs: list[Image.Image] = []
    for idx, path in enumerate(images, start=1):
        img = Image.open(path).convert("RGB")
        ratio = img.height / img.width
        thumb_h = int(thumb_w * ratio)
        img = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (thumb_w, thumb_h + 26), (245, 241, 232))
        canvas.paste(img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, thumb_h, thumb_w, thumb_h + 26), fill=(17, 24, 39))
        draw.text((10, thumb_h + 7), f"{idx:02d}", fill=(255, 255, 255))
        thumbs.append(canvas)

    rows = (len(thumbs) + cols - 1) // cols
    gap = 12
    cell_w = thumb_w
    cell_h = thumbs[0].height
    grid = Image.new("RGB", (cols * cell_w + (cols + 1) * gap, rows * cell_h + (rows + 1) * gap), (230, 224, 214))
    for idx, thumb in enumerate(thumbs):
        col = idx % cols
        row = idx // cols
        grid.paste(thumb, (gap + col * (cell_w + gap), gap + row * (cell_h + gap)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grid.save(out_path, quality=92)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render SVG deck previews and a thumbnail grid")
    parser.add_argument("project", type=Path)
    parser.add_argument("--source", default="svg_output")
    parser.add_argument("--cols", type=int, default=5)
    parser.add_argument("--force", action="store_true", help="Rerender all preview images even when cached images are fresh")
    args = parser.parse_args()

    project = args.project
    images, cache_stats = render_svgs(project, args.source, force=args.force)
    grid = build_grid(images, project / "previews" / args.source / "thumbnail-grid.jpg", cols=args.cols)
    write_json(
        project / "svg_preview_manifest.json",
        {
            "schema_version": "1.0.0",
            "tool": "qiaomu-ppt/scripts/svg_preview.py",
            "source": args.source,
            "slide_count": len(images),
            "slide_images": [str(path.relative_to(project)) for path in images],
            "thumbnail_grid": str(grid.relative_to(project)),
            "cache": cache_stats,
        },
    )
    print(json.dumps({"slide_count": len(images), "thumbnail_grid": str(grid), "cache": cache_stats}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
