# 乔木 PPT 路线卡

- 路线：`broad_topic_ppt`（宽泛主题做 PPT）
- 最终交付：`editable_pptx`
- 置信度：`medium`
- 允许生产：`true`
- 检查档位：`release`（发布档）
- 暂停在：`none`
- 下一步：按已确认或免确认的路线执行生产流程，并记录验证证据。

## 关键假设

- 检测到免确认措辞：不用确认。

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

- final 档全部检查
- 公开交付包完整性检查
- 敏感路径/凭证泄露检查
- 用户明确要求的原生软件验证
- PPTX 预览缩略图
- PPTX 文本/可编辑性检查
- 用户明确要求的原生 Office/WPS/Keynote 验证

## 默认跳过

- 与用户交付格式无关的旁路导出
- HTML 动效验证，除非同时交付 HTML deck
