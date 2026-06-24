# Quality Gates

## Route Gate

- The route matches the expected final delivery.
- The skill did not choose HTML-only when the user needed editable PPTX.
- The skill did not force sparse launch-deck aesthetics onto dense courseware.
- For normal user-facing PPT creation, a `PPT Design Proposal` was shown and approved before full generation, unless the user explicitly requested an immediate draft or batch mode.
- When `scripts/prepare_deck_project.py` is used, `project_prepare_report.json` records whether the project is `needs_research` or `ready_for_design_review`; the prepare stage is not reported as a final PPT export.

## Source Gate

- Product facts, prices, specs, dates, and claims are sourced or user-provided.
- Courseware facts, formulas, translations, historical claims, and exam standards are verified from supplied material or labeled draft assumptions.
- Mixed-source decks preserve source identity in `source_manifest.json`; PDFs, EPUBs, Office docs, Feishu exports, folders, ZIPs, images, and URLs are not flattened into anonymous notes.
- `source_manifest.json` records extraction route, Markdown path, warnings, missing evidence, and image/asset candidates for each source.
- Source-backed decks have `source_notes.md` and `source_cards.json` generated from the manifest as a first-pass evidence index before content contracts and slide plans are written.
- File/link-backed prepare runs have `deck_brief.md`, `style_brief.md`, `design_proposal.md`, `content_contract.json`, `slide_plan_seed.json`, and `visual_contract.json` before rendering starts.
- Paper sources from arXiv or Hugging Face Papers are normalized to an arXiv ID and have `paper_manifest.json`; TeX/source extraction is preferred, figures/tables/captions are recorded, and PDF fallback explicitly records `tex_source_unavailable`.
- Paper figures, tables, diagrams, and benchmark charts used on slides are linked to `source_card_ids`, `source_anchor`, or a paper manifest entry. Generated images are not used as substitutes for paper-original evidence.
- WeChat public-account sources are marked as `wechat_article`; if generic extraction yields weak text or missing images, `wechat_specialized_extractor_recommended` or `wechat_images_not_extracted` is recorded before slide planning.
- Topic-only decks have `research_plan`, `sources/source_manifest.json`, `sources/source_notes.md`, and `sources/source_cards.json`, unless the user explicitly skipped research.
- Automated topic research has `sources/topic_research_report.json` when `scripts/topic_research.py` is used; search candidates alone do not count as evidence until selected URLs are ingested into `source_manifest.json` and `source_cards.json`.
- Topic-only decks record the selected content angle, source coverage, image availability, and material gaps before the design proposal.
- Every mainline slide in a topic-researched deck has `source_card_ids` or is clearly marked as cover/chapter/closing/breathing.
- Image/logo rights are not assumed.
- Source and generation provenance is recorded in sidecar artifacts, not automatically printed on every slide.

## Topic Research Gate

- The deck did not start from a bare topic and immediately generate slide copy.
- Research covers multiple dimensions appropriate to the topic, such as biography, context, works/products, influence, timeline, primary text, and visual assets.
- Source notes separate factual claims from interpretation.
- The user was shown 2-3 content angles and the selected angle is recorded, unless they explicitly asked to skip discussion.
- Weak material is handled honestly: request more material, use `research_status: partial`, choose a source-light visual strategy, or mark `missing evidence`.
- Images are not treated as decoration. The project records visual asset candidates, source/rights notes, and whether generated concept images are allowed.
- Feishu/Lark documents are read from exports or authenticated connectors; a bare private link without access is marked as missing evidence.
- EPUB/book decks have chapter/source notes and quote/location limitations recorded before slide planning.
- Paper decks have source cards for abstract, key sections, figures, and tables before slide planning.
- WeChat article decks do not rely on empty Markdown image placeholders; article images are downloaded, user-provided, or marked as missing.
- Scanned PDFs/images use OCR when available; otherwise the OCR gap is visible and claims are not inferred from the image.

## Narrative Gate

- Every slide has one clear intent.
- Brand/talk decks move the audience state forward.
- Courseware moves the learner state forward.
- No slide exists only because the template had room.

## Upstream Creation Audit Gate

