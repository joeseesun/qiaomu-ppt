#!/usr/bin/env python3
"""Plan the qiaomu-ppt route, references, scripts, and confirmation boundary."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_MAP = SKILL_DIR / "data" / "route_reference_map.json"
DEFAULT_CHECK_POLICY = SKILL_DIR / "data" / "check_policy.json"


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


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\u4e00-\u9fff:/.\-]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def phrase_present(haystack: str, phrase: str) -> bool:
    phrase = normalize(phrase)
    if not phrase:
        return False
    if re.search(r"[\u4e00-\u9fff]", phrase) and not re.search(r"[a-z0-9]", phrase):
        return phrase in haystack
    if "://" in phrase or phrase.startswith(".") or "/" in phrase:
        return phrase in haystack
    return f" {phrase} " in f" {haystack} "


def find_first_phrase(text: str, phrases: list[str]) -> str:
    normalized = normalize(text)
    for phrase in phrases:
        if phrase_present(normalized, phrase):
            return phrase
    return ""


def score_route(route: dict[str, Any], text: str, inputs: list[str]) -> dict[str, Any]:
    normalized = normalize(" ".join([text, *inputs]))
    matched_terms = [term for term in route.get("match_terms", []) if phrase_present(normalized, str(term))]
    matched_inputs = [
        pattern
        for pattern in route.get("input_patterns", [])
        if any(str(pattern).lower() in item.lower() for item in inputs) or phrase_present(normalized, str(pattern))
    ]
    score = int(route.get("priority", 0)) + len(matched_terms) * 12 + len(matched_inputs) * 18
    if not matched_terms and not matched_inputs:
        score = 0
    return {
        "route": route,
        "score": score,
        "matched_terms": matched_terms,
        "matched_inputs": matched_inputs,
    }


def choose_route(route_map: dict[str, Any], prompt: str, inputs: list[str]) -> dict[str, Any]:
    scored = [score_route(route, prompt, inputs) for route in route_map.get("routes", [])]
    scored = [item for item in scored if item["score"] > 0]
    if not scored:
        fallback = next((route for route in route_map.get("routes", []) if route.get("id") == "broad_topic_ppt"), None)
        if fallback is None:
            raise SystemExit("route map has no broad_topic_ppt fallback")
        return {"route": fallback, "score": 1, "matched_terms": [], "matched_inputs": []}
    return sorted(scored, key=lambda item: item["score"], reverse=True)[0]


def confidence(scored: dict[str, Any]) -> str:
    matches = len(scored.get("matched_terms", [])) + len(scored.get("matched_inputs", []))
    if matches >= 3 or scored.get("score", 0) >= 120:
        return "high"
    if matches >= 1:
        return "medium"
    return "low"


def append_unique(target: list[str], values: list[Any]) -> None:
    seen = set(target)
    for value in values:
        item = str(value)
        if item and item not in seen:
            target.append(item)
            seen.add(item)


def policy_values(block: dict[str, Any], key: str, profile: str) -> list[str]:
    value = block.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if not isinstance(value, dict):
        return []
    values: list[str] = []
    append_unique(values, list(value.get("all", [])))
    append_unique(values, list(value.get(profile, [])))
    return values


def choose_validation_profile(
    *,
    route_id: str,
    final_delivery: str,
    stage: str,
    production_authorized: bool,
    validation_profile_override: str,
    check_policy: dict[str, Any],
) -> str:
    if validation_profile_override:
        return validation_profile_override
    if route_id == "not_qiaomu_ppt" or final_delivery == "not_applicable":
        return "none"
    if final_delivery == "planning_only":
        return "plan"
    route_override = check_policy.get("route_profile_overrides", {}).get(route_id)
    if isinstance(route_override, str):
        return route_override
    if isinstance(route_override, dict) and stage in route_override:
        return str(route_override[stage])
    if production_authorized:
        return str(check_policy.get("direct_production_profile", "final"))
    return str(check_policy.get("stage_profile_defaults", {}).get(stage, "plan"))


def build_check_plan(
    *,
    route_id: str,
    final_delivery: str,
    stage: str,
    production_authorized: bool,
    validation_profile_override: str,
    check_policy: dict[str, Any],
) -> dict[str, Any]:
    profile = choose_validation_profile(
        route_id=route_id,
        final_delivery=final_delivery,
        stage=stage,
        production_authorized=production_authorized,
        validation_profile_override=validation_profile_override,
        check_policy=check_policy,
    )
    profile_block = dict(check_policy.get("profiles", {}).get(profile, {}))
    check_plan = {
        "profile": profile,
        "profile_label": profile_block.get("label_zh", profile),
        "run_now": [],
        "defer_until_final": [],
        "skip_by_default": [],
        "expensive_checks": [],
        "notes": [],
    }
    for key in ("run_now", "defer_until_final", "skip_by_default", "expensive_checks", "notes"):
        append_unique(check_plan[key], policy_values(profile_block, key, profile))

    for section_name, lookup_key in (("delivery_policy", final_delivery), ("route_policy", route_id)):
        block = check_policy.get(section_name, {}).get(lookup_key, {})
        if not isinstance(block, dict):
            continue
        for key in ("run_now", "defer_until_final", "skip_by_default", "expensive_checks", "notes"):
            append_unique(check_plan[key], policy_values(block, key, profile))

    return check_plan


def plan_run(
    *,
    prompt: str,
    inputs: list[str],
    stage: str,
    slides: int,
    requested_format: str,
    route_map: dict[str, Any],
    check_policy: dict[str, Any],
    validation_profile_override: str = "",
) -> dict[str, Any]:
    combined = " ".join([prompt, *inputs])
    global_rules = route_map.get("global", {})
    negative = find_first_phrase(combined, list(global_rules.get("negative_ppt_phrases", [])))
    bypass_phrase = find_first_phrase(combined, list(global_rules.get("approval_bypass_phrases", [])))

    if negative:
        check_plan = build_check_plan(
            route_id="not_qiaomu_ppt",
            final_delivery="not_applicable",
            stage=stage,
            production_authorized=False,
            validation_profile_override="",
            check_policy=check_policy,
        )
        return {
            "schema_version": "1.0.0",
            "tool": "qiaomu-ppt/scripts/plan_run.py",
            "generated_at": utc_now(),
            "ok": True,
            "is_qiaomu_ppt_task": False,
            "negative_phrase": negative,
            "route_card": {
                "route": "not_qiaomu_ppt",
                "final_delivery": "not_applicable",
                "confidence": "high",
                "assumptions": ["用户明确排除了 PPT/PPTX/幻灯片生产。"],
            },
            "next_action": "不要使用 qiaomu-ppt；按用户实际请求选择其他工具或直接回答。",
            "production_authorized": False,
            "stop_before": "qiaomu_ppt_activation",
            "validation_profile": check_plan["profile"],
            "check_plan": check_plan,
            "required_references": [],
            "optional_references": [],
            "primary_scripts": [],
            "required_gates": ["触发边界门"],
        }

    selected = choose_route(route_map, prompt, inputs)
    route = selected["route"]
    route_id = str(route.get("id", "unknown"))
    final_delivery = str(route.get("final_delivery", "editable_pptx"))
    approval_bypassed = bool(bypass_phrase)
    stage_authorizes_production = stage in {"proposal_approved", "preview_approved", "production"}
    confirmation_required = bool(route.get("confirmation_required", True))
    planning_only = route.get("final_delivery") == "planning_only"
    production_authorized = (approval_bypassed or stage_authorizes_production) and not planning_only
    check_plan = build_check_plan(
        route_id=route_id,
        final_delivery=final_delivery,
        stage=stage,
        production_authorized=production_authorized,
        validation_profile_override=validation_profile_override,
        check_policy=check_policy,
    )

    if production_authorized and not planning_only:
        next_action = "按已确认或免确认的路线执行生产流程，并记录验证证据。"
        stop_before = "none"
    elif stage == "after_choice":
        next_action = str(route.get("after_choice_action") or route.get("first_action") or "进入资料收集和方案规划。")
        stop_before = str(route.get("stop_before") or "design_proposal_confirmation")
    elif planning_only:
        next_action = str(route.get("first_action") or "只输出规划或文案结果，不生成最终文件。")
        stop_before = str(route.get("stop_before") or "final_export")
    else:
        next_action = str(route.get("first_action") or "先输出路线卡和方案，等待确认。")
        stop_before = str(route.get("stop_before") or "design_proposal_confirmation")

    assumptions = []
    if slides:
        assumptions.append(f"目标页数约 {slides} 页。")
    if requested_format:
        assumptions.append(f"用户请求的格式倾向：{requested_format}。")
    if approval_bypassed:
        assumptions.append(f"检测到免确认措辞：{bypass_phrase}。")
    if not inputs and route_id in {"source_to_ppt", "paper_to_ppt", "wechat_to_ppt"}:
        assumptions.append("路线需要来源输入；若当前没有文件/链接，需要向用户索取或调整路线。")
    if not assumptions:
        assumptions.append("未发现会改变路线的额外约束。")

    global_reminders = list(global_rules.get("always_keep", []))
    append_unique(global_reminders, list(route.get("route_reminders", [])))

    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/plan_run.py",
        "generated_at": utc_now(),
        "ok": True,
        "is_qiaomu_ppt_task": True,
        "stage": stage,
        "approval_bypass_phrase": bypass_phrase,
        "production_authorized": production_authorized,
        "stop_before": stop_before,
        "next_action": next_action,
        "validation_profile": check_plan["profile"],
        "check_plan": check_plan,
        "route_card": {
            "route": route_id,
            "route_label": route.get("label_zh", route_id),
            "final_delivery": final_delivery,
            "confidence": confidence(selected),
            "matched_terms": selected.get("matched_terms", []),
            "matched_inputs": selected.get("matched_inputs", []),
            "assumptions": assumptions,
        },
        "required_references": list(route.get("required_references", [])),
        "optional_references": list(route.get("optional_references", [])),
        "primary_scripts": list(route.get("primary_scripts", [])),
        "required_gates": list(route.get("required_gates", [])),
        "global_reminders": global_reminders,
    }


def render_markdown(report: dict[str, Any]) -> str:
    card = report.get("route_card", {})
    check_plan = report.get("check_plan", {})
    lines = [
        "# 乔木 PPT 路线卡",
        "",
        f"- 路线：`{card.get('route', '')}`（{card.get('route_label', '')}）",
        f"- 最终交付：`{card.get('final_delivery', '')}`",
        f"- 置信度：`{card.get('confidence', '')}`",
        f"- 允许生产：`{str(report.get('production_authorized')).lower()}`",
        f"- 检查档位：`{report.get('validation_profile', '')}`（{check_plan.get('profile_label', '')}）",
        f"- 暂停在：`{report.get('stop_before', '')}`",
        f"- 下一步：{report.get('next_action', '')}",
    ]
    if card.get("assumptions"):
        lines.extend(["", "## 关键假设", ""])
        lines.extend(f"- {item}" for item in card["assumptions"])
    if report.get("required_references"):
        lines.extend(["", "## 必读参考", ""])
        lines.extend(f"- `{item}`" for item in report["required_references"])
    if report.get("primary_scripts"):
        lines.extend(["", "## 主要脚本", ""])
        lines.extend(f"- `{item}`" for item in report["primary_scripts"])
    if report.get("required_gates"):
        lines.extend(["", "## 必过质量门", ""])
        lines.extend(f"- {item}" for item in report["required_gates"])
    if report.get("global_reminders"):
        lines.extend(["", "## 全局提醒", ""])
        lines.extend(f"- {item}" for item in report["global_reminders"])
    if check_plan.get("run_now"):
        lines.extend(["", "## 现在要跑", ""])
        lines.extend(f"- {item}" for item in check_plan["run_now"])
    if check_plan.get("defer_until_final"):
        lines.extend(["", "## 最终档再跑", ""])
        lines.extend(f"- {item}" for item in check_plan["defer_until_final"])
    if check_plan.get("skip_by_default"):
        lines.extend(["", "## 默认跳过", ""])
        lines.extend(f"- {item}" for item in check_plan["skip_by_default"])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan qiaomu-ppt route, references, scripts, and confirmation boundary.")
    parser.add_argument("inputs", nargs="*", help="Optional URLs/files/folders mentioned by the user.")
    parser.add_argument("--prompt", default="", help="User request text.")
    parser.add_argument("--stage", choices=["initial", "after_choice", "proposal_approved", "preview_approved", "production"], default="initial")
    parser.add_argument("--slides", type=int, default=0, help="Target slide count when known.")
    parser.add_argument("--format", default="", help="Requested delivery format when known.")
    parser.add_argument("--validation-profile", choices=["plan", "draft", "final", "release"], default="", help="Override the default check profile.")
    parser.add_argument("--route-map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--check-policy", type=Path, default=DEFAULT_CHECK_POLICY)
    parser.add_argument("--output", type=Path, help="Write JSON report.")
    parser.add_argument("--markdown", type=Path, help="Write Markdown report.")
    args = parser.parse_args()

    route_map = read_json(args.route_map)
    check_policy = read_json(args.check_policy)
    report = plan_run(
        prompt=args.prompt,
        inputs=args.inputs,
        stage=args.stage,
        slides=args.slides,
        requested_format=args.format,
        route_map=route_map,
        check_policy=check_policy,
        validation_profile_override=args.validation_profile,
    )
    if args.output:
        write_json(args.output, report)
    if args.markdown:
        write_text(args.markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
