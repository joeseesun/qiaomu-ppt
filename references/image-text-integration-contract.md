# Image Text Integration Contract

Use this contract whenever a slide contains a major image, screenshot, chart,
figure, document page, product render, portrait, before/after pair, or generated
atmosphere/concept image. The goal is not to place text near a picture. The goal
is to make image and copy share one readable argument.

## Required Fields

Record these fields in `slide_plan.json`, `visual_contract.json`,
`spec_lock.json`, `visual_asset_manifest.json`, or an equivalent project
contract before rendering media-rich slides:

- `image_text_pattern_id`: an `ITLxx` pattern from
  [image-text-layout-patterns.md](image-text-layout-patterns.md).
- `layout_pattern_id`: the proof-structure `Lxx` pattern that owns the slide.
- `image_role`: evidence, atmosphere, product, portrait, source screenshot,
  chart, figure, document page, comparison object, or concept metaphor.
- `text_safe_area`: protected title/body/proof/caption rectangles.
- `image_slot`: x/y/w/h, intended ratio, fit mode, crop policy, and clearance.
- `foreground_role`: what text or proof object explains the image.
- `integration_move`: the deliberate move that makes image and copy share one
  argument instead of sitting in adjacent rectangles.
- `annotation_targets`: the concrete image regions, objects, or evidence
  details that labels, chips, arrows, or callouts point to.
- `text_surface_policy`: the stable reading surface for every foreground text
  group: true image copy-space, baked gradient/scrim in the bitmap, local
  editable matte, separate light/dark proof zone, caption outside the image, or
  speaker-notes-only.
- `readability_floor`: the minimum phone/thumbnail review expectation for
  title, claim, body, label, and source text.
- `contrast_policy`: copy-space, scrim, matte, edge fade, blur, tint, or no
  overlay because image and text are separated.
- `image_finish_policy`: crop/mask/compositing, border, shadow, color
  normalization, corner radius, and padding behavior.
- `overflow_policy`: clip, fit, split slide, or fail. Do not allow accidental
  text/image overlap.

## Integration Moves

Pick at least one deliberate integration move for media-rich slides:

- use real copy space in the image
- add a local gradient scrim only where text sits
- crop/mask the image into a declared slot
- use an editorial matte or paper frame
- color-normalize the image to the deck palette
- use the image as a canvas for editable native annotations
- use leader lines or callouts that point to real image details
- zoom into the important evidence region while preserving source context
- arrange text around the subject instead of trapping it in a separate rail
- let the image edge fade into a local proof zone without covering the focal
  subject
- pair image and claim through a repeated shape, axis, or rhythm

Avoid placing a large opaque card over a full-bleed image as the default move.
That often makes the image decorative and the text cramped. Use it only when the
selected `ITLxx` pattern justifies a strong panel and the title/body/proof
clearance is verified.

## Text Surface And Contrast

Text over an image is allowed only when the text has a declared stable reading
surface. Do not rely on attractive palette contrast by eye. In particular,
amber, teal, red, blue, or other accent colors usually fail as body/claim text
on pale fossil, paper, sand, skin, product, UI, or textured backgrounds.

Default rules:

- title text may sit over image copy-space only when the local image area is
  calm and has strong light/dark separation
- long claim and body text need neutral high-contrast color on a quiet surface
- accent color is for short emphasis, labels, leader lines, or large display
  words, not paragraph reading
- source notes and footnotes should move to speaker notes unless they remain
  readable in phone/contact-sheet review
- if a renderer handles PPT transparency inconsistently, bake the gradient or
  scrim into the bitmap while keeping all text editable
- if a text group needs a heavy opaque block to become readable, reconsider the
  crop, prompt, `ITLxx`, or copy length before adding the block

## Panelized Image-Text Failure

Generated or source images must not be treated as a wallpaper beside a text
slab. A slide fails this contract when the thumbnail reads as two unrelated
rectangles: a large black/white explanation panel on one side and an image on
the other, especially when neighboring slides repeat the same structure.

Repair the layout contract before moving objects by hand:

- replace the half-slide text panel with real copy space, a local scrim, or
  title text placed in a calm image zone
- move labels near the image regions they explain, with leader lines or clear
  proximity
- enlarge or delete tiny chips that read as UI controls instead of information
- change the `ITLxx` pattern if the image focal point and text safe area fight
- regenerate or recrop the image when the focal subject leaves no stable text
  area

## Evidence Boundaries

Source/user/web images carry evidence. Do not crop them into vague atmosphere
when the audience needs to inspect the real object, page, figure, chart, or
screenshot.

Generated images carry atmosphere, concept, scenario, object study, texture, or
moodboard roles. They must not invent source-like foreground evidence such as
fake screenshots, album covers, product packages, documents, UI, labels, logos,
or chart data unless the user explicitly supplied or requested that object.

Low-resolution evidence should be displayed as an inspectable object at a safe
size, not stretched into a full-bleed hero image.

## Hard Failures

- title, body, proof, source note, or caption overlaps the image unintentionally
- text sits over a busy image without a declared contrast move
- source evidence is cropped so the important context is no longer inspectable
- a generated atmosphere image is treated as proof
- image slot uses arbitrary 50:50 split despite poor source aspect ratio fit
- media pages repeat the same opaque side panel or bottom label bar across a
  short deck without a deliberate series rationale
- chips, labels, or callouts float without concrete `annotation_targets`
- a title is forced into a narrow rail and wraps awkwardly while image space is
  underused
- small captions, source notes, or labels are unreadable in mobile or thumbnail
  review
- body, long claim, or path text sits directly on pale/complex image texture
  without a declared `text_surface_policy`
- accent-colored text is used for sentence-level reading on an unstable image
  background
- rounded frame is drawn behind an unmasked image instead of clipping the image
- image consumes the safe area needed by the title or proof object
- every image page repeats the same left/right template without rhythm

## Repair Moves

- reduce or split copy before shrinking type below the readability floor
- move long body text into a real reading zone or speaker notes
- switch sentence-level foreground text to high-contrast neutral color
- bake a soft gradient/scrim into the bitmap when native PPT transparency
  renders as a hard block or disappears
- move the image to a different `ITLxx` pattern
- shrink low-resolution evidence into an object study layout
- crop only after identifying the evidence region
- move detailed source inspection into a second slide
- replace generic atmosphere with a page-specific source/user/web/generated asset
- update `visual_asset_manifest.json` and `spec_lock.json` before rerendering

## QA

For formal output, verify:

- image slot and text safe area do not overlap
- source images preserve useful context
- title hierarchy remains dominant
- phone/thumbnail screenshots preserve readable hierarchy and do not collapse
  into repeated text-panel/image rectangles
- phone/thumbnail screenshots preserve readable text contrast: title, claim,
  body, and path text can be read without guessing; weak footnotes are hidden or
  moved to notes
- every visible label or chip has a target, or it has been converted into a
  takeaway sentence or speaker note
- local image file exists and matches the declared manifest row
- HTML images have `data-image-slot`
- PPTX foreground text remains editable where the route requires editable PPTX
- screenshots at deck review size show the image/text relationship clearly
