# Production Contract

Each normal run should create a project folder with these artifacts or explain why a route does not need them.

```text
<project>/
  README.md             # human-readable task archive index
  task_manifest.json    # machine-readable stage/file index
  deck_brief.md
  research_dossier.md   # first-stage research package, useful even without PPT generation
  content_report.md      # source-synthesis article; Chinese projects may use 内容母稿-<主题>.md
  content_contract.json  # audience-purpose card, structure framework, title policy, slide claims
  slide_plan.json
  page_content_guide.md  # human-readable per-page content/script guide when generated
  page_content_guide.json
  style_recommendations.json  # when style is unspecified or auto recommendation is requested
  layout_recommendations.json # when image/text pattern recommendation is used
  style_brief.md
  spec_lock.json
  ppt_config.json       # optional explicit PPT execution config, when a route uses it
  visual_asset_manifest.json  # acquisition route, status, prompt/source, files, rights, QA notes
  visual_contract.json  # background rhythm, layout roles, image/text plan, image slots
  visible_provenance_policy.json  # optional; required when citations are visible
  speaker_notes_plan.md
  svg_generation_manifest.json # SVG-first page generation evidence
  svg_preview_manifest.json    # browser-rendered SVG visual preview evidence
  pptx_generation_manifest.json # built-in PPTX exporter evidence
  pptx_preview_manifest.json    # LibreOffice/Poppler rendered preview evidence
  pptx_text_check.json          # visible text parity/placeholders/internal metadata check
  export_manifest.json          # multi-format delivery status for PPTX/PDF/HTML/parity/Keynote
  assets/
    images/
      image_prompts.json # AI image work queue when generated visuals are planned
      image_prompts.md   # human-readable prompt sidecar
      image_sources.json # optional; web/user/source asset provenance
    source-images/
    charts/
    diagrams/
  sources/
    source_manifest.json  # when URLs/PDFs/images were ingested
    images/
  previews/
  svg_output/          # editable PPTX route
  svg_final/           # checked SVG pages after final fixes, when SVG-first output is used
  html/                # formal semantic HTML deck
  html-parity/         # preview-only PPTX/PDF screenshot parity route
  exports/
    <slug>.pptx
    <slug>.pptx.trace.json # SVG-to-PPTX conversion trace when enabled
    <slug>.pdf         # portable viewing artifact when exported or reused from PPTX preview
    <slug>.html        # formal semantic HTML deck when requested/expected
    <slug>.parity.html # preview-only PPTX parity HTML when generated
    <slug>.key         # optional macOS Keynote artifact when automation succeeds
  html_delivery_manifest.json  # required for formal HTML delivery
  html_parity_manifest.json    # required only for screenshot parity preview
  animations.json      # optional sidecar for group-level animation intent
  notes/
    total.md           # full narration / word-for-word speaker script when requested
  qa_report.md
```

Stage boundaries:

- `00_research`: `README.md`, `task_manifest.json`, `research_dossier.md`,
  `sources/source_manifest.json`, `sources/source_notes.md`,
  `sources/source_cards.json`, and downloaded/extracted source images. This is
  a first-class deliverable even when the deck is never generated.
- `01_content_synthesis`: `content_report.md` or `内容母稿-<主题>.md`. This is
  the source-synthesis article that turns links, notes, and evidence cards into
  a readable argument. Formal `slide_plan.json` should be extracted from this
  article, not directly from link lists or raw source summaries.
- `02_story_planning`: `content_contract.json`, `slide_plan.json`,
  `page_content_guide.*`, speaker notes, and per-page scripts.
- `03_visual_and_config`: `style_*`, `spec_lock.json`, `ppt_config.json`,
  `visual_contract.json`, `visual_asset_manifest.json`, and image prompts.
- `04_generation_and_delivery`: PPTX/HTML/PDF/Keynote exports, previews,
  checks, QA reports, and delivery manifests.

Default project root is `~/Downloads/Qiaomu PPT/<date>-<slug>/` unless the user
or calling project explicitly provides another path.

## README.md / task_manifest.json

Required for normal project preparation. These files make each task folder
understandable later.

Required shape for `task_manifest.json`:

