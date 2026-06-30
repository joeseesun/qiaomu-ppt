# Topic Research Method

This is the default method when the user asks for a PPT from a broad topic
instead of supplying a finished source document. A topic-only request has no
real soul until the deck has sources, facts, images, quotes, and an angle.

Example trigger:

```text
制作一个 PPT 介绍蒲松龄
```

Do not jump from this sentence directly to slide rendering. First build the
material base, then discuss the angle with the user, then generate structured
content.

## When This Gate Applies

Use this gate when the user provides:

- a person, book, place, company, technology, historical period, concept, or
  cultural topic with no source packet
- a vague command such as "介绍 X", "做一个关于 X 的 PPT", "讲讲 X"
- a topic whose facts, dates, images, or interpretations should be verified
- a topic where visual material matters, such as biography, literature, brand,
  product, history, travel, art, or science explanation

Skip only when the user explicitly provides complete source material and says
not to research, or when the deck is a purely internal draft with stated
assumptions.

## Core Principle

Research is not a decoration step. It decides:

- what the deck is really about
- what can be claimed with confidence
- what visual objects can carry proof
- what should be a timeline, map, quote, diagram, image, table, or sidebar
- what should be left out because the source base is thin

If the original data and images are weak, do not compensate with generic copy.
Report the weakness, ask for material, or choose a more honest visual strategy.

## Phase 0: Context Intake

Before searching or rendering, collect the minimum context through the guided
choice flow unless the user's first message is already complete or includes a
strict approval-bypass phrase.

Show a compact card with recommended defaults for:

- topic angle or narrative direction
- audience/depth
- page count
- style or scene type
- image/source policy
- output format

If the user replies `生成`, `默认`, or partial codes after this card, apply the
defaults and begin the research workflow. This reply does not approve final PPT
generation.

## Phase 1: Research Brief

Write a short research brief before searching:

```json
{
  "topic": "蒲松龄",
  "assumed_audience": "general Chinese-speaking audience",
  "route": "talk_deck",
  "research_questions": [
    "他的人生经历如何塑造《聊斋志异》？",
    "《聊斋志异》的文学价值是什么？",
    "哪些图像、地点、文本片段可以成为视觉证据？"
  ],
  "source_strategy": [
    "authoritative biography",
    "museum or memorial source",
    "academic/literary-history source",
    "work/text source",
    "rights-clear or public-domain visual material"
  ],
  "known_risks": [
    "folk anecdotes may be unstable",
    "portrait and manuscript images need rights checks",
    "literary evaluation should not be stated as bare fact"
  ]
}
```

## Phase 2: Source Collection

Search broadly enough to avoid a Wikipedia-shaped deck. For a person/literary
topic, use separate queries for:

- biography and chronology
- historical/social context
- major works and publication history
- core ideas, themes, or intellectual contribution
- representative quotes or passages
- later influence, adaptations, museums, memorials, or education use
- usable images: portraits, manuscripts, old editions, places, maps, museum
  photos, or public-domain illustrations

Prefer source variety:

- official/museum/memorial institution
- encyclopedia baseline
- academic or university source
- book/article review from a reliable publication
- original text or public-domain edition when relevant
- image source with rights/attribution information

Save evidence under:

```text
~/Downloads/Qiaomu PPT/<date>-<slug>/
  README.md
  task_manifest.json
  research_dossier.md
  content_report.md or 内容母稿-<主题>.md
  sources/
    source_manifest.json
    source_notes.md
    source_cards.json
    images/
```

`source_manifest.json` records where material came from. `source_notes.md`
records what the material means. `source_cards.json` is a structured bridge to
the slide plan. `research_dossier.md` is the human-readable research Markdown
shown or summarized before the slide plan; it may be a root-level file or a
substantial `sources/source_notes.md` when the project stays compact.
`content_report.md` or `内容母稿-<主题>.md` is the source-synthesis article: it
turns the research into a readable argument with a central thesis, reasoning,
boundaries, and slide-worthy claims. It is not optional for broad-topic decks
unless the user supplied a finished article/source document and explicitly asks
to skip synthesis.
`README.md` and `task_manifest.json` make the research package reusable even if
the workflow stops before PPT generation.

