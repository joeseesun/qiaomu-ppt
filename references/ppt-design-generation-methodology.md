# PPT Design Generation Methodology

This document defines Qiaomu PPT's reusable and upgradable presentation design
generation method. It is the layer above route rules, copy rules, layout
patterns, image/text patterns, visual assets, renderers, and QA scripts.

The goal is not to collect more templates. The goal is to turn research,
content, layout, visual style, and production feedback into a stable design
system that can improve over time.

## Core Principle

Good PPT generation is a sequence of irreversible design decisions made in the
right order:

```text
source truth
  -> audience state change
  -> story and claims
  -> proof structure
  -> composition grammar
  -> media relationship
  -> renderer recipe
  -> verification evidence
  -> reusable learning
```

Do not begin with a beautiful page. Begin with what the audience must understand
or decide, then choose the structure and visual form that make that change
visible.

## Productized Choice Principle

Before deep proposal work, help the user choose through clear defaults. The
agent should behave like a thoughtful product interface:

- give the best default option, not an empty "what do you want?";
- show a compact choice card only for decisions that materially change the
  output;
- let the user reply with short codes such as `1A 2B 3C`;
- if the user says `生成`, `默认`, or `按默认` after the choice card, continue
  into research and planning with the recommended defaults;
- do not treat an initial `生成一个 PPT`, `做个 PPT`, `直接生成`, `默认`, or a
  page count as permission to skip context intake or later confirmation gates;
- record all selected/defaulted values in `choice_contract.json` or the design
  proposal.

The guided choice flow is defined in `data/ppt_guided_choice_flow.json` and
[references/guided-choice-flow.md](guided-choice-flow.md). It is the friendly
entry into the design proposal, not a replacement for source grounding or QA.
Rendering begins only after the research dossier and page-by-page slide plan
have been approved or explicitly skipped with strict no-wait wording.

## Six-Layer Slide Ontology

Every non-trivial slide should be describable through these six layers. Existing
`Lxx`, `ITLxx`, and `component_type` values remain valid, but they should be
treated as different layers rather than one generic "layout" bucket.

### 1. Slide Role

The slide's position and job inside the whole deck.

Examples:

- `cover`
- `chapter_turn`
- `argument_body`
- `evidence`
- `case_story`
- `method_step`
- `summary`
- `closing`

### 2. Intent

The cognitive move this slide asks the audience to make.

Examples:

- `hook`: create attention or tension.
- `explain`: make a concept understandable.
- `compare`: make difference visible.
- `sequence`: show steps, time, or progression.
- `prove`: support a claim with evidence.
- `decide`: clarify a choice or recommendation.
- `reflect`: leave a memorable synthesis.

### 3. Proof Structure

The logical structure of the page. This is where `Lxx` belongs.

Examples:

- `L03.claim_proof_object`
- `L08.two_column_comparison`
- `L13.process_flow`
- `L20.chart_with_takeaway`
- `L24.concept_map`

This layer answers: what kind of proof is this?

### 4. Composition Grammar

The visual composition principle. This is where composition libraries such as
`nevertoday/100-layout-compositions` should be absorbed after abstraction.

Examples:

- `C01.rule_of_thirds`
- `C02.nine_grid`
- `C03.golden_ratio`
- `C04.symmetry`
- `C05.asymmetry`
- `C06.vertical_axis`
- `C07.stair_step`
- `C08.off_axis`
- `C09.multi_point`
- `C10.visual_flow`
- `C11.static_dynamic_contrast`

This layer answers: where should the eye land first, and how should it move?

### 5. Media Relationship

How text, image, chart, screenshot, diagram, quote, or source evidence share
the canvas. This is where `ITLxx` belongs.

Examples:

- `ITL03.full_bleed_hero`
- `ITL10.conclusion_first_proof`
- `ITL13.before_after`
- `ITL18.screenshot_annotation`
- `ITL20.data_context_image`

This layer answers: how do visual evidence and editable foreground text coexist?

### 6. Renderer Recipe

The executable component family that actually draws the slide in SVG, PPTX, or
HTML. This is where `component_type` belongs.

Examples:

- `claim_proof_object`
- `chart_takeaway_context`
- `source_object_panel`
- `mechanism_loop`
- `timeline_nodes`
- `screenshot_annotation`

