#!/usr/bin/env python3
"""Audit first-step content preparation before qiaomu-ppt outline generation."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CONTRACT = SKILL_DIR / "data" / "content_preparation_contract.json"

ARTIFACT_CANDIDATES = {
    "research_archive": ["task_manifest.json", "research_archive.json", "README.md"],
    "content_brief": ["content_brief.json", "deck_brief.json", "content_contract.json", "deck_brief.md"],
    "question_tree": ["research_questions.json", "research_question_tree.json", "question_tree.json", "research_questions.md"],
    "research_dossier": ["research_dossier.md", "sources/research_dossier.md", "sources/source_notes.md"],
    "source_synthesis": ["content_report.md", "内容母稿.md", "内容母稿-*.md", "content_synthesis.md", "source_synthesis.md"],
    "evidence_matrix": ["evidence_matrix.json", "source_evidence_matrix.json", "sources/source_cards.json", "source_cards.json"],
    "page_kernel_map": ["page_kernel_map.json", "slide_kernel_map.json", "slide_plan.json"],
    "visual_translation": ["visual_translation_plan.json", "visual_contract.json", "style_direction.json", "style_direction.md"],
}

PREP_WEIGHTS = {
    "research_archive": 8,
    "content_brief": 14,
    "question_tree": 14,
    "evidence_matrix": 18,
    "source_synthesis": 16,
    "story_premise": 12,
    "page_kernels": 12,
    "visual_translation": 6,
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
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: Path | None) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path and path.exists() else ""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json_optional(path: Path | None) -> Any:
    if not path or not path.exists() or path.suffix.lower() not in {".json"}:
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clamp_score(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def contains_any(text: str, terms: list[str] | set[str]) -> bool:
    low = text.lower()
    return any(str(term).lower() in low for term in terms)


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [norm(item) for item in value if norm(item)]
    if norm(value):
        return [norm(value)]
    return []


def candidate_path(project: Path, explicit: str | None, candidates: list[str]) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = project / path
        return path
    for item in candidates:
        if "*" in item:
            matches = sorted(project.glob(item))
            if matches:
                return matches[0]
            continue
        path = project / item
        if path.exists():
            return path
    return None


def project_inputs(project: Path, args: argparse.Namespace | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for artifact_id, candidates in ARTIFACT_CANDIDATES.items():
        explicit = getattr(args, artifact_id.replace("-", "_"), None) if args is not None else None
        path = candidate_path(project, explicit, candidates)
        payload[f"{artifact_id}_path"] = path
        payload[f"{artifact_id}_text"] = read_text(path)
        payload[f"{artifact_id}_json"] = read_json_optional(path)
    return payload


def text_blob(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            parts.append(json.dumps(value, ensure_ascii=False))
        else:
            parts.append(str(value))
    return " ".join(parts)


def value_at(payload: Any, key: str) -> Any:
    if not isinstance(payload, dict):
        return None
    if key in payload:
        return payload.get(key)
    aliases = {
        "delivery_format": ["final_delivery", "format", "output_format"],
        "success_criteria": ["success", "quality_bar", "done_definition"],
        "constraints": ["boundary", "risks", "must_not"],
        "root_question": ["core_question", "main_question"],
        "counter_questions": ["objections", "skeptical_questions", "反方问题"],
        "must_verify": ["verification_questions", "facts_to_verify", "必须验证"],
        "visual_questions": ["visual_opportunities", "visual_prompts"],
        "known_gaps": ["gaps", "missing_evidence"],
        "central_thesis": ["thesis", "main_claim"],
        "current_state": ["before_state", "audience_current_state"],
        "desired_state": ["after_state", "audience_desired_state"],
    }
    for alias in aliases.get(key, []):
        if alias in payload:
            return payload.get(alias)
    return None


def has_field(payload: Any, text: str, key: str) -> bool:
    value = value_at(payload, key)
    if isinstance(value, list):
        return any(norm(item) for item in value)
    if norm(value):
        return True
    readable = key.replace("_", " ")
    zh_terms = {
        "topic": ["主题"],
        "audience": ["受众", "听众", "读者"],
        "use_context": ["使用场景", "演讲场景", "汇报场景"],
        "current_state": ["当前状态", "现状", "原有认知"],
        "desired_state": ["目标状态", "看完后", "希望相信"],
        "central_thesis": ["中心论点", "核心判断", "主张"],
        "success_criteria": ["成功标准", "验收标准"],
        "constraints": ["边界", "限制", "禁区"],
        "delivery_format": ["交付格式", "输出格式"],
        "root_question": ["核心问题", "主问题"],
        "subquestions": ["子问题", "分问题"],
        "counter_questions": ["反方问题", "质疑", "反驳"],
        "must_verify": ["必须验证", "待验证", "关键事实"],
        "source_plan": ["来源计划", "资料计划"],
        "visual_questions": ["视觉问题", "可视化问题", "视觉机会"],
        "known_gaps": ["缺口", "missing evidence"],
    }
    terms = [readable, key, *zh_terms.get(key, [])]
    return contains_any(text, terms)


def field_coverage(payload: Any, text: str, fields: list[str]) -> tuple[int, list[str], list[str]]:
    present = [field for field in fields if has_field(payload, text, field)]
    missing = [field for field in fields if field not in present]
    return len(present), present, missing


def extract_cards(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("cards", "evidence_cards", "items", "claims", "matrix"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def extract_page_kernels(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("page_kernels", "kernels", "slides", "slide_plan", "pages"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def card_has_source(card: dict[str, Any]) -> bool:
    return bool(
        normalize_list(card.get("source_ids") or card.get("source_id"))
        or norm(card.get("source_url_or_path") or card.get("source_url") or card.get("source_path"))
    )


def card_has_support(card: dict[str, Any]) -> bool:
    return bool(
        normalize_list(card.get("supports_questions"))
        or normalize_list(card.get("supports_slide") or card.get("supports_slides"))
        or normalize_list(card.get("usable_as"))
    )


def card_has_visual(card: dict[str, Any]) -> bool:
    return bool(norm(card.get("visual_opportunity") or card.get("visual_role") or card.get("image_opportunity")))


def kernel_title(kernel: dict[str, Any]) -> str:
    return norm(kernel.get("claim_title") or kernel.get("title") or kernel.get("headline"))


def kernel_has_source(kernel: dict[str, Any]) -> bool:
    return bool(
        normalize_list(kernel.get("source_card_ids") or kernel.get("evidence_card_ids") or kernel.get("source_ids"))
        or norm(kernel.get("concrete_anchor") or kernel.get("source_anchor"))
    )


def title_is_claim(title: str) -> bool:
    if len(title) < 8:
        return False
    if contains_any(title, GENERIC_PHRASES):
        return False
    weak = {"目录", "背景", "问题", "方案", "总结", "结论", "现状", "挑战", "overview", "background", "summary"}
    compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", title.lower())
    return compact not in {re.sub(r"[^\w\u4e00-\u9fff]+", "", item.lower()) for item in weak}


def category(
    *,
    category_id: str,
    label: str,
    weight: int,
    score: float,
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


def audit_content_brief(inputs: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    path = inputs.get("content_brief_path")
    payload = inputs.get("content_brief_json")
    text = inputs.get("content_brief_text", "")
    if not path or (payload is None and not text.strip()):
        return category(
            category_id="content_brief",
            label="内容任务书",
            weight=PREP_WEIGHTS["content_brief"],
            score=0,
            evidence="未找到 content_brief/deck_brief/content_contract。",
            findings=[],
            actions=["先写内容任务书：主题、受众、场景、目标状态、交付格式、边界和成功标准。"],
            blockers=["缺内容任务书"],
        )
    fields = list(contract.get("content_brief_fields", []))
    count, present, missing = field_coverage(payload, text, fields)
    score = 15 + 75 * ratio(count, len(fields))
    if has_field(payload, text, "central_thesis") and has_field(payload, text, "desired_state"):
        score += 10
    blockers: list[str] = []
    actions: list[str] = []
    for required in ("audience", "use_context", "desired_state"):
        if required in missing:
            blockers.append(f"内容任务书缺 {required}")
    if missing:
        actions.append("补内容任务书字段：" + "、".join(missing[:8]))
    return category(
        category_id="content_brief",
        label="内容任务书",
        weight=PREP_WEIGHTS["content_brief"],
        score=score,
        evidence=f"{path}; fields={','.join(present) or 'none'}",
        findings=[f"检测到 {count}/{len(fields)} 个任务书字段。"],
        actions=actions,
        blockers=blockers,
    )


def audit_question_tree(inputs: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    path = inputs.get("question_tree_path")
    payload = inputs.get("question_tree_json")
    text = inputs.get("question_tree_text", "")
    if not path or (payload is None and not text.strip()):
        return category(
            category_id="question_tree",
            label="研究问题树",
            weight=PREP_WEIGHTS["question_tree"],
            score=0,
            evidence="未找到 research_questions/question_tree。",
            findings=[],
            actions=["先把主题拆成核心问题、子问题、反方问题、必须验证事实、来源计划和视觉问题。"],
            blockers=["缺研究问题树"],
        )
    fields = list(contract.get("question_tree_fields", []))
    count, present, missing = field_coverage(payload, text, fields)
    question_marks = len(re.findall(r"[?？]", text_blob(payload, text)))
    list_items = len(re.findall(r"^\s*[-*]\s+", text, flags=re.M))
    score = 12 + 66 * ratio(count, len(fields)) + min(12, question_marks * 2) + min(10, list_items)
    blockers: list[str] = []
    actions: list[str] = []
    for required in ("root_question", "subquestions", "must_verify"):
        if required in missing:
            blockers.append(f"研究问题树缺 {required}")
    if "counter_questions" in missing:
        actions.append("补反方问题或质疑问题，避免只搜支持性材料。")
    if "visual_questions" in missing:
        actions.append("补可视化问题：哪些事实适合图表、时间线、对比、地图或主视觉。")
    if missing:
        actions.append("补研究问题树字段：" + "、".join(missing[:8]))
    return category(
        category_id="question_tree",
        label="研究问题树",
        weight=PREP_WEIGHTS["question_tree"],
        score=score,
        evidence=f"{path}; fields={','.join(present) or 'none'}; question_marks={question_marks}",
        findings=[f"检测到 {count}/{len(fields)} 个问题树字段。"],
        actions=actions,
        blockers=blockers,
    )


def count_image_files(project: Path) -> int:
    suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".svg"}
    roots = [
        project / "sources" / "images",
        project / "assets" / "source-images",
        project / "assets" / "source_visuals",
    ]
    count = 0
    for root in roots:
        if root.exists():
            count += sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)
    return count


def audit_research_archive(project: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    archive_path = inputs.get("research_archive_path")
    archive_text = inputs.get("research_archive_text", "")
    dossier_path = inputs.get("research_dossier_path")
    dossier_text = inputs.get("research_dossier_text", "")
    source_manifest_path = project / "sources" / "source_manifest.json"
    source_notes_path = project / "sources" / "source_notes.md"
    source_cards_path = project / "sources" / "source_cards.json"
    source_manifest = read_json_optional(source_manifest_path)
    source_cards = read_json_optional(source_cards_path)
    source_count = len(source_manifest.get("sources", [])) if isinstance(source_manifest, dict) else 0
    cards = extract_cards(source_cards)
    image_candidates = 0
    if isinstance(source_cards, dict):
        image_candidates = len(source_cards.get("image_candidates") or [])
    image_files = count_image_files(project)
    link_hits = len(re.findall(r"https?://", text_blob(archive_text, dossier_text, source_manifest)))

    score = 0
    if archive_path and read_text(archive_path).strip():
        score += 24
    if dossier_path and dossier_text.strip():
        score += 24
    if source_manifest_path.exists() and source_count:
        score += 18
    if source_notes_path.exists() or cards:
        score += 14
    score += min(12, link_hits * 3)
    if image_candidates or image_files:
        score += 8

    blockers: list[str] = []
    actions: list[str] = []
    if not archive_path:
        blockers.append("缺任务归档索引")
        actions.append("写入 README.md 或 task_manifest.json，说明本次任务的资料、图片、规划和导出产物位置。")
    if not dossier_path:
        blockers.append("缺调研报告")
        actions.append("先写 research_dossier.md，把来源、链接、图片候选、解释判断和缺口沉淀下来。")
    if source_count == 0 and not cards:
        blockers.append("缺来源清单或来源卡")
        actions.append("补 sources/source_manifest.json 和 sources/source_cards.json；搜索结果必须落盘，不只留在聊天里。")
    if not image_candidates and not image_files:
        actions.append("如果素材中有可用图片，把下载/提取图片或图片候选记录进 sources/images、source_cards 或 visual_asset_manifest。")

    findings = [
        f"来源记录 {source_count} 条，证据卡 {len(cards)} 张。",
        f"链接锚点 {link_hits} 个，图片候选 {image_candidates} 个，本地图片 {image_files} 个。",
    ]
    return category(
        category_id="research_archive",
        label="调研归档包",
        weight=PREP_WEIGHTS["research_archive"],
        score=score,
        evidence=f"index={archive_path or 'missing'}; dossier={dossier_path or 'missing'}; source_manifest={source_manifest_path if source_manifest_path.exists() else 'missing'}",
        findings=findings,
        actions=actions,
        blockers=blockers,
    )


def audit_evidence_matrix(inputs: dict[str, Any]) -> dict[str, Any]:
    path = inputs.get("evidence_matrix_path")
    payload = inputs.get("evidence_matrix_json")
    cards = extract_cards(payload)
    research_text = inputs.get("research_dossier_text", "")
    if not cards and research_text.strip():
        # Markdown dossier can still be useful, but it is weaker than structured cards.
        source_hits = len(re.findall(r"https?://|\b(?:S|SC|SRC|C)[-_]?\d+\b", research_text))
        score = 25 + min(35, source_hits * 4)
        return category(
            category_id="evidence_matrix",
            label="证据卡矩阵",
            weight=PREP_WEIGHTS["evidence_matrix"],
            score=score,
            evidence=f"{inputs.get('research_dossier_path')}; structured_cards=0; source_hits={source_hits}",
            findings=[f"资料档案里检测到 {source_hits} 个来源锚点，但缺结构化证据卡。"],
            actions=["把核心来源整理成 evidence_matrix.json 或 sources/source_cards.json，标注 claim、evidence、source 和 supports_slide。"],
            blockers=["缺结构化证据卡"],
        )
    if not cards:
        return category(
            category_id="evidence_matrix",
            label="证据卡矩阵",
            weight=PREP_WEIGHTS["evidence_matrix"],
            score=0,
            evidence="未找到 evidence_matrix/source_cards。",
            findings=[],
            actions=["先生成或整理证据卡矩阵，每张卡要有 claim、evidence、source、confidence、页面支撑和视觉机会。"],
            blockers=["缺证据卡矩阵"],
        )
    total = len(cards)
    claim_count = sum(1 for card in cards if norm(card.get("claim")))
    evidence_count = sum(1 for card in cards if norm(card.get("evidence")))
    source_count = sum(1 for card in cards if card_has_source(card))
    confidence_count = sum(1 for card in cards if norm(card.get("confidence")))
    support_count = sum(1 for card in cards if card_has_support(card))
    visual_count = sum(1 for card in cards if card_has_visual(card))
    score = 8
    score += 14 * ratio(claim_count, total)
    score += 18 * ratio(evidence_count, total)
    score += 20 * ratio(source_count, total)
    score += 12 * ratio(confidence_count, total)
    score += 18 * ratio(support_count, total)
    score += 10 * ratio(visual_count, total)
    if total >= 8:
        score += 8
    elif total >= 4:
        score += 4
    blockers: list[str] = []
    actions: list[str] = []
    if source_count / total < 0.75:
        blockers.append("多数证据卡缺来源")
        actions.append("为每张核心证据卡补 source_ids、URL 或文件路径。")
    if support_count / total < 0.55:
        actions.append("补 supports_questions 或 supports_slide，让证据能映射到页面。")
    if visual_count / total < 0.35:
        actions.append("为关键证据补 visual_opportunity，提前判断图表、对比、时间线或主视觉可能性。")
    return category(
        category_id="evidence_matrix",
        label="证据卡矩阵",
        weight=PREP_WEIGHTS["evidence_matrix"],
        score=score,
        evidence=f"{path}; cards={total}; source={source_count}; support={support_count}; visual={visual_count}",
        findings=[
            f"{claim_count}/{total} 张卡有主张，{evidence_count}/{total} 张卡有证据。",
            f"{source_count}/{total} 张卡有来源，{support_count}/{total} 张卡有页面或问题支撑。",
        ],
        actions=actions,
        blockers=blockers,
    )


def audit_source_synthesis(inputs: dict[str, Any]) -> dict[str, Any]:
    path = inputs.get("source_synthesis_path")
    text = inputs.get("source_synthesis_text", "")
    if not path or not text.strip():
        return category(
            category_id="source_synthesis",
            label="内容母稿",
            weight=PREP_WEIGHTS["source_synthesis"],
            score=0,
            evidence="未找到 content_report.md / 内容母稿*.md。",
            findings=[],
            actions=[
                "先写内容母稿，把来源资料消化成有主张、有结构、有判断和边界的可读长文。",
                "不要把 research_dossier.md 或链接清单当成内容母稿；资料档案解决可追溯，内容母稿解决观点质量。",
            ],
            blockers=["缺内容母稿"],
        )

    length = len(text)
    groups = {
        "中心判断": ["中心判断", "核心判断", "这份内容母稿", "本文认为", "判断是", "thesis"],
        "资料消化": ["资料", "来源", "官方", "依据", "证据", "调研"],
        "解释结构": ["为什么", "机制", "原因", "关键", "不是", "而是"],
        "叙事推进": ["第一", "第二", "接着", "最后", "这条线", "更有价值的讲法"],
        "主张结构": ["主张", "论点", "判断", "结构", "例子", "可复用"],
        "边界风险": ["边界", "风险", "不要", "不能", "missing evidence", "版权"],
    }
    matched = [label for label, terms in groups.items() if contains_any(text, terms)]
    heading_count = len(re.findall(r"^#{1,3}\s+", text, flags=re.M))
    source_hits = len(re.findall(r"https?://|\b(?:S|SC|SRC)[-_][A-Za-z0-9_-]+\b|来源|依据", text))

    score = 8
    if length >= 2500:
        score += 28
    elif length >= 1500:
        score += 20
    elif length >= 800:
        score += 10
    score += 8 * len(matched)
    score += min(8, heading_count * 2)
    score += min(8, source_hits * 2)

    blockers: list[str] = []
    actions: list[str] = []
    if length < 800:
        blockers.append("内容母稿过短")
        actions.append("把内容母稿扩展为可读长文，至少说明核心判断、证据依据、解释结构、主张结构和边界。")
    if "中心判断" not in matched:
        blockers.append("内容母稿缺中心判断")
        actions.append("在开头明确写出“我读完资料后得到的核心判断”。")
    if "资料消化" not in matched:
        actions.append("补资料如何支撑判断，而不是只写观点。")
    if "主张结构" not in matched:
        actions.append("补这篇文章的可复用主张、关键例子和推理结构；不要在内容母稿里写排版或生成建议。")
    if "边界风险" not in matched:
        actions.append("补来源边界、版权、低置信结论或 missing evidence。")

    return category(
        category_id="source_synthesis",
        label="内容母稿",
        weight=PREP_WEIGHTS["source_synthesis"],
        score=score,
        evidence=f"{path}; chars={length}; headings={heading_count}; matched={','.join(matched) or 'none'}",
        findings=[
            f"内容母稿 {length} 字符，{heading_count} 个标题层级。",
            f"覆盖：{','.join(matched) or '无'}。",
        ],
        actions=actions,
        blockers=blockers,
    )


def audit_story_premise(inputs: dict[str, Any]) -> dict[str, Any]:
    brief = inputs.get("content_brief_json")
    brief_text = inputs.get("content_brief_text", "")
    question = inputs.get("question_tree_json")
    question_text = inputs.get("question_tree_text", "")
    kernels = extract_page_kernels(inputs.get("page_kernel_map_json"))
    merged = text_blob(brief, brief_text, question, question_text, inputs.get("page_kernel_map_json"))
    fields = {
        "中心论点": ["central_thesis", "中心论点", "核心判断", "主张", "thesis"],
        "观众起点": ["current_state", "当前状态", "现状", "原有认知"],
        "目标状态": ["desired_state", "目标状态", "看完后", "希望相信"],
        "冲突张力": ["conflict", "tension", "stakes", "冲突", "张力", "赌注", "风险"],
        "转折点": ["turning_point", "认知转折", "转折"],
        "叙事弧": ["narrative_arc", "故事线", "叙事弧", "推进链"],
    }
    matched = [label for label, terms in fields.items() if contains_any(merged, terms)]
    transition_count = sum(1 for kernel in kernels if norm(kernel.get("transition_from_previous") or kernel.get("speaker_note_goal")))
    score = 10 + 70 * ratio(len(matched), len(fields)) + min(20, transition_count * 3)
    actions: list[str] = []
    blockers: list[str] = []
    if len(matched) < 4:
        actions.append("补观众状态变化、核心冲突、认知转折和中心论点，不要只列内容目录。")
    if "中心论点" not in matched:
        blockers.append("缺中心论点")
    if "观众起点" not in matched or "目标状态" not in matched:
        blockers.append("缺观众状态变化")
    return category(
        category_id="story_premise",
        label="叙事主线",
        weight=PREP_WEIGHTS["story_premise"],
        score=score,
        evidence=f"matched={','.join(matched) or 'none'}; transitions={transition_count}",
        findings=[f"叙事要素覆盖：{','.join(matched) or '无'}。"],
        actions=actions,
        blockers=blockers,
    )


def audit_page_kernels(inputs: dict[str, Any], allow_missing: bool) -> dict[str, Any]:
    path = inputs.get("page_kernel_map_path")
    kernels = extract_page_kernels(inputs.get("page_kernel_map_json"))
    if not kernels:
        blockers = [] if allow_missing else ["缺页面内核表"]
        score = 45 if allow_missing else 0
        return category(
            category_id="page_kernels",
            label="页面内核表",
            weight=PREP_WEIGHTS["page_kernels"],
            score=score,
            evidence="未找到 page_kernel_map/slide_plan 或没有页面。",
            findings=[],
            actions=["正式大纲前补页面内核表：每页唯一主张、证明对象、证据锚点、观众反应、视觉角色和布局理由。"],
            blockers=blockers,
        )
    total = len(kernels)
    claim_count = sum(1 for kernel in kernels if title_is_claim(kernel_title(kernel)))
    proof_count = sum(1 for kernel in kernels if norm(kernel.get("proof_object")))
    source_count = sum(1 for kernel in kernels if kernel_has_source(kernel))
    audience_shift_count = sum(1 for kernel in kernels if norm(kernel.get("audience_shift") or kernel.get("viewer_shift")))
    visual_count = sum(1 for kernel in kernels if norm(kernel.get("visual_role") or kernel.get("media_need")))
    layout_reason_count = sum(1 for kernel in kernels if norm(kernel.get("layout_reason") or kernel.get("layout_pattern_id") or kernel.get("reading_path")))
    transition_count = sum(1 for kernel in kernels if norm(kernel.get("transition_from_previous") or kernel.get("speaker_note_goal")))
    score = 8
    score += 20 * ratio(claim_count, total)
    score += 18 * ratio(proof_count, total)
    score += 20 * ratio(source_count, total)
    score += 12 * ratio(audience_shift_count, total)
    score += 10 * ratio(visual_count, total)
    score += 8 * ratio(layout_reason_count, total)
    score += 4 * ratio(transition_count, total)
    blockers: list[str] = []
    actions: list[str] = []
    if claim_count / total < 0.65:
        blockers.append("页面内核主张不足")
        actions.append("把页面标题改成判断式主张，不要用背景、问题、方案等标签词。")
    if source_count / total < 0.6:
        blockers.append("关键页面缺证据锚点")
        actions.append("为页面补 source_card_ids、concrete_anchor 或 source_anchor。")
    if visual_count / total < 0.6:
        actions.append("补 visual_role，让每页知道自己是证据图、对比、流程、呼吸页还是主视觉。")
    if layout_reason_count / total < 0.5:
        actions.append("补 layout_reason 或 reading_path，解释为什么这样展示。")
    return category(
        category_id="page_kernels",
        label="页面内核表",
        weight=PREP_WEIGHTS["page_kernels"],
        score=score,
        evidence=f"{path}; pages={total}; claim={claim_count}; source={source_count}; visual={visual_count}",
        findings=[
            f"{claim_count}/{total} 页有判断式主张，{proof_count}/{total} 页有证明对象。",
            f"{source_count}/{total} 页有证据锚点，{layout_reason_count}/{total} 页有布局或阅读理由。",
        ],
        actions=actions,
        blockers=blockers,
    )


def audit_visual_translation(inputs: dict[str, Any]) -> dict[str, Any]:
    path = inputs.get("visual_translation_path")
    payload = inputs.get("visual_translation_json")
    text = inputs.get("visual_translation_text", "")
    kernels = extract_page_kernels(inputs.get("page_kernel_map_json"))
    merged = text_blob(payload, text, inputs.get("page_kernel_map_json"))
    groups = {
        "图文关系": ["图文关系", "image_text", "image text", "图片和文字", "safe_area"],
        "布局理由": ["layout_reason", "布局理由", "阅读路径", "reading_path", "grid"],
        "图片角色": ["visual_role", "主视觉", "证据图", "背景", "image_role"],
        "图解方式": ["图解", "diagram", "流程", "对比", "时间线", "chart"],
        "反俗套": ["反俗套", "禁止", "避免", "不要", "anti"],
    }
    matched = [label for label, terms in groups.items() if contains_any(merged, terms)]
    visual_kernel_count = sum(1 for kernel in kernels if norm(kernel.get("visual_role") or kernel.get("layout_reason") or kernel.get("reading_path")))
    if not path and not matched and not visual_kernel_count:
        return category(
            category_id="visual_translation",
            label="视觉翻译准备",
            weight=PREP_WEIGHTS["visual_translation"],
            score=0,
            evidence="未找到 visual_translation/visual_contract/style_direction，页面也缺视觉字段。",
            findings=[],
            actions=["补视觉翻译准备：图文关系、布局理由、图片角色、图解方式和反俗套限制。"],
            blockers=["缺视觉翻译准备"],
        )
    score = 10 + 70 * ratio(len(matched), len(groups)) + min(20, visual_kernel_count * 3)
    actions: list[str] = []
    blockers: list[str] = []
    if "图文关系" not in matched:
        actions.append("补图文关系和文字安全区，避免后面生图或排版遮挡正文。")
    if "布局理由" not in matched:
        actions.append("补布局理由：为什么用对比、流程、时间线、大图或留白页。")
    if len(matched) < 3:
        blockers.append("视觉翻译准备过薄")
    return category(
        category_id="visual_translation",
        label="视觉翻译准备",
        weight=PREP_WEIGHTS["visual_translation"],
        score=score,
        evidence=f"{path or 'page kernels'}; matched={','.join(matched) or 'none'}; visual_kernels={visual_kernel_count}",
        findings=[f"视觉翻译覆盖：{','.join(matched) or '无'}。"],
        actions=actions,
        blockers=blockers,
    )


def profile_rules(contract: dict[str, Any], profile: str) -> dict[str, Any]:
    profiles = contract.get("profiles", {})
    fallback = profiles.get("plan", {})
    selected = profiles.get(profile, fallback)
    return selected if isinstance(selected, dict) else fallback


def evaluate_project(project: Path, inputs: dict[str, Any], contract: dict[str, Any], profile: str, min_score: int | None = None) -> dict[str, Any]:
    profile_rule = profile_rules(contract, profile)
    threshold = int(min_score or profile_rule.get("minimum_overall_score", 80))
    category_threshold = int(profile_rule.get("minimum_category_score", 70))
    allow_missing_page_kernels = bool(profile_rule.get("allow_missing_page_kernels", False))
    categories = [
        audit_research_archive(project, inputs),
        audit_content_brief(inputs, contract),
        audit_question_tree(inputs, contract),
        audit_evidence_matrix(inputs),
        audit_source_synthesis(inputs),
        audit_story_premise(inputs),
        audit_page_kernels(inputs, allow_missing_page_kernels),
        audit_visual_translation(inputs),
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
    artifacts = {}
    for artifact_id in ARTIFACT_CANDIDATES:
        path = inputs.get(f"{artifact_id}_path")
        artifacts[artifact_id] = str(path) if path else ""
    ok = overall >= threshold and not blockers and not warnings
    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/content_preflight.py",
        "generated_at": utc_now(),
        "project": str(project),
        "profile": profile,
        "minimum_overall_score": threshold,
        "minimum_category_score": category_threshold,
        "overall_score": overall,
        "ok": ok,
        "gate_ready": ok,
        "artifacts": artifacts,
        "categories": categories,
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        "recommended_actions": list(dict.fromkeys(actions))[:24],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 内容准备前置评估",
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


def write_self_test_project(project: Path) -> None:
    content = {
        "topic": "AI 创作生产线",
        "audience": "AI 创作者",
        "use_context": "15 分钟公开分享",
        "current_state": "工具很多但流程松散，观众容易把重点放在模型尝鲜。",
        "desired_state": "相信稳定产出来自可复用流程，而不是单次提示词。",
        "central_thesis": "AI 创作价值正在从模型尝鲜转向流程复用。",
        "success_criteria": ["观众能复述主判断", "观众知道如何开始搭生产线"],
        "constraints": ["不伪造平台截图", "不使用无来源数据"],
        "delivery_format": "editable_pptx",
        "narrative_arc": "问题现场 -> 证据 -> 机制 -> 行动",
        "turning_point": "从追新模型转向建设流程资产",
        "stakes": "如果没有流程，产出不可复制。",
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
    cards = {
        "cards": [
            {
                "id": "C01",
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
                "id": "C02",
                "claim": "创作者更关心稳定产出和复用。",
                "evidence": "调研样本中稳定产出、分发和复用被反复提及。",
                "source_ids": ["S02"],
                "source_url_or_path": "https://example.com/survey",
                "confidence": "medium",
                "supports_questions": ["subquestions"],
                "supports_slide": [3],
                "visual_opportunity": "内容资产库图解",
            },
            {
                "id": "C03",
                "claim": "流程复用能减少每次从零开始的决策成本。",
                "evidence": "案例显示模板、检查表和素材库能缩短生产路径。",
                "source_ids": ["S03"],
                "source_url_or_path": "case-notes.md",
                "confidence": "medium",
                "supports_questions": ["counter_questions"],
                "supports_slide": [4],
                "visual_opportunity": "前后对比图",
            },
        ]
    }
    kernels = {
        "page_kernels": [
            {
                "slide_no": 1,
                "claim_title": "AI 创作正在从尝鲜走向稳定生产线",
                "proof_object": "创作流程变化",
                "source_card_ids": ["C01"],
                "concrete_anchor": "工作流类 AI 工具采用率变化",
                "audience_shift": "从模型热闹转向产出系统",
                "content_role": "开场判断",
                "visual_role": "主视觉",
                "layout_reason": "大图建立问题现场，少量文字压住主题",
                "transition_from_previous": "开场",
            },
            {
                "slide_no": 2,
                "claim_title": "真正的门槛不是会用模型，而是能复用流程",
                "proof_object": "流程复用的价值",
                "source_card_ids": ["C02", "C03"],
                "concrete_anchor": "创作者稳定产出诉求和流程案例",
                "audience_shift": "从工具清单转向方法系统",
                "content_role": "机制解释",
                "visual_role": "流程图解",
                "layout_reason": "用节点图说明输入、资产、检查和输出的关系",
                "transition_from_previous": "解释开场判断为什么成立",
            },
        ]
    }
    visual = {
        "image_text_relation": "主视觉保留左侧文字安全区，图解页中央留低细节背景。",
        "layout_reason": "开场大图、证据密页、流程图解和呼吸页交替。",
        "image_role": "封面背景、流程图解背景、证据页来源图。",
        "diagram_plan": "流程、对比、证据卡矩阵。",
        "anti_slop": "禁止紫色渐变、装饰球、假截图和假数据。",
    }
    write_json(project / "content_contract.json", content)
    write_json(project / "research_questions.json", questions)
    write_json(
        project / "task_manifest.json",
        {
            "schema_version": "1.0.0",
            "topic": "AI 创作生产线",
            "stages": [
                {
                    "id": "00_research",
                    "label_zh": "资料搜索整理",
                    "artifacts": ["research_dossier.md", "content_report.md", "sources/source_manifest.json", "sources/source_cards.json"],
                }
            ],
        },
    )
    write_text(
        project / "README.md",
        "# Qiaomu PPT Task Archive\n\n- `research_dossier.md`\n- `content_report.md`\n- `sources/source_manifest.json`\n- `sources/source_cards.json`\n",
    )
    write_json(
        project / "sources" / "source_manifest.json",
        {
            "schema_version": "1.0.0",
            "sources": [
                {
                    "input": "https://example.com/report",
                    "title": "AI workflow report",
                    "source_type": "url",
                    "fetch_route": "self_test",
                    "markdown_path": "report.md",
                    "images": ["images/workflow.png"],
                    "warnings": [],
                    "missing_evidence": [],
                }
            ],
        },
    )
    write_json(project / "sources" / "source_cards.json", cards)
    write_text(
        project / "research_dossier.md",
        "# Research Dossier\n\n来源链接：https://example.com/report\n\n图片候选：`sources/images/workflow.png`\n\n已验证事实、解释判断、缺口和页面支撑映射已记录。\n",
    )
    write_text(
        project / "content_report.md",
        """# 为什么 AI 创作需要从模型尝鲜走向稳定生产线

