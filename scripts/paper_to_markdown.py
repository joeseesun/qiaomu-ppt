#!/usr/bin/env python3
"""Ingest arXiv or Hugging Face paper URLs into qiaomu-ppt sources.

The paper route is intentionally self-contained. It absorbs the useful
arXiv/TeX extraction discipline from Qiaomu's paper-reading workflow without
depending on that skill at runtime.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import shutil
import tarfile
import tempfile
import zipfile
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from url_to_markdown import (  # noqa: E402
    cleanup_markdown,
    extract_pdf_text,
    fetch_url,
    hash_text,
    is_url,
    now_iso,
    slugify,
    update_manifest,
    write_markdown,
)


NEW_ARXIV_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?(?!\d)", re.I)
OLD_ARXIV_RE = re.compile(r"\b([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?\b", re.I)
FIGURE_ENV_RE = re.compile(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", re.S)
TABLE_ENV_RE = re.compile(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", re.S)
INCLUDE_GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", re.S)
MEDIA_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".webp"}
MAX_COPIED_MEDIA_BYTES = 20 * 1024 * 1024


def looks_like_paper_input(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if is_url(value):
        parsed = urlparse(value)
        host = parsed.netloc.lower()
        return "arxiv.org" in host or (host == "huggingface.co" and parsed.path.startswith("/papers/"))
    bare = re.sub(r"^arxiv:\s*", "", value, flags=re.I)
    return bool(NEW_ARXIV_RE.fullmatch(bare) or OLD_ARXIV_RE.fullmatch(bare))


def normalize_arxiv_input(value: str, fetch_huggingface: bool = True) -> tuple[str, str, list[str]]:
    """Return arXiv ID, source type, and warnings for arXiv/HF/bare inputs."""
    original = value.strip()
    warnings: list[str] = []
    if not original:
        raise ValueError("empty paper input")

    if is_url(original):
        parsed = urlparse(original)
        host = parsed.netloc.lower()
        path = unescape(parsed.path)

        if "arxiv.org" in host:
            match = re.search(r"/(?:abs|pdf|html|e-print)/([^?#]+)", path)
            if match:
                candidate = match.group(1).replace(".pdf", "").strip("/")
                arxiv_id = extract_arxiv_id_from_text(candidate)
                if arxiv_id:
                    return arxiv_id, "arxiv_paper", warnings

        if host == "huggingface.co" and path.startswith("/papers/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 2:
                arxiv_id = extract_arxiv_id_from_text(parts[1])
                if arxiv_id:
                    return arxiv_id, "huggingface_paper", warnings

            if fetch_huggingface:
                page = fetch_url(original, timeout=30)
                warnings.extend(page.warnings)
                html = page.data.decode("utf-8", errors="replace") if page.data else ""
                arxiv_id = extract_arxiv_id_from_text(html)
                if arxiv_id:
                    return arxiv_id, "huggingface_paper", warnings
            raise ValueError("could not resolve an arXiv ID from Hugging Face paper URL")

    arxiv_id = extract_arxiv_id_from_text(original)
    if arxiv_id:
        return arxiv_id, "arxiv_paper", warnings
    raise ValueError(f"cannot extract arXiv ID from: {value}")


def extract_arxiv_id_from_text(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^arxiv:\s*", "", value, flags=re.I)
    match = NEW_ARXIV_RE.search(value)
    if match:
        return f"{match.group(1)}{match.group(2) or ''}"
    match = OLD_ARXIV_RE.search(value)
    if match:
        return f"{match.group(1)}{match.group(2) or ''}"
    return ""


def safe_arxiv_id(arxiv_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", arxiv_id)


def fetch_arxiv_metadata(arxiv_id: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    result = fetch_url(url, timeout=20)
    warnings.extend(result.warnings)
    if not result.data:
        warnings.append("arxiv api returned no data")
        return {}, warnings
    xml = result.data.decode("utf-8", errors="replace")
    entry_match = re.search(r"<entry>(.*?)</entry>", xml, re.S)
    entry = entry_match.group(1) if entry_match else xml
    title = first_xml_text(entry, "title")
    summary = first_xml_text(entry, "summary")
    published = first_xml_text(entry, "published")
    updated = first_xml_text(entry, "updated")
    authors = re.findall(r"<name>(.*?)</name>", entry, re.S)
    return {
        "title": normalize_space(title),
        "abstract": normalize_space(summary),
        "published_date": published[:10] if published else "",
        "updated_date": updated[:10] if updated else "",
        "authors": [normalize_space(author) for author in authors if normalize_space(author)],
    }, warnings


def first_xml_text(xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, re.S)
    if not match:
        return ""
    return unescape(re.sub(r"<[^>]+>", " ", match.group(1)))


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_extract_tar(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if not str(target).startswith(str(root)):
            continue
        archive.extract(member, destination)


def safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for name in archive.namelist():
        target = (destination / name).resolve()
        if not str(target).startswith(str(root)):
            continue
        archive.extract(name, destination)


def download_and_extract_tex(arxiv_id: str, source_dir: Path) -> tuple[bool, list[str], str]:
    """Download arXiv e-print and extract source files.

    Returns `(has_tex_source, warnings, raw_archive_path)`.
    """
    warnings: list[str] = []
    source_dir.mkdir(parents=True, exist_ok=True)
    eprint_url = f"https://arxiv.org/e-print/{arxiv_id}"
    result = fetch_url(eprint_url, timeout=60)
    warnings.extend(result.warnings)
    if not result.data:
        warnings.append("arxiv e-print returned no data")
        return False, warnings, ""
    if result.status and result.status >= 400:
        warnings.append(f"arxiv e-print returned HTTP {result.status}")
        return False, warnings, ""
    if result.data[:4] == b"%PDF":
        pdf_path = source_dir.parent / "paper.pdf"
        pdf_path.write_bytes(result.data)
        warnings.append("arxiv e-print returned PDF; TeX source unavailable")
        return False, warnings, str(pdf_path)

    raw_path = source_dir.parent / "source-archive.bin"
    raw_path.write_bytes(result.data)

    stream = io.BytesIO(result.data)
    try:
        with tarfile.open(fileobj=stream, mode="r:*") as archive:
            safe_extract_tar(archive, source_dir)
        return True, warnings, str(raw_path)
    except tarfile.TarError:
        pass

    stream = io.BytesIO(result.data)
    try:
        with zipfile.ZipFile(stream) as archive:
            safe_extract_zip(archive, source_dir)
        return True, warnings, str(raw_path)
    except zipfile.BadZipFile:
        pass

    if result.data[:2] == b"\x1f\x8b":
        try:
            decompressed = gzip.decompress(result.data)
            (source_dir / "source.tex").write_bytes(decompressed)
            return True, warnings, str(raw_path)
        except Exception as exc:
            warnings.append(f"gzip source extraction failed: {exc}")

    if b"\\documentclass" in result.data or b"\\begin{document}" in result.data:
        (source_dir / "source.tex").write_bytes(result.data)
        return True, warnings, str(raw_path)

    warnings.append("arxiv e-print did not look like TeX, tar, zip, gzip, or PDF")
    return False, warnings, str(raw_path)


def find_main_tex(source_dir: Path) -> Path | None:
    tex_files = sorted(source_dir.rglob("*.tex"))
    if not tex_files:
        return None
    preferred_names = {"main", "paper", "article", "root", "ms"}
    for tex_file in tex_files:
        if tex_file.stem.lower() in preferred_names:
            return tex_file
    for tex_file in tex_files:
        try:
            content = tex_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if r"\begin{document}" in content:
            return tex_file
    return max(tex_files, key=lambda item: item.stat().st_size)


def strip_latex_comments(content: str) -> str:
    lines = []
    for line in content.splitlines():
        lines.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(lines)


def resolve_inputs(content: str, base_dir: Path, seen: set[Path] | None = None) -> str:
    seen = seen or set()

    def replace(match: re.Match[str]) -> str:
        raw_name = match.group(1).strip()
        candidates = []
        raw_path = Path(raw_name)
        if raw_path.suffix:
            candidates.append(base_dir / raw_path)
        else:
            candidates.extend([base_dir / raw_path, base_dir / f"{raw_name}.tex"])
        candidates.extend(base_dir.glob(f"**/{raw_path.name if raw_path.suffix else raw_path.name + '.tex'}"))
        for candidate in candidates:
            candidate = candidate.resolve()
            if not candidate.exists() or candidate in seen:
                continue
            seen.add(candidate)
            try:
                sub = candidate.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            sub = strip_latex_comments(sub)
            sub = re.sub(r"^.*?\\begin\{document\}", "", sub, flags=re.S)
            sub = re.sub(r"\\end\{document\}.*$", "", sub, flags=re.S)
            return resolve_inputs(sub, candidate.parent, seen)
        return f"[missing input: {raw_name}]"

    return re.sub(r"\\(?:input|include)\{([^}]+)\}", replace, content)


def find_balanced_brace(text: str, open_index: int) -> int:
    depth = 0
    for idx in range(open_index, len(text)):
        char = text[idx]
        if char == "{" and (idx == 0 or text[idx - 1] != "\\"):
            depth += 1
        elif char == "}" and (idx == 0 or text[idx - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return idx
    return -1


def command_argument(text: str, command: str) -> str:
    start = text.find(f"\\{command}")
    if start < 0:
        return ""
    brace_start = text.find("{", start)
    if brace_start < 0:
        return ""
    brace_end = find_balanced_brace(text, brace_start)
    if brace_end < 0:
        return ""
    return text[brace_start + 1 : brace_end]


def clean_latex_text(value: str) -> str:
    value = value or ""
    value = re.sub(r"\\label\{[^}]*\}", "", value)
    value = re.sub(r"\\(?:cite|citep|citet|autocite|parencite)(?:\[[^\]]*\])?\{[^}]+\}", "[citation]", value)
    value = re.sub(r"\\(?:ref|autoref|cref|Cref)\{([^}]+)\}", r"[\1]", value)
    value = re.sub(r"\\url\{([^}]+)\}", r"\1", value)
    value = re.sub(r"\\href\{([^}]+)\}\{([^}]+)\}", r"[\2](\1)", value)
    value = re.sub(r"\\footnote\{([^{}]*)\}", r" (note: \1)", value)
    value = re.sub(r"\\item(?:\[[^\]]+\])?", "\n- ", value)
    for _ in range(4):
        value = re.sub(
            r"\\(?:textbf|textit|emph|texttt|textrm|textsf|underline|small|large|Large|footnotesize)\{([^{}]*)\}",
            r"\1",
            value,
        )
    value = re.sub(r"\\begin\{(?:center|flushleft|flushright|itemize|enumerate)\}", "\n", value)
    value = re.sub(r"\\end\{(?:center|flushleft|flushright|itemize|enumerate)\}", "\n", value)
    value = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", " ", value)
    value = value.replace(r"\&", "&").replace(r"\%", "%").replace(r"\#", "#").replace(r"\_", "_")
    value = value.replace("~", " ").replace("``", '"').replace("''", '"')
    value = re.sub(r"[{}]", "", value)
    return cleanup_markdown(normalize_space(value))


def extract_title_author(content: str) -> tuple[str, list[str]]:
    title = clean_latex_text(command_argument(content, "title"))
    author_text = command_argument(content, "author")
    authors: list[str] = []
    if author_text:
        author_text = re.sub(r"\\thanks\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", "", author_text, flags=re.S)
        author_text = re.sub(r"\\(?:AND|And|and)\b", "|||", author_text)
        author_text = re.sub(r"\\\\", "|||", author_text)
        for part in author_text.split("|||"):
            part = re.sub(r"\S+@\S+", "", part)
            part = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", part)
            part = clean_latex_text(part)
            part = part.strip(" ,.;")
            if part and len(part) > 2 and part not in authors:
                authors.append(part)
    return title, authors[:20]


def extract_abstract(content: str) -> str:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.S)
    return clean_latex_text(match.group(1)) if match else ""


def document_body(content: str) -> str:
    match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", content, re.S)
    return match.group(1) if match else content


def extract_sections(content: str) -> list[dict[str, str]]:
    body = document_body(content)
    body = FIGURE_ENV_RE.sub("\n[figure omitted here; see figure inventory]\n", body)
    body = TABLE_ENV_RE.sub("\n[table omitted here; see table inventory]\n", body)
    body = re.sub(r"\\maketitle", "", body)
    body = re.sub(r"\\begin\{abstract\}.*?\\end\{abstract\}", "", body, flags=re.S)
    pattern = re.compile(r"\\(section|subsection|subsubsection)\*?\{((?:[^{}]|\{[^{}]*\})*)\}", re.S)
    matches = list(pattern.finditer(body))
    sections: list[dict[str, str]] = []
    if not matches:
        text = clean_latex_text(body)
        if text:
            sections.append({"level": "section", "title": "Paper Text", "text": text})
        return sections
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        title = clean_latex_text(match.group(2))
        text = clean_latex_text(body[start:end])
        if title or text:
            sections.append({"level": match.group(1), "title": title, "text": text})
    return sections


def media_inventory(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS)


def normalized_stem(path_or_ref: str | Path) -> str:
    path = Path(str(path_or_ref))
    return re.sub(r"[^a-z0-9]+", "", path.stem.lower())


def resolve_media_ref(ref: str, source_dir: Path, media_files: list[Path]) -> Path | None:
    ref = ref.strip()
    if not ref:
        return None
    direct = source_dir / ref
    if direct.exists():
        return direct
    ref_path = Path(ref)
    for ext in MEDIA_EXTENSIONS:
        candidate = source_dir / (str(ref_path) + ext)
        if candidate.exists():
            return candidate
        candidate = source_dir / ref_path.with_suffix(ext)
        if candidate.exists():
            return candidate
    ref_stem = normalized_stem(ref)
    for media in media_files:
        if normalized_stem(media) == ref_stem:
            return media
    return None


def copy_media(path: Path, output_dir: Path, arxiv_id: str, idx: int, caption: str) -> tuple[str, list[str], bool]:
    warnings: list[str] = []
    if path.stat().st_size > MAX_COPIED_MEDIA_BYTES:
        warnings.append(f"figure {idx} skipped because source asset exceeds 20MB: {path.name}")
        return "", warnings, True
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower() or ".bin"
    caption_slug = slugify(caption, fallback="figure")[:36]
    target = images_dir / f"paper-{safe_arxiv_id(arxiv_id)}-fig-{idx:02d}-{caption_slug}-{hash_text(str(path), 6)}{suffix}"
    shutil.copy2(path, target)
    return str(target.relative_to(output_dir)), warnings, False


def extract_figures(content: str, source_dir: Path, output_dir: Path, arxiv_id: str) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    warnings: list[str] = []
    missing_evidence: list[str] = []
    media_files = media_inventory(source_dir)
    figures: list[dict[str, Any]] = []
    for idx, match in enumerate(FIGURE_ENV_RE.finditer(content), start=1):
        env = match.group(1)
        caption = clean_latex_text(command_argument(env, "caption"))
        refs = [ref.strip() for ref in INCLUDE_GRAPHICS_RE.findall(env) if ref.strip()]
        copied: list[dict[str, str]] = []
        unresolved: list[str] = []
        for ref in refs:
            media = resolve_media_ref(ref, source_dir, media_files)
            if not media:
                unresolved.append(ref)
                continue
            rel_path, copy_warnings, skipped = copy_media(media, output_dir, arxiv_id, idx, caption)
            warnings.extend(copy_warnings)
            if rel_path:
                copied.append({"path": rel_path, "source_ref": ref, "source_path": str(media.relative_to(source_dir))})
            if skipped:
                unresolved.append(ref)
        if refs and not copied:
            missing_evidence.append(f"figure_{idx}_asset_not_copied")
        if unresolved:
            warnings.append(f"figure {idx} unresolved media refs: {', '.join(unresolved[:4])}")
        figures.append(
            {
                "index": idx,
                "caption": caption,
                "tex_refs": refs,
                "assets": copied,
                "unresolved_refs": unresolved,
            }
        )
    return figures, warnings, missing_evidence


def extract_table_rows(tabular: str) -> str:
    rows: list[list[str]] = []
    for raw in tabular.splitlines():
        line = raw.strip()
        if not line or line.startswith("%") or re.match(r"^\\(?:hline|toprule|midrule|bottomrule|cline)", line):
            continue
        if "&" not in line:
            continue
        cells = [clean_latex_text(re.sub(r"\\\\.*$", "", cell)) for cell in re.split(r"(?<!\\)&", line)]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    for row in rows:
        row.extend([""] * (width - len(row)))
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join(["---"] * width) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def extract_tables(content: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for idx, match in enumerate(TABLE_ENV_RE.finditer(content), start=1):
        env = match.group(1)
        caption = clean_latex_text(command_argument(env, "caption"))
        tabular_match = re.search(r"\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}", env, re.S)
        table_markdown = extract_table_rows(tabular_match.group(0)) if tabular_match else ""
        tables.append({"index": idx, "caption": caption, "markdown": table_markdown})
    return tables


def render_paper_markdown(
    title: str,
    authors: list[str],
    arxiv_id: str,
    abstract: str,
    sections: list[dict[str, str]],
    figures: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    parts = [
        f"# {title or 'Untitled arXiv Paper'}",
        "",
        f"**arXiv**: https://arxiv.org/abs/{arxiv_id}",
    ]
    if metadata.get("published_date"):
        parts.append(f"**Published**: {metadata['published_date']}")
    if authors:
        parts.append(f"**Authors**: {', '.join(authors[:12])}")
    if abstract:
        parts.extend(["", "## Abstract", "", abstract])
    if figures:
        parts.extend(["", "## Figure Inventory", ""])
        for fig in figures:
            asset_text = ", ".join(asset["path"] for asset in fig.get("assets", [])) or "asset not copied"
            caption = fig.get("caption") or "(no caption)"
            parts.append(f"- **Figure {fig['index']}**: {caption}  \n  Asset: `{asset_text}`")
    if tables:
        parts.extend(["", "## Table Inventory", ""])
        for table in tables:
            caption = table.get("caption") or "(no caption)"
            parts.append(f"### Table {table['index']}: {caption}")
            if table.get("markdown"):
                parts.append(table["markdown"])
            else:
                parts.append("(table structure not extracted)")
            parts.append("")
    if sections:
        parts.extend(["", "## Extracted Text", ""])
        level_map = {"section": "###", "subsection": "####", "subsubsection": "#####"}
        for section in sections:
            title_part = section.get("title") or "Untitled Section"
            parts.append(f"{level_map.get(section.get('level', 'section'), '###')} {title_part}")
            if section.get("text"):
                parts.append(section["text"])
            parts.append("")
    return cleanup_markdown("\n".join(parts))


def card_text(value: str, limit: int = 900) -> str:
    value = cleanup_markdown(value)
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0] + "..."


def build_source_cards(
    arxiv_id: str,
    title: str,
    abstract: str,
    sections: list[dict[str, str]],
    figures: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    safe_id = safe_arxiv_id(arxiv_id)
    source_id = f"paper:{arxiv_id}"
    cards: list[dict[str, Any]] = []
    if abstract:
        cards.append(
            {
                "id": f"{safe_id}-abstract",
                "claim": f"{title or arxiv_id} 的摘要说明研究问题、方法和主要结论。",
                "source_ids": [source_id],
                "evidence": card_text(abstract),
                "usable_as": ["opening_context", "problem_setup", "paper_summary"],
                "confidence": "high",
                "source_anchor": f"arXiv:{arxiv_id}:abstract",
            }
        )
    for idx, section in enumerate(sections[:16], start=1):
        if not section.get("text"):
            continue
        cards.append(
            {
                "id": f"{safe_id}-sec-{idx:02d}",
                "claim": section.get("title") or f"Section {idx}",
                "source_ids": [source_id],
                "evidence": card_text(section["text"]),
                "usable_as": ["method_explanation", "evidence_slide", "speaker_notes"],
                "confidence": "medium",
                "source_anchor": f"arXiv:{arxiv_id}:section:{idx}",
            }
        )
    for fig in figures:
        cards.append(
            {
                "id": f"{safe_id}-fig-{fig['index']:02d}",
                "claim": f"Figure {fig['index']}: {fig.get('caption') or 'paper figure'}",
                "source_ids": [source_id],
                "evidence": card_text(fig.get("caption") or ""),
                "usable_as": ["visual_evidence", "diagram_slide", "method_explanation"],
                "confidence": "high" if fig.get("assets") else "medium",
                "source_anchor": f"arXiv:{arxiv_id}:figure:{fig['index']}",
                "asset_paths": [asset["path"] for asset in fig.get("assets", [])],
            }
        )
    for table in tables:
        cards.append(
            {
                "id": f"{safe_id}-table-{table['index']:02d}",
                "claim": f"Table {table['index']}: {table.get('caption') or 'paper table'}",
                "source_ids": [source_id],
                "evidence": card_text((table.get("caption") or "") + "\n\n" + (table.get("markdown") or "")),
                "usable_as": ["benchmark_slide", "comparison_table", "speaker_notes"],
                "confidence": "high" if table.get("markdown") else "medium",
                "source_anchor": f"arXiv:{arxiv_id}:table:{table['index']}",
            }
        )
    return cards


def update_source_cards(output_dir: Path, cards: list[dict[str, Any]]) -> Path:
    path = output_dir / "source_cards.json"
    existing_cards: list[dict[str, Any]] = []
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                existing_cards = [item for item in raw if isinstance(item, dict)]
            elif isinstance(raw, dict) and isinstance(raw.get("cards"), list):
                existing_cards = [item for item in raw["cards"] if isinstance(item, dict)]
        except Exception:
            existing_cards = []
    new_ids = {card.get("id") for card in cards}
    merged = [card for card in existing_cards if card.get("id") not in new_ids]
    merged.extend(cards)
    path.write_text(
        json.dumps({"schema_version": "1.0.0", "updated_at": now_iso(), "cards": merged}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return path


def ingest_pdf_fallback(
    input_value: str,
    output_dir: Path,
    paper_dir: Path,
    arxiv_id: str,
    source_type: str,
    metadata: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    pdf_path = paper_dir / "paper.pdf"
    result = fetch_url(pdf_url, timeout=60)
    warnings.extend(result.warnings)
    missing_evidence: list[str] = ["tex_source_unavailable"]
    markdown = ""
    extractor = "none"
    if result.data:
        pdf_path.write_bytes(result.data)
        markdown, pdf_warnings, extractor = extract_pdf_text(pdf_path)
        warnings.extend(pdf_warnings)
    else:
        warnings.append("arxiv PDF fallback returned no data")
    if not markdown:
        missing_evidence.append("pdf_text_extraction_failed")

    title = metadata.get("title") or f"arXiv {arxiv_id}"
    markdown_path = output_dir / "extracted" / f"paper-{safe_arxiv_id(arxiv_id)}.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(markdown_path, title, input_value, source_type, f"arxiv_pdf_fallback:{extractor}", markdown)
    cards = build_source_cards(arxiv_id, title, metadata.get("abstract", ""), [], [], [])
    cards_path = update_source_cards(output_dir, cards) if cards else output_dir / "source_cards.json"
    paper_manifest = {
        "schema_version": "1.0.0",
        "input": input_value,
        "source_type": source_type,
        "arxiv_id": arxiv_id,
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
        "title": title,
        "authors": metadata.get("authors", []),
        "abstract": metadata.get("abstract", ""),
        "published_date": metadata.get("published_date", ""),
        "fetch_route": f"arxiv_pdf_fallback:{extractor}",
        "has_tex_source": False,
        "markdown_path": str(markdown_path.relative_to(output_dir)),
        "pdf_path": str(pdf_path.relative_to(output_dir)) if pdf_path.exists() else "",
        "figures": [],
        "tables": [],
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "source_cards_path": str(cards_path.relative_to(output_dir)) if cards_path.exists() else "",
    }
    manifest_path = paper_dir / "paper_manifest.json"
    manifest_path.write_text(json.dumps(paper_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record = {
        "input": input_value,
        "title": title,
        "source_type": source_type,
        "fetch_route": f"arxiv_pdf_fallback:{extractor}",
        "fetched_at": now_iso(),
        "markdown_path": str(markdown_path.relative_to(output_dir)),
        "paper_manifest_path": str(manifest_path.relative_to(output_dir)),
        "source_cards_path": str(cards_path.relative_to(output_dir)) if cards_path.exists() else "",
        "pdf_path": str(pdf_path.relative_to(output_dir)) if pdf_path.exists() else "",
        "images": [],
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "text_chars": len(markdown),
        "arxiv_id": arxiv_id,
    }
    source_manifest = update_manifest(output_dir, record)
    record["manifest_path"] = str(source_manifest)
    record["markdown_abs_path"] = str(markdown_path)
    return record


def ingest_paper(input_value: str, output_dir: Path, pdf_fallback: bool = True) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    arxiv_id, source_type, warnings = normalize_arxiv_input(input_value)
    safe_id = safe_arxiv_id(arxiv_id)
    paper_dir = output_dir / "papers" / safe_id
    source_dir = paper_dir / "tex_source"
    if paper_dir.exists():
        shutil.rmtree(paper_dir)
    paper_dir.mkdir(parents=True, exist_ok=True)

    metadata, meta_warnings = fetch_arxiv_metadata(arxiv_id)
    warnings.extend(meta_warnings)
    has_tex, tex_warnings, raw_archive_path = download_and_extract_tex(arxiv_id, source_dir)
    warnings.extend(tex_warnings)
    if not has_tex:
        if pdf_fallback:
            return ingest_pdf_fallback(input_value, output_dir, paper_dir, arxiv_id, source_type, metadata, warnings)
        raise RuntimeError("TeX source unavailable and PDF fallback disabled")

    missing_evidence: list[str] = []
    main_tex = find_main_tex(source_dir)
    if not main_tex:
        missing_evidence.append("main_tex_not_found")
        if pdf_fallback:
            warnings.append("main .tex not found; switching to PDF fallback")
            return ingest_pdf_fallback(input_value, output_dir, paper_dir, arxiv_id, source_type, metadata, warnings)
        raise RuntimeError("No main .tex file found in arXiv source")

    content = main_tex.read_text(encoding="utf-8", errors="replace")
    content = strip_latex_comments(content)
    content = resolve_inputs(content, main_tex.parent)
    title, authors = extract_title_author(content)
    abstract = extract_abstract(content)
    title = title or metadata.get("title") or f"arXiv {arxiv_id}"
    authors = authors or metadata.get("authors", [])
    abstract = abstract or metadata.get("abstract", "")
    sections = extract_sections(content)
    figures, figure_warnings, figure_missing = extract_figures(content, source_dir, output_dir, arxiv_id)
    warnings.extend(figure_warnings)
    missing_evidence.extend(figure_missing)
    tables = extract_tables(content)

    markdown = render_paper_markdown(title, authors, arxiv_id, abstract, sections, figures, tables, metadata)
    markdown_path = output_dir / "extracted" / f"paper-{safe_id}-{slugify(title, 'paper')[:48]}.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(markdown_path, title, input_value, source_type, "arxiv_eprint_tex", markdown)

    cards = build_source_cards(arxiv_id, title, abstract, sections, figures, tables)
    cards_path = update_source_cards(output_dir, cards)

    paper_manifest = {
        "schema_version": "1.0.0",
        "input": input_value,
        "source_type": source_type,
        "arxiv_id": arxiv_id,
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published_date": metadata.get("published_date", ""),
        "updated_date": metadata.get("updated_date", ""),
        "fetch_route": "arxiv_eprint_tex",
        "has_tex_source": True,
        "main_tex": str(main_tex.relative_to(source_dir)),
        "raw_archive_path": str(Path(raw_archive_path).relative_to(output_dir)) if raw_archive_path else "",
        "tex_source_dir": str(source_dir.relative_to(output_dir)),
        "markdown_path": str(markdown_path.relative_to(output_dir)),
        "source_cards_path": str(cards_path.relative_to(output_dir)),
        "figures": figures,
        "tables": tables,
        "warnings": warnings,
        "missing_evidence": missing_evidence,
    }
    manifest_path = paper_dir / "paper_manifest.json"
    manifest_path.write_text(json.dumps(paper_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    images = []
    for figure in figures:
        for asset in figure.get("assets", []):
            images.append(
                {
                    "path": asset["path"],
                    "alt": figure.get("caption", ""),
                    "role": "paper_figure",
                    "figure_index": figure["index"],
                }
            )

    record = {
        "input": input_value,
        "title": title,
        "source_type": source_type,
        "fetch_route": "arxiv_eprint_tex",
        "fetched_at": now_iso(),
        "markdown_path": str(markdown_path.relative_to(output_dir)),
        "paper_manifest_path": str(manifest_path.relative_to(output_dir)),
        "source_cards_path": str(cards_path.relative_to(output_dir)),
        "tex_source_dir": str(source_dir.relative_to(output_dir)),
        "images": images,
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "text_chars": len(markdown),
        "arxiv_id": arxiv_id,
        "figure_count": len(figures),
        "table_count": len(tables),
    }
    source_manifest = update_manifest(output_dir, record)
    record["manifest_path"] = str(source_manifest)
    record["markdown_abs_path"] = str(markdown_path)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an arXiv or Hugging Face paper into qiaomu-ppt sources.")
    parser.add_argument("input", help="arXiv URL/ID or Hugging Face papers URL.")
    parser.add_argument("--output-dir", "-o", default="sources", help="Output source directory.")
    parser.add_argument("--no-pdf-fallback", action="store_true", help="Fail instead of using arXiv PDF when TeX is unavailable.")
    args = parser.parse_args()

    try:
        record = ingest_paper(args.input, Path(args.output_dir), pdf_fallback=not args.no_pdf_fallback)
    except Exception as exc:
        print(f"qiaomu-ppt paper ingestion failed: {exc}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if record.get("missing_evidence"):
        print("Warning: paper ingestion completed with missing evidence; inspect paper_manifest.json before slide planning.", file=sys.stderr)


if __name__ == "__main__":
    main()
