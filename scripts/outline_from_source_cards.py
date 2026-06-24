#!/usr/bin/env python3
"""Create a qiaomu-ppt content contract and slide-plan seed from source cards."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LAYOUT_SEQUENCE = [
    "L01 hero claim",
    "L03 claim plus model",
    "L08 comparison",
    "L13 process flow",
    "L18 mechanism loop",
    "L20 chart with takeaway",
    "L24 concept map",
    "L31 objection response",
    "L35 closing",
]

LAYOUT_TO_COMPONENT = {
    "L01": "hero_claim",
    "L08": "comparison",
    "L13": "process_flow",
    "L18": "mechanism_loop",
    "L20": "chart_with_takeaway",
    "L24": "concept_map",
    "L31": "objection_response",
    "L34": "pull_quote",
    "L35": "closing_takeaway",
}

ROLE_SEQUENCE = [
    "context",
    "core_text",
    "mechanism",
    "conflict",
    "social_reading",
    "comparison",
    "influence",
    "objection",
    "synthesis",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_claim(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip(" -:：;；")
    if not value:
        return ""
    value = re.sub(r"(\.\.\.|…)+$", "", value).strip(" -:：;；，,。.、")
    if len(value) > 42:
        parts = re.split(r"[，,。；;：:、]", value)
        if parts and 10 <= len(parts[0]) <= 42:
            value = parts[0]
        else:
            value = value[:42].rstrip("，,。.；;、 ")
    return value


def layout_id_from_value(value: str) -> str:
    match = re.search(r"\bL\d{2}\b", str(value or "").upper())
    return match.group(0) if match else ""


def component_type_for_layout(layout: str, fallback: str) -> str:
    layout_id = layout_id_from_value(layout)
    return LAYOUT_TO_COMPONENT.get(layout_id) or fallback


def compact_text(value: str, limit: int = 120) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip(" -:：;；")
    if len(value) <= limit:
        return value
    return value[:limit].rstrip("，,。.；;、 ") + "..."


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value or ""))


def dedupe_key(value: str) -> str:
    value = re.sub(r"\s+", "", value.lower())
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value)


def load_cards(sources_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = sources_dir / "source_cards.json"
    payload = load_json(path)
    cards = payload.get("cards") if isinstance(payload, dict) else None
    if not isinstance(cards, list) or not cards:
        raise ValueError("source_cards.json needs a non-empty cards list")
    return payload, [item for item in cards if isinstance(item, dict)]


def card_claim(card: dict[str, Any]) -> str:
    return clean_claim(str(card.get("claim") or card.get("evidence") or ""))


def raw_card_claim(card: dict[str, Any] | None) -> str:
    if not isinstance(card, dict):
        return ""
    return compact_text(str(card.get("claim") or card.get("evidence") or ""), 150)


def visible_card_claim(card: dict[str, Any] | None, limit: int = 90) -> str:
    if not isinstance(card, dict):
        return ""
    claim = str(card.get("claim") or "").strip()
    if claim and has_cjk(claim):
        return compact_text(claim, limit)
    localized = localized_visible_evidence(str(card.get("evidence") or claim), card)
    return compact_text(localized, limit)


def localized_visible_evidence(value: str, card: dict[str, Any] | None = None) -> str:
    """Return slide-visible evidence text; keep raw source text for notes."""
    value = re.sub(r"\s+", " ", str(value or "")).strip(" -:：;；")
    if not value or has_cjk(value):
        return value
    title = str(card.get("source_title") or "") if isinstance(card, dict) else ""
    lower = value.lower()
    title_lower = title.lower()
    if "pu songling" in title_lower or "pu songling" in lower:
        if "spent most of his life" in lower and "strange tales from a chinese studio" in lower:
            return "蒲松龄长期做私塾教师并搜集故事，这些故事后来结集为《聊斋志异》。"
        if "collecting stories" in lower and "strange tales from a chinese studio" in lower:
            return "蒲松龄搜集的故事后来以《聊斋志异》之名流传。"
        if "later published in strange tales from a chinese studio" in lower:
            return "这些搜集而来的故事后来以《聊斋志异》之名出版和流传。"
        if "was born into a poor merchant family" in lower:
            return "蒲松龄出生于山东淄川一个贫寒商人家庭。"
        if "poor merchant family" in lower and "zichuan" in lower:
            return "蒲松龄的出身与山东淄川的地方经验密切相关。"
        if "received the xiucai degree" in lower:
            return "蒲松龄 18 岁取得秀才功名，但仕途并不顺利。"
    return value


def visible_source_anchor(card: dict[str, Any] | None, limit: int = 180) -> str:
    if not isinstance(card, dict):
        return ""
    claim = str(card.get("claim") or "").strip()
    evidence = str(card.get("evidence") or "").strip()
    if claim and has_cjk(claim):
        return compact_text(claim, limit)
    return compact_text(localized_visible_evidence(evidence or claim, card), limit)


def evidence_visibility_line(claim: str, evidence: str) -> str:
    if not evidence or dedupe_key(claim) == dedupe_key(evidence):
        return ""
    if has_cjk(claim) and not has_cjk(evidence):
        return "原始英文证据保留在备注和 source card，画面只呈现中文判断。"
    return f"文本线索：{compact_text(evidence, 90)}"


def role_title(card: dict[str, Any], role: str, deck_title: str = "", partner: dict[str, Any] | None = None) -> str:
    claim = raw_card_claim(card)
    partner_claim = raw_card_claim(partner)
    book = re.search(r"《([^》]{2,30})》", claim)
    if role == "context":
        if "1842" in claim and "聊斋" in claim:
            return "1842 年序言，把《聊斋志异》推向文学评价现场"
        if re.search(r"(清代|明代|宋代|时代|世纪|\b(1[5-9]\d{2}|20\d{2})\b)", claim):
            return "先把主题放回它的时代现场"
        return "第一步不是贴标签，而是找到问题现场"
    if role == "core_text":
        if book:
            return clean_claim(f"核心入口是《{book.group(1)}》，不是人物简介")
        return "核心入口来自材料本身，不是泛泛介绍"
    if role == "mechanism":
        if any(token in claim for token in ("通过", "借", "以", "表现", "呈现")):
            return "关键机制在这里，而不是在概念标签里"
        return "把材料变成机制，而不是罗列"
    if role == "conflict":
        if "吉尔斯" in claim or "维多利亚" in claim or "篡改" in claim:
            return "翻译与改写，让《聊斋志异》进入另一种道德框架"
        if any(token in claim for token in ("冲突", "困境", "矛盾", "欲望", "制度", "道德")):
            return clean_claim(f"真正推动故事的是冲突：{claim}")
        return clean_claim(f"这一页要回答：材料里的张力在哪里")
    if role == "social_reading":
        if any(token in claim for token in ("社会", "现实", "制度", "地方", "伦理", "秩序")):
            return "表面是故事，深处是社会结构"
        if any(token in claim for token in ("私塾", "教师", "搜集", "贫寒", "科举", "秀才")):
            return clean_claim(f"蒲松龄的现实经验，进入了志怪故事")
        return "从材料里读出更大的现实问题"
    if role == "comparison":
        if partner_claim:
            return clean_claim(f"两条证据放在一起，才看见主线")
        return clean_claim(f"换一个角度看同一条证据")
    if role == "influence":
        if any(token in claim for token in ("影响", "后世", "成为", "奠定", "改变")):
            return "影响力来自可被反复转述的核心判断"
        if "《" in claim or "聊斋" in claim:
            return clean_claim("《聊斋志异》的生命力来自持续流传")
        return "为什么这条材料值得被今天记住"
    if role == "objection":
        if "贫寒" in claim or "淄川" in claim:
            return "贫寒出身不是背景噪声，而是理解入口"
        return "如果只把它当资料点，就会漏掉主线"
    return clean_claim(f"把这些证据收束成一条可讲的主线")


def role_points(card: dict[str, Any], role: str, partner: dict[str, Any] | None = None) -> list[str]:
    claim = visible_card_claim(card)
    evidence = compact_text(str(card.get("evidence") or claim), 150)
    partner_claim = visible_card_claim(partner)
    points: list[str] = []
    if role == "comparison" and partner_claim:
        points = [
            f"线索 A：{claim}",
            f"线索 B：{partner_claim}",
            "比较它们的差异和共同指向，形成一页可视化对照。",
        ]
    elif role == "mechanism":
        points = [
            f"材料线索：{claim}",
            "把这条证据拆成「媒介 / 动作 / 结果」三个节点。",
            "页面重点是解释机制，不是重复原句。",
        ]
    elif role == "conflict":
        points = [
            f"材料线索：{claim}",
            "标出谁和谁发生冲突：个人、制度、道德、时代或技术条件。",
            "用对立关系支撑标题判断。",
        ]
    elif role == "social_reading":
        points = [
            f"材料线索：{claim}",
            "把个案放大到社会结构、组织方式或文化心理。",
            "避免把例子讲成孤立轶事。",
        ]
    elif role == "objection":
        points = [
            f"材料线索：{claim}",
            "写出一种常见误读，再用来源材料纠正它。",
            "让页面承担转折作用。",
        ]
    else:
        points = [
            f"材料线索：{claim}",
            evidence_visibility_line(claim, evidence),
            "把证据转成一个清晰的可讲判断。",
        ]
    seen: set[str] = set()
    out: list[str] = []
    for point in points:
        if not point:
            continue
        key = dedupe_key(point)
        if key and key not in seen:
            seen.add(key)
            out.append(point)
    return out[:4]


def score_card_for_role(card: dict[str, Any], role: str) -> float:
    claim = raw_card_claim(card)
    score = 0.0
    role_keywords = {
        "context": ("清代", "明代", "宋代", "时代", "世纪", "科举", "生平", "经历", "失意", "出生", "文学家"),
        "core_text": ("《", "》", "著有", "作品", "文本", "文章", "书", "志异", "核心"),
        "mechanism": ("通过", "借", "以", "表现", "呈现", "承载", "形成", "如何", "机制"),
        "conflict": ("冲突", "矛盾", "困境", "欲望", "制度", "道德", "张力", "失意"),
        "social_reading": ("社会", "现实", "制度", "地方", "伦理", "秩序", "士人", "命运"),
        "comparison": ("并不只是", "不是", "而是", "对比", "同时", "另一方面"),
        "influence": ("影响", "后世", "闻名", "成为", "奠定", "改变", "长期"),
        "objection": ("并不只是", "不是", "误读", "猎奇", "批判", "同情"),
        "synthesis": ("社会", "现实", "影响", "冲突", "秩序", "核心"),
    }
    for token in role_keywords.get(role, ()):
        if token in claim:
            score += 2.0
    if re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", claim) and role in {"context", "influence"}:
        score += 1.5
    if re.search(r"《[^》]{2,30}》", claim) and role in {"core_text", "mechanism", "conflict"}:
        score += 1.2
    if role == "mechanism" and any(token in claim for token in ("通过", "借", "承载")):
        score += 2.5
    if role == "context" and any(token in claim for token in ("通过", "承载", "冲突")):
        score -= 1.0
    return score


def choose_card_for_role(cards: list[dict[str, Any]], role: str, used_counts: dict[str, int]) -> dict[str, Any]:
    def sort_key(card: dict[str, Any]) -> tuple[float, int, str]:
        card_id = str(card.get("id") or "")
        return (score_card_for_role(card, role), -used_counts.get(card_id, 0), raw_card_claim(card))

    chosen = max(cards, key=sort_key)
    used_counts[str(chosen.get("id") or "")] = used_counts.get(str(chosen.get("id") or ""), 0) + 1
    return chosen


def build_slide(
    slide_no: int,
    total: int,
    card: dict[str, Any] | None,
    title: str,
    visual_role: str,
    intent: str,
    points: list[str],
) -> dict[str, Any]:
    source_ids = card.get("source_ids", []) if isinstance(card, dict) else []
    card_id = str(card.get("id") or "").strip() if isinstance(card, dict) else ""
    evidence = str(card.get("evidence") or card.get("claim") or "").strip() if isinstance(card, dict) else ""
    visible_anchor = visible_source_anchor(card) if isinstance(card, dict) else ""
    anchor = visible_anchor or compact_text(evidence, 180)
    layout = LAYOUT_SEQUENCE[min(slide_no - 1, len(LAYOUT_SEQUENCE) - 1)]
    if slide_no == total:
        layout = "L35 closing"
    elif slide_no == 1:
        layout = "L01 hero claim"
    elif slide_no % 5 == 0:
        layout = "L24 concept map"
    elif slide_no % 4 == 0:
        layout = "L13 process flow"
    elif slide_no % 3 == 0:
        layout = "L08 comparison"

    return {
        "slide_no": slide_no,
        "page": slide_no,
        "title": title,
        "claim_title": title,
        "intent": intent,
        "audience_or_learning_state_before": "The audience has source fragments but no clear argument spine.",
        "audience_or_learning_state_after": "The audience can remember one sourced claim and why it matters.",
        "content_points": points[:4],
        "concrete_anchor": anchor[:180],
        "source_card_ids": [card_id] if card_id else [],
        "source_ids": source_ids if isinstance(source_ids, list) else [],
        "source_anchor": anchor[:180],
        "source_evidence_raw": evidence[:500],
        "visual_role": visual_role,
        "rhythm": "claim_proof",
        "layout_pattern": layout,
        "reading_path": "claim -> proof object -> implication",
        "proof_object": visual_role,
        "component_plan": {
            "component_type": component_type_for_layout(layout, visual_role),
            "narrative_role": visual_role,
            "source_card_id": card_id,
            "layout_pattern": layout,
        },
        "media_need": "Use source images if available; otherwise use diagram, timeline, quote, or procedural background.",
        "speaker_note_goal": "Explain the source evidence, add context, and connect this claim to the deck argument.",
        "qa_risk": "Verify the claim is not broader than the cited source card.",
    }


def build_outline(
    sources_dir: Path,
    deck_title: str,
    audience: str,
    purpose: str,
    desired_action: str,
    slide_count: int,
    research_required: bool,
) -> dict[str, Any]:
    cards_payload, cards = load_cards(sources_dir)
    usable_cards = [card for card in cards if card_claim(card)]
    if not usable_cards:
        raise ValueError("source_cards.json has no usable card claims")
    slide_count = max(3, slide_count)
    mainline_count = max(1, slide_count - 2)
    mainline_roles = [ROLE_SEQUENCE[idx % len(ROLE_SEQUENCE)] for idx in range(mainline_count)]
    used_counts: dict[str, int] = {}
    selected_cards = [choose_card_for_role(usable_cards, role, used_counts) for role in mainline_roles]

    slides: list[dict[str, Any]] = []
    first = usable_cards[0]
    title = deck_title or card_claim(first)
    slides.append(
        build_slide(
            1,
            slide_count,
            first,
            clean_claim(title),
            "cover",
            "Open with the strongest sourced claim, not a generic topic label.",
            [
                visible_card_claim(first),
                "这份 PPT 先从来源证据出发，再组织成一条可讲的主线。",
            ],
        )
    )

    used_titles: set[str] = {dedupe_key(slides[0]["claim_title"])}
    for idx, card in enumerate(selected_cards):
        offset = idx + 2
        role = mainline_roles[idx]
        partner = selected_cards[(idx + 1) % len(selected_cards)] if len(selected_cards) > 1 else None
        claim = role_title(card, role, title, partner)
        key = dedupe_key(claim)
        if key in used_titles:
            claim = clean_claim(f"{claim}（换成{role}视角）")
            key = dedupe_key(claim)
        used_titles.add(key)
        slides.append(
            build_slide(
                offset,
                slide_count,
                card,
                claim,
                role,
                "Advance the argument with one source-backed claim.",
                role_points(card, role, partner),
            )
        )

    last_card = selected_cards[-1]
    closing_title = clean_claim(f"最终要记住的不是资料数量，而是证据如何连成主线")
    closing_action = desired_action
    if desired_action == "remember the argument and know what to inspect next":
        closing_action = "记住核心判断，并知道下一步该回到哪些来源继续核查。"
    slides.append(
        build_slide(
            slide_count,
            slide_count,
            last_card,
            closing_title,
            "closing",
            "Close by restating the sourced thesis and next action.",
            [
                "回到开头的问题，把人物、文本、机制和影响收束成一句可复述的判断。",
                closing_action,
            ],
        )
    )

    slide_claims = [
        {
            "slide_no": slide["slide_no"],
            "claim_title": slide["claim_title"],
            "evidence_type": "source_card" if slide.get("source_card_ids") else "synthesis",
            "source_card_ids": slide.get("source_card_ids", []),
            "spoken_role": "explain and connect source evidence",
        }
        for slide in slides
    ]
    coverage = cards_payload.get("source_coverage", [])
    content_contract = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "generator": "qiaomu-ppt/scripts/outline_from_source_cards.py",
        "audience": audience,
        "purpose": purpose,
        "desired_action": desired_action,
        "current_state": "The audience has raw source material or a broad topic but no structured presentation argument.",
        "desired_state": "The audience can scan claim titles, understand the argument, and trust the source-backed proof.",
        "stakes": "A deck without source-linked claims may look polished but feel hollow.",
        "structure_framework": ["storyline", "pyramid"],
        "title_policy": "claim_titles",
        "copy_density": "medium: one claim, up to four visible support chunks, details in speaker notes",
        "evidence_policy": "Every mainline slide cites source_card_ids and keeps the claim within the cited evidence.",
        "speaker_note_policy": "Speaker notes carry context, caveats, source provenance, and extra detail not suitable for visible copy.",
        "research_required": research_required,
        "research_status": "source_cards_generated" if research_required else "source_backed_intake",
        "topic_angle": title,
        "source_coverage": coverage,
        "slide_claims": slide_claims,
    }
    slide_plan_seed = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "generator": "qiaomu-ppt/scripts/outline_from_source_cards.py",
        "deck_title": title,
        "slides": slides,
    }
    return {
        "content_contract": content_contract,
        "slide_plan_seed": slide_plan_seed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create content_contract.json and slide_plan seed from source_cards.json.")
    parser.add_argument("project", type=Path, help="Project directory containing sources/source_cards.json, or the sources directory itself.")
    parser.add_argument("--title", default="", help="Deck title or topic angle.")
    parser.add_argument("--audience", default="general audience", help="Target audience.")
    parser.add_argument("--purpose", default="turn source material into a clear, sourced presentation argument", help="Deck purpose.")
    parser.add_argument("--desired-action", default="remember the argument and know what to inspect next", help="Desired audience action.")
    parser.add_argument("--slides", type=int, default=8, help="Number of slides to seed.")
    parser.add_argument("--research-required", action="store_true", help="Mark content_contract.json as topic-researched and require topic research artifacts.")
    parser.add_argument("--write-slide-plan", action="store_true", help="Also write slide_plan.json if it does not already exist.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing content_contract.json / slide_plan_seed.json / slide_plan.json.")
    args = parser.parse_args()

    project = args.project.resolve()
    sources_dir = project if (project / "source_cards.json").exists() else project / "sources"
    project_dir = sources_dir.parent if sources_dir.name == "sources" else project
    outline = build_outline(
        sources_dir=sources_dir,
        deck_title=args.title,
        audience=args.audience,
        purpose=args.purpose,
        desired_action=args.desired_action,
        slide_count=args.slides,
        research_required=args.research_required,
    )

    content_path = project_dir / "content_contract.json"
    seed_path = project_dir / "slide_plan_seed.json"
    slide_plan_path = project_dir / "slide_plan.json"
    for path, payload in ((content_path, outline["content_contract"]), (seed_path, outline["slide_plan_seed"])):
        if path.exists() and not args.force:
            raise SystemExit(f"{path.name} already exists; use --force to overwrite")
        write_json(path, payload)
    wrote_slide_plan = False
    if args.write_slide_plan:
        if slide_plan_path.exists() and not args.force:
            raise SystemExit("slide_plan.json already exists; use --force to overwrite")
        write_json(slide_plan_path, outline["slide_plan_seed"])
        wrote_slide_plan = True

    result = {
        "ok": True,
        "content_contract": str(content_path),
        "slide_plan_seed": str(seed_path),
        "slide_plan": str(slide_plan_path) if wrote_slide_plan else "",
        "slide_count": len(outline["slide_plan_seed"]["slides"]),
        "source_cards_used": sum(1 for slide in outline["slide_plan_seed"]["slides"] if slide.get("source_card_ids")),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
