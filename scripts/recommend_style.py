#!/usr/bin/env python3
"""Recommend qiaomu-ppt design style presets for a deck brief."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_LIBRARY = DATA_DIR / "design_style_presets.json"
DEFAULT_EXTRA_LIBRARIES = [
    DATA_DIR / "magazine_art_styles.json",
    DATA_DIR / "ppt_master_case_styles.json",
    DATA_DIR / "32kw_bento_style_presets.json",
]


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
    "英伟达": "NVIDIA nvidia green accelerated computing GPU AI infrastructure Jensen Huang",
    "黄仁勋": "NVIDIA nvidia Jensen Huang GPU AI infrastructure keynote",
    "NVIDIA": "NVIDIA nvidia green accelerated computing GPU AI infrastructure Jensen Huang",
    "nvidia": "NVIDIA nvidia green accelerated computing GPU AI infrastructure Jensen Huang",
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
    "杂志": "magazine editorial luxury fashion art direction",
    "时尚": "fashion magazine vogue elle luxury editorial",
    "知识卡片": "knowledge card magazine editorial pull quote",
    "奢华": "luxury editorial magazine art direction",
    "主编": "editor art direction magazine folio pull quote",
    "论文解读": "paper reading academic blueprint arxiv formula table source figure TeX",
    "论文": "paper academic blueprint research formula table source figure",
    "arxiv": "paper academic blueprint research formula table source figure TeX",
    "Hugging Face": "paper academic blueprint research formula table source figure",
    "蓝图": "blueprint technical architecture diagram formula",
    "数据新闻": "data journalism Bloomberg Economist chart micro-chart finance report source line",
    "彭博": "Bloomberg data journalism finance market chart",
    "经济学人": "Economist data journalism editorial chart source line",
    "年度报告": "annual report data journalism newspaper chart source line",
    "瑞士": "Swiss grid typography modular red accent minimal",
    "网格": "Swiss grid typography modular layout minimal",
    "玻璃拟态": "glassmorphism frosted glass SaaS AI agent UI screenshot",
    "毛玻璃": "glassmorphism frosted glass gradient SaaS product launch",
    "智能体": "AI agent workflow SaaS product architecture",
    "孟菲斯": "Memphis pop vivid geometric festival event creative",
    "波普": "Memphis pop vivid geometric creative youth",
    "音乐节": "festival event Memphis pop schedule guide",
    "Risograph": "risograph riso zine screen print duotone collage",
    "risograph": "risograph riso zine screen print duotone collage",
    "Riso": "risograph riso zine screen print duotone collage",
    "zine": "zine risograph indie bookstore screen print duotone collage",
    "独立书店": "indie bookstore zine risograph guide collage",
    "孔版印刷": "risograph riso screen print duotone zine",
    "报章": "brutalist newspaper mono ink red signal annual report editorial",
    "粗野主义": "brutalist newspaper mono ink red signal editorial",
    "建筑摄影": "architecture editorial photo essay Pritzker museum catalog",
    "普利兹克": "Pritzker architecture editorial photo essay museum catalog",
    "策展": "museum catalog architecture editorial photo essay culture",
    "工程蓝图": "engineering blueprint Kubernetes Claude Code agent architecture infrastructure",
    "系统架构": "engineering blueprint architecture diagram infrastructure developer",
    "云原生": "Kubernetes engineering blueprint cloud native process flow",
    "Kubernetes": "engineering blueprint Kubernetes architecture cloud native",
    "Claude Code": "engineering blueprint Claude Code developer workflow agent",
    "有效智能体": "engineering blueprint AI agent effective agents workflow architecture",
    "咨询": "top consulting strategy root cause roadmap executive recommendation",
    "战略": "strategy consulting root cause roadmap pillar initiative",
    "根因": "root cause consulting strategy diagnosis",
    "路线图": "roadmap consulting strategy workstream initiative",
    "忠诚度": "loyalty programme customer profile consulting strategy",
    "客户画像": "customer profile loyalty consulting business diagnosis",
    "家居": "luxury editorial digest home design trend material lifestyle",
    "美学周鉴": "luxury editorial digest fashion weekly magazine lookbook",
    "趋势": "trend digest magazine editorial luxury home design fashion",
    "生活方式": "lifestyle luxury editorial digest fashion home design",
    "植物染": "eastern culture plant dye craft heritage poetic color",
    "李子柒": "eastern culture plant dye craft heritage Chinese culture",
    "非遗": "intangible heritage craft eastern culture Chinese culture",
    "传统色": "poetic color plant dye eastern culture Chinese culture",
    "东方": "eastern culture Chinese culture ink craft heritage",
    "中国文化": "Chinese culture eastern culture craft heritage ink",
    "水墨": "Chinese ink aesthetic eastern culture ink paper cinnabar",
    "藏拙": "Chinese ink aesthetic eastern culture philosophy",
    "蒲松龄": "Eastern Chinese culture classical literature Liaozhai ghost fox story heritage ink poetic object",
    "聊斋": "Eastern Chinese culture classical literature Liaozhai ghost fox story heritage ink poetic object",
    "聊斋志异": "Eastern Chinese culture classical literature Liaozhai ghost fox story heritage ink poetic object",
    "狐鬼": "Eastern Chinese culture classical literature ghost fox story heritage ink poetic object",
    "清代文学": "Eastern Chinese culture classical literature heritage biography ink poetic object",
    "古典文学": "Eastern Chinese culture classical literature heritage biography ink poetic object",
    "文学": "literature culture biography editorial heritage",
    "现实秩序": "culture literature social order editorial argument",
    "人物传记": "biography culture heritage museum catalog editorial",
    "图文混排": "image text layout showcase collage gallery image slot",
    "图片排版": "image text layout showcase image slot crop focal point",
    "版式展示": "image text layout showcase composition gallery poster",
    "bento": "bento grid modular card grid style seed",
    "Bento": "bento grid modular card grid style seed",
    "Bento Grid": "bento grid modular card grid style seed",
    "设计风格": "style seed visual language bento grid",
    "大胆现代": "bold modern vivid contrast visual impact",
    "艺术装饰": "art deco black gold geometric luxury",
    "赛博朋克": "cyberpunk neon dark futuristic city",
    "蒸汽波": "vaporwave pink cyan nostalgia internet",
    "包豪斯": "bauhaus geometry functional primary color",
    "构成主义": "constructivist diagonal geometric dynamic",
    "新拟物": "neumorphism soft shadow tactile ui",
    "玻璃态": "glassmorphism frosted glass translucent depth",
    "扁平化": "flat design clean shadow gradient",
    "像素艺术": "pixel art retro game low resolution",
    "中国传统": "Chinese traditional cinnabar gold ink pattern",
    "电影海报": "cinematic poster dramatic typography photography",
    "作品集": "portfolio image text layout showcase gallery",
    "城市更新": "urban renewal architecture humanities before after case study",
    "高层住宅": "urban renewal architecture before after regeneration",
    "林徽因": "architecture humanities museum exhibition biography Lin Huiyin",
    "建筑人文": "architecture humanities museum exhibition biography heritage",
    "前后对比": "before after urban renewal case study architecture",
}

ROUTE_TOKENS = {route.lower() for route in ROUTE_HINTS}
STYLE_NAME_STOP_TOKENS = {
    "ppt",
    "style",
    "seed",
    "template",
    "bento",
    "grid",
    "case",
    "design",
    "qiaomu",
    "风格",
    "设计",
    "模板",
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
    expanded_query = expand_query(query)
    query_tokens = tokenize(expanded_query)
    audience_tokens = tokenize(audience or "")
    score = 0
    reasons: list[str] = []

    label_text = " ".join(
        str(value or "")
        for value in (
            style.get("label"),
            style.get("id"),
            style.get("ppt", {}).get("template_name") if isinstance(style.get("ppt"), dict) else "",
        )
    ).lower()
    raw_query_lower = query.lower()
    for name_part in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9_.-]*", label_text):
        if re.search(r"[\u4e00-\u9fff]", name_part) and len(name_part) < 3:
            continue
        if not re.search(r"[\u4e00-\u9fff]", name_part) and len(name_part) < 3:
            continue
        if (
            name_part
            and name_part in raw_query_lower
            and name_part not in ROUTE_TOKENS
            and name_part not in STYLE_NAME_STOP_TOKENS
        ):
            score += 18
            reasons.append(f"exact style/name match `{name_part}`")
            break

    for token in query_tokens:
        if token in ROUTE_TOKENS:
            continue
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
    avoid_tokens = tokenize(avoid_text)
    if query_tokens & avoid_tokens:
        score -= 8
        reasons.append("possible avoid_for conflict")

    if not reasons:
        reasons.append("general style-library fit")
    return score, reasons


def load_styles(libraries: list[Path]) -> list[dict[str, Any]]:
    styles: list[dict[str, Any]] = []
    for library in libraries:
        if not library.exists():
            continue
        payload = json.loads(library.read_text(encoding="utf-8"))
        library_styles = payload.get("styles")
        if not isinstance(library_styles, list):
            continue
        for style in library_styles:
            if isinstance(style, dict):
                style = dict(style)
                style.setdefault("_library", library.name)
                styles.append(style)
    return styles


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend qiaomu-ppt design styles from a deck brief.")
    parser.add_argument("--query", "-q", required=True, help="Deck brief, topic, or visual need.")
    parser.add_argument("--route", help="Optional qiaomu-ppt route override.")
    parser.add_argument("--audience", help="Optional audience description.")
    parser.add_argument("--top", type=int, default=5, help="Number of styles to return.")
    parser.add_argument(
        "--library",
        type=Path,
        action="append",
        help="Style library JSON. Can be passed multiple times. Defaults to design_style_presets.json plus magazine_art_styles.json and ppt_master_case_styles.json.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    libraries = args.library or [DEFAULT_LIBRARY, *DEFAULT_EXTRA_LIBRARIES]
    styles = load_styles(libraries)
    if not styles:
        raise SystemExit("No styles found in the selected libraries.")
    route = args.route or infer_route(args.query) or "brand_release"
    ranked = []
    for style in styles:
        score, reasons = score_style(style, args.query, route, args.audience)
        ranked.append(
            {
                "score": score,
                "id": style["id"],
                "label": style["label"],
                "library": style.get("_library", ""),
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
        if item.get("library"):
            print(f"   library: {item['library']}")
        print(f"   palette: {palette}")
        print(f"   reasons: {'; '.join(item['reasons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
