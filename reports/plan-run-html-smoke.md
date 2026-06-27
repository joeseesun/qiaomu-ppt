# 乔木 PPT 路线卡

- 路线：`html_deck`（HTML 演示）
- 最终交付：`semantic_html_deck`
- 置信度：`high`
- 允许生产：`false`
- 检查档位：`plan`（方案档）
- 暂停在：`design_proposal_confirmation`
- 下一步：先确认 HTML 是否为最终交付，是否需要 PPTX 静态伴随版，以及动效等级。

## 关键假设

- 未发现会改变路线的额外约束。

## 必读参考

- `references/html-output.md`
- `references/html-motion.md`
- `references/model-driven-generation.md`

## 主要脚本

- `scripts/create_deck.py --topic "<topic>" <inputs...> --project <project> --formats html`
- `scripts/validate_html_deck.py <project>/html/index.html --json <project>/reports/html_deck_validation.json --markdown <project>/reports/html_deck_validation.md`

## 必过质量门

- HTML 语义门
- 固定舞台门
- 动效降级门
- 浏览器截图门
- 最终验证门

## 现在要跑

- 路线卡与最终交付门
- 来源/事实缺口判断
- 确认边界门
- HTML 最终交付确认门
- 动效等级确认门

## 最终档再跑

- PPTX/HTML 导出验证
- 原生 Office/Keynote/WPS 验证
- 图片生成完整性验证
- 质量基准评分
- 浏览器截图
- validate_html_deck.py
- html_motion_manifest.json 检查

## 默认跳过

- bootstrap.py --check
- check_project.py <project>
- pptx_preview.py
- pptx_text_check.py
- validate_html_deck.py
- PPTX 可编辑性检查，除非用户要求静态伴随版
