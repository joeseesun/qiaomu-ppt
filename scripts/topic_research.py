#!/usr/bin/env python3
"""Collect topic research sources for qiaomu-ppt and build source cards."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


USER_AGENT = "qiaomu-ppt-topic-research/0.1 (+https://github.com/joeseesun/qiaomu-ppt)"
DEFAULT_LANES = [
    ("entity", "{topic}"),
    ("overview", "{topic} overview chronology key facts"),
    ("context", "{topic} background context interpretation"),
    ("primary", "{topic} primary source original work document"),
    ("visuals", "{topic} images museum archive map figure"),
    ("influence", "{topic} influence legacy modern relevance"),
]


@dataclass
class Candidate:
    url: str
    title: str = ""
    snippet: str = ""
    provider: str = ""
    lane: str = ""
    score: int = 0
    warnings: list[str] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def fetch_json(url: str, headers: dict[str, str] | None = None, timeout: int = 25) -> tuple[Any | None, list[str]]:
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    req = Request(url, headers=request_headers)
    try:
        with urlopen(req, timeout=timeout) as response:
            data = response.read()
        return json.loads(data.decode("utf-8", errors="replace")), []
    except Exception as exc:
        return None, [f"{urlparse(url).netloc or url} failed: {exc}"]


def clean_text(value: str) -> str:
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def relevance_tokens(topic: str) -> list[str]:
    tokens = [topic.strip().lower()]
    tokens.extend(token.lower() for token in re.findall(r"[a-z0-9][a-z0-9_.-]{2,}", topic))
    tokens.extend(token for token in re.findall(r"[\u4e00-\u9fff]{2,}", topic))
    return [token for token in dict.fromkeys(tokens) if token]


def topic_focus_terms(topic: str, limit: int = 5) -> list[str]:
    """Extract searchable focus terms from a natural-language deck topic."""
    raw = re.sub(r"[《》“”\"']", " ", str(topic or ""))
    pieces = re.split(r"\s*(?:与|和|及|以及|、|，|,|：|:|/|\\+|&|vs\\.?|VS\\.?|——|--|-)\s*", raw)
    terms: list[str] = []
    for piece in [topic, *pieces]:
        value = re.sub(r"\s+", " ", piece).strip()
        value = re.sub(r"^(介绍|解读|关于|制作|一份|PPT|ppt|主题)\s*", "", value).strip()
        if len(value) < 2:
            continue
        if value not in terms:
            terms.append(value)
    # If one compound CJK phrase survived intact, also try shorter CJK chunks.
    for match in re.findall(r"[\u4e00-\u9fff]{2,12}", raw):
        if match not in terms:
            terms.append(match)
    return terms[:limit]


def is_relevant_to_topic(topic: str, title: str, snippet: str = "", url: str = "") -> bool:
    haystack = " ".join([title, snippet, url]).lower()
    tokens = relevance_tokens(topic)
    if not tokens:
        return True
    if any(token.lower() in haystack for token in tokens):
        return True
    # For CJK names, partial overlap is sometimes useful, but require at least
    # two shared CJK characters to avoid random scholarly hits.
    cjk_topic = set(re.findall(r"[\u4e00-\u9fff]", topic))
    cjk_haystack = set(re.findall(r"[\u4e00-\u9fff]", title + snippet))
    return len(cjk_topic & cjk_haystack) >= min(2, len(cjk_topic))


def normalize_url(url: str) -> str:
    url = str(url or "").strip()
    if url.startswith("//"):
        return "https:" + url
    return url


def topic_lanes(topic: str, depth: str = "balanced") -> list[tuple[str, str]]:
    lanes = [(lane, template.format(topic=topic)) for lane, template in DEFAULT_LANES]
    focus_terms = topic_focus_terms(topic)
    for idx, term in enumerate(focus_terms[1:], start=1):
        lanes.append((f"entity_focus_{idx}", term))
        lanes.append((f"overview_focus_{idx}", f"{term} overview key facts"))
    if re.search(r"[\u4e00-\u9fff]", topic):
        lanes.extend(
            [
                ("overview_zh", f"{topic} 生平 年谱 主要事实"),
                ("context_zh", f"{topic} 背景 解读 研究"),
                ("visuals_zh", f"{topic} 图片 故居 博物馆 档案"),
            ]
        )
        for idx, term in enumerate(focus_terms[1:], start=1):
            lanes.append((f"overview_focus_zh_{idx}", f"{term} 生平 主要事实"))
            lanes.append((f"visuals_focus_zh_{idx}", f"{term} 图片 档案"))
    if depth == "fast":
        return [
            item
            for item in lanes
            if item[0] in {"entity", "overview_zh", "overview"}
            or item[0].startswith(("entity_focus", "overview_focus"))
        ]
    if depth == "deep":
        return lanes
    return [item for item in lanes if item[0] not in {"visuals", "visuals_zh"}]
    return lanes


def brave_search(query: str, lane: str, max_results: int) -> tuple[list[Candidate], list[str]]:
    key = os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY")
    if not key:
        return [], ["BRAVE_SEARCH_API_KEY not set"]
    url = "https://api.search.brave.com/res/v1/web/search?" + urlencode(
        {"q": query, "count": min(max_results, 10), "search_lang": "zh-cn"}
    )
    payload, warnings = fetch_json(
        url,
        headers={"Accept": "application/json", "X-Subscription-Token": key},
    )
    candidates: list[Candidate] = []
    if isinstance(payload, dict):
        results = ((payload.get("web") or {}).get("results") or [])
        for idx, item in enumerate(results[:max_results], start=1):
            if not isinstance(item, dict):
                continue
            result_url = normalize_url(item.get("url", ""))
            if result_url:
                candidates.append(
                    Candidate(
                        url=result_url,
                        title=clean_text(item.get("title", "")),
                        snippet=clean_text(item.get("description", "")),
                        provider="brave",
                        lane=lane,
                        score=100 - idx,
                    )
                )
    return candidates, warnings


def wikipedia_opensearch(query: str, lane: str, lang: str, max_results: int) -> tuple[list[Candidate], list[str]]:
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urlencode(
        {
            "action": "opensearch",
            "search": query,
            "limit": min(max_results, 8),
            "namespace": "0",
            "format": "json",
        }
    )
    payload, warnings = fetch_json(url)
    candidates: list[Candidate] = []
    if isinstance(payload, list) and len(payload) >= 4:
        titles = payload[1] if isinstance(payload[1], list) else []
        snippets = payload[2] if isinstance(payload[2], list) else []
        urls = payload[3] if isinstance(payload[3], list) else []
        for idx, result_url in enumerate(urls[:max_results], start=1):
            result_url = normalize_url(result_url)
            if not result_url:
                continue
            candidates.append(
                Candidate(
                    url=result_url,
                    title=clean_text(titles[idx - 1] if idx - 1 < len(titles) else ""),
                    snippet=clean_text(snippets[idx - 1] if idx - 1 < len(snippets) else ""),
                    provider=f"wikipedia:{lang}",
                    lane=lane,
                    score=110 - idx,
                )
            )
    return candidates, warnings


def wikidata_search(query: str, lane: str, lang: str, max_results: int) -> tuple[list[Candidate], list[str]]:
    url = "https://www.wikidata.org/w/api.php?" + urlencode(
        {
            "action": "wbsearchentities",
            "search": query,
            "language": lang,
            "format": "json",
            "limit": min(max_results, 6),
        }
    )
    payload, warnings = fetch_json(url)
    candidates: list[Candidate] = []
    if isinstance(payload, dict):
        for idx, item in enumerate(payload.get("search") or [], start=1):
            if not isinstance(item, dict):
                continue
            result_url = normalize_url(item.get("concepturi") or item.get("url") or "")
            if result_url.startswith("//"):
                result_url = "https:" + result_url
            if result_url:
                candidates.append(
                    Candidate(
                        url=result_url,
                        title=clean_text(item.get("label", "")),
                        snippet=clean_text(item.get("description", "")),
                        provider="wikidata",
                        lane=lane,
                        score=95 - idx,
                    )
                )
    return candidates, warnings


def duckduckgo_instant_answer(query: str, lane: str, max_results: int) -> tuple[list[Candidate], list[str]]:
    url = "https://api.duckduckgo.com/?" + urlencode(
        {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
    )
    payload, warnings = fetch_json(url)
    candidates: list[Candidate] = []
    if not isinstance(payload, dict):
        return candidates, warnings
    if payload.get("AbstractURL"):
        candidates.append(
            Candidate(
                url=normalize_url(payload["AbstractURL"]),
                title=clean_text(payload.get("Heading", "")),
                snippet=clean_text(payload.get("AbstractText", "")),
                provider="duckduckgo_instant_answer",
                lane=lane,
                score=75,
            )
        )
    for idx, item in enumerate(payload.get("Results") or [], start=1):
        if not isinstance(item, dict) or not item.get("FirstURL"):
            continue
        candidates.append(
            Candidate(
                url=normalize_url(item.get("FirstURL", "")),
                title=clean_text(item.get("Text", "")),
                snippet=clean_text(item.get("Result", "")),
                provider="duckduckgo_instant_answer",
                lane=lane,
                score=65 - idx,
            )
        )
        if len(candidates) >= max_results:
            break
    return candidates, warnings


def openalex_search(query: str, lane: str, max_results: int) -> tuple[list[Candidate], list[str]]:
    url = "https://api.openalex.org/works?" + urlencode(
        {"search": query, "per-page": min(max_results, 8), "select": "id,display_name,publication_year,primary_location,doi"}
    )
    payload, warnings = fetch_json(url)
    candidates: list[Candidate] = []
    if isinstance(payload, dict):
        for idx, item in enumerate(payload.get("results") or [], start=1):
            if not isinstance(item, dict):
                continue
            primary = item.get("primary_location") if isinstance(item.get("primary_location"), dict) else {}
            landing = primary.get("landing_page_url") or item.get("doi") or item.get("id")
            if not landing:
                continue
            title = clean_text(item.get("display_name", ""))
            year = item.get("publication_year") or ""
            candidates.append(
                Candidate(
                    url=normalize_url(str(landing)),
                    title=title,
                    snippet=f"OpenAlex scholarly result {year}".strip(),
                    provider="openalex",
                    lane=lane,
                    score=42 - idx,
                )
            )
    return candidates, warnings


def collect_candidates(topic: str, max_results_per_lane: int, provider: str, lang: str, depth: str) -> tuple[list[Candidate], list[str]]:
    all_candidates: list[Candidate] = []
    warnings: list[str] = []
    for lane, query in topic_lanes(topic, depth):
        providers = []
        if provider in {"auto", "brave"}:
            providers.append(brave_search)
        if provider in {"auto", "wikipedia"}:
            providers.append(lambda q, l, m: wikipedia_opensearch(q, l, lang, m))
            if lang != "en":
                providers.append(lambda q, l, m: wikipedia_opensearch(q, l, "en", max(2, m // 2)))
            providers.append(lambda q, l, m: wikidata_search(q, l, "zh" if lang.startswith("zh") else lang, m))
        if provider in {"auto", "duckduckgo"} and depth != "fast":
            providers.append(duckduckgo_instant_answer)
        if provider in {"auto", "openalex"} and depth == "deep" and lane in {"context", "context_zh", "influence", "primary"}:
            providers.append(openalex_search)

        for func in providers:
            try:
                found, provider_warnings = func(query, lane, max_results_per_lane)
            except Exception as exc:
                found, provider_warnings = [], [f"{getattr(func, '__name__', 'provider')} failed: {exc}"]
            all_candidates.extend(found)
            warnings.extend(provider_warnings)

    return dedupe_candidates(all_candidates, topic), sorted(set(warnings))


def dedupe_candidates(candidates: list[Candidate], topic: str = "") -> list[Candidate]:
    by_url: dict[str, Candidate] = {}
    for item in candidates:
        url = normalize_url(item.url)
        if not url.startswith(("http://", "https://")):
            continue
        if item.provider == "openalex" and topic and not is_relevant_to_topic(topic, item.title, item.snippet, url):
            continue
        if item.provider.startswith("duckduckgo") and topic and not is_relevant_to_topic(topic, item.title, item.snippet, url):
            continue
        existing = by_url.get(url)
        if existing:
            existing.score = max(existing.score, item.score)
            if item.lane and item.lane not in existing.lane.split(","):
                existing.lane = ",".join(filter(None, [existing.lane, item.lane]))
            if item.provider and item.provider not in existing.provider.split(","):
                existing.provider = ",".join(filter(None, [existing.provider, item.provider]))
            continue
        item.url = url
        item.score += provider_boost(item.provider)
        by_url[url] = item
    return sorted(by_url.values(), key=lambda item: (-item.score, item.url))


def provider_boost(provider: str) -> int:
    if "wikipedia" in provider:
        return 25
    if "wikidata" in provider:
        return 12
    if "manual" in provider:
        return 30
    if "brave" in provider:
        return 8
    if "duckduckgo" in provider:
        return 2
    if "openalex" in provider:
        return -8
    return 0


def candidate_payload(candidates: list[Candidate]) -> list[dict[str, Any]]:
    return [
        {
            "url": item.url,
            "title": item.title,
            "snippet": item.snippet,
            "provider": item.provider,
            "lane": item.lane,
            "score": item.score,
            "warnings": item.warnings,
        }
        for item in candidates
    ]


def write_research_brief(output_dir: Path, topic: str, audience: str, route: str, warnings: list[str]) -> None:
    brief = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "topic": topic,
        "assumed_audience": audience,
        "route": route,
        "research_status": "attempted",
        "research_questions": [
            f"{topic} 的基本事实、时间线和关键人物/概念是什么？",
            f"{topic} 哪些解释角度最适合做成 PPT 主线？",
            f"{topic} 有哪些可作为视觉证据的图片、图表、原文、地点或档案？",
        ],
        "source_strategy": [
            "search lanes: overview/context/primary/visuals/influence",
            "prefer authoritative or primary sources when available",
            "ingest selected URLs through qiaomu-ppt source_to_markdown.py before slide planning",
        ],
        "warnings": warnings,
    }
    write_json(output_dir / "research_brief.json", brief)
    write_text(
        output_dir / "research_plan.md",
        f"""# Topic Research Plan: {topic}

