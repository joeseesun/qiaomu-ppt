#!/usr/bin/env python3
"""Plan visual asset acquisition rows from a qiaomu-ppt slide plan.

This script is intentionally conservative: it does not fetch or generate
images. It turns slide intent into an actionable asset queue that
visual_asset_manifest.py can normalize, prompt, and validate.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


WEAK_SOURCE_IMAGE_TOKENS = {
    "centralautologin",
    "commons-logo",
    "copyright",
    "disambig",
    "edit-ltr",
    "footer",
    "icon_edit",
    "lock-blue",
    "mediawiki",
    "oojs_ui_icon",
    "powered by",
    "scholia_logo",
    "speaker_icon",
    "static/images",
    "tagline",
    "the free encyclopedia",
    "wikimedia foundation",
    "wikipedia-wordmark",
    "wikisource-logo",
    "wikiquote-logo",
    "wordmark",
    "需注册账号查阅",
    "自由的百科全书",
    "维基百科",
    "[icon]",
}

REAL_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".tif", ".tiff")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_slides(plan: Any) -> list[dict[str, Any]]:
    if isinstance(plan, dict):
        slides = plan.get("slides") or plan.get("slide_plan") or []
    elif isinstance(plan, list):
        slides = plan
    else:
        slides = []
    return [slide for slide in slides if isinstance(slide, dict)]


def slide_no(slide: dict[str, Any], fallback: int) -> int:
    for key in ("slide_no", "page", "number"):
        try:
            value = int(slide.get(key))
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return fallback


def title_of(slide: dict[str, Any]) -> str:
    return str(slide.get("claim_title") or slide.get("title") or "").strip()


def role_of(slide: dict[str, Any]) -> str:
    component = slide.get("component_plan")
    if isinstance(component, dict) and component.get("component_type"):
        return str(component["component_type"]).strip()
    return str(slide.get("visual_role") or slide.get("proof_object") or "").strip()


def text_blob(slide: dict[str, Any]) -> str:
    parts = [title_of(slide)]
    for key in ("source_anchor", "concrete_anchor", "speaker_note_goal", "media_need", "visual_role"):
        if slide.get(key):
            parts.append(str(slide[key]))
    points = slide.get("content_points") or []
    if isinstance(points, list):
        parts.extend(str(item) for item in points)
    elif points:
        parts.append(str(points))
    return " ".join(parts)


def topic_terms(*values: Any) -> set[str]:
    text = " ".join(str(value or "") for value in values)
    cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    latin_terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
    stop = {
        "wikipedia",
        "free",
        "encyclopedia",
        "slide",
        "source",
        "image",
        "topic",
        "deck",
        "the",
        "and",
        "for",
        "with",
        "维基百科",
        "自由的百科全书",
    }
    terms: set[str] = set()
    for term in [*cjk_terms, *latin_terms]:
        cleaned = term.strip().lower()
        if cleaned and cleaned not in stop:
            terms.add(cleaned)
    return terms


def slugify(value: str, fallback: str = "asset") -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:48] or fallback


def source_cards_by_id(project: Path) -> dict[str, dict[str, Any]]:
    path = project / "sources" / "source_cards.json"
    if not path.exists():
        return {}
    payload = load_json(path)
    cards = payload.get("cards") if isinstance(payload, dict) else []
    return {str(card.get("id")): card for card in cards if isinstance(card, dict) and card.get("id")}


def source_ids_for_slide(slide: dict[str, Any], cards: dict[str, dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    card_ids = slide.get("source_card_ids") or []
    if isinstance(card_ids, str):
        card_ids = [card_ids]
    if isinstance(card_ids, list):
        for card_id in card_ids:
            card = cards.get(str(card_id))
            if not isinstance(card, dict):
                continue
            source_ids = card.get("source_ids") or []
            if isinstance(source_ids, str):
                source_ids = [source_ids]
            for source_id in source_ids:
                value = str(source_id).strip()
                if value and value not in ids:
                    ids.append(value)
    return ids


def image_candidates(project: Path) -> list[dict[str, Any]]:
    cards_path = project / "sources" / "source_cards.json"
    if cards_path.exists():
        payload = load_json(cards_path)
        candidates = payload.get("image_candidates") if isinstance(payload, dict) else []
        if isinstance(candidates, list) and candidates:
            return [item for item in candidates if isinstance(item, dict)]
    manifest_path = project / "sources" / "source_manifest.json"
    if not manifest_path.exists():
        return []
    manifest = load_json(manifest_path)
    out: list[dict[str, Any]] = []
    for source in manifest.get("sources", []) if isinstance(manifest, dict) else []:
        if not isinstance(source, dict):
            continue
        sid = str(source.get("source_id") or source.get("title") or "source")
        for idx, image in enumerate(source.get("images") or [], start=1):
            if isinstance(image, dict):
                out.append(
                    {
                        "id": f"img-{sid}-{idx:02d}",
                        "source_id": sid,
                        "title": source.get("title") or sid,
                        "path": image.get("path", ""),
                        "url": image.get("url", ""),
                        "alt": image.get("alt", ""),
                        "role": image.get("role") or "source_visual_candidate",
                        "source_path": image.get("source_path", ""),
                        "source_page": image.get("page", "") or image.get("source_page", ""),
                    }
                )
    return out


def source_candidate_key(candidate: dict[str, Any]) -> str:
    return str(candidate.get("id") or candidate.get("path") or candidate.get("url") or "").strip()


def candidate_quality_score(project: Path, candidate: dict[str, Any], subject: str, slide: dict[str, Any] | None = None) -> int:
    """Score whether a source image is real visual evidence, not site chrome."""
    path = str(candidate.get("path") or "").strip()
    url = str(candidate.get("url") or "").strip()
    alt = str(candidate.get("alt") or "").strip()
    title = str(candidate.get("title") or "").strip()
    role = str(candidate.get("role") or "").strip()
    haystack = " ".join([path, url, alt, title, role]).lower()
    asset_haystack = " ".join([path, url, alt, role]).lower()

    score = 0
    if path:
        normalized = project_relative_source_image_path(path)
        score += 8 if (project / normalized).exists() else 3
    if re.search(r"\.(jpe?g|png|webp|avif|tiff?)(?:[?#]|$)", url.lower()):
        score += 5
    if "upload.wikimedia.org" in haystack:
        score += 2
    if "social preview image" in haystack:
        score += 2
    if candidate.get("width") and candidate.get("height"):
        try:
            width = int(candidate.get("width") or 0)
            height = int(candidate.get("height") or 0)
            if width >= 160 and height >= 120:
                score += 3
            if width <= 64 or height <= 64:
                score -= 8
        except (TypeError, ValueError):
            pass

    if ".svg" in asset_haystack:
        score -= 5
    if re.search(r"/(?:20|25|40|50|64)px-", asset_haystack):
        score -= 8
    if any(token in asset_haystack for token in WEAK_SOURCE_IMAGE_TOKENS):
        score -= 18
    if "logo" in asset_haystack and not any(token in haystack for token in ("book", "cover", "portrait", "photo")):
        score -= 10
    if "flag" in asset_haystack and not any(token in haystack for token in ("map", "nation", "country", "国家", "地图")):
        score -= 5

    terms = topic_terms(subject, title_of(slide or {}), text_blob(slide or {}))
    if terms:
        joined = haystack
        hits = sum(1 for term in terms if term and term in joined)
        score += min(hits, 3) * 2
    return score


def usable_source_candidates(
    project: Path,
    candidates: list[dict[str, Any]],
    subject: str,
    slides: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not candidates:
        return []
    deck_text = " ".join([subject, *(text_blob(slide) for slide in slides[:8])])
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for idx, candidate in enumerate(candidates):
        score = candidate_quality_score(project, candidate, deck_text)
        if score >= 4:
            scored.append((score, idx, candidate))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [candidate for _, _, candidate in scored]


def project_relative_source_image_path(candidate_path: str) -> str:
    value = str(candidate_path or "").strip()
    if not value:
        return ""
    if value.startswith(("sources/", "assets/", "charts/", "diagrams/", "images/")):
        return value if value.startswith("sources/") else f"sources/{value}" if value.startswith("images/") else value
    if value.startswith("../"):
        return value
    return f"sources/{value}"


def apply_source_candidate_to_row(project: Path, row: dict[str, Any], candidate: dict[str, Any]) -> None:
    normalized_path = project_relative_source_image_path(str(candidate.get("path") or ""))
    if normalized_path:
        row["path"] = normalized_path
    elif row.get("filename"):
        row["path"] = f"assets/images/{row.get('filename')}"
    else:
        row["path"] = str(row.get("path") or "")
    row["asset_role"] = "source_evidence"
    row["acquire_via"] = "source"
    row["status"] = "Existing" if normalized_path and (project / normalized_path).exists() else "Needs-Manual"
    row["reference"] = str(candidate.get("alt") or candidate.get("title") or row.get("reference") or "")
    row["source_image_id"] = candidate.get("id", "")
    row["source_id"] = candidate.get("source_id", "")
    row["source_page_url"] = candidate.get("source_page_url") or candidate.get("url", "")
    row["source_path"] = candidate.get("source_path", "")
    row["source_page"] = candidate.get("source_page", "")
    row["rights_notes"] = "Inherited from ingested source; verify rights before public distribution."


def candidate_has_existing_path(project: Path, candidate: dict[str, Any]) -> bool:
    normalized = project_relative_source_image_path(str(candidate.get("path") or ""))
    return bool(normalized and (project / normalized).exists())


def rebalance_source_rows(
    project: Path,
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Use every available source image before repeating one.

    Source matching remains conservative during row creation; this pass only
    replaces repeated source-image rows with still-unused candidates so extracted
    Office/EPUB/PDF/URL visuals do not get stranded.
    """
    if not rows or not candidates:
        return rows

    by_key = {source_candidate_key(candidate): candidate for candidate in candidates if source_candidate_key(candidate)}
    if not by_key:
        return rows

    source_rows = [row for row in rows if str(row.get("acquire_via") or "") == "source"]
    if len(source_rows) < 2:
        return rows

    counts: dict[str, int] = {}
    for row in source_rows:
        key = str(row.get("source_image_id") or row.get("path") or "").strip()
        if key:
            counts[key] = counts.get(key, 0) + 1

    unused = [key for key, candidate in by_key.items() if counts.get(key, 0) == 0 and candidate_has_existing_path(project, candidate)]
    if not unused:
        return rows

    unused_by_source: dict[str, list[str]] = {}
    for key in unused:
        source_id = str(by_key[key].get("source_id") or "")
        unused_by_source.setdefault(source_id, []).append(key)

    def take_replacement(row: dict[str, Any]) -> str:
        source_id = str(row.get("source_id") or "")
        if source_id and unused_by_source.get(source_id):
            key = unused_by_source[source_id].pop(0)
            unused.remove(key)
            return key
        if unused:
            key = unused.pop(0)
            other_source = str(by_key[key].get("source_id") or "")
            if key in unused_by_source.get(other_source, []):
                unused_by_source[other_source].remove(key)
            return key
        return ""

    seen_in_order: set[str] = set()
    for row in source_rows:
        if not unused:
            break
        key = str(row.get("source_image_id") or row.get("path") or "").strip()
        if not key:
            continue
        if key not in seen_in_order:
            seen_in_order.add(key)
            continue
        if counts.get(key, 0) <= 1:
            continue
        replacement_key = take_replacement(row)
        if not replacement_key:
            break
        counts[key] -= 1
        counts[replacement_key] = counts.get(replacement_key, 0) + 1
        seen_in_order.add(replacement_key)
        apply_source_candidate_to_row(project, row, by_key[replacement_key])
        row["notes"] = (
            "Source-extracted image candidate assigned by balanced source-image planner. "
            "Verify rights, crop, and relevance before final deck."
        )

    # Later rows are cheaper to swap because early title/context pages often
    # have tighter source anchoring.
    for row in reversed(source_rows):
        if not unused:
            break
        key = str(row.get("source_image_id") or row.get("path") or "").strip()
        if not key or counts.get(key, 0) <= 1:
            continue
        replacement_key = take_replacement(row)
        if not replacement_key:
            break
        counts[key] -= 1
        counts[replacement_key] = 1
        apply_source_candidate_to_row(project, row, by_key[replacement_key])
        row["notes"] = (
            "Source-extracted image candidate assigned by balanced source-image planner. "
            "Verify rights, crop, and relevance before final deck."
        )

    return rows


