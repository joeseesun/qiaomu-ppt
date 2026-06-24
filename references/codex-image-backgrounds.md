# Codex Image Backgrounds

Use this when the runtime has an image generation tool, especially Codex with built-in image generation.

## Recommended Generation Stack

Current project experience favors Claude Opus 4.8 for reasoning, story shaping,
layout planning, code generation, and QA repair, paired with gpt-image-2 or
Codex built-in image generation for bitmap backgrounds, concept images,
texture packs, and magazine-style moodboards.

This is a recommendation, not a hard dependency. If the preferred stack is not
available, use the strongest available reasoning model plus the available image
generation route or the procedural fallback. Always record the actual model or
tool in `generation_report.md` or `qa_report.md`; do not print it on the slide
canvas by default.

## Goal

Generate content-led bitmap backgrounds and concept images before slide
rendering. These replace shape-based decorative backgrounds, but they must
serve the page's claim, evidence, audience emotion, or explanatory metaphor.
They are not hero posters, UI chrome, layout scaffolds, chart containers,
cards, frames, or "tech-feel" linework.

The background is part of the slide argument. Before generating any background,
write its `content_link`: the slide claim/proof it supports, the mood or
scenario it should make tangible, and the exact foreground-safe area it leaves
for editable text/diagrams. If a background cannot be tied to the page content
in one sentence, do not generate it; use a quieter neutral surface instead.

For full production, use [visual-asset-acquisition.md](visual-asset-acquisition.md)
and `scripts/visual_asset_manifest.py` first. `background_prompt_pack.py` is a
lightweight background-only helper; `visual_asset_manifest.json` is the source
of truth for generated images, web images, user images, source figures,
formula/chart renders, icons, placeholders, status, file evidence, and
rights/provenance.

## When To Use

- Use by default for brand launch, talk decks, and technical evidence decks when image generation is available.
- Use for courseware only if the generated background stays extremely quiet and does not reduce classroom readability.
- Skip only when the user forbids image generation, rights are unclear, or the deck must be fully deterministic without bitmap backgrounds.
- The decision must be written into the design proposal before generation. Do not silently fall back to procedural backgrounds in Codex when image generation is available.

## Background Pack

Create a candidate pack before final rendering. Default to 3-5 generated
candidates for shorter decks and 5-8 candidates for longer decks when the deck
uses role-based reuse. For high-design talk/brand/editorial decks, prefer
page-specific AI backgrounds or concept images for representative pages and up
to 12 unique per-slide assets, while keeping a coherent deck-wide rendering and
palette lock.

```text
assets/backgrounds/
  bg-cover.png
  bg-evidence-dark.png
  bg-evidence-light.png
  bg-diagram.png
  bg-closing.png
  background_prompts.json
```

Each background should be 16:9, preferably 1920x1080 or larger. It may contain
topic-specific environment, objects, surfaces, color fields, gradients, soft
light, subtle grain, atmospheric texture, and restrained abstract material. It
must not contain text, logos, charts, UI controls, fake screenshots, boxes,
panels, cards, frames, windows, placeholders, chart areas, image slots, text
blocks, or hard ornamental lines.

## Prompt Rules

Prompts should specify:

- slide claim, proof focus, or audience state change the image supports
- deck subject and mood
- route, such as brand launch, technical evidence, courseware
- background role
- semantic anchor: concrete object, place, material, scene, or metaphor derived
  from the source/slide content
- color budget: neutral base plus one accent only
- atmosphere-only treatment: color, gradient, light, grain, and abstract texture
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

- Put the bitmap as the full-slide background.
- Add a soft scrim only when needed for text contrast.
- Do not use the bitmap to solve layout. Every card, evidence frame, title, label, chart slot, and diagram must be an editable foreground object.
- Do not add extra decorative lines, grids, wedges, or rails on top of the generated background.
- Do not accept random abstract lines as a substitute for content-linked visual
  thinking. Lines are allowed only when the foreground diagram/chart/table needs
  them, or when the bitmap depicts a real-world/material phenomenon tied to the
  page's semantic anchor.
- Use the same 5 backgrounds as a rhythm across the deck; do not generate one unrelated image per slide.
- Select backgrounds by slide role: cover and closing use atmosphere images, dense charts use the quiet light evidence image, benchmark proof slides use the dark evidence image, and architecture/process slides use the diagram focus image.
- If a source chart/image is colorful, make the generated background quieter and keep non-image UI neutral.
- The selected background set should be visible in thumbnail rhythm but not become the design itself. Variation should come from focal light, texture, tone, and depth, not from baked-in panels or fake slide layout.
- If the user has recently rejected repeated or monotonous backgrounds, prefer one unique selected background asset per slide up to 12 slides, while keeping a coherent family.

## Concept Images

Built-in image generation is not only for backgrounds. In talk decks, it can be used for:

- one chapter-opening metaphor image
- a quiet conceptual illustration
- an object/material/scene that makes an abstract idea tangible
- a small set of visual direction candidates before production

These images still must not contain slide text, diagrams, UI, charts, or fake evidence. They should sit in declared image slots, while explanation remains editable foreground text and diagrams.

## Fallback

If image generation is unavailable:

- First use `scripts/procedural_background_pack.py` to create a deterministic 5-role SVG background pack.
- For HTML previews, CSS gradients, Canvas, canvas-sketch, p5.js, Pts.js, Paper.js, Two.js, Simplex-noise/Noise.js, GLSL Canvas, Regl/OGL, Motion Canvas, Theatre.js, or Anime.js may be used when they remain atmosphere-only.
- For editable PPTX, render Canvas/WebGL/CSS backgrounds to static PNG/SVG assets before insertion.
- Keep at most one accent and record the seed/engine in `visual_contract.json`.
- Do not emulate generated backgrounds with baked-in boxes, cards, panels, frames, decorative stripes, grids, rails, or random geometry.
- Record this in `visual_contract.json` as `background_asset_policy.procedural_fallback_policy`.
