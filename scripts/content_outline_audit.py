#!/usr/bin/env python3
"""Audit upstream content outline quality before visual production."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WEAK_LABELS = {
    "agenda",
    "overview",
    "background",
    "problem",
    "solution",
    "summary",
    "conclusion",
    "目录",
    "概览",
    "背景",
    "问题",
    "方案",
    "总结",
    "结论",
}
GENERIC_PHRASES = {
    "提升效率",
    "理解用户",
    "形成闭环",
    "赋能",
    "创新发展",
    "价值提升",
    "多维度",
    "系统性",
    "持续创作",
    "作品和选择",
    "核心价值",
    "关键路径",
    "重要意义",
    "深度解读",
    "全面了解",
    "重新理解",
    "带来启发",
    "值得关注",
}
MAINLINE_SKIP_TOKENS = {"cover", "closing", "chapter", "section", "divider", "封面", "结尾", "章节", "分隔"}
SOURCE_ID_ONLY_RE = re.compile(r"^(?:S|SC|SRC)[-_][A-Z0-9_-]+(?:\s*[/,;；]\s*(?:S|SC|SRC)[-_][A-Z0-9_-]+)*$", re.I)
CARD_ID_RE = re.compile(r"^(?:S|SC|SRC)[-_][A-Z0-9_-]+$", re.I)


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


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def compact_key(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value.lower())


def pct(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 100))


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def normalize_id_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def is_mainline(slide: dict[str, Any]) -> bool:
    haystack = " ".join(
        norm(slide.get(key)).lower()
        for key in ("visual_role", "intent", "proof_object", "layout_pattern")
    )
    return not any(token in haystack for token in MAINLINE_SKIP_TOKENS)


def load_source_stats(project: Path) -> dict[str, Any]:
    path = project / "sources" / "source_cards.json"
    stats = {
        "source_card_count": 0,
        "source_card_ids": [],
        "weak_source_card_count": 0,
        "image_candidate_count": 0,
        "source_count": 0,
        "missing_evidence_count": 0,
        "source_types": [],
    }
    if not path.exists():
        return stats
    try:
        payload = read_json(path)
    except Exception:
        return stats
    cards = payload.get("cards") if isinstance(payload, dict) else payload
    stats["source_card_count"] = len(cards) if isinstance(cards, list) else 0
    if isinstance(cards, list):
        card_ids: list[str] = []
        weak_cards = 0
        for idx, card in enumerate(cards, start=1):
            if not isinstance(card, dict):
                weak_cards += 1
                continue
            card_id = norm(card.get("id") or card.get("source_card_id") or f"card-{idx}")
            if card_id:
                card_ids.append(card_id)
            claim = norm(card.get("claim") or card.get("title"))
            evidence = norm(card.get("evidence") or " ".join(str(item) for item in card.get("facts", []) if item) if isinstance(card.get("facts"), list) else card.get("evidence"))
            combined = f"{claim} {evidence}"
            if len(combined) < 36 or any(phrase in combined for phrase in GENERIC_PHRASES):
                weak_cards += 1
        stats["source_card_ids"] = card_ids
        stats["weak_source_card_count"] = weak_cards
    candidates = payload.get("image_candidates") if isinstance(payload, dict) else []
    stats["image_candidate_count"] = len(candidates) if isinstance(candidates, list) else 0
    coverage = payload.get("source_coverage") if isinstance(payload, dict) else []
    if isinstance(coverage, list):
        stats["source_count"] = len(coverage)
        source_types: set[str] = set()
        missing = 0
        for item in coverage:
            if not isinstance(item, dict):
                continue
            if item.get("source_type"):
                source_types.add(str(item["source_type"]))
            raw_missing = item.get("missing_evidence")
            if isinstance(raw_missing, list):
                missing += len(raw_missing)
        stats["source_types"] = sorted(source_types)
        stats["missing_evidence_count"] = missing
    return stats


def score_project(project: Path, min_score: int) -> dict[str, Any]:
    project = project.resolve()
    failures: list[str] = []
    warnings: list[str] = []
    slide_plan_path = project / "slide_plan.json"
    content_path = project / "content_contract.json"
    if not slide_plan_path.exists():
        raise SystemExit(f"slide_plan.json missing: {slide_plan_path}")
    slides = iter_slides(read_json(slide_plan_path))
    content = read_json(content_path) if content_path.exists() else {}
    mainline = [slide for slide in slides if is_mainline(slide)] or slides
    source_stats = load_source_stats(project)

    sourced = 0
    strong_sourced = 0
    anchored = 0
    specific = 0
    weak_titles: list[str] = []
    duplicate_titles: list[str] = []
    generic_slides: list[int] = []
    hollow_anchor_slides: list[int] = []
    source_id_usage: Counter[str] = Counter()
    seen_titles: set[str] = set()
    for slide in slides:
        title = norm(slide.get("claim_title") or slide.get("title"))
        key = compact_key(title)
        if key in seen_titles and title:
            duplicate_titles.append(title)
        seen_titles.add(key)
        if title.lower() in WEAK_LABELS or title in WEAK_LABELS or len(title) < 6:
            weak_titles.append(title or f"slide {slide.get('slide_no')}")
        points = " ".join(norm(item) for item in slide.get("content_points", []) if item)
        if any(phrase in title + points for phrase in GENERIC_PHRASES):
            generic_slides.append(int(slide.get("slide_no") or 0))
    for slide in mainline:
        ids = normalize_id_list(slide.get("source_card_ids") or slide.get("source_ids"))
        source_id_usage.update(ids)
        if ids:
            sourced += 1
            if not (len(ids) == 1 and CARD_ID_RE.match(ids[0]) and ids[0].lower().endswith(("bio", "overview", "summary", "general"))):
                strong_sourced += 1
        anchor = norm(slide.get("source_anchor") or slide.get("concrete_anchor"))
        id_only_anchor = bool(SOURCE_ID_ONLY_RE.match(anchor.replace(" ", ""))) or bool(
            anchor and all(CARD_ID_RE.match(part.strip()) for part in re.split(r"[/,;；]", anchor) if part.strip())
        )
        if anchor and not id_only_anchor:
            anchored += 1
        elif id_only_anchor:
            hollow_anchor_slides.append(int(slide.get("slide_no") or 0))
        has_specific_anchor = bool(
            len(anchor) >= 18
            and not id_only_anchor
            and (
                re.search(r"\d", anchor)
                or re.search(r"《[^》]{2,40}》", anchor)
                or re.search(r"「[^」]{2,40}」", anchor)
                or re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", anchor)
                or has_cjk(anchor)
            )
        )
        if has_specific_anchor:
            specific += 1

    contract_fields = [
        "audience",
        "purpose",
        "desired_action",
        "current_state",
        "desired_state",
        "stakes",
        "structure_framework",
        "title_policy",
        "evidence_policy",
        "slide_claims",
    ]
    contract_present = sum(1 for field in contract_fields if content.get(field))
    slide_claims = content.get("slide_claims") if isinstance(content, dict) else []
    source_cards_target = max(3, min(len(slides), round(len(slides) * 0.6)))
    unique_source_ids = len(source_id_usage)
    unique_source_target = max(3, min(source_stats["source_card_count"], round(len(mainline) * 0.45)))
    max_source_reuse = max(source_id_usage.values()) if source_id_usage else 0
    reuse_limit = max(3, round(len(mainline) * 0.22))
    reuse_penalty = 0.0 if max_source_reuse <= reuse_limit else min(0.7, (max_source_reuse - reuse_limit) / max(1, len(mainline)))

    categories = [
        {
            "id": "source_backed_claims",
            "weight": 24,
            "score": pct(min(ratio(sourced, len(mainline)), ratio(strong_sourced, len(mainline)))),
            "evidence": f"{sourced}/{len(mainline)} sourced; {strong_sourced}/{len(mainline)} avoid single generic source cards",
        },
        {
            "id": "concrete_anchors",
            "weight": 22,
            "score": pct(min(ratio(anchored, len(mainline)), ratio(specific, len(mainline)))),
            "evidence": f"{anchored}/{len(mainline)} non-id anchors; {specific}/{len(mainline)} look concrete; id-only anchors {hollow_anchor_slides[:8]}",
        },
        {
            "id": "source_card_diversity",
            "weight": 12,
            "score": pct(max(0.0, min(ratio(unique_source_ids, unique_source_target), 1.0 - reuse_penalty))),
            "evidence": f"{unique_source_ids} unique source cards used; target {unique_source_target}; max reuse {max_source_reuse}/{reuse_limit}",
        },
        {
            "id": "claim_title_quality",
            "weight": 16,
            "score": pct(1.0 - ratio(len(weak_titles) + len(duplicate_titles), max(1, len(slides)))),
            "evidence": f"weak titles {len(weak_titles)}, duplicates {len(duplicate_titles)}",
        },
        {
            "id": "story_contract",
            "weight": 14,
            "score": pct(min(ratio(contract_present, len(contract_fields)), ratio(len(slide_claims or []), len(slides)))),
            "evidence": f"{contract_present}/{len(contract_fields)} contract fields; {len(slide_claims or [])}/{len(slides)} slide claims",
        },
        {
            "id": "source_material_depth",
            "weight": 14,
            "score": pct(
                min(
                    ratio(source_stats["source_card_count"], source_cards_target),
                    1.0 - min(0.7, ratio(source_stats["weak_source_card_count"], max(1, source_stats["source_card_count"]))),
                    1.0 - min(0.6, source_stats["missing_evidence_count"] * 0.08),
                )
            ),
            "evidence": (
                f"{source_stats['source_card_count']} source cards; target {source_cards_target}; "
                f"weak cards {source_stats['weak_source_card_count']}; "
                f"{source_stats['source_count']} sources; missing evidence {source_stats['missing_evidence_count']}"
            ),
        },
        {
            "id": "anti_generic_copy",
            "weight": 6,
            "score": pct(1.0 - ratio(len(generic_slides), max(1, len(slides)))),
            "evidence": f"generic phrase slides: {generic_slides[:8]}",
        },
    ]
    total_weight = sum(int(item["weight"]) for item in categories)
    score = round(sum(int(item["score"]) * int(item["weight"]) for item in categories) / total_weight)

    if score < min_score:
        failures.append(f"content outline score {score} below target {min_score}")
    if weak_titles:
        warnings.append("weak label-like titles: " + ", ".join(weak_titles[:5]))
    if duplicate_titles:
        warnings.append("duplicate titles: " + ", ".join(duplicate_titles[:5]))
    if source_stats["source_card_count"] < source_cards_target:
        warnings.append("source card depth is thin for slide count")
    if hollow_anchor_slides:
        warnings.append("source anchors are ids instead of concrete evidence on slides: " + ", ".join(map(str, hollow_anchor_slides[:8])))
    if max_source_reuse > reuse_limit:
        warnings.append(f"one source card is reused too often: {max_source_reuse} uses, limit {reuse_limit}")

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/content_outline_audit.py",
        "generated_at": utc_now(),
        "project": str(project),
        "ok": not failures,
        "score": score,
        "target_score": min_score,
        "slide_count": len(slides),
        "mainline_slide_count": len(mainline),
        "source_stats": source_stats,
        "source_card_usage": dict(source_id_usage.most_common()),
        "categories": categories,
        "failures": failures,
        "warnings": warnings,
        "boundary": "This gate checks whether the deck has a sourced argument spine before visual generation; it does not replace human editorial judgment.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Content Outline Audit",
        "",
        f"- OK: `{str(report['ok']).lower()}`",
        f"- Score: `{report['score']}` / 100",
        f"- Target: `{report['target_score']}`",
        f"- Slides: `{report['slide_count']}`",
        f"- Mainline slides: `{report['mainline_slide_count']}`",
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
    output = args.output or project / "reports" / "content_outline_audit.json"
    markdown = args.markdown or project / "reports" / "content_outline_audit.md"
    write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.enforce and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
