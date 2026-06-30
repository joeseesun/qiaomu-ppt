# NotebookLM Native Deck Route

Use this route only when the user explicitly asks for NotebookLM-native output,
NotebookLM search/research, or an image-backed/native PPTX that does not need
the normal Qiaomu editable foreground contract.

This route is built into qiaomu-ppt. Do not depend on
`qiaomu-anything-to-notebooklm` at runtime.

## Capability Boundary

This is a direct-source route. When a user explicitly wants NotebookLM-native
generation, pass the complete source file, URL, YouTube URL, or NotebookLM
research result directly to NotebookLM. Do not run the qiaomu editable-PPTX
source-card pipeline first. In particular, skip `source_cards.py`,
`outline_from_source_cards.py`, `content_preflight.py`, four-slide previews, and
source-adequacy gates unless the user switches back to the normal editable PPTX
route.

For private Feishu/Lark/wiki sources, first export or fetch the full document
into a single Markdown/TXT/PDF/DOCX file, then upload that file to NotebookLM.
Do not summarize the Feishu document into a handful of cards before upload.

NotebookLM currently supports:

- adding URLs, YouTube links, local files, and inline text as sources through
  the local `notebooklm` CLI
- Fast/Deep Research through `notebooklm source add-research`
- slide deck generation through `notebooklm generate slide-deck`
- slide deck download as PDF or PPTX through
  `notebooklm download slide-deck --format pdf|pptx`
- a free-form slide-deck description prompt plus structured controls:
  `--format detailed|presenter`, `--length default|short`, and `--language`

The output may be image-backed or only partially editable. It is not the default
Qiaomu editable-PPTX path.

## Main Command

```bash
python3 scripts/notebooklm_deck.py ~/Downloads/Qiaomu\ PPT/2026-06-29-topic \
  --title "Topic" \
  --input "https://example.com/article" \
  --search "topic search query" \
  --research-mode fast \
  --style-preset data_storytelling \
  --style "补充：用更强的结论标题和图表注释" \
  --format presenter \
  --length short \
  --language zh_Hans \
  --research-wait-timeout 180 \
  --artifact-wait-timeout 900 \
  --preview
```

Use `--research-mode deep` only when the user wants deeper NotebookLM web
research and can tolerate a slower run.

For a source-only run, omit `--search`. For a search-led run, omit `--input`.
For an existing notebook, use `--notebook-id`.

Local files must be uploaded as files. The wrapper uses `notebooklm source add
--type file` for existing local paths so NotebookLM receives the file content
instead of the path string.

## Waiting Strategy

Do not treat `notebooklm research wait` as the only completion signal. A
research task can remain `in_progress` after useful sources have already been
imported. The script therefore waits for research only up to
`--research-wait-timeout`, then records `notebooklm source list --json` as
`source_readiness` evidence and continues when there are enough ready sources.

Slide generation uses `notebooklm generate slide-deck --no-wait`, then waits
with `notebooklm artifact wait`. If artifact creation succeeds but a wait call
times out, the script still attempts PPTX/PDF download and records the state in
`notebooklm_generation_manifest.json`. If artifact-specific download fails, it
tries `--latest` once as a fallback.

## Style Prompt Injection

The user-facing style phrase must become a real slide-deck prompt, not only a
title suffix. Keep the NotebookLM prompt compact: one creative direction plus
one or two hard boundaries is usually better than a long visual rulebook.
NotebookLM is capable of composing the slide system; over-specifying layout,
colors, components, and negative rules can make it satisfy keywords page by
page and reduce style consistency.

The built-in style catalog lives at `data/notebooklm_style_prompts.json` and
contains exactly 20 practical NotebookLM slide-deck presets. List them with:

```bash
python3 scripts/notebooklm_deck.py --list-styles
```

Use `--style-preset <id>` for a known preset, such as
`executive_consulting`, `data_storytelling`, `editorial_magazine`,
`teaching_whiteboard`, `technical_blueprint`, or `social_card_deck`.
Natural-language `--style` still works and is matched against preset aliases
when possible; any extra `--style` text is treated as a short creative
direction, not a full production contract.

Examples:

- `--style-preset stick_figure_explainer` or `--style "火柴人风格PPT"` injects a whiteboard/stick-figure visual contract:
  black line characters, arrows, simple action scenes, sparse color accents,
  and one core action/relationship per slide.
- `--style-preset teaching_whiteboard` or `--style "手绘白板风"` injects a hand-drawn explainer contract with generous
  whitespace, low decoration density, and step-by-step diagram logic.
- Unknown style phrases are still passed as a visual contract and must affect
  layout, illustration language, color, type mood, and diagram method.

The prompt must also ask NotebookLM not to place tool names, generation process,
source IDs, or watermark/footer text on the slide canvas. This does not control
service-level watermarks; it only avoids prompt-induced visible clutter.

## Audience Copy Boundary

Treat every style preset, free-form style phrase, length/readability rule, and
tool-process instruction as internal generation direction. It must never become
visible slide copy. Do not allow wording such as `老师讲解`, `白板讲解风`,
`教学白板风`, `手绘极简少字版`, `创意方向`, `可读性要求`, `视觉要求`, or
`结构要求` to appear as a title, subtitle, label, section heading, or footer.