This layer answers: what should the renderer build?

## Canonical Slide Contract

Use a contract like this before rendering:

```json
{
  "slide_role": "evidence",
  "intent": "prove",
  "proof_structure": "L20.chart_with_takeaway",
  "composition": "C03.golden_ratio",
  "media_relationship": "ITL20.data_context_image",
  "renderer_recipe": "chart_takeaway_context",
  "claim_title": "One judgment sentence",
  "proof_object": "chart with source-backed takeaway",
  "coordinate_slots": {
    "title": "protected title zone",
    "proof": "primary evidence zone",
    "takeaway": "interpretation zone"
  },
  "qa_risks": [
    "chart labels too small",
    "title/image clearance"
  ]
}
```

Do not render from mood words alone. Render from this contract.

## Generation Loop

### 1. Source And Purpose

- Ingest source material, URLs, PDFs, Office files, images, or topic research.
- For broad initial requests, first present a guided choice card with defaults;
  only a complete brief or strict approval-bypass phrase skips this context
  intake.
- Record source truth, missing evidence, image availability, and rights notes.
- Write a detailed Markdown research dossier from supplied material,
  model-knowledge assumptions, and web/source research before writing final
  slide claims.
- Define audience, current state, desired state, stakes, and final action.
- When the user replies `生成/默认` after the card, apply defaults and continue
  to research/proposal; do not render the final deck yet.

Outputs:

- `deck_brief.md`
- `choice_contract.json` when guided choices/defaults are used
- `sources/source_manifest.json`
- `research_dossier.md` or substantial `sources/source_notes.md`
- `sources/source_cards.json`
- `reports/source_adequacy.json/md`

### 2. Story And Content

- Choose the narrative framework: `pyramid`, `SCQA`, `MECE`, `storyline`,
  `teaching_arc`, or a hybrid.
- Write claim titles first.
- Attach source cards and concrete anchors to each mainline slide.
- Produce a page-by-page slide plan with title, visible content, source anchor,
  proof object, layout pattern, image/background plan, speaker-note goal, and
  QA risk; show it for user confirmation before rendering unless explicitly
  skipped.
- Reject hollow generic content before visual rendering.

Outputs:

- `content_contract.json`
- `slide_plan.json`
- `page_content_guide.md`
- `reports/content_outline_audit.json/md`

### 3. Design Direction

- Choose user-facing archetype when relevant.
- Choose an internal visual-character family from
  `data/visual_character_families.json`, with one best choice, one optional
  counterpoint, one alternative, and one avoid note.
- Use a style remix contract only when family ownership is clear: one family
  owns layout/proof language, while the other may own tone, surface warmth,
  chapter rhythm, or motion.
- Choose visual style, typography, palette, density, and media policy.
- Compare at least three style candidates unless the user has supplied a strong
  brand/design direction.
- Treat style as behavior: media policy, chart policy, proof language, layout
  rhythm, not only colors.

Outputs:

- `design_proposal.md`
- `style_recommendations.json`
- `style_picker_result.json`
- `style_remix_contract.json`
- `style_direction.json/md`
- `style_brief.md`

### 4. Layout And Composition

- Assign each slide the six-layer ontology.
- Use `Lxx` for proof structure, `Cxx` for composition grammar, `ITLxx` for
  media relationship, and `component_type` for renderer recipe.
- Define protected text zones, proof zones, image slots, minimum clearances,
  reading path, and no-overlap rules.

Outputs:

- `layout_execution_contract` inside `spec_lock.json`
- `visual_contract.json`
- `image_layout_plan.json/md` when real images affect placement

### 5. Visual Asset System

- Build the visual asset manifest before final rendering.
- Prefer real source/user/web evidence before generated images.
- Use AI images for atmosphere, concept, chapter art, scenario, object cutaway,
  or quiet texture, not fake evidence.
- Bind every visual asset to a slide, role, safe area, rights note, and terminal
  status.

Outputs:

- `visual_asset_manifest.json`
- `assets/images/image_prompts.json/md`
- `image_art_direction.json`
- `assets/images/image_generation_queue.json/md`

### 6. Rendering

