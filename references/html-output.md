# HTML Output

For normal PPT generation, `qiaomu-ppt` can produce two different HTML artifacts. Keep them separate:

- formal semantic HTML deck: real web presentation, suitable as a delivery artifact.
- PPTX parity HTML preview: screenshot-based QA artifact, not a formal HTML deck.

The formal HTML output is not a screenshot replacement. It is useful for:

- browser preview and iteration
- lightweight sharing
- interaction, keyboard navigation, and optional animation
- preserving motion effects that PPTX export may not support
- selectable/searchable text and semantic structure

## Formal HTML Contract

Save formal HTML under one of:

```text
<project>/html/index.html
<project>/exports/<slug>.html
```

For a self-contained article/talk deck, prefer `exports/<slug>.html` plus local assets. For complex web presentations, use `html/index.html` with a local asset folder.

Also write:

```text
<project>/html_delivery_manifest.json
```

The manifest should declare:

- `mode: semantic_html_deck`
- output paths
- slide count
- source contracts used: `slide_plan.json`, `content_contract.json`, `visual_contract.json`
- component strategy: DOM/SVG/Canvas/CSS/JS
- accessibility/searchability notes
- `whole_slide_screenshot_policy: forbidden_for_formal_html`
- `readability_qa`: checked viewport sizes, minimum font size, overflow policy, stage scale strategy, and content parity policy

Example:

```json
{
  "mode": "semantic_html_deck",
  "html_outputs": ["html/index.html", "exports/talk.html"],
  "slide_count": 12,
  "component_strategy": "DOM text + SVG diagrams + CSS stage + JS keyboard navigation",
  "whole_slide_screenshot_policy": "forbidden_for_formal_html",
  "readability_qa": {
    "viewports_checked": ["1440x900", "1280x720"],
    "stage_strategy": "fixed 16:9 inner stage scaled to viewport",
    "min_body_px_at_1280_stage": 18,
    "overflow_policy": "no hidden slide-content overflow",
    "content_parity_policy": "all slide titles and concrete anchors come from slide_plan.json"
  }
}
```

## Formal HTML Requirements

- Fixed 16:9 stage with responsive fit.
- Keyboard navigation: arrow keys, space, Home/End.
- Visible progress indicator.
- HTML must be generated from the same slide plan and visual contract as the PPTX. Do not hand-write a simplified second presentation that drops proof text, changes titles, or invents sparse filler content.
- HTML must preserve the same title hierarchy, proof objects, concrete anchors, and speaker-facing slide sequence as the PPTX. Implementation can differ; content cannot become hollow.
- The visible slide layer must be semantic DOM/SVG/Canvas/CSS/JS, not a full-slide JPG/PNG/PDF screenshot.
- Text should be selectable/searchable where practical. If a chart or diagram is rasterized, only that chart/diagram should be an image, not the whole slide.
- Motion is optional and content-led: fade, reveal, pan, count-up, chart emphasis, or section transition.
- Source/provenance metadata stays off visible slides unless the user requests citations.
- All assets should be local or clearly listed as external dependencies.
- Use a real stage scaler: either CSS `aspect-ratio: 16 / 9` with a stable inner stage, or a 1920x1080/1280x720 coordinate stage scaled to fit. Do not let viewport units alone resize text into unreadability.
- If using a fixed coordinate stage, position the stage from the scaled dimensions: `scale = min(viewportW / stageW, viewportH / stageH)`, `left = (viewportW - stageW * scale) / 2`, `top = (viewportH - stageH * scale) / 2`, and `transform-origin: top left`. Do not center the unscaled 1920px DOM box with flex/grid and then apply `transform: scale(...)`; that can push the visible canvas sideways and crop right or left content.
- Do not use `vw`, `%`, or `clamp()` as the primary layout system for final slide geometry when PPTX parity matters. They are acceptable for outer UI chrome, but slide text and components should come from the locked coordinate system or stable aspect-ratio tokens.
- Define readable type tokens for HTML separately from PPTX if needed: title, subtitle, body, label, annotation. The body floor should normally stay at 18 px on a 1280px-wide stage.
- Define title line-height tokens explicitly. For Chinese/CJK multi-line titles, normal h1/h2 leading should be `1.14-1.30`; very large cover or closing titles may tighten to `1.06-1.16` only after screenshot review. Do not use `line-height: .9`, `font: .../.9`, or negative letter-spacing as a generic "cinematic" shortcut for CJK titles.
- Check at least two viewport sizes before reporting completion: 1440x900 or similar desktop, and 1280x720 or similar laptop/projector. For a four-slide preview, screenshot every slide at one desktop viewport and at least slide 1 plus the densest slide at 1280x720.
- No unplanned clipping. If a slide needs overflow, it must be an intentional scrollable notes/speaker pane, never hidden content on the slide canvas.

## Four-Slide HTML Preview

For any final deliverable that includes formal HTML and is expected to exceed 7 slides, include HTML in the four-slide preview gate before full generation.

- Preview should include four representative slides: cover/opening, dense proof, diagram/process, and breathing/turning-point/closing.
- Open the preview in a browser or use an equivalent screenshot/render check.
- If the preview is hard to read, clipped, hollow, or visually unrelated to PPTX, stop and fix the HTML generator/contract before generating all slides.
- Record the decision in `preview_gate.json`; do not continue from memory.

## PPTX Parity Preview

For PPTX-first projects, generate a parity HTML preview only for QA or when the user explicitly asks for exact PPTX rendering in the browser:

```bash
python3 <skill>/scripts/html_from_previews.py <project> --slug <slug> --title "<title>"
```

This creates `html-parity/index.html`, `exports/<slug>.parity.html`, and `html_parity_manifest.json`. The visible layer uses rendered slide previews, so the browser version matches the PPTX preview exactly; semantic text from `slide_plan.json` remains off-screen for accessibility and search.

This mode is not the formal HTML deck. Do not report it as `HTML version` unless you explicitly label it as `PPTX parity preview`.

Use a semantic/interactive HTML layout when HTML is the final deliverable, when the user asks for an HTML version, or when interaction is the point. It may differ visually from the PPTX in implementation details but must still share:

- slide order
- core claims
- visual system
- palette and typography
- background asset rhythm
- source and QA sidecars

HTML may add:

- keyboard-driven reveals
- animated transitions
- hover details
- speaker view affordances
- chapter progress

HTML must not hide content that exists in PPTX unless it is a deliberate reveal with accessible fallback.

## Failure Patterns

- If the user asks for HTML and the output is only a full-slide screenshot deck, it fails the formal HTML delivery gate.
- If `html/index.html` or `exports/<slug>.html` is generated by `html_from_previews.py`, it is misfiled. Move it to `html-parity/index.html` or `exports/<slug>.parity.html`.
- If a project has `html_parity_manifest.json` but no `html_delivery_manifest.json`, report that only the QA preview exists, not the formal HTML version.
- If the HTML title, subtitle, bullets, examples, or evidence do not match the PPTX/slide plan, regenerate it from the common source or switch to parity preview mode.
- If HTML feels hollow because it only keeps slogans while PPTX has proof, it fails the content-parity gate.
- Do not put internal production words such as `deck`, `route`, `artifact`, or tool/model provenance in visible HTML.
- If the 1280x720 screenshot cuts off the right side of a fixed-stage deck, check whether the unscaled coordinate stage is being centered by layout before scaling. Fix with explicit scaled `left/top` and `transform-origin: top left`.
