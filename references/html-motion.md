# HTML Motion

Formal HTML decks may use motion as an enhancement layer when the user asks for
an HTML version, an interactive presentation, a product launch page deck, or a
cinematic browser-first talk. Motion must serve the reading path. It is not a
generic decoration layer, and it must not become the only way to read the slide.

Use `data/html_motion_presets.json` as the machine-readable preset source, then
record the project decision in `html_motion_manifest.json`.

## Motion Levels

- `none`: no authored motion beyond basic slide navigation.
- `subtle`: default for business, research, and courseware HTML. Use CSS or
  GSAP for fade, reveal, small y/x movement, count-up, chart emphasis, and
  simple slide enter/exit.
- `expressive`: use GSAP timelines for product launches, public talks, and
  story decks where sequencing materially improves persuasion. Use labels,
  finite timelines, stable targets, and per-slide reset behavior.
- `cinematic`: HTML-first delivery. GSAP may orchestrate multi-object timelines
  and Lottie may play high-quality After Effects exports. This is not a promise
  of editable PPTX parity; provide static or poster fallback states.

## Engine Policy

### GSAP

Use GSAP when the deck needs precise timeline choreography: staged title
reveals, proof-object emphasis, chart growth, path motion, parallax, or
slide-transition sequencing.

- Prefer `gsap.timeline()` with labels over scattered delayed tweens.
- Animate transforms and opacity before layout properties.
- Use stable targets such as `data-motion-id`, `data-screen-label`, or element
  ids that map back to `html_source_map.json`.
- Build reset behavior so `window.qiaomuShowSlide(index)` can show any slide
  directly without stale animation state.
- Keep loops finite. Presenter navigation must not depend on an endless loop.
- Respect `prefers-reduced-motion`; the static state must remain readable.
- Count animated rays, orbits, speed lines, grids, and decorative paths against
  `background_decoration_budget`. GSAP should choreograph the reading path, not
  add a second background rhythm. Body slides default to `quiet` unless the
  line/path is the proof object.
- GSAP must not legitimize weak SVG decoration. Any animated line-like SVG
  element must pass `data-line-purpose` semantics from
  `data/line_semantics_policy.json`; "energy", "speed", "tech feel", and
  "atmosphere" are rejected purposes. If the motion is only mood, use opacity,
  transforms, scale, blur, particles, or bitmap atmosphere instead of stroked
  curves/lines.

### Lottie

Use Lottie when the visual should come from a prepared After Effects / Bodymovin
asset: logo reveal, icon motion, product flow, data metaphor, onboarding loop, or
hero accent.

- Store `.json` or `.lottie` files under the project asset folder. Do not rely on
  remote Lottie URLs at delivery time.
- Use `autoplay: false` and `loop: false` unless the deck explicitly needs a
  short, finite ambient loop and the manifest explains why.
- Keep container dimensions fixed and record the intended slot in
  `html_motion_manifest.json`.
- Provide a poster or readable static fallback for cinematic Lottie usage.
- Test the exported file in a browser. Not every After Effects effect survives
  Bodymovin export.

## Motion Manifest

When authored motion is used, write:

```text
<project>/html_motion_manifest.json
```

Recommended shape:

```json
{
  "schema_version": "1.0.0",
  "mode": "html_motion",
  "level": "expressive",
  "reduced_motion": "respect prefers-reduced-motion and render final static state",
  "engines": [
    {
      "id": "gsap",
      "source": "local",
      "path": "html/assets/vendor/gsap.min.js",
      "role": "timeline choreography"
    },
    {
      "id": "lottie-web",
      "source": "local",
      "path": "html/assets/vendor/lottie.min.js",
      "role": "After Effects JSON playback"
    }
  ],
  "fallback": {
    "static_state": "all slide copy and proof objects are readable without playback",
    "poster_policy": "cinematic Lottie assets declare fallback poster images"
  },
  "slides": [
    {
      "slide_id": "slide-01",
      "engine": "gsap",
      "timeline_id": "slide-01-intro",
      "purpose": "stage the opening claim before the proof object",
      "targets": ["hero-title", "hero-proof", "hero-media"]
    }
  ],
  "lottie_assets": [
    {
      "id": "brand-reveal",
      "path": "html/assets/lottie/brand-reveal.json",
      "poster": "html/assets/lottie/brand-reveal.png",
      "renderer": "svg",
      "autoplay": false,
      "loop": false
    }
  ],
  "qa": {
    "validated_with": "scripts/validate_html_deck.py --motion-manifest html_motion_manifest.json",
    "browser_checked": false,
    "console_errors": "not_checked"
  }
}
```

Also reference the manifest from `html_delivery_manifest.json`:

```json
{
  "motion_system": {
    "level": "expressive",
    "manifest": "html_motion_manifest.json",
    "engines": ["gsap", "lottie-web"],
    "fallback": "static final-state readable without motion"
  }
}
```

## Validation

Run the formal HTML validator with the manifest:

```bash
python3 <skill>/scripts/validate_html_deck.py \
  <project>/html/index.html \
  --motion-manifest <project>/html_motion_manifest.json \
  --json <project>/reports/html_deck_validation.json \
  --markdown <project>/reports/html_deck_validation.md
```

For final/professional HTML motion, add `--strict`.

The validator checks that:

- motion level is one of `none`, `subtle`, `expressive`, or `cinematic`
- GSAP/Lottie/dotLottie/custom engine ids are declared
- local engine and Lottie asset files exist inside the project
- Lottie assets are `.json` or `.lottie`
- Lottie does not autoplay
- reduced-motion and static fallback policy are declared
- per-slide motion targets exist in the HTML through ids, classes,
  `data-screen-label`, `data-motion-id`, or `data-motion-group`

Browser QA is still required. For motion-heavy decks, capture screenshots or
short clips for first, dense, diagram, and cinematic/hero slides; inspect console
errors; and record the evidence in `html_delivery_manifest.json` or
`html_motion_manifest.json`.

## Boundaries

- Formal HTML motion can exceed PPTX animation capability. Do not promise
  editable PPTX parity for cinematic GSAP/Lottie pages.
- If the user asks for both editable PPTX and extreme HTML motion, keep PPTX as
  the stable editable static deck and HTML as the enhanced presentation layer.
- Do not print engine names, Lottie provenance, generation notes, or fallback
  explanations on the audience-facing slide canvas.
- If GSAP/Lottie assets cannot be packaged locally, either list the external
  dependency explicitly in the manifest or downgrade to CSS/static motion.
