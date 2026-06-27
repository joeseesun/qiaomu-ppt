---
name: qiaomu-ppt
description: 乔木 PPT 生产技能和工作流路由器（qiaomu-ppt skill workflow），用于中文优先、资料有据的演示文稿策划、路线判断、可编辑 PowerPoint/PPTX 交付、语义化 HTML deck、PDF/URL/文章/论文/资料包转 PPT、品牌发布/产品发布 slide deck、课件、演讲备注、视觉资产规划、图片生成交接和导出验证。用户要求制作、生成、优化、转换、设计、研究、规划路线或验证 PPT/PPTX/PowerPoint/slides/slide deck/课件/演示文稿/幻灯片时使用，包括 URL/PDF/EPUB/Office/飞书/微信/arXiv/Hugging Face 输入、宽泛主题转 PPT、可编辑 PPTX、HTML PPT、Keynote、自动推荐设计风格/模板、PPT 内容/文案/标题/说服力优化。
license: AGPL-3.0-only
---

# Qiaomu PPT

制作真正可用的演示文稿。除非用户明确要求只要 HTML、只看风格预览或只要策划材料，否则默认走中文优先、资料有据、面向可编辑 PPTX 的生产流程。

Copyright (c) 向阳乔木
X: https://x.com/vista8
GitHub: https://github.com/joeseesun/
License: AGPL-3.0-only

## 核心契约

- 把 `SKILL.md` 当作入口路由器，而不是完整手册。只读取当前路线和风险真正需要的参考文件。
- 面向用户的说明、方案、问题和结论默认使用准确中文。英文只保留在文件名、脚本名、字段名、格式名、产品名或必须稳定匹配的机器状态中，例如 `route`、`final_delivery`、`research_dossier.md`、`design_proposal.md`、PPTX、HTML deck、`missing evidence`。
- 不要把用户项目、来源抓取、预览或导出文件写进 skill 目录。默认写到调用方工作区的 `outputs/<date>-<slug>/`、`~/Documents/Qiaomu PPT/<date>-<slug>/`，或用户明确指定的位置。
- 用户提到 PPT、PowerPoint、PPTX、课件、可编辑或二次修改时，默认交付可编辑 PPTX。整页图片式 PPTX 只能作为明确标注的等效预览、社交图片导出，或用户批准的不可编辑草稿。
- 在 Codex 或宿主生图可用时，推荐方案、预览和正式 PPT 默认必须使用生图作为整页或主区域主视觉。PPT/HTML 前景只承载可编辑标题、介绍文本、结论、短标签、讲解路径、必要标注、真实来源证据框和少量版面控件；不要用 SVG/形状手画人物、骨架、产品、场景、复杂图解或氛围画面作为主视觉，除非用户明确要求这种风格，或生图不可用并已标为降级。
- 使用生图不等于完成设计。媒体页必须把主视觉当作可读论证画布，声明文字安全区、焦点、裁切、标注目标和融合动作；不要把图片和一块大黑/白文字栏并排，当成默认的图文排版。
- 可见文案必须先从观众视角生成，而不是从制作方法、版式合同、图片资产说明或检查报告里摘取。把“观众会读到/听到的话”作为独立内容层，内部工作流只写入 sidecar、备注或 QA 报告。
- 不要把上游演示文稿 skill 当运行时依赖。上游研究只作为参考证据；实际执行使用本包的脚本、数据、参考文档和乔木自有契约。
- 不要把第三方模板、完整风格包、长提示词或受版权保护的页面设计复制进生成结果。
- 缺工具、缺凭证、缺来源权限、缺图片生成、缺 Office/Keynote/导出验证时，必须记录为缺失证据；机器状态仍使用 `missing evidence`，不要说成已经完成。

## 第一步

