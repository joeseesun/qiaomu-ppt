# Chart And Diagram Components

Use this routing guide when a slide needs richer charts, diagrams, or generated visuals while keeping the deck coordinated.

## Principle

Do not choose a charting component because it looks impressive. Choose it from the information job:

- `comparison`: compare categories, alternatives, before/after, rank.
- `trend`: show movement over time.
- `composition`: show parts of a whole, but avoid default pies unless the story is truly part/whole.
- `distribution`: show spread, outliers, range, uncertainty.
- `relationship`: show correlation, network, dependency, causality candidates.
- `process`: show ordered steps, state changes, system flow.
- `architecture`: show components, boundaries, data/control flow.
- `concept`: show a mental model, metaphor, or explanatory frame.

The slide should still have one dominant claim. Charts and diagrams are proof objects, not decoration.

## Visual Component Planning

Before rendering, write a per-slide visual component plan. This belongs in the design proposal and later in `slide_plan.json` or `visual_contract.json`.

For decks longer than 8 slides:

- Use at least 4 layout families unless the user explicitly requests a minimalist keynote.
- Use at least 2 non-card explanatory visual components when the source is conceptual or essay-like: mechanism loop, tension map, boundary matrix, process, decision tree, mental model, annotated quote, or causal chain.
- Use at least 1 real chart/table/structured evidence component when the source contains data or comparisons.
- Do not count generic cards, bullets, metric chips, or decorative icons as diagrams.
- If no chart or diagram is appropriate, document why in the design proposal.

Good article-to-PPT visual components:

| Source Pattern | Better Component |
|---|---|
| two opposing ideas | split comparison or tension scale |
| hidden mechanism | loop, flywheel, causal chain |
| author's boundary conditions | 2x2 matrix or applicability map |
| repeated method | process sequence with verbs |
| analogy | side-by-side mapping diagram |
| objection/answer | argument tree or rebuttal stack |

Failure signs:

- every slide is title + paragraph + card.
- the deck has no chart, no diagram, no annotated quote, and no visual model.
- diagrams are only arrows between boxes without a new understanding.
- generated images are used as decoration while the core argument remains visually unexplained.

## Component Routing

### Data Charts

Use these components when the slide has structured data.

- `Apache ECharts`: best for polished presentation charts, mixed chart types, maps, network/graph, sankey, treemap, sunburst, heatmap, dashboards, and interactive HTML outputs. Render to SVG/PNG before PPTX insertion when editability or portability matters.
- `Observable Plot`: best for concise, clean statistical charts from tabular data: line, bar, area, dot, rule, text labels, faceting, small multiples, distributions, and exploratory charts that need fast iteration.
- `Vega-Lite`: best for declarative JSON chart specs, reproducibility, layered statistical graphics, multi-view charts, and when a chart spec should be saved as a sidecar artifact.
- `Matplotlib/Seaborn`: best for offline Python routes, academic/scientific charts, distributions, uncertainty bands, and environments without browser rendering.

Rules:

- Prefer bar/dot/lollipop/slope charts for comparisons.
- Prefer line/area/small multiples for trends.
- Prefer histogram/box/violin/ridgeline for distributions.
- Prefer scatter/bubble with direct labels for relationships.
- Prefer heatmap/table sparklines for matrix comparisons.
- Prefer waterfall, bridge, or stacked bar only when the arithmetic is central.
- Avoid 3D charts, default pies, gauge charts, and rainbow categorical palettes unless the route explicitly calls for them.
- Use direct labels whenever possible; legends are a last resort on presentation slides.
- Export chart source specs under `<project>/charts/` and rendered assets under `<project>/assets/charts/`.

### Diagrams

Use these components when the slide explains structure, sequence, or logic.

- `Mermaid`: best for quick flowcharts, sequence diagrams, state diagrams, Gantt-like plans, user journeys, and simple architecture sketches. Good for source-controlled diagram specs.
- `Graphviz/DOT`: best for dependency graphs, trees, DAGs, layout-stable networks, and compiler/system diagrams.
- `Excalidraw-style SVG`: best for teaching, rough conceptual explanation, hand-drawn story framing, and friendly internal talks.
- `React Flow` or DOM/SVG custom layout: best for interactive HTML presentations, node-link editors, product flows, and architecture diagrams with rich labels.
- `D3/SVG custom`: best when the diagram has non-standard geometry or needs exact editorial control.

Rules:

- Diagrams must declare node types, edge meanings, reading direction, and scope boundary.
- Do not use arrows as decoration. Arrows mean sequence, dependency, causality, or flow.
- Do not put more than 7 primary nodes on one slide unless it is a full evidence slide.
- Use icon labels only when icons add recognition; otherwise text labels are clearer.
- Store diagram source under `<project>/diagrams/` and rendered assets under `<project>/assets/diagrams/`.

