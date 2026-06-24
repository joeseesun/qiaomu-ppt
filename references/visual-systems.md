# Qiaomu Visual Systems

These are independent visual route families for `qiaomu-ppt`. They are inspired by local research but are Qiaomu-owned abstractions.

See [reference-system.md](reference-system.md) for the full separation between
deck mode, visual style, image rendering, image palette behavior, image type,
image layout, SVG object model, and visual review. This file describes visual
systems only; it does not decide the deck's rhetorical mode by itself.

## Mode And Style Are Separate

Before selecting a visual system, choose the deck mode:

| Deck Mode | Primary Job |
|---|---|
| `pyramid` | recommendation or executive argument |
| `narrative` | audience state transfer and persuasive story |
| `instructional` | learning state transfer and practice sequence |
| `showcase` | object/case/product proof |
| `briefing` | situation, risk, and next action |

Then choose a visual style/system. A `pyramid` deck can be Swiss, editorial, or
data-journalism. A `zine`-style deck can still be instructional, narrative, or
showcase. Do not let a style word replace the content structure.

## A. Launch Editorial

Best for:

- brand release
- creator keynote
- industry viewpoint
- product story with emotion and images

Rules:

- Use strong title sequence and few words per slide.
- Mix serif or high-personality display type with calmer sans body type.
- Use full-bleed or large-slot imagery only when it supports the story.
- Use a rhythm of cover, claim, evidence, diagram, proof, and closing pages; do not make every slide a sibling of the first evidence page.
- Prefer cinematic restraint over decorative density.
- Speaker notes carry nuance; slides carry signal.

Avoid:

- fake suspense titles
- generic SaaS cards
- random purple/blue gradients
- image prompts that generate slide chrome

## B. Swiss Evidence

Best for:

- technology/product analysis
- data-backed claims
- systems and frameworks
- clean brand releases

Rules:

- One anchor color plus black/white/gray.
- Strong grid, left alignment, thin rules, direct labels.
- Large type should be lighter; small type must be heavier enough to read.
- Images are evidence blocks, not decoration.
- Every image has a declared slot and ratio.
- Alternate evidence treatments: full-chart, chart-with-rail, metric-grid, process/architecture, and takeaway-only. A deck of repeated chart-left/bullets-right pages fails this route.

Avoid:

- rounded shadows, glassmorphism, gradients, uncontrolled cards
- invented page structures when a layout family has been chosen
- captions near bottom navigation or unsafe areas
- fake rounded image frames where the image is not actually clipped to the frame

## C. Classroom Clear

Best for:

- high school courseware
- lesson explanation
- review and exercise decks

Rules:

- Start from teaching objective and learner state.
- Use concept -> example -> practice -> summary rhythm.
- Use teacher notes for questions, likely misconceptions, and answer reveals.
- Keep projection readability above visual novelty.
- Split dense material; do not shrink into unreadable text.

Avoid:

- launch-deck minimalism
- decorative hero slides that do not teach
- hiding answers or formulas in tiny notes

## D. Fast Preview

Best for:

- quickly deciding a deck look
- comparing style directions
- aligning with the user before full PPTX production

Rules:

- Generate 2-3 real title/cover previews, not abstract option cards.
- Put no internal labels on the slide itself.
- Use actual deck title/content.
- Choose diverse directions: safe, strong, wildcard.
- After selection, translate the chosen style into the production contract.

## E. Design-MD Preset Library

Best for:

- user asks for automatic PPT style recommendation
- brand/industry is clear but visual direction is not
- comparing several aesthetics before PPTX production
- adapting web/product design language into slide language

Rules:

- Use `data/design_style_presets.json` as the machine-readable source.
- Use `scripts/recommend_style.py` when no style is specified or when the user asks for candidates.
- Treat preset output as a PPT abstraction: palette, typography, slide patterns, media policy, chart policy, and animation hints.
- Resolve concrete type choices through `data/font_manifest.json`. Use Noto Sans CJK SC as the Chinese-first workhorse, Inter Variable for modern Latin titles and numbers, IBM Plex Sans for stable Latin body/technical text, and Noto Serif CJK SC sparingly for editorial or quote-led slides. Optional packs are role-specific: Smiley Sans for short display covers, LXGW WenKai for warm courseware/reading decks, and Sarasa Mono SC or JetBrains Mono for code, terminal, and aligned CJK/Latin snippets.
- Write the chosen preset into `style_brief.md` and `spec_lock.json`; do not leave it as a loose inspiration note.
- Prefer route fit and `avoid_for` safety over superficial brand similarity.

