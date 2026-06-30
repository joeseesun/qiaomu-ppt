# HTML Design Kernel

This reference defines the Qiaomu-owned method for high-quality formal HTML
decks. It is informed by upstream web-deck projects, but it must not copy their
templates, CSS classes, visual presets, long prompts, or fixed page designs.

## Why This Exists

Formal HTML decks need a stronger contract than "make slides in a browser".
The winning pattern is:

- make native semantic HTML the primary render path; SVG is a local component
  layer or compatibility fallback, not the default slide container;
- choose a visual direction by showing concrete HTML previews, not by asking
  abstract style adjectives;
- lock a fixed 16:9 stage plus a compact design/context contract before full
  production, while leaving HTML renderers room to compose with DOM/CSS,
  browser-native layout, Canvas/WebGL, and purposeful motion rather than
  copying PPTX absolute-coordinate slots or a fixed layout-pattern catalog;
- keep real semantic slide sections, source maps, and manifests so browser
  feedback can be patched at the source;
- keep motion, presenter controls, search, and progress outside the slide
  canvas unless the user explicitly asks for visible UI;
- package local assets like a real website, not like a screenshot dump.

## Research Inputs And Boundaries

These are research references only:

- `frontend-slides`: useful for visual discovery, fixed-stage preview, single
  HTML simplicity, and anti-generic design discipline.
- `guizang-ppt-skill`: useful for named visual systems, registered layouts,
  image-slot ratios, and preflight discipline.
- `Open Design`: useful for skill plus design-system composition, deck export
  surfaces, deterministic stage scaffolds, and artifact manifests.
- `html-ppt-skill`: useful for tokenized themes, layout/component grammar,
  presenter notes, and optional runtime features.
- `pbakaus/impeccable`: useful for a context-first design workflow:
  PRODUCT/DESIGN context, shape-before-build, explicit anti-references,
  deterministic anti-pattern detection, browser live iteration, and polish
  loops. Use these ideas as methodology only; do not copy Impeccable's brand
  system, templates, command text, class names, or detector implementation into
  Qiaomu artifacts.

Qiaomu must not vendor or imitate their templates. Convert the ideas into the
contracts below.

## Kernel Artifacts

Every formal HTML deck should have:

```text
<project>/html/index.html
<project>/exports/<slug>.html
<project>/html_design_kernel.json
<project>/html_product_context.md or .json
<project>/html_generation_playbook.md or .json
<project>/html_source_map.json
<project>/html_delivery_manifest.json
<project>/html_motion_manifest.json      # only when authored motion exists
```

`html_design_kernel.json` is the design lock for the web deck. It records:

- `kernel_id`: stable id such as `qiaomu-html-deck-kernel-v1`.
- `stage_model`: 1920 x 1080 or equivalent 16:9 coordinate system, scaler,
  transform origin, viewport checks, and text-size floor.
- `style_discovery`: recommended / alternative / wildcard visual directions
  with content-fit reasons and avoid rules.
- `html_product_context`: audience, use context, viewing environment,
  emotional target, primary reader action, content constraints, rights
  boundary, accessibility floor, and success criteria. This is the HTML deck's
  equivalent of a product/design brief and must be read before layout choices.
- `html_generation_playbook`: the Impeccable-inspired execution plan:
  shape, build, critique, polish, harden. It records anti-references,
  deterministic checks, browser screenshot plan, and what feedback should patch
  in the source contract.
- `token_contract`: color, type, spacing, radius, chart, and emphasis tokens,
  each marked as source-backed, derived, or fallback.
- `layout_registry`: slide ids, semantic HTML layout intent ids, component
  types, and density rhythm. In HTML-only projects these ids describe intent
  and review anchors; they are not template names. `Lxx` / `ITLxx` ids may be
  recorded only as optional legacy/reference tags for parity routes.
- `html_layout_intent`: optional lightweight per-slide intent for HTML-only
  projects. It records semantic role, density, hierarchy, component family,
  renderer freedoms, composition axes, avoid rules, and QA focus. It is the
  primary layout contract when HTML is the only requested delivery.
- `image_slot_registry`: image slot ids, ratios, fit policy, safe text areas,
  compression format, source/generator, and file-size evidence.
- `semantic_component_registry`: permitted component families such as title,
  claim proof, evidence grid, timeline, process, compare, KPI, quote, chart,
  image hero, code, terminal, closing, and presenter notes.
- `motion_policy`: level, engines, reduced-motion behavior, static fallback,
  and whether motion is content-led or purely decorative.
- `review_model`: screen-label policy, source map policy, browser screenshot
  requirements, deterministic/Impeccable-style anti-pattern checks, and
  patch-back rule.
- `non_copy_policy`: confirms no upstream template, class name system, page
  layout, long prompt, or bundled runtime is copied.

`html_source_map.json` connects visible HTML back to `slide_plan.json`,
`visual_contract.json`, source cards, image rows, and motion entries. This lets
visual feedback become source changes instead of one-off DOM edits.

## Workflow

1. Route card: confirm that HTML is the final or companion delivery, whether a
   static PPTX/PDF is also needed, and motion level.
2. Source and content package: write the same research dossier, content
   contract, and slide plan used by PPTX routes.
3. Shape the HTML surface before rendering:
   - write or update `html_product_context` and `html_generation_playbook`;
   - choose color strategy, theme scene sentence, primary interaction model,
     motion level, and anti-references;
   - define composition axes per slide, such as asymmetric editorial, object
     canvas, process path, kinetic typography, spatial map, or quiet reading
     field. These axes replace mandatory `Lxx` / `ITLxx` selection.
