# Model-Driven PPT Generation Contract

Use this reference after the user approves the `PPT Design Proposal`. It turns the proposal into durable project artifacts so the generator does not drift across pages.

## Core Rule

Do not generate slides directly from chat memory. Generate from project files:

```text
design_proposal.md       user-facing approved direction
research_plan.md/json    topic research questions and source strategy when needed
sources/source_notes.md  topic/source understanding, timeline, quote bank, gaps
sources/source_cards.json structured evidence units for slide claims
sources/papers/<id>/paper_manifest.json paper metadata, TeX/PDF route, figures, tables
design_spec.md           human-readable story and design plan
spec_lock.md             machine-readable execution lock
slide_plan.json          per-slide content and visual role
layout_execution_contract spec_lock section for proof object, geometry slots, component type, group IDs
visual_asset_manifest.json images/backgrounds/icons/charts
generation_report.md     deviations, checks, export evidence
```

For decks longer than 8 slides, these artifacts are mandatory. For shorter decks, they are still strongly preferred when the request involves URLs, images, charts, teaching material, brand material, or PPTX export.

For decks expected to exceed 7 slides, add a preview artifact before full generation:

```text
preview_gate.json       four-slide preview selection, outputs, QA notes, user decision
```

Full generation may proceed only when `preview_gate.json.user_decision` is `approved`, or when `skipped_by_user` is true with the exact user instruction recorded.

## Phase Discipline

### Phase 1: Route and Source

Output:

- `route_card.md`
- `sources/source_manifest.json`
- cleaned source Markdown and downloaded/copied assets when URLs/files/source packets are present
- `sources/papers/<id>/paper_manifest.json` when arXiv/Hugging Face paper sources are present
- `research_plan.md` or `research_plan.json` for broad-topic requests
- `sources/source_notes.md` and `sources/source_cards.json` for topic-researched decks

Rules:

- Source Markdown owns text facts.
- Image/PPT/PDF metadata owns geometry and media facts.
- Broad topic requests are source tasks first, not writing tasks. Follow `topic-research-method.md` before generating an outline.
- Mixed source requests are source-intake tasks first. Use `source-intake-method.md` and `source_to_markdown.py` to preserve source identity across URLs, arXiv/Hugging Face papers, WeChat articles, PDFs, EPUBs, Office docs, Feishu exports, images, ZIPs, and folders.
- Paper requests use `paper-source-intake.md`: normalize to arXiv, prefer TeX/e-print, extract figure/table evidence, and bind paper cards to `slide_plan.json.source_card_ids`.
- WeChat article requests use `wechat-source-intake.md`: treat generic URL conversion as a baseline, and do not plan image-backed slides from empty image placeholders.
- NotebookLM/Anything-to-NotebookLM analysis may be used as an optional source analysis layer, but its output must be saved into source notes/cards before slide planning.
- Source cards are the bridge from research to slides; each mainline slide should cite source-card ids.
- If source coverage or images are weak, record the gap and discuss it before style selection.
- QA notes and provenance stay out of visible slide canvases unless the user explicitly asks.

### Phase 2: Design Proposal

Output:

- `design_proposal.md`

It must contain:

- page count
- source research summary, including coverage, gaps, and selected/user-confirmed angle when the deck started from a topic
- audience state change
- story arc
- 3 style candidates
- selected direction
- layout mix with concrete pattern IDs from `layout-pattern-library.md`
- chart/diagram/image plan
- image generation decision
- background rhythm
- font and compatibility plan
- deliverables

Normal user-facing PPT generation stops here for approval.

### Phase 2.5: Four-Slide Preview Gate

Required for any normal deck expected to exceed 7 slides.

Output:

- 4 representative preview slides
- semantic HTML preview for those 4 slides when HTML is part of delivery
- rendered thumbnails/screenshots where possible
- `preview_gate.json`

Default preview slide selection:

- opening/cover or thesis slide
- dense proof/evidence slide
- diagram/process/model slide
- breathing/quote/turning-point/closing slide

`preview_gate.json` should include:

```json
{
  "mode": "four_slide_preview",
  "applies_to_slide_count": 12,
  "selected_slides": ["P01", "P04", "P06", "P11"],
  "outputs": ["preview/preview-4.pptx", "preview/html/index.html"],
  "qa_focus": ["typography", "background rhythm", "connector geometry", "HTML readability"],
  "user_decision": "pending",
  "skipped_by_user": false
}
```

Rules:

- Do not render the remaining slides while `user_decision` is `pending`.
- If the user approves with revisions, update `design_spec.md`, `spec_lock.md`, and relevant policies before full generation.
- If the preview reveals a systemic issue, change the generator/rules, not only the affected page.
- Batch mode or explicit "skip preview" requests must set `skipped_by_user: true` and record the exact instruction.

