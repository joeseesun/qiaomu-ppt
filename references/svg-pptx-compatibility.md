# SVG and PPTX Compatibility Rules

These rules are distilled for Qiaomu-owned SVG page authoring. They are not a copy of any upstream converter; they define the safest SVG subset for eventual editable PPTX export.

## Required

- `width`, `height`, and `viewBox` must all match the selected canvas.
- Use absolute coordinates in a fixed pixel canvas, default 1920 x 1080 for 16:9 decks.
- Use inline attributes for shape styling.
- Use HEX colors and `fill-opacity` / `stroke-opacity`; avoid `rgba()`.
- Keep text in real `<text>` nodes, not rasterized inside images.
- Use one logical line as one `<text>` where practical, with inline `<tspan>` for emphasis.
- Escape XML-reserved characters: `&`, `<`, `>`, `"`, `'`.
- Use raw Unicode for normal punctuation and symbols.

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

- Clip paths only for image cropping, and only when the target converter supports it.
- Arrow markers only for simple connector arrows. Use explicit polygon/path arrows for block arrows.
- Pattern fills only if the export path declares support.

## Preferred Alternatives

- Replace masks with overlays, gradients, or pre-baked images.
- Replace group opacity by setting opacity on child shapes.
- Replace HTML/CSS layout with explicit SVG groups and coordinates.
- Replace complex SVG filters with simple shadow/glow layers only when the export path supports them.

## Check Before Export

- No placeholder text such as TODO, TBD, lorem ipsum, `[必填]`, `SLIDES_HERE`.
- No text smaller than the route allows.
- No visible overlap, clipping, or off-canvas content.
- Images exist at the referenced paths.
- Speaker notes are present when required.
