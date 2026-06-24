#!/usr/bin/env python3
"""Inspect visible text in a generated qiaomu-ppt PPTX."""

from __future__ import annotations

import argparse
import html
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


PLACEHOLDERS = [
    r"\[必填\]",
    r"lorem ipsum",
    r"\bTODO\b",
    r"\bTBD\b",
    r"SLIDES_HERE",
]

FORBIDDEN_VISIBLE = [
    r"\bfetched\s+via\b",
    r"\bgenerated\s+with\b",
    r"qiaomu-markdown-proxy",
    r"Speaker\s+cue\s*:",
    r"\bsource_fetch\b",
    r"\bPPTX\s+export\b",
]

EMU_MARGIN_RATIO = 0.06
FULL_SLIDE_COVER_RATIO = 0.88


def load_json(path: Path) -> Any:
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


def expected_title(slide: dict[str, Any]) -> str:
    return str(slide.get("claim_title") or slide.get("title") or "").strip()


def visible_text_by_slide(pptx: Path) -> list[str]:
    presentation = Presentation(str(pptx))
    result: list[str] = []
    for slide in presentation.slides:
        chunks: list[str] = []
        for shape in slide.shapes:
            text = getattr(shape, "text", "")
            if text:
                chunks.append(text)
        result.append("\n".join(chunks))
    return result


