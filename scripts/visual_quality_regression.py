#!/usr/bin/env python3
"""Regression checks for Qiaomu PPT visual hygiene.

This is intentionally small and fast: it verifies that the generic SVG renderer
uses the CJK-first font strategy and that strict visual lint catches recurring
weak CJK font heads and repeated decorative red rules.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "svg_deck_from_slide_plan.py"
CHECKER = ROOT / "scripts" / "svg_quality_checker.py"


def run(cmd: list[str], *, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if expect_ok and proc.returncode != 0:
        raise SystemExit(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    if not expect_ok and proc.returncode == 0:
        raise SystemExit(f"Command unexpectedly passed: {' '.join(cmd)}\n{proc.stdout}")
    return proc


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_good_project(project: Path) -> None:
    write_json(
        project / "slide_plan.json",
        {
            "slides": [
                {
                    "title": "中文标题应该优先使用好字体",
                    "content_points": ["用字号、字重、对比和留白建立层级，而不是默认红色下划线。"],
                    "visual_role": "cover",
                    "layout_pattern_id": "L01",
                },
                {
                    "title": "知识结构如何被看见",
                    "content_points": ["关系线只在表达结构时出现。", "装饰线默认关闭。"],
                    "visual_role": "mechanism",
                    "layout_pattern_id": "L24",
                },
                {
                    "title": "证据页保持安静",
                    "content_points": ["中性细线承担分隔，强调色只编码内容。"],
                    "visual_role": "evidence",
                    "layout_pattern_id": "L20",
                },
                {
                    "title": "最终判断回到内容",
                    "content_points": ["缩略图应该先看到主题与层级，而不是模板习惯。"],
                    "visual_role": "closing",
                    "layout_pattern_id": "L35",
                },
            ]
        },
    )
    write_json(
        project / "style_direction.json",
        {
            "selected_style": {"id": "source-backed-editorial", "label": "Source-backed Editorial"},
            "style_contract": {
                "typography": "Use Noto Sans CJK SC for Chinese display and body; use Sarasa Mono SC for mono snippets.",
                "palette": {
                    "primary": "#2F66D0",
                    "canvas": "#F4EFE4",
                    "swatches": [
                        {"role": "paper canvas", "hex": "#F4EFE4"},
                        {"role": "primary blue", "hex": "#2F66D0"},
                        {"role": "rule line", "hex": "#C8BDAA"},
                    ],
                },
            },
        },
    )


def build_bad_svg(path: Path) -> None:
    path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<text x="80" y="120" font-family="Georgia, SimSun, serif" font-size="44">中文坏字体栈</text>
<line x1="80" y1="160" x2="180" y2="160" stroke="#C8472C" stroke-width="3"/>
<line x1="80" y1="220" x2="180" y2="220" stroke="#C8472C" stroke-width="3"/>
</svg>
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run qiaomu-ppt visual hygiene regression checks.")
    parser.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="qiaomu-ppt-visual-regression-"))
    try:
        good_project = tmp / "good"
        build_good_project(good_project)
        run([sys.executable, str(RENDERER), str(good_project), "--force"])
        run([sys.executable, str(CHECKER), str(good_project / "svg_output"), "--expected-format", "ppt169", "--strict-visual"])

        bad_svg = tmp / "bad.svg"
        build_bad_svg(bad_svg)
        bad_result = run([sys.executable, str(CHECKER), str(bad_svg), "--strict-visual"], expect_ok=False)
        if "weak primary display font" not in bad_result.stdout or "decorative underlines" not in bad_result.stdout:
            raise SystemExit(f"Strict visual lint did not report both expected issues:\n{bad_result.stdout}")

        print("[OK] visual_quality_regression passed")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
