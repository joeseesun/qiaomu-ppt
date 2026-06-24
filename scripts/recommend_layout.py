#!/usr/bin/env python3
"""Recommend qiaomu-ppt image/text layout patterns for a slide or deck brief."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_LIBRARY = DATA_DIR / "image_text_layout_patterns.json"


ROUTE_HINTS = {
    "brand_release": ["brand", "launch", "release", "product", "keynote", "品牌", "发布会", "新品", "产品"],
    "high_school_courseware": ["courseware", "lesson", "classroom", "student", "teacher", "课件", "教学", "课堂", "步骤"],
    "business_report": ["report", "strategy", "market", "finance", "metric", "data", "商务", "汇报", "报告", "数据"],
    "talk_deck": ["talk", "speech", "conference", "seminar", "keynote", "演讲", "分享", "大会"],
    "pptx_beautify": ["redesign", "before after", "beautify", "refresh", "美化", "改版", "前后对比"],
    "html_preview": ["preview", "html", "web", "style", "预览", "网页", "风格"],
}


QUERY_EXPANSIONS = {
    "封面": "cover hero full bleed big title premium magazine",
    "高级": "premium luxury editorial copy space magazine",
    "高端": "premium luxury editorial copy space magazine",
    "品牌": "brand creative moodboard product hero magazine",
    "发布会": "launch keynote product hero full bleed",
    "产品": "product feature screenshot spec benefit callout",
    "功能": "feature product screenshot annotation callout",
    "截图": "screenshot annotation step app SaaS UI",
    "SaaS": "screenshot annotation product UI demo",
    "App": "screenshot annotation product UI demo",
    "教程": "tutorial step annotation timeline courseware",
    "教学": "courseware explain timeline screenshot step caption",
    "数据": "data chart evidence insight context metric",
    "图表": "chart data evidence context takeaway",
    "证据": "evidence chart screenshot before after comparison",
    "市场": "market insight data chart report",
    "商业汇报": "business report executive data evidence split conclusion",
    "案例": "case customer testimonial caption floating card",
    "客户": "customer case testimonial quote portrait",
    "用户故事": "user story customer case quote portrait caption",
    "金句": "quote testimonial pull quote portrait",
    "访谈": "interview quote portrait testimonial",
    "前后对比": "before after comparison old new redesign",
    "对比": "compare contrast before after two column",
    "流程": "process timeline journey step",
    "旅程": "journey timeline process milestone",
    "时间线": "timeline journey milestone",
    "作品集": "portfolio gallery sidebar moodboard collage",
    "多图": "gallery collage moodboard three cards",
    "拼贴": "collage moodboard gallery",
    "图文混排": "image text layout split caption collage",
    "图片排版": "image text layout crop slot focal point",
    "杂志": "magazine editorial cover big type quote caption",
}


ROUTE_GROUP_PRIORS = {
    "brand_release": {"hero_image": 6, "product": 5, "editorial": 3},
    "business_report": {"split": 5, "evidence": 5, "product": 2},
    "high_school_courseware": {"product": 4, "evidence": 4, "editorial": 3},
    "talk_deck": {"hero_image": 4, "editorial": 4, "evidence": 3},
    "pptx_beautify": {"split": 4, "evidence": 4, "product": 3},
    "html_preview": {"hero_image": 5, "editorial": 4},
}


def expand_query(text: str) -> str:
    expanded = [text]
    for key, value in QUERY_EXPANSIONS.items():
        if key.lower() in text.lower():
            expanded.append(value)
    return " ".join(expanded)


def tokenize(text: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9][a-z0-9_.-]*", text.lower()))
    for token in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        words.add(token)
    return words


def infer_route(text: str) -> str | None:
    lower = text.lower()
    scores = []
    for route, hints in ROUTE_HINTS.items():
        score = sum(1 for hint in hints if hint.lower() in lower)
        if score:
            scores.append((score, route))
    if not scores:
        return None
    return sorted(scores, reverse=True)[0][1]


def pattern_text(pattern: dict[str, Any]) -> str:
    fields: list[str] = [
        pattern.get("id", ""),
        pattern.get("name_zh", ""),
        pattern.get("name_en", ""),
        pattern.get("master_group", ""),
        pattern.get("structure", ""),
    ]
    for key in ("use_for", "image_role", "rules", "avoid", "layout_pattern_mappings", "recommended_routes", "query_terms"):
        value = pattern.get(key, [])
        if isinstance(value, list):
            fields.extend(str(item) for item in value)
        else:
            fields.append(str(value))
    return " ".join(fields)


def selection_boosts(payload: dict[str, Any], query: str) -> dict[str, tuple[int, str]]:
    lower = query.lower()
    boosts: dict[str, tuple[int, str]] = {}
    for entry in payload.get("selection_table", []):
        goal = entry.get("goal", "")
        terms = [goal, *entry.get("query_terms", [])]
        matched = any(term and term.lower() in lower for term in terms)
        if not matched:
            continue
        for pattern_id in entry.get("pattern_ids", []):
            boosts[pattern_id] = (18, f"matches goal `{goal}`")
    return boosts


def score_pattern(
    payload: dict[str, Any],
    pattern: dict[str, Any],
    query: str,
    route: str | None,
) -> tuple[int, list[str]]:
    haystack = pattern_text(pattern)
    haystack_tokens = tokenize(haystack)
    query_tokens = tokenize(expand_query(query))
    score = 0
    reasons: list[str] = []

    for token in query_tokens:
        matched = token in haystack_tokens
        if not matched and re.search(r"[\u4e00-\u9fff]", token) and len(token) >= 2:
            matched = token in haystack
        if matched:
            score += 3
            if len(reasons) < 5:
                reasons.append(f"matches `{token}`")

    boosts = selection_boosts(payload, query)
    if pattern.get("id") in boosts:
        boost, reason = boosts[pattern["id"]]
        score += boost
        reasons.append(reason)

    if route and route in pattern.get("recommended_routes", []):
        score += 10
        reasons.append(f"fits route `{route}`")

    if route:
        group_prior = ROUTE_GROUP_PRIORS.get(route, {}).get(pattern.get("master_group", ""), 0)
        if group_prior:
            score += group_prior
            reasons.append(f"strong `{pattern.get('master_group')}` group for `{route}`")

    # Favor patterns that have explicit mappings into the proof-structure layout library.
    if pattern.get("layout_pattern_mappings"):
        score += min(4, len(pattern["layout_pattern_mappings"]))

    if not reasons:
        reasons.append("general image/text layout fit")
    return score, reasons


def load_library(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Layout library not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("patterns"), list):
        raise SystemExit(f"Layout library has no patterns list: {path}")
    return payload


def format_pattern(item: dict[str, Any]) -> str:
    mappings = ", ".join(item["layout_pattern_mappings"])
    use_for = " / ".join(item["use_for"][:4])
    reasons = "; ".join(item["reasons"][:4])
    return (
        f"{item['rank']}. {item['id']} {item['name_zh']} / {item['name_en']} "
        f"[{item['master_group']}] score={item['score']}\n"
        f"   structure: {item['structure']}\n"
        f"   use_for: {use_for}\n"
        f"   maps_to: {mappings}\n"
        f"   why: {reasons}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend qiaomu-ppt image/text layout patterns.")
    parser.add_argument("--query", "-q", required=True, help="Slide/deck brief or media-placement need.")
    parser.add_argument("--route", help="Optional qiaomu-ppt route override.")
    parser.add_argument("--top", type=int, default=5, help="Number of patterns to return.")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="Image/text layout JSON library.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    payload = load_library(args.library)
    route = args.route or infer_route(args.query) or "business_report"
    ranked = []
    for pattern in payload["patterns"]:
        score, reasons = score_pattern(payload, pattern, args.query, route)
        ranked.append(
            {
                "score": score,
                "id": pattern["id"],
                "name_zh": pattern["name_zh"],
                "name_en": pattern["name_en"],
                "master_group": pattern["master_group"],
                "structure": pattern["structure"],
                "use_for": pattern.get("use_for", []),
                "font_size": pattern.get("font_size", {}),
                "image_role": pattern.get("image_role", []),
                "rules": pattern.get("rules", []),
                "avoid": pattern.get("avoid", []),
                "layout_pattern_mappings": pattern.get("layout_pattern_mappings", []),
                "recommended_routes": pattern.get("recommended_routes", []),
                "reasons": reasons,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["id"]))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    result = {
        "query": args.query,
        "route": route,
        "source_library": str(args.library),
        "top": ranked[: args.top],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Route: {route}")
    for item in result["top"]:
        print(format_pattern(item))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