1. 能运行脚本时，先用 `python3 <skill>/scripts/plan_run.py --prompt "<用户请求>"` 生成路线卡、必读参考、主要脚本、确认边界和检查计划。不能运行脚本时，按本节手动判断。
2. 先判断请求类型，并在生成幻灯片前写一个简短路线卡。路线卡包含 `route`、`final_delivery`、`confidence`，以及会影响输出的关键假设。
3. 如果首条请求宽泛或信息不足，按 `data/ppt_guided_choice_flow.json` 和 [references/guided-choice-flow.md](references/guided-choice-flow.md) 给出紧凑选择卡。可以推荐默认值，不要强迫用户回答不必要的问题。
4. 用户在选择卡之后回复 `生成`、`默认`、`按默认` 或部分选项代码，只代表同意按默认值进入资料收集和规划阶段，不代表允许直接渲染最终 PPT。
5. 只有用户明确使用免确认生产措辞时，才能跳过确认，例如 `不用确认`、`无需确认`、`跳过方案`、`跳过资料确认`、`跳过预览`、`直接进入生成阶段`、`直接生成最终版`、`直接出完整 PPT`、`一口气生成` 或 `先出草稿不用等我`。把原话记录进项目。

## 确认门

- 对 PPT、deck 或较重的演示内容生产，先给用户一个可审阅的方案，再生成最终文件。方案应包括假设、推荐路线、交付格式、受众/使用场景、页数、故事线或逐页大纲、视觉方向、资料/搜索深度、已知风险和取舍。
- 方案给出后停下，等用户明确确认，再生成 PPTX、PDF、正式 HTML、图片资产或其他最终交付物。
- 简短主题、`ppt`、`介绍下`、`不用过多搜索` 等说法，不等于允许跳过确认。把它们理解为允许先出方案，而不是直接渲染整套 PPT。
- 不要把粗略想法、路线卡、道歉时顺手列出的简纲或不完整草案当成正式方案。可审阅方案必须包含路线卡、推荐判断、关键假设、完整逐页大纲或 storyboard、内容与资料来源计划、视觉方向、预览/审批计划、输出清单、风险和取舍。
- 可审阅方案中的视觉方向必须明确生图计划：哪些页用 Codex/宿主生图做整页或主区域主视觉，哪些页使用真实来源图，哪些可编辑前景文字/标注/讲解路径会叠加在图像之上。默认所有非来源证据的视觉页都先规划 Codex/宿主主视觉；SVG/形状只作为简洁前景控件或降级方案。缺少这部分时，不得进入预览或生产。
- 可审阅方案必须先定版式再定生图：逐页列出 `Lxx` 版式模式；有主要图片、截图、人物、产品、场景、证据图或生成图时，同时列出 `ITLxx` 图文模式、焦点位置、安全文字区、裁切策略和缩略图节奏角色。缺少逐页版式合同的方案，不得当作已确认的视觉方案。
- 进入正式逐页大纲前，运行或等价检查 `python3 <skill>/scripts/content_preflight.py <project> --profile plan`。内容任务书、研究问题树、证据卡矩阵、叙事主线、页面内核表或视觉翻译准备不足时，先补第一步，不要直接写大纲。
- 进入四页预览或最终生成前，运行或等价检查 `python3 <skill>/scripts/top_quality_plan.py <project> --profile plan|draft|final`。资料档案、故事大纲、页面文案、视觉系统和图片艺术指导任一项阻塞时，先补上游契约，不要直接靠渲染修质量。
- 需要预览时，用户确认方案只代表授权生成预览或草稿，不代表可以直接生成最终整套 PPT。最终生成仍需要用户看过预览后批准，或在看过方案后明确要求跳过预览。
- 用户在当前流程里看过方案后，回复 `确认`、`按这个做`、`生成`、`继续生成` 或同等明确批准，可以进入生产。

## 路线默认值

- `editable_pptx`：PPT、PowerPoint、PPTX、课件、教师交接、协作修改，或最终格式不清楚时的默认路线。
- `pptx_plus_semantic_html`：用户想要普通 PPT 加网页版本时使用；两种输出必须共享同一内容和视觉契约。
- `semantic_html_deck`：仅在用户明确要求网页/HTML、浏览器演示、互动 deck、WebGL 或强动效时使用。
- `html_preview` 或 `preview_then_pptx`：用于快速看视觉方向、风格关卡或“先看效果”；必须标注为预览。
- `planning_only`：用户只要大纲、方案、故事线、重设计计划、审计或页面文案时使用。

检查档位：

- `plan`：路线、来源缺口、方案和确认边界；默认不跑导出、预览、图片生成、原生软件或完整质量基准。
- `draft`：草稿/预览验证；只检查项目结构、文件存在、关键页预览或截图，不承诺最终质量。
- `final`：最终交付验证；才运行 PPTX/HTML 路线相关导出、预览、文本、语义、质量基准和修复计划。
- `release`：公开发布、客户交付或用户要求严验时使用；在 final 基础上追加交付包、敏感信息和明确要求的原生软件验证。需要强制严验时给 `plan_run.py` 加 `--validation-profile release`。

