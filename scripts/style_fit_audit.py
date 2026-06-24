#!/usr/bin/env python3
"""Audit whether the selected visual style fits the content and source material."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DOMAIN_RULES = [
    {
        "id": "academic_paper",
        "triggers": ["论文", "paper", "arxiv", "hugging face", "transformer", "模型", "实验"],
        "style_tokens": ["paper", "academic", "blueprint", "research", "technical", "formula"],
    },
    {
        "id": "chinese_culture",
        "triggers": ["蒲松龄", "聊斋", "中国文化", "古典", "文学", "非遗", "传统", "东方", "历史"],
        "style_tokens": ["eastern", "culture", "heritage", "editorial", "ink", "paper", "museum"],
    },
    {
        "id": "business_strategy",
        "triggers": ["战略", "咨询", "商业", "市场", "增长", "复盘", "报告", "客户", "finance"],
        "style_tokens": ["consulting", "strategy", "data", "report", "editorial", "finance", "minimal"],
    },
    {
        "id": "image_zine",
        "triggers": ["zine", "独立书店", "画册", "影像", "摄影", "杂志", "视觉"],
        "style_tokens": ["zine", "risograph", "editorial", "magazine", "collage", "photo"],
    },
    {
        "id": "product_launch",
        "triggers": ["发布会", "产品", "品牌", "launch", "app", "saas", "agent"],
        "style_tokens": ["launch", "product", "cinematic", "brand", "technical", "glass"],
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_slides(payload: Any) -> list[dict[str, Any]]:
    slides = payload.get("slides") if isinstance(payload, dict) else payload
    return [item for item in slides if isinstance(item, dict)] if isinstance(slides, list) else []


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def collect_brief_text(project: Path, slides: list[dict[str, Any]], content: dict[str, Any]) -> str:
    pieces = [
        norm(content.get("topic_angle")),
        norm(content.get("purpose")),
        norm(content.get("audience")),
        norm(content.get("desired_action")),
    ]
    for path in (project / "deck_brief.md", project / "design_proposal.md"):
        if path.exists():
            pieces.append(path.read_text(encoding="utf-8", errors="replace")[:4000])
    for slide in slides:
        pieces.append(norm(slide.get("claim_title") or slide.get("title")))
        pieces.append(norm(slide.get("concrete_anchor")))
    return "\n".join(pieces).lower()


def style_text(style_direction: dict[str, Any]) -> str:
    selected = style_direction.get("selected_style") if isinstance(style_direction.get("selected_style"), dict) else {}
    contract = style_direction.get("style_contract") if isinstance(style_direction.get("style_contract"), dict) else {}
    return json.dumps({"selected_style": selected, "style_contract": contract}, ensure_ascii=False).lower()


def matched_domain(brief: str, style: str) -> dict[str, Any]:
    matches = []
    for rule in DOMAIN_RULES:
        trigger_hits = [token for token in rule["triggers"] if token.lower() in brief]
        if not trigger_hits:
            continue
        style_hits = [token for token in rule["style_tokens"] if token.lower() in style]
        matches.append(
            {
                "id": rule["id"],
                "trigger_hits": trigger_hits,
                "style_hits": style_hits,
                "ok": bool(style_hits),
            }
        )
    if not matches:
        return {"domain_required": False, "matches": [], "ok": True}
    ok = any(item["ok"] for item in matches)
    return {"domain_required": True, "matches": matches, "ok": ok}


def asset_counts(project: Path) -> dict[str, int]:
    path = project / "visual_asset_manifest.json"
    counts = {"source": 0, "web": 0, "user": 0, "ai": 0, "formula": 0, "placeholder": 0}
    if not path.exists():
        return counts
    try:
        payload = read_json(path)
    except Exception:
        return counts
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return counts
    for item in items:
        if not isinstance(item, dict):
            continue
        via = norm(item.get("acquire_via")).lower()
        if via in counts:
            counts[via] += 1
    return counts


def score_project(project: Path, min_score: int) -> dict[str, Any]:
    project = project.resolve()
    slide_plan_path = project / "slide_plan.json"
    style_path = project / "style_direction.json"
    content_path = project / "content_contract.json"
    if not slide_plan_path.exists():
        raise SystemExit(f"slide_plan.json missing: {slide_plan_path}")
    slides = iter_slides(read_json(slide_plan_path))
    style_direction = read_json(style_path) if style_path.exists() else {}
    content = read_json(content_path) if content_path.exists() else {}
    style_contract = style_direction.get("style_contract") if isinstance(style_direction.get("style_contract"), dict) else {}
    density = style_direction.get("density_targets") if isinstance(style_direction.get("density_targets"), dict) else {}
    layout_program = style_direction.get("layout_program") if isinstance(style_direction.get("layout_program"), list) else []
    non_negotiables = style_direction.get("non_negotiables") if isinstance(style_direction.get("non_negotiables"), list) else []
    selected = style_direction.get("selected_style") if isinstance(style_direction.get("selected_style"), dict) else {}
    failures: list[str] = []
    warnings: list[str] = []
    brief = collect_brief_text(project, slides, content if isinstance(content, dict) else {})
    style_blob = style_text(style_direction if isinstance(style_direction, dict) else {})
    domain = matched_domain(brief, style_blob)
    counts = asset_counts(project)

    required_style_fields = ["palette", "typography", "media_policy", "chart_policy"]
    present_style_fields = sum(1 for field in required_style_fields if style_contract.get(field))
    selected_score = 1.0 if selected.get("id") and selected.get("label") else 0.0
    density_fields = ["target_visual_pages", "target_source_evidence_pages", "max_consecutive_same_layout", "max_active_colors_per_slide"]
    density_score = ratio(sum(1 for field in density_fields if field in density), len(density_fields))
    layout_score = ratio(len(layout_program), len(slides))
    domain_score = 1.0 if domain["ok"] else 0.0
    media_policy = norm(style_contract.get("media_policy")).lower()
    source_first_ok = (
        not any(token in media_policy for token in ["source", "evidence", "figures", "artifact", "screenshot"])
        or counts["source"] + counts["web"] + counts["user"] > 0
    )
    generated_policy_ok = bool(non_negotiables) and any("generated" in norm(item).lower() or "生成" in norm(item) for item in non_negotiables)

    categories = [
        {
            "id": "selected_style_identity",
            "weight": 14,
            "score": pct(selected_score),
            "evidence": f"selected style `{selected.get('id', '')}` / `{selected.get('label', '')}`",
        },
        {
            "id": "domain_style_fit",
            "weight": 22,
            "score": pct(domain_score),
            "evidence": json.dumps(domain["matches"][:3], ensure_ascii=False),
        },
        {
            "id": "style_contract_completeness",
            "weight": 20,
            "score": pct(ratio(present_style_fields, len(required_style_fields))),
            "evidence": f"{present_style_fields}/{len(required_style_fields)} style contract fields",
        },
        {
            "id": "density_targets",
            "weight": 14,
            "score": pct(density_score),
            "evidence": f"{sum(1 for field in density_fields if field in density)}/{len(density_fields)} density targets",
        },
        {
            "id": "slide_level_layout_program",
            "weight": 16,
            "score": pct(layout_score),
            "evidence": f"{len(layout_program)}/{len(slides)} style layout-program rows",
        },
        {
            "id": "media_policy_alignment",
            "weight": 8,
            "score": pct(1.0 if source_first_ok else 0.0),
            "evidence": f"assets {counts}; media_policy={media_policy[:140]}",
        },
        {
            "id": "generation_boundaries",
            "weight": 6,
            "score": pct(1.0 if generated_policy_ok else 0.0),
            "evidence": f"{len(non_negotiables)} non-negotiables; generated-image boundary present={generated_policy_ok}",
        },
    ]
    total_weight = sum(int(item["weight"]) for item in categories)
    score = round(sum(int(item["score"]) * int(item["weight"]) for item in categories) / total_weight)
    if score < min_score:
        failures.append(f"style fit score {score} below target {min_score}")
    if domain["domain_required"] and not domain["ok"]:
        failures.append("selected style does not match detected content domain")
    if not source_first_ok:
        warnings.append("style media policy expects source/evidence visuals but asset plan has none")
    if layout_score < 1:
        warnings.append("style layout program does not cover every slide")

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/style_fit_audit.py",
        "generated_at": utc_now(),
        "project": str(project),
        "ok": not failures,
        "score": score,
        "target_score": min_score,
        "selected_style": selected,
        "domain_fit": domain,
        "asset_counts": counts,
        "categories": categories,
        "failures": failures,
        "warnings": warnings,
        "boundary": "This gate checks whether style selection serves content, source material, and element planning before rendering.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    style = report.get("selected_style", {})
    lines = [
        "# Style Fit Audit",
        "",
        f"- OK: `{str(report['ok']).lower()}`",
        f"- Score: `{report['score']}` / 100",
        f"- Target: `{report['target_score']}`",
        f"- Selected style: `{style.get('id', '')}`",
        "",
        "## Categories",
        "",
    ]
    for item in report["categories"]:
        lines.append(f"- `{item['id']}`: {item['score']} ({item['evidence']})")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    lines.extend(["", f"> {report['boundary']}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--min-score", type=int, default=75)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    project = args.project.resolve()
    report = score_project(project, args.min_score)
    output = args.output or project / "reports" / "style_fit_audit.json"
    markdown = args.markdown or project / "reports" / "style_fit_audit.md"
    write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.enforce and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