```json
{
  "schema_version": "1.0.0",
  "topic": "Deck topic",
  "project": "/absolute/path",
  "storage_policy": {
    "default_root": "~/Downloads/Qiaomu PPT",
    "project_naming": "<YYYY-MM-DD>-<slug>"
  },
  "stages": [
    {
      "id": "00_research",
      "label_zh": "资料搜索整理",
        "artifacts": ["research_dossier.md", "content_report.md", "sources/source_manifest.json"]
    }
  ]
}
```

Hard rules:

- Every normal run gets one task folder. Do not scatter downloaded images,
  source links, prompts, and exports across unrelated temp paths.
- The research archive must remain useful if the workflow stops before PPT
  generation.
- Broad-topic decks should include `content_report.md` or `内容母稿-<主题>.md`
  before `slide_plan.json`; `research_dossier.md` is a source archive, not the
  content argument.

Hard HTML rules:

- Formal HTML delivery must be a real web presentation built from DOM/SVG/Canvas/CSS/JS components, not whole-slide PDF/JPG/PNG screenshots.
- `html-parity/` and `*.parity.html` are QA/preview artifacts only. They may use rendered slide images, but must not be reported as the formal HTML deck.
- If the user asks for an HTML version, `html_delivery_manifest.json` must exist and point to the formal semantic HTML outputs.
- `export_manifest.json` is the authority for final multi-format delivery. PPTX, PDF, formal HTML, parity HTML, and Keynote must have separate statuses; Keynote failure must not poison PPTX/PDF/HTML delivery, and PPTX/PDF success must not imply Keynote compatibility.

## deck_brief.md

Required fields:

- title
- route
- final_delivery
- audience
- goal
- current_state
- desired_state
- density
- page_count
- source_inventory
- url_inventory
- assumptions
- verification_plan

## sources/source_manifest.json

Required when the task ingests URLs, PDFs, or page images.

Required shape:

```json
{
  "schema_version": "1.0.0",
  "sources": [
    {
      "input": "https://example.com/article",
      "title": "Article title",
      "source_type": "url",
      "fetch_route": "direct_html",
      "fetched_at": "2026-06-20T00:00:00+00:00",
      "markdown_path": "article-title.md",
      "pdf_path": "",
      "images": [],
      "warnings": [],
      "missing_evidence": []
    }
  ]
}
```

Hard rules:

- Slide claims must be traceable to a source record or marked as draft assumptions.
- `missing_evidence` must be carried into `qa_report.md`; do not hide failed extraction.
- Image records are candidate evidence only. They still need image slots before slide use.

## content_contract.json

Required when the deck has more than 8 slides, unless the route is only a short visual preview.

Required fields:

- `audience`
- `purpose`
- `desired_action`
- `current_state`
- `desired_state`
- `stakes`
- `structure_framework`: list using `pyramid`, `SCQA`, `MECE`, `storyline`, `teaching_arc`, or `hybrid`.
- `title_policy`: normally `claim_titles`.
- `copy_density`: expected visible copy density.
- `evidence_policy`: how claims connect to proof.
- `speaker_note_policy`: what notes must carry.
- `slide_claims`: per-slide `slide_no`, `claim_title`, `evidence_type`, and `spoken_role`.

Hard rules:

- The slide titles should read as an argument when scanned in order.
- Generic label titles such as `背景`, `现状`, `问题`, `方案`, `数据`, `总结`, `Overview`, and `Agenda` are not acceptable unless they include a specific claim.
- Mainline slides should carry one dominant claim. Put dense evidence, caveats, and secondary detail into notes or appendix.
- Visible support copy should normally stay within 3-5 chunks per slide, except classroom/report routes where density is intentional.

## slide_plan.json

Each slide item should include:

- `slide_no`
- `title` or `claim_title`
- `intent`
- `audience_or_learning_state_before`
- `audience_or_learning_state_after`
- `content_points`
- `visual_role`
- `media_need`
- `speaker_note_goal`
- `qa_risk`

## style_brief.md

Required fields:

- selected_preset_id, when a Design-MD preset is used
- visual thesis
- content thesis
- title policy
- copy density
- visual noise budget
- color budget
- palette
- typography
- layout rhythm
- background rhythm
- background asset policy
- layout role matrix
- image slot contract
- visible provenance policy
- density rules
- chart/table rules
- image rules
- animation policy
- forbidden moves

## spec_lock.json

This is the execution contract. Re-read it before authoring or revising each slide.

Required fields:

- canvas
- route
- final_delivery
- density
- content_contract
- selected_preset_id
- palette
- typography
- layout_rhythm
- background_rhythm
- image_generation_model
- visual_asset_policy
- visual_noise_budget
- color_budget
- layout_roles
- image_slot_contract
- image_policy
- visible_provenance_policy
- svg_policy
- layout_execution_contract
- notes_policy

The file should be literal enough that colors, fonts, spacing, image slots, and notes policy cannot drift during long deck production.

## visual_asset_manifest.json

Required when the deck uses generated images, web images, user images,
source-extracted images, charts, diagrams, formula renders, icons, or
placeholders.

Top-level required fields:

- `schema_version`
- `deck_image_model`: deck-wide image generation/style lock, including `image_rendering`, `image_palette_behavior`, and model/tool route when known.
- `items`: list of visual asset rows.
- `status_summary`: counts by status, optional before final QA but useful in reports.

Each asset row should include:

- `asset_id`
- `acquire_via`: one of `ai`, `web`, `user`, `source`, `formula`, or `placeholder`.
- `status`: `Pending`, `Generated`, `Sourced`, `Existing`, `Rendered`, `Placeholder`, `Needs-Manual`, `Missing`, or `Failed`.
- `asset_role`: such as `background`, `chapter_art`, `concept_metaphor`, `scenario`, `object_cutaway`, `texture`, `moodboard`, `evidence_image`, `paper_figure`, `chart`, `diagram`, `formula`, `icon`, or `placeholder`.
- `page_role`: `hero_page`, `local`, `supporting`, or `reference`.
- `text_policy`: `none` for generated bitmaps by default; `embedded` only when the image itself is source evidence containing text.
- `prompt` for AI assets, or `source_url` / `source_path` / `source_card_id` for non-AI assets.
- `path`: required for `Generated`, `Sourced`, `Existing`, and `Rendered` rows.
- `slide_usage`: planned slide numbers or roles.
- `fit`, `crop_policy`, and `safe_area` when the row appears in a slide slot.
- `rights` and `provenance_notes`.
- `qa_notes`.

Hard rules:

- Generated images may carry atmosphere, concept, scenario, object, texture, or moodboard roles. They must not fake paper figures, screenshots, product UI, logos, data charts, tables, or citation evidence.
- Hero-style generated images should not contain text. Editable slide titles, captions, charts, diagrams, labels, and UI are foreground PPT/HTML objects.
- A `Generated`, `Sourced`, `Existing`, or `Rendered` row without an existing file is a hard defect.
- `Pending` rows are allowed during proposal and preview work. They are not allowed in a claimed final deck unless the limitation is listed as missing evidence.
- `Needs-Manual`, `Missing`, and `Failed` are truthful terminal statuses. They can be accepted only when the deck explicitly works around them or reports the limitation.
- Web/source images need rights/provenance notes. Do not assume a public URL grants slide-use rights.

## layout_execution_contract

Required for SVG-first, PPTX-oriented, chart/diagram-heavy, image-rich, or deck
runs longer than 8 slides.

It lives inside `spec_lock.json` and connects slide content to renderable layout.

Required top-level fields:

- `coordinate_policy`: normally `absolute_stage_coordinates`.
- `text_fit_policy`: how the renderer handles line breaks, min/max sizes, and overflow.
- `slides`: per-slide execution entries.

Each slide entry should include:

- `slide_no` or `slide_id`
- `rhythm`: `anchor`, `dense`, or `breathing`
- `proof_object`: the semantic object that supports the claim
- `layout_pattern_id`: concrete ID from `layout-pattern-library.md`
- `image_text_pattern_id`: concrete ID from `image-text-layout-patterns.md` when the slide uses a major image, screenshot, product render, quote portrait, before/after pair, image timeline, or data plus context media
- `component_type`: renderable family such as `numbered_steps`, `timeline`, `basic_table`, `chart_with_takeaway`, `full_bleed_image_claim`, or `mechanism_loop`
- `reading_path`
- `coordinate_slots`: title/proof/media/chart/table boxes with `x`, `y`, `w`, `h`
- `group_ids`: stable top-level SVG/PPT object groups for editing, QA, and optional animation. SVG-first executors should emit semantic top-level groups such as `slide-XX-background`, `slide-XX-media`, `slide-XX-title`, `slide-XX-proof`, `slide-XX-body`, and `slide-XX-footer`, and `spec_lock.json` must declare the generated IDs.