这份内容母稿的中心判断是：AI 创作的价值正在从模型尝鲜转向流程复用。资料显示，创作者面对的问题已经不只是会不会调用某个模型，而是能不能把选题、资料、提示词、图片、检查和分发组织成稳定链路。

## 资料消化：从工具热闹到流程压力

第一，来源资料说明工作流类 AI 工具正在成为基础设施。这个事实不能直接变成“AI 很重要”的空泛页面，而应该转译成一个更具体的判断：单次聊天解决灵感，生产线解决持续产出。依据自测来源 S-001，创作者已经在同一条产出链里同时面对选题、素材、文案、图片和发布检查，瓶颈不是模型能力单点不足，而是每一步之间缺少可复用衔接。

第二，创作者调研反复提到稳定产出、分发和复用。这意味着核心问题不应停留在工具清单，而应解释为什么复用流程降低每次从零开始的决策成本。更有价值的判断是：AI 创作的真实成本不在一次产出，而在每次重新定义任务、寻找资料、整理证据、重写提示词和返工视觉。流程把这些高频动作沉淀下来，让新项目可以站在上一次项目的肩膀上开始。

第三，流程并不会限制创意。更准确的判断是：流程把重复劳动收纳起来，让创作者把注意力放回判断、审美和取舍。这个转折回应了一个常见反方问题：不是流程让内容变普通，而是没有流程时，创作者的大量注意力被格式、素材和检查吞掉，真正需要人的判断反而被挤压。