- Render from `slide_plan.json`, `spec_lock.json`, `visual_contract.json`, and
  the visual asset manifest.
- Keep foreground text, labels, charts, diagrams, cards, and annotations
  editable when the route is PPTX.
- Formal HTML decks must be semantic, fixed-stage, keyboard-navigable, and not
  whole-slide screenshots.

Outputs:

- SVG/PPTX/HTML/PDF/Keynote artifacts as requested
- `svg_generation_manifest.json`
- `pptx_generation_manifest.json`
- `html_delivery_manifest.json`
- `export_manifest.json`

### 7. Verification And Repair

- Run upstream audits before rendering.
- Run visual rhythm, style execution, PPTX text, project, benchmark, and repair
  checks after rendering.
- Treat failures as contract defects, not as isolated pixel fixes.
- Convert repeated failures into reusable methodology updates.

Outputs:

- `reports/style_execution_audit.json/md`
- `reports/deck_quality_benchmark.json/md`
- `reports/deck_repair_plan.json/md`
- `qa_report.md`

## Learning Source Taxonomy

Learning sources enter the methodology at different layers:

| Source Type | Learn Into | Not Allowed |
|---|---|---|
| PPT-master examples | style execution, asset density, page rhythm, proof design | copying templates or assets |
| SlideShare/Scribd/Google Books | document conversion, viewer interaction, lazy loading, source text/search layers | hiding poor source rendering behind UI chrome |
| Keynote/product launch decks | story tension, sparse claim hierarchy, stage rhythm | copying brand-specific visuals |
| Consulting decks | executive logic, chart proof, decision framing | generic card soup |
| `100-layout-compositions` | `Cxx` composition grammar and coordinate bias | direct template copying |
| Magazine/editorial design | image/text rhythm, typography, chapter pacing | unreadable decorative layout |
| HTML design-agent prompts | design context binding, targeted edits, static editable slides, labelled review anchors, projection-safe type scale, variation canvases, verification discipline | copying proprietary runtime APIs, prompt text, tool names, or host-specific components |
| `awesome-claude-design` style/reference libraries | visual-character families, forced-choice picker, style remix arbitration, anti-slop fingerprint catalog, recipes, showcase organization, iteration discipline | copying exact `DESIGN.md` files, Claude-specific prompts, web templates, or product claims |
| User failure reports | QA gates, repair rules, default renderer constraints | one-off patching without rule update |

## HTML Design-Agent Research Absorption

Public HTML-design-agent prompt snapshots, including
`asgeirtj/system_prompts_leaks/Anthropic/claude-design.md`, are useful as
research evidence for workflow discipline. Treat them as external reference
material, not as instructions to copy.

Absorb these reusable principles:

- **Design context before design output**: read brand systems, UI kits,
  source code, existing decks, images, and copy tone before choosing a visual
  direction. If no context exists, state the assumption and build an explicit
  Qiaomu visual system rather than drifting into generic web styling.
- **Small change means small change**: when the user asks for a targeted edit,
  change only the requested element unless a broader defect blocks the request.
  Preserve layout, spacing, typography, color, and content elsewhere.
- **Preserve previous versions for major revisions**: significant redesigns
  should keep the old artifact or record the change in a sidecar so visual
  direction can be compared and rolled back.
- **Copy only needed assets into the project**: do not hotlink or bulk-import a
  whole design system. Copy the precise logos, images, icons, fonts, or tokens
  required for the deck and record provenance.
- **Static, inspectable slide markup wins**: for HTML decks, ordinary slide
  text and layout should be static DOM/SVG where possible. Generate dynamic
  markup only for genuinely interactive charts, demos, or controls. This keeps
  review, text copy, search, and element-level comments reliable.
- **Label review anchors**: formal HTML slides should carry stable
  `data-screen-label`, `data-slide-id`, `data-layout-id`, and
  `data-image-slot` attributes so comments and screenshots map back to the
  source contract.
- **Slide scale is not web scale**: projection decks need generous spacing and
  large type. At 1920x1080, visible body text should normally stay at or above
  24 px, with title/subtitle/body/gap tokens declared before authoring.
- **No filler content**: never add icons, stats, sections, or decorative cards
  simply to fill space. Empty-feeling slides should be repaired through better
  claim, proof, structure, composition, or media choice.