Hard rules:

- The component must match the proof object. A process becomes steps/flow; records become table; time milestones become timeline; evidence chart becomes chart-with-takeaway.
- Do not render from mood words such as "premium", "magazine", or "tech" without concrete slots and components.
- SVG pages under `svg_output/` or `svg_final/` should contain matching top-level `<g id="...">` groups for the declared group IDs.
- Do not rely on one wrapper group such as `slide-XX` for the whole page. Top-level groups should preserve z-order while exposing editable/animatable semantic regions.
- If `animations.json` exists, its group IDs must refer to real SVG groups.

## visual_contract.json

Required when the deck has more than 8 slides or uses source images/charts.

Required fields:

- `background_roles`: list of reusable roles such as `cover_atmosphere`, `dark_evidence`, `light_evidence`, `diagram_focus`, and `closing_atmosphere`.
- `slide_roles`: per-slide mapping of `slide_no`, `layout_role`, `background_role`, `dominant_object`.
- `visual_noise_budget`: normally `quiet`; use `moderate` only when justified by brand or route.
- `color_budget`: `max_active_colors_per_slide: 3`, `count_source_images: false`, and a one-accent policy.
- `slide_palette_slots`: per-slide mapping of `slide_no` and `active_colors`; each slide must stay within the color budget.
- `background_asset_policy`: whether generated bitmap backgrounds, procedural CSS/Canvas/SVG backgrounds, neutral surfaces, or no backgrounds were used. It must also declare `atmosphere_only_policy`, `procedural_fallback_policy`, `editable_foreground_policy`, and `forbidden_generated_objects`.
- `visual_asset_manifest_path`: path to `visual_asset_manifest.json` when visual assets are planned.
- `image_acquisition_policy`: summary of which asset types are `ai`, `web`, `user`, `source`, `formula`, or `placeholder`, and which statuses must be terminal before final export.
- `image_text_layout_plan`: per-slide mapping of `slide_no`, `layout_pattern_id`, `image_text_pattern_id`, `image_role`, `crop_policy`, `text_safe_area`, `contrast_policy`, and `font_floor_pt` when a slide uses substantial media.
- `image_slots`: every source image/chart slot with `slot_id`, `slide_no`, `x`, `y`, `w`, `h`, `fit`, `mask`, `padding`, and `overflow_policy`.
- `max_consecutive_background_role`: normally `2`.
- `thumbnail_review_required`: `true` for PPTX decks.

Hard rules:

- No repeated decorative background role for more than 2 consecutive slides.
- Background decoration must stay subordinate to content. Avoid repeated hard rails, oversized saturated wedges, ornamental grids, meaningless thin rules, and multiple decorative systems on the same slide.
- Prefer generated 16:9 bitmap background packs in Codex image-generation environments. If unavailable, use deterministic CSS/Canvas/SVG procedural backgrounds or clean neutral surfaces instead of line-based decoration.
- Generated backgrounds must be atmosphere only: colors, gradients, soft light, subtle grain, and abstract texture. Do not bake boxes, cards, panels, frames, placeholders, chart areas, image slots, UI chrome, text blocks, or other layout scaffolding into the bitmap.
- Canvas/WebGL/CSS backgrounds for editable PPTX routes must be rendered to static PNG/SVG assets before insertion.
- Titles, cards, charts, frames, diagrams, labels, and evidence slots must be editable foreground objects in PPT/HTML.
- No slide should use more than 3 active non-image colors. Do not combine cyan, green, yellow, red, and other accent colors on one page.
- Image/text compositions must name an `ITLxx` pattern when media placement is the main layout decision. Text-over-image layouts must use copy space, scrim, gradient, text block, or local blur and pass readability review.
- Dense charts use `contain` unless a crop is explicitly justified.
- A rounded frame is not a clipping mask; if `mask` is `rounded_rect`, the renderer must actually clip or pre-compose the image.

## visible_provenance_policy

Default policy:

```json
{
  "visible_slide_provenance": "none",
  "content_source_location": "qa_report_or_notes",
  "generation_metadata_location": "generation_report",
  "allow_internal_toolchain_on_slide": false
}
```

Rules:

- Do not print fetch tools, model names, provider names, or QA status on the slide canvas by default.
- Do not show `Speaker cue:` on slides. Use speaker notes or `speaker_notes_plan.md`.
- Use visible citations only when the user asks, the route requires it, or the deck is an academic/report artifact. In that case, cite content sources only and keep generation metadata out of the slide.
- If a final references page is used, put it at the end; do not repeat production metadata as a footer on every page.

## qa_report.md

Required fields:

- route gate
- source gate
- narrative gate
- copy gate
- visual gate
- provenance gate
- readability gate
- production gate
- speaker gate
- verification gate
- missing evidence
- next actions

## Deterministic Check

When a style is unspecified, produce recommendations first:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/recommend_style.py --query "<brief>" --route "<route>" --top 5 --json
```

Save the result as `style_recommendations.json`, then write the selected style
entry into `style_brief.md` and `spec_lock.json`.

The default recommender searches `design_style_presets.json`,
`magazine_art_styles.json`, and `ppt_master_case_styles.json`. When the selected
entry is a case style, copy its media, chart, and image asset strategy into the
visual contract instead of treating it as a color theme only.

For a selected ppt-master case style, consult
`data/ppt_master_examples_catalog.json` before rendering. If the reference case
is image-rich, the current project needs an explicit source/generated image
plan. If the reference case is chart-rich, the current project needs chart specs
or source data. If neither exists, revise the style choice or mark the missing
evidence in the design proposal.

When an image/text composition is unspecified but the deck uses substantial
media, produce image/text pattern recommendations:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/recommend_layout.py --query "<brief>" --route "<route>" --top 5 --json
```

Save the result as `layout_recommendations.json`, then write selected `ITLxx`
entries into `slide_plan.json`, `spec_lock.json`, and
`visual_contract.json.image_text_layout_plan`. The selected `ITLxx` pattern must
be mapped to an `Lxx` proof-structure pattern rather than replacing it.

When generated/web/user/source/formula visual assets are planned, create a
visual asset manifest before rendering:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/visual_asset_manifest.py init \
  --project <project_dir> \
  --subject "<deck subject>" \
  --route "<route>" \
  --rendering "<image rendering>" \
  --palette "<palette behavior>" \
  --primary "<hex>" \
  --secondary "<hex>" \
  --accent "<hex>"
```

Update `visual_asset_manifest.json` as assets are generated, sourced, copied, or
rendered. If AI assets are present, keep `assets/images/image_prompts.json` and
`assets/images/image_prompts.md` in sync:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/visual_asset_manifest.py render-md \
  --prompts <project_dir>/assets/images/image_prompts.json \
  --output <project_dir>/assets/images/image_prompts.md
```

Before final export or handoff, validate the asset manifest:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/visual_asset_manifest.py validate \
  --manifest <project_dir>/visual_asset_manifest.json \
  --project <project_dir> \
  --require-terminal
```

For decks longer than 8 slides or decks with source images/charts, create `visual_contract.json` before rendering. Use it as the check list during thumbnail review.

For decks longer than 8 slides, create `content_contract.json` before rendering. Use it to check audience fit, structure choice, title quality, evidence policy, and speaker notes.

When these artifacts exist, run:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/check_project.py <project_dir>
```

If the checker reports failures, fix them before claiming the deck is done. If it only reports warnings, either fix them or list them under `missing evidence` / known limitations.

## SVG-first PPTX Export

The final-quality editable PPTX path is self-contained and SVG-first inside
`qiaomu-ppt`; do not invoke an external `pptx` skill at runtime.

The visual source of truth is the shared `slide_plan.json`, `spec_lock.json`,
and `layout_execution_contract`. Do not make a polished HTML/PNG preview and
then hand-build a separate lower-quality editable PPTX. If the deck needs
pixel-level atmosphere, texture, soft light, or photographic depth, rasterize
only those background/media layers; keep the foreground reading layer as native
PPTX objects after SVG-to-DrawingML export.

Generate PPT-safe SVG pages, inspect them, then export native DrawingML PPTX:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/svg_deck_from_slide_plan.py \
  <project_dir> --force

python3 ~/.agents/skills/qiaomu-ppt/scripts/svg_quality_checker.py \
  <project_dir>/svg_output

python3 ~/.agents/skills/qiaomu-ppt/scripts/svg_preview.py \
  <project_dir> --source svg_output

