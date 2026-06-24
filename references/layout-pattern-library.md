# Layout Pattern Library

This reference turns common presentation layouts and design principles into ASCII patterns that an AI agent can read before planning or rendering slides. Use it during the `PPT Design Proposal` stage and again during slide generation.

For image-heavy slides, also use
[`image-text-layout-patterns.md`](image-text-layout-patterns.md). The `Lxx`
patterns here describe the proof structure; the `ITLxx` patterns there describe
how images, screenshots, products, quotes, comparisons, and text share the
canvas.

The purpose is not to copy template websites. The purpose is to select a layout as a thinking tool: decide what the slide must prove, then choose the structure that makes that proof visible.

## Research Basis

Use these external references as background context, not as templates to copy:

- Nielsen Norman Group: visual hierarchy is created through color/contrast, scale, and grouping/proximity; excessive equal-weight elements create visual clutter. Source: https://www.nngroup.com/articles/visual-hierarchy-ux-definition/
- Nielsen Norman Group: scale, hierarchy, balance, contrast, and Gestalt help layouts become understandable. Source: https://www.nngroup.com/articles/principles-visual-design/
- StrategyU: consulting layouts work because they separate the thinking question from the drawing task; process flows should usually stay to 4-5 steps, and executive summaries often compress Situation / Findings / Recommendation. Source: https://strategyu.co/slide-layouts/
- SlideModel: common slide types include title, picture, text, agenda, intro, summary, quote, chart/diagram, table, animation/video, CTA, and closing. Source: https://slidemodel.com/types-of-slides/
- Deckary: chart and diagram choice should follow the data relationship: comparison, trend, composition, distribution, relationship, process, architecture, or concept. Source: https://deckary.com/blog/pillar-diagrams-powerpoint-guide
- Microsoft PowerPoint guidance: reusable templates should show complete slide layouts with clear intent, including image usage, data visualization, charts, tables, timelines, diagrams, and infographics. Sources: https://support.microsoft.com/en-us/powerpoint/copilot/keep-your-presentation-on-brand-with-copilot and https://powerpoint.cloud.microsoft/create/en/blog/the-best-creative-presentation-ideas-topics-layouts-and-designs/

## Global Layout Rules

- One slide, one dominant claim.
- Pick the layout before drawing; the layout answers "what kind of proof is this?"
- The eye should know where to land first within one second.
- Use scale first, then weight, contrast, color, and grouping. Do not make every object equally loud.
- Limit normal slides to 3-5 visible content chunks.
- Use cards only when they clarify grouping or contrast; whitespace and alignment are often better.
- For decks longer than 8 slides, use at least 5 layout families.
- For slides with major images, screenshots, product renders, portraits,
  before/after pairs, timelines, or data plus contextual media, pair the `Lxx`
  proof pattern with an `ITLxx` image/text pattern.
- Do not count generic cards as diagrams. A diagram must explain a relationship, process, mechanism, boundary, or model.
- For AI image generation:
  - If generating a complete slide mockup, the ASCII layout may guide composition.
  - If generating an atmosphere/background image, do not bake boxes, text, charts, panels, or slots into the image. Layout remains editable foreground.

## Selection Matrix

| Slide Job | Prefer Layouts | Avoid |
|---|---|---|
| Hook / opening thesis | L01, L02, L04, L05 | agenda-first, dense bullets |
| Explain one concept | L03, L07, L18, L24, L28 | three generic cards |
| Compare alternatives | L08, L09, L10, L11, L12, L21 | unlabeled two columns |
| Show sequence or method | L13, L14, L15, L16, L17 | arrows between paragraph boxes |
| Prove with data | L19, L20, L22, L23, L25, L26 | decorative charts, chart too small |
| Explain causes | L27, L29, L30 | random icon rows |
| Handle objection | L31, L32 | hidden caveats in notes only |
| Summarize / decide | L06, L33, L34, L35 | vague "summary" bullets |
| Teach / classroom | L13, L18, L24, L36, L37 | sparse launch slide only |

## ASCII Conventions

```text
+-----+ = visible region / card / chart slot
T      = claim title
S      = subtitle / context
V      = visual, image, chart, or diagram
N      = number or metric
Q      = quote
A      = annotation / callout
```

## Core Patterns

### L01 Hero Claim

