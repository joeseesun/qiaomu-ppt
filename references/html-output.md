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

## Qiaomu HTML Deck System

Use native semantic HTML as the primary formal deck surface. SVG is valuable
for local diagrams, charts, maps, and compatibility export, but a formal HTML
PPT should not require an SVG file per slide when `slide_plan.json` is
available.

Use upstream web-deck projects only as research evidence. Do not copy their
templates, class names, CSS recipes, fixed layout catalogs, or visual presets
into generated Qiaomu artifacts. The Qiaomu implementation should exceed a
single-template deck by keeping one source contract across PPTX, PDF, formal
HTML, parity preview, Keynote, and website viewing.

For formal HTML, write these contracts before full generation:

- `html_design_kernel`: the approved Qiaomu-owned visual/stage/token/layout
  kernel for the web deck. See [html-design-kernel.md](html-design-kernel.md)
  and `data/html_deck_design_kernel.json`.
- `layout_registry`: every slide has a stable `data-slide-id` and
  `data-layout-id`, but in HTML-only projects this is an audit label and
  review anchor, not a template cage. Prefer semantic ids such as
  `html-freeform-cover`, `html-process-canvas`, or `html-editorial-quote`
  that map to `html_layout_intent`; keep `Lxx` / `ITLxx` only as optional
  fallback/reference tags when PPTX parity, SVG export, or strict component
  reuse is actually needed.
- `image_slot_registry`: every non-decorative local image has
  `data-image-slot` plus a manifest row recording role, intended ratio, fit
  policy, safe area, source/generator, final format, and final file size.
- `viewer_chrome_boundary`: progress, search, page position, keyboard hints,
  download/share, and thumbnails belong outside the fixed slide stage.
- `performance_budget`: package and per-image budgets are declared before
  packaging, then validated against actual files.
- `user_facing_archetype`: when the deck is created for HTML/web sharing or a
  style selector is shown, record the selected id/label from
  `data/html_style_archetypes.json` plus the hidden internal style families used
  to execute it.
- `interaction_fallback`: if the HTML deck uses canvas/WebGL/animations, it
  must also have a readable static state or low-power mode. Motion should
  serve the reading path; it is not a decoration layer.
- `motion_system`: when GSAP, Lottie, dotLottie, or custom authored motion is
  used, record the level, engines, manifest path, reduced-motion policy, static
  fallback, and browser QA evidence. See [html-motion.md](html-motion.md).
- `point_review_map`: every major visible title, proof, media object, chart,
  diagram, callout, and note control has `data-screen-label` or a stable id.
- `html_product_context` and `html_design_context`: a compact, Impeccable-style
  context layer for HTML decks. It records audience, use context, physical
  viewing scene, tone, color strategy, anti-references, accessibility floor,
  and what would make the deck feel generic. This sits above page layout so the
  renderer makes design decisions from context, not from a fixed layout catalog.
- `source_synthesis`: for broad-topic HTML decks, a source-synthesis article
  (`content_report.md` or `内容母稿-<主题>.md`) sits between the source cards and
  the slide plan. It is the content mother document for page claims; do not
  generate formal HTML directly from links or a thin `research_dossier.md`.

This makes the formal HTML deck a multi-format presentation surface, not a
one-off web page.

## HTML Speed Profiles

Separate first draft speed from final delivery evidence.

`fast_draft` is for quickly seeing whether the content and HTML direction work:

- content report or `内容母稿-<主题>.md`
- semantic `html/index.html`
- `html_source_map.json`
- strict `validate_html_deck.py`
- key browser screenshots only: cover/opening, dense proof, diagram/process,
  and closing
- manifest may record unresolved polish items

`final_qa` is for delivery:

- full screenshot set
- console/page-error check
- critique/polish report
- complete `html_delivery_manifest.json`
- motion manifest when authored motion exists
- package and readability evidence

