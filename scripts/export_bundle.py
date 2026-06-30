#!/usr/bin/env python3
"""Build a qiaomu-ppt multi-format delivery bundle.

The exporter is intentionally conservative: it records missing evidence instead
of pretending that every target format was produced. Formal HTML is generated
as native semantic HTML from slide_plan.json when available; inline SVG pages
are only a compatibility fallback. Screenshot-based browser output remains a
separate parity preview.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


STATUS_EXPORTED = "exported"
STATUS_EXISTING = "existing"
STATUS_MISSING = "missing"
STATUS_FAILED = "failed"
SUPPORTED_FORMATS = {"pptx", "pdf", "html", "html-parity", "keynote"}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def keynote_capability_report(project: Path) -> dict[str, Any]:
    report_path = project / "keynote_capability.json"
    script = Path(__file__).resolve().parent / "keynote_capability.py"
    if not script.exists():
        return {
            "can_attempt_keynote_export": False,
            "reason": "keynote_capability.py not found",
            "report": rel(project, report_path),
        }
    proc = run([sys.executable, str(script), "--output", str(report_path)], timeout=20)
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {
            "can_attempt_keynote_export": False,
            "reason": "keynote capability command did not emit valid JSON",
            "stdout": proc.stdout[-1000:],
            "stderr": proc.stderr[-1000:],
        }
        write_json(report_path, payload)
    payload["report"] = rel(project, report_path)
    return payload


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def rel(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except Exception:
        return str(path)


def parse_formats(value: str) -> list[str]:
    formats = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in formats if item not in SUPPORTED_FORMATS]
    if unknown:
        raise SystemExit("unsupported export format(s): " + ", ".join(unknown))
    return formats


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, dict):
        for key in ("slides", "slide_plan", "pages"):
            value = plan.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    if isinstance(plan, list):
        return [item for item in plan if isinstance(item, dict)]
    return []


def load_slides(project: Path) -> list[dict[str, Any]]:
    plan_path = project / "slide_plan.json"
    if not plan_path.exists():
        return []
    return iter_slides(read_json(plan_path))


def slide_title(slide: dict[str, Any], idx: int) -> str:
    return str(slide.get("claim_title") or slide.get("title") or f"Slide {idx}").strip()


def slide_text(slide: dict[str, Any], idx: int) -> str:
    parts = [slide_title(slide, idx)]
    for key in ("subtitle", "intent", "concrete_anchor", "source_anchor"):
        value = str(slide.get(key) or "").strip()
        if value:
            parts.append(value)
    points = slide.get("content_points") or slide.get("bullets") or slide.get("points")
    if isinstance(points, list):
        parts.extend(str(item).strip() for item in points if str(item).strip())
    return " ".join(part for part in parts if part)


def safe_attr_id(value: Any, fallback: str, *, lower: bool = True) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^0-9A-Za-z_-]+", "-", text).strip("-_")
    if lower:
        text = text.lower()
    return text or fallback


def slide_stable_id(slide: dict[str, Any], idx: int) -> str:
    for key in ("slide_id", "page_id", "id", "slug"):
        value = slide.get(key)
        if value:
            return safe_attr_id(value, f"s{idx:02d}")
    return f"s{idx:02d}"


def slide_layout_id(slide: dict[str, Any]) -> str:
    for key in (
        "layout_id",
        "layout_pattern_id",
        "layout_pattern",
        "image_text_layout_id",
        "page_layout_id",
        "page_layout",
        "layout",
    ):
        value = slide.get(key)
        if value:
            match = re.search(r"\bL\d{2}\b", str(value).upper())
            if match:
                return match.group(0)
            return safe_attr_id(value, "L00", lower=False)
    return "L00"


def slide_component_type(slide: dict[str, Any]) -> str:
    component_plan = slide.get("component_plan")
    if isinstance(component_plan, dict) and component_plan.get("component_type"):
        return safe_attr_id(component_plan.get("component_type"), "generic")
    for key in ("component_type", "page_role", "visual_role", "content_type"):
        value = slide.get(key)
        if value:
            return safe_attr_id(value, "generic")
    return "generic"


def slide_screen_labels(slide: dict[str, Any], idx: int) -> list[dict[str, str]]:
    slide_id = slide_stable_id(slide, idx)
    labels: list[dict[str, str]] = []
    for key in (
        "claim_title",
        "title",
        "subtitle",
        "audience_takeaway",
        "visible_title",
        "visible_body",
        "concrete_anchor",
        "source_anchor",
    ):
        value = str(slide.get(key) or "").strip()
        if value:
            labels.append({"id": f"{slide_id}-{safe_attr_id(key, key)}", "field": key, "label": value})
    points = slide.get("content_points") or slide.get("bullets") or slide.get("points")
    if isinstance(points, list):
        for point_idx, point in enumerate(points, start=1):
            value = str(point).strip()
            if value:
                labels.append({"id": f"{slide_id}-point-{point_idx}", "field": "content_points", "label": value})
    if not labels:
        labels.append({"id": f"{slide_id}-title", "field": "title", "label": slide_title(slide, idx)})
    return labels


def existing_source_contracts(project: Path) -> list[str]:
    return [
        path
        for path in ("slide_plan.json", "content_contract.json", "visual_contract.json", "spec_lock.json")
        if (project / path).exists()
    ]


def build_html_source_map(
    project: Path,
    slides: list[dict[str, Any]],
    svgs: list[Path],
    source_dir: Path,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    count = max(len(slides), len(svgs))
    for idx in range(1, count + 1):
        slide = slides[idx - 1] if idx - 1 < len(slides) else {}
        svg_path = svgs[idx - 1] if idx - 1 < len(svgs) else None
        title_text = slide_title(slide, idx) if slide else f"Slide {idx}"
        row: dict[str, Any] = {
            "slide_no": idx,
            "slide_id": slide_stable_id(slide, idx),
            "layout_id": slide_layout_id(slide),
            "component_type": slide_component_type(slide),
            "title": title_text,
            "source_slide_plan_index": idx - 1 if idx - 1 < len(slides) else None,
            "screen_labels": slide_screen_labels(slide, idx),
            "render_mode": "native_semantic_dom" if slide else "svg_compatibility_fallback",
        }
        if svg_path:
            row["source_svg"] = rel(project, svg_path)
        rows.append(
            row
        )
    return {
        "schema_version": "1.0.0",
        "mode": "html_source_map",
        "render_strategy": "native_semantic_html_primary",
        "source_svg_dir": rel(project, source_dir) if svgs else "",
        "source_contracts": existing_source_contracts(project),
        "slide_count": len(rows),
        "slides": rows,
    }


def build_html_design_kernel(
    project: Path,
    title: str,
    source_map: dict[str, Any],
) -> dict[str, Any]:
    rows = source_map.get("slides") if isinstance(source_map.get("slides"), list) else []
    layout_rows = [
        {
            "slide_id": str(row.get("slide_id") or ""),
            "layout_id": str(row.get("layout_id") or "L00"),
            "component_type": str(row.get("component_type") or "generic"),
        }
        for row in rows
        if isinstance(row, dict)
    ]
    return {
        "schema_version": "1.0.0",
        "mode": "html_design_kernel",
        "kernel_id": "qiaomu-html-deck-kernel-v1",
        "title": title,
        "render_strategy": "native_semantic_html_primary",
        "stage_model": {
            "width": 1920,
            "height": 1080,
            "aspect_ratio": "16:9",
            "scaler": "top-left explicit 1920x1080 coordinate stage scaled by viewport fit; SVG may appear only as local component or compatibility fallback",
            "host_chrome": "outside_slide_stage",
            "min_body_px_at_1280_stage": 18,
        },
        "style_discovery": {
            "status": "derived_from_project_contracts",
            "candidate_roles": ["safe_fit", "distinctive_fit", "wildcard_risk"],
            "source": "design_proposal.md/style_direction.json when present; otherwise project renderer fallback",
        },
        "token_contract": {
            "status": "fallback_export_tokens",
            "groups": ["color", "typography", "spacing", "surface", "motion"],
            "evidence": "source_backed tokens should be supplied by style_direction.json or visual_contract.json for custom formal HTML",
        },
        "layout_registry": {
            "slide_id_attr": "data-slide-id",
            "layout_id_attr": "data-layout-id",
            "source": "html_source_map.json",
            "slides": layout_rows,
        },
        "image_slot_registry": {
            "slot_attr": "data-image-slot",
            "source": "visual_asset_manifest.json or html_delivery_manifest.json",
            "status": "native DOM export uses no raster image slots by default" if not (project / "visual_asset_manifest.json").exists() else "see visual_asset_manifest.json",
        },
        "semantic_component_registry": {
            "slide_selector": "section.slide",
            "screen_label_attr": "data-screen-label",
            "component_types": sorted({row["component_type"] for row in layout_rows}) if layout_rows else ["generic"],
        },
        "motion_policy": {
            "level": "none",
            "engines": [],
            "fallback": "static deck remains readable without playback",
        },
        "review_model": {
            "source_map": "html_source_map.json",
            "validator": "reports/html_deck_validation.json",
            "patch_back_rule": "systemic visual comments should patch slide_plan/spec/renderers, not one-off DOM output",
        },
        "non_copy_policy": {
            "upstream_role": "research_evidence_only",
            "forbidden": "no copied upstream templates, CSS class systems, long prompts, or complete page designs",
            "qiaomu_owned": "stage contract, source map, manifest, and layout ids",
        },
    }


def latest_pptx(project: Path) -> Path | None:
    exports = project / "exports"
    if not exports.is_dir():
        return None
    candidates = sorted(exports.glob("*.pptx"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def artifact_mtime(path: Path) -> float:
    """Return the newest mtime for a file or package-style directory."""
    if path.is_dir():
        newest = path.stat().st_mtime
        for child in path.rglob("*"):
            try:
                newest = max(newest, child.stat().st_mtime)
            except OSError:
                continue
        return newest
    return path.stat().st_mtime


def is_fresh(output: Path, source: Path | None) -> bool:
    if not output.exists():
        return False
    if source is None or not source.exists():
        return True
    try:
        return artifact_mtime(output) >= artifact_mtime(source)
    except OSError:
        return False


def outputs_fresh(outputs: list[Path], inputs: list[Path]) -> bool:
    if not outputs or any(not output.exists() for output in outputs):
        return False
    existing_inputs = [path for path in inputs if path.exists()]
    input_mtime = max((artifact_mtime(path) for path in existing_inputs), default=0.0)
    try:
        return min(artifact_mtime(output) for output in outputs) >= input_mtime
    except OSError:
        return False


def resolve_svg_source_dir(project: Path, source: str) -> Path:
    aliases = {
        "final": "svg_final",
        "output": "svg_output",
    }
    if source == "auto":
        for name in ("svg_final", "svg_output"):
            candidate = project / name
            if candidate.is_dir() and list(candidate.glob("*.svg")):
                return candidate
        return project / "svg_output"
    return project / aliases.get(source, source)


def find_svg_files(project: Path, source: str) -> list[Path]:
    svg_dir = resolve_svg_source_dir(project, source)
    if not svg_dir.is_dir():
        return []
    return sorted(svg_dir.glob("*.svg"))


def find_preview_images(project: Path) -> list[Path]:
    preview_dir = project / "previews"
    if not preview_dir.is_dir():
        return []
    images = sorted(preview_dir.glob("slide-*.jpg"))
    if images:
        return images
    images = sorted(preview_dir.glob("slide-*.png"))
    if images:
        return images
    return sorted((preview_dir / "render").glob("page-*.png"))


def chromium_executable_candidates(playwright_obj: Any) -> list[str | None]:
    candidates: list[Path] = []
    cache_root = Path.home() / "Library/Caches/ms-playwright"
    if cache_root.exists():
        candidates.extend(
            cache_root.glob("chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell")
        )
        candidates.extend(
            cache_root.glob(
                "chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
            )
        )
    candidates.extend(
        [
            Path(playwright_obj.chromium.executable_path),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
    )
    ordered: list[str | None] = []
    seen: set[str] = set()
    for path in candidates:
        if not path.exists():
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    ordered.append(None)
    return ordered


def find_chromium_executable(playwright_obj: Any) -> str | None:
    return chromium_executable_candidates(playwright_obj)[0]


def convert_pptx_to_pdf(project: Path, pptx: Path, slug: str) -> dict[str, Any]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    output = project / "exports" / f"{slug}.pdf"
    if not pptx:
        return {"status": STATUS_MISSING, "reason": "no pptx input"}
    stale_outputs: list[str] = []
    if is_fresh(output, pptx):
        return {"status": STATUS_EXISTING, "path": rel(project, output)}
    if output.exists():
        stale_outputs.append(rel(project, output))
    preview_manifest = project / "pptx_preview_manifest.json"
    if preview_manifest.exists():
        try:
            preview = read_json(preview_manifest)
            pdf_rel = str(preview.get("pdf") or "")
            preview_pdf = project / pdf_rel
            if pdf_rel and is_fresh(preview_pdf, pptx):
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(preview_pdf, output)
                return {
                    "status": STATUS_EXPORTED,
                    "path": rel(project, output),
                    "source": rel(project, preview_pdf),
                    "tool": "existing pptx_preview_manifest PDF",
                }
            if pdf_rel and preview_pdf.exists():
                stale_outputs.append(rel(project, preview_pdf))
        except Exception:
            pass
    if not soffice:
        return {"status": STATUS_MISSING, "reason": "LibreOffice not found", "stale_outputs": stale_outputs}
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(output.parent), str(pptx)])
    produced = output.parent / f"{pptx.stem}.pdf"
    if produced.exists() and produced != output:
        if output.exists():
            output.unlink()
        produced.rename(output)
    if result.returncode != 0 or not output.exists():
        return {
            "status": STATUS_FAILED,
            "reason": "LibreOffice PDF export failed",
            "stale_outputs": stale_outputs,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }
    return {
        "status": STATUS_EXPORTED,
        "path": rel(project, output),
        "tool": soffice,
    }


def compact_html_text(value: Any, max_chars: int = 420) -> str:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if str(item).strip())
    elif isinstance(value, dict):
        value = " ".join(str(item) for item in value.values() if str(item).strip())
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "..."
    return text


def html_text_list(value: Any, max_items: int = 5, max_chars: int = 140) -> list[str]:
    if isinstance(value, list):
        raw = value
    elif isinstance(value, dict):
        raw = [f"{key}: {val}" for key, val in value.items()]
    elif str(value or "").strip():
        raw = re.split(r"\n+|[;；]\s*", str(value))
    else:
        raw = []
    items: list[str] = []
    for item in raw:
        text = compact_html_text(item, max_chars)
        if text:
            items.append(text)
        if len(items) >= max_items:
            break
    return items


def slide_visible_title(slide: dict[str, Any], idx: int) -> str:
    return str(slide.get("visible_title") or slide.get("claim_title") or slide.get("title") or f"Slide {idx}").strip()


def slide_kicker(slide: dict[str, Any], idx: int) -> str:
    for key in ("section", "chapter", "kicker"):
        value = compact_html_text(slide.get(key), 72)
        if value:
            return value
    return f"{idx:02d}"


def slide_body_copy(slide: dict[str, Any]) -> str:
    for key in ("visible_body", "visible_content", "audience_takeaway", "subtitle", "concrete_anchor", "intent"):
        value = compact_html_text(slide.get(key), 260)
        if value:
            return value
    return ""


def slide_point_items(slide: dict[str, Any]) -> list[str]:
    for key in ("visible_labels", "content_points", "points", "bullets", "evidence"):
        items = html_text_list(slide.get(key), max_items=5)
        if items:
            return items
    body = slide_body_copy(slide)
    return html_text_list(body, max_items=3, max_chars=160) if body else []


def screen_label_attr(value: str) -> str:
    return f' data-screen-label="{escape(compact_html_text(value, 110), quote=True)}"'


def render_point_list(slide_id: str, items: list[str], *, ordered: bool = False) -> str:
    if not items:
        return ""
    tag = "ol" if ordered else "ul"
    cls = "sequence-list" if ordered else "point-list"
    rendered = []
    for idx, item in enumerate(items, start=1):
        rendered.append(
            f'<li id="{escape(slide_id)}-point-{idx}"{screen_label_attr(item)}>'
            f"<span>{escape(item)}</span></li>"
        )
    return f'<{tag} class="{cls}">' + "".join(rendered) + f"</{tag}>"


def render_compare(slide_id: str, items: list[str]) -> str:
    left = items[0::2] or items[:1]
    right = items[1::2] or items[1:2] or items[:1]
    return (
        '<div class="compare-grid">'
        '<div class="compare-panel"><h3>当前判断</h3>'
        + render_point_list(f"{slide_id}-left", left[:3])
        + '</div><div class="compare-panel strong"><h3>关键变化</h3>'
        + render_point_list(f"{slide_id}-right", right[:3])
        + "</div></div>"
    )


def render_metrics(slide_id: str, items: list[str]) -> str:
    rendered: list[str] = []
    for idx, item in enumerate(items[:4], start=1):
        match = re.search(r"([+-]?\d+(?:\.\d+)?\s*(?:%|倍|x|X|万|亿|ms|s|天|页|个)?)", item)
        number = match.group(1) if match else f"{idx:02d}"
        label = item.replace(number, "", 1).strip(" ：:-") if match else item
        rendered.append(
            f'<article class="metric-card" id="{escape(slide_id)}-metric-{idx}"{screen_label_attr(item)}>'
            f'<strong>{escape(number)}</strong><span>{escape(label or item)}</span></article>'
        )
    return '<div class="metric-grid">' + "".join(rendered) + "</div>" if rendered else ""


def render_native_slide(slide: dict[str, Any], idx: int, total: int) -> str:
    slide_id = slide_stable_id(slide, idx)
    layout_id = slide_layout_id(slide)
    component_type = slide_component_type(slide)
    title_text = slide_visible_title(slide, idx)
    kicker = slide_kicker(slide, idx)
    body = slide_body_copy(slide)
    points = slide_point_items(slide)
    component_l = component_type.lower()
    layout_l = layout_id.lower()
    section_classes = ["slide", "native-slide", f"rhythm-{safe_attr_id(slide.get('rhythm') or 'body', 'body')}"]
    if idx == 1 or "hero" in component_l or "cover" in component_l:
        section_classes.append("slide-hero")
    elif idx == total or "closing" in component_l:
        section_classes.append("slide-closing")
    elif any(token in component_l + " " + layout_l for token in ("compare", "comparison", "objection")):
        section_classes.append("slide-compare")
    elif any(token in component_l + " " + layout_l for token in ("process", "roadmap", "sequence", "architecture", "mechanism")):
        section_classes.append("slide-process")
    elif any(token in component_l + " " + layout_l for token in ("chart", "kpi", "metric", "data")):
        section_classes.append("slide-metric")
    elif "quote" in component_l:
        section_classes.append("slide-quote")

    if "slide-compare" in section_classes:
        main = render_compare(slide_id, points)
    elif "slide-process" in section_classes:
        main = render_point_list(slide_id, points, ordered=True)
    elif "slide-metric" in section_classes:
        main = render_metrics(slide_id, points) or render_point_list(slide_id, points)
    elif "slide-quote" in section_classes and points:
        quote = points[0]
        main = f'<blockquote{screen_label_attr(quote)}>{escape(quote)}</blockquote>'
    else:
        main = render_point_list(slide_id, points)

    body_html = f'<p class="lead"{screen_label_attr(body)}>{escape(body)}</p>' if body else ""
    proof = compact_html_text(slide.get("concrete_anchor"), 120)
    proof_html = (
        f'<aside class="proof-card"{screen_label_attr(proof)}><b>核心依据</b><span>{escape(proof)}</span></aside>'
        if proof and proof not in body
        else ""
    )
    return f'''<section class="{" ".join(section_classes)}" id="{escape(slide_id)}" data-slide-id="{escape(slide_id)}" data-layout-id="{escape(layout_id)}" data-component-type="{escape(component_type)}" aria-label="{escape(title_text, quote=True)}">
        <div class="slide-bg" aria-hidden="true"></div>
        <header class="slide-header">
          <p class="kicker"{screen_label_attr(kicker)}>{escape(kicker)}</p>
          <h1{screen_label_attr(title_text)}>{escape(title_text)}</h1>
          {body_html}
        </header>
        <div class="slide-content">
          {main}
          {proof_html}
        </div>
      </section>'''


def render_svg_fallback_slide(svg_path: Path, idx: int) -> str:
    svg_text = svg_path.read_text(encoding="utf-8", errors="replace")
    svg_text = re.sub(r"<\?xml[^>]*>\s*", "", svg_text)
    svg_text = re.sub(r"<!DOCTYPE[^>]*>\s*", "", svg_text, flags=re.IGNORECASE)
    slide_id = f"s{idx:02d}"
    title_text = f"Slide {idx}"
    return f'''<section class="slide svg-compat-slide" id="{slide_id}" data-slide-id="{slide_id}" data-layout-id="L00" data-component-type="svg_compatibility_fallback" aria-label="{escape(title_text, quote=True)}">
        <div class="svg-layer" data-screen-label="{escape(title_text, quote=True)}" aria-hidden="false">
{svg_text}
        </div>
      </section>'''


def render_formal_html(slides: list[dict[str, Any]], svgs: list[Path], title: str) -> str:
    sections: list[str] = []
    if slides:
        total = len(slides)
        sections = [render_native_slide(slide, idx, total) for idx, slide in enumerate(slides, start=1)]
    else:
        sections = [render_svg_fallback_slide(svg_path, idx) for idx, svg_path in enumerate(svgs, start=1)]
    return f'''<!doctype html>
<html lang="zh-CN" data-qiaomu-html-deck="native-semantic-primary">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="qiaomu-reference-stage" content="1920x1080">
  <title>{escape(title)}</title>
  <style>
    :root {{ --bg: #151412; --paper: #f7f1e3; --ink: #191817; --muted: #6e695f; --red: #c43d2b; --blue: #245b9d; --green: #1f7a5a; --gold: #c18a2a; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: var(--bg); color: var(--ink); font-family: Inter, "Noto Sans SC", "PingFang SC", system-ui, sans-serif; }}
    .presentation {{ position: fixed; inset: 0; background: radial-gradient(circle at 78% 8%, rgba(193,138,42,.20), transparent 32%), linear-gradient(135deg, #161514, #22211e 64%, #111315); }}
    .stage {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: top left; overflow: hidden; background: var(--paper); box-shadow: 0 30px 90px rgba(0,0,0,.44); }}
    .slide {{ position: absolute; inset: 0; display: grid; grid-template-rows: auto 1fr; gap: 42px; padding: 92px 110px 86px; opacity: 0; transform: translateY(14px); transition: opacity .26s ease, transform .26s ease; pointer-events: none; background: var(--paper); }}
    .slide.active {{ opacity: 1; transform: translateY(0); pointer-events: auto; z-index: 2; }}
    .slide-bg {{ position: absolute; inset: 0; opacity: .8; background: linear-gradient(90deg, rgba(196,61,43,.10), transparent 34%), linear-gradient(180deg, rgba(36,91,157,.11), transparent 46%); }}
    .slide-header, .slide-content {{ position: relative; z-index: 1; }}
    .slide-header {{ max-width: 1280px; }}
    .kicker {{ margin: 0 0 24px; color: var(--red); font-size: 25px; font-weight: 800; letter-spacing: 0; }}
    h1 {{ margin: 0; color: var(--ink); font-size: 78px; line-height: 1.15; letter-spacing: 0; font-weight: 850; text-wrap: balance; }}
    .lead {{ margin: 28px 0 0; max-width: 980px; color: #34302b; font-size: 34px; line-height: 1.48; font-weight: 600; }}
    .slide-content {{ display: grid; grid-template-columns: minmax(0, 1fr) 430px; gap: 54px; align-items: end; }}
    .point-list, .sequence-list {{ margin: 0; padding: 0; list-style: none; display: grid; gap: 22px; }}
    .point-list li, .sequence-list li {{ display: grid; grid-template-columns: 18px minmax(0, 1fr); gap: 22px; align-items: start; color: #24211e; font-size: 32px; line-height: 1.45; font-weight: 650; }}
    .point-list li::before {{ content: ""; width: 12px; height: 12px; margin-top: 16px; border-radius: 50%; background: var(--blue); }}
    .sequence-list {{ counter-reset: step; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 26px; align-items: stretch; }}
    .sequence-list li {{ counter-increment: step; display: block; min-height: 250px; padding: 34px 30px; background: rgba(255,255,255,.66); border: 1px solid rgba(25,24,23,.16); border-radius: 8px; font-size: 25px; }}
    .sequence-list li::before {{ content: counter(step, decimal-leading-zero); display: block; margin-bottom: 30px; color: var(--red); font-size: 44px; line-height: 1; font-weight: 850; }}
    .proof-card {{ align-self: end; padding: 34px 34px 38px; border-radius: 8px; background: #191817; color: #f7f1e3; min-height: 220px; }}
    .proof-card b {{ display: block; margin-bottom: 18px; color: #f0b458; font-size: 22px; }}
    .proof-card span {{ display: block; font-size: 26px; line-height: 1.42; font-weight: 650; }}
    .compare-grid {{ grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1fr; gap: 34px; }}
    .compare-panel {{ padding: 42px; min-height: 410px; border-radius: 8px; background: rgba(255,255,255,.66); border: 1px solid rgba(25,24,23,.16); }}
    .compare-panel.strong {{ background: #191817; color: #f7f1e3; }}
    .compare-panel h3 {{ margin: 0 0 28px; font-size: 30px; line-height: 1.2; color: var(--red); }}
    .compare-panel.strong h3 {{ color: #f0b458; }}
    .compare-panel.strong li {{ color: #f7f1e3; }}
    .metric-grid {{ grid-column: 1 / -1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 28px; }}
    .metric-card {{ min-height: 300px; padding: 38px; border-radius: 8px; background: #191817; color: #f7f1e3; display: flex; flex-direction: column; justify-content: space-between; }}
    .metric-card strong {{ color: #f0b458; font-size: 78px; line-height: 1; font-weight: 880; }}
    .metric-card span {{ font-size: 25px; line-height: 1.38; font-weight: 650; }}
    blockquote {{ grid-column: 1 / -1; margin: 0; padding: 54px 72px; border-radius: 8px; background: #191817; color: #f7f1e3; font-size: 58px; line-height: 1.32; font-weight: 780; }}
    .slide-hero, .slide-closing {{ align-content: center; grid-template-rows: auto auto; }}
    .slide-hero h1, .slide-closing h1 {{ max-width: 1260px; font-size: 96px; line-height: 1.08; }}
    .slide-hero .slide-content, .slide-closing .slide-content {{ grid-template-columns: minmax(0, 1fr) 380px; }}
    .svg-compat-slide {{ padding: 0; display: block; }}
    .svg-layer, .svg-layer > svg {{ width: 100%; height: 100%; display: block; }}
    .progress {{ position: fixed; left: 0; bottom: 0; height: 4px; width: 0; background: var(--red); transition: width .2s ease; z-index: 10; }}
    .counter {{ position: fixed; right: 18px; bottom: 14px; z-index: 11; color: rgba(255,255,255,.72); font-size: 13px; letter-spacing: 0; }}
    @media (prefers-reduced-motion: reduce) {{ .slide {{ transition: none; }} }}
  </style>
</head>
<body>
  <main class="presentation" aria-live="polite">
    <div class="stage" data-stage="1920x1080">
      {"".join(sections)}
    </div>
  </main>
  <div class="progress" aria-hidden="true"></div>
  <div class="counter" aria-hidden="true"></div>
  <script>
    const stage = document.querySelector('.stage');
    const slides = [...document.querySelectorAll('.slide')];
    const progress = document.querySelector('.progress');
    const counter = document.querySelector('.counter');
    const STAGE_W = 1920;
    const STAGE_H = 1080;
    let index = 0;
    function fitStage() {{
      const scale = Math.min(innerWidth / STAGE_W, innerHeight / STAGE_H);
      const left = (innerWidth - STAGE_W * scale) / 2;
      const top = (innerHeight - STAGE_H * scale) / 2;
      stage.style.transform = `translate(${{left}}px, ${{top}}px) scale(${{scale}})`;
    }}
    function show(next) {{
      index = Math.max(0, Math.min(slides.length - 1, Number(next) || 0));
      slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
      progress.style.width = slides.length ? ((index + 1) / slides.length * 100) + '%' : '0';
      counter.textContent = `${{index + 1}} / ${{slides.length}}`;
      history.replaceState(null, '', `#slide-${{index + 1}}`);
    }}
    window.qiaomuShowSlide = show;
    addEventListener('resize', fitStage);
    addEventListener('keydown', event => {{
      if (['ArrowRight', ' ', 'PageDown'].includes(event.key)) show(index + 1);
      if (['ArrowLeft', 'PageUp'].includes(event.key)) show(index - 1);
      if (event.key === 'Home') show(0);
      if (event.key === 'End') show(slides.length - 1);
    }});
    addEventListener('click', event => {{ if (!event.altKey) show(index + 1); }});
    const match = location.hash.match(/slide-(\\d+)/);
    fitStage();
    show(match ? Number(match[1]) - 1 : 0);
  </script>
</body>
</html>
'''


def screenshot_html(project: Path, html_path: Path, slide_count: int, selected: list[int]) -> list[str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for HTML screenshot QA") from exc

    out_dir = project / "previews" / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    with sync_playwright() as p:
        errors: list[str] = []
        for executable in chromium_executable_candidates(p):
            launch_kwargs = {"executable_path": executable} if executable else {}
            try:
                browser = p.chromium.launch(**launch_kwargs)
            except Exception as exc:
                label = executable or "playwright-default"
                errors.append(f"{label}: {exc}")
                continue
            try:
                for viewport in ({"width": 1280, "height": 720}, {"width": 1440, "height": 900}):
                    context = browser.new_context(viewport=viewport, device_scale_factor=1)
                    page = context.new_page()
                    page.goto(html_path.resolve().as_uri(), wait_until="load")
                    page.wait_for_timeout(200)
                    for slide_no in selected:
                        if slide_no > slide_count:
                            continue
                        page.evaluate("(n) => window.qiaomuShowSlide && window.qiaomuShowSlide(n)", slide_no - 1)
                        page.wait_for_timeout(420)
                        out = out_dir / f"slide-{slide_no:02d}-{viewport['width']}x{viewport['height']}.png"
                        page.screenshot(path=str(out), full_page=False)
                        outputs.append(rel(project, out))
                    page.close()
                    context.close()
                return outputs
            finally:
                browser.close()
        raise RuntimeError("All Chromium launch candidates failed: " + " | ".join(errors))
    return outputs


def run_html_deck_validator(project: Path, html_path: Path) -> dict[str, Any]:
    reports = project / "reports"
    json_report = reports / "html_deck_validation.json"
    markdown_report = reports / "html_deck_validation.md"
    script = Path(__file__).resolve().parent / "validate_html_deck.py"
    command = [
        sys.executable,
        str(script),
        str(html_path),
        "--json",
        str(json_report),
        "--markdown",
        str(markdown_report),
    ]
    result = run(command)
    payload: dict[str, Any] = {}
    if json_report.exists():
        try:
            loaded = read_json(json_report)
            if isinstance(loaded, dict):
                payload = loaded
        except Exception:
            payload = {}
    return {
        "command": " ".join(shlex.quote(part) for part in command),
        "status": payload.get("status") or ("passed" if result.returncode == 0 else STATUS_FAILED),
        "returncode": result.returncode,
        "json": rel(project, json_report),
        "markdown": rel(project, markdown_report),
        "error_count": len(payload.get("errors") or []),
        "warning_count": len(payload.get("warnings") or []),
        "stdout": result.stdout[-1200:] if result.stdout else "",
        "stderr": result.stderr[-1200:] if result.stderr else "",
    }


def export_formal_html(project: Path, slug: str, title: str, source: str, screenshots: bool) -> dict[str, Any]:
    slides = load_slides(project)
    source_dir = resolve_svg_source_dir(project, source)
    svgs = find_svg_files(project, source)
    if not slides and not svgs:
        existing = project / "html" / "index.html"
        export_existing = project / "exports" / f"{slug}.html"
        if existing.exists() or export_existing.exists():
            return {
                "status": STATUS_EXISTING,
                "path": rel(project, existing if existing.exists() else export_existing),
                "reason": "existing formal HTML found",
            }
        return {"status": STATUS_MISSING, "reason": "no slide_plan.json slides or SVG compatibility pages found"}

    cached = cached_formal_html(project, slug, title, slides, svgs, screenshots)
    if cached:
        return cached

    html = render_formal_html(slides, svgs, title)
    html_dir = project / "html"
    exports = project / "exports"
    html_dir.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    html_path = html_dir / "index.html"
    export_path = exports / f"{slug}.html"
    html_path.write_text(html, encoding="utf-8")
    export_path.write_text(html, encoding="utf-8")

    slide_count = len(slides) if slides else len(svgs)
    render_strategy = "native_semantic_html_primary" if slides else "svg_compatibility_fallback"
    source_map = build_html_source_map(project, slides, svgs, source_dir)
    design_kernel = build_html_design_kernel(project, title, source_map)
    write_json(project / "html_source_map.json", source_map)
    write_json(project / "html_design_kernel.json", design_kernel)
    validation = run_html_deck_validator(project, html_path)

    selected = [1, max(1, slide_count // 3), max(1, slide_count * 2 // 3), slide_count]
    selected = sorted(set(selected))[:4]
    screenshots_out: list[str] = []
    screenshot_warning = ""
    if screenshots:
        try:
            screenshots_out = screenshot_html(project, html_path, slide_count, selected)
        except Exception as exc:
            screenshot_warning = str(exc)

    manifest = {
        "schema_version": "1.0.0",
        "mode": "semantic_html_deck",
        "render_strategy": render_strategy,
        "title": title,
        "slide_count": slide_count,
        "svg_source": rel(project, source_dir) if svgs else "",
        "html_design_kernel": "html_design_kernel.json",
        "html_source_map": "html_source_map.json",
        "source_contracts": existing_source_contracts(project),
        "html_outputs": [rel(project, html_path), rel(project, export_path)],
        "component_strategy": "DOM-first semantic slide sections with CSS stage and JS navigation; SVG/Canvas are optional local components, and full-page SVG is compatibility fallback only.",
        "whole_slide_screenshot_policy": "forbid whole-slide screenshot images for formal HTML; screenshots are QA evidence only.",
        "accessibility_notes": "Slide titles, body copy, and proof points are emitted as inspectable HTML text when slide_plan.json is available.",
        "point_review_policy": {
            "slide_ids": "stable data-slide-id values from html_source_map.json",
            "element_labels": "major title/body/points carry data-screen-label",
            "review_status": "needs-browser-review" if not screenshots_out else "screenshots-captured",
        },
        "asset_performance": {
            "strategy": "local assets only; native DOM export embeds no whole-slide raster screenshots",
            "preferred_formats": ["webp", "avif", "jpg", "svg"],
            "package_budget_kb": 3072,
            "image_budget_kb": 250,
            "largest_image_kb": 0,
            "package_size_mb": 0,
            "lazy_loading": "not applicable unless image slots are declared",
        },
        "slide_chrome_policy": {
            "stage": "content_only_canvas",
            "viewer_chrome": "progress and page position outside stage",
            "visible_footer": "none unless explicitly requested",
        },
        "motion_system": {
            "level": "none",
            "engines": [],
            "manifest": "",
            "reduced_motion": "prefers-reduced-motion disables slide transitions",
            "fallback": "static deck remains readable without playback",
        },
        "layout_registry": design_kernel.get("layout_registry", {}),
        "image_slot_registry": design_kernel.get("image_slot_registry", {}),
        "validation": validation,
        "readability_qa": {
            "viewports_checked": ["1280x720", "1440x900"],
            "stage_strategy": "1920x1080 fixed 16:9 coordinate stage with explicit top-left transform origin and viewport-fit scale",
            "min_body_px_at_1280_stage": 18,
            "overflow_policy": "fit stage without hidden/clipped slide content; page overflow is intentionally disabled",
            "content_parity_policy": "same slide_plan titles, anchors, and proof objects as the source contract",
            "background_decoration_budget": {
                "level": "quiet",
                "decorative_line_families_max_body": 0,
                "standalone_line_segments_max_body": 0,
                "safe_area_clearance_px_min_1280x720": 32,
            },
            "browser_screenshots": screenshots_out,
            "screenshot_warning": screenshot_warning,
        },
        "external_skill_dependency": "none",
    }
    write_json(project / "html_delivery_manifest.json", manifest)
    status = STATUS_EXPORTED if not screenshot_warning and validation.get("status") == "passed" else STATUS_FAILED
    return {
        "status": status,
        "path": rel(project, export_path),
        "index": rel(project, html_path),
        "manifest": "html_delivery_manifest.json",
        "html_design_kernel": "html_design_kernel.json",
        "html_source_map": "html_source_map.json",
        "validation": validation,
        "warning": screenshot_warning,
    }


def cached_formal_html(
    project: Path,
    slug: str,
    title: str,
    slides: list[dict[str, Any]],
    svgs: list[Path],
    screenshots: bool,
) -> dict[str, Any] | None:
    html_path = project / "html" / "index.html"
    export_path = project / "exports" / f"{slug}.html"
    manifest_path = project / "html_delivery_manifest.json"
    kernel_path = project / "html_design_kernel.json"
    source_map_path = project / "html_source_map.json"
    validation_json = project / "reports" / "html_deck_validation.json"
    validation_md = project / "reports" / "html_deck_validation.md"
    if (
        not html_path.exists()
        or not export_path.exists()
        or not manifest_path.exists()
        or not kernel_path.exists()
        or not source_map_path.exists()
        or not validation_json.exists()
    ):
        return None
    try:
        manifest = read_json(manifest_path)
    except Exception:
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("mode") != "semantic_html_deck":
        return None
    slide_count = len(slides) if slides else len(svgs)
    if manifest.get("title") != title or manifest.get("slide_count") != slide_count:
        return None
    inputs = svgs + [
        project / "slide_plan.json",
        project / "content_contract.json",
        project / "visual_contract.json",
        project / "spec_lock.json",
        Path(__file__).resolve(),
    ]
    outputs = [html_path, export_path, manifest_path, kernel_path, source_map_path, validation_json]
    if validation_md.exists():
        outputs.append(validation_md)
    readability = manifest.get("readability_qa") if isinstance(manifest.get("readability_qa"), dict) else {}
    if screenshots:
        if readability.get("screenshot_warning"):
            return None
        screenshots_out = readability.get("browser_screenshots")
        if not isinstance(screenshots_out, list) or not screenshots_out:
            return None
        outputs.extend(project / str(path) for path in screenshots_out)
        inputs.append(html_path)
    if not outputs_fresh(outputs, inputs):
        return None
    return {
        "status": STATUS_EXISTING,
        "path": rel(project, export_path),
        "index": rel(project, html_path),
        "manifest": "html_delivery_manifest.json",
        "html_design_kernel": "html_design_kernel.json",
        "html_source_map": "html_source_map.json",
        "validation": "reports/html_deck_validation.json",
        "cache": {"status": "reused", "reason": "formal HTML outputs are fresh for unchanged source contracts"},
    }


def ensure_preview_images(project: Path, pptx: Path | None) -> dict[str, Any]:
    existing = find_preview_images(project)
    if not pptx:
        return {"status": STATUS_MISSING, "reason": "no pptx input"}
    if existing and all(is_fresh(path, pptx) for path in existing):
        return {"status": STATUS_EXISTING, "count": len(existing)}
    stale_count = len(existing) if existing else 0
    try:
        from pptx_preview import build_preview
    except ImportError as exc:
        return {"status": STATUS_FAILED, "reason": f"cannot import pptx_preview: {exc}"}
    try:
        manifest = build_preview(project, pptx, project / "previews", 150)
    except SystemExit as exc:
        return {"status": STATUS_FAILED, "reason": str(exc), "stale_preview_count": stale_count}
    return {"status": STATUS_EXPORTED, "count": manifest.get("slide_count"), "manifest": "pptx_preview_manifest.json"}


def export_html_parity(project: Path, slug: str, title: str, pptx: Path | None) -> dict[str, Any]:
    preview_status = ensure_preview_images(project, pptx)
    if preview_status["status"] not in {STATUS_EXISTING, STATUS_EXPORTED}:
        return {"status": STATUS_MISSING, "reason": "preview images unavailable", "preview": preview_status}
    cached = cached_html_parity(project, slug, title)
    if cached:
        cached["preview"] = preview_status
        return cached
    try:
        from html_from_previews import build
    except ImportError as exc:
        return {"status": STATUS_FAILED, "reason": f"cannot import html_from_previews: {exc}"}
    try:
        manifest = build(project, slug, title)
    except SystemExit as exc:
        return {"status": STATUS_FAILED, "reason": str(exc), "preview": preview_status}
    outputs = manifest.get("html_outputs", [])
    return {
        "status": STATUS_EXPORTED,
        "path": outputs[-1] if outputs else "",
        "manifest": "html_parity_manifest.json",
        "preview": preview_status,
    }


def cached_html_parity(project: Path, slug: str, title: str) -> dict[str, Any] | None:
    manifest_path = project / "html_parity_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = read_json(manifest_path)
    except Exception:
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("artifact_type") != "html_parity_preview" or manifest.get("title") != title:
        return None
    outputs = [manifest_path]
    html_outputs = manifest.get("html_outputs")
    if not isinstance(html_outputs, list) or not html_outputs:
        return None
    outputs.extend(project / str(path) for path in html_outputs)
    images = find_preview_images(project)
    if not images:
        return None
    script = Path(__file__).resolve().parent / "html_from_previews.py"
    inputs = images + [project / "slide_plan.json", script, Path(__file__).resolve()]
    if not outputs_fresh(outputs, inputs):
        return None
    return {
        "status": STATUS_EXISTING,
        "path": str(html_outputs[-1]),
        "manifest": "html_parity_manifest.json",
        "cache": {"status": "reused", "reason": "parity HTML is fresh for unchanged preview images"},
    }


def apple_script_quote(value: Path) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def apple_script_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def apple_script_string_list(values: list[str]) -> str:
    return "{" + ", ".join(apple_script_string(value) for value in values) + "}"


def keynote_document_names() -> list[str]:
    if platform.system() != "Darwin" or not shutil.which("osascript"):
        return []
    result = run(["osascript", "-e", 'tell application "Keynote" to get name of documents'], timeout=15)
    if result.returncode != 0:
        return []
    text = result.stdout.strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def cleanup_keynote_documents(name_prefix: str, before_names: list[str] | None = None) -> dict[str, Any]:
    if platform.system() != "Darwin" or not shutil.which("osascript"):
        return {"status": "skipped"}
    escaped = name_prefix.replace("\\", "\\\\").replace('"', '\\"')
    before_names = before_names or []
    before_list = apple_script_string_list(before_names)
    script = f'''
tell application "Keynote"
  set beforeNames to {before_list}
  repeat with i from (count of documents) to 1 by -1
    set d to document i
    set docName to name of d
    if docName starts with "{escaped}" or beforeNames does not contain docName then
      close d saving no
    end if
  end repeat
end tell
'''
    result = run(["osascript", "-e", script], timeout=15)
    if result.returncode == 0:
        return {"status": "closed_matching_documents"}
    return {"status": STATUS_FAILED, "stderr": result.stderr[-1000:]}


def cleanup_keynote_documents_after_timeout(name_prefix: str, before_names: list[str] | None = None) -> dict[str, Any]:
    first = cleanup_keynote_documents(name_prefix, before_names)
    time.sleep(2)
    second = cleanup_keynote_documents(name_prefix, before_names)
    after_names = keynote_document_names()
    return {
        "status": second.get("status", first.get("status")),
        "first": first,
        "second": second,
        "remaining_documents": after_names,
    }


def keynote_probe_command(pptx: Path, output: Path, project: Path) -> str:
    probe = Path(__file__).resolve().parent / "keynote_probe.py"
    report = project / "reports" / f"{output.stem}.keynote-probe.json"
    return (
        f"python3 {shlex.quote(str(probe))} {shlex.quote(str(pptx.resolve()))} "
        f"--output {shlex.quote(str(output.resolve()))} --report {shlex.quote(str(report.resolve()))} "
        "--with-control"
    )


def keynote_probe_report(project: Path, output: Path) -> str:
    return rel(project, project / "reports" / f"{output.stem}.keynote-probe.json")


def existing_keynote_result(project: Path, output: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"status": STATUS_EXISTING, "path": rel(project, output)}
    manifest_path = project / "export_manifest.json"
    if not manifest_path.exists():
        return result
    try:
        manifest = read_json(manifest_path)
    except Exception:
        return result
    item = manifest.get("formats", {}).get("keynote") if isinstance(manifest, dict) else None
    if not isinstance(item, dict):
        return result
    if item.get("path") != rel(project, output):
        return result
    for key in ("tool", "compatibility_format", "fallback_from", "primary_failure"):
        if key in item:
            result[key] = item[key]
    if result.get("compatibility_format") == "Keynote 09" and result.get("fallback_from") != "save as Keynote":
        result["fallback_from"] = "save as Keynote"
        result["normalized_from_existing_manifest"] = True
    result["source"] = "existing export_manifest.json"
    return result


def normalize_preserved_formats(project: Path, formats: dict[str, Any], pptx: Path | None) -> dict[str, Any]:
    if not pptx or not pptx.exists():
        return dict(formats)
    normalized: dict[str, Any] = {}
    for name, item in formats.items():
        if not isinstance(item, dict):
            normalized[name] = item
            continue
        preserved = dict(item)
        rel_path = str(preserved.get("path") or "")
        if name in {"pdf", "html-parity", "keynote"} and preserved.get("status") in {STATUS_EXISTING, STATUS_EXPORTED} and rel_path:
            output_path = project / rel_path
            try:
                if not output_path.exists() or artifact_mtime(output_path) < artifact_mtime(pptx):
                    preserved = {
                        "status": STATUS_MISSING,
                        "reason": f"preserved {name} artifact is missing or older than current PPTX source",
                        "stale_path": rel_path,
                        "source": "normalized preserved export_manifest.json",
                    }
                    if name == "keynote":
                        preserved["diagnostic_command"] = keynote_probe_command(pptx, project / rel_path, project)
                        preserved["diagnostic_report"] = keynote_probe_report(project, project / rel_path)
            except OSError as exc:
                preserved = {
                    "status": STATUS_MISSING,
                    "reason": f"could not verify preserved {name} artifact freshness: {exc}",
                    "stale_path": rel_path,
                    "source": "normalized preserved export_manifest.json",
                }
        normalized[name] = preserved
    return normalized


def export_keynote_09_fallback(
    project: Path,
    pptx: Path,
    output: Path,
    timeout: int,
    before_docs: list[str],
    primary_failure: dict[str, Any],
    *,
    fallback_from: str = "save as Keynote",
) -> dict[str, Any]:
    if output.exists():
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    script = f'''
tell application "Keynote"
  set inputFile to POSIX file "{apple_script_quote(pptx.resolve())}"
  set outputFile to POSIX file "{apple_script_quote(output.resolve())}"
  set docRef to open inputFile
  delay 1
  export docRef to outputFile as Keynote 09
  close docRef saving no
end tell
'''
    try:
        result = run([shutil.which("osascript") or "osascript", "-e", script], timeout=max(timeout, 15))
    except subprocess.TimeoutExpired:
        cleanup = cleanup_keynote_documents_after_timeout(pptx.stem, before_docs)
        return {
            "status": STATUS_FAILED,
            "reason": f"Keynote 09 fallback export timed out after {max(timeout, 15)}s",
            "primary_failure": primary_failure,
            "cleanup": cleanup,
            "diagnostic_command": keynote_probe_command(pptx, output, project),
            "diagnostic_report": keynote_probe_report(project, output),
        }
    if result.returncode != 0 or not output.exists():
        cleanup = cleanup_keynote_documents(pptx.stem, before_docs)
        return {
            "status": STATUS_FAILED,
            "reason": "Keynote 09 fallback export failed",
            "primary_failure": primary_failure,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
            "cleanup": cleanup,
            "diagnostic_command": keynote_probe_command(pptx, output, project),
            "diagnostic_report": keynote_probe_report(project, output),
        }
    if not is_fresh(output, pptx):
        cleanup = cleanup_keynote_documents(pptx.stem, before_docs)
        return {
            "status": STATUS_FAILED,
            "reason": "Keynote 09 fallback output is older than PPTX source after export",
            "path": rel(project, output),
            "primary_failure": primary_failure,
            "cleanup": cleanup,
            "diagnostic_command": keynote_probe_command(pptx, output, project),
            "diagnostic_report": keynote_probe_report(project, output),
        }
    return {
        "status": STATUS_EXPORTED,
        "path": rel(project, output),
        "tool": "Keynote AppleScript export",
        "compatibility_format": "Keynote 09",
        "fallback_from": fallback_from,
        "primary_failure": primary_failure,
    }


def export_keynote(project: Path, pptx: Path | None, slug: str, timeout: int, *, strategy: str = "auto") -> dict[str, Any]:
    output = project / "exports" / f"{slug}.key"
    if not pptx:
        return {"status": STATUS_MISSING, "reason": "no pptx input"}
    stale_outputs: list[str] = []
    if is_fresh(output, pptx):
        return existing_keynote_result(project, output)
    if output.exists():
        stale_outputs.append(rel(project, output))
    if platform.system() != "Darwin":
        return {"status": STATUS_MISSING, "reason": "Keynote export is macOS-only", "stale_outputs": stale_outputs}
    osascript = shutil.which("osascript")
    if not osascript:
        return {"status": STATUS_MISSING, "reason": "osascript not found", "stale_outputs": stale_outputs}
    keynote_app = Path("/Applications/Keynote.app")
    if not keynote_app.exists():
        return {"status": STATUS_MISSING, "reason": "Keynote.app not found", "stale_outputs": stale_outputs}
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    before_docs = keynote_document_names()
    if strategy == "keynote09":
        primary_failure = {
            "reason": "modern Keynote save skipped by --keynote-strategy keynote09",
            "cleanup": {"status": "skipped"},
        }
        return export_keynote_09_fallback(
            project,
            pptx,
            output,
            timeout,
            before_docs,
            primary_failure,
            fallback_from="save as Keynote",
        )
    script = f'''
tell application "Keynote"
  set inputFile to POSIX file "{apple_script_quote(pptx.resolve())}"
  set outputFile to POSIX file "{apple_script_quote(output.resolve())}"
  set docRef to open inputFile
  delay 1
  save docRef in outputFile as Keynote
  close docRef saving no
end tell
'''
    try:
        result = run([osascript, "-e", script], timeout=timeout)
    except subprocess.TimeoutExpired:
        cleanup = cleanup_keynote_documents_after_timeout(pptx.stem, before_docs)
        primary_failure = {
            "reason": f"Keynote export timed out after {timeout}s",
            "cleanup": cleanup,
        }
        if strategy == "modern":
            return {
                "status": STATUS_FAILED,
                "reason": primary_failure["reason"],
                "cleanup": cleanup,
                "diagnostic_command": keynote_probe_command(pptx, output, project),
                "diagnostic_report": keynote_probe_report(project, output),
            }
        return export_keynote_09_fallback(project, pptx, output, timeout, before_docs, primary_failure)
    if result.returncode != 0 or not output.exists():
        cleanup = cleanup_keynote_documents(pptx.stem, before_docs)
        primary_failure = {
            "reason": "Keynote AppleScript export failed",
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
            "cleanup": cleanup,
        }
        if strategy == "modern":
            return {
                "status": STATUS_FAILED,
                "reason": primary_failure["reason"],
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
                "cleanup": cleanup,
                "diagnostic_command": keynote_probe_command(pptx, output, project),
                "diagnostic_report": keynote_probe_report(project, output),
            }
        return export_keynote_09_fallback(project, pptx, output, timeout, before_docs, primary_failure)
    if not is_fresh(output, pptx):
        cleanup = cleanup_keynote_documents(pptx.stem, before_docs)
        primary_failure = {
            "reason": "Keynote output is older than PPTX source after export",
            "path": rel(project, output),
            "cleanup": cleanup,
        }
        if strategy == "modern":
            return {
                "status": STATUS_FAILED,
                "reason": primary_failure["reason"],
                "path": rel(project, output),
                "cleanup": cleanup,
                "diagnostic_command": keynote_probe_command(pptx, output, project),
                "diagnostic_report": keynote_probe_report(project, output),
            }
        return export_keynote_09_fallback(project, pptx, output, timeout, before_docs, primary_failure)
    return {"status": STATUS_EXPORTED, "path": rel(project, output), "tool": "Keynote AppleScript save", "compatibility_format": "Keynote"}


def build_bundle(
    project: Path,
    formats: list[str],
    slug: str,
    title: str,
    pptx: Path | None,
    svg_source: str,
    html_screenshots: bool,
    keynote_timeout: int,
    keynote_strategy: str,
) -> dict[str, Any]:
    project = project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    (project / "exports").mkdir(parents=True, exist_ok=True)
    pptx = pptx.resolve() if pptx else latest_pptx(project)
    manifest_path = project / "export_manifest.json"
    previous_manifest: dict[str, Any] = {}
    previous_formats: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            loaded = read_json(manifest_path)
            if isinstance(loaded, dict):
                previous_manifest = loaded
                if isinstance(loaded.get("formats"), dict):
                    previous_formats = dict(loaded["formats"])
        except Exception:
            previous_manifest = {}
            previous_formats = {}
    results: dict[str, Any] = normalize_preserved_formats(project, previous_formats, pptx)
    keynote_capability = keynote_capability_report(project)
    if "pptx" in formats:
        if pptx and pptx.exists():
            results["pptx"] = {"status": STATUS_EXISTING, "path": rel(project, pptx)}
        else:
            results["pptx"] = {"status": STATUS_MISSING, "reason": "no PPTX found"}
    if "pdf" in formats:
        results["pdf"] = convert_pptx_to_pdf(project, pptx, slug) if pptx else {"status": STATUS_MISSING, "reason": "no PPTX found"}
    if "html" in formats:
        results["html"] = export_formal_html(project, slug, title, svg_source, html_screenshots)
    if "html-parity" in formats:
        results["html-parity"] = export_html_parity(project, slug, title, pptx)
    if "keynote" in formats:
        results["keynote"] = export_keynote(project, pptx, slug, keynote_timeout, strategy=keynote_strategy)

    previous_requested = previous_manifest.get("requested_formats", [])
    if not isinstance(previous_requested, list):
        previous_requested = []
    requested_formats = ordered_unique([str(item) for item in previous_requested] + formats)
    manifest = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/export_bundle.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": str(project),
        "slug": slug,
        "title": title,
        "requested_formats": requested_formats,
        "last_requested_formats": formats,
        "keynote_strategy": keynote_strategy,
        "keynote_capability": keynote_capability,
        "formats": results,
        "deliverable_policy": {
            "pptx": "editable PPTX source of truth when present",
            "pdf": "portable viewing/export artifact generated from PPTX",
            "html": "formal semantic web deck generated as native DOM from slide_plan.json; full-page SVG is compatibility fallback only",
            "html-parity": "preview-only browser parity artifact generated from rendered PPTX previews",
            "keynote": "macOS Keynote import/export artifact; failure is recorded as missing evidence or failed evidence",
        },
        "external_skill_dependency": "none",
    }
    write_json(project / "export_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a qiaomu-ppt multi-format export bundle.")
    parser.add_argument("project_dir", type=Path, help="Generated qiaomu-ppt project directory.")
    parser.add_argument("--pptx", type=Path, help="PPTX input. Defaults to newest exports/*.pptx.")
    parser.add_argument("--slug", help="Output basename. Defaults to PPTX stem or project name.")
    parser.add_argument("--title", help="HTML title. Defaults to slug.")
    parser.add_argument(
        "--formats",
        default="pptx,pdf,html,html-parity",
        help="Comma-separated formats: pptx,pdf,html,html-parity,keynote. Keynote is opt-in because it requires macOS Keynote automation.",
    )
    parser.add_argument(
        "--svg-source",
        default="auto",
        help="SVG source directory for formal HTML. Use auto, final, output, or a project-relative directory.",
    )
    parser.add_argument("--no-html-screenshots", action="store_true", help="Skip Playwright screenshots for formal HTML QA.")
    parser.add_argument("--keynote-timeout", type=int, default=90, help="AppleScript Keynote export timeout in seconds.")
    parser.add_argument(
        "--keynote-strategy",
        choices=["auto", "modern", "keynote09"],
        default="auto",
        help="Keynote export strategy. auto tries modern save then Keynote 09 fallback; keynote09 skips the slow modern save path.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any requested format is missing or failed.")
    args = parser.parse_args()

    formats = parse_formats(args.formats)
    project = args.project_dir.resolve()
    pptx = args.pptx.resolve() if args.pptx else latest_pptx(project)
    slug = args.slug or (pptx.stem if pptx else project.name)
    title = args.title or slug
    manifest = build_bundle(
        project=project,
        formats=formats,
        slug=slug,
        title=title,
        pptx=pptx,
        svg_source=args.svg_source,
        html_screenshots=not args.no_html_screenshots,
        keynote_timeout=args.keynote_timeout,
        keynote_strategy=args.keynote_strategy,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.strict:
        bad = [
            name
            for name, item in manifest.get("formats", {}).items()
            if item.get("status") in {STATUS_MISSING, STATUS_FAILED}
        ]
        if bad:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
