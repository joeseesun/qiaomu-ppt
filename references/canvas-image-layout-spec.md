# Canvas And Image Layout Spec

Use this reference when a deck, poster, social image, article header, or image-rich
page needs a target aspect ratio or image/text layout plan.

## Core Split

Keep these decisions separate:

- `canvas_format`: the output surface and viewBox, such as `ppt169`, `ppt43`,
  `xiaohongshu`, `moments`, `story`, `wechat`, `banner`, or `a4`.
- `narrative_intent`: how the image functions on the page: `hero`,
  `atmosphere`, `side-by-side`, or `accent`.
- `image_layout_pattern`: the visual vocabulary, such as ITL or
  image-layout-pattern ids.
- `computed_slots`: exact `image_area`, `text_area`, fit mode, and safe area
  derived from the real image dimensions.

Do not let one style word decide all four. The format chooses the stage; the
intent chooses whether ratio math applies; the layout pattern chooses the page
language; computed slots prevent stretched, cropped, or unreadable images.

## Canvas Formats

The canonical Qiaomu data file is `data/canvas_format_specs.json`.

Common formats:

| Key | ViewBox | Use |
|---|---|---|
| `ppt169` | `0 0 1280 720` | normal widescreen PPT |
| `ppt43` | `0 0 1024 768` | traditional projector or academic PPT |
| `xiaohongshu` / `xhs` | `0 0 1242 1660` | RED image-text post |
| `moments` | `0 0 1080 1080` | WeChat Moments / Instagram square |
| `story` | `0 0 1080 1920` | vertical story or phone poster |
| `wechat` | `0 0 900 383` | WeChat article header |
| `banner` | `0 0 1920 1080` | web banner or digital screen |
| `a4` | `0 0 1240 1754` | print poster/flyer |

Current production boundary: the SVG-first editable PPTX renderer is still
optimized for `ppt169`. Other formats are supported as planning, SVG-quality,
HTML/social/poster, and future-renderer contracts unless a project-specific
renderer has been written for that canvas. Do not claim final editable PPTX
multi-canvas support without actual exported evidence.

## Side-By-Side Ratio Rule

For `narrative_intent: side-by-side`, calculate slots from the source image's
actual width/height ratio. Do not use a fixed 50:50 split.

Rule of thumb on landscape or square canvases:

- ratio `> 2.0`: top image + bottom text.
- ratio `1.5-2.0`: top/bottom unless text volume is high, then constrained
  left/right.
- ratio `1.2-1.5`: left image + right text.
- ratio `0.8-1.2`: left image + right text.
- ratio `< 0.8`: tall image + side text.

Portrait canvas override:

- wide, standard, and square images usually use top/bottom stacking.
- portrait or extreme portrait source images may use left/right because the
  image itself fits the tall canvas.

Validation:

- Top/bottom text area must remain tall enough to read.
- Left/right text area must remain wide enough to read.
- Side-by-side evidence images use `preserveAspectRatio="xMidYMid meet"`.
- Hero/background/atmosphere images may use `xMidYMid slice` only when crop is
  intentional and foreground text stays in the safe area.

## Automation

Run:

```bash
python3 scripts/plan_image_layouts.py <image-or-dir> --format ppt169 \
  --output <project>/image_layout_plan.json \
  --markdown <project>/image_layout_plan.md
```

Other examples:

```bash
python3 scripts/plan_image_layouts.py <dir> --format xhs
python3 scripts/plan_image_layouts.py <dir> --format story --text-volume high
python3 scripts/plan_image_layouts.py <dir> --canvas 1920x1080 --safe-margin 96,80,96,80
python3 scripts/plan_image_layouts.py <dir> --intent hero
```

The output fields to hand off are:

- `canvas_format`
- `canvas.viewBox`
- `image_area`
- `text_area`
- `recommended_layout`
- `layout_type`
- `preserve_aspect_ratio`
- `pattern_candidates`
- `decision_signals`
- `multi_image_plan`

Copy these into `visual_contract.json`, `spec_lock.json`, or relevant
`visual_asset_manifest.json` rows before rendering.

## Text Clearance Contract

Image slots are not allowed to drift into live text regions. Before rendering a
media-rich slide, declare protected boxes for the title, body, proof objects,
captions, footers, and the image slot. Then check clearance.

Recommended minimums:

- `xiaohongshu` / `1242x1660`: `48px` minimum gap between image and live text.
- `ppt169` / `1280x720`: `28px` minimum gap between image and live text.
- PPTX native units: `0.22in` minimum gap.

If boxes overlap or the clearance is below the minimum, fix the contract before
rendering:

- reduce the title measure so it wraps before the image column;
- move the image into a dedicated slot;
- shrink the image and increase surrounding negative space;
- switch from side-by-side to top/bottom, or from hero to editorial caption;
- move long explanatory copy out of the image band.

Do not fix accidental collisions by adding a shadow, scrim, or opacity layer.
Those are image-integration tools, not layout-collision tools.

## Image Finish Policy

Source images often look pasted-on when inserted raw. Each substantial image
slot should declare a finish policy:

- real clipping/masking when using rounded corners;
- `contain` for evidence and `cover` only for atmosphere/hero images;
- a 1-3 px low-contrast border or hairline when the image edge needs definition;
- a subtle shadow on light paper only when it separates the image from the
  surface without becoming a card;
- local color/contrast normalization so a source image does not fight the deck
  palette;
- enough surrounding negative space so the image feels placed, not crammed.

Avoid heavy shadows, glossy photo frames, fake rounded frames, and decorative
cards behind every image. If the image is evidence, clarity beats polish.

## Multi-Image Pages

For multiple images, use the generated `multi_image_plan`:

- 2 landscape/square images: side-by-side 2x1.
- 2 portrait images: stacked 1x2.
- 3 images: one large + two small.
- 4 images: 2x2 grid.
- 5-6 images: 3-column grid unless a stronger editorial collage is specified.

Use the same crop/fit logic within an image group. Captions, before/after
labels, panel labels, and source notes stay editable.

## Anti-Patterns

- fixed 50:50 split regardless of source ratio
- forcing a wide image into a square slot
- placing a portrait image in a shallow horizontal strip
- cropping source evidence to make it look decorative
- using `slice` for paper figures, screenshots, formula renders, or source charts
- leaving text area too narrow or too short to read
- baking Chinese text, chart labels, citations, or data into the image