常见路线重点：

- 品牌发布：叙事张力、首屏冲击、品牌真实性、少字、真实产品/媒体证据。
- 高中课件：教学目标、概念阶梯、教室可读性、例题、练习、教师备注、学科正确性。
- 商业报告/演讲：来源支撑的判断、具体锚点、有说服力的结构、清楚的证明对象、可讲备注。
- 旧 PPTX 优化：先看缩略图和文本，保留有价值的版式，再进入修复和验证循环。

路线不明显时，读 [references/routing-playbook.md](references/routing-playbook.md)。

## 按需读取参考

不要一次读完所有参考。按场景读取：

- 机器可读路线表在 `data/route_reference_map.json`，检查策略在 `data/check_policy.json`。优先按 `scripts/plan_run.py` 输出读取参考、脚本和检查计划；只有路线不明、验证失败或用户要求更深解释时，再读更多参考。
- 第一步内容准备规则在 `data/content_preparation_contract.json`，执行 `scripts/content_preflight.py`。需要让资料更充分、大纲更精准、故事线更强或后续视觉更稳时，先看内容任务书、研究问题树、证据卡矩阵、页面内核表和视觉翻译准备。
- 顶级质量前置规则在 `data/top_quality_rubric.json`、`data/research_dossier_schema.json`、`data/story_outline_contract.json` 和 `data/image_art_direction_schema.json`。需要判断资料、大纲、文案、视觉系统或图片计划是否足够支撑高质量 PPT 时，运行 `scripts/top_quality_plan.py`，不要靠主观感觉放行。
- 宽泛主题、URL、PDF、Office、EPUB、文件夹、ZIP、图片、微信、飞书、arXiv 或 Hugging Face 输入：读 [references/source-intake-method.md](references/source-intake-method.md)、[references/topic-research-method.md](references/topic-research-method.md)、[references/url-ingestion.md](references/url-ingestion.md)，并按来源类型追加 [references/paper-source-intake.md](references/paper-source-intake.md) 或 [references/wechat-source-intake.md](references/wechat-source-intake.md)。
- 设计方案、执行锁定或多阶段生产：读 [references/model-driven-generation.md](references/model-driven-generation.md)、[references/production-contract.md](references/production-contract.md) 和 [references/ppt-design-generation-methodology.md](references/ppt-design-generation-methodology.md)。
- 版式、中文字体/间距、图文关系、图表、图解、组件、图标或视觉系统：读 [references/chinese-typography-layout.md](references/chinese-typography-layout.md)、[references/presentation-layout-principles.md](references/presentation-layout-principles.md)、[references/layout-pattern-library.md](references/layout-pattern-library.md)、[references/image-text-layout-patterns.md](references/image-text-layout-patterns.md)、[references/image-text-integration-contract.md](references/image-text-integration-contract.md)、[references/chart-diagram-components.md](references/chart-diagram-components.md)、[references/icon-assets.md](references/icon-assets.md) 和 [references/visual-systems.md](references/visual-systems.md)。
- 高设计要求、编辑风、`ppt-master` 级别、低质量返工或风格匹配：读 [references/ppt-master-grade-execution.md](references/ppt-master-grade-execution.md)、[references/ppt-master-research.md](references/ppt-master-research.md)、[references/design-style-library.md](references/design-style-library.md)、[references/visual-character-and-style-picker.md](references/visual-character-and-style-picker.md)、[references/ppt-anti-slop.md](references/ppt-anti-slop.md) 和 [references/ppt-visual-failure-patterns.md](references/ppt-visual-failure-patterns.md)。
- 生成图片、来源图片、背景、图片队列或媒体出处：读 [references/visual-asset-acquisition.md](references/visual-asset-acquisition.md)、[references/codex-image-backgrounds.md](references/codex-image-backgrounds.md)、[references/procedural-backgrounds.md](references/procedural-backgrounds.md) 和 `data/image_generation_providers.json`。
- 正式 HTML deck 或动效：读 [references/html-output.md](references/html-output.md)、[references/html-motion.md](references/html-motion.md) 和 `data/html_motion_presets.json`。
- PPTX 导出、SVG 兼容、Keynote 或旧 deck 修复：读 [references/svg-pptx-compatibility.md](references/svg-pptx-compatibility.md)、[references/pptx-skill-method-adaptation.md](references/pptx-skill-method-adaptation.md) 和 [references/quality-gates.md](references/quality-gates.md)。

