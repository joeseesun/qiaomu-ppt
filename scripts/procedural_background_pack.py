#!/usr/bin/env python3
"""Generate deterministic atmosphere-only procedural PPT backgrounds."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path


ROLES = [
    ("cover_atmosphere", "opening statement background"),
    ("dark_evidence", "dark proof background"),
    ("light_evidence", "light dense-chart background"),
    ("diagram_focus", "architecture/process background"),
    ("closing_atmosphere", "closing action background"),
]

LIBRARY_GUIDANCE = {
    "css": ["linear-gradient", "radial-gradient", "filter blur", "mix-blend-mode"],
    "svg": ["gradients", "filters", "feTurbulence", "large abstract paths"],
    "canvas": ["canvas-sketch", "p5.js", "Pts.js", "Paper.js", "Two.js", "Simplex-noise", "Noise.js"],
    "webgl": ["GLSL Canvas", "Regl", "OGL", "Curtains.js"],
    "animation": ["Motion Canvas", "Theatre.js", "Anime.js"],
}

NEGATIVE_CONSTRAINTS = [
    "text",
    "letters",
    "numbers",
    "logo",
    "icon",
    "UI chrome",
    "chart",
    "table",
    "diagram",
    "screenshot",
    "mockup",
    "box",
    "rectangle-as-container",
    "card",
    "panel",
    "frame",
    "window",
    "placeholder",
    "layout scaffolding",
    "image slot",
    "chart area",
    "content block",
    "grid",
    "rail",
]


def stable_seed(subject: str, route: str, role: str, seed: str | None) -> int:
    raw = f"{seed or 'qiaomu-ppt'}:{subject}:{route}:{role}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:16], 16)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError("accent must be a 6-digit hex color such as 00D9FF")
    return int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def role_palette(role: str, accent: tuple[int, int, int]) -> dict[str, str]:
    if role == "light_evidence":
        base = (246, 248, 251)
        mid = (229, 237, 244)
        ink = mix(base, accent, 0.11)
    else:
        base = (6, 15, 23)
        mid = (9, 28, 38)
        ink = mix(base, accent, 0.18)
    return {
        "base": rgb_hex(base),
        "mid": rgb_hex(mid),
        "accent": rgb_hex(accent),
        "accent_soft": rgb_hex(mix(base, accent, 0.38)),
        "ink": rgb_hex(ink),
    }


def blob_path(rng: random.Random, cx: float, cy: float, rx: float, ry: float, points: int = 9) -> str:
    coords: list[tuple[float, float]] = []
    for idx in range(points):
        angle = (math.tau * idx / points) + rng.uniform(-0.12, 0.12)
        radius = rng.uniform(0.82, 1.16)
        coords.append((cx + math.cos(angle) * rx * radius, cy + math.sin(angle) * ry * radius))
    commands = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    for idx, current in enumerate(coords):
        nxt = coords[(idx + 1) % points]
        c1 = (current[0] * 0.65 + nxt[0] * 0.35, current[1] * 0.65 + nxt[1] * 0.35)
        c2 = (current[0] * 0.35 + nxt[0] * 0.65, current[1] * 0.35 + nxt[1] * 0.65)
        commands.append(f"C {c1[0]:.1f} {c1[1]:.1f}, {c2[0]:.1f} {c2[1]:.1f}, {nxt[0]:.1f} {nxt[1]:.1f}")
    commands.append("Z")
    return " ".join(commands)


def svg_background(role: str, subject: str, route: str, accent_hex: str, seed: str | None) -> str:
    rng = random.Random(stable_seed(subject, route, role, seed))
    accent = hex_to_rgb(accent_hex)
    palette = role_palette(role, accent)
    width, height = 1920, 1080
    blur = 90 if role != "light_evidence" else 70
    opacity = "0.28" if role != "light_evidence" else "0.18"
    noise_opacity = "0.075" if role != "light_evidence" else "0.045"

    blobs = []
    anchors = [
        (rng.uniform(1250, 1740), rng.uniform(-80, 250), rng.uniform(420, 720), rng.uniform(260, 520)),
        (rng.uniform(-160, 420), rng.uniform(680, 1140), rng.uniform(380, 700), rng.uniform(240, 440)),
        (rng.uniform(760, 1360), rng.uniform(380, 960), rng.uniform(300, 520), rng.uniform(200, 380)),
    ]
    for idx, (cx, cy, rx, ry) in enumerate(anchors):
        fill = "accentSoft" if idx == 0 else "inkGlow"
        blobs.append(
            f'<path d="{blob_path(rng, cx, cy, rx, ry)}" fill="url(#{fill})" opacity="{opacity}"/>'
        )

    if role == "diagram_focus":
        for idx in range(10):
            cx = 250 + idx * 160 + rng.uniform(-20, 20)
            cy = 540 + math.sin(idx * 0.9) * 90 + rng.uniform(-25, 25)
            r = rng.uniform(3.5, 8.0)
            blobs.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{palette["accent"]}" opacity="0.10"/>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{role} atmosphere background">
  <defs>
    <linearGradient id="baseGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{palette["base"]}"/>
      <stop offset="55%" stop-color="{palette["mid"]}"/>
      <stop offset="100%" stop-color="{palette["base"]}"/>
    </linearGradient>
    <radialGradient id="accentSoft" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{palette["accent"]}" stop-opacity="0.52"/>
      <stop offset="100%" stop-color="{palette["accent"]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="inkGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{palette["ink"]}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{palette["ink"]}" stop-opacity="0"/>
    </radialGradient>
    <filter id="softBlur" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="{blur}"/>
    </filter>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.72" numOctaves="2" seed="{stable_seed(subject, route, role, seed) % 997}"/>
      <feColorMatrix type="saturate" values="0"/>
      <feComponentTransfer>
        <feFuncA type="table" tableValues="0 {noise_opacity}"/>
      </feComponentTransfer>
    </filter>
  </defs>
  <path d="M0 0H{width}V{height}H0Z" fill="url(#baseGrad)"/>
  <g filter="url(#softBlur)">
    {"".join(blobs)}
  </g>
  <path d="M0 0H{width}V{height}H0Z" filter="url(#grain)" opacity="0.85"/>
</svg>
'''


def css_snippet(role: str, accent_hex: str) -> str:
    accent = "#" + accent_hex.strip().lstrip("#")
    dark = role != "light_evidence"
    base = "#071018" if dark else "#F6F8FB"
    mid = "#0A2430" if dark else "#EAF1F6"
    return (
        f".qiaomu-bg-{role} {{\n"
        f"  background:\n"
        f"    radial-gradient(circle at 78% 18%, color-mix(in srgb, {accent} 22%, transparent), transparent 34%),\n"
        f"    radial-gradient(circle at 18% 88%, color-mix(in srgb, {accent} 10%, transparent), transparent 30%),\n"
        f"    linear-gradient(135deg, {base}, {mid} 56%, {base});\n"
        "}\n"
    )


def create_pack(subject: str, route: str, accent: str, output_dir: Path, seed: str | None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for role, usage in ROLES:
        svg = svg_background(role, subject, route, accent, seed)
        filename = f"bg-{role}.svg"
        path = output_dir / filename
        path.write_text(svg, encoding="utf-8")
        assets.append(
            {
                "role": role,
                "usage": usage,
                "path": filename,
                "engine": "svg",
                "css_fallback": css_snippet(role, accent),
                "negative_constraints": NEGATIVE_CONSTRAINTS,
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "subject": subject,
        "route": route,
        "seed": seed or "qiaomu-ppt",
        "accent": "#" + accent.strip().lstrip("#").upper(),
        "policy": "procedural atmosphere-only backgrounds; layout remains editable foreground",
        "library_guidance": LIBRARY_GUIDANCE,
        "assets": assets,
    }
    (output_dir / "procedural_backgrounds.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 5 deterministic procedural qiaomu-ppt backgrounds.")
    parser.add_argument("--subject", required=True, help="Deck subject or theme.")
    parser.add_argument("--route", default="talk_deck", help="Deck route, such as brand_release or talk_deck.")
    parser.add_argument("--accent", default="00D9FF", help="Single accent color as 6-digit hex, default 00D9FF.")
    parser.add_argument("--seed", help="Optional deterministic seed.")
    parser.add_argument("--output-dir", "-o", required=True, help="Directory for SVG assets and procedural_backgrounds.json.")
    args = parser.parse_args()

    manifest = create_pack(args.subject, args.route, args.accent, Path(args.output_dir), args.seed)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
