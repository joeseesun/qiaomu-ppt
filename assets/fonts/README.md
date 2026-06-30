# Fonts

`qiaomu-ppt` uses a small presentation font kit so public installs can render
Chinese-first decks consistently. The font binaries are not committed to the
public repository; download them locally when you need full PPTX/preview
fidelity.

Curated families:

- Noto Sans CJK SC: default Simplified Chinese body, title, and classroom-safe deck text.
- Noto Serif CJK SC: editorial Chinese headings, quote slides, and reading-heavy chapter pages.
- Inter Variable: modern Latin titles, product decks, UI labels, and large numbers.
- IBM Plex Sans: stable Latin body text, technical captions, and static-font fallback.
- Smiley Sans: distinctive short Chinese display titles for covers and campaign-like pages.
- LXGW WenKai: warmer courseware, reading, and reflective Chinese pages.
- Sarasa Mono SC: CJK/Latin aligned code blocks, terminal text, and monospace tables.
- JetBrains Mono: Latin code and developer-oriented monospace labels.

Optional packs are declared in `data/font_manifest.json`:

- `display`: Smiley Sans for high-impact cover titles.
- `courseware`: LXGW WenKai for classroom and reading decks.
- `code`: Sarasa Mono SC and JetBrains Mono for code, CLI, and aligned CJK/Latin snippets.

The recommended font binaries are licensed under the SIL Open Font License 1.1.
See `OFL.txt` in this directory and `data/font_manifest.json` for source URLs,
license URLs, roles, and recommended stacks.

Re-download or repair the bundled fonts with:

```bash
python3 scripts/bootstrap.py --download-fonts
```

Sarasa Mono SC is distributed upstream as a `.7z` archive; repairing it requires
`bsdtar`, `7zz`, or `7z`. If those tools are missing, the skill will fall back to
system CJK and Latin fonts and record typography fidelity as missing evidence
when needed.

If the fonts are missing in a downstream install, generated decks should record
exact typography as missing evidence and fall back to system CJK and Latin fonts.
