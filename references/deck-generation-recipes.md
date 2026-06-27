# Deck Generation Recipes

Qiaomu PPT should expose a small set of repeatable source-to-deck workflows.
The recipes live in `data/ppt_generation_recipes.json`; this document explains
how to use them.

Recipes are not templates. A recipe defines the production path, required
evidence, style picker defaults, and quality risks for a source type.

## Recipe Selection

Pick a recipe when the input shape is obvious:

- URL, X article, blog, WeChat article -> `url_article_to_talk_deck`
- README or repository -> `readme_to_pitch_deck`
- PDF/report/book excerpt -> `pdf_report_to_research_deck`
- HTML-native interactive request -> `html_interactive_deck`
- Existing deck delivery prep -> `speaker_notes_delivery`

If no recipe fits, use the normal router and record `recipe_id: custom`.

## Recipe Contract

Record this in `deck_brief.md`, `design_proposal.md`, or a sidecar:

```json
{
  "recipe_id": "readme_to_pitch_deck",
  "route": "brand_release",
  "required_steps": ["read_readme_and_repo_assets", "tighten_one_line_pitch"],
  "default_archetype": "product_launch",
  "preferred_visual_families": ["technical_terminal", "data_dense_pro"],
  "quality_rules": ["Do not invent metrics", "Slide 11 contains a specific ask"]
}
```

The recipe should influence the deck before visual rendering:

- source-intake route;
- story arc;
- proof and evidence requirements;
- visual family defaults;
- speaker notes or delivery artifacts;
- QA gates and failure repairs.

## README To Pitch Deck Rule

A README is not enough by itself if it lacks:

- one-line product pitch;
- user-language problem;
- alternatives or differentiation;
- proof points such as metrics, screenshots, customers, demos, or adoption;
- a specific ask or next action.

If these are missing, tighten or report the gap before generating a polished
pitch deck. Never invent proof to fill slide 7.

## URL/X Article To Talk Deck Rule

Do not turn each paragraph into a slide. Extract:

- main claim;
- tension or contradiction;
- concrete examples;
- mechanism or causal chain;
- counterargument;
- memorable close.

Then build a speaker-ready story with claim titles and source-backed proof
objects. If image generation is available, use it for concept/atmosphere pages
only after source evidence and real images are considered.

## Token And Iteration Discipline

For HTML/high-design decks, spend effort in this order:

1. source and design context;
2. four representative slides: cover, dense proof, visual/diagram, closing;
3. targeted fixes to the source contract or renderer;
4. full deck generation after preview acceptance;
5. final export and validation.

Do not regenerate a whole deck for a one-slide spacing or title problem unless
the underlying contract is wrong across the deck.