Use when the slide's job is to make one sentence memorable.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTTTTTTTTTTTTTT                      |
| SSSSSSSSSSS                                      |
|                                                  |
|                         optional visual texture  |
|                                                  |
| [proof chip]     [proof chip]     [proof chip]   |
+--------------------------------------------------+
```

- Best for: cover, chapter turn, central thesis.
- Slots: one large claim, one support line, 0-3 proof chips.
- Avoid: turning the cover into a dashboard.
- AI prompt hint: "one dominant typographic claim, wide whitespace, optional quiet atmospheric background."

### L02 Big Number / Big Object

Use when one number or object is the proof.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| SSSSSSSSSSS                                      |
|                                                  |
| NNNNNNNNNNN          short interpretation        |
| NNNNNNNNNNN          support 1                   |
|                      support 2                   |
+--------------------------------------------------+
```

- Best for: benchmark score, growth rate, time saved, cost delta.
- Slots: number, label, interpretation, 1-2 supports.
- Avoid: 4+ numbers competing for attention.

### L03 Claim + Proof Object

Use for a normal argument slide with one visual proof.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| SSSSSSSSSSS                                      |
|                                                  |
| claim/body zone          +---------------------+ |
| 1-3 concise lines        | V chart/image/model | |
|                          |                     | |
|                          +---------------------+ |
+--------------------------------------------------+
```

- Best for: source chart, screenshot, diagram, quote interpretation.
- Slots: claim, short body, proof object.
- Avoid: shrinking proof to make room for decorative cards.

### L04 Full-Bleed Image + Claim

Use when a real or generated image carries the emotional context.

```text
+--------------------------------------------------+
| VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV |
| V  TTTTTTTTTTTTTTT                              |
| V  SSSSSSSSSSS                                  |
| V                                                |
| V                                      chip      |
+--------------------------------------------------+
```

- Best for: brand/story chapter, scene-setting, product/place/person.
- Slots: full image, title over scrim, optional proof chip.
- Avoid: dark blurred stock-like images when the image should be inspectable.

### L05 Split Image / Text

Use when image and explanation must both be visible.

```text
+--------------------------------------------------+
| +----------------------+  TTTTTTTTTTTTTTT        |
| | V image / evidence   |  SSSSSSSSSSS            |
| |                      |                         |
| |                      |  bullet or takeaway     |
| |                      |  bullet or takeaway     |
| +----------------------+                         |
+--------------------------------------------------+
```

- Best for: product screenshots, article images, classroom examples.
- Slots: image left/right, claim, 2-3 takeaways.
- Avoid: fake rounded frame where image is not clipped.

### L06 Executive Summary / Three-Part Compression

Use when the slide must answer a senior-reader question fast.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +--------------+ +--------------+ +-------------+|
| | Situation    | | Finding      | | Action      ||
| | 3-5 lines    | | 3-5 lines    | | 3-5 lines   ||
| +--------------+ +--------------+ +-------------+|
| optional footer: decision / next step            |
+--------------------------------------------------+
```

- Best for: board/executive summary, recap, decision slide.
- Variants: Problem / Analysis / Recommendation; Context / Insight / Implication.
- Avoid: paragraphs in columns.

### L07 Sidebar + Main Proof

Use when one proof object needs a strong interpretive rail.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +------------+  +------------------------------+ |
| | takeaway   |  | VVVVVVVVVVVVVVVVVVVVVVVVVV  | |
| | number     |  | chart / diagram / evidence   | |
| | note 1     |  |                              | |
| | note 2     |  +------------------------------+ |
| +------------+                                    |
+--------------------------------------------------+
```

- Best for: chart-with-takeaway, screenshot with explanation.
- Avoid: right/left rail of generic bullets beside every chart.

### L08 Two-Column Comparison

Use when two alternatives must be compared directly.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +----------------------+ +----------------------+ |
| | Option A             | | Option B             | |
| | evidence             | | evidence             | |
| | implication          | | implication          | |
| +----------------------+ +----------------------+ |
|             one sentence contrast                |
+--------------------------------------------------+
```

- Best for: before/after, old/new, myth/reality, option A/B.
- Avoid: equal columns without a declared contrast axis.

### L09 Pros / Cons or For / Against

Use when the audience must weigh a tradeoff.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +----------------------+ +----------------------+ |
| | + supports           | | - risks              | |
| | + supports           | | - risks              | |
| | + supports           | | - risks              | |
| +----------------------+ +----------------------+ |
| decision rule / threshold                         |
+--------------------------------------------------+
```

- Best for: decision decks, policy tradeoffs, product strategy.
- Avoid: implying false balance when one side clearly wins.

### L10 Before / After Transformation

Use when the story is a change from current to desired state.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +-------------+     change lever      +---------+|
| | BEFORE      | --------------------> | AFTER   ||
| | pain/data   |                       | value   ||
| +-------------+                       +---------+|
| bottom: what changed / why it matters             |
+--------------------------------------------------+
```