## 运行依赖

- 不要在方案档或纯路线判断阶段默认运行依赖检查。只有新安装、环境未知、脚本报缺包、准备来源转换、PPTX/HTML 导出、图片生成或检查计划要求时，运行 `python3 <skill>/scripts/bootstrap.py --check`。
- 如果缺 Python 包，运行 `python3 <skill>/scripts/bootstrap.py --install-python`；需要隔离环境时使用 `--venv`，然后重跑 `--check`。
- 完整可编辑 PPTX 交付和 PPTX 预览验证需要 LibreOffice (`soffice`)。缺失时运行 `python3 <skill>/scripts/bootstrap.py --install-system`，然后重跑 `--check`。
- 只有需要 Poppler、ImageMagick、Node.js 或压缩包解压器等可选工具时，才使用 `--install-system --include-optional-system`。
- Keynote 导出是 macOS 可选能力。不要用 PPTX 或 LibreOffice 证据推断 Keynote 兼容性。需要 Keynote 证据时使用 `scripts/export_bundle.py`、`scripts/keynote_smoke.py` 或 `scripts/keynote_probe.py --with-control`。
- HTML 动效是可选增强层。GSAP、Lottie 和 dotLottie 只能作为打包的浏览器资产或明确声明的外部依赖使用，并写入 `html_motion_manifest.json`，再用 `validate_html_deck.py --motion-manifest` 验证。

## 生产流程

1. 收集上下文和来源材料。
   - 先选择项目目录。
   - 有来源输入时运行 `python3 <skill>/scripts/source_to_markdown.py <inputs...> --output-dir <project>/sources`。
   - 宽泛主题默认运行 `python3 <skill>/scripts/topic_research.py "<topic>" --output-dir <project>/sources --depth fast`，除非用户禁止网页或来源研究。
   - 正式大纲前先按 `data/content_preparation_contract.json` 准备或审计内容包：`content_contract.json`、`research_questions.json`、`sources/source_cards.json` 或 `evidence_matrix.json`、`page_kernel_map.json` 和视觉翻译准备；运行 `python3 <skill>/scripts/content_preflight.py <project> --profile plan`。
   - 幻灯片规划前按 `data/research_dossier_schema.json` 保存 Markdown 资料与研究档案，区分已验证事实、解释判断、来源覆盖、候选图片、权利说明、矛盾和缺口。机器文件可使用 `research_dossier.md`。
2. 创建演示文稿契约。
   - 普通主题/文件/链接准备优先使用 `python3 <skill>/scripts/create_deck.py --topic "<topic>" <inputs...> --project <project> --slides <n>`。
   - 只有方案获批或用户明确免确认时，才使用 `--produce`。
   - 方案必须方便用户审阅：页数、受众状态变化、故事线、来源摘要、风格候选、推荐方向、图片策略、版式组合、逐页计划、备注目标和质量风险。
   - `slide_plan.json` 按 `data/story_outline_contract.json` 从 `page_kernel_map.json` 扩展成叙事链：每页有主判断、证明对象、来源/具体锚点、观众变化、视觉角色、布局理由、阅读路径和 QA 风险。
   - 同时建立观众文案层：每页先写 `audience_takeaway`、`audience_question`、`visible_title`、`visible_body`、`visible_labels` 和 `speaker_notes_only`。只有 `visible_*` 字段允许进入幻灯片画布；`speaker_notes_only`、版式理由、制作方法、检查策略和资产说明必须留在备注或 sidecar。
