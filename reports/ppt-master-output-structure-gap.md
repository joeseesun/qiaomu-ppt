# PPT Master Output Structure Gap

Generated: 2026-06-21

## What PPT Master Examples Ship

The public `ppt-master/examples/README.md` defines a deliberately lean example project:

- `design_spec.md`: human-readable design specification.
- `spec_lock.md`: machine-readable execution contract.
- `images/`: image assets.
- `notes/`: speaker notes per page.
- `svg_output/`: original SVG pages, sometimes with placeholders.
- `svg_final/`: final SVG pages after icon/image embedding.

The public examples intentionally omit `sources/` and `exports/` to keep the repository small. Real projects are expected to have both original source documents and PPTX exports.

From the local `data/ppt_master_examples_catalog.json` learning catalog:

- Projects: `21`
- Slides: `280`
- SVG final pages: `280`
- Image files: `260`
- Spec image references: `241`
- Notes files: `301`
- Export files indexed: `21`
- Median slide count: `12`
- Median image files per slide: `0.667`
- Median spec image refs per slide: `0.667`
- Median notes per slide: `1.083`
- Most image-heavy cases:
  - `ppt169_liziqi_plant_dye_colors`: 12 slides / 32 images / 2.67 images per slide
  - `ppt169_pritzker_2026`: 11 slides / 25 images / 2.27 images per slide
  - `ppt169_home_design_trends_2026`: 12 slides / 24 images / 2.0 images per slide
  - `ppt169_high_rise_renewal`: 15 slides / 25 images / 1.67 images per slide
  - `ppt169_fashion_weekly_digest`: 16 slides / 23 images / 1.44 images per slide

## What Qiaomu PPT Already Ships

The current `/tmp/qiaomu-source-reuse-smoke` project demonstrates a richer production folder:

- Source intake:
  - `sources/source_manifest.json`
  - `sources/source_notes.md`
  - `sources/source_cards.json`
  - extracted source Markdown
  - topic research reports
- Content planning:
  - `deck_brief.md`
  - `design_proposal.md`
  - `content_contract.json`
  - `slide_plan_seed.json`
  - `slide_plan.json`
- Style and layout:
  - `style_recommendations.json`
  - `style_direction.json/md`
  - `layout_recommendations.json`
  - `visual_contract.json`
  - `design_spec.md`
  - `spec_lock.json/md`
- Visual assets:
  - `visual_asset_rows.json`
  - `visual_asset_manifest.json`
  - `image_art_direction.json`
  - `image_generation_readiness.json`
- Rendered slide sources:
  - `svg_output/*.svg`
  - `svg_final/*.svg`
  - `svg_generation_manifest.json`
  - `svg_preview_manifest.json`
- Speaker notes:
  - `notes/*.md`
- Multi-format exports:
  - editable `.pptx`
  - `.pdf`
  - formal semantic `.html`
  - parity preview `.html`
  - Keynote `.key`
  - PPTX trace
- Preview evidence:
  - rendered slide JPGs
  - thumbnail grid
  - HTML screenshots
  - PPTX preview manifest
- Quality evidence:
  - `source_adequacy`
  - `content_outline_audit`
  - `element_plan_audit`
  - `style_fit_audit`
  - `style_execution_audit`
  - `visual_rhythm_report`
  - `svg_quality_report`
  - `pptx_text_check`
  - `project_check`
  - `deck_quality_benchmark`
  - `deck_repair_plan`
  - `production_manifest/report`
  - `export_manifest`

Smoke metrics:

- Slides: `6`
- Source cards: `16`
- Source image candidates: `35`
- Terminal source visual assets: `6`
- Source-backed slides: `6/6`
- Notes files: `6`
- Final SVG pages: `6`
- Export formats: `pptx`, `pdf`, `html`, `html-parity`, `keynote`
- Benchmark: `100`
- Readiness: `ppt_master_ready`
- Upstream creation quality: `100`

## Where PPT Master Is Still Stronger

- Visual richness in the best examples: several public cases exceed `1.4-2.7` images per slide. Qiaomu can match this when sources are image-rich, but topic-only decks still need stronger source/web/AI image acquisition.
- Gallery/demo polish: PPT Master has a clean public gallery and examples index. Qiaomu has stronger project evidence, but less packaged public showcase.
- Native animation/narration direction: recent PPT Master releases emphasize native animations, audio narration, and video export. Qiaomu has export breadth, but narrated/video delivery is not yet a first-class gate.
- Template routes: PPT Master highlights template-follow/fill and beautify routes. Qiaomu should add stronger template ingestion, identity inheritance, and content-faithful relayout evidence.

## How Qiaomu PPT Can Surpass

The winning axis is not copying the example folder. It is shipping a more complete, source-grounded production system:

1. Keep PPT Master parity:
   - `design_spec`
   - `spec_lock`
   - `images`
   - `notes`
   - `svg_output`
   - `svg_final`
   - editable PPTX

2. Exceed with source intelligence:
   - Always preserve `source_manifest`, extracted Markdown, source cards, image candidates, and missing-evidence flags.
   - Paper/WeChat/EPUB/PDF/Office/ZIP sources should carry source-type-specific sidecars, not collapse into generic text.

3. Exceed with creation gates:
   - Fail early on weak content outline, weak element plan, and style mismatch.
   - Treat these as upstream creative quality, not post-export QA.

4. Exceed with visual asset governance:
   - Maintain `visual_asset_manifest` as the single procurement ledger for source/web/user/AI/formula assets.
   - Compare each deck's image density against the PPT Master case catalog by route/style, not only globally.
   - Require source visuals before AI substitutes when evidence matters.

5. Exceed with multi-format delivery:
   - Deliver PPTX, formal semantic HTML, parity HTML, PDF, and Keynote with freshness checks.
   - Keep formal HTML selectable/semantic, not only a screenshot gallery.

6. Exceed with repair loops:
   - `deck_quality_benchmark` should continue to score upstream creation quality, visual rhythm, style execution, image density, source grounding, image resolution, export coverage, and contracts.
   - `deck_repair_plan` should convert every weak category into artifact-level repairs.

7. Add next-generation parity gaps:
   - First-class narration/audio/video export.
   - Template follow/fill route with identity inheritance and native layout reuse.
   - Public gallery generated from production manifests, showing not only thumbnails but also source coverage, asset density, output formats, and QA status.

## Practical Next Gates

- Add an `output_superiority_audit.py` that compares a project against PPT Master example baselines and checks:
  - example-parity structure
  - source-intelligence surplus
  - multi-format delivery surplus
  - quality-report surplus
  - image-density target by style family
  - notes/animation/narration readiness
- Add a route-aware image-density target instead of one global target:
  - paper/technical: figures, formulas, diagrams, charts
  - culture/biography: portraits, places, artifacts, timelines
  - magazine/fashion/home: 1.5+ visual assets per slide
  - consulting/report: charts/tables/diagram assets may substitute for photos
- Add gallery export from `production_manifest.json` so each Qiaomu output can be inspected like PPT Master examples, but with stronger provenance and QA evidence.
