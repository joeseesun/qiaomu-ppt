# 乔木 PPT 路线卡

- 路线：`broad_topic_ppt`（宽泛主题做 PPT）
- 最终交付：`editable_pptx`
- 置信度：`high`
- 允许生产：`false`
- 检查档位：`plan`（方案档）
- 暂停在：`guided_choice_or_design_proposal`
- 下一步：先给路线卡和选择卡；用户接受默认后，再做主题研究、资料与研究档案和方案。

## 关键假设

- 未发现会改变路线的额外约束。

## 必读参考

- `references/guided-choice-flow.md`
- `references/topic-research-method.md`
- `references/model-driven-generation.md`

## 主要脚本

- `scripts/topic_research.py "<topic>" --output-dir <project>/sources --depth fast`
- `scripts/create_deck.py --topic "<topic>" --project <project> --slides <n>`

## 必过质量门

- 信息收集门
- 主题研究门
- 逐页计划确认门
- 四页预览门
- 最终验证门

## 现在要跑

- 路线卡与最终交付门
- 来源/事实缺口判断
- 确认边界门
- content_preflight.py <project> --profile plan（进入正式大纲前）
- top_quality_plan.py <project> --profile plan（已有资料/大纲/视觉计划时）
- 选择卡或默认路线门

## 最终档再跑

- PPTX/HTML 导出验证
- 原生 Office/Keynote/WPS 验证
- 图片生成完整性验证
- 质量基准评分
- PPTX 可编辑性检查
- PPTX 预览缩略图
- LibreOffice 导出证据

## 默认跳过

- bootstrap.py --check
- check_project.py <project>
- pptx_preview.py
- pptx_text_check.py
- validate_html_deck.py
- HTML 动效验证，除非同时交付 HTML deck