python3 ~/.agents/skills/qiaomu-ppt/scripts/finalize_svg.py \
  <project_dir>

python3 ~/.agents/skills/qiaomu-ppt/scripts/svg_to_pptx.py \
  <project_dir> -s output --no-compat \
  --conversion-trace \
  -o <project_dir>/exports/<slug>.pptx
```

This writes `svg_generation_manifest.json`, `svg_preview_manifest.json`, and
optionally `<slug>.pptx.trace.json`. `--no-compat` still exports editable native
DrawingML; remove it only when CairoSVG or svglib/reportlab is installed and
older-Office PNG fallback is required.

Use the `python-pptx` direct exporter only as a low-complexity fallback:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/pptx_from_slide_plan.py \
  <project_dir> \
  --output <project_dir>/exports/<slug>.pptx
```

This writes `pptx_generation_manifest.json` with source-contract and output
evidence. It is appropriate for quick drafts, skeleton decks, and simple
diagrams where `python-pptx` supports them; do not use it as the main path for
polished image-rich, chart-rich, or `ppt-master`-level decks.

Whole-slide image PPTX files are not editable PPTX deliverables. They may be
created only as parity previews, social-image packs, or user-approved
non-editable visual drafts, and their filenames/reports must say
`image-backed` or `non-editable`.

Check visible text:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/pptx_text_check.py \
  <project_dir>/exports/<slug>.pptx \
  --slide-plan <project_dir>/slide_plan.json \
  --output <project_dir>/pptx_text_check.json
```

Render preview evidence:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/pptx_preview.py \
  <project_dir>/exports/<slug>.pptx \
  --project <project_dir>
```

This creates `pptx_preview_manifest.json`, a PDF, per-slide JPG previews, and
`previews/thumbnail-grid.jpg`. If LibreOffice or Poppler is unavailable, report
the missing visual preview evidence instead of claiming full PPTX QA.

## Multi-Format Export Bundle

After the main deck artifacts exist, use the bundle exporter to collect the
delivery targets and write a single status manifest:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/export_bundle.py \
  <project_dir> \
  --slug <slug> \
  --title "<deck title>" \
  --formats pptx,pdf,html,html-parity
```

Add `keynote` only when macOS Keynote delivery or compatibility testing is part
of the request:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/export_bundle.py \
  <project_dir> \
  --slug <slug> \
  --title "<deck title>" \
  --formats pptx,pdf,html,html-parity,keynote
```

The bundle exporter writes `export_manifest.json`. When a manifest already
exists, a subset export such as `--formats keynote` updates only the requested
formats, preserves earlier statuses for other formats, and records the subset in
`last_requested_formats`. It should:

- reuse an existing PPTX and preview PDF when they already exist;
- reuse existing PDF, parity preview, or Keynote package evidence only when it is at least as fresh as the current PPTX source;
- create formal HTML from `svg_final/` when present, then `svg_output/`;
- create screenshot-based parity HTML only under `html-parity/` and
  `*.parity.html`;
- record `missing` or `failed` for formats that cannot be produced, including stale `.key` packages that cannot be refreshed;
- try Keynote 09 `.key` fallback when modern `save as Keynote` automation fails or times out, and record `compatibility_format: Keynote 09` plus the primary failure when the fallback succeeds;
- include a `diagnostic_command` for failed Keynote exports that runs
  `scripts/keynote_probe.py --with-control` against the same PPTX and `.key` target;
- never call an external `pptx` skill at runtime.

Use `--strict` only when every requested target is required. For normal
delivery, keep Keynote out of `--strict` unless the user explicitly made it a
hard requirement, because Keynote automation can be blocked by macOS UI state or
document import timing.

For deeper Keynote failures, run the diagnostic command from
`export_manifest.json` or invoke the probe directly:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/keynote_probe.py \
  <project_dir>/exports/<slug>.pptx \
  --output <project_dir>/exports/<slug>.key \
  --report <project_dir>/reports/<slug>.keynote-probe.json \
  --with-control
```

Treat the probe as successful only when it reports `status: ok` and the `.key`
artifact is at least as fresh as the PPTX source. If the probe reports
`export_strategy: Keynote 09 fallback`, the `.key` is a valid fallback artifact
but the compatibility format must be reported honestly. Use the `control_probe`
section to distinguish input-specific Keynote failures from baseline Keynote
save automation failures.
