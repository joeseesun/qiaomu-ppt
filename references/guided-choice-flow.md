# Guided Choice Flow

Qiaomu PPT should feel like a product, not a form. When the user says "我要做
PPT" or gives only a broad topic, guide them with a compact choice card. The
card should give the best default, let the user reply with short codes, and
allow "生成/默认" to proceed into research and planning, not final rendering.

## When To Use

Use a guided choice card when:

- the user gives a broad topic with no audience, page count, style, image/API
  policy, or delivery;
- the user asks to "做 PPT" or "生成 PPT" but has not provided a complete brief;
- the topic has several plausible angles;
- the user is in an exploratory creation flow;
- a wrong assumption would affect narrative, depth, length, or style, but the
  risk is not high enough to block execution.

Do not use it when:

- the user already gave explicit source, audience, page count, style, image/API
  policy, and delivery;
- the user gave a complete brief and an explicit strict approval-bypass phrase
  such as "不用确认", "跳过方案", "跳过资料确认", "直接进入生成阶段",
  "直接生成最终版", "一口气生成", or "先出草稿不用等我";
- a required factual, legal, medical, paid API, rights, or credential issue must
  be resolved first.

## User-Facing Card Shape

Keep the card short, but do not hide production-impact choices. Normal cards
should show up to 6 groups: 3-4 core content/design choices plus production
choices for image generation/API policy and output format. Image API provider
setup is an optional follow-up, not a mandatory group in the first card.

Example:

```text
我先给你一个默认方案，你可以直接回复「生成」，也可以用编号改：

1. 主题方向
   A. 大脑是旧系统，现代社会是新环境（推荐）
   B. 爱、嫉妒、合作、地位：人性的进化解释
   C. 进化心理学为什么有争议

2. 页数
   A. 8页精简
   B. 12页标准（推荐）
   C. 16页深入

3. 风格
   A. 清晰讲解（推荐）
   B. 演讲故事
   C. 研究报告

4. 配图/生图
   A. Codex 生图优先（推荐默认）
   B. 帮我配置生图 API
   C. 只用来源/图解
   D. 预览后决定

5. 生成格式
   A. PPTX + PDF + HTML（推荐）
   B. 只要 PPTX
   C. HTML 优先
   D. 加 Keynote
   E. NotebookLM 原生 PPTX/PDF（图片式，含水印清理证据）

默认执行：1A 2B 3A 4A 5A。你可以回「生成」，或回「1B 2C 3A 4B 5A」。
```

Rules:

- Mark exactly one recommended option per group.
- The recommended combination must be executable without more questions.
- Use plain labels, not internal style-family names.
- Avoid more than four options in one group.
- Do not ask for anything that can be safely inferred.
- Do ask for image-generation/API policy and output format when they are not
  specified, because they affect quality, cost, runtime, and deliverables.
- When Codex or another host-native image-generation route is available, make it
  the recommended image default and say so explicitly. Use a configured API only
  as the second route; procedural assets are preview/offline fallback.
- If the user chooses `帮我配置生图 API`, ask one optional follow-up:
  `A GPT-image/OpenAI`, `B Nanobanana`, `C Seedream/即梦`, `D 其他兼容 API`.
  If the user does not answer, default to GPT-image/OpenAI when an
  `OPENAI_API_KEY` style setup is available; otherwise proceed with prompts and
  placeholders rather than blocking.
- Do not ask the user to paste API keys into chat. Ask which provider route they
  want, then provide environment-variable or local provider-config setup steps.
- Treat GPT-image/OpenAI, Nanobanana, Seedream/即梦, Jimeng, and other compatible
  providers as selectable setup routes, not as hardcoded endpoints. Verify the
  endpoint, model name, and auth scheme before adding a reusable preset.
- If the user replies with only partial codes, keep defaults for the rest.

## Parsing Rule

Accept loose replies:

- `1A 2B 3C`
- `1.a 2b 3c`
- `1a,2b,3c`
- Chinese labels such as `标准页数` when obvious
- `生成`, `默认`, `按默认`

If an option code is invalid, ignore only that code and keep the default for
that group unless the invalid choice would change cost/rights/safety.

These short replies are valid only after the guided choice card has been shown.
They mean "use the recommended/default values and begin the research/proposal
workflow." They do not skip the later research-dossier, slide-plan, design
proposal, or preview confirmation gates. In the first user message, phrases
such as `生成一个 PPT`, `做个 PPT`, `直接生成`, `越快越好`, or a page count are
task requests, not approval bypass.

## Choice Contract

Record choices in the project as `choice_contract.json` or a section inside
`deck_brief.md` / `design_proposal.md`.

```json
{
  "choice_flow": "guided_choice_v1",
  "defaults_used": true,
  "user_reply": "1B 2C 3A",
  "selections": {
    "topic_direction": "case_attraction",
    "audience_depth": "ordinary_audience",
    "page_count": 12,
    "style": "knowledge_explainer",
    "image_generation": "codex_host_native_first",
    "image_api_provider": "not_required",
    "delivery": "editable_pptx_pdf_html"
  },
  "unanswered_groups_used_defaults": ["delivery"]
}
```

## Relationship To Design Proposal

The guided choice card is not a replacement for the design proposal. It is the
friendly entry into it.

- Guided choice selects direction, depth, length, style, image-generation/API
  policy, and delivery defaults.
- After the guided choice reply, the next production artifacts are a
  source-grounded Markdown research dossier and a source-synthesis article
  (`content_report.md` or `内容母稿-<主题>.md`) built from supplied material,
  model knowledge, and web/source research when allowed.
- Design proposal turns those choices into story arc, style candidates,
  visual-character picker, page-by-page slide plan, layout mix, image plan,
  anti-slop plan, and deliverables.
- If the user says `生成` after the choice card, proceed with defaults into the
  research dossier and design proposal. Proceed into rendering only when they
  explicitly asked to skip approval with the strict bypass language above.

## Defaults Are Product Decisions

Every broad-topic deck should have a strong default. Do not say "都可以，你想选
哪个". Recommend the best default from the topic and audience, then make it easy
to override.

For example, "进化心理学" defaults to:

- topic direction: "大脑是旧系统，现代社会是新环境";
- audience depth: ordinary audience;
- page count: 12;
- style: clear explainer;
- image generation: use Codex/host-native image generation by default when
  available for cover/section/concept/quiet-background visuals, while keeping
  evidence images source-backed; in non-Codex environments, use a configured API
  as the second route or optionally ask whether to configure GPT-image,
  Nanobanana, Seedream/即梦, Jimeng, or another compatible API;
- delivery: editable PPTX + PDF + semantic HTML.

This is better than asking the user to design the workflow.
