# Magazine Art Direction

This reference adapts a user-provided "luxury digital magazine card" prompt into
Qiaomu-owned PPT style guidance. It is for decks that should feel like a
high-end editorial spread, not a SaaS dashboard or generic card grid.

## Core Thesis

Treat each slide like a magazine page with one editorial job:

- a cover or opener sells the issue
- a feature spread makes one argument memorable
- a pull quote gives the audience a sentence to keep
- an editor note adds a compact aside
- a folio/date/source mark gives the page publishing context
- a sidebar organizes supporting points without becoming a dashboard

Do not blindly generate ten unrelated styles inside one production deck. Use
one primary magazine direction for the full deck, with at most one controlled
variant for chapter turns or visual previews. Random multi-style output is only
appropriate for a style gallery, moodboard, or four-slide preview.

## PPT Component Mapping

The original card prompt includes date, title, subtitle, quote, key points, QR,
and editor note. For PPT, map those to presentation objects:

| Prompt Element | PPT Adaptation |
|---|---|
| date area | small folio, issue mark, section/date label, or source date |
| title/subtitle | editorial headline and deck, not generic slide label |
| quote block | pull quote or proof sentence |
| core points | editorial sidebar, numbered notes, or short evidence rail |
| QR area | optional source/action code only when the user asks for it |
| editor note | callout, speaker-note cue, or "why this matters" marginalia |

Keep all readable text editable in SVG/PPTX/HTML. Generated images may provide
texture, photography, collage, or atmosphere, but should not bake in Chinese
body text, tables, QR codes, chart values, or citations.

## Style Families

The prompt lists 29 entries, with Memphis appearing twice. Treat the later,
more detailed Memphis entry as a separate variant rather than a mistake to hide.
Use `data/magazine_art_styles.json` as the machine-readable index.

Useful PPT groupings:

| Family | Variants | Best Use |
|---|---|---|
| restraint | Minimalist, Japanese Minimalism, Extreme Minimalism, Hypersensory Minimalism, Scandinavian | serious essays, premium reports, calm quotes |
| editorial luxury | Elegant Vintage, Art Deco, Victorian, Neo-Baroque Digital | luxury, culture, history, brand ritual |
| modern impact | Bold Modern, Deconstructed Swiss, Bauhaus, Constructivism | strong argument, manifesto, launch keynote |
| experimental culture | Postmodern Deconstruction, Punk, British Rock, Black Metal, German Expressionism | counterculture, media critique, music/culture decks |
| digital future | Futuristic Tech, Cyberpunk, Vaporwave, Neo-Futurism, Liquid Digital Morphism | AI, future, speculative technology |
| visual play | Memphis, Pop Art, Neo-Expressionism, Surrealist Digital Collage | creative workshops, public social cards, style previews |
| data editorial | Neo-Expressionist Data Visualization | data storytelling that should feel authored, not dashboard-like |

## Editorial Rules

- One slide has one headline idea. The headline is the page's editorial claim.
- Use typography as hierarchy: display headline, deck/subtitle, body note,
  caption/folio. Do not make every text block the same weight.
- Use magazine whitespace. Empty space should feel intentional, not unfinished.
- Use image scale deliberately: full bleed, edge crop, figure overlap, or
  image-as-canvas with editable annotations.
- Use decorative systems sparingly. A style may allow ornament, but the content
  still needs a clear reading path.
- Use pull quotes when the source contains a sentence worth remembering. Do not
  invent a quote merely because the template has a quote slot.
- Keep QR codes optional. A visible QR block is useful for handouts and social
  cards, but usually unnecessary in a talk deck.

## Style Safety

Some variants are expressive enough to damage ordinary PPT readability:

- `black_metal`, `punk`, `postmodern_deconstruction`, and
  `german_expressionism` are preview/wildcard styles unless the brief asks for
  counterculture or strong emotional disruption.
- `futuristic_tech`, `cyberpunk`, `vaporwave`, and `liquid_digital_morphism`
  must avoid fake HUD clutter behind charts.
- `art_deco`, `neo_baroque_digital`, and `victorian` must keep ornament at the
  edge or chapter level; do not bury evidence in frames.
- `minimalist` and `extreme_minimalism` still need proof objects. Empty slides
  are not automatically premium.

## Recommended Stack

When model choice is available, current project experience favors:

- reasoning/layout/code: Claude Opus 4.8
- bitmap generation: gpt-image-2, including Codex built-in image generation when
  that environment exposes it

This is a recommendation, not a hard dependency. Record the actual model/tool
used in `generation_report.md` or `qa_report.md`, not on the visible slide
canvas.

## Prompt Adaptation Pattern

For a magazine-style PPT direction, write the style request like this:

```text
Use Magazine Art Direction as the visual system.
Deck mode: narrative or pyramid.
Primary variant: <one selected magazine variant>.
Visual intensity: quiet/editorial/expressive/experimental.
Editorial components: headline, deck/subtitle, pull quote, sidebar notes, folio.
Image policy: generated/source images provide atmosphere or object context only;
all text, charts, labels, QR/source marks, and annotations remain editable.
Do not mix unrelated variants across production slides unless this is a style
gallery or four-slide preview.
```