def slide_wants_source_visual(slide: dict[str, Any], role: str) -> bool:
    media_need = str(slide.get("media_need") or "").lower()
    blob = text_blob(slide).lower()
    explicit_source_media = any(
        token in f"{media_need} {blob}"
        for token in ("source", "image", "photo", "screenshot", "figure", "picture", "图片", "照片", "截图", "图表", "页面")
    )
    source_friendly_roles = {
        "cover",
        "closing",
        "chapter",
        "core_text",
        "context",
        "social_reading",
        "influence",
        "evidence",
        "image_evidence",
        "quote",
        "synthesis",
    }
    return explicit_source_media or role.lower() in source_friendly_roles or bool(slide.get("source_card_ids"))


def source_candidate_for_slide(
    project: Path,
    slide: dict[str, Any],
    cards: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    slide_index: int,
    role: str = "",
    subject: str = "",
) -> dict[str, Any] | None:
    if not candidates:
        return None
    source_ids = source_ids_for_slide(slide, cards)
    if source_ids:
        best: dict[str, Any] | None = None
        best_score = -10_000
        for source_id in source_ids:
            for candidate in candidates:
                if str(candidate.get("source_id") or "") == source_id:
                    score = candidate_quality_score(project, candidate, subject, slide)
                    if score > best_score:
                        best = candidate
                        best_score = score
        if best_score >= 4:
            return best
        if slide_wants_source_visual(slide, role):
            return candidates[(slide_index - 1) % len(candidates)]
        return None
    card_ids = slide.get("source_card_ids") or []
    if card_ids:
        return candidates[(slide_index - 1) % len(candidates)]
    if slide_wants_source_visual(slide, role):
        return candidates[(slide_index - 1) % len(candidates)]
    return None