Avoid:

- using third-party logos, proprietary fonts, screenshots, or brand assets unless provided by the user
- copying upstream `DESIGN.md` text into the deck
- applying web UI chrome literally when PPT readability needs a simpler shape system

## F. Magazine Art Direction

Best for:

- essay-to-slides and thought-leadership talks
- knowledge cards and social preview packs
- culture/media/creator decks
- luxury editorial direction exploration
- visual moodboard or four-slide preview

Rules:

- Use the guidance in [magazine-art-direction.md](magazine-art-direction.md).
- Treat the slide as a magazine page: headline, deck/subtitle, folio, pull
  quote, sidebar, editor note, and one strong image/proof object.
- Select one primary magazine variant for a production deck. Use multiple
  variants only for a style gallery, moodboard, or preview gate.
- Keep Chinese text, quotes, QR/source marks, charts, and labels editable.
  Generated images provide atmosphere, collage, paper, object, or fashion
  texture only.
- Use `data/magazine_art_styles.json` as the machine-readable style index. The
  default `recommend_style.py` command loads it alongside the Design-MD library.
- Record variant choice in `style_brief.md` and `spec_lock.json`, such as
  `magazine_variant: art_deco` or `magazine_variant: deconstructed_swiss`.

Avoid:

- randomizing many unrelated magazine variants inside one final deck
- turning every slide into a 440px card composition
- ornamental frames behind dense evidence
- fake magazine text baked into generated images
- using QR blocks unless they have a real source/action purpose

## G. PPT Master Case Grammar

Best for:

- borrowing proven PPT style and layout grammar without depending on upstream
  skills at runtime
- choosing an image/chart-rich direction for a deck before writing
  `spec_lock.json`
- avoiding the common failure where the deck has nice colors but no visual
  substance

Rules:

- Use `data/ppt_master_case_styles.json` as a searchable case style index.
  The default `scripts/recommend_style.py` command loads it with the Design-MD
  and Magazine Art Direction libraries.
- Use `data/ppt_master_examples_catalog.json` and
  [ppt-master-example-catalog.md](ppt-master-example-catalog.md) as the deeper
  case-study map when a direction needs concrete evidence: slide count, local
  image count, `page_charts`, `page_rhythm`, notes, animations, and final SVG
  geometry.
- Treat each case as a bundle of decisions:
  `archetype`, `qiaomu_visual_system`, `page_rhythm`, `image_rendering`,
  `image_palette_behavior`, `image_asset_strategy`, `slide_patterns`,
  `chart_policy`, and `avoid_for`.
- When a case style is selected, record it in `style_brief.md`, such as
  `case_style: pptmaster-case-data-journalism`, and copy the relevant asset and
  chart constraints into `spec_lock.json`.
- Build the source and visual asset plan before slide rendering. Rich examples
  work because they have real photos, source figures, tables, charts, icons,
  maps, screenshots, or diagrams. If the source lacks those, either fetch more
  evidence, generate atmosphere-only concept images, or choose a more
  text/diagram-led style.
- Treat image integration as a slot contract, not a filter. A polished source
  image page needs text clearance, real crop/mask, subtle edge definition,
  restrained shadow, color/contrast normalization, and surrounding negative
  space. Rounded corners and shadows are optional finishing details; they cannot
  rescue a layout where the image intrudes into title/body/proof text.
- Keep mode and style separate. A paper deck can use Academic Blueprint or
  Swiss Grid; a culture deck can use Architecture Editorial, Risograph Zine, or
  Magazine Art Direction depending on the image evidence.
- Do not copy upstream images, templates, exact slide wording, or code. Recreate
  foreground objects from Qiaomu slide plans and user/source evidence.

Case mapping:

