#!/usr/bin/env python3
"""Turn deck benchmark evidence into an actionable qiaomu-ppt repair plan."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(path)


def run_benchmark(project: Path, min_score: int) -> dict[str, Any]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "deck_quality_benchmark.py"),
        str(project),
        "--output",
        str(project / "reports" / "deck_quality_benchmark.json"),
        "--markdown",
        str(project / "reports" / "deck_quality_benchmark.md"),
        "--min-score",
        str(min_score),
    ]
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    if proc.returncode not in {0, 2}:
        raise SystemExit(
            "deck_quality_benchmark.py failed before repair planning:\n"
            + (proc.stderr or proc.stdout)[-4000:]
        )
    return read_json(project / "reports" / "deck_quality_benchmark.json")


def category_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in report.get("categories", [])
        if isinstance(item, dict) and item.get("id")
    }


def add_action(
    actions: list[dict[str, Any]],
    *,
    action_id: str,
    priority: int,
    severity: str,
    category: str,
    title: str,
    reason: str,
    target_artifacts: list[str],
    steps: list[str],
    verification: list[str],
) -> None:
    actions.append(
        {
            "id": action_id,
            "priority": priority,
            "severity": severity,
            "category": category,
            "title": title,
            "reason": reason,
            "target_artifacts": target_artifacts,
            "steps": steps,
            "verification": verification,
        }
    )


def score_of(categories: dict[str, dict[str, Any]], key: str) -> int:
    try:
        return int(categories.get(key, {}).get("score") or 0)
    except Exception:
        return 0


def evidence_of(categories: dict[str, dict[str, Any]], key: str) -> str:
    return str(categories.get(key, {}).get("evidence") or "")


def build_repair_plan(project: Path, report: dict[str, Any], *, min_score: int, ready_score: int) -> dict[str, Any]:
    categories = category_map(report)
    stats = report.get("stats") if isinstance(report.get("stats"), dict) else {}
    assets = stats.get("assets") if isinstance(stats.get("assets"), dict) else {}
    sources = stats.get("sources") if isinstance(stats.get("sources"), dict) else {}
    exports = stats.get("exports") if isinstance(stats.get("exports"), dict) else {}
    rhythm = stats.get("rhythm") if isinstance(stats.get("rhythm"), dict) else {}
    layout = stats.get("layout_execution") if isinstance(stats.get("layout_execution"), dict) else {}
    image_diversity = stats.get("image_diversity") if isinstance(stats.get("image_diversity"), dict) else {}
    style_execution = stats.get("style_execution") if isinstance(stats.get("style_execution"), dict) else {}
    upstream_creation = stats.get("upstream_creation") if isinstance(stats.get("upstream_creation"), dict) else {}
    slide_count = int(report.get("slide_count") or 0)
    actions: list[dict[str, Any]] = []

    if "upstream_creation_quality" in categories and score_of(categories, "upstream_creation_quality") < 80:
        add_action(
            actions,
            action_id="repair-upstream-creation",
            priority=5,
            severity="critical",
            category="content",
            title="Repair the content outline, proof elements, and style fit before rendering",
            reason=evidence_of(categories, "upstream_creation_quality"),
            target_artifacts=[
                "sources/source_cards.json",
                "content_contract.json",
                "slide_plan.json",
                "visual_asset_manifest.json",
                "style_direction.json",
                "design_proposal.md",
            ],
            steps=[
                "Rebuild source cards until every mainline slide has a concrete source-backed claim, not a generic section label.",
                "Assign each slide a proof_object, component_plan, layout_pattern, media_need, and visual asset row before changing SVG/PPTX code.",
                "Re-run style recommendation and style_direction so the chosen style matches the content domain and defines media policy, chart policy, density targets, and per-slide layout program.",
                "Run content_outline_audit.py, element_plan_audit.py, and style_fit_audit.py before another production pass.",
            ],
            verification=[
                "python3 scripts/content_outline_audit.py <project> --enforce",
                "python3 scripts/element_plan_audit.py <project> --enforce",
                "python3 scripts/style_fit_audit.py <project> --enforce",
            ],
        )

    if score_of(categories, "source_grounding") < 80 and slide_count:
        add_action(
            actions,
            action_id="repair-source-grounding",
            priority=10,
            severity="critical",
            category="content",
            title="Add source-backed anchors to every mainline slide",
            reason=evidence_of(categories, "source_grounding"),
            target_artifacts=["sources/source_cards.json", "content_contract.json", "slide_plan.json"],
            steps=[
                "Re-run or refine source intake until source_cards.json contains concrete evidence facets, named examples, dates, numbers, quotes, mechanisms, and counterpoints.",
                "Update every mainline slide in slide_plan.json with source_card_ids and a short source_anchor; keep cover/chapter/closing slides exempt only when intentional.",
                "Rewrite generic support copy into source-specific proof objects before changing visual style.",
            ],
            verification=[
                "python3 scripts/check_project.py <project>",
                "python3 scripts/deck_quality_benchmark.py <project> --min-score "
                + str(min_score),
            ],
        )

    if score_of(categories, "source_visual_usage") < 80 and int(sources.get("image_candidates") or 0):
        add_action(
            actions,
            action_id="repair-source-visuals",
            priority=20,
            severity="critical",
            category="visual_assets",
            title="Use collected source visuals before decorative substitutes",
            reason=evidence_of(categories, "source_visual_usage"),
            target_artifacts=["visual_asset_rows.json", "visual_asset_manifest.json", "slide_plan.json"],
            steps=[
                "Map source image_candidates to slides with matching source_card_ids, media_need, figure/page/screenshot roles, ITL13/ITL14 comparisons, ITL18 annotations, or ITL20 data-context pages.",
                "Promote usable sources/images paths into visual_asset_manifest.json with acquire_via=source/web/user, terminal status, source_path/source_page provenance, and an explicit image slot.",
                "Regenerate SVG pages so evidence images are visible as source-evidence spreads, screenshot annotations, before/after panels, or chart-with-takeaway pages.",
            ],
            verification=[
                "python3 scripts/visual_asset_manifest.py validate --manifest <project>/visual_asset_manifest.json --project <project> --require-terminal",
                "python3 scripts/deck_quality_benchmark.py <project> --min-score "
                + str(min_score),
            ],
        )

    if score_of(categories, "image_presence") < 80 and slide_count >= 4:
        add_action(
            actions,
            action_id="repair-image-density",
            priority=30,
            severity="high",
            category="visual_assets",
            title="Raise image density to match image-rich reference decks",
            reason=evidence_of(categories, "image_presence"),
            target_artifacts=["visual_asset_manifest.json", "image_art_direction.json", "assets/images/image_generation_queue.json"],
            steps=[
                "For anchor/breathing/story pages, add atmosphere, chapter, concept, object, scenario, or texture assets that serve the claim.",
                "For evidence pages, prefer source/user/web images, figures, screenshots, charts, and rendered formulas over generic background art.",
                "Keep generated images text-free and layout-free; editable SVG/PPTX foreground objects own titles, cards, charts, labels, and callouts.",
            ],
            verification=[
                "python3 scripts/visual_rhythm_check.py <project> --source svg_output",
                "python3 scripts/deck_quality_benchmark.py <project> --min-score "
                + str(min_score),
            ],
        )

    if score_of(categories, "real_image_generation") < 80 and int(assets.get("ai_count") or 0):
        severity = "critical" if int(assets.get("procedural_fallback_count") or 0) else "high"
        add_action(
            actions,
            action_id="repair-real-imagegen",
            priority=40,
            severity=severity,
            category="image_generation",
            title="Replace procedural preview assets with real generated visuals",
            reason=evidence_of(categories, "real_image_generation"),
            target_artifacts=["assets/images/generation_batch/", "visual_asset_manifest.json", "assets/images/image_prompts.json"],
            steps=[
                "Stage the existing image_generation_queue into one prompt folder per asset.",
                "Generate/import real image files through Codex built-in image generation or a configured provider; keep generator, dimensions, and import time in the manifest.",
                "Do not claim final-quality visuals while generator=procedural-preview-fallback remains on used AI rows.",
            ],
            verification=[
                "python3 scripts/stage_image_generation.py <project> --force",
                "python3 scripts/check_project.py <project> --require-real-imagegen",
            ],
        )

    if score_of(categories, "image_diversity") < 80:
        add_action(
            actions,
            action_id="repair-image-diversity",
            priority=45,
            severity="high",
            category="visual_assets",
            title="Break repeated image assets in the thumbnail rhythm",
            reason=evidence_of(categories, "image_diversity"),
            target_artifacts=["visual_asset_manifest.json", "visual_asset_rows.json", "slide_plan.json", "svg_output/"],
            steps=[
                "Reassign repeated visual_asset_manifest rows so adjacent slides do not use the same exact file.",
                "Prefer unused source/user/web image candidates for evidence pages; if evidence images are limited, display repeated source images at different scale/role only when the source needs recurrence.",
                "For atmosphere or section pages, generate/import distinct image assets with different focal area, light direction, tone, or texture instead of reusing one background.",
                f"Current diversity stats: unique={image_diversity.get('unique_image_count', 0)}, adjacent_repeats={image_diversity.get('adjacent_repeat_count', 0)}, max_reuse={image_diversity.get('max_reuse_count', 0)}.",
            ],
            verification=[
                "python3 scripts/produce_deck.py <project> --quality-profile professional --formats pptx,pdf,html",
                "python3 scripts/deck_quality_benchmark.py <project> --min-score " + str(min_score),
                "Inspect <project>/previews/svg_output/thumbnail-grid.jpg for repeated exact images.",
            ],
        )

    if score_of(categories, "layout_pattern_execution") < 80:
        add_action(
            actions,
            action_id="repair-layout-execution",
            priority=50,
            severity="high",
            category="layout",
            title="Turn layout IDs into distinct executed compositions",
            reason=evidence_of(categories, "layout_pattern_execution"),
            target_artifacts=["slide_plan.json", "spec_lock.json", "visual_contract.json", "svg_output/"],
            steps=[
                "Assign every slide a concrete Lxx proof structure and, when media is important, an ITLxx image-text pattern.",
                "Write layout_execution_contract.slides with proof_object, layout_pattern_id, component_type, reading_path, coordinate_slots, and group_ids.",
                "Map repeated card grids into distinct compositions such as L13 process flow, L18 mechanism loop, L20 chart-with-takeaway, L24 concept map, L31 objection/response, L34 pull quote, or L35 closing.",
            ],
            verification=[
                "python3 scripts/svg_deck_from_slide_plan.py <project> --force",
                "python3 scripts/deck_quality_benchmark.py <project> --min-score "
                + str(min_score),
            ],
        )

    if score_of(categories, "style_execution") < 80:
        add_action(
            actions,
            action_id="repair-style-execution",
            priority=55,
            severity="high",
            category="art_direction",
            title="Make the selected visual style executable, not cosmetic",
            reason=evidence_of(categories, "style_execution"),
            target_artifacts=[
                "style_direction.json",
                "style_brief.md",
                "spec_lock.json",
                "visual_contract.json",
                "visual_asset_manifest.json",
            ],
            steps=[
                "Rebuild style_direction.json so the selected style specifies palette, typography, media policy, chart policy, density targets, and a per-slide layout program.",
                "Map the style layout program into spec_lock.json: each slide needs a concrete art_direction, component_type, rhythm, image_text_pattern_id when media exists, and coordinate slots.",
                "If the style is image-rich, add source/user/web/generated assets until terminal visual slides and source-like visual slides meet the style density targets.",
                "Regenerate SVG pages and inspect the thumbnail grid for style-specific compositions rather than repeated generic card pages.",
                "Current style audit warnings: "
                + "; ".join(str(item) for item in style_execution.get("warnings", [])[:4]),
            ],
            verification=[
                "python3 scripts/style_execution_audit.py <project> --min-score 80 --enforce",
                "python3 scripts/deck_quality_benchmark.py <project> --min-score " + str(min_score),
            ],
        )

    if score_of(categories, "visual_rhythm") < 80 or score_of(categories, "structural_variety") < 80:
        add_action(
            actions,
            action_id="repair-visual-rhythm",
            priority=60,
            severity="high",
            category="art_direction",
            title="Break repeated page rhythm and background sameness",
            reason=(
                evidence_of(categories, "visual_rhythm")
                + " | "
                + evidence_of(categories, "structural_variety")
            ).strip(" |"),
            target_artifacts=["style_brief.md", "visual_contract.json", "spec_lock.json", "reports/visual_rhythm_report.json"],
            steps=[
                "Define anchor/dense/breathing rhythm per slide; do not let adjacent slides share the same evidence composition more than twice.",
                "Use multiple background roles with visibly different tone, focal area, light direction, or surface treatment; filenames alone do not count as variety.",
                "Regenerate thumbnails and inspect the grid for repeated dashboards, rails, numbered badges, and identical card systems.",
            ],
            verification=[
                "python3 scripts/visual_rhythm_check.py <project> --source svg_output --output <project>/reports/visual_rhythm_report.json",
                "Open <project>/previews/svg_output/thumbnail-grid.jpg",
            ],
        )

    if score_of(categories, "export_coverage") < 100:
        missing = []
        for name in ("pptx", "pdf", "html", "keynote"):
            if not exports.get(f"has_{name}"):
                missing.append(name)
        add_action(
            actions,
            action_id="repair-export-coverage",
            priority=80,
            severity="medium",
            category="delivery",
            title="Complete requested multi-format delivery evidence",
            reason=evidence_of(categories, "export_coverage"),
            target_artifacts=["export_manifest.json", "exports/", "previews/"],
            steps=[
                "Run export_bundle.py after PPTX is fresh, and keep formal HTML separate from parity preview HTML.",
                "If Keynote is not feasible on this machine, run keynote_probe.py --with-control and record missing evidence instead of implying compatibility.",
                "Missing formats: " + (", ".join(missing) if missing else "none detected from benchmark stats"),
            ],
            verification=[
                "python3 scripts/export_bundle.py <project> --formats pptx,pdf,html,html-parity",
                "python3 scripts/check_project.py <project>",
            ],
        )

    if score_of(categories, "speaker_notes_and_contracts") < 100:
        add_action(
            actions,
            action_id="repair-contract-completeness",
            priority=90,
            severity="medium",
            category="contracts",
            title="Complete model contracts before another render pass",
            reason=evidence_of(categories, "speaker_notes_and_contracts"),
            target_artifacts=["content_contract.json", "visual_contract.json", "spec_lock.json", "image_art_direction.json"],
            steps=[
                "Write or repair content_contract.json, visual_contract.json, spec_lock.json, and image_art_direction.json before touching final SVG pages.",
                "Make these contracts agree on page rhythm, page layouts, image slots, color budget, title line-height policy, and visual asset IDs.",
                "Use the contracts as the source of truth for the next SVG/PPTX render.",
            ],
            verification=[
                "python3 scripts/check_project.py <project>",
                "python3 scripts/deck_quality_benchmark.py <project> --min-score "
                + str(min_score),
            ],
        )

    critical_count = sum(1 for item in actions if item["severity"] == "critical")
    high_count = sum(1 for item in actions if item["severity"] == "high")
    score = int(report.get("score") or 0)
    if not actions and score >= ready_score and report.get("ppt_master_ready"):
        status = "ready_for_human_visual_review"
    elif critical_count:
        status = "must_repair_before_final_claim"
    elif score < min_score or high_count:
        status = "repair_recommended"
    else:
        status = "production_candidate_with_minor_gaps"
    actions.sort(key=lambda item: (item["priority"], item["id"]))
    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/deck_repair_plan.py",
        "generated_at": utc_now(),
        "project": str(project),
        "benchmark": rel(project, project / "reports" / "deck_quality_benchmark.json"),
        "score": score,
        "target_score": min_score,
        "ready_score": ready_score,
        "readiness": report.get("readiness"),
        "status": status,
        "summary": {
            "action_count": len(actions),
            "critical_count": critical_count,
            "high_count": high_count,
            "slide_count": slide_count,
            "unique_art_directions": rhythm.get("unique_art_directions"),
            "component_types": layout.get("component_types", []),
            "source_cards": sources.get("source_cards"),
            "source_image_candidates": sources.get("image_candidates"),
            "terminal_image_slides": assets.get("terminal_slide_count"),
            "real_imagegen_count": assets.get("real_imagegen_count"),
            "procedural_fallback_count": assets.get("procedural_fallback_count"),
            "upstream_creation_score": upstream_creation.get("score"),
            "style_execution_score": style_execution.get("score"),
            "successful_formats": exports.get("successful_formats", []),
        },
        "actions": actions,
        "next_command": (
            "python3 scripts/produce_deck.py <project> --slug <slug> --formats pptx,pdf,html,html-parity "
            "--auto-apply-repairs --enforce-quality-benchmark --benchmark-min-score "
            + str(max(min_score, ready_score))
        ),
        "boundary": "Repair actions are Qiaomu-owned production guidance derived from benchmark evidence; do not copy upstream templates, images, or exact slide designs.",
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Deck Repair Plan",
        "",
        f"- Score: `{plan['score']}` / 100",
        f"- Target: `{plan['target_score']}`",
        f"- Ready score: `{plan['ready_score']}`",
        f"- Readiness: `{plan.get('readiness', '')}`",
        f"- Status: `{plan['status']}`",
        f"- Project: `{plan['project']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in plan.get("summary", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    actions = plan.get("actions", [])
    if actions:
        lines.extend(["", "## Actions", ""])
        for action in actions:
            lines.append(
                f"### P{action['priority']} {action['title']} "
                f"(`{action['severity']}`, `{action['category']}`)"
            )
            lines.append("")
            lines.append(f"Reason: {action['reason']}")
            lines.append("")
            lines.append("Targets: " + ", ".join(f"`{item}`" for item in action["target_artifacts"]))
            lines.append("")
            lines.append("Steps:")
            for step in action["steps"]:
                lines.append(f"- {step}")
            lines.append("")
            lines.append("Verification:")
            for check in action["verification"]:
                lines.append(f"- `{check}`")
            lines.append("")
    else:
        lines.extend(["", "No repair actions generated. Move to human visual review and final delivery checks.", ""])
    lines.extend(["## Next Command", "", f"`{plan['next_command']}`", "", f"> {plan['boundary']}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Generated qiaomu-ppt project directory.")
    parser.add_argument("--benchmark", type=Path, help="Existing deck_quality_benchmark.json. Default: <project>/reports/deck_quality_benchmark.json")
    parser.add_argument("--output", type=Path, help="JSON repair plan output. Default: <project>/reports/deck_repair_plan.json")
    parser.add_argument("--markdown", type=Path, help="Markdown repair plan output. Default: <project>/reports/deck_repair_plan.md")
    parser.add_argument("--min-score", type=int, default=70, help="Benchmark target score.")
    parser.add_argument("--ready-score", type=int, default=85, help="Score expected before claiming ppt-master-level readiness.")
    parser.add_argument("--refresh-benchmark", action="store_true", help="Run deck_quality_benchmark.py before creating the repair plan.")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit non-zero when critical repair actions exist.")
    args = parser.parse_args()

    project = args.project.resolve()
    benchmark_path = args.benchmark or project / "reports" / "deck_quality_benchmark.json"
    if args.refresh_benchmark or not benchmark_path.exists():
        report = run_benchmark(project, args.min_score)
    else:
        report = read_json(benchmark_path)
    output = args.output or project / "reports" / "deck_repair_plan.json"
    markdown = args.markdown or project / "reports" / "deck_repair_plan.md"
    plan = build_repair_plan(project, report, min_score=args.min_score, ready_score=args.ready_score)
    write_json(output, plan)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(plan), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.fail_on_critical and plan["summary"]["critical_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