def source_candidates_for_slide(
    project: Path,
    slide: dict[str, Any],
    cards: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    slide_index: int,
    role: str = "",
    *,
    limit: int = 2,
) -> list[dict[str, Any]]:
    if not candidates or limit <= 0:
        return []
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(candidate: dict[str, Any] | None) -> None:
        if not candidate:
            return
        key = str(candidate.get("id") or candidate.get("path") or len(seen))
        if candidate_quality_score(project, candidate, "", slide) < 4:
            return
        if key in seen:
            return
        seen.add(key)
        selected.append(candidate)

    source_ids = source_ids_for_slide(slide, cards)
    for source_id in source_ids:
        for candidate in candidates:
            if str(candidate.get("source_id") or "") == source_id:
                add(candidate)
                if len(selected) >= limit:
                    return selected

    first = source_candidate_for_slide(project, slide, cards, candidates, slide_index, role)
    add(first)
    offset = (slide_index - 1) % len(candidates)
    for n in range(len(candidates)):
        add(candidates[(offset + n) % len(candidates)])
        if len(selected) >= limit:
            break
    return selected


def slide_wants_multi_source_visual(slide: dict[str, Any], role: str) -> bool:
    pattern = str(slide.get("image_text_pattern_id") or slide.get("image_text_pattern") or "").upper()
    blob = text_blob(slide).lower()
    role_l = role.lower()
    if pattern in {"ITL13", "ITL14"}:
        return True
    if role_l == "comparison" and any(token in blob for token in ("before", "after", "对比", "前后", "比较")):
        return True
    return False


