# Content and Copy Method

This method distills Qiaomu's internal presentation research notes into Qiaomu-owned production rules. Use it to make decks sharper, more persuasive, and easier to present.

## Core Principle

Good PPT is not decoration. It is a communication system that aligns:

- audience task
- presentation purpose
- argument structure
- evidence
- visual hierarchy
- spoken delivery

The default order is:

```text
audience task
  -> one-sentence outcome
  -> structure framework
  -> title-first outline
  -> one-claim-per-slide plan
  -> evidence and chart choices
  -> speaker notes and rehearsal rhythm
```

Do not start by filling slides. Start by deciding what the audience should understand, feel, believe, or do differently.

## Audience and Purpose Fit

Write an audience-purpose card before the slide plan:

```json
{
  "audience": "executives | customers | colleagues | students | academic_committee | investors",
  "purpose": "persuade | report | teach | train | fundraise | decide",
  "desired_action": "the concrete decision, behavior, or learning outcome",
  "current_state": "what the audience currently knows/believes/can do",
  "desired_state": "what should change by the end",
  "stakes": "why this matters now",
  "density_mode": "speaker_led | report_like | classroom | appendix_heavy"
}
```

Route defaults:

| Audience | Care Most About | Better Structure | Copy Style |
|---|---|---|---|
| executives | conclusion, impact, risk, ask | pyramid + optional SCQA opening | action titles, numbers, decision words |
| customers | problem fit, credibility, ROI | SCQA + proof + implementation path | business value before feature detail |
| colleagues | context, ownership, next action | MECE + timeline/process | explicit owner, deadline, dependency |
| students | understanding, examples, practice | teaching arc + segmentation | simple concepts, repeated keywords |
| academic_committee | research question, method, evidence, limits | research narrative | precise claims and boundaries |
| investors | why now, traction, advantage, ask | storyline + growth proof | memorable one-liners, traction-first |

One deck cannot serve all audiences equally. If the audience changes, create a variant instead of making one universal deck.

## Structure Framework Selector

Use frameworks as composable tools:

- `pyramid`: use for executives, reports, board materials, and decision decks. State the answer first, then support it.
- `SCQA`: use for opening a proposal or diagnosing a problem. Situation, complication, question, answer.
- `MECE`: use for chaptering complex material. Make groups non-overlapping and collectively complete.
- `storyline`: use for brand, vision, launch, fundraising, and motivation. Move between current reality and possible future.
- `teaching_arc`: use for courseware and training. Diagnose, explain, demonstrate, practice, summarize.

Recommended hybrid:

```text
SCQA opening
  -> pyramid answer
  -> MECE support chapters
  -> evidence slides
  -> decisive ask / learning transfer / call to action
```

## Title-First Outline

Before designing pages, write all slide titles as a readable argument.

Rules:

- Each title should be a claim, not a label.
- A reader should understand the deck's argument by reading only the slide titles.
- Prefer verbs, stakes, contrast, causality, and audience value.
- Avoid generic labels: `背景`, `现状`, `问题`, `方案`, `数据`, `总结`, `Overview`, `Agenda`, unless paired with a specific claim.

Examples:

| Weak | Stronger |
|---|---|
| 市场背景 | 获客成本上升正在压缩下季度增长空间 |
| 产品能力 | GLM-5.2 把长上下文从参数卖点变成工程底座 |
| 数据分析 | 华东区增长主要由高客单用户拉动 |
| 解决方案 | 用内容获客和私域转化替代单一买量增长 |
| 总结 | 现在批准试点，能把风险控制在一个季度内 |

## One Slide, One Claim

Each slide needs one main claim and one job.

Slide fields:

```json
{
  "slide_no": 1,
  "claim_title": "one sentence the audience should remember",
  "audience_state_before": "what they think before this slide",
  "audience_state_after": "what this slide changes",
  "evidence_type": "data | example | diagram | quote | demo | exercise | decision",
  "spoken_role": "hook | explain | prove | transition | ask | practice",
  "copy_risk": "too vague | too dense | no evidence | no action"
}
```

Keep visible copy lean:

- 1 headline claim.
- 1 proof object or visual anchor.
- 3-5 supporting chunks at most.
- Put nuance, caveats, and transitions in speaker notes.

## Copywriting Ladder

Improve slide copy in this order:

1. **Task clarity**: What should the audience do or understand?
2. **Claim strength**: Is the title a judgment or merely a topic?
3. **Stakes**: Why does this matter now?
4. **Specificity**: Can vague nouns become numbers, actors, time, or contrast?
5. **Evidence**: Is the proof close to the claim?
6. **Brevity**: Can the sentence become tighter without losing meaning?
7. **Voice**: Does the wording sound like the route: executive, launch, teaching, academic, or investor?

Good slide copy is usually plain, specific, and consequential. It does not need inflated adjectives.

## Evidence and Chart Choice

Choose charts by data relationship, not by visual novelty:

| Data Job | Prefer | Avoid |
|---|---|---|
| comparison/ranking | bar chart, dot plot | pie chart, 3D chart |
| trend | line chart, small multiples | dual-axis chart by default |
| composition | stacked bar, 100% stacked bar | pie chart with many categories |
| distribution | histogram, box plot, dot plot | radar chart |
| correlation | scatter plot | bubble chart without clear scale |
| geography | map only when location matters | decorative map |

Rules:

- Use direct labels and callouts so the audience does not search between legend and chart.
- Dense tables belong in appendix unless the route is report-like.
- Mainline slides should explain what the data means, not merely show that data exists.
- Be skeptical of dual-axis charts. Use split charts or indexed trends when they reduce misread risk.

## Cognitive Load Rules

Use these as copy and layout constraints:

- Treat 3-5 chunks as the safe visible complexity range for most slides.
- Remove decorative images, redundant text, and animation that does not help understanding.
- Keep related labels close to the graphic they explain.
- Segment difficult ideas into chapter pages, transition pages, and recap pages.
- Do not repeat the spoken script on the slide. Let the slide cue attention; let notes carry nuance.

## Speaker Notes and Rehearsal

Speaker notes should include:

- slide purpose
- must-say facts or numbers
- transition sentence to the next slide
- likely question or objection
- timing target

Useful timing guidance:

- Write for blocks: information -> pause -> transition.
- For formal talks, avoid relying on "slides per minute"; rehearse the real deck.
- Most business decks should have backup pages for details and Q&A.

## Content Contract

For normal decks longer than 8 slides, create `content_contract.json` before production:

```json
{
  "audience": "executives",
  "purpose": "decide",
  "desired_action": "approve the pilot budget",
  "current_state": "uncertain whether the problem is urgent",
  "desired_state": "believes the pilot is timely and bounded",
  "stakes": "delay increases cost and narrows the window",
  "structure_framework": ["SCQA", "pyramid", "MECE"],
  "title_policy": "claim_titles",
  "copy_density": "3-5 chunks per slide",
  "evidence_policy": "claim-near-proof; dense details in appendix",
  "speaker_note_policy": "purpose, must-say facts, transition, likely objection, timing",
  "slide_claims": [
    {
      "slide_no": 1,
      "claim_title": "The decision window is open now, but it will not stay open",
      "evidence_type": "market signal",
      "spoken_role": "hook"
    }
  ]
}
```

If the deck is a short visual preview, create a compact version in `deck_brief.md` instead.