3. 锁定叙事和视觉系统。
   - 按路线写入或检查 `deck_brief.md`、`design_proposal.md`、`content_contract.json`、`slide_plan.json`、`style_direction.json/md`、`spec_lock.md/json`、`visual_contract.json` 和 `visual_asset_manifest.json`。
   - 普通页面必须有判断式标题、具体锚点、证明对象、版式模式、阅读路径和质量风险。
   - 图文页面必须声明图文版式、安全文字区、裁切策略、前景角色和图文融合方式。
   - 图文页面的图片槽必须是比例受约束的媒体容器：声明 `slot_aspect_ratio`、`fit_policy`（`cover_crop`、`contain_letterbox` 或 `native_size`）、焦点位置和允许裁切边界。渲染时先把图片裁切/留白到槽比例，再插入 PPTX；不得用同时指定宽高的方式把不同比例图片强行拉伸进槽。
   - 图文页面还必须声明至少一个 `integration_move`：真实留白、局部渐隐/遮罩、图像作为标注画布、证据区域放大、边缘融合、引线标注、对象周边排布或对比构图。连续页面不得复用“左侧大文字栏 + 右侧图片”或同等黑/白半屏面板作为默认结构。
   - 图文页面必须声明 `text_surface_policy`：原图真实留白、烘焙渐变阅读底、局部编辑 matte、独立浅/深阅读区、证据图外侧说明区或讲者备注。正文、长 claim 和来源说明不得直接压在浅色纹理、复杂图像或高频细节上。
   - 背景默认不得使用网格线、引导线、稿纸线、施工线、装饰线叠层、tech lines、side rails 或抽象条纹。除非用户明确要求，线条只能作为图表轴/系列、表格线、连接线、流程/时间线/地图路径、焦点下划线、分隔线或真实形状边界，并在契约中说明语义目的。
   - 版式不是渲染后的微调。进入图片生成前，先从 `layout-pattern-library.md` 和 `image-text-layout-patterns.md` 选择逐页 `Lxx`/`ITLxx`，并把这些 ID 写入 `slide_plan.json`、`spec_lock`、`visual_contract.json` 和 `visual_asset_manifest.json` 的对应条目。
   - 高设计、编辑风或 `ppt-master` 级别项目还必须把组件选择理由写进 `slide_plan.json`、`design_spec.md` 或 `spec_lock`：每个图表、步骤、地图、表格、KPI、票档、日程、列表或卡片系统要说明为什么选它；有明显但错误的备选组件时记录 rejected reason。
   - 在 Codex/宿主生图可用且用户未禁止时，`visual_asset_manifest.json` 必须按 `data/image_art_direction_schema.json` 包含整页或主区域 Codex/宿主主视觉条目；每张图要有对应 `Lxx`/`ITLxx`、画面角色、焦点位置、构图、文字安全区、裁切策略、负面提示、可编辑前景边界和缩略图节奏角色。正文、标题、结论、标签、标注、来源说明和讲解路径不得烘焙进图像。只用 SVG、形状、渐变、程序化纹理或占位图的预览/正式稿必须标为降级方案，并向用户说明。
   - 计划 AI 图片时，最终质量项目必须有 `assets/images/image_prompts.json` 和 `assets/images/image_prompts.md` 或等价 sidecar；prompt 队列不能只存在聊天上下文里。对 presentation-ready、旁白或 Keynote 式交付，另需规划 `notes/total.md` 和 `animations.json`/`animation_manifest.json`，或在报告中标明静态降级。
   - 四页预览前运行 `python3 <skill>/scripts/top_quality_plan.py <project> --profile draft`；最终生成前运行 `--profile final`。未过线时先修资料、大纲、文案、视觉系统或图片艺术指导。
4. 普通 7 页以上 deck 先生成四页预览。
   - 四页预览应覆盖不同页面角色：封面/开场、密集证明页、图解/流程页、呼吸页/引用页/转折页。
   - 优先使用 `python3 <skill>/scripts/prepare_deck_project.py ... --generate-preview --preview-decision pending` 或 `python3 <skill>/scripts/four_slide_preview.py <project>`。
   - `preview_gate.json` 记录批准或用户明确跳过之前，不要进入完整生成。
5. 生成演示文稿。
   - 默认最终质量命令：`python3 <skill>/scripts/produce_deck.py <project> --quality-profile final --generate-images --enforce-quality-benchmark --fail-on-critical-repairs --benchmark-min-score 85`
   - 快速视觉草稿使用 `--quality-profile draft --image-limit 4 --formats pptx`，仍应包含真实关键图片。
   - `--no-generate-images` 只用于明确标注的离线或文本结构冒烟测试，不用于最终视觉质量。
   - 手工排障不得把默认路线改回 SVG/形状主视觉。SVG-first 只能用于验证版面、导出链路、前景可编辑控件或离线降级；一旦视觉质量进入评审，优先重新生成或替换 Codex/宿主主视觉，再叠加可编辑前景文本，并运行预览缩略图、PPTX 导出、文本检查、项目检查、质量基准和修复计划。
