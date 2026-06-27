# PPT Anti-Slop Rules

This document defines Qiaomu PPT's anti-default-aesthetic quality gate. It is
inspired by public design-agent critique and repeated user feedback, but it is
written for PPT/HTML deck production rather than generic websites.

The goal is not to make every deck strange. The goal is to prevent outputs that
look like a model filled space with default web UI parts.

## Default Fingerprints To Reject

Reject these unless the user explicitly asks for them and the design proposal
reserves space for them.

- Generic purple/blue gradients that do not come from the brand/source.
- Floating orbs, glow blobs, bokeh, particles, or decorative mesh backgrounds.
- Three-card feature grids used as the second slide by reflex.
- Nested card soup: section card inside page card inside content card.
- Repeated left accent bars on every card without semantic role.
- Animated status dots, live badges, or AI-looking blinking indicators.
- Lucide/icon stacks used to fill weak content.
- Default top progress strips, page-number bars, generic footers, date stamps,
  or source URLs baked into the slide canvas.
- Fake glassmorphism or frosted-card stacks without a product/interface reason.
- Dashboard-looking metric rows on slides that are actually arguments.
- Decorative separator lines that are not axes, table rules, timelines,
  connectors, or intentional editorial dividers.
- Fake source evidence: generated screenshots, fake documents, fake app UI,
  fake product packaging, fake logos, or fake charts.
- Huge images that cover title space, or titles placed without a protected safe
  area.
- CJK title line-height so tight that Chinese glyphs crowd or collide.
- Reused background images on adjacent slides when the source/story role
  changed.
- Text overflow hidden by clipping, shrinking, or accidental HTML/PPT wrapping.

## Positive Bias

Prefer:

- source-backed proof objects over decorative cards;
- one strong visual idea per slide over many small widgets;
- typography, spacing, alignment, and contrast before ornaments;
- real product/source/media assets before generated atmosphere;
- generated images that represent a concrete object, scene, material, or
  metaphor from the slide claim;
- viewer chrome outside the slide canvas;
- local scrims, mattes, crop masks, leader lines, and annotations that connect
  image and text rather than covering the image with a generic opaque panel;
- slide-specific layout rhythm across the thumbnail grid.

## Audit Contract

For professional/final decks, record an anti-slop audit in a report or QA
section:

```json
{
  "anti_slop_audit": {
    "status": "passed",
    "checked": [
      "no_generic_gradient",
      "no_nested_card_soup",
      "no_default_slide_chrome",
      "no_fake_source_evidence",
      "title_image_clearance",
      "cjk_title_line_height",
      "source_or_asset_grounding"
    ],
    "repairs_applied": []
  }
}
```

If the audit fails, repair the contract or renderer mapping. Do not patch only
one visible element when the same default fingerprint will reappear on another
slide.

## Repair Moves

- Generic gradient -> replace with source image, generated content-linked
  atmosphere, or quiet neutral surface.
- Card soup -> remove parent panels, use whitespace/lines/type hierarchy.
- Three-card default -> choose L13 process, L20 chart, L24 concept map, ITL18
  screenshot annotation, quote spread, or source object page.
- Fake evidence -> use source/user/web image, rebuild as editable diagram, or
  mark the slide as draft.
- Image/title collision -> change ITL pattern, crop/fit, safe area, or title
  density before export.
- Tight CJK title -> increase leading, split title/subtitle, or reduce text.
- Repeated background -> assign slide-specific asset role or switch to a
  source/object-led layout.
