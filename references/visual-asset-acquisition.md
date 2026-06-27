# Visual Asset Acquisition

This reference defines how Qiaomu PPT uses image generation and image sourcing
as a controlled asset pipeline. It absorbs the useful methodology from
`ppt-master` without depending on upstream scripts or copying upstream prompts.

The thesis is simple: do not generate finished slides with baked-in text.
Generate full-slide or main-region Codex/AI visuals under a locked deck spec,
then keep titles, body text, captions, charts, tables, citations, labels,
callouts, and reading-path objects editable in PPT/HTML foreground.

## Core Model

Every substantial visual asset goes through a row in `visual_asset_manifest.json`.

```text
design_proposal
  -> design_spec/spec_lock
  -> visual_asset_manifest
  -> assets/images/image_prompts.json      # ai rows
  -> assets/images/image_sources.json      # web rows
  -> generated/sourced/user/source/formula files
  -> visual_contract image slots
  -> SVG/PPTX/HTML executor consumes files only
```

The executor does not decide where images come from. It consumes already
declared assets and applies image slots, crop policy, attribution policy, and
editable foreground overlays.

## Acquire Via

| acquire_via | Initial Status | Terminal Statuses | Use For |
|---|---|---|---|
| `ai` | `Pending` | `Generated`, `Needs-Manual`, `Missing`, `Failed` | full-slide main visual, main-region visual, atmosphere, chapter art, concept metaphor, scenario illustration, object cutaway, texture |
| `web` | `Pending` | `Sourced`, `Needs-Manual`, `Missing`, `Failed` | rights-clear photo, place, historical image, public educational image |
| `user` | `Existing` | `Existing`, `Needs-Manual`, `Missing` | user-owned brand/product/team/private assets |
| `source` | `Existing` | `Existing`, `Needs-Manual`, `Missing` | extracted paper figures, PDF charts, WeChat images, article images |
| `formula` | `Rendered` | `Rendered`, `Needs-Manual`, `Missing` | equations and math assets |
| `placeholder` | `Placeholder` | `Placeholder`, `Needs-Manual`, `Missing` | planning-only or assets awaiting user approval |

`Needs-Manual` is a valid terminal state. It means the project can continue
with an explicit gap, but completion reports must tell the user exactly which
file is missing and where to place it.

## Source Image Quality Gate

Do not promote every extracted image candidate into the deck. URL extractors
often collect site chrome before content images. Reject or heavily demote:

- site icons, wordmarks, taglines, footer logos, edit buttons, lock icons, audio
  icons, tracking pixels, and other UI chrome
- tiny `20px` / `40px` / `1x1` images unless the deck is explicitly about that
  UI element
- generic wiki/project logos and non-topic flags
- downloaded files whose URL/alt/role indicates navigation rather than evidence

Prefer candidates with a local `sources/images/...` path, real raster extension,
large enough dimensions, topic terms in title/alt/URL, and source provenance.
If the only usable candidate is a remote URL, keep a `source` row with
`Needs-Manual` provenance, then run `scripts/resolve_source_visuals.py` after
`visual_asset_manifest.py init`. The resolver downloads only the remote source
images already selected for slide use, writes them under
`sources/images/resolved-source-visuals/`, and backfills
`source_cards.json`, `source_manifest.json`, `visual_asset_rows.json`, and
`visual_asset_manifest.json`. This is intentionally narrower than full
`--download-images`: it avoids slow whole-page image harvesting and reduces UI
chrome pollution. If the selected source image still cannot be resolved, add or
keep an AI fallback row for the same slide. The AI fallback must be described as
atmosphere/concept only; it must not fake the source page, figure, screenshot,
chart, citation, or logo.

## Required Manifest

Create `<project>/visual_asset_manifest.json` for image-rich, source-rich,
brand, teaching, paper, and long decks.

Required top-level fields:

- `schema_version`
- `generated_at`
- `project`
- `subject`
- `route`
- `deck_image_model`
- `status_summary`
- `items`

Required `deck_image_model` fields:

- `image_rendering`: deck-wide image style family.
- `image_palette_behavior`: deck-wide color-use behavior.
- `color_scheme`: primary, secondary/background, accent.
- `generation_paths`: Path A/B/C policy.

Required `items[]` fields:

- `asset_id`
- `filename`
- `path`
- `slide_no` or `allowed_pages`
- `purpose`
- `asset_role`
- `acquire_via`
- `status`
- `reference`
- `page_role`
- `text_policy`
- `aspect_ratio`
- `editable_policy`

Recommended content-link fields for every `acquire_via: ai` row:

- `content_link`: the exact slide claim, proof focus, or audience state change
  the image supports.
- `background_duty`: what the bitmap should do for the slide, such as
  establish scene, provide material depth, make an abstraction tangible,
  create a transition mood, or support contrast behind editable evidence.
- `semantic_anchor`: concrete nouns from the slide/source that should guide the
  image: object, place, material, scene, era, mechanism, or metaphor.
- `layout_pattern_id`: the selected `Lxx` proof structure from
  `layout-pattern-library.md`.
- `image_text_pattern_id`: the selected `ITLxx` composition from
  `image-text-layout-patterns.md` when the generated image shares the slide
  with editable text, labels, screenshots, charts, source evidence, or callouts.
- `composition_role`: how the generated bitmap serves that layout, such as
  full-bleed canvas, main-region proof visual, negative-space hero, central
  object, before/after half, filmstrip cell, or contextual image beside data.
- `foreground_text_zones`: exact safe areas reserved for editable foreground
  title, body, labels, source notes, captions, callouts, or chart overlays.
- `integration_move`: how the generated bitmap and editable foreground will be
  fused, such as real copy space, local scrim, image-as-canvas annotations,
  edge fade, detail zoom, object-adjacent labels, or comparison structure.
- `annotation_targets`: concrete image regions or objects that foreground
  labels, chips, arrows, and callouts explain.
- `text_surface_policy`: how foreground text remains readable on or near the
  image: true copy-space, baked gradient/scrim, local matte, separate proof
  zone, caption outside image, or speaker-notes-only.
- `readability_floor`: phone/thumbnail expectations for title, claim, body,
  label, and source text; sentence-level text must use high-contrast neutral
  color on a quiet surface.
- `thumbnail_rhythm_role`: how the slide should read in the deck thumbnail
  grid, such as anchor opener, dense evidence, diagram turn, breathing page, or
  closing echo.

These fields prevent AI images from becoming generic decoration. If they are
missing, `image_art_direction.py` should infer them from `slide_plan.json`, but
final-quality decks should review and edit them before generation.

For `acquire_via: ai`, also include:

- `prompt`
- `image_size`
- `visual_type` when `page_role: local`
- `hero_primitive` when `page_role: hero_page`

For `acquire_via: web`, also include or link:

- `search_intent`
- `license_tier`
- `attribution_required`
- `attribution_text`
- `source_page_url`

## Deck-Wide AI Image Lock

Before writing prompts, lock:

- `image_rendering`: how the image is drawn.
- `image_palette_behavior`: how deck colors behave inside generated images.
- `color_scheme`: the exact HEX values from the style/spec lock.

This prevents the common failure where each generated image looks like a
different project. If using a case style, copy its image asset strategy into the
lock. If the style is custom, write custom prose for rendering and palette
behavior instead of using vague labels.

Good examples of deck-wide locks:

```json
{
  "image_rendering": "screen-print",
  "image_palette_behavior": "duotone",
  "color_scheme": {
    "primary": "#1E4DBC",
    "secondary": "#F5EFE0",
    "accent": "#FF5C8A"
  }
}
```

```json
{
  "image_rendering": "blueprint",
  "image_palette_behavior": "cool-corporate",
  "color_scheme": {
    "primary": "#1E3A5F",
    "secondary": "#F8F9FA",
    "accent": "#D4AF37"
  }
}
```

## Page Role

`page_role` is different from `asset_role`.

| page_role | Meaning | Prompt Consequence |
|---|---|---|
| `full_slide_main_visual` | Image carries the slide's visual quality and subject matter across the full canvas while editable text sits above it | Reserve explicit negative space or a calm overlay area; include no readable text, labels, charts, UI, cards, frames, or fake evidence. |
| `hero_page` | Image is the page's main visual voice: cover, chapter divider, transition, closing, large concept image | It may reserve calm space for editable SVG/PPT overlay only when the slide actually overlays text. |
| `local` | Image sits inside a declared region on the slide: proof image, side image, screenshot, object, context block | It should fill its own slot. Do not reserve arbitrary overlay space inside it. |