6. 完成前验证。
   - 运行或检查 `produce_deck.py` 生成的路线相关报告。
   - 检查 `top_quality_plan.py` 报告；如果总分或分项未达当前档位门槛，不要说已经达到顶级质量。
   - 按 `plan_run.py` 的 `check_plan` 执行当前档位检查；不要把 `defer_until_final` 或 `skip_by_default` 的项目提前跑成默认动作。
   - 生成了项目目录且检查计划要求时，运行 `python3 <skill>/scripts/check_project.py <project>`。
   - 生成最终 PPTX 后，必须运行 `python3 <skill>/scripts/pptx_text_check.py <pptx> --slide-plan <project>/slide_plan.json --output <project>/pptx_text_check.json`，并只在 `ok: true` 后交付。这个检查要早于最终回答，不应等用户指出标题、小字或强调框问题后再补跑。
   - 生成了 SVG/HTML/PPTX 预览缩略图或 SVG 中间层时，运行 `python3 <skill>/scripts/visual_rhythm_check.py <project> --output reports/visual-rhythm.json` 或等价检查；若报告指出连续重复结构、图片使用不足或节奏单调，先修版式合同和视觉 prompts，再进入最终导出。
   - 检查缩略图、手机截图或联系表时，把图文割裂当成硬缺陷：大块文字面板遮住主视觉、短标签像底部控件但没有指向目标、标题在窄栏里尴尬换行、来源/脚注小到不可读、文字跨过复杂亮区或连续页面结构指纹重复，都要先改 `Lxx`/`ITLxx`、融合动作或图片构图。
   - 预览通过后进入完整 PPTX 时，必须重新跑 PPTX 几何检查，而不能沿用 PNG/HTML 预览的肉眼判断。`pptx_text_check.py` 或 `layout_guard.py` 报告标题框过紧、标题与副标题/正文间距不足、强调 chip 过扁、强调条不是圆角矩形、或任意文本溢出时，先修 PPTX 再交付。
   - 检查手机截图或单页预览时，把低对比文字当成硬缺陷：彩色文字落在浅色/纹理图上、正文没有稳定阅读底、透明 PPT 形状在 LibreOffice/PowerPoint 渲染不一致、脚注比主视觉先丢失可读性，都要先修 `text_surface_policy`、字号、文字颜色或图片处理。
   - 能打开或预览 HTML/PPTX 时必须打开或预览。无法验证原生 Office、WPS、PowerPoint、Keynote、浏览器截图或图片生成时，说清具体缺口。

## 视觉与内容规则

