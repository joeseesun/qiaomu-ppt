#!/usr/bin/env python3
"""Recommend qiaomu-ppt design style presets for a deck brief."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_LIBRARY = Path(__file__).resolve().parents[1] / "data" / "design_style_presets.json"


ROUTE_HINTS = {
    "brand_release": ["brand", "launch", "release", "product", "keynote", "发布", "发布会", "产品"],
    "high_school_courseware": ["courseware", "lesson", "classroom", "teacher", "student", "高中", "课件", "课堂", "老师"],
    "business_report": ["report", "strategy", "market", "finance", "metrics", "analysis", "报告", "复盘", "策略", "数据"],
    "talk_deck": ["talk", "speech", "conference", "seminar", "keynote", "演讲", "分享", "大会"],
    "pptx_beautify": ["redesign", "beautify", "old ppt", "refresh", "美化", "重做", "二次编辑"],
    "html_preview": ["preview", "html", "web", "style direction", "预览", "网页", "风格"],
}


QUERY_EXPANSIONS = {
    "黑底": "black dark near-black dark-canvas",
    "黑色": "black dark",
    "深色": "dark black",
    "科技感": "technical futuristic developer product",
    "技术": "technical developer infrastructure",
    "技术证据": "technical evidence proof metric",
    "代码": "code terminal developer",
    "架构": "architecture system diagram",
    "数据": "data metrics dashboard chart",
    "金融": "finance fintech trust",
    "信任": "trust credible institutional",
    "电影感": "cinematic photography full-bleed",
    "产品影像": "product photography cinematic",
    "发布会": "launch keynote product",
    "极简": "minimal precision monochrome",
    "高级": "premium editorial luxury",
    "活泼": "playful colorful vibrant",
    "复古": "retro nostalgia",
}


def expand_query(text: str) -> str:
    expanded = [text]
    for key, value in QUERY_EXPANSIONS.items():
        if key in text:
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


def score_style(style: dict[str, Any], query: str, route: str | None, audience: str | None) -> tuple[int, list[str]]:
    haystack = style.get("recommendation_text", "")
    haystack_tokens = tokenize(haystack)
    query_tokens = tokenize(expand_query(query))
    audience_tokens = tokenize(audience or "")
    score = 0
    reasons: list[str] = []

    for token in query_tokens:
        matched = token in haystack_tokens
        if not matched and re.search(r"[\u4e00-\u9fff]", token) and len(token) >= 3:
            matched = token in haystack
        if matched:
            score += 3
            if len(reasons) < 5:
                reasons.append(f"matches `{token}`")

    for token in audience_tokens:
        if token in haystack_tokens:
            score += 2

    ppt = style["ppt"]
    if route and route in ppt.get("recommended_routes", []):
        score += 12
        reasons.append(f"fits route `{route}`")

    archetype = ppt.get("archetype", "")
    if route == "high_school_courseware" and archetype in {"minimal_precision", "editorial_argument"}:
        score += 6
        reasons.append("safe for readable courseware")
    if route == "brand_release" and archetype in {"cinematic_product_reveal", "editorial_argument", "playful_creative_canvas"}:
        score += 6
        reasons.append("strong for launch storytelling")
    if route == "business_report" and archetype in {"minimal_precision", "developer_technical_evidence", "trust_finance_dashboard"}:
        score += 6
        reasons.append("strong for evidence/reporting")

    avoid_text = " ".join(ppt.get("avoid_for", [])).lower()
    if any(token in avoid_text for token in query_tokens):
        score -= 8
        reasons.append("possible avoid_for conflict")

    if not reasons:
        reasons.append("general style-library fit")
    return score, reasons


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend qiaomu-ppt design styles from a deck brief.")
    parser.add_argument("--query", "-q", required=True, help="Deck brief, topic, or visual need.")
    parser.add_argument("--route", help="Optional qiaomu-ppt route override.")
    parser.add_argument("--audience", help="Optional audience description.")
    parser.add_argument("--top", type=int, default=5, help="Number of styles to return.")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="Path to design_style_presets.json.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    payload = json.loads(args.library.read_text())
    route = args.route or infer_route(args.query) or "brand_release"
    ranked = []
    for style in payload["styles"]:
        score, reasons = score_style(style, args.query, route, args.audience)
        ranked.append(
            {
                "score": score,
                "id": style["id"],
                "label": style["label"],
                "archetype": style["ppt"]["archetype"],
                "qiaomu_visual_system": style["ppt"]["qiaomu_visual_system"],
                "recommended_routes": style["ppt"]["recommended_routes"],
                "palette": style["ppt"]["palette"]["swatches"][:5],
                "reasons": reasons,
                "summary": style["description_summary"],
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["label"]))
    result = {"query": args.query, "route": route, "top": ranked[: args.top]}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Route: {route}")
    for index, item in enumerate(result["top"], start=1):
        palette = ", ".join(color["hex"] for color in item["palette"])
        print(f"{index}. {item['label']} [{item['archetype']}] score={item['score']}")
        print(f"   visual_system: {item['qiaomu_visual_system']}")
        print(f"   palette: {palette}")
        print(f"   reasons: {'; '.join(item['reasons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
