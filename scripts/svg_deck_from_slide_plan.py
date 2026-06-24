#!/usr/bin/env python3
"""Generate a PPT-safe SVG deck from a qiaomu-ppt slide_plan.json.

This is the SVG-first execution path. It creates editable/vector-first pages
that can be checked, finalized, previewed, and converted to native PPTX with
scripts/svg_to_pptx.py. The current renderer is intentionally opinionated:
it favors scientific/editorial decks with real images, native diagrams, and
strong page rhythm over generic card grids.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path
from typing import Any


W = 1280
H = 720

PALETTE = {
    "paper": "#F4EFE4",
    "paper2": "#E7DDCA",
    "ink": "#111827",
    "muted": "#56616F",
    "faint": "#9A8F7E",
    "dark": "#0B1628",
    "navy": "#163B63",
    "blue": "#2F66D0",
    "cyan": "#77B6EA",
    "red": "#C8472C",
    "gold": "#D8A642",
    "green": "#2D7A65",
    "white": "#FFFFFF",
    "line": "#C8BDAA",
}

RENDER_STYLE = {
    "style_id": "source-backed-editorial",
    "label": "Source-backed Editorial",
    "material": "editorial-paper",
    "palette_behavior": "warm-paper-cobalt-vermilion",
    "component_language": "editorial-hairline",
    "proof_language": "editorial-proof-objects",
}

TITLE_FONT = "Georgia, SimSun, serif"
BODY_FONT = "Arial, Microsoft YaHei, sans-serif"
MONO_FONT = "Consolas, Courier New, monospace"


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None


def esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def hex_from_swatches(swatches: list[Any], role_keywords: tuple[str, ...], fallback: str) -> str:
    for item in swatches:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").lower()
        if any(keyword in role for keyword in role_keywords):
            value = str(item.get("hex") or "").strip()
            if re.match(r"^#[0-9a-fA-F]{6}$", value):
                return value.upper()
    return fallback


def lighten_hex(value: str, amount: float = 0.12) -> str:
    value = value.strip().lstrip("#")
    if not re.match(r"^[0-9a-fA-F]{6}$", value):
        return "#E7DDCA"
    channels = [int(value[i : i + 2], 16) for i in (0, 2, 4)]
    mixed = [round(channel + (255 - channel) * amount) for channel in channels]
    return "#" + "".join(f"{max(0, min(255, channel)):02X}" for channel in mixed)


def style_material(style_id: str, palette_behavior: str) -> str:
    text_value = f"{style_id} {palette_behavior}".lower()
    if any(token in text_value for token in ("nvidia", "signal-green", "gpu")):
        return "nvidia-terminal"
    if any(token in text_value for token in ("theverge", "verge", "brutalist-tech", "cyan", "violet")):
        return "verge-neon-editorial"
    if any(token in text_value for token in ("opencode", "developer-manpage", "manpage")):
        return "opencode-manpage"
    if any(token in text_value for token in ("bento", "商务科技", "tile")):
        return "bento-tech"
    if any(token in text_value for token in ("architecture", "museum-catalog", "stone", "brass")):
        return "architecture-catalog"
    if any(token in text_value for token in ("wired", "magazine-editorial-tech")):
        return "wired-tech-magazine"
    if any(token in text_value for token in ("blueprint", "academic", "engineering", "technical")):
        return "blueprint-grid"
    if any(token in text_value for token in ("newspaper", "brutalist", "newsprint")):
        return "brutalist-newsprint"
    if re.search(r"\b(risograph|riso|zine|screen-print)\b", text_value):
        return "risograph-zine"
    if any(token in text_value for token in ("eastern", "plant-dye", "ink", "rice-paper", "cinnabar", "heritage")):
        return "eastern-rice-paper"
    if any(token in text_value for token in ("luxury", "magazine", "editorial", "digest")):
        return "luxury-editorial-paper"
    return "editorial-paper"


def component_language_for_material(material: str) -> str:
    mapping = {
        "blueprint-grid": "blueprint-annotation",
        "brutalist-newsprint": "newspaper-rulebox",
        "risograph-zine": "riso-overprint",
        "eastern-rice-paper": "ink-seal-paper",
        "luxury-editorial-paper": "folio-hairline",
        "nvidia-terminal": "gpu-control-panel",
        "verge-neon-editorial": "neon-news-module",
        "opencode-manpage": "terminal-manpage-block",
        "bento-tech": "bento-product-tile",
        "architecture-catalog": "museum-caption-frame",
        "wired-tech-magazine": "wired-index-card",
    }
    return mapping.get(material, "editorial-hairline")


def proof_language_for_material(material: str) -> str:
    mapping = {
        "blueprint-grid": "blueprint-formula-rails",
        "brutalist-newsprint": "newspaper-proof-columns",
        "risograph-zine": "riso-proof-collage",
        "eastern-rice-paper": "ink-artifact-proof",
        "luxury-editorial-paper": "folio-proof-spread",
        "nvidia-terminal": "gpu-metric-console",
        "verge-neon-editorial": "neon-argument-stack",
        "opencode-manpage": "cli-proof-transcript",
        "bento-tech": "tile-evidence-system",
        "architecture-catalog": "museum-archive-plate",
        "wired-tech-magazine": "index-proof-system",
    }
    return mapping.get(material, "editorial-proof-objects")


def apply_render_style(project: Path) -> None:
    """Project selected style_direction.json into renderer palette/material tokens."""
    path = project / "style_direction.json"
    if not path.exists():
        return
    try:
        direction = load_json(path)
    except Exception:
        return
    if not isinstance(direction, dict):
        return
    selected = direction.get("selected_style") if isinstance(direction.get("selected_style"), dict) else {}
    contract = direction.get("style_contract") if isinstance(direction.get("style_contract"), dict) else {}
    palette = contract.get("palette") if isinstance(contract.get("palette"), dict) else {}
    strategy = contract.get("image_asset_strategy") if isinstance(contract.get("image_asset_strategy"), dict) else {}
    typography = contract.get("typography") if isinstance(contract.get("typography"), dict) else {}
    swatches = palette.get("swatches") if isinstance(palette.get("swatches"), list) else []
    style_id = str(selected.get("id") or "source-backed-editorial")
    behavior = str(strategy.get("image_palette_behavior") or strategy.get("image_rendering") or "")
    material = style_material(style_id, behavior)

    primary = str(palette.get("primary") or "").strip()
    canvas = str(palette.get("canvas") or "").strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", primary):
        primary = hex_from_swatches(swatches, ("blue", "ink", "primary", "mist"), PALETTE["blue"])
    if not re.match(r"^#[0-9a-fA-F]{6}$", canvas):
        canvas = hex_from_swatches(swatches, ("paper", "canvas", "newsprint", "rice"), PALETTE["paper"])

    palette_updates: dict[str, str] = {
        "paper": canvas.upper(),
        "paper2": lighten_hex(canvas, 0.28),
        "blue": hex_from_swatches(swatches, ("blue", "primary", "mist"), primary),
        "red": hex_from_swatches(swatches, ("red", "cinnabar", "pink", "signal"), PALETTE["red"]),
        "gold": hex_from_swatches(swatches, ("gold", "ochre", "plant"), PALETTE["gold"]),
        "green": hex_from_swatches(swatches, ("green", "leaf"), PALETTE["green"]),
        "ink": hex_from_swatches(swatches, ("ink", "text"), PALETTE["ink"]),
        "muted": hex_from_swatches(swatches, ("muted", "body"), PALETTE["muted"]),
        "line": hex_from_swatches(swatches, ("rule", "line", "border"), PALETTE["line"]),
    }
    if material == "blueprint-grid":
        palette_updates.update({"paper2": "#EBF4FB", "dark": "#102A43", "navy": primary.upper(), "cyan": "#63B3ED"})
    elif material == "brutalist-newsprint":
        palette_updates.update({"dark": "#111111", "navy": "#111111", "cyan": palette_updates["muted"]})
    elif material == "risograph-zine":
        palette_updates.update({"paper2": "#ECE2CE", "dark": "#1A1A1A", "navy": primary.upper(), "cyan": "#5C7CFF"})
    elif material == "eastern-rice-paper":
        palette_updates.update({"paper2": "#E9E0D0", "dark": "#25342E", "navy": "#355F6D", "cyan": "#A8C5C9"})
    elif material == "luxury-editorial-paper":
        palette_updates.update({"paper2": "#E7DDCA", "dark": "#111111", "navy": "#34251D", "cyan": "#C7A96B"})
    elif material == "nvidia-terminal":
        palette_updates.update({"paper": "#080A07", "paper2": "#11160E", "dark": "#050705", "navy": "#0F1A10", "blue": "#76B900", "cyan": "#C5FF35", "red": "#76B900", "ink": "#F4F8EF", "muted": "#9AA497", "line": "#263322"})
    elif material == "verge-neon-editorial":
        palette_updates.update({"paper": "#131313", "paper2": "#1A1A1A", "dark": "#0A0A0A", "navy": "#5200FF", "blue": "#3CFFD0", "cyan": "#3CFFD0", "red": "#FF3864", "ink": "#F8F8F8", "muted": "#B8B8B8", "line": "#2D2D2D"})
    elif material == "opencode-manpage":
        palette_updates.update({"paper": "#FDFCFC", "paper2": "#EFECE8", "dark": "#201D1D", "navy": "#302C2C", "blue": "#E15B3A", "cyan": "#6F6A65", "red": "#E15B3A", "ink": "#201D1D", "muted": "#56514D", "line": "#D8D2CA"})
    elif material == "bento-tech":
        palette_updates.update({"paper": "#F8FAFC", "paper2": "#E2E8F0", "dark": "#0F172A", "navy": "#1D4ED8", "blue": "#1D4ED8", "cyan": "#06B6D4", "red": "#F97316", "ink": "#0F172A", "muted": "#475569", "line": "#CBD5E1"})
    elif material == "architecture-catalog":
        palette_updates.update({"paper": "#F3EFE8", "paper2": "#E5D8CA", "dark": "#2C2A27", "navy": "#4C433A", "blue": "#A4743B", "cyan": "#C8B8A6", "red": "#A4743B", "ink": "#2C2A27", "muted": "#726A60", "line": "#C8B8A6"})
    elif material == "wired-tech-magazine":
        palette_updates.update({"paper": "#FFFFFF", "paper2": "#F2F2F2", "dark": "#000000", "navy": "#000000", "blue": "#000000", "cyan": "#00AEEF", "red": "#D71920", "ink": "#000000", "muted": "#5F5F5F", "line": "#D9D9D9"})

    PALETTE.update(palette_updates)

    global TITLE_FONT, BODY_FONT, MONO_FONT
    title_font = str(typography.get("display") or "").split("/")[0].strip()
    body_font = str(typography.get("body") or "").split("/")[0].strip()
    mono_font = str(typography.get("mono") or "").split("/")[0].strip()
    if title_font:
        TITLE_FONT = f"{title_font}, Georgia, SimSun, serif"
    if body_font:
        BODY_FONT = f"{body_font}, Arial, Microsoft YaHei, sans-serif"
    if mono_font:
        MONO_FONT = f"{mono_font}, Consolas, Courier New, monospace"

    RENDER_STYLE.update(
        {
            "style_id": style_id,
            "label": str(selected.get("label") or style_id),
            "material": material,
            "palette_behavior": behavior or material,
            "component_language": component_language_for_material(material),
            "proof_language": proof_language_for_material(material),
        }
    )


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, list):
        return [s for s in plan if isinstance(s, dict)]
    if isinstance(plan, dict):
        for key in ("slides", "slide_plan", "pages"):
            value = plan.get(key)
            if isinstance(value, list):
                return [s for s in value if isinstance(s, dict)]
    return []


def title_of(slide: dict[str, Any]) -> str:
    return str(slide.get("claim_title") or slide.get("title") or "").strip()


def points_of(slide: dict[str, Any]) -> list[str]:
    value = slide.get("content_points") or slide.get("points") or slide.get("bullets") or []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


EINSTEIN_TOKENS = (
    "einstein",
    "爱因斯坦",
    "albert",
    "相对论",
    "光电效应",
    "布朗运动",
    "质能",
    "e=mc",
    "e = mc",
    "时空",
    "引力",
    "1905",
)


def slide_text_blob(slide: dict[str, Any]) -> str:
    parts: list[str] = [title_of(slide), *points_of(slide)]
    for key in ("source_anchor", "speaker_note_goal", "proof_object", "visual_role", "media_need"):
        value = slide.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def is_einstein_deck(slides: list[dict[str, Any]]) -> bool:
    blob = " ".join(slide_text_blob(slide) for slide in slides).lower()
    return any(token.lower() in blob for token in EINSTEIN_TOKENS)


def deck_label(slide: dict[str, Any] | None = None) -> str:
    title = title_of(slide or {}) if slide else ""
    label = re.sub(r"\s+", " ", title).strip()
    if label:
        return label[:34]
    return "QIAOMU PPT / SOURCE-BACKED DECK"


def keywords_for_slide(slide: dict[str, Any], limit: int = 6) -> list[str]:
    text_value = "。".join([title_of(slide), *points_of(slide)])
    parts = re.split(r"[，。；、:：,.|/()\[\]《》“”\"'\s]+", text_value)
    keywords: list[str] = []
    for raw in parts:
        item = raw.strip()
        if len(item) < 2:
            continue
        if len(item) > 10:
            item = item[:10]
        if item not in keywords:
            keywords.append(item)
        if len(keywords) >= limit:
            break
    return keywords


def years_from_slide(slide: dict[str, Any], limit: int = 5) -> list[str]:
    years: list[str] = []
    for match in re.finditer(r"\b(1[5-9]\d{2}|20\d{2})\b", slide_text_blob(slide)):
        year = match.group(1)
        if year not in years:
            years.append(year)
        if len(years) >= limit:
            break
    return years


def cjk_wrap(text: str, limit: int) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return [text]
    lines: list[str] = []
    buf = ""
    count = 0.0
    for ch in text:
        weight = 0.55 if ord(ch) < 128 else 1.0
        if count + weight > limit and buf:
            lines.append(buf.rstrip())
            buf = ch
            count = weight
        else:
            buf += ch
            count += weight
    if buf:
        lines.append(buf.rstrip())
    return lines


def text(
    x: float,
    y: float,
    content: str | list[str],
    *,
    size: int = 24,
    fill: str = PALETTE["ink"],
    family: str = BODY_FONT,
    weight: str = "400",
    anchor: str = "start",
    line_height: float = 1.25,
    opacity: float | None = None,
    rotate: float | None = None,
    letter_spacing: float | None = None,
) -> str:
    lines = content if isinstance(content, list) else [content]
    attrs = [
        f'x="{x:.1f}"',
        f'y="{y:.1f}"',
        f'font-family="{esc(family)}"',
        f'font-size="{size}"',
        f'font-weight="{weight}"',
        f'fill="{fill}"',
        f'text-anchor="{anchor}"',
    ]
    if opacity is not None:
        attrs.append(f'fill-opacity="{opacity:.3f}"')
    if rotate:
        attrs.append(f'transform="rotate({rotate:.2f} {x:.1f} {y:.1f})"')
    if letter_spacing is not None:
        attrs.append(f'letter-spacing="{letter_spacing:.2f}"')
    tspans = []
    for idx, line in enumerate(lines):
        dy = 0 if idx == 0 else size * line_height
        tspans.append(f'<tspan x="{x:.1f}" dy="{dy:.1f}">{esc(line)}</tspan>')
    return f'<text {" ".join(attrs)}>{"".join(tspans)}</text>'


def rect(
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = "none",
    *,
    stroke: str | None = None,
    sw: float = 1,
    rx: float = 0,
    opacity: float | None = None,
    fill_opacity: float | None = None,
    dash: str | None = None,
) -> str:
    attrs = [
        f'x="{x:.1f}"',
        f'y="{y:.1f}"',
        f'width="{w:.1f}"',
        f'height="{h:.1f}"',
        f'fill="{fill}"',
    ]
    if rx:
        attrs.append(f'rx="{rx:.1f}"')
    if stroke:
        attrs.append(f'stroke="{stroke}" stroke-width="{sw:.1f}"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity:.3f}"')
    if fill_opacity is not None:
        attrs.append(f'fill-opacity="{fill_opacity:.3f}"')
    if dash:
        attrs.append(f'stroke-dasharray="{dash}"')
    return f'<rect {" ".join(attrs)}/>'


def circle(cx: float, cy: float, r: float, fill: str, *, stroke: str | None = None, sw: float = 1,
           opacity: float | None = None, fill_opacity: float | None = None) -> str:
    attrs = [f'cx="{cx:.1f}"', f'cy="{cy:.1f}"', f'r="{r:.1f}"', f'fill="{fill}"']
    if stroke:
        attrs.append(f'stroke="{stroke}" stroke-width="{sw:.1f}"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity:.3f}"')
    if fill_opacity is not None:
        attrs.append(f'fill-opacity="{fill_opacity:.3f}"')
    return f'<circle {" ".join(attrs)}/>'


def line(x1: float, y1: float, x2: float, y2: float, stroke: str, *, sw: float = 1,
         opacity: float | None = None, dash: str | None = None) -> str:
    attrs = [
        f'x1="{x1:.1f}"',
        f'y1="{y1:.1f}"',
        f'x2="{x2:.1f}"',
        f'y2="{y2:.1f}"',
        f'stroke="{stroke}"',
        f'stroke-width="{sw:.1f}"',
    ]
    if opacity is not None:
        attrs.append(f'stroke-opacity="{opacity:.3f}"')
    if dash:
        attrs.append(f'stroke-dasharray="{dash}"')
    return f'<line {" ".join(attrs)}/>'


def path(d: str, stroke: str = PALETTE["ink"], *, fill: str = "none", sw: float = 2,
         opacity: float | None = None, dash: str | None = None) -> str:
    attrs = [f'd="{esc(d)}"', f'fill="{fill}"', f'stroke="{stroke}"', f'stroke-width="{sw:.1f}"']
    if opacity is not None:
        attrs.append(f'stroke-opacity="{opacity:.3f}"')
    if dash:
        attrs.append(f'stroke-dasharray="{dash}"')
    return f'<path {" ".join(attrs)}/>'


def image_tag(href: str, x: float, y: float, w: float, h: float, *, preserve: str = "xMidYMid slice",
              clip_id: str | None = None, opacity: float | None = None) -> str:
    attrs = [
        f'href="{esc(href)}"',
        f'x="{x:.1f}"',
        f'y="{y:.1f}"',
        f'width="{w:.1f}"',
        f'height="{h:.1f}"',
        f'preserveAspectRatio="{preserve}"',
    ]
    if clip_id:
        attrs.append(f'clip-path="url(#{clip_id})"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity:.3f}"')
    return f'<image {" ".join(attrs)}/>'


def attr_float(markup: str, name: str) -> float | None:
    match = re.search(rf'\b{name}="(-?\d+(?:\.\d+)?)"', markup)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def group_markup(group_id: str, role: str, lines: list[str]) -> str:
    content = "\n".join(line for line in lines if line.strip())
    return f'<g id="{group_id}" data-role="{role}">\n{content}\n</g>'


def classify_svg_line(line_text: str, *, before_reading_content: bool) -> str:
    stripped = line_text.strip()
    if not stripped:
        return "proof"
    if "<defs" in stripped or stripped.startswith("</defs") or stripped.startswith("<linearGradient") or stripped.startswith("</linearGradient"):
        return "defs"
    if any(token in stripped for token in ('y="672.0"', 'y="698.0"', 'ALBERT EINSTEIN')) or re.search(r"\d{2}\s*/\s*\d{2}", stripped):
        return "footer"
    if stripped.startswith("<image"):
        return "media"
    if before_reading_content and not stripped.startswith("<text") and not stripped.startswith("<image"):
        return "background"
    if stripped.startswith("<text"):
        y = attr_float(stripped, "y") or 0
        size = attr_float(stripped, "font-size") or 0
        if y <= 170 or (size >= 50 and y <= 280) or (size >= 34 and y <= 230):
            return "title"
        if size >= 34:
            return "proof"
        return "body"
    return "proof"


def semantic_group_body(slide_no: int, body: str) -> tuple[str, list[str]]:
    """Wrap top-level SVG elements into stable semantic groups.

    The grouping is deliberately z-order preserving: consecutive elements with
    the same semantic role become one top-level group. This gives PowerPoint
    usable group anchors without changing visual stacking.
    """
    groups: list[str] = []
    group_ids: list[str] = []
    current_role: str | None = None
    current_lines: list[str] = []
    role_counts: dict[str, int] = {}
    before_reading_content = True

    def flush() -> None:
        nonlocal current_role, current_lines
        if not current_lines or current_role is None:
            current_lines = []
            current_role = None
            return
        role_counts[current_role] = role_counts.get(current_role, 0) + 1
        suffix = "" if role_counts[current_role] == 1 else f"-{role_counts[current_role]}"
        group_id = f"slide-{slide_no:02d}-{current_role}{suffix}"
        groups.append(group_markup(group_id, current_role, current_lines))
        group_ids.append(group_id)
        current_lines = []
        current_role = None

    for raw_line in body.splitlines():
        if not raw_line.strip():
            continue
        role = classify_svg_line(raw_line, before_reading_content=before_reading_content)
        if role == "defs":
            continue
        if role not in {"background"}:
            before_reading_content = False
        if current_role != role:
            flush()
            current_role = role
        current_lines.append(raw_line)
    flush()
    return "\n".join(groups), group_ids


def defs(slide_no: int) -> str:
    return f"""<defs>
  <linearGradient id="blueScrim{slide_no}" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="{PALETTE['dark']}" stop-opacity="0.94"/>
    <stop offset="64%" stop-color="{PALETTE['dark']}" stop-opacity="0.62"/>
    <stop offset="100%" stop-color="{PALETTE['dark']}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="paperFade{slide_no}" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="{PALETTE['paper']}" stop-opacity="1"/>
    <stop offset="100%" stop-color="{PALETTE['paper2']}" stop-opacity="1"/>
  </linearGradient>
  <linearGradient id="softPaperScrim{slide_no}" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="{PALETTE['paper']}" stop-opacity="0.94"/>
    <stop offset="62%" stop-color="{PALETTE['paper']}" stop-opacity="0.78"/>
    <stop offset="100%" stop-color="{PALETTE['paper']}" stop-opacity="0"/>
  </linearGradient>
  <clipPath id="photoClip{slide_no}">
    <rect x="720" y="64" width="500" height="592" rx="10"/>
  </clipPath>
  <clipPath id="wideClip{slide_no}">
    <rect x="60" y="104" width="1160" height="430" rx="8"/>
  </clipPath>
  <marker id="arrow{slide_no}" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L10,5 L0,10 Z" fill="{PALETTE['red']}"/>
  </marker>
