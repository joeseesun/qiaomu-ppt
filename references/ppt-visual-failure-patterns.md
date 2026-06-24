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

- Define 5 reusable background/layout roles before rendering:
  - `cover_atmosphere`: cover and opening thesis.
  - `dark_evidence`: dramatic proof slide with compact takeaway.
  - `light_evidence`: dense benchmark charts needing high readability.
  - `diagram_focus`: architecture, system, and process explanations.
  - `closing_atmosphere`: closing action or final statement.
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
- Prefer generated bitmap backgrounds in Codex image-generation environments,
  but only when each generated background has a `content_link`,
  `background_duty`, and `semantic_anchor` tied to the slide claim/proof.
- If image generation is unavailable, use clean neutral surfaces, not faux-technical linework.
- Record `background_asset_policy.decorative_line_policy` in `visual_contract.json`.

## 4A. Generic AI Wallpaper

Symptom:

- The slide uses a generated bitmap, but it could belong to any deck.
- The background looks premium in isolation yet does not clarify the page's
  claim, evidence, mood, scenario, or transition.
- The foreground text sits on top of an unrelated cinematic image.

Root cause:

- The prompt described only style words, palette, and "negative space".
- The asset row did not record what the image is supposed to do for the page.
- The generator used image generation as decoration rather than content
  staging.

Fix:

- Every AI background/concept row needs:
  - `content_link`: which claim/proof/audience-state the image supports.
  - `background_duty`: scene, material depth, conceptual metaphor, transition,
    or evidence-supporting atmosphere.
  - `semantic_anchor`: concrete nouns from the source/slide.
- The prompt must mention the slide title/claim and semantic anchor before
  style instructions.
- Reject backgrounds that are merely abstract gradients, line fields, generic
  data-center walls, stock people, or cinematic fog when the slide content
  points to a more specific object, place, mechanism, document, product, era, or
  consequence.
- Keep the foreground editable: titles, bullets, labels, diagrams, charts,
  frames, and source evidence stay outside the bitmap.

## 5. Dashboard Card Chrome

Symptom:

- The deck feels like a SaaS dashboard or UI mockup instead of a presentation.
- Slides contain giant rounded parent panels, nested cards, repeated metric cards, cyan outlines, numbered badges, and bottom mini-card rows.
- Each slide is individually tidy, but the whole deck feels samey and over-framed.

Root cause:

- The generator treats cards as the default answer to weak hierarchy.
- Parent containers are used to group content that should be grouped by whitespace, alignment, and scale.
- Repeated badges and metric chips create the illusion of structure without adding narrative value.

Fix:

- Set `layout_chrome_policy` before rendering.
- No card inside a visible parent card.
- No giant rounded parent container used only for grouping.
- No bottom mini-card row unless the slide is a real process, timeline, or agenda.
- No repeated numbered badges unless the numbers encode a real sequence.
- Ordinary slides may use at most 4 visible card-like foreground containers. Cover slides may use at most 3 metric chips.
- Prefer one dominant object plus one support zone; let empty space work.

## 6. Generic Evidence Rail

Symptom:

- Chart slides repeat the same left chart + right three bullets + vertical dot rail composition.
- The right side reads as notes, not as an insight.
- Dense charts are shrunk to make room for decorative bullets and rails.

Root cause:

- Evidence slides are treated as a reusable template instead of a proof moment.
- The generator extracts bullets but does not decide which number or conclusion matters most.

Fix:

- Every evidence slide must choose one treatment:
  - `full_chart`: chart owns 70-85% of the slide; detail goes into notes.
  - `chart_with_takeaway`: chart owns 55-65%; right side has one large conclusion/number plus at most 2 supports.
  - `chart_crop`: crop/zoom the critical area and cite the full chart in notes.
  - `chart_then_takeaway`: first slide shows the chart; next slide extracts implications.
- Do not use vertical timeline rails unless the slide is actually a timeline or process.
- No more than 2 consecutive evidence slides may use the same composition.

## 7. Cover as Dashboard

Symptom:

- The cover has a strong title, but also a metric grid, bottom card row, product badges, and heavy panels.
- The first slide feels like an admin console rather than a keynote opening.

Root cause:

- The generator tries to preview the whole deck on the cover.
- Proof objects are not prioritized, so every capability gets a card.

Fix:

- Cover slide should carry one big claim and at most 2-3 proof chips.
- Do not use bottom mini-card rows on covers.
- Avoid right-side dashboard panels unless the deck is explicitly a product UI walkthrough.
- Make the title or claim the largest object; metrics support it, not compete with it.

## 8. Baked-In Background Layout Objects

Symptom:

- Generated background images contain boxes, rectangles, card panels, frames, windows, placeholders, chart areas, or text-block zones.
- The slide looks structured, but those structures are trapped inside a bitmap and cannot be edited in PowerPoint.
- Foreground titles, charts, or cards have to fight a pre-baked container drawn by the background.

Root cause:

- The prompt asked for "chart-safe area", "card area", "dashboard background", or "evidence background" without forbidding actual UI/layout objects.
- The generator tried to solve page composition inside the background image.
- Background design and editable foreground layout were not separated.

Fix:

- Prompt backgrounds as atmosphere only: color fields, gradients, soft glow, subtle grain, abstract texture.
- Explicitly forbid boxes, rectangles, cards, panels, frames, placeholders, chart areas, image slots, UI chrome, text blocks, diagrams, and screenshots.
- Add cards, chart frames, labels, source images, and diagram structures later as editable PPT/HTML foreground objects.
- Record `background_asset_policy.atmosphere_only_policy` and `editable_foreground_policy` in `visual_contract.json`.

## 9. Fake Rounded Image Frame

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

## 10. Evidence Chart Legibility Drift

Symptom:

- Source charts are technically present but too small, dense, or low-contrast in presentation view.
- Bullets beside the chart compete with the evidence object.

Fix:

- For dense source charts, use one of three treatments:
  - `full_chart`: chart owns 70-85% of the slide, bullets become speaker notes.
  - `chart_crop`: crop/zoom one region and cite the full chart in notes.
  - `chart_then_takeaway`: first slide shows full chart, next slide extracts 2-3 callouts.
- Do not shrink a dense benchmark chart below the size where labels are readable in the rendered preview.

## 11. Visible Internal Provenance Footer

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

## 12. Shape Text Escape

Symptom:

- Text visually crosses a card, pill, formula block, callout, or diagram node border.
- The component looks acceptable in code coordinates, but rendered PPTX/PDF shows body text hanging below or outside the container.
- The slide feels broken even when the text itself is readable.

Root cause:

- The generator estimated text box height instead of checking rendered fit.
- The shape and the text box were created as separate objects without a shared content-box contract.
- Long CJK text was placed in a small rounded rectangle, leaving no slack for line wrapping differences across PowerPoint, Keynote, LibreOffice, and HTML.

Fix:

- Treat component overflow as a hard defect.
- Give every component a content box with real padding and vertical slack.
- Use short labels inside cards and move sentence-level explanations outside the frame when needed.
- If the text needs more than two lines in a small card, enlarge the card, split the idea, or remove the card.
- Inspect rendered previews, not just PPTX coordinates.

## 13. Connector Glyph Soup

Symptom:

- A chunky arrow or chevron contains another arrow, `x`, `+`, `=`, `≠`, or `?`.
- The slide looks like a UI widget or flowchart stencil rather than a professional presentation.
- Connectors, separators, pills, and cards compete for attention.

Root cause:

- The generator used block arrows as decorative separators.
- Operators were embedded inside arrow shapes instead of being expressed as relationships.
- The slide tried to create structure by adding more chrome rather than simplifying the reading path.

Fix:

- Prefer thin connectors, simple arrowheads, braces, or whitespace relationships.
- Put operators outside connector shapes as small standalone text only when the operator is truly part of the idea.
- Use block arrows only for explicit process-step graphics, never as the default relation marker.
- If a slide has heavy cards plus block arrows plus separator lines plus pills, remove at least one visual system.

## 14. Card And Separator Overload

Symptom:

- A slide contains several rounded cards, a long horizontal separator, multiple outlined pills, shadows, and connector arrows.
- The page is technically organized but feels crowded, noisy, and dashboard-like.
- The viewer sees the chrome before the idea.

Root cause:

- Cards were used to compensate for weak hierarchy and grouping.
- Separator lines were added as decoration, not because two reading zones needed separation.
- Every small sub-idea was boxed instead of letting alignment and whitespace carry grouping.

Fix:

- Start with one dominant proof object and one support zone.
- Use cards only for true contrast, comparison, or contained evidence.
- Replace bottom pill rows with direct labels, annotations, or speaker notes unless the slide is a real process/timeline.
- Use a separator only when it marks a meaningful zone boundary.
- In talk decks, prefer fewer frames, larger type, and cleaner whitespace over dense UI chrome.

## 15. Required Visual QA

Before calling a deck complete:

- Render the PPTX to PDF/images or open it in PowerPoint/Keynote and screenshot thumbnails.
- Inspect the thumbnail grid for repeated backgrounds, samey layouts, blank slides, and visual fatigue.
- Inspect every slide for color budget drift: max three active non-image colors, one accent.
- Inspect every slide for dashboard/card chrome: no nested cards, no giant parent panels, no filler bottom card rows, no repeated sequence badges without actual sequence meaning.
- Inspect evidence slides for repeated generic rails. A chart page should have a chosen proof treatment and one clear takeaway.
- Inspect generated backgrounds for baked-in layout objects. Regenerate backgrounds that include boxes, panels, cards, frames, placeholders, or chart/image slots.
- Inspect every slide for decorative linework. Remove lines that are not axes, table rules, connectors, separators, or real frames.
- Inspect every generated background for content fit. Regenerate or replace any
  background whose `content_link`, `background_duty`, or `semantic_anchor` does
  not match the visible slide claim.
- Inspect every chart/image slide for image overflow beyond the declared slot.
- Inspect visible slide text for internal provenance or speaker-cue leakage.
- Inspect every card, pill, callout, formula block, and diagram node for text escaping the visible shape.
- Inspect every connector for nested symbols, block-arrow clutter, and operator-in-arrow motifs.
- Inspect every slide for card/separator overload: if chrome dominates the idea, simplify before export.
- If a screenshot reveals a frame/clip problem, fix the generation method, not just that slide's coordinates.

## 16. Connector Lines Cut Through Nodes

Symptom:

- Connector lines pass through an oval/card/node and cross the label text.
- The line is visually louder than the shape and makes the diagram look careless.
- A concept map or loop looks like raw geometry construction instead of a finished presentation diagram.

Root cause:

- The generator drew center-to-center lines between node coordinates.
- Connectors were drawn after nodes, so they sat on top of text and fills.
- The spec described connector style but did not define connector ports, z-order, or stroke weight.

Fix:

- Define connector ports for every node: top, right, bottom, left, or an explicit anchor point on the node perimeter.
- Draw lines from perimeter to perimeter, never center to center. Leave a 4-10 px / 0.04-0.10 in visual gap from the node border unless the connector is intentionally attached.
- For ellipses and rounded rectangles, compute a clipped endpoint at the shape boundary or shorten the line by half the node width/height along the direction vector.
- Render connectors before opaque nodes, or send connectors behind the node layer, so a node fill hides any line segment that would otherwise cross the interior.
- Default stroke: 0.75-1.25 pt in PPTX, 1-2 px in SVG/HTML. Use muted colors at lower contrast. Avoid shadows on connectors unless the whole diagram style requires them.
- If ports create awkward crossings, use elbow/orthogonal connectors, curved arcs outside the nodes, braces, spatial grouping, or labels instead of forcing a line.
- Visual QA must zoom into every diagram slide and reject any connector that crosses text or a node interior.

## 17. Formal HTML Is Technically Present But Unusable

Symptom:

- `html/index.html` exists, but the page is hard to read, clipped, or visually unrelated to the PPTX.
- Text is too large/small after viewport scaling, slides overlap, navigation is unclear, or important content is hidden.
- The HTML output keeps only slogans while the PPTX carries the actual proof.

Root cause:

- HTML was treated as a secondary export rather than a real presentation surface.
- The HTML was hand-written from memory instead of generated from `slide_plan.json`, `content_contract.json`, and `visual_contract.json`.
- There was no browser readability check before claiming delivery.

Fix:

- Formal HTML must use the same slide plan, titles, proof objects, and concrete anchors as PPTX.
- Use a fixed 16:9 stage with responsive `scale()` or `aspect-ratio`, and verify desktop/laptop viewport readability.
- Put text in semantic DOM where practical; use SVG/Canvas only for charts, diagrams, generated backgrounds, and interaction.
- Provide keyboard navigation, progress indication, and visible focus/active states.
- Add `html_delivery_manifest.json` with `readability_qa`: viewport sizes checked, min font sizes, overflow policy, scaling strategy, and content parity policy.
- For decks over 7 slides, include the HTML version in the four-slide preview. If the preview is unreadable, fix HTML before full generation.

## 18. Full Deck Generated Before Preview Approval

Symptom:

- A long PPT is fully generated, then the user catches basic style, HTML, or diagram issues.
- Fixing one issue means reworking many slides, and the same mistake appears repeatedly.

Root cause:

- The generator treated proposal approval as permission to render everything.
- No intermediate visual proof existed for connector grammar, typography, background variety, or HTML delivery.

Fix:

- For any deck expected to exceed 7 slides, generate exactly a four-slide preview first.
- Pick preview slides from different roles: opening, dense proof/evidence, diagram/process, and breathing/turning-point/closing.
- Save `preview_gate.json` with selected slides, preview outputs, QA notes, and user decision.
- Continue to full generation only after the user approves or explicitly skips preview. Batch mode must record the skip reason.
