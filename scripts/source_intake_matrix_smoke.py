#!/usr/bin/env python3
"""Run an offline source-intake smoke matrix for qiaomu-ppt."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent

SAMPLE_TEXT = (
    "蒲松龄长期生活在清代基层社会，他把科举失意、乡里秩序、民间信仰和士人想象写进狐鬼故事。"
    "这些故事不是单纯志怪，而是通过异类角色观察现实制度中的欲望、恐惧和道德压力。"
    "一份好的介绍型 PPT 应该先建立时代现场，再解释《聊斋志异》的叙事机制，最后回到作品为什么仍然能被现代读者理解。"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tail(value: str, limit: int = 4000) -> str:
    return value[-limit:] if len(value) > limit else value


def run(command: list[Any], *, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": " ".join(str(part) for part in command),
            "status": "passed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "duration_seconds": round(time.time() - started, 2),
            "stdout_tail": tail(proc.stdout),
            "stderr_tail": tail(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(str(part) for part in command),
            "status": "failed",
            "returncode": None,
            "duration_seconds": round(time.time() - started, 2),
            "reason": f"timed out after {timeout}s",
            "stdout_tail": tail(exc.stdout or ""),
            "stderr_tail": tail(exc.stderr or ""),
        }


def make_docx(path: Path) -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<document><body><p><r><t>{SAMPLE_TEXT}</t></r></p></body></document>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)


def make_pptx(path: Path) -> None:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sld><cSld><spTree><sp><txBody><p><r><t>{SAMPLE_TEXT}</t></r></p></txBody></sp></spTree></cSld></sld>
"""
    notes = "<notes><cSld><spTree><sp><txBody><p><r><t>演讲备注需要解释狐鬼故事如何承载社会观察。</t></r></p></txBody></sp></spTree></cSld></notes>"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ppt/slides/slide1.xml", xml)
        archive.writestr("ppt/notesSlides/notesSlide1.xml", notes)


def make_xlsx(path: Path) -> None:
    shared = """<?xml version="1.0" encoding="UTF-8"?>
<sst>
  <si><t>主题</t></si>
  <si><t>蒲松龄</t></si>
  <si><t>证据</t></si>
  <si><t>狐鬼故事反映现实秩序和士人心理</t></si>
</sst>
"""
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet><sheetData><row><c t="s"><v>0</v></c><c t="s"><v>1</v></c></row><row><c t="s"><v>2</v></c><c t="s"><v>3</v></c></row></sheetData></worksheet>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def make_png(path: Path) -> None:
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/l8k6NwAAAABJRU5ErkJggg=="
    )
    path.write_bytes(data)


