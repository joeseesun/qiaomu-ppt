#!/usr/bin/env python3
"""Create per-slide image art-direction briefs and generation queues."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import visual_asset_manifest as vam  # noqa: E402


NEGATIVE_PROMPT = (
    "visible text, letters, numbers, captions, labels, watermarks, logo, brand mark, UI, "
    "fake screenshot, fake chart, fake paper figure, fake citation, fake data label, "
    "stock photo cliche, clutter, crowded typography, random decorative linework, ornamental grid, "
    "glowing rail, abstract polygon wallpaper, low resolution, distorted hands, "
    "celebrity likeness, purple gradient background, generic style-only background"
)

TEXT_POLICY = {
    "none": (
        "No visible text of any kind in the image: no letters, numbers, handwriting, signage, "
        "captions, labels, watermarks, stamps, or interface text. All titles, body copy, data, "
        "citations, and labels must remain editable foreground objects in the slide."
    ),
    "embedded": (
        "Only image-owned markings that are not needed as slide content may appear. Do not bake "
        "the slide title, body copy, citations, chart values, labels, or speaker-facing text into the image."
    ),
}

ROLE_BRIEFS = {
    "cover": {
        "art_direction": "cinematic editorial cover with one memorable subject and generous negative space",
        "image_role": "full-bleed cover atmosphere",
        "composition": "dominant subject on the right third or lower right; calm dark-to-light field on the left for editable title",
        "camera": "50mm editorial still-life lens, slightly low angle, shallow depth of field only around the subject",
        "material": "tactile surface, paper grain, glass, ink, metal, fabric, or archival object depending on topic",
        "lighting": "directional museum lighting with soft falloff and restrained contrast",
        "safe_area": "reserve the left 45% and bottom-left 25% as low-detail title-safe space",
        "foreground_boundary": "title and subtitle must sit outside the generated subject silhouette",
    },
    "source": {
        "art_direction": "source-evidence editorial spread without fake readable documents",
        "image_role": "evidence atmosphere or source object",
        "composition": "layered documents or artifacts as abstract proof texture; one clear focal object, never a readable fake page",
        "camera": "top-down archival table or 35mm documentary crop",
        "material": "archival paper, marginalia-like texture without legible glyphs, dust, ink wash, neutral fabric",
        "lighting": "soft window light with controlled shadow",
        "safe_area": "reserve a clean side band of at least 34% width for editable claim and notes",
        "foreground_boundary": "editable citations and source labels must be added by the slide renderer",
    },
    "diagram": {
        "art_direction": "quiet conceptual field that supports an editable diagram",
        "image_role": "background texture for model or mechanism",
        "composition": "subtle depth, diagonal flow, and one symbolic anchor; avoid pre-rendered boxes, arrows, charts, or UI",
        "camera": "orthographic editorial macro, no perspective distortion",
        "material": "matte paper, translucent layers, fine grid texture, faint ink wash, or low-relief objects",
        "lighting": "even softbox light with mild directional gradient",
        "safe_area": "keep the central 70% low-contrast so editable diagram nodes stay readable",
        "foreground_boundary": "all arrows, nodes, labels, operators, and numbers must remain editable foreground objects",
    },
    "comparison": {
        "art_direction": "editorial contrast image with two visual worlds but no baked-in labels",
        "image_role": "split-stage comparison atmosphere",
        "composition": "two opposing materials or moods divided by light, surface, or depth; no literal text labels",
        "camera": "balanced front-facing crop with a stable horizon",
        "material": "left and right sides use meaningfully different textures tied to the slide claim",
        "lighting": "controlled dual-zone lighting with one shared neutral bridge",
        "safe_area": "reserve top 22% and both side margins for editable headings and takeaway",
        "foreground_boundary": "all labels, before/after tags, metrics, and captions stay editable",
    },
    "quote": {
        "art_direction": "literary breathing-space image with poetic restraint",
        "image_role": "quote or transition atmosphere",
        "composition": "one small object or silhouette in a wide quiet field; no decorative filler",
        "camera": "long-lens editorial crop with ample empty space",
        "material": "paper, ink, shadow, fabric, mist, or a symbolic object tied to the topic",
        "lighting": "soft low-contrast light with a clear calm area for large editable quote text",
        "safe_area": "reserve at least 55% of the frame as quiet low-detail quote-safe space",
        "foreground_boundary": "the quote must be editable text, never drawn in the image",
    },
    "closing": {
        "art_direction": "closing editorial image with a sense of synthesis and afterglow",
        "image_role": "final atmosphere",
        "composition": "one strong but quiet symbol receding into space; leave an open area for final claim",
        "camera": "cinematic wide crop, stable horizon, moderate depth",
        "material": "topic-relevant object, landscape, tool, archive, or abstract threshold",
        "lighting": "warm directional end-of-day light or controlled studio glow",
        "safe_area": "reserve the left 50% or upper-left quadrant for editable conclusion text",
        "foreground_boundary": "final conclusion and call-to-action stay editable foreground text",
    },
    "core": {
        "art_direction": "magazine feature image with concrete topic-specific subject matter",
        "image_role": "supporting image or atmosphere",
        "composition": "one clear subject, one secondary texture layer, and enough quiet field for slide hierarchy",
        "camera": "editorial still-life or documentary crop chosen to match the topic",
        "material": "specific object/material from the source, not a generic gradient or abstract wallpaper",
        "lighting": "clean editorial light with readable foreground contrast",
        "safe_area": "reserve at least 30% of the frame as low-detail editable-text space",
        "foreground_boundary": "slide text, icons, diagrams, charts, and data must be editable foreground objects",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_slides(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    slides = payload.get("slides") if isinstance(payload, dict) else payload
    if not isinstance(slides, list):
        return []
    return [item for item in slides if isinstance(item, dict)]


def slide_no(slide: dict[str, Any], fallback: int) -> int:
    try:
        return int(slide.get("slide_no") or slide.get("page") or fallback)
    except Exception:
        return fallback


def slide_title(slide: dict[str, Any]) -> str:
    for key in ("claim_title", "title", "headline"):
        value = normalize_space(slide.get(key))
        if value:
            return value
    return "Untitled slide"


def slide_text(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "claim_title", "intent", "concrete_anchor", "visual_role", "proof_object", "source_anchor"):
        value = normalize_space(slide.get(key))
        if value:
            parts.append(value)
    for key in ("points", "evidence", "speaker_notes", "notes"):
        value = slide.get(key)
        if isinstance(value, list):
            parts.extend(normalize_space(item) for item in value if normalize_space(item))
        elif normalize_space(value):
            parts.append(normalize_space(value))
    return " ".join(parts)


def infer_role(slide: dict[str, Any], item: dict[str, Any], total_slides: int) -> str:
    no = int(item.get("slide_no") or slide.get("slide_no") or 0)
    text = " ".join(
        normalize_space(value).lower()
        for value in [
            item.get("asset_id"),
            item.get("purpose"),
            item.get("reference"),
            slide.get("intent"),
            slide.get("visual_role"),
            slide.get("layout_pattern_id"),
            slide.get("proof_object"),
        ]
    )
    if no == 1 or any(token in text for token in ("cover", "封面", "opening")):
        return "cover"
    if no == total_slides or any(token in text for token in ("closing", "结尾", "收束", "summary")):
        return "closing"
    if any(token in text for token in ("source", "evidence", "citation", "paper", "figure", "资料", "证据", "引用", "原文", "论文", "图表")):
        return "source"
    if any(token in text for token in ("mechanism", "framework", "model", "process", "diagram", "流程", "框架", "模型", "机制")):
        return "diagram"
    if any(token in text for token in ("compare", "comparison", "versus", "before", "after", "对比", "两种")):
        return "comparison"
    if any(token in text for token in ("quote", "breathing", "transition", "金句", "引语", "留白")):
        return "quote"
    return "core"


def subject_visual_context(subject: str, slide: dict[str, Any], item: dict[str, Any]) -> str:
    combined = f"{subject} {slide_text(slide)} {normalize_space(item.get('reference'))}"
    if any(token in combined for token in ("蒲松龄", "聊斋", "志异")):
        return (
            "Qing dynasty Chinese literati world: an inkstone, brush, thread-bound book, "
            "old paper, candle smoke, studio desk, faint strange-tale atmosphere, restrained Chinese ink aesthetics"
        )
    if any(token in combined.lower() for token in ("einstein", "爱因斯坦", "relativity", "相对论")):
        return (
            "early twentieth-century physics world: chalkboard texture without formulas, desk papers without legible text, "
            "warm study light, abstract spacetime curvature suggested by light and shadow"
        )
    if any(token in combined.lower() for token in ("transformer", "attention", "arxiv", "paper", "论文")):
        return (
            "research-paper and machine-learning world: layered attention-like translucent bands, paper texture, "
            "clean laboratory light, no fake equations or fake charts"
        )
    return (
        "topic-specific concrete artifacts, environment, materials, and atmosphere drawn from the source material; "
        "avoid generic business gradients or stock-photo metaphors"
    )


def content_link_for(slide: dict[str, Any], item: dict[str, Any]) -> str:
    existing = normalize_space(item.get("content_link"))
    if existing:
        return existing
    title = slide_title(slide)
    anchors = []
    for key in ("proof_object", "concrete_anchor", "source_anchor", "intent", "visual_role"):
        value = normalize_space(slide.get(key))
        if value and value not in anchors:
            anchors.append(value)
    reference = normalize_space(item.get("reference") or item.get("purpose"))
    if reference and reference not in anchors:
        anchors.append(reference)
    detail = "; ".join(anchors[:3])
    return f"{title} -> {detail}" if title and detail else title or detail


def background_duty_for(role: str, slide: dict[str, Any], item: dict[str, Any]) -> str:
    existing = normalize_space(item.get("background_duty"))
    if existing:
        return existing
    text = " ".join(
        normalize_space(value).lower()
        for value in (role, item.get("visual_type"), slide.get("layout_pattern_id"), slide.get("proof_object"))
    )
    if role == "cover":
        return "establish the deck thesis and emotional entry while leaving strong editable title space"
    if role == "closing":
        return "create synthesis and forward motion behind the final editable claim"
    if role == "diagram" or any(token in text for token in ("diagram", "process", "framework", "mechanism", "模型", "机制", "流程")):
        return "provide quiet material depth behind an editable diagram or process model"
    if role in {"comparison", "source"}:
        return "support the proof or contrast while source evidence and labels stay editable in foreground"
    if role == "quote":
        return "create breathing space and tone for editable quote or transition text"
    return "make the slide's abstract point tangible through a topic-specific object, scene, material, or mood"


def semantic_anchor_for(subject: str, slide: dict[str, Any], item: dict[str, Any]) -> str:
    existing = normalize_space(item.get("semantic_anchor"))
    if existing:
        return existing
    candidates = []
    for value in (
        item.get("reference"),
        slide.get("source_anchor"),
        slide.get("concrete_anchor"),
        slide.get("proof_object"),
        item.get("purpose"),
        subject,
    ):
        cleaned = normalize_space(value)
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return "; ".join(candidates[:4])


def extract_spec_hint(project: Path, slide_number: int) -> str:
    spec_path = project / "spec_lock.json"
    if not spec_path.exists():
        return ""
    try:
        spec = read_json(spec_path)
    except Exception:
        return ""
    contract = spec.get("layout_execution_contract") if isinstance(spec, dict) else None
    entries: list[Any]
    if isinstance(contract, dict):
        entries = list(contract.get("slides") or contract.get("slide_contracts") or contract.values())
    elif isinstance(contract, list):
        entries = contract
    else:
        return ""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_no = entry.get("slide_no") or entry.get("page") or entry.get("slide")
        if str(raw_no) == str(slide_number):
            fields = [
                entry.get("rhythm"),
                entry.get("layout_pattern_id"),
                entry.get("reading_path"),
                entry.get("proof_object"),
                entry.get("component_type"),
            ]
            return "; ".join(normalize_space(field) for field in fields if normalize_space(field))
    return ""


def should_queue_ai_item(item: dict[str, Any], *, pending_only: bool = False) -> bool:
    status = normalize_space(item.get("status"))
    generator = normalize_space(item.get("generator"))
    notes = normalize_space(item.get("notes")).lower()
    if is_source_ai_fallback(item):
        return False
    if status == "Pending":
        return True
    if pending_only:
        return False
    if status == "Generated" and generator == "procedural-preview-fallback":
        return True
    if status == "Generated" and normalize_space(item.get("materialization_mode")) == "procedural-preview-fallback":
        return True
    if status == "Needs-Manual" and "dormant fallback" in notes:
        return False
    return False


def is_source_ai_fallback(item: dict[str, Any]) -> bool:
    asset_id = normalize_space(item.get("asset_id")).lower()
    notes = normalize_space(item.get("notes")).lower()
    return asset_id.endswith("-ai-fallback") or "dormant fallback" in notes or (
        "ai fallback for preview/production while the remote source image remains" in notes
    )


def final_prompt(
    *,
    subject: str,
    slide: dict[str, Any],
    item: dict[str, Any],
    role: str,
    brief: dict[str, str],
    spec_hint: str,
    provider: str,
    model: str,
) -> str:
    title = slide_title(slide)
    text_policy = TEXT_POLICY.get(str(item.get("text_policy") or "none"), TEXT_POLICY["none"])
    visual_context = subject_visual_context(subject, slide, item)
    reference = normalize_space(item.get("reference") or item.get("purpose"))
    size = normalize_space(item.get("image_size") or "2K")
    aspect = normalize_space(item.get("aspect_ratio") or "16:9")
    content_link = content_link_for(slide, item)
    background_duty = background_duty_for(role, slide, item)
    semantic_anchor = semantic_anchor_for(subject, slide, item)
    pieces = [
        f"Create a {aspect} editorial presentation image for slide {item.get('slide_no') or slide.get('slide_no')}: {title}.",
        f"Slide content link: {content_link}.",
        f"Image duty for this page: {background_duty}.",
        f"Semantic anchor: {semantic_anchor}.",
        f"Subject context: {subject}. {visual_context}.",
        f"Slide role: {role}. Image role: {brief['image_role']}.",
        f"Art direction: {brief['art_direction']}.",
        f"Composition: {brief['composition']}.",
        f"Camera and crop: {brief['camera']}.",
        f"Materials and surface: {brief['material']}.",
        f"Lighting: {brief['lighting']}.",
        f"Safe area: {brief['safe_area']}.",
        f"Foreground boundary: {brief['foreground_boundary']}.",
        f"Specific reference to interpret visually, not literally: {reference}.",
    ]
    if spec_hint:
        pieces.append(f"Existing slide layout hint: {spec_hint}.")
    pieces.extend(
        [
            "The generated bitmap is background/supporting art only; all slide text, charts, labels, citations, icons, and diagrams stay editable in SVG/PPTX/HTML foreground.",
            text_policy,
            "Do not create fake screenshots, fake charts, fake equations, fake paper figures, fake UI, fake source documents, or fake evidence.",
            "Avoid generic wallpaper, decorative blobs, random linework, ornamental grids, glowing rails, one-note purple/blue gradients, stock-photo smiles, and layout objects such as boxes, cards, panels, arrows, or placeholder frames.",
            f"Target model path: {provider}/{model}; target size: {size}; output filename: {item.get('filename')}.",
        ]
    )
    return " ".join(part for part in pieces if part)


def queue_markdown(queue: list[dict[str, Any]], provider: str, model: str) -> str:
    lines = [
        "# Image Generation Queue",
        "",
        f"> Provider: {provider}",
        f"> Model: {model}",
        "> Generate or replace these files, then run `import_generated_assets.py` if the files are exported elsewhere.",
        "",
        "---",
        "",
    ]
    for idx, item in enumerate(queue, start=1):
        lines.extend(
            [
                f"## {idx}. Slide {item.get('slide_no')} - {item.get('filename')}",
                "",
                f"- Asset ID: `{item.get('asset_id')}`",
                f"- Save path: `{item.get('path')}`",
                f"- Safe area: {item.get('safe_area')}",
                "",
                "Prompt:",
                "",
                "```text",
                str(item.get("prompt") or ""),
                "```",
                "",
                "Negative prompt:",
                "",
                "```text",
                str(item.get("negative_prompt") or ""),
                "```",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_direction(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.resolve()
    slide_plan_path = args.slide_plan or project / "slide_plan.json"
    manifest_path = args.manifest or project / "visual_asset_manifest.json"
    if not slide_plan_path.exists():
        raise SystemExit(f"slide_plan not found: {slide_plan_path}")
    if not manifest_path.exists():
        raise SystemExit(f"visual_asset_manifest not found: {manifest_path}")

    slides = load_slides(slide_plan_path)
    slides_by_no = {slide_no(slide, idx): slide for idx, slide in enumerate(slides, start=1)}
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise SystemExit("visual_asset_manifest.json must be an object")
    items = manifest.get("items")
    if not isinstance(items, list):
        raise SystemExit("visual_asset_manifest.json needs items")
    subject = normalize_space(args.subject or manifest.get("subject") or project.name)
    generated_at = utc_now()

    direction_items: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []
    updated_ai_items = 0
    skipped_source_fallbacks = 0
    total_slides = len(slides)
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict) or item.get("acquire_via") != "ai":
            continue
        if is_source_ai_fallback(item):
            skipped_source_fallbacks += 1
            item["generation_policy"] = "preview_fallback_only"
            item["generation_queue_status"] = "skipped_source_visual_fallback"
            continue
        if not should_queue_ai_item(item, pending_only=args.pending_only):
            continue
        no = int(item.get("slide_no") or min(idx, max(1, total_slides)))
        slide = slides_by_no.get(no) or (slides[min(idx - 1, total_slides - 1)] if slides else {})
        role = infer_role(slide, item, total_slides)
        role_brief = dict(ROLE_BRIEFS.get(role, ROLE_BRIEFS["core"]))
        spec_hint = extract_spec_hint(project, no)
        prompt = final_prompt(
            subject=subject,
            slide=slide,
            item=item,
            role=role,
            brief=role_brief,
            spec_hint=spec_hint,
            provider=args.provider,
            model=args.model,
        )
        quality_rubric = [
            "contains one topic-specific visual subject, not generic decoration",
            "visibly supports the slide content_link and semantic_anchor",
            "keeps declared safe area quiet enough for editable foreground text",
            "contains no visible text, logos, UI, fake charts, fake documents, or fake evidence",
            "does not bake slide layout containers, arrows, labels, charts, or data into the bitmap",
            "works at 16:9 crop and can be replaced without changing slide copy",
        ]
        art_brief = {
            "slide_no": no,
            "slide_title": slide_title(slide),
            "slide_role": role,
            "asset_id": str(item.get("asset_id") or ""),
            "filename": str(item.get("filename") or ""),
            "path": str(item.get("path") or ""),
            "image_role": role_brief["image_role"],
            "content_link": content_link_for(slide, item),
            "background_duty": background_duty_for(role, slide, item),
            "semantic_anchor": semantic_anchor_for(subject, slide, item),
            "art_direction": role_brief["art_direction"],
            "composition": role_brief["composition"],
            "camera": role_brief["camera"],
            "material": role_brief["material"],
            "lighting": role_brief["lighting"],
            "safe_area": role_brief["safe_area"],
            "foreground_boundary": role_brief["foreground_boundary"],
            "crop_policy": "16:9, keep the subject away from declared text-safe region; no important detail at extreme edges",
            "text_policy": TEXT_POLICY.get(str(item.get("text_policy") or "none"), TEXT_POLICY["none"]),
            "negative_prompt": NEGATIVE_PROMPT,
            "quality_rubric": quality_rubric,
            "editable_foreground_policy": "All semantic slide content remains editable in PPTX/SVG/HTML foreground layers.",
            "spec_hint": spec_hint,
        }
        item["art_direction_brief"] = art_brief
        item["prompt"] = prompt
        item["prompt_v2"] = prompt
        item["negative_prompt"] = NEGATIVE_PROMPT
        item["content_link"] = art_brief["content_link"]
        item["background_duty"] = art_brief["background_duty"]
        item["semantic_anchor"] = art_brief["semantic_anchor"]
        item["safe_area"] = role_brief["safe_area"]
        item["foreground_boundary"] = role_brief["foreground_boundary"]
        item["generation_slot"] = {
            "provider": args.provider,
            "model": args.model,
            "size": normalize_space(item.get("image_size") or "2K"),
            "aspect_ratio": normalize_space(item.get("aspect_ratio") or "16:9"),
            "save_path": str(item.get("path") or ""),
        }
        item["quality_rubric"] = quality_rubric
        updated_ai_items += 1
        direction_items.append(art_brief)
        queue.append(
            {
                "asset_id": item.get("asset_id"),
                "slide_no": no,
                "filename": item.get("filename"),
                "path": item.get("path"),
                "provider": args.provider,
                "model": args.model,
                "size": item.get("image_size", "2K"),
                "aspect_ratio": item.get("aspect_ratio", "16:9"),
                "page_role": item.get("page_role") or "",
                "asset_role": item.get("asset_role") or "",
                "visual_type": item.get("visual_type") or "",
                "text_policy": item.get("text_policy") or "none",
                "prompt": prompt,
                "negative_prompt": NEGATIVE_PROMPT,
                "safe_area": role_brief["safe_area"],
                "content_link": art_brief["content_link"],
                "background_duty": art_brief["background_duty"],
                "semantic_anchor": art_brief["semantic_anchor"],
                "generation_policy": "real_image_generation",
                "import_hint": (
                    "Save the generated image at this path, or place external outputs in a folder and run "
                    "`import_generated_assets.py <project> <folder> --generator <name>`."
                ),
            }
        )

    manifest["image_art_direction"] = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "provider": args.provider,
        "model": args.model,
        "items": len(direction_items),
    }
    write_json(manifest_path, manifest)

    output = args.output or project / "image_art_direction.json"
    payload = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "project": project.name,
        "subject": subject,
        "provider": args.provider,
        "model": args.model,
        "skipped_source_fallbacks": skipped_source_fallbacks,
        "items": direction_items,
    }
    write_json(output, payload)

    queue_path = project / "assets" / "images" / "image_generation_queue.json"
    queue_md_path = project / "assets" / "images" / "image_generation_queue.md"
    write_json(
        queue_path,
        {
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "project": project.name,
            "provider": args.provider,
            "model": args.model,
            "skipped_source_fallbacks": skipped_source_fallbacks,
            "items": queue,
        },
    )
    queue_md_path.write_text(queue_markdown(queue, args.provider, args.model), encoding="utf-8")

    if args.update_prompts:
        prompt_manifest = vam.ai_prompt_manifest(manifest)
        prompts_path = project / "assets" / "images" / "image_prompts.json"
        write_json(prompts_path, prompt_manifest)
        prompts_path.with_suffix(".md").write_text(vam.render_prompts_markdown(prompt_manifest), encoding="utf-8")

    return {
        "ok": True,
        "items": len(direction_items),
        "updated_ai_items": updated_ai_items,
        "skipped_source_fallbacks": skipped_source_fallbacks,
        "outputs": {
            "image_art_direction": str(output),
            "image_generation_queue": str(queue_path),
            "image_generation_queue_md": str(queue_md_path),
            "visual_asset_manifest": str(manifest_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Prepared qiaomu-ppt project directory.")
    parser.add_argument("--manifest", type=Path, help="visual_asset_manifest.json path.")
    parser.add_argument("--slide-plan", type=Path, help="slide_plan.json path.")
    parser.add_argument("--subject", default="", help="Deck subject override.")
    parser.add_argument("--provider", default="gpt-image-2", help="Image generation provider label.")
    parser.add_argument("--model", default="gpt-image-2", help="Image generation model label.")
    parser.add_argument("--output", type=Path, help="Output image_art_direction.json path.")
    parser.add_argument("--update-prompts", action="store_true", help="Rewrite image_prompts.json/md with the upgraded prompts.")
    parser.add_argument("--pending-only", action="store_true", help="Only queue Pending AI rows. By default procedural-preview-fallback Generated rows are queued for real replacement.")
    args = parser.parse_args()
    result = build_direction(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
