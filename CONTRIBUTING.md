# Contributing

Thanks for helping improve Qiaomu PPT.

## Development Setup

```bash
python3 scripts/bootstrap.py --check
python3 scripts/bootstrap.py --install-python
```

Optional tools for full deck verification:

- LibreOffice for PPTX-to-PDF preview.
- Poppler for PDF extraction and thumbnail rendering.
- Noto Sans CJK SC via `python3 scripts/bootstrap.py --download-fonts`.

## Quality Bar

Before opening a PR, run:

```bash
python3 /Users/joe/.agents/skills/qiaomu-meta-skill/scripts/validate_skill.py .
python3 /Users/joe/.agents/skills/qiaomu-meta-skill/scripts/trigger_eval.py . \
  --cases evals/trigger_cases.json \
  --output reports/trigger-eval.json
python3 scripts/url_to_markdown.py "https://example.com" --output-dir /tmp/qiaomu-ppt-url-test
```

For generated deck projects, also run:

```bash
python3 scripts/check_project.py <project_dir>
```

## Design Rules

- Keep default backgrounds calm and content-led.
- Do not add visible per-slide toolchain footers unless the route explicitly needs citations.
- Every source image/chart needs an image slot and overflow policy.
- Do not vendor upstream skill code or templates.
- Keep Chinese-first usability and CJK typography in mind.

## Security

Do not commit API keys, cookies, private documents, exported paid content, or user source material.
