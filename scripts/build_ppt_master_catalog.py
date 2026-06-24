#!/usr/bin/env python3
"""Build a Qiaomu-owned learning catalog from ppt-master example folders.

This is an optional research-refresh utility. It reads a local ppt-master
`examples/` snapshot and emits a compact catalog of case metadata, learning
materials, slide assets, and spec-lock vocabulary. The generated catalog is
used as Qiaomu reference data; ppt-master is not a runtime dependency.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def rel(path: Path, base: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def markdown_headings(text: str, limit: int = 24) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(2).strip())
        if len(headings) >= limit:
            break
    return headings


def spec_section(text: str, name: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(name)}\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+", text[start:], re.M)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def parse_bullet_map(section_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+([^:]+):\s*(.*?)\s*$", line)
        if match:
            result[match.group(1).strip()] = match.group(2).strip()
    return result


def parse_bullet_list(section_text: str) -> list[str]:
    values: list[str] = []
    for line in section_text.splitlines():
        match = re.match(r"^\s*-\s+(.*?)\s*$", line)
        if match:
            values.append(match.group(1).strip())
    return values


def count_files(directory: Path, suffixes: set[str] | None = None) -> int:
    if not directory.exists():
        return 0
    files = [p for p in directory.iterdir() if p.is_file()]
    if suffixes is not None:
        files = [p for p in files if p.suffix.lower() in suffixes]
    return len(files)


def sorted_files(directory: Path, suffixes: set[str] | None = None) -> list[str]:
    if not directory.exists():
        return []
    files = [p.name for p in directory.iterdir() if p.is_file()]
    if suffixes is not None:
        files = [name for name in files if Path(name).suffix.lower() in suffixes]
    return sorted(files)


def infer_learning_tags(project: dict[str, Any], charts: dict[str, str], image_count: int) -> list[str]:
    haystack = " ".join(
        str(project.get(key, ""))
        for key in ["id", "title", "description", "style", "styleName", "desc"]
    ).lower()
    tags: set[str] = set()

    if any(token in haystack for token in ["paper", "lora", "attention", "blueprint", "kubernetes", "agent"]):
        tags.add("technical-evidence")
    if any(token in haystack for token in ["bloomberg", "newspaper", "annual", "finance", "capital", "consulting"]):
        tags.add("report-and-data")
    if any(token in haystack for token in ["architecture", "pritzker", "lin_huiyin", "museum", "展陈", "建筑"]):
        tags.add("architecture-and-humanities")
    if any(token in haystack for token in ["fashion", "home", "editorial", "magazine", "showcase"]):
        tags.add("magazine-editorial")
    if any(token in haystack for token in ["zine", "risograph", "memphis", "pop"]):
        tags.add("expressive-culture")
    if any(token in haystack for token in ["liziqi", "plant", "cangzhuo", "ink", "东方", "藏拙", "李子柒"]):
        tags.add("eastern-cultural-narrative")
    if image_count >= 16:
        tags.add("image-rich")
    if len(charts) >= 6:
        tags.add("chart-rich")
    if "image_text_showcase" in haystack:
        tags.add("layout-pattern-showcase")

    return sorted(tags)


def summarize_project(project: dict[str, Any], examples_dir: Path, base: Path) -> dict[str, Any]:
    project_id = project["id"]
    folder = examples_dir / project_id
    spec_text = read_text(folder / "spec_lock.md")
    design_text = read_text(folder / "design_spec.md")

    colors = parse_bullet_map(spec_section(spec_text, "colors"))
    typography = parse_bullet_map(spec_section(spec_text, "typography"))
    page_rhythm = parse_bullet_map(spec_section(spec_text, "page_rhythm"))
    page_charts = parse_bullet_map(spec_section(spec_text, "page_charts"))
    spec_images = parse_bullet_map(spec_section(spec_text, "images"))
    icons = parse_bullet_map(spec_section(spec_text, "icons"))
    forbidden = parse_bullet_list(spec_section(spec_text, "forbidden"))

    image_dir = folder / "images"
    svg_dir = folder / "svg_final"
    exports_dir = folder / "exports"
    notes_dir = folder / "notes"

    image_count = count_files(image_dir, IMAGE_SUFFIXES)
    slide_count = len(project.get("slides") or [])
    learning_tags = infer_learning_tags(project, page_charts, image_count)

    return {
        "id": project_id,
        "title": project.get("title"),
        "description": project.get("description"),
        "style": project.get("style"),
        "style_name": project.get("styleName"),
        "tags": project.get("tags", []),
        "online_viewer": f"https://hugohe3.github.io/ppt-master/viewer.html?project={project_id}",
        "qiaomu_learning_tags": learning_tags,
        "slide_count": slide_count,
        "slide_files": [
            {
                "file": slide.get("file"),
                "title": slide.get("title"),
                "desc": slide.get("desc"),
            }
            for slide in project.get("slides", [])
        ],
        "learning_materials": {
            "readme": rel(folder / "README.md", base),
            "design_spec": rel(folder / "design_spec.md", base),
            "spec_lock": rel(folder / "spec_lock.md", base),
            "animations": rel(folder / "animations.json", base),
            "image_analysis": rel(folder / "image_analysis.csv", base),
            "svg_final_dir": rel(svg_dir, base),
            "images_dir": rel(image_dir, base),
            "exports": [rel(path, base) for path in sorted(exports_dir.glob("*")) if path.is_file()],
            "notes_dir": rel(notes_dir, base),
        },
        "asset_counts": {
            "svg_final_files": count_files(svg_dir, {".svg"}),
            "image_files": image_count,
            "export_files": count_files(exports_dir),
            "notes_files": count_files(notes_dir, {".md"}),
            "spec_image_refs": len(spec_images),
        },
        "spec_lock_summary": {
            "colors": colors,
            "image_rendering": colors.get("image_rendering"),
            "image_palette": colors.get("image_palette"),
            "typography": {
                "title_family": typography.get("title_family"),
                "body_family": typography.get("body_family"),
                "font_family": typography.get("font_family"),
                "code_family": typography.get("code_family"),
            },
            "icon_library": icons.get("library"),
            "icon_inventory_count": len([item for item in icons.get("inventory", "").split(",") if item.strip()]),
            "page_rhythm_counts": dict(Counter(page_rhythm.values())),
            "page_rhythm": page_rhythm,
            "page_chart_counts": dict(Counter(page_charts.values())),
            "page_charts": page_charts,
            "forbidden_count": len(forbidden),
            "forbidden": forbidden[:12],
        },
        "design_spec_headings": markdown_headings(design_text),
        "learnable_layers": [
            "design_spec narrative and visual rationale" if (folder / "design_spec.md").exists() else None,
            "spec_lock execution values and per-page rhythm" if (folder / "spec_lock.md").exists() else None,
            "svg_final page geometry and component composition" if svg_dir.exists() else None,
            "images and image prompt manifests" if image_dir.exists() else None,
            "speaker notes" if notes_dir.exists() else None,
            "object animation sidecar" if (folder / "animations.json").exists() else None,
        ],
    }


def build_catalog(examples_dir: Path, source_hint: str | None = None) -> dict[str, Any]:
    examples_dir = examples_dir.resolve()
    examples_json = examples_dir / "examples.json"
    if not examples_json.exists():
        raise FileNotFoundError(f"examples.json not found: {examples_json}")

    payload = json.loads(examples_json.read_text(encoding="utf-8"))
    base = examples_dir.parent
    projects = [summarize_project(project, examples_dir, base) for project in payload.get("projects", [])]
    style_counts = Counter(project.get("style_name") or "unknown" for project in projects)
    learning_tag_counts = Counter(tag for project in projects for tag in project.get("qiaomu_learning_tags", []))

    return {
        "schema_version": "1.0.0",
        "generated_at": date.today().isoformat(),
        "source": {
            "repo": "hugohe3/ppt-master",
            "examples_dir": source_hint or "research/ppt-master/examples",
            "examples_json": f"{source_hint or 'research/ppt-master/examples'}/examples.json",
            "online_gallery": "https://hugohe3.github.io/ppt-master/index.html",
            "online_examples_json": "https://hugohe3.github.io/ppt-master/examples/examples.json",
            "boundary": "Learning catalog only. Do not copy upstream templates, images, exact wording, or code into Qiaomu-generated decks.",
        },
        "upstream_stats": payload.get("stats", {}),
        "catalog_stats": {
            "projects": len(projects),
            "slides": sum(project.get("slide_count", 0) for project in projects),
            "svg_final_files": sum(project["asset_counts"]["svg_final_files"] for project in projects),
            "image_files": sum(project["asset_counts"]["image_files"] for project in projects),
            "export_files": sum(project["asset_counts"]["export_files"] for project in projects),
            "notes_files": sum(project["asset_counts"]["notes_files"] for project in projects),
            "style_counts": dict(style_counts),
            "learning_tag_counts": dict(learning_tag_counts),
        },
        "projects": projects,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build qiaomu-ppt's ppt-master example learning catalog.")
    parser.add_argument("examples_dir", type=Path, help="Local ppt-master examples directory containing examples.json.")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output catalog JSON path.")
    args = parser.parse_args()

    catalog = build_catalog(args.examples_dir, source_hint=args.examples_dir.as_posix())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output), "projects": len(catalog["projects"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
