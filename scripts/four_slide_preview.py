#!/usr/bin/env python3
"""Generate a four-slide SVG preview package for a qiaomu-ppt project."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def slide_no(slide: dict[str, Any], index: int) -> int:
    try:
        return int(slide.get("slide_no") or slide.get("page") or index)
    except Exception:
        return index


def select_slide_numbers(slides: list[dict[str, Any]], explicit: list[int] | None = None) -> list[int]:
    total = len(slides)
    if explicit:
        selected = [num for num in explicit if 1 <= num <= total]
    else:
        selected = [1, max(2, total // 3), max(3, (total * 2) // 3), total]
    unique: list[int] = []
    for num in selected:
        if num not in unique:
            unique.append(num)
    for num in range(1, total + 1):
        if len(unique) >= min(4, total):
            break
        if num not in unique:
            unique.append(num)
    return unique[:4]


def renumber_for_preview(slide: dict[str, Any], preview_index: int, original_number: int) -> dict[str, Any]:
    item = dict(slide)
    item["original_slide_no"] = original_number
    item["slide_no"] = preview_index
    item["page"] = preview_index
    item["preview_label"] = f"source slide {original_number}"
    return item


def run(command: list[str], cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed {proc.returncode}: {' '.join(command)}\nstdout:\n{proc.stdout[-1500:]}\nstderr:\n{proc.stderr[-1500:]}"
        )
    return proc


def copy_preview_assets(project: Path, work: Path, selected: list[int]) -> None:
    assets_dir = project / "assets"
    if assets_dir.exists():
        shutil.copytree(assets_dir, work / "assets", dirs_exist_ok=True)

    manifest_path = project / "visual_asset_manifest.json"
    if not manifest_path.exists():
        return
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        return
    items = manifest.get("items")
    if not isinstance(items, list):
        return
    selected_map = {original: idx for idx, original in enumerate(selected, start=1)}
    remapped: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            original = int(item.get("slide_no"))
        except (TypeError, ValueError):
            original = 0
        if original not in selected_map:
            continue
        copied = dict(item)
        copied["original_slide_no"] = original
        copied["slide_no"] = selected_map[original]
        remapped.append(copied)
    if remapped:
        new_manifest = dict(manifest)
        new_manifest["items"] = remapped
        status_summary: dict[str, int] = {}
        for item in remapped:
            status = str(item.get("status") or "")
            status_summary[status] = status_summary.get(status, 0) + 1
        new_manifest["status_summary"] = status_summary
        write_json(work / "visual_asset_manifest.json", new_manifest)


def copy_outputs(work: Path, project: Path, selected: list[int]) -> dict[str, Any]:
    out_dir = project / "previews" / "four_slide"
    svg_out = out_dir / "svg"
    png_out = out_dir / "png"
    svg_out.mkdir(parents=True, exist_ok=True)
    png_out.mkdir(parents=True, exist_ok=True)

    copied_svgs: list[str] = []
    for idx, svg in enumerate(sorted((work / "svg_output").glob("*.svg")), start=1):
        original = selected[idx - 1] if idx - 1 < len(selected) else idx
        target = svg_out / f"preview-{idx:02d}-source-{original:02d}.svg"
        shutil.copy2(svg, target)
        copied_svgs.append(str(target.relative_to(project)))

    copied_pngs: list[str] = []
    for idx, png in enumerate(sorted((work / "previews" / "svg_output").glob("slide-*.png")), start=1):
        original = selected[idx - 1] if idx - 1 < len(selected) else idx
        target = png_out / f"preview-{idx:02d}-source-{original:02d}.png"
        shutil.copy2(png, target)
        copied_pngs.append(str(target.relative_to(project)))

    grid_src = work / "previews" / "svg_output" / "thumbnail-grid.jpg"
    grid_rel = ""
    if grid_src.exists():
        grid_target = out_dir / "thumbnail-grid.jpg"
        shutil.copy2(grid_src, grid_target)
        grid_rel = str(grid_target.relative_to(project))

    return {
        "svg_outputs": copied_svgs,
        "png_outputs": copied_pngs,
        "thumbnail_grid": grid_rel,
        "all_outputs": [*copied_pngs, grid_rel, *copied_svgs] if grid_rel else [*copied_pngs, *copied_svgs],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate four representative SVG preview slides and preview_gate.json.")
    parser.add_argument("project", type=Path, help="qiaomu-ppt project directory containing slide_plan.json")
    parser.add_argument("--plan", type=Path, help="Optional slide plan path")
    parser.add_argument("--slides", nargs="*", type=int, help="Explicit original slide numbers to preview")
    parser.add_argument("--decision", choices=["pending", "approved", "skipped"], default="pending")
    parser.add_argument("--approval-note", default="", help="Required when --decision approved or skipped")
    parser.add_argument("--force", action="store_true", help="Overwrite existing preview work/output")
    parser.add_argument("--keep-work", action="store_true", help="Keep _preview_work/four_slide")
    args = parser.parse_args()

    if args.decision in {"approved", "skipped"} and not args.approval_note.strip():
        raise SystemExit("--approval-note is required when marking preview approved or skipped")

    project = args.project.resolve()
    plan_path = args.plan.resolve() if args.plan else project / "slide_plan.json"
    slides = iter_slides(load_json(plan_path))
    if len(slides) < 4:
        raise SystemExit("four-slide preview needs at least 4 slides in slide_plan.json")
    selected = select_slide_numbers(slides, args.slides)
    selected_set = set(selected)
    selected_slides = [
        renumber_for_preview(slide, len([n for n in selected if n <= slide_no(slide, idx)]) or pos, slide_no(slide, idx))
        for idx, slide in enumerate(slides, start=1)
        for pos in [idx]
        if slide_no(slide, idx) in selected_set
    ]
    # Preserve the selected order exactly.
    slide_by_original = {slide["original_slide_no"]: slide for slide in selected_slides}
    selected_slides = [slide_by_original[num] for num in selected if num in slide_by_original]

    work = project / "_preview_work" / "four_slide"
    if work.exists():
        if not args.force:
            raise SystemExit(f"{work} exists; pass --force")
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    work_plan = {"schema_version": "1.0.0", "slides": selected_slides}
    write_json(work / "slide_plan.json", work_plan)
    copy_preview_assets(project, work, selected)

    run([sys.executable, str(SCRIPT_DIR / "svg_deck_from_slide_plan.py"), str(work), "--force"], timeout=120)
    quality_proc = run([sys.executable, str(SCRIPT_DIR / "svg_quality_checker.py"), str(work / "svg_output")], timeout=120)
    render_proc = run([sys.executable, str(SCRIPT_DIR / "svg_preview.py"), str(work), "--source", "svg_output", "--cols", "4"], timeout=180)
    copied = copy_outputs(work, project, selected)

    preview_manifest = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "tool": "qiaomu-ppt/scripts/four_slide_preview.py",
        "project": str(project),
        "source_slide_plan": str(plan_path),
        "selected_slides": selected,
        "work_dir": str(work.relative_to(project)),
        "quality_stdout": quality_proc.stdout[-2000:],
        "render_stdout": render_proc.stdout[-2000:],
        **copied,
    }
    write_json(project / "previews" / "four_slide" / "four_slide_preview_manifest.json", preview_manifest)

    gate = {
        "schema_version": "1.0.0",
        "mode": "four_slide_preview",
        "status": "generated" if args.decision == "pending" else args.decision,
        "user_decision": args.decision,
        "selected_slides": selected,
        "outputs": copied["all_outputs"],
        "qa_focus": ["typography", "background", "connector geometry", "html readability"],
        "preview_manifest": "previews/four_slide/four_slide_preview_manifest.json",
        "known_risks": [
            "Preview SVGs are generated in isolated preview work and must not be treated as the final full deck.",
            "Formal HTML/PPTX/PDF/Keynote exports still require the full generation pipeline.",
        ],
    }
    if args.decision == "approved":
        gate["approval_note"] = args.approval_note
    if args.decision == "skipped":
        gate["skipped_by_user"] = True
        gate["skip_instruction"] = args.approval_note
    write_json(project / "preview_gate.json", gate)

    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({"ok": True, "selected_slides": selected, "preview_gate": str(project / "preview_gate.json"), **copied}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