def visible_text_by_slide_xml(pptx: Path) -> list[str]:
    """Fallback reader for native DrawingML generated outside python-pptx.

    Some SVG-native exporters inject valid DrawingML that is visible in
    PowerPoint/LibreOffice but is not surfaced by python-pptx shape.text.
    Reading the raw slide XML keeps text QA aligned with rendered output.
    """
    def slide_index(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    result: list[str] = []
    with zipfile.ZipFile(pptx) as zf:
        names = sorted(
            [name for name in zf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")],
            key=slide_index,
        )
        for name in names:
            xml = zf.read(name).decode("utf-8", errors="ignore")
            chunks = [html.unescape(value) for value in re.findall(r"<a:t>(.*?)</a:t>", xml, flags=re.DOTALL)]
            result.append("\n".join(chunks))
    return result


def inspect_editability(pptx: Path) -> dict[str, Any]:
    presentation = Presentation(str(pptx))
    slide_w = int(presentation.slide_width)
    slide_h = int(presentation.slide_height)
    slides: list[dict[str, Any]] = []
    image_backed_count = 0
    full_slide_picture_count = 0
    native_text_chars_total = 0
    native_text_shape_count_total = 0

    for idx, slide in enumerate(presentation.slides, start=1):
        picture_count = 0
        full_slide_pictures = 0
        native_text_chars = 0
        native_text_shapes = 0
        native_non_picture_shapes = 0
        for shape in slide.shapes:
            text = getattr(shape, "text", "") or ""
            if text.strip():
                native_text_shapes += 1
                native_text_chars += len(text.strip())
            if getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.PICTURE:
                picture_count += 1
                left = int(getattr(shape, "left", 0))
                top = int(getattr(shape, "top", 0))
                width = int(getattr(shape, "width", 0))
                height = int(getattr(shape, "height", 0))
                covers_width = width >= slide_w * FULL_SLIDE_COVER_RATIO and left <= slide_w * EMU_MARGIN_RATIO
                covers_height = height >= slide_h * FULL_SLIDE_COVER_RATIO and top <= slide_h * EMU_MARGIN_RATIO
                if covers_width and covers_height:
                    full_slide_pictures += 1
            else:
                native_non_picture_shapes += 1

        image_backed = full_slide_pictures > 0 and native_text_chars < 12
        if image_backed:
            image_backed_count += 1
        if full_slide_pictures:
            full_slide_picture_count += full_slide_pictures
        native_text_chars_total += native_text_chars
        native_text_shape_count_total += native_text_shapes
        slides.append(
            {
                "slide_no": idx,
                "picture_count": picture_count,
                "full_slide_picture_count": full_slide_pictures,
                "native_text_shape_count": native_text_shapes,
                "native_text_chars": native_text_chars,
                "native_non_picture_shape_count": native_non_picture_shapes,
                "image_backed": image_backed,
            }
        )

    slide_count = len(slides)
    return {
        "slide_count": slide_count,
        "native_text_shape_count": native_text_shape_count_total,
        "native_text_chars": native_text_chars_total,
        "full_slide_picture_count": full_slide_picture_count,
        "image_backed_slide_count": image_backed_count,
        "image_backed_ratio": image_backed_count / slide_count if slide_count else 0,
        "slides": slides,
    }


def best_visible_text_by_slide(pptx: Path) -> tuple[list[str], str]:
    primary = visible_text_by_slide(pptx)
    if sum(len(text.strip()) for text in primary) >= max(1, len(primary)) * 12:
        return primary, "python-pptx"
    fallback = visible_text_by_slide_xml(pptx)
    return fallback, "pptx-slide-xml"


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+", "", value)
    return re.sub(r"[，,。.:：；;、＋+\-—–·/／()（）\[\]【】\"“”'‘’]", "", value)


def scan_patterns(text: str, patterns: list[str]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE)]


def check(pptx: Path, slide_plan: Path | None, *, allow_image_backed: bool = False) -> dict[str, Any]:
    texts, extraction_method = best_visible_text_by_slide(pptx)
    editability = inspect_editability(pptx)
    failures: list[str] = []
    warnings: list[str] = []
    expected: list[dict[str, Any]] = []
    if slide_plan and slide_plan.exists():
        expected = iter_slides(load_json(slide_plan))
        if expected and len(expected) != len(texts):
            failures.append(f"slide count mismatch: pptx={len(texts)} slide_plan={len(expected)}")
        for idx, slide in enumerate(expected[: len(texts)], start=1):
            title = expected_title(slide)
            if title and normalize_text(title) not in normalize_text(texts[idx - 1]):
                failures.append(f"slide {idx} missing expected title: {title}")
    for idx, text in enumerate(texts, start=1):
        placeholder_hits = scan_patterns(text, PLACEHOLDERS)
        if placeholder_hits:
            failures.append(f"slide {idx} has placeholder residue: {', '.join(placeholder_hits)}")
        forbidden_hits = scan_patterns(text, FORBIDDEN_VISIBLE)
        if forbidden_hits:
            failures.append(f"slide {idx} has forbidden production text: {', '.join(forbidden_hits)}")
        if len(text.strip()) < 12:
            warnings.append(f"slide {idx} has very little visible text")
    image_backed_slides = [
        str(item["slide_no"]) for item in editability["slides"] if item.get("image_backed")
    ]
    if image_backed_slides and not allow_image_backed:
        failures.append(
            "slides appear to be image-backed instead of editable native PPTX content: "
            + ", ".join(image_backed_slides)
        )
    if editability["image_backed_ratio"] >= 0.8 and not allow_image_backed:
        failures.append(
            "PPTX is mostly whole-slide raster images; this is not acceptable for normal editable PPTX delivery"
        )
    elif image_backed_slides and allow_image_backed:
        warnings.append(
            "image-backed slides allowed by flag; label this artifact as non-editable/parity/social-image output"
        )
    return {
        "ok": not failures,
        "pptx": str(pptx),
        "extraction_method": extraction_method,
        "slide_count": len(texts),
        "editability": editability,
        "allow_image_backed": allow_image_backed,
        "failures": failures,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check visible text in qiaomu-ppt PPTX exports.")
    parser.add_argument("pptx", help="PPTX file to inspect")
    parser.add_argument("--slide-plan", help="Optional slide_plan.json for title/slide-count parity")
    parser.add_argument("--output", "-o", help="Optional JSON report path")
    parser.add_argument(
        "--allow-image-backed",
        action="store_true",
        help="Allow whole-slide raster PPTX exports for explicitly labelled parity/social-image artifacts.",
    )
    args = parser.parse_args()
    result = check(
        Path(args.pptx).resolve(),
        Path(args.slide_plan).resolve() if args.slide_plan else None,
        allow_image_backed=args.allow_image_backed,
    )
    if args.output:
        write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