For a deterministic first pass, use:

```bash
python3 ~/.agents/skills/qiaomu-ppt/scripts/topic_research.py "蒲松龄" \
  --output-dir <project>/sources \
  --depth fast \
  --max-pages 3
```

`--depth fast` prioritizes quick, stable entity/overview sources and is the
default route used by `prepare_deck_project.py` for topic-only requests.
`--depth balanced` or `--depth deep` may broaden search lanes and scholarly
sources, but those modes are slower and should record provider gaps in
`topic_research_report.json`. Search candidates are only candidates; final
slide claims must come from ingested source cards.

For compound topics, split the user's phrase into entity focus terms before
searching. A topic such as `蒲松龄与聊斋志异` should search both `蒲松龄` and
`聊斋志异`, not only the full phrase. The default automated route must not
require a private search key: use Wikipedia/Wikidata, DuckDuckGo Instant Answer,
OpenAlex for deep scholarly lanes, and manual `--candidate-url` seeds when a
general web search has already found useful sources.

If automated candidate discovery returns no useful URLs, do not report a missing
search key as the problem. Record the candidate gap and try a different route:
Codex/web search or site search to seed URLs, then ingest known URLs through the
source intake cascade. For special source types, use the methods in
`source-intake-method.md` before marking `missing evidence`.

When building `source_cards.json`, filter navigation text, footnotes, external
advertising, bibliography-only lines, language switchers, wiki project links,
and citation metadata. Prefer factual sentences with dates, works, places,
mechanisms, named examples, or interpretive tension. For Chinese-first decks,
Chinese-facing claims may be deterministic paraphrases of raw English evidence,
but the original evidence text must remain in the card so the claim can be
audited.

Recommended `source_cards.json` shape:

```json
{
  "topic": "蒲松龄",
  "cards": [
    {
      "id": "bio-exam-failure",
      "source_id": "s02",
      "type": "biography_fact",
      "claim": "蒲松龄长期科举失意，这一人生经验影响了《聊斋志异》的现实批判气质。",
      "evidence": "source-backed summary or short compliant quote",
      "usable_as": ["timeline", "turning_point", "speaker_note"],
      "confidence": "high",
      "visual_potential": "timeline marker or scholar-at-desk scene",
      "missing_evidence": []
    }
  ],
  "image_candidates": [
    {
      "id": "zichuan-memorial",
      "source_id": "s05",
      "path_or_url": "sources/images/...",
      "role": "place_context",
      "rights_note": "record source and license/status",
      "usable_pages": ["cover", "chapter_context"]
    }
  ]
}
```

## Phase 3: Source Notes

`source_notes.md` and/or `research_dossier.md` should include:

- one-paragraph topic understanding
- timeline or key sequence
- quote bank and source page/title
- important names, places, dates, works, and terms
- interpretive claims separated from factual claims
- contradictions or uncertain facts
- visual asset inventory and rights notes
- material gaps that would weaken the deck
- which points came from supplied material, which came from web/source research,
  and which are model-knowledge assumptions needing verification

Never hide gaps. A deck with honest gaps is better than a confident generic
deck.

## Phase 3.5: Source-Synthesis Article

Before writing `content_contract.json`, `slide_plan.json`, or a formal HTML/PPTX
render, write a source-synthesis article:

```text
<project>/content_report.md
<project>/内容母稿-<主题>.md
```

This is the content mother document for the deck. It should read like a compact
essay, not like a bibliography or a list of links. It answers:

- after reading the sources, what is the central judgment?
- what facts and examples support that judgment?
- what interpretation is yours, and what is source-backed?
- what tension, contradiction, or audience misconception makes the topic worth
  presenting?
- what reusable claims, examples, and reasoning structure does the article make
  available for later planning?
- what should not be claimed because evidence, rights, or freshness is weak?

Minimum shape:

```markdown
# <主题>: <清晰判断>

## 中心判断
...

## 资料如何改变了我的理解
...

## 支撑这个判断的关键事实
...

## 解释结构
...

## 可复用的主张结构
...

## 资料边界与风险
...
```

