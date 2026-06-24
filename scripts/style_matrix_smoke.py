#!/usr/bin/env python3
"""Run a multi-style SVG/style-execution smoke matrix for a qiaomu-ppt project."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent

STYLE_CASES: dict[str, dict[str, Any]] = {
    "eastern": {
        "id": "pptmaster-case-eastern-culture-narrative",
        "label": "PPT Master Case: Eastern Culture Narrative",
        "behavior": "rice-paper-plant-dye-cinnabar",
        "palette": {
            "primary": "#355F6D",
            "canvas": "#F7F2E8",
            "swatches": [
                {"role": "ink", "hex": "#111827"},
                {"role": "paper", "hex": "#F7F2E8"},
                {"role": "cinnabar-red", "hex": "#B83A2F"},
                {"role": "plant-gold", "hex": "#C59B4A"},
                {"role": "mist-blue", "hex": "#A8C5C9"},
            ],
        },
    },
    "blueprint": {
        "id": "pptmaster-case-academic-blueprint",
        "label": "PPT Master Case: Academic Blueprint",
        "behavior": "blueprint-technical",
        "palette": {
            "primary": "#1A365D",
            "canvas": "#FFFFFF",
            "swatches": [
                {"role": "blueprint-ink", "hex": "#1A365D"},
                {"role": "accent-blue", "hex": "#3182CE"},
                {"role": "accent-light", "hex": "#63B3ED"},
                {"role": "paper", "hex": "#FFFFFF"},
                {"role": "blueprint-tint", "hex": "#EBF4FB"},
            ],
        },
    },
    "newsprint": {
        "id": "pptmaster-case-brutalist-newsprint",
        "label": "PPT Master Case: Brutalist Newsprint",
        "behavior": "brutalist-newsprint",
        "palette": {
            "primary": "#111111",
            "canvas": "#F5F1E8",
            "swatches": [
                {"role": "ink", "hex": "#111111"},
                {"role": "paper", "hex": "#F5F1E8"},
                {"role": "red", "hex": "#C21F1F"},
                {"role": "rule-line", "hex": "#BBB3A5"},
            ],
        },
    },
    "risograph": {
        "id": "pptmaster-case-risograph-zine",
        "label": "PPT Master Case: Risograph Zine",
        "behavior": "risograph-zine",
        "palette": {
            "primary": "#2040A0",
            "canvas": "#F7E7C5",
            "swatches": [
                {"role": "blue", "hex": "#2040A0"},
                {"role": "red", "hex": "#FF4F4F"},
                {"role": "paper", "hex": "#F7E7C5"},
                {"role": "ink", "hex": "#181818"},
            ],
        },
    },
    "luxury": {
        "id": "pptmaster-case-luxury-editorial",
        "label": "PPT Master Case: Luxury Editorial",
        "behavior": "luxury-editorial",
        "palette": {
            "primary": "#34251D",
            "canvas": "#F8F5EF",
            "swatches": [
                {"role": "ink", "hex": "#111111"},
                {"role": "paper", "hex": "#F8F5EF"},
                {"role": "gold", "hex": "#C7A96B"},
                {"role": "line", "hex": "#D7CCBC"},
            ],
        },
    },
    "magazine": {
        "id": "qiaomu-magazine-art-direction",
        "label": "Magazine Art Direction",
        "behavior": "luxury-magazine-editorial",
        "palette": {
            "primary": "#B11226",
            "canvas": "#F6F0E7",
            "swatches": [
                {"role": "ink", "hex": "#111111"},
                {"role": "paper", "hex": "#F6F0E7"},
                {"role": "editorial-red", "hex": "#B11226"},
                {"role": "champagne", "hex": "#C7A96B"},
                {"role": "muted-ink", "hex": "#5E554B"},
            ],
        },
    },
    "architecture": {
        "id": "pptmaster-case-architecture-editorial",
        "label": "PPT Master Case: Architecture Editorial",
        "behavior": "museum-catalog-editorial",
        "palette": {
            "primary": "#A4743B",
            "canvas": "#F3EFE8",
            "swatches": [
                {"role": "warm-paper", "hex": "#F3EFE8"},
                {"role": "stone", "hex": "#C8B8A6"},
                {"role": "ink", "hex": "#2C2A27"},
                {"role": "caption", "hex": "#726A60"},
                {"role": "brass-accent", "hex": "#A4743B"},
            ],
        },
    },
    "nvidia": {
        "id": "designmd-nvidia",
        "label": "NVIDIA",
        "behavior": "technical-editorial-nvidia-green",
        "palette": {
            "primary": "#76B900",
            "canvas": "#0A0A0A",
            "swatches": [
                {"role": "ink", "hex": "#0A0A0A"},
                {"role": "paper", "hex": "#FFFFFF"},
                {"role": "signal-green", "hex": "#76B900"},
                {"role": "muted", "hex": "#A7A7A7"},
                {"role": "line", "hex": "#2B2B2B"},
            ],
        },
    },
    "wired": {
        "id": "designmd-wired",
        "label": "WIRED",
        "behavior": "magazine-editorial-tech",
        "palette": {
            "primary": "#000000",
            "canvas": "#FFFFFF",
            "swatches": [
                {"role": "ink", "hex": "#000000"},
                {"role": "paper", "hex": "#FFFFFF"},
                {"role": "hairline", "hex": "#E0E0E0"},
                {"role": "body", "hex": "#757575"},
                {"role": "accent-red", "hex": "#D71920"},
            ],
        },
    },
    "verge": {
        "id": "designmd-theverge",
        "label": "The Verge",
        "behavior": "brutalist-tech-editorial",
        "palette": {
            "primary": "#3CFFD0",
            "canvas": "#131313",
            "swatches": [
                {"role": "ink", "hex": "#131313"},
                {"role": "paper", "hex": "#FFFFFF"},
                {"role": "cyan", "hex": "#3CFFD0"},
                {"role": "violet", "hex": "#5200FF"},
                {"role": "line", "hex": "#2D2D2D"},
            ],
        },
    },
    "opencode": {
        "id": "designmd-opencode.ai",
        "label": "OpenCode AI",
        "behavior": "developer-manpage-editorial",
        "palette": {
            "primary": "#201D1D",
            "canvas": "#FDFCFC",
            "swatches": [
                {"role": "ink", "hex": "#201D1D"},
                {"role": "paper", "hex": "#FDFCFC"},
                {"role": "charcoal", "hex": "#302C2C"},
                {"role": "muted", "hex": "#424245"},
                {"role": "accent", "hex": "#E15B3A"},
            ],
        },
    },
    "bento": {
        "id": "32kw-bento-23-商务科技",
        "label": "32kw Bento: 商务科技风格",
        "behavior": "bento-tech-editorial",
        "palette": {
            "primary": "#1D4ED8",
            "canvas": "#F8FAFC",
            "swatches": [
                {"role": "ink", "hex": "#0F172A"},
                {"role": "paper", "hex": "#F8FAFC"},
                {"role": "blue", "hex": "#1D4ED8"},
                {"role": "cyan", "hex": "#06B6D4"},
                {"role": "line", "hex": "#CBD5E1"},
            ],
        },
    },
}

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "exports",
    "html",
    "html-parity",
    "previews",
    "reports",
    "svg_final",
    "svg_output",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def tail(value: str, limit: int = 4000) -> str:
    return value[-limit:] if len(value) > limit else value


def ignore_names(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE_DIRS}


def run(command: list[Any], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": " ".join(str(part) for part in command),
            "status": "passed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "duration_seconds": round(time.time() - started, 2),
            "stdout_tail": tail(proc.stdout),
            "stderr_tail": tail(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(str(part) for part in command),
            "status": "failed",
            "returncode": None,
            "duration_seconds": round(time.time() - started, 2),
            "reason": f"timed out after {timeout}s",
            "stdout_tail": tail(exc.stdout or ""),
            "stderr_tail": tail(exc.stderr or ""),
        }


def mutate_style_direction(project: Path, case: dict[str, Any]) -> None:
    path = project / "style_direction.json"
    if path.exists():
        data = read_json(path)
        if not isinstance(data, dict):
            data = {}
    else:
        data = {}
    selected = data.get("selected_style") if isinstance(data.get("selected_style"), dict) else {}
    selected.update(
        {
            "id": case["id"],
            "label": case["label"],
            "library": "style_matrix_smoke",
        }
    )
    data["selected_style"] = selected
    contract = data.get("style_contract") if isinstance(data.get("style_contract"), dict) else {}
    contract["palette"] = case["palette"]
    contract.setdefault("typography", {
        "display": "Noto Serif CJK SC / IBM Plex Sans",
        "body": "Noto Sans CJK SC / Inter",
        "mono": "JetBrains Mono / Sarasa Mono SC",
        "headline_treatment": "claim-first titles with readable CJK line-height",
    })
    contract.setdefault("media_policy", "Generated images are atmosphere/concept backgrounds only; source evidence, text, charts, and diagrams stay editable foreground objects.")
    contract.setdefault("layout_rules", [
        "Preserve the locked slide_plan claim, layout_pattern_id, image_text_pattern_id, proof_object, and reading_path.",
        "Style variants may change palette/material/component language, but not the source-backed argument spine.",
        "No whole-slide screenshots as normal editable PPT output.",
    ])
    strategy = contract.get("image_asset_strategy") if isinstance(contract.get("image_asset_strategy"), dict) else {}
    strategy["image_palette_behavior"] = case["behavior"]
    contract["image_asset_strategy"] = strategy
    data["style_contract"] = contract
    data.setdefault(
        "density_targets",
        {
            "style_density": "medium",
            "target_visual_pages": 10,
            "target_source_evidence_pages": 3,
            "max_consecutive_same_layout": 2,
            "max_active_colors_per_slide": 3,
        },
    )
    plan_path = project / "slide_plan.json"
    try:
        plan = read_json(plan_path)
    except Exception:
        plan = {}
    slides = plan.get("slides") if isinstance(plan, dict) else []
    proof_map = {
        "hero_claim": "cover",
        "chart_takeaway_context": "chart",
        "mechanism_loop_flywheel": "mechanism",
        "hub_spoke_concept_map": "mechanism",
        "objection_response": "conflict",
        "stepped_process_flow": "mechanism",
        "comparison": "comparison",
        "closing_formula": "closing",
    }
    layout_program: list[dict[str, Any]] = []
    if isinstance(slides, list):
        for idx, slide in enumerate(slides, start=1):
            if not isinstance(slide, dict):
                continue
            component_plan = slide.get("component_plan") if isinstance(slide.get("component_plan"), dict) else {}
            component_type = str(component_plan.get("component_type") or "")
            proof_object = proof_map.get(component_type, str(slide.get("visual_role") or "context").split()[0].lower())
            layout_program.append(
                {
                    "slide_no": int(slide.get("slide_no") or idx),
                    "proof_object": proof_object,
                    "recommended_itl": str(slide.get("image_text_pattern_id") or ""),
                    "layout_pattern_candidates": [str(slide.get("layout_pattern_id") or slide.get("layout_pattern") or "")],
                    "component_type": component_type,
                    "style_case": case["id"],
                }
            )
    if layout_program:
        data["layout_program"] = layout_program
    write_json(path, data)


def category_score(audit: dict[str, Any], category_id: str) -> int:
    categories = audit.get("categories") if isinstance(audit.get("categories"), list) else []
    for item in categories:
        if isinstance(item, dict) and item.get("id") == category_id:
            return int(item.get("score") or 0)
    return 0


def run_case(
    base_project: Path,
    work_root: Path,
    name: str,
    case: dict[str, Any],
    timeout: int,
    min_score: int,
    *,
    render_preview: bool = False,
) -> dict[str, Any]:
    case_project = work_root / name
    shutil.copytree(base_project, case_project, ignore=ignore_names)
    mutate_style_direction(case_project, case)

    svg_step = run(
        [sys.executable, SCRIPT_DIR / "svg_deck_from_slide_plan.py", case_project, "--force"],
        cwd=case_project,
        timeout=timeout,
    )
    audit_step = run(
        [sys.executable, SCRIPT_DIR / "style_execution_audit.py", case_project, "--min-score", str(min_score), "--enforce"],
        cwd=case_project,
        timeout=timeout,
    )
    preview_step: dict[str, Any] = {"status": "skipped"}
    if render_preview:
        preview_step = run(
            [sys.executable, SCRIPT_DIR / "svg_preview.py", case_project, "--source", "svg_output", "--cols", "5"],
            cwd=case_project,
            timeout=timeout,
        )
    audit_path = case_project / "reports" / "style_execution_audit.json"
    audit: dict[str, Any] = {}
    if audit_path.exists():
        try:
            payload = read_json(audit_path)
            audit = payload if isinstance(payload, dict) else {}
        except Exception:
            audit = {}
    render_style = audit.get("stats", {}).get("render_style") if isinstance(audit.get("stats"), dict) else {}
    if not isinstance(render_style, dict):
        render_style = {}
    failures = []
    if svg_step.get("status") != "passed":
        failures.append("svg render failed")
    if audit_step.get("status") != "passed":
        failures.append("style audit failed")
    if render_preview and preview_step.get("status") != "passed":
        failures.append("svg preview failed")
    if int(audit.get("score") or 0) < min_score:
        failures.append(f"audit score below {min_score}")
    return {
        "name": name,
        "style_id": case["id"],
        "project": str(case_project),
        "ok": not failures,
        "score": int(audit.get("score") or 0),
        "render_style": render_style,
        "category_scores": {
            "render_style_token": category_score(audit, "render_style_token"),
            "style_canvas_execution": category_score(audit, "style_canvas_execution"),
            "proof_canvas_execution": category_score(audit, "proof_canvas_execution"),
            "layout_program_execution": category_score(audit, "layout_program_execution"),
        },
        "warnings": audit.get("warnings") if isinstance(audit.get("warnings"), list) else [],
        "failures": failures + (audit.get("failures") if isinstance(audit.get("failures"), list) else []),
        "steps": {
            "svg": svg_step,
            "style_audit": audit_step,
            "preview": preview_step,
        },
        "preview_grid": str(case_project / "previews" / "svg_output" / "thumbnail-grid.jpg") if (case_project / "previews" / "svg_output" / "thumbnail-grid.jpg").exists() else "",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Style Matrix Smoke",
        "",
        f"- OK: `{str(report.get('ok')).lower()}`",
        f"- Project: `{report.get('project', '')}`",
        f"- Cases: `{len(report.get('cases', []))}`",
        f"- Min score: `{report.get('min_score')}`",
        f"- Generated at: `{report.get('generated_at')}`",
        "",
        "## Cases",
        "",
    ]
    for case in report.get("cases", []):
        marker = "OK" if case.get("ok") else "FAIL"
        render_style = case.get("render_style") if isinstance(case.get("render_style"), dict) else {}
        scores = case.get("category_scores") if isinstance(case.get("category_scores"), dict) else {}
        lines.append(
            f"- {marker} `{case.get('name')}` score {case.get('score')} "
            f"material `{render_style.get('material', '')}` "
            f"component `{render_style.get('component_language', '')}` "
            f"proof `{render_style.get('proof_language', '')}` "
            f"style/proof/layout {scores.get('style_canvas_execution', 0)}/"
            f"{scores.get('proof_canvas_execution', 0)}/"
            f"{scores.get('layout_program_execution', 0)}"
        )
        if case.get("preview_grid"):
            lines.append(f"  - preview: `{case.get('preview_grid')}`")
        for failure in case.get("failures", [])[:3]:
            lines.append(f"  - {failure}")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Base qiaomu-ppt project directory.")
    parser.add_argument("--styles", default="eastern,blueprint,newsprint,risograph,luxury", help="Comma-separated style cases or 'all'.")
    parser.add_argument("--work-root", type=Path, help="Directory for generated matrix projects. Defaults to a temporary directory.")
    parser.add_argument("--keep-work", action="store_true", help="Keep the temporary matrix project copies.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per SVG/audit command in seconds.")
    parser.add_argument("--min-score", type=int, default=75, help="Minimum style audit score per case.")
    parser.add_argument("--output", type=Path, help="JSON report path. Default: <project>/reports/style_matrix_smoke.json")
    parser.add_argument("--markdown", type=Path, help="Markdown report path. Default: <project>/reports/style_matrix_smoke.md")
    parser.add_argument("--preview", action="store_true", help="Render SVG preview thumbnails for each case.")
    parser.add_argument("--enforce", action="store_true", help="Exit non-zero if any case fails.")
    args = parser.parse_args()

    project = args.project.expanduser().resolve()
    if not project.exists():
        raise SystemExit(f"project does not exist: {project}")
    if not (project / "slide_plan.json").exists():
        raise SystemExit("base project is missing slide_plan.json")

    style_names = list(STYLE_CASES) if args.styles.strip().lower() == "all" else [
        item.strip() for item in args.styles.split(",") if item.strip()
    ]
    unknown = [name for name in style_names if name not in STYLE_CASES]
    if unknown:
        raise SystemExit(f"unknown style case(s): {', '.join(unknown)}")

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if args.work_root:
        work_root = args.work_root.expanduser().resolve()
        work_root.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="qiaomu-style-matrix-")
        work_root = Path(temp_dir.name).resolve()

    cases = [
        run_case(project, work_root, name, STYLE_CASES[name], args.timeout, args.min_score, render_preview=args.preview)
        for name in style_names
    ]
    failures = [
        f"{case['name']}: " + "; ".join(case.get("failures") or ["failed"])
        for case in cases
        if not case.get("ok")
    ]
    report = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/style_matrix_smoke.py",
        "ok": not failures,
        "project": str(project),
        "work_root": str(work_root),
        "kept_work": bool(args.keep_work or args.work_root),
        "style_names": style_names,
        "min_score": args.min_score,
        "generated_at": utc_now(),
        "cases": cases,
        "failures": failures,
    }
    output = args.output or project / "reports" / "style_matrix_smoke.json"
    markdown = args.markdown or project / "reports" / "style_matrix_smoke.md"
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if temp_dir and not args.keep_work:
        temp_dir.cleanup()
    if args.enforce and failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