</defs>"""


def style_canvas_folio(slide_no: int, *, dark: bool = False) -> str:
    material = str(RENDER_STYLE.get("material") or "editorial-paper")
    fill = PALETTE["white"] if dark else PALETTE["muted"]
    accent = PALETTE["cyan"] if material == "blueprint-grid" else PALETTE["red"]
    labels = {
        "blueprint-grid": "GRID SYSTEM",
        "brutalist-newsprint": "NEWS FIELD",
        "risograph-zine": "RISO PRINT",
        "eastern-rice-paper": "纸本",
        "luxury-editorial-paper": "LUXE FOLIO",
        "nvidia-terminal": "GPU CONSOLE",
        "verge-neon-editorial": "EDGE SIGNAL",
        "opencode-manpage": "MANPAGE",
        "bento-tech": "BENTO SYSTEM",
        "architecture-catalog": "ARCHIVE PLATE",
        "wired-tech-magazine": "WIRED INDEX",
        "editorial-paper": "EDITORIAL FOLIO",
    }
    label = labels.get(material, "EDITORIAL FOLIO")
    return "\n".join([
        line(1082, 24, 1218, 24, accent, sw=0.8, opacity=0.38),
        text(1218, 18, f"{label} {slide_no:02d}", size=7, fill=fill, family=MONO_FONT if re.search(r"[A-Za-z]", label) else BODY_FONT, weight="700", anchor="end", opacity=0.58, letter_spacing=0.8 if re.search(r"[A-Za-z]", label) else None),
    ])


def paper_bg(slide_no: int, dark: bool = False) -> str:
    material = str(RENDER_STYLE.get("material") or "editorial-paper")
    if dark:
        bg = [rect(0, 0, W, H, PALETTE["dark"])]
        if material == "blueprint-grid":
            for x in range(80, 1240, 80):
                bg.append(line(x, 0, x, H, PALETTE["cyan"], sw=0.7, opacity=0.13))
            for y in range(80, 680, 80):
                bg.append(line(0, y, W, y, PALETTE["cyan"], sw=0.7, opacity=0.13))
            for x in range(160, 1220, 160):
                bg.append(line(x, 0, x, H, PALETTE["white"], sw=1.0, opacity=0.08))
            bg.append(rect(72, 64, 1136, 590, "none", stroke=PALETTE["cyan"], sw=1.1, opacity=0.35))
        elif material == "brutalist-newsprint":
            bg.append(rect(0, 0, W, 96, PALETTE["white"], fill_opacity=0.08))
            for x in (320, 640, 960):
                bg.append(line(x, 96, x, 650, PALETTE["white"], sw=1.0, opacity=0.16))
            for y in range(146, 650, 92):
                bg.append(line(68, y, 1212, y, PALETTE["white"], sw=0.8, opacity=0.10))
            bg.append(rect(78, 118, 214, 54, PALETTE["red"], fill_opacity=0.82))
        elif material == "risograph-zine":
            for x in range(70, 1230, 38):
                for y in range(62, 660, 38):
                    if (x + y + slide_no * 11) % 3 == 0:
                        bg.append(circle(x, y, 1.7, PALETTE["red"], fill_opacity=0.20))
            bg.append(rect(84, 72, 1112, 568, "none", stroke=PALETTE["blue"], sw=2.2, opacity=0.42))
            bg.append(rect(98, 86, 1112, 568, "none", stroke=PALETTE["red"], sw=1.4, opacity=0.28))
        elif material == "eastern-rice-paper":
            for y in range(92, 650, 66):
                bg.append(path(f"M72,{y} C250,{y - 16} 380,{y + 20} 560,{y - 4} S940,{y + 8} 1190,{y - 12}", PALETTE["cyan"], sw=0.9, opacity=0.12))
            bg.append(rect(1112, 92, 48, 48, PALETTE["red"], fill_opacity=0.55))
            bg.append(text(1124, 124, "印", size=18, fill=PALETTE["paper"], family=TITLE_FONT, weight="700"))
            bg.append(rect(76, 62, 1128, 592, "none", stroke=PALETTE["gold"], sw=1.0, opacity=0.18))
        elif material == "nvidia-terminal":
            bg.append(rect(0, 0, W, H, PALETTE["dark"]))
            for x in range(64, 1240, 96):
                bg.append(line(x, 72, x, 650, PALETTE["line"], sw=0.8, opacity=0.42))
            for y in range(84, 650, 84):
                bg.append(line(56, y, 1224, y, PALETTE["line"], sw=0.8, opacity=0.36))
            for i, x in enumerate(range(760, 1160, 92)):
                bg.append(rect(x, 114 + (i % 3) * 46, 62, 62, "none", stroke=PALETTE["blue"], sw=1.4, opacity=0.48))
            bg.append(rect(64, 58, 1152, 600, "none", stroke=PALETTE["blue"], sw=1.2, opacity=0.50))
        elif material == "verge-neon-editorial":
            bg.append(rect(0, 0, W, H, PALETTE["dark"]))
            bg.append(rect(0, 0, W, 92, PALETTE["navy"], fill_opacity=0.52))
            bg.append(rect(0, 604, W, 116, PALETTE["blue"], fill_opacity=0.16))
            bg.append(line(72, 118, 1208, 118, PALETTE["blue"], sw=2.6, opacity=0.75))
            bg.append(line(72, 598, 1208, 598, PALETTE["red"], sw=2.2, opacity=0.65))
            bg.append(rect(864, 146, 260, 260, "none", stroke=PALETTE["blue"], sw=1.1, opacity=0.28))
        elif material == "opencode-manpage":
            bg.append(rect(46, 44, 1188, 632, PALETTE["paper"], fill_opacity=0.96))
            for y in range(100, 642, 32):
                bg.append(line(78, y, 1204, y, PALETTE["line"], sw=0.7, opacity=0.52))
            bg.append(rect(78, 70, 1126, 34, PALETTE["dark"], fill_opacity=0.94))
            bg.append(text(96, 92, "PG_EARN(1)  Startup Wealth Manual", size=13, fill=PALETTE["paper"], family=MONO_FONT, weight="700"))
        elif material == "bento-tech":
            bg.append(rect(52, 48, 1176, 620, PALETTE["paper"], fill_opacity=0.98))
            for x, y, w, h in ((76, 92, 312, 190), (414, 92, 352, 190), (792, 92, 360, 190), (76, 308, 448, 260), (550, 308, 602, 260)):
                bg.append(rect(x, y, w, h, PALETTE["white"], stroke=PALETTE["line"], sw=1.0, rx=14, opacity=0.46))
            bg.append(rect(52, 48, 1176, 620, "none", stroke=PALETTE["line"], sw=1.0, opacity=0.72))
        elif material == "architecture-catalog":
            bg.append(rect(80, 56, 1120, 608, "none", stroke=PALETTE["line"], sw=1.0, opacity=0.74))
            bg.append(rect(108, 84, 320, 496, PALETTE["cyan"], fill_opacity=0.14))
            bg.append(rect(466, 84, 248, 496, PALETTE["white"], fill_opacity=0.36))
            bg.append(rect(752, 84, 340, 496, PALETTE["cyan"], fill_opacity=0.10))
            for x in (428, 714, 1092):
                bg.append(line(x, 84, x, 580, PALETTE["line"], sw=0.8, opacity=0.82))
        elif material == "wired-tech-magazine":
            bg.append(rect(0, 0, W, 42, PALETTE["ink"]))
            bg.append(rect(52, 68, 1176, 578, PALETTE["white"], stroke=PALETTE["line"], sw=1.0))
            for x in range(112, 1210, 112):
                bg.append(line(x, 68, x, 646, PALETTE["line"], sw=0.65, opacity=0.38))
            bg.append(rect(52, 68, 128, 36, PALETTE["red"], fill_opacity=0.95))
        else:
            bg.append(circle(1070, 120, 260, PALETTE["blue"], fill_opacity=0.13))
            bg.append(circle(1010, 580, 360, PALETTE["red"], fill_opacity=0.07))
            for x in range(72, 1240, 76):
                bg.append(line(x, 0, x + 220, 720, PALETTE["white"], sw=0.8, opacity=0.045))
        bg.append(style_canvas_folio(slide_no, dark=True))
        return "\n".join(bg)
    bg = [rect(0, 0, W, H, f"url(#paperFade{slide_no})")]
    if material == "blueprint-grid":
        bg.append(rect(0, 0, W, 18, PALETTE["blue"], fill_opacity=0.95))
        for x in range(60, 1230, 40):
            bg.append(line(x, 52, x, 668, PALETTE["blue"], sw=0.55, opacity=0.15))
        for y in range(72, 672, 40):
            bg.append(line(52, y, 1228, y, PALETTE["blue"], sw=0.55, opacity=0.15))
        for x in range(120, 1220, 160):
            bg.append(line(x, 52, x, 668, PALETTE["blue"], sw=1.0, opacity=0.22))
        for y in range(112, 650, 160):
            bg.append(line(52, y, 1228, y, PALETTE["blue"], sw=1.0, opacity=0.22))
        bg.append(rect(44, 36, 1192, 648, "none", stroke=PALETTE["blue"], sw=1.1, opacity=0.36))
    elif material == "brutalist-newsprint":
        bg.append(rect(0, 0, W, 20, PALETTE["dark"]))
        bg.append(line(60, 104, 1220, 104, PALETTE["ink"], sw=2.0, opacity=0.82))
        bg.append(line(60, 610, 1220, 610, PALETTE["ink"], sw=2.0, opacity=0.68))
        for x in (346, 640, 934):
            bg.append(line(x, 124, x, 592, PALETTE["line"], sw=1.0, opacity=0.92))
        for y in range(154, 590, 74):
            bg.append(line(60, y, 1220, y, PALETTE["line"], sw=0.75, opacity=0.42))
        bg.append(rect(60, 52, 132, 36, PALETTE["red"], fill_opacity=0.92))
    elif material == "risograph-zine":
        bg.append(rect(0, 0, W, 18, PALETTE["blue"], fill_opacity=0.88))
        for x in range(74, 1230, 36):
            for y in range(72, 658, 36):
                if (x * 3 + y + slide_no * 17) % 5 == 0:
                    bg.append(circle(x, y, 1.45, PALETTE["red"], fill_opacity=0.26))
                elif (x + y) % 7 == 0:
                    bg.append(circle(x, y, 1.2, PALETTE["blue"], fill_opacity=0.18))
        bg.append(rect(48, 42, 1184, 636, "none", stroke=PALETTE["blue"], sw=2.2, opacity=0.40))
        bg.append(rect(60, 54, 1184, 636, "none", stroke=PALETTE["red"], sw=1.2, opacity=0.28))
    elif material == "eastern-rice-paper":
        bg.append(rect(0, 0, W, 18, PALETTE["red"], fill_opacity=0.78))
        bg.append(rect(44, 36, 1192, 648, "none", stroke=PALETTE["gold"], sw=1.0, opacity=0.24))
        for y in range(94, 680, 82):
            bg.append(path(f"M62,{y} C260,{y - 14} 410,{y + 18} 590,{y - 2} S930,{y + 6} 1220,{y - 12}", PALETTE["cyan"], sw=0.8, opacity=0.16))
        for x in range(110, 1200, 130):
            bg.append(line(x, 60, x - 34, 660, PALETTE["line"], sw=0.7, opacity=0.16))
        bg.append(rect(1128, 82, 40, 40, PALETTE["red"], fill_opacity=0.68))
        bg.append(text(1138, 109, "乔", size=15, fill=PALETTE["paper"], family=TITLE_FONT, weight="700"))
    elif material == "nvidia-terminal":
        bg.append(rect(0, 0, W, H, PALETTE["dark"]))
        bg.append(rect(0, 0, W, 18, PALETTE["blue"], fill_opacity=0.95))
        for x in range(64, 1240, 96):
            bg.append(line(x, 58, x, 660, PALETTE["line"], sw=0.75, opacity=0.42))
        for y in range(84, 668, 84):
            bg.append(line(56, y, 1224, y, PALETTE["line"], sw=0.75, opacity=0.36))
        bg.append(rect(52, 42, 1176, 636, "none", stroke=PALETTE["blue"], sw=1.2, opacity=0.52))
    elif material == "verge-neon-editorial":
        bg.append(rect(0, 0, W, H, PALETTE["dark"]))
        bg.append(rect(0, 0, W, 92, PALETTE["navy"], fill_opacity=0.58))
        bg.append(rect(0, 604, W, 116, PALETTE["blue"], fill_opacity=0.14))
        bg.append(line(58, 108, 1220, 108, PALETTE["blue"], sw=2.4, opacity=0.75))
        bg.append(line(58, 610, 1220, 610, PALETTE["red"], sw=2.0, opacity=0.62))
    elif material == "opencode-manpage":
        bg.append(rect(48, 42, 1184, 636, PALETTE["white"], stroke=PALETTE["line"], sw=1.0))
        for y in range(108, 642, 32):
            bg.append(line(78, y, 1204, y, PALETTE["line"], sw=0.7, opacity=0.48))
        bg.append(rect(78, 72, 1126, 30, PALETTE["dark"], fill_opacity=0.94))
    elif material == "bento-tech":
        bg.append(rect(0, 0, W, H, PALETTE["paper2"], fill_opacity=0.70))
        for x, y, w, h in ((60, 62, 350, 194), (432, 62, 362, 194), (816, 62, 350, 194), (60, 282, 520, 332), (604, 282, 562, 332)):
            bg.append(rect(x, y, w, h, PALETTE["white"], stroke=PALETTE["line"], sw=1.0, rx=14, opacity=0.52))
    elif material == "architecture-catalog":
        bg.append(rect(80, 56, 1120, 608, "none", stroke=PALETTE["line"], sw=1.0, opacity=0.76))
        bg.append(rect(108, 84, 300, 498, PALETTE["cyan"], fill_opacity=0.16))
        bg.append(line(444, 84, 444, 582, PALETTE["line"], sw=0.8, opacity=0.80))
        bg.append(line(778, 84, 778, 582, PALETTE["line"], sw=0.8, opacity=0.80))
    elif material == "wired-tech-magazine":
        bg.append(rect(0, 0, W, 42, PALETTE["ink"]))
        bg.append(rect(52, 68, 1176, 578, PALETTE["white"], stroke=PALETTE["line"], sw=1.0))
        for x in range(112, 1210, 112):
            bg.append(line(x, 68, x, 646, PALETTE["line"], sw=0.65, opacity=0.38))
        bg.append(rect(52, 68, 128, 36, PALETTE["red"], fill_opacity=0.95))
    else:
        bg.append(rect(44, 36, 1192, 648, "none", stroke=PALETTE["line"], sw=1))
        bg.append(rect(0, 0, W, 18, PALETTE["dark"]))
        for y in range(96, 680, 80):
            bg.append(line(60, y, 1220, y, PALETTE["line"], sw=0.8, opacity=0.32))
        for x in range(100, 1220, 120):
            bg.append(line(x, 60, x, 660, PALETTE["line"], sw=0.8, opacity=0.16, dash="2 10"))
        bg.append(circle(1110, 108, 92, PALETTE["blue"], fill_opacity=0.06))
        bg.append(circle(1088, 520, 180, PALETTE["red"], fill_opacity=0.04))
    bg.append(style_canvas_folio(slide_no, dark=False))
    return "\n".join(bg)


def footer(slide_no: int, total: int, *, dark: bool = False) -> str:
    fill = PALETTE["white"] if dark else PALETTE["muted"]
    return "\n".join([
        line(60, 672, 1220, 672, PALETTE["white"] if dark else PALETTE["line"], sw=1, opacity=0.55),
        text(60, 698, "ALBERT EINSTEIN / A SCIENTIFIC BIOGRAPHY", size=11, fill=fill, family=MONO_FONT, opacity=0.78),
        text(1220, 698, f"{slide_no:02d} / {total:02d}", size=11, fill=fill, family=MONO_FONT, anchor="end", opacity=0.78),
    ])


def style_title_marker(slide_no: int, *, dark: bool = False) -> list[str]:
    material = str(RENDER_STYLE.get("material") or "editorial-paper")
    ink = PALETTE["white"] if dark else PALETTE["ink"]
    muted = PALETTE["white"] if dark else PALETTE["muted"]
    if material == "blueprint-grid":
        return [
            rect(56, 44, 42, 42, "none", stroke=PALETTE["blue"], sw=1.1, opacity=0.65),
            line(56, 65, 98, 65, PALETTE["blue"], sw=0.9, opacity=0.45),
            line(77, 44, 77, 86, PALETTE["blue"], sw=0.9, opacity=0.45),
            text(112, 50, f"GRID P{slide_no:02d}", size=10, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ]
    if material == "brutalist-newsprint":
        return [
            rect(56, 42, 96, 28, PALETTE["ink"], fill_opacity=0.92),
            text(66, 62, f"PAGE {slide_no:02d}", size=12, fill=PALETTE["paper"], family=MONO_FONT, weight="700", letter_spacing=0.7),
            line(162, 56, 1218, 56, ink, sw=2.2, opacity=0.88),
        ]
    if material == "risograph-zine":
        return [
            rect(57, 48, 48, 28, PALETTE["red"], fill_opacity=0.72),
            rect(62, 54, 48, 28, PALETTE["blue"], fill_opacity=0.54),
            text(70, 73, f"{slide_no:02d}", size=15, fill=PALETTE["paper"], family=MONO_FONT, weight="700"),
            text(118, 65, f"RISO P{slide_no:02d}", size=9, fill=PALETTE["red"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ]
    if material == "eastern-rice-paper":
        return [
            line(76, 42, 76, 124, PALETTE["gold"], sw=1.1, opacity=0.55),
            rect(56, 48, 38, 38, PALETTE["red"], fill_opacity=0.72),
            text(66, 74, f"{slide_no}", size=15, fill=PALETTE["paper"], family=TITLE_FONT, weight="700"),
        ]
    if material == "luxury-editorial-paper":
        return [
            line(60, 50, 1220, 50, PALETTE["gold"], sw=0.9, opacity=0.68),
            text(60, 72, f"FOLIO {slide_no:02d}", size=10, fill=muted, family=MONO_FONT, weight="700", letter_spacing=1.1),
        ]
    if material == "nvidia-terminal":
        return [
            rect(56, 46, 92, 28, PALETTE["blue"], fill_opacity=0.92),
            text(68, 66, f"GPU {slide_no:02d}", size=11, fill=PALETTE["dark"], family=MONO_FONT, weight="700", letter_spacing=0.7),
            line(160, 60, 1218, 60, PALETTE["blue"], sw=1.4, opacity=0.54),
        ]
    if material == "verge-neon-editorial":
        return [
            rect(56, 42, 112, 30, PALETTE["blue"], fill_opacity=0.92),
            rect(168, 42, 18, 30, PALETTE["red"], fill_opacity=0.92),
            text(68, 64, f"EDGE {slide_no:02d}", size=11, fill=PALETTE["dark"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ]
    if material == "opencode-manpage":
        return [
            text(60, 62, f"::{slide_no:02d}", size=18, fill=PALETTE["blue"], family=MONO_FONT, weight="700"),
            text(114, 62, "SYNOPSIS", size=10, fill=muted, family=MONO_FONT, weight="700", letter_spacing=1.0),
        ]
    if material == "bento-tech":
        return [
            rect(56, 44, 42, 42, PALETTE["blue"], rx=10, fill_opacity=0.92),
            text(69, 72, f"{slide_no}", size=18, fill=PALETTE["white"], family=MONO_FONT, weight="700"),
            text(112, 65, "BENTO VIEW", size=10, fill=muted, family=MONO_FONT, weight="700", letter_spacing=0.9),
        ]
    if material == "architecture-catalog":
        return [
            line(60, 50, 1220, 50, PALETTE["line"], sw=1.0, opacity=0.85),
            text(60, 72, f"PLATE {slide_no:02d}", size=10, fill=PALETTE["red"], family=MONO_FONT, weight="700", letter_spacing=1.2),
            line(60, 82, 218, 82, PALETTE["red"], sw=1.0, opacity=0.55),
        ]
    if material == "wired-tech-magazine":
        return [
            rect(56, 42, 84, 28, PALETTE["red"], fill_opacity=0.95),
            text(68, 63, f"{slide_no:02d}", size=13, fill=PALETTE["white"], family=MONO_FONT, weight="700"),
            text(156, 62, "FIELD INDEX", size=10, fill=muted, family=MONO_FONT, weight="700", letter_spacing=1.1),
        ]
    return []


def generic_footer(slide_no: int, total: int, slide: dict[str, Any], *, dark: bool = False) -> str:
    fill = PALETTE["white"] if dark else PALETTE["muted"]
    label = deck_label(slide).upper() if re.search(r"[A-Za-z]", deck_label(slide)) else deck_label(slide)
    return "\n".join([
        line(60, 672, 1220, 672, PALETTE["white"] if dark else PALETTE["line"], sw=1, opacity=0.55),
        text(60, 698, label, size=11, fill=fill, family=MONO_FONT if re.search(r"[A-Za-z]", label) else BODY_FONT, opacity=0.78),
        text(1220, 698, f"{slide_no:02d} / {total:02d}", size=11, fill=fill, family=MONO_FONT, anchor="end", opacity=0.78),
    ])


def page_title(slide_no: int, title: str, *, dark: bool = False) -> str:
    fill = PALETTE["white"] if dark else PALETTE["ink"]
    candidate_lines = cjk_wrap(title, 21)
    title_size = 31 if len(candidate_lines) <= 2 else 28
    lines = candidate_lines[: 3 if len(candidate_lines) > 2 else 2]
    material = str(RENDER_STYLE.get("material") or "editorial-paper")
    number_x = 112 if material in {"blueprint-grid", "eastern-rice-paper"} else 60
    title_x = 158 if material in {"blueprint-grid", "eastern-rice-paper"} else 106
    if material == "brutalist-newsprint":
        number_x, title_x = 60, 106
    if material == "risograph-zine":
        number_x, title_x = 124, 176
    out = style_title_marker(slide_no, dark=dark)
    out.extend([
        text(number_x, 72, f"{slide_no:02d}", size=18, fill=PALETTE["red"], family=MONO_FONT, weight="700"),
        text(title_x, 76, lines, size=title_size, fill=fill, family=TITLE_FONT, weight="700", line_height=1.26),
    ])
    return "\n".join(out)


def style_component_frame(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str,
    accent: str,
    dark: bool = False,
    label: str = "",
) -> list[str]:
    material = str(RENDER_STYLE.get("material") or "editorial-paper")
    ink = PALETTE["white"] if dark else PALETTE["ink"]
    paper = PALETTE["dark"] if dark else fill
    if material == "blueprint-grid":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["blue"], sw=1.15, opacity=0.96),
            rect(x + 8, y + 8, w - 16, h - 16, "none", stroke=PALETTE["cyan"], sw=0.8, opacity=0.38, dash="5 5"),
            line(x, y + 30, x + w, y + 30, PALETTE["blue"], sw=0.8, opacity=0.35),
            text(x + 14, y + 22, label or "ANNOTATION", size=9, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.7),
        ]
    if material == "brutalist-newsprint":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["ink"], sw=2.0),
            rect(x, y, w, 28, PALETTE["ink"], fill_opacity=0.92),
            text(x + 12, y + 20, label or "FIELD NOTE", size=10, fill=PALETTE["paper"], family=MONO_FONT, weight="700", letter_spacing=0.75),
            line(x, y + h - 2, x + w, y + h - 2, PALETTE["red"], sw=2.2, opacity=0.88),
        ]
    if material == "risograph-zine":
        return [
            rect(x + 8, y + 8, w, h, PALETTE["red"], fill_opacity=0.20),
            rect(x - 5, y - 5, w, h, PALETTE["blue"], fill_opacity=0.14),
            rect(x, y, w, h, fill, stroke=accent, sw=1.6),
            line(x + 12, y + h - 14, x + w - 14, y + 14, accent, sw=0.7, opacity=0.20),
        ]
    if material == "eastern-rice-paper":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["gold"], sw=1.05, fill_opacity=0.94),
            line(x + 16, y + 16, x + 16, y + h - 16, accent, sw=1.2, opacity=0.55),
            rect(x + w - 38, y + 18, 24, 24, PALETTE["red"], fill_opacity=0.56),
            text(x + w - 31, y + 36, "记", size=11, fill=PALETTE["paper"], family=TITLE_FONT, weight="700"),
        ]
    if material == "luxury-editorial-paper":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["gold"], sw=0.9, fill_opacity=0.96),
            line(x + 18, y + 20, x + w - 18, y + 20, PALETTE["gold"], sw=0.8, opacity=0.58),
            text(x + 18, y + 14, label or "EDITORIAL NOTE", size=8, fill=PALETTE["muted"], family=MONO_FONT, weight="700", letter_spacing=1.0),
        ]
    if material == "nvidia-terminal":
        return [
            rect(x, y, w, h, "#0D140B" if dark else "#111A0E", stroke=PALETTE["blue"], sw=1.2, fill_opacity=0.94, rx=2),
            rect(x, y, w, 30, PALETTE["blue"], fill_opacity=0.18),
            text(x + 14, y + 21, label or "KERNEL", size=9, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ]
    if material == "verge-neon-editorial":
        return [
            rect(x, y, w, h, "#171717" if dark else "#FFFFFF", stroke=PALETTE["blue"], sw=1.4, fill_opacity=0.94),
            rect(x, y, 10, h, PALETTE["red"], fill_opacity=0.88),
            rect(x + 10, y, w - 10, 28, PALETTE["blue"], fill_opacity=0.12),
            text(x + 24, y + 20, label or "SIGNAL", size=9, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ]
    if material == "opencode-manpage":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["ink"], sw=1.0),
            rect(x, y, w, 28, PALETTE["dark"], fill_opacity=0.94),
            text(x + 12, y + 20, label or "SECTION", size=9, fill=PALETTE["paper"], family=MONO_FONT, weight="700", letter_spacing=0.7),
        ]
    if material == "bento-tech":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["line"], sw=1.0, rx=14, fill_opacity=0.96),
            rect(x + 14, y + 14, 36, 36, accent, rx=10, fill_opacity=0.90),
        ]
    if material == "architecture-catalog":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["line"], sw=1.0, fill_opacity=0.94),
            line(x + 18, y + 18, x + 18, y + h - 18, PALETTE["red"], sw=0.9, opacity=0.58),
            text(x + 32, y + 18, label or "CATALOG NOTE", size=8, fill=PALETTE["muted"], family=MONO_FONT, weight="700", letter_spacing=1.1),
        ]
    if material == "wired-tech-magazine":
        return [
            rect(x, y, w, h, fill, stroke=PALETTE["ink"], sw=1.1),
            rect(x, y, w, 30, PALETTE["ink"], fill_opacity=0.94),
            rect(x, y, 12, h, PALETTE["red"], fill_opacity=0.94),
            text(x + 24, y + 21, label or "INDEX", size=9, fill=PALETTE["white"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ]
    return [rect(x, y, w, h, paper, stroke=ink if dark else PALETTE["ink"], sw=1.4, rx=0)]


def style_proof_ornament(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    kind: str,
    dark: bool = False,
    index: int = 0,
) -> list[str]:
    material = str(RENDER_STYLE.get("material") or "editorial-paper")
    proof_language = str(RENDER_STYLE.get("proof_language") or "editorial-proof-objects")
    ink = PALETTE["white"] if dark else PALETTE["ink"]
    muted = "#D8CCBC" if dark else PALETTE["muted"]
    accent = PALETTE["cyan"] if material == "blueprint-grid" else PALETTE["red"]
    label = kind.upper().replace("_", " ")
    out: list[str] = [
        text(x, y - 10, proof_language, size=8, fill=muted, family=MONO_FONT, weight="700", letter_spacing=0.6),
    ]
    if material == "blueprint-grid":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["cyan"], sw=0.8, opacity=0.34, dash="6 6"),
            line(x, y + h * 0.5, x + w, y + h * 0.5, PALETTE["cyan"], sw=0.8, opacity=0.25, dash="4 10"),
            line(x + w * 0.5, y, x + w * 0.5, y + h, PALETTE["cyan"], sw=0.8, opacity=0.25, dash="4 10"),
            text(x + 12, y + 24, f"GRID-{index:02d} / {label}", size=9, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.7),
        ])
        for tick in range(0, 7):
            tx = x + tick * w / 6
            out.append(line(tx, y + h - 14, tx, y + h, PALETTE["blue"], sw=0.75, opacity=0.42))
        return out
    if material == "brutalist-newsprint":
        out.extend([
            line(x, y, x + w, y, ink, sw=3.0, opacity=0.86),
            line(x, y + h, x + w, y + h, ink, sw=3.0, opacity=0.86),
            rect(x, y + 12, 112, 24, ink, fill_opacity=0.9),
            text(x + 10, y + 30, "EVIDENCE", size=10, fill=PALETTE["paper"], family=MONO_FONT, weight="700", letter_spacing=0.9),
            line(x + w * 0.33, y + 22, x + w * 0.33, y + h - 20, ink, sw=1.0, opacity=0.32),
            line(x + w * 0.66, y + 22, x + w * 0.66, y + h - 20, ink, sw=1.0, opacity=0.32),
        ])
        return out
    if material == "risograph-zine":
        out.extend([
            rect(x + 10, y + 10, w * 0.36, h * 0.44, PALETTE["red"], fill_opacity=0.12),
            rect(x + w * 0.56, y + h * 0.18, w * 0.32, h * 0.56, PALETTE["blue"], fill_opacity=0.10),
            line(x, y + h, x + w, y, accent, sw=1.1, opacity=0.26),
            text(x + 14, y + 26, f"PROOF {index:02d}", size=10, fill=PALETTE["red"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ])
        for dot in range(0, 10):
            dx = x + 26 + (dot % 5) * 18
            dy = y + h - 32 + (dot // 5) * 14
            out.append(circle(dx, dy, 2.4, PALETTE["blue"], fill_opacity=0.38))
        return out
    if material == "eastern-rice-paper":
        out.extend([
            line(x + 20, y + 8, x + 20, y + h - 8, PALETTE["gold"], sw=1.0, opacity=0.48),
            line(x + w - 20, y + 8, x + w - 20, y + h - 8, PALETTE["gold"], sw=1.0, opacity=0.34),
            rect(x + w - 54, y + 16, 32, 32, PALETTE["red"], fill_opacity=0.52),
            text(x + w - 45, y + 39, "证", size=13, fill=PALETTE["paper"], family=TITLE_FONT, weight="700"),
            text(x + 34, y + 30, "source artifact", size=9, fill=muted, family=MONO_FONT, weight="700", letter_spacing=0.7),
        ])
        return out
    if material == "luxury-editorial-paper":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["gold"], sw=0.75, opacity=0.50),
            line(x + 18, y + 22, x + w - 18, y + 22, PALETTE["gold"], sw=0.75, opacity=0.72),
            line(x + 18, y + h - 22, x + w - 18, y + h - 22, PALETTE["gold"], sw=0.75, opacity=0.52),
            text(x + w - 138, y + 18, "PROOF SPREAD", size=8, fill=muted, family=MONO_FONT, weight="700", letter_spacing=1.1),
        ])
        return out
    if material == "nvidia-terminal":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["blue"], sw=1.0, opacity=0.55),
            rect(x + 12, y + 12, w - 24, h - 24, "none", stroke=PALETTE["line"], sw=0.75, opacity=0.50),
            text(x + 14, y + 28, f"CUDA TRACE {index:02d}", size=10, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ])
        return out
    if material == "verge-neon-editorial":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["blue"], sw=1.4, opacity=0.60),
            rect(x, y, 16, h, PALETTE["red"], fill_opacity=0.72),
            text(x + 28, y + 28, f"SIGNAL STACK {index:02d}", size=10, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ])
        return out
    if material == "opencode-manpage":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["ink"], sw=1.0, opacity=0.56),
            text(x + 12, y + 26, f"$ proof --slide {index:02d}", size=10, fill=PALETTE["blue"], family=MONO_FONT, weight="700"),
            line(x + 12, y + 40, x + w - 12, y + 40, PALETTE["line"], sw=0.8, opacity=0.72),
        ])
        return out
    if material == "bento-tech":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["line"], sw=1.0, rx=14, opacity=0.72),
            rect(x + 16, y + 16, 42, 42, PALETTE["blue"], rx=12, fill_opacity=0.90),
            text(x + 72, y + 42, f"EVIDENCE TILE {index:02d}", size=10, fill=PALETTE["blue"], family=MONO_FONT, weight="700", letter_spacing=0.7),
        ])
        return out
    if material == "architecture-catalog":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["line"], sw=0.9, opacity=0.68),
            line(x + 20, y + 18, x + 20, y + h - 18, PALETTE["red"], sw=1.0, opacity=0.48),
            text(x + 36, y + 28, f"ARCHIVE PLATE {index:02d}", size=9, fill=PALETTE["muted"], family=MONO_FONT, weight="700", letter_spacing=1.0),
        ])
        return out
    if material == "wired-tech-magazine":
        out.extend([
            rect(x, y, w, h, "none", stroke=PALETTE["ink"], sw=1.0, opacity=0.72),
            rect(x, y, w, 28, PALETTE["ink"], fill_opacity=0.94),
            text(x + 14, y + 20, f"PROOF INDEX {index:02d}", size=9, fill=PALETTE["white"], family=MONO_FONT, weight="700", letter_spacing=0.8),
        ])
        return out
    out.extend([
        rect(x, y, w, h, "none", stroke=ink, sw=0.8, opacity=0.28),
        line(x, y + h, x + 86, y + h, accent, sw=2.0, opacity=0.6),
        text(x + 12, y + 24, f"PROOF {index:02d}", size=9, fill=muted, family=MONO_FONT, weight="700", letter_spacing=0.8),
    ])
    return out


def card(x: float, y: float, w: float, h: float, title: str, body: str, *,
         idx: int | None = None, fill: str = PALETTE["paper"], accent: str = PALETTE["blue"]) -> str:
    out = style_component_frame(x, y, w, h, fill=fill, accent=accent, label=f"ITEM {idx:02d}" if idx else "NOTE")
    material = str(RENDER_STYLE.get("material") or "editorial-paper")
    if material not in {"blueprint-grid", "brutalist-newsprint", "eastern-rice-paper"}:
        out.append(rect(x, y, 8, h, accent))
    if idx is not None:
        out.append(text(x + 28, y + 38, f"{idx:02d}", size=22, fill=accent, family=MONO_FONT, weight="700"))
        title_x = x + 78
    else:
        title_x = x + 24
    out.append(text(title_x, y + 39, cjk_wrap(title, 12), size=21, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.12))
    out.append(text(x + 24, y + 96, cjk_wrap(body, 19), size=16, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.35))
    return "\n".join(out)


def formula_chip(x: float, y: float, content: str, *, dark: bool = False, size: int = 24) -> str:
    fill = PALETTE["dark"] if not dark else PALETTE["paper"]
    stroke = PALETTE["red"]
    text_fill = PALETTE["white"] if not dark else PALETTE["dark"]
    width = max(110, len(content) * size * 0.62)
    return "\n".join([
        rect(x, y, width, size * 1.65, fill, stroke=stroke, sw=1.2),
        text(x + width / 2, y + size * 1.08, content, size=size, fill=text_fill, family=MONO_FONT, weight="700", anchor="middle"),
    ])


def editorial_scrim(slide_no: int, *, dark: bool = False) -> str:
    if dark:
        return "\n".join([
            rect(0, 0, W, H, PALETTE["dark"], fill_opacity=0.62),
            rect(0, 0, W, H, f"url(#blueScrim{slide_no})"),
        ])
    return "\n".join([
        rect(0, 0, W, H, PALETTE["paper"], fill_opacity=0.72),
        rect(0, 0, W, H, f"url(#paperFade{slide_no})", fill_opacity=0.42),
    ])


def editorial_label(x: float, y: float, value: str, *, dark: bool = False, accent: str | None = None) -> str:
    accent = accent or PALETTE["red"]
    fill = PALETTE["white"] if dark else PALETTE["ink"]
    return "\n".join([
        line(x, y - 20, x + 78, y - 20, accent, sw=2.2, opacity=0.9),
        text(x, y, value.upper() if re.search(r"[A-Za-z]", value) else value, size=13, fill=fill, family=MONO_FONT if re.search(r"[A-Za-z]", value) else BODY_FONT, weight="700", letter_spacing=0.8 if re.search(r"[A-Za-z]", value) else None),
    ])


def image_panel(href: str, x: float, y: float, w: float, h: float, *, slide_no: int) -> str:
    if not href:
        return "\n".join([
            rect(x, y, w, h, PALETTE["dark"], fill_opacity=0.88),
            circle(x + w * 0.68, y + h * 0.36, min(w, h) * 0.32, PALETTE["blue"], fill_opacity=0.16),
            circle(x + w * 0.45, y + h * 0.68, min(w, h) * 0.26, PALETTE["red"], fill_opacity=0.13),
            line(x + 28, y + h - 46, x + w - 30, y + 38, PALETTE["cyan"], sw=1.2, opacity=0.22),
        ])
    return "\n".join([
        image_tag(href, x, y, w, h, preserve="xMidYMid slice"),
        rect(x, y, w, h, "none", stroke=PALETTE["ink"], sw=1.2, opacity=0.7),
    ])


def has_slide_image(images: dict[str, str], slide_no: int) -> bool:
    return bool(images.get(f"slide_{slide_no:02d}") or images.get(f"slide-{slide_no:02d}"))


def magazine_headline(
    x: float,
    y: float,
    title: str,
    *,
    width_chars: int,
    size: int,
    dark: bool = False,
    max_lines: int = 3,
) -> str:
    fill = PALETTE["white"] if dark else PALETTE["ink"]
    return text(
        x,
        y,
        cjk_wrap(title, width_chars)[:max_lines],
        size=size,
        fill=fill,
        family=TITLE_FONT,
        weight="700",
        line_height=1.18,
    )


def bullet_stack(
    x: float,
    y: float,
    points: list[str],
    *,
    w_chars: int,
    dark: bool = False,
    max_items: int = 3,
    accent: str = PALETTE["red"],
) -> str:
    fill = "#EADFCF" if dark else PALETTE["ink"]
    muted = "#D8CCBC" if dark else PALETTE["muted"]
    out: list[str] = []
    for idx, point in enumerate(points[:max_items]):
        yy = y + idx * 104
        out.append(text(x, yy, f"{idx + 1:02d}", size=18, fill=accent, family=MONO_FONT, weight="700"))
        out.append(text(x + 52, yy, cjk_wrap(point, w_chars)[:3], size=20, fill=fill if idx == 0 else muted, family=BODY_FONT, weight="700", line_height=1.32))
    return "\n".join(out)


def pull_quote_block(x: float, y: float, w: float, quote: str, *, dark: bool = False, size: int = 32) -> str:
    fill = PALETTE["white"] if dark else PALETTE["ink"]
    muted = "#D8CCBC" if dark else PALETTE["muted"]
    return "\n".join([
        text(x, y, "“", size=size + 44, fill=PALETTE["red"], family=TITLE_FONT, weight="700", opacity=0.82),
        text(x + 48, y + 16, cjk_wrap(quote, max(8, int(w / (size * 0.88))))[:5], size=size, fill=fill, family=TITLE_FONT, weight="700", line_height=1.13),
        text(x + 50, y + 172, "把证据压成一句可讲述的判断", size=15, fill=muted, family=BODY_FONT, weight="700"),
    ])


def render_cover(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    title = title_of(slide)
    out = [paper_bg(slide_no, dark=True)]
    out.append(image_tag(images.get("einstein_head", ""), 660, 0, 620, 720, preserve="xMidYMid slice"))
    out.append(rect(660, 0, 620, 720, PALETTE["dark"], fill_opacity=0.28))
    out.append(rect(0, 0, W, H, f"url(#blueScrim{slide_no})"))
    out.append(circle(770, 360, 250, "none", stroke=PALETTE["cyan"], sw=1.1, opacity=0.34))
    out.append(circle(770, 360, 160, "none", stroke=PALETTE["red"], sw=1.1, opacity=0.28))
    out.append(text(72, 122, cjk_wrap(title, 12), size=64, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.04))
    out.append(text(78, 344, "从光量子、时空测量到引力几何", size=24, fill="#EADFCF", family=BODY_FONT, weight="500"))
    out.append(formula_chip(78, 426, "E = mc²", dark=False, size=35))
    out.append(text(78, 538, "不是天才头像，而是一套重写常识的方法。", size=21, fill="#D8CCBC", family=BODY_FONT))
    out.append(footer(slide_no, total, dark=True))
    return "\n".join(out)


def render_problem(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(text(90, 190, "THREE CONTRADICTIONS", size=15, fill=PALETTE["red"], family=MONO_FONT, weight="700", letter_spacing=1.2))
    centers = [(250, 385), (640, 385), (1030, 385)]
    labels = ["光", "时空", "引力"]
    for idx, (cx, cy) in enumerate(centers):
        out.append(circle(cx, cy, 118, PALETTE["white"], stroke=PALETTE["ink"], sw=1.8))
        out.append(circle(cx, cy, 78, "none", stroke=PALETTE["blue" if idx != 1 else "red"], sw=2.4, opacity=0.82))
        for k in range(6):
            angle = k * math.pi / 3 + idx * 0.3
            out.append(circle(cx + math.cos(angle) * 94, cy + math.sin(angle) * 94, 5, PALETTE["red" if k % 2 else "blue"], fill_opacity=0.82))
        out.append(text(cx, cy + 11, labels[idx], size=42, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", anchor="middle"))
        body = points[idx] if idx < len(points) else ""
        out.append(text(cx - 142, 552, cjk_wrap(body, 15), size=18, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.3))
    out.append(line(370, 385, 520, 385, PALETTE["red"], sw=2.2, dash="9 9"))
    out.append(line(760, 385, 910, 385, PALETTE["red"], sw=2.2, dash="9 9"))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_timeline(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(image_tag(images.get("einstein_nobel", ""), 820, 104, 340, 480, preserve="xMidYMid slice", clip_id=f"photoClip{slide_no}"))
    out.append(rect(800, 84, 380, 522, "none", stroke=PALETTE["ink"], sw=2))
    events = [("1879", "乌尔姆出生"), ("1901", "瑞士国籍"), ("1902", "专利局"), ("1905", "博士与四篇论文")]
    x0, y0 = 90, 290
    out.append(line(x0, y0, 720, y0, PALETTE["ink"], sw=2))
    for idx, (year, label) in enumerate(events):
        x = x0 + idx * 205
        out.append(circle(x, y0, 11, PALETTE["red"]))
        out.append(text(x, y0 - 48, year, size=36, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", anchor="middle"))
        out.append(text(x - 64, y0 + 58, cjk_wrap(label, 6), size=18, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.25))
    out.append(card(90, 438, 600, 116, "边缘位置", "没有马上进入大学体系，反而训练了他从测量、装置和定义出发的问题感。", accent=PALETTE["red"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_patent(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(rect(740, 96, 390, 512, PALETTE["white"], stroke=PALETTE["ink"], sw=1.5))
    out.append(image_tag(images.get("patent_electromagnet", ""), 762, 118, 346, 468, preserve="xMidYMid meet"))
    out.append(text(92, 180, cjk_wrap("专利文件要求把装置、信号、时钟和可验证的动作说清楚。", 20), size=34, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.12))
    out.append(card(94, 356, 520, 98, "测量语言", "狭义相对论后来也从“如何定义同时性”切入。", idx=1, accent=PALETTE["blue"]))
    out.append(card(124, 478, 520, 98, "制度边缘", "好问题常来自流程现场，而不是职位中心。", idx=2, accent=PALETTE["red"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_miracle_year(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(text(96, 422, "1905", size=178, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", opacity=0.12))
    labels = ["光量子", "布朗运动", "狭义相对论", "质能关系"]
    for idx, label in enumerate(labels):
        x = 110 + (idx % 2) * 520
        y = 168 + (idx // 2) * 190
        out.append(rect(x, y, 440, 138, PALETTE["white"], stroke=PALETTE["ink"], sw=1.3))
        out.append(text(x + 24, y + 42, label, size=30, fill=PALETTE["ink"], family=TITLE_FONT, weight="700"))
        out.append(text(x + 24, y + 88, cjk_wrap(points[idx] if idx < len(points) else "", 21), size=17, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.25))
        out.append(circle(x + 384, y + 42, 22, PALETTE["red" if idx % 2 else "blue"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_photoelectric(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    metal_y = 450
    out.append(rect(92, metal_y, 720, 42, PALETTE["dark"]))
    out.append(text(98, 522, "光的能量不是连续洒下去，而是一份一份击中电子。", size=22, fill=PALETTE["ink"], family=BODY_FONT, weight="700"))
    for i in range(8):
        x = 130 + i * 78
        out.append(path(f"M{x},160 C{x+36},210 {x-20},250 {x+28},305 C{x+72},356 {x+18},388 {x+44},438", PALETTE["blue"], sw=2.4, opacity=0.75))
        out.append(circle(x + 42, 438, 8, PALETTE["gold"]))
    for i in range(5):
        x = 230 + i * 115
        out.append(path(f"M{x},{metal_y} C{x+28},{metal_y-56} {x+82},{metal_y-66} {x+126},{metal_y-130}", PALETTE["red"], sw=2.6))
        out.append(circle(x + 126, metal_y - 130, 12, PALETTE["red"]))
    out.append(card(870, 180, 276, 132, "阈值现象", "连续波图景解释不顺。", accent=PALETTE["blue"]))
    out.append(card(890, 350, 276, 132, "离散份额", "光量子打开量子论入口。", accent=PALETTE["red"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_brownian(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(circle(470, 380, 224, PALETTE["white"], stroke=PALETTE["ink"], sw=3))
    points = [(330, 355), (380, 312), (448, 338), (410, 405), (502, 432), (580, 382), (548, 312), (620, 280)]
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    out.append(path(d, PALETTE["red"], sw=3.4))
    for idx, (x, y) in enumerate(points):
        out.append(circle(x, y, 10 if idx == len(points) - 1 else 6, PALETTE["blue" if idx % 2 else "red"]))
    for i in range(36):
        x = 270 + (i * 47) % 420
        y = 200 + (i * 73) % 340
        out.append(circle(x, y, 2.5, PALETTE["muted"], fill_opacity=0.34))
    out.append(text(760, 214, cjk_wrap("随机抖动不是噪声，而是分子热运动留下的可统计痕迹。", 12), size=33, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.12))
    out.append(text(765, 452, cjk_wrap("原子论从抽象假设，变成显微镜下可接近的证据。", 20), size=20, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.32))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_relativity_train(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(rect(130, 390, 720, 92, PALETTE["dark"]))
    for x in (190, 320, 450, 580, 710):
        out.append(rect(x, 408, 72, 34, PALETTE["paper"], stroke=PALETTE["white"], sw=1))
    out.append(circle(230, 492, 22, PALETTE["ink"]))
    out.append(circle(720, 492, 22, PALETTE["ink"]))
    out.append(line(110, 520, 885, 520, PALETTE["ink"], sw=3))
    out.append(path("M230,300 L520,235 L812,300", PALETTE["red"], sw=3.2, dash="10 7"))
    out.append(path("M230,300 L520,365 L812,300", PALETTE["blue"], sw=3.2, dash="10 7"))
    out.append(text(925, 210, cjk_wrap("光速不变迫使“同时性”重新定义。", 12), size=38, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.08))
    out.append(text(928, 400, cjk_wrap("不是时间变玄学，而是测量规则换了坐标系。", 18), size=19, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.32))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_mass_energy(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no, dark=True)]
    out.append(text(70, 90, f"{slide_no:02d}", size=18, fill=PALETTE["red"], family=MONO_FONT, weight="700"))
    out.append(text(82, 240, "E = mc²", size=128, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    out.append(text(96, 350, cjk_wrap("质量和能量不再是两个账本。", 14), size=43, fill="#EDE1D1", family=TITLE_FONT, weight="700", line_height=1.08))
    out.append(circle(920, 350, 118, PALETTE["red"], fill_opacity=0.72))
    out.append(circle(990, 350, 118, PALETTE["blue"], fill_opacity=0.66))
    out.append(text(870, 358, "m", size=48, fill=PALETTE["white"], family=MONO_FONT, weight="700", anchor="middle"))
    out.append(text(1038, 358, "E", size=48, fill=PALETTE["white"], family=MONO_FONT, weight="700", anchor="middle"))
    out.append(text(826, 528, cjk_wrap("极短公式改变的是概念边界：质量可以理解为能量的一种形式。", 25), size=19, fill="#D8CCBC", family=BODY_FONT, line_height=1.34))
    out.append(footer(slide_no, total, dark=True))
    return "\n".join(out)


def render_spacetime(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    for i in range(12):
        y = 185 + i * 32
        d = f"M150,{y} C360,{y+80} 600,{y-80} 860,{y+40} C980,{y+70} 1080,{y+10} 1160,{y+22}"
        out.append(path(d, PALETTE["blue"], sw=1.3, opacity=0.42))
    for i in range(11):
        x = 170 + i * 82
        d = f"M{x},160 C{x-60},330 {x+60},430 {x-28},600"
        out.append(path(d, PALETTE["blue"], sw=1.1, opacity=0.34))
    out.append(circle(660, 382, 76, PALETTE["red"], fill_opacity=0.86))
    out.append(circle(820, 324, 18, PALETTE["dark"]))
    out.append(path("M820,324 C760,278 682,298 660,382", PALETTE["ink"], sw=2, dash="7 7"))
    out.append(card(92, 480, 390, 110, "1915", "引力从“远距离作用”变成“时空几何”。", accent=PALETTE["red"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_newspaper(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no)]
    out.append(text(60, 86, "RELATIVITY BECOMES PUBLIC CULTURE", size=24, fill=PALETTE["ink"], family=MONO_FONT, weight="700"))
    out.append(line(60, 108, 1220, 108, PALETTE["ink"], sw=3))
    out.append(image_tag(images.get("einstein_blackboard", ""), 60, 135, 540, 360, preserve="xMidYMid slice"))
    out.append(rect(60, 135, 540, 360, "none", stroke=PALETTE["ink"], sw=2))
    out.append(text(640, 170, cjk_wrap(title_of(slide), 13), size=48, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.04))
    out.append(text(642, 390, cjk_wrap("相对论从专业理论走向公众文化符号；但大众记住的头像，常遮住了问题本身。", 24), size=19, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.38))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_nobel(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(rect(110, 170, 460, 320, PALETTE["white"], stroke=PALETTE["gold"], sw=5))
    out.append(circle(340, 305, 78, PALETTE["gold"], fill_opacity=0.78))
    out.append(text(340, 322, "1921", size=46, fill=PALETTE["dark"], family=MONO_FONT, weight="700", anchor="middle"))
    out.append(text(150, 552, "诺奖选择的是光电效应", size=30, fill=PALETTE["ink"], family=TITLE_FONT, weight="700"))
    out.append(path("M640,274 L840,274", PALETTE["red"], sw=3))
    out.append(path("M835,274 L812,258 M835,274 L812,290", PALETTE["red"], sw=3))
    out.append(card(875, 190, 270, 122, "证据节奏", "科学承认依赖更稳的验证路径。", accent=PALETTE["blue"]))
    out.append(card(875, 354, 270, 122, "不是否定", "相对论成名更快，但验证和争议门槛更高。", accent=PALETTE["red"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_quantum(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(rect(80, 160, 520, 390, PALETTE["dark"]))
    out.append(rect(680, 160, 520, 390, PALETTE["white"], stroke=PALETTE["ink"], sw=2))
    for i in range(12):
        x = 120 + i * 38
        y = 335 + math.sin(i / 1.3) * 72
        out.append(circle(x, y, 10, PALETTE["cyan"], fill_opacity=0.72))
    out.append(path("M120,335 C220,220 330,450 440,335 C500,270 548,300 570,335", PALETTE["red"], sw=3))
    out.append(text(110, 508, "打开量子之门", size=28, fill=PALETTE["white"], family=TITLE_FONT, weight="700"))
    out.append(text(720, 262, cjk_wrap("他推动量子革命，却长期质疑概率解释。", 14), size=40, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.08))
    out.append(text(724, 430, cjk_wrap("这不是保守，而是关于“物理实在”的哲学分歧。", 22), size=20, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.32))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_unified(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    cx, cy = 640, 380
    for i in range(18):
        angle = i * math.tau / 18
        r1, r2 = 86 + (i % 4) * 22, 260
        x1, y1 = cx + math.cos(angle) * r1, cy + math.sin(angle) * r1
        x2, y2 = cx + math.cos(angle + 0.42) * r2, cy + math.sin(angle + 0.42) * r2
        out.append(path(f"M{x1},{y1} C{cx},{cy} {cx+math.cos(angle)*190},{cy+math.sin(angle)*190} {x2},{y2}", PALETTE["blue" if i % 2 else "red"], sw=1.8, opacity=0.58))
    out.append(circle(cx, cy, 82, PALETTE["dark"]))
    out.append(text(cx, cy + 8, "?", size=68, fill=PALETTE["white"], family=TITLE_FONT, weight="700", anchor="middle"))
    out.append(card(92, 488, 620, 110, "长期问题意识", "晚年的统一场论不是失败段子，而是他持续追问：自然能否被同一个框架理解。", accent=PALETTE["red"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_exile(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(rect(90, 170, 720, 360, PALETTE["white"], stroke=PALETTE["ink"], sw=1.8))
    out.append(text(170, 310, "EUROPE", size=46, fill=PALETTE["muted"], family=MONO_FONT, weight="700", opacity=0.42))
    out.append(text(600, 432, "PRINCETON", size=42, fill=PALETTE["muted"], family=MONO_FONT, weight="700", opacity=0.42))
    out.append(path("M290,330 C410,220 560,250 710,420", PALETTE["red"], sw=4))
    out.append(path("M710,420 L668,407 M710,420 L690,382", PALETTE["red"], sw=4))
    out.append(circle(288, 330, 12, PALETTE["dark"]))
    out.append(circle(710, 420, 12, PALETTE["blue"]))
    out.append(card(870, 210, 284, 122, "1933", "政治重写了欧洲科学共同体。", accent=PALETTE["red"]))
    out.append(card(870, 374, 284, 122, "1940", "成为美国公民，普林斯顿成为后半生基地。", accent=PALETTE["blue"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_ias(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no)]
    out.append(image_tag(images.get("einstein_head", ""), 0, 0, W, H, preserve="xMidYMid slice"))
    out.append(rect(0, 0, W, H, PALETTE["paper"], fill_opacity=0.82))
    out.append(page_title(slide_no, title_of(slide)))
    for i in range(7):
        x = 160 + i * 130
        out.append(rect(x, 315 - i % 2 * 18, 78, 176 + i % 2 * 18, PALETTE["dark"], fill_opacity=0.86))
        out.append(rect(x + 18, 340, 42, 16, PALETTE["paper"], fill_opacity=0.78))
    out.append(line(120, 492, 1050, 492, PALETTE["ink"], sw=2))
    out.append(text(134, 570, cjk_wrap("IAS 时期不是退场，而是一代流亡科学家的学术自由坐标。", 31), size=24, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.25))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_public_voice(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(circle(330, 380, 150, PALETTE["dark"]))
    out.append(rect(302, 276, 56, 170, PALETTE["white"], rx=28))
    out.append(line(330, 446, 330, 526, PALETTE["white"], sw=10))
    out.append(line(270, 526, 390, 526, PALETTE["white"], sw=10))
    for r in (210, 258, 306):
        out.append(circle(330, 380, r, "none", stroke=PALETTE["red"], sw=1.8, opacity=0.22))
    out.append(card(690, 198, 430, 110, "战争与和平", "核时代让科学声望无法停在实验室门口。", accent=PALETTE["red"]))
    out.append(card(730, 340, 430, 110, "世界政府运动", "公共立场成为科学家身份的一部分。", accent=PALETTE["blue"]))
    out.append(card(690, 482, 430, 110, "以色列总统邀约", "曾获邀但谢绝，说明符号权力已经超出物理学。", accent=PALETTE["gold"]))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_gps(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no, dark=True), page_title(slide_no, title_of(slide), dark=True)]
    out.append(circle(520, 405, 154, PALETTE["blue"], fill_opacity=0.38, stroke=PALETTE["cyan"], sw=2))
    for i in range(7):
        out.append(path(f"M{370+i*50},270 C{430+i*24},390 {430+i*24},430 {370+i*50},540", PALETTE["cyan"], sw=1, opacity=0.38))
        out.append(line(370, 300 + i * 34, 670, 300 + i * 16, PALETTE["cyan"], sw=0.9, opacity=0.28))
    for idx, (x, y) in enumerate([(370, 190), (760, 280), (700, 560)]):
        out.append(rect(x - 28, y - 16, 56, 32, PALETTE["white"], stroke=PALETTE["cyan"], sw=1.5))
        out.append(line(x, y + 16, x, y + 46, PALETTE["white"], sw=2))
        out.append(circle(x, y + 56, 9, PALETTE["red"]))
    out.append(text(850, 238, "38 μs / day", size=52, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    out.append(text(852, 326, "≈ 10 km / day", size=42, fill=PALETTE["red"], family=MONO_FONT, weight="700"))
    out.append(text(854, 416, cjk_wrap("GPS 卫星时钟每天都在使用相对论修正；不修正，误差会迅速累积。", 21), size=20, fill="#D8CCBC", family=BODY_FONT, line_height=1.34))
    out.append(footer(slide_no, total, dark=True))
    return "\n".join(out)


def render_method(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    steps = [("01", "选择概念缝隙", "旧概念解释不了新现象"), ("02", "构造思想实验", "把抽象问题变成可推演场景"), ("03", "压成数学结构", "让直觉进入可检验形式")]
    for idx, (num, head, body) in enumerate(steps):
        x = 110 + idx * 370
        out.append(circle(x + 110, 340, 108, PALETTE["white"], stroke=PALETTE["ink"], sw=2))
        out.append(text(x + 110, 308, num, size=42, fill=PALETTE["red"], family=MONO_FONT, weight="700", anchor="middle"))
        out.append(text(x + 110, 358, cjk_wrap(head, 7), size=25, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", anchor="middle", line_height=1.05))
        out.append(text(x + 18, 510, cjk_wrap(body, 15), size=18, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.28))
        if idx < 2:
            out.append(path(f"M{x+230},340 L{x+330},340", PALETTE["red"], sw=3))
            out.append(path(f"M{x+330},340 L{x+306},326 M{x+330},340 L{x+306},354", PALETTE["red"], sw=3))
    out.append(footer(slide_no, total))
    return "\n".join(out)


def render_closing(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    out = [paper_bg(slide_no, dark=True)]
    out.append(image_tag(images.get("einstein_head", ""), 760, 0, 520, 720, preserve="xMidYMid slice"))
    out.append(rect(760, 0, 520, 720, PALETTE["dark"], fill_opacity=0.58))
    for i in range(9):
        x = 120 + i * 60
        out.append(line(x, 130, x + 260, 600, PALETTE["cyan"], sw=1, opacity=0.16))
    out.append(text(78, 136, cjk_wrap(title_of(slide), 12), size=58, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.06))
    out.append(text(86, 410, cjk_wrap("当旧概念解释不了新现象，真正的突破不是补丁，而是重画坐标系。", 22), size=26, fill="#EADFCF", family=BODY_FONT, weight="700", line_height=1.3))
    out.append(formula_chip(86, 548, "change the frame", dark=False, size=21))
    out.append(footer(slide_no, total, dark=True))
    return "\n".join(out)


RENDERERS = {
    1: render_cover,
    2: render_problem,
    3: render_timeline,
    4: render_patent,
    5: render_miracle_year,
    6: render_photoelectric,
    7: render_brownian,
    8: render_relativity_train,
    9: render_mass_energy,
    10: render_spacetime,
    11: render_newspaper,
    12: render_nobel,
    13: render_quantum,
    14: render_unified,
    15: render_exile,
    16: render_ias,
    17: render_public_voice,
    18: render_gps,
    19: render_method,
    20: render_closing,
}


def image_href(value: Any) -> str:
    if isinstance(value, list):
        return image_href(value[0]) if value else ""
    if isinstance(value, dict):
        return str(value.get("href") or "")
    return str(value or "")


def first_image(images: dict[str, Any]) -> str:
    return image_href(next(iter(images.values()), ""))


def first_image_meta(images: dict[str, Any]) -> dict[str, Any]:
    value = next(iter(images.values()), "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return value if isinstance(value, dict) else {"href": str(value or "")}


def slide_image_metas(images: dict[str, Any], slide_no: int, *, allow_fallback: bool = False) -> list[dict[str, Any]]:
    all_key = f"slide_{slide_no:02d}_all"
    values = images.get(all_key)
    if isinstance(values, list):
        return [item if isinstance(item, dict) else {"href": str(item or "")} for item in values if item]
    specific = images.get(f"slide_{slide_no:02d}") or images.get(f"slide-{slide_no:02d}")
    if isinstance(specific, list):
        return [item if isinstance(item, dict) else {"href": str(item or "")} for item in specific if item]
    if isinstance(specific, dict):
        return [specific]
    if specific:
        return [{"href": str(specific)}]
    return [first_image_meta(images)] if allow_fallback else []


def slide_image_meta(images: dict[str, Any], slide_no: int, *, allow_fallback: bool = False) -> dict[str, Any]:
    metas = slide_image_metas(images, slide_no, allow_fallback=allow_fallback)
    return metas[0] if metas else {}


def slide_image(images: dict[str, Any], slide_no: int, *, allow_fallback: bool = False) -> str:
    return image_href(slide_image_meta(images, slide_no, allow_fallback=allow_fallback))


def dimensions_from_meta(meta: dict[str, Any]) -> tuple[int, int] | None:
    dims = meta.get("dimensions") if isinstance(meta, dict) else None
    if isinstance(dims, (list, tuple)) and len(dims) >= 2:
        try:
            return int(dims[0]), int(dims[1])
        except (TypeError, ValueError):
            return None
    return None


def image_fit_for_slot(meta: dict[str, Any], display_w: float, display_h: float, *, max_upscale: float = 1.35) -> bool:
    dims = dimensions_from_meta(meta)
    if not dims:
        return True
    actual_w, actual_h = dims
    if actual_w <= 0 or actual_h <= 0:
        return True
    return display_w <= actual_w * max_upscale and display_h <= actual_h * max_upscale


def image_object_size(meta: dict[str, Any], *, max_w: float, max_h: float, min_w: float = 220, min_h: float = 180) -> tuple[float, float]:
    dims = dimensions_from_meta(meta)
    if not dims:
        return max_w, max_h
    actual_w, actual_h = dims
    scale = min(max_w / max(1, actual_w), max_h / max(1, actual_h), 1.0)
    w = max(min_w, min(max_w, actual_w * scale))
    h = max(min_h, min(max_h, actual_h * scale))
    return w, h


def source_object_panel(meta: dict[str, Any], x: float, y: float, max_w: float, max_h: float, *, slide_no: int, dark: bool) -> str:
    href = image_href(meta)
    w, h = image_object_size(meta, max_w=max_w, max_h=max_h)
    panel_w = w + 48
    panel_h = h + 82
    fill = PALETTE["paper"] if dark else PALETTE["white"]
    caption = source_visual_caption(meta)
    out = style_component_frame(
        x,
        y,
        panel_w,
        panel_h,
        fill=fill,
        accent=PALETTE["gold"] if dark else PALETTE["red"],
        dark=dark,
        label="SOURCE OBJECT",
    )
    out.extend([
        rect(x + 18, y + 18, w + 12, h + 12, PALETTE["dark"], fill_opacity=0.10),
        image_tag(href, x + 24, y + 24, w, h, preserve="xMidYMid meet"),
        text(x + 24, y + panel_h - 28, caption, size=13, fill=PALETTE["muted"] if not dark else PALETTE["dark"], family=MONO_FONT, weight="700", letter_spacing=0.7),
        text(x + panel_w - 24, y + panel_h - 28, "SOURCE", size=13, fill=PALETTE["red"], family=MONO_FONT, weight="700", anchor="end", letter_spacing=0.7),
    ])
    return "\n".join(out)


def is_source_visual(meta: dict[str, Any]) -> bool:
    if not meta:
        return False
    acquire_via = str(meta.get("acquire_via") or "").lower()
    role = str(meta.get("asset_role") or meta.get("role") or "").lower()
    return acquire_via in {"source", "user", "web"} or "source" in role or "evidence" in role


def source_visual_caption(meta: dict[str, Any]) -> str:
    page = str(meta.get("source_page") or "").strip()
    source_path = str(meta.get("source_path") or "").strip()
    if page:
        return f"P.{page}"
    if source_path:
        return Path(source_path).name[:34]
    return "SOURCE VISUAL"


def source_visual_renderer(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any], image_text_id: str) -> str:
    layout_id = layout_id_for_render(slide)
    role_l = slide_role(slide).lower()
    if slide_no == 1 or layout_id == "L01":
        return render_generic_cover(slide, slide_no, total, images)
    if slide_no == total or layout_id == "L35":
        return render_generic_closing(slide, slide_no, total, images)
    if image_text_id in {"ITL13", "ITL14"} and len([m for m in slide_image_metas(images, slide_no) if is_source_visual(m)]) >= 2:
        return render_source_image_comparison(slide, slide_no, total, images)
    if image_text_id == "ITL18":
        return render_source_screenshot_annotation(slide, slide_no, total, images)
    if image_text_id == "ITL20":
        return render_source_data_context(slide, slide_no, total, images)
    if layout_id in {"L13", "L14", "L15", "L16", "L17"} or "process" in role_l:
        return render_source_process_flow(slide, slide_no, total, images)
    if layout_id == "L24" or "concept" in role_l or "map" in role_l:
        return render_source_concept_map(slide, slide_no, total, images)
    if image_text_id in {"ITL08", "ITL09", "ITL10"} or slide_no % 5 == 0:
        return render_source_top_feature(slide, slide_no, total, images)
    return render_generic_source_evidence_spread(slide, slide_no, total, images)


def render_generic_cover(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    title = title_of(slide)
    points = points_of(slide)
    subtitle = points[0] if points else str(slide.get("source_anchor") or "从资料、证据和叙事结构出发的主题型演示")
    keywords = keywords_for_slide(slide, 5)
    image_meta = slide_image_meta(images, slide_no, allow_fallback=True)
    image = image_href(image_meta)
    out = [paper_bg(slide_no, dark=True)]
    if image and image_fit_for_slot(image_meta, W, H, max_upscale=1.35):
        out.append(image_tag(image, 0, 0, W, H, preserve="xMidYMid slice"))
        out.append(rect(0, 0, W, H, PALETTE["dark"], fill_opacity=0.24))
        out.append(rect(0, 0, 790, H, f"url(#blueScrim{slide_no})"))
    elif image:
        out.append(rect(700, 0, 580, H, PALETTE["dark"], fill_opacity=0.82))
        out.append(circle(1006, 244, 178, PALETTE["blue"], fill_opacity=0.16))
        out.append(circle(910, 520, 132, PALETTE["red"], fill_opacity=0.12))
        out.append(source_object_panel(image_meta, 804, 150, 330, 330, slide_no=slide_no, dark=True))
    else:
        out.append(rect(705, 0, 575, H, PALETTE["dark"], fill_opacity=0.78))
        out.append(rect(746, 72, 390, 528, "none", stroke=PALETTE["cyan"], sw=1.2, opacity=0.46))
        for idx, keyword in enumerate(keywords or ["资料", "人物", "时代", "作品", "影响"]):
            x = 792 + (idx % 2) * 168
            y = 146 + idx * 82
            out.append(rect(x, y, 138, 42, PALETTE["paper"], stroke=PALETTE["cyan"], sw=1, fill_opacity=0.12))
            out.append(text(x + 69, y + 28, keyword, size=18, fill="#EADFCF", family=BODY_FONT, weight="700", anchor="middle"))
        for i in range(7):
            out.append(line(760 + i * 52, 112, 1020 + i * 25, 610, PALETTE["cyan"], sw=1, opacity=0.13))
    out.append(editorial_label(76, 96, "主题叙事", dark=True))
    out.append(text(72, 176, cjk_wrap(title, 10), size=74, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.14))
    out.append(text(78, 442, cjk_wrap(subtitle, 24)[:3], size=25, fill="#EADFCF", family=BODY_FONT, weight="700", line_height=1.34))
    out.append(line(78, 560, 380, 560, PALETTE["red"], sw=3.2, opacity=0.92))
    for idx, keyword in enumerate((keywords or ["资料", "证据", "叙事"])[:3]):
        out.append(text(78 + idx * 128, 604, keyword, size=18, fill=PALETTE["white"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide, dark=True))
    return "\n".join(out)


def render_generic_timeline(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    years = years_from_slide(slide, 5)
    if not years:
        return render_generic(slide, slide_no, total, images)
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    y0 = 330
    out.append(line(118, y0, 1120, y0, PALETTE["ink"], sw=2.2))
    spacing = 1000 / max(1, len(years) - 1)
    for idx, year in enumerate(years):
        x = 118 + idx * spacing
        body = points[idx] if idx < len(points) else year
        out.append(circle(x, y0, 12, PALETTE["red" if idx % 2 else "blue"]))
        out.append(text(x, y0 - 50, year, size=34, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", anchor="middle"))
        out.append(text(x - 82, y0 + 58, cjk_wrap(body, 8), size=16, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.28))
    anchor = str(slide.get("source_anchor") or "")
    if anchor:
        out.append(card(112, 515, 690, 94, "证据锚点", anchor, accent=PALETTE["green"]))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_closing(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    image_meta = slide_image_meta(images, slide_no, allow_fallback=True)
    image = image_href(image_meta)
    out = [paper_bg(slide_no, dark=True)]
    if image and image_fit_for_slot(image_meta, W, H, max_upscale=1.35):
        out.append(image_tag(image, 0, 0, W, H, preserve="xMidYMid slice"))
        out.append(rect(0, 0, W, H, PALETTE["dark"], fill_opacity=0.42))
        out.append(rect(0, 0, 820, H, f"url(#blueScrim{slide_no})"))
    elif image:
        out.append(rect(742, 0, 538, H, PALETTE["dark"], fill_opacity=0.82))
        out.append(circle(1048, 236, 170, PALETTE["gold"], fill_opacity=0.13))
        out.append(circle(940, 512, 142, PALETTE["blue"], fill_opacity=0.14))
        out.append(source_object_panel(image_meta, 835, 168, 300, 300, slide_no=slide_no, dark=True))
        out.append(rect(0, 0, 850, H, f"url(#blueScrim{slide_no})"))
    title = title_of(slide)
    out.append(editorial_label(78, 94, "最终判断", dark=True))
    out.append(text(78, 174, cjk_wrap(title, 13), size=60, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.18))
    takeaway = points[0] if points else str(slide.get("speaker_note_goal") or "把主题重新放回它的时代、证据与当代意义中。")
    out.append(text(86, 396, cjk_wrap(takeaway, 25)[:3], size=26, fill="#EADFCF", family=BODY_FONT, weight="700", line_height=1.34))
    out.append(line(86, 504, 470, 504, PALETTE["red"], sw=3.4, opacity=0.9))
    for idx, keyword in enumerate(keywords_for_slide(slide, 4) or ["结构", "证据", "人物", "余响"]):
        x = 92 + idx * 178
        out.append(text(x, 562, keyword, size=20, fill=PALETTE["white"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide, dark=True))
    return "\n".join(out)


def slide_role(slide: dict[str, Any]) -> str:
    component_plan = slide.get("component_plan")
    if isinstance(component_plan, dict) and component_plan.get("component_type"):
        return str(component_plan["component_type"]).strip()
    return str(slide.get("visual_role") or slide.get("proof_object") or "").strip()


def evidence_of(slide: dict[str, Any]) -> str:
    return str(slide.get("source_anchor") or slide.get("concrete_anchor") or slide.get("proof_object") or "").strip()


def render_generic_context(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else "")
    image = slide_image(images, slide_no)
    out = [paper_bg(slide_no), image_panel(image, 690, 0, 590, 720, slide_no=slide_no)]
    out.append(rect(0, 0, 760, H, f"url(#softPaperScrim{slide_no})"))
    out.append(editorial_label(78, 92, "现场证据"))
    out.append(magazine_headline(76, 166, title_of(slide), width_chars=13, size=45, max_lines=3))
    out.append(rect(82, 388, 430, 142, PALETTE["white"], stroke=PALETTE["ink"], sw=1.35))
    out.append(text(112, 438, cjk_wrap(evidence, 17)[:3], size=25, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.22))
    out.append(editorial_label(112, 570, "证据锚点"))
    labels = ["现场", "处境", "含义"]
    for idx, label in enumerate(labels):
        y = 158 + idx * 132
        body = points[idx] if idx < len(points) else evidence
        out.append(rect(538, y, 260, 96, PALETTE["paper"], stroke=PALETTE["line"], sw=1.1, fill_opacity=0.86))
        out.append(text(562, y + 36, label, size=24, fill=PALETTE["red"], family=TITLE_FONT, weight="700"))
        out.append(text(628, y + 34, cjk_wrap(body, 11)[:2], size=15, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.28))
    out.append(line(526, 154, 526, 548, PALETTE["red"], sw=2.8))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_core_text(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else "")
    keywords = keywords_for_slide(slide, 5)
    book_match = re.search(r"《([^》]{2,30})》", title_of(slide) + " " + evidence)
    book_title = f"《{book_match.group(1)}》" if book_match else "核心文本"
    out = [paper_bg(slide_no)]
    image = slide_image(images, slide_no)
    if image:
        out.append(image_tag(image, 0, 0, W, H, preserve="xMidYMid slice"))
        out.append(rect(0, 0, W, H, PALETTE["paper"], fill_opacity=0.52))
    out.append(page_title(slide_no, title_of(slide)))
    out.append(rect(92, 134, 410, 468, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.8))
    out.append(rect(128, 176, 338, 384, PALETTE["paper"], stroke=PALETTE["gold"], sw=1.5))
    out.append(line(160, 214, 434, 214, PALETTE["line"], sw=1.1))
    out.append(line(160, 520, 434, 520, PALETTE["line"], sw=1.1))
    out.append(text(297, 326, cjk_wrap(book_title, 7), size=49, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", anchor="middle", line_height=1.12))
    out.append(text(297, 470, cjk_wrap(evidence, 13)[:4], size=19, fill=PALETTE["muted"], family=BODY_FONT, anchor="middle", line_height=1.28))
    out.append(editorial_label(610, 152, "文本入口"))
    for idx, keyword in enumerate(keywords[:4]):
        x = 590 + (idx % 2) * 292
        y = 190 + (idx // 2) * 162
        out.append(rect(x, y, 250, 116, PALETTE["white"], stroke=PALETTE["ink"], sw=1.2))
        out.append(text(x + 22, y + 42, f"{idx + 1:02d}", size=22, fill=PALETTE["red" if idx % 2 else "blue"], family=MONO_FONT, weight="700"))
        out.append(text(x + 78, y + 42, cjk_wrap(keyword, 8), size=24, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.1))
        body = points[idx] if idx < len(points) else evidence
        out.append(text(x + 22, y + 82, cjk_wrap(body, 18)[:2], size=15, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.25))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_mechanism(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else "")
    labels = keywords_for_slide(slide, 3) or ["媒介", "动作", "结果"]
    while len(labels) < 3:
        labels.append(["媒介", "动作", "结果"][len(labels)])
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.append(text(86, 612, cjk_wrap(evidence, 48)[:2], size=20, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.28))
    centers = [(258, 382), (640, 318), (1022, 382)]
    for idx, (cx, cy) in enumerate(centers):
        out.append(circle(cx, cy, 116, PALETTE["white"], stroke=PALETTE["ink"], sw=1.7))
        out.append(circle(cx, cy, 80, "none", stroke=PALETTE["red" if idx == 1 else "blue"], sw=2.2, opacity=0.7))
        out.append(text(cx, cy - 18, labels[idx], size=31, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", anchor="middle"))
        body = points[idx] if idx < len(points) else evidence
        out.append(text(cx - 82, cy + 44, cjk_wrap(body, 10)[:3], size=15, fill=PALETTE["muted"], family=BODY_FONT, weight="700", line_height=1.22))
    out.append(path("M374,368 C468,300 530,300 524,318", PALETTE["red"], sw=2.8, dash="9 7"))
    out.append(path("M756,318 C790,304 864,316 906,368", PALETTE["red"], sw=2.8, dash="9 7"))
    out.append(text(640, 514, "机制不是线性说明，而是冲突如何被叙事装置放大。", size=22, fill=PALETTE["muted"], family=BODY_FONT, weight="700", anchor="middle"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_conflict(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else "")
    image = slide_image(images, slide_no)
    out = [paper_bg(slide_no, dark=True)]
    if image:
        out.append(image_tag(image, 0, 0, W, H, preserve="xMidYMid slice"))
    out.append(rect(0, 0, W, H, PALETTE["dark"], fill_opacity=0.48 if image else 0.72))
    out.append(rect(0, 0, W, H, f"url(#blueScrim{slide_no})"))
    out.append(editorial_label(72, 88, "冲突结构", dark=True))
    out.append(text(70, 164, cjk_wrap(title_of(slide), 15)[:3], size=48, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.12))
    axes = [
        ("欲望", points[0] if points else evidence),
        ("制度", points[1] if len(points) > 1 else evidence),
        ("道德", points[2] if len(points) > 2 else evidence),
    ]
    for idx, (label, body) in enumerate(axes):
        x = 94 + idx * 380
        y = 400 - (idx % 2) * 44
        out.append(rect(x, y, 310, 126, PALETTE["paper"], stroke=PALETTE["white"], sw=1.1, fill_opacity=0.12))
        out.append(text(x + 28, y + 45, label, size=34, fill=PALETTE["white"], family=TITLE_FONT, weight="700"))
        out.append(text(x + 28, y + 86, cjk_wrap(body, 16)[:2], size=16, fill="#D8CCBC", family=BODY_FONT, line_height=1.28))
    out.append(path("M404,452 C492,356 592,342 680,408 C762,470 838,472 946,402", PALETTE["red"], sw=3.2, opacity=0.9))
    out.append(text(86, 596, cjk_wrap(evidence, 40)[:2], size=18, fill="#EADFCF", family=BODY_FONT, weight="700", line_height=1.3))
    out.append(generic_footer(slide_no, total, slide, dark=True))
    return "\n".join(out)


def render_generic_comparison(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    image = slide_image(images, slide_no)
    out = [paper_bg(slide_no)]
    if image:
        out.append(image_tag(image, 0, 0, W, H, preserve="xMidYMid slice"))
        out.append(rect(0, 0, W, H, PALETTE["paper"], fill_opacity=0.54))
    out.append(page_title(slide_no, title_of(slide)))
    left = points[0] if points else evidence_of(slide)
    right = points[1] if len(points) > 1 else evidence_of(slide)
    out.extend(style_proof_ornament(70, 154, 1140, 356, kind="comparison", index=slide_no))
    out.append(rect(80, 170, 500, 320, PALETTE["white"], stroke=PALETTE["ink"], sw=1.4))
    out.append(rect(700, 170, 500, 320, PALETTE["white"], stroke=PALETTE["ink"], sw=1.4))
    out.append(text(112, 232, "A", size=52, fill=PALETTE["blue"], family=MONO_FONT, weight="700"))
    out.append(text(732, 232, "B", size=52, fill=PALETTE["red"], family=MONO_FONT, weight="700"))
    out.append(text(178, 232, cjk_wrap(left, 14)[:5], size=29, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.16))
    out.append(text(798, 232, cjk_wrap(right, 14)[:5], size=29, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.16))
    out.append(circle(640, 328, 52, PALETTE["dark"]))
    out.append(text(640, 342, "VS", size=28, fill=PALETTE["white"], family=MONO_FONT, weight="700", anchor="middle"))
    out.append(line(580, 328, 700, 328, PALETTE["red"], sw=2.2, opacity=0.62))
    takeaway = points[2] if len(points) > 2 else "比较之后，把共同指向写成一条判断。"
    out.append(text(146, 566, cjk_wrap(takeaway, 38)[:2], size=26, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.2))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_image_left_story(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    image = slide_image(images, slide_no)
    evidence = evidence_of(slide) or (points[0] if points else "")
    out = [paper_bg(slide_no)]
    out.append(image_panel(image, 0, 0, 590, 720, slide_no=slide_no))
    out.append(rect(520, 0, 760, H, f"url(#softPaperScrim{slide_no})"))
    out.append(editorial_label(654, 92, "图像证据"))
    out.append(magazine_headline(650, 166, title_of(slide), width_chars=13, size=43, max_lines=3))
    out.append(text(656, 356, cjk_wrap(evidence, 23)[:3], size=22, fill=PALETTE["muted"], family=BODY_FONT, weight="700", line_height=1.35))
    out.append(bullet_stack(656, 488, points, w_chars=22, max_items=2))
    out.append(rect(54, 562, 420, 68, PALETTE["dark"], fill_opacity=0.76))
    out.append(text(80, 604, cjk_wrap(evidence or "source-backed image", 20)[:1], size=18, fill=PALETTE["white"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_image_top_feature(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    image = slide_image(images, slide_no)
    evidence = evidence_of(slide) or (points[0] if points else "")
    out = [paper_bg(slide_no)]
    out.append(image_panel(image, 0, 0, W, 330, slide_no=slide_no))
    out.append(rect(0, 0, W, 330, PALETTE["dark"], fill_opacity=0.22))
    out.append(rect(0, 0, 760, 330, f"url(#blueScrim{slide_no})"))
    out.append(editorial_label(72, 76, "专题页", dark=True))
    out.append(magazine_headline(70, 138, title_of(slide), width_chars=14, size=42, dark=True, max_lines=3))
    out.append(rect(72, 376, 380, 178, PALETTE["white"], stroke=PALETTE["ink"], sw=1.4))
    out.append(text(104, 430, cjk_wrap(evidence, 15)[:4], size=25, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.22))
    for idx, point in enumerate(points[:3]):
        x = 520 + idx * 226
        out.append(line(x, 386, x + 138, 386, PALETTE["red" if idx % 2 else "blue"], sw=3.0))
        out.append(text(x, 430, f"{idx + 1:02d}", size=24, fill=PALETTE["red" if idx % 2 else "blue"], family=MONO_FONT, weight="700"))
        out.append(text(x, 474, cjk_wrap(point, 12)[:4], size=17, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.3))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_pull_quote_spread(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    quote = evidence_of(slide) or (points[0] if points else title_of(slide))
    image = slide_image(images, slide_no)
    out = [paper_bg(slide_no, dark=True)]
    if image:
        out.append(image_tag(image, 0, 0, W, H, preserve="xMidYMid slice"))
    out.append(rect(0, 0, W, H, PALETTE["dark"], fill_opacity=0.52 if image else 0.9))
    out.append(rect(0, 0, 820, H, f"url(#blueScrim{slide_no})"))
    out.append(editorial_label(74, 92, "记忆钩子", dark=True))
    out.append(pull_quote_block(72, 190, 680, quote, dark=True, size=38))
    out.append(text(92, 470, cjk_wrap(title_of(slide), 24)[:2], size=23, fill="#EADFCF", family=BODY_FONT, weight="700", line_height=1.32))
    out.append(bullet_stack(830, 170, points[1:] if len(points) > 1 else points, w_chars=15, dark=True, max_items=3, accent=PALETTE["gold"]))
    out.append(generic_footer(slide_no, total, slide, dark=True))
    return "\n".join(out)


def render_generic_source_evidence_spread(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else title_of(slide))
    meta = slide_image_meta(images, slide_no)
    image = image_href(meta)
    caption = source_visual_caption(meta)
    out = [paper_bg(slide_no)]
    out.extend(style_proof_ornament(46, 62, 1188, 570, kind="source_evidence", index=slide_no))
    if slide_no % 2 == 0:
        out.append(editorial_label(72, 92, "源图证据"))
        out.append(magazine_headline(70, 166, title_of(slide), width_chars=12, size=41, max_lines=3))
        out.append(rect(78, 360, 410, 116, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.2))
        out.append(text(106, 405, cjk_wrap(evidence, 16)[:3], size=23, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.18))
        support_points = points[:3] if points else [evidence]
        for idx, point in enumerate(support_points[:3]):
            y = 512 + idx * 42
            out.append(text(82, y, f"{idx + 1:02d}", size=18, fill=PALETTE["red" if idx % 2 else "blue"], family=MONO_FONT, weight="700"))
            out.append(text(130, y, cjk_wrap(point, 20)[:1], size=16, fill=PALETTE["muted"], family=BODY_FONT, weight="700"))
        out.append(rect(554, 70, 676, 552, PALETTE["white"], stroke=PALETTE["ink"], sw=1.3))
        if image and image_fit_for_slot(meta, 628, 488, max_upscale=1.35):
            out.append(image_tag(image, 578, 96, 628, 488, preserve="xMidYMid meet"))
            out.append(rect(578, 552, 628, 32, PALETTE["dark"], fill_opacity=0.72))
            out.append(text(600, 574, caption, size=13, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
        elif image:
            out.append(source_object_panel(meta, 694, 142, 360, 330, slide_no=slide_no, dark=False))
        else:
            out.append(image_panel("", 578, 96, 628, 488, slide_no=slide_no))
        out.append(line(522, 94, 522, 612, PALETTE["red"], sw=2.6, opacity=0.7))
        out.append(generic_footer(slide_no, total, slide))
        return "\n".join(out)
    out.append(rect(52, 74, 686, 548, PALETTE["white"], stroke=PALETTE["ink"], sw=1.3))
    if image and image_fit_for_slot(meta, 642, 504, max_upscale=1.35):
        out.append(image_tag(image, 74, 96, 642, 504, preserve="xMidYMid meet"))
        out.append(rect(74, 568, 642, 32, PALETTE["dark"], fill_opacity=0.72))
        out.append(text(96, 590, caption, size=13, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    elif image:
        out.append(source_object_panel(meta, 206, 142, 360, 330, slide_no=slide_no, dark=False))
    else:
        out.append(image_panel("", 74, 96, 642, 504, slide_no=slide_no))
    out.append(editorial_label(800, 96, "源图证据"))
    out.append(magazine_headline(798, 166, title_of(slide), width_chars=12, size=42, max_lines=3))
    out.append(rect(802, 356, 330, 120, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.2))
    out.append(text(828, 402, cjk_wrap(evidence, 13)[:3], size=24, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.18))
    support_points = points[:3] if points else [evidence]
    for idx, point in enumerate(support_points[:3]):
        y = 512 + idx * 42
        out.append(line(804, y - 12, 852, y - 12, PALETTE["red" if idx % 2 else "blue"], sw=2.3))
        out.append(text(868, y, cjk_wrap(point, 18)[:1], size=16, fill=PALETTE["muted"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_source_top_feature(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else title_of(slide))
    meta = slide_image_meta(images, slide_no)
    image = image_href(meta)
    caption = source_visual_caption(meta)
    out = [paper_bg(slide_no)]
    out.append(rect(58, 72, 1164, 344, PALETTE["white"], stroke=PALETTE["ink"], sw=1.35))
    if image:
        out.append(image_tag(image, 82, 96, 1116, 276, preserve="xMidYMid meet"))
    else:
        out.append(image_panel("", 82, 96, 1116, 276, slide_no=slide_no))
    out.append(rect(82, 372, 1116, 28, PALETTE["dark"], fill_opacity=0.74))
    out.append(text(104, 392, caption, size=12, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    out.append(editorial_label(78, 476, "源图主视觉"))
    out.append(magazine_headline(76, 548, title_of(slide), width_chars=18, size=35, max_lines=2))
    out.append(rect(780, 472, 356, 122, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.2))
    out.append(text(808, 518, cjk_wrap(evidence, 16)[:2], size=22, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.2))
    for idx, point in enumerate((points[1:] if len(points) > 1 else points)[:2]):
        out.append(line(808, 630 + idx * 24, 866, 630 + idx * 24, PALETTE["red" if idx % 2 else "blue"], sw=2.0))
        out.append(text(880, 636 + idx * 24, cjk_wrap(point, 20)[:1], size=15, fill=PALETTE["muted"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_source_process_flow(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any]) -> str:
    points = step_labels(slide, 4)
    evidence = evidence_of(slide) or points[0]
    meta = slide_image_meta(images, slide_no)
    image = image_href(meta)
    caption = source_visual_caption(meta)
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.extend(style_proof_ornament(64, 154, 1084, 430, kind="source_process", index=slide_no))
    out.append(rect(76, 170, 380, 332, PALETTE["white"], stroke=PALETTE["ink"], sw=1.35))
    if image:
        out.append(image_tag(image, 98, 194, 336, 248, preserve="xMidYMid meet"))
    else:
        out.append(image_panel("", 98, 194, 336, 248, slide_no=slide_no))
    out.append(rect(98, 442, 336, 30, PALETTE["dark"], fill_opacity=0.74))
    out.append(text(118, 463, caption, size=11, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    out.append(editorial_label(76, 558, "证据驱动流程"))
    out.append(text(218, 558, cjk_wrap(evidence, 24)[:2], size=18, fill=PALETTE["muted"], family=BODY_FONT, weight="700", line_height=1.25))
    xs = [584, 838, 584, 838]
    ys = [222, 222, 456, 456]
    for idx, point in enumerate(points[:4]):
        x, y = xs[idx], ys[idx]
        accent = [PALETTE["blue"], PALETTE["red"], PALETTE["green"], PALETTE["gold"]][idx]
        out.append(circle(x, y, 42, PALETTE["white"], stroke=accent, sw=2.2))
        out.append(text(x, y + 9, f"{idx + 1}", size=27, fill=accent, family=MONO_FONT, weight="700", anchor="middle"))
        out.append(rect(x + 58, y - 48, 226, 96, PALETTE["white"], stroke=PALETTE["ink"], sw=1.1))
        out.append(text(x + 80, y - 12, cjk_wrap(point, 11)[:3], size=16, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.18))
    out.append(path("M626,222 C690,178 770,178 796,222", PALETTE["red"], sw=2.0, dash="8 7", opacity=0.82))
    out.append(path("M838,270 C886,324 886,386 838,414", PALETTE["red"], sw=2.0, dash="8 7", opacity=0.82))
    out.append(path("M796,456 C720,510 636,510 626,456", PALETTE["red"], sw=2.0, dash="8 7", opacity=0.82))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_source_concept_map(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any]) -> str:
    points = step_labels(slide, 6)
    evidence = evidence_of(slide) or title_of(slide)
    meta = slide_image_meta(images, slide_no)
    image = image_href(meta)
    caption = source_visual_caption(meta)
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.extend(style_proof_ornament(64, 150, 1054, 456, kind="source_map", index=slide_no))
    out.append(rect(78, 164, 310, 390, PALETTE["white"], stroke=PALETTE["ink"], sw=1.3))
    if image:
        out.append(image_tag(image, 100, 188, 266, 290, preserve="xMidYMid meet"))
    else:
        out.append(image_panel("", 100, 188, 266, 290, slide_no=slide_no))
    out.append(rect(100, 478, 266, 28, PALETTE["dark"], fill_opacity=0.74))
    out.append(text(118, 498, caption, size=11, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    out.append(text(100, 538, cjk_wrap(evidence, 16)[:2], size=17, fill=PALETTE["muted"], family=BODY_FONT, weight="700", line_height=1.22))
    cx, cy = 774, 380
    out.append(circle(cx, cy, 88, PALETTE["dark"]))
    out.append(text(cx, cy - 8, cjk_wrap("主线", 4), size=27, fill=PALETTE["white"], family=TITLE_FONT, weight="700", anchor="middle"))
    out.append(text(cx - 70, cy + 42, cjk_wrap(evidence, 8)[:2], size=13, fill="#D8CCBC", family=BODY_FONT, weight="700", line_height=1.16))
    nodes = [(560, 210), (782, 184), (1004, 242), (1034, 492), (772, 574), (530, 492)]
    for idx, (point, (x, y)) in enumerate(zip(points, nodes)):
        accent = [PALETTE["blue"], PALETTE["red"], PALETTE["green"], PALETTE["gold"], PALETTE["navy"], PALETTE["red"]][idx]
        out.append(line(cx, cy, x, y, accent, sw=1.5, opacity=0.58))
        out.append(rect(x - 96, y - 40, 192, 80, PALETTE["white"], stroke=accent, sw=1.15))
        out.append(text(x - 74, y - 8, cjk_wrap(point, 9)[:2], size=15, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.16))
    out.append(editorial_label(82, 604, "概念关系图"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_source_screenshot_annotation(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else title_of(slide))
    meta = slide_image_meta(images, slide_no)
    image = image_href(meta)
    caption = source_visual_caption(meta)
    callouts = points[:4] if points else [evidence]
    while len(callouts) < 3:
        callouts.append(evidence)
    image_on_left = slide_no % 2 == 1
    img_x, img_y, img_w, img_h = (58, 92, 760, 524) if image_on_left else (462, 92, 760, 524)
    text_x = 852 if image_on_left else 72
    label_x = text_x
    out = [paper_bg(slide_no)]
    out.extend(style_proof_ornament(img_x - 10, img_y - 10, img_w + 20, img_h + 24, kind="screenshot_annotation", index=slide_no))
    out.append(editorial_label(label_x, 82, "截图注释"))
    out.append(magazine_headline(text_x, 138, title_of(slide), width_chars=9, size=34, max_lines=4))
    out.append(rect(text_x, 314, 352, 116, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.2))
    out.append(text(text_x + 26, 358, cjk_wrap(evidence, 12)[:3], size=22, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.18))
    out.append(rect(img_x, img_y, img_w, img_h, PALETTE["white"], stroke=PALETTE["ink"], sw=1.35))
    if image:
        out.append(image_tag(image, img_x + 22, img_y + 24, img_w - 44, img_h - 62, preserve="xMidYMid meet"))
    else:
        out.append(image_panel("", img_x + 22, img_y + 24, img_w - 44, img_h - 62, slide_no=slide_no))
    out.append(rect(img_x + 22, img_y + img_h - 54, img_w - 44, 32, PALETTE["dark"], fill_opacity=0.72))
    out.append(text(img_x + 44, img_y + img_h - 32, caption, size=13, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    y_positions = [206, 322, 438, 536]
    for idx, point in enumerate(callouts[:4]):
        y = y_positions[idx]
        color = [PALETTE["red"], PALETTE["blue"], PALETTE["red"], PALETTE["gold"]][idx % 4]
        if image_on_left:
            boundary_x = img_x + img_w
            box_x = text_x
            line_x2 = box_x - 16
            box_y = 448 + idx * 50 if idx < 3 else 596
        else:
            boundary_x = img_x
            box_x = text_x
            line_x2 = box_x + 326
            box_y = 448 + idx * 50 if idx < 3 else 596
        pin_y = max(img_y + 58, min(img_y + img_h - 78, y))
        out.append(circle(boundary_x, pin_y, 10, color, stroke=PALETTE["white"], sw=2.0))
        out.append(line(boundary_x, pin_y, line_x2, pin_y, color, sw=1.8, opacity=0.86, dash="6 5"))
        out.append(rect(box_x, box_y, 352, 42, PALETTE["white"], stroke=color, sw=1.15))
        out.append(text(box_x + 18, box_y + 27, f"{idx + 1:02d}", size=15, fill=color, family=MONO_FONT, weight="700"))
        out.append(text(box_x + 60, box_y + 27, cjk_wrap(point, 19)[:1], size=15, fill=PALETTE["ink"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_source_data_context(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else title_of(slide))
    meta = slide_image_meta(images, slide_no)
    image = image_href(meta)
    caption = source_visual_caption(meta)
    out = [paper_bg(slide_no)]
    out.append(page_title(slide_no, title_of(slide)))
    chart_x, chart_y, chart_w, chart_h = 72, 140, 1040, 392
    out.extend(style_proof_ornament(chart_x - 10, chart_y - 10, chart_w + 20, chart_h + 22, kind="data_context", index=slide_no))
    out.append(rect(chart_x, chart_y, chart_w, chart_h, PALETTE["white"], stroke=PALETTE["ink"], sw=1.4))
    if image:
        out.append(image_tag(image, chart_x + 20, chart_y + 20, chart_w - 40, chart_h - 58, preserve="xMidYMid meet"))
    else:
        out.append(image_panel("", chart_x + 20, chart_y + 20, chart_w - 40, chart_h - 58, slide_no=slide_no))
    out.append(rect(chart_x + 20, chart_y + chart_h - 38, chart_w - 40, 24, PALETTE["dark"], fill_opacity=0.72))
    out.append(text(chart_x + 42, chart_y + chart_h - 21, caption, size=11, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
    panel_x, panel_y, panel_w, panel_h = 104, 564, 1038, 82
    out.append(rect(panel_x, panel_y, panel_w, panel_h, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.2))
    out.append(text(panel_x + 26, panel_y + 32, "TAKEAWAY", size=13, fill=PALETTE["gold"], family=MONO_FONT, weight="700", letter_spacing=1.0))
    out.append(text(panel_x + 26, panel_y + 63, cjk_wrap(evidence, 31)[:1], size=26, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.1))
    support = points[1:] if len(points) > 1 else points
    for idx, point in enumerate((support or [evidence])[:3]):
        x = panel_x + 560 + idx * 150
        out.append(line(x, panel_y + 26, x + 54, panel_y + 26, PALETTE["red" if idx % 2 else "cyan"], sw=2.0))
        out.append(text(x, panel_y + 58, cjk_wrap(point, 8)[:1], size=14, fill="#D8CCBC", family=BODY_FONT, weight="700"))
    out.append(line(1118, 140, 1118, 532, PALETTE["red"], sw=2.4, opacity=0.75))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_source_image_comparison(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, Any]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[2] if len(points) > 2 else title_of(slide))
    source_metas = [meta for meta in slide_image_metas(images, slide_no) if is_source_visual(meta)]
    if len(source_metas) < 2:
        return render_generic_comparison(slide, slide_no, total, images)
    left_meta, right_meta = source_metas[:2]
    left_label = points[0] if points else "对照 A"
    right_label = points[1] if len(points) > 1 else "对照 B"
    takeaway = points[2] if len(points) > 2 else evidence
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.extend(style_proof_ornament(70, 154, 1140, 384, kind="source_comparison", index=slide_no))
    panel_y = 174
    panel_w = 500
    panel_h = 328
    left_x = 84
    right_x = 696
    for idx, (x, meta, label, accent) in enumerate(
        [
            (left_x, left_meta, left_label, PALETTE["blue"]),
            (right_x, right_meta, right_label, PALETTE["red"]),
        ],
        start=1,
    ):
        out.append(rect(x, panel_y, panel_w, panel_h, PALETTE["white"], stroke=PALETTE["ink"], sw=1.35))
        href = image_href(meta)
        if href:
            out.append(image_tag(href, x + 20, panel_y + 22, panel_w - 40, panel_h - 70, preserve="xMidYMid meet"))
        else:
            out.append(image_panel("", x + 20, panel_y + 22, panel_w - 40, panel_h - 70, slide_no=slide_no))
        out.append(rect(x + 20, panel_y + panel_h - 44, panel_w - 40, 26, PALETTE["dark"], fill_opacity=0.72))
        out.append(text(x + 40, panel_y + panel_h - 26, source_visual_caption(meta), size=11, fill=PALETTE["white"], family=MONO_FONT, weight="700"))
        out.append(rect(x, panel_y - 48, panel_w, 38, PALETTE["white"], stroke=accent, sw=1.2))
        out.append(text(x + 22, panel_y - 23, f"{idx:02d}", size=15, fill=accent, family=MONO_FONT, weight="700"))
        out.append(text(x + 72, panel_y - 23, cjk_wrap(label, 18)[:1], size=17, fill=PALETTE["ink"], family=BODY_FONT, weight="700"))
    out.append(circle(640, 336, 42, PALETTE["dark"]))
    out.append(text(640, 350, "VS", size=24, fill=PALETTE["white"], family=MONO_FONT, weight="700", anchor="middle"))
    out.append(line(584, 336, 696, 336, PALETTE["red"], sw=2.0, opacity=0.68))
    out.append(rect(126, 548, 1028, 82, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.1))
    out.append(text(154, 580, "TAKEAWAY", size=13, fill=PALETTE["gold"], family=MONO_FONT, weight="700", letter_spacing=1.0))
    out.append(text(154, 612, cjk_wrap(takeaway, 38)[:1], size=26, fill=PALETTE["white"], family=TITLE_FONT, weight="700"))
    out.append(text(780, 584, cjk_wrap(evidence, 20)[:2], size=16, fill="#D8CCBC", family=BODY_FONT, weight="700", line_height=1.22))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def wants_source_visual_render(slide: dict[str, Any], image_text_id: str, role_l: str, meta: dict[str, Any]) -> bool:
    if not is_source_visual(meta):
        return False
    media_need = str(slide.get("media_need") or "").lower()
    source_tokens = ("source", "screenshot", "figure", "image", "page", "图片", "截图", "图表", "页面")
    if any(token in media_need for token in source_tokens):
        return True
    if image_text_id in {"ITL03", "ITL09", "ITL10", "ITL13", "ITL14", "ITL18", "ITL20"}:
        return True
    return role_l in {"context", "evidence", "image_evidence", "source_evidence", "quote", "synthesis"}


def layout_id_for_render(slide: dict[str, Any]) -> str:
    value = str(slide.get("layout_pattern_id") or slide.get("layout_pattern") or "").upper()
    match = re.search(r"\bL\d{2}\b", value)
    return match.group(0) if match else ""


def image_text_id_for_render(slide: dict[str, Any]) -> str:
    value = str(slide.get("image_text_pattern_id") or slide.get("image_text_pattern") or "").upper()
    match = re.search(r"\bITL\d{2}\b", value)
    return match.group(0) if match else ""


def step_labels(slide: dict[str, Any], count: int = 5) -> list[str]:
    labels = points_of(slide)[:count]
    if len(labels) < 3:
        labels.extend(keywords_for_slide(slide, count - len(labels)))
    defaults = ["起点", "动作", "转折", "验证", "结果"]
    for item in defaults:
        if len(labels) >= count:
            break
        labels.append(item)
    return labels[:count]


def render_generic_process_flow(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = step_labels(slide, 5)
    evidence = evidence_of(slide) or points[0]
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.extend(style_proof_ornament(82, 146, 1074, 430, kind="process_flow", index=slide_no))
    out.append(editorial_label(92, 150, "过程不是列表"))
    out.append(text(92, 196, cjk_wrap(evidence, 25)[:3], size=25, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.22))
    y = 405
    start_x = 168
    gap = 226
    centers: list[tuple[float, float]] = []
    for idx, point in enumerate(points):
        x = start_x + idx * gap
        yy = y - 46 if idx % 2 else y + 34
        centers.append((x, yy))
        out.append(circle(x, yy, 50, PALETTE["white"], stroke=PALETTE["ink"], sw=1.6))
        out.append(text(x, yy + 9, f"{idx + 1}", size=30, fill=PALETTE["red" if idx % 2 else "blue"], family=MONO_FONT, weight="700", anchor="middle"))
        out.append(text(x - 82, yy + 94, cjk_wrap(point, 9)[:3], size=17, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.22))
    for (x1, y1), (x2, y2) in zip(centers, centers[1:]):
        out.append(path(f"M{x1 + 54:.1f},{y1:.1f} C{x1 + 112:.1f},{y1:.1f} {x2 - 112:.1f},{y2:.1f} {x2 - 56:.1f},{y2:.1f}", PALETTE["red"], sw=2.2, opacity=0.75, dash="8 7"))
    out.append(text(92, 604, "每一步都应能对应到来源、动作或判断；多余步骤宁可拆页，不压成段落。", size=18, fill=PALETTE["muted"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_mechanism_loop(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = step_labels(slide, 4)
    evidence = evidence_of(slide) or points[0]
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    cx, cy = 640, 388
    out.extend(style_proof_ornament(190, 168, 900, 440, kind="mechanism_loop", index=slide_no))
    out.append(circle(cx, cy, 116, PALETTE["dark"], fill_opacity=0.96))
    out.append(text(cx, cy - 12, cjk_wrap("核心机制", 5), size=30, fill=PALETTE["white"], family=TITLE_FONT, weight="700", anchor="middle", line_height=1.05))
    out.append(text(cx - 92, cy + 48, cjk_wrap(evidence, 11)[:2], size=15, fill="#D8CCBC", family=BODY_FONT, weight="700", line_height=1.22))
    nodes = [(330, 244), (950, 244), (950, 536), (330, 536)]
    labels = ["输入", "放大", "反馈", "改变"]
    for idx, (x, y) in enumerate(nodes):
        out.append(rect(x - 122, y - 62, 244, 124, PALETTE["white"], stroke=PALETTE["ink"], sw=1.35))
        out.append(text(x - 96, y - 20, labels[idx], size=25, fill=PALETTE["red" if idx % 2 else "blue"], family=TITLE_FONT, weight="700"))
        out.append(text(x - 96, y + 22, cjk_wrap(points[idx], 13)[:3], size=16, fill=PALETTE["muted"], family=BODY_FONT, weight="700", line_height=1.22))
    out.append(path("M452,244 C532,188 746,188 828,244", PALETTE["red"], sw=2.4, dash="8 7"))
    out.append(path("M950,306 C1008,372 1008,446 950,474", PALETTE["red"], sw=2.4, dash="8 7"))
    out.append(path("M828,536 C744,594 532,594 452,536", PALETTE["red"], sw=2.4, dash="8 7"))
    out.append(path("M330,474 C272,418 272,350 330,306", PALETTE["red"], sw=2.4, dash="8 7"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_chart_takeaway(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    evidence = evidence_of(slide) or (points[0] if points else title_of(slide))
    keywords = keywords_for_slide(slide, 5) or ["证据", "变化", "结论"]
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    out.extend(style_proof_ornament(76, 156, 720, 406, kind="chart_takeaway", index=slide_no))
    out.append(rect(86, 166, 700, 384, PALETTE["white"], stroke=PALETTE["ink"], sw=1.4))
    out.append(editorial_label(118, 214, "证据图形"))
    base_y = 486
    bar_w = 74
    for idx, keyword in enumerate(keywords[:5]):
        height = 88 + ((idx * 47 + len(keyword) * 13) % 190)
        x = 140 + idx * 120
        color = [PALETTE["blue"], PALETTE["red"], PALETTE["green"], PALETTE["gold"], PALETTE["navy"]][idx % 5]
        out.append(rect(x, base_y - height, bar_w, height, color, fill_opacity=0.82))
        out.append(text(x + bar_w / 2, base_y + 36, cjk_wrap(keyword, 5)[:2], size=14, fill=PALETTE["muted"], family=BODY_FONT, weight="700", anchor="middle", line_height=1.15))
    out.append(line(120, base_y, 738, base_y, PALETTE["ink"], sw=1.4))
    out.append(line(120, 254, 120, base_y, PALETTE["ink"], sw=1.4))
    out.append(rect(840, 174, 328, 366, PALETTE["dark"], stroke=PALETTE["ink"], sw=1.4))
    out.append(text(876, 242, "TAKEAWAY", size=15, fill=PALETTE["gold"], family=MONO_FONT, weight="700", letter_spacing=1.0))
    out.append(text(874, 314, cjk_wrap(evidence, 9)[:5], size=30, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.18))
    support = points[1] if len(points) > 1 else "结论必须指向一个具体判断，而不是装饰性图表。"
    out.append(text(878, 498, cjk_wrap(support, 17)[:2], size=17, fill="#D8CCBC", family=BODY_FONT, weight="700", line_height=1.28))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_concept_map(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = step_labels(slide, 6)
    evidence = evidence_of(slide) or title_of(slide)
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    cx, cy = 640, 368
    out.extend(style_proof_ornament(126, 148, 1028, 448, kind="concept_map", index=slide_no))
    out.append(circle(cx, cy, 104, PALETTE["dark"]))
    out.append(text(cx, cy - 10, cjk_wrap(evidence, 5)[:3], size=22, fill=PALETTE["white"], family=TITLE_FONT, weight="700", anchor="middle", line_height=1.14))
    angles = [-130, -62, 0, 62, 130, 180]
    radius = 270
    for idx, (point, deg) in enumerate(zip(points, angles)):
        rad = math.radians(deg)
        x = cx + math.cos(rad) * radius
        y = cy + math.sin(rad) * 205
        out.append(line(cx + math.cos(rad) * 116, cy + math.sin(rad) * 88, x - math.cos(rad) * 82, y - math.sin(rad) * 50, PALETTE["red" if idx % 2 else "blue"], sw=1.8, opacity=0.65))
        out.append(rect(x - 118, y - 48, 236, 96, PALETTE["white"], stroke=PALETTE["ink"], sw=1.15))
        out.append(text(x - 92, y - 12, cjk_wrap(point, 11)[:3], size=17, fill=PALETTE["ink"], family=BODY_FONT, weight="700", line_height=1.2))
    out.append(editorial_label(92, 600, "概念地图"))
    out.append(text(210, 600, "用空间关系解释结构，不把关系藏进项目符号。", size=18, fill=PALETTE["muted"], family=BODY_FONT, weight="700"))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_generic_objection_response(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    objection = points[0] if points else "常见反对意见"
    response = points[1] if len(points) > 1 else evidence_of(slide) or "回应需要回到证据、边界和条件。"
    boundary = points[2] if len(points) > 2 else "承认限制，才有可信判断。"
    out = [paper_bg(slide_no, dark=True)]
    out.append(rect(0, 0, W, H, f"url(#blueScrim{slide_no})"))
    out.append(editorial_label(78, 94, "反对意见 / 回应", dark=True))
    out.append(text(76, 170, cjk_wrap(title_of(slide), 18)[:3], size=46, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.14))
    out.append(rect(92, 350, 470, 180, PALETTE["paper"], stroke=PALETTE["white"], sw=1.1, fill_opacity=0.13))
    out.append(text(124, 408, "OBJECTION", size=15, fill=PALETTE["gold"], family=MONO_FONT, weight="700", letter_spacing=1.0))
    out.append(text(124, 462, cjk_wrap(objection, 18)[:3], size=25, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.18))
    out.append(rect(720, 276, 470, 254, PALETTE["paper"], stroke=PALETTE["red"], sw=1.4, fill_opacity=0.18))
    out.append(text(754, 342, "RESPONSE", size=15, fill=PALETTE["red"], family=MONO_FONT, weight="700", letter_spacing=1.0))
    out.append(text(754, 398, cjk_wrap(response, 17)[:4], size=27, fill=PALETTE["white"], family=TITLE_FONT, weight="700", line_height=1.18))
    out.append(path("M562,438 C622,380 668,370 720,394", PALETTE["red"], sw=3.0, opacity=0.92))
    out.append(text(124, 606, cjk_wrap(boundary, 45)[:2], size=18, fill="#D8CCBC", family=BODY_FONT, weight="700", line_height=1.3))
    out.append(generic_footer(slide_no, total, slide, dark=True))
    return "\n".join(out)


def render_generic(slide: dict[str, Any], slide_no: int, total: int, images: dict[str, str]) -> str:
    points = points_of(slide)
    role = slide_role(slide)
    layout_id = layout_id_for_render(slide)
    image_text_id = image_text_id_for_render(slide)
    role_l = role.lower()
    image_meta = slide_image_meta(images, slide_no)
    if slide_no == total or layout_id == "L35":
        return render_generic_closing(slide, slide_no, total, images)
    if wants_source_visual_render(slide, image_text_id, role_l, image_meta):
        return source_visual_renderer(slide, slide_no, total, images, image_text_id)
    if layout_id in {"L13", "L14", "L15", "L16", "L17"} or "process" in role_l or "method" in role_l:
        return render_generic_process_flow(slide, slide_no, total, images)
    if layout_id == "L18" or "loop" in role_l or "flywheel" in role_l:
        return render_generic_mechanism_loop(slide, slide_no, total, images)
    if layout_id in {"L19", "L20", "L22", "L23", "L25", "L26"} or image_text_id == "ITL20":
        return render_generic_chart_takeaway(slide, slide_no, total, images)
    if layout_id == "L24" or "concept" in role_l or "map" in role_l or "ecosystem" in role_l:
        return render_generic_concept_map(slide, slide_no, total, images)
    if layout_id in {"L31", "L32"} or "objection" in role_l:
        return render_generic_objection_response(slide, slide_no, total, images)
    if layout_id == "L34" or "quote" in role_l:
        return render_generic_pull_quote_spread(slide, slide_no, total, images)
    if image_text_id in {"ITL01", "ITL02", "ITL08", "ITL09", "ITL10"} and has_slide_image(images, slide_no):
        return render_generic_image_left_story(slide, slide_no, total, images)
    if image_text_id in {"ITL13", "ITL14"}:
        return render_generic_comparison(slide, slide_no, total, images)
    if role_l in {"context", "social_reading", "influence", "objection"}:
        return render_generic_context(slide, slide_no, total, images)
    if role_l == "core_text":
        return render_generic_core_text(slide, slide_no, total, images)
    if role_l == "mechanism":
        return render_generic_mechanism(slide, slide_no, total, images)
    if role_l == "conflict":
        return render_generic_conflict(slide, slide_no, total, images)
    if role_l == "comparison":
        return render_generic_comparison(slide, slide_no, total, images)
    if years_from_slide(slide):
        return render_generic_timeline(slide, slide_no, total, images)
    if has_slide_image(images, slide_no):
        variant = slide_no % 3
        if variant == 0:
            return render_generic_image_top_feature(slide, slide_no, total, images)
        if variant == 1:
            return render_generic_pull_quote_spread(slide, slide_no, total, images)
        return render_generic_image_left_story(slide, slide_no, total, images)
    out = [paper_bg(slide_no), page_title(slide_no, title_of(slide))]
    anchor = str(slide.get("source_anchor") or slide.get("proof_object") or "核心证据")
    out.append(rect(92, 168, 390, 390, PALETTE["white"], stroke=PALETTE["ink"], sw=1.5))
    out.append(text(122, 224, cjk_wrap(anchor, 13)[:5], size=31, fill=PALETTE["ink"], family=TITLE_FONT, weight="700", line_height=1.16))
    for idx, keyword in enumerate(keywords_for_slide(slide, 4)):
        out.append(text(122, 455 + idx * 30, keyword, size=15, fill=PALETTE["red" if idx % 2 else "blue"], family=MONO_FONT if re.search(r"[A-Za-z0-9]", keyword) else BODY_FONT, weight="700"))
    for idx, point in enumerate(points[:4]):
        x = 550 + (idx % 2) * 310
        y = 176 + (idx // 2) * 188
        out.append(card(x, y, 282, 136, f"要点 {idx + 1}", point, idx=idx + 1, accent=PALETTE["red" if idx % 2 else "blue"]))
    if not points:
        out.append(text(550, 250, cjk_wrap(str(slide.get("speaker_note_goal") or "补足内容要点后生成正式页面。"), 22), size=24, fill=PALETTE["muted"], family=BODY_FONT, line_height=1.3))
    out.append(generic_footer(slide_no, total, slide))
    return "\n".join(out)


def render_svg_with_groups(
    slide: dict[str, Any],
    slide_no: int,
    total: int,
    images: dict[str, str],
    *,
    use_special_renderers: bool = True,
) -> tuple[str, list[str]]:
    if use_special_renderers:
        body = RENDERERS.get(slide_no, render_generic)(slide, slide_no, total, images)
    elif wants_source_visual_render(
        slide,
        image_text_id_for_render(slide),
        slide_role(slide).lower(),
        slide_image_meta(images, slide_no),
    ):
        body = source_visual_renderer(slide, slide_no, total, images, image_text_id_for_render(slide))
    elif slide_no == 1:
        body = render_generic_cover(slide, slide_no, total, images)
    elif slide_no == total:
        body = render_generic_closing(slide, slide_no, total, images)
    else:
        body = render_generic(slide, slide_no, total, images)
    grouped_body, group_ids = semantic_group_body(slide_no, body)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" data-render-style="{esc(RENDER_STYLE['style_id'])}" data-render-material="{esc(RENDER_STYLE['material'])}" data-component-language="{esc(RENDER_STYLE['component_language'])}" data-proof-language="{esc(RENDER_STYLE['proof_language'])}">
{defs(slide_no)}
{grouped_body}
</svg>
''', group_ids


def render_svg(
    slide: dict[str, Any],
    slide_no: int,
    total: int,
    images: dict[str, str],
    *,
    use_special_renderers: bool = True,
) -> str:
    return render_svg_with_groups(slide, slide_no, total, images, use_special_renderers=use_special_renderers)[0]


def image_map(project: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    manifest_path = project / "visual_asset_manifest.json"
    if manifest_path.exists():
        data = load_json(manifest_path)
        items = data.get("items") if isinstance(data, dict) else []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                path_value = str(item.get("path") or "")
                status = str(item.get("status") or "")
                if not path_value or status not in {"Generated", "Sourced", "Existing", "Rendered"}:
                    continue
                path = project / path_value
                if not path.exists():
                    continue
                dimensions = image_dimensions(path)
                href = "../" + path_value
                meta = {
                    "href": href,
                    "asset_id": item.get("asset_id", ""),
                    "path": path_value,
                    "slide_no": item.get("slide_no", ""),
                    "asset_role": item.get("asset_role", ""),
                    "acquire_via": item.get("acquire_via", ""),
                    "status": status,
                    "source_id": item.get("source_id", ""),
                    "source_image_id": item.get("source_image_id", ""),
                    "source_page_url": item.get("source_page_url", ""),
                    "source_path": item.get("source_path", ""),
                    "source_page": item.get("source_page", ""),
                    "rights_notes": item.get("rights_notes", ""),
                    "reference": item.get("reference", ""),
                }
                if dimensions:
                    meta["dimensions"] = list(dimensions)
                asset_id = str(item.get("asset_id") or "")
                if asset_id:
                    out[asset_id] = meta
                try:
                    slide_no = int(item.get("slide_no"))
                except (TypeError, ValueError):
                    slide_no = 0
                if slide_no > 0:
                    slide_key = f"slide_{slide_no:02d}"
                    out.setdefault(slide_key, meta)
                    all_key = f"{slide_key}_all"
                    if not isinstance(out.get(all_key), list):
                        out[all_key] = []
                    out[all_key].append(meta)

    source_path = project / "assets/images/image_sources.json"
    if not source_path.exists():
        return out
    data = load_json(source_path)
    if not isinstance(data, list):
        return out
    for item in data:
        if isinstance(item, dict) and item.get("id") and item.get("path"):
            out.setdefault(str(item["id"]), "../" + str(item["path"]))
    return out


def layout_pattern_of(slide: dict[str, Any], idx: int) -> str:
    value = str(slide.get("layout_pattern_id") or slide.get("layout_pattern") or "").strip()
    match = re.search(r"\bL\d{2}\b", value.upper())
    if match:
        return match.group(0)
    fallback = {
        1: "L01",
        2: "L24",
        3: "L13",
        5: "L20",
        10: "L18",
        18: "L20",
        20: "L35",
    }
    return fallback.get(idx, "L08")


def component_type_of(slide: dict[str, Any], idx: int) -> str:
    layout_id = layout_pattern_of(slide, idx)
    layout_components = {
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
    if layout_id in layout_components:
        return layout_components[layout_id]
    component_plan = slide.get("component_plan")
    if isinstance(component_plan, dict) and component_plan.get("component_type"):
        return str(component_plan["component_type"])
    return str(slide.get("component_type") or slide.get("proof_object") or ("hero_claim" if idx == 1 else "evidence_layout"))


def normalized_page_rhythm(
    slide: dict[str, Any],
    idx: int,
    slide_count: int,
    use_special_renderers: bool = False,
) -> str:
    allowed = {"anchor", "breathing", "dense"}
    raw = str(slide.get("rhythm") or "").strip().lower().replace("-", "_")
    if raw in allowed:
        rhythm = raw
    elif idx in {1, slide_count}:
        rhythm = "anchor"
    elif raw in {"cover", "opening", "closing", "summary", "chapter", "hero", "anchor_page"}:
        rhythm = "anchor"
    elif raw in {"synthesis", "quote", "pause", "transition", "visual", "breathing_page"}:
        rhythm = "breathing"
    elif raw in {"claim_proof", "argument", "evidence", "mechanism", "comparison", "timeline", "framework"}:
        role = slide_role(slide).lower()
        rhythm = "breathing" if role in {"context", "social_reading", "closing"} else "dense"
    else:
        role = slide_role(slide).lower()
        rhythm = "breathing" if role in {"context", "social_reading", "quote", "synthesis"} else "dense"
    if use_special_renderers and idx in {3, 9, 11, 16, 20} and idx not in {1, slide_count}:
        rhythm = "breathing"
    return rhythm


def art_direction_of(slide: dict[str, Any], idx: int, slide_count: int, use_special_renderers: bool = False) -> str:
    if use_special_renderers:
        return "scientific_archive_custom"
    role = slide_role(slide).lower()
    if idx == 1:
        return "full_bleed_editorial_cover_itl03"
    if idx == slide_count:
        return "dark_editorial_closing_itl11"
    layout_id = layout_pattern_of(slide, idx)
    layout_mapping = {
        "L08": "asymmetric_comparison_itl13",
        "L13": "stepped_process_flow_l13",
        "L18": "mechanism_loop_flywheel_l18",
        "L20": "chart_takeaway_context_itl20",
        "L24": "hub_spoke_concept_map_l24",
        "L31": "dark_objection_response_l31",
        "L34": "pull_quote_breathing_spread_l34",
        "L35": "dark_editorial_closing_itl11",
    }
    if layout_id in layout_mapping:
        return layout_mapping[layout_id]
    mapping = {
        "context": "editorial_source_spread_itl09",
        "core_text": "book_object_plus_keyword_grid_itl15",
        "mechanism": "concept_mechanism_diagram_l13",
        "conflict": "dark_tension_triptych_itl12",
        "social_reading": "editorial_source_spread_itl09",
        "comparison": "asymmetric_comparison_itl13",
    }
    if role in mapping:
        return mapping[role]
    if years_from_slide(slide):
        return "timeline_evidence_band_itl16"
    return "claim_proof_editorial_panel"


def slide_coordinate_slots(slide: dict[str, Any], idx: int) -> list[dict[str, int | str]]:
    media_need = str(slide.get("media_need") or "").lower()
    has_media = idx in {1, 3, 4, 11, 16, 20} or "image" in media_need or "photo" in media_need
    layout_id = layout_pattern_of(slide, idx)
    if layout_id in {"L13", "L18", "L24"}:
        return [
            {"slot_id": "title_claim", "x": 58, "y": 48, "w": 1120, "h": 112},
            {"slot_id": "proof_object", "x": 80, "y": 150, "w": 1120, "h": 430},
            {"slot_id": "takeaway", "x": 86, "y": 584, "w": 1080, "h": 64},
        ]
    if layout_id in {"L20", "L31"}:
        return [
            {"slot_id": "title_claim", "x": 58, "y": 48, "w": 1120, "h": 112},
            {"slot_id": "proof_object", "x": 80, "y": 160, "w": 720, "h": 420},
            {"slot_id": "takeaway", "x": 820, "y": 160, "w": 370, "h": 420},
        ]
    if idx in {1, 9, 20}:
        return [
            {"slot_id": "title_claim", "x": 58, "y": 70, "w": 690, "h": 190},
            {"slot_id": "proof_object", "x": 64, "y": 250, "w": 700, "h": 350},
            {"slot_id": "media_or_takeaway", "x": 720, "y": 0, "w": 560, "h": 720},
        ]
    if has_media:
        return [
            {"slot_id": "title_claim", "x": 58, "y": 48, "w": 1120, "h": 112},
            {"slot_id": "proof_object", "x": 72, "y": 160, "w": 640, "h": 430},
            {"slot_id": "media_or_takeaway", "x": 720, "y": 104, "w": 500, "h": 500},
        ]
    return [
        {"slot_id": "title_claim", "x": 58, "y": 48, "w": 1120, "h": 112},
        {"slot_id": "proof_object", "x": 72, "y": 160, "w": 980, "h": 430},
        {"slot_id": "media_or_takeaway", "x": 840, "y": 160, "w": 360, "h": 430},
    ]


def build_spec_lock_json(
    slides: list[dict[str, Any]],
    group_ids_by_slide: dict[int, list[str]],
    *,
    use_special_renderers: bool,
) -> dict[str, Any]:
    contract_slides: list[dict[str, Any]] = []
    for idx, slide in enumerate(slides, start=1):
        rhythm = normalized_page_rhythm(slide, idx, len(slides), use_special_renderers)
        contract_slides.append(
            {
                "slide_no": idx,
                "slide_id": f"slide-{idx:02d}",
                "rhythm": rhythm,
                "proof_object": str(slide.get("proof_object") or slide.get("visual_role") or "claim_proof"),
                "layout_pattern_id": layout_pattern_of(slide, idx),
                "component_type": component_type_of(slide, idx),
                "art_direction": art_direction_of(slide, idx, len(slides), use_special_renderers),
                "reading_path": str(slide.get("reading_path") or "title_to_visual_to_takeaway"),
                "coordinate_slots": slide_coordinate_slots(slide, idx),
                "group_ids": group_ids_by_slide.get(idx, []),
                "image_text_pattern_id": str(slide.get("image_text_pattern_id") or image_text_pattern_for_layout(layout_pattern_of(slide, idx), idx, len(slides))),
            }
        )
    return {
        "schema_version": "1.0.0",
        "stage": {"width": W, "height": H, "unit": "px"},
        "selected_preset": "scientific_archive_editorial_svg_first" if use_special_renderers else "source_backed_editorial_svg_first",
        "render_style": dict(RENDER_STYLE),
        "palette": {
            "paper": PALETTE["paper"],
            "paper2": PALETTE["paper2"],
            "dark": PALETTE["dark"],
            "accent": PALETTE["red"],
            "secondary_accent": PALETTE["blue"],
            "text": PALETTE["ink"],
            "muted": PALETTE["muted"],
            "line": PALETTE["line"],
            "gold": PALETTE["gold"],
            "green": PALETTE["green"],
        },
        "typography": {
            "title_family": TITLE_FONT,
            "body_family": BODY_FONT,
            "code_family": MONO_FONT,
            "title_line_height_policy": "CJK multi-line page titles use 1.14-1.30 leading; cover/closing titles may tighten only after preview review.",
        },
        "layout_execution_contract": {
            "coordinate_policy": "absolute 1280x720 SVG coordinates with fixed safe margins",
            "text_fit_policy": "manual line breaks, fit checks, split slides, or shrink text before export; foreignObject is forbidden",
            "group_policy": "top-level semantic SVG groups for background, media, title, proof, body, and footer; group_ids must match rendered SVG.",
            "slides": contract_slides,
        },
    }


def image_text_pattern_for_layout(layout_id: str, idx: int, slide_count: int) -> str:
    if idx == 1:
        return "ITL03"
    if idx == slide_count:
        return "ITL11"
    mapping = {
        "L08": "ITL13",
        "L13": "ITL16",
        "L18": "ITL17",
        "L20": "ITL20",
        "L24": "ITL17",
        "L31": "ITL12",
        "L34": "ITL11",
        "L35": "ITL11",
    }
    return mapping.get(layout_id, "")


def write_specs(project: Path, slides: list[dict[str, Any]], group_ids_by_slide: dict[int, list[str]]) -> None:
    title = title_of(slides[0]) if slides else "Qiaomu SVG-first deck"
    use_special_renderers = is_einstein_deck(slides)
    rhythms = []
    charts = []
    for idx, slide in enumerate(slides, start=1):
        rhythm = normalized_page_rhythm(slide, idx, len(slides), use_special_renderers)
        rhythms.append(f"- P{idx:02d}: {rhythm}")
        if use_special_renderers and idx in {3, 5, 6, 7, 8, 10, 15, 18, 19}:
            chart = {
                3: "timeline",
                5: "paper_stack",
                6: "mechanism_diagram",
                7: "particle_path",
                8: "thought_experiment",
                10: "curvature_grid",
                15: "migration_map",
                18: "satellite_system",
                19: "method_loop",
            }[idx]
            charts.append(f"- P{idx:02d}: {chart}")
        elif not use_special_renderers:
            charts.append(f"- P{idx:02d}: {layout_pattern_of(slide, idx)} / {component_type_of(slide, idx)}")

    design_style = (
        "scientific archive editorial: public-domain archival images, blueprint diagrams, newspaper cuts, formula typography"
        if use_special_renderers
        else "source-backed editorial: theme-specific evidence panels, timelines when dates exist, magazine-like contrast, native SVG labels"
    )
    use_case = (
        "biographical science talk / classroom explainer / public lecture"
        if use_special_renderers
        else "topic explainer / research synthesis / presentation-ready narrative deck"
    )
    visual_theme = (
        "- Warm archival paper base with dark-blue anchor pages.\n"
        "- Real images are used as evidence/mood carriers; native SVG carries claims, labels, formulas, diagrams, and exact numbers.\n"
        "- Page rhythm alternates anchor, dense explanation, and breathing pages."
        if use_special_renderers
        else "- Warm editorial paper base with dark anchor pages for opening and closing.\n"
        "- Real source images are used when available; otherwise native SVG builds evidence objects, keyword rails, timelines, and claim panels.\n"
        "- Page rhythm follows the content: anchor pages for framing, dense pages for arguments, breathing pages for synthesis."
    )
    visual_theme += f"\n- Render style token: `{RENDER_STYLE['style_id']}` / `{RENDER_STYLE['material']}` / `{RENDER_STYLE['palette_behavior']}` / `{RENDER_STYLE['proof_language']}`."
    layout_principles = (
        "- No generic repeated card soup.\n"
        "- Every visual page has one dominant proof object: portrait, timeline, patent sheet, mechanism diagram, curvature grid, map, or satellite model.\n"
        "- Source/provenance is recorded in sidecars and notes, not as visible production labels."
        if use_special_renderers
        else "- No sample-specific visual language unless the topic explicitly calls for it.\n"
        "- Every page needs a dominant proof object: source quote, date sequence, comparison panel, image evidence, data shape, or concept diagram.\n"
        "- Source/provenance is recorded in sidecars and notes, while visible pages prioritize narrative clarity."
    )
    image_section = (
        "See `assets/images/image_sources.json`. Images are public-domain or no-known-restrictions Commons assets used as archival evidence/mood."
        if use_special_renderers
        else "See `assets/images/image_sources.json` when images were collected. Generated previews must remain topic-specific even when no images are available yet."
    )

    design_spec = f"""# {title} — Design Spec