def make_fixtures(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    md = root / "local-markdown.md"
    write_text(md, f"# 蒲松龄资料\n\n{SAMPLE_TEXT}\n")
    html = root / "local-html.html"
    write_text(html, f"<html><body><h1>蒲松龄网页资料</h1><p>{SAMPLE_TEXT}</p></body></html>")
    docx = root / "local-docx.docx"
    make_docx(docx)
    pptx = root / "local-pptx.pptx"
    make_pptx(pptx)
    xlsx = root / "local-xlsx.xlsx"
    make_xlsx(xlsx)
    png = root / "local-image.png"
    make_png(png)
    zip_path = root / "mixed-sources.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(md, "bundle/source.md")
        archive.write(docx, "bundle/source.docx")
        archive.write(png, "bundle/image.png")
    return {
        "markdown": md,
        "html": html,
        "docx": docx,
        "pptx": pptx,
        "xlsx": xlsx,
        "image": png,
        "zip": zip_path,
    }


def parse_stdout_json(step: dict[str, Any]) -> dict[str, Any]:
    text = str(step.get("stdout_tail") or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def case_expectations(name: str) -> dict[str, Any]:
    if name == "image":
        return {"min_records": 1, "min_cards": 0, "min_images": 1, "allow_missing_evidence": True}
    if name == "zip":
        return {"min_records": 3, "min_cards": 2, "min_images": 1, "allow_missing_evidence": True}
    if name == "xlsx":
        return {"min_records": 1, "min_cards": 1, "min_images": 0, "allow_missing_evidence": False}
    return {"min_records": 1, "min_cards": 1, "min_images": 0, "allow_missing_evidence": False}


def inspect_output(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "source_manifest.json"
    cards_path = output_dir / "source_cards.json"
    notes_path = output_dir / "source_notes.md"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    records = manifest.get("sources") if isinstance(manifest, dict) else []
    if not isinstance(records, list):
        records = []
    cards_payload = read_json(cards_path) if cards_path.exists() else {}
    cards = cards_payload.get("cards") if isinstance(cards_payload, dict) else []
    if not isinstance(cards, list):
        cards = []
    image_count = 0
    missing: list[str] = []
    text_chars = 0
    markdown_paths: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        image_count += len(record.get("images") if isinstance(record.get("images"), list) else [])
        missing.extend(str(item) for item in (record.get("missing_evidence") or []) if item)
        text_chars += int(record.get("text_chars") or 0)
        if record.get("markdown_path"):
            markdown_paths.append(str(record["markdown_path"]))
    return {
        "manifest_exists": manifest_path.exists(),
        "source_cards_exists": cards_path.exists(),
        "source_notes_exists": notes_path.exists(),
        "record_count": len(records),
        "card_count": len(cards),
        "image_count": image_count,
        "missing_evidence": sorted(set(missing)),
        "text_chars": text_chars,
        "markdown_paths": markdown_paths,
    }


def run_case(name: str, source_path: Path, matrix_root: Path, timeout: int) -> dict[str, Any]:
    output_dir = matrix_root / "outputs" / name
    step = run(
        [
            sys.executable,
            SCRIPT_DIR / "source_to_markdown.py",
            source_path,
            "--output-dir",
            output_dir,
            "--max-cards-per-source",
            "4",
        ],
        cwd=matrix_root,
        timeout=timeout,
    )
    parsed = parse_stdout_json(step)
    stats = inspect_output(output_dir)
    expected = case_expectations(name)
    failures: list[str] = []
    if step.get("status") != "passed":
        failures.append("source_to_markdown failed")
    if stats["record_count"] < expected["min_records"]:
        failures.append(f"record count {stats['record_count']} below {expected['min_records']}")
    if stats["card_count"] < expected["min_cards"]:
        failures.append(f"card count {stats['card_count']} below {expected['min_cards']}")
    if stats["image_count"] < expected["min_images"]:
        failures.append(f"image count {stats['image_count']} below {expected['min_images']}")
    if not expected["allow_missing_evidence"] and stats["missing_evidence"]:
        failures.append(f"unexpected missing evidence: {', '.join(stats['missing_evidence'])}")
    if parsed.get("failures"):
        failures.append(f"ingest failures: {parsed['failures']}")
    return {
        "name": name,
        "input": str(source_path),
        "output_dir": str(output_dir),
        "ok": not failures,
        "stats": stats,
        "expectations": expected,
        "failures": failures,
        "step": step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source Intake Matrix Smoke",
        "",
        f"- OK: `{str(report.get('ok')).lower()}`",
        f"- Cases: `{len(report.get('cases', []))}`",
        f"- Generated at: `{report.get('generated_at')}`",
        f"- Work root: `{report.get('work_root')}`",
        "",
        "## Cases",
        "",
    ]
    for case in report.get("cases", []):
        stats = case.get("stats") if isinstance(case.get("stats"), dict) else {}
        marker = "OK" if case.get("ok") else "FAIL"
        lines.append(
            f"- {marker} `{case.get('name')}` records {stats.get('record_count', 0)}, "
            f"cards {stats.get('card_count', 0)}, images {stats.get('image_count', 0)}, "
            f"text {stats.get('text_chars', 0)}"
        )
        for failure in case.get("failures", [])[:3]:
            lines.append(f"  - {failure}")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="markdown,html,docx,pptx,xlsx,image,zip", help="Comma-separated cases or 'all'.")
    parser.add_argument("--work-root", type=Path, help="Matrix work directory. Defaults to a temporary directory.")
    parser.add_argument("--keep-work", action="store_true", help="Keep temporary fixtures and outputs.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per case in seconds.")
    parser.add_argument("--output", type=Path, help="JSON report path. Default: <cwd>/reports/source_intake_matrix_smoke.json")
    parser.add_argument("--markdown", type=Path, help="Markdown report path. Default: <cwd>/reports/source_intake_matrix_smoke.md")
    parser.add_argument("--enforce", action="store_true", help="Exit non-zero when any case fails.")
    args = parser.parse_args()

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if args.work_root:
        work_root = args.work_root.expanduser().resolve()
        if work_root.exists():
            shutil.rmtree(work_root)
        work_root.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="qiaomu-source-intake-")
        work_root = Path(temp_dir.name).resolve()

    fixtures = make_fixtures(work_root / "fixtures")
    case_names = list(fixtures) if args.cases.strip().lower() == "all" else [
        item.strip() for item in args.cases.split(",") if item.strip()
    ]
    unknown = [name for name in case_names if name not in fixtures]
    if unknown:
        raise SystemExit(f"unknown case(s): {', '.join(unknown)}")
    cases = [run_case(name, fixtures[name], work_root, args.timeout) for name in case_names]
    failures = [
        f"{case['name']}: " + "; ".join(case.get("failures") or ["failed"])
        for case in cases
        if not case.get("ok")
    ]
    report = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/source_intake_matrix_smoke.py",
        "ok": not failures,
        "generated_at": utc_now(),
        "work_root": str(work_root),
        "kept_work": bool(args.keep_work or args.work_root),
        "case_names": case_names,
        "cases": cases,
        "failures": failures,
    }
    base = Path.cwd()
    output = args.output or base / "reports" / "source_intake_matrix_smoke.json"
    markdown = args.markdown or base / "reports" / "source_intake_matrix_smoke.md"
    write_json(output, report)
    write_text(markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if temp_dir and not args.keep_work:
        temp_dir.cleanup()
    if args.enforce and failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
