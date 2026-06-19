# Independent Qiaomu PPT Method

`qiaomu-ppt` does not depend on `ppt-master`, `baoyu-design`, `frontend-slides`, `guizang-ppt-skill`, or `humanize-ppt` at runtime. Those projects were pulled locally and analyzed as research inputs. This skill internalizes the useful production ideas as Qiaomu rules.

## Core Thesis

The strongest practical route is:

```text
source material
  -> route card
  -> audience/learning-state plan
  -> style contract
  -> fixed-stage preview or SVG pages
  -> artifact checker
  -> editable PPTX export when a converter is available
  -> speaker/teacher notes and QA report
```

## Internal Roles

### 1. Router

Decides route and final delivery. It protects against the common error of using a beautiful HTML deck route when the user really needs editable PPTX.

### 2. Story Director

For brand/talk decks, every page turn must move the audience. For courseware, every page must move the learner. The director owns:

- audience or learner state
- central tension or learning obstacle
- title sequence
- page intent
- speaker or teacher note goal

### 3. Visual Director

Turns taste into a contract:

- visual thesis
- type scale
- palette
- layout rhythm
- density mode
- image/diagram rules
- forbidden style moves

If style is uncertain, it creates 2-3 cover or title-slide previews before full production.

### 4. Slide Composer

Creates either:

- fixed 1920 x 1080 HTML preview pages, or
- SVG pages in a PowerPoint-compatible subset.

The composer must re-read `style_brief.md` / `spec_lock.json` before each slide and keep every page tied to the slide plan.

### 5. Artifact Checker

Runs deterministic checks where possible:

- required artifacts exist
- slide plan fields are complete
- visible placeholders are gone
- SVG avoids known PowerPoint-breaking features
- HTML has no obvious deck placeholders
- output path claims match real files

### 6. Exporter

Exports only through tools available in the current environment. If no editable PPTX converter is configured, the skill must stop with SVG/HTML artifacts and mark PPTX export as `missing evidence`; it must not pretend to have produced a real `.pptx`.

## Non-Dependency Rule

Do not run upstream skill commands as part of `qiaomu-ppt` unless the user explicitly asks to compare or reproduce an upstream workflow. The normal route should work from Qiaomu-owned prompts, contracts, and checks.

## Page Artifact Contract

Every slide needs:

- `slide_no`
- `title`
- `intent`
- `state_before`
- `state_after`
- `visible_content`
- `visual_role`
- `media_need`
- `speaker_or_teacher_note`
- `qa_risk`

## Spec Lock

Create `spec_lock.json` when generating a deck. It should include:

```json
{
  "canvas": {"width": 1920, "height": 1080, "ratio": "16:9"},
  "route": "brand_release",
  "density": "speaker-led",
  "palette": {},
  "typography": {},
  "layout_rhythm": [],
  "image_policy": {},
  "svg_policy": {},
  "notes_policy": {}
}
```

Before authoring or editing each page, re-read this file and use it as the literal execution contract.
