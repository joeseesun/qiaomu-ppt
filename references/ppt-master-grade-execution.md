# PPT Master Grade Execution

Use this reference when the user asks to learn from or match `ppt-master`, asks
for a high-design/editorial deck, rejects a draft as ugly/generic, or when a
deck's purpose depends on magazine-level visual trust.

This is a Qiaomu-owned execution mode. It does not call `ppt-master` at runtime
and must not copy upstream templates, slide designs, wording, images, or exact
prompts.

## Trigger

Enter `ppt_master_grade` mode when any of these are true:

- The user says `ppt-master`, `对标`, `赶上`, `学习吸收`, `高级`, `精致`, `杂志感`,
  `高质量`, or similar in the context of visual output.
- The user complains that a generated deck is ugly, generic, card-heavy,
  poorly illustrated, poorly laid out, or visually below examples.
- The deck is a culture, biography, architecture, fashion, design, music,
  product-launch, research-paper, or publication-style deck where image,
  chart, or source-object treatment is central.

Record the mode in `route_card.md`, `design_proposal.md`,
`design_spec.md`, `spec_lock.md`/`spec_lock.json`, and `preview_gate.json`.

## Non-Negotiables

The route is slower and more deliberate:

1. Do not continue a rejected low-quality deck by adding more slides. Restart or
   fork into a new project folder with a fresh execution lock.
2. Do not render from chat memory. Create or update `design_spec.md` and
   `spec_lock.md`/`spec_lock.json` before authoring preview pages.
3. Do not use a generic batch SVG renderer to satisfy the high-fidelity
   four-slide preview. Scripts may prepare sidecars, compute geometry, validate,
   rasterize previews, and export PPTX, but the representative preview pages
   must be authored or revised page-by-page from the current lock.
4. Do not use one visual device on every page. Each representative page needs a
   content-specific proof object and a visibly different composition.
5. Keep readable foreground content editable. Bitmap assets may carry
   atmosphere, photography, texture, or concept illustration; slide text,
   labels, callouts, chart marks, diagram nodes, captions, and source notes stay
   in SVG/PPT foreground objects.

## Contract Before Drawing

Before visual authoring, the project must contain:

- `design_spec.md`: human-readable story, audience shift, visual thesis, and
  page intent.
- `spec_lock.md` or `spec_lock.json`: exact canvas, palette, typography, image
  rendering, page rhythm, page layouts, page charts/diagrams, image layout
  patterns, coordinate slots, group IDs, and forbidden moves.
- `slide_plan.json`: claim-title, proof object, source anchors, component plan,
  rhythm, layout pattern, image/text pattern, and QA risk for each page in
  scope.
- `visual_asset_manifest.json`: all source/user/web/generated/formula/chart
  assets with status, role, path or prompt, text policy, fit mode, usage, and
  provenance notes.
- `assets/images/image_prompts.json` or
  `assets/images/image_generation_queue.json` when generated images are planned.
- `page_content_guide.md` plus per-page notes when the deck is longer than
  eight pages or expected to become speaker-ready.

If any exact value needed for a page is missing, update the lock before drawing.

## Image Generation Discipline

Generated images should be planned like a deck-wide art direction, not as a
per-page decoration reflex.

For every AI image row, define:

- `image_rendering`: one deck-wide family such as editorial photography,
  risograph print, eastern ink-paper, blueprint technical, cinematic stage, or
  museum-catalog object study.
- `image_palette_behavior`: how colors behave across all generated assets.
- `asset_role`: background, chapter art, concept metaphor, scenario,
  object cutaway, texture, or moodboard.
- `page_role`: cover, chapter, dense proof, breathing turn, closing, etc.
- `composition`: camera/crop, focal subject, foreground boundary, negative
  space, safe text area, and whether source objects will sit over it.
- `text_policy`: normally `no_text`; never ask the generated image to contain
  real slide text, charts, tables, UI, logos, or evidence labels.
- `prompt`: a coherent paragraph, usually 150-300 words for final-quality
  assets, not a tag list.

Evidence assets such as album covers, paper figures, screenshots, charts,
tables, logos, product UI, and historical photos must come from source, user,
web, formula, or chart-renderer routes. Generated images may interpret mood or
context, but must not fake evidence.

## Four-Page Preview Standard

For decks longer than seven pages, the preview should prove the style can
survive the full deck:

- Page A: cover or thesis anchor.
- Page B: dense evidence or source-object page.
- Page C: diagram, map, timeline, mechanism, or concept model.
- Page D: breathing turn, quote, chapter close, or final memory hook.

Each page must have:

- a distinct `rhythm`;
- a named `layout_pattern_id`;
- a declared `image_text_pattern_id` when media is present;
- a primary proof object;
- at least four top-level semantic SVG groups when the page has title, media,
  proof, annotations, and footer;
- visible integration between media and foreground objects: crop/mask,
  editorial matte, scrim, color normalization, annotation leaders, or
  deliberate negative space.

A preview fails this mode if it reads as:

- repeated cards with different text;
- a decorative background plus bullets;
- image and text merely placed side by side without a reason;
- source images pasted raw with no crop, matte, caption, or alignment logic;
- generated backgrounds that contain fake slide frames, fake charts, or baked
  title areas;
- PPTX pages that are full-slide screenshots when editable PPTX is expected.

## Quality Review

Before offering the preview to the user:

- Run SVG compatibility checks.
- Render a thumbnail grid and inspect it for rhythm variety, source-image
  integration, overlap, title leading, and card/dashboard noise.
- Export or attempt editable PPTX through the SVG-first route.
- Run visible PPTX text checks without `--allow-image-backed`.
- Render PPTX previews when LibreOffice/Poppler are available.
- Write `generation_report.md` or `qa_report.md` with passed checks, missing
  evidence, and what still needs real image generation or user approval.

If the preview exposes a systemic flaw, update the project contracts and, when
reusable, this skill's rules. Do not only patch the visible page.
