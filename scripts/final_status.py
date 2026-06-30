#!/usr/bin/env python3
"""Create the single final delivery status for a qiaomu-ppt project."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUCCESS_STATUSES = {"existing", "exported", "passed", "success", "ok"}
FAIL_STATUSES = {"failed", "missing", "error", "missing_dependency"}
FINAL_PROFILES = {"professional", "final", "release"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def maybe_load(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, "missing"
    try:
        payload = load_json(path)
    except Exception as exc:
        return None, f"invalid: {exc}"
    if not isinstance(payload, dict):
        return None, "invalid: JSON root is not an object"
    return payload, ""


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value:
        return [str(value)]
    return []


def extend_limited(target: list[str], prefix: str, values: Any, *, limit: int = 8) -> None:
    for item in as_list(values)[:limit]:
        target.append(f"{prefix}: {item}")


def report_ok(payload: dict[str, Any] | None) -> bool | None:
    if payload is None:
        return None
    if "ok" in payload:
        return bool(payload.get("ok"))
    status = str(payload.get("status") or "").lower()
    if status in SUCCESS_STATUSES:
        return True
    if status in FAIL_STATUSES:
        return False
    return None


def requested_formats(production: dict[str, Any] | None, export_manifest: dict[str, Any] | None) -> list[str]:
    for payload in (production, export_manifest):
        if isinstance(payload, dict):
            values = payload.get("requested_formats") or payload.get("last_requested_formats")
            formats = as_list(values)
            if formats:
                return formats
    return []


def format_success(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    status = str(item.get("status") or "").lower()
    if status not in SUCCESS_STATUSES:
        return False
    raw_path = str(item.get("path") or item.get("index") or "").strip()
    return bool(raw_path) or status in {"passed", "ok", "success"}


def evaluate_project(project: Path) -> dict[str, Any]:
    project = project.resolve()
    production, production_error = maybe_load(project / "production_manifest.json")
    project_check, project_check_error = maybe_load(project / "project_check.json")
    export_manifest, export_error = maybe_load(project / "export_manifest.json")
    pptx_text, pptx_text_error = maybe_load(project / "pptx_text_check.json")
    benchmark, benchmark_error = maybe_load(project / "reports" / "deck_quality_benchmark.json")
    repair_plan, repair_error = maybe_load(project / "reports" / "deck_repair_plan.json")

    quality_policy = production.get("quality_policy", {}) if production else {}
    profile = str(quality_policy.get("profile") or production.get("quality_profile") if production else "")
    profile = profile or "unknown"
    formats = requested_formats(production, export_manifest)
    allow_missing_formats = bool(
        production
        and isinstance(production.get("exit_policy"), dict)
        and production["exit_policy"].get("allow_missing_formats")
    )

    blocking_failures: list[str] = []
    warnings: list[str] = []
    advisory: list[str] = []
    evidence: dict[str, Any] = {
        "project": str(project),
        "quality_profile": profile,
        "requested_formats": formats,
        "allow_missing_formats": allow_missing_formats,
        "precedence": [
            "production_manifest",
            "project_check",
            "requested_export_formats",
            "pptx_text_check",
            "enforced_benchmark",
            "critical_repair_plan",
        ],
    }

    if production is None:
        blocking_failures.append(f"production_manifest.json {production_error}; cannot prove production pipeline")
    else:
        evidence["production_manifest_ok"] = bool(production.get("ok"))
        if not production.get("ok"):
            blocking_failures.append("production_manifest.json ok=false")
            extend_limited(blocking_failures, "production_manifest", production.get("failures"))
        for step in production.get("steps", []):
            if not isinstance(step, dict) or not step.get("required", True):
                continue
            if step.get("status") != "passed":
                reason = step.get("reason") or step.get("stderr_tail") or step.get("stdout_tail") or "not passed"
                blocking_failures.append(f"required step {step.get('name', 'unknown')} {step.get('status')}: {str(reason).strip()[:240]}")

    if project_check is None:
        message = f"project_check.json {project_check_error}"
        if profile in FINAL_PROFILES:
            blocking_failures.append(message)
        else:
            warnings.append(message)
    else:
        evidence["project_check_ok"] = bool(project_check.get("ok"))
        if not project_check.get("ok"):
            blocking_failures.append("project_check.json ok=false")
            extend_limited(blocking_failures, "project_check", project_check.get("failures"))
        extend_limited(warnings, "project_check warning", project_check.get("warnings"), limit=5)

    if export_manifest is None:
        if formats:
            blocking_failures.append(f"export_manifest.json {export_error}; requested formats cannot be verified")
        else:
            warnings.append(f"export_manifest.json {export_error}")
    else:
        format_payload = export_manifest.get("formats") if isinstance(export_manifest.get("formats"), dict) else {}
        evidence["export_format_status"] = {
            name: format_payload.get(name, {}).get("status") if isinstance(format_payload.get(name), dict) else "missing"
            for name in formats
        }
        for name in formats:
            item = format_payload.get(name)
            if format_success(item):
                continue
            if allow_missing_formats:
                warnings.append(f"requested format {name} not successful but allowed missing formats")
            else:
                status = item.get("status") if isinstance(item, dict) else "missing"
                reason = item.get("reason") or item.get("warning") if isinstance(item, dict) else ""
                blocking_failures.append(f"requested format {name} is {status}{': ' + str(reason) if reason else ''}")

    if "pptx" in formats:
        if pptx_text is None:
            blocking_failures.append(f"pptx_text_check.json {pptx_text_error}; editable PPTX not verified")
        else:
            evidence["pptx_text_check_ok"] = bool(pptx_text.get("ok"))
            if not pptx_text.get("ok"):
                blocking_failures.append("pptx_text_check.json ok=false")
                extend_limited(blocking_failures, "pptx_text_check", pptx_text.get("failures"))

    benchmark_enforced = bool(quality_policy.get("enforce_quality_benchmark")) or profile in FINAL_PROFILES
    if benchmark is None:
        message = f"reports/deck_quality_benchmark.json {benchmark_error}"
        if benchmark_enforced:
            blocking_failures.append(message)
        else:
            warnings.append(message)
    else:
        score = int(benchmark.get("score") or 0)
        target = int(benchmark.get("target_score") or quality_policy.get("benchmark_min_score") or 0)
        evidence["benchmark"] = {
            "score": score,
            "target_score": target,
            "ok": benchmark.get("ok"),
            "readiness": benchmark.get("readiness"),
            "enforced": benchmark_enforced,
        }
        if benchmark_enforced and target and score < target:
            blocking_failures.append(f"deck_quality_benchmark score {score} below required {target}")
        elif target and score < target:
            warnings.append(f"deck_quality_benchmark score {score} below advisory target {target}")
        if benchmark.get("ok") is False and not benchmark_enforced:
            advisory.append("deck_quality_benchmark ok=false but benchmark is advisory for this profile")

    repair_required = bool(quality_policy.get("fail_on_critical_repairs"))
    if repair_plan is None:
        message = f"reports/deck_repair_plan.json {repair_error}"
        if repair_required:
            blocking_failures.append(message)
        else:
            warnings.append(message)
    else:
        summary = repair_plan.get("summary") if isinstance(repair_plan.get("summary"), dict) else {}
        critical_count = int(summary.get("critical_count") or 0)
        evidence["repair_plan"] = {
            "critical_count": critical_count,
            "required": repair_required,
        }
        if repair_required and critical_count > 0:
            blocking_failures.append(f"deck_repair_plan has {critical_count} critical repair action(s)")

    ok = not blocking_failures
    status = "passed" if ok else "failed"
    if ok and warnings:
        status = "passed_with_warnings"
    return {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/final_status.py",
        "generated_at": utc_now(),
        "project": str(project),
        "ok": ok,
        "status": status,
        "blocking_failures": blocking_failures,
        "warnings": warnings,
        "advisory": advisory,
        "evidence": evidence,
    }


def render_markdown(report: dict[str, Any]) -> str:
    evidence = report.get("evidence", {})
    lines = [
        "# 交付检查",
        "",
        f"- Final OK: `{str(report.get('ok')).lower()}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Quality profile: `{evidence.get('quality_profile', 'unknown')}`",
        f"- Requested formats: `{', '.join(evidence.get('requested_formats', [])) or 'none'}`",
        "",
        "## 判定优先级",
        "",
    ]
    for item in evidence.get("precedence", []):
        lines.append(f"- `{item}`")
    if report.get("blocking_failures"):
        lines.extend(["", "## 阻塞问题", ""])
        lines.extend(f"- {item}" for item in report["blocking_failures"])
    if report.get("warnings"):
        lines.extend(["", "## 警告", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    if report.get("advisory"):
        lines.extend(["", "## 建议项", ""])
        lines.extend(f"- {item}" for item in report["advisory"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the single final delivery status for a qiaomu-ppt project.")
    parser.add_argument("project", type=Path, help="Generated qiaomu-ppt project directory.")
    parser.add_argument("--output", type=Path, help="JSON output. Default: <project>/final_status.json")
    parser.add_argument("--markdown", type=Path, help="Markdown output. Default: <project>/交付检查.md")
    parser.add_argument("--report-only", action="store_true", help="Always exit 0 after writing reports, even when final status is failed.")
    args = parser.parse_args()

    project = args.project.resolve()
    report = evaluate_project(project)
    output = args.output or project / "final_status.json"
    markdown = args.markdown or project / "交付检查.md"
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report_only:
        return 0
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
