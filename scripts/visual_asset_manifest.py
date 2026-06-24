#!/usr/bin/env python3
"""Build and validate qiaomu-ppt visual asset acquisition manifests."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_TAXONOMY = DATA_DIR / "visual_asset_acquisition_taxonomy.json"

ACQUIRE_INITIAL_STATUS = {
    "ai": "Pending",
    "web": "Pending",
    "user": "Existing",
    "source": "Existing",
    "formula": "Rendered",
    "placeholder": "Placeholder",
}
TERMINAL_STATUS = {
    "ai": {"Generated", "Needs-Manual", "Missing", "Failed"},
    "web": {"Sourced", "Needs-Manual", "Missing", "Failed"},
    "user": {"Existing", "Needs-Manual", "Missing"},
    "source": {"Existing", "Needs-Manual", "Missing"},
    "formula": {"Rendered", "Needs-Manual", "Missing"},
    "placeholder": {"Placeholder", "Needs-Manual", "Missing"},
}
NON_FILE_STATUSES = {"Pending", "Placeholder", "Needs-Manual", "Missing", "Failed"}
TEXT_POLICY_CUES = {
    "none": "NO text of any kind anywhere in the image: no letters, numbers, words, signs, labels, captions, watermarks, UI text, or written symbols.",
    "embedded": "Only stable image-owned lettering may appear. Never bake slide title, body copy, citations, captions, data values, or editable page text into the image.",
}
HEX_TEXT_RULE = (
    "Color values and color names are rendering guidance only; do not display HEX codes, "
    "palette labels, or color names as visible text anywhere in the image."
)
NO_BRAND_RULE = (
    "Do not depict identifiable brand logos, trademarks, or real product likenesses unless "
    "the asset reference explicitly names a user-owned source image."
)
NO_FAKE_EVIDENCE_RULE = (
    "Do not create fake screenshots, fake charts, fake paper figures, fake UI, or fake evidence."
)
NO_GENERIC_WALLPAPER_RULE = (
    "Do not create generic wallpaper, random decorative lines, ornamental grids, glowing rails, "
    "abstract polygons, or style-only background texture. The image must support the slide content."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "asset"


def load_taxonomy(path: Path = DEFAULT_TAXONOMY) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"taxonomy must be a JSON object: {path}")
    return payload


def rows_from_file(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("items") or payload.get("assets") or payload.get("rows") or []
    else:
        rows = []
    if not isinstance(rows, list):
        raise SystemExit(f"rows file must contain a list or an object with items/assets/rows: {path}")
    normalized: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise SystemExit(f"row {idx} in {path} must be an object")
        normalized.append(row)
    return normalized


def default_rows(subject: str) -> list[dict[str, Any]]:
    return [
        {
            "asset_id": "cover_atmosphere",
            "filename": "cover_atmosphere.png",
            "slide_no": 1,
            "purpose": "Cover atmosphere image",
            "asset_role": "background",
            "acquire_via": "ai",
            "page_role": "hero_page",
            "hero_primitive": "atmospheric",
            "text_policy": "none",
            "aspect_ratio": "16:9",
            "image_size": "2K",
            "reference": f"Quiet opening atmosphere for {subject}; calm center or upper field for editable title overlay.",
        },
        {
            "asset_id": "dark_evidence",
            "filename": "dark_evidence.png",
            "purpose": "Dark evidence atmosphere image",
            "asset_role": "background",
            "acquire_via": "ai",
            "page_role": "hero_page",
            "hero_primitive": "atmospheric",
            "text_policy": "none",
            "aspect_ratio": "16:9",
            "image_size": "2K",
            "reference": f"Dark restrained evidence background for {subject}; low-noise field behind editable charts and numbers.",
        },
        {
            "asset_id": "light_evidence",
            "filename": "light_evidence.png",
            "purpose": "Light dense-evidence atmosphere image",
            "asset_role": "background",
            "acquire_via": "ai",
            "page_role": "hero_page",
            "hero_primitive": "atmospheric",
            "text_policy": "none",
            "aspect_ratio": "16:9",
            "image_size": "2K",
            "reference": f"Light quiet evidence background for dense readable slides about {subject}.",
        },
        {
            "asset_id": "diagram_focus",
            "filename": "diagram_focus.png",
            "purpose": "Diagram/process focus atmosphere image",
            "asset_role": "background",
            "acquire_via": "ai",
            "page_role": "hero_page",
            "hero_primitive": "atmospheric",
            "text_policy": "none",
            "aspect_ratio": "16:9",
            "image_size": "2K",
            "reference": f"Neutral diagram-focus atmosphere for architecture, process, or framework slides about {subject}.",
        },
        {
            "asset_id": "closing_atmosphere",
            "filename": "closing_atmosphere.png",
            "purpose": "Closing atmosphere image",
            "asset_role": "background",
            "acquire_via": "ai",
            "page_role": "hero_page",
            "hero_primitive": "atmospheric",
            "text_policy": "none",
            "aspect_ratio": "16:9",
            "image_size": "2K",
            "reference": f"Quiet closing atmosphere for {subject}; a sense of completion and forward motion.",
        },
    ]


def infer_page_role(row: dict[str, Any]) -> str:
    if row.get("page_role"):
        return str(row["page_role"])
    role = str(row.get("asset_role") or "").lower()
    purpose = str(row.get("purpose") or "").lower()
    if role in {"background", "cover_art", "chapter_art", "closing_art"}:
        return "hero_page"
    if any(token in purpose for token in ("cover", "chapter", "closing", "封面", "章节", "结尾")):
        return "hero_page"
    return "local"


def infer_visual_type(row: dict[str, Any], page_role: str) -> str:
    if page_role == "hero_page":
        return ""
    if row.get("visual_type"):
        return str(row["visual_type"])
    text = " ".join(str(row.get(key) or "").lower() for key in ("purpose", "reference", "asset_role"))
    mapping = [
        (("timeline", "history", "milestone", "时间线", "历程"), "timeline"),
        (("process", "workflow", "step", "流程", "步骤"), "flowchart"),
        (("matrix", "2x2", "quadrant", "矩阵"), "matrix"),
        (("cycle", "loop", "flywheel", "循环", "闭环"), "cycle"),
        (("funnel", "漏斗"), "funnel"),
        (("pyramid", "金字塔"), "pyramid"),
        (("compare", "comparison", "before", "after", "对比"), "comparison"),
        (("map", "地图", "路线"), "map"),
        (("portrait", "headshot", "人物", "肖像"), "portrait"),
        (("screenshot", "ui", "界面", "截图"), "screenshot_context"),
        (("texture", "paper", "grain", "纹理"), "texture"),
        (("object", "cutaway", "product", "物体", "产品"), "object"),
        (("framework", "model", "method", "框架", "模型"), "framework"),
    ]
    for tokens, visual_type in mapping:
        if any(token in text for token in tokens):
            return visual_type
    return "scene"


def infer_hero_primitive(row: dict[str, Any]) -> str:
    if row.get("hero_primitive"):
        return str(row["hero_primitive"])
    text = " ".join(str(row.get(key) or "").lower() for key in ("purpose", "reference", "asset_role"))
    if any(token in text for token in ("portrait", "人物", "肖像", "founder", "ceo")):
        return "portrait"
    if any(token in text for token in ("typographic", "big number", "大字", "数字", "wordmark")):
        return "typographic"
    if any(token in text for token in ("product", "object", "hero", "symbol", "物体", "产品")):
        return "single_subject"
    return "atmospheric"


def default_alt_text(row: dict[str, Any]) -> str:
    reference = str(row.get("reference") or row.get("purpose") or row.get("asset_id") or "visual asset")
    reference = re.sub(r"\s+", " ", reference).strip()
    return reference[:160]


def rendering_text(taxonomy: dict[str, Any], rendering: str) -> str:
    renderings = taxonomy.get("ai_renderings", {})
    if isinstance(renderings, dict) and rendering in renderings:
        return str(renderings[rendering])
    return str(renderings.get("editorial") or "Editorial presentation image with controlled composition and clear hierarchy.")


def palette_text(taxonomy: dict[str, Any], palette: str) -> str:
    palettes = taxonomy.get("ai_palette_behaviors", {})
    if isinstance(palettes, dict) and palette in palettes:
        return str(palettes[palette])
    return str(palettes.get("cool-corporate") or "Use the deck colors with restrained hierarchy and one accent.")


def composition_text(taxonomy: dict[str, Any], row: dict[str, Any], page_role: str, visual_type: str, hero_primitive: str) -> str:
    if page_role == "hero_page":
        primitives = taxonomy.get("hero_primitives", {})
        primitive_text = primitives.get(hero_primitive, primitives.get("atmospheric", "Quiet hero composition."))
        overlay = str(row.get("overlay_reservation") or "").strip()
        if overlay:
            return f"Hero-page composition: {primitive_text} Overlay reservation: {overlay}."
        return f"Hero-page composition: {primitive_text}"
    return (
        f"Local visual type: {visual_type}. The image fills its declared region as a self-contained visual block; "
        "do not reserve arbitrary slide-title overlay space inside the image."
    )


def build_prompt(
    taxonomy: dict[str, Any],
    row: dict[str, Any],
    rendering: str,
    palette: str,
    colors: dict[str, str],
) -> str:
    page_role = str(row["page_role"])
    visual_type = str(row.get("visual_type") or "")
    hero_primitive = str(row.get("hero_primitive") or "")
    text_policy = str(row.get("text_policy") or "none")
    reference = str(row.get("reference") or row.get("purpose") or row.get("asset_id") or "visual asset").strip()
    subject = str(row.get("subject") or reference)
    content_link = str(row.get("content_link") or "").strip()
    background_duty = str(row.get("background_duty") or "").strip()
    semantic_anchor = str(row.get("semantic_anchor") or "").strip()
    color_sentence = (
        f"Apply deck colors as rendering guidance: primary {colors['primary']}, "
        f"secondary/background {colors['secondary']}, accent {colors['accent']}."
    )
    container = (
        f"Composed as a {row.get('aspect_ratio', '16:9')} image for {page_role} use, "
        f"target size {row.get('image_size', '1K')}, saved as {row.get('filename')}."
    )
    human_rule = ""
    if re.search(r"person|people|human|portrait|founder|ceo|人物|人像|肖像|团队", reference, flags=re.IGNORECASE):
        if rendering == "corporate-photo":
            human_rule = "If people appear, use editorial photography style with natural composition and professional subjects."
        else:
            human_rule = "If people appear, render them as simplified stylized silhouettes or symbolic figures, with no photorealistic faces or celebrity likeness."
    prompt = " ".join(
        part.strip()
        for part in [
            rendering_text(taxonomy, rendering),
            palette_text(taxonomy, palette),
            color_sentence,
            f"Slide content link: {content_link}." if content_link else "",
            f"Image duty for this page: {background_duty}." if background_duty else "",
            f"Semantic anchor: {semantic_anchor}." if semantic_anchor else "",
            composition_text(taxonomy, row, page_role, visual_type, hero_primitive),
            f"Specific subject: {subject}.",
            container,
            TEXT_POLICY_CUES.get(text_policy, TEXT_POLICY_CUES["none"]),
            human_rule,
            HEX_TEXT_RULE,
            NO_BRAND_RULE,
            NO_FAKE_EVIDENCE_RULE,
            NO_GENERIC_WALLPAPER_RULE,
        ]
        if part and part.strip()
    )
    return prompt


def normalize_item(
    taxonomy: dict[str, Any],
    raw: dict[str, Any],
    idx: int,
    args: argparse.Namespace,
    assets_dir: str,
) -> dict[str, Any]:
    acquire_via = str(raw.get("acquire_via") or raw.get("source") or "ai").strip().lower()
    if acquire_via not in ACQUIRE_INITIAL_STATUS:
        raise SystemExit(f"asset row {idx} has unsupported acquire_via: {acquire_via}")
    asset_id = str(raw.get("asset_id") or raw.get("id") or slugify(raw.get("purpose") or f"asset-{idx}"))
    filename = str(raw.get("filename") or f"{slugify(asset_id)}.png")
    path = str(raw.get("path") or f"{assets_dir.rstrip('/')}/{filename}")
    page_role = infer_page_role(raw)
    text_policy = str(raw.get("text_policy") or "none")
    if text_policy not in {"none", "embedded"}:
        raise SystemExit(f"asset row {idx} has unsupported text_policy: {text_policy}")
    visual_type = infer_visual_type(raw, page_role)
    hero_primitive = infer_hero_primitive(raw) if page_role == "hero_page" else ""
    item: dict[str, Any] = {
        "asset_id": asset_id,
        "filename": filename,
        "path": path,
        "slide_no": raw.get("slide_no") or raw.get("page") or raw.get("slide"),
        "allowed_pages": raw.get("allowed_pages") or ([] if raw.get("slide_no") else []),
        "purpose": str(raw.get("purpose") or raw.get("reference") or asset_id),
        "asset_role": str(raw.get("asset_role") or "concept_metaphor"),
        "acquire_via": acquire_via,
        "status": str(raw.get("status") or ACQUIRE_INITIAL_STATUS[acquire_via]),
        "reference": str(raw.get("reference") or raw.get("purpose") or asset_id),
        "page_role": page_role,
        "text_policy": text_policy,
        "aspect_ratio": str(raw.get("aspect_ratio") or "16:9"),
        "image_size": str(raw.get("image_size") or ("2K" if page_role == "hero_page" else "1K")),
        "visual_type": visual_type,
        "hero_primitive": hero_primitive,
        "editable_policy": str(
            raw.get("editable_policy")
            or "All page titles, body copy, captions, data values, citations, charts, and layout objects stay editable in foreground SVG/PPT/HTML."
        ),
        "content_link": str(raw.get("content_link") or ""),
        "background_duty": str(raw.get("background_duty") or ""),
        "semantic_anchor": str(raw.get("semantic_anchor") or ""),
        "source_card_ids": raw.get("source_card_ids") or [],
        "notes": str(raw.get("notes") or ""),
        "alt_text": str(raw.get("alt_text") or default_alt_text(raw)),
    }
    if acquire_via == "ai":
        item["prompt"] = str(raw.get("prompt") or build_prompt(taxonomy, item, args.rendering, args.palette, {
            "primary": args.primary,
            "secondary": args.secondary,
            "accent": args.accent,
        }))
    if acquire_via == "web":
        item["search_intent"] = str(raw.get("search_intent") or raw.get("reference") or raw.get("purpose") or asset_id)
        item["license_tier"] = str(raw.get("license_tier") or "")
        item["attribution_required"] = bool(raw.get("attribution_required", False))
        item["attribution_text"] = str(raw.get("attribution_text") or "")
        item["source_page_url"] = str(raw.get("source_page_url") or "")
    if acquire_via in {"source", "user"}:
        for field in ("source_id", "source_image_id", "source_page_url", "source_path", "source_page", "rights_notes"):
            if raw.get(field):
                item[field] = raw.get(field)
    return item


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    taxonomy = load_taxonomy(args.taxonomy)
    rows = rows_from_file(args.rows) if args.rows else default_rows(args.subject)
    assets_dir = args.assets_dir.strip("/")
    items = [
        normalize_item(taxonomy, row, idx, args, assets_dir)
        for idx, row in enumerate(rows, start=1)
    ]
    status_summary: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "")
        status_summary[status] = status_summary.get(status, 0) + 1
    return {
        "schema_version": "1.0.0",
        "generated_at": utc_now(),
        "project": Path(args.project).name,
        "subject": args.subject,
        "route": args.route,
        "deck_image_model": {
            "image_rendering": args.rendering,
            "image_palette_behavior": args.palette,
            "color_scheme": {
                "primary": args.primary,
                "secondary": args.secondary,
                "accent": args.accent,
            },
            "generation_paths": {
                "path_a": "configured API backend, when available",
                "path_b": "host-native image generation, such as Codex built-in image generation, when available",
                "path_c": "offline manual mode with prompts and Needs-Manual statuses",
            },
        },
        "status_policy": {
            "generated_requires_file": True,
            "pending_allowed_only_before_acquisition": True,
            "needs_manual_is_terminal_gap": True,
        },
        "status_summary": status_summary,
        "items": items,
    }


def ai_prompt_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    model = manifest.get("deck_image_model", {})
    items = []
    for item in manifest.get("items", []):
        if item.get("acquire_via") != "ai":
            continue
        prompt_item = {
            "filename": item["filename"],
            "purpose": item["purpose"],
            "page_role": item["page_role"],
            "text_policy": item["text_policy"],
            "aspect_ratio": item["aspect_ratio"],
            "image_size": item.get("image_size", "1K"),
            "content_link": item.get("content_link", ""),
            "background_duty": item.get("background_duty", ""),
            "semantic_anchor": item.get("semantic_anchor", ""),
            "prompt": item.get("prompt", ""),
            "alt_text": item.get("alt_text", ""),
            "status": item.get("status", "Pending"),
        }
        if item.get("page_role") == "local" and item.get("visual_type"):
            prompt_item["type"] = item["visual_type"]
        if item.get("page_role") == "hero_page" and item.get("hero_primitive"):
            prompt_item["hero_primitive"] = item["hero_primitive"]
        items.append(prompt_item)
    return {
        "schema_version": "1.0.0",
        "project": manifest.get("project", ""),
        "generated_at": manifest.get("generated_at", utc_now()),
        "deck_rendering": model.get("image_rendering", ""),
        "deck_palette": model.get("image_palette_behavior", ""),
        "color_scheme": model.get("color_scheme", {}),
        "items": items,
    }


def render_prompts_markdown(prompt_manifest: dict[str, Any]) -> str:
    lines = [
        "# Image Generation Prompts",
        "",
        "> Generated from `image_prompts.json` by `visual_asset_manifest.py render-md`.",
        "> Do not hand-edit prompts here; update the JSON manifest and re-render.",
        "",
        f"> Project: {prompt_manifest.get('project', '')}",
        f"> Generated: {prompt_manifest.get('generated_at', '')}",
        f"> Deck rendering: {prompt_manifest.get('deck_rendering', '')}",
        f"> Deck palette: {prompt_manifest.get('deck_palette', '')}",
        "",
        "---",
        "",
    ]
    for idx, item in enumerate(prompt_manifest.get("items", []), start=1):
        lines.extend(
            [
                f"### Image {idx}: {item.get('filename', '')}",
                "",
                "| Attribute | Value |",
                "|---|---|",
                f"| Purpose | {item.get('purpose', '')} |",
                f"| Content link | {item.get('content_link', '')} |",
                f"| Background duty | {item.get('background_duty', '')} |",
                f"| Semantic anchor | {item.get('semantic_anchor', '')} |",
                f"| Page role | {item.get('page_role', '')} |",
                f"| Text policy | {item.get('text_policy', '')} |",
                f"| Type | {item.get('type') or item.get('hero_primitive') or ''} |",
                f"| Aspect ratio | {item.get('aspect_ratio', '')} |",
                f"| Image size | {item.get('image_size', '')} |",
                f"| Status | {item.get('status', '')} |",
                "",
                "**Prompt**:",
                "",
                str(item.get("prompt") or ""),
                "",
            ]
        )
        alt = item.get("alt_text")
        if alt:
            lines.extend(["**Alt Text**:", "", f"> {alt}", ""])
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_init(args: argparse.Namespace) -> int:
    manifest = build_manifest(args)
    project = Path(args.project)
    output = Path(args.output) if args.output else project / "visual_asset_manifest.json"
    write_json(output, manifest)

    prompts = ai_prompt_manifest(manifest)
    prompts_path = project / args.assets_dir.strip("/") / "image_prompts.json"
    if prompts["items"]:
        write_json(prompts_path, prompts)
        prompts_md = prompts_path.with_suffix(".md")
        prompts_md.write_text(render_prompts_markdown(prompts), encoding="utf-8")
    print(json.dumps({"visual_asset_manifest": str(output), "image_prompts": str(prompts_path) if prompts["items"] else ""}, ensure_ascii=False, indent=2))
    return 0


def command_render_md(args: argparse.Namespace) -> int:
    prompt_manifest = load_json(Path(args.prompts))
    rendered = render_prompts_markdown(prompt_manifest)
    output = Path(args.output) if args.output else Path(args.prompts).with_suffix(".md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(str(output))
    return 0


def validate_manifest(path: Path, project: Path | None, require_terminal: bool) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    try:
        manifest = load_json(path)
    except Exception as exc:
        return [f"invalid visual asset manifest: {exc}"], warnings
    if not isinstance(manifest, dict):
        return ["visual asset manifest must be a JSON object"], warnings
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        failures.append("visual asset manifest needs a non-empty items list")
        return failures, warnings
    model = manifest.get("deck_image_model")
    if not isinstance(model, dict):
        failures.append("visual asset manifest missing deck_image_model")
    else:
        for field in ("image_rendering", "image_palette_behavior", "color_scheme"):
            if not model.get(field):
                failures.append(f"deck_image_model missing {field}")
    ai_count = 0
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            failures.append(f"asset item {idx} must be an object")
            continue
        for field in ("asset_id", "filename", "path", "purpose", "asset_role", "acquire_via", "status", "reference", "page_role", "text_policy", "aspect_ratio", "editable_policy"):
            if not item.get(field):
                failures.append(f"asset item {idx} missing {field}")
        acquire_via = str(item.get("acquire_via") or "")
        status = str(item.get("status") or "")
        if acquire_via not in ACQUIRE_INITIAL_STATUS:
            failures.append(f"asset item {idx} has unsupported acquire_via: {acquire_via}")
            continue
        allowed_statuses = TERMINAL_STATUS[acquire_via] | {"Pending"}
        if status not in allowed_statuses:
            failures.append(f"asset item {idx} has invalid status `{status}` for acquire_via `{acquire_via}`")
        if require_terminal and status == "Pending":
            failures.append(f"asset item {idx} remains Pending")
        if acquire_via == "ai":
            ai_count += 1
            prompt = str(item.get("prompt") or "")
            for field in ("content_link", "background_duty", "semantic_anchor"):
                if not str(item.get(field) or "").strip():
                    warnings.append(f"AI asset item {idx} missing {field}; prompt may drift into generic wallpaper")
            if not prompt:
                failures.append(f"AI asset item {idx} missing prompt")
            elif len(prompt.split()) < 35:
                warnings.append(f"AI asset item {idx} prompt may be too short to encode rendering/palette/composition/hard rules")
            if "," in prompt and len(prompt.split()) < 25:
                warnings.append(f"AI asset item {idx} looks like tag-soup; use a coherent paragraph")
            if item.get("page_role") == "local" and not item.get("visual_type"):
                failures.append(f"AI local asset item {idx} missing visual_type")
            if item.get("page_role") == "hero_page" and not item.get("hero_primitive"):
                warnings.append(f"AI hero_page asset item {idx} should declare hero_primitive")
        if acquire_via == "web":
            if status == "Sourced" and not item.get("license_tier"):
                failures.append(f"web asset item {idx} is Sourced but missing license_tier")
        if project and status not in NON_FILE_STATUSES:
            asset_path = project / str(item.get("path") or "")
            if not asset_path.exists():
                failures.append(f"asset item {idx} status `{status}` requires file: {asset_path}")
    if ai_count:
        base = project or path.parent
        prompts_path = base / "assets" / "images" / "image_prompts.json"
        if not prompts_path.exists():
            warnings.append("AI assets exist but assets/images/image_prompts.json was not found at the default path")
    return failures, warnings


def command_validate(args: argparse.Namespace) -> int:
    failures, warnings = validate_manifest(Path(args.manifest), Path(args.project) if args.project else None, args.require_terminal)
    result = {"ok": not failures, "failures": failures, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


def add_common_init_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True, help="Project directory where artifacts should be written.")
    parser.add_argument("--subject", required=True, help="Deck subject.")
    parser.add_argument("--route", default="talk_deck", help="qiaomu-ppt route.")
    parser.add_argument("--rows", type=Path, help="JSON file with visual asset rows. Defaults to a five-item AI background pack.")
    parser.add_argument("--output", help="Output visual_asset_manifest.json path. Defaults to <project>/visual_asset_manifest.json.")
    parser.add_argument("--assets-dir", default="assets/images", help="Project-relative image asset directory.")
    parser.add_argument("--rendering", default="editorial", help="Deck-wide AI image rendering family.")
    parser.add_argument("--palette", default="cool-corporate", help="Deck-wide image palette behavior.")
    parser.add_argument("--primary", default="#1E3A5F", help="Primary deck color.")
    parser.add_argument("--secondary", default="#F8F9FA", help="Secondary/background deck color.")
    parser.add_argument("--accent", default="#D4AF37", help="Accent deck color.")
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY, help="Visual asset acquisition taxonomy JSON.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate qiaomu-ppt visual asset acquisition manifests.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create visual_asset_manifest.json and image_prompts sidecars.")
    add_common_init_args(init_parser)
    init_parser.set_defaults(func=command_init)

    render_parser = subparsers.add_parser("render-md", help="Render image_prompts.md from image_prompts.json.")
    render_parser.add_argument("--prompts", required=True, help="Path to image_prompts.json.")
    render_parser.add_argument("--output", "-o", help="Output Markdown path. Defaults to image_prompts.md.")
    render_parser.set_defaults(func=command_render_md)

    validate_parser = subparsers.add_parser("validate", help="Validate visual_asset_manifest.json.")
    validate_parser.add_argument("--manifest", required=True, help="Path to visual_asset_manifest.json.")
    validate_parser.add_argument("--project", help="Project directory for file-existence checks.")
    validate_parser.add_argument("--require-terminal", action="store_true", help="Fail if any row remains Pending.")
    validate_parser.set_defaults(func=command_validate)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
