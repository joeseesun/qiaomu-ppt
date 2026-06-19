#!/usr/bin/env python3
"""Create a 3-5 item background-image prompt pack for qiaomu-ppt decks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROLES = [
    ("cover", "quiet opening background with a strong but calm focal depth"),
    ("evidence_dark", "dark evidence background with a calm chart-safe area"),
    ("evidence_light", "light paper-like evidence background with generous white space"),
    ("diagram", "neutral diagram background with depth but no grid or decorative lines"),
    ("closing", "quiet closing background with subtle momentum and no extra objects"),
]


def build_prompt(subject: str, route: str, role: str, role_goal: str, accent: str) -> str:
    return (
        f"Create a quiet 16:9 presentation background for a {route} deck about {subject}. "
        f"Role: {role} - {role_goal}. "
        f"Use a neutral base, readable quiet space for slide content, and one restrained {accent} accent only. "
        "No text, no logos, no icons, no UI controls, no charts, no fake screenshots, no decorative stripes, "
        "no ornamental grids, no thin tech lines, no neon rails. "
        "The background must support foreground typography and source images without competing."
    )


def create_pack(subject: str, route: str, accent: str, count: int) -> dict:
    count = max(3, min(5, count))
    prompts = []
    for role, role_goal in ROLES[:count]:
        prompts.append(
            {
                "role": role,
                "size": "16:9",
                "recommended_pixels": "1920x1080",
                "prompt": build_prompt(subject, route, role, role_goal, accent),
                "negative_constraints": [
                    "text",
                    "logo",
                    "UI chrome",
                    "chart",
                    "decorative linework",
                    "multiple accent colors",
                ],
            }
        )
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "subject": subject,
        "route": route,
        "color_budget": {
            "max_active_colors_per_slide": 3,
            "count_source_images": False,
            "accent_policy": "one accent per slide",
            "accent": accent,
        },
        "prompts": prompts,
        "use_policy": "Generate these with Codex image generation when available; save outputs under assets/backgrounds/ and record paths in visual_contract.json.",
        "fallback_policy": "If image generation is unavailable, use neutral solid surfaces only; do not replace with decorative lines or grids.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate qiaomu-ppt background image prompts.")
    parser.add_argument("--subject", required=True, help="Deck subject or theme.")
    parser.add_argument("--route", default="talk_deck", help="Deck route, such as brand_release or talk_deck.")
    parser.add_argument("--accent", default="cyan", help="Single accent color name, such as cyan or red.")
    parser.add_argument("--count", type=int, default=5, help="Number of prompts, clamped to 3-5.")
    parser.add_argument("--output", "-o", help="Write JSON prompt pack to this path.")
    args = parser.parse_args()

    pack = create_pack(args.subject, args.route, args.accent, args.count)
    rendered = json.dumps(pack, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