- `reports/content_outline_audit.json` exists before formal rendering in professional/final runs. It scores source-backed claims, concrete anchors, claim-title quality, story contract completeness, source material depth, and anti-generic copy.
- `reports/element_plan_audit.json` exists before formal rendering in professional/final runs. It scores proof-object coverage, component plans, layout/media intent, element diversity, asset queue readiness, and source-visual priority.
- `reports/style_fit_audit.json` exists before formal rendering in professional/final runs. It checks selected-style identity, content-domain fit, style contract completeness, density targets, slide-level layout program coverage, media policy alignment, and generated-image boundaries.
- These audits run before SVG/PPTX/HTML generation because they answer the real production question: whether the deck has enough source-backed thinking, a proof-driven element plan, and a style that serves the content.
- A deck that fails any enforced upstream audit should be repaired at `sources/source_cards.json`, `content_contract.json`, `slide_plan.json`, `visual_asset_manifest.json`, `style_direction.json`, or `design_proposal.md` before visual rendering. Do not hide upstream weakness by adding decorative backgrounds, cards, or icons.

## Copy Gate

- Decks longer than 8 slides have a `content_contract.json` or equivalent audience-purpose card.
- The selected structure framework fits the route: `pyramid` for decisions/reports, `SCQA` for problem/proposal openings, `MECE` for complex decomposition, `storyline` for launch/fundraising/vision, and `teaching_arc` for courseware.
- Slide titles are claim titles, not vague labels. Reading only the titles should reveal the deck's argument.
- Each mainline slide has one dominant claim, one proof focus, and normally no more than 3-5 visible support chunks.
- Each mainline slide has at least one concrete anchor from the source or user brief: number, named example, scenario, mechanism step, boundary condition, counterargument, or consequence. Slides that read like generic advice fail the copy gate.
- Generic titles such as `背景`, `现状`, `问题`, `方案`, `数据`, `总结`, `Overview`, and `Agenda` are revised into specific claims unless the slide is an explicit navigation page.
- Speaker notes carry nuance, caveats, transitions, and likely objections; visible copy carries signal.

## Visual Gate

- The visual system has a thesis, palette, type scale, layout rhythm, and media policy.
- The deck separates `narrative_mode`, `visual_style`, image rendering, palette behavior, image type, and image layout. A single vague adjective must not drive all decisions.
- Style selection compares at least 3 visibly different candidates when the user did not specify a style. The chosen direction is justified, and repeated use of the same recent style is avoided unless intentionally approved.
- Decks longer than 8 slides use at least 5 distinct layout families unless the route explicitly calls for a minimalist keynote.
- Image-rich, screenshot, quote, product, before/after, timeline, or data-context slides declare an `ITLxx` image/text pattern from `image-text-layout-patterns.md` and map it to the slide's `Lxx` proof-structure pattern.
- The deck has a per-slide visual component plan. Conceptual/article decks normally include 2-4 explanatory diagrams or visual models; data/report decks include appropriate charts or tables when source data exists.
- Decks longer than 8 slides have a `background_rhythm` with at least 4 roles and no role repeated more than 2 consecutive slides.
- Decks longer than 8 slides should have 8-12 available background assets or justified fewer assets, and should not use the exact same background asset on consecutive slides.
- Decks longer than 8 slides declare `visual_noise_budget`, normally `quiet`.
- Decks longer than 8 slides declare `color_budget` with `max_active_colors_per_slide <= 3`, and each slide declares `active_colors`.
- When Codex image generation is available, decks explicitly decide whether to use generated backgrounds/concept images. Default for talk/brand/technical decks is a 3-5 candidate background or concept-image exploration before final rendering; if skipped, the reason is recorded.
- Generated backgrounds are content-led atmosphere only. Each AI background or
  concept image used in a final-quality deck declares `content_link`,
  `background_duty`, and `semantic_anchor`, tied to the slide claim/proof or
  audience state change. A generated image that is only generic wallpaper,
  random linework, a style mood, or decoration fails the visual gate.
- Generated backgrounds must not contain boxes, rectangles, panels, cards, frames, placeholders, chart areas, image slots, UI chrome, or text blocks; these must remain editable foreground objects.
- `visual_contract.json` records the background engine, seed or prompt pack, and `procedural_fallback_policy`.
- When generated, web, user, source, formula, or placeholder assets are planned, `visual_asset_manifest.json` exists and is referenced from `visual_contract.json` or `spec_lock.json`.
- The thumbnail grid shows visible variation in background tone, dominant object placement, and slide density.
- Backgrounds are calmer than the content: no repeated hard side stripes, oversized saturated wedges, stacked decorative motifs, meaningless tech lines, ornamental grids, or noisy chart backdrops unless explicitly brand-required.
- Lines are functional only: chart axes, table rules, connectors, or content separators. Lines that exist only to add texture or "tech feel" fail the visual gate.
- Connector lines must terminate at shape perimeter/ports and must not pass through node interiors or text. Heavy connector strokes, connector shadows, and center-to-center lines through nodes fail the visual gate.
- If style was unspecified, `style_recommendations.json` exists or the reason for skipping style recommendation is stated.
- Any selected Design-MD preset is copied into `style_brief.md` and `spec_lock.json` as PPT rules, not left as vague inspiration.
- No one-note generic palette, no default purple-gradient design, no arbitrary style mixing.
- Chinese content uses readable spacing and avoids obvious CJK layout failure.

