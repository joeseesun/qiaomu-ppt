# Reference System

This document records how `qiaomu-ppt` absorbs external PPT reference research
into a Qiaomu-owned production system. It is a local method, not a runtime
dependency on any upstream skill.

## Separation Of Concerns

A good deck should not mix narrative, style, image rendering, and SVG execution
into one vague prompt. Lock these layers separately:

| Layer | Question | Qiaomu Artifact |
|---|---|---|
| Deck mode | What argument or teaching skeleton drives the whole deck? | `content_contract.structure_framework`, `spec_lock.narrative_mode` |
| Visual style | What shape language, typography behavior, texture, and spatial rhythm should the deck use? | `style_brief.md`, `visual_contract.json`, `spec_lock.visual_style` |
| Image rendering | How should generated/local images be drawn? | `visual_asset_manifest.json`, `image_generation_model.rendering` |
| Image palette behavior | How should image colors behave relative to the deck palette? | `image_generation_model.palette_behavior` |
| Image type | What internal geometry should a local infographic image use? | `image_generation_model.type_template` |
| Image layout | Where does the image sit, and what native SVG layer sits over or beside it? | `visual_contract.image_slots`, `layout_execution_contract.coordinate_slots` |
| SVG object model | Which editable groups make the slide testable and portable? | `layout_execution_contract.group_ids`, SVG `<g id="...">` |
| Visual review | What static and rendered defects must be fixed before export? | `check_project.py`, `qa_report.md` |

The strongest habit is to name each layer before rendering. If the output only
has a style adjective such as "premium", "zine", or "tech", the plan is not
specific enough.

## Deck Modes

Use one primary mode per deck. Mode is the rhetorical skeleton, not the visual
look.

| Mode | Use | Content Rule |
|---|---|---|
| `pyramid` | executive argument, strategy, recommendation | Titles are conclusions; evidence ladders toward a decision. |
| `narrative` | launch, creator talk, persuasive essay | State transfer matters: old belief -> tension -> turn -> proof -> new belief. |
| `instructional` | courseware, tutorial, workshop | Learner state matters: prerequisite -> concept -> example -> practice -> check. |
| `showcase` | portfolio, product or case display | Objects and before/after proof carry the story. |
| `briefing` | status, update, situation room | Clarity, recency, risk, next action, and source confidence beat drama. |

Record the chosen mode in the design proposal and `spec_lock.json`. A user
outline can override reshaping, but the mode still governs titles, slide order,
and speaker-note emphasis.

## Visual Styles

Style is the surface grammar: shape, spacing, texture, typography, elevation,
and decorative restraint. It is not the HEX palette by itself.

Examples:

- `swiss_minimal`: strict grid, flat geometry, sparse color, strong alignment.
- `zine`: cut-and-paste blocks, hard edges, rough print texture, poster type.
- `editorial`: magazine-like hierarchy, large text/image tension, confident
  whitespace.
- `blueprint`: linework, technical annotations, precise measurements.
- `data_journalism`: evidence-first charts, labels near data, calm annotation.

Do not apply a style by copying a template. Translate it into local decisions:
canvas, type scale, max active colors, image use, group structure, and forbidden
moves. Palette comes from the selected Qiaomu visual contract; style only says
how those colors behave.

## Image Generation Model

For every generated or sourced image, separate three decisions:

```json
{
  "image_id": "cover_scene",
  "page_role": "hero_page",
  "rendering": "screen_print",
  "palette_behavior": "duotone",
  "type_template": null,
  "text_policy": "none",
  "layout_pattern": "image_layout_01_full_bleed_background",
  "native_overlay_policy": "title, chips, labels, charts, and Chinese text stay editable SVG"
}
```

Rules:

- Use one deck-wide rendering family when the images are meant to feel unified.
- Use one deck-wide palette behavior unless a source image must remain faithful.
- Use image type templates only for local infographic images. Hero pages use
  hero primitives instead of infographic skeletons.
- `text_policy: none` is the default. Chinese labels, numbers, charts, tables,
  and diagrams belong in native SVG/PPTX objects.
- Generated images may carry atmosphere, scene, object shape, or texture. They
  must not bake in cards, titles, charts, tables, UI chrome, or placeholders.

## Image Layout Vocabulary

A page image layout has two parts:

1. Primary structure: full-bleed, thirds, banner, strip, sidebar, montage,
   small multiples, etc.
2. Modifier layers: scrim, fade, crop, callout lens, hotspots, annotation cards,
   native chart overlay, native diagram overlay, texture overlay.

The key production move:

> Image carries atmosphere, world-building, or object context. Native SVG/PPTX
> carries information, data, editable text, labels, and accurate diagrams.

Therefore a rich image slide should rarely be "image on left, bullets on
right" only. Prefer combinations such as:

- full-bleed scene + native annotation cards and leader lines
- evidence screenshot + native magnified lens and labels
- product image + numbered hotspots + sidebar legend
- background atmosphere + native process route through the scene
- generated dashboard atmosphere + native data chart on top

Use `scripts/plan_image_layouts.py` when source/user/web images exist. It reads
image dimensions, applies the confirmed `canvas_format`, and proposes
ratio-driven `image_area`, `text_area`, fit policy, and multi-image slots for
the `visual_contract` or `layout_execution_contract`. Side-by-side evidence
images use `xMidYMid meet`; hero/background roles may crop only by explicit
intent.

## SVG Execution Standards

SVG pages are production objects, not final screenshots. Use:

- a fixed `viewBox` matching the canvas
- real `<text>` and `<tspan>` nodes
- inline attributes instead of CSS classes
- top-level semantic groups such as `title-block`, `chart-main`, `step-01`
- 3-8 top-level content groups per slide, excluding chrome groups
- a chart plot marker such as `chart-plot-area` inside chart groups
- group IDs shared by `layout_execution_contract`, SVG files, and
  `animations.json`

Avoid anonymous piles of paths. If an object should animate, be edited, or be
checked as one unit, give it a stable group ID.

## Visual Review Loop

Run review in this order:

1. Static SVG/HTML/project contract checks.
2. Rendered screenshots or thumbnails.
3. Hard visual defect pass: out-of-bounds, overlap, contrast, broken images,
   hidden title/proof object, text overflow.
4. Soft visual quality pass: rhythm too tight or hollow, alignment drift,
   accent overload, CJK spacing issues, image-text relationship, breathing-page
   violations.
5. Focused fixes only. Do not quietly redesign the whole page during a QA fix.

The review question is not "does it look fancy?" It is "does the page make the
claim easier to understand, verify, and present?"
