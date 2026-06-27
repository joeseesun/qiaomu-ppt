# PPT Master Research Notes

This document records what Qiaomu PPT learned from the local study of `hugohe3/ppt-master`. It is an adaptation map. The upstream skill is not a runtime dependency; selected MIT-licensed SVG/PPTX infrastructure may be vendored with attribution in `NOTICE.md`.

Upstream studied locally at:

```text
/Users/joe/Documents/Qiaomu PPT Skill/research/ppt-master
```

Latest refresh for this learning note also inspected a fresh sparse shallow
clone at `/tmp/ppt-master-latest-study` on 2026-06-25, remote `main` at
`850ad1b`, with the public README reporting `v2.11.0`. The online gallery
manifest reported 21 examples, 280 pages, and 21 templates in the prior catalog
refresh. Local example statistics from that clone found 260 image files across the 280 pages
(about 0.93 image files per slide), with image-rich cases such as
`ppt169_liziqi_plant_dye_colors` (12 slides / 32 images),
`ppt169_pritzker_2026` (11 slides / 25 images), and
`ppt169_fashion_weekly_digest` (16 slides / 23 images). Treat these numbers as
learning signals, not a requirement to copy upstream assets.

Primary files inspected:

- `README.md`, `README_CN.md`
- `skills/ppt-master/SKILL.md`
- `skills/ppt-master/scripts/README.md`
- `docs/technical-design.md`
- `docs/templates-architecture.md`
- `skills/ppt-master/templates/design_spec_reference.md`
- `skills/ppt-master/templates/spec_lock_reference.md`
- `skills/ppt-master/references/strategist.md`
- `skills/ppt-master/references/executor-base.md`
- `skills/ppt-master/references/shared-standards.md`
- `skills/ppt-master/references/image-layout-patterns.md`
- `skills/ppt-master/references/image-layout-spec.md`
- `skills/ppt-master/references/modes/*`
- `skills/ppt-master/references/visual-styles/*`
- `skills/ppt-master/references/image-renderings/*`
- `skills/ppt-master/references/image-palettes/*`
- `skills/ppt-master/references/image-type-templates/*`
- `skills/ppt-master/references/image-generator.md`
- `skills/ppt-master/references/image-base.md`
- `skills/ppt-master/references/visual-review.md`
- `examples/*/design_spec.md`
- `examples/*/spec_lock.md`

## 2026-06-25 Correction: The Essence Is the Axis System

The earlier Qiaomu absorption was directionally useful but incomplete. It
learned the visible nouns: editorial examples, source images, visual rhythm,
style execution audits, and benchmark categories. It did not sufficiently
enforce the upstream mechanism that makes those examples cohere.

The current upstream code splits the design decision into independent catalogs:

- `mode`: narrative or persuasion skeleton.
- `visual_style`: deck layout aesthetic.
- `image_rendering`: deck-wide generated-image look.
- `image_palette`: behavior for how the deck colors are distributed in images.
- `image_type_templates`: per-image local infographic geometry; hero-page
  images instead use composition primitives.

Qiaomu now records this as `data/ppt_master_axis_catalog.json` and audits it via
`scripts/ppt_master_axis_audit.py`. The audit is intentionally about execution
artifacts, not style prose: it checks that the axes exist in project contracts,
that image rows carry page role and text policy, that local AI images declare a
type while hero images declare a primitive, that image-rich subjects have
inspectable source/user/web/formula primary-media rows, and that page rhythm and
layout locks exist before rendering.

The practical consequence: a deck may be beautiful without `ppt-master` labels,
but a deck should not claim `ppt_master_grade` if it only says "magazine style",
uses generic AI backgrounds, or lacks real primary media for an image-rich
subject. More images are not enough; the axes must be locked and then executed.

## 2026-06-27 Case Refresh: Sugar Rush + Indie Bookstore

This refresh inspected the live viewer URLs for:

- `ppt169_sugar_rush_memphis`
- `ppt169_indie_bookstore_zine_guide`

