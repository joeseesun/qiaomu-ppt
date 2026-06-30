# PPT Aesthetic Quality Framework

Use this framework when the user wants a PPT, slide deck, lesson, report, talk,
or public deck and has not specified a visual direction. The goal is not to
pick a pretty style. The goal is to make the deck look inevitable for its
subject.

## Core Principle

A beautiful PPT is content-fit beauty:

- the style matches the topic, audience, venue, evidence, and desired action
- the page has one clear visual idea, not a pile of components
- image, title, proof object, and labels form one argument
- typography feels intentional and readable in thumbnail and presentation view
- the deck has rhythm: anchor pages, dense proof pages, breathing pages, and
  closing pages do not all share one template
- every decorative decision has a job, or it is removed

Do not reuse the previous task's style failure as a universal rule. Each deck
needs a fresh aesthetic decision.

## Default Aesthetic Decision

Before style prompts, renderer work, or image generation, write this decision
into `design_proposal.md`, `style_direction.json/md`, or an equivalent sidecar:

```json
{
  "aesthetic_goal": "what the audience should feel and trust after 5 seconds",
  "content_domain": "business strategy / culture / education / technical / product / research / ...",
  "audience_and_venue": "who reads it and where it will be shown",
  "evidence_media": "source screenshots, charts, generated scenes, portraits, artifacts, diagrams",
  "visual_temperature": "calm / premium / rigorous / energetic / playful / cinematic / documentary",
  "primary_visual_family": "one main visual family",
  "counterpoint_family": "optional, only if it owns a specific role",
  "rhythm_strategy": "anchor / dense / breathing / diagram / closing page mix",
  "image_content_binding_policy": "how images will prove or sharpen page claims",
  "avoid_style": "one concrete style direction that would harm this deck",
  "avoid_reason": "why it would harm credibility, clarity, or emotion"
}
```

If this decision cannot be written without vague words like "高级", "科技感",
"杂志感", or "插画风", the style is not ready.

## Domain Fit, Not Domain Lock

The following are defaults, not fixed templates. Use them to reason, then adapt
to the actual source material and audience.

| Domain | Strong defaults | Good images | Common mismatch |
| --- | --- | --- | --- |
| Technical, AI, infrastructure, engineering | rigorous editorial, operational realism, data-dense proof | system cutaways, real workflow scenes, consoles, traces, architecture, metrics | cute illustration, decorative cyberpunk, soft craft texture |
| Business, strategy, market, finance | crisp report, executive editorial, clean data story | charts, tables, maps, annotated source pages, customer workflow | cinematic mood without evidence, fake KPI dashboards |
| Product, brand, SaaS, app launch | product-first cinematic or clean product editorial | real product surfaces, user workflows, before/after scenes, integrations | abstract gradients with no product signal, fake UI |
| Education, courseware, knowledge explainer | clear teaching hierarchy, friendly but disciplined visuals | examples, diagrams, manipulatives, progressive steps, memory anchors | luxury launch style, tiny labels, decorative stickers |
| Culture, history, biography, literature, music | artifact-led editorial, premium cultural, archival clarity | portraits, places, timelines, source artifacts, maps | fake antique paper, fake seals, generic nostalgia |
| Research paper, scientific report | paper/technical editorial, figure-first proof, precise diagrams | source figures, formulas, tables, experiment flow, result comparisons | dramatic hero scenes that hide methods or evidence |
| Creator/community/social talk | warm editorial, energetic poster rhythm, controlled playfulness | real moments, quotes, examples, behind-the-scenes objects | icon soup, random stickers, unreadable novelty type |

Mismatch is not about banning a style globally. A style fails only when it makes
the subject less clear, less trustworthy, less emotionally accurate, or harder
to read.

## Image Beauty

Images are beautiful when they belong to the slide.

Every major image should answer:

- What claim does it support?
- What concrete object, place, person, system, or artifact should the audience
  inspect?
- Where will the editable title/body/label sit safely?
- What can be annotated or visually compared?
- What style would make this subject less credible?

Generated image prompts must include:

- page role
- page claim or audience takeaway
- concrete subject and focal object
- camera/medium appropriate to the domain
- safe text area
- annotation targets
- negative style list for this topic

If an image can be reused unchanged under an unrelated title, it is not good
enough for final quality.

## Layout Beauty

Before rendering, assign each slide a role:

- `anchor`: opening claim, chapter turn, closing idea
- `dense`: evidence, source, chart, table, comparison
- `diagram`: process, system, causal loop, map
- `breathing`: quote, synthesis, transition, reset
- `action`: checklist, decision, next step

A 7+ page deck should show rhythm across these roles. Consecutive slides may
share a family, but they should not share the same visual fingerprint unless
the deck is intentionally a strict report template.

## Typography Beauty

Default requirements:

- one dominant title hierarchy per slide
- Chinese body text uses readable sans/serif, not novelty display fonts
- body lines have real line height and paragraph spacing
- accent color is for short emphasis, labels, lines, or large display words
- long claims and paragraphs stay neutral high contrast
- source notes move to speaker notes unless readable in contact-sheet review

If beauty requires shrinking text until it becomes hard to read, the content or
slide split is wrong.

## Anti-Slop Review

Before final delivery, inspect a contact sheet or key screenshots and fail the
deck if any of these are visible:

- every page looks like the same card/grid template
- images are decorative wallpaper rather than proof or atmosphere with a role
- title, body, source notes, and labels compete for attention
- text sits on busy images without a stable reading surface
- accent colors are used for sentence-level reading
- generated images contain fake UI, fake charts, fake documents, fake logos, or
  baked-in readable Chinese text
- the deck looks like the previous task's leftover style
- the first four thumbnails do not signal a clear subject and visual promise

## Repair Order

When the deck is ugly, do not start with colors. Repair in this order:

1. Clarify the audience takeaway and page role.
2. Rechoose the aesthetic decision if the style is wrong for the domain.
3. Rebuild the image/content binding.
4. Change the layout pattern and slide rhythm.
5. Reduce copy or split the slide.
6. Then tune typography, palette, spacing, and micro-components.

