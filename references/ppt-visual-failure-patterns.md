# PPT Visual Failure Patterns

These rules capture recurring visual failures found in generated PPTX decks. Treat them as production defects, not taste notes.

## 1. Single-Background Template Drift

Symptom:

- Most slides use the same background construction, decorative side stripe, card style, and evidence layout.
- Individual slides are acceptable, but the full deck feels monotonous when scanned as thumbnails.
- The visual motif becomes a wallpaper instead of a narrative rhythm.

Root cause:

- The style brief defines palette and motif but not a `background_rhythm`.
- The slide plan does not assign per-slide layout/background roles.
- The generator repeats the first working layout because it is safe.

Fix:

- Define 4-6 reusable background/layout roles before rendering:
  - `hero_dark`: cover, chapter open, closing.
  - `evidence_dark`: dark background with white chart/card.
  - `evidence_light`: light background for dense benchmark charts.
  - `split_panel`: left evidence / right bullets or reversed.
  - `diagram_focus`: centered architecture/process diagram with small explanation rail.
  - `quote_or_claim`: large statement, sparse support, no chart.
- Assign each slide a `layout_role` and `background_role` in `slide_plan.json`.
- Do not use the same decorative background role more than 2 consecutive slides.
- In decks longer than 8 pages, use at least 4 background roles and at least 4 layout structures.
- Thumbnail-scan the whole deck. If the deck reads as one repeated page, revise before export.

## 2. Overdesigned Background Noise

Symptom:

- Slides feel hard, busy, flashy, or visually tiring.
- Decorative wedges, rails, glows, cards, dots, or gradients compete with titles and evidence.
- Thumbnail grid looks energetic, but individual slides become harder to read.

Root cause:

- The deck treats background as the design instead of supporting the message.
- The style brief lacks a `visual_noise_budget`.
- The generator stacks multiple decorative systems because each one works in isolation.

Fix:

- Set `visual_noise_budget` to `quiet` by default.
- Use restrained background families: `quiet_dark`, `quiet_light`, `editorial_band`, `split_surface`, `focus_canvas`.
- Evidence and chart slides get the quietest backgrounds.
- Use one accent system per slide.
- Remove large saturated wedges or hard side rails unless they are part of the brand and the content stays clearly dominant.

## 3. Rainbow Color Budget Failure

Symptom:

- One slide uses cyan bullets, green badges, yellow metric cards, red metric cards, and several neutral surfaces.
- The page feels cheap or dashboard-like even when each component is individually tidy.
- The user cannot tell which color carries meaning.

Root cause:

- The generator treats color as decoration rather than information hierarchy.
- Status/metric cards use different colors by index.
- The style brief lacks a per-slide color budget.

Fix:

- Set `color_budget.max_active_colors_per_slide <= 3`.
- Default formula: neutral base + readable text + one accent.
- Use one accent per slide; vary hierarchy with size, weight, spacing, or ordering instead of new colors.
- Source charts/screenshots are exempt, but the surrounding slide UI must become quieter when the evidence object is colorful.

## 4. Meaningless Decorative Linework

Symptom:

- Slides contain thin lines, grids, rails, or light streaks that do not connect content or frame a real object.
- The design says "technical" but does not improve reading, hierarchy, or evidence focus.
- Backgrounds look busy even after saturated shapes are removed.

Root cause:

- The generator tries to replace weak composition with surface texture.
- Words such as `subtle grid`, `thin rule`, or `tech line` were treated as a style recipe.
- Layout roles are not strong enough, so linework becomes filler.

Fix:

- Lines must be functional: chart axes, table rules, connectors, content separators, or real framing.
- Prefer generated bitmap backgrounds in Codex image-generation environments.
- If image generation is unavailable, use clean neutral surfaces, not faux-technical linework.
- Record `background_asset_policy.decorative_line_policy` in `visual_contract.json`.

## 5. Fake Rounded Image Frame

Symptom:

- A rounded rectangle is drawn behind an image, but the image itself is rectangular and spills beyond the intended card.
- The chart/image crosses the card border, covers rounded corners, or visually floats outside the frame.
- The slide looks almost correct at full size but fails in screenshot/thumbnail review.

Root cause:

- A decorative frame is not a clipping mask.
- The image is inserted after the frame and is not actually cropped, masked, or composited.
- The generator confuses "draw a card behind the image" with "fit the image into a card".

Fix:

- Every image slot must declare:
  - `slot_id`
  - `x`, `y`, `w`, `h`
  - `fit`: `contain`, `cover`, or `crop`
  - `mask`: `none`, `rounded_rect`, or `circle`
  - `padding`
  - `overflow_policy`: always `clip_or_fail`
- If the tool supports real image cropping/masking, use it.
- If the tool does not support real rounded clipping, choose one of:
  - Use a square/rectangular frame with no rounded-card promise.
  - Pre-compose the image onto a rounded card canvas with Pillow/SVG and insert the composed image.
  - Use a native PowerPoint picture crop / placeholder route.
- Never place a rectangular image over a rounded rectangle and call it clipped.

## 6. Evidence Chart Legibility Drift

Symptom:

- Source charts are technically present but too small, dense, or low-contrast in presentation view.
- Bullets beside the chart compete with the evidence object.

Fix:

- For dense source charts, use one of three treatments:
  - `full_chart`: chart owns 70-85% of the slide, bullets become speaker notes.
  - `chart_crop`: crop/zoom one region and cite the full chart in notes.
  - `chart_then_takeaway`: first slide shows full chart, next slide extracts 2-3 callouts.
- Do not shrink a dense benchmark chart below the size where labels are readable in the rendered preview.

## 7. Visible Internal Provenance Footer

Symptom:

- Every slide shows internal production text such as `fetched via`, `generated with`, `qiaomu-markdown-proxy`, or `Speaker cue:`.
- The deck feels like a debug artifact instead of a finished presentation.
- Source lines compete with slide content and create visual noise in screenshots.

Root cause:

- QA provenance was treated as slide chrome.
- Speaker notes or generator metadata were written into visible text boxes instead of notes/sidecar files.

Fix:

- Default `visible_provenance_policy` to `hidden_internal`.
- Keep source URLs, fetch method, model name, and verification evidence in `qa_report.md`, `generation_report.md`, speaker notes, or an optional final references page.
- Use visible citations only when the route needs them, such as academic/report decks, and keep them content-level, not toolchain-level.
- Never print `fetched via`, `generated with`, model/provider names, or internal speaker cues on every slide unless the user explicitly asks.

## 8. Required Visual QA

Before calling a deck complete:

- Render the PPTX to PDF/images or open it in PowerPoint/Keynote and screenshot thumbnails.
- Inspect the thumbnail grid for repeated backgrounds, samey layouts, blank slides, and visual fatigue.
- Inspect every slide for color budget drift: max three active non-image colors, one accent.
- Inspect every slide for decorative linework. Remove lines that are not axes, table rules, connectors, separators, or real frames.
- Inspect every chart/image slide for image overflow beyond the declared slot.
- Inspect visible slide text for internal provenance or speaker-cue leakage.
- If a screenshot reveals a frame/clip problem, fix the generation method, not just that slide's coordinates.
