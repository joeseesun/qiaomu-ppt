# Notices

Qiaomu PPT vendors and adapts selected MIT-licensed SVG/PPTX pipeline code from:

- `hugohe3/ppt-master`
- Copyright (c) 2025-2026 Hugo He
- License: MIT
- Upstream repository: https://github.com/hugohe3/ppt-master

Vendored/adapted areas include the SVG finalization, SVG quality checking, and
SVG-to-native-PPTX conversion scripts under `scripts/`.

The upstream project is used as licensed source code and research inspiration.
`qiaomu-ppt` does not require the upstream skill to be installed or invoked at
runtime.

Qiaomu PPT also adapts the bottom-right raster watermark detection and
patch-healing approach from:

- `Albonire/notebooklm-watermark-remover`
- Copyright (c) 2025 Anderson Fabián González Aparicio
- License: MIT
- Upstream repository: https://github.com/Albonire/notebooklm-watermark-remover

The adapted code is scoped to optional NotebookLM raster watermark cleanup in
`scripts/notebooklm_raster_watermark.py`. It does not require the upstream
project to be installed or invoked at runtime.

Qiaomu PPT project metadata:

- Copyright (c) 向阳乔木
- X: https://x.com/vista8
- GitHub: https://github.com/joeseesun/