## Visual Asset Acquisition Gate

- Every non-trivial image/chart/diagram/icon/placeholder has a row in `visual_asset_manifest.json`.
- Every row declares `acquire_via`: `ai`, `web`, `user`, `source`, `formula`, or `placeholder`.
- AI rows declare deck-wide image rendering/palette behavior plus a concrete prompt, page role, asset role, and `text_policy`.
- Web/source/user rows declare source URL/path/card id, rights/provenance notes, and extraction gaps when relevant.
- Formula/chart/diagram rows declare the source spec and rendered output path.
- `Generated`, `Sourced`, `Existing`, and `Rendered` rows point to files that exist under the project folder or to explicitly allowed external user files.
- `Pending` rows are accepted only for proposals, drafts, or previews. Final decks either resolve them or list them under `missing evidence`.
- Generated images are never used as substitutes for paper figures, screenshots, product UI, logos, charts, tables, legal/medical/financial evidence, or citation-bearing source material.
- `assets/images/image_prompts.json` and `assets/images/image_prompts.md` exist when AI images are planned and cover all AI rows.
- `scripts/visual_asset_manifest.py validate` passes before final export, or failures are explicitly reported.

## Visual Review Gate

Run visual review after static checks and rendered screenshots/thumbnails exist.

Hard defects must be fixed before export:

- out-of-bounds content
- text overflow, clipping, or incoherent overlap
- low contrast on title, proof object, or essential labels
- broken or missing image assets
- title or proof object covered by decoration, texture, or watermark
- chart/table/diagram too small to read at the target preview size
- text over image without copy space, scrim, gradient, text block, or local blur
- screenshot annotations, before/after pairs, or collages with no clear focal hierarchy

Soft quality defects should be fixed in focused passes:

- rhythm is too tight, too hollow, or monotonously repeated
- centroid is unintentionally off-balance
- alignment drift or uneven grid spacing weakens the reading path
- accent colors overload the content
- image and text feel adjacent but unrelated
- breathing pages use dense multi-card grids
- CJK text uses awkward letter spacing, tiny punctuation, or cramped line breaks

Fix one concrete defect at a time. QA fixes should not quietly change the deck
mode, rewrite the argument, or replace the approved visual direction.

## Benchmark Repair Gate

- `reports/deck_quality_benchmark.json` records score, readiness, score caps,
  category evidence, warnings, and ppt-master learning-catalog baseline gaps.
- `reports/deck_repair_plan.json` / `.md` must be generated after benchmark for
  non-trivial decks. It converts weak categories into prioritized repair actions
  for source grounding, source visual usage, image density, real image
  generation, layout execution, visual rhythm, export coverage, and contract
  completeness.
- A deck with critical repair actions is not final-quality, even if PPTX/PDF/HTML
  export succeeded. Fix the highest-priority contract/manifest/renderer problem
  first, then rerun the relevant checks.
- Use `produce_deck.py --fail-on-critical-repairs` when a batch or release run
  should fail instead of emitting a low-quality deck with a warning.
- Use `deck_repair_apply.py` or `produce_deck.py --auto-apply-repairs` only for
  safe deterministic contract fixes: visible title fit, layout IDs, component
  types, rhythms, repetitive-layout rhythm repair, image-text pattern IDs, deck/style brief defaults,
  visual/content/asset contract defaults, prompt sidecars, and pre-render
  spec-lock structure. Missing asset manifests may be created only as
  `Needs-Manual` planning rows. It must not invent source evidence, fake image
  files, mark pending images as generated, or claim final-quality visuals.
- Repair actions are guidance for Qiaomu-owned artifact edits. Do not copy
  upstream templates, images, exact slide wording, or copyrighted designs while
  fixing benchmark gaps.

## Layout Execution Gate