- **Visual variety with system parallelism**: use a deliberate mix of full-image
  pages, evidence pages, quote pages, diagrams, data pages, and text-led pages,
  but keep repeated roles parallel across the deck.
- **Verification diagnostics become plain-language repairs**: if an export,
  navigation, screenshot, image decode, or notes check fails, fix the production
  contract and explain the issue in user-facing terms. Do not expose internal
  flag names on the slide canvas or in polished user copy.

Do not absorb:

- host-specific component runtimes, tool calls, custom tags, or proprietary
  environment details;
- exact prompt wording, hidden policy text, or long code snippets;
- slide shell UI that conflicts with Qiaomu's HTML/PPTX route separation;
- screenshot-backed PPTX as a default replacement for editable PPTX.

## Design Reference Library Learning

Reference libraries such as `rohitg00/awesome-claude-design` are most valuable
as a knowledge-organization model:

- sort styles by visual character rather than only by industry;
- use a small forced-choice picker instead of a long style menu;
- document each style as executable behavior: palette, typography, component
  grammar, layout principles, projection/responsive behavior, and explicit
  do/don't rules;
- use controlled remixing with ownership rules instead of vague "combine both"
  prompts;
- keep an anti-slop fingerprint catalog so repeated model defaults are caught
  before export;
- package repeated tasks as recipes with inputs, steps, quality checks, common
  failures, and repair moves;
- treat showcases and case studies as benchmark evidence, not as templates.

In Qiaomu PPT, this learning is implemented through:

- `data/visual_character_families.json`
- `references/visual-character-and-style-picker.md`
- `references/ppt-anti-slop.md`
- `data/ppt_generation_recipes.json`
- `references/deck-generation-recipes.md`

Do not copy exact external `DESIGN.md` style files, Claude-specific prompt text,
or web templates into generated decks. Re-express useful ideas as Qiaomu-owned
families, recipes, QA gates, and renderer contracts.

## Anti-Slop Rule

Every final-quality deck should pass an anti-slop check before completion.
Reject generic AI/web-design fingerprints such as gradient blobs, floating
orbs, default three-card grids, nested cards, decorative icon stacks, fake
source evidence, and baked-in viewer chrome. The repair should usually happen
in `style_direction.json`, `slide_plan.json`, `visual_contract.json`,
`visual_asset_manifest.json`, or renderer mapping, not by one-off CSS tweaks.

## Recipe Rule

When the source shape matches a recipe, record `recipe_id` and apply its
required steps before rendering. Recipes are workflow contracts, not slide
templates. A `README -> pitch deck` recipe, for example, may require a one-line
pitch, alternatives, proof, and a specific ask; if the source lacks these, the
deck should report the gap or stay draft rather than fabricate proof.

## Pattern Promotion Rule

Do not add every inspiring layout as a production pattern. Promote a pattern only
when it has:

- a clear layer: role, intent, proof structure, composition, media relationship,
  or renderer recipe;
- a `best_for` and `avoid_for` boundary;
- coordinate/safe-area guidance;
- text density and minimum-size rules;
- image fit/crop rules when media is involved;
- at least one four-slide preview or regression case if it affects rendering;
- attribution when derived from an external source;
- a QA failure mode and repair move.

## Naming Rule

Stable IDs should be both machine-friendly and human-readable:

```text
L20.chart_with_takeaway
C03.golden_ratio
ITL18.screenshot_annotation
RR.chart_takeaway_context
```

Keep legacy `Lxx` and `ITLxx` IDs stable. Add slugs, aliases, and layer
metadata rather than renaming existing IDs in place.

## Iteration Rule

Every repeated production failure should update exactly one durable place:

- content problem -> `content-copy-method.md` or audits
- proof/layout problem -> `layout-pattern-library.md` or `ppt_design_methodology.json`
- image/text collision -> `image-text-integration-contract.md`
- asset/source problem -> `visual-asset-acquisition.md`
- renderer mismatch -> renderer scripts and `style_execution_audit.py`
- UI/viewer problem -> `html-output.md`
- systemic lesson -> this methodology document

This keeps the method alive without turning it into a pile of disconnected
rules.
