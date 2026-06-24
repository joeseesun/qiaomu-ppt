# Content And Layout Execution

This reference defines how `qiaomu-ppt` turns content into page layout. It is
Qiaomu-owned production guidance distilled from local research and from our own
deck failures. It is not a runtime dependency on any upstream skill.

## Core Idea

Do not begin a slide by choosing a pretty template. Begin with the proof job.

Every slide needs three locks before rendering:

1. `content_semantics`: what the slide must make the audience understand,
   believe, remember, or do.
2. `layout_execution`: the concrete visual grammar that makes that proof
   visible.
3. `svg_object_model`: named editable objects and groups that can be checked,
   animated, and translated toward PPTX.

The slide is ready to draw only when these locks agree.

## Content Semantics

Each slide entry in `slide_plan.json` should answer:

- `claim_title`: a judgment, conclusion, action, or memorable phrase, not a
  label such as "背景" or "流程".
- `proof_object`: the one object that supports the claim. Examples: source
  chart, timeline, table, process, quote, screenshot, map, comparison, mechanism
  diagram, scene image, or big number.
- `content_chunks`: the visible pieces the audience should read. Most talk
  slides use 3-5 chunks; dense report/courseware pages may use more only when
  intentional.
- `spoken_note_goal`: what belongs in notes instead of on the canvas.
- `qa_risk`: the likely failure mode, such as table density, connector clutter,
  title overflow, weak source coverage, or image crop risk.

Hard rule: if a slide has no proof object, it is probably filler. Merge it,
rewrite it, or turn it into a breathing/chapter page with a clear role.

## Layout Execution Contract

`spec_lock.json` should contain `layout_execution_contract` once the deck has a
real rendering target.

Recommended shape:

```json
{
  "layout_execution_contract": {
    "canvas": {"w": 1920, "h": 1080, "safe_margin": [96, 80, 96, 80]},
    "coordinate_policy": "absolute_stage_coordinates",
    "text_fit_policy": "explicit line breaks; no foreignObject; shrink only within declared min/max",
    "slides": [
      {
        "slide_no": 1,
        "slide_id": "P01",
        "rhythm": "anchor",
        "claim_title": "One dominant sentence",
        "proof_object": "scene image plus three proof chips",
        "layout_pattern_id": "L04",
        "component_type": "full_bleed_image_claim",
        "reading_path": "title -> subtitle -> chips",
        "coordinate_slots": [
          {"slot_id": "hero", "x": 0, "y": 0, "w": 1920, "h": 1080},
          {"slot_id": "title", "x": 120, "y": 140, "w": 940, "h": 220}
        ],
        "group_ids": ["hero", "title-block", "proof-chips", "footer"]
      }
    ]
  }
}
```

Required per-slide fields:

- `rhythm`: `anchor`, `dense`, or `breathing`.
- `proof_object`: the semantic object doing the proof.
- `layout_pattern_id`: concrete ID from `layout-pattern-library.md`.
- `component_type`: a renderable component family, not a vague mood word.
- `reading_path`: first-look order.
- `coordinate_slots`: absolute boxes for important title, proof, media, chart,
  table, or diagram regions.
- `group_ids`: top-level SVG/PPT object groups for editing, QA, and animation.

## Component Choice

Map content shape to layout/component before drawing:

| Content Shape | Prefer Component | Notes |
|---|---|---|
| 3-6 ordered steps | `numbered_steps` / L13-L16 | Use sequence numbers and light connectors; avoid paragraph boxes with arrows. |
| Time milestones | `timeline` / L14 | Use only when x-axis time is meaningful. |
| 2-4 alternatives | `comparison_columns` / L08-L12 | Make basis of comparison explicit. |
| Many records | `basic_table` / L22 | Tables must have type scale and row-height budget. |
| One source chart | `chart_with_takeaway` / L20 | Chart is the proof; do not shrink it below legibility. |
| Cause/mechanism | `mechanism_loop` / L18/L27-L30 | Diagrams need labeled relationships, not decorative icons. |
| Parallel categories | `icon_grid` / L23/L28 | Icons must label semantic categories, not fill empty space. |
| Strong scene/object | `full_bleed_image_claim` / L04 | The image carries context; text overlays must remain readable. |
| Definition or principle | `claim_plus_model` / L03/L24 | Use a model, formula, or contrast, not bullets alone. |
| Closing/action | `closing_memory_hook` / L35 | One memorable action beats many recap bullets. |