> SVG-first Qiaomu PPT execution. The page visuals are authored as PPT-safe SVG,
> then finalized and converted to editable PPTX. Runtime dependency on external
> skills: none.

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | {project.name} |
| Canvas Format | PPT 16:9 (1280×720) |
| Page Count | {len(slides)} |
| Design Style | {design_style} |
| Use Case | {use_case} |

## II. Canvas Specification

- viewBox: `0 0 1280 720`
- safe margin: 60px horizontal / 48px vertical

## III. Visual Theme

{visual_theme}

## IV. Typography System

- Title: `{TITLE_FONT}`
- Body: `{BODY_FONT}`
- Mono/formula: `{MONO_FONT}`
- Normal page title: 28-31px with 1.14-1.30 leading; hero title: 58-64px; body: 18-24px.

## V. Layout Principles

{layout_principles}

## VI. Icon Usage

- No external icon dependency in this sample; semantic marks are native SVG shapes.

## VII. Visualization Reference List

{chr(10).join(charts)}

## VIII. Image Resource List

{image_section}

## IX. Content Outline

""" + "\n".join(
        f"### Slide {idx:02d} — {title_of(slide)}\n\n" +
        "\n".join(f"- {p}" for p in points_of(slide)) + "\n"
        for idx, slide in enumerate(slides, start=1)
    )
    spec_lock = f"""# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## colors