- Every mainline slide has a declared `proof_object`; slides without proof objects are rewritten, merged, or treated as intentional navigation/breathing pages.
- `spec_lock.json` contains `layout_execution_contract` for SVG-first, PPTX-oriented, chart/diagram-heavy, image-rich, or long deck runs.
- Each slide in the contract declares `rhythm`, `layout_pattern_id`, `component_type`, `reading_path`, `coordinate_slots`, and `group_ids`.
- Media-rich slides also declare `image_text_pattern_id`, `image_role`, `crop_policy`, `text_safe_area`, `contrast_policy`, and `font_floor_pt`.
- The component type matches the proof object: steps use steps/flow, time uses timeline, records use table, source data uses chart-with-takeaway, categories use icon grid or labeled cards, scenes use image claim layouts.
- Coordinate slots include title and proof regions and use the deck's fixed coordinate system.
- SVG pages under `svg_output/` or `svg_final/` use stable top-level `<g id="...">` groups that match the contract.
- SVG-first decks should expose multiple semantic top-level groups per slide, not just a single whole-slide wrapper. At minimum, normal pages should make background/chrome, title, proof or media, body/callouts, and footer separable when those regions exist.
- If `animations.json` exists, every animated group ID exists in the corresponding SVG page.
- Motion follows the reading path; it does not introduce a second decorative rhythm.

## Image Slot Gate

- Every source image/chart has a declared image slot with `fit`, `mask`, `padding`, and `overflow_policy`.
- Every substantial image slot has a declared `finish_policy`: real clipping/masking when rounded, low-contrast border or hairline when needed, subtle shadow only when it improves separation, and color/contrast normalization when the source image fights the deck palette.
- Every media-rich slide has protected title/body/proof/caption boxes and a minimum clearance from the image slot. Default clearance is `48px` on `1242x1660` social canvases, `28px` on `1280x720` slides, or `0.22in` in PPTX coordinates.
- Every substantial media slide has a declared image role: background, evidence, emotion, product, person, step, context, or screenshot. One image should not be asked to do several roles at once.
- Text-over-image slides meet the contrast policy or move text into safe copy space / scrim / text block.
- Accidental image/text overlap fails QA. Do not hide it with opacity, shadow, blur, or scrim; resize, move, wrap, or change the layout pattern.
- Screenshot annotation slides crop away irrelevant UI chrome and keep annotation count to 3-5 unless a report route explicitly requires detail.
- Before/after slides use matching ratios, label positions, and crop logic; otherwise they fail comparison readability.
- Collage and moodboard slides have one dominant image and consistent crop/tonal logic.
- Images/charts do not exceed their intended frame in the rendered preview.
- A rounded rectangle behind an image is not accepted as clipping. Use real crop/mask/compositing, a square frame, or a native picture placeholder.
- Dense benchmark charts use `contain` or an intentional crop with a source note; do not stretch or crop silently.

## Readability Gate

- No overflow, overlap, clipped text, unreadable small type, or unplanned scroll.
- Important classroom content is visible from a projector-distance mindset.
- Speaker-led decks avoid walls of bullets.

## Provenance Gate

- Visible slide text does not include internal toolchain metadata such as `fetched via`, `generated with`, `qiaomu-markdown-proxy`, or `Speaker cue:`.
- Visible slide text does not include internal production jargon such as `deck`, `route`, `fallback`, `artifact`, `pipeline`, `source_fetch`, `PPTX export`, model names, or tool names unless the topic is explicitly about the production workflow.
- Model names, fetch method, and QA evidence live in `generation_report.md`, `qa_report.md`, speaker notes, or a final references page.
- Visible source citations are opt-in or route-specific. When used, they cite content sources only; they do not expose generation tools.

## Production Gate