Do not spend final-QA time before the source-synthesis article is strong enough
to justify rendering. If the user complains about speed or asks for a quick
draft, use `fast_draft` and clearly mark what is deferred to `final_qa`.

## HTML Layout Intent, Not PPTX Coordinate Lock

Formal HTML decks should use native semantic layout intent first. Do not force
the editable-PPTX `spec_lock.json` model onto an HTML-only deck.

For `semantic_html_deck` projects whose `export_manifest.json` requests only
HTML:

- `spec_lock.json` is optional and, when present, is a lightweight audit record
  or intent record. It should not be treated as a mandatory per-slide absolute
  coordinate program.
- Prefer a compact `html_layout_intent` object in `spec_lock.json`,
  `html_design_kernel.json`, or a sidecar. It should declare the slide role,
  density, reading hierarchy, component family, safe text surfaces, visual
  motifs, renderer freedoms, avoid rules, composition axes, and screenshot QA
  focus. For HTML-only, this object is the main layout contract.
- The renderer may choose CSS grid/flex, fixed-stage tokens, local SVG charts,
  Canvas/WebGL scenes, or DOM components as long as the slide preserves
  content parity, stable ids, accessibility/searchability, and screenshot
  readability.
- Do not force a page through `Lxx` / `ITLxx` just to satisfy a validator. If a
  check needs a `layout_id`, use an expressive `html-*` intent id and preserve
  the true composition rationale in `html_layout_intent`.
- Do not create decorative assets only to satisfy image slots, background
  roles, or PPTX-oriented visual-asset quotas. CSS/DOM atmosphere can be
  recorded as visual motifs without becoming fake images.
- Add an Impeccable-style anti-pattern list before rendering: no generic
  purple/blue gradients, no nested cards, no identical icon-card grids, no
  decorative line fields, no text overflow, no tiny unreadable labels, no
  official/protected media imitation, and no full-slide screenshots masquerading
  as semantic HTML.
- Avoid inherited template leftovers: unrelated arcs, blocks, grids, rails,
  badges, or seal-like accents must have a content reason on the slide. If the
  motif cannot be explained from the topic, remove it.
- Primary QA is `validate_html_deck.py`, browser screenshots, visible text
  parity, source grounding, style fit, responsiveness, and package size.
  PPTX/PDF/Keynote export coverage and Codex image-generation gates apply only
  when those outputs or image-led visuals were explicitly requested.

Example lightweight intent:

```json
{
  "html_layout_intent": {
    "slide_id": "s04-example",
    "semantic_role": "quote_focus",
    "density": "breathing",
    "hierarchy": ["chapter_kicker", "quote", "interpretation", "source_note"],
    "component_family": "native_dom_quote",
    "renderer_freedom": "CSS grid/flex inside fixed 16:9 stage; no required absolute coordinate slots",
    "composition_axes": ["asymmetry", "density", "media_depth"],
    "visual_motifs": ["quiet paper field", "soft water wash", "small cinnabar text accent"],
    "avoid": ["unrelated arcs", "decorative boxes", "grid-line backgrounds", "full-slide SVG screenshot"],
    "qa_focus": ["quote line breaks", "contrast at 1280x720", "no hidden overflow"]
  }
}
```

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
<project>/html_design_kernel.json
<project>/html_source_map.json
<project>/html_motion_manifest.json      # only when authored motion is used
```

The manifest should declare:

- `mode: semantic_html_deck`
- output paths
- slide count
- source contracts used: `content_report.md` or `内容母稿-<主题>.md`,
  `slide_plan.json`, `content_contract.json`, `visual_contract.json`
- design kernel path and selected kernel id
- source map path
- component strategy: DOM/SVG/Canvas/CSS/JS
- user-facing style archetype: selected id/label from
  `data/html_style_archetypes.json`, plus internal execution mapping
- accessibility/searchability notes
- `whole_slide_screenshot_policy: forbidden_for_formal_html`
- `readability_qa`: checked viewport sizes, minimum font size, overflow policy, stage scale strategy, and content parity policy
- `point_review_policy`: stable slide ids, `data-screen-label` usage, local HTTP preview path/URL, screenshot evidence, and review status when browser iteration is part of the route
- `asset_performance`: local asset strategy, converted image formats, package size, largest image size, lazy-loading policy, and any justified exceptions
- `slide_chrome_policy`: whether progress/search/navigation/page counters are outside the slide stage; default is `host_chrome_only`
- `motion_system`: `none` when no authored motion is used; otherwise level,
  engines, `html_motion_manifest.json`, reduced-motion policy, fallback policy,
  and browser QA evidence
- `layout_registry`: slide ids, semantic HTML layout intent ids, component
  families, and optional legacy `Lxx` / `ITLxx` reference ids when parity needs
  them
- `html_critique_policy`: whether the project will run an Impeccable-style
  critique pass, local detector, or equivalent manual anti-pattern review
- `image_slot_registry`: image slot ids, ratios, fit policy, compression format, and file-size evidence
- `validation`: `validate_html_deck.py` command, status, report paths, and unresolved warnings/errors

Example:

```json
{
  "mode": "semantic_html_deck",
  "html_design_kernel": "html_design_kernel.json",
  "html_source_map": "html_source_map.json",
  "html_outputs": ["html/index.html", "exports/talk.html"],
  "slide_count": 12,
  "component_strategy": "DOM text + SVG diagrams + CSS stage + JS keyboard navigation",
  "user_facing_archetype": {
    "id": "talk_story",
    "label": "演讲故事型",
    "internal_style_families": ["editorial_argument"]
  },
  "whole_slide_screenshot_policy": "forbidden_for_formal_html",
  "point_review_policy": {
    "slide_ids": "stable data-slide-id values",
    "element_labels": "data-screen-label on title, proof, image, chart, callout",
    "preview_url": "http://localhost:PORT/html/index.html",
    "review_status": "needs-review"
  },
  "asset_performance": {
    "strategy": "local assets folder, no multi-MB base64 images",
    "preferred_formats": ["webp", "avif", "jpg"],
    "largest_image_kb": 212,
    "package_size_mb": 2.8,
    "lazy_loading": "non-critical images use loading=lazy decoding=async"
  },
  "slide_chrome_policy": {
    "stage": "content_only_canvas",
    "viewer_chrome": "progress/search/page position outside stage",
    "visible_footer": "none unless explicitly requested"
  },
  "motion_system": {
    "level": "subtle",
    "engines": ["css"],
    "manifest": "",
    "reduced_motion": "respect prefers-reduced-motion",
    "fallback": "static final-state readable without playback"
  },
  "layout_registry": {
    "slide_id_attr": "data-slide-id",
    "layout_id_attr": "data-layout-id",
    "source": "html_layout_intent in slide_plan.json/html_design_kernel.json",
    "legacy_pattern_policy": "optional reference only; not a renderer constraint"
  },
  "image_slot_registry": {
    "slot_attr": "data-image-slot",
    "manifest": "visual_asset_manifest.json",
    "policy": "all non-decorative local images have declared role, ratio, fit, format, and file size"
  },
  "validation": {
    "command": "python3 <skill>/scripts/validate_html_deck.py html/index.html --json reports/html_deck_validation.json --markdown reports/html_deck_validation.md",
    "status": "passed"
  },
  "readability_qa": {
    "viewports_checked": ["1440x900", "1280x720"],
    "stage_strategy": "fixed 16:9 inner stage scaled to viewport",
    "min_body_px_at_1280_stage": 18,
    "overflow_policy": "no hidden slide-content overflow",
    "content_parity_policy": "all slide titles and concrete anchors come from slide_plan.json"
  }
}
```

## Web Asset Performance Contract

Formal HTML decks should load like a real website, not like a design file dump.

- Resize generated, source, or screenshot images to their actual maximum display size before packaging. Avoid shipping 2x-4x oversized PNGs unless zoom inspection is a declared feature.
- Prefer WebP or AVIF for generated/concept/photographic images. Use JPEG for broad compatibility when AVIF/WebP is unavailable, and keep PNG only for transparency, crisp line art, or tiny UI/icon assets where it is truly smaller.
- Do not embed multi-MB images as base64 data URIs in final HTML. Use `html/index.html` plus an `assets/` folder, or a ZIP package with local assets, so the browser can cache and stream them.
- Target ordinary conceptual/background images at `<= 250 KB` each, first-view critical images at `<= 500 KB` total, and the full formal HTML package at `<= 3 MB` unless source evidence or high-resolution zoom explicitly requires more. Record justified exceptions in `html_delivery_manifest.json`.
- Use `loading="lazy"` and `decoding="async"` for non-critical images. Preload only the first visible hero/background image when it materially improves the first slide.
- Check actual file sizes before delivery. A formal HTML deck with huge PNGs, repeated uncompressed assets, or base64-bundled generated images fails this gate even if it renders correctly.

## Slide Chrome Boundary

The fixed slide stage is the presentation content, not the viewer UI.

- Do not place top progress bars, page indicator strips, floating page counters, navigation pills, search boxes, download/share controls, or duplicated viewer buttons inside the slide canvas by default.
- Do not add visible generic footers, page numbers, date stamps, source URLs, model/tool names, or production labels to every slide by default. Keep provenance in `html_source_map.json`, speaker notes, QA reports, manifests, or an optional references page.
- If the user explicitly asks for visible page numbers, citations, or a formal report footer, reserve layout space for it in `slide_chrome_policy` and verify it does not crowd title/body/proof areas.
- Browser viewer controls may show progress, search, page position, or keyboard hints outside the slide stage. Those controls should not be exported as part of PPTX/SVG slide content.

## Formal HTML Requirements

- Fixed 16:9 stage with responsive fit.
- Keyboard navigation: arrow keys, space, Home/End.
- Optional progress/page position only in host viewer chrome outside the fixed slide stage. Do not draw a visible top progress strip or page counter on the slide canvas by default.
- Every slide must have a stable slide id and registered layout id: prefer
  `data-slide-id` plus `data-layout-id` that points back to an
  `html_layout_intent` record. In HTML-only projects the id may be an
  expressive composition intent such as `html-freeform-cover`; it must not
  force the renderer into a fixed `Lxx` / `ITLxx` template unless PPTX parity
  explicitly requires that constraint.
- Stable slide ids and element labels: major title, subtitle, proof, image, chart, diagram, source object, callout, and notes controls should have `data-screen-label` or a stable id so a screenshot comment can be located in the source.
- Point comments and browser critique are first-class: visible elements need
  stable anchors so feedback can patch the source contract, not just the DOM.
- Every non-decorative local image should have `data-image-slot`; the slot should match the declared ratio/fit/compression row in `visual_asset_manifest.json` or `html_delivery_manifest.json`.
- HTML must be generated from the same slide plan and visual contract as the PPTX. Do not hand-write a simplified second presentation that drops proof text, changes titles, or invents sparse filler content.
- HTML must preserve the same title hierarchy, proof objects, concrete anchors, and speaker-facing slide sequence as the PPTX. Implementation can differ; content cannot become hollow.
- The visible slide layer must be native semantic DOM/CSS/JS first, with SVG/Canvas only for local components or compatibility fallback. It must not be a full-slide JPG/PNG/PDF screenshot.
- Text should be selectable/searchable where practical. If a chart or diagram is rasterized, only that chart/diagram should be an image, not the whole slide.
- Ordinary title, subtitle, body, callout, caption, and label text should be static DOM/SVG text whenever feasible. Avoid generating every slide's visible copy from opaque JS loops; direct markup is easier to inspect, edit, and map back to the slide plan.
- Motion is optional and content-led: fade, reveal, pan, count-up, chart emphasis, or section transition.
- For authored motion beyond basic CSS transitions, choose a level from
  `data/html_motion_presets.json`, write `html_motion_manifest.json`, and run
  the validator with `--motion-manifest`. Use GSAP for timeline orchestration
  and Lottie/dotLottie for prepared After Effects animation assets; both must
  have a readable static state and reduced-motion behavior.
- Source/provenance metadata stays off visible slides unless the user requests citations.
- All assets should be local or clearly listed as external dependencies.
- All local image assets should follow the web asset performance contract above.
- Use a real stage scaler: either CSS `aspect-ratio: 16 / 9` with a stable inner stage, or a 1920x1080/1280x720 coordinate stage scaled to fit. Do not let viewport units alone resize text into unreadability.
- If using a fixed coordinate stage, position the stage from the scaled dimensions: `scale = min(viewportW / stageW, viewportH / stageH)`, `left = (viewportW - stageW * scale) / 2`, `top = (viewportH - stageH * scale) / 2`, and `transform-origin: top left`. Do not center the unscaled 1920px DOM box with flex/grid and then apply `transform: scale(...)`; that can push the visible canvas sideways and crop right or left content.
- Do not use `vw`, `%`, or `clamp()` as the primary layout system for final slide geometry when PPTX parity matters. They are acceptable for outer UI chrome, but slide text and components should come from the locked coordinate system or stable aspect-ratio tokens.
- Define readable type tokens for HTML separately from PPTX if needed: title, subtitle, body, label, annotation. The body floor should normally stay at 18 px on a 1280px-wide stage.
- Define title line-height tokens explicitly. For Chinese/CJK multi-line titles, normal h1/h2 leading should be `1.14-1.30`; very large cover or closing titles may tighten to `1.06-1.16` only after screenshot review. Do not use `line-height: .9`, `font: .../.9`, or negative letter-spacing as a generic "cinematic" shortcut for CJK titles.
- Check at least two viewport sizes before reporting completion: 1440x900 or similar desktop, and 1280x720 or similar laptop/projector. For a four-slide preview, screenshot every slide at one desktop viewport and at least slide 1 plus the densest slide at 1280x720.
- No unplanned clipping. If a slide needs overflow, it must be an intentional scrollable notes/speaker pane, never hidden content on the slide canvas.
- Run `python3 <skill>/scripts/validate_html_deck.py <html> --json <project>/reports/html_deck_validation.json --markdown <project>/reports/html_deck_validation.md` before claiming a formal HTML deck is done. The script does not replace browser review; it catches structural failures before visual QA.

## Browser Iteration Contract

For high-design/editorial/brand decks, HTML deliverables, or user requests to preview before final export:

- Serve the preview over local HTTP, not `file://`.
- Record the preview path/URL, screenshot paths, checked viewport sizes, and review status in `deck_project_meta.json`, `preview_gate.json`, or `html_delivery_manifest.json`.
- Keep a source map from visible slide elements to `slide_plan.json`, `visual_contract.json`, source cards, or asset rows. A lightweight `html_source_map.json` is enough.
- Use review status values such as `needs-review`, `approved`, or `changes-requested`; do not rely on chat memory as the only state.
- When the user points at a visual issue in a screenshot, patch the source contract or reusable renderer whenever the issue is systemic. Patch a single HTML element only for a truly one-off visual correction.
- If Impeccable is available in the environment, its ideas can be used as a
  review model: shape first, critique with both human/LLM judgment and
  deterministic anti-pattern checks, then polish. Do not vendor its templates
  or require its CLI for normal qiaomu-ppt operation; treat it as an optional
  quality lens.

