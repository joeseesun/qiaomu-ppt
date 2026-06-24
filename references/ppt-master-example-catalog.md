# PPT Master Example Catalog

This is the Qiaomu learning map for the full `hugohe3/ppt-master` gallery. It
does not make ppt-master a runtime dependency. Use it to study case structure,
asset density, chart vocabulary, image/text composition, notes, and spec-lock
discipline.

Machine-readable catalog:

- `data/ppt_master_examples_catalog.json`

Refresh command from this workspace:

```bash
python3 qiaomu-ppt/scripts/build_ppt_master_catalog.py \
  research/ppt-master/examples \
  --output qiaomu-ppt/data/ppt_master_examples_catalog.json
```

The online gallery loads the same shape of data from:

- `https://hugohe3.github.io/ppt-master/index.html`
- `https://hugohe3.github.io/ppt-master/examples/examples.json`

## What To Learn

For each case, inspect these layers in order:

1. `design_spec.md`: audience, story, visual concept, slide plan.
2. `spec_lock.md`: canvas, colors, typography, icons, images, page rhythm,
   page charts, and forbidden rendering moves.
3. `svg_final/*.svg`: actual geometry, grouping, chart construction, image
   slots, text hierarchy, and composition.
4. `images/`: source/generated image assets, formula images, prompt manifests,
   and image-density expectations.
5. `notes/`: speaker-note density and how slide text differs from narration.
6. `animations.json`: object-level animation vocabulary when present.
7. `exports/*.pptx`: final editable artifact for compatibility study.

Do not copy upstream images, SVGs, PPTX files, prompts, exact wording, or
templates into Qiaomu-generated decks. Absorb the grammar and rebuild from the
user's sources.

## Case Index

| Case | Style | Slides | Local Images | Page Charts | Learn From |
|---|---|---:|---:|---:|---|
| `ppt169_attention_is_all_you_need` | Academic Blueprint | 16 | 11 | 9 | chart-rich, technical-evidence |
| `ppt169_lora_hu_2021` | Blueprint Technical | 15 | 10 | 9 | chart-rich, technical-evidence |
| `ppt169_brutalist_ai_newspaper_2026` | Brutalist Newspaper | 10 | 5 | 8 | chart-rich, magazine-editorial, report-and-data |
| `ppt169_pritzker_2026` | Architecture Editorial | 11 | 25 | 0 | architecture-and-humanities, image-rich, magazine-editorial |
| `ppt169_global_ai_capital_2026` | Bloomberg Editorial | 20 | 3 | 12 | chart-rich, magazine-editorial, report-and-data |
| `ppt169_swiss_grid_systems` | Swiss Typographic | 14 | 3 | 9 | chart-rich |
| `ppt169_glassmorphism_demo` | Glassmorphism SaaS | 12 | 8 | 9 | chart-rich |
| `ppt169_sugar_rush_memphis` | Memphis / Pop | 14 | 9 | 8 | chart-rich, expressive-culture, report-and-data |
| `ppt169_indie_bookstore_zine_guide` | Risograph Zine | 18 | 10 | 12 | chart-rich, expressive-culture |
| `ppt169_kubernetes_blueprint_2026` | Engineering Blueprint | 10 | 0 | 4 | architecture-and-humanities, magazine-editorial, technical-evidence |
| `ppt169_high_rise_renewal` | Editorial Magazine | 15 | 25 | 2 | expressive-culture, image-rich, magazine-editorial |
| `ppt169_cangzhuo` | Chinese Ink Aesthetic | 14 | 6 | 2 | eastern-cultural-narrative |
| `ppt169_image_text_showcase` | Editorial Showcase | 20 | 22 | 0 | image-rich, layout-pattern-showcase, magazine-editorial |
| `ppt169_building_effective_agents` | General + Dark Tech | 12 | 9 | 0 | technical-evidence |
| `ppt169_fashion_weekly_digest` | Luxury Editorial | 16 | 23 | 0 | image-rich, magazine-editorial |
| `ppt169_home_design_trends_2026` | Magazine Editorial | 12 | 24 | 0 | expressive-culture, image-rich, magazine-editorial |
| `ppt169_kimsoong_loyalty_programme` | Top Consulting | 10 | 4 | 0 | report-and-data |
| `ppt169_lin_huiyin_architect` | 建筑人文纪念 | 10 | 14 | 0 | architecture-and-humanities, magazine-editorial |
| `ppt169_lin_huiyin_architect_revised` | 博物馆展陈风 | 9 | 13 | 0 | architecture-and-humanities, magazine-editorial |
| `ppt169_liziqi_plant_dye_colors` | 东方文化叙事 | 12 | 32 | 0 | eastern-cultural-narrative, image-rich, magazine-editorial |
| `ppt169_general_dark_tech_claude_code_auto_mode` | General + Dark Tech | 10 | 4 | 0 | case grammar |

## Use In Qiaomu PPT

- When selecting style candidates, consult both
  `data/ppt_master_case_styles.json` and this catalog. The style file provides
  reusable abstractions; the catalog points to concrete cases for deeper study.
- When a selected case has high local image count, require stronger source
  image planning in the user's project. Do not promise a similar result from
  weak text-only input.
- When a selected case has many `page_charts`, require chart specs or source
  data before rendering.
- When a case has no charts but high image count, use image-slot contracts,
  captions, crop focal points, and rights notes as the main visual QA surface.
- When a case is mainly a layout showcase, borrow only 3-5 compatible layout
  patterns for a production deck; do not turn every page into a different
  experiment unless the user requested a gallery.
