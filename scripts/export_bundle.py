#!/usr/bin/env python3
"""Build a qiaomu-ppt multi-format delivery bundle.

The exporter is intentionally conservative: it records missing evidence instead
of pretending that every target format was produced. Formal HTML is generated
from inline SVG pages when available; screenshot-based browser output remains a
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


def find_chromium_executable(playwright_obj: Any) -> str | None:
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
    executable = next((path for path in candidates if path.exists()), None)
    return str(executable) if executable else None


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


def render_formal_html(slides: list[dict[str, Any]], svgs: list[Path], title: str) -> str:
    sections: list[str] = []
    for idx, svg_path in enumerate(svgs, start=1):
        svg_text = svg_path.read_text(encoding="utf-8", errors="replace")
        svg_text = re.sub(r"<\?xml[^>]*>\s*", "", svg_text)
        svg_text = re.sub(r"<!DOCTYPE[^>]*>\s*", "", svg_text, flags=re.IGNORECASE)
        slide = slides[idx - 1] if idx - 1 < len(slides) else {}
        title_text = slide_title(slide, idx)
        accessible = slide_text(slide, idx)
        sections.append(
            f'''<section class="page" aria-label="{escape(title_text)}" data-page="{idx}">
        <div class="svg-layer" aria-hidden="false">
{svg_text}
        </div>
        <div class="visually-hidden">{escape(accessible)}</div>
      </section>'''
        )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="qiaomu-reference-stage" content="1920x1080">
  <title>{escape(title)}</title>
  <style>
    :root {{ --bg: #11100e; --accent: #c8472c; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: var(--bg); color: #f8f4ea; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; }}
    .presentation {{ position: fixed; inset: 0; background: var(--bg); }}
    .stage {{ position: absolute; left: 50%; top: 50%; width: min(100vw, calc(100vh * 16 / 9)); aspect-ratio: 16 / 9; transform: translate(-50%, -50%); overflow: hidden; background: #0f1116; box-shadow: 0 24px 88px rgba(0,0,0,.42); }}
    .page {{ position: absolute; inset: 0; opacity: 0; transform: scale(.992); transition: opacity .28s ease, transform .28s ease; pointer-events: none; }}
    .page.active {{ opacity: 1; transform: scale(1); pointer-events: auto; z-index: 2; }}
    .svg-layer, .svg-layer > svg {{ width: 100%; height: 100%; display: block; }}
    .progress {{ position: fixed; left: 0; bottom: 0; height: 4px; width: 0; background: var(--accent); transition: width .2s ease; z-index: 10; }}
    .counter {{ position: fixed; right: 18px; bottom: 14px; z-index: 11; color: rgba(255,255,255,.68); font-size: 13px; letter-spacing: 0; }}
    .visually-hidden {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }}
  </style>
</head>
<body>
  <main class="presentation" aria-live="polite">
    <div class="stage">
      {"".join(sections)}
    </div>
  </main>
  <div class="progress" aria-hidden="true"></div>
  <div class="counter" aria-hidden="true"></div>
  <script>
    const pages = [...document.querySelectorAll('.page')];
    const progress = document.querySelector('.progress');
    const counter = document.querySelector('.counter');
    let index = 0;
    function show(next) {{
      index = Math.max(0, Math.min(pages.length - 1, Number(next) || 0));
      pages.forEach((page, i) => page.classList.toggle('active', i === index));
      progress.style.width = ((index + 1) / pages.length * 100) + '%';
      counter.textContent = `${{index + 1}} / ${{pages.length}}`;
      location.hash = `slide-${{index + 1}}`;
    }}
    window.qiaomuShowSlide = show;
    addEventListener('keydown', event => {{
      if (['ArrowRight', ' ', 'PageDown'].includes(event.key)) show(index + 1);
      if (['ArrowLeft', 'PageUp'].includes(event.key)) show(index - 1);
      if (event.key === 'Home') show(0);
      if (event.key === 'End') show(pages.length - 1);
    }});
    addEventListener('click', event => {{ if (!event.altKey) show(index + 1); }});
    const match = location.hash.match(/slide-(\\d+)/);
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
        executable = find_chromium_executable(p)
        launch_kwargs = {"executable_path": executable} if executable else {}
        browser = p.chromium.launch(**launch_kwargs)
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
                    page.wait_for_timeout(100)
                    out = out_dir / f"slide-{slide_no:02d}-{viewport['width']}x{viewport['height']}.png"
                    page.screenshot(path=str(out), full_page=False)
                    outputs.append(rel(project, out))
                page.close()
                context.close()
        finally:
            browser.close()
    return outputs


def export_formal_html(project: Path, slug: str, title: str, source: str, screenshots: bool) -> dict[str, Any]:
    slides = load_slides(project)
    source_dir = resolve_svg_source_dir(project, source)
    svgs = find_svg_files(project, source)
    if not svgs:
        existing = project / "html" / "index.html"
        export_existing = project / "exports" / f"{slug}.html"
        if existing.exists() or export_existing.exists():
            return {
                "status": STATUS_EXISTING,
                "path": rel(project, existing if existing.exists() else export_existing),
                "reason": "existing formal HTML found",
            }
        return {"status": STATUS_MISSING, "reason": f"no SVG pages found under {rel(project, source_dir)}/"}

    html = render_formal_html(slides, svgs, title)
    html_dir = project / "html"
    exports = project / "exports"
    html_dir.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    html_path = html_dir / "index.html"
    export_path = exports / f"{slug}.html"
    html_path.write_text(html, encoding="utf-8")
    export_path.write_text(html, encoding="utf-8")

    selected = [1, max(1, len(svgs) // 3), max(1, len(svgs) * 2 // 3), len(svgs)]
    selected = sorted(set(selected))[:4]
    screenshots_out: list[str] = []
    screenshot_warning = ""
    if screenshots:
        try:
            screenshots_out = screenshot_html(project, html_path, len(svgs), selected)
        except Exception as exc:
            screenshot_warning = str(exc)

    manifest = {
        "schema_version": "1.0.0",
        "mode": "semantic_html_deck",
        "slide_count": len(svgs),
        "svg_source": rel(project, source_dir),
        "source_contracts": [
            path
            for path in ("slide_plan.json", "content_contract.json", "visual_contract.json", "spec_lock.json")
            if (project / path).exists()
        ],
        "html_outputs": [rel(project, html_path), rel(project, export_path)],
        "component_strategy": "DOM navigation plus inline SVG slide components; visible layer is not rendered slide screenshots.",
        "whole_slide_screenshot_policy": "forbid whole-slide screenshot images for formal HTML; screenshots are QA evidence only.",
        "accessibility_notes": "Slide titles and source anchors are mirrored into hidden accessible text; SVG text remains in the DOM where supported.",
        "readability_qa": {
            "viewports_checked": ["1280x720", "1440x900"],
            "stage_strategy": "fixed 16:9 aspect stage, centered with explicit absolute position and scaled by viewport fit",
            "min_body_px_at_1280_stage": 18,
            "overflow_policy": "fit stage without hidden/clipped slide content; page overflow is intentionally disabled",
            "content_parity_policy": "same slide_plan titles, anchors, and proof objects as the PPTX/SVG source",
            "browser_screenshots": screenshots_out,
            "screenshot_warning": screenshot_warning,
        },
        "external_skill_dependency": "none",
    }
    write_json(project / "html_delivery_manifest.json", manifest)
    status = STATUS_EXPORTED if not screenshot_warning else STATUS_FAILED
    return {
        "status": status,
        "path": rel(project, export_path),
        "index": rel(project, html_path),
        "manifest": "html_delivery_manifest.json",
        "warning": screenshot_warning,
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
            "html": "formal semantic web deck generated from inline SVG when SVG pages exist",
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
