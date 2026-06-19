# Routing Playbook

## Route Card

Write this before production:

```text
Route:
Final delivery:
Confidence:
Audience:
Use context:
Density:
Speaker/teacher notes:
Assumptions:
Verification plan:
```

## Brand Release

Use when the user says:

- 品牌发布, 新品发布, 发布会, 产品故事, pitch deck, keynote, launch deck
- wants emotional impact, strong first impression, product narrative, media assets

Default:

- `final_delivery`: `editable_pptx`
- `density`: low to medium
- `notes`: speaker notes for presenter rhythm
- `preview`: recommended when visual direction is open

Structure:

1. Hook or contradiction
2. Category/user pain
3. Product insight
4. Breakthrough
5. Proof or demo
6. Product/feature story
7. Ecosystem, availability, or business detail
8. Closing line

Copy method:

- Use `storyline` plus proof: current reality, tension, breakthrough, proof, future state.
- Titles should create momentum and contrast, not merely name features.
- Prefer memorable one-line claims over feature lists.
- Put product detail and nuance into speaker notes.

## High School Courseware

Use when the user says:

- 高中, 课件, 教学, 老师, 课堂, 例题, 复习, 讲题, 教案

Default:

- `final_delivery`: `editable_pptx`
- `density`: medium, classroom readable
- `notes`: teacher notes with prompts, misconceptions, answers
- `preview`: optional; do not let visual preview delay correctness

Structure:

1. Lead-in / diagnosis
2. Learning objectives
3. Prerequisite review
4. Concept build
5. Worked example
6. Guided practice
7. Independent exercise
8. Summary and homework/extension

Copy method:

- Use `teaching_arc`: diagnose, explain, demonstrate, practice, summarize.
- Titles should state what students will understand or be able to do.
- Keep repeated keywords stable; do not over-optimize for slogan-like copy.
- Teacher notes should include questions, expected answers, misconceptions, and timing.

## Business Report / Decision Deck

Use when:

- the user asks for 汇报, 经营分析, 复盘, board deck, management update, decision memo.

Default:

- `final_delivery`: `editable_pptx`
- `density`: medium, evidence-led
- `notes`: speaker notes with decision context and likely objections

Structure:

1. Executive summary
2. Decision or recommendation
3. KPI / situation evidence
4. Causes or drivers
5. Options and trade-offs
6. Risks and mitigations
7. Decision request
8. Appendix

Copy method:

- Use `pyramid` as the spine and `MECE` for support chapters.
- Put the answer first; do not make executives wait for the conclusion.
- Every data page title should say what the data means.

## Customer Proposal

Use when:

- the user asks for 客户提案, 解决方案, 售前, proposal, pitch to client.

Structure:

1. Customer situation
2. Complication / cost of inaction
3. Core question
4. Proposed answer
5. Solution modules
6. Proof or case
7. ROI / implementation path
8. Next step

Copy method:

- Use `SCQA` opening plus proof.
- Lead with the customer's problem and business outcome before product features.
- Keep jargon low; translate capability into business impact.

## HTML Preview

Use when:

- the user explicitly asks for HTML / web deck / horizontal swipe deck.
- visual direction is uncertain and a style gate saves rework.
- interaction or motion matters more than PowerPoint editing.

Do not use as final output when:

- the user asked for PPTX, editable PowerPoint, courseware collaboration, or handoff to teachers.

## PPTX Beautify

Use when:

- the user provides an existing PPTX and wants redesign or cleanup.

Rules:

- Extract or inspect original content first.
- Preserve facts and required text unless the user asks for rewriting.
- Rebuild layout and notes; do not promise to preserve all original animations.