Hard rules:

- `research_dossier.md` is a research archive; it does not replace the
  source-synthesis article.
- The source-synthesis article is research material, not a layout plan. Do not
  include page-by-page structure, typography, image-generation prompts, visual
  style choices, or PPT production advice in this article; put those in second
  stage sidecars such as `page_kernel_map.json`, `visual_translation_plan.json`,
  `design_proposal.md`, or `slide_plan.json`.
- Do not generate `slide_plan.json` directly from search results, link lists, or
  unprocessed source cards for a broad topic.
- If the user wants speed, write a shorter but still coherent article first,
  then produce a fast draft; do not skip the article.
- The final answer should report the content article path alongside the PPT/HTML
  output path.

## Phase 4: User Alignment Checkpoint

Before creating the full design proposal, discuss the content direction with
the user. Offer 2-3 angles, not 10.

For `蒲松龄`, possible angles:

1. `文学人物传记`: 科举失意者如何写出《聊斋志异》。
2. `作品解读`: 《聊斋志异》不是鬼故事集，而是社会现实的镜子。
3. `文化传播`: 从书斋志怪到影视改编，蒲松龄如何进入现代想象。

Ask for confirmation when the choice affects the deck:

- audience: students, general public, literature lovers, lecture audience
- depth: 8-10 page overview or 15-20 page lecture
- tone: museum exhibition, literary magazine, classroom courseware, dark zhi-guai
- image tolerance: source images only, generated concept images allowed, or both
- citation visibility: visible source page, notes only, or final references page

If the user asks to move fast, record assumptions and continue, but still keep
`missing_evidence` visible in sidecar artifacts.

## Phase 5: Content Contract

Only after research, source synthesis, and alignment, write
`content_contract.json`.

Required fields for topic-researched decks:

```json
{
  "research_required": true,
  "research_status": "completed | partial | skipped_by_user",
  "source_synthesis": "content_report.md",
  "topic_angle": "作品解读",
  "audience": "...",
  "purpose": "...",
  "desired_action": "...",
  "source_coverage": {
    "biography": "covered",
    "context": "covered",
    "primary_work": "covered",
    "visual_assets": "partial",
    "image_rights": "needs_review"
  },
  "evidence_policy": "every mainline slide must cite source_cards ids",
  "slide_claims": []
}
```

Then write `slide_plan.json`. Every mainline slide should include:

- `source_card_ids`
- `source_anchor`
- `proof_object`
- `claim_title`
- `visible_content`
- `layout_pattern`
- `image_or_background_plan`
- `visual_role`
- `speaker_note_goal`
- `qa_risk`

If a slide lacks a source card, it is probably filler.

Before rendering, present the slide plan to the user for confirmation. The
confirmation surface should make every page inspectable: slide number, title,
content, source anchor, layout, background/image plan, and risk. If the user
approves with changes, update `content_contract.json`, `slide_plan.json`, and
the design proposal before any preview or full deck generation.

## Phase 6: Style Comes After Evidence

Select style after the content angle is chosen. For a Pu Songling deck, viable
directions might be:

- museum exhibition: calm paper, archival images, map/timeline/table
- literary magazine: large pull quotes, folio marks, manuscript texture
- dark zhi-guai: restrained dark paper, ink texture, source-backed ghost/fox
  motifs, no fake occult clutter
- classroom clear: readable diagrams, definitions, examples, teacher notes

Do not choose `dark zhi-guai` just because the topic contains ghosts. If the
deck is for class, readability wins.

## Minimum Research Quality

For a normal public-facing topic PPT, aim for:

- at least 5 credible text sources
- at least 2 source types, such as official/museum plus academic/encyclopedia
- at least 1 primary-work or primary-document source when the topic is literary,
  historical, legal, scientific, or technical
- at least 3 visual asset candidates or a clear reason why generated conceptual
  images will be used instead
- a source note for every major date, number, quotation, and interpretation
- a Markdown research dossier detailed enough to support the slide-plan
  confirmation step

If these are not met, mark `research_status: partial` and discuss the gap with
the user before pretending the deck is final.