## Four-Slide HTML Preview

For any final deliverable that includes formal HTML and is expected to exceed 7 slides, include HTML in the four-slide preview gate before full generation.

- Preview should include four representative slides: cover/opening, dense proof, diagram/process, and breathing/turning-point/closing.
- Open the preview in a browser or use an equivalent screenshot/render check.
- If the preview is hard to read, clipped, hollow, or visually unrelated to PPTX, stop and fix the HTML generator/contract before generating all slides.
- Record the decision in `preview_gate.json`; do not continue from memory.

## Qiaomu HTML Validator

Use the validator for formal semantic HTML decks and web-deck previews:

```bash
python3 <skill>/scripts/validate_html_deck.py \
  <project>/html/index.html \
  --json <project>/reports/html_deck_validation.json \
  --markdown <project>/reports/html_deck_validation.md
```

When authored motion is used:

```bash
python3 <skill>/scripts/validate_html_deck.py \
  <project>/html/index.html \
  --motion-manifest <project>/html_motion_manifest.json \
  --json <project>/reports/html_deck_validation.json \
  --markdown <project>/reports/html_deck_validation.md
```

The validator checks:

- slide sections exist and carry stable `data-slide-id`/`id`
- each slide has a registered `data-layout-id`/`data-layout`
- point-review anchors exist through `data-screen-label`
- forbidden viewer chrome/progress/footer/source labels are not inside the slide canvas
- non-decorative images have `data-image-slot`
- large base64 data URIs are rejected
- local image and package size budgets are respected
- obvious tiny inline text is flagged
- a fixed stage/scaler marker exists
- optional `html_motion_manifest.json` declares valid motion level/engines,
  local GSAP/Lottie/dotLottie assets, static fallback, reduced-motion policy,
  and existing per-slide motion targets

