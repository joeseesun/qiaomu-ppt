# Image-Text Layout Patterns

This reference captures 20 practical PPT image/text composition patterns as
`ITL01`-`ITL20`. Use it together with
`references/layout-pattern-library.md`: the `Lxx` library chooses the slide's
proof structure, while this `ITLxx` library chooses how text and images share
the canvas.

This is not an authoritative popularity ranking. It is a reusable production
library distilled from public template ecosystems, presentation design guidance,
web/editorial composition, magazine layouts, and consulting deck conventions.

## When To Use

Use this reference whenever a slide includes a major image, screenshot, product
render, source chart, person photo, quote portrait, before/after pair, timeline
node images, or data plus contextual media.

Do not use it as decoration. First decide the slide claim and proof object,
then pick the image/text pattern that makes the proof visible.

## Production Sequence

1. Write one slide conclusion.
2. Choose `proof_object`: image, screenshot, chart, quote, product, process, or
   comparison.
3. Choose `layout_pattern_id` from `layout-pattern-library.md`.
4. Choose `image_text_pattern_id` from this reference when media placement
   matters.
5. Write the media contract: `image_role`, `image_slot`, `fit`, `crop_policy`,
   `text_safe_area`, and `contrast_policy`.
6. Render only from the locked contract; do not drift by copying the last slide.

For normal generated decks, record the chosen pattern in both
`slide_plan.json.component_plan.image_text_pattern_id` and
`spec_lock.json.layout_execution_contract.slides[]`.

For image-rich decks, also record per-slide media policy in
`visual_contract.json.image_text_layout_plan`:

```json
{
  "slide_no": 3,
  "image_text_pattern_id": "ITL18",
  "layout_pattern_id": "L33",
  "image_role": "screenshot",
  "text_safe_area": "top title band plus right callout rail",
  "crop_policy": "crop away browser chrome; zoom local details if labels are unreadable",
  "contrast_policy": "no text directly over screenshot; callouts use opaque labels",
  "font_floor_pt": 18
}
```

## Global Rules

- PPT canvas: 16:9, PowerPoint Widescreen `13.333 x 7.5 in`.
- Safe margin: keep all live text inside `0.45-0.7 in`; images may bleed.
- Grid: 12 columns; common ratios are `5:7`, `6:6`, `4:8`, and `3:9`.
- Spacing rhythm: 8pt multiples, usually `8 / 16 / 24 / 32 / 48`.
- Text levels: title, body, label. Avoid more than three visible levels.
- One first focus per slide: large image, large number, or large title.
- Image role must be singular: background, evidence, emotion, product, person,
  or step.
- Projected decks should keep key visible text at 24pt or larger.
- Text over image needs real contrast: normal text `4.5:1`, large text `3:1`.
- Approved text-over-image methods: full scrim, gradient scrim, solid or
  translucent text block, copy space, and local blur.
- Run a squint test: the first thing visible must be the intended message.

## Pattern Groups

| Group | Patterns | Use For |
|---|---|---|
| Hero 大图组 | ITL03, ITL04, ITL05, ITL06, ITL11 | covers, chapter turns, emotional context, high-impact openings |
| Split 分屏组 | ITL01, ITL02, ITL08, ITL10 | stable business pages, explanation, conclusion-first evidence |
| Editorial 编辑组 | ITL09, ITL12, ITL15 | magazine-like cases, quotes, photo essays, moodboards |
| Product 产品组 | ITL17, ITL18, ITL19 | product breakdown, screenshots, feature demos, sales pages |
| Evidence 证据组 | ITL13, ITL14, ITL16, ITL20 | before/after, multi-scene proof, timelines, data insight |

## Selection Table

| Goal | Preferred Patterns |
|---|---|
| 稳妥商务汇报 | ITL01, ITL02, ITL07, ITL10 |
| 高级感封面 | ITL03, ITL04, ITL08, ITL11 |
| 产品介绍 | ITL01, ITL17, ITL18, ITL19 |
| 用户故事/案例 | ITL07, ITL09, ITL12, ITL18 |
| 对比表达 | ITL13 |
| 多场景展示 | ITL14, ITL15 |
| 流程/旅程 | ITL16 |
| 数据洞察 | ITL20 |
| 品牌/创意提案 | ITL04, ITL11, ITL15 |
| 教学/说明文档 | ITL09, ITL16, ITL18 |

## Pattern Index

| ID | Name | Structure | Best For | Lxx Mapping |
|---|---|---|---|---|
| ITL01 | 经典左右二分 | 45-50% text, 50-55% image | product/profile/explanation | L05, L03 |
| ITL02 | 非对称主图分屏 | 35-40% text, 60-65% image | brand story/trend/emotion | L05, L04 |
| ITL03 | 全屏大图 + 大标题 | full-bleed image, title in safe area | cover/chapter/opening | L04, L01 |
| ITL04 | 留白摄影 + 文本落位 | photo copy space plus text | premium brand/lifestyle | L04, L01 |
| ITL05 | 渐变遮罩图文叠加 | image with gradient scrim | complex image with text | L04 |
| ITL06 | 色块/高亮条压图 | image plus readable text bar | event/news/case cover | L04, L01 |
| ITL07 | 悬浮文字卡片 + 背景图 | background image plus one foreground card | case/value page | L04, L07 |
| ITL08 | 纵向侧栏 + 主图 | fixed 20-30% rail plus main image | sections/portfolio/report series | L07, L05 |
| ITL09 | 上图下文 | 55-65% image, 35-45% analysis | report/news/case/courseware | L03, L05 |
| ITL10 | 上标题下主图 | conclusion title above proof image | finding/evidence/report page | L03, L20 |
| ITL11 | 杂志封面式大字压图 | very large type over person/product | brand/consumer/event cover | L04, L01 |
| ITL12 | 金句/证言 + 人物图 | portrait or scene plus pull quote | customer/CEO/interview | L34, L05 |
| ITL13 | Before / After 对比 | matched before/after images | redesign/comparison/solution | L10, L21, L08 |
| ITL14 | 三图卡片 | three equal image cards | three features/scenes/results | L06, L22 |
| ITL15 | 多图拼贴 / Moodboard | collage with one dominant image | brand mood/scene/trend | L22, L04 |
| ITL16 | 时间线图文 | 3-5 timeline nodes with images | journey/history/process | L15, L13 |
| ITL17 | 中心物体 + 环绕标注 | central object with callouts | product/system/space explanation | L24, L33 |
| ITL18 | 截图 + 步骤注释 | large screenshot plus 3-5 annotations | SaaS/app/tutorial | L33, L07, L03 |
| ITL19 | 产品主图 + 参数/卖点栏 | product hero plus spec/benefit rail | launch/sales/solution | L02, L07, L03 |
| ITL20 | 数据/证据 + 情境图 | number/chart plus contextual image | business insight/research | L20, L19, L03 |