## Text Policy

AI image text belongs to Layer 1. Editable slide text belongs to Layer 2.

| text_policy | Use |
|---|---|
| `none` | The generated image must contain no letters, numbers, labels, signs, captions, watermarks, or visible written symbols. |
| `embedded` | Stable visual lettering or image-internal identifiers are part of the artwork. |

Use `embedded` only when the text is stable and genuinely visual: a designed
word/number, schematic node name, panel marker, axis label, scale bar, or unit
symbol. Page titles, body copy, citations, quote text, data values, source
labels, and anything likely to be edited stay in SVG/PPT/HTML foreground.

## Codex Visual + Editable Text Default

When Codex/host-native image generation is available and the user has not
forbidden it, Qiaomu PPT's default visual method is:

1. Select the slide's `Lxx` proof layout and `ITLxx` image-text layout before
   writing the prompt. The image prompt inherits this contract; it is not a
   freeform decorative background.
2. Generate a Codex/AI bitmap as the full-slide or main-region visual layer.
3. Keep title, introduction text, conclusion, labels, callouts, source notes,
   chart values, and the speaker's reading path as native editable foreground.
4. Use simple foreground shapes only for legibility panels, scrims, small
   badges, arrows, source evidence frames, and layout control.
5. Do not hand-draw complex skeletons, people, products, scenes, maps, or
   conceptual illustrations with SVG/shapes as the primary visual finish.
6. If SVG/shape-only output looks rough, regenerate or replace the Codex visual
   instead of polishing the SVG drawing, unless the user explicitly asks for a
   diagrammatic SVG style.
7. If the thumbnail grid feels monotonous, change the layout/image-text pattern
   and regenerate or recompose the visual. Do not treat repeated left-text /
   right-image slides as a design system.
8. If the slide needs a large opaque text rail, bottom chip bar, or floating
   labels with no target to become readable, the image-text plan has failed.
   Repair the `ITLxx`, `integration_move`, crop, or prompt before rendering.
9. If foreground text becomes hard to read on the generated image, repair the
   `text_surface_policy` before changing decorative style: use true copy-space,
   baked gradient/scrim, a local matte, shorter copy, neutral high-contrast text,
   or move low-priority text to speaker notes.

Full-slide bitmaps are allowed as the visual layer. They become unacceptable
only when the visible slide text, conclusion, labels, charts, or citations are
baked into the bitmap, or when `pptx_text_check.py` reports the deck as
image-backed with too little native foreground text.

## AI Prompt Contract

Prompts are coherent visual paragraphs, not tag lists.

Paragraph order:

1. Rendering style.
2. Palette behavior applied to the deck HEX values.
3. Selected `layout_pattern_id` and, when media matters, `image_text_pattern_id`.
4. Slide claim/proof/audience-state `content_link`.
5. `background_duty`, `semantic_anchor`, `composition_role`, and
   `thumbnail_rhythm_role`.
6. Focal subject position, negative space, crop policy, and
   `foreground_text_zones`.
7. Specific subject using concrete nouns.
8. Container note: size, aspect ratio, page role, and overlay reservation only
   when actually needed.
9. Hard rules.

Routine prompts can be 150-300 words. Domain-accurate prompts for scientific,
engineering, medical, legal, academic, or regulated visuals may be 500-1000+
words when needed. Do not shorten a technical prompt merely to look neat.

Forbidden:

- tag-soup such as `modern, clean, professional, high quality, 4K`
- visible HEX codes or color names inside the image
- brand names, logos, trademarks, or real product likenesses unless the user
  owns/provides them
- fake screenshots, fake charts, fake evidence, fake paper figures
- baked-in slide title, navigation, footer, body bullets, citations, long quote,
  or conclusion callout
- random decorative linework, grids, glowing rails, polygons, blobs, or
  "futuristic" geometry that is not tied to the slide claim or a real foreground
  diagram/chart function
- mixed image renderings/palettes within one deck unless the deck is explicitly
  a style showcase

## Hero Primitives

Use these for `page_role: hero_page`:

- `single_subject`: one dominant object, product, symbol, or concept.
- `portrait`: one person or symbolic portrait.
- `typographic`: one stable word or number is the artwork itself.
- `atmospheric`: no dominant subject; quiet field for editable overlay.
- `custom`: custom prose naming subject count, structure, and breathing room.

