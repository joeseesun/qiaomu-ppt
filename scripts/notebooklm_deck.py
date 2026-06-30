#!/usr/bin/env python3
"""Generate a NotebookLM-native slide deck from qiaomu-ppt.

This route is self-contained and calls the installed ``notebooklm`` CLI
directly. It does not import or depend on qiaomu-anything-to-notebooklm.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LANGUAGE = "zh_Hans"
STYLE_PROMPTS_PATH = SCRIPT_DIR.parent / "data" / "notebooklm_style_prompts.json"
NOTEBOOKLM_VISIBLE_COPY_GUARD = (
    "可见文案边界：本提示中的风格、结构、可读性、视觉和工具流程说明只用于生成，"
    "不得写进幻灯片画布。不要把任何规则名称、字段名、风格名称、生成方式、工具流程或制作者说明"
    "当作标题、副标题、标签或脚注。"
    "幻灯片可见文字只允许来自来源内容中的观众判断、概念名称、证据锚点和行动结论。"
)

LANGUAGE_ALIASES = {
    "zh": "zh_Hans",
    "zh-cn": "zh_Hans",
    "zh_cn": "zh_Hans",
    "zh-hans": "zh_Hans",
    "zh_hans": "zh_Hans",
    "cn": "zh_Hans",
    "简体中文": "zh_Hans",
    "中文": "zh_Hans",
    "zh-tw": "zh_Hant",
    "zh_tw": "zh_Hant",
    "zh-hant": "zh_Hant",
    "zh_hant": "zh_Hant",
    "繁体中文": "zh_Hant",
}

FALLBACK_STYLE_PROMPTS = {
    "火柴人": (
        "整体视觉风格使用清晰的火柴人/白板手绘风格：黑白线条为主，人物和流程用简洁 stick figure 表达；"
        "每页只保留一个核心动作或关系，不要做复杂写实插画；重点用箭头、分镜、对话气泡和少量高亮色帮助理解。"
    ),
    "stick": (
        "Use a clean stick-figure whiteboard style: simple black line characters, arrows, sparse color accents, "
        "and one main action or relationship per slide."
    ),
    "手绘": (
        "整体视觉风格使用手绘图解感：清晰线稿、手写标注感、少量强调色、低装饰密度；"
        "不要使用商务模板式卡片堆叠。"
    ),
    "白板": (
        "整体视觉风格使用白板线稿图解感：留白充足、黑色线条、简洁图解、逐步推演；"
        "用箭头、框线和逐步展开的图解组织信息，不要把白板、讲者或老师等风格说明写到页面上。"
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except Exception:
        return str(path)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "notebooklm-deck"


def normalize_match_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_language_code(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return DEFAULT_LANGUAGE
    return LANGUAGE_ALIASES.get(raw.lower(), raw)


def contains_style_token(query: str, token: str) -> bool:
    token = normalize_match_text(token)
    if not query or not token:
        return False
    if re.search(r"[\u4e00-\u9fff]", token):
        return token in query
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", query))


def load_style_catalog(path: Path = STYLE_PROMPTS_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema_version": "fallback", "global_prompt_rules": [], "styles": []}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid NotebookLM style prompt catalog: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid NotebookLM style prompt catalog: {path}: root must be an object")
    styles = payload.get("styles", [])
    if not isinstance(styles, list):
        raise ValueError(f"Invalid NotebookLM style prompt catalog: {path}: styles must be a list")
    payload["styles"] = [item for item in styles if isinstance(item, dict) and item.get("id") and item.get("prompt")]
    return payload


def style_prompt_catalog_for_cli() -> dict[str, Any]:
    catalog = load_style_catalog()
    return {
        "schema_version": catalog.get("schema_version", ""),
        "updated_at": catalog.get("updated_at", ""),
        "usage": catalog.get("usage", ""),
        "styles": [
            {
                "id": style.get("id", ""),
                "name_zh": style.get("name_zh", ""),
                "best_for": style.get("best_for", ""),
                "aliases": style.get("aliases", []),
            }
            for style in catalog.get("styles", [])
        ],
    }


def match_style_preset(styles: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    query = normalize_match_text(query)
    if not query:
        return None
    for style in styles:
        candidates = [str(style.get("id", "")), str(style.get("name_zh", ""))]
        aliases = style.get("aliases", [])
        if isinstance(aliases, list):
            candidates.extend(str(alias) for alias in aliases)
        if any(contains_style_token(query, candidate) for candidate in candidates):
            return style
    return None


def resolve_style_prompt(style: str, style_preset: str = "") -> tuple[str, dict[str, Any]]:
    catalog = load_style_catalog()
    styles = catalog.get("styles", [])
    if not isinstance(styles, list):
        styles = []
    selected: dict[str, Any] | None = None
    if style_preset.strip():
        selected = match_style_preset(styles, style_preset)
        if not selected:
            available = ", ".join(str(item.get("id", "")) for item in styles[:20])
            raise ValueError(f"Unknown --style-preset '{style_preset}'. Available ids: {available}")
    elif style.strip():
        selected = match_style_preset(styles, style)

    parts: list[str] = []
    if selected:
        parts.append(str(selected.get("prompt", "")).strip())
        if style_preset.strip() and style.strip():
            parts.append(f"补充风格方向：{style.strip()}")
        return "\n".join(part for part in parts if part), {
            "id": selected.get("id", ""),
            "name_zh": selected.get("name_zh", ""),
            "best_for": selected.get("best_for", ""),
            "matched_by": "style_preset" if style_preset.strip() else "style",
            "custom_style": style.strip() if style_preset.strip() else "",
            "catalog": rel(SCRIPT_DIR.parent, STYLE_PROMPTS_PATH),
        }

    custom_style = style.strip()
    if custom_style:
        matched: list[str] = []
        lowered = custom_style.lower()
        for key, prompt in FALLBACK_STYLE_PROMPTS.items():
            if key.lower() in lowered:
                matched.append(prompt)
        if matched:
            parts.extend(matched)
        else:
            parts.append(custom_style)
        return "\n".join(part for part in parts if part), {
            "id": "custom",
            "name_zh": custom_style,
            "best_for": "用户自定义 NotebookLM 风格提示词",
            "matched_by": "style",
            "catalog": rel(SCRIPT_DIR.parent, STYLE_PROMPTS_PATH),
        }

    return "", {}


def sanitize_command(cmd: list[str]) -> list[str]:
    return [str(item) for item in cmd]


def run(
    cmd: list[str],
    *,
    timeout: int,
    cwd: Path | None = None,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            [str(item) for item in cmd],
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        timeout_note = f"\ncommand timed out after {timeout}s"
        if not allow_failure:
            raise RuntimeError(
                "command timed out: "
                + " ".join(sanitize_command(cmd))
                + timeout_note
                + f"\nstdout:\n{stdout[-2000:]}\nstderr:\n{stderr[-2000:]}"
            ) from exc
        return subprocess.CompletedProcess([str(item) for item in cmd], 124, stdout, stderr + timeout_note)
    if proc.returncode != 0 and not allow_failure:
        raise RuntimeError(
            "command failed: "
            + " ".join(sanitize_command(cmd))
            + f"\nexit={proc.returncode}\nstdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
        )
    return proc


def load_json_from_stdout(proc: subprocess.CompletedProcess[str]) -> Any:
    return load_json_from_text(proc.stdout)


def load_json_from_text(text: str) -> Any:
    text = str(text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
        if match:
            return json.loads(match.group(1))
        raise


def find_id(payload: Any, keys: tuple[str, ...]) -> str:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for nested in ("notebook", "source", "artifact", "task", "data"):
            value = payload.get(nested)
            found = find_id(value, keys)
            if found:
                return found
        for value in payload.values():
            found = find_id(value, keys)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_id(item, keys)
            if found:
                return found
    return ""


def notebooklm_available() -> str:
    found = shutil.which("notebooklm")
    if not found:
        raise RuntimeError("notebooklm CLI not found. Install/login to NotebookLM before using this route.")
    return found


def create_notebook(title: str, *, timeout: int) -> tuple[str, dict[str, Any]]:
    proc = run(["notebooklm", "create", "--json", title], timeout=timeout)
    payload = load_json_from_stdout(proc)
    notebook_id = find_id(payload, ("notebook_id", "id"))
    if not notebook_id:
        raise RuntimeError(f"Cannot parse NotebookLM notebook id from output:\n{proc.stdout}")
    run(["notebooklm", "use", notebook_id], timeout=timeout, allow_failure=True)
    return notebook_id, payload if isinstance(payload, dict) else {"raw": payload}


def add_source(notebook_id: str, source: str, *, timeout: int) -> dict[str, Any]:
    title = ""
    path = Path(source).expanduser()
    source_type = ""
    if path.exists():
        title = path.stem
        source_arg = str(path.resolve())
        source_type = "file"
    else:
        source_arg = source
    cmd = ["notebooklm", "source", "add", "-n", notebook_id, source_arg, "--json"]
    if source_type:
        cmd.extend(["--type", source_type])
    if title:
        cmd.extend(["--title", title])
    proc = run(cmd, timeout=timeout)
    payload = load_json_from_stdout(proc)
    source_id = find_id(payload, ("source_id", "id"))
    wait_status: dict[str, Any] = {}
    if source_id:
        wait_proc = run(
            ["notebooklm", "source", "wait", "-n", notebook_id, source_id, "--timeout", str(timeout), "--json"],
            timeout=timeout + 10,
            allow_failure=True,
        )
        try:
            wait_status = load_json_from_stdout(wait_proc)
        except Exception:
            wait_status = {"stdout": wait_proc.stdout[-1000:], "stderr": wait_proc.stderr[-1000:], "returncode": wait_proc.returncode}
    return {
        "input": source,
        "source_type": source_type or "auto",
        "source_id": source_id,
        "add": payload,
        "wait": wait_status,
    }


def source_readiness(notebook_id: str, *, timeout: int = 60) -> dict[str, Any]:
    proc = run(
        ["notebooklm", "source", "list", "-n", notebook_id, "--json"],
        timeout=timeout,
        allow_failure=True,
    )
    result: dict[str, Any] = {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-1000:],
    }
    try:
        payload = load_json_from_stdout(proc)
    except Exception:
        return result
    result["payload"] = payload
    sources = payload.get("sources", []) if isinstance(payload, dict) else []
    if isinstance(sources, list):
        statuses: dict[str, int] = {}
        for source in sources:
            if not isinstance(source, dict):
                continue
            status = str(source.get("status") or "unknown")
            statuses[status] = statuses.get(status, 0) + 1
        result["summary"] = {
            "count": len(sources),
            "statuses": statuses,
            "ready_count": statuses.get("ready", 0),
            "error_count": statuses.get("error", 0),
        }
    return result


def list_slide_deck_artifacts(notebook_id: str, *, timeout: int = 60) -> dict[str, Any]:
    proc = run(
        ["notebooklm", "artifact", "list", "-n", notebook_id, "--type", "slide-deck", "--json"],
        timeout=timeout,
        allow_failure=True,
    )
    result: dict[str, Any] = {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-1000:],
    }
    try:
        payload = load_json_from_stdout(proc)
    except Exception:
        return result
    result["payload"] = payload
    artifacts = payload.get("artifacts", []) if isinstance(payload, dict) else []
    result["artifacts"] = artifacts if isinstance(artifacts, list) else []
    return result


def find_newest_slide_deck_artifact(listing: dict[str, Any], *, exclude_ids: set[str] | None = None) -> dict[str, Any]:
    exclude_ids = exclude_ids or set()
    artifacts = listing.get("artifacts", [])
    if not isinstance(artifacts, list):
        return {}
    candidates = [
        item for item in artifacts
        if isinstance(item, dict) and str(item.get("id") or "") and str(item.get("id")) not in exclude_ids
    ]
    if not candidates:
        candidates = [item for item in artifacts if isinstance(item, dict) and str(item.get("id") or "")]
    if not candidates:
        return {}
    return sorted(candidates, key=lambda item: str(item.get("created_at") or ""), reverse=True)[0]


def wait_for_artifact(
    notebook_id: str,
    artifact_id: str,
    *,
    timeout: int,
    interval: int,
) -> dict[str, Any]:
    if not artifact_id:
        return {"status": "skipped", "reason": "missing artifact id"}
    proc = run(
        [
            "notebooklm",
            "artifact",
            "wait",
            artifact_id,
            "-n",
            notebook_id,
            "--timeout",
            str(timeout),
            "--interval",
            str(interval),
            "--json",
        ],
        timeout=timeout + 10,
        allow_failure=True,
    )
    result: dict[str, Any] = {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-1000:],
    }
    try:
        result["payload"] = load_json_from_stdout(proc)
    except Exception:
        pass
    return result


def add_research(
    notebook_id: str,
    query: str,
    *,
    source_from: str,
    mode: str,
    import_all: bool,
    timeout: int,
    wait_timeout: int,
) -> dict[str, Any]:
    cmd = [
        "notebooklm",
        "source",
        "add-research",
        "-n",
        notebook_id,
        query,
        "--from",
        source_from,
        "--mode",
        mode,
    ]
    if import_all:
        cmd.append("--import-all")
    proc = run(cmd, timeout=timeout, allow_failure=True)
    result: dict[str, Any] = {
        "query": query,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }
    if proc.returncode != 0:
        return result
    wait_cmd = [
        "notebooklm",
        "research",
        "wait",
        "-n",
        notebook_id,
        "--timeout",
        str(wait_timeout),
        "--json",
    ]
    if import_all:
        wait_cmd.append("--import-all")
    wait_proc = run(wait_cmd, timeout=wait_timeout + 10, allow_failure=True)
    result["wait_returncode"] = wait_proc.returncode
    try:
        result["wait"] = load_json_from_stdout(wait_proc)
    except Exception:
        result["wait"] = {"stdout": wait_proc.stdout[-4000:], "stderr": wait_proc.stderr[-4000:]}
    result["source_readiness"] = source_readiness(notebook_id, timeout=min(60, max(10, wait_timeout)))
    return result


def build_generation_prompt(args: argparse.Namespace, style_prompt: str) -> str:
    parts: list[str] = [
        "请基于当前 NotebookLM notebook 中的全部来源生成一份中文 PowerPoint 演示文稿。",
    ]
    if args.topic:
        parts.append(f"主题：{args.topic}")
    if args.audience:
        parts.append(f"受众：{args.audience}")
    if args.slide_count:
        parts.append(f"页数：约 {args.slide_count} 页。")
    if style_prompt:
        parts.append("请将以下视觉风格落实到版式和图解中，不能把这段文字照抄进页面：" + style_prompt)
    if args.prompt:
        parts.append(args.prompt.strip())
    if args.presenter_notes:
        parts.append("需要适合 presenter 模式。")
    parts.append(NOTEBOOKLM_VISIBLE_COPY_GUARD)
    parts.append("不要在幻灯片画布上写 NotebookLM、Google、source id、生成流程或内部提示词。")
    return "\n\n".join(part for part in parts if part)


def generate_slide_deck(
    notebook_id: str,
    prompt: str,
    *,
    deck_format: str,
    length: str,
    language: str,
    timeout: int,
    artifact_wait_timeout: int,
    artifact_wait_interval: int,
    retry: int,
) -> dict[str, Any]:
    before_listing = list_slide_deck_artifacts(notebook_id, timeout=60)
    before_ids = {
        str(item.get("id"))
        for item in before_listing.get("artifacts", [])
        if isinstance(item, dict) and item.get("id")
    }
    cmd = [
        "notebooklm",
        "generate",
        "slide-deck",
        "-n",
        notebook_id,
        prompt,
        "--format",
        deck_format,
        "--length",
        length,
        "--language",
        language,
        "--no-wait",
        "--retry",
        str(retry),
        "--json",
    ]
    proc = run(cmd, timeout=timeout, allow_failure=True)
    try:
        payload = load_json_from_stdout(proc)
    except Exception:
        payload = {}
    artifact_id = find_id(payload, ("artifact_id", "id", "task_id"))
    recovered_from_listing = False
    after_listing: dict[str, Any] = {}
    if not artifact_id:
        after_listing = list_slide_deck_artifacts(notebook_id, timeout=60)
        newest = find_newest_slide_deck_artifact(after_listing, exclude_ids=before_ids)
        artifact_id = str(newest.get("id") or "")
        recovered_from_listing = bool(artifact_id)
    if proc.returncode != 0 and not artifact_id:
        raise RuntimeError(
            "NotebookLM slide-deck generation failed before an artifact id could be recovered."
            + f"\nexit={proc.returncode}\nstdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
        )
    artifact_wait = wait_for_artifact(
        notebook_id,
        artifact_id,
        timeout=artifact_wait_timeout,
        interval=artifact_wait_interval,
    )
    return {
        "command": cmd[:5] + ["<prompt>", *cmd[6:]],
        "artifact_id": artifact_id,
        "returncode": proc.returncode,
        "response": payload,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
        "before_artifacts": before_listing,
        "after_artifacts": after_listing,
        "recovered_from_artifact_list": recovered_from_listing,
        "artifact_wait": artifact_wait,
    }


def download_slide_deck(
    notebook_id: str,
    output: Path,
    *,
    fmt: str,
    artifact_id: str,
    timeout: int,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "notebooklm",
        "download",
        "slide-deck",
        "-n",
        notebook_id,
        "--format",
        fmt,
        "--force",
    ]
    if artifact_id:
        cmd.extend(["--artifact", artifact_id])
    else:
        cmd.append("--latest")
    cmd.append(str(output))
    proc = run(cmd, timeout=timeout, allow_failure=True)
    status = "downloaded" if proc.returncode == 0 and output.exists() and output.stat().st_size > 0 else "failed"
    fallback: dict[str, Any] = {}
    if status != "downloaded" and artifact_id:
        latest_cmd = [
            "notebooklm",
            "download",
            "slide-deck",
            "-n",
            notebook_id,
            "--format",
            fmt,
            "--force",
            "--latest",
            str(output),
        ]
        latest_proc = run(latest_cmd, timeout=timeout, allow_failure=True)
        fallback = {
            "command": latest_cmd,
            "returncode": latest_proc.returncode,
            "stdout": latest_proc.stdout[-2000:],
            "stderr": latest_proc.stderr[-2000:],
        }
        if latest_proc.returncode == 0 and output.exists() and output.stat().st_size > 0:
            status = "downloaded"
    return {
        "status": status,
        "path": str(output) if output.exists() else "",
        "format": fmt,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
        "fallback_latest": fallback,
    }


def run_watermark_cleanup(
    raw_pptx: Path,
    clean_pptx: Path,
    clean_pdf: Path,
    report: Path,
    *,
    remove_corner_logo: bool,
    inpaint_raster_watermark: bool,
    timeout: int,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "strip_notebooklm_watermark.py"),
        str(raw_pptx),
        "--output",
        str(clean_pptx),
        "--report",
        str(report),
        "--pdf-output",
        str(clean_pdf),
        "--pdf-timeout",
        str(timeout),
    ]
    if remove_corner_logo:
        cmd.append("--remove-corner-logo")
    if inpaint_raster_watermark:
        cmd.append("--inpaint-raster-watermark")
    proc = run(cmd, timeout=timeout + 30, allow_failure=True)
    payload: dict[str, Any] = {}
    if report.exists():
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    return {
        "status": "completed" if clean_pptx.exists() else "failed",
        "command": cmd,
        "returncode": proc.returncode,
        "report": str(report),
        "payload": payload,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


def run_text_check(project: Path, pptx: Path, report: Path, *, timeout: int) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "pptx_text_check.py"),
        str(pptx),
        "--allow-image-backed",
        "--output",
        str(report),
    ]
    proc = run(cmd, timeout=timeout, allow_failure=True)
    return {
        "status": "passed" if proc.returncode == 0 else "failed",
        "command": cmd,
        "returncode": proc.returncode,
        "report": rel(project, report),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


def run_preview(project: Path, pptx: Path, *, timeout: int, force: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "pptx_preview.py"),
        str(pptx),
        "--project",
        str(project),
        "--output-dir",
        str(project / "previews" / "notebooklm"),
    ]
    if force:
        cmd.append("--force")
    proc = run(cmd, timeout=timeout, allow_failure=True)
    return {
        "status": "passed" if proc.returncode == 0 else "failed",
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


def write_export_manifest(
    project: Path,
    *,
    raw_pptx: Path,
    clean_pptx: Path,
    raw_pdf: Path,
    clean_pdf: Path,
    cleanup: dict[str, Any],
) -> dict[str, Any]:
    formats: dict[str, Any] = {
        "pptx": {
            "status": "exported" if clean_pptx.exists() else "failed",
            "path": rel(project, clean_pptx) if clean_pptx.exists() else "",
            "source": "notebooklm-native-slide-deck",
            "image_backed_ok": True,
            "editable_expectation": "notebooklm-native; may contain image-backed slides",
            "watermark_cleanup_report": rel(project, Path(str(cleanup.get("report", "")))) if cleanup.get("report") else "",
        },
        "pdf": {
            "status": "exported" if clean_pdf.exists() else ("existing" if raw_pdf.exists() else "missing"),
            "path": rel(project, clean_pdf if clean_pdf.exists() else raw_pdf) if (clean_pdf.exists() or raw_pdf.exists()) else "",
            "source": "cleaned-pptx-libreoffice" if clean_pdf.exists() else "notebooklm-raw-pdf",
            "warning": "" if clean_pdf.exists() else "Clean PDF could not be regenerated from cleaned PPTX; raw NotebookLM PDF may still contain service watermark.",
        },
    }
    raw_formats = {
        "raw_notebooklm_pptx": {"status": "existing" if raw_pptx.exists() else "missing", "path": rel(project, raw_pptx) if raw_pptx.exists() else ""},
        "raw_notebooklm_pdf": {"status": "existing" if raw_pdf.exists() else "missing", "path": rel(project, raw_pdf) if raw_pdf.exists() else ""},
    }
    manifest = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/notebooklm_deck.py",
        "generated_at": utc_now(),
        "route": "notebooklm_native_slide_deck",
        "requested_formats": ["pptx", "pdf"],
        "last_requested_formats": ["pptx", "pdf"],
        "formats": formats,
        "raw_formats": raw_formats,
        "notes": [
            "NotebookLM-native PPTX is an explicit route and may be image-backed.",
            "Use qiaomu-ppt SVG-first production when the user needs normal editable foreground objects.",
        ],
    }
    write_json(project / "export_manifest.json", manifest)
    return manifest


def render_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# NotebookLM Native Deck Report",
        "",
        f"- OK: `{str(manifest.get('ok')).lower()}`",
        f"- Notebook ID: `{manifest.get('notebook_id', '')}`",
        f"- Artifact ID: `{manifest.get('artifact_id', '')}`",
        f"- Route: `notebooklm_native_slide_deck`",
        "",
        "## Outputs",
        "",
    ]
    exports = manifest.get("export_manifest", {}).get("formats", {})
    if isinstance(exports, dict):
        for name, item in exports.items():
            if isinstance(item, dict):
                path = item.get("path") or ""
                warning = item.get("warning") or ""
                lines.append(f"- `{name}`: {item.get('status')} `{path}`" + (f" ({warning})" if warning else ""))
    lines.extend(["", "## Warnings", ""])
    for warning in manifest.get("warnings", []):
        lines.append(f"- {warning}")
    if not manifest.get("warnings"):
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path, help="Project directory to store NotebookLM artifacts.")
    parser.add_argument("--title", default="", help="Notebook/deck title.")
    parser.add_argument("--topic", default="", help="Topic hint for generation prompt.")
    parser.add_argument("--input", action="append", default=[], help="URL, YouTube URL, local file, or inline source. Repeatable.")
    parser.add_argument("--search", action="append", default=[], help="NotebookLM research/search query. Repeatable.")
    parser.add_argument("--research-from", choices=["web", "drive"], default="web")
    parser.add_argument("--research-mode", choices=["fast", "deep"], default="fast")
    parser.add_argument("--no-import-all", action="store_true", help="Do not auto-import all NotebookLM research results.")
    parser.add_argument("--notebook-id", default="", help="Use an existing NotebookLM notebook instead of creating one.")
    parser.add_argument("--prompt", default="", help="Custom slide-deck prompt requirements.")
    parser.add_argument("--style", default="", help="Natural-language style hint, e.g. 火柴人风格.")
    parser.add_argument("--style-preset", default="", help="NotebookLM style preset id from data/notebooklm_style_prompts.json.")
    parser.add_argument("--list-styles", action="store_true", help="List NotebookLM style preset ids and exit.")
    parser.add_argument("--audience", default="")
    parser.add_argument("--slide-count", type=int, default=0)
    parser.add_argument("--format", choices=["detailed", "presenter"], default="presenter")
    parser.add_argument("--length", choices=["default", "short"], default="short")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--presenter-notes", action="store_true")
    parser.add_argument("--slug", default="")
    parser.add_argument("--retry", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--research-wait-timeout",
        type=int,
        default=180,
        help="Maximum seconds to wait for NotebookLM research import before continuing with source readiness evidence.",
    )
    parser.add_argument(
        "--artifact-wait-timeout",
        type=int,
        default=900,
        help="Maximum seconds to wait for NotebookLM slide-deck artifact completion after creation.",
    )
    parser.add_argument("--artifact-wait-interval", type=int, default=5)
    parser.add_argument("--download-timeout", type=int, default=240)
    parser.add_argument("--keep-corner-logo", action="store_true", help="Do not remove small lower-right corner logo shapes.")
    parser.add_argument(
        "--skip-raster-watermark-inpaint",
        action="store_true",
        help="Do not attempt optional OpenCV cleanup of watermarks baked into NotebookLM media images.",
    )
    parser.add_argument("--skip-text-check", action="store_true")
    parser.add_argument("--preview", action="store_true", help="Render PPTX preview evidence after download.")
    parser.add_argument("--force-preview", action="store_true")
    args = parser.parse_args()

    if args.list_styles:
        print(json.dumps(style_prompt_catalog_for_cli(), ensure_ascii=False, indent=2))
        return 0

    if not args.project:
        parser.error("project is required unless --list-styles is used.")

    try:
        style_prompt, selected_style = resolve_style_prompt(args.style, args.style_preset)
    except ValueError as exc:
        parser.error(str(exc))

    notebooklm_available()
    project = args.project.expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    (project / "reports").mkdir(exist_ok=True)
    (project / "exports").mkdir(exist_ok=True)

    title = args.title or args.topic or project.name
    slug = slugify(args.slug or title or project.name)
    warnings: list[str] = []
    commands_started = time.time()
    language = normalize_language_code(args.language)
    research_wait_timeout = max(10, min(args.timeout, args.research_wait_timeout))
    artifact_wait_timeout = max(30, args.artifact_wait_timeout)
    artifact_wait_interval = max(1, args.artifact_wait_interval)

    if not args.input and not args.search and not args.notebook_id:
        raise SystemExit("Provide at least one --input, --search query, or --notebook-id.")

    notebook_payload: dict[str, Any] = {}
    notebook_id = args.notebook_id.strip()
    if notebook_id:
        run(["notebooklm", "use", notebook_id], timeout=60, allow_failure=True)
    else:
        notebook_id, notebook_payload = create_notebook(title, timeout=120)

    source_results: list[dict[str, Any]] = []
    for source in args.input:
        source_results.append(add_source(notebook_id, source, timeout=args.timeout))

    research_results: list[dict[str, Any]] = []
    for query in args.search:
        research_results.append(
            add_research(
                notebook_id,
                query,
                source_from=args.research_from,
                mode=args.research_mode,
                import_all=not args.no_import_all,
                timeout=args.timeout,
                wait_timeout=research_wait_timeout,
            )
        )
    failed_research = [item for item in research_results if item.get("returncode") not in {0, None}]
    if failed_research:
        warnings.append(f"{len(failed_research)} NotebookLM research query failed; see notebooklm_generation_manifest.json.")

    prompt = build_generation_prompt(args, style_prompt)
    write_text(project / "notebooklm_slide_prompt.txt", prompt)
    generation = generate_slide_deck(
        notebook_id,
        prompt,
        deck_format=args.format,
        length=args.length,
        language=language,
        timeout=args.timeout,
        artifact_wait_timeout=artifact_wait_timeout,
        artifact_wait_interval=artifact_wait_interval,
        retry=args.retry,
    )
    artifact_id = str(generation.get("artifact_id") or "")
    artifact_wait_result = generation.get("artifact_wait") if isinstance(generation.get("artifact_wait"), dict) else {}
    if artifact_wait_result and artifact_wait_result.get("returncode") not in {0, None}:
        warnings.append("NotebookLM artifact wait did not finish cleanly; download will still be attempted and recorded.")

    raw_pptx = project / "exports" / "raw" / f"{slug}.notebooklm.raw.pptx"
    raw_pdf = project / "exports" / "raw" / f"{slug}.notebooklm.raw.pdf"
    clean_pptx = project / "exports" / f"{slug}.notebooklm.pptx"
    clean_pdf = project / "exports" / f"{slug}.notebooklm.pdf"
    pptx_download = download_slide_deck(notebook_id, raw_pptx, fmt="pptx", artifact_id=artifact_id, timeout=args.download_timeout)
    pdf_download = download_slide_deck(notebook_id, raw_pdf, fmt="pdf", artifact_id=artifact_id, timeout=args.download_timeout)
    if pptx_download["status"] != "downloaded":
        raise RuntimeError("NotebookLM PPTX download failed; see manifest output for details.")

    cleanup_report = project / "reports" / "notebooklm_watermark_cleanup.json"
    cleanup = run_watermark_cleanup(
        raw_pptx,
        clean_pptx,
        clean_pdf,
        cleanup_report,
        remove_corner_logo=not args.keep_corner_logo,
        inpaint_raster_watermark=not args.skip_raster_watermark_inpaint,
        timeout=args.download_timeout,
    )
    if cleanup.get("status") != "completed":
        warnings.append("Watermark cleanup did not produce a cleaned PPTX; raw PPTX remains available.")
    cleanup_payload = cleanup.get("payload") if isinstance(cleanup.get("payload"), dict) else {}
    for warning in cleanup_payload.get("warnings", []) if isinstance(cleanup_payload, dict) else []:
        warnings.append(str(warning))

    text_check: dict[str, Any] = {}
    if not args.skip_text_check and clean_pptx.exists():
        text_check = run_text_check(project, clean_pptx, project / "pptx_text_check.json", timeout=180)
        if text_check.get("status") != "passed":
            warnings.append("pptx_text_check.py did not pass; see pptx_text_check.json.")

    preview: dict[str, Any] = {}
    if args.preview and clean_pptx.exists():
        preview = run_preview(project, clean_pptx, timeout=args.download_timeout, force=args.force_preview)
        if preview.get("status") != "passed":
            warnings.append("PPTX preview render failed or dependencies are missing.")

    export_manifest = write_export_manifest(
        project,
        raw_pptx=raw_pptx,
        clean_pptx=clean_pptx,
        raw_pdf=raw_pdf,
        clean_pdf=clean_pdf,
        cleanup=cleanup,
    )

    manifest = {
        "schema_version": "1.0.0",
        "tool": "qiaomu-ppt/scripts/notebooklm_deck.py",
        "generated_at": utc_now(),
        "duration_seconds": round(time.time() - commands_started, 2),
        "ok": clean_pptx.exists(),
        "project": str(project),
        "title": title,
        "slug": slug,
        "notebook_id": notebook_id,
        "research_wait_timeout": research_wait_timeout,
        "artifact_wait_timeout": artifact_wait_timeout,
        "artifact_wait_interval": artifact_wait_interval,
        "notebook_create_response": notebook_payload,
        "source_results": source_results,
        "research_results": research_results,
        "generation_prompt": rel(project, project / "notebooklm_slide_prompt.txt"),
        "language": {
            "requested": args.language,
            "normalized": language,
        },
        "style_request": {
            "style": args.style,
            "style_preset": args.style_preset,
            "resolved": selected_style,
        },
        "generation": generation,
        "artifact_id": artifact_id,
        "downloads": {
            "pptx": pptx_download,
            "pdf": pdf_download,
        },
        "watermark_cleanup": cleanup,
        "text_check": text_check,
        "preview": preview,
        "export_manifest": export_manifest,
        "warnings": warnings,
        "external_skill_dependency": "none",
    }
    write_json(project / "notebooklm_generation_manifest.json", manifest)
    write_text(project / "notebooklm_generation_report.md", render_report(manifest))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
