# Generation Failure Retrospective

This reference records concrete failures observed during Qiaomu PPT generation and converts them into reusable production rules.

## Incident: Connector Lines Through Diagram Nodes

Observed:

- Connector lines entered oval nodes and crossed Chinese labels.
- Lines were too strong and made the diagram look like construction geometry.
- After fixing line-through-node defects, one preview still looked wrong because the nodes and connector endpoints were not aligned to a shared diamond/grid.

Root cause:

- The generator drew center-to-center connectors between node coordinates.
- Connector z-order was above shapes.
- The contract said "thin/simple connectors" but did not require perimeter ports, clipping, or stroke limits.
- The diagram used hand-tuned endpoint coordinates instead of one source of truth for node centers, sizes, ports, and alignment.

Skill rule:

- Connector-based diagrams must define node bounding boxes and ports.
- Draw connectors from node perimeter to node perimeter, not center to center.
- Leave a visible gap or render connectors behind opaque nodes.
- Connector stroke should be 0.75-1.25 pt in PPTX and 1-2 px in HTML/SVG.
- Connector diagrams must declare alignment geometry: shared centerlines, equal spacing, symmetry axis, or grid coordinates.
- Do not hand-code endpoints independently from node positions. Compute endpoints from node centers and bounding boxes.
- Reject any rendered slide where a line crosses node text or interior.
- Reject any rendered diagram where intended symmetric structures are visibly off-axis or unevenly spaced.

## Incident: Formal HTML Exists But Is Not Usable

Observed:

- HTML was delivered as a separate artifact, but readability and layout quality were not good enough.
- The browser version could drift from PPTX and become a hollow second presentation.

Root cause:

- HTML was treated as an export checkbox, not as a first-class presentation.
- The contract did not require browser readability QA or content parity beyond basic file existence.

Skill rule:

- Formal HTML must be generated from `slide_plan.json`, `content_contract.json`, and `visual_contract.json`.
- It must preserve slide titles, proof objects, concrete anchors, and reading sequence.
- Use a fixed 16:9 stage with responsive scaling and explicit HTML type tokens.
- Check at least desktop and laptop/projector viewports before claiming completion.
- Record `readability_qa` in `html_delivery_manifest.json`.

## Incident: Full Deck Generated Before Visual Risk Was Known

Observed:

- A 12-slide deck was generated in one pass; systemic issues appeared in multiple slides.
- Fixing after full generation wastes time and lets repeated defects spread.

Root cause:

- Proposal approval was treated as approval for full rendering.
- No intermediate preview gate tested typography, background rhythm, diagrams, or HTML.

Skill rule:

- If a normal PPT is expected to exceed 7 slides, generate a four-slide preview first.
- Preview must include four different roles: opening, dense proof, diagram/process, and breathing/turning-point/closing.
- Wait for user approval before full generation.
- Record the state in `preview_gate.json`.

## Incident: Checks Passed But Visual Defects Remained

Observed:

- Static project checks passed even when the preview image revealed design defects.

Root cause:

- JSON contract checks cannot see every rendered geometry issue.
- Visual inspection happened after reporting, not before.

Skill rule:

- Render or open preview artifacts before final response.
- Inspect actual thumbnails/screenshots, especially diagram slides.
- If a screenshot reveals a defect, repair the generator or rule contract and rerun checks before reporting completion.
