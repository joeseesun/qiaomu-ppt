# Icon Assets

Use icons when they clarify a concept, label a repeated semantic role, or create a restrained semantic watermark. Do not use icons as filler decoration.

## Sources

Primary local source:

- `/Users/joe/Documents/qm-icon-studio`

That project provides:

- a small offline built-in SVG path library in `js/icons.js`
- Chinese and English keyword metadata
- optional candidate generation for app/site/logo icons

Network-capable source:

- Iconify API can query and export common open-source sets such as Lucide, Heroicons, Tabler, Phosphor, Material Symbols, MDI, Carbon, and Radix Icons.
- Lucide is ISC licensed. Heroicons is MIT licensed. Record provider, collection, license, source URL, and exported file path in the project manifest when used.

## Search

Search local built-ins only:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/icon_search.py "增长 用户 传播" --limit 8
```

Search local plus preferred public icon sets and export SVGs:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/icon_search.py "pencil writing edit" \
  --iconify \
  --sets lucide,heroicons,tabler \
  --limit 12 \
  --color '#161410' \
  --export-dir <project>/assets/icons
```

Supported common `--sets` aliases:

- `lucide`
- `heroicons` / `heroicon`
- `tabler`
- `ph` / `phosphor`
- `material` / `material-symbols`
- `mdi`
- `carbon`
- `radix`

## Per-Slide Icon Watermark Workflow

Icon watermarks are opt-in. Use them only for styles where they clearly strengthen the visual system. For designs where typography, whitespace, charts, or diagrams already carry the page, prefer no watermark. If a preview review says the watermark feels distracting, stop tuning opacity/position and set `mode: disabled_for_this_style`.

For decks where subtle icon watermarks can strengthen the visual system, create `icon_watermark_plan.json` before rendering:

```json
{
  "mode": "semantic_icon_watermark",
  "style": "single-outline-or-single-solid",
  "opacity_range": "outline 0.08-0.16 or solid 0.03-0.08, adjusted by background contrast",
  "max_icons_per_slide": 1,
  "placement": "off-canvas edge or quiet negative space, never behind primary text",
  "slides": [
    {
      "slide_no": 1,
      "theme": "writing as clarification",
      "query": "pencil edit writing",
      "preferred_sets": ["lucide", "heroicons"],
      "selected_icon": "lucide:pencil-line",
      "rationale": "semantic writing mark, quiet enough for cover watermark",
      "placement": {"x": 0.68, "y": 0.16, "scale": 0.42, "rotation": -8}
    }
  ]
}
```

Pick a different semantic query for each page role:

- cover/opening: `pencil`, `edit`, `book-open`, `pen-line`
- contrast/comparison: `scale`, `split`, `target`, `scan-search`
- mechanism/loop: `refresh-cw`, `repeat`, `rotate-ccw`, `workflow`
- method/action: `list-checks`, `check-circle`, `clipboard-check`, `route`
- evidence/data: `chart-line`, `bar-chart`, `table`, `scan`
- warning/objection: `triangle-alert`, `shield-alert`, `x-circle`
- audience/user: `user`, `users`, `message-circle`, `eye`
- timing/duration: `clock`, `hourglass`, `history`
- growth/market: `trending-up`, `chart-no-axes-combined`, `network`

## Watermark Design Rules

- Use one icon style per deck: outline, solid, or filled path. Do not mix Lucide outline with Heroicons solid in the same deck unless the visual contract explicitly separates roles.
- One slide may use at most one background watermark icon. Avoid icon wallpaper, repeated patterns, and multiple giant icons.
- The icon must match the slide's claim, not just the deck topic. If the query is generic for every slide, do not use a watermark.
- Use low contrast adjusted by icon style: outline/line watermarks usually need 8-16% opacity; cropped visible-large outline watermarks usually work best around 10-16%; solid/filled watermarks usually need 3-8%. The icon should be perceptible in a 1280px preview and recognizable in the contact sheet, but it must not become the first thing the eye reads.
- Prefer edge placement with 35-65% of the icon cropped off-canvas, or quiet negative-space placement. Avoid complete centered icons. Do not put icons behind titles, body text, charts, or diagrams.
- The watermark layer is allowed only as a semantic background accent. It must not create frames, boxes, rails, separators, arrows, UI chrome, chart placeholders, or fake evidence.
- PPTX route: keep the icon as an editable SVG/vector foreground object when practical. If rasterized into a background, record it as `background_with_semantic_icon_watermark` and keep opacity/placement in the manifest.
- HTML route: render watermark icons as real SVG/DOM with `aria-hidden="true"`, not as screenshot slides.
- SVG rasterization route: force `svg { width:100%; height:100%; display:block; }` before screenshot/export. Do not rely on SVG default `1em` or intrinsic 24px icon size, or the watermark will become a tiny mark in PPTX/PNG while looking correct in HTML.
- If thumbnail scan shows the watermark before the title, move it farther off-canvas, reduce contrast, or remove it. If the watermark cannot be perceived at all at preview/contact-sheet size, raise contrast/scale, change to a more legible icon style, or omit it.

## Manifest

Record icon use in `visual_asset_manifest.json`:

```json
{
  "icons": [
    {
      "asset_id": "slide-03-loop-watermark",
      "provider": "iconify",
      "collection": "lucide",
      "icon_id": "lucide:refresh-cw",
      "license": "ISC",
      "source": "https://github.com/lucide-icons/lucide",
      "path": "assets/icons/slide-03-refresh-cw.svg",
      "role": "semantic_watermark",
      "allowed_pages": ["P03"],
      "opacity": 0.045,
      "editable_policy": "editable_svg_or_dom",
      "text_policy": "no_text"
    }
  ]
}
```

## Rejection Rules

Reject icon watermark use when:

- the icon is merely decorative and does not map to the slide claim.
- the icon competes with title, body, diagram, or chart readability.
- the icon repeats on several adjacent slides without semantic change.
- the icon creates visual clutter similar to the gray brush-stroke and empty-seal failure.
- the selected icon set license/source cannot be recorded.
- the selected deck style works better with plain atmosphere backgrounds and editable foreground content.