| Case Style | Qiaomu Visual System | Decks It Improves |
|---|---|---|
| Academic Blueprint | Swiss Evidence | paper-to-PPT, technical seminar, algorithm or architecture explanation |
| Data Journalism | Swiss Evidence | market report, annual review, industry briefing, data-backed strategy |
| Architecture Editorial | Launch Editorial | design/culture talk, biography, image-rich place story |
| Swiss Grid | Swiss Evidence | methodology, courseware, old deck cleanup, framework explanation |
| Glassmorphism SaaS | Launch Editorial | AI product launch, SaaS demo, UI screenshot story |
| Memphis Pop | Fast Preview | youth/event/creative campaign, festival guide |
| Risograph Zine | Launch Editorial | indie culture guide, bookstore/zine workshop, creator community |
| Brutalist Newspaper | Swiss Evidence | dossier, media briefing, annual observation, critical essay |
| Engineering Blueprint | Swiss Evidence | infrastructure, Kubernetes, AI agents, developer workflow |
| Top Consulting | Swiss Evidence | executive strategy, loyalty, root-cause diagnosis, roadmap |
| Luxury Editorial Digest | Launch Editorial | fashion, home, lifestyle, premium trend digest |
| Eastern Culture Narrative | Launch Editorial | Chinese culture, craft, plant dye, heritage, poetic object decks |
| Image-Text Layout Showcase | Launch Editorial | visual essays, portfolios, composition exploration |
| Urban Renewal Editorial | Launch Editorial | architecture humanities, museum exhibition, before/after case studies |

Avoid:

- selecting a case style after the deck has already been laid out
- using a high-image style when no images can be fetched, generated, or provided
- copying case palettes while ignoring their chart and media policy
- making every slide a literal clone of one admired example

## Style Selection Discipline

The style library exists to prevent visual sameness. Do not let previous decks or recent context silently choose the next deck's style.

Before production, compare at least three visibly different candidates:

| Candidate Type | Purpose | Example Direction |
|---|---|---|
| conservative fit | safest route match | Swiss Evidence, Apple-like clarity, IBM technical rigor |
| distinctive fit | stronger personality | editorial argument, high-contrast magazine, studio poster restraint |
| wildcard | useful surprise | playful creative canvas, monochrome typographic, warm classroom |

For each candidate, state:

- palette and max active colors
- typography stack
- layout rhythm
- chart/diagram treatment
- media/background treatment
- risks and avoid conditions

Then pick one selected direction. The selected direction must be traceable to `style_recommendations.json`, `style_brief.md`, and `visual_contract.json`. If the same visual system has been used in the previous two generated decks, prefer a different system unless the user explicitly asks for continuity.

Failure signs:

- multiple decks all look like dark editorial copper/teal pages.
- every deck uses the same title-left, card-right pattern.
- the style recommendation output exists but is ignored.
- “quiet” is interpreted as “visually identical.”

## Background Rhythm Matrix

For decks longer than 8 slides, define at least 4 roles before production. Use these as a rhythm, not as one-off decoration:

| Role | Use | Background | Layout |
|---|---|---|---|
| `cover_atmosphere` | cover and opening thesis | dark or image-led atmosphere | sparse title, one strong visual |
| `dark_evidence` | dramatic proof slide | dark quiet surface + evidence object | chart/image plus one clear takeaway |
| `light_evidence` | dense chart/table readability | light quiet surface | chart owns 65-85% of slide |
| `diagram_focus` | architecture/process | quiet canvas, generated bitmap, or procedural SVG | centered diagram with compact labels |
| `closing_atmosphere` | closing action or final statement | dark quiet atmosphere | action path or final claim |

Rules:

- No role repeats more than 2 consecutive slides.
- Do not use the exact same background asset on consecutive slides. If two neighboring slides need the same base role, assign different role variants such as `dark_evidence` and `dark_evidence_v2`.
- For decks longer than 8 slides, prefer one unique background asset per slide up to 12 slides. Reusing a base family is allowed, but the actual asset must visibly change in tone, light direction, focal area, or surface treatment.
- "Different seed, same-looking background" fails. The thumbnail grid must make the background rhythm obvious without reading filenames.
- Thumbnail scan must show visible variation in background tone, dominant object placement, and slide density.
- Keep motif continuity through palette/type/spacing, not by repeating one side stripe or one card forever.
- If a page uses a dense source image, background should become quieter, not busier.

Background planning must be explicit in the design proposal. State whether the deck will use built-in image generation, procedural backgrounds, source imagery, or plain surfaces. If Codex image generation is available and the deck is a talk, brand, or technical evidence deck, default to generating 3-5 candidate backgrounds or concept images before final rendering unless the user forbids it.

## Calm Background System

