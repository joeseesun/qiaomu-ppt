#!/usr/bin/env python3
"""Validate formal semantic HTML decks for qiaomu-ppt.

This checker focuses on constraints that should be machine-enforced before a
browser review: registered slide/layout metadata, viewer chrome kept outside
the slide canvas, image slot declarations, and web asset budgets.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SLIDE_RE = re.compile(
    r"<section\b(?P<tag>[^>]*\bclass=[\"'][^\"']*\bslide\b[^\"']*[\"'][^>]*)>"
    r"(?P<body>[\s\S]*?)</section>",
    re.IGNORECASE,
)
ATTR_RE = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*([\"'])(.*?)\2", re.DOTALL)
IMG_RE = re.compile(r"<img\b(?P<tag>[^>]*)>", re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b(?P<tag>[^>]*)>", re.IGNORECASE)
LINK_RE = re.compile(r"<link\b(?P<tag>[^>]*)>", re.IGNORECASE)
SVG_LINE_TAG_RE = re.compile(r"<(?P<name>line|polyline|path|ellipse)\b(?P<tag>[^>]*)>", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<(?P<name>[a-zA-Z][\w:-]*)\b(?P<tag>[^>]*)>", re.IGNORECASE)
STYLE_SIZE_RE = re.compile(r"font-size\s*:\s*(?P<size>\d+(?:\.\d+)?)px", re.IGNORECASE)
DATA_URI_RE = re.compile(r"data:(?P<mime>[^;,]+)(?:;[^,]*)?,(?P<data>[^\"')\s>]+)", re.IGNORECASE)
URL_RE = re.compile(r"url\((?P<quote>[\"']?)(?P<url>.*?)(?P=quote)\)", re.IGNORECASE)

IMAGE_EXTS = {".avif", ".gif", ".jpg", ".jpeg", ".png", ".svg", ".webp"}
UNOPTIMIZED_EXTS = {".png", ".bmp", ".tiff", ".tif"}
MOTION_LEVELS = {"none", "subtle", "expressive", "cinematic"}
MOTION_ENGINES = {"css", "gsap", "lottie-web", "dotlottie", "custom"}
MOTION_ASSET_EXTS = {".js", ".mjs", ".json", ".lottie", ".wasm", ".svg", ".png", ".webp", ".jpg", ".jpeg"}
LINE_LIKE_CLASS_RE = re.compile(
    r"(?:^|[-_\s])(?:line|curve|connector|orbit|ring|route|path|ray|burst|streak|whisker)(?:$|[-_\s])",
    re.IGNORECASE,
)
ALLOWED_LINE_PURPOSES = {
    "chart-axis",
    "chart-series",
    "table-rule",
    "connector",
    "diagram-edge",
    "process-flow",
    "timeline",
    "map-route",
    "separator",
    "focus-underline",
    "shape-border",
}
TEXT_LINE_LABEL_TAGS = {"b", "em", "h1", "h2", "h3", "h4", "i", "label", "li", "p", "small", "span", "strong"}
FORBIDDEN_LINE_PURPOSE_RE = re.compile(
    r"(decor|ornament|energy|speed|tech|atmosphere|texture|noise|effect|background|motion-only)",
    re.IGNORECASE,
)

FORBIDDEN_CHROME_ATTR_RE = re.compile(
    r"\b(class|id|data-screen-label|data-role)\s*=\s*([\"'])"
    r"[^\"']*(?:top[-_ ]?(?:progress|page|pager)|page[-_ ]?(?:indicator|number|counter|progress)|"
    r"progress[-_ ]?(?:bar|strip|indicator)|slide[-_ ]?(?:footer|chrome)|"
    r"viewer[-_ ]?(?:nav|toolbar|chrome)|nav[-_ ]?(?:button|controls|dots)|"
    r"search[-_ ]?(?:box|control)|source[-_ ]?(?:url|footer|label)|production[-_ ]?footer)"
    r"[^\"']*\2",
    re.IGNORECASE,
)

PROVENANCE_TEXT_RE = re.compile(
    r"(?:来源[:：]\s*https?://|source\s*:\s*https?://|generated with|fetched via|"
    r"qiaomu-ppt|ppt-master|pipeline|artifact|fallback|model\s*:)",
    re.IGNORECASE,
)


@dataclass
class Finding:
    severity: str
    message: str
    slide: int | None = None


@dataclass
class AssetInfo:
    path: str
    size_bytes: int
    source: str


@dataclass
class Report:
    html_path: str
    slide_count: int = 0
    assets: list[AssetInfo] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    motion: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def total_asset_bytes(self) -> int:
        return sum(a.size_bytes for a in self.assets)

    @property
    def largest_asset_bytes(self) -> int:
        return max((a.size_bytes for a in self.assets), default=0)

    def add(self, severity: str, message: str, slide: int | None = None) -> None:
        self.findings.append(Finding(severity=severity, message=message, slide=slide))


def parse_attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): " ".join(m.group(3).split()) for m in ATTR_RE.finditer(tag)}


def iter_local_asset_refs(html: str) -> Iterable[tuple[str, str]]:
    for match in IMG_RE.finditer(html):
        attrs = parse_attrs(match.group("tag"))
        src = attrs.get("src")
        if src:
            yield src, "img"

    for match in SCRIPT_RE.finditer(html):
        attrs = parse_attrs(match.group("tag"))
        src = attrs.get("src")
        if src:
            yield src, "script"

    for match in LINK_RE.finditer(html):
        attrs = parse_attrs(match.group("tag"))
        href = attrs.get("href")
        rel = attrs.get("rel", "")
        if href and any(token in rel for token in ("stylesheet", "preload", "modulepreload")):
            yield href, "link"

    for match in URL_RE.finditer(html):
        url = match.group("url").strip()
        if url:
            yield url, "css-url"


def looks_external(ref: str) -> bool:
    return ref.startswith(("http://", "https://", "//", "mailto:", "tel:", "#"))


def data_uri_size(ref: str) -> int:
    match = DATA_URI_RE.search(ref)
    if not match:
        return 0
    data = match.group("data")
    try:
        return len(base64.b64decode(data, validate=False))
    except Exception:
        return int(len(data) * 0.75)


def resolve_asset(html_dir: Path, ref: str) -> Path | None:
    clean = ref.split("#", 1)[0].split("?", 1)[0]
    if not clean or looks_external(clean) or clean.startswith("data:"):
        return None
    path = (html_dir / clean).resolve()
    try:
        path.relative_to(html_dir.resolve())
    except ValueError:
        return None
    return path


def infer_project_root(html_path: Path) -> Path:
    if html_path.parent.name in {"html", "exports"}:
        return html_path.parent.parent
    return html_path.parent


def resolve_project_asset(project_root: Path, html_dir: Path, ref: str) -> Path | None:
    clean = ref.split("#", 1)[0].split("?", 1)[0].strip()
    if not clean or looks_external(clean) or clean.startswith("data:"):
        return None
    raw_path = Path(clean)
    candidates = [raw_path] if raw_path.is_absolute() else [project_root / clean, html_dir / clean]
    project_resolved = project_root.resolve()
    for candidate in candidates:
        path = candidate.resolve()
        try:
            path.relative_to(project_resolved)
        except ValueError:
            continue
        return path
    return None


def maybe_motion_finding(strict: bool) -> str:
    return "error" if strict else "warning"


def is_line_like_svg(name: str, attrs: dict[str, str]) -> bool:
    tag_name = name.lower()
    klass = attrs.get("class", "")
    if tag_name in {"line", "polyline"}:
        return True
    if attrs.get("data-line-purpose"):
        return True
    if attrs.get("stroke"):
        return True
    return bool(LINE_LIKE_CLASS_RE.search(klass))


def validate_line_purpose(report: Report, attrs: dict[str, str], label: str, slide_idx: int, *, strict: bool, element_kind: str) -> None:
    purpose = str(attrs.get("data-line-purpose") or "").strip().lower()
    severity = "error" if strict else "warning"
    if not purpose:
        report.add(severity, f"Line-like {element_kind} element must declare data-line-purpose: {label}", slide_idx)
        return
    if FORBIDDEN_LINE_PURPOSE_RE.search(purpose):
        report.add("error", f"Line-like {element_kind} element uses decorative/atmospheric purpose: {label} -> {purpose}", slide_idx)
        return
    if purpose not in ALLOWED_LINE_PURPOSES:
        report.add(
            severity,
            f"Line-like {element_kind} element has unsupported data-line-purpose `{purpose}`: {label}",
            slide_idx,
        )


def validate_svg_line_semantics(report: Report, body: str, slide_idx: int, *, strict: bool) -> None:
    for match in SVG_LINE_TAG_RE.finditer(body):
        name = match.group("name").lower()
        attrs = parse_attrs(match.group("tag"))
        if not is_line_like_svg(name, attrs):
            continue
        label = attrs.get("id") or attrs.get("class") or name
        validate_line_purpose(report, attrs, label, slide_idx, strict=strict, element_kind="SVG")


def validate_html_line_semantics(report: Report, body: str, slide_idx: int, *, strict: bool) -> None:
    for match in HTML_TAG_RE.finditer(body):
        name = match.group("name").lower()
        if name in TEXT_LINE_LABEL_TAGS or name in {"svg", "defs", "g", "line", "polyline", "path", "ellipse"}:
            continue
        attrs = parse_attrs(match.group("tag"))
        tokens = " ".join(
            str(attrs.get(key) or "") for key in ("id", "class", "data-motion-id", "data-role", "data-visual")
        )
        if not attrs.get("data-line-purpose") and not LINE_LIKE_CLASS_RE.search(tokens):
            continue
        label = attrs.get("id") or attrs.get("class") or name
        validate_line_purpose(report, attrs, label, slide_idx, strict=strict, element_kind="HTML")


def html_has_target(html: str, target: str) -> bool:
    value = target.strip()
    if not value:
        return True
    if value.startswith("#"):
        name = re.escape(value[1:])
        return bool(re.search(rf"\bid\s*=\s*([\"']){name}\1", html))
    if value.startswith("."):
        name = re.escape(value[1:])
        return bool(re.search(rf"\bclass\s*=\s*([\"'])[^\"']*\b{name}\b[^\"']*\1", html))
    if value.startswith("["):
        return value in html
    name = re.escape(value)
    return bool(
        re.search(rf"\bid\s*=\s*([\"']){name}\1", html)
        or re.search(rf"\bdata-screen-label\s*=\s*([\"']){name}\1", html)
        or re.search(rf"\bdata-motion-id\s*=\s*([\"']){name}\1", html)
        or re.search(rf"\bdata-motion-group\s*=\s*([\"']){name}\1", html)
    )


def load_motion_manifest(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__load_error__": str(exc)}
    if not isinstance(payload, dict):
        return {"__load_error__": "motion manifest must be a JSON object"}
    return payload


def iter_motion_slides(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
    elif isinstance(value, dict):
        for slide_id, item in value.items():
            if isinstance(item, dict):
                merged = dict(item)
                merged.setdefault("slide_id", slide_id)
                yield merged


def validate_motion_manifest(
    report: Report,
    html: str,
    html_path: Path,
    motion_manifest: Path | None,
    *,
    require_motion_manifest: bool,
    strict: bool,
    max_motion_asset_kb: int,
) -> None:
    html_dir = html_path.parent
    project_root = infer_project_root(html_path)
    if motion_manifest is None:
        candidate = project_root / "html_motion_manifest.json"
        if candidate.exists():
            motion_manifest = candidate
    if motion_manifest is None:
        if require_motion_manifest:
            report.add("error", "Motion manifest is required but html_motion_manifest.json was not found.")
        report.motion = {"status": "not_checked", "reason": "no motion manifest"}
        return

    motion_manifest = motion_manifest.resolve()
    payload = load_motion_manifest(motion_manifest)
    rel_manifest = str(motion_manifest)
    try:
        rel_manifest = motion_manifest.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        pass
    report.motion = {"status": "checked", "manifest": rel_manifest}
    if not payload:
        report.add("error", "Motion manifest could not be loaded.")
        return
    if "__load_error__" in payload:
        report.add("error", f"Invalid motion manifest: {payload['__load_error__']}")
        return

    mode = str(payload.get("mode") or "").strip()
    if mode and mode != "html_motion":
        report.add("error", "Motion manifest mode must be html_motion.")
    level = str(payload.get("level") or "").strip().lower()
    report.motion["level"] = level
    if level not in MOTION_LEVELS:
        report.add("error", "Motion manifest level must be one of: " + ", ".join(sorted(MOTION_LEVELS)))

    accessibility = payload.get("accessibility")
    accessibility_reduced_motion = accessibility.get("reduced_motion") if isinstance(accessibility, dict) else ""
    reduced_motion = str(payload.get("reduced_motion") or accessibility_reduced_motion or "").lower()
    if not any(token in reduced_motion for token in ("respect", "prefers-reduced-motion", "reduce")):
        report.add(maybe_motion_finding(strict), "Motion manifest must respect prefers-reduced-motion.")

    fallback = payload.get("fallback")
    if not isinstance(fallback, dict) or not any(
        key in fallback for key in ("static_state", "poster_policy", "readable_static_state", "final_state")
    ):
        report.add(maybe_motion_finding(strict), "Motion manifest needs a readable static fallback policy.")

    engines = payload.get("engines")
    engine_ids: list[str] = []
    if not isinstance(engines, list) or not engines:
        report.add("error", "Motion manifest needs at least one engine entry.")
        engines = []
    for engine in engines:
        if not isinstance(engine, dict):
            report.add("error", "Motion engine entries must be objects.")
            continue
        engine_id = str(engine.get("id") or engine.get("engine") or "").strip().lower()
        engine_ids.append(engine_id)
        if engine_id not in MOTION_ENGINES:
            report.add("error", f"Unsupported motion engine: {engine_id or '<empty>'}")
        source = str(engine.get("source") or "local").lower()
        path_ref = str(engine.get("path") or engine.get("src") or engine.get("library_path") or "").strip()
        if source in {"cdn", "external", "remote"}:
            report.add(maybe_motion_finding(strict), f"Motion engine {engine_id} is external; prefer local packaged JS.")
        if source == "local":
            if not path_ref:
                report.add("error", f"Local motion engine {engine_id} must declare path.")
                continue
            resolved = resolve_project_asset(project_root, html_dir, path_ref)
            if not resolved or not resolved.exists():
                report.add("error", f"Motion engine asset missing: {path_ref}")
                continue
            size = resolved.stat().st_size
            if resolved.suffix.lower() not in MOTION_ASSET_EXTS:
                report.add("warning" if not strict else "error", f"Motion engine asset has unexpected extension: {path_ref}")
            if size > max_motion_asset_kb * 1024:
                report.add("warning" if not strict else "error", f"Motion engine asset exceeds {max_motion_asset_kb} KB: {path_ref}")
    report.motion["engines"] = [engine_id for engine_id in engine_ids if engine_id]

    slides = list(iter_motion_slides(payload.get("slides")))
    if level != "none" and not slides:
        report.add(maybe_motion_finding(strict), "Motion manifest has no per-slide motion entries.")
    for slide in slides:
        slide_id = str(slide.get("slide_id") or slide.get("id") or slide.get("page") or "").strip()
        engine_id = str(slide.get("engine") or "").strip().lower()
        if engine_id and engine_id not in MOTION_ENGINES:
            report.add("error", f"Slide {slide_id or '<unknown>'} uses unsupported motion engine: {engine_id}")
        targets = slide.get("targets") or slide.get("groups") or slide.get("elements")
        target_values: list[str] = []
        if isinstance(targets, list):
            for item in targets:
                if isinstance(item, str):
                    target_values.append(item)
                elif isinstance(item, dict):
                    target = str(item.get("target") or item.get("id") or item.get("data_motion_id") or "").strip()
                    if target:
                        target_values.append(target)
        if not target_values:
            report.add(maybe_motion_finding(strict), f"Slide {slide_id or '<unknown>'} motion entry has no targets.")
        for target in target_values:
            if not html_has_target(html, target):
                report.add("error", f"Motion target not found in HTML: {target}")

    lottie_assets = payload.get("lottie_assets") or payload.get("lottie")
    if isinstance(lottie_assets, list):
        for item in lottie_assets:
            if not isinstance(item, dict):
                report.add("error", "Lottie asset entries must be objects.")
                continue
            asset_id = str(item.get("id") or item.get("name") or "").strip() or "<unnamed>"
            path_ref = str(item.get("path") or item.get("src") or "").strip()
            if not path_ref:
                report.add("error", f"Lottie asset {asset_id} must declare path.")
                continue
            resolved = resolve_project_asset(project_root, html_dir, path_ref)
            if not resolved or not resolved.exists():
                report.add("error", f"Lottie asset missing: {path_ref}")
            elif resolved.suffix.lower() not in {".json", ".lottie"}:
                report.add("error", f"Lottie asset must be .json or .lottie: {path_ref}")
            autoplay = bool(item.get("autoplay"))
            if autoplay:
                report.add("error", f"Lottie asset {asset_id} must set autoplay false for deterministic review.")
            if bool(item.get("loop")):
                report.add(maybe_motion_finding(strict), f"Lottie asset {asset_id} loops; record why a finite presentation loop is needed.")
            poster_ref = str(item.get("poster") or item.get("fallback_poster") or "").strip()
            if poster_ref:
                poster_path = resolve_project_asset(project_root, html_dir, poster_ref)
                if not poster_path or not poster_path.exists():
                    report.add("error", f"Lottie fallback poster missing: {poster_ref}")
            elif level == "cinematic":
                report.add(maybe_motion_finding(strict), f"Cinematic Lottie asset {asset_id} should declare a poster/fallback_poster.")


def image_slot_required(img_attrs: dict[str, str]) -> bool:
    src = img_attrs.get("src", "")
    klass = img_attrs.get("class", "")
    role = img_attrs.get("role", "")
    alt = img_attrs.get("alt", "")
    if role == "presentation":
        return False
    if re.search(r"\b(icon|logo|avatar|favicon|emoji|badge)\b", f"{klass} {alt}", re.IGNORECASE):
        return False
    return bool(src and not src.startswith("data:image/svg+xml"))


def validate_html(
    html_path: Path,
    *,
    max_package_kb: int,
    max_image_kb: int,
    max_data_uri_kb: int,
    max_motion_asset_kb: int,
    motion_manifest: Path | None,
    require_motion_manifest: bool,
    strict: bool,
) -> Report:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    html_dir = html_path.parent
    report = Report(html_path=str(html_path))

    slides = list(SLIDE_RE.finditer(html))
    report.slide_count = len(slides)
    if not slides:
        report.add("error", "No <section class=\"slide\"> pages found.")

    for idx, match in enumerate(slides, start=1):
        tag = match.group("tag")
        body = match.group("body")
        attrs = parse_attrs(tag)

        if not (attrs.get("data-slide-id") or attrs.get("id")):
            report.add("error", "Slide is missing stable id or data-slide-id.", idx)

        if not (attrs.get("data-layout-id") or attrs.get("data-layout")):
            report.add("error", "Slide is missing data-layout-id/data-layout registration.", idx)

        if not re.search(r"data-screen-label\s*=", body, re.IGNORECASE):
            report.add("warning" if not strict else "error", "Slide has no data-screen-label anchors for point review.", idx)

        if FORBIDDEN_CHROME_ATTR_RE.search(body):
            report.add("error", "Viewer chrome/progress/footer appears inside the slide canvas.", idx)

        if PROVENANCE_TEXT_RE.search(body):
            report.add("error", "Visible provenance/toolchain text appears inside the slide canvas.", idx)

        validate_svg_line_semantics(report, body, idx, strict=strict)
        validate_html_line_semantics(report, body, idx, strict=strict)

        for img_match in IMG_RE.finditer(body):
            img_attrs = parse_attrs(img_match.group("tag"))
            if image_slot_required(img_attrs) and not img_attrs.get("data-image-slot"):
                report.add("error", "Non-decorative image is missing data-image-slot.", idx)
            src = img_attrs.get("src", "")
            if src.startswith("data:"):
                size = data_uri_size(src)
                if size > max_data_uri_kb * 1024:
                    report.add("error", f"Image data URI is {size // 1024} KB; use a local optimized asset file.", idx)

        small_sizes = [float(m.group("size")) for m in STYLE_SIZE_RE.finditer(body)]
        if any(size < 14 for size in small_sizes):
            report.add("warning" if not strict else "error", "Inline font-size below 14px found in slide content.", idx)

    stage_markers = [
        "aspect-ratio",
        "data-stage",
        "1920x1080",
        "1280x720",
        "width:1920",
        "height:1080",
        "stageW",
        "stage-w",
    ]
    if not any(marker in html for marker in stage_markers):
        report.add("warning" if not strict else "error", "No fixed 16:9 stage/scaler marker found.")

    seen_assets: set[Path] = set()
    for ref, source in iter_local_asset_refs(html):
        if ref.startswith("data:"):
            size = data_uri_size(ref)
            if size > max_data_uri_kb * 1024:
                report.add("error", f"Data URI asset is {size // 1024} KB; use a local optimized asset file.")
            continue
        path = resolve_asset(html_dir, ref)
        if not path:
            continue
        if path in seen_assets:
            continue
        seen_assets.add(path)
        if not path.exists():
            report.add("error", f"Local asset missing: {ref}")
            continue
        size = path.stat().st_size
        report.assets.append(AssetInfo(path=str(path), size_bytes=size, source=source))
        if path.suffix.lower() in IMAGE_EXTS:
            if size > max_image_kb * 1024:
                report.add("error", f"Image asset exceeds {max_image_kb} KB: {ref} ({size // 1024} KB)")
            if path.suffix.lower() in UNOPTIMIZED_EXTS and size > 250 * 1024:
                report.add("warning" if not strict else "error", f"Large {path.suffix.upper()} image should usually be WebP/AVIF/JPEG: {ref}")

    if report.total_asset_bytes > max_package_kb * 1024:
        report.add("error", f"Local assets exceed package budget: {report.total_asset_bytes // 1024} KB > {max_package_kb} KB")

    validate_motion_manifest(
        report,
        html,
        html_path,
        motion_manifest,
        require_motion_manifest=require_motion_manifest,
        strict=strict,
        max_motion_asset_kb=max_motion_asset_kb,
    )

    return report


def write_outputs(report: Report, json_path: Path | None, markdown_path: Path | None) -> None:
    payload = {
        "html_path": report.html_path,
        "slide_count": report.slide_count,
        "asset_count": len(report.assets),
        "total_asset_kb": round(report.total_asset_bytes / 1024, 1),
        "largest_asset_kb": round(report.largest_asset_bytes / 1024, 1),
        "status": "failed" if report.errors else "passed",
        "errors": [f.__dict__ for f in report.errors],
        "warnings": [f.__dict__ for f in report.warnings],
        "assets": [a.__dict__ for a in report.assets],
        "motion": report.motion,
    }
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if markdown_path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# HTML Deck Validation",
            "",
            f"- HTML: `{report.html_path}`",
            f"- Status: `{payload['status']}`",
            f"- Slides: {report.slide_count}",
            f"- Assets: {len(report.assets)}",
            f"- Total assets: {payload['total_asset_kb']} KB",
            f"- Largest asset: {payload['largest_asset_kb']} KB",
            f"- Motion: `{report.motion.get('status', 'not_checked')}`",
            "",
        ]
        if report.errors:
            lines.append("## Errors")
            lines.extend(format_finding(f) for f in report.errors)
            lines.append("")
        if report.warnings:
            lines.append("## Warnings")
            lines.extend(format_finding(f) for f in report.warnings)
            lines.append("")
        markdown_path.write_text("\n".join(lines), encoding="utf-8")


def format_finding(finding: Finding) -> str:
    prefix = f"- slide {finding.slide}: " if finding.slide is not None else "- "
    return f"{prefix}{finding.message}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate qiaomu-ppt formal HTML deck output.")
    parser.add_argument("html", type=Path, help="Path to html/index.html or exports/<slug>.html")
    parser.add_argument("--max-package-kb", type=int, default=3072)
    parser.add_argument("--max-image-kb", type=int, default=250)
    parser.add_argument("--max-data-uri-kb", type=int, default=64)
    parser.add_argument("--max-motion-asset-kb", type=int, default=1024)
    parser.add_argument("--motion-manifest", type=Path, help="Optional html_motion_manifest.json path.")
    parser.add_argument("--require-motion-manifest", action="store_true", help="Fail if no motion manifest is present.")
    parser.add_argument("--strict", action="store_true", help="Promote selected warnings to errors.")
    parser.add_argument("--json", type=Path, help="Write JSON report.")
    parser.add_argument("--markdown", type=Path, help="Write Markdown report.")
    args = parser.parse_args(argv)

    report = validate_html(
        args.html,
        max_package_kb=args.max_package_kb,
        max_image_kb=args.max_image_kb,
        max_data_uri_kb=args.max_data_uri_kb,
        max_motion_asset_kb=args.max_motion_asset_kb,
        motion_manifest=args.motion_manifest,
        require_motion_manifest=args.require_motion_manifest,
        strict=args.strict,
    )
    write_outputs(report, args.json, args.markdown)

    if report.warnings:
        print("Warnings:", file=sys.stderr)
        for warning in report.warnings:
            print(format_finding(warning), file=sys.stderr)

    if report.errors:
        print("HTML deck validation failed:", file=sys.stderr)
        for error in report.errors:
            print(format_finding(error), file=sys.stderr)
        return 1

    print(
        "HTML deck validation passed: "
        f"{report.slide_count} slide(s), {len(report.assets)} asset(s), "
        f"{round(report.total_asset_bytes / 1024, 1)} KB."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