- Declared output files exist.
- Export commands completed successfully.
- When `scripts/export_bundle.py` is used, `export_manifest.json` exists and lists separate statuses for PPTX, PDF, formal HTML, parity HTML, and Keynote if requested.
- `export_manifest.json` success paths for PDF, parity HTML, and Keynote are fresh relative to the current PPTX. Older files are stale evidence and fail the production gate.
- Decks over 7 slides have `preview_gate.json` with an approved four-slide preview or an explicit user skip recorded before full generation.
- Final decks with `visual_asset_manifest.json` have no unresolved `Pending` rows for assets used on mainline slides unless the limitation is recorded as missing evidence.
- Final-quality editable PPTX decks use the SVG-first built-in route: `scripts/svg_deck_from_slide_plan.py` or page-specific SVG authoring, `scripts/svg_quality_checker.py`, `scripts/svg_preview.py`, `scripts/finalize_svg.py`, and `scripts/svg_to_pptx.py`; do not rely on an external `pptx` skill as a runtime dependency.
- A normal editable PPTX must not be a deck of full-slide screenshots. Run `scripts/pptx_text_check.py` without `--allow-image-backed`; most slides must expose native foreground text/shapes. Full-slide raster pages are allowed only for explicitly labelled parity preview, social-image output, or user-approved non-editable drafts.
- A high-quality HTML/PNG preview must not be followed by a separate low-fidelity editable redraw. Preview, SVG, and PPTX should be generated from the same `slide_plan.json`, `spec_lock.json`, and `layout_execution_contract`. If visual richness requires bitmap material, use it only for atmosphere/background/photographic layers and keep text, cards, charts, labels, frames, and diagrams editable.
- `page_content_guide.md`, `page_content_guide.json`, and `page_content/` exist for normal production runs. They gather each page's outline, source evidence, visual plan, visual assets, speaker notes, and QA summary in human-readable form so the user can understand and edit what each page is doing.
- `svg_generation_manifest.json` and `svg_preview_manifest.json` exist when SVG-first pages are generated.
- `pptx_generation_manifest.json` exists when the low-complexity `python-pptx` fallback exporter is used.
- `pptx_text_check.json` exists for final PPTX runs and reports no missing slide-plan titles, placeholders, or internal production metadata.
- Normal PPT runs produce editable PPTX; when HTML is requested or expected, they produce a formal semantic HTML presentation artifact unless the user explicitly forbids HTML or the route is planning-only.
- Formal HTML decks have `html_delivery_manifest.json`, use DOM/SVG/Canvas/CSS/JS as the visible layer, preserve slide-plan content parity, include readability QA, and do not use whole-slide PPTX/PDF/JPG/PNG screenshots.
- PPTX parity screenshot HTML is allowed only as QA/preview output under `html-parity/` or `*.parity.html`, with `html_parity_manifest.json`.
- PDF delivery is backed by a real exported or preview-derived PDF file, or it is marked `missing` / `failed` in `export_manifest.json`.
- Keynote delivery is backed by a real `.key` artifact saved by Keynote automation and at least as fresh as the current PPTX source, or it is marked `missing` / `failed` in `export_manifest.json`. LibreOffice preview evidence is not Keynote evidence.
- If modern `save as Keynote` fails but Keynote 09 fallback succeeds, `export_manifest.json` records `compatibility_format: Keynote 09`, `fallback_from: save as Keynote`, and the primary failure. Do not describe that artifact as a modern Keynote save.
- Failed Keynote exports include a `diagnostic_command` or a corresponding `reports/*.keynote-probe.json` so the failure is attributable to environment, launch, open/import, save, freshness, cleanup, or baseline-control behavior.
- Run `scripts/check_project.py` when a project folder exists.
- If an editable PPTX exporter is missing, the output is checked SVG/HTML artifacts plus `missing evidence`, not a claimed `.pptx`.

## Speaker Gate

- Brand/talk decks include presenter notes that explain what to say and why the slide exists.
- Courseware includes teacher notes: questions, expected answers, common misconceptions, and board-work cues.

## Verification Gate

- Formal HTML decks are opened where possible and checked as real webpages, not static screenshot galleries.
- For decks over 7 slides, the four-slide preview includes representative typography, dense content, a diagram/process slide, and any formal HTML route before full production.
- PPTX parity previews are opened where possible only to verify rendered PPTX appearance.
- PPTX export exists and is opened where possible.
- PPTX preview evidence exists through `pptx_preview_manifest.json`, per-slide preview images, and a thumbnail grid when LibreOffice/Poppler are available.
- If Keynote is a target or the user is on macOS, fonts declared in the PPTX are installed or verified, macOS Quick Look is tested, and Keynote import is tested through UI or automation where possible. LibreOffice success alone is not enough to claim Keynote compatibility.
- A rendered thumbnail grid or equivalent visual evidence is reviewed when PPTX output exists.
- Visual asset status, missing files, and image rights/provenance gaps are reviewed in `qa_report.md`.
- Missing native Office/WPS verification is explicitly marked `missing evidence`.
- Stop after 3 focused fix rounds and report unresolved risks.