- Best for: product launch, transformation, lesson outcome.
- Avoid: decorative arrows with symbols inside.

### L11 2x2 Matrix

Use when two dimensions define strategic zones.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|          high Y                                  |
| +-------------------+-------------------+        |
| | zone 1            | zone 2            |        |
| |                   |                   |        |
| +-------------------+-------------------+        |
| | zone 3            | zone 4            |        |
| |                   |                   |        |
| +-------------------+-------------------+        |
| low X                                 high X     |
+--------------------------------------------------+
```

- Best for: priority map, product/market fit, portfolio, risk/value.
- Avoid: axes without meaningful variables.

### L12 Quadrant Scatter

Use when items have two quantitative or ordinal scores.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|  high Y                                          |
|       * focus item                               |
|             *                                    |
|   *                                              |
|        ------------------------------            |
|   *                    *                         |
|  low X                                  high X   |
+--------------------------------------------------+
```

- Best for: portfolio analysis, opportunity map, competitors.
- Avoid: too many unlabeled points.

### L13 Process Flow

Use when the audience needs to know "how it works."

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +--------+ -> +--------+ -> +--------+ -> +-----+|
| | step 1 |    | step 2 |    | step 3 |    |step4||
| +--------+    +--------+    +--------+    +-----+|
|      timing / owner / output labels below         |
+--------------------------------------------------+
```

- Best for: method, workflow, teaching sequence, implementation.
- Keep to 4-5 steps; group longer processes into phases.
- Avoid: paragraphs inside each step.

### L14 Swimlane Process

Use when multiple actors or systems participate in a sequence.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| Actor A | [task] -----> [task]                   |
| Actor B |      [handoff] -----> [task]           |
| System  | [input] -----> [process] -----> [out]  |
+--------------------------------------------------+
```

- Best for: customer journey, service delivery, cross-team workflow.
- Avoid: more than 3 lanes on a mainline slide.

### L15 Timeline

Use when time order matters.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| 2024      2025       2026       2027             |
|  |---------|----------|----------|               |
| milestone milestone  milestone  target          |
| note       note       note       note            |
+--------------------------------------------------+
```

- Best for: history, roadmap, project plan.
- Avoid: using a timeline for unordered bullets.

### L16 Roadmap / Phases

Use when a sequence has phases, not exact dates.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +-----------+   +-----------+   +--------------+ |
| | Phase 1   |   | Phase 2   |   | Phase 3      | |
| | now       |   | build     |   | scale        | |
| +-----------+   +-----------+   +--------------+ |
| capabilities / deliverables under each phase      |
+--------------------------------------------------+
```

- Best for: strategy, rollout, curriculum units.
- Avoid: using equal phase widths when one phase dominates the work.

### L17 Gantt / Plan

Use when duration and overlap matter.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| Task A  |████████                               |
| Task B  |    █████████                          |
| Task C  |        ███████████                    |
|         Q1     Q2      Q3      Q4               |
+--------------------------------------------------+
```

- Best for: execution plan, project schedule.
- Avoid: using Gantt for conceptual story slides.

### L18 Mechanism Loop / Flywheel

Use when a concept reinforces itself.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|              +---------+                         |
|        ----> | step A  | ----                    |
|       /      +---------+     \                   |
| +---------+              +---------+             |
| | step C  | <----------- | step B  |             |
| +---------+              +---------+             |
| center: mechanism / compounding effect           |
+--------------------------------------------------+
```

- Best for: growth loops, learning loops, writing/revision loops.
- Avoid: calling any circular graphic a flywheel without reinforcement.

### L19 Full Chart

Use when the chart is the slide.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +----------------------------------------------+ |
| |                                              | |
| |                CHART                         | |
| |                                              | |
| +----------------------------------------------+ |
| direct annotation / source note in tiny text      |
+--------------------------------------------------+
```

- Best for: dense evidence, benchmark, trend.
- Chart owns 70-85% of slide.
- Avoid: decorative side cards.

### L20 Chart + Takeaway

Use when the audience needs one chart and one conclusion.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +------------------------------+ +-------------+ |
| | CHART                        | | takeaway    | |
| |                              | | N / claim   | |
| |                              | | support 1   | |
| +------------------------------+ +-------------+ |
+--------------------------------------------------+
```

- Best for: executive evidence slide.
- Avoid: three-bullet rail repeated across many slides.

