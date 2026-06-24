#!/usr/bin/env python3
"""Ingest mixed source files into qiaomu-ppt Markdown artifacts.

This is the PPT-facing source intake layer inspired by the local
qiaomu-anything-to-notebooklm workflow. It is self-contained: NotebookLM,
markitdown, OCR, and Feishu connectors are optional enhancement routes, not hard
runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from url_to_markdown import (  # noqa: E402
    cleanup_markdown,
    hash_text,
    ingest as ingest_url_or_pdf,
    is_url,
    now_iso,
    slugify,
    update_manifest,
    write_markdown,
)
from paper_to_markdown import ingest_paper, looks_like_paper_input  # noqa: E402
from source_cards import build_cards, write_outputs  # noqa: E402


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".xml", ".html", ".htm"}
PDF_EXTENSIONS = {".pdf"}
EPUB_EXTENSIONS = {".epub"}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp"}
ARCHIVE_EXTENSIONS = {".zip"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | PDF_EXTENSIONS | EPUB_EXTENSIONS | OFFICE_EXTENSIONS | IMAGE_EXTENSIONS | ARCHIVE_EXTENSIONS
OFFICE_MEDIA_PREFIXES = {
    ".docx": ("word/media/",),
    ".pptx": ("ppt/media/",),
    ".xlsx": ("xl/media/",),
}
FEISHU_HOST_TOKENS = {"feishu.cn", "larksuite.com", "larkoffice.com"}
WECHAT_HOST_TOKENS = {"mp.weixin.qq.com"}
WECHAT_OPEN_SOURCE_CANDIDATES = [
    {
        "name": "jackwener/wechat-article-to-markdown",
        "url": "https://github.com/jackwener/wechat-article-to-markdown",
        "fit": "Primary optional extractor. Camoufox browser route, Markdown output, local image downloads, code-snippet handling.",
    },
    {
        "name": "gxcsoccer/wechat-article-crawler",
        "url": "https://github.com/gxcsoccer/wechat-article-crawler",
        "fit": "Crawl4AI route, MicroMessenger UA, lazy image repair, local image downloads with Referer.",
    },
    {
        "name": "fengxxc/wechatmp2markdown",
        "url": "https://github.com/fengxxc/wechatmp2markdown",
        "fit": "Go CLI/server route, Markdown output, optional local image save/zip response.",
    },
    {
        "name": "Digidai/website2markdown",
        "url": "https://github.com/Digidai/website2markdown",
        "fit": "General website-to-Markdown service with WeChat adapter, MicroMessenger UA, image proxy.",
    },
]


def optional_command(name: str) -> str | None:
    found = shutil.which(name)
    return found


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def is_feishu_url(value: str) -> bool:
    if not is_url(value):
        return False
    host = urlparse(value).netloc.lower()
    return any(token in host for token in FEISHU_HOST_TOKENS)


def is_wechat_url(value: str) -> bool:
    if not is_url(value):
        return False
    host = urlparse(value).netloc.lower()
    return any(token == host for token in WECHAT_HOST_TOKENS)


def strip_xml_text(xml_text: str) -> str:
    try:
        root = ElementTree.fromstring(xml_text)
    except Exception:
        return ""
    parts: list[str] = []
    for element in root.iter():
        if element.text and element.text.strip():
            parts.append(element.text.strip())
    return cleanup_markdown("\n".join(parts))


def markitdown_convert(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    markitdown = optional_command("markitdown")
    if not markitdown:
        return "", ["markitdown unavailable"]
    try:
        proc = subprocess.run(
            [markitdown, str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
    except Exception as exc:
        return "", [f"markitdown failed: {exc}"]
    if proc.returncode != 0:
        warnings.append(f"markitdown returned {proc.returncode}: {proc.stderr.strip()[:300]}")
    if proc.stdout.strip():
        return cleanup_markdown(proc.stdout), warnings
    warnings.append("markitdown produced no text")
    return "", warnings


def extract_epub(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not zipfile.is_zipfile(path):
        return "", ["epub is not a valid zip archive"]
    chapters: list[tuple[str, str]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            html_names = [
                name
                for name in names
                if name.lower().endswith((".xhtml", ".html", ".htm"))
                and "nav" not in Path(name).name.lower()
            ]
            # OPF spine ordering is ideal, but many EPUBs work well enough with
            # archive order. Prefer common chapter-like names when present.
            html_names.sort(key=lambda item: (0 if re.search(r"(chapter|chap|split|part|section|正文)", item, re.I) else 1, item))
            for idx, name in enumerate(html_names, start=1):
                raw = archive.read(name).decode("utf-8", errors="replace")
                text = html_to_plain_text(raw)
                if text:
                    chapters.append((name, f"## {idx:03d}. {Path(name).stem}\n\n{text}"))
    except Exception as exc:
        return "", [f"epub extraction failed: {exc}"]
    if not chapters:
        warnings.append("no readable html chapters found in epub")
    toc = "\n".join(f"- {idx + 1:03d}: {name}" for idx, (name, _) in enumerate(chapters))
    body = "\n\n".join(text for _, text in chapters)
    if toc:
        body = f"# EPUB Contents\n\n{toc}\n\n{body}"
    return cleanup_markdown(body), warnings


def html_to_plain_text(html: str) -> str:
    html = re.sub(r"<(script|style|svg|head|noscript)\b.*?</\1>", "\n", html, flags=re.I | re.S)
    html = re.sub(r"</?(h[1-6]|p|div|section|article|li|br|tr|table|blockquote)[^>]*>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = (
        html.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    return cleanup_markdown(html)


def extract_docx(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            parts = []
            for name in names:
                if name.startswith("word/") and name.endswith(".xml") and (
                    name == "word/document.xml" or name.startswith("word/comments") or name.startswith("word/footnotes")
                ):
                    text = strip_xml_text(archive.read(name).decode("utf-8", errors="replace"))
                    if text:
                        parts.append(f"## {Path(name).stem}\n\n{text}")
            return cleanup_markdown("\n\n".join(parts)), warnings
    except Exception as exc:
        return "", [f"docx fallback extraction failed: {exc}"]


def extract_pptx(path: Path) -> tuple[str, list[str]]:
    try:
        with zipfile.ZipFile(path) as archive:
            slide_names = sorted(
                [name for name in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name)],
                key=lambda value: int(re.search(r"slide(\d+)\.xml$", value).group(1)),  # type: ignore[union-attr]
            )
            note_names = sorted(
                [name for name in archive.namelist() if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", name)],
                key=lambda value: int(re.search(r"notesSlide(\d+)\.xml$", value).group(1)),  # type: ignore[union-attr]
            )
            parts: list[str] = []
            for idx, name in enumerate(slide_names, start=1):
                text = strip_xml_text(archive.read(name).decode("utf-8", errors="replace"))
                if text:
                    parts.append(f"## Slide {idx}\n\n{text}")
            for idx, name in enumerate(note_names, start=1):
                text = strip_xml_text(archive.read(name).decode("utf-8", errors="replace"))
                if text:
                    parts.append(f"## Notes {idx}\n\n{text}")
            return cleanup_markdown("\n\n".join(parts)), []
    except Exception as exc:
        return "", [f"pptx fallback extraction failed: {exc}"]


def extract_xlsx(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_text = strip_xml_text(archive.read("xl/sharedStrings.xml").decode("utf-8", errors="replace"))
                shared_strings = [line.strip() for line in shared_text.splitlines() if line.strip()]
            sheet_names = sorted(name for name in archive.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", name))
            parts = []
            for idx, name in enumerate(sheet_names, start=1):
                raw = archive.read(name).decode("utf-8", errors="replace")
                cell_values = re.findall(r"<v>(.*?)</v>", raw, flags=re.S)
                values = []
                for value in cell_values:
                    value = value.strip()
                    if value.isdigit() and shared_strings:
                        numeric = int(value)
                        values.append(shared_strings[numeric] if numeric < len(shared_strings) else value)
                    else:
                        values.append(value)
                if values:
                    parts.append(f"## Sheet {idx}\n\n" + "\n".join(values))
            if not parts:
                warnings.append("xlsx fallback extracted no visible cell values")
            return cleanup_markdown("\n\n".join(parts)), warnings
    except Exception as exc:
        return "", [f"xlsx fallback extraction failed: {exc}"]


def extract_zip_media_images(
    path: Path,
    output_dir: Path,
    *,
    role: str,
    max_images: int,
    prefixes: tuple[str, ...] = (),
) -> tuple[list[dict[str, str]], list[str]]:
    if max_images <= 0:
        return [], []
    warnings: list[str] = []
    if not zipfile.is_zipfile(path):
        return [], [f"{path.suffix.lower().lstrip('.') or 'zip'} media extraction skipped: not a zip archive"]
    target_dir = output_dir / "images" / f"{role}-{slugify(path.stem)}-{hash_text(str(path), 8)}"
    images: list[dict[str, str]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = []
            for name in archive.namelist():
                suffix = Path(name).suffix.lower()
                if suffix not in IMAGE_EXTENSIONS:
                    continue
                if prefixes and not any(name.startswith(prefix) for prefix in prefixes):
                    continue
                names.append(name)
            names = sorted(dict.fromkeys(names))
            if len(names) > max_images:
                warnings.append(f"{role} image count {len(names)} exceeds max_images {max_images}; copied first {max_images}")
            for idx, name in enumerate(names[:max_images], start=1):
                suffix = Path(name).suffix.lower() or ".bin"
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / f"{idx:03d}-{slugify(Path(name).stem)}-{hash_text(path.name + name, 8)}{suffix}"
                target.write_bytes(archive.read(name))
                images.append(
                    {
                        "path": str(target.relative_to(output_dir)),
                        "alt": f"{path.stem} embedded image {idx}",
                        "role": role,
                        "source_path": str(path),
                        "source_archive_member": name,
                    }
                )
    except Exception as exc:
        return images, [f"{role} image extraction failed: {exc}"]
    return images, warnings


def extract_office(path: Path) -> tuple[str, list[str], str]:
    text, warnings = markitdown_convert(path)
    if text:
        return text, warnings, "markitdown"
    suffix = path.suffix.lower()
    if suffix == ".docx":
        fallback_text, fallback_warnings = extract_docx(path)
        return fallback_text, warnings + fallback_warnings, "docx_xml"
    if suffix == ".pptx":
        fallback_text, fallback_warnings = extract_pptx(path)
        return fallback_text, warnings + fallback_warnings, "pptx_xml"
    if suffix == ".xlsx":
        fallback_text, fallback_warnings = extract_xlsx(path)
        return fallback_text, warnings + fallback_warnings, "xlsx_xml"
    return "", warnings, "none"


def extract_image(path: Path) -> tuple[str, list[str], str, list[str]]:
    text, warnings = markitdown_convert(path)
    if text:
        return text, warnings, "markitdown_ocr", []
    missing = ["ocr_required"]
    body = (
        f"# Image Source: {path.name}\n\n"
        "No OCR text was extracted. Use this image as a visual asset candidate only, "
        "or install/configure OCR before using it as text evidence."
    )
    return body, warnings, "image_metadata_only", missing


def source_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return "local_pdf"
    if suffix in EPUB_EXTENSIONS:
        return "epub"
    if suffix in OFFICE_EXTENSIONS:
        return suffix.lstrip("_").lstrip(".")
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in ARCHIVE_EXTENSIONS:
        return "zip"
    if suffix in TEXT_EXTENSIONS:
        return "local_text"
    return "unsupported_file"


def write_record(
    output_dir: Path,
    input_value: str,
    title: str,
    source_type: str,
    fetch_route: str,
    body: str,
    warnings: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    warnings = warnings or []
    missing_evidence = missing_evidence or []
    extracted_dir = output_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(title or Path(input_value).stem or input_value, fallback=f"source-{hash_text(input_value)}")
    markdown_path = extracted_dir / f"{slug}.md"
    if markdown_path.exists():
        markdown_path = extracted_dir / f"{slug}-{hash_text(input_value)}.md"
    write_markdown(markdown_path, title, input_value, source_type, fetch_route, body or "(No useful text extracted.)")
    record: dict[str, Any] = {
        "input": input_value,
        "title": title,
        "source_type": source_type,
        "fetch_route": fetch_route,
        "fetched_at": now_iso(),
        "markdown_path": str(markdown_path.relative_to(output_dir)),
        "images": [],
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "text_chars": len(body or ""),
    }
    if extra:
        record.update(extra)
    manifest_path = update_manifest(output_dir, record)
    record["manifest_path"] = str(manifest_path)
    record["markdown_abs_path"] = str(markdown_path)
    return record


def ingest_feishu_placeholder(input_value: str, output_dir: Path) -> dict[str, Any]:
    title = urlparse(input_value).netloc or "Feishu document"
    body = (
        "# Feishu/Lark Document\n\n"
        f"Input: {input_value}\n\n"
        "This looks like a Feishu/Lark document URL. qiaomu-ppt cannot assume private "
        "document access from a public URL. Export the document as Markdown, DOCX, PDF, "
        "or ZIP, or run an authenticated Feishu connector and place the exported content "
        "under sources/ before writing slide claims."
    )
    return write_record(
        output_dir=output_dir,
        input_value=input_value,
        title=title,
        source_type="feishu_doc",
        fetch_route="feishu_access_required",
        body=body,
        warnings=["feishu document requires export or authenticated connector"],
        missing_evidence=["feishu_content_not_fetched"],
        extra={"access_route": "missing", "comments_included": False, "highlights_included": False},
    )


def ingest_wechat_url(input_value: str, output_dir: Path, download_images: bool, max_images: int) -> dict[str, Any]:
    jackwener_record, jackwener_warnings = ingest_wechat_with_jackwener(input_value, output_dir)
    if jackwener_record:
        return jackwener_record

    record = ingest_url_or_pdf(input_value, output_dir, download_images, max_images)
    record["source_type"] = "wechat_article"
    record["wechat_open_source_candidates"] = WECHAT_OPEN_SOURCE_CANDIDATES
    record.setdefault("warnings", [])
    record["warnings"].extend(jackwener_warnings)
    record["warnings"].append(
        "WeChat articles often need a specialized extractor for full text and hotlink-protected images; "
        "see references/wechat-source-intake.md."
    )
    if record.get("missing_evidence"):
        record["missing_evidence"] = list(dict.fromkeys(record["missing_evidence"] + ["wechat_specialized_extractor_recommended"]))
    if not record.get("images"):
        record["missing_evidence"] = list(dict.fromkeys(record.get("missing_evidence", []) + ["wechat_images_not_extracted"]))
    update_manifest(output_dir, record)
    return record


def ingest_wechat_with_jackwener(input_value: str, output_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    command = optional_command("wechat-article-to-markdown")
    if not command:
        return None, ["preferred WeChat extractor not installed: wechat-article-to-markdown"]

    tool_root = output_dir / "wechat_articles" / hash_text(input_value, 12)
    tool_root.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [command, input_value, "-o", str(tool_root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
        )
    except Exception as exc:
        return None, [f"wechat-article-to-markdown failed before output: {exc}"]

    md_files = sorted(tool_root.rglob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
    if proc.returncode != 0 or not md_files:
        warnings = [f"wechat-article-to-markdown returned {proc.returncode}"]
        if proc.stderr.strip():
            warnings.append(proc.stderr.strip()[:500])
        if proc.stdout.strip():
            warnings.append(proc.stdout.strip()[:500])
        return None, warnings

    markdown_path = md_files[0]
    body = read_text_file(markdown_path)
    title = extract_markdown_title(body) or markdown_path.stem
    images = discover_local_markdown_images(body, markdown_path, output_dir)
    missing_evidence = [] if images else ["wechat_images_not_extracted"]
    warnings = []
    if proc.stderr.strip():
        warnings.append(proc.stderr.strip()[:500])
    record: dict[str, Any] = {
        "input": input_value,
        "title": title,
        "source_type": "wechat_article",
        "fetch_route": "wechat-article-to-markdown",
        "fetched_at": now_iso(),
        "markdown_path": str(markdown_path.relative_to(output_dir)),
        "images": images,
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "text_chars": len(body),
        "wechat_extractor": {
            "name": "jackwener/wechat-article-to-markdown",
            "url": "https://github.com/jackwener/wechat-article-to-markdown",
            "command": "wechat-article-to-markdown",
        },
        "wechat_open_source_candidates": WECHAT_OPEN_SOURCE_CANDIDATES,
    }
    manifest_path = update_manifest(output_dir, record)
    record["manifest_path"] = str(manifest_path)
    record["markdown_abs_path"] = str(markdown_path)
    return record, []


def extract_markdown_title(markdown: str) -> str:
    for line in markdown.splitlines()[:40]:
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def discover_local_markdown_images(markdown: str, markdown_path: Path, output_dir: Path) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", markdown):
        alt = match.group(1).strip()
        raw_path = match.group(2).strip()
        if not raw_path or is_url(raw_path) or raw_path.startswith("data:"):
            continue
        path = (markdown_path.parent / raw_path).resolve()
        if not path.exists():
            continue
        try:
            rel_path = str(path.relative_to(output_dir.resolve()))
        except ValueError:
            rel_path = str(path)
        images.append({"path": rel_path, "alt": alt, "role": "wechat_article_image"})
    return images


def ingest_file(path: Path, output_dir: Path, download_images: bool = False, max_images: int = 12) -> dict[str, Any]:
    path = path.expanduser().resolve()
    suffix = path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return ingest_url_or_pdf(str(path), output_dir, download_images, max(1, max_images))
    if suffix in TEXT_EXTENSIONS:
        body = read_text_file(path)
        return write_record(output_dir, str(path), path.stem, source_type_for_path(path), "direct_text", body)
    if suffix in EPUB_EXTENSIONS:
        body, warnings = extract_epub(path)
        images, image_warnings = extract_zip_media_images(
            path,
            output_dir,
            role="epub_image",
            max_images=max_images,
        )
        warnings.extend(image_warnings)
        missing = [] if body else ["epub_text_extraction_failed"]
        return write_record(
            output_dir,
            str(path),
            path.stem,
            "epub",
            "epub_zip_html",
            body,
            warnings,
            missing,
            extra={"images": images, "embedded_image_count": len(images)} if images else {"embedded_image_count": 0},
        )
    if suffix in OFFICE_EXTENSIONS:
        body, warnings, route = extract_office(path)
        images, image_warnings = extract_zip_media_images(
            path,
            output_dir,
            role=f"{suffix.lstrip('.')}_embedded_image",
            max_images=max_images,
            prefixes=OFFICE_MEDIA_PREFIXES.get(suffix, ()),
        )
        warnings.extend(image_warnings)
        missing = [] if body else [f"{suffix.lstrip('.')}_text_extraction_failed"]
        return write_record(
            output_dir,
            str(path),
            path.stem,
            source_type_for_path(path),
            route,
            body,
            warnings,
            missing,
            extra={"images": images, "embedded_image_count": len(images)} if images else {"embedded_image_count": 0},
        )
    if suffix in IMAGE_EXTENSIONS:
        body, warnings, route, missing = extract_image(path)
        rel_image = copy_visual_asset(path, output_dir)
        return write_record(
            output_dir,
            str(path),
            path.stem,
            "image",
            route,
            body,
            warnings,
            missing,
            extra={"images": [{"path": rel_image, "source_path": str(path), "role": "visual_asset_candidate"}]},
        )
    raise ValueError(f"unsupported source file type: {path}")


def copy_visual_asset(path: Path, output_dir: Path) -> str:
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / f"{slugify(path.stem)}-{hash_text(str(path), 8)}{path.suffix.lower()}"
    shutil.copy2(path, target)
    return str(target.relative_to(output_dir))


def ingest_zip(path: Path, output_dir: Path, max_files: int, download_images: bool = False, max_images: int = 12) -> list[dict[str, Any]]:
    extract_root = output_dir / "extracted" / f"{slugify(path.stem)}-{hash_text(str(path), 8)}"
    extract_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        archive.extractall(extract_root)
    files = [item for item in extract_root.rglob("*") if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS - ARCHIVE_EXTENSIONS]
    for item in files[:max_files]:
        try:
            record = ingest_file(item, output_dir, download_images=download_images, max_images=max_images)
            record["archive_source"] = str(path)
            records.append(record)
        except Exception as exc:
            records.append(
                write_record(
                    output_dir,
                    str(item),
                    item.stem,
                    "archive_member_error",
                    "zip_extract",
                    f"Failed to ingest archive member: {exc}",
                    warnings=[str(exc)],
                    missing_evidence=["archive_member_ingestion_failed"],
                )
            )
    if len(files) > max_files:
        records.append(
            write_record(
                output_dir,
                str(path),
                f"{path.stem} archive overflow",
                "zip",
                "zip_extract",
                f"Archive contained {len(files)} supported files; ingested first {max_files}.",
                warnings=[f"archive supported file count {len(files)} exceeds max_files {max_files}"],
                missing_evidence=["archive_partially_ingested"],
            )
        )
    return records


def iter_folder_files(path: Path, max_files: int) -> list[Path]:
    files = [item for item in sorted(path.rglob("*")) if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS]
    return files[:max_files]


def ingest_input(input_value: str, output_dir: Path, download_images: bool, max_images: int, max_files: int) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if looks_like_paper_input(input_value):
        return [ingest_paper(input_value, output_dir, pdf_fallback=True)]
    if is_feishu_url(input_value):
        return [ingest_feishu_placeholder(input_value, output_dir)]
    if is_wechat_url(input_value):
        return [ingest_wechat_url(input_value, output_dir, download_images, max_images)]
    if is_url(input_value):
        return [ingest_url_or_pdf(input_value, output_dir, download_images, max_images)]

    path = Path(input_value).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"input does not exist: {path}")
    if path.is_dir():
        records: list[dict[str, Any]] = []
        for item in iter_folder_files(path, max_files):
            if item.suffix.lower() in ARCHIVE_EXTENSIONS:
                records.extend(
                    ingest_zip(
                        item,
                        output_dir,
                        max_files=max_files,
                        download_images=download_images,
                        max_images=max_images,
                    )
                )
            else:
                records.append(ingest_file(item, output_dir, download_images=download_images, max_images=max_images))
        return records
    if path.suffix.lower() in ARCHIVE_EXTENSIONS:
        return ingest_zip(path, output_dir, max_files=max_files, download_images=download_images, max_images=max_images)
    return [ingest_file(path, output_dir, download_images=download_images, max_images=max_images)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest mixed qiaomu-ppt sources into Markdown and source_manifest.json.")
    parser.add_argument("inputs", nargs="+", help="URLs, files, folders, or ZIP archives.")
    parser.add_argument("--output-dir", "-o", default="sources", help="Output source directory.")
    parser.add_argument("--download-images", action="store_true", help="Download URL images when ingesting web pages.")
    parser.add_argument("--max-images", type=int, default=12, help="Maximum URL images to record/download.")
    parser.add_argument("--max-files", type=int, default=80, help="Maximum files to ingest from a folder or ZIP.")
    parser.add_argument("--max-cards-per-source", type=int, default=3, help="First-pass source cards to build per source.")
    parser.add_argument("--no-build-cards", action="store_true", help="Skip source_notes.md and source_cards.json generation.")
    args = parser.parse_args()

    all_records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    output_dir = Path(args.output_dir)
    for input_value in args.inputs:
        try:
            all_records.extend(
                ingest_input(
                    input_value=input_value,
                    output_dir=output_dir,
                    download_images=args.download_images,
                    max_images=args.max_images,
                    max_files=args.max_files,
                )
            )
        except Exception as exc:
            failures.append({"input": input_value, "error": str(exc)})

    card_outputs: dict[str, Any] = {}
    if all_records and not args.no_build_cards:
        try:
            card_payload = build_cards(output_dir, max_cards_per_source=args.max_cards_per_source)
            card_outputs = write_outputs(output_dir, card_payload)
            card_outputs.update(
                {
                    "cards": len(card_payload.get("cards", [])),
                    "image_candidates": len(card_payload.get("image_candidates", [])),
                    "gaps": len(card_payload.get("gaps", [])),
                }
            )
        except Exception as exc:
            failures.append({"input": str(output_dir / "source_manifest.json"), "error": f"source card build failed: {exc}"})

    result = {
        "schema_version": "1.0.0",
        "ingested": len(all_records),
        "records": all_records,
        "failures": failures,
        "output_dir": str(output_dir),
        "source_card_outputs": card_outputs,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