def card_reference(slide: dict[str, Any], cards: dict[str, dict[str, Any]]) -> str:
    card_ids = slide.get("source_card_ids") or []
    if isinstance(card_ids, list):
        for card_id in card_ids:
            card = cards.get(str(card_id))
            if card:
                return str(card.get("claim") or card.get("evidence") or "")
    return str(slide.get("source_anchor") or slide.get("concrete_anchor") or title_of(slide))


def content_link_for_slide(slide: dict[str, Any], reference: str) -> str:
    title = title_of(slide)
    anchors = []
    for key in ("proof_object", "concrete_anchor", "source_anchor", "intent", "visual_role"):
        value = str(slide.get(key) or "").strip()
        if value and value not in anchors:
            anchors.append(value)
    if reference and reference not in anchors:
        anchors.append(reference)
    detail = "; ".join(anchors[:3])
    if title and detail:
        return f"{title} -> {detail}"
    return title or detail or "support the slide claim with topic-specific atmosphere"


def background_duty_for_slide(role: str, visual_type: str, acquire_via: str) -> str:
    role_l = role.lower()
    if acquire_via == "source":
        return "preserve source evidence as an inspectable object; editable foreground text provides interpretation"
    if role_l in {"cover", "opening"}:
        return "establish the deck thesis and emotional entry while leaving strong editable title space"
    if role_l in {"closing", "summary", "synthesis"}:
        return "create a sense of synthesis and forward motion for the final editable claim"
    if visual_type in {"flowchart", "framework", "cycle", "timeline"} or role_l in {"mechanism", "process"}:
        return "provide quiet material depth behind an editable diagram or process model"
    if role_l in {"comparison", "objection", "conflict"} or visual_type == "comparison":
        return "make the contrast tangible through scene/material differences while editable labels carry the argument"
    return "make the slide's abstract point feel concrete through topic-specific scene, object, material, or mood"