- 普通页面应有一个主判断和一个主证明对象。教学页或报告页可以更密，但仍要有层级。
- 页面可见文字是给观众看的正式文案，不是给制作者看的项目说明。生成每个文本框前先问：观众是否需要在现场读到这句话？讲者是否会自然照着这句话说？如果答案是否定的，移动到讲者备注、`qa_report.md`、`design_spec.md`、`visual_contract.json` 或其他 sidecar。
- 强制三层分离：`visible audience copy` 只写观众要理解的判断、证据、行动和对象名称；`speaker notes` 写讲解顺序、转场、读图提示和讲者提醒；`production metadata` 写路线、版式、Lxx/ITLxx、素材、生成策略、质量门和导出状态。普通科普、商业、课件和报告 PPT 不得把后两层露在画布上。
- 不要把内部词汇露到画布上，例如 `deck`、`route`、`artifact`、`fallback`、`pipeline`、`source_fetch`、模型名、工具名、生成策略、质量备注或出处标签。中文也一样：`讲解顺序`、`版式`、`路线卡`、`交付`、`可编辑 PPTX`、`生成图`、`提示词`、`检查报告`、`图版`、`证据 01 / ...` 这类制作者标签默认不能出现在观众画面里，除非用户明确要做流程/方法类演示。
- 图片说明要从“资产说明”改写成“观众可理解的内容锚点”。例如不要写“复原图版：羽毛恐龙与现代鸟类的连续感”，改成“羽毛和前肢结构提示它们在同一条演化线上”；不要写“讲解顺序：化石图版 -> 特征组合”，改成讲者备注或直接删除。
- 页面角色、证据编号、章节名和风格名只有在它们本身能帮助观众定位内容时才可见。否则把“自然史图鉴 01”“证据 02 / 共享结构”改成面向观众的问题或判断，例如“鸟为什么属于恐龙？”“骨骼比外形更能说明亲缘关系”。
- 有来源图、用户图或网页图时，优先把它们作为证据使用；同时仍应使用生图提供场景、质感、复原示意或主视觉节奏。AI 生成图不能伪造截图、图表、表格、标志、来源文档、产品证据或用户未提供的前景物。
- 在 Codex 或宿主原生图片生成可用时，推荐生成的 PPT 默认必须先生成真实整页或主区域位图主视觉，再叠加可编辑标题、介绍文本、结论、标签、标注、图表、来源说明和少量版面形状。整页位图作为视觉层是允许的，但不得把可编辑文本和科学/商业结论烘焙进图像；`pptx_text_check.py` 应证明前景文字仍是原生对象且 `image_backed_ratio` 不构成伪可编辑整页截图。程序化资产、纯 SVG 线稿、几何形状和渐变只能作为离线 fallback、占位预览或前景可编辑解释层，除非用户明确接受它们作为视觉风格。
- 图片、截图、生成图和来源图不得非等比缩放。每个媒体对象进入 PPTX 前必须满足：`embedded_image_ratio` 与 `shape_slot_ratio` 基本一致，或明确使用 contain/letterbox；如果比例不一致，先重生图、扩图、裁切、加留白或调整槽位，不允许拉伸人物、产品、骨骼、场景、图表或截图。
- 不要把 Codex 图当作普通背景再随手贴文字框。生成图的构图必须服从已选 `Lxx`/`ITLxx`：焦点、留白、裁切、安全文字区、前景标注区和阅读路径都要在 prompt 里被指定。若缩略图看起来单调、图文割裂或只是重复左文右图，优先更换版式模式并重生/重组主视觉，而不是只挪动文本框。
- 图文融合优先使用图像中的真实留白、对象周边标注、局部渐隐、边缘裁切、放大细节和引线关系。大块半屏文字面板、底部标签排、重复黑栏和漂浮卡片只能在版式合同明确需要时使用；如果它们在缩略图里先于主视觉被看见，说明 chrome 抢戏，必须简化。
- 所有标注、标签、chip 和引线必须指向具体图像目标、比较对象或讲解路径；没有目标的标签排应改为标题副句、讲者备注或直接删除。手机预览中不可读的脚注、来源、标签和长词换行不是小问题，是导出前缺陷。
- 红色/蓝色/绿色等强调 chip、短标签和信息条必须是稳定的圆角矩形组件，不要做成压扁胶囊、贴纸、短高不足的色块或硬边矩形。强调条默认高度至少 `0.40in`（短词标签也不低于 `0.34in`），文字上下要有真实内边距；如果只是为了装饰，不要用强调色容器。
- 可读性优先于配色好看。长句、正文、解释性 claim 和路径文字默认使用高对比中性色；强调色只用于短词、短标签、线条或大号标题。若文字压在生成图或来源图上，必须先有稳定阅读底，再谈色彩风格。
- 中文标题和正文必须拉开层级：16:9 画布上标题到正文/证明对象默认至少留 `36-56px` 或 `0.55-0.80` 个标题行高；标题到副标题至少 `18-28px`；正文行高默认 `1.45-1.75`。如果缩略图里标题、正文、标签或媒体对象像粘在一起，必须先增大间距、重排换行或减少内容，不要靠线条、边框、阴影补救。
- 普通视觉型 deck 不应连续复用同一种结构指纹。除非是严格报告模板，4 页以上的视觉预览应包含明显不同的封面/证据/图解/呼吸页结构；7 页以上 deck 应在缩略图网格中体现 `anchor`、`dense`、`breathing` 节奏和多种 `Lxx`/`ITLxx` 组合。
- 拒绝常见 AI/网页设计指纹：默认紫色渐变、装饰球、卡片套卡片、假玻璃、装饰图标堆、假证据、嘈杂线条、默认页面控件、重复卡片栅格。
- 路线承诺可编辑 PPTX 时，前景标题、介绍文本、标签、图表、标注、讲解路径、引用和关键形状应尽量保持可编辑；复杂图像质感和主视觉质量交给 Codex/宿主生成图，而不是手画 SVG/形状。
- 正式 HTML deck 必须是语义化网页演示，不是整页截图。使用固定 16:9 舞台，默认键盘导航；除非用户明确要求，不要把可见上一页/下一页按钮或进度条放进幻灯片画布；使用本地优化资产并提供 `validate_html_deck.py` 证据。

