# Paper Source Intake

Paper-based PPTs need a stronger source route than generic web extraction. A
paper URL is not just an article; it usually contains figures, tables,
equations, benchmark numbers, method diagrams, and captions that should become
PPT proof objects.

## Supported Inputs

`qiaomu-ppt` treats these as paper sources:

- `https://arxiv.org/abs/<id>`
- `https://arxiv.org/pdf/<id>`
- `https://arxiv.org/html/<id>`
- `https://huggingface.co/papers/<id>`
- bare arXiv IDs such as `2606.02437` or `2606.02437v2`

Hugging Face Papers is a discovery input. Before extraction, normalize it to an
arXiv ID, then use arXiv as the source of truth.

## Extraction Ladder

1. Resolve the arXiv ID.
2. Fetch arXiv API metadata for title, authors, published date, and abstract.
3. Download `https://arxiv.org/e-print/<id>`.
4. If the e-print contains TeX/source files, extract them under
   `sources/papers/<id>/tex_source/`.
5. Find the main `.tex`, resolve `\input{}` / `\include{}` files, then extract:
   - abstract
   - section text
   - figure captions
   - `\includegraphics` assets
   - table captions and basic tabular data
6. Copy usable figure assets into `sources/images/`.
7. Write `sources/extracted/paper-*.md`, `sources/papers/<id>/paper_manifest.json`,
   and `sources/source_cards.json`.
8. If TeX is unavailable, use arXiv PDF text fallback and record
   `tex_source_unavailable`.

Run:

```bash
python3 scripts/paper_to_markdown.py \
  "https://huggingface.co/papers/2606.02437" \
  --output-dir demo/sources
```

Mixed source intake uses the same route automatically:

```bash
python3 scripts/source_to_markdown.py \
  "https://arxiv.org/abs/2606.02437" \
  --output-dir demo/sources
```

## PPT Usage Rules

- Treat paper figures, tables, diagrams, and benchmark charts as proof objects,
  not decorative images.
- In `slide_plan.json`, map each method/result slide to a `source_card_id`,
  `source_anchor`, and `proof_object` such as `paper_figure`, `paper_table`,
  `method_diagram`, or `benchmark_chart`.
- If a figure asset is not copied, keep the caption as evidence but mark the
  visual as missing. Do not redraw or regenerate it as if it were the original
  evidence.
- Generated images may explain a concept metaphorically, but must not replace
  paper figures, tables, screenshots, or benchmark charts.
- Use `paper_manifest.json` as the audit trail for arXiv ID, source route,
  figures, tables, warnings, and missing evidence.

## Missing Evidence

Record these explicitly:

| Case | Missing Evidence |
|---|---|
| HF page has no discoverable arXiv ID | `huggingface_arxiv_id_not_found` |
| arXiv e-print returns PDF only | `tex_source_unavailable` |
| main `.tex` cannot be found | `main_tex_not_found` |
| a figure caption exists but asset cannot be copied | `figure_N_asset_not_copied` |
| PDF fallback has no extractable text | `pdf_text_extraction_failed` |

If the paper has important TikZ-only diagrams, use the PDF screenshot/crop route
as a manual enhancement and record `source: pdf_screenshot` on that asset. Never
pretend a generated replacement is a paper original.