def semantic_anchor_for_slide(subject: str, slide: dict[str, Any], reference: str, visual_type: str) -> str:
    candidates = []
    for key in ("source_anchor", "concrete_anchor", "proof_object", "visual_role"):
        value = str(slide.get(key) or "").strip()
        if value:
            candidates.append(value)
    if reference:
        candidates.append(reference)
    if visual_type:
        candidates.append(f"visual type: {visual_type}")
    candidates.append(subject)
    text = " / ".join(dict.fromkeys(candidates))
    return text[:360] or subject


def visual_type_for_role(role: str, blob: str) -> str:
    role = role.lower()
    lower = blob.lower()
    if role in {"mechanism", "conflict"}:
        return "flowchart"
    if role in {"comparison", "objection"}:
        return "comparison"
    if role in {"context", "influence"} or re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", blob):
        return "timeline"
    if role in {"social_reading", "synthesis"}:
        return "framework"
    if any(token in lower for token in ("map", "地图", "地点", "路线")):
        return "map"
    if any(token in lower for token in ("screenshot", "截图", "界面")):
        return "screenshot_context"
    return "scene"


def acquire_via_for_slide(
    slide: dict[str, Any],
    role: str,
    candidate: dict[str, Any] | None,
    slide_index: int,
) -> tuple[str, dict[str, Any] | None]:
    role_l = role.lower()
    if candidate and slide_wants_source_visual(slide, role):
        return "source", candidate
    if role_l in {"cover", "closing", "chapter", "core_text", "context", "social_reading"}:
        return "ai", None
    if role_l in {"mechanism", "conflict", "comparison", "objection"}:
        return "placeholder", None
    return "ai", None


def convert_source_row_to_ai(row: dict[str, Any], subject: str, reason: str) -> None:
    slide_number = int(row.get("slide_no") or 0)
    role_slug = slugify(str(row.get("asset_role") or "concept"))
    title_slug = slugify(str(row.get("purpose") or row.get("reference") or "visual"), "visual")
    row["filename"] = f"{slide_number:02d}-{role_slug}-{title_slug}.png" if slide_number else f"{title_slug}.png"
    row["path"] = f"assets/images/{row['filename']}"
    row["asset_role"] = "background" if row.get("page_role") == "hero_page" else "concept_metaphor"
    row["acquire_via"] = "ai"
    row.pop("status", None)
    for key in ("source_image_id", "source_id", "source_page_url", "source_path", "source_page", "rights_notes"):
        row.pop(key, None)
    row["reference"] = (
        f"{subject}: create a topic-specific editorial image for this slide. "
        f"Reason source image was not used: {reason}. Keep all text, citations, charts, and labels editable."
    )
    row["content_link"] = row.get("content_link") or row.get("purpose") or row["reference"]
    row["background_duty"] = (
        "replace weak/missing source imagery with honest atmosphere or concept support; do not fake source evidence"
    )
    row["semantic_anchor"] = row.get("semantic_anchor") or row["reference"]
    row["notes"] = (
        "Source image candidates were missing, weak, or over-repeated; queue this as an AI atmosphere/concept asset "
        "instead of using site chrome or fake evidence."
    )


