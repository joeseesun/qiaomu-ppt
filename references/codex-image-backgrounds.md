# Codex Image Backgrounds

Use this when the runtime has an image generation tool, especially Codex with
built-in image generation. Despite the filename, this reference now covers
full-slide/main-region Codex visuals as the default visual layer, not only quiet
backgrounds.

## Recommended Generation Stack

Current project experience favors Claude Opus 4.8 for reasoning, story shaping,
layout planning, code generation, and QA repair, paired with gpt-image-2 or
Codex built-in image generation for bitmap backgrounds, concept images,
texture packs, and magazine-style moodboards.

In Codex environments, treat built-in image generation as the default route for
recommended PPT visuals, not an optional add-on. Plans, previews, and final
decks should use generated full-slide/main-region visuals, concept images, or
concrete scene/reconstruction images unless the user forbids image generation,
it is unavailable, or the project is explicitly planning-only. If the preferred
stack is not available, use the strongest available reasoning model plus a
configured image API as the second route; use procedural/SVG fallback only for
preview/offline work or an explicitly accepted downgrade. Always record the
actual model or tool in `generation_report.md` or `qa_report.md`; do not print
it on the slide canvas by default.

If the user explicitly says Codex image generation is required, treat it as a
hard gate, not a preference. Generate or import the requested Codex/host-native
bitmap assets first, record real file paths in `visual_asset_manifest.json`, and
only then render PPTX/HTML previews. Do not use procedural fallback, CSS/Pillow/
Canvas/SVG texture packs, placeholders, a different image API, or manual art as
a substitute unless the user explicitly re-approves that downgrade after the
blocker is disclosed.

## Goal

Generate content-led bitmap visuals before slide rendering. These replace
shape/SVG-drawn main visuals and decorative backgrounds, but they must serve the
page's claim, evidence, audience emotion, or explanatory metaphor. They are not
finished slide screenshots, UI chrome, layout scaffolds, chart containers,
cards, frames, or "tech-feel" linework.

The generated image is part of the slide argument. Before generating any
full-slide visual, main-region visual, or background, write its `content_link`:
the slide claim/proof it supports, the mood or scenario it should make
tangible, and the exact foreground-safe area it leaves for editable text,
labels, diagrams, or source evidence. If an image cannot be tied to the page
content in one sentence, do not generate it; use a quieter neutral surface
instead.

The generated image also inherits the page layout. Before prompting, choose the
slide's `Lxx` proof pattern and `ITLxx` image-text pattern when media matters.
The prompt must tell the image where the focal subject belongs, which region is
quiet negative space, how the crop should behave, and where editable foreground
text or callouts will sit. It must also name the intended
`integration_move`: copy space, local scrim, object-adjacent annotation,
edge-fade proof zone, detail zoom, comparison split, or another concrete move.
Do not generate a beautiful generic background first and then search for a
layout that happens to fit it.

For full production, use [visual-asset-acquisition.md](visual-asset-acquisition.md)
and `scripts/visual_asset_manifest.py` first. `background_prompt_pack.py` is a
lightweight background-only helper; `visual_asset_manifest.json` is the source
of truth for generated images, web images, user images, source figures,
formula/chart renders, icons, placeholders, status, file evidence, and
rights/provenance.

## When To Use

- Use by default for brand launch, talk decks, science explainers, teaching
  decks, and technical evidence decks when image generation is available.
- Use by default for ordinary Qiaomu PPT recommendations and previews when
  image generation is available; do not deliver a shape-only/SVG-only visual
  draft unless it is clearly labelled as a downgrade or the user asked for it.
- Use for courseware with quieter copy-space and restrained visuals so
  classroom readability remains strong.
- Skip only when the user forbids image generation, rights are unclear, or the deck must be fully deterministic without bitmap backgrounds.
- The decision must be written into the design proposal before generation. Do not silently fall back to procedural backgrounds in Codex when image generation is available.

## Visual Pack

Create a candidate pack before final rendering. Default to 3-5 generated
candidates for shorter decks and 5-8 candidates for longer decks when the deck
uses role-based reuse. For high-design talk/brand/editorial/science decks,
prefer page-specific AI full-slide or main-region visuals for representative
pages and up to 12 unique per-slide assets, while keeping a coherent deck-wide
rendering and palette lock.

```text
assets/backgrounds/
  bg-cover.png
  bg-evidence-dark.png
  bg-evidence-light.png
  bg-diagram.png
  bg-closing.png
assets/codex-visuals/
  slide-01-cover.png
  slide-02-concept.png
  slide-03-evidence.png
  background_prompts.json
```

Each full-slide visual or background should be 16:9, preferably 1920x1080 or
larger. It may contain topic-specific environment, objects, surfaces, characters
when appropriate, reconstruction, visual comparison, color fields, gradients,
soft light, subtle grain, atmospheric texture, and restrained abstract material.
It must not contain readable text, logos, charts, UI controls, fake screenshots,
boxes, panels, cards, frames, windows, placeholders, chart areas, image slots,
text blocks, citations, or hard ornamental lines.

## Prompt Rules

Prompts should specify:

- slide claim, proof focus, or audience state change the image supports
- selected `Lxx` layout pattern and `ITLxx` image-text pattern when applicable
- deck subject and mood
- route, such as brand launch, technical evidence, courseware
- visual role: full-slide main visual, main-region evidence visual, cover,
  chapter visual, quiet background, or local object/scene
- semantic anchor: concrete object, place, material, scene, or metaphor derived
  from the source/slide content
- color budget: neutral base plus one accent only
- visual treatment: concrete subject/scene/reconstruction for main visuals, or
  atmosphere-only color/gradient/light/grain for background assets
- focal point, copy-space/negative-space region, crop behavior, and foreground
  safe area for editable title, labels, callouts, source notes, or chart overlays
