# Visual Character And Style Picker

This document turns external design-reference research into a Qiaomu-owned PPT
style selection method.

Do not expose raw design-history or web-design jargon to normal users. Public
choices should stay scenario-based through `data/html_style_archetypes.json`.
Internally, use `data/visual_character_families.json` to choose the visual
character that will drive typography, color, media policy, chart policy,
composition, and renderer behavior.

## Decision Order

Use this order before rendering:

1. Choose the user-facing scenario archetype when the output is HTML, public
   sharing, a style picker, or a user-facing design proposal.
2. Choose one primary visual-character family.
3. Choose at most one counterpoint family when the deck needs a deliberate
   tension, such as `data_dense_pro` proof with `warm_editorial` reading rhythm.
4. Translate the family into `style_direction.json`: typography, palette,
   density, media policy, chart policy, slide-level layout program, and avoid
   rules.
5. Record an explicit `avoid_family` when a tempting style would harm the task.

## Fit Before Taste

When the user does not specify a style, style selection is a content decision,
not a taste decision. Pick the visual character that best preserves the deck's
credibility, audience trust, evidence density, and intended action.

Do not choose a style because it is novel, pretty, or different from the last
deck. A style is suitable only when it helps the audience believe the claim,
inspect the proof, and remember the transition between pages.

Required default-selection fields:

```json
{
  "primary_visual_family": "the family that best serves this subject",
  "counterpoint_family": "optional family with a narrow job",
  "alternative_family": "the next-best viable family",
  "domain_fit_reason": "why this subject and audience need this visual language",
  "avoid_family": "a tempting but harmful direction",
  "avoid_reason": "why it would weaken clarity, trust, emotion, or reading",
  "image_content_binding_policy": "how images will belong to each page instead of acting as generic atmosphere"
}
```

If the selected style cannot produce concrete image subjects, annotation
targets, and a stable text surface for the slide claims, choose another style
before writing prompts.

## Domain Defaults And Avoids

Use these defaults when the user gives no visual direction. They are starting
points; source evidence and audience context can override them, but the override
must be recorded.

| Content domain | Default visual direction | Good image subjects | Avoid by default |
| --- | --- | --- | --- |
| Technical, AI, infrastructure, engineering, field deployment | `technical_terminal` + `data_dense_pro`, with `editorial_minimal` for chapter breath | real operations room, field engineer with customer workflow, system cutaway, trace/eval console, deployment pipeline, KPI loop, architecture wall | cute illustration, decorative cyberpunk, soft craft texture, fake dashboards |
| Market, strategy, finance, company analysis | `data_dense_pro` + restrained editorial | charts, tables, annotated source pages, product screenshots, market maps | cinematic atmosphere without evidence, fake dashboards, decorative metrics |
| Product launch or SaaS workflow | `cinematic_product` + `technical_terminal` when the product is technical | real product surfaces, user workflow, before/after use case, system integration | fake UI, glass-card stacks, abstract gradients without product signal |
| Teaching and knowledge explainer | `editorial_minimal` or `warm_editorial` with proof diagrams | examples, step diagrams, source objects, instructor-friendly whitespace | novelty illustration that hides the concept, tiny labels, decorative icons |
| Culture, history, biography, music, literature | `premium_cultural` or `warm_editorial` | primary artifacts, portraits, places, timelines, archival texture | generic antique paper, fake seals, fake documents |
| Creator, community, social talk | `warm_editorial` + controlled `playful_creative` | real moments, quotes, examples, behind-the-scenes objects | icon soup, random stickers, unreadable novelty type |

These defaults are not locks. A watercolor style can be excellent for a poetry,
craft, childhood memory, or art-history deck; it is weak only when it makes the
current subject less credible or less clear. A data-dense style can be excellent
for a market deck; it is weak when it turns an emotional biography into a
spreadsheet. Decide from the subject, not from a global blacklist.

## Three-Question Picker

Use these three questions internally. Ask the user only when the answer cannot
be inferred from the brief or source material.

1. Is the deck read-heavy, scan-heavy, media-heavy, or action-heavy?
2. Who is the audience: developers, decision-makers, learners, creators,
   consumers, or public readers?
3. Should the deck feel familiar/trustworthy, distinctive/brave, premium/calm,
   or high-energy?

Output one best family, one alternative, and one avoid note. Do not recommend a
long menu.

Example contract:

```json
{
  "user_facing_archetype_id": "research_report",
  "primary_visual_family": "data_dense_pro",
  "counterpoint_family": "warm_editorial",
  "why": "The source is scan-heavy and evidence-led, but the audience needs a readable argument rather than a dashboard.",
  "alternative_family": "editorial_minimal",
  "avoid_family": "cinematic_product",
  "avoid_reason": "Large hero imagery would hide source evidence and weaken trust."
}
```

## Style Remix Contract

Use remixing to avoid one-note decks, not to create style soup.

Allowed remix structure:

```json
{
  "base_family": "data_dense_pro",
  "counterpoint_family": "warm_editorial",
  "ratio": "70/30",
  "base_owns": ["layout density", "chart language", "table treatment"],
  "counterpoint_owns": ["surface warmth", "chapter rhythm", "speaker tone"],
  "non_negotiables": ["single accent", "no nested cards", "CJK body readability"],
  "conflict_resolution": "When density conflicts with warmth, proof pages follow base_family and chapter/summary pages follow counterpoint_family."
}
```

Rules:

- One family owns layout and proof language.
- The counterpoint family may own atmosphere, type tone, chapter rhythm, or
  surface warmth.
- Never mix two unrelated accent systems.
- Never mix two display-font personalities on the same slide.
- If a remix cannot explain which family owns which decision, use one family.
- If the counterpoint family makes the deck less credible for the content
  domain, reject the remix. For example, storybook warmth may help a children's
  courseware deck but can weaken compliance or production architecture proof;
  data-dense dashboard language may help finance but flatten a biography.

## Family To Slide Behavior

Visual family is not a skin. It must affect:

- `layout_mix`: which Lxx and ITLxx patterns appear.
- `composition_grammar`: whether the deck favors symmetry, asymmetry, data
  grids, poster contrast, or cinematic stage.
- `visual_asset_manifest`: whether images are source evidence, product media,
  generated concept art, portraits, diagrams, or quiet textures.
- `renderer_recipe`: which components are built, not just colors.
- `quality gates`: which failures are likely and must be checked.

Before image generation, translate the visual family into prompt-level rules:

- concrete page-specific subject
- camera/medium appropriate to the domain
- visible work object or evidence object
- protected text safe area
- annotation targets
- negative styles that would weaken credibility

Do not send prompts that only say "high-end", "tech", "editorial", "watercolor",
"cinematic", or similar surface adjectives without tying the image to the slide
claim.

## External Reference Boundary

The repository `rohitg00/awesome-claude-design` is useful as taxonomy and
workflow research. In Qiaomu PPT:

- learn its family/picker/remix/anti-slop organization;
- do not copy exact `DESIGN.md` files into projects;
- do not copy prompt text into the skill;
- do not inherit Claude Design product assumptions;
- do not treat web landing pages as PPT templates.

Every learned pattern must be re-expressed as Qiaomu-owned PPT contracts,
style families, recipes, QA gates, or renderer behavior.
