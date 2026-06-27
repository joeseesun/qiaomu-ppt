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

## Family To Slide Behavior

Visual family is not a skin. It must affect:

- `layout_mix`: which Lxx and ITLxx patterns appear.
- `composition_grammar`: whether the deck favors symmetry, asymmetry, data
  grids, poster contrast, or cinematic stage.
- `visual_asset_manifest`: whether images are source evidence, product media,
  generated concept art, portraits, diagrams, or quiet textures.
- `renderer_recipe`: which components are built, not just colors.
- `quality gates`: which failures are likely and must be checked.

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