## 质量门

按 `plan_run.py` 输出的检查档位和检查计划运行相关质量门。没有通过当前档位要求、或没有标明缺失证据前，不要声称该档位完成。

修改本技能的路由、确认边界、检查策略或指令遵循规则后，运行 `python3 <skill>/scripts/instruction_eval.py --cases <skill>/evals/instruction_cases.json --output <skill>/reports/instruction-eval.json --markdown <skill>/reports/instruction-eval.md`。

1. 信息收集门。
2. 路线和最终交付门。
3. 内容准备门：内容任务书、研究问题树、证据卡矩阵、叙事主线、页面内核表、视觉翻译准备。
4. 资料与研究档案门、来源证据门。
5. 主题/论文/微信/特定来源提取门。
6. 逐页计划确认门。
7. 面向专业/最终/高设计运行的内容大纲、元素计划、风格适配和 `ppt-master` 轴向审计。
8. 顶级质量前置门：内容准备包、资料档案、叙事大纲、页面文案、视觉系统、图片艺术指导。
9. 叙事、文案、具体性、版式多样性、缩略图节奏、字体层级和图文融合门。
10. 视觉资产获取、来源图片使用、生成图片出处、主要媒体证据和视觉资产状态门。
11. 反俗套、页面控件、形状组件、连接线、可读性、观众视角可见文案和可见文案出处门。
12. HTML、PPTX 可编辑性、PPTX 预览、PDF、Keynote、备注、生产、`export_manifest.json`、质量基准、修复计划和最终验证门。

详细规则见 [references/quality-gates.md](references/quality-gates.md)。如果质量基准或修复计划报告关键问题，先修契约、清单、来源、资产或渲染映射，再说达到最终质量。

## 输出证据

普通 deck 运行应按路线产出或报告以下相关子集：

- skill 目录外的项目目录。
- `deck_brief.md`、`research_dossier.md` 或足够完整的 `sources/source_notes.md`、`design_proposal.md`、`content_contract.json`、`slide_plan.json`、`style_direction.json/md`、`spec_lock.md/json` 和 `visual_contract.json`。
- 高质量第一步应包含 `content-preflight.json/md`，以及 `research_questions.json`、`evidence_matrix.json` 或 `sources/source_cards.json`、`page_kernel_map.json` 等内容准备包产物。
- 使用来源输入时的 `sources/source_manifest.json`、`sources/source_cards.json`、提取的来源图片或来源侧车文件。
- 使用视觉时的 `visual_asset_manifest.json`、图片提示/队列、生成或来源资产文件、出处说明。
- 高设计或 `ppt-master` 级别运行时的 `reports/ppt_master_axis_audit.json/md`，以及 AI 图片对应的 `assets/images/image_prompts.json/md`。
- 高质量运行时的 `top-quality-plan.json/md`，或等价的资料、叙事、文案、视觉系统和图片艺术指导评估。
- 用户请求的 SVG/HTML/PPTX/PDF/Keynote 导出；无法交付时，在 `export_manifest.json` 中明确记录缺失或失败。
- 需要现场讲述、旁白或演示动效时的 `notes/total.md`、per-page notes、`animations.json` 或 `animation_manifest.json`。
- PPTX 文本/可编辑性检查、预览或缩略图网格、HTML 验证报告、`qa_report.md`、质量基准报告、修复计划和已知缺口。

完整产物结构见 [references/production-contract.md](references/production-contract.md)。

## 暂停条件

遇到以下情况，先暂停并询问用户：

- 需要专有品牌资产、受版权保护的源文件、付费 API、凭证或账号操作。
- 任务需要产品、法律、医学/科学事实、考试标准或当前事件判断，但无法从用户提供的来源中验证。
- 用户要求复杂 HTML/WebGL deck 与可编辑 PPTX 像素级一致。说明可编辑 PPTX 和网页渲染的取舍。
- 可编辑 PPTX 导出器不可用，但用户要求真实 `.pptx`。
- 连续三轮聚焦修复后，叙事、可读性或导出问题仍未解决。
