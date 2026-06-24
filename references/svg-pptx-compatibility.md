# SVG and PPTX Compatibility Rules

These rules are distilled for Qiaomu-owned SVG page authoring. They are not a copy of any upstream converter; they define the safest SVG subset for eventual editable PPTX export.

## Required

- `width`, `height`, and `viewBox` must all match the selected canvas.
- Use absolute coordinates in a fixed pixel canvas, default 1920 x 1080 for 16:9 decks.
- Use inline attributes for shape styling.
- Use HEX colors and `fill-opacity` / `stroke-opacity`; avoid `rgba()`.
- Keep text in real `<text>` nodes, not rasterized inside images.
- Use one logical line as one `<text>` where practical, with inline `<tspan>` for emphasis. Do not split adjacent inline emphasis into many separate `<text>` objects unless they are truly separate positioned labels.
- Escape XML-reserved characters: `&`, `<`, `>`, `"`, `'`.
- Use raw Unicode for normal punctuation and symbols.
- Wrap slide content in named top-level semantic groups. Aim for 3-8 top-level content groups per slide, excluding background and footer/chrome groups.
- Reuse the same group IDs in `layout_execution_contract`, final SVG pages, and `animations.json` when animations exist.
- For native SVG chart pages, include a stable plot-area marker such as `<rect id="chart-plot-area" ...>` inside the chart group so review/export tools can find the evidence object.

## Forbidden In Final SVG Pages

- `<style>` and CSS `class`
- external CSS
- `<foreignObject>`
- `<mask>`
- `<symbol>` / `<use>` reuse for visible objects
- `textPath`
- `@font-face`
- SVG animation tags
- scripts, event handlers, iframes
- group opacity as a layout shortcut
- image opacity as the only contrast control

## Conditional

- Clip paths only for image cropping. Use one simple clipping shape and apply it to the image, not to text, chart, diagram, or whole-slide groups.
- Arrow markers only for simple connector arrows. Use explicit polygon/path arrows for block arrows, and keep connectors attached to node edges or declared ports.
- Pattern fills only if the export path declares support.

## Preferred Alternatives

- Replace masks with overlays, gradients, or pre-baked images.
- Replace group opacity by setting opacity on child shapes.
- Replace HTML/CSS layout with explicit SVG groups and coordinates.
- Replace complex SVG filters with simple shadow/glow layers only when the export path supports them.

## Grouping Model

Top-level direct children of the slide SVG should be semantic groups, not loose
atoms. Good examples:

```xml
<g id="bg">...</g>
<g id="title-block">...</g>
<g id="chart-main">...</g>
<g id="annotation-01">...</g>
<g id="footer">...</g>
```

Naming guidance:

- Use `title-*` for title and subtitle groups.
- Use `proof-*`, `chart-*`, `table-*`, `diagram-*`, `process-*`, or
  `comparison-*` for the main evidence object.
- Use `media-*` for images, screenshots, generated art, and texture.
- Use `annotation-*`, `legend`, or `callout-*` for explanatory overlays.
- Use `bg`, `footer`, and `chrome-*` for non-animated deck chrome.

If a group is declared in `layout_execution_contract.group_ids`, it must exist
in the final SVG. If an animation targets a group, that group must exist in the
same slide SVG.

## Check Before Export

- No placeholder text such as TODO, TBD, lorem ipsum, `[必填]`, `SLIDES_HERE`.
- No text smaller than the route allows.
- No visible overlap, clipping, or off-canvas content.
- Images exist at the referenced paths.
- Speaker notes are present when required.