4. Style discovery: produce three web-deck candidates:
   - safe fit: domain-appropriate and easy to approve;
   - distinctive fit: stronger visual identity while preserving credibility;
   - wildcard: useful contrast, explicitly marked risky.
5. Four-slide HTML preview for decks over seven slides: cover/opening, dense
   proof, diagram/process, and breathing/closing or turning-point slide.
6. Kernel lock: after approval, write `html_design_kernel.json`,
   optional `html_layout_intent`, `html_source_map.json`, and the planned
   `html_delivery_manifest.json`. For HTML-only delivery, lock semantic role,
   hierarchy, component family, density, composition axes, renderer freedoms,
   and avoid rules; do not require a PPTX-style absolute coordinate
   `layout_execution_contract` or fixed pattern id unless PPTX parity or SVG
   export is also requested.
7. Full generation: render semantic HTML slide sections, local assets, optional
   motion manifest, presenter notes if needed, and host chrome outside stage.
8. Critique/polish: run `validate_html_deck.py`, capture browser screenshots at
   least at 1280 x 720 and 1440 x 900, then perform an Impeccable-style review:
   AI-slop/anti-pattern check, hierarchy and cognitive-load critique, contrast
   and overflow check, and source-map patch-back. Update the manifest with
   report paths plus unresolved findings.

## Stage Model

Prefer a locked coordinate stage:

- internal stage: `1920 x 1080`;
- scaler: `scale = min(viewportW / 1920, viewportH / 1080)`;
- position: explicit `left` and `top` offsets from the scaled size;
- `transform-origin: top left`;
- viewer chrome outside the stage;
- slide text/layout tokens derived from the fixed coordinate system.

CSS `aspect-ratio: 16 / 9` is acceptable when geometry is not trying to match a
PPTX/SVG coordinate system. Avoid flex/grid centering of an unscaled 1920px DOM
box combined with a scale transform; it commonly causes sideways cropping.

For HTML-only decks, the fixed stage is a reading and QA boundary, not a demand
that every element be assigned PPTX-like `x/y/w/h` coordinates. Use
coordinates only where they clarify a chart, map, diagram, or motion path.
Normal title/body/quote/comparison/process pages can use semantic DOM
containers, CSS grid/flex, and tokenized spacing, then prove the result through
screenshots and `html_source_map.json`.

Do not demote HTML to "PPTX rendered in a browser." The stage is a theatrical
frame; inside it, the renderer may use asymmetric compositions, scroll-free
micro-scenes, CSS masks, generated or source images, Canvas particles, clipped
typography, and responsive DOM components as long as the slide remains
semantic, searchable, stable under screenshots, and grounded in the slide plan.

## Style Discovery Rules

Style previews must look like real first slides, not mood boards. Borrow the
Impeccable discipline of named context and anti-references: each preview
records:

- target audience and scene;
- domain-fit reason;
- avoid-style reason;
- token sketch;
- layout rhythm;
- composition axes and what is deliberately unconstrained;
- image/media role;
- motion level;
- anti-patterns it avoids;
- risks.

For serious AI, infrastructure, enterprise, research, production, or evidence
decks, default to credible technical/editorial language: real screenshots,
system diagrams, field evidence, product surfaces, chart discipline, and
high-contrast Chinese typography. Avoid watercolor, cute illustration, generic
purple gradients, fake glass, decorative cards, and ungrounded sci-fi unless the
user explicitly chooses that risk.

## Semantic HTML Rules

- Use `<section class="slide">` for each slide.
- Do not require SVG to generate a formal HTML PPT. Prefer native DOM text,
  lists, grids, media containers, charts, notes, CSS, and JS navigation.
- Each slide has stable `data-slide-id` and `data-layout-id`. For HTML-only
  decks, `data-layout-id` is an expressive intent id, not a mandatory pattern
  library key.
- Each major visible element has `data-screen-label` or a stable id.
- Non-decorative images have `data-image-slot` and a manifest row.
- Presenter notes are in semantic off-stage markup such as `<aside class="notes">`.
- Search/progress/counters/navigation live in host chrome, not inside slides.
- Visible slide content is native DOM/CSS/JS first. SVG and Canvas layers are
  allowed for diagrams, charts, maps, particles, or motion, but text and proof
  objects should stay inspectable where practical.
- Avoid layout-pattern monoculture: do not make every page a card grid, left
  text/right media split, centered title stack, or numbered section marker.
  Vary topology because the content asks for it, not because the pattern
  library has a nearby option.

## Motion Rules

Motion should reveal reading order, compare before/after states, emphasize
chart evidence, or transition sections. It should not be a texture layer.

Use levels:

- `none`: static deck.
- `subtle`: CSS fades/reveals/section transitions.
- `expressive`: authored timelines for charts, diagrams, or sequence reveal.
- `cinematic`: rare; needs explicit fallback, heavier browser QA, and a reason.

When using GSAP, Lottie, dotLottie, WebGL, or custom canvas animation, package
or declare the engine, write `html_motion_manifest.json`, respect
`prefers-reduced-motion`, and provide a readable static final state.

## Innovation Bar

A Qiaomu HTML deck should improve on copied-template workflows by combining:

- source-backed narrative planning;
- approved style candidates before production;
- a design kernel that survives export and review;
- semantic source maps for point comments;
- content-bound generated/source imagery;
- browser QA plus package budgets;
- Impeccable-style shape/critique/polish loops and anti-pattern detection when
  available;
- optional presenter and motion layers that do not pollute the slide canvas.

If a deck is merely a third-party template with swapped text, it fails this
route even if it looks polished.
