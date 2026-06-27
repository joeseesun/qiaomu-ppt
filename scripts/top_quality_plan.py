#!/usr/bin/env python3
"""Audit top-quality readiness before qiaomu-ppt preview or production."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_RUBRIC = SKILL_DIR / "data" / "top_quality_rubric.json"

sys.path.insert(0, str(SCRIPT_DIR))
import content_preflight as content_preflight_tool  # noqa: E402

WEAK_TITLES = {
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
    "引言",
    "现状",
    "挑战",
}
GENERIC_PHRASES = {
    "提升效率",
    "形成闭环",
    "赋能",
    "创新发展",
    "价值提升",
    "多维度",
    "系统性",
    "核心价值",
    "关键路径",
    "重要意义",
    "深度解读",
    "全面了解",
    "值得关注",
}
SECTION_GROUPS = {
    "scope": ["任务范围", "主题", "受众", "使用场景", "交付"],
    "facts": ["已验证事实", "事实", "verified facts"],
    "evidence": ["证据", "来源", "source", "evidence", "引用"],
    "interpretation": ["解释判断", "判断", "推断", "interpretation"],
    "gaps": ["缺口", "冲突", "missing evidence", "风险", "矛盾"],
    "visual": ["候选图片", "视觉机会", "可视化", "图片", "主视觉"],
    "rights": ["权利", "版权", "来源风险", "肖像", "许可"],
    "slide_map": ["页面支撑", "支持页面", "supports slide", "slide support", "第", "页"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def clamp_score(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def pct(value: float) -> int:
    return clamp_score(value * 100)


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def compact(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value.lower())


def contains_any(text: str, terms: list[str] | set[str]) -> bool:
    low = text.lower()
    return any(str(term).lower() in low for term in terms)


def count_hits(text: str, terms: list[str] | set[str]) -> int:
    low = text.lower()
    return sum(1 for term in terms if str(term).lower() in low)


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def candidate_path(project: Path, explicit: str | None, candidates: list[str]) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = project / path
        return path if path.exists() else path
    for item in candidates:
        path = project / item
        if path.exists():
            return path
    return None


def read_json_optional(path: Path | None) -> Any:
    if not path or not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def iter_slides(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        slides = payload.get("slides") or payload.get("slide_plan") or []
    elif isinstance(payload, list):
        slides = payload
    else:
        slides = []
    return [item for item in slides if isinstance(item, dict)]


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [norm(item) for item in value if norm(item)]
    if norm(value):
        return [norm(value)]
    return []


def slide_no(slide: dict[str, Any], fallback: int) -> int:
    try:
        value = int(slide.get("slide_no") or slide.get("page") or fallback)
        return value if value > 0 else fallback
    except Exception:
        return fallback


def slide_title(slide: dict[str, Any]) -> str:
    return norm(slide.get("claim_title") or slide.get("title") or slide.get("headline"))


def slide_text(slide: dict[str, Any]) -> str:
    parts = [
        norm(slide.get(key))
        for key in (
            "claim_title",
            "title",
            "proof_object",
            "concrete_anchor",
            "source_anchor",
            "visual_role",
            "layout_pattern_id",
            "reading_path",
            "speaker_note_goal",
            "qa_risk",
        )
        if norm(slide.get(key))
    ]
    for key in ("content_points", "points", "evidence"):
        parts.extend(normalize_list(slide.get(key)))
    return " ".join(parts)


def title_is_claim(title: str) -> bool:
    value = title.strip()
    if not value:
        return False
    if compact(value) in {compact(item) for item in WEAK_TITLES}:
        return False
    if len(value) < 8:
        return False
    if contains_any(value, GENERIC_PHRASES):
        return False
    return True


def has_source(slide: dict[str, Any]) -> bool:
    return bool(
        normalize_list(slide.get("source_card_ids") or slide.get("source_ids"))
        or norm(slide.get("source_anchor"))
        or norm(slide.get("concrete_anchor"))
    )


def has_layout(slide: dict[str, Any]) -> bool:
    return bool(norm(slide.get("layout_pattern_id") or slide.get("layout_pattern") or slide.get("layout")))


def has_image_text_pattern(slide: dict[str, Any]) -> bool:
    return bool(norm(slide.get("image_text_pattern_id") or slide.get("image_text_pattern") or slide.get("media_need")))


def project_inputs(
    project: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    research_path = candidate_path(
        project,
        args.research_dossier,
        ["research_dossier.md", "sources/research_dossier.md", "sources/source_notes.md"],
    )
    slide_plan_path = candidate_path(project, args.slide_plan, ["slide_plan.json"])
    content_contract_path = candidate_path(project, args.content_contract, ["content_contract.json", "deck_brief.json"])
    visual_contract_path = candidate_path(project, args.visual_contract, ["visual_contract.json"])
    visual_manifest_path = candidate_path(project, args.visual_asset_manifest, ["visual_asset_manifest.json"])
    style_direction_path = candidate_path(project, args.style_direction, ["style_direction.json", "style_direction.md"])
    return {
        "research_path": research_path,
        "research_text": read_text(research_path) if research_path else "",
        "slide_plan_path": slide_plan_path,
        "slide_plan": read_json_optional(slide_plan_path),
        "content_contract_path": content_contract_path,
        "content_contract": read_json_optional(content_contract_path),
        "visual_contract_path": visual_contract_path,
        "visual_contract": read_json_optional(visual_contract_path),
        "visual_manifest_path": visual_manifest_path,
        "visual_manifest": read_json_optional(visual_manifest_path),
        "style_direction_path": style_direction_path,
        "style_direction_text": read_text(style_direction_path) if style_direction_path and style_direction_path.suffix.lower() == ".md" else "",
        "style_direction": read_json_optional(style_direction_path) if style_direction_path and style_direction_path.suffix.lower() == ".json" else None,
    }


def category(
    *,
    category_id: str,
    label: str,
    weight: int,
    score: int,
    evidence: str,
    findings: list[str],
    actions: list[str],
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    blockers = blockers or []
    return {
        "id": category_id,
        "label": label,
        "weight": weight,
        "score": clamp_score(score),
        "passed": clamp_score(score) >= 70 and not blockers,
        "evidence": evidence,
        "findings": findings,
        "recommended_actions": actions,
        "blockers": blockers,
    }


def audit_content_preparation(project: Path, profile: str, weight: int) -> dict[str, Any]:
    try:
        contract = content_preflight_tool.read_json(content_preflight_tool.DEFAULT_CONTRACT)
        inputs = content_preflight_tool.project_inputs(project)
        report = content_preflight_tool.evaluate_project(project, inputs, contract, profile, None)
    except Exception as exc:
        return category(
            category_id="content_preparation",
            label="内容准备包",
            weight=weight,
            score=0,
            evidence=f"content_preflight.py 运行失败：{exc}",
            findings=[],
            actions=["先运行 content_preflight.py，修复内容任务书、问题树、证据卡、页面内核和视觉翻译准备。"],
            blockers=["内容准备前置评估失败"],
        )
    findings = [
        f"内容准备前置分 {report.get('overall_score')}/100。",
        f"内容准备分项："
        + "、".join(f"{item.get('label')} {item.get('score')}" for item in report.get("categories", [])[:6]),
    ]
    blockers = list(report.get("blockers", []))
    actions = list(report.get("recommended_actions", []))
    if not report.get("ok"):
        actions.insert(0, "先修内容准备包，再进入正式大纲、预览或最终生成。")
    return category(
        category_id="content_preparation",
        label="内容准备包",
        weight=weight,
        score=int(report.get("overall_score", 0) or 0),
        evidence="content_preflight.py; artifacts="
        + ",".join(key for key, value in report.get("artifacts", {}).items() if value),
        findings=findings,
        actions=actions,
        blockers=blockers,
    )


def audit_research(text: str, path: Path | None, weight: int) -> dict[str, Any]:
    findings: list[str] = []
    actions: list[str] = []
    blockers: list[str] = []
    if not text.strip():
        return category(
            category_id="research_dossier",
            label="资料档案",
            weight=weight,
            score=0,
            evidence="未找到 research_dossier.md 或 sources/source_notes.md。",
            findings=[],
            actions=["先按 research_dossier_schema.json 写资料档案，再进入大纲和视觉计划。"],
            blockers=["缺资料档案"],
        )
    score = 18
    length = len(text)
    if length >= 1200:
        score += 12
        findings.append("资料档案长度足够承载证据库。")
    elif length >= 500:
        score += 6
        actions.append("资料档案偏短，补充证据卡、视觉机会和缺口。")
    else:
        actions.append("资料档案过短，容易导致大纲泛化。")

    matched_groups = []
    for group_id, terms in SECTION_GROUPS.items():
        if contains_any(text, terms):
            matched_groups.append(group_id)
            score += 6
    urls = len(re.findall(r"https?://", text))
    source_ids = len(re.findall(r"\b(?:S|SC|SRC)[-_][A-Za-z0-9_-]+\b", text))
    slide_links = len(re.findall(r"(?:第\s*\d+\s*页|slide\s*\d+|supports?_slide)", text, flags=re.I))
    if urls or source_ids:
        score += min(12, (urls + source_ids) * 2)
        findings.append(f"检测到 {urls} 个 URL、{source_ids} 个来源 ID。")
    else:
        actions.append("为核心事实补来源 URL、文件路径或 source_id。")
    if slide_links:
        score += min(8, slide_links * 2)
    else:
        actions.append("补充“证据支撑哪一页”的页面映射。")
    missing_groups = sorted(set(SECTION_GROUPS) - set(matched_groups))
    if missing_groups:
        actions.append("补齐资料档案章节：" + "、".join(missing_groups))
    if "gaps" not in matched_groups:
        blockers.append("缺冲突/缺口记录")
    if "visual" not in matched_groups:
        actions.append("补候选图片、可生成主视觉和可图解机会。")
    return category(
        category_id="research_dossier",
        label="资料档案",
        weight=weight,
        score=score,
        evidence=f"{path or 'inline'}; sections={','.join(matched_groups) or 'none'}; chars={length}",
        findings=findings,
        actions=actions,
        blockers=blockers,
    )


def audit_story(slides: list[dict[str, Any]], content: Any, weight: int) -> dict[str, Any]:
    findings: list[str] = []
    actions: list[str] = []
    blockers: list[str] = []
    if not slides:
        return category(
            category_id="story_outline",
            label="叙事大纲",
            weight=weight,
            score=0,
            evidence="slide_plan.json 缺失或没有 slides。",
            findings=[],
            actions=["先生成 slide_plan.json，并按 story_outline_contract.json 补齐每页叙事字段。"],
            blockers=["缺 slide_plan.json 或 slides"],
        )
    mainline = slides
    total = len(mainline)
    claim_count = sum(1 for slide in mainline if title_is_claim(slide_title(slide)))
    proof_count = sum(1 for slide in mainline if norm(slide.get("proof_object")))
    source_count = sum(1 for slide in mainline if has_source(slide))
    visual_count = sum(1 for slide in mainline if norm(slide.get("visual_role")))
    transition_count = sum(1 for slide in mainline if norm(slide.get("transition_from_previous") or slide.get("speaker_note_goal")))
    deck_fields = []
    if isinstance(content, dict):
        for key in ("audience", "use_context", "current_state", "desired_state", "central_thesis", "purpose", "stakes"):
            if content.get(key):
                deck_fields.append(key)
    score = 10
    score += 18 * ratio(claim_count, total)
    score += 17 * ratio(proof_count, total)
    score += 17 * ratio(source_count, total)
    score += 14 * ratio(visual_count, total)
    score += 12 * ratio(transition_count, total)
    score += min(12, len(deck_fields) * 2)
    findings.append(f"{claim_count}/{total} 页有判断式标题，{proof_count}/{total} 页有证明对象。")
    findings.append(f"{source_count}/{total} 页有来源或具体锚点，{visual_count}/{total} 页有视觉角色。")
    if claim_count / total < 0.65:
        blockers.append("判断式标题覆盖不足")
        actions.append("把标签标题改成能独立成立的观点句。")
    if proof_count / total < 0.7:
        actions.append("为每页补唯一证明对象，删除一页多主张。")
    if source_count / total < 0.6:
        actions.append("为主线页面补来源卡、source_anchor 或 concrete_anchor。")
    if transition_count / total < 0.4:
        actions.append("补转场关系或 speaker_note_goal，让大纲成为叙事链。")
    if len(deck_fields) < 4:
        actions.append("在 content_contract.json 补受众、当前状态、目标状态、中心论点和使用场景。")
    return category(
        category_id="story_outline",
        label="叙事大纲",
        weight=weight,
        score=score,
        evidence=f"slides={total}; deck_fields={','.join(deck_fields) or 'none'}",
        findings=findings,
        actions=actions,
        blockers=blockers,
    )


def audit_copy(slides: list[dict[str, Any]], weight: int) -> dict[str, Any]:
    findings: list[str] = []
    actions: list[str] = []
    blockers: list[str] = []
    if not slides:
        return category(
            category_id="slide_copy",
            label="页面文案",
            weight=weight,
            score=0,
            evidence="没有可审计页面。",
            findings=[],
            actions=["先生成 slide_plan.json。"],
            blockers=["缺页面文案"],
        )
    total = len(slides)
    claim_titles = 0
    concise_points = 0
    concrete_anchors = 0
    weak_slides: list[int] = []
    generic_slides: list[int] = []
    for idx, slide in enumerate(slides, start=1):
        title = slide_title(slide)
        if title_is_claim(title):
            claim_titles += 1
        else:
            weak_slides.append(slide_no(slide, idx))
        points = normalize_list(slide.get("content_points") or slide.get("points"))
        point_chars = sum(len(item) for item in points)
        if 1 <= len(points) <= 4 and point_chars <= 180:
            concise_points += 1
        anchor = norm(slide.get("concrete_anchor") or slide.get("source_anchor") or slide.get("proof_object"))
        if len(anchor) >= 10:
            concrete_anchors += 1
        if contains_any(slide_text(slide), GENERIC_PHRASES):
            generic_slides.append(slide_no(slide, idx))
    score = 8
    score += 35 * ratio(claim_titles, total)
    score += 25 * ratio(concise_points, total)
    score += 22 * ratio(concrete_anchors, total)
    score += 10 * (1 - ratio(len(generic_slides), total))
    findings.append(f"{claim_titles}/{total} 页标题像判断句；{concise_points}/{total} 页正文数量和长度较克制。")
    if weak_slides:
        actions.append("重写弱标题页：" + ", ".join(str(item) for item in weak_slides[:12]))
    if generic_slides:
        actions.append("替换泛化表达页：" + ", ".join(str(item) for item in generic_slides[:12]))
    if claim_titles / total < 0.65:
        blockers.append("多数标题不是判断句")
    if concise_points / total < 0.6:
        actions.append("把每页正文压到 2-4 条，并让每条服务主标题。")
    if concrete_anchors / total < 0.6:
        actions.append("为页面补具体人物、数字、原文、场景或来源锚点。")
    return category(
        category_id="slide_copy",
        label="页面文案",
        weight=weight,
        score=score,
        evidence=f"slides={total}; weak_titles={len(weak_slides)}; generic={len(generic_slides)}",
        findings=findings,
        actions=actions,
        blockers=blockers,
    )


def audit_visual_system(
    slides: list[dict[str, Any]],
    visual_contract: Any,
    style_direction: Any,
    style_text: str,
    weight: int,
) -> dict[str, Any]:
    findings: list[str] = []
    actions: list[str] = []
    blockers: list[str] = []
    visual_text = " ".join(
        [
            json.dumps(visual_contract, ensure_ascii=False) if visual_contract is not None else "",
            json.dumps(style_direction, ensure_ascii=False) if style_direction is not None else "",
            style_text,
        ]
    )
    score = 10 if visual_text.strip() else 0
    groups = {
        "字体": ["字体", "font", "typography", "字号", "字重"],
        "色彩": ["色彩", "palette", "color", "主色", "辅助色"],
        "布局节奏": ["布局", "layout", "grid", "节奏", "密度", "留白"],
        "图像风格": ["图片", "image", "主视觉", "art direction", "生图", "材质", "镜头"],
        "反俗套": ["反俗套", "anti", "禁用", "避免", "不要", "fallback"],
    }
    matched = []
    for label, terms in groups.items():
        if contains_any(visual_text, terms):
            matched.append(label)
            score += 10
    total = len(slides) or 1
    layout_count = sum(1 for slide in slides if has_layout(slide))
    image_text_count = sum(1 for slide in slides if has_image_text_pattern(slide))
    reading_count = sum(1 for slide in slides if norm(slide.get("reading_path")))
    score += 18 * ratio(layout_count, total)
    score += 12 * ratio(image_text_count, total)
    score += 10 * ratio(reading_count, total)
    findings.append(f"视觉系统覆盖：{','.join(matched) or '无'}。")
    findings.append(f"{layout_count}/{total} 页有布局模式，{reading_count}/{total} 页有阅读路径。")
    if not visual_text.strip():
        blockers.append("缺 visual_contract/style_direction")
        actions.append("先写 visual_contract.json 或 style_direction.md，锁定字体、色彩、版式节奏和图像风格。")
    if len(matched) < 4:
        actions.append("补齐视觉系统：字体、色彩、布局节奏、图像风格、反俗套约束。")
    if layout_count / total < 0.7:
        actions.append("为每页指定 layout_pattern_id 或明确版式模式。")
    if reading_count / total < 0.5:
        actions.append("为关键页补阅读路径，防止页面只堆元素。")
    return category(
        category_id="visual_system",
        label="视觉系统",
        weight=weight,
        score=score,
        evidence=f"matched={','.join(matched) or 'none'}; layout={layout_count}/{total}",
        findings=findings,
        actions=actions,
        blockers=blockers,
    )


def extract_assets(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("assets", "items", "visual_assets", "image_assets", "queue"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def audit_images(visual_manifest: Any, slides: list[dict[str, Any]], profile: str, allow_missing: bool, weight: int) -> dict[str, Any]:
    findings: list[str] = []
    actions: list[str] = []
    blockers: list[str] = []
    assets = extract_assets(visual_manifest)
    total_assets = len(assets)
    if not assets:
        score = 45 if allow_missing and any(norm(slide.get("visual_role") or slide.get("media_need")) for slide in slides) else 0
        if not allow_missing:
            blockers.append("缺视觉资产或图片艺术指导")
        return category(
            category_id="image_art_direction",
            label="图片艺术指导",
            weight=weight,
            score=score,
            evidence="visual_asset_manifest.json 缺失或没有 assets。",
            findings=[],
            actions=["运行 plan_visual_assets.py 和 image_art_direction.py，生成带安全区、负面提示和前景边界的图片队列。"],
            blockers=blockers,
        )
    art_fields = ("art_direction", "composition", "safe_area", "foreground_boundary", "prompt", "negative_prompt", "text_policy")
    role_count = sum(1 for item in assets if norm(item.get("image_role") or item.get("role") or item.get("purpose")))
    content_link_count = sum(1 for item in assets if norm(item.get("content_link") or item.get("supports_claim")))
    prompt_count = sum(1 for item in assets if norm(item.get("prompt") or item.get("positive_prompt")))
    negative_count = sum(1 for item in assets if contains_any(norm(item.get("negative_prompt")), ["text", "文字", "logo", "fake", "假"]))
    safe_count = sum(1 for item in assets if norm(item.get("safe_area")))
    boundary_count = sum(1 for item in assets if norm(item.get("foreground_boundary")))
    art_complete = 0
    for item in assets:
        hits = sum(1 for field in art_fields if norm(item.get(field)))
        if hits >= 5:
            art_complete += 1
    score = 8
    score += 14 * ratio(role_count, total_assets)
    score += 14 * ratio(content_link_count, total_assets)
    score += 18 * ratio(prompt_count, total_assets)
    score += 16 * ratio(negative_count, total_assets)
    score += 16 * ratio(safe_count, total_assets)
    score += 14 * ratio(boundary_count, total_assets)
    findings.append(f"{art_complete}/{total_assets} 个资产有较完整艺术指导。")
    findings.append(f"{safe_count}/{total_assets} 个资产声明文字安全区，{negative_count}/{total_assets} 个资产有有效负面提示。")
    if safe_count / total_assets < 0.75:
        blockers.append("多数图片缺文字安全区")
        actions.append("为主视觉和背景补 safe_area，明确低细节文字区域。")
    if boundary_count / total_assets < 0.65:
        actions.append("补 foreground_boundary，明确哪些文字、标签、图表必须保持可编辑。")
    if negative_count / total_assets < 0.75:
        actions.append("负面提示必须禁止可见文字、假 Logo、假截图、假数据和水印。")
    if prompt_count / total_assets < 0.8:
        actions.append("为 planned/queued 图片补可执行 prompt。")
    if profile in {"final", "release"} and art_complete / total_assets < 0.7:
        blockers.append("final/release 档图片艺术指导不完整")
    return category(
        category_id="image_art_direction",
        label="图片艺术指导",
        weight=weight,
        score=score,
        evidence=f"assets={total_assets}; prompts={prompt_count}; safe_area={safe_count}; negative={negative_count}",
        findings=findings,
        actions=actions,
        blockers=blockers,
    )


def rubric_weights(rubric: dict[str, Any]) -> dict[str, int]:
    return {str(item["id"]): int(item.get("weight", 0)) for item in rubric.get("categories", []) if isinstance(item, dict) and item.get("id")}


def profile_rules(rubric: dict[str, Any], profile: str) -> dict[str, Any]:
    profiles = rubric.get("profiles", {})
    fallback = profiles.get("plan", {})
    selected = profiles.get(profile, fallback)
    return selected if isinstance(selected, dict) else fallback


def evaluate_project(project: Path, inputs: dict[str, Any], rubric: dict[str, Any], profile: str, min_score: int | None) -> dict[str, Any]:
    weights = rubric_weights(rubric)
    profile_rule = profile_rules(rubric, profile)
    threshold = int(min_score or profile_rule.get("minimum_overall_score", 80))
    category_threshold = int(profile_rule.get("minimum_category_score", 70))
    allow_missing_visual_assets = bool(profile_rule.get("allow_missing_visual_assets", False))
    slide_plan = inputs.get("slide_plan")
    slides = iter_slides(slide_plan)
    content = inputs.get("content_contract") if isinstance(inputs.get("content_contract"), dict) else {}
    categories = [
        audit_content_preparation(project, profile, weights.get("content_preparation", 18)),
        audit_research(inputs.get("research_text", ""), inputs.get("research_path"), weights.get("research_dossier", 24)),
        audit_story(slides, content, weights.get("story_outline", 24)),
        audit_copy(slides, weights.get("slide_copy", 20)),
        audit_visual_system(slides, inputs.get("visual_contract"), inputs.get("style_direction"), inputs.get("style_direction_text", ""), weights.get("visual_system", 17)),
        audit_images(inputs.get("visual_manifest"), slides, profile, allow_missing_visual_assets, weights.get("image_art_direction", 15)),
    ]
    total_weight = sum(item["weight"] for item in categories) or 1
    overall = clamp_score(sum(item["score"] * item["weight"] for item in categories) / total_weight)
    blockers: list[str] = []
    warnings: list[str] = []
    actions: list[str] = []
    for item in categories:
        blockers.extend(item.get("blockers", []))
        actions.extend(item.get("recommended_actions", []))
        if item["score"] < category_threshold:
            warnings.append(f"{item['label']} 分数低于 {category_threshold}: {item['score']}")
    gate_ready = overall >= threshold and not blockers and not warnings
    files = {}
    for key in ("research_path", "slide_plan_path", "content_contract_path", "visual_contract_path", "visual_manifest_path", "style_direction_path"):
        value = inputs.get(key)
        files[key] = str(value) if value else ""
    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/top_quality_plan.py",
        "generated_at": utc_now(),
        "project": str(project),
        "profile": profile,
        "minimum_overall_score": threshold,
        "minimum_category_score": category_threshold,
        "overall_score": overall,
        "ok": gate_ready,
        "gate_ready": gate_ready,
        "files": files,
        "categories": categories,
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        "recommended_actions": list(dict.fromkeys(actions))[:24],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 顶级质量前置评估",
        "",
        f"- OK: `{str(report.get('ok')).lower()}`",
        f"- 档位：`{report.get('profile')}`",
        f"- 总分：`{report.get('overall_score')}` / 100",
        f"- 门槛：`{report.get('minimum_overall_score')}`",
    ]
    if report.get("blockers"):
        lines.extend(["", "## 阻塞项", ""])
        lines.extend(f"- {item}" for item in report["blockers"])
    if report.get("warnings"):
        lines.extend(["", "## 警告", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    lines.extend(["", "## 分项", ""])
    for item in report.get("categories", []):
        lines.append(f"### {item['label']} `{item['score']}`")
        lines.append("")
        lines.append(f"- 证据：{item.get('evidence', '')}")
        for finding in item.get("findings", [])[:3]:
            lines.append(f"- 发现：{finding}")
        for blocker in item.get("blockers", [])[:3]:
            lines.append(f"- 阻塞：{blocker}")
        lines.append("")
    if report.get("recommended_actions"):
        lines.extend(["## 建议动作", ""])
        lines.extend(f"- {item}" for item in report["recommended_actions"])
    return "\n".join(lines).rstrip() + "\n"


def self_test_inputs(project: Path) -> dict[str, Any]:
    research = """
