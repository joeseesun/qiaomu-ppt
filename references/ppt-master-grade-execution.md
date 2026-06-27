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
6. Do not let atmosphere backgrounds masquerade as evidence. For image-rich
   subjects, the lock must include primary media rows such as album covers,
   artist/product/place photos, source screenshots, paper figures, charts, or
   document/page images. If those are unavailable, write explicit `Needs-Manual`
   rows and call the output a draft.
7. Do not accept "background image plus pasted text panel" as the default visual
   solution. Each media-rich page must follow
   `references/image-text-integration-contract.md`: named primary structure,
   editable foreground role, prompt-level safe area, and at least one visible
   integration modifier such as gradient scrim, matte, edge fade, crop/mask,
   leader lines, or texture wash.
8. Do not treat a case style as a skin. If a deck selects Memphis Pop,
   Risograph Zine, Brutalist Newspaper, Swiss Grid, or any other learned case
   style, translate it into hard production constraints: active color count,
   allowed texture/media behavior, required component families, and forbidden
   moves. A style label without constraints is not `ppt_master_grade`.

## Five-Axis Lock

The strongest current lesson from `ppt-master` v2.10/v2.11 is the independent
axis split. Do not treat "高级", "杂志感", "Keynote 风", or "ppt-master 风" as a
style. Before preview or production, lock these axes separately:

1. `mode`: the argument or teaching skeleton, such as pyramid, narrative,
   instructional, showcase, briefing, or a fully described custom cadence.
2. `visual_style`: the page-layout aesthetic, such as editorial, swiss-minimal,
   photo-editorial, data-journalism, blueprint, zine, ink-wash, or a custom
   behavior paragraph.
3. `image_rendering`: the deck-wide generated-image look, such as editorial,
   minimalist-swiss, corporate-photo, blueprint, screen-print, ink-notes, or a
   custom behavior paragraph.
4. `image_palette_behavior`: how the confirmed deck colors are distributed in
   generated images. This is not the HEX palette itself.
5. `image_type_strategy`: per-image composition contracts. Local image blocks
   use types such as infographic, flowchart, framework, matrix, comparison,
   timeline, map, or scene; hero-page images use primitives such as atmospheric,
   single subject, portrait, typographic, or custom.

Run:

```bash
python3 <skill>/scripts/ppt_master_axis_audit.py <project> \
  --output <project>/reports/ppt_master_axis_audit.json \
  --markdown <project>/reports/ppt_master_axis_audit.md \
  --min-score 85 --enforce
```

If this gate fails, repair `design_proposal.md`, `spec_lock.*`,
`style_direction.json`, `slide_plan.json`, and `visual_asset_manifest.json`
before drawing more pages. More generated backgrounds are not a fix for a
missing axis lock.

The audit also checks the newest absorbed lesson from the Sugar Rush Memphis and
Indie Bookstore Zine examples: AI image prompt sidecars, prompt-level
composition/safe-area/editable-foreground boundaries, component selection
rationale, and presentation sidecars. If the score fails because these are
missing, repair the contracts before making more pages.

## Rejection Recovery

When the user says a deck still does not feel like `ppt-master`, assume the
problem is systemic until proven otherwise. Do not continue by adding slides or
making another isolated demo page. First check:

- Whether the latest upstream study is current enough for the method being
  claimed.
- Whether `mode` and `visual_style` were collapsed into one vague direction.
- Whether image rendering, palette behavior, page role, text policy, and local
  type/hero primitive exist as real fields in the asset manifest.
- Whether image-rich subjects have inspectable source/user/web/formula media,
  not only AI atmosphere.
- Whether representative pages were authored or revised page-by-page from the
  lock rather than emitted by a generic batch renderer.

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
- `assets/images/image_prompts.json` and `assets/images/image_prompts.md` when
  generated images are planned. These sidecars must cover all AI rows and record
  purpose, ratio, composition, safe text area, text policy, negative prompts, and
  editable foreground boundary.
- `reports/ppt_master_axis_audit.json` / `.md`: proof that the five-axis lock,
  image role contract, primary-media boundary, page rhythm, and layout lock are
  present before page execution.
