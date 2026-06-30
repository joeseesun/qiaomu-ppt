## Summary

-

## Verification

- [ ] `python3 scripts/instruction_eval.py --cases evals/instruction_cases.json --output reports/instruction-eval.json --markdown reports/instruction-eval.md`
- [ ] `python3 scripts/source_intake_matrix_smoke.py --output reports/source_intake_matrix_smoke.json --markdown reports/source_intake_matrix_smoke.md`
- [ ] `python3 scripts/visual_quality_regression.py`
- [ ] `python3 scripts/url_to_markdown.py "https://example.com" --output-dir /tmp/qiaomu-ppt-url-test`
- [ ] `python3 scripts/check_project.py <project_dir>` when generated deck artifacts are included

## Design/Content Checklist

- [ ] Default background remains calm and content-led.
- [ ] Images/charts have image slots and overflow policy.
- [ ] Visible slides do not leak internal toolchain metadata.
- [ ] No upstream skill code or proprietary templates are vendored.
- [ ] No secrets or private source materials are committed.
