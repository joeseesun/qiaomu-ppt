---
name: qiaomu-ppt
description: |
  Independent Qiaomu PPT production skill for creating Chinese-first PPT, PowerPoint, PPTX, presentation, slide deck, brand launch deck, teaching courseware, URL-to-PPT, and speaker-ready decks. It routes requests, fetches URLs/PDFs/images into Markdown sources when needed, builds an audience or learning-state plan, chooses persuasive structure frameworks, improves content and copy through claim-title outlines, recommends a suitable design style from a local PPT style library when needed, locks a calm Qiaomu visual system, enforces a per-slide max-three active color budget, prefers generated bitmap background packs in Codex image-generation environments, rejects meaningless decorative lines, enforces visual-noise budget and image-slot containment, produces fixed-stage HTML previews or PPTX-oriented SVG artifacts, runs local artifact checks, and prefers editable PPTX delivery when an exporter is available. Use when the user asks to 做PPT, 生成PPT, URL做PPT, 根据链接做PPT, 优化PPT文案, 改PPT内容, 制作课件, 品牌发布PPT, 发布会deck, 演讲slides, PowerPoint, PPTX, 自动推荐PPT风格, or wants a Qiaomu workflow that combines practical editability, stronger content, aesthetics, speaker notes, and verification without relying on upstream skills at runtime.
version: 0.5.1
owner: 向阳乔木
---

# Qiaomu PPT

Create presentation work that can actually be used: first route the job, then shape the story, then lock the visual system, then produce checked artifacts. Default to an editable PPTX-oriented path when the user says PPT / PowerPoint / 课件 / 二次编辑, and use HTML-only routes only when the user explicitly wants a web deck, a fast visual preview, or an interactive presentation.

Copyright (c) 向阳乔木
X: https://x.com/vista8
GitHub: https://github.com/joeseesun/

## Router Rules

- Start by writing a short route card before generating slides:
  - `route`: `brand_release`, `high_school_courseware`, `business_report`, `talk_deck`, `pptx_beautify`, or `html_preview`.
  - `final_delivery`: `editable_pptx`, `html_deck`, `preview_then_pptx`, or `planning_only`.
  - `confidence`: high / medium / low.
  - `assumptions`: only the assumptions that affect output.
- If the user says PPT, PowerPoint, PPTX, 课件, 可编辑, 二次修改, 老师要改, or deliverable is unclear, default to `editable_pptx`.
- If the user says 网页 PPT, HTML, 横向翻页, WebGL, 先看风格, 快速预览, or does not need PowerPoint editing, route to `html_preview` or `preview_then_pptx`.
- Brand launch decks prioritize story tension, brand signal, first-slide impact, sparse copy, media decisions, and a polished visual thesis.
- High school courseware prioritizes learning objective, prerequisite check, concept ladder, examples, exercises, board-work rhythm, answer reveal plan, and teacher notes. Do not use a sparse keynote style for dense teaching unless the user asks for a public talk.
- If the user provides one or more URLs, route through the built-in URL ingestion step first. Save clean Markdown, images, and source metadata before writing slide claims.
- Do not call `ppt-master`, `baoyu-design`, `frontend-slides`, `guizang-ppt-skill`, or `humanize-ppt` as runtime dependencies. Their local clones are research evidence only.
- Do not copy upstream templates, long wording, bundled code, or exact style packs into generated artifacts. Use Qiaomu-owned route contracts, visual systems, artifact contracts, and checks.

See [references/routing-playbook.md](references/routing-playbook.md) for route details.
Read [references/independent-method.md](references/independent-method.md), [references/url-ingestion.md](references/url-ingestion.md), [references/content-copy-method.md](references/content-copy-method.md), [references/visual-systems.md](references/visual-systems.md), [references/codex-image-backgrounds.md](references/codex-image-backgrounds.md), [references/design-style-library.md](references/design-style-library.md), [references/ppt-visual-failure-patterns.md](references/ppt-visual-failure-patterns.md), and [references/svg-pptx-compatibility.md](references/svg-pptx-compatibility.md) before changing this skill's production strategy.

## Compact Workflow

1. Inspect the source material and goal.
   - Read user files, pasted notes, links, old decks, images, brand material, syllabus, textbook sections, and constraints.
   - If this is a fresh install, run `python3 <skill>/scripts/bootstrap.py --check` before relying on URL/PDF/PPTX conversion tools.
   - If URLs are present, run `python3 <skill>/scripts/url_to_markdown.py "<url>" --output-dir <project>/sources --download-images` before planning.
   - For PDFs, article pages, and image-rich pages, keep `source_manifest.json` and downloaded images as evidence inputs for the slide plan.
   - If the user supplied only a topic, do lightweight research only when requested or necessary, then cite sources in the work notes.
   - For high school courseware, identify subject, grade, textbook/module, teaching duration, and whether it is new lesson, review, exam explanation, or open class.
