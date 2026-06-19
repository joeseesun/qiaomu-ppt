#!/usr/bin/env python3
"""Fetch a URL or PDF into Markdown sources for qiaomu-ppt projects.

This script intentionally keeps the URL-to-PPT entry self-contained. It can use
optional packages listed in requirements.txt, but it does not require the
qiaomu-markdown-proxy skill at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
    "qiaomu-ppt-url-ingester/0.5"
)
MIN_USEFUL_MARKDOWN_CHARS = 420
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@dataclass
class FetchResult:
    url: str
    data: bytes
    status: int | None = None
    content_type: str = ""
    final_url: str = ""
    warnings: list[str] = field(default_factory=list)


def optional_import(name: str) -> Any | None:
    try:
        return __import__(name)
    except Exception:
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def slugify(value: str, fallback: str = "source") -> str:
    value = unescape(value or "").strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:80] or fallback


def hash_text(value: str, length: int = 8) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:length]


def fetch_url(url: str, timeout: int = 30) -> FetchResult:
    warnings: list[str] = []
    requests = optional_import("requests")
    if requests is not None:
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            content_type = response.headers.get("content-type", "")
            return FetchResult(
                url=url,
                data=response.content,
                status=response.status_code,
                content_type=content_type,
                final_url=response.url,
                warnings=warnings,
            )
        except Exception as exc:
            warnings.append(f"requests fetch failed: {exc}")

    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            content_type = response.headers.get("content-type", "")
            status = getattr(response, "status", None)
            final_url = response.geturl()
            return FetchResult(
                url=url,
                data=data,
                status=status,
                content_type=content_type,
                final_url=final_url,
                warnings=warnings,
            )
    except Exception as exc:
        warnings.append(f"urllib fetch failed: {exc}")
        return FetchResult(url=url, data=b"", warnings=warnings)


def jina_reader_url(url: str) -> str:
    return f"https://r.jina.ai/{url}"


def extract_title_from_html(html: str) -> str:
    soup_mod = optional_import("bs4")
    if soup_mod is not None:
        try:
            soup = soup_mod.BeautifulSoup(html, "lxml")
            for selector in (
                'meta[property="og:title"]',
                'meta[name="twitter:title"]',
                "title",
                "h1",
            ):
                element = soup.select_one(selector)
                if not element:
                    continue
                value = element.get("content") if element.name == "meta" else element.get_text(" ", strip=True)
                if value:
                    return re.sub(r"\s+", " ", value).strip()
        except Exception:
            pass
    for pattern in (r"<title[^>]*>(.*?)</title>", r"<h1[^>]*>(.*?)</h1>"):
        match = re.search(pattern, html, flags=re.I | re.S)
        if match:
            title = re.sub(r"<[^>]+>", " ", match.group(1))
            title = re.sub(r"\s+", " ", unescape(title)).strip()
            if title:
                return title
    return ""


def discover_images(html: str, base_url: str) -> list[dict[str, str]]:
    soup_mod = optional_import("bs4")
    images: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_image(raw_url: str, alt: str = "") -> None:
        if not raw_url or raw_url.startswith("data:"):
            return
        raw_url = raw_url.split()[0].strip()
        absolute = urljoin(base_url, raw_url)
        if absolute in seen:
            return
        seen.add(absolute)
        images.append({"url": absolute, "alt": alt.strip()})

    if soup_mod is not None:
        try:
            soup = soup_mod.BeautifulSoup(html, "lxml")
            for selector in ('meta[property="og:image"]', 'meta[name="twitter:image"]'):
                element = soup.select_one(selector)
                if element and element.get("content"):
                    add_image(element.get("content", ""), "social preview image")
            for img in soup.find_all("img"):
                src = img.get("data-src") or img.get("src") or ""
                if not src and img.get("srcset"):
                    src = img.get("srcset", "").split(",")[0].strip().split()[0]
                add_image(src, img.get("alt", ""))
            return images
        except Exception:
            pass

    for match in re.finditer(r"<img\b[^>]*?\bsrc=['\"]([^'\"]+)['\"][^>]*>", html, flags=re.I | re.S):
        add_image(match.group(1), "")
    for match in re.finditer(r"<meta\b[^>]*(?:property|name)=['\"](?:og:image|twitter:image)['\"][^>]*content=['\"]([^'\"]+)['\"]", html, flags=re.I | re.S):
        add_image(match.group(1), "social preview image")
    return images


def discover_markdown_images(markdown: str, base_url: str) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", markdown):
        alt = match.group(1).strip()
        raw_url = match.group(2).strip()
        if not raw_url or raw_url.startswith("data:"):
            continue
        absolute = urljoin(base_url, raw_url)
        if absolute in seen:
            continue
        seen.add(absolute)
        images.append({"url": absolute, "alt": alt})
    return images


def merge_images(primary: list[dict[str, str]], secondary: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in primary + secondary:
        url = item.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append(item)
    return merged


def extract_title_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines()[:40]:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("title:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def html_to_markdown(html: str, base_url: str) -> str:
    markdownify_mod = optional_import("markdownify")
    soup_mod = optional_import("bs4")
    if soup_mod is not None:
        try:
            soup = soup_mod.BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
                tag.decompose()
            root = soup.find("article") or soup.find("main") or soup.body or soup
            if markdownify_mod is not None:
                text = markdownify_mod.markdownify(str(root), heading_style="ATX", bullets="-")
            else:
                text = root.get_text("\n", strip=True)
            text = normalize_markdown_links(text, base_url)
            return cleanup_markdown(text)
        except Exception:
            pass

    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.I | re.S)
    body = body_match.group(1) if body_match else html
    body = re.sub(r"<(script|style|noscript|iframe)\b.*?</\1>", "\n", body, flags=re.I | re.S)
    body = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: "\n" + "#" * int(m.group(1)) + " " + strip_tags(m.group(2)) + "\n", body, flags=re.I | re.S)
    body = re.sub(r"<p[^>]*>", "\n", body, flags=re.I)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = strip_tags(body)
    return cleanup_markdown(unescape(body))


def normalize_markdown_links(text: str, base_url: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label, link = match.group(1), match.group(2)
        if link.startswith(("#", "mailto:", "tel:", "data:")):
            return match.group(0)
        return f"[{label}]({urljoin(base_url, link)})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, text)


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def cleanup_markdown(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{4,}", "\n\n\n", value)
    value = "\n".join(line.rstrip() for line in value.splitlines())
    return value.strip()


def looks_like_pdf(input_value: str, result: FetchResult | None = None) -> bool:
    if input_value.lower().split("?")[0].endswith(".pdf"):
        return True
    if result and ("application/pdf" in result.content_type.lower() or result.data[:4] == b"%PDF"):
        return True
    return False


def extract_pdf_text(pdf_path: Path) -> tuple[str, list[str], str]:
    warnings: list[str] = []
    pdftotext = subprocess.run(
        ["which", "pdftotext"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if pdftotext.returncode == 0:
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return cleanup_markdown(proc.stdout), warnings, "pdftotext"
            warnings.append(f"pdftotext produced no text: {proc.stderr.strip()[:200]}")
        except Exception as exc:
            warnings.append(f"pdftotext failed: {exc}")

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        pages: list[str] = []
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"## Page {idx}\n\n{text.strip()}")
        if pages:
            return cleanup_markdown("\n\n".join(pages)), warnings, "pypdf"
        warnings.append("pypdf produced no text")
    except Exception as exc:
        warnings.append(f"pypdf unavailable or failed: {exc}")

    return "", warnings, "none"


def write_markdown(path: Path, title: str, input_value: str, source_type: str, fetch_route: str, body: str) -> None:
    frontmatter = {
        "title": title or Path(path).stem,
        "source": input_value,
        "source_type": source_type,
        "fetch_route": fetch_route,
        "fetched_at": now_iso(),
    }
    yaml = ["---"] + [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in frontmatter.items()] + ["---", ""]
    path.write_text("\n".join(yaml) + cleanup_markdown(body) + "\n", encoding="utf-8")


def safe_extension(url: str, content_type: str) -> str:
    parsed_ext = Path(urlparse(url).path).suffix.lower()
    if parsed_ext in IMAGE_EXTENSIONS:
        return parsed_ext
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip()) if content_type else ""
    if guessed in IMAGE_EXTENSIONS:
        return guessed
    return ".jpg"


def download_images(candidates: list[dict[str, str]], images_dir: Path, max_images: int) -> list[dict[str, str]]:
    images_dir.mkdir(parents=True, exist_ok=True)
    saved: list[dict[str, str]] = []
    for idx, item in enumerate(candidates[:max_images], start=1):
        url = item["url"]
        result = fetch_url(url, timeout=20)
        if not result.data or (result.status and result.status >= 400):
            saved.append({"url": url, "alt": item.get("alt", ""), "warning": "download_failed"})
            continue
        content_type = result.content_type or ""
        if content_type and "image" not in content_type.lower() and not Path(urlparse(url).path).suffix.lower() in IMAGE_EXTENSIONS:
            saved.append({"url": url, "alt": item.get("alt", ""), "warning": f"not_image_content_type:{content_type}"})
            continue
        ext = safe_extension(url, content_type)
        name = f"image-{idx:02d}-{hash_text(url, 10)}{ext}"
        path = images_dir / name
        path.write_bytes(result.data)
        saved.append(
            {
                "url": url,
                "alt": item.get("alt", ""),
                "path": str(path.relative_to(images_dir.parent)),
                "bytes": path.stat().st_size,
                "content_type": content_type,
            }
        )
    return saved


def update_manifest(output_dir: Path, record: dict[str, Any]) -> Path:
    manifest_path = output_dir / "source_manifest.json"
    manifest: dict[str, Any] = {"schema_version": "1.0.0", "sources": []}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                manifest.update(existing)
        except Exception:
            pass
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        sources = []
    sources = [item for item in sources if isinstance(item, dict) and item.get("input") != record.get("input")]
    sources.append(record)
    manifest["sources"] = sources
    manifest["latest"] = record
    manifest["updated_at"] = now_iso()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def ingest(input_value: str, output_dir: Path, download_image_files: bool, max_images: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    missing_evidence: list[str] = []
    source_type = "url" if is_url(input_value) else "file"
    slug_basis = input_value
    title = ""
    fetch_route = ""
    markdown = ""
    images: list[dict[str, str]] = []
    saved_pdf_path = ""

    if not is_url(input_value):
        path = Path(input_value).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"input file does not exist: {path}")
        slug_basis = path.stem
        if path.suffix.lower() == ".pdf":
            source_type = "local_pdf"
            fetch_route = "local_pdf"
            markdown, pdf_warnings, extractor = extract_pdf_text(path)
            warnings.extend(pdf_warnings)
            if not markdown:
                missing_evidence.append("pdf_text_extraction_failed")
            title = path.stem
            saved_pdf_path = str(path)
        else:
            source_type = "local_file"
            fetch_route = "local_file"
            markdown = path.read_text(encoding="utf-8", errors="replace")
            title = path.stem
    else:
        result = fetch_url(input_value)
        warnings.extend(result.warnings)
        if result.status and result.status >= 400:
            warnings.append(f"direct fetch returned HTTP {result.status}")

        if looks_like_pdf(input_value, result):
            source_type = "remote_pdf"
            fetch_route = "remote_pdf"
            pdf_name = f"{slugify(Path(urlparse(input_value).path).stem or 'remote-pdf')}-{hash_text(input_value)}.pdf"
            pdf_path = output_dir / pdf_name
            pdf_path.write_bytes(result.data)
            saved_pdf_path = str(pdf_path.relative_to(output_dir))
            markdown, pdf_warnings, extractor = extract_pdf_text(pdf_path)
            warnings.extend(pdf_warnings)
            if not markdown:
                missing_evidence.append("pdf_text_extraction_failed")
            title = Path(urlparse(input_value).path).stem or "Remote PDF"
            fetch_route = f"remote_pdf:{extractor}"
        else:
            html = result.data.decode("utf-8", errors="replace") if result.data else ""
            title = extract_title_from_html(html) or urlparse(input_value).netloc
            markdown = html_to_markdown(html, result.final_url or input_value)
            fetch_route = "direct_html"
            image_candidates = discover_images(html, result.final_url or input_value)

            if len(markdown) < MIN_USEFUL_MARKDOWN_CHARS:
                jina = fetch_url(jina_reader_url(input_value), timeout=35)
                warnings.extend([f"jina fallback: {item}" for item in jina.warnings])
                jina_text = jina.data.decode("utf-8", errors="replace") if jina.data else ""
                if len(cleanup_markdown(jina_text)) > len(markdown):
                    markdown = cleanup_markdown(jina_text)
                    fetch_route = "jina_reader"
                    title = extract_title_from_markdown(markdown) or title
                    if not title:
                        title = urlparse(input_value).netloc
                else:
                    warnings.append("jina_reader did not improve extracted text")

            image_candidates = merge_images(
                image_candidates,
                discover_markdown_images(markdown, result.final_url or input_value),
            )
            if download_image_files and image_candidates:
                images = download_images(image_candidates, output_dir / "images", max_images)
            elif image_candidates:
                images = [{"url": item["url"], "alt": item.get("alt", "")} for item in image_candidates[:max_images]]

            if len(markdown) < MIN_USEFUL_MARKDOWN_CHARS:
                missing_evidence.append("weak_text_extraction")

    slug = slugify(title or slug_basis, fallback=f"source-{hash_text(input_value)}")
    markdown_path = output_dir / f"{slug}.md"
    if markdown_path.exists():
        markdown_path = output_dir / f"{slug}-{hash_text(input_value)}.md"
    write_markdown(markdown_path, title, input_value, source_type, fetch_route, markdown or "(No useful text extracted.)")

    record: dict[str, Any] = {
        "input": input_value,
        "title": title,
        "source_type": source_type,
        "fetch_route": fetch_route,
        "fetched_at": now_iso(),
        "markdown_path": str(markdown_path.relative_to(output_dir)),
        "pdf_path": saved_pdf_path,
        "images": images,
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "text_chars": len(markdown),
    }
    manifest_path = update_manifest(output_dir, record)
    record["manifest_path"] = str(manifest_path)
    record["markdown_abs_path"] = str(markdown_path)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a URL, PDF, or local text/PDF into qiaomu-ppt Markdown source artifacts."
    )
    parser.add_argument("input", help="URL, local PDF path, or local text/Markdown path.")
    parser.add_argument("--output-dir", "-o", default="sources", help="Directory for Markdown, manifest, and images.")
    parser.add_argument("--download-images", action="store_true", help="Download discovered page images into sources/images.")
    parser.add_argument("--max-images", type=int, default=12, help="Maximum discovered images to record or download.")
    args = parser.parse_args()

    try:
        record = ingest(args.input, Path(args.output_dir), args.download_images, args.max_images)
    except Exception as exc:
        print(f"qiaomu-ppt URL ingestion failed: {exc}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(record, ensure_ascii=False, indent=2))
    if record["missing_evidence"]:
        print(
            textwrap.fill(
                "Warning: extraction completed with missing evidence. Use the manifest to decide whether to verify manually before writing slide claims.",
                width=88,
            ),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
