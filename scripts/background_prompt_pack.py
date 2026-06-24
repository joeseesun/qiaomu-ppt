#!/usr/bin/env python3
"""Create a five-item atmosphere-only background prompt pack."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROLES = [
    ("cover_atmosphere", "quiet opening atmosphere with soft depth and no layout objects"),
    ("dark_evidence", "dark atmospheric color wash for high-impact evidence slides"),
    ("light_evidence", "light paper-like color wash for dense readable evidence slides"),
    ("diagram_focus", "neutral abstract depth for architecture or process slides"),
    ("closing_atmosphere", "quiet closing atmosphere with subtle momentum"),
]

NEGATIVE_CONSTRAINTS = [
    "text",
    "letters",
    "numbers",
    "logo",
    "icon",
    "UI chrome",
    "button",
    "chart",
    "table",
    "diagram",
    "screenshot",
    "mockup",
    "box",
    "rectangle",
    "square",
    "card",
    "panel",
    "frame",
    "window",
    "container",
    "placeholder",
    "layout scaffolding",
    "image slot",
    "content block",
    "decorative linework",
    "ornamental grid",
    "neon rail",
    "multiple accent colors",
]


def build_prompt(subject: str, route: str, role: str, role_goal: str, accent: str) -> str:
    return (
        f"Create a quiet 16:9 presentation background for a {route} deck about {subject}. "
        f"Role: {role} - {role_goal}. "
        "The image must support the deck content, not act as generic decoration. "
        f"Semantic anchor: use concrete objects, spaces, materials, era cues, or mechanisms connected to {subject}; "
        "avoid style-only wallpaper and random futuristic linework. "
        f"Use only atmosphere: color fields, soft gradients, diffuse glow, subtle grain, and restrained topic-specific material. "
        f"Use a neutral base and one restrained {accent} accent only. "
        "Do not create slide structure. No boxes, rectangles, cards, panels, frames, windows, placeholders, "
        "chart areas, image slots, UI containers, text blocks, labels, diagrams, mockups, screenshots, logos, or icons. "
        "Foreground titles, cards, charts, frames, and all page elements will be added later as editable objects. "
        "The background must stay behind the layout and never imply a non-editable content container."
    )


def create_pack(subject: str, route: str, accent: str, count: int) -> dict:
    count = max(3, min(5, count))
    prompts = []
    for role, role_goal in ROLES[:count]:
        prompts.append(
            {
                "role": role,
                "content_link": f"Deck-level {role} background supporting {subject}; refine per slide before final-quality use.",
                "background_duty": role_goal,
                "semantic_anchor": f"Concrete source/topic material tied to {subject}, not generic abstract decoration.",
                "size": "16:9",
                "recommended_pixels": "1920x1080",
                "prompt": build_prompt(subject, route, role, role_goal, accent),
                "negative_constraints": NEGATIVE_CONSTRAINTS,
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
        "use_policy": "Generate these backgrounds with Codex image generation when available; save outputs under assets/backgrounds/ and record paths in visual_contract.json. Select by slide role: cover/closing atmosphere for statement pages, dark evidence for benchmark proof, light evidence for dense charts, and diagram focus for architecture/process pages. For final-quality decks, refine each selected image with slide-level content_link, background_duty, and semantic_anchor before generation. These images are atmosphere-only; all slide elements remain editable foreground objects.",
        "fallback_policy": "If image generation is unavailable, use neutral solid/gradient surfaces only; do not replace with boxes, panels, decorative lines, grids, or fake layout containers.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate qiaomu-ppt background image prompts.")
    parser.add_argument("--subject", required=True, help="Deck subject or theme.")
    parser.add_argument("--route", default="talk_deck", help="Deck route, such as brand_release or talk_deck.")
    parser.add_argument("--accent", default="cyan", help="Single accent color name, such as cyan or red.")
    parser.add_argument("--count", type=int, default=5, help="Number of prompts; default 5, clamped to 3-5.")
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