Visible slide text should come only from the source material: audience-facing
claims, concept names, evidence anchors, comparisons, questions, and action
conclusions. If a sentence describes how the deck should be generated or styled,
keep it in `notebooklm_slide_prompt.txt`, reports, or speaker notes, not on the
canvas.

Because NotebookLM-native PPTX is often image-backed, `pptx_text_check.py` may
not see text rasterized into slide images. Always inspect
`previews/notebooklm/thumbnail-grid.jpg` or equivalent slide thumbnails before
delivery and reject prompt leakage even when native PPTX text checks pass.

## Default Style Suggestions

When the user asks for a NotebookLM-native deck but does not clearly name a
visual style, stop at the proposal/choice stage and suggest 3-5 style options
before generation. Include one recommended default and 2-4 alternatives. Each
option must include:

- a short style label
- why it fits this topic/source type
- a one-line UI description prompt that can be passed through wrapper
  `--prompt` or as the native CLI `DESCRIPTION`

Prefer styles that improve comprehension without overwhelming the source
content. Good defaults by content type:

- complex concepts, education, workflows: `手绘白板图解风`, `火柴人分镜风`,
  `极简教学卡片风`
- culture, history, people, IP: `博物馆专题展览风`, `都市杂志插画风`,
  `动画设定集风`, `复古丝网电影海报风`
- science, nature, classification, worldbuilding: `自然图鉴风`,
  `科学实验笔记风`
- product, systems, technical breakdowns: `极简产品说明书风`,
  `专利图纸风`, `等距城市地图风`
- strategy, journeys, mechanisms: `桌游规则书风`, `路线图/旅行海报风`

Avoid defaulting to styles that tend to create dense panels, fake telemetry, or
decorative clutter, such as cyber HUDs, data dashboards, RPG skill screens,
arcade manuals, and dense consulting grids. Use them only when the user asks
for that flavor and accept that they may reduce readability.

Do not ask NotebookLM to copy a specific publication, studio, designer, or
living artist. Translate those references into visual language instead, e.g.
`都市杂志插画风` instead of a named magazine, or `复古丝网电影海报风` instead of
a named poster brand.

Example style suggestion prompt:

```text
视觉风格采用白板线稿和大留白；页面文字只写来源内容里的结论、概念名和短标签。每页只讲一个观点，用简单线稿、箭头和小场景解释关系，不要长段落和密集信息框。
```

For NotebookLM-native decks, default to `--format presenter --length short`.
This is the least wordy CLI combination and best matches live presentation
slides. Use `--format detailed` or `--length default` only when the user
explicitly wants a reading/standalone document, handout, or detailed lecture
notes. `--length short|default` is not a perfect per-slide readability control,
so the DESCRIPTION/prompt must still say: one conclusion per slide, 1-2 short
points or labels, details in speaker notes or omitted, no long paragraphs or
dense tables.

## Watermark Handling

NotebookLM account tiers may control official watermark removal. Prefer the
official account capability when available.

After downloading the PPTX, always run:

```bash
python3 scripts/strip_notebooklm_watermark.py \
  <project>/exports/raw/<slug>.notebooklm.raw.pptx \
  --output <project>/exports/<slug>.notebooklm.pptx \
  --report <project>/reports/notebooklm_watermark_cleanup.json \
  --remove-corner-logo \
  --inpaint-raster-watermark \
  --pdf-output <project>/exports/<slug>.notebooklm.pdf
```

The cleaner removes editable watermark text/shapes and small lower-right logo
objects first. With `--inpaint-raster-watermark`, it also attempts optional
OpenCV-based cleanup of NotebookLM watermarks baked into `ppt/media` images,
using a bottom-right ROI detection and patch-healing approach adapted from
`Albonire/notebooklm-watermark-remover` (MIT). If OpenCV is unavailable, no
watermark is detected, or a watermark is too different from the expected
NotebookLM mark, the report must say so instead of claiming a clean result.

For PDF delivery, prefer regenerating PDF from the cleaned PPTX with
LibreOffice. A raw NotebookLM PDF may still contain a service watermark and
should be labeled as raw if clean PDF regeneration fails.

## Required Evidence

NotebookLM-native projects must include:

- `notebooklm_slide_prompt.txt`
- `notebooklm_generation_manifest.json`
- `notebooklm_generation_report.md`
- `reports/notebooklm_watermark_cleanup.json`
- `pptx_text_check.json` with `allow_image_backed: true`
- `export_manifest.json` with `route: notebooklm_native_slide_deck`
- `export_manifest.json.formats.pptx.image_backed_ok: true`
- raw artifacts under `exports/raw/`
- cleaned public artifacts under `exports/`

When preview dependencies exist, also render:

- `pptx_preview_manifest.json`
- `previews/notebooklm/slide-*.jpg`
- `previews/notebooklm/thumbnail-grid.jpg`

## Verification

Run:

```bash
python3 scripts/check_project.py <project>
```

For this explicit route, `check_project.py` may warn about image-backed slides
but should not fail solely because the PPTX is mostly whole-slide raster images.
It should still fail missing files, invalid export manifest entries, stretched
images, forbidden visible production metadata, and missing watermark cleanup
reports.
