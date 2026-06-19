# Qiaomu PPT

中文优先的 PPT 生成工作流：把主题、文档、URL、PDF、旧 deck 或课程材料，变成可编辑、可讲、可验证的演示文稿。

`qiaomu-ppt` 不是模板仓库，也不是把几个上游 skill 打包转卖。它把 PPT 创作拆成一条可复用的生产线：先抓取资料，再判断路线，再写有说服力的内容结构，再锁定安静、克制、可读的视觉系统，最后用质量门检查导出证据。

![Qiaomu PPT social preview](docs/assets/social-preview.png)

示例缩略图：

![GLM 5.2 deck thumbnail grid](docs/assets/glm52-deck-grid.jpg)

## 亮点

- URL / PDF 到 PPT：用户说“做一个 PPT：URL”时，内置 `scripts/url_to_markdown.py` 会抓取网页/PDF正文、发现图片、保存 `source_manifest.json`。
- 可编辑优先：默认面向 PowerPoint/PPTX，而不是只生成一张好看的网页截图。
- 内容先赢：用受众状态变化、claim title、证据策略和 speaker notes 组织材料，避免“资料搬运式 PPT”。
- 背景降噪：默认 `visual_noise_budget: quiet`，限制大色块、霓虹边栏、复杂装饰和图表背后噪声。
- 图片不出框：所有图片/图表都要有 image slot、fit、mask、padding 和 `overflow_policy: clip_or_fail`。
- 风格自动推荐：内置 74 个从 `awesome-design-md` 抽象出的 PPT 风格预设，可按场景推荐。
- 开源自包含：声明 Python 包、PDF/PPTX 转换工具、CJK 字体和降级策略，不依赖原始 upstream skill 运行。

## 安装

```bash
npx skills add joeseesun/qiaomu-ppt
```

本地开发或手动安装：

```bash
git clone https://github.com/joeseesun/qiaomu-ppt.git
cd qiaomu-ppt
python3 scripts/bootstrap.py --check
python3 scripts/bootstrap.py --install-python
python3 scripts/bootstrap.py --download-fonts
```

`--download-fonts` 会按 `data/font_manifest.json` 下载 Noto Sans CJK SC 到 `assets/fonts/`。字体文件默认不提交到仓库，避免包体积膨胀。

## 快速使用

把网页变成 PPT 资料源：

```bash
python3 scripts/url_to_markdown.py "https://example.com/article" \
  --output-dir demo/sources \
  --download-images \
  --max-images 12
```

自动推荐 PPT 风格：

```bash
python3 scripts/recommend_style.py \
  --query "AI 产品发布会，技术证据，黑底，少字，大屏演讲" \
  --route brand_release \
  --top 5
```

检查生成项目：

```bash
python3 scripts/check_project.py <project_dir>
```

## 你可以直接这样说

```text
做一个PPT：https://z.ai/blog/glm-5.2，保留关键图片和数据证据，最终导出可编辑 PPTX。
```

```text
把这份高中物理课做成 18 页课件，45 分钟，含例题、课堂练习和教师备注。
```

```text
帮我把这份老 PPT 的内容和文案改得更有说服力，标题要更吸引人，背景不要花。
```

## 工作流

1. 资料入口：读取用户材料；如果有 URL/PDF，先生成 Markdown、图片和 `source_manifest.json`。
2. 路线判断：品牌发布、课件、商务汇报、演讲 deck、旧 PPT 美化或 HTML 预览。
3. 内容契约：定义受众、目的、目标动作、当前状态、期望状态、stakes、结构框架和逐页主张。
4. 视觉契约：定义风格 thesis、字体、配色、背景节奏、视觉噪声预算、图片槽位和来源显示策略。
5. 生产导出：默认走可编辑 PPTX 路线；HTML 仅作为预览或用户明确要求的最终交付。
6. 质量门：检查来源、叙事、文案、视觉、图片溢出、内部元数据泄漏、备注和导出证据。

## 产物契约

一个完整项目通常应该包含：

- `deck_brief.md`
- `sources/source_manifest.json`
- `content_contract.json`
- `slide_plan.json`
- `style_recommendations.json`
- `style_brief.md`
- `visual_contract.json`
- `visible_provenance_policy.json`
- `exports/*.pptx` 或明确的 `missing evidence`
- `speaker_notes_plan.md`
- `qa_report.md`

## 视觉原则

默认不是“越炫越好”，而是让观众先读懂。`qiaomu-ppt` 会约束这些常见问题：

- 背景过度设计：大面积斜切色块、重复高饱和边栏、玻璃卡片堆叠、装饰元素压过证据。
- 布局单调：12 页看起来像同一页换文字，没有背景/密度/主视觉节奏。
- 图片假裁切：圆角底框在后面，图片本身没有被裁切，导致截图越出框。
- 内部元数据泄漏：`Source: ... fetched via ... generated with ...` 不应该默认出现在每页画布上。