## 可复用的主张结构

这篇母稿可以沉淀出四个可复用主张：第一，单点模型能力不等于稳定生产能力；第二，复用流程降低的是重新启动成本；第三，流程和创意不是对立关系，流程释放的是判断空间；第四，可持续产出的关键不是追逐更多工具，而是把选题、素材、提示词、检查表和发布清单沉淀成可反复调用的系统。这些主张各自有证据对象和反方问题，后续规划可以再决定它们是否进入页面、报告章节或讲者备注。

## 边界风险

边界也要写清楚：示例数据只来自自测来源，不伪造平台截图，不把局部案例说成全行业结论。涉及产品能力、行业规模或具体效果时，必须回到来源继续核查，不能用漂亮但无证据的表达替代事实。
""",
    )
    write_text(project / "sources" / "images" / "workflow.png", "self-test image placeholder")
    write_json(project / "page_kernel_map.json", kernels)
    write_json(project / "visual_contract.json", visual)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit first-step qiaomu-ppt content preparation.")
    parser.add_argument("project", nargs="?", type=Path, help="Qiaomu PPT project directory.")
    parser.add_argument("--profile", choices=["plan", "draft", "final", "release"], default="plan")
    parser.add_argument("--min-score", type=int, help="Override profile minimum overall score.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--content-brief")
    parser.add_argument("--question-tree")
    parser.add_argument("--research-dossier")
    parser.add_argument("--evidence-matrix")
    parser.add_argument("--page-kernel-map")
    parser.add_argument("--visual-translation")
    parser.add_argument("--output", type=Path, default=SKILL_DIR / "reports" / "content-preflight.json")
    parser.add_argument("--markdown", type=Path, default=SKILL_DIR / "reports" / "content-preflight.md")
    parser.add_argument("--self-test", action="store_true", help="Run built-in positive fixture without reading a project.")
    args = parser.parse_args()

    contract = read_json(args.contract)
    if args.self_test:
        with tempfile.TemporaryDirectory(prefix="qiaomu-ppt-content-preflight-") as tmpdir:
            project = Path(tmpdir)
            write_self_test_project(project)
            inputs = project_inputs(project)
            report = evaluate_project(project, inputs, contract, args.profile, args.min_score)
    else:
        if not args.project:
            raise SystemExit("project is required unless --self-test is used")
        project = args.project.expanduser().resolve()
        inputs = project_inputs(project, args)
        report = evaluate_project(project, inputs, contract, args.profile, args.min_score)

    write_json(args.output, report)
    write_text(args.markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
