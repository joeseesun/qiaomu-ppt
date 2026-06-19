# Fonts

`qiaomu-ppt` declares open-source CJK fonts in `data/font_manifest.json`.

Download them locally with:

```bash
python3 scripts/bootstrap.py --download-fonts
```

Font binaries are ignored by git to keep the open-source package small. If the
fonts are missing, generated decks should record exact typography as missing
evidence and fall back to system CJK fonts.