### L21 Slope / Before-After Comparison Chart

Use for change between two moments or states.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| Before                         After             |
| A  o----------------------------o                |
| B     o---------------------o                    |
| C          o-------------o                       |
| direct labels and one highlighted series          |
+--------------------------------------------------+
```

- Best for: rank change, score movement, pre/post.
- Avoid: cluttered legends.

### L22 Small Multiples

Use when several similar charts should be compared by pattern.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +----------+ +----------+ +----------+           |
| | chart A  | | chart B  | | chart C  |           |
| +----------+ +----------+ +----------+           |
| +----------+ +----------+ +----------+           |
| | chart D  | | chart E  | | chart F  |           |
| +----------+ +----------+ +----------+           |
+--------------------------------------------------+
```

- Best for: regional trends, category comparisons, repeated measures.
- Avoid: different scales unless explicitly labeled.

### L23 Heatmap / Score Matrix

Use when a matrix pattern matters.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|        A   B   C   D                             |
| item1 [ ] [#] [#] [ ]                            |
| item2 [#] [#] [ ] [ ]                            |
| item3 [ ] [ ] [#] [#]                            |
| legend: low -> high                              |
+--------------------------------------------------+
```

- Best for: capability matrix, risk map, performance by segment.
- Avoid: using saturated rainbow scales.

### L24 Concept Map / Hub and Spoke

Use when one central idea connects to parts.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|           [part]                                 |
|             |                                    |
| [part] -- [CORE IDEA] -- [part]                  |
|             |                                    |
|           [part]                                 |
| implication line at bottom                       |
+--------------------------------------------------+
```

- Best for: framework, mental model, ecosystem.
- Avoid: 8+ spokes with long labels.

### L25 Funnel

Use when volume drops through stages.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +----------------------------------+  10,000     |
|   +----------------------------+      4,200      |
|      +--------------------+           900        |
|         +-------------+               210        |
| biggest drop annotation                         |
+--------------------------------------------------+
```

- Best for: conversion, hiring, sales pipeline.
- Avoid: funnels when widths are not proportional or when no dropoff exists.

### L26 Waterfall / Bridge

Use when the math moves from start to finish.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| start  +a   -b   +c   -d   end                  |
| ████   ██        ███        █████               |
|        |    ██        █                         |
| note: biggest lever                             |
+--------------------------------------------------+
```

- Best for: revenue bridge, cost variance, target gap.
- Avoid: using as a generic process.

### L27 Cause and Effect / Fishbone

Use for root cause analysis.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| cause A \                                        |
| cause B  \                                       |
| cause C ---=====> EFFECT                         |
| cause D  /                                       |
| cause E /                                        |
+--------------------------------------------------+
```

- Best for: diagnosis, quality, incident review.
- Avoid: too many tiny bones.

### L28 Pyramid / Hierarchy

Use when ideas have levels.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|                 [top claim]                      |
|              [support A] [support B]             |
|          [detail] [detail] [detail] [detail]     |
| bottom: implication                              |
+--------------------------------------------------+
```

- Best for: strategy hierarchy, Maslow-like levels, argument logic.
- Avoid: using pyramid only because it looks executive.

### L29 Iceberg

Use when visible symptoms hide deeper causes.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|          visible symptom                         |
| ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ waterline  |
|       hidden driver 1                            |
|       hidden driver 2                            |
|       hidden system condition                    |
+--------------------------------------------------+
```

- Best for: hidden assumptions, root cause, culture/process.
- Avoid: overused metaphor if no hidden layer exists.

### L30 Layered Stack

Use when one foundation supports another.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|        +----------------------+                  |
|        | outcome              |                  |
|      +--------------------------+                |
|      | capability               |                |
|    +------------------------------+              |
|    | foundation                   |              |
+--------------------------------------------------+
```

- Best for: architecture layers, capability maturity, learning ladder.
- Avoid: unclear layer dependencies.

### L31 Objection / Response

Use when handling a likely counterargument.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +----------------------+ +----------------------+ |
| | Objection            | | Response             | |
| | quote / concern      | | evidence / logic     | |
| +----------------------+ +----------------------+ |
| what this changes                                 |
+--------------------------------------------------+
```

- Best for: persuasive talks, FAQ, stakeholder concerns.
- Avoid: strawman objections.

### L32 Argument Tree

Use when a conclusion depends on several premises.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
|          conclusion                              |
|          /     |     \                           |
| premise A  premise B  premise C                 |
|   data       example     boundary                |
+--------------------------------------------------+
```

- Best for: logic-heavy essays, policy, strategy.
- Avoid: more than 3 top-level branches.

### L33 Annotated Screenshot / Evidence

Use when the source object must be inspected.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +-------------------------------------+          |
| | screenshot / source image           | A1       |
| |       [highlight region]            | A2       |
| |                                     | A3       |
| +-------------------------------------+          |
| one conclusion                                     |
+--------------------------------------------------+
```

- Best for: product UI, benchmark screenshot, document excerpt.
- Avoid: cropping away evidence needed to trust the point.

### L34 Quote + Interpretation

Use when the author's exact wording matters.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| "QQQQQQQQQQQQQQQQQQQQQQQQ"                      |
|                                    source/name   |
| +----------------------------------------------+ |
| | what this means / implication                 | |
| +----------------------------------------------+ |
+--------------------------------------------------+
```

- Best for: essay decks, teaching, thought leadership.
- Avoid: long quotes that become unreadable or copyright-risky.

### L35 Closing / Call to Action

Use when the deck must end with a clear next move.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| final claim / memorable sentence                 |
|                                                  |
| +--------------+ +--------------+ +-------------+|
| | next step 1  | | next step 2  | | next step 3 ||
| +--------------+ +--------------+ +-------------+|
+--------------------------------------------------+
```

- Best for: final recommendation, action plan, course summary.
- Avoid: generic "Thank You" as the only ending.

### L36 Teaching: Concept -> Example -> Practice

Use for classroom or training.

```text
+--------------------------------------------------+
| TTTTTTTTTTTTTTT                                  |
| +-------------+ +-------------+ +--------------+ |
| | concept     | | worked ex.  | | practice     | |
| | definition  | | steps       | | prompt       | |
| +-------------+ +-------------+ +--------------+ |
| teacher note / answer reveal plan                 |
+--------------------------------------------------+
```

- Best for: courseware, skill training.
- Avoid: keynote minimalism when students need scaffolding.

### L37 Knowledge Check / Quiz

Use when the audience should actively decide.

```text
+--------------------------------------------------+
| TTTTT question                                  |
| +-------------+ +-------------+ +--------------+ |
| | option A    | | option B    | | option C     | |
| +-------------+ +-------------+ +--------------+ |
| reveal zone: answer + explanation                |
+--------------------------------------------------+
```

- Best for: classroom, workshops, interactive talks.
- Avoid: hiding the explanation outside speaker notes.

## Layout Mixing Recipes

### Talk / Essay Deck

```text
L01 Hero -> L08 Tension -> L34 Quote -> L18 Mechanism ->
L11 Boundary -> L31 Objection -> L13 Method -> L35 Close
```

Use 2-4 diagrams: tension map, mechanism loop, boundary matrix, method flow.

### Business / Strategy Deck

```text
L06 Executive Summary -> L20 Chart+Takeaway -> L11 Matrix ->
L26 Waterfall -> L16 Roadmap -> L35 CTA
```

Use charts when data exists; avoid purely decorative diagrams.

### Product / Launch Deck

```text
L04 Image Hook -> L10 Before/After -> L03 Proof Object ->
L24 Ecosystem -> L15 Timeline/Roadmap -> L35 CTA
```

Use generated or real product imagery only when it supports the story.

### Courseware

```text
L01 Objective -> L36 Concept/Example/Practice -> L13 Process ->
L37 Quiz -> L36 Practice -> L35 Summary
```

Prioritize readability, examples, and teacher notes over visual novelty.

## Prompt Snippets for AI Layout Planning

Use these when asking an AI to plan or render a slide:

```text
Choose one layout pattern from layout-pattern-library.md.
State the slide job, dominant claim, proof object, and why this layout fits.
Do not use generic cards unless the pattern requires grouped options.
Keep max 3 active colors and 3-5 visible chunks.
If rendering a background only, do not include text, boxes, panels, chart slots, or UI.
```

```text
For this article slide, identify whether the source contains:
- tension pair
- mechanism loop
- boundary condition
- objection/answer
- analogy mapping
- process or method
Then choose L08, L18, L11, L31, L34, or L13 instead of default bullets.
```

## Anti-Patterns

- Same layout on 5+ consecutive slides.
- Three cards used as a substitute for thinking.
- Big title plus small unreadable evidence.
- Timeline for non-time content.
- Arrow chain for non-sequential ideas.
- 2x2 matrix with meaningless axes.
- Full-bleed generated image that hides the actual argument.
- Background that bakes in boxes, panels, or text.
- Repeated side rail or bottom mini-card row.
- Quote slide with no interpretation.