长 deck 必须声明：

```json
{
  "visual_noise_budget": "quiet",
  "background_roles": ["hero_dark", "evidence_light", "split_panel", "diagram_focus"],
  "max_consecutive_background_role": 2
}
```

## URL / PDF 能力

`scripts/url_to_markdown.py` 支持：

- 普通文章 URL：直连抓取，必要时使用 Jina Reader fallback。
- 图片丰富页面：发现 `og:image`、`twitter:image` 和正文图片，可下载到 `sources/images/`。
- 远程 PDF：下载后用 `pdftotext` 或 `pypdf` 抽取文本。
- 本地 PDF：直接抽取为 Markdown。

它会记录：

```text
sources/
  article-title.md
  source_manifest.json
  images/
```

登录页、付费页、飞书私有文档、微信公众号反爬失败等情况不会假装成功，会写入 `missing_evidence`。

## 依赖

Python 包在 `requirements.txt` 中声明。外部工具在 `data/dependency_manifest.json` 中声明：

- LibreOffice / `soffice`：PPTX 转 PDF/图片预览。
- Poppler / `pdftotext` / `pdftoppm`：PDF 抽取和缩略图渲染。
- ImageMagick：可选图片优化和 contact sheet。
- Playwright Chromium：可选 JS 重页面抓取。

检查当前环境：

```bash
python3 scripts/bootstrap.py --check
```

如果缺少 LibreOffice、Poppler 或字体，skill 仍然可以运行部分流程，但必须把对应导出或排版验证标为 `missing evidence`。

## 验证

```bash
python3 /Users/joe/.agents/skills/qiaomu-meta-skill/scripts/validate_skill.py .
python3 /Users/joe/.agents/skills/qiaomu-meta-skill/scripts/trigger_eval.py . \
  --cases evals/trigger_cases.json \
  --output reports/trigger-eval.json
python3 scripts/url_to_markdown.py "https://example.com" --output-dir /tmp/qiaomu-ppt-url-test
python3 scripts/check_project.py /path/to/generated-project
```

## 边界

- 不内置、不调用 `ppt-master`、`baoyu-design`、`frontend-slides`、`guizang-ppt-skill` 或 `humanize-ppt` 的代码。
- 不依赖 `qiaomu-markdown-proxy` 运行；URL 能力已经内置为轻量脚本。
- 不承诺 HTML/WebGL 与 PPTX 像素级一致。默认优先可编辑。
- 不把抓取工具、模型名、QA 状态默认打印到每页 slide footer。
- 不授予第三方商标、专有字体、产品截图或页面布局的使用权。

## Troubleshooting

- 背景太花：检查 `visual_contract.json` 是否声明 `visual_noise_budget: quiet`，并删除大色块、霓虹边栏和多套装饰系统。
- 版式单调：给长 deck 至少 4 种背景/布局角色，缩略图网格里不应该像同一页换文字。
- 图片出框：检查 image slot，不要只放圆角底框；图片本身要真实裁切、mask 或预合成。
- URL 没图片：确认 `source_manifest.json` 的 `images` 字段；Jina fallback 会从 Markdown 图片链接里补图。
- 每页出现 `fetched via` 或 `generated with`：这是内部元数据泄漏，移到 `qa_report.md`、speaker notes 或最终资料页。
- 需要 PDF/PPTX 预览但失败：运行 `python3 scripts/bootstrap.py --check`，确认 Poppler/LibreOffice 是否可用。

## Credits

`qiaomu-ppt` 研究了 `ppt-master`、`baoyu-design`、`frontend-slides`、`guizang-ppt-skill`、`humanize-ppt` 和 `awesome-design-md` 的公开方法，也使用 `yaojingang/yao-meta-skill` 的元技能方法做本地校验，但运行时不复制或依赖这些项目的代码、模板和原始 skill。

## English

Qiaomu PPT is a Chinese-first presentation workflow skill for turning topics, URLs, PDFs, old decks, reports, and course materials into editable, speaker-ready, and verifiable slide decks.

It focuses on production discipline rather than decorative templates: URL/PDF ingestion, claim-title outlines, audience-state transfer, calm visual systems, image-slot containment, speaker notes, and local QA gates.

Install:

```bash
npx skills add joeseesun/qiaomu-ppt
```

Run dependency checks:

```bash
python3 scripts/bootstrap.py --check
```

Fetch a URL into deck sources:

```bash
python3 scripts/url_to_markdown.py "https://example.com/article" \
  --output-dir demo/sources \
  --download-images
```

Qiaomu PPT does not depend on upstream presentation skills at runtime. Inspiration from prior projects was distilled into Qiaomu-owned contracts, scripts, and QA rules.

## License

MIT

Copyright (c) 向阳乔木

X: https://x.com/vista8

GitHub: https://github.com/joeseesun/