The viewer itself is only a static gallery shell. It reads
`examples/examples.json` and displays `examples/<folder>/svg_final/*.svg` through
SVG `<object>` embeds. The interesting generation evidence lives in each example
folder:

```text
README.md
design_spec.md
spec_lock.md
animations.json
notes/total.md + per-page notes
images/image_prompts.json + image_prompts.md
svg_output/
svg_final/
exports/*.pptx
```

The direct lesson for Qiaomu is that `ppt-master` quality is a bundle of sidecar
contracts, not a single renderer. `svg_output` is the authored SVG source;
`svg_final` is the post-processed preview source with image/icon expansion; the
PPTX export is the editable delivery artifact; notes and animation manifests are
separate delivery layers.

### Sugar Rush Memphis

Observed shape:

- 14-slide fictional festival guide.
- Style: Memphis / Pop.
- Deck image lock: `flat` rendering + `vivid-launch` palette behavior.
- 9 generated images: 6 hero-page assets and 3 local assets.
- Components: KPI cards, vertical pillars, icon grid, quadrant bullets,
  hub-spoke stage map, timeline schedule, comparison columns.
- Rhythm: anchor cover/closing, dense guide pages, breathing chapter pages.

Transfer:

- Event and youth-brand decks need real guide objects: schedule, map, ticket
  tiers, lineup, zones, market/installations, not only a poster skin.
- Bright palettes require a per-page active-color budget and thumbnail review;
  the case is energetic, but some dense pages show how quickly edge cropping and
  small text can creep in.
- Memphis motifs should be controlled accents with thick editable foreground
  geometry; generated images should carry atmosphere and scene only.

### Indie Bookstore Zine Guide

Observed shape:

- 18-slide culture/guide deck.
- Style: Risograph Zine.
- Deck image lock: `screen-print` rendering + `duotone` palette behavior.
- 10 generated images: print studio, object portrait, process banner, folding
  hands, bookstore/place scenes, fair scene, outro.
- Components: agenda list, timeline, vertical list, numbered steps, icon grid,
  vertical pillars, basic table, labeled cards.
- Hard visual constraints: duotone, paper grain, halftone, 1-3px
  misregistration, hard edges, no rounded cards.

Transfer:

- A "style" becomes reliable only when it is translated into mechanical
  constraints and forbidden moves. For zine/print styles, gradients, soft glass,
  rounded cards, and generic digital polish should be blocked unless the user
  explicitly asks for a hybrid.
- Dense guide decks can still feel designed when every page keeps a stable
  chrome rhythm: header band, component area, footer/source line, and recurring
  source/credit discipline.
- A sources/credits slide and long-form speaker notes are part of the trust
  system, especially for culture or place-based guides.

### New Qiaomu Absorption From This Refresh

- `ppt_master_axis_audit.py` should not only check the five axes. It should also
  check AI-image prompt sidecars, prompt-level composition/safe-area/foreground
  boundaries, component selection rationale, and presentation sidecars when a
  deck claims `ppt_master_grade`.
- `visual_asset_manifest.json` plus `assets/images/image_prompts.json|md` are
  a contract pair. The manifest says what assets exist and where they are used;
  the prompt sidecar says how each AI image is generated without baking slide
  claims, labels, charts, or source text into pixels.
- Component selection should record rejected alternatives when there is a
  likely wrong-but-plausible choice, such as using numbered steps for a fixed
  date timeline or using a dense table where marketing tier cards are clearer.
- For presentation-ready decks, `notes/total.md` and `animations.json` should be
  treated as first-class optional-to-required artifacts depending on the route.
  They prove spoken delivery and object groups were planned separately from the
  static visual.

## References Directory Absorption Map

The `skills/ppt-master/references` directory is valuable because it is not a
gallery. It is a vocabulary system for turning content into executable slide
objects. Qiaomu absorbs the useful ideas this way:

