# Production Contract

Each normal run should create a project folder with these artifacts or explain why a route does not need them.

```text
<project>/
  deck_brief.md
  content_contract.json  # audience-purpose card, structure framework, title policy, slide claims
  slide_plan.json
  style_recommendations.json  # when style is unspecified or auto recommendation is requested
  style_brief.md
  spec_lock.json
  visual_contract.json  # background rhythm, layout roles, image slots
  visible_provenance_policy.json  # optional; required when citations are visible
  speaker_notes_plan.md
  sources/
    source_manifest.json  # when URLs/PDFs/images were ingested
    images/
  previews/
  svg_output/          # editable PPTX route
  html/                # preview or HTML final route
  exports/
  qa_report.md
```

## deck_brief.md

Required fields:

- title
- route
- final_delivery
- audience
- goal
- current_state
- desired_state
- density
- page_count
- source_inventory
- url_inventory
- assumptions
- verification_plan

## sources/source_manifest.json

Required when the task ingests URLs, PDFs, or page images.

Required shape:

```json
{
  "schema_version": "1.0.0",
  "sources": [
    {
      "input": "https://example.com/article",
      "title": "Article title",
      "source_type": "url",
      "fetch_route": "direct_html",
      "fetched_at": "2026-06-20T00:00:00+00:00",
      "markdown_path": "article-title.md",
      "pdf_path": "",
      "images": [],
      "warnings": [],
      "missing_evidence": []
    }
  ]
}
```

Hard rules:

- Slide claims must be traceable to a source record or marked as draft assumptions.
- `missing_evidence` must be carried into `qa_report.md`; do not hide failed extraction.
- Image records are candidate evidence only. They still need image slots before slide use.

## content_contract.json

Required when the deck has more than 8 slides, unless the route is only a short visual preview.

Required fields:

- `audience`
- `purpose`
- `desired_action`
- `current_state`
- `desired_state`
- `stakes`
- `structure_framework`: list using `pyramid`, `SCQA`, `MECE`, `storyline`, `teaching_arc`, or `hybrid`.
- `title_policy`: normally `claim_titles`.
- `copy_density`: expected visible copy density.
- `evidence_policy`: how claims connect to proof.
- `speaker_note_policy`: what notes must carry.
- `slide_claims`: per-slide `slide_no`, `claim_title`, `evidence_type`, and `spoken_role`.

Hard rules:

- The slide titles should read as an argument when scanned in order.
- Generic label titles such as `背景`, `现状`, `问题`, `方案`, `数据`, `总结`, `Overview`, and `Agenda` are not acceptable unless they include a specific claim.
- Mainline slides should carry one dominant claim. Put dense evidence, caveats, and secondary detail into notes or appendix.
- Visible support copy should normally stay within 3-5 chunks per slide, except classroom/report routes where density is intentional.

## slide_plan.json

Each slide item should include:

- `slide_no`
- `title` or `claim_title`
- `intent`
- `audience_or_learning_state_before`
- `audience_or_learning_state_after`
- `content_points`
- `visual_role`
- `media_need`
- `speaker_note_goal`
- `qa_risk`

## style_brief.md

Required fields:

- selected_preset_id, when a Design-MD preset is used
- visual thesis
- content thesis
- title policy
- copy density
- visual noise budget
- palette
- typography
- layout rhythm
- background rhythm
- layout role matrix
- image slot contract
- visible provenance policy
- density rules
- chart/table rules
- image rules
- animation policy
- forbidden moves

## spec_lock.json

This is the execution contract. Re-read it before authoring or revising each slide.

Required fields:

- canvas
- route
- final_delivery
- density
- content_contract
- selected_preset_id
- palette
- typography
- layout_rhythm
- background_rhythm
- visual_noise_budget
- layout_roles
- image_slot_contract
- image_policy
- visible_provenance_policy
- svg_policy
- notes_policy

The file should be literal enough that colors, fonts, spacing, image slots, and notes policy cannot drift during long deck production.

## visual_contract.json

Required when the deck has more than 8 slides or uses source images/charts.

Required fields:

- `background_roles`: list of reusable roles such as `hero_dark`, `evidence_dark`, `evidence_light`, `split_panel`, `diagram_focus`, `claim_card`.
- `slide_roles`: per-slide mapping of `slide_no`, `layout_role`, `background_role`, `dominant_object`.
- `visual_noise_budget`: normally `quiet`; use `moderate` only when justified by brand or route.
- `image_slots`: every source image/chart slot with `slot_id`, `slide_no`, `x`, `y`, `w`, `h`, `fit`, `mask`, `padding`, and `overflow_policy`.
- `max_consecutive_background_role`: normally `2`.
- `thumbnail_review_required`: `true` for PPTX decks.

Hard rules:

- No repeated decorative background role for more than 2 consecutive slides.
- Background decoration must stay subordinate to content. Avoid repeated hard rails, oversized saturated wedges, and multiple decorative systems on the same slide.
- Dense charts use `contain` unless a crop is explicitly justified.
- A rounded frame is not a clipping mask; if `mask` is `rounded_rect`, the renderer must actually clip or pre-compose the image.

## visible_provenance_policy

Default policy:

```json
{
  "visible_slide_provenance": "none",
  "content_source_location": "qa_report_or_notes",
  "generation_metadata_location": "generation_report",
  "allow_internal_toolchain_on_slide": false
}
```

Rules:

- Do not print fetch tools, model names, provider names, or QA status on the slide canvas by default.
- Do not show `Speaker cue:` on slides. Use speaker notes or `speaker_notes_plan.md`.
- Use visible citations only when the user asks, the route requires it, or the deck is an academic/report artifact. In that case, cite content sources only and keep generation metadata out of the slide.
- If a final references page is used, put it at the end; do not repeat production metadata as a footer on every page.

## qa_report.md

Required fields:

- route gate
- source gate
- narrative gate
- copy gate
- visual gate
- provenance gate
- readability gate
- production gate
- speaker gate
- verification gate
- missing evidence
- next actions

## Deterministic Check

When a style is unspecified, produce recommendations first:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/recommend_style.py --query "<brief>" --route "<route>" --top 5 --json
```

Save the result as `style_recommendations.json`, then write the selected preset into `style_brief.md` and `spec_lock.json`.

For decks longer than 8 slides or decks with source images/charts, create `visual_contract.json` before rendering. Use it as the check list during thumbnail review.

For decks longer than 8 slides, create `content_contract.json` before rendering. Use it to check audience fit, structure choice, title quality, evidence policy, and speaker notes.

When these artifacts exist, run:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/check_project.py <project_dir>
```

If the checker reports failures, fix them before claiming the deck is done. If it only reports warnings, either fix them or list them under `missing evidence` / known limitations.