## Pattern Notes

### ITL01 Classic Split

Stable and automation-friendly. Use for product introductions, people, problem
explanations, and chapter body slides. Keep the text side to one title and up
to three bullets; crop the image full height without cutting the subject into
the edge.

### ITL02 Asymmetric Split

Use when the image is the protagonist. The text rail should carry a judgment
sentence and no more than 5-7 short lines.

### ITL03 Full-Bleed Hero

Use for covers, chapter turns, and emotional openings. Title should usually stay
under 12 Chinese characters or 8 English words. Add vignette, gradient, or local
scrim only where needed for readability.

### ITL04 Copy-Space Photography

Choose images with natural negative space. Place text in the quiet third and
avoid covering faces, hands, products, or source evidence.

### ITL05 Gradient Scrim

Use when the image is too complex but must carry text. The gradient should
spread from the text area outward; do not use thin type over the photo.

### ITL06 Text Bar Over Image

Use a text bar as a readability device. It should follow the copy width and use
24-40pt padding; avoid full-screen opaque slabs unless the art direction demands
it.

### ITL07 Floating Text Card

Good for customer cases, enterprise pages, and value statements. Keep one card,
30-45% of the canvas, with enough padding. Multiple floating cards often become
dashboard noise.

### ITL08 Sidebar + Main Image

Good as a master rhythm for reports or portfolio decks. Keep side rail width,
color, and placement consistent across related slides.

### ITL09 Editorial Caption

Image provides context; lower text provides analysis. Keep captions close to
the image. A two-column bottom zone can create a magazine feel for reading
decks.

### ITL10 Conclusion First

Use when the audience needs the answer before the evidence. The top title must
be a full judgment sentence, and the bottom proof object must remain readable.

### ITL11 Magazine Cover Type

Use only when the image and typeface have enough character. The oversized type
may overlap the visual field, but must not block the subject's face, product
core, or identifying detail.

### ITL12 Quote + Portrait

Use for interviews, customer testimony, CEO views, and user insight. Keep quotes
short; make the portrait gaze support the reading path when possible.

### ITL13 Before / After

The two images must share aspect ratio, label position, and crop logic. Declare
the contrast axis in the title or subtitle, then annotate only the differences
that matter.

When both images are source/user/web evidence, keep them on the same slide and
fit both with `meet` so the audience can inspect the original context. The
renderer should use two matched source panels, source captions, and an editable
takeaway band; it should not collapse the page to one source image plus bullets.

### ITL14 Three Image Cards

Use when there are genuinely three features, audiences, scenes, or results.
All images must share ratio, tone, and crop logic.

For source-backed decks, two available source images may still use the ITL13
comparison executor. Use three equal cards only when there are genuinely three
source visuals with matched role and relevance.

### ITL15 Moodboard

There must be one dominant image. Use collage to express a visual field or scene
family, not to fill space.

### ITL16 Image Timeline

Use 3-5 nodes. Split into multiple slides when the timeline has more than five
meaningful nodes.

### ITL17 Central Object Callouts

The center object should occupy 40-55% of the canvas. Leader lines must not
cross, and each callout should stay within two lines.

### ITL18 Screenshot Annotation

Crop away irrelevant UI chrome first. Use 3-5 annotations and local zoom boxes
when a complete screenshot would become unreadable.

For source/user/web screenshots and rendered PDF page images, keep the source
image/page inspectable with `meet` fitting. Put editable callouts outside the
dense source area where possible; leader lines should stop at the image boundary
or a deliberate local zoom box and must not cross body text.

### ITL19 Product Hero + Spec Rail

The product should occupy at least 45% of slide width. Keep specs/benefits to
four items and align the rail strictly.

### ITL20 Data + Context Image

Data is the protagonist; the image is supporting context. Chart labels should
stay at least 16-18pt in projected decks.

When the data visual is a source chart, paper figure, or PDF evidence page, use
the source visual itself as the wide primary canvas. Add a separate editable
takeaway band/panel for interpretation instead of redrawing a fake chart from
keywords.

## Failure Patterns

- Choosing a photo first and then inventing a claim.
- Using a beautiful image whose role is not evidence, emotion, product, person,
  background, or step.
- Putting text over an image without a contrast plan.
- Shrinking a screenshot or chart to make room for decorative cards.
- Treating every set of three bullets as ITL14.
- Using collage with no dominant image.
- Comparing before/after images with unrelated perspective, crop, or scale.
- Letting sidebars, cards, badges, arrows, and overlays all compete at once.
