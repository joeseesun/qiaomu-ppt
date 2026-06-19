# Fonts

`qiaomu-ppt` bundles Noto Sans CJK SC Regular/Bold so public installs can render
Chinese decks consistently without a separate font download step.

The bundled font binaries are licensed under the SIL Open Font License 1.1. See
`OFL.txt` in this directory and `data/font_manifest.json` for source URLs.

Re-download or repair the bundled fonts with:

```bash
python3 scripts/bootstrap.py --download-fonts
```

If the fonts are missing in a downstream install, generated decks should record
exact typography as missing evidence and fall back to system CJK fonts.