- render_style: {RENDER_STYLE['style_id']}
- render_material: {RENDER_STYLE['material']}
- component_language: {RENDER_STYLE['component_language']}
- proof_language: {RENDER_STYLE['proof_language']}
- palette_behavior: {RENDER_STYLE['palette_behavior']}
- bg: {PALETTE['paper']}
- bg_secondary: {PALETTE['paper2']}
- primary: {PALETTE['navy']}
- accent: {PALETTE['red']}
- secondary_accent: {PALETTE['blue']}
- cyan: {PALETTE['cyan']}
- gold: {PALETTE['gold']}
- green: {PALETTE['green']}
- white: {PALETTE['white']}
- warm_caption: #D8CCBC
- warm_light: #EADFCF
- warm_title: #EDE1D1
- text: {PALETTE['ink']}
- text_secondary: {PALETTE['muted']}
- text_tertiary: {PALETTE['faint']}
- border: {PALETTE['line']}
- dark: {PALETTE['dark']}
- image_rendering: archival-photo-plus-blueprint-svg
- image_palette: warm-paper-cobalt-vermilion

## typography
- font_family: {BODY_FONT}
- title_family: {TITLE_FONT}
- body_family: {BODY_FONT}
- code_family: {MONO_FONT}
- body: 20
- title: 31
- subtitle: 24
- annotation: 14
- footnote: 11
- cover_title: 64
- hero_number: 58
- formula_or_hero_number: 128
- year_or_keyword_hero: 178