2. Create the route card and deck contract.
   - Output route, audience, desired audience state change, final format, page count range, density mode, and verification plan.
   - Write an audience-purpose card: audience, purpose, desired action, current state, desired state, stakes, density mode.
   - Choose the structure framework: `pyramid`, `SCQA`, `MECE`, `storyline`, `teaching_arc`, or a hybrid.
   - Ask at most 1-3 questions only when a wrong assumption would change route, cost, rights, or teaching correctness.
3. Build the narrative plan.
   - For talk/brand decks, use an audience-state-transfer arc: current state, tension, turning point, proof, desired state.
   - For courseware, use a learning-state-transfer arc: diagnosis, concept build, guided example, independent exercise, summary, homework/extension.
   - Write the slide titles first as a claim-title outline. A reader should understand the argument by reading only titles.
   - Produce a slide plan with per-page `claim_title`, `intent`, `content`, `visual_role`, `speaker_note_goal`, and `qa_risk`.
   - For decks longer than 8 slides, write `content_contract.json` with audience, purpose, desired action, structure framework, title policy, evidence policy, speaker-note policy, and per-slide claims.
4. Lock the visual system.
   - Create a style brief: visual thesis, palette, typography, layout rhythm, media policy, chart policy, and forbidden moves.
   - If the user did not specify a style, run `python3 <skill>/scripts/recommend_style.py --query "<brief>" --route "<route>" --top 5` and choose a style whose `avoid_for` does not conflict with the task.
   - Use `data/design_style_presets.json` as a PPT style library: extract the selected preset's palette, typography, slide patterns, media policy, chart policy, and animation hints into `style_brief.md` and `spec_lock.json`.
   - Define a `color_budget`: each slide may use at most 3 active non-image colors. Default to neutral base, readable text, and one accent. Do not use rainbow metrics, alternating cyan/green/yellow/red dots, or more than one accent family on the same page.
   - Define a `background_rhythm` with 4-6 roles for decks longer than 8 slides; no decorative background role may repeat more than 2 consecutive slides.
   - Define a `visual_noise_budget`: default `quiet`. Backgrounds should support the content, not compete with it. Avoid large saturated wedges, repeated neon rails, busy cards, ornamental grids, and decorative lines behind evidence.
   - Run `python3 <skill>/scripts/background_prompt_pack.py --subject "<deck subject>" --route "<route>" --count 5 --output <project>/assets/backgrounds/background_prompts.json` when image generation may be used.
   - In Codex environments where the built-in image generation tool is available, use the prompt pack to generate 3-5 quiet 16:9 text-free background bitmap assets before rendering. Use those as the background system instead of shape-based decoration. If image generation is unavailable, use neutral surfaces only; do not fake richness with decorative lines.
   - Define an `image_slot_contract`: every image/chart has a declared slot, fit mode, mask/crop method, padding, and `overflow_policy: clip_or_fail`.
   - Define `visible_provenance_policy`: default to no visible internal source/toolchain footer. Keep sources, fetch method, model name, QA evidence, and speaker cues in `qa_report.md`, speaker notes, or an optional final references page unless the user explicitly asks for visible citations.
   - For brand decks, generate or request 2-3 visual directions before full production when the brief is open-ended.
   - For courseware, prefer readable, classroom-safe design over decorative hero treatment.
5. Produce the deck through the selected route.
   - Editable PPTX route: create PPTX-oriented SVG pages under a Qiaomu spec lock and export only through tools available in the current project. If no editable PPTX exporter is configured, stop at checked SVG/HTML artifacts and mark PPTX export as `missing evidence`.
   - Preview route: create a fixed-stage single HTML preview owned by this project. Treat it as a style gate unless the user asked for HTML as the final output.
   - Hybrid route: approve visual direction in HTML, then translate the locked visual system into the editable PPTX path.
6. Run quality gates before calling the work done.
   - Narrative, copy quality, source coverage, visual consistency, overflow, readability, SVG/PPTX export, speaker notes, and route-specific gates must pass or be reported as missing evidence.
   - Check copy quality: one slide = one claim, title is a judgment not a label, visible copy stays within 3-5 chunks unless route is report-like or classroom-specific.
   - Thumbnail-scan the whole deck for background monotony and repeated layouts. If the deck reads as one repeated page, revise the background/layout roles before export.
   - Thumbnail-scan for visual noise. If backgrounds feel harder to read than the content, simplify surfaces before export.
   - Thumbnail-scan for color noise. If any slide reads as more than three active colors excluding source images, reduce to neutral base + text + one accent before export.
   - Reject decorative background lines unless they are functional chart axes, table rules, connectors, or part of a generated bitmap background. Lines that only add "tech feel" are defects.
   - Inspect every source-image/chart slide for fake rounded frames: a frame behind an image is not clipping. Use real crop/mask/compositing or a rectangular frame.
   - Inspect visible slide text for internal metadata such as `fetched via`, `generated with`, `qiaomu-markdown-proxy`, and `Speaker cue:`. These are QA artifacts, not presentation content.
   - Run `python3 <skill>/scripts/check_project.py <project_dir>` when a project folder has been produced.
   - Open the generated HTML or PPTX where possible. If direct PowerPoint/WPS verification is unavailable, say that explicitly.