| Upstream Reference Area | Useful Idea | Qiaomu Absorption |
|---|---|---|
| `modes/*` | Mode is the argument or teaching skeleton, not the visual skin. | `reference-system.md`, `content_contract.structure_framework`, `spec_lock.narrative_mode` |
| `visual-styles/*` | Style controls shape, texture, spacing, type behavior, and decoration. Palette is separate. | `visual-systems.md`, `style_brief.md`, `visual_contract.json` |
| `image-renderings/*` | Image rendering should be deck-wide when images need unity. | `visual_asset_manifest.image_generation_model.rendering` |
| `image-palettes/*` | Palette behavior is distinct from HEX tokens. | `image_generation_model.palette_behavior`, `color_budget` |
| `image-type-templates/*` | Local infographic images need their own geometry skeleton. Hero images do not. | `image_generation_model.type_template`, `text_policy` |
| `image-layout-patterns.md` | Image is atmosphere/context; native SVG carries editable information. | `reference-system.md`, `content-layout-execution.md`, `plan_image_layouts.py` |
| `image-layout-spec.md` | Source image aspect ratio should drive initial image/text slot geometry. | `scripts/plan_image_layouts.py` |
| `shared-standards.md` | PPT-safe SVG is a strict subset with XML-safe text, inline attributes, and semantic groups. | `svg-pptx-compatibility.md`, `check_project.py` SVG checks |
| `executor-base.md` | Spec lock is reread per page; page rhythm and page component maps prevent drift. | `model-driven-generation.md`, `production-contract.md` |
| `visual-review.md` | Review has static checks first, then hard defects and soft quality defects. | `quality-gates.md`, `check_project.py` |

The important adoption boundary: Qiaomu keeps the taxonomy and, where useful,
license-compatible infrastructure code, but not the upstream skill dependency.
Generated projects should cite Qiaomu artifacts and scripts, not upstream command
paths or skill names.

## What Makes PPT Master Strong

### 1. The Pipeline Is a Contract, Not a Suggestion

PPT Master makes presentation generation a serial pipeline:

```text
source -> project -> optional template -> strategy/spec -> image acquisition
       -> page execution -> quality gate -> notes -> post-process/export
```

The important lesson is not the exact toolchain. The lesson is that each phase emits a bounded artifact that becomes the next phase's input. This prevents the model from mixing planning, design, asset collection, SVG authoring, notes, and export into one vague pass.

Qiaomu adoption:

- Keep `PPT Design Proposal` as the only normal blocking user gate.
- After approval, write persistent `design_spec.md` and `spec_lock.md`.
- Treat output contracts as source of truth, not chat memory.
- Stop speculative SVG/HTML/PPTX authoring before the plan/spec is locked.

### 2. Two Specs: Human Narrative and Machine Lock

PPT Master separates:

- `design_spec.md`: human-readable rationale, audience, style objective, page outline, resource plan.
- `spec_lock.md`: machine-readable exact values for execution: canvas, colors, typography, icons, images, page rhythm, page layouts, page charts.

This is the strongest anti-drift idea in the project. Long decks drift because the model "remembers" palettes, fonts, layouts, and image usage imprecisely. A small execution lock can be re-read per page.

Qiaomu adoption:

- `design_spec.md` becomes the complete story/design plan.
- `spec_lock.md` becomes the only allowed source for exact colors, font stacks, layout pattern IDs, background IDs, image paths, chart choices, icon inventory, and per-slide rhythm.
- When `design_spec.md` and `spec_lock.md` disagree, `spec_lock.md` wins for rendering.

### 3. Page Rhythm Prevents the "Everything Is Cards" Failure

PPT Master uses a small rhythm vocabulary:

- `anchor`: structural slides such as cover, chapter, TOC, closing.
- `dense`: information-heavy slides with charts, tables, comparisons, KPI blocks, or multi-column content.
- `breathing`: low-density slides where one idea lands with space.

This is more actionable than "make layouts varied." It tells the executor when cards are allowed and when they are a defect.

Qiaomu adoption:

- Every slide in `spec_lock.md` must have `page_rhythm`.
- Decks over 8 pages must include at least three rhythm roles unless the content is intentionally all-report.
- `breathing` pages must not be multi-card grids.

### 4. Page Layouts and Page Charts Are Per-Slide Truth

PPT Master avoids global template guessing by declaring per-page mappings:

```text
page_layouts:
  P01: cover template or free design
  P04: content-image-text

page_charts:
  P05: grouped-bar
  P09: timeline
```

Qiaomu adoption:

- `page_layouts` should point to our `layout-pattern-library.md` IDs, not upstream template files.
- `page_charts` should point to our chart/diagram component vocabulary.
- Empty entries are valid design decisions. Do not force a layout or chart on every page.

### 5. Templates Are Reference Bundles with Segment Ownership

PPT Master distinguishes three template kinds:

- Brand: identity only, such as color, typography, logo, tone, icon style.
- Layout: structure only, such as canvas, page types, and page skeletons.
- Deck: identity plus structure plus overall intent.

The segment model matters more than the implementation. It prevents "style soup" where a brand color, an unrelated layout, and a full-deck template fight each other.

Qiaomu adoption:

- Treat any future templates as `identity`, `structure`, and `middle/intent` segments.
- Segment override happens whole-segment first; field-level tweaks must be explicit.
- Do not auto-match a template by name unless the user explicitly asks for that template.

### 6. Image Generation Needs a Deck-Wide Lock

PPT Master locks AI image direction along three dimensions:

- rendering style family
- palette behavior
- per-image type/composition

This avoids the common problem where each generated image looks like it came from a different project.

Qiaomu adoption:

- When using built-in image generation, choose one deck-wide `image_rendering` and `image_palette_behavior`.
- Create `visual_asset_manifest.json` and `assets/images/image_prompts.json` before rendering. The manifest records `acquire_via`, status, prompt/source, file evidence, page role, text policy, rights/provenance, and QA notes; the prompt sidecar is the actual work queue for Codex or another image backend.
- Each generated image gets an `asset_role`: `background`, `chapter_art`, `scenario`, `concept_metaphor`, `texture`, `moodboard`, or `object_cutaway`. Evidence roles such as paper figures, screenshots, product UI, charts, and tables must come from `source`, `web`, `user`, or `formula` routes.
- Editable slide information stays in foreground objects; generated images must not bake in text, chart values, UI chrome, cards, or layout frames.

### 7. Image Layout Has Primary Structures and Modifier Layers

The most useful idea in the image layout registry is the two-layer split:

- Primary structure: where the image sits and what role it plays.
- Modifier layer: clipping, scrim, annotation, glow, texture, montage, frame, zoom, or overlay treatment.

The key warning: a bare left/right image split with no modifier is often the AI-default look.

Qiaomu adoption:

- For image slides, declare an `image_layout_pattern` with at least one primary structure.
- Add one or more modifier layers when they earn their place.
- Use image-as-canvas with editable SVG/HTML/PPT foreground overlays for annotations, charts, networks, and labels.
- For side-by-side source/user/web images, calculate `image_area` and `text_area` from the source image's original aspect ratio and target canvas format. Do not default to 50:50 or crop evidence images to fit a decorative rectangle. In Qiaomu, use `scripts/plan_image_layouts.py` plus `data/canvas_format_specs.json` and record the result in `image_layout_plan.json/md`, `visual_contract.json`, or `spec_lock.json`.

### 8. SVG/PPTX Compatibility Must Be a Design Constraint

PPT Master treats SVG as the editable intermediate format, then converts it to native PowerPoint objects. The exact converter is upstream-specific, but the authoring constraints are reusable:

- Inline presentation attributes are safer than CSS classes.
- Text should be XML-safe.
- RGBA is risky; use HEX plus opacity attributes.
- Logical groups should be named for editability and animation anchors.
- Charts need explicit plot-area metadata when geometry must be checked.

Qiaomu adoption:

- Keep a PPT-safe SVG subset in `quality-gates.md`.
- Prefer grouped semantic objects over raw ungrouped primitives.
- Chart pages must include enough geometry metadata or source spec for coordinate checks.

### 9. Quality Gate Must Run Before Post-Processing

The important point is placement: check authored artifacts before any clean-up step hides the original mistake.

Qiaomu adoption:

- Run project checks against source authored SVG/HTML/page previews first.
- Errors block export; warnings are reported and fixed when straightforward.
- If a slide violates the lock, regenerate or edit the slide in context, not by blind global patching.

### 10. Editable Output Is the Product Thesis

PPT Master's central product claim is that a real PPT should remain editable. That stance matches Qiaomu PPT's direction.

Qiaomu adoption:

- PPTX route prioritizes editable text, shapes, charts, icons, and notes.
- HTML route must be semantic DOM/SVG/Canvas, not screenshot pages.
- Pixel-perfect screenshot PPTX/HTML is allowed only as a preview or backup artifact.

## Case Gallery Absorption

The `examples/` directory is worth studying because the good case decks are not
only visual skins. They combine:

- a deck-wide `image_rendering` and `image_palette`
- a declared `page_rhythm` sequence
- per-slide `page_charts`
- explicit image inventories
- icon library constraints
- a small set of forbidden SVG/PPTX constructs

Qiaomu absorbs the repeatable grammar into two local data files:

- `data/ppt_master_case_styles.json`: searchable style abstractions for
  recommendation and spec-lock decisions.
- `data/ppt_master_examples_catalog.json`: full 21-case learning index with
  slide counts, local image counts, learning materials, page rhythm, page
  charts, notes, and final SVG/PPTX paths.

| Upstream Case | Absorbed Qiaomu Style | Key Transfer |
|---|---|---|
| `ppt169_attention_is_all_you_need` | `pptmaster-case-academic-blueprint` | Paper figures, formulas, tables, source diagrams, blueprint palette, no-crop evidence. |
| `ppt169_global_ai_capital_2026` | `pptmaster-case-data-journalism` | Bloomberg/Economist density, chart variety, source captions, dark editorial finance palette. |
| `ppt169_pritzker_2026` | `pptmaster-case-architecture-editorial` | Image-led architecture/culture storytelling with museum-catalog captions. |
| `ppt169_swiss_grid_systems` | `pptmaster-case-swiss-grid` | Modular grid, strict typography, red signal accent, functional rules. |
| `ppt169_glassmorphism_demo` | `pptmaster-case-glassmorphism-saas` | Product screenshot story, frosted depth, AI-agent workflow and KPI panels. |
| `ppt169_sugar_rush_memphis` | `pptmaster-case-memphis-pop` | Vivid flat event energy, geometric accents, schedule and guide components. |
| `ppt169_indie_bookstore_zine_guide` | `pptmaster-case-risograph-zine` | Screen-print duotone images, hard edges, collage rhythm, guide-like tables and lists. |
| `ppt169_brutalist_ai_newspaper_2026` | `pptmaster-case-brutalist-newspaper` | Newspaper columns, mono-ink texture, red signal, source clips and investigation pacing. |
| `ppt169_kubernetes_blueprint_2026` / `ppt169_building_effective_agents` / `ppt169_general_dark_tech_claude_code_auto_mode` | `pptmaster-case-engineering-blueprint` | Developer/infrastructure diagrams, process flows, client-server maps, dark technical evidence. |
| `ppt169_kimsoong_loyalty_programme` | `pptmaster-case-top-consulting` | Consulting logic, issue framing, customer profile, root cause, pillars, initiatives, roadmap. |
| `ppt169_fashion_weekly_digest` / `ppt169_home_design_trends_2026` | `pptmaster-case-luxury-editorial-digest` | Image-rich premium editorial pacing, product/lifestyle photography, trend digest grids. |
| `ppt169_liziqi_plant_dye_colors` / `ppt169_cangzhuo` | `pptmaster-case-eastern-culture-narrative` | Chinese cultural color tokens, craft/process imagery, ink-paper surfaces, poetic object narration. |
| `ppt169_image_text_showcase` | `pptmaster-case-image-text-showcase` | Image/text layout vocabulary, safe text areas, crop focal points, collage and poster compositions. |
| `ppt169_high_rise_renewal` / `ppt169_lin_huiyin_architect*` | `pptmaster-case-urban-renewal-editorial` | Architecture humanities, before/after evidence, museum pacing, biography and place-based timelines. |