def reduce_overused_source_rows(
    project: Path,
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    subject: str,
) -> list[dict[str, Any]]:
    source_rows = [row for row in rows if str(row.get("acquire_via") or "") == "source"]
    if len(source_rows) < 3:
        return rows
    max_uses = 3 if len(rows) >= 16 else 2
    existing_candidates = [candidate for candidate in candidates if candidate_has_existing_path(project, candidate)]
    usage: dict[str, int] = {}

    def replacement_for(current_key: str) -> dict[str, Any] | None:
        for candidate in existing_candidates:
            key = source_candidate_key(candidate)
            if not key or key == current_key:
                continue
            if usage.get(key, 0) < max_uses:
                return candidate
        return None

    for row in source_rows:
        key = str(row.get("source_image_id") or row.get("path") or "").strip()
        if not key:
            convert_source_row_to_ai(row, subject, "source candidate had no stable image identity")
            continue
        usage[key] = usage.get(key, 0) + 1
        if usage[key] > max_uses:
            replacement = replacement_for(key)
            if replacement:
                usage[key] -= 1
                apply_source_candidate_to_row(project, row, replacement)
                replacement_key = source_candidate_key(replacement)
                usage[replacement_key] = usage.get(replacement_key, 0) + 1
                row["notes"] = (
                    "Reused an already-resolved source image candidate to stay under the per-image repetition cap. "
                    "Verify crop and relevance before final deck."
                )
            else:
                convert_source_row_to_ai(row, subject, f"same source image already used {max_uses} times")
    return rows


def ai_fallback_for_unresolved_source(row: dict[str, Any], subject: str) -> dict[str, Any]:
    slide_number = int(row.get("slide_no") or 0)
    base_asset_id = str(row.get("asset_id") or f"slide-{slide_number:02d}-source")
    title_slug = slugify(str(row.get("purpose") or row.get("reference") or "source-visual"), "source-visual")
    filename = f"{slide_number:02d}-ai-fallback-{title_slug}.png" if slide_number else f"ai-fallback-{title_slug}.png"
    return {
        **row,
        "asset_id": f"{base_asset_id}-ai-fallback",
        "filename": filename,
        "path": f"assets/images/{filename}",
        "asset_role": "background" if row.get("page_role") == "hero_page" else "concept_metaphor",
        "acquire_via": "ai",
        "status": "Pending",
        "reference": (
            f"{subject}: generate a topic-specific editorial atmosphere/concept image for this slide because the "
            "matched source image is a remote or unresolved evidence candidate. Do not fake the source image, "
            "page text, chart, screenshot, citation, or logo; keep all information editable in foreground."
        ),
        "content_link": row.get("content_link") or row.get("purpose") or row.get("reference") or "",
        "background_duty": (
            "temporary atmosphere/concept support while unresolved source evidence remains separate and declared"
        ),
        "semantic_anchor": row.get("semantic_anchor") or row.get("reference") or subject,
        "source_image_id": "",
        "source_id": "",
        "source_page_url": row.get("source_page_url", ""),
        "source_path": "",
        "source_page": "",
        "rights_notes": "",
        "notes": (
            "AI fallback for preview/production while the remote source image remains a Needs-Manual evidence asset. "
            "Replace with a rights-cleared downloaded source image or generated art before final claim."
        ),
        "alt_text": f"{subject} - generated fallback for unresolved source visual",
    }