## icons
- library: none
- inventory:

## images
"""
    if use_special_renderers:
        spec_lock += """- einstein_nobel: assets/images/einstein_nobel.png
- einstein_head: assets/images/einstein_head.jpg
- einstein_blackboard: assets/images/einstein_blackboard.jpg
- patent_electromagnet: assets/images/patent_electromagnet.png
"""
    else:
        spec_lock += """- resolved_image_manifest: assets/images/image_sources.json
- visual_asset_manifest: visual_asset_manifest.json
- preview_rule: non-topic sample assets and hardcoded sample labels are forbidden
"""
    spec_lock += f"""
## page_rhythm
{chr(10).join(rhythms)}

## page_charts
{chr(10).join(charts)}

## forbidden
- Mixing icon libraries
- rgba()
- `<style>`, `class`, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<script>`, `<iframe>`, `<symbol>`+`<use>`
- `<g opacity>` (set opacity on each child element individually)
- HTML named entities in text; XML reserved chars are escaped
"""
    write(project / "design_spec.md", design_spec)
    write(project / "spec_lock.md", spec_lock)
    write(project / "spec_lock.json", json.dumps(build_spec_lock_json(slides, group_ids_by_slide, use_special_renderers=use_special_renderers), ensure_ascii=False, indent=2) + "\n")


def write_manifest(project: Path, slides: list[dict[str, Any]], group_ids_by_slide: dict[int, list[str]]) -> None:
    payload = {
        "schema_version": "1.0.0",
        "generator": "qiaomu-ppt/scripts/svg_deck_from_slide_plan.py",
        "method": "svg_first_design_spec_spec_lock",
        "external_skill_dependency": "none",
        "slide_count": len(slides),
        "render_style": dict(RENDER_STYLE),
        "semantic_group_policy": "top-level PPT-editable SVG groups are generated per slide and mirrored into spec_lock.json layout_execution_contract.group_ids",
        "group_ids_by_slide": {f"slide-{idx:02d}": ids for idx, ids in group_ids_by_slide.items()},
        "outputs": {
            "svg_output": "svg_output",
            "design_spec": "design_spec.md",
            "spec_lock": "spec_lock.md",
            "notes": "notes",
        },
        "recommended_next_commands": [
            "python3 qiaomu-ppt/scripts/svg_quality_checker.py <project>/svg_output",
            "python3 qiaomu-ppt/scripts/finalize_svg.py <project>",
            "python3 qiaomu-ppt/scripts/svg_to_pptx.py <project> -s final --no-compat -o <project>/exports/<slug>.pptx",
        ],
    }
    write(project / "svg_generation_manifest.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SVG-first deck pages from slide_plan.json")
    parser.add_argument("project", type=Path, help="Project directory containing slide_plan.json")
    parser.add_argument("--plan", type=Path, default=None, help="Optional slide plan path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing svg_output")
    args = parser.parse_args()

    project = args.project
    plan_path = args.plan or project / "slide_plan.json"
    if not plan_path.exists():
        raise SystemExit(f"slide_plan not found: {plan_path}")
    slides = iter_slides(load_json(plan_path))
    if not slides:
        raise SystemExit("No slides found in slide_plan")

    svg_dir = project / "svg_output"
    notes_dir = project / "notes"
    if svg_dir.exists() and not args.force:
        raise SystemExit(f"{svg_dir} already exists; pass --force to overwrite")
    if args.force:
        for old_svg in svg_dir.glob("*.svg") if svg_dir.exists() else []:
            old_svg.unlink()
        for old_note in notes_dir.glob("*.md") if notes_dir.exists() else []:
            old_note.unlink()
    svg_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)
    images = image_map(project)
    apply_render_style(project)
    group_ids_by_slide: dict[int, list[str]] = {}
    use_special_renderers = is_einstein_deck(slides)

    for idx, slide in enumerate(slides, start=1):
        name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", title_of(slide))[:32].strip("_") or f"slide_{idx:02d}"
        svg_path = svg_dir / f"{idx:02d}_{name}.svg"
        svg_text, group_ids = render_svg_with_groups(
            slide,
            idx,
            len(slides),
            images,
            use_special_renderers=use_special_renderers,
        )
        group_ids_by_slide[idx] = group_ids
        write(svg_path, svg_text)
        note = [
            f"# Slide {idx:02d} — {title_of(slide)}",
            "",
            str(slide.get("speaker_note_goal") or "Explain the slide claim with source-backed details."),
            "",
            "Visible points:",
            *[f"- {point}" for point in points_of(slide)],
            "",
            f"Source anchor: {slide.get('source_anchor', '')}",
        ]
        write(notes_dir / f"{idx:02d}_{name}.md", "\n".join(note) + "\n")

    write_specs(project, slides, group_ids_by_slide)
    write_manifest(project, slides, group_ids_by_slide)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