For `page_role: local`, use `visual_type` instead:

- `scene`
- `framework`
- `flowchart`
- `matrix`
- `cycle`
- `funnel`
- `pyramid`
- `comparison`
- `timeline`
- `map`
- `object`
- `portrait`
- `screenshot_context`
- `texture`

## Generation Paths

Qiaomu uses a three-path strategy, with Codex/host-native generation first when
available because it usually produces better finished PPT visuals:

1. **Path A: host-native image tool**  
   When the environment has built-in image generation, such as Codex image
   generation, use it directly. Run `stage_image_generation.py --force
   --only-missing`, then `built_in_image_generation_guide.py --only-missing`.
   The guide writes `assets/images/built_in_image_generation_tasks.json` and
   `assets/images/built_in_image_generation_guide.md`, grouping work into
   modest 3-4 image batches with prompt, negative prompt, expected output,
   `page_role`, `text_policy`, safe area, and import command. Save outputs to
   `assets/images/generation_batch/generated/`, import them with
   `import_generated_assets.py`, and update status to `Generated` only after the
   real file exists.

   If the user explicitly required Codex/host-native image generation, Path A is
   mandatory and blocking. A slide listed in the hard gate may not enter PPTX,
   HTML, SVG preview, or parity rendering until its real generated bitmap file
   exists and is recorded in the manifest. Path B, Path C, procedural
   backgrounds, and placeholders are prohibited unless the user explicitly
   approves a downgrade after seeing the blocker.

   When the deck has no source evidence image that must remain literal, Path A
   should normally create the primary visual layer for every representative
   visual page in the preview, not only a decorative background pack.

2. **Path B: configured API backend**  
   If host-native generation is unavailable or declined, use a configured image
   backend such as `gpt-image-2` when available. The prompt source of truth is
   `assets/images/image_prompts.json`.

3. **Path C: offline manual mode**  
   If no automated image path is available, write `image_prompts.json` and
   `image_prompts.md`, mark affected rows `Needs-Manual`, and continue with an
   explicit handoff.

Do not ask the user to choose a path during execution unless the earlier design
proposal did not settle cost, rights, or provider use. The path is an execution
detail; the asset contract is stable across all paths.

## Web-Sourced Images

Use `acquire_via: web` when the deck needs real-world material instead of
generated imagery.

License discipline:

- Accept `no-attribution`: CC0, Public Domain, Pexels, Pixabay.
- Accept `attribution-required`: CC BY, CC BY-SA, with visible credit.
- Reject non-commercial, no-derivatives, all-rights-reserved, unknown, or
  missing licenses.

Web search references are intent descriptions, not prompt text. Use concrete
nouns: `offshore wind farm`, `Tokyo bookstore street`, `Tang dynasty mural`.
Do not include negative prompts; image search APIs search words literally.

Store web-source metadata in `assets/images/image_sources.json`.

## Source Images

Paper figures, tables, source charts, article images, WeChat images, rendered
PDF page images, and PDF figures should normally use `acquire_via: source`, not
`ai`.

Hard rule: generated images can explain an analogy or create atmosphere, but
must not replace original source evidence. For paper decks, source figures and
tables are proof objects.

When a slide uses rendered PDF pages, article screenshots, source charts, or
other source evidence images, the renderer should preserve the image/page with
`meet` fitting unless the design contract explicitly names a safe crop. Put the
interpretation in editable foreground text beside or over a local scrim, not by
cropping the evidence into a decorative full-bleed background. Adjacent source
evidence pages should alternate composition, such as left-image/right-claim and
left-claim/right-image, so thumbnail rhythm does not collapse into repeated
pages.

Source screenshots that declare `image_text_pattern_id: ITL18` should render as
annotation pages: the screenshot/page remains visible, callout text is editable,
and leader lines terminate at the image boundary instead of crossing dense
source content. Source charts, paper figures, or data pages that declare
`ITL20` should render as wide evidence canvases with a separate editable
takeaway band/panel. Do not replace these source visuals with generated or
procedural charts unless the original evidence is explicitly unavailable and
the deck records that gap.

Comparison slides that declare `ITL13` or `ITL14`, or whose role/brief asks for
before/after or source comparison, should keep multiple source rows for the same
slide when multiple source image candidates exist. The first source row is not
enough for a real comparison page; the manifest should preserve at least two
project-relative source image paths, their source pages, and their provenance.