The default visual taste for `qiaomu-ppt` is calm, not loud. The deck should feel authored and premium, but the background must never compete with the message.

Rules:

- Default `visual_noise_budget` is `quiet`.
- Use generated bitmap backgrounds when the environment supports it; otherwise use deterministic CSS/Canvas/SVG procedural backgrounds, large quiet surfaces, or paper bands. Generated and procedural backgrounds are atmosphere only: color, gradient, light, grain, abstract texture, soft noise, or subtle mathematical forms.
- Generated backgrounds must not include boxes, rectangles, panels, cards, frames, placeholders, chart areas, image slots, windows, UI chrome, or text blocks. Those are editable foreground objects.
- Do not use ornamental grids, random thin rules, tech lines, side rails, or abstract stripes as decoration. Lines are allowed only as chart axes, table rules, connectors, or true content structure.
- Use one accent system per slide. Do not combine neon wedges, rails, glows, multiple card stacks, and saturated dots on the same page.
- Enforce a max-three active color budget per slide: neutral base, readable text, and one accent. Source images/charts are exempt, but surrounding UI must become quieter when a source image is colorful.
- Evidence slides should use the quietest backgrounds in the deck.
- Decorative shapes should not occupy more than roughly 15% of a slide unless they are the main subject.
- Avoid repeated hard side stripes, oversized cyan wedges, heavy shadows, glassy cards, and ornamental backgrounds behind charts.
- If the thumbnail grid feels energetic but the individual slide is harder to read, the background failed.

Preferred background families:

| Family | Use | Treatment |
|---|---|---|
| `generated_cover` | cover, chapter open, closing | full-slide text-free atmosphere bitmap, quiet focal depth |
| `generated_evidence` | technical proof, source charts | atmosphere bitmap only; chart frames and cards stay editable foreground objects |
| `quiet_dark` | technical proof, product narrative | near-black/navy ground, no decorative lines |
| `quiet_light` | dense charts, courseware, reports | off-white/paper surface, no ornamental rules |
| `editorial_band` | chapter open, argument transition | wide neutral band with one restrained accent edge |
| `split_surface` | compare, problem/solution | calm 50/50 or 60/40 surfaces without heavy shadows |
| `focus_canvas` | diagram/process | clean frame or generated surface, diagram owns attention |

Generated background prompt boundaries:

```json
{
  "atmosphere_only": true,
  "allowed": ["color fields", "soft gradients", "diffuse glow", "subtle grain", "abstract texture"],
  "forbidden": ["boxes", "cards", "panels", "frames", "placeholders", "chart areas", "image slots", "UI chrome", "text blocks"],
  "editable_foreground_policy": "titles, cards, charts, frames, diagrams, and labels are added later as editable objects"
}
```

## Color Budget

Every slide needs a color budget before rendering:

```json
{
  "max_active_colors_per_slide": 3,
  "count_source_images": false,
  "default_formula": "neutral base + readable text + one accent",
  "forbidden": ["rainbow metrics", "alternating accent bullets", "more than one accent family per page"]
}
```

Rules:

- A slide with dark background, white text, and cyan accent is valid.
- A slide with dark background, white text, cyan dots, green badges, yellow metric cards, and red metric cards fails.
- If semantic status colors are required, use shape, label, or ordering first; add a second semantic color only when the user explicitly needs it and the slide still stays within 3 active colors.
- If a screenshot or chart contains many colors, those colors belong to the evidence object, not to the surrounding slide system. The UI around it should use neutral plus one accent.

## Image Slot Contract

Every image/chart slot must be explicit before rendering:

```json
{
  "slot_id": "chart_main",
  "x": 0.7,
  "y": 1.4,
  "w": 7.2,
  "h": 4.8,
  "fit": "contain",
  "mask": "none",
  "padding": 0.12,
  "overflow_policy": "clip_or_fail"
}
```

Rules:

- `contain`: preserve the whole source image; use for benchmark charts and screenshots where labels matter.
- `cover`: crop for hero/product/lifestyle images only when the crop is intentional.
- `crop`: use only when the cropped region is declared in the slide note or style brief.
- `rounded_rect` mask requires actual clipping/compositing. A rounded rectangle behind an unmasked picture is a defect.
- If the renderer cannot clip images to rounded rectangles, use a square frame or pre-compose a rounded-card PNG.
