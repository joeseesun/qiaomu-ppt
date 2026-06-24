#!/usr/bin/env python3
"""Check visual rhythm and repetition in generated qiaomu-ppt SVG decks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def svg_files(project: Path, source: str) -> list[Path]:
    folder = project / source
    return sorted(folder.glob("*.svg")) if folder.exists() else []


def contract_slides(project: Path) -> list[dict[str, Any]]:
    path = project / "spec_lock.json"
    if not path.exists():
        return []
    try:
        data = load_json(path)
    except Exception:
        return []
    contract = data.get("layout_execution_contract") if isinstance(data, dict) else {}
    slides = contract.get("slides") if isinstance(contract, dict) else []
    return [item for item in slides if isinstance(item, dict)] if isinstance(slides, list) else []


def image_manifest_slide_count(project: Path) -> int:
    path = project / "visual_asset_manifest.json"
    if not path.exists():
        return 0
    try:
        data = load_json(path)
    except Exception:
        return 0
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return 0
    slides: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") not in {"Generated", "Sourced", "Existing", "Rendered"}:
            continue
        path_value = str(item.get("path") or "")
        if not path_value or not (project / path_value).exists():
            continue
        try:
            slide_no = int(item.get("slide_no"))
        except (TypeError, ValueError):
            slide_no = 0
        if slide_no > 0:
            slides.add(slide_no)
    return len(slides)


def analyze_svg(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    counts = {tag: len(re.findall(rf"<{tag}\b", text)) for tag in ("image", "rect", "circle", "path", "line", "text")}
    bg_color_match = re.search(
        r'<rect\b[^>]*\bx="0"[^>]*\by="0"[^>]*\bwidth="(?:1280|100%)"[^>]*\bheight="(?:720|100%)"[^>]*\bfill="([^"]+)"',
        text[:2200],
        flags=re.IGNORECASE,
    )
    background_color = (bg_color_match.group(1).lower() if bg_color_match else "")
    has_dark_bg = background_color in {"#0b1628", "#0b0b0a", "#050505", "#11110f"} or '#0B1628' in text[:1600] or '#0b1628' in text[:1600]
    has_full_bleed_image = bool(
        re.search(r"<image\b[^>]*\bwidth=\"(?:1280\.0|1280)\"[^>]*\bheight=\"(?:720\.0|720)\"", text)
    )
    image_slot = "none"
    image_match = re.search(r"<image\b[^>]*>", text)
    if image_match:
        tag = image_match.group(0)
        def attr(name: str) -> float:
            match = re.search(rf'\b{name}="(-?\d+(?:\.\d+)?)"', tag)
            return float(match.group(1)) if match else 0.0

        x, y, w, h = attr("x"), attr("y"), attr("width"), attr("height")
        horizontal = "left" if x < 320 else "right" if x > 520 else "center"
        vertical = "top" if y < 80 else "middle" if y < 220 else "lower"
        scale = "full" if w >= 1180 and h >= 660 else "wide" if w >= 900 else "panel"
        image_slot = f"{horizontal}-{vertical}-{scale}"
    fingerprint = (
        f"img{min(counts['image'], 2)}-rect{min(counts['rect'], 6)}-"
        f"circle{min(counts['circle'], 6)}-path{min(counts['path'], 6)}-"
        f"line{min(counts['line'], 6)}-text{min(counts['text'], 9)}-"
        f"slot{image_slot}-dark{int(has_dark_bg)}"
    )
    return {
        "path": str(path),
        "counts": counts,
        "has_image": counts["image"] > 0,
        "has_full_bleed_image": has_full_bleed_image,
        "has_dark_background": has_dark_bg,
        "background_color": background_color,
        "image_slot": image_slot,
        "fingerprint": fingerprint,
    }


def longest_run(values: list[str]) -> tuple[str, int]:
    best_value = ""
    best_len = 0
    current_value = ""
    current_len = 0
    for value in values:
        if value == current_value:
            current_len += 1
        else:
            current_value = value
            current_len = 1
        if current_len > best_len:
            best_value = current_value
            best_len = current_len
    return best_value, best_len


def check(project: Path, source: str) -> dict[str, Any]:
    project = project.resolve()
    files = svg_files(project, source)
    failures: list[str] = []
    warnings: list[str] = []
    slides = contract_slides(project)
    analyses = [analyze_svg(path) for path in files]
    art_directions = [str(item.get("art_direction") or item.get("component_type") or "") for item in slides]
    component_types = [str(item.get("component_type") or "") for item in slides]
    rhythms = [str(item.get("rhythm") or "") for item in slides]

    if not files:
        failures.append(f"no SVG files found under {source}/")
    if slides and len(slides) != len(files):
        failures.append(f"spec_lock slide count {len(slides)} does not match SVG count {len(files)}")

    if len(files) > 7:
        unique_art = len(set(item for item in art_directions if item))
        minimum_art = min(5, max(3, len(files) // 2))
        if unique_art < minimum_art:
            failures.append(f"visual rhythm needs at least {minimum_art} art directions for {len(files)} slides; found {unique_art}")
        repeated_art, repeated_art_len = longest_run(art_directions)
        if repeated_art and repeated_art_len > 3:
            failures.append(f"art direction repeats {repeated_art_len} slides in a row: {repeated_art}")
        repeated_component, repeated_component_len = longest_run(component_types)
        if repeated_component and repeated_component_len > 3:
            warnings.append(f"component type repeats {repeated_component_len} slides in a row: {repeated_component}")
        unique_rhythm = len(set(item for item in rhythms if item))
        if unique_rhythm < 2:
            warnings.append("deck uses fewer than two page rhythms")

    fingerprints = [item["fingerprint"] for item in analyses]
    repeated_fp, repeated_fp_len = longest_run(fingerprints)
    if repeated_fp and repeated_fp_len > 2:
        warnings.append(f"SVG structural fingerprint repeats {repeated_fp_len} slides in a row: {repeated_fp}")

    terminal_image_slides = image_manifest_slide_count(project)
    svg_image_slides = sum(1 for item in analyses if item["has_image"])
    if terminal_image_slides and svg_image_slides < max(1, terminal_image_slides // 2):
        failures.append(
            f"visual_asset_manifest has {terminal_image_slides} terminal image slide(s), "
            f"but SVGs use images on only {svg_image_slides} slide(s)"
        )
    if len(files) > 7 and svg_image_slides == 0:
        warnings.append("long deck has no SVG image usage; consider generated/source visual assets before final delivery")

    dark_pages = sum(1 for item in analyses if item["has_dark_background"])
    background_colors = [item["background_color"] for item in analyses if item["background_color"]]
    unique_background_colors = len(set(background_colors))
    if len(files) > 7 and dark_pages < 2:
        warnings.append("long deck has fewer than two dark/anchor pages; thumbnail rhythm may feel flat")
    if len(files) > 12 and unique_background_colors <= 1:
        warnings.append(
            "all slides appear to share the same base background color; verify thumbnail rhythm uses real image/texture/composition variation, not only foreground rearrangement"
        )

    return {
        "ok": not failures,
        "project": str(project),
        "source": source,
        "slide_count": len(files),
        "failures": failures,
        "warnings": warnings,
        "summary": {
            "unique_art_directions": len(set(item for item in art_directions if item)),
            "art_directions": art_directions,
            "component_types": component_types,
            "rhythms": rhythms,
            "svg_image_slides": svg_image_slides,
            "terminal_image_slides": terminal_image_slides,
            "dark_pages": dark_pages,
            "unique_background_colors": unique_background_colors,
            "unique_structural_fingerprints": len(set(fingerprints)),
        },
        "slides": analyses,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check generated SVG deck visual rhythm and repetition.")
    parser.add_argument("project", type=Path, help="Project directory.")
    parser.add_argument("--source", default="svg_output", help="SVG directory relative to project. Default: svg_output.")
    parser.add_argument("--output", "-o", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()
    result = check(args.project, args.source)
    if args.output:
        output = args.output if args.output.is_absolute() else args.project / args.output
        write_json(output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
