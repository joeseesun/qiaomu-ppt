# Qiaomu Visual Systems

These are independent visual route families for `qiaomu-ppt`. They are inspired by local research but are Qiaomu-owned abstractions.

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
- Write the chosen preset into `style_brief.md` and `spec_lock.json`; do not leave it as a loose inspiration note.
- Prefer route fit and `avoid_for` safety over superficial brand similarity.

Avoid:

- using third-party logos, proprietary fonts, screenshots, or brand assets unless provided by the user
- copying upstream `DESIGN.md` text into the deck
- applying web UI chrome literally when PPT readability needs a simpler shape system

## Background Rhythm Matrix

For decks longer than 8 slides, define at least 4 roles before production. Use these as a rhythm, not as one-off decoration:

| Role | Use | Background | Layout |
|---|---|---|---|
| `hero_dark` | cover, chapter opener, closing | dark or image-led | sparse title, one strong visual |
| `evidence_dark` | dramatic proof slide | dark canvas + bright evidence card | chart/image plus compact takeaway rail |
| `evidence_light` | dense chart/table readability | light canvas | chart owns 65-85% of slide |
| `split_panel` | comparison or explanation | two-tone or divided surface | 50/50 or 60/40 split |
| `diagram_focus` | architecture/process | quiet canvas or generated bitmap | centered diagram with compact labels |
| `claim_card` | argument transition | solid field or paper band | one large sentence, small proof |

Rules:

- No role repeats more than 2 consecutive slides.
- Thumbnail scan must show visible variation in background tone, dominant object placement, and slide density.
- Keep motif continuity through palette/type/spacing, not by repeating one side stripe or one card forever.
- If a page uses a dense source image, background should become quieter, not busier.

## Calm Background System

The default visual taste for `qiaomu-ppt` is calm, not loud. The deck should feel authored and premium, but the background must never compete with the message.

Rules:

- Default `visual_noise_budget` is `quiet`.
- Use generated bitmap backgrounds when the environment supports it; otherwise use large quiet surfaces and paper bands. Generated backgrounds are atmosphere only: color, gradient, light, grain, and abstract texture.
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