### Phase 3: Design Spec

Output:

- `design_spec.md`

Recommended sections:

```text
I. Project Information
II. Source Understanding
III. Audience and State Change
IV. Narrative Mode and Story Arc
V. Visual Thesis
VI. Color and Typography
VII. Layout System
VIII. Chart and Diagram Plan
IX. Image and Background Plan
X. Icon and Asset Plan
XI. Slide Outline
XII. Speaker Notes Policy
XIII. Technical Constraints
XIV. Verification Plan
```

Rules:

- This file explains why choices were made.
- It may contain rationale, tradeoffs, and page-by-page intent.
- It is read once before generation and when context is lost.
- It is not the source of exact rendering constants when `spec_lock.md` exists.

### Phase 4: Execution Lock

Output:

- `spec_lock.md`

This file contains exact renderable values and per-page routing. Before authoring each page, re-read it or inspect the relevant section.

Recommended structure:

```text
## canvas
- format: ppt169
- viewBox: 0 0 1280 720
- safe_margin: 60 56 60 56

## mode
- narrative_mode: narrative | pyramid | briefing | instructional | showcase | custom
- mode_behavior: ...

## visual_style
- style_id: ...
- style_behavior: ...

## colors
- bg: #...
- surface: #...
- text: #...
- text_secondary: #...
- primary: #...
- accent: #...
- border: #...

## typography
- title_family: ...
- body_family: ...
- code_family: ...
- body: 22
- title: 40
- subtitle: 28
- annotation: 15

## icons
- library: qm-icon-studio | lucide | none
- style: outline | filled | duotone | mixed-brand-only
- inventory: name, name, name

## backgrounds
- P01: bg_cover_01.png
- P02: bg_light_02.png
- P03: bg_diagram_03.png

## images
- key: path | fit: slice | role: background | source: ai
- key: path | fit: meet | role: evidence | source: url

## page_rhythm
- P01: anchor
- P02: breathing
- P03: dense

## page_layouts
- P01: L01
- P02: L24
- P03: L20

## page_charts
- P03: chart_with_takeaway
- P06: mechanism_loop

## page_components
- P02: concept_map, icon_labels
- P05: source_screenshot_crop, annotation_callouts

## layout_execution_contract
- coordinate_policy: absolute_stage_coordinates
- text_fit_policy: explicit line breaks; no foreignObject; shrink only within declared min/max
- P01:
  - rhythm: anchor
  - proof_object: full-bleed product scene plus three proof chips
  - layout_pattern_id: L04
  - component_type: full_bleed_image_claim
  - reading_path: title -> subtitle -> chips
  - coordinate_slots: hero 0 0 1920 1080; title 120 140 940 220; chips 120 820 1320 120
  - group_ids: hero, title-block, proof-chips, footer
- P03:
  - rhythm: dense
  - proof_object: five-step process
  - layout_pattern_id: L13
  - component_type: numbered_steps
  - reading_path: title -> process banner -> steps
  - coordinate_slots: title 120 90 1260 120; steps 120 560 1680 360
  - group_ids: header, process-banner, step-01, step-02, step-03, step-04, step-05, footer

## forbidden
- visible toolchain footer
- more than 3 active colors per slide
- nested cards
- baked-in background frames
```

Hard rules:

- Colors, font families, icons, image paths, background IDs, and layout IDs must come from `spec_lock.md`.
- If a needed value is missing, update `spec_lock.md` before drawing. Do not silently invent it.
- If `design_spec.md` and `spec_lock.md` conflict, `spec_lock.md` controls rendering.
- If `slide_plan.json` and `layout_execution_contract` conflict, update the contract before drawing. Do not choose a component that does not match the slide's proof object.
- SVG-first pages should create top-level `<g id="...">` groups that match `layout_execution_contract.group_ids`. These groups are the unit for editability, QA, and optional `animations.json`.

## Page Rhythm Vocabulary

Use exactly these default rhythm tags unless the project explicitly defines a custom rhythm:

| Tag | Use | Layout Discipline |
|---|---|---|
| `anchor` | cover, chapter opener, TOC, closing, major turn | strong composition; may use hero type or full-bleed media |
| `dense` | data, comparison, table, process, multi-point explanation | cards, grids, charts, diagrams allowed; must stay readable |
| `breathing` | one idea, quote, big number, decisive contrast, short example | avoid multi-card grids; use whitespace, one visual subject, or one proof object |

Rules:

- A 10+ page deck should not be all `dense` unless it is explicitly a report.
- Consecutive pages may share rhythm, but not the same exact layout and background.
- `breathing` is not filler. It must say something independently useful.

## Layout Mapping

Every page in `slide_plan.json` should include:

```json
{
  "page": "P04",
  "claim_title": "...",
  "rhythm": "dense",
  "layout_pattern": "L20",
  "reading_path": "title -> chart -> takeaway",
  "proof_object": "bar chart of ...",
  "component_plan": ["chart_with_takeaway", "source_note_in_speaker_notes"],
  "background_id": "bg_evidence_04",
  "qa_risk": "chart label density"
}
```

Use `layout-pattern-library.md` for layout IDs. Use `chart-diagram-components.md` for chart and diagram names.

## Visual Asset Manifest

Write `visual_asset_manifest.json` when the deck uses images, generated backgrounds, URL images, screenshots, icons, charts, or diagrams.

Recommended fields:

```json
{
  "asset_id": "bg_cover_01",
  "kind": "background",
  "source": "codex_imagegen | procedural | url | user | chart_renderer | icon_search",
  "path": "assets/backgrounds/bg_cover_01.png",
  "role": "cover_atmosphere",
  "fit": "slice",
  "editable_policy": "background_only",
  "text_policy": "no_text",
  "allowed_pages": ["P01"],
  "notes": "quiet color field, no boxes"
}
```

Image rules:

- `fit: meet` for evidence, screenshots, charts, formula images, certificates, and anything where cropping loses facts.
- `fit: slice` only for atmosphere, hero photography, or texture where cropping is acceptable.
- Background images are atmosphere only. They may not contain text, boxes, cards, chart slots, UI frames, slide panels, or placeholders.
- If an image needs labels, labels are editable foreground objects.

## Image Layout Pattern Contract

For image slides, declare an image composition:

```text
primary: full-bleed image as canvas
modifiers: scrim, native annotation cards, leader lines
foreground: editable labels and metrics
```

Preferred primary structures:

- full-bleed image with floating title
- image-as-canvas with native annotations
- side-by-side comparison
- multi-image small multiples
- image strip / filmstrip
- full-height sidebar image
- negative-space small image
- zoom-callout using the same source image twice

Preferred modifiers:

- gradient scrim for legibility
- subtle tint to match palette
- rounded image crop
- thin matte frame
- native annotation cards
- leader lines
- spotlight / lens rectangle
- bottom or side fade into background

Avoid:

- fixed 50/50 image-text split for every image slide
- text baked into generated images
- source screenshots cropped so facts disappear
- meaningless decorative frames around every image

## Chart and Diagram Contract

Every chart/diagram page must identify:

- data or concept source
- chart/diagram type
- why this form is appropriate
- source spec path under `<project>/charts/` or `<project>/diagrams/`
- rendered asset path when applicable
- editability expectation
- QA risk

For charts:

- Include a chart spec even if rendered as SVG/PNG.
- If coordinates matter, store plot area metadata or source dimensions for verification.
- Never ask a generated background image to contain a real chart.

For concept diagrams:

- Prefer semantic shape names: mechanism loop, tension pair, pyramid, matrix, funnel, timeline, flywheel, cause-effect, decision tree, architecture map.
- Do not reduce every concept to three cards.
- Every connector-based diagram must define node geometry and connector ports. Draw connector lines from perimeter to perimeter or render them behind opaque nodes; never draw center-to-center lines through node text.
- Keep connector stroke quiet: 0.75-1.25 pt in PPTX or 1-2 px in HTML/SVG, muted color, no heavy shadow.

## Typography and Editing Contract

- The primary title remains visually dominant unless the page is deliberately number-led, quote-led, or image-led.
- Body size is the baseline; title, subtitle, annotation, chart label, and hero sizes derive from it.
- Keep logical inline emphasis in the same text object when the target route supports it.
- Use semantic groups for editable foreground objects: title group, chart group, card group, diagram node group, footer group.
- Do not split one sentence into many independent positioned text fragments unless exact graphic typography is intended.

## Generation Discipline

- Generate pages sequentially after the lock is written.
- Before each page, use only the current page's entries from `slide_plan.json` and `spec_lock.md`.
- Do not let the last generated page dictate the next page's layout.
- If context is compacted or a long pause occurs, re-read `design_spec.md`, `spec_lock.md`, and the current page entry before continuing.
- For substantial decks, create and inspect a thumbnail grid before export.

## Gate Checklist

Before export, verify:

- `design_proposal.md` exists or the user explicitly skipped it.
- `design_spec.md` exists.
- `spec_lock.md` exists and includes page rhythm, layouts, backgrounds, typography, colors.
- `slide_plan.json` pages match the generated pages.
- No exact background repeats on adjacent pages.
- No slide uses more than three active colors unless source images require it.
- No slide uses unsupported background structure baked into an image.
- No hollow generic copy remains.
- No visible internal tooling/provenance metadata appears.
- HTML output, when requested, is semantic, not a screenshot wrapper.
- PPTX output, when requested, has the best available editability path and is opened/tested where possible.
