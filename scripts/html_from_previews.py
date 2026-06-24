#!/usr/bin/env python3
"""Build a browser QA preview from rendered slide previews for PPTX parity.

This script intentionally creates preview-only HTML. It must not overwrite the
formal semantic HTML deck at html/index.html or exports/<slug>.html.
"""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, dict):
        value = plan.get("slides") or plan.get("slide_plan") or plan.get("pages")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(plan, list):
        return [item for item in plan if isinstance(item, dict)]
    return []


def slide_preview_paths(root: Path) -> list[Path]:
    candidates = sorted((root / "previews").glob("slide-*.jpg"))
    if candidates:
        return candidates
    candidates = sorted((root / "previews").glob("slide-*.png"))
    if candidates:
        return candidates
    candidates = sorted((root / "previews" / "render").glob("page-*.jpg"))
    if candidates:
        return candidates
    return sorted((root / "previews" / "render").glob("page-*.png"))


def image_rel(path: Path) -> str:
    return "../" + path.as_posix()


def slide_text(slide: dict[str, Any]) -> str:
    parts = [str(slide.get("title") or slide.get("claim_title") or "").strip()]
    subtitle = str(slide.get("subtitle") or "").strip()
    if subtitle:
        parts.append(subtitle)
    bullets = slide.get("bullets")
    if isinstance(bullets, list):
        parts.extend(str(item).strip() for item in bullets if str(item).strip())
    source_fact = str(slide.get("source_fact") or slide.get("concrete_anchor") or "").strip()
    if source_fact:
        parts.append(source_fact)
    return " ".join(part for part in parts if part)


def render_html(slides: list[dict[str, Any]], images: list[Path], title: str) -> str:
    sections: list[str] = []
    for idx, image in enumerate(images, start=1):
        slide = slides[idx - 1] if idx - 1 < len(slides) else {"title": f"第 {idx} 页"}
        title_text = str(slide.get("title") or slide.get("claim_title") or f"第 {idx} 页").strip()
        accessible = slide_text(slide)
        sections.append(
            f'''<section class="slide" aria-label="{escape(title_text)}" data-page="{idx}">
        <img src="{escape(image_rel(image))}" alt="{escape(title_text)}">
        <div class="visually-hidden">{escape(accessible)}</div>
      </section>'''
        )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ --stage-w: 1920; --stage-h: 1080; --accent: #D26A2C; --bg: #11100E; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 100%; height: 100%; background: var(--bg); color: #fff; font-family: Inter, "Noto Sans SC", system-ui, sans-serif; overflow: hidden; }}
    .presentation {{ position: fixed; inset: 0; display: grid; place-items: center; background: #11100E; }}
    .stage {{ width: min(100vw, calc(100vh * 16 / 9)); aspect-ratio: 16 / 9; position: relative; overflow: hidden; box-shadow: 0 24px 80px rgba(0,0,0,.42); background: #11100E; }}
    .slide {{ position: absolute; inset: 0; opacity: 0; transform: scale(.992); transition: opacity .36s ease, transform .36s ease; pointer-events: none; }}
    .slide.active {{ opacity: 1; transform: scale(1); pointer-events: auto; z-index: 2; }}
    .slide img {{ display: block; width: 100%; height: 100%; object-fit: contain; background: #11100E; }}
    .progress {{ position: fixed; left: 0; bottom: 0; height: 4px; background: var(--accent); width: 0; z-index: 10; transition: width .25s ease; }}
    .counter {{ position: fixed; right: 18px; bottom: 14px; z-index: 11; color: rgba(255,255,255,.72); font-size: 13px; letter-spacing: 0; }}
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
    const pages = [...document.querySelectorAll('.slide')];
    const progress = document.querySelector('.progress');
    const counter = document.querySelector('.counter');
    let index = 0;
    function show(next) {{
      index = Math.max(0, Math.min(pages.length - 1, next));
      pages.forEach((page, i) => page.classList.toggle('active', i === index));
      progress.style.width = ((index + 1) / pages.length * 100) + '%';
      counter.textContent = `${{index + 1}} / ${{pages.length}}`;
    }}
    addEventListener('keydown', event => {{
      if (['ArrowRight', ' ', 'PageDown'].includes(event.key)) show(index + 1);
      if (['ArrowLeft', 'PageUp'].includes(event.key)) show(index - 1);
      if (event.key === 'Home') show(0);
      if (event.key === 'End') show(pages.length - 1);
    }});
    addEventListener('click', event => {{ if (!event.altKey) show(index + 1); }});
    show(0);
  </script>
</body>
</html>
'''


def build(root: Path, slug: str, title: str) -> dict[str, Any]:
    root = root.resolve()
    plan_path = root / "slide_plan.json"
    slides = iter_slides(load_json(plan_path)) if plan_path.exists() else []
    images = [path.relative_to(root) for path in slide_preview_paths(root)]
    if not images:
        raise SystemExit("no slide preview images found under previews/")

    html = render_html(slides, images, title)
    html_dir = root / "html-parity"
    export_dir = root / "exports"
    html_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    html_path = html_dir / "index.html"
    export_path = export_dir / f"{slug}.parity.html"
    html_path.write_text(html, encoding="utf-8")
    export_path.write_text(html, encoding="utf-8")

    manifest = {
        "mode": "rendered_slide_parity",
        "artifact_type": "html_parity_preview",
        "slide_count": len(images),
        "slide_plan_count": len(slides),
        "html_outputs": [str(html_path.relative_to(root)), str(export_path.relative_to(root))],
        "preview_images": [str(path) for path in images],
        "policy": "Preview-only HTML uses rendered slide previews as the visual layer so browser output matches the PPTX preview; it is not the formal semantic HTML deck.",
        "formal_html_policy": "Do not report this artifact as the HTML version. Formal HTML must be generated as semantic DOM/SVG/Canvas/CSS/JS and recorded in html_delivery_manifest.json.",
    }
    (root / "html_parity_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a preview-only PPTX-parity HTML artifact from rendered slide previews.")
    parser.add_argument("project_dir", help="Generated qiaomu-ppt project directory.")
    parser.add_argument("--slug", required=True, help="Output HTML basename without extension.")
    parser.add_argument("--title", required=True, help="Browser title.")
    args = parser.parse_args()
    manifest = build(Path(args.project_dir), args.slug, args.title)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