- no text, no icons, no UI, no logos, no boxes, no rectangles, no cards, no panels, no frames, no placeholders, no chart areas, no image slots, no decorative stripes, no glowing rails

Example:

```text
Create a quiet 16:9 presentation background for a technical evidence slide whose claim is that long-horizon AI coding depends on verified feedback loops.
Semantic anchor: a dim engineering bench with layered terminal-light reflections and a single soft loop-shaped light path, suggesting verification without drawing a diagram.
Near-black graphite color field, soft gradient depth, subtle material grain, one cyan accent glow kept below 8% of the frame.
Atmosphere only: no text, logo, UI, chart, image slot, card, panel, rectangle, frame, window, placeholder, grid, or neon rail.
All titles, cards, charts, frames, and layout objects will be added later as editable foreground elements.
```

## Use Rules

- Put the bitmap as the full-slide visual layer or declared main-region visual.
- Add a soft scrim only when needed for text contrast.
- Do not use the bitmap to solve editable information layout. Every title,
  body sentence, evidence frame, label, chart value, source note, citation, and
  speaker reading path must be an editable foreground object.
- Do not add extra decorative lines, grids, wedges, or rails on top of the generated background.
- Do not accept random abstract lines as a substitute for content-linked visual
  thinking. Lines are allowed only when the foreground diagram/chart/table needs
  them, or when the bitmap depicts a real-world/material phenomenon tied to the
  page's semantic anchor.
- For background-only packs, use a coherent role-based family across the deck;
  do not generate unrelated art per slide.
- Select background-only assets by slide role: cover and closing use atmosphere
  images, dense charts use the quiet light evidence image, benchmark proof
  slides use the dark evidence image, and architecture/process slides use the
  diagram focus image.
- For Codex full-slide or main-region visuals, vary the structural fingerprint
  by the approved `Lxx`/`ITLxx` plan. Avoid accidental repetition of the same
  left-text/right-image split, same foreground card, same centered subject, or
  same title-over-photo composition unless it is a deliberate series.
- Do not rescue a poorly staged image by adding a large black/white text slab.
  If foreground copy needs a half-slide opaque panel, first ask whether the
  chosen image crop, focus, or `ITLxx` pattern is wrong. Prefer real image
  copy-space, localized scrims, edge fades, or annotations tied to the subject.
- Do not place decorative chip rows on top of a generated image. A chip, badge,
  or label must either point to a visible target in the image or become a
  normal takeaway outside the visual.
- If a source chart/image is colorful, make the generated background quieter and keep non-image UI neutral.
- The selected background set should be visible in thumbnail rhythm but not become the design itself. Variation should come from focal light, texture, tone, and depth, not from baked-in panels or fake slide layout.
- If the user has recently rejected repeated or monotonous backgrounds, prefer one unique selected background asset per slide up to 12 slides, while keeping a coherent family.
- If the user rejects SVG/shape drawings as ugly, do not polish the shape
  drawing as the main route. Regenerate or replace the Codex visual and keep
  only editable text/labels in the foreground.
- If thumbnail review says the deck is monotonous, repair the layout contract
  and visual prompts first. Moving text boxes on top of the same generic image
  is not enough.

## Concept Images

Built-in image generation is not only for backgrounds. In talk decks and
science/teaching explainers, it should be used for:

- full-slide or main-region visual layers
- one chapter-opening metaphor image
- a quiet conceptual illustration
- an object/material/scene that makes an abstract idea tangible
- a small set of visual direction candidates before production

These images still must not contain slide text, UI, charts, labels, citations,
or fake evidence. They should sit in declared image slots, while explanation
remains editable foreground text, labels, callouts, and source-grounded diagrams
or charts.

Concept-image prompts should name the selected `ITLxx` structure when they will
share the slide with editable foreground. For example, a central object prompt
for `ITL17` should leave radial annotation space; an `ITL20` data-context image
should stay visually subordinate to the chart/takeaway zone; an `ITL03` hero
image should provide deliberate title copy space rather than random darkness.
After importing the generated file, inspect it at thumbnail size. If title copy
would be forced into a narrow rail, labels have no visible targets, or the image
needs a repeated opaque panel to become readable, treat the asset as a failed
composition and regenerate or recrop it before rendering the slide.

## Editable Foreground Rule

Generated bitmaps carry beauty, mood, scene, material depth, reconstruction,
visual comparison, and main visual presence. Editable foreground objects carry
titles, body copy, labels, arrows, callouts, diagrams, charts, citations, reading
path, and small legibility panels. A deck that uses only foreground shapes/SVG
without generated bitmap main visuals is a fallback, not the normal recommended
production path.

## Fallback

If image generation is unavailable:

- First use `scripts/procedural_background_pack.py` to create a deterministic 5-role SVG background pack.
- For HTML previews, CSS gradients, Canvas, canvas-sketch, p5.js, Pts.js, Paper.js, Two.js, Simplex-noise/Noise.js, GLSL Canvas, Regl/OGL, Motion Canvas, Theatre.js, or Anime.js may be used when they remain atmosphere-only.
- For editable PPTX, render Canvas/WebGL/CSS backgrounds to static PNG/SVG assets before insertion.
- Keep at most one accent and record the seed/engine in `visual_contract.json`.
- Do not emulate generated visuals with baked-in boxes, cards, panels, frames,
  decorative stripes, grids, rails, random geometry, or hand-drawn complex SVG
  scenes.
- Record this in `visual_contract.json` as `background_asset_policy.procedural_fallback_policy`.

Fallback is forbidden when the user explicitly required Codex/host-native image
generation. In that case, stop and report `missing evidence: codex_image_asset`
instead of producing a downgraded preview.
