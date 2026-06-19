# Quality Gates

## Route Gate

- The route matches the expected final delivery.
- The skill did not choose HTML-only when the user needed editable PPTX.
- The skill did not force sparse launch-deck aesthetics onto dense courseware.

## Source Gate

- Product facts, prices, specs, dates, and claims are sourced or user-provided.
- Courseware facts, formulas, translations, historical claims, and exam standards are verified from supplied material or labeled draft assumptions.
- Image/logo rights are not assumed.
- Source and generation provenance is recorded in sidecar artifacts, not automatically printed on every slide.

## Narrative Gate

- Every slide has one clear intent.
- Brand/talk decks move the audience state forward.
- Courseware moves the learner state forward.
- No slide exists only because the template had room.

## Copy Gate

- Decks longer than 8 slides have a `content_contract.json` or equivalent audience-purpose card.
- The selected structure framework fits the route: `pyramid` for decisions/reports, `SCQA` for problem/proposal openings, `MECE` for complex decomposition, `storyline` for launch/fundraising/vision, and `teaching_arc` for courseware.
- Slide titles are claim titles, not vague labels. Reading only the titles should reveal the deck's argument.
- Each mainline slide has one dominant claim, one proof focus, and normally no more than 3-5 visible support chunks.
- Generic titles such as `背景`, `现状`, `问题`, `方案`, `数据`, `总结`, `Overview`, and `Agenda` are revised into specific claims unless the slide is an explicit navigation page.
- Speaker notes carry nuance, caveats, transitions, and likely objections; visible copy carries signal.

## Visual Gate

- The visual system has a thesis, palette, type scale, layout rhythm, and media policy.
- Decks longer than 8 slides have a `background_rhythm` with at least 4 roles and no role repeated more than 2 consecutive slides.
- Decks longer than 8 slides declare `visual_noise_budget`, normally `quiet`.
- Decks longer than 8 slides declare `color_budget` with `max_active_colors_per_slide <= 3`, and each slide declares `active_colors`.
- When Codex image generation is available, decks declare a 3-5 item generated background bitmap pack; if unavailable, the fallback must be neutral surfaces, not decorative linework.
- Generated backgrounds are atmosphere only. They must not contain boxes, rectangles, panels, cards, frames, placeholders, chart areas, image slots, UI chrome, or text blocks; these must remain editable foreground objects.
- The thumbnail grid shows visible variation in background tone, dominant object placement, and slide density.
- Backgrounds are calmer than the content: no repeated hard side stripes, oversized saturated wedges, stacked decorative motifs, meaningless tech lines, ornamental grids, or noisy chart backdrops unless explicitly brand-required.
- Lines are functional only: chart axes, table rules, connectors, or content separators. Lines that exist only to add texture or "tech feel" fail the visual gate.
- If style was unspecified, `style_recommendations.json` exists or the reason for skipping style recommendation is stated.
- Any selected Design-MD preset is copied into `style_brief.md` and `spec_lock.json` as PPT rules, not left as vague inspiration.
- No one-note generic palette, no default purple-gradient design, no arbitrary style mixing.
- Chinese content uses readable spacing and avoids obvious CJK layout failure.

## Image Slot Gate

- Every source image/chart has a declared image slot with `fit`, `mask`, `padding`, and `overflow_policy`.
- Images/charts do not exceed their intended frame in the rendered preview.
- A rounded rectangle behind an image is not accepted as clipping. Use real crop/mask/compositing, a square frame, or a native picture placeholder.
- Dense benchmark charts use `contain` or an intentional crop with a source note; do not stretch or crop silently.

## Readability Gate

- No overflow, overlap, clipped text, unreadable small type, or unplanned scroll.
- Important classroom content is visible from a projector-distance mindset.
- Speaker-led decks avoid walls of bullets.

## Provenance Gate

- Visible slide text does not include internal toolchain metadata such as `fetched via`, `generated with`, `qiaomu-markdown-proxy`, or `Speaker cue:`.
- Model names, fetch method, and QA evidence live in `generation_report.md`, `qa_report.md`, speaker notes, or a final references page.
- Visible source citations are opt-in or route-specific. When used, they cite content sources only; they do not expose generation tools.

## Production Gate

- Declared output files exist.
- Export commands completed successfully.
- Run `scripts/check_project.py` when a project folder exists.
- If an editable PPTX exporter is missing, the output is checked SVG/HTML artifacts plus `missing evidence`, not a claimed `.pptx`.

## Speaker Gate

- Brand/talk decks include presenter notes that explain what to say and why the slide exists.
- Courseware includes teacher notes: questions, expected answers, common misconceptions, and board-work cues.

## Verification Gate

- HTML previews are opened where possible.
- PPTX export exists and is opened where possible.
- A rendered thumbnail grid or equivalent visual evidence is reviewed when PPTX output exists.
- Missing native Office/WPS verification is explicitly marked `missing evidence`.
- Stop after 3 focused fix rounds and report unresolved risks.