When `source_cards.json` contains multiple `image_candidates`, asset planning
should use the available source-image pool before repeating one candidate. This
is especially important for mixed Office/EPUB/PDF/URL projects: a DOCX cover
image, PPTX embedded chart, EPUB illustration, PDF page render, and article
screenshot should all have a chance to become slide evidence instead of being
stranded while one early image is reused across the deck.

Source evidence pages should not all share one renderer. Route source images
through the slide's layout/component intent: cover and closing pages can use a
source image as full-bleed atmosphere, L13-style pages should combine the source
image with an editable process flow, L24-style pages should combine the image
with a concept map, feature pages can use a top evidence image, and ordinary
claim/evidence pages can alternate left/right source spreads. The visual rhythm
gate should count both image slot and structural fingerprint so repeated
source-panel pages are caught before export.

During SVG finalization, oversized raster evidence images may be downsampled
from the final SVG display box before Base64 embedding so PPTX/PDF/HTML exports
stay small and fast. The default target is display long-edge times 2.5 with a
960px floor, while full-slide images remain large enough for presentation
preview. Disable this only when the user explicitly needs original-resolution
source images for later zoom/crop editing.

## Output Files

Recommended project structure:

```text
<project>/
  visual_asset_manifest.json
  assets/
    images/
      image_prompts.json
      image_prompts.md
      image_sources.json
      *.png
      *.jpg
  visual_contract.json
  qa_report.md
```

`visual_contract.json` uses the manifest entries to declare actual slide slots:
coordinates, fit, crop, mask, padding, overflow policy, contrast policy, and
source/credit behavior.

## Status Rules

- `Pending`: row is planned but not yet attempted.
- `Generated`: AI row has an actual file at the expected path.
- `Sourced`: web row has an actual file and license metadata.
- `Existing`: user/source row has a file or source record.
- `Rendered`: formula row has a rendered asset.
- `Placeholder`: intentional planning placeholder.
- `Needs-Manual`: terminal explicit gap.
- `Missing`: expected asset is not available and the deck must either work
  around it or report the gap.
- `Failed`: attempted and failed; should usually be converted to
  `Needs-Manual` before user-facing completion.

Do not claim an image is generated without a file. Do not leave `Pending` rows
when reporting final deck completion unless the task is planning-only.

## QA Checklist

- Every generated/sourced/existing/rendered row points to a real file.
- Every `ai` row has a prompt and appears in `assets/images/image_prompts.json`.
- Every `web` row has `image_sources.json` metadata and allowed license tier.
- Deck-wide rendering and palette behavior are consistent.
- AI rows cite `layout_pattern_id`, media-heavy rows cite
  `image_text_pattern_id`, and prompts describe the focal point, negative
  space, crop, foreground-safe area, and thumbnail rhythm role.
- AI rows and media-heavy source rows cite an `integration_move`; labels,
  chips, arrows, or callouts cite `annotation_targets` or are removed.
- AI rows and media-heavy source rows cite `text_surface_policy`; sentence-level
  text does not sit directly on pale/complex image texture, and accent color is
  not used for long readable copy on unstable backgrounds.
- Generated images do not contain slide chrome, body copy, source citations, or
  fake evidence.
- Generated full-slide/main-region images are paired with native editable
  foreground text; `pptx_text_check.py` should pass with no text overflow and no
  image-backed-slide failure.
- Text-over-image pages declare a calm overlay area, scrim, gradient, text
  block, or copy-space strategy.
- Thumbnail grid review shows layout diversity and image-text integration:
  no accidental run of identical split panels, identical foreground cards, or
  generic background-plus-text slides unless the approved design system calls
  for that repetition.
- Mobile/phone screenshot review does not show awkward title wrapping in narrow
  rails, unreadable footnotes, tiny UI-like chip rows, overlarge black/white
  slabs, or labels disconnected from the image.
- Mobile/phone screenshot review preserves text contrast: title, claim, body,
  and reading-path text remain readable without zoom; weak source notes are
  moved to notes or enlarged on a stable surface.
- Image slots in `visual_contract.json` match asset roles and paths.
- Any `Needs-Manual` row is reported with filename, prompt/source intent, and
  target path.