## Shape Component Fit

Every editable visual component must fit its own content before the slide can pass review.

- Cards, pills, formula blocks, callouts, and diagram nodes need real internal padding. Default to at least 0.18-0.28 inches on small components and 0.28-0.42 inches on large cards.
- Text must remain inside the visible shape in the rendered PPTX/PDF preview. If a paragraph crosses the border, the correct fix is to enlarge the component, shorten the copy, split it into two components, or remove the container.
- Avoid long body copy inside small rounded rectangles. Use unframed body text next to a small label when the content needs more than two lines.
- Pills are for one short label only. They should not contain sentence-level content.
- Do not use a rounded card merely to make content feel designed. If proximity, alignment, or whitespace already groups the content, keep it unframed.
- When using PowerPoint shapes, account for renderer differences between PowerPoint, Keynote, LibreOffice, and HTML. Leave extra vertical slack rather than fitting to the exact text box height.
- Record reusable component constraints in `visual_contract.json.shape_component_policy`.

## Connector Grammar

Connector style carries meaning. Keep it quiet and legible.

- Prefer thin connector lines, simple arrowheads, braces, or whitespace relationships.
- Chunky chevrons and block arrows are allowed only for a deliberate process-step graphic; they are not default connectors.
- Never place `→`, `x`, `+`, `=`, `≠`, `?`, or similar symbols inside arrow or chevron shapes. This creates nested symbols and reads as cheap UI chrome.
- If an operator matters, place it as small standalone text between two objects, or use a caption such as `multiplies`, `not equal to`, or `leads to`.
- One slide should not combine heavy cards, block arrows, separator rules, pills, and shadows unless the route explicitly calls for a dense process map. For talks, choose one dominant component system.
- Horizontal separator lines are allowed only when they separate two real reading zones. A line used to make the slide feel structured is filler.

## Coordination Rules

Richer charts/diagrams must still belong to one visual system.

- Reuse the deck's type scale, color budget, corner radius, grid, and label style.
- Use neutral surfaces for dense charts; let the data be the visual object.
- Use one accent family per slide. If a chart needs many categories, mute non-focus categories and highlight only the story.
- Match stroke widths, label sizes, and annotation style across charts and diagrams.
- Prefer directly labeled annotations over separate explanatory cards.
- Keep source data/specs as sidecars so charts can be regenerated.

## Codex Image Generation Usage

When built-in image generation is available, use it as the default route for presentation imagery that benefits from visual atmosphere or metaphor. Do not use it to bake editable layout into the background.

Good uses:

- `chapter_art`: abstract editorial visual for section opens.
- `concept_metaphor`: one symbolic image that makes an abstract idea memorable.
- `scenario_illustration`: a realistic or stylized scene representing a user, classroom, product context, or market moment.
- `object_cutaway`: product/material/technology visualization when no real asset exists.
- `texture_pack`: quiet atmospheric backgrounds with no text, panels, frames, chart slots, or UI.
- `case_moodboard`: 2-4 related images for brand direction exploration before final production.

Forbidden uses:

- Text, titles, bullet points, charts, tables, logos, UI panels, card layouts, image frames, or source citations baked into the image.
- Fake screenshots or fake data evidence.
- Generated images that replace a real product screenshot, real chart, or source evidence the user expects to inspect.

Workflow:

1. Decide whether the image is `evidence`, `metaphor`, `atmosphere`, or `story`.
2. If it is evidence, prefer real source assets or charts over image generation.
3. Generate 3-5 candidate images only for open visual choices.
4. Place generated images in declared slots with `fit`, crop rationale, and `overflow_policy: clip_or_fail`.
5. Keep foreground text, charts, labels, callouts, and frames editable in PPTX/HTML.

In Codex, make this decision explicit. If image generation is available but not used, write the reason, such as source-only evidence, user forbids generated imagery, deterministic build required, or visual risk outweighs benefit. Silence counts as a missed design decision.

## PPTX Export Policy

- For editable PPTX, render complex charts/diagrams to SVG when possible; use PNG only when SVG compatibility fails or the renderer output is raster by nature.
- For HTML final decks, keep interactive charts live if useful, but also export a static fallback image.
- For PPTX parity HTML previews, render the PPTX pages and use `html_from_previews.py`; this produces preview-only `html-parity/` and `*.parity.html` artifacts, not the formal semantic HTML deck.
- Always include chart/diagram source files in the project folder, not inside the installed skill directory.
