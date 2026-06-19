## Summary

-

## Verification

- [ ] `python3 /Users/joe/.agents/skills/qiaomu-meta-skill/scripts/validate_skill.py .`
- [ ] `python3 /Users/joe/.agents/skills/qiaomu-meta-skill/scripts/trigger_eval.py . --cases evals/trigger_cases.json --output reports/trigger-eval.json`
- [ ] `python3 scripts/url_to_markdown.py "https://example.com" --output-dir /tmp/qiaomu-ppt-url-test`
- [ ] `python3 scripts/check_project.py <project_dir>` when generated deck artifacts are included

## Design/Content Checklist

- [ ] Default background remains calm and content-led.
- [ ] Images/charts have image slots and overflow policy.
- [ ] Visible slides do not leak internal toolchain metadata.
- [ ] No upstream skill code or proprietary templates are vendored.
- [ ] No secrets or private source materials are committed.
