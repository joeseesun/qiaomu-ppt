# Anthropic PPTX Skill Method Adaptation

This document records Qiaomu-owned lessons abstracted from the public
`anthropics/skills/skills/pptx` directory and the locally installed `pptx`
skill. The upstream skill materials are proprietary. Do not copy upstream text,
scripts, prompts, assets, or examples into Qiaomu PPT. Use this page only as an
adaptation map for workflow design and QA behavior.

Source for study: https://github.com/anthropics/skills/tree/main/skills/pptx

## What To Absorb

### 1. Route By PPTX Operation

Treat PPTX work as three different jobs, not one generic generation task:

- read/analyze a deck
- edit/adapt an existing deck or template
- create a deck from scratch

Qiaomu PPT already has source intake and SVG-first creation. It should add a
stronger template-editing route for user-provided decks:

1. Render thumbnail grids for layout inventory.
2. Extract text for placeholder/content inventory.
3. Map each new content section to a varied existing layout.
4. Complete structural slide operations before text/media replacement.
5. Replace or remove all placeholder objects.
6. Repack and run visual QA.

### 2. Template Mapping Beats Blank-Slate Redraw

When a user gives a PPTX template or old deck, preserve useful masters, layouts,
theme colors, image masks, and object geometry where possible. Do not rebuild
everything from scratch unless the source deck is too broken or the user asks
for a new visual system.

Hard rules:

- If the template has more object slots than the source content needs, delete
  surplus objects and their related media instead of leaving empty shapes.
- If source content is longer than the slot allows, shorten, split, or select a
  different layout. Do not trust PowerPoint auto-wrap to save the page.
- Use varied layouts. Repeating the same text-heavy template slide is a defect.

### 3. Native PPT Object Details Matter

For fallback direct PPTX generation or template editing, record these
implementation constraints in the project renderer/checker:

- Text boxes have internal padding; when aligning with shapes, set or account
  for margins explicitly.
- Use real bullet/list structures, not pasted bullet glyphs.
- Use explicit line breaks or paragraph separation for multi-item content.
- Keep colors as six-character hex values without alpha channels in fields that
  do not support alpha.
- Use explicit shadow opacity fields rather than encoding opacity inside color
  strings.
- Do not reuse mutable option dictionaries/objects across generated shapes in
  libraries that mutate options.
- Treat rounded cards, image masks, accent bars, and shadows as geometry that
  must survive PPTX rendering, not as CSS-like decoration.

### 4. QA Is A Bug Hunt

Assume the first render has problems. The minimum PPTX verification loop is:

1. Generate or edit the PPTX.
2. Extract visible text and compare against the slide plan.
3. Render the PPTX to PDF/images.
4. Inspect full-slide images for collisions, clipping, low contrast, placeholder
   residue, over-wrapping, inconsistent alignment, cramped margins, and stale
   template objects.
5. Fix at the contract/renderer/XML level.
6. Re-render affected slides.

Qiaomu PPT should not report completion after a single export command. A
fix-and-verify pass is part of the delivery, especially after template edits,
PptxGenJS fallback generation, or any change that touches text geometry.

### 5. Relationship To Qiaomu SVG-First Route

The upstream PPTX skill is strong at direct PPTX operations. Qiaomu PPT's main
final-quality route remains source/content planning -> SVG-first page authoring
-> native DrawingML export -> preview QA.

Use the upstream method as:

- a template/old-deck editing playbook
- a native PPT object pitfall checklist
- a visual QA standard
- a fallback guide when SVG-first export is unavailable

Do not use it as:

- a runtime dependency
- a license to copy proprietary scripts or docs
- a reason to abandon source-grounded content planning
- a reason to downgrade polished HTML/SVG previews into crude editable redraws

## Qiaomu Implementation Hooks

- `pptx_text_check.py`: check visible text and detect image-backed fake
  editable decks.
- `pptx_preview.py`: render PPTX back to PDF/JPG thumbnails for visual review.
- `check_project.py`: require text check, preview evidence, preview-gate status,
  and no mostly image-backed normal PPTX.
- Future template route: add a Qiaomu-owned `pptx_template_intake.py` or extend
  `source_to_markdown.py` to write a layout inventory, placeholder inventory,
  and content-to-template mapping before editing.

