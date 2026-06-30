#!/usr/bin/env python3
"""Evaluate qiaomu-ppt instruction-following boundaries through plan_run.py."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CASES = SKILL_DIR / "evals" / "instruction_cases.json"
DEFAULT_ROUTE_MAP = SKILL_DIR / "data" / "route_reference_map.json"
DEFAULT_CHECK_POLICY = SKILL_DIR / "data" / "check_policy.json"

sys.path.insert(0, str(SCRIPT_DIR))
from plan_run import plan_run, read_json  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def list_contains(actual: list[Any], expected: str) -> bool:
    expected_lower = expected.lower()
    for item in actual:
        if expected_lower in str(item).lower():
            return True
    return False


def assert_expected(report: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    card = report.get("route_card", {})

    scalar_paths = {
        "is_qiaomu_ppt_task": report.get("is_qiaomu_ppt_task"),
        "production_authorized": report.get("production_authorized"),
        "stop_before": report.get("stop_before"),
        "approval_bypass_phrase": report.get("approval_bypass_phrase"),
        "validation_profile": report.get("validation_profile"),
        "route": card.get("route"),
        "final_delivery": card.get("final_delivery"),
    }
    for key, actual in scalar_paths.items():
        if key in expected and actual != expected[key]:
            failures.append(f"{key}: expected {expected[key]!r}, got {actual!r}")

    for key in ("required_references", "optional_references", "primary_scripts", "required_gates", "global_reminders"):
        if key not in expected:
            continue
        actual_list = list(report.get(key, []))
        for item in expected[key]:
            if not list_contains(actual_list, str(item)):
                failures.append(f"{key}: missing {item!r}")

    check_plan = report.get("check_plan", {})
    check_expectations = {
        "check_plan_run_now": "run_now",
        "check_plan_defer_until_final": "defer_until_final",
        "check_plan_skip_by_default": "skip_by_default",
        "check_plan_expensive_checks": "expensive_checks",
    }
    for expected_key, actual_key in check_expectations.items():
        if expected_key not in expected:
            continue
        actual_list = list(check_plan.get(actual_key, []))
        for item in expected[expected_key]:
            if not list_contains(actual_list, str(item)):
                failures.append(f"{expected_key}: missing {item!r}")

    for item in expected.get("forbidden_scripts", []):
        if list_contains(list(report.get("primary_scripts", [])), str(item)):
            failures.append(f"primary_scripts: forbidden script appeared: {item!r}")

    for snippet in expected.get("next_action_contains", []):
        if str(snippet) not in str(report.get("next_action", "")):
            failures.append(f"next_action: missing snippet {snippet!r}")

    return failures


def evaluate(cases_path: Path, route_map_path: Path, check_policy_path: Path) -> dict[str, Any]:
    cases_payload = read_json(cases_path)
    route_map = read_json(route_map_path)
    check_policy = read_json(check_policy_path)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for case in cases_payload.get("cases", []):
        if not isinstance(case, dict):
            continue
        report = plan_run(
            prompt=str(case.get("prompt", "")),
            inputs=[str(item) for item in case.get("inputs", [])],
            stage=str(case.get("stage", "initial")),
            slides=int(case.get("slides", 0) or 0),
            requested_format=str(case.get("format", "")),
            route_map=route_map,
            check_policy=check_policy,
        )
        expected = case.get("expected", {})
        case_failures = assert_expected(report, expected if isinstance(expected, dict) else {})
        result = {
            "id": case.get("id", ""),
            "prompt": case.get("prompt", ""),
            "stage": case.get("stage", "initial"),
            "passed": not case_failures,
            "failures": case_failures,
            "route": report.get("route_card", {}).get("route"),
            "final_delivery": report.get("route_card", {}).get("final_delivery"),
            "production_authorized": report.get("production_authorized"),
            "validation_profile": report.get("validation_profile"),
            "stop_before": report.get("stop_before"),
            "next_action": report.get("next_action"),
        }
        results.append(result)
        if case_failures:
            failures.append(result)

    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/instruction_eval.py",
        "generated_at": utc_now(),
        "ok": not failures,
        "cases": str(cases_path),
        "route_map": str(route_map_path),
        "check_policy": str(check_policy_path),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 3) if total else 0,
        },
        "failures": failures,
        "results": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# 指令遵循评测",
        "",
        f"- OK: `{str(report['ok']).lower()}`",
        f"- 通过：`{summary['passed']}/{summary['total']}`",
        f"- 失败：`{summary['failed']}`",
        f"- 通过率：`{summary['pass_rate']}`",
    ]
    if report.get("failures"):
        lines.extend(["", "## 失败用例", ""])
        for failure in report["failures"]:
            lines.append(f"### {failure['id']}")
            lines.append("")
            lines.append(f"- 路线：`{failure.get('route')}`")
            lines.append(f"- 检查档位：`{failure.get('validation_profile')}`")
            lines.append(f"- 暂停在：`{failure.get('stop_before')}`")
            for item in failure.get("failures", []):
                lines.append(f"- {item}")
            lines.append("")
    else:
        lines.extend(["", "全部指令边界用例通过。", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate qiaomu-ppt instruction-following cases.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--route-map", type=Path, default=DEFAULT_ROUTE_MAP)
    parser.add_argument("--check-policy", type=Path, default=DEFAULT_CHECK_POLICY)
    parser.add_argument("--output", type=Path, default=SKILL_DIR / "reports" / "instruction-eval.json")
    parser.add_argument("--markdown", type=Path, default=SKILL_DIR / "reports" / "instruction-eval.md")
    args = parser.parse_args()

    report = evaluate(args.cases, args.route_map, args.check_policy)
    write_json(args.output, report)
    write_text(args.markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
