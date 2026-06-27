# Procedural Backgrounds

Use this when image generation is unavailable, forbidden, too expensive, or too slow. The goal is not to draw the slide layout in code. The goal is to create quiet atmosphere-only background assets that support editable foreground PPT objects.

## Core Rule

Procedural backgrounds obey the same separation as image-generated backgrounds:

- Allowed: color fields, CSS gradients, radial light, soft noise, subtle grain, particles, mathematical texture, organic flow, abstract marks, and gentle depth.
- Forbidden: text, letters, numbers, logos, icons, UI chrome, boxes, rectangles used as content containers, cards, panels, frames, windows, chart areas, image slots, grids, neon rails, dashboards, screenshots, mockups, and layout scaffolding.
- All titles, body copy, callouts, chart frames, picture masks, diagrams, and cards must be editable foreground objects added after the background.

## Decoration Budget

Before drawing procedural lines, grids, streaks, particles, or orbital paths,
choose a budget from `data/background_decoration_budgets.json` and record it in
`visual_contract.json`, `spec_lock.json`, or `html_delivery_manifest.json`.

- Use `quiet` for normal body slides: 0-1 decorative line family, no global
  tech-line overlay, and no decorative line crossing title/body/proof zones.
- Use `moderate` only when linework expresses a map, timeline, process, orbit,
  or reading path.
- Use `cinematic` mainly for cover, chapter, and closing slides. Body slides
  may use it only when the line itself is the proof object.
- If the preview feels busy, remove whole line families first. Do not fix noisy
  backgrounds by only lowering opacity.
- Procedural linework still needs a semantic purpose from
  `data/line_semantics_policy.json`. Mood words such as energy, speed, tech,
  atmosphere, texture, and decoration are not acceptable purposes. CSS border
  rings, pseudo-element rays, and gradient stripes follow the same rule.

## Default Pack

Generate 5 roles per deck:

1. `cover_atmosphere`
2. `dark_evidence`
3. `light_evidence`
4. `diagram_focus`
5. `closing_atmosphere`

Use a deterministic seed and record it in `visual_contract.json`, so the deck can be rebuilt.

## Engine Choice

For editable PPTX:

- Prefer deterministic SVG or Python/Pillow backgrounds because they export predictably.
- Canvas/WebGL outputs must be rendered to static PNG/SVG before PPTX insertion.
- Avoid runtime-only backgrounds unless the final delivery is HTML.

For HTML preview:

- CSS gradients and pseudo-elements are the lightest path.
- Canvas is good for particles, noise, flowing fields, and generative marks.
- WebGL/shaders are allowed only when the background remains quiet and does not compete with text.

## Library Palette

Use libraries as optional engines, not runtime requirements:

- `canvas-sketch`: sketch-oriented generative background prototyping.
- `p5.js`: friendly creative coding for particles, noise, and organic motion.
- `Pts.js`: mathematical point/line/shape systems.
- `Paper.js`: vector path generation and organic contours.
- `Two.js`: renderer-independent 2D drawing when SVG/Canvas/WebGL parity matters.
- `Zdog`: subtle pseudo-3D flat forms; avoid illustrative objects unless the deck asks for them.
- `Simplex-noise` or `Noise.js`: organic flow fields and grain.
- `GLSL Canvas`, `Regl`, `OGL`, or `Curtains.js`: shader/WebGL backgrounds for HTML preview, then rasterize for PPTX.
- `Motion Canvas`, `Theatre.js`, or `Anime.js`: timed background motion for web decks; static export for PPTX.

Do not add these as hard dependencies unless a project actually uses them. Public skill outputs must still work through SVG/Python fallback.

## Recommended Patterns

### Quiet Gradient Field

- Use 2-3 large blurred radial gradients.
- Keep accent below 8-12% of the frame.
- Add subtle grain to prevent flatness.

### Flow Field

- Use low-alpha curved paths or particles driven by simplex noise.
- Keep paths sparse and low contrast.
- Do not create rail-like lines or chart-like grids.

### Mathematical Texture

- Use points, soft blobs, contours, or interference fields.
- Keep any repeated pattern non-rectilinear and non-layout-like.
- Fade texture near text-heavy zones.

### SVG Fallback

- Use gradients, filters, turbulence, and large abstract shapes.
- Avoid hard rectangles that read as panels.
- Keep the SVG self-contained and static for PPTX compatibility.

## Required Contract Fields

Record the chosen fallback in `visual_contract.json`:

```json
{
  "background_asset_policy": {
    "mode": "procedural_svg_pack",
    "procedural_fallback_policy": "image generation unavailable; generated 5 deterministic SVG atmosphere-only backgrounds",
    "procedural_engine": "svg",
    "seed": "qiaomu-ppt:<deck-subject>",
    "forbidden_generated_objects": ["box", "card", "panel", "frame", "placeholder", "chart area", "image slot", "ui chrome", "text block"]
  }
}
```

## QA

- Render thumbnails and inspect the background at slide size.
- If the background implies an editable content area, frame, or dashboard, regenerate.
- If procedural marks read as decorative linework, remove or soften them.
- If a chart/image is colorful, reduce background contrast and saturation.
