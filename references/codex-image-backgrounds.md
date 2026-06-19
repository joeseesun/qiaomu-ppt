# Codex Image Backgrounds

Use this when the runtime has an image generation tool, especially Codex with built-in image generation.

## Goal

Generate 3-5 quiet bitmap backgrounds for the whole deck before slide rendering. These backgrounds replace shape-based decorative backgrounds, but they must remain atmosphere only. They are not hero illustrations, posters, UI chrome, layout scaffolds, chart containers, cards, or frames.

## When To Use

- Use by default for brand launch, talk decks, and technical evidence decks when image generation is available.
- Use for courseware only if the generated background stays extremely quiet and does not reduce classroom readability.
- Skip only when the user forbids image generation, rights are unclear, or the deck must be fully deterministic without bitmap backgrounds.

## Background Pack

Create a small pack:

```text
assets/backgrounds/
  bg-cover.png
  bg-evidence-dark.png
  bg-evidence-light.png
  bg-diagram.png
  bg-closing.png
  background_prompts.json
```

Each background should be 16:9, preferably 1920x1080 or larger. It may contain color fields, gradients, soft light, subtle grain, atmospheric texture, and restrained abstract decoration. It must not contain text, logos, charts, UI controls, fake screenshots, boxes, panels, cards, frames, windows, placeholders, chart areas, image slots, text blocks, or hard ornamental lines.

## Prompt Rules

Prompts should specify:

- deck subject and mood
- route, such as brand launch, technical evidence, courseware
- background role
- color budget: neutral base plus one accent only
- atmosphere-only treatment: color, gradient, light, grain, and abstract texture
- no text, no icons, no UI, no logos, no boxes, no rectangles, no cards, no panels, no frames, no placeholders, no chart areas, no image slots, no decorative stripes, no glowing rails

Example:

```text
Create a quiet 16:9 presentation background for a technical evidence slide about long-horizon AI coding.
Near-black graphite color field, soft gradient depth, subtle material grain, one cyan accent glow kept below 8% of the frame.
Atmosphere only: no text, logo, UI, chart, image slot, card, panel, rectangle, frame, window, placeholder, grid, or neon rail.
All titles, cards, charts, frames, and layout objects will be added later as editable foreground elements.
```

## Use Rules

- Put the bitmap as the full-slide background.
- Add a soft scrim only when needed for text contrast.
- Do not use the bitmap to solve layout. Every card, evidence frame, title, label, chart slot, and diagram must be an editable foreground object.
- Do not add extra decorative lines, grids, wedges, or rails on top of the generated background.
- Use the same 3-5 backgrounds as a rhythm across the deck; do not generate one unrelated image per slide.
- If a source chart/image is colorful, make the generated background quieter and keep non-image UI neutral.

## Fallback

If image generation is unavailable:

- Use clean solid or subtly tonal surfaces.
- Keep at most one accent.
- Do not emulate generated backgrounds with baked-in boxes, cards, panels, frames, decorative stripes, grids, or random geometry.
- Record this in `visual_contract.json` as `background_asset_policy.generated_backgrounds: "unavailable"`.
