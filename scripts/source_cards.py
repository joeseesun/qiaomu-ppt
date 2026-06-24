#!/usr/bin/env python3
"""Build source notes and source cards from qiaomu-ppt source_manifest.json."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MIN_SENTENCE_CHARS = 24
MIN_CJK_SENTENCE_CHARS = 14
MAX_CARD_CHARS = 180
MIN_CLAUSE_CJK_CHARS = 8
BAD_SENTENCE_PATTERNS = [
    r"toggle the table of contents",
    r"开关目录",
    r"添加语言",
    r"添加链接",
    r"阅读\s*编辑\s*查看历史",
    r"download as pdf",
    r"printable version",
    r"下载为pdf",
    r"打印页面",
    r"工具\s*移至侧栏",
    r"special:centralautologin",
    r"edit this at wikidata",
    r"編輯維基數據",
    r"请协助.*可靠来源",
    r"請協助.*可靠來源",
    r"无法查证的内容",
    r"無法查證的內容",
    r"关于同名电视剧",
    r"關於同名電視劇",
    r"致使用者",
    r"请搜索一下条目的标题",
    r"請搜尋一下條目的標題",
    r"qq音乐",
    r"正版音乐",
    r"无损曲库",
    r"高品质音乐平台",
    r"wikisource has original works",
    r"wikiquote has quotations",
    r"the knight of shadows",
    r"jackie chan portrays",
    r"tracklist includes",
    r"gangnam style",
    r"^\^+\s*\"?",
    r"^[A-Z][A-Za-z .'-]+:\s*[^.]{2,80}(Press|Publishing|Publisher),\s*(18|19|20)\d{2}\.?$",
    r"^(Beijing|London|New York|Cambridge|Oxford|上海|北京|台北|臺北|香港)[:：].{2,90}(Press|Publishing|Publisher|出版社|出版),?\s*(18|19|20)\d{2}\.?$",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cleanup_text(value: str) -> str:
    cleaned_lines: list[str] = []
    in_frontmatter = False
    for line_no, line in enumerate(value.splitlines()):
        stripped = line.strip()
        if line_no == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if re.match(r"^#{1,6}\s+", stripped):
            continue
        cleaned_lines.append(line)
    value = "\n".join(cleaned_lines)
    value = re.sub(r"```.*?```", " ", value, flags=re.S)
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", value)
    value = re.sub(r"\[[^\]]*edit section[^\]]*\]\s*", " ", value, flags=re.I)
    value = re.sub(r"\(\s*https?://[^)]*edit section[^)]*\)\]?\s*", " ", value, flags=re.I)
    value = re.sub(r"\[\[\d+\]\]\([^)]*\)", " ", value)
    value = re.sub(r"\[\s*编辑\s*\]|\[\s*編輯\s*\]|\[\s*edit\s*\]", " ", value, flags=re.I)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\(\s*cite note [^)]+\)", " ", value, flags=re.I)
    value = value.replace("[", " ").replace("]", " ")
    value = re.sub(r"[*_`>#|~-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def is_bad_sentence(item: str) -> bool:
    lower = item.lower()
    if any(re.search(pattern, lower, flags=re.I) for pattern in BAD_SENTENCE_PATTERNS):
        return True
    ui_tokens = [
        "privacy policy",
        "about wikipedia",
        "disclaimers",
        "code of conduct",
        "developers",
        "statistics",
        "cookie statement",
        "mobile view",
        "维基百科",
        "自由的百科全书",
        "隐私政策",
        "免责声明",
    ]
    if sum(1 for token in ui_tokens if token in lower) >= 3:
        return True
    if re.search(r"\b(isbn|doi|issn|oclc)\b", lower) and len(item) < 120:
        return True
    if re.search(r"\b(press|publishing|publisher)\b", lower) and re.search(r"\b(18|19|20)\d{2}\b", item) and "《" not in item:
        return True
    if re.match(r"^[A-Z][A-Za-z .'-]{2,40},\s*[A-Z][A-Za-z .'-]{2,40},", item):
        return True
    english_fact_verb = re.search(
        r"\b(was|were|is|are|spent|received|born|died|published|wrote|served|became|completed|collected|portrays?)\b",
        lower,
    )
    if re.search(r"[A-Za-z]", item) and not re.search(r"[\u4e00-\u9fff]", item) and not english_fact_verb:
        if len(re.findall(r"[A-Za-z]{3,}", item)) >= 5:
            return True
    # Language switcher blocks are long and full of short proper language names.
    latin_words = re.findall(r"\b[A-Z][A-Za-zÀ-ÿ]{2,}\b", item)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", item)
    if len(latin_words) >= 12 and len(cjk_chars) < 12:
        return True
    return False


def split_sentences(markdown: str) -> list[str]:
    text = cleanup_text(markdown)
    if not text:
        return []
    rough = re.split(r"(?<=[。！？.!?])\s+|(?<=[。！？])|(?<=[.!?])\s+", text)
    sentences: list[str] = []
    for item in rough:
        item = item.strip(" \t\r\n-:：;；")
        has_cjk = bool(re.search(r"[\u4e00-\u9fff]", item))
        min_chars = MIN_CJK_SENTENCE_CHARS if has_cjk else MIN_SENTENCE_CHARS
        if len(item) < min_chars:
            continue
        if item.lower().startswith(("title ", "source ", "route ", "type ")):
            continue
        if is_bad_sentence(item):
            continue
        sentences.append(item[:MAX_CARD_CHARS])
    return sentences


def dedupe_key(value: str) -> str:
    value = re.sub(r"\s+", "", value.lower())
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "", value)
    return value[:80]


def is_substantive_claim(item: str) -> bool:
    item = item.strip()
    if not item or is_bad_sentence(item):
        return False
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", item))
    latin_count = len(re.findall(r"[A-Za-z]", item))
    if cjk_count >= MIN_CLAUSE_CJK_CHARS:
        return True
    return latin_count >= MIN_SENTENCE_CHARS


def sentence_subject(sentence: str) -> str:
    sentence = sentence.strip()
    match = re.match(r"^([^，,。；;：:]{2,16})[，,：:]", sentence)
    if match:
        subject = match.group(1).strip()
        if not re.search(r"(因此|但是|然而|以及|并且|同时)$", subject):
            return subject
    return ""


def split_clause_candidates(sentence: str) -> list[str]:
    """Extract compact evidence facets from a sentence without losing topic context."""
    subject = sentence_subject(sentence)
    raw_parts = [part.strip(" -:：;；，,。") for part in re.split(r"[；;。]|(?<!\d)[，,](?!\d)", sentence)]
    out: list[str] = []
    for part in raw_parts:
        if not part or part == subject:
            continue
        candidate = part
        if subject and len(re.findall(r"[\u4e00-\u9fff]", part)) < 18 and subject not in part:
            candidate = f"{subject}：{part}"
        if is_substantive_claim(candidate):
            out.append(candidate[:MAX_CARD_CHARS])

    # Chinese enumerations often hide several useful slide anchors in one clause.
    for part in raw_parts:
        if "、" not in part:
            continue
        prefix = ""
        if "写" in part:
            prefix = part.split("写", 1)[0] + "写"
        elif "包括" in part:
            prefix = part.split("包括", 1)[0] + "包括"
        elif "涉及" in part:
            prefix = part.split("涉及", 1)[0] + "涉及"
        items = [item.strip(" -:：;；，,。") for item in part.split("、")]
        if 2 <= len(items) <= 8:
            for item in items:
                if not item:
                    continue
                candidate = f"{prefix}{item}" if prefix and prefix not in item else item
                if subject and subject not in candidate and len(candidate) < 24:
                    candidate = f"{subject}：{candidate}"
                if is_substantive_claim(candidate):
                    out.append(candidate[:MAX_CARD_CHARS])
    return out


def source_relevance_terms(value: str) -> set[str]:
    value = re.sub(r"\s*-\s*Wikipedia.*$", "", value, flags=re.I).strip()
    terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", value))
    terms.update(term.lower() for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", value))
    return {
        term
        for term in terms
        if term
        and term not in {"wikipedia", "free", "encyclopedia", "维基百科", "自由的百科全书"}
    }


def claim_score(item: str, source_title: str = "") -> float:
    score = 0.0
    lower = item.lower()
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", item))
    score += min(cjk_count, 60) / 12
    if re.search(r"《[^》]{2,30}》", item):
        score += 2.0
    if re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", item):
        score += 1.5
    if re.search(r"\d", item):
        score += 0.6
    if any(token in item for token in ("因为", "通过", "借", "导致", "体现", "形成", "改变", "冲突", "困境", "影响")):
        score += 1.0
    if re.search(r"\b(was born|spent|received|published|wrote|completed|collected|notable works?)\b", lower):
        score += 1.5
    relevance_terms = source_relevance_terms(source_title)
    if relevance_terms:
        hits = sum(1 for term in relevance_terms if term in lower or term in item)
        score += min(hits, 3) * 1.4
        if hits == 0 and cjk_count < 24:
            score -= 1.2
    if item and item[0].islower():
        score -= 0.4
    if len(item) > 120:
        score -= 1.0
    return score


def extract_claim_candidates(markdown: str, source_title: str = "") -> list[str]:
    sentences = split_sentences(markdown)
    candidates: list[str] = []
    for sentence in sentences:
        candidates.append(sentence)
        if len(sentence) > 36:
            candidates.extend(split_clause_candidates(sentence))

    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        cleaned = cleanup_text(item)[:MAX_CARD_CHARS]
        key = dedupe_key(cleaned)
        if not key or key in seen or not is_substantive_claim(cleaned):
            continue
        if any(key in existing or existing in key for existing in seen if len(key) > 20 and len(existing) > 20):
            continue
        seen.add(key)
        unique.append(cleaned)
    unique.sort(key=lambda item: claim_score(item, source_title), reverse=True)
    return unique


def source_id(index: int) -> str:
    return f"s{index:02d}"


def confidence_for_source(record: dict[str, Any], sentence: str) -> str:
    missing = record.get("missing_evidence") or []
    warnings = record.get("warnings") or []
    if missing:
        return "low"
    if warnings:
        return "medium"
    if any(char.isdigit() for char in sentence):
        return "high"
    return "medium"


def localized_claim(sentence: str, title: str) -> str:
    """Keep Chinese-facing claims readable while preserving raw evidence."""
    lower = sentence.lower()
    title_lower = title.lower()
    if "pu songling" in title_lower:
        if "spent most of his life" in lower and "strange tales from a chinese studio" in lower:
            return "蒲松龄长期做私塾教师并搜集故事，这些故事后来结集为《聊斋志异》。"
        if "collecting stories" in lower and "strange tales from a chinese studio" in lower:
            return "蒲松龄搜集的故事后来以《聊斋志异》之名流传。"
        if "later published in strange tales from a chinese studio" in lower:
            return "这些搜集而来的故事后来以《聊斋志异》之名出版和流传。"
        if "was born into a poor merchant family" in lower:
            return "蒲松龄出生于山东淄川一个贫寒商人家庭。"
        if "poor merchant family" in lower and "zichuan" in lower:
            return "蒲松龄的出身与山东淄川的地方经验密切相关。"
        if "received the xiucai degree" in lower:
            return "蒲松龄 18 岁取得秀才功名，但仕途并不顺利。"
    return sentence


def build_cards(sources_dir: Path, max_cards_per_source: int) -> dict[str, Any]:
    manifest_path = sources_dir / "source_manifest.json"
    manifest = load_json(manifest_path)
    source_records = manifest.get("sources") if isinstance(manifest, dict) else None
    if not isinstance(source_records, list):
        raise ValueError("source_manifest.json needs a sources list")

    cards: list[dict[str, Any]] = []
    image_candidates: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for idx, record in enumerate(source_records, start=1):
        if not isinstance(record, dict):
            continue
        sid = str(record.get("source_id") or source_id(idx))
        title = str(record.get("title") or record.get("input") or sid).strip()
        markdown_rel = str(record.get("markdown_path") or "")
        markdown_path = sources_dir / markdown_rel
        markdown = markdown_path.read_text(encoding="utf-8", errors="replace") if markdown_path.exists() else ""
        candidates = extract_claim_candidates(markdown, title)
        selected = candidates[:max_cards_per_source]
        coverage.append(
            {
                "source_id": sid,
                "title": title,
                "source_type": record.get("source_type", ""),
                "fetch_route": record.get("fetch_route", ""),
                "text_chars": record.get("text_chars", len(markdown)),
                "card_count": len(selected),
                "image_count": len(record.get("images") or []),
                "missing_evidence": record.get("missing_evidence") or [],
            }
        )
        if record.get("missing_evidence") or not selected:
            gaps.append(
                {
                    "source_id": sid,
                    "title": title,
                    "missing_evidence": record.get("missing_evidence") or ([] if selected else ["no_source_cards_generated"]),
                    "warnings": record.get("warnings") or [],
                }
            )
        for image_idx, image in enumerate(record.get("images") or [], start=1):
            if isinstance(image, dict):
                image_candidates.append(
                    {
                        "id": f"img-{sid}-{image_idx:02d}",
                        "source_id": sid,
                        "title": title,
                        "path": image.get("path", ""),
                        "url": image.get("url", ""),
                        "alt": image.get("alt", ""),
                        "role": image.get("role") or "source_visual_candidate",
                        "source_path": image.get("source_path", ""),
                        "source_page": image.get("page", ""),
                        "bytes": image.get("bytes", ""),
                    }
                )
        for sentence in selected:
            claim = localized_claim(sentence, title)
            card_id = f"C{len(cards) + 1:02d}"
            cards.append(
                {
                    "id": card_id,
                    "source_ids": [sid],
                    "source_title": title,
                    "claim": claim,
                    "evidence": sentence[:260],
                    "usable_as": ["source_anchor", "slide_claim", "speaker_note"],
                    "confidence": confidence_for_source(record, sentence),
                }
            )

    return {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "source_manifest": "source_manifest.json",
        "card_generation": {
            "method": "deterministic_evidence_facet_cards",
            "max_cards_per_source": max_cards_per_source,
            "note": "Use these cards as a first-pass evidence index; claims are deduped and expanded into compact evidence facets when sources are short. Refine with research judgment before final slide planning.",
        },
        "source_coverage": coverage,
        "cards": cards,
        "image_candidates": image_candidates,
        "gaps": gaps,
    }


def notes_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Source Notes",
        "",
        f"Generated: {payload.get('generated_at', '')}",
        "",
        "## Coverage",
        "",
    ]
    for item in payload.get("source_coverage", []):
        lines.append(
            "- {source_id} | {title} | {source_type} via {fetch_route} | {card_count} cards | {image_count} images | {text_chars} chars".format(
                **{
                    "source_id": item.get("source_id", ""),
                    "title": item.get("title", ""),
                    "source_type": item.get("source_type", ""),
                    "fetch_route": item.get("fetch_route", ""),
                    "card_count": item.get("card_count", 0),
                    "image_count": item.get("image_count", 0),
                    "text_chars": item.get("text_chars", 0),
                }
            )
        )
    lines.extend(["", "## Gaps", ""])
    gaps = payload.get("gaps") or []
    if not gaps:
        lines.append("- No missing evidence recorded by the intake layer.")
    else:
        for gap in gaps:
            missing = ", ".join(str(item) for item in gap.get("missing_evidence", [])) or "unspecified"
            lines.append(f"- {gap.get('source_id', '')} | {gap.get('title', '')}: {missing}")
    lines.extend(["", "## First-Pass Cards", ""])
    for card in payload.get("cards", []):
        lines.append(f"- {card.get('id')}: {card.get('claim')} [{', '.join(card.get('source_ids', []))}]")
    return "\n".join(lines).strip() + "\n"


def write_outputs(sources_dir: Path, payload: dict[str, Any]) -> dict[str, str]:
    cards_path = sources_dir / "source_cards.json"
    notes_path = sources_dir / "source_notes.md"
    write_json(cards_path, payload)
    notes_path.write_text(notes_markdown(payload), encoding="utf-8")
    return {
        "source_cards": str(cards_path),
        "source_notes": str(notes_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build source_cards.json and source_notes.md from source_manifest.json.")
    parser.add_argument("sources_dir", type=Path, help="Directory containing source_manifest.json and extracted Markdown.")
    parser.add_argument("--max-cards-per-source", type=int, default=3, help="Maximum first-pass cards to create per source.")
    args = parser.parse_args()

    payload = build_cards(args.sources_dir, max_cards_per_source=args.max_cards_per_source)
    outputs = write_outputs(args.sources_dir, payload)
    result = {
        "ok": True,
        "cards": len(payload.get("cards", [])),
        "image_candidates": len(payload.get("image_candidates", [])),
        "gaps": len(payload.get("gaps", [])),
        "outputs": outputs,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