Run with `--strict` when generating final/professional HTML. A passing
validator report is necessary but not sufficient; still do browser screenshots
and visual inspection.

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
- GSAP timelines for staged DOM/SVG motion
- Lottie/dotLottie players for packaged AE-exported motion assets
- hover details
- speaker view affordances
- chapter progress

HTML must not hide content that exists in PPTX unless it is a deliberate reveal with accessible fallback.

## Structured HTML-To-PPTX Boundary

Editable PPTX export from HTML is credible only for slide-structured decks:

- fixed canvas size such as 1920x1080 or a declared 16:9 coordinate system
- discrete slide selector and stable order
- navigation or `goTo(slideIndex)` behavior that can reset the active slide before capture/export
- known selectors for active slide content
- separate text, image, shape, chart, and diagram regions rather than one flattened screenshot layer

If the source is an arbitrary scrolling page, WebGL scene, animation-heavy prototype, or screenshot collage, do not promise editable PPTX. Rebuild it as a slide deck first, or export a clearly labelled screenshot/parity artifact.

## Failure Patterns

- If the user asks for HTML and the output is only a full-slide screenshot deck, it fails the formal HTML delivery gate.
- If `html/index.html` or `exports/<slug>.html` is generated by `html_from_previews.py`, it is misfiled. Move it to `html-parity/index.html` or `exports/<slug>.parity.html`.
- If a project has `html_parity_manifest.json` but no `html_delivery_manifest.json`, report that only the QA preview exists, not the formal HTML version.
- If the HTML title, subtitle, bullets, examples, or evidence do not match the PPTX/slide plan, regenerate it from the common source or switch to parity preview mode.
- If HTML feels hollow because it only keeps slogans while PPTX has proof, it fails the content-parity gate.
- If formal HTML lacks stable slide ids or element labels, screenshot feedback cannot be mapped back to the deck source; add the labels before asking for detailed visual review.
- If HTML-only generation requires every slide to choose from a fixed layout
  pattern library before rendering, the workflow is over-constrained. Replace
  the pattern with semantic `html_layout_intent`, composition axes, and browser
  screenshot critique; keep pattern ids only as trace metadata.
- If a browser preview is opened through `file://`, rerun it through a local HTTP server before claiming preview evidence.
- Do not put internal production words such as `deck`, `route`, `artifact`, or tool/model provenance in visible HTML.
- If the 1280x720 screenshot cuts off the right side of a fixed-stage deck, check whether the unscaled coordinate stage is being centered by layout before scaling. Fix with explicit scaled `left/top` and `transform-origin: top left`.
