# Upstream Research Notes

These notes summarize the local research used to shape `qiaomu-ppt`. The full upstream repositories were cloned under `research/upstreams/` and pinned in `research/upstreams.lock.json`. They are not runtime skill dependencies. MIT-licensed infrastructure code may be vendored into `qiaomu-ppt` with attribution; upstream commands and installed upstream skills are still not required at runtime.

## ppt-master

Source: https://github.com/hugohe3/ppt-master

What to borrow:

- Editable PPTX should be the default when the user asks for real PPT / PowerPoint.
- A strict serial pipeline is safer than a one-shot prompt: source, project, strategy, SVG pages, quality check, post-processing, export.
- Speaker notes and animation/export discipline belong in the production path, not as afterthoughts.
- A harness is not a wishing well. Users still need iteration and review.

Boundary:

- Do not vendor or call `ppt-master` here. Its package is intentionally large and script-heavy.
- Internalize the serial pipeline, SVG/PPTX compatibility discipline, spec lock, and quality gates as Qiaomu-owned rules.
- `qiaomu-ppt` compensates for weaker raw SVG aesthetics with a stronger narrative and visual strategy layer before production.

## baoyu-design

Source: https://github.com/JimLiu/baoyu-design

What to borrow:

- Use real design context: brand assets, Figma/HTML/CSS, screenshots, product UI, and design systems when available.
- Preview and iterate visually in a browser when the style is uncertain.
- Distinguish editable PPTX export from screenshot-style export.

Boundary:

- `baoyu-design` is strongest for HTML design artifacts and local design iteration. `qiaomu-ppt` borrows its design-context and preview ideas, not its starter components or export tool.

## frontend-slides

Source: https://github.com/zarazhangrui/frontend-slides

What to borrow:

- Visual style discovery beats abstract style questions.
- Fixed 1920 x 1080 stage is a good preview discipline.
- Zero-dependency HTML is fast for style exploration and web sharing.
- Anti-generic design language is useful, especially against default purple-gradient decks.
- Progressive disclosure is useful: keep a compact style index, inspect only
  shortlisted preview cards, then open the full template details only after a
  direction is chosen.

Boundary:

- HTML slides are not automatically real editable PPTX. Treat the idea as a preview/final-web route, or translate the chosen style system into Qiaomu's PPTX-oriented route.
- Do not copy the stage CSS, presets, prompt text, or template pack. Qiaomu
  uses the method: concrete previews, fixed stage, anti-slop gate, and
  source-backed style choice.

## guizang-ppt-skill

Source: https://github.com/op7418/guizang-ppt-skill

What to borrow:

- Chinese deck production benefits from named visual systems, layout discipline, image slots, and explicit suitability rules.
- Editorial magazine and Swiss routes are useful defaults for brand/talk decks.
- Low-performance fallback and screenshot/image slot thinking matter for real presentation use.
- A locked layout registry and image-slot ratio contract are stronger than
  freeform page-by-page HTML. Each slide should carry a registered layout id.

Boundary:

- Dense training courseware and collaboration-heavy editing are not ideal for a static HTML route. For high school courseware, use the visual principles sparingly and keep editable PPTX as the default final delivery.
- Do not copy its magazine/Swiss templates, theme class names, or visual
  recipes. Qiaomu uses its own `Lxx` / `ITLxx` ids and design kernel.

## Open Design

Source: https://github.com/nexu-io/open-design

What to borrow:

- Treat a deck as a skill plus design-system plus export surface, not just an
  HTML file.
- `DESIGN.md`-style token contracts and artifact manifests make agent work
  easier to review and repeat.
- A stable deck skeleton should own stage scaling, keyboard navigation, print
  mode, and host chrome so generation focuses on slide content.
- Deterministic layout QA catches stage/scaler regressions before visual review.

Boundary:

- Do not depend on Open Design as a runtime or copy its scaffold. Qiaomu keeps
  a smaller native `html_design_kernel.json`, `html_source_map.json`, and
  `html_delivery_manifest.json`.

## html-ppt-skill

Source: https://github.com/lewislulu/html-ppt-skill

What to borrow:

- Tokenized themes, component/layout catalogs, presenter notes, keyboard
  navigation, deep links, and optional presenter mode are valuable HTML deck
  affordances.
- Themes should be variable contracts rather than a pile of ad hoc colors.
- Notes and presenter-only controls must remain off the visible slide canvas.

Boundary:

- Do not copy its themes, layouts, animations, or presenter implementation.
  Qiaomu may implement equivalent concepts with its own tokens, components,
  manifests, and validation rules.

## humanize-ppt

Source: https://github.com/LearnPrompt/humanize-ppt

What to borrow:

- Start with audience-state-transfer: every page turn should move the audience or learner.
- Decide per-page media needs before rendering.
- Run a capped checkup loop and produce fix prompts instead of spinning forever.

Boundary:

- Humanize is an outline/director/checkup layer, not a renderer. `qiaomu-ppt` borrows the state-transfer and capped-checkup ideas as internal rules.

## awesome-design-md

Source: https://github.com/voltagent/awesome-design-md

What to borrow:

- `DESIGN.md` documents are useful as agent-readable style systems: mood, palette, typography, component rhythm, layout rules, depth, and do/don't constraints.
- The collection covers many useful PPT aesthetics: cinematic product reveals, developer evidence decks, finance/trust dashboards, editorial arguments, playful creative canvases, marketplace friendliness, precision reports, and retro nostalgia.
- Style should be selected from the user's route, audience, industry, evidence needs, and readability constraints, not from a vague request for "高级感".
- A style library becomes much more useful when machine-readable: every preset should carry recommendation keywords, route fit, `best_for`, `avoid_for`, palette, typography, slide patterns, media policy, chart policy, and animation hints.

Boundary:

- Do not vendor the original `DESIGN.md` files into the runtime package.
- Do not imply rights to third-party brands, logos, proprietary fonts, product screenshots, or exact page layouts.
- `qiaomu-ppt` uses `data/design_style_presets.json` as a derived PPT abstraction and `scripts/recommend_style.py` as the selector.

## Model Council Summary

The qllm MCP discussion converged on this architecture:

- Keep the SVG-to-PPTX-oriented production spine as the practical default, without depending on `ppt-master`.
- Add a pre-production narrative and visual strategy layer to offset aesthetics.
- Route brand launch and courseware differently because their success criteria are opposite in density, pacing, and note style.
- Keep the package lightweight; vendor only the infrastructure code that materially improves output quality, is license-compatible, and is attributed in `NOTICE.md`.
- Be explicit about verification gaps, especially native Office/WPS opening, exporter availability, and HTML-to-PPTX parity.
- Add a local design-style recommender so open-ended PPT requests can choose a concrete visual system before production.