- `primary_media_evidence_plan` or equivalent manifest coverage when the subject
  is music, culture, architecture, fashion, biography, product, or brand-led.
  Full-slide backgrounds are not enough; at least one representative preview
  page should prove real/source/user/web media integration or document the exact
  missing asset.
- `page_content_guide.md` plus per-page notes when the deck is longer than
  eight pages or expected to become speaker-ready.
- `notes/total.md` or equivalent speaker-notes sidecar when the deck is longer
  than eight pages, culture/report/courseware oriented, or expected to be
  delivered live.
- `animations.json` or `animation_manifest.json` when the user asks for a
  presentation-ready deck, narrated deck, keynote-style reveal, or object-level
  motion. Animation groups must reference stable SVG/PPT group IDs and follow
  the reading path.

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
- `integration_modifiers`: how the renderer will fuse the bitmap with editable
  foreground objects: copy-space title, directional scrim, color wash, image
  fade-to-background, source-object matte, native callout lines, or local zoom.
- `prompt`: a coherent paragraph, usually 150-300 words for final-quality
  assets, not a tag list.

Evidence assets such as album covers, paper figures, screenshots, charts,
tables, logos, product UI, and historical photos must come from source, user,
web, formula, or chart-renderer routes. Generated images may interpret mood or
context, but must not fake evidence.

Music and culture decks deserve special discipline: fetch or request the album
cover, artist/producer images, physical media, venue/place, score/lyrics/source
screenshots, or other inspectable materials before relying on AI scenery. AI can
make the emotional field feel richer, but it cannot stand in for the album art
or historical/source artifact.

## Four-Page Preview Standard

For decks longer than seven pages, the preview should prove the style can
survive the full deck:

- Page A: cover or thesis anchor.
- Page B: dense evidence or source-object page using real primary media when
  the subject calls for it.
- Page C: diagram, map, timeline, mechanism, or concept model.
- Page D: breathing turn, quote, chapter close, or final memory hook.

Each page must have:

- a distinct `rhythm`;
- a named `layout_pattern_id`;
- a declared `image_text_pattern_id` when media is present;
- a primary proof object;
- a declared component type plus selection rationale when the page uses a chart,
  process, table, list, map, guide component, KPI block, card system, or
  diagram. Record rejected alternatives when an obvious component would be
  semantically wrong.
- at least four top-level semantic SVG groups when the page has title, media,
  proof, annotations, and footer;
- visible integration between media and foreground objects: crop/mask,
  editorial matte, scrim, color normalization, annotation leaders, or
  deliberate negative space.
- no full-height/full-width text slab unless the page's named ITL pattern
  explicitly uses a text bar/card and the slab's color, opacity, size, and
  anchor are justified by the image composition.

A preview fails this mode if it reads as:

- repeated cards with different text;
- a decorative background plus bullets;
- a generated background and a large unrelated opaque panel that could be moved
  to any other slide without changing the composition;
- image and text merely placed side by side without a reason;
- source images pasted raw with no crop, matte, caption, or alignment logic;
- no source/web/user/formula primary media on a music/culture/product/brand
  deck while every image row is only `background` or `atmosphere`;
- generated backgrounds that contain fake slide frames, fake charts, or baked
  title areas;
- PPTX pages that are full-slide screenshots when editable PPTX is expected.

## Quality Review

Before offering the preview to the user:

- Run SVG compatibility checks.
- Render a thumbnail grid and inspect it for rhythm variety, source-image
  integration, overlap, title leading, and card/dashboard noise.
- Run `deck_quality_benchmark.py` and read the `primary_media_evidence` category
  plus `deck_repair_plan.py`; critical primary-media actions block final claims.
- Export or attempt editable PPTX through the SVG-first route.
- Run visible PPTX text checks without `--allow-image-backed`.
- Render PPTX previews when LibreOffice/Poppler are available.
- Check `assets/images/image_prompts.*` against AI rows in
  `visual_asset_manifest.json`; no final-quality image queue should be hidden
  only in chat history.
- Check `notes/total.md` and `animations.json` when the route promises live
  delivery, narration, or presentation-ready polish.
- Write `generation_report.md` or `qa_report.md` with passed checks, missing
  evidence, and what still needs real image generation or user approval.

If the preview exposes a systemic flaw, update the project contracts and, when
reusable, this skill's rules. Do not only patch the visible page.