def add_unresolved_source_ai_fallbacks(rows: list[dict[str, Any]], subject: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(row)
        if str(row.get("acquire_via") or "") != "source":
            continue
        if str(row.get("status") or "") == "Existing":
            continue
        out.append(ai_fallback_for_unresolved_source(row, subject))
    return out


def row_for_slide(
    project: Path,
    slide: dict[str, Any],
    idx: int,
    total: int,
    cards: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    subject: str,
) -> dict[str, Any]:
    number = slide_no(slide, idx)
    role = role_of(slide) or ("cover" if idx == 1 else "closing" if idx == total else "evidence")
    title = title_of(slide) or f"Slide {number}"
    reference = card_reference(slide, cards)
    blob = text_blob(slide)
    visual_type = visual_type_for_role(role, blob)
    matched_candidate = source_candidate_for_slide(project, slide, cards, candidates, idx, role, subject)
    acquire_via, candidate = acquire_via_for_slide(slide, role, matched_candidate, idx)
    asset_role = "background" if role in {"cover", "closing"} else "concept_metaphor"
    page_role = "hero_page" if role in {"cover", "closing"} else "local"
    hero_primitive = "atmospheric"
    text_policy = "none"
    status = None
    filename = f"{number:02d}-{slugify(role)}-{slugify(title, 'slide')}.png"
    purpose = f"Slide {number} {role} visual: {title}"
    notes = "Generated at project-prep stage from slide_plan.json; acquire before final rendering or keep as declared gap."
    path = f"assets/images/{filename}"

    if acquire_via == "source" and candidate:
        asset_role = "source_evidence"
        normalized_path = project_relative_source_image_path(str(candidate.get("path") or ""))
        status = "Existing" if normalized_path and (project / normalized_path).exists() else "Needs-Manual"
        path = normalized_path or path
        reference = str(candidate.get("alt") or candidate.get("title") or reference)
        slide_source_ids = set(source_ids_for_slide(slide, cards))
        candidate_source_id = str(candidate.get("source_id") or "")
        if slide_source_ids and candidate_source_id not in slide_source_ids:
            notes = (
                "Topic-level source image candidate backfilled because the slide's own source cards had no usable image. "
                "Verify rights, crop, and relevance before final deck."
            )
        else:
            notes = "Source-extracted image candidate matched from source cards. Verify rights, crop, and relevance before final deck."
    elif acquire_via == "placeholder":
        asset_role = "chart_context" if visual_type in {"flowchart", "comparison", "timeline", "framework"} else "concept_metaphor"
        status = "Placeholder"
        reference = f"Create editable {visual_type} foreground diagram for: {reference}"
        notes = "Use editable SVG/PPT foreground diagram; do not generate fake evidence image."

    content_link = content_link_for_slide(slide, reference)
    background_duty = background_duty_for_slide(role, visual_type, acquire_via)
    semantic_anchor = semantic_anchor_for_slide(subject, slide, reference, visual_type)

    row: dict[str, Any] = {
        "asset_id": f"slide-{number:02d}-{slugify(role)}",
        "filename": filename,
        "path": path,
        "slide_no": number,
        "purpose": purpose,
        "asset_role": asset_role,
        "acquire_via": acquire_via,
        "page_role": page_role,
        "text_policy": text_policy,
        "aspect_ratio": "16:9" if page_role == "hero_page" else "4:3",
        "image_size": "2K" if page_role == "hero_page" else "1K",
        "visual_type": "" if page_role == "hero_page" else visual_type,
        "hero_primitive": hero_primitive if page_role == "hero_page" else "",
        "reference": reference,
        "content_link": content_link,
        "background_duty": background_duty,
        "semantic_anchor": semantic_anchor,
        "source_card_ids": slide.get("source_card_ids") or [],
        "notes": notes,
        "alt_text": f"{subject} - {title}",
    }
    if acquire_via == "source" and candidate:
        row["source_image_id"] = candidate.get("id", "")
        row["source_id"] = candidate.get("source_id", "")
        row["source_page_url"] = candidate.get("source_page_url") or candidate.get("url", "")
        row["source_path"] = candidate.get("source_path", "")
        row["source_page"] = candidate.get("source_page", "")
        row["rights_notes"] = "Inherited from ingested source; verify rights before public distribution."
    if status:
        row["status"] = status
    return row


def extra_source_rows_for_slide(
    project: Path,
    slide: dict[str, Any],
    idx: int,
    cards: dict[str, dict[str, Any]],
    candidates: list[dict[str, Any]],
    subject: str,
    base_row: dict[str, Any],
) -> list[dict[str, Any]]:
    role = role_of(slide) or "evidence"
    if not slide_wants_multi_source_visual(slide, role):
        return []
    selected = source_candidates_for_slide(project, slide, cards, candidates, idx, role, limit=2)
    if len(selected) < 2:
        return []
    rows: list[dict[str, Any]] = []
    base_source_id = str(base_row.get("source_image_id") or "")
    number = slide_no(slide, idx)
    title = title_of(slide) or f"Slide {number}"
    for order, candidate in enumerate(selected, start=1):
        if order == 1 and str(candidate.get("id") or "") == base_source_id:
            continue
        normalized_path = project_relative_source_image_path(str(candidate.get("path") or ""))
        status = "Existing" if normalized_path and (project / normalized_path).exists() else "Needs-Manual"
        rows.append(
            {
                **base_row,
                "asset_id": f"slide-{number:02d}-{slugify(role)}-{order}",
                "filename": f"{number:02d}-{slugify(role)}-{order}-{slugify(title, 'slide')}.png",
                "path": normalized_path or str(base_row.get("path") or ""),
                "purpose": f"Slide {number} {role} comparison source visual {order}: {title}",
                "asset_role": "source_evidence",
                "acquire_via": "source",
                "status": status,
                "reference": str(candidate.get("alt") or candidate.get("title") or base_row.get("reference") or ""),
                "source_image_id": candidate.get("id", ""),
                "source_id": candidate.get("source_id", ""),
                "source_page_url": candidate.get("source_page_url") or candidate.get("url", ""),
                "source_path": candidate.get("source_path", ""),
                "source_page": candidate.get("source_page", ""),
                "rights_notes": "Inherited from ingested source; verify rights before public distribution.",
                "notes": "Additional source-extracted image candidate for a multi-image comparison/evidence slide.",
                "alt_text": f"{subject} - {title} - source visual {order}",
            }
        )
    return rows


def build_rows(project: Path, subject: str, plan_path: Path) -> list[dict[str, Any]]:
    plan = load_json(plan_path)
    slides = iter_slides(plan)
    if not slides:
        raise SystemExit(f"no slides found in {plan_path}")
    cards = source_cards_by_id(project)
    candidates = usable_source_candidates(project, image_candidates(project), subject, slides)
    rows: list[dict[str, Any]] = []
    for idx, slide in enumerate(slides, start=1):
        row = row_for_slide(project, slide, idx, len(slides), cards, candidates, subject)
        rows.append(row)
        rows.extend(extra_source_rows_for_slide(project, slide, idx, cards, candidates, subject, row))
    rows = rebalance_source_rows(project, rows, candidates)
    rows = reduce_overused_source_rows(project, rows, candidates, subject)
    return add_unresolved_source_ai_fallbacks(rows, subject)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create visual asset rows from slide_plan.json.")
    parser.add_argument("project", type=Path, help="Project directory.")
    parser.add_argument("--plan", type=Path, default=None, help="Slide plan path. Defaults to <project>/slide_plan.json.")
    parser.add_argument("--subject", default="", help="Deck subject. Defaults to deck title/topic inferred from slide 1.")
    parser.add_argument("--output", type=Path, default=None, help="Output rows JSON. Defaults to <project>/visual_asset_rows.json.")
    args = parser.parse_args()

    project = args.project.resolve()
    plan_path = args.plan or project / "slide_plan.json"
    rows = build_rows(project, args.subject or project.name, plan_path)
    output = args.output or project / "visual_asset_rows.json"
    payload = {
        "schema_version": "1.0.0",
        "generator": "qiaomu-ppt/scripts/plan_visual_assets.py",
        "project": project.name,
        "subject": args.subject or project.name,
        "rows": rows,
    }
    write_json(output, payload)
    print(json.dumps({"ok": True, "rows": len(rows), "output": str(output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
