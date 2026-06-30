#!/usr/bin/env python3
"""Search and export SVG icons for qiaomu-ppt projects.

The first source is the local QM Icon Studio built-in library. When requested,
the script can also query Iconify and save selected SVGs into the project.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_STUDIO = Path(os.environ.get("QM_ICON_STUDIO", str(Path.home() / "Documents" / "qm-icon-studio")))
ICONIFY_SET_ALIASES = {
    "lucide": "lucide",
    "heroicon": "heroicons",
    "heroicons": "heroicons",
    "heroicons-outline": "heroicons",
    "heroicons-solid": "heroicons",
    "tabler": "tabler",
    "phosphor": "ph",
    "ph": "ph",
    "material": "material-symbols",
    "material-symbols": "material-symbols",
    "mdi": "mdi",
    "carbon": "carbon",
    "radix": "radix-icons",
}
COLLECTION_LICENSES = {
    "lucide": {"license": "ISC", "source": "https://github.com/lucide-icons/lucide"},
    "heroicons": {"license": "MIT", "source": "https://github.com/tailwindlabs/heroicons"},
    "tabler": {"license": "MIT", "source": "https://github.com/tabler/tabler-icons"},
    "ph": {"license": "MIT", "source": "https://github.com/phosphor-icons/core"},
    "material-symbols": {"license": "Apache-2.0", "source": "https://github.com/google/material-design-icons"},
    "mdi": {"license": "Apache-2.0", "source": "https://github.com/Templarian/MaterialDesign"},
    "carbon": {"license": "Apache-2.0", "source": "https://github.com/carbon-design-system/carbon"},
    "radix-icons": {"license": "MIT", "source": "https://github.com/radix-ui/icons"},
}


def load_builtin_icons(studio_root: Path) -> list[dict]:
    icons_js = studio_root / "js" / "icons.js"
    if not icons_js.exists():
        return []
    text = icons_js.read_text(encoding="utf-8", errors="replace")
    matches = re.finditer(
        r'\{\s*n:\s*"(?P<name>[^"]+)",\s*k:\s*"(?P<keywords>[^"]*)",\s*d:\s*"(?P<path>[^"]+)"(?:,\s*fr:\s*"(?P<fillrule>[^"]+)")?\s*\}',
        text,
    )
    icons = []
    for match in matches:
        icons.append(
            {
                "provider": "qm-icon-studio-builtin",
                "id": match.group("name"),
                "name": match.group("name"),
                "keywords": match.group("keywords"),
                "path": match.group("path"),
                "fillrule": match.group("fillrule") or "",
            }
        )
    return icons


def score_icon(icon: dict, terms: list[str]) -> int:
    haystack = f"{icon.get('name', '')} {icon.get('keywords', '')}".lower()
    score = 0
    for term in terms:
        if not term:
            continue
        if icon.get("name", "").lower() == term:
            score += 100
        elif term in icon.get("name", "").lower():
            score += 60
        elif term in haystack:
            score += 35
    return score


def search_builtin(icons: list[dict], query: str, limit: int) -> list[dict]:
    terms = re.findall(r"[a-z0-9\u4e00-\u9fff]+", query.lower())
    scored = []
    for icon in icons:
        score = score_icon(icon, terms)
        if score > 0:
            item = dict(icon)
            item["score"] = score
            scored.append(item)
    scored.sort(key=lambda item: (-item["score"], item["name"]))
    return scored[:limit]


def iconify_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "qiaomu-ppt-icon-search/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_sets(value: str | None) -> list[str]:
    if not value:
        return []
    sets: list[str] = []
    for raw in re.split(r"[,，\s]+", value.strip()):
        if not raw:
            continue
        sets.append(ICONIFY_SET_ALIASES.get(raw.lower(), raw.lower()))
    return list(dict.fromkeys(sets))


def search_iconify_once(query: str, limit: int, prefix: str | None = None) -> list[dict]:
    # Iconify search currently enforces a minimum limit of 32; trim locally.
    params = {"query": query, "limit": str(max(32, limit))}
    if prefix:
        params["prefix"] = prefix
    encoded = urllib.parse.urlencode(params)
    data = iconify_json(f"https://api.iconify.design/search?{encoded}")
    icons = data.get("icons") or []
    results = []
    for icon_id in icons[:limit]:
        collection = icon_id.split(":", 1)[0] if ":" in icon_id else prefix or ""
        results.append(
            {
                "provider": "iconify",
                "id": icon_id,
                "name": icon_id,
                "keywords": query,
                "collection": collection,
                "license": COLLECTION_LICENSES.get(collection, {}).get("license", "unknown"),
                "source": COLLECTION_LICENSES.get(collection, {}).get("source", "https://iconify.design/"),
            }
        )
    return results


def search_iconify(query: str, limit: int, sets: list[str] | None = None) -> list[dict]:
    if not sets:
        return search_iconify_once(query, limit)
    results: list[dict] = []
    seen: set[str] = set()
    per_set = max(4, min(32, limit))
    for prefix in sets:
        try:
            candidates = search_iconify_once(query, per_set, prefix)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            continue
        for item in candidates:
            if item["id"] not in seen:
                item["preferred_set"] = prefix
                results.append(item)
                seen.add(item["id"])
            if len(results) >= limit:
                return results
    return results[:limit]


def builtin_svg(icon: dict, color: str) -> str:
    fillrule = f' fill-rule="{icon["fillrule"]}"' if icon.get("fillrule") else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" role="img" aria-label="'
        + icon["name"]
        + '">'
        + f'<path d="{icon["path"]}" fill="{color}"{fillrule}/>'
        + "</svg>\n"
    )


def fetch_iconify_svg(icon_id: str, color: str) -> str:
    prefix, name = icon_id.split(":", 1)
    encoded_name = urllib.parse.quote(name)
    url = f"https://api.iconify.design/{prefix}/{encoded_name}.svg?color={urllib.parse.quote(color)}"
    request = urllib.request.Request(url, headers={"User-Agent": "qiaomu-ppt-icon-search/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def export_icons(results: list[dict], out_dir: Path, color: str) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    exported = []
    for idx, icon in enumerate(results, start=1):
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", icon["id"]).strip("-")
        path = out_dir / f"{idx:02d}-{safe_id}.svg"
        if icon["provider"] == "qm-icon-studio-builtin":
            svg = builtin_svg(icon, color)
        else:
            svg = fetch_iconify_svg(icon["id"], color)
        path.write_text(svg, encoding="utf-8")
        item = dict(icon)
        item["path"] = str(path)
        exported.append(item)
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description="Search QM Icon Studio/Iconify icons for PPT use.")
    parser.add_argument("query", help="Semantic icon query, Chinese or English.")
    parser.add_argument("--studio-root", default=str(DEFAULT_STUDIO), help="Path to qm-icon-studio.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum results. Default: 12.")
    parser.add_argument("--iconify", action="store_true", help="Also query Iconify online if local matches are weak.")
    parser.add_argument(
        "--sets",
        help="Comma/space separated Iconify collections to prefer, e.g. lucide,heroicons,tabler,ph,material-symbols.",
    )
    parser.add_argument("--export-dir", help="Write result SVGs to this directory.")
    parser.add_argument("--color", default="#111111", help="SVG color when exporting. Default: #111111.")
    args = parser.parse_args()

    limit = max(1, min(48, args.limit))
    builtins = load_builtin_icons(Path(args.studio_root))
    results = search_builtin(builtins, args.query, limit)
    if args.iconify and len(results) < limit:
        seen = {item["id"] for item in results}
        for item in search_iconify(args.query, limit - len(results), normalize_sets(args.sets)):
            if item["id"] not in seen:
                results.append(item)
                seen.add(item["id"])

    payload = {"query": args.query, "count": len(results), "results": results}
    if args.export_dir:
        payload["exported"] = export_icons(results, Path(args.export_dir), args.color)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