# 资料档案
## 任务范围
受众是创作者，使用场景是 15 分钟分享，交付可编辑 PPTX。
## 已验证事实
- SC-01：2026 年 AI 工具从单点聊天走向工作流，来源 https://example.com/report。
- SC-02：创作者最关心稳定产出、分发和复用，来源 https://example.com/survey。
## 证据卡
- id: SC-01; claim: AI 工具正在从尝鲜变成流程基础设施; evidence: 报告提到工作流采用率提升; supports_slide: 2,3; visual_opportunity: 桌面工作流主视觉。
- id: SC-02; claim: 创作者要的不是更多模型，而是可复用生产线; supports_slide: 4; visual_opportunity: 一条生产线隐喻。
## 解释判断
这些事实说明用户价值从模型能力转向系统产出。
## 冲突与缺口
部分平台数据缺少公开口径，标记为 missing evidence。
## 候选图片与视觉机会
生成主视觉：工作台、卡片流、真实质感，不使用假截图。
## 权利与风险
禁止伪造平台截图、品牌标志和用户数据。
## 页面支撑映射
第 2 页由 SC-01 支撑，第 4 页由 SC-02 支撑。
"""
    slide_plan = {
        "slides": [
            {
                "slide_no": 1,
                "claim_title": "AI 创作正在从尝鲜走向稳定生产线",
                "slide_role": "opening",
                "proof_object": "创作流程变化",
                "source_card_ids": ["SC-01"],
                "concrete_anchor": "报告中的工作流采用率变化",
                "content_points": ["从单点聊天转向可复用流程", "创作者更关心稳定产出"],
                "visual_role": "cover main visual",
                "layout_pattern_id": "L01",
                "image_text_pattern_id": "ITL01",
                "reading_path": "标题 -> 主视觉 -> 关键判断",
                "transition_from_previous": "开场建立问题",
                "speaker_note_goal": "把焦点从模型热闹拉回产出系统",
                "qa_risk": "不要把趋势说成所有人都已经完成转型",
            },
            {
                "slide_no": 2,
                "claim_title": "真正的门槛不是会用模型，而是能复用流程",
                "slide_role": "evidence",
                "proof_object": "复用流程",
                "source_card_ids": ["SC-02"],
                "concrete_anchor": "创作者调研中的稳定产出诉求",
                "content_points": ["流程决定一致性", "资产沉淀决定下次速度"],
                "visual_role": "diagram background",
                "layout_pattern_id": "L12",
                "image_text_pattern_id": "ITL03",
                "reading_path": "判断标题 -> 左侧流程图 -> 右侧证据",
                "transition_from_previous": "回答开场判断为什么成立",
                "speaker_note_goal": "解释生产线比单点模型更重要",
                "qa_risk": "流程图不要画得像软件 UI",
            },
        ]
    }
    content = {
        "topic": "AI 创作生产线",
        "audience": "AI 创作者",
        "use_context": "15 分钟分享",
        "current_state": "工具很多但流程松散",
        "desired_state": "建立可复用生产线",
        "central_thesis": "AI 创作价值正在从模型尝鲜转向流程复用",
        "success_criteria": ["观众能复述主判断", "观众知道如何开始搭生产线"],
        "constraints": ["不伪造平台截图", "不使用无来源数据"],
        "delivery_format": "editable_pptx",
        "narrative_arc": "问题现场 -> 证据 -> 机制 -> 行动",
        "turning_point": "从追新模型转向建设流程资产",
        "stakes": "如果没有流程，产出不可复制。",
    }
    visual = {
        "typography": "Noto Sans CJK SC + Inter",
        "palette": "墨黑、雾白、冷绿点缀",
        "layout_rhythm": "开场大图、证据密页、图解页、呼吸页交替",
        "image_style": "editorial still-life, tactile desk, no fake UI",
        "image_text_relation": "主视觉保留左侧文字安全区，图解页中央留低细节背景。",
        "layout_reason": "开场用大图建立问题现场，证据页使用密度更高的来源锚点，机制页使用流程图。",
        "diagram_plan": "流程、对比、证据卡矩阵。",
        "anti_slop": "禁止紫色渐变、装饰球、假玻璃和卡片堆",
    }
    manifest = {
        "assets": [
            {
                "asset_id": "img-001",
                "slide_no": 1,
                "image_role": "cover background",
                "content_link": "AI 创作从尝鲜走向生产线",
                "art_direction": "cinematic editorial workbench with calm negative space",
                "composition": "subject on right third, left 45% quiet title-safe area",
                "safe_area": "left 45% low-detail dark field",
                "camera": "50mm editorial still-life",
                "lighting": "soft directional studio light",
                "material": "paper, glass, matte metal",
                "foreground_boundary": "title, subtitle, labels stay editable",
                "prompt": "editorial AI creator workbench, tactile materials, no text, left negative space",
                "negative_prompt": "visible text, logo, watermark, fake screenshot, fake chart, fake data",
                "text_policy": "none",
                "status": "planned",
            },
            {
                "asset_id": "img-002",
                "slide_no": 2,
                "image_role": "diagram background",
                "content_link": "复用流程决定一致性",
                "art_direction": "quiet material field for editable process diagram",
                "composition": "low contrast central field with subtle depth",
                "safe_area": "central 70% low-detail area",
                "camera": "orthographic macro",
                "lighting": "even softbox",
                "material": "matte paper layers",
                "foreground_boundary": "nodes, arrows, labels and metrics stay editable",
                "prompt": "subtle layered paper field for editable workflow diagram, no text",
                "negative_prompt": "visible text, labels, logo, fake UI, fake chart, watermark",
                "text_policy": "none",
                "status": "planned",
            },
        ]
    }
    questions = {
        "root_question": "为什么 AI 创作者需要从模型尝鲜转向流程生产线？",
        "subquestions": [
            "哪些事实说明创作者痛点已经从工具数量转向稳定产出？",
            "流程复用如何提升内容一致性？",
            "哪些资产最适合被沉淀？",
        ],
        "counter_questions": ["是不是只要模型更强就够了？", "流程会不会限制创意？"],
        "must_verify": ["工具采用变化", "创作者稳定产出诉求", "流程复用案例"],
        "source_plan": ["行业报告", "创作者访谈", "产品案例"],
        "visual_questions": ["生产线能否用工作台主视觉表达？", "流程复用是否适合画成节点图？"],
        "known_gaps": ["部分平台数据缺公开口径，标记 missing evidence。"],
    }
    source_cards = {
        "cards": [
            {
                "id": "SC-01",
                "claim": "AI 工具正在从单点聊天走向工作流。",
                "evidence": "报告显示工作流类 AI 工具采用率提升。",
                "source_ids": ["S01"],
                "source_url_or_path": "https://example.com/report",
                "confidence": "medium",
                "supports_questions": ["root_question"],
                "supports_slide": [1, 2],
                "visual_opportunity": "工作台和流程节点主视觉",
            },
            {
                "id": "SC-02",
                "claim": "创作者更关心稳定产出和复用。",
                "evidence": "调研样本中稳定产出、分发和复用被反复提及。",
                "source_ids": ["S02"],
                "source_url_or_path": "https://example.com/survey",
                "confidence": "medium",
                "supports_questions": ["subquestions"],
                "supports_slide": [2],
                "visual_opportunity": "内容资产库图解",
            },
            {
                "id": "SC-03",
                "claim": "流程复用能减少每次从零开始的决策成本。",
                "evidence": "案例显示模板、检查表和素材库能缩短生产路径。",
                "source_ids": ["S03"],
                "source_url_or_path": "case-notes.md",
                "confidence": "medium",
                "supports_questions": ["counter_questions"],
                "supports_slide": [2],
                "visual_opportunity": "前后对比图",
            },
        ]
    }
    page_kernel_map = {
        "page_kernels": [
            {
                "slide_no": slide["slide_no"],
                "claim_title": slide["claim_title"],
                "proof_object": slide["proof_object"],
                "source_card_ids": slide["source_card_ids"],
                "concrete_anchor": slide["concrete_anchor"],
                "audience_shift": "从模型热闹转向产出系统" if slide["slide_no"] == 1 else "从工具清单转向方法系统",
                "content_role": slide["slide_role"],
                "visual_role": slide["visual_role"],
                "layout_reason": slide["reading_path"],
                "transition_from_previous": slide["transition_from_previous"],
            }
            for slide in slide_plan["slides"]
        ]
    }
    write_text(project / "research_dossier.md", research)
    write_json(project / "slide_plan.json", slide_plan)
    write_json(project / "content_contract.json", content)
    write_json(project / "research_questions.json", questions)
    write_json(project / "sources" / "source_cards.json", source_cards)
    write_json(project / "page_kernel_map.json", page_kernel_map)
    write_json(project / "visual_contract.json", visual)
    write_json(project / "visual_asset_manifest.json", manifest)
    write_json(project / "style_direction.json", visual)
    return {
        "research_path": project / "research_dossier.md",
        "research_text": research,
        "slide_plan_path": project / "slide_plan.json",
        "slide_plan": slide_plan,
        "content_contract_path": project / "content_contract.json",
        "content_contract": content,
        "visual_contract_path": project / "visual_contract.json",
        "visual_contract": visual,
        "visual_manifest_path": project / "visual_asset_manifest.json",
        "visual_manifest": manifest,
        "style_direction_path": project / "style_direction.json",
        "style_direction": visual,
        "style_direction_text": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit top-quality readiness before qiaomu-ppt preview or production.")
    parser.add_argument("project", nargs="?", type=Path, help="Qiaomu PPT project directory.")
    parser.add_argument("--profile", choices=["plan", "draft", "final", "release"], default="plan")
    parser.add_argument("--min-score", type=int, help="Override profile minimum overall score.")
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--research-dossier")
    parser.add_argument("--slide-plan")
    parser.add_argument("--content-contract")
    parser.add_argument("--visual-contract")
    parser.add_argument("--visual-asset-manifest")
    parser.add_argument("--style-direction")
    parser.add_argument("--output", type=Path, default=SKILL_DIR / "reports" / "top-quality-plan.json")
    parser.add_argument("--markdown", type=Path, default=SKILL_DIR / "reports" / "top-quality-plan.md")
    parser.add_argument("--self-test", action="store_true", help="Run built-in positive fixture without reading a project.")
    args = parser.parse_args()

    rubric = read_json(args.rubric)
    if args.self_test:
        with tempfile.TemporaryDirectory(prefix="qiaomu-ppt-top-quality-") as tmpdir:
            project = Path(tmpdir)
            inputs = self_test_inputs(project)
            report = evaluate_project(project, inputs, rubric, args.profile, args.min_score)
    else:
        if not args.project:
            raise SystemExit("project is required unless --self-test is used")
        project = args.project.expanduser().resolve()
        inputs = project_inputs(project, args)
        report = evaluate_project(project, inputs, rubric, args.profile, args.min_score)

    write_json(args.output, report)
    write_text(args.markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