Status: attempted automated source discovery.

## Lanes

{chr(10).join(f"- {lane}: {query}" for lane, query in topic_lanes(topic, "deep"))}

## Evidence Rule

Only sources successfully ingested into `source_manifest.json` and represented in
`source_cards.json` should drive final slide claims. Search candidates are not
slide evidence until they pass ingestion.
""",
    )


def run_source_intake(
    output_dir: Path,
    urls: list[str],
    download_images: bool,
    max_images: int,
    max_cards_per_source: int,
    per_url_timeout: int,
) -> dict[str, Any]:
    if not urls:
        return {"schema_version": "1.0.0", "ingested": 0, "records": [], "failures": [], "source_card_outputs": {}}
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    warnings: list[str] = []
    for url in urls:
        command = [
            sys.executable,
            str(SCRIPT_DIR / "source_to_markdown.py"),
            url,
            "--output-dir",
            str(output_dir),
            "--max-images",
            str(max_images),
            "--max-cards-per-source",
            str(max_cards_per_source),
            "--no-build-cards",
        ]
        if download_images:
            command.append("--download-images")
        try:
            proc = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=per_url_timeout,
            )
        except subprocess.TimeoutExpired:
            failures.append({"input": url, "error": f"timed out after {per_url_timeout}s"})
            continue
        if proc.stderr.strip():
            warnings.append(proc.stderr.strip()[:1000])
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            failures.append({"input": url, "error": f"source_to_markdown emitted non-JSON output: {proc.stdout[:300]}"})
            continue
        records.extend(item for item in payload.get("records", []) if isinstance(item, dict))
        failures.extend(item for item in payload.get("failures", []) if isinstance(item, dict))
        if proc.returncode not in {0, 2}:
            failures.append({"input": url, "error": f"source_to_markdown exited {proc.returncode}"})

    card_outputs: dict[str, Any] = {}
    if records:
        command = [
            sys.executable,
            str(SCRIPT_DIR / "source_cards.py"),
            str(output_dir),
            "--max-cards-per-source",
            str(max_cards_per_source),
        ]
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if proc.returncode == 0:
            try:
                cards_payload = json.loads(proc.stdout)
                card_outputs = cards_payload.get("outputs", {})
                card_outputs.update(
                    {
                        "cards": cards_payload.get("cards", 0),
                        "image_candidates": cards_payload.get("image_candidates", 0),
                        "gaps": cards_payload.get("gaps", 0),
                    }
                )
            except json.JSONDecodeError:
                failures.append({"input": str(output_dir / "source_manifest.json"), "error": "source_cards emitted non-JSON output"})
        else:
            failures.append({"input": str(output_dir / "source_manifest.json"), "error": f"source_cards exited {proc.returncode}: {proc.stderr[:300]}"})

    return {
        "schema_version": "1.0.0",
        "ingested": len(records),
        "records": records,
        "failures": failures,
        "warnings": warnings,
        "output_dir": str(output_dir),
        "source_card_outputs": card_outputs,
    }


def write_report(
    output_dir: Path,
    topic: str,
    provider: str,
    candidates: list[Candidate],
    selected_urls: list[str],
    warnings: list[str],
    source_result: dict[str, Any],
) -> dict[str, Any]:
    report = {
        "schema_version": "1.0.0",
        "ok": bool(source_result.get("ingested", 0)),
        "generated_at": now_iso(),
        "topic": topic,
        "provider": provider,
        "research_status": "completed" if source_result.get("ingested", 0) else "partial",
        "candidate_count": len(candidates),
        "selected_urls": selected_urls,
        "candidates": candidate_payload(candidates),
        "warnings": warnings,
        "source_result": source_result,
        "artifacts": {
            "research_brief": "research_brief.json",
            "research_plan": "research_plan.md",
            "source_manifest": "source_manifest.json" if (output_dir / "source_manifest.json").exists() else "",
            "source_notes": "source_notes.md" if (output_dir / "source_notes.md").exists() else "",
            "source_cards": "source_cards.json" if (output_dir / "source_cards.json").exists() else "",
        },
    }
    write_json(output_dir / "topic_research_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Research a broad topic and ingest selected URLs into qiaomu-ppt sources.")
    parser.add_argument("topic", help="Topic to research.")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("sources"), help="Sources output directory.")
    parser.add_argument("--provider", choices=["auto", "brave", "wikipedia", "duckduckgo", "openalex"], default="auto")
    parser.add_argument("--depth", choices=["fast", "balanced", "deep"], default="balanced", help="Search breadth. fast skips slow scholarly/deep lanes.")
    parser.add_argument("--lang", default="zh", help="Primary Wikipedia/Wikidata language code.")
    parser.add_argument("--audience", default="general Chinese-speaking audience")
    parser.add_argument("--route", default="talk_deck")
    parser.add_argument("--max-results-per-lane", type=int, default=4)
    parser.add_argument("--max-pages", type=int, default=6, help="Maximum selected URLs to ingest.")
    parser.add_argument("--per-url-timeout", type=int, default=45, help="Seconds allowed for each selected URL ingestion.")
    parser.add_argument("--download-images", action="store_true")
    parser.add_argument("--max-images", type=int, default=12)
    parser.add_argument("--max-cards-per-source", type=int, default=4)
    parser.add_argument("--candidate-url", action="append", default=[], help="Manual candidate URL to include before provider results.")
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates, warnings = collect_candidates(
        args.topic,
        max_results_per_lane=args.max_results_per_lane,
        provider=args.provider,
        lang=args.lang,
        depth=args.depth,
    )
    manual_candidates = [
        Candidate(url=url, title=urlparse(url).netloc, provider="manual", lane="manual", score=120)
        for url in args.candidate_url
    ]
    candidates = dedupe_candidates([*manual_candidates, *candidates], args.topic)
    selected_urls = [item.url for item in candidates[: max(0, args.max_pages)]]
    write_research_brief(output_dir, args.topic, args.audience, args.route, warnings)
    source_result = run_source_intake(
        output_dir=output_dir,
        urls=selected_urls,
        download_images=args.download_images,
        max_images=args.max_images,
        max_cards_per_source=args.max_cards_per_source,
        per_url_timeout=args.per_url_timeout,
    )
    report = write_report(output_dir, args.topic, args.provider, candidates, selected_urls, warnings, source_result)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