## SVG Object Model

For SVG-first/PPTX-oriented output, author pages as editable object groups.

Layer order:

1. `bg`: base surface and non-semantic texture.
2. `media-*`: images, screenshots, or generated art.
3. `title-*`: title, subtitle, eyebrow, section mark.
4. `proof-*`: chart/table/process/diagram groups.
5. `annotation-*`: callouts, labels, legends.
6. `footer`: page number, optional section label, or visible citations when
   explicitly requested.

Top-level groups should be named with stable semantic IDs:

```xml
<g id="title-block">...</g>
<g id="process-banner">...</g>
<g id="step-01">...</g>
<g id="step-02">...</g>
<g id="legend">...</g>
```

The same IDs may be referenced by:

- `animations.json`
- visual QA scripts
- SVG-to-PPTX conversion
- manual PowerPoint/Keynote editing

Avoid anonymous piles of shapes. If an object should move, animate, be edited,
or be checked as one unit, it needs a group ID.

## Text Layout

- Use real SVG `<text>` and `<tspan>` nodes.
- Use explicit coordinates and line breaks.
- Set minimum and maximum type sizes in `spec_lock.json`.
- Keep title visually dominant unless the slide is deliberately number-led or
  quote-led.
- Do not rely on browser wrapping, CSS classes, `<foreignObject>`, or hidden
  overflow to make text fit.
- Put nuance, caveats, and extra examples into speaker notes.

## Image And Texture Treatment

Generated or source images should have a declared `image_slot` and a role:

- `hero_page`
- `evidence`
- `background_atmosphere`
- `local_illustration`
- `scenario`
- `object_cutaway`
- `texture`

Images can carry mood, scene, object shape, or evidence. They must not bake in
editable slide structure such as cards, charts, tables, labels, title blocks, or
placeholder frames.

Texture should be a controlled foreground/background layer. For print-inspired
styles this may include paper grain, halftone dots, registration offsets, ink
overlap, and rough edges. These effects should not hide text or replace content
hierarchy.

## Print/Zine Style Pattern

When the selected direction is risograph, zine, DIY publishing, or indie print:

- Use a warm paper base and one dominant ink color plus one accent.
- Simulate registration offset with duplicate shapes/text shifted 1-3 px.
- Use halftone patterns sparingly as texture, not as a busy background.
- Prefer hard rectangular edges over glossy rounded cards.
- Keep the same image rendering and palette behavior across the deck.
- Let big typography overlap image edges when it clarifies the poster rhythm.

This is a style preset pattern, not a default for all decks.

## Animation Sidecar

If animations are used, record them in `animations.json` using the same group
IDs as the SVG pages:

```json
{
  "slides": {
    "06_process": {
      "transition": {"effect": "fade", "duration": 0.3},
      "groups": {
        "process-banner": {"effect": "wipe", "order": 1},
        "step-01": {"order": 2},
        "step-02": {"order": 3}
      }
    }
  }
}
```

Animations must follow the reading path. They are not a decoration layer.

## QA Checklist

- Does every non-navigation slide have a proof object?
- Does the component type match the proof object?
- Does `layout_pattern_id` exist in the layout library?
- Do coordinate slots cover title and proof areas?
- Are SVG group IDs present and stable?
- If `animations.json` exists, do its group IDs exist in SVG?
- Does visible copy stay within the slots?
- Are images and textures subordinate to content?
- Can a reviewer understand the deck by scanning titles and proof objects?
