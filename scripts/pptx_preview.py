#!/usr/bin/env python3
"""Render PPTX previews for qiaomu-ppt QA.

This script uses system LibreOffice/Poppler directly and does not call any
external PPTX skill.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def which_any(candidates: list[str]) -> str | None:
    for item in candidates:
        found = shutil.which(item)
        if found:
            return found
    return None


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def convert_to_pdf(pptx: Path, out_dir: Path, soffice: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)]
    result = run(cmd)
    pdf = out_dir / f"{pptx.stem}.pdf"
    if result.returncode != 0 or not pdf.exists():
        raise SystemExit(
            "LibreOffice PPTX-to-PDF conversion failed\n"
            + "command: "
            + " ".join(cmd)
            + "\nstdout:\n"
            + result.stdout
            + "\nstderr:\n"
            + result.stderr
        )
    return pdf


def render_pages(pdf: Path, out_dir: Path, pdftoppm: str, resolution: int) -> list[Path]:
    for stale in list(out_dir.glob("slide-*.jpg")) + list(out_dir.glob("slide-*.png")):
        stale.unlink()
    grid = out_dir / "thumbnail-grid.jpg"
    if grid.exists():
        grid.unlink()
    prefix = out_dir / "slide"
    cmd = [pdftoppm, "-jpeg", "-r", str(resolution), str(pdf), str(prefix)]
    result = run(cmd)
    if result.returncode != 0:
        raise SystemExit(
            "Poppler PDF-to-image rendering failed\n"
            + "command: "
            + " ".join(cmd)
            + "\nstdout:\n"
            + result.stdout
            + "\nstderr:\n"
            + result.stderr
        )
    images = sorted(out_dir.glob("slide-*.jpg"))
    if not images:
        raise SystemExit("pdftoppm completed but no slide-*.jpg files were produced")
    normalized: list[Path] = []
    for idx, path in enumerate(images, start=1):
        target = out_dir / f"slide-{idx:02d}.jpg"
        if path != target:
            if target.exists():
                target.unlink()
            path.rename(target)
        normalized.append(target)
    return normalized


def make_contact_sheet(images: list[Path], output: Path, columns: int = 5, thumb_width: int = 360) -> Path:
    thumbs: list[Image.Image] = []
    for path in images:
        image = Image.open(path).convert("RGB")
        ratio = thumb_width / image.width
        thumb = image.resize((thumb_width, round(image.height * ratio)))
        thumbs.append(thumb)
    if not thumbs:
        raise SystemExit("no preview images for contact sheet")
    rows = (len(thumbs) + columns - 1) // columns
    gap = 18
    label_h = 28
    thumb_h = max(image.height for image in thumbs)
    sheet = Image.new("RGB", (columns * thumb_width + (columns + 1) * gap, rows * (thumb_h + label_h) + (rows + 1) * gap), "#151515")
    draw = ImageDraw.Draw(sheet)
    for idx, thumb in enumerate(thumbs):
        row = idx // columns
        col = idx % columns
        x = gap + col * (thumb_width + gap)
        y = gap + row * (thumb_h + label_h + gap)
        sheet.paste(thumb, (x, y))
        draw.text((x, y + thumb_h + 7), f"{idx + 1:02d}", fill="#E8E1D2")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)
    return output


def build_preview(project: Path, pptx: Path, out_dir: Path, resolution: int) -> dict[str, Any]:
    soffice = which_any(["soffice", "libreoffice"])
    if not soffice:
        raise SystemExit("LibreOffice executable not found; install soffice before PPTX preview QA")
    pdftoppm = which_any(["pdftoppm"])
    if not pdftoppm:
        raise SystemExit("pdftoppm not found; install Poppler before slide image QA")
    pdf = convert_to_pdf(pptx, out_dir, soffice)
    images = render_pages(pdf, out_dir, pdftoppm, resolution)
    grid = make_contact_sheet(images, out_dir / "thumbnail-grid.jpg")
    manifest = {
        "schema_version": "1.0.0",
        "project": str(project),
        "pptx": str(pptx),
        "pdf": str(pdf.relative_to(project) if pdf.is_relative_to(project) else pdf),
        "slide_count": len(images),
        "resolution": resolution,
        "preview_images": [str(path.relative_to(project) if path.is_relative_to(project) else path) for path in images],
        "thumbnail_grid": str(grid.relative_to(project) if grid.is_relative_to(project) else grid),
        "tools": {
            "soffice": soffice,
            "pdftoppm": pdftoppm,
        },
        "external_skill_dependency": "none",
    }
    write_json(project / "pptx_preview_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Render qiaomu-ppt PPTX preview images and thumbnail grid.")
    parser.add_argument("pptx", help="PPTX file to render")
    parser.add_argument("--project", help="Project root. Defaults to PPTX parent parent when under exports/.")
    parser.add_argument("--output-dir", "-o", help="Preview output directory. Defaults to <project>/previews.")
    parser.add_argument("--resolution", "-r", type=int, default=150, help="pdftoppm render resolution")
    args = parser.parse_args()
    pptx = Path(args.pptx).resolve()
    if args.project:
        project = Path(args.project).resolve()
    elif pptx.parent.name == "exports":
        project = pptx.parent.parent
    else:
        project = pptx.parent
    out_dir = Path(args.output_dir).resolve() if args.output_dir else project / "previews"
    manifest = build_preview(project, pptx, out_dir, args.resolution)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