7. Report completion evidence.
   - Include output paths, preview URL/file path, commands run, checks passed, checks unavailable, and known limitations.

## Route-Specific Rules

### Brand Release

- Strong default structure: hook, product/category tension, user pain, breakthrough, proof, product story, ecosystem/price/availability, closing line.
- Use fewer words and more deliberate visual hierarchy. One slide should have one dominant sentence or one dominant proof object.
- Preserve brand truth: use real product names, screenshots, logos, colors, and release facts only when verified or provided.
- Speaker notes should help the presenter sell the turn, not read slide copy aloud.
- Default final delivery remains editable PPTX unless the user asked for a web presentation.

### High School Courseware

- Start from teaching objective and student state, not visual style.
- Prefer a classroom sequence: lead-in, objective, prerequisite review, concept explanation, example, guided practice, independent practice, summary, homework/extension.
- Keep text readable from the back of a classroom; split dense content instead of shrinking it.
- Use diagrams, tables, and progressive reveal plans where they reduce cognitive load.
- Put teacher prompts, misconceptions, answer explanations, and board-work cues into speaker notes.
- Treat subject correctness as a hard gate. Pause if textbook edition, exam standard, formula, historical fact, or curriculum constraint is unclear and cannot be verified locally.

## Gate Ladder

Run these gates in order. Do not claim success before the relevant gates pass.

1. Route gate: route and final delivery match the user’s real need.
2. Source gate: every required claim, data point, image, brand asset, or textbook fact is either sourced, user-provided, or labeled as a draft assumption.
3. Narrative gate: every slide has a clear audience/learning state change.
4. Copy gate: every normal slide has a claim title, a visible proof focus, and concise supporting copy.
5. Visual gate: palette, typography, layout density, and media treatment are consistent; no generic purple-gradient default, no style soup.
6. Provenance gate: source/model/toolchain evidence exists in sidecar artifacts, but internal QA metadata is not printed on the slide canvas by default.
7. Readability gate: no text overflow, no overlap, no unreadable small type, no buried CJK punctuation issues obvious in preview.
8. Production gate: SVG/HTML/PPTX files exist in the declared output paths; export commands succeeded or are explicitly unavailable.
9. Speaker gate: speaker notes or teacher notes exist when the route requires them.
10. Verification gate: preview/open/export checks ran; missing apps, credentials, fonts, or PPTX exporters are marked as `missing evidence`.

See [references/quality-gates.md](references/quality-gates.md).

## Distilled Research

- `ppt-master`: serial editable PPTX pipeline, SVG compatibility discipline, spec lock, notes/export gates.
- `humanize-ppt`: state-transfer outline, per-page intent, media decisions, capped presentation checkup.
- `guizang-ppt-skill`: Chinese visual-system constraints, editorial/Swiss route families, layout and image-slot discipline.
- `frontend-slides`: fixed 16:9 stage, visual style discovery, density modes, anti-generic preview authenticity.
- `baoyu-design`: design context, browser preview, point-and-iterate loop, editable-vs-screenshot export distinction.
- `voltagent/awesome-design-md`: 74 public DESIGN.md style documents abstracted into local PPT presets and route-aware recommendation rules.

Read [references/upstream-research.md](references/upstream-research.md) for the research summary. Normal runs should use Qiaomu-owned rules, not upstream commands.

## Output Contract

For a normal deck run, produce or report:

- `deck_brief.md`: audience, goal, route, final delivery, assumptions, success criteria.
- `sources/source_manifest.json` when URLs, PDFs, or page images are ingested: source URL/path, fetch route, Markdown path, image paths, warnings, and missing evidence.
- `content_contract.json` or equivalent for decks longer than 8 slides: audience-purpose card, structure framework, title policy, evidence policy, and per-slide claim titles.
- `slide_plan.json` or equivalent structured plan.
- `style_recommendations.json` when style is unspecified or the user asks for automatic style selection.
- `style_brief.md`: visual thesis, tokens, layout rhythm, media policy.
- `layout_variation` or equivalent: per-slide layout/background roles and image slot contract.
- `visible_provenance_policy` or equivalent: whether sources/citations appear on slides, in notes, in a final references page, or only in QA.
- deck source files, such as SVG pages or HTML preview.
- exported `.pptx` when the route is editable PPTX and an exporter is available; otherwise checked SVG/HTML artifacts plus `missing evidence`.
- speaker notes / teacher notes when expected.
- `qa_report.md`: passed gates, failed gates, missing evidence, and next actions.

## Pause Conditions

Pause and ask the user before continuing if:

- required proprietary brand assets, copyrighted source files, paid APIs, credentials, or account actions are needed.
- the task requires factual claims about a product, law, medical/scientific fact, exam standard, or current event that cannot be verified from supplied sources.
- a user asks for pixel-perfect PPTX equality with a complex HTML/WebGL deck; explain that editable PPTX and web rendering have different tradeoffs.
- an editable PPTX exporter is unavailable but the user requires a real `.pptx`.
- three focused QA/fix rounds still leave narrative, readability, or export failures.