The catalog can be refreshed from a local research snapshot:

```bash
python3 qiaomu-ppt/scripts/build_ppt_master_catalog.py \
  research/ppt-master/examples \
  --output qiaomu-ppt/data/ppt_master_examples_catalog.json
```

### The Asset Lesson

These examples feel alive because the slide plan knows what visual evidence each
page needs before rendering. For Qiaomu PPT, every selected case style should
force an asset decision:

```json
{
  "case_style": "pptmaster-case-data-journalism",
  "image_rendering": "editorial",
  "image_palette_behavior": "dark-cinematic",
  "asset_density": "low-image-high-chart",
  "page_rhythm": {
    "P01": "anchor",
    "P02": "breathing",
    "P03": "dense"
  },
  "page_charts": {
    "P04": "kpi_cards",
    "P05": "bar_chart"
  }
}
```

If a user asks for a deck on a broad topic and the source intake has no images,
charts, figures, tables, screenshots, maps, or diagrams, do not pick a
high-image case style by wishful thinking. First fetch more source material,
request user assets, choose rights-clear public images, generate
atmosphere-only concept art, or move to a typography/diagram-led style.

The 2026-06-25 refresh sharpened this lesson: background images are not the same
as primary media. A music, culture, architecture, fashion, biography, product,
or brand deck needs inspectable objects such as an album cover, artist/product
photo, place photo, source screenshot, figure, chart, or document/page image.
Generated atmosphere can make the page beautiful, but it should not be the only
visual layer on every slide. Qiaomu's benchmark therefore tracks
`primary_media_evidence` separately from generic image presence.

### The Chart Lesson

The case decks avoid the "same three cards every page" failure by varying proof
objects. Qiaomu should plan chart/component diversity before rendering:

- report decks: KPI, bar, dumbbell, bubble, Sankey, Pareto, quadrant, table
- paper decks: formula focus, source figure, comparison table, architecture map
- guide decks: agenda, timeline, steps, icon grid, map, labeled cards
- culture decks: photo essay, caption grid, timeline, quote, location map

Every chart or visual component needs a source or a declared draft assumption.
Decorative pseudo-charts fail the source gate.

## What We Do Not Adopt

- We do not call `ppt-master` scripts at runtime.
- We do not copy upstream template files, icon packs, chart templates, exact prompt text, or slide designs into generated projects.
- MIT-licensed infrastructure code that materially improves export fidelity may be vendored with attribution and local adaptation.
- We do not inherit the "SVG must be hand-written and never script-generated" rule literally for all routes. Qiaomu may use code generation when it improves consistency, but must still run visual and structural gates. In `ppt_master_grade` mode, however, the four representative preview pages must be authored or revised page-by-page from the lock instead of emitted by a generic batch renderer.
- We do not require the same Confirm UI implementation. Qiaomu uses a chat proposal gate unless a local UI is explicitly built.

## Qiaomu-Specific Synthesis

The core Qiaomu model is:

```text
route_card
  -> source_manifest
  -> design_proposal
  -> design_spec
  -> spec_lock
  -> visual_asset_manifest
  -> slide_plan
  -> authored pages
  -> checks
  -> PPTX + semantic HTML + reports
```

Every page should answer:

```text
What is the claim?
What proof object supports it?
What rhythm role does it play?
Which layout pattern ID does it use?
Which chart/diagram/image/component assets are allowed?
Which exact colors/fonts/icons/backgrounds may appear?
What must be editable in the final artifact?
```
