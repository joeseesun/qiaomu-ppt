# Source Intake Method

`qiaomu-ppt` should treat information gathering as a first-class production
stage. URL ingestion is only one route. Feishu documents, EPUB books, PDFs,
Office files, videos, podcasts, screenshots, folders, and mixed source packets
all need to become usable evidence before the deck can have a soul.

This method is inspired by the local `qiaomu-anything-to-notebooklm` workflow,
especially its broad source detection and deep-analysis discipline. Qiaomu PPT
does not depend on that skill at runtime; it internalizes the useful source
intake model as Qiaomu-owned rules, scripts, and contracts.

## Source Ladder

Classify every input before writing a slide:

| Input | Intake Route | PPT Use |
|---|---|---|
| public URL | `url_to_markdown.py` or `source_to_markdown.py` | article claims, images, source cards |
| arXiv / Hugging Face paper URL | `paper_to_markdown.py` via arXiv e-print TeX, PDF fallback | paper figures, tables, method diagrams, benchmark evidence |
| WeChat public-account URL | `source_to_markdown.py` baseline plus specialized open-source WeChat extractor when needed | article claims, account metadata, downloaded article images |
| local PDF / remote PDF | text extraction via Poppler or `pypdf`; OCR if scanned | report evidence, tables, quote cards |
| EPUB | unzip OPF/spine/html and extract chapters plus packaged images | book thesis, chapter cards, quote bank, book figures |
| Markdown/TXT | direct import | notes, draft outline, source cards |
| DOCX/PPTX/XLSX | `markitdown` when available; XML fallback for text; copy `word/media`, `ppt/media`, and `xl/media` images | internal docs, old decks, screenshots, tables, embedded figures |
| ZIP/folder | recurse and ingest supported files | source packet, course pack, research folder |
| image/scanned PDF | OCR route when available; otherwise mark missing evidence | captions, screenshots, scan quotes |
| audio/video/podcast | transcript route or NotebookLM/Get笔记 when available | time-stamped claims, quote clips |
| YouTube | NotebookLM can accept URL directly when NotebookLM route is chosen | transcript-backed cards |
| Feishu/Lark doc | export, API/credential route, or user-provided Markdown/PDF/DOCX | private docs, comments, highlights |
| search keywords | web search summary with manifest | topic research seed, not final authority |

For paper sources, follow
[paper-source-intake.md](paper-source-intake.md): Hugging Face Papers links are
normalized to arXiv IDs, TeX is preferred over PDF, and extracted figures/tables
become proof objects. For WeChat public-account links, follow
[wechat-source-intake.md](wechat-source-intake.md): generic extraction is only a
baseline; specialized extractors are needed when images, lazy content, or
hotlink-protected assets matter.

The output target is the same regardless of source type:

```text
sources/
  source_manifest.json
  source_notes.md
  source_cards.json
  images/
  extracted/
```

`scripts/source_to_markdown.py` should generate `source_notes.md` and
`source_cards.json` by default after updating `source_manifest.json`. The cards
are a first-pass evidence index, not the final slide outline. Use
`scripts/source_cards.py` directly when a lightweight URL route or manually
prepared source folder needs cards:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/source_cards.py <project>/sources
```

Before writing `content_contract.json`, refine or merge these deterministic
cards into the deck's actual angle, source anchors, and visual proof objects.
For a deterministic first pass, use:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/outline_from_source_cards.py <project>
```

This creates `content_contract.json` and `slide_plan_seed.json` from
`source_cards.json`. Treat the result as an outline seed that still needs human
or agent editorial judgment before rendering.

For ordinary "topic/file/link to PPT" requests, prefer the higher-level
project-prep entrypoint:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/prepare_deck_project.py \
  --topic "<topic or title>" \
  --project <project> \
  --slides 10 \
  <inputs...>
```

With inputs, this runs source intake, source cards, outline seed, style/layout
recommendation, visual contract, design proposal, and pending preview-gate
setup. With only a topic, it calls `scripts/topic_research.py` by default in
fast mode, selects a small set of candidate URLs, ingests them through
`source_to_markdown.py`, and proceeds only when `source_cards.json` exists.
If automated research is skipped or unavailable, it writes a research brief and
reports `needs_research`; it must not invent source cards or final slide claims.

Standalone topic research:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/topic_research.py "<topic>" \
  --output-dir <project>/sources \
  --depth fast \
  --max-pages 3
```

`topic_research_report.json` records search candidates and provider gaps.
Search candidates are not evidence until the selected URLs are ingested into
`source_manifest.json` and represented in `source_cards.json`.

## Relationship To NotebookLM

NotebookLM is useful when:

- the source packet is large or mixed
- the user asks for deep analysis, recursive questions, report, mind map, or
  NotebookLM-specific artifacts
- YouTube/podcast/video handling benefits from NotebookLM or transcript tooling
- the user wants a Feishu document after analysis

For PPT generation, NotebookLM output should be treated as one analysis source,
not as the final slide plan. The Qiaomu PPT pipeline still needs:

- a Markdown research dossier that can be reviewed before slide planning
- source cards
- content angle confirmation
- `content_contract.json`
- `slide_plan.json`
- `layout_execution_contract`

Do not blindly use NotebookLM's generated slide deck as the final PPT. Use it as
a research aide or comparison artifact when helpful.

## Feishu Documents

Feishu/Lark documents are often private and context-rich. Handle them honestly:

- If the user provides an exported `.md`, `.docx`, `.pdf`, `.html`, or `.zip`,
  ingest that file normally.
- If an API/CLI/connector credential is available in the current environment,
  fetch the document, comments, highlights, and metadata into `sources/`.
- If the document is not accessible, ask for export or permission. Do not claim
  the content was read.
- If comments/highlights matter, treat them as first-class source cards, not
  as noise.

Record:

```json
{
  "source_type": "feishu_doc",
  "access_route": "exported_docx | exported_pdf | api | connector | missing",
  "comments_included": true,
  "highlights_included": true,
  "missing_evidence": []
}
```

## EPUB / Book Intake

Book-based PPTs need more than a summary:

- extract table of contents and chapter text
- create chapter cards
- build quote bank with chapter/location when available
- separate author claims, evidence, examples, and your interpretation
- record missing page/location evidence when EPUB lacks stable pagination

For a long book, do not make one slide per chapter by default. First identify:

- central thesis
- argument spine
- 5-8 reusable concepts
- strongest examples
- useful diagrams or frameworks
- audience-relevant action points

## PDF Intake

For PDFs:

- preserve the original PDF path and page count when available
- extract text page by page when possible
- render the first few pages to `sources/images/pdf-.../page-*.jpg` with
  Poppler when available, so cover, context, quote, and evidence slides can use
  real source-page visuals
- identify tables, figures, charts, and captions
- record pages for every quote or key claim
- OCR scanned PDFs only when OCR tooling is available; otherwise mark
  `missing_evidence: ["ocr_required"]`
- if page rendering is unavailable, mark
  `missing_evidence: ["pdf_page_images_not_rendered"]` instead of silently
  planning AI visuals as evidence

Dense reports often need chart/table extraction before deck writing. If the PDF
has no extractable text but appears important, pause rather than hallucinate.

## Paper Intake

For arXiv/Hugging Face paper sources:

- normalize Hugging Face paper URLs to arXiv IDs before extraction
- fetch arXiv API metadata; never guess title, authors, or published date
- download `https://arxiv.org/e-print/<id>` and prefer TeX/source extraction
- extract figure captions, table captions, image files, and section text
- save `paper_manifest.json` and `source_cards.json`
- fallback to arXiv PDF only when TeX/source is unavailable

Paper figures and tables should become slide proof objects. Generated images
can explain an analogy or concept, but must not replace paper originals.

## WeChat Article Intake

For `mp.weixin.qq.com`:

- first run the built-in URL baseline to capture whatever is immediately
  available
- record `source_type: wechat_article` and the specialized extractor candidates
- if text is weak or images are missing, use a WeChat-specific open-source
  extractor or ask for an exported article copy
- preserve account name, author, publish time, original URL, image paths, and
  extraction route when the extractor provides them

Do not trust empty Markdown image placeholders from generic converters. If the
image cannot be downloaded or permission is unclear, treat it as missing visual
evidence.

## Mixed Source Packets

When the user supplies multiple sources, do not flatten them too early. Maintain
source identity:

```json
{
  "source_id": "s03",
  "title": "Interview transcript",
  "source_type": "audio_transcript",
  "role": "primary_evidence",
  "markdown_path": "extracted/interview.md"
}
```

Then create cross-source cards:

```json
{
  "id": "cross-01",
  "claim": "Three sources agree that the bottleneck is source quality, not slide styling.",
  "source_ids": ["s01", "s03", "s05"],
  "evidence": "short synthesis",
  "usable_as": ["opening_tension", "summary_claim"],
  "confidence": "medium"
}
```

## Deep Analysis Questions

For long sources, generate 8-12 questions before writing slide claims:

- What is the central thesis?
- What are the strongest supporting facts or examples?
- What is surprising, counterintuitive, or contested?
- What should be a timeline, map, diagram, table, quote, or image?
- What does the intended audience already know?
- What would change their mind?
- What source evidence is missing?
- Which details belong in speaker notes instead of visible slide copy?

These questions can be answered by the agent, NotebookLM, or another analysis
tool, but the answers must be saved in `source_notes.md` or a sidecar JSON.

## Research Dossier Before Slide Plan

Before writing `content_contract.json` or `slide_plan.json`, synthesize the
cleaned sources into a user-reviewable Markdown dossier. Use
`research_dossier.md` when the project has multiple sources or a broad topic;
for small projects, `sources/source_notes.md` may serve this role if it is
detailed enough.

The dossier should include:

- supplied-source summary and what each source contributes
- model-knowledge assumptions that need source confirmation
- web/source research findings with source IDs or URLs
- source coverage, contradictions, and missing evidence
- visual asset inventory, image rights notes, and source/image gaps
- recommended content angle options when the material supports more than one
  story

After the dossier, create a page-by-page slide plan and ask for confirmation
unless the user explicitly skipped this gate. Do not use a polished design or
PPTX export as the first review surface for source-heavy work.

## Minimum Gate

Before `content_contract.json`, a source-backed PPT should have:

- `source_manifest.json` with every source and extraction route
- cleaned Markdown/text for each usable source
- `research_dossier.md` or substantial `source_notes.md` synthesizing the
  material before slide planning
- source coverage notes and gaps
- source cards for main claims
- image/visual asset candidates when visual material matters
- user-confirmed or explicitly assumed content angle

If this stage is missing, the deck may look polished but will feel hollow.
