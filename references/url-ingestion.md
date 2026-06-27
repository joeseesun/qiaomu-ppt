# URL Ingestion

Use this when the user says something like:

- `做一个PPT：https://example.com/article`
- `根据这个链接做 PPT`
- `把这篇文章/报告/PDF 生成幻灯片`
- `读这个网页里的图片和内容做 deck`

The workflow uses a built-in proxy cascade inspired by prior Markdown proxy
work, but this skill is self-contained and does not depend on any external
Markdown-proxy skill at runtime.

For mixed source packets, Feishu exports, EPUB books, Office files, folders, ZIP
archives, or image/OCR sources, use [source-intake-method.md](source-intake-method.md)
and `scripts/source_to_markdown.py` instead. This file documents the lightweight
URL/PDF path.

## Route

1. Detect URLs before planning.
2. Run:

```bash
python3 <skill>/scripts/url_to_markdown.py "<url>" --output-dir <project>/sources --download-images
```

3. Read the generated Markdown and `source_manifest.json`.
4. Use extracted images as candidate evidence objects; do not use them as decoration unless they support the slide claim.
5. Continue with `content_contract.json`, `visual_contract.json`, and normal deck production.

## Supported Inputs

| Input | Built-In Handling | Notes |
|---|---|---|
| ordinary article URL | direct fetch, metadata extraction, Markdown conversion, image discovery | falls back to Jina Reader when direct fetch is weak |
| X/Twitter status, X Article, `t.co` | proxy-first cascade inside `url_to_markdown.py`: Jina Reader, defuddle, then `npx agent-fetch` when available | filters X JavaScript/login/error pages; records `proxy_cascade_failed` instead of pretending content was fetched |
| image-rich page | downloads candidate images with source metadata | every image still needs an image slot before deck use |
| remote PDF | downloads and extracts text with `pdftotext` or `pypdf` when available | keep PDF path in manifest |
| local PDF | extract text with `pdftotext` or `pypdf` | path is recorded |
| WeChat / login pages | try general route, then mark missing evidence if blocked | do not pretend login-only content was fetched |
| Feishu/Lark docs | use `source_to_markdown.py` with exported files, or an authenticated connector route | do not pretend private docs were fetched from a bare link |

## Source Manifest

Each URL run should create:

```text
sources/
  <slug>.md
  source_manifest.json
  images/
```

`source_manifest.json` should include:

- original URL
- title
- fetch route
- fetched time
- Markdown path
- image paths and original image URLs
- warnings and missing evidence

## Slide Rules

- Do not put raw provenance footers on every slide.
- Use source evidence in notes, `qa_report.md`, or final reference pages.
- If the URL has many images, select by relevance to slide claims, not by visual attractiveness.
- When facts are current, high-stakes, or commercially sensitive, verify from the original source or mark `missing evidence`.
