# Chinese Typography And Layout

Use this reference whenever a deck contains Chinese/CJK copy, when the user
complains about spacing, or when a deck is meant for Qiaomu public release.

Sources to internalize:

- W3C Chinese Layout Requirements (CLReq), <https://www.w3.org/TR/clreq/>:
  character flow, punctuation,
  interlinear notes, mixed Latin/CJK behavior, and the principle that Chinese
  layout depends on rhythm and readable line boxes, not arbitrary decoration.
- Chinese Copywriting Guidelines,
  <https://github.com/sparanoid/chinese-copywriting-guidelines>: Chinese
  punctuation, spacing around Latin
  letters/numbers, and avoiding random spaces between Chinese characters.
- Microsoft PowerPoint paragraph controls,
  <https://support.microsoft.com/en-us/powerpoint/change-text-alignment-indentation-and-spacing-in-powerpoint>:
  line spacing and paragraph spacing are available controls, so title/body
  crowding is a production failure, not a tool limitation.
- Google/Adobe Noto CJK and Source Han families:
  <https://github.com/notofonts/noto-cjk>,
  <https://github.com/adobe-fonts/source-han-sans>, and
  <https://github.com/adobe-fonts/source-han-serif>. Use broad CJK families for
  reliable coverage before choosing expressive decorative fonts.
- Other useful font sources to license-check before bundling:
  <https://hyperos.mi.com/font/en/>,
  <https://www.alibabafonts.com/>, and
  <https://github.com/lxgw/LxgwWenKai>.

## Hard Rules

- Do not add default background grid lines, guide lines, ruled-paper lines,
  visible construction lines, decorative line overlays, "tech lines", or
  abstract stripes unless the user explicitly asks for that device.
- Lines are allowed only as chart axes/series, table rules, diagram connectors,
  process/timeline paths, map routes, focus underlines, separators, or shape
  borders with a declared semantic purpose.
- If a background still needs texture, use quiet color fields, image atmosphere,
  grain, paper tone, soft light, or subject-specific bitmap imagery instead of
  linework.
- A title and its body text must never look attached. If the slide has a
  headline, subtitle, body, chips, source note, and media object, each needs its
  own rhythm zone.
- At thumbnail size, the viewer must still see where the title ends and where
  the proof/body begins. If the title and body collapse into one block, the
  slide fails.

## Chinese Font Defaults

Use at most two font families and three weights in one deck unless a supplied
brand guide requires more.

Recommended default stacks:

- Neutral report/courseware/UI: `Noto Sans CJK SC`, `Source Han Sans SC`,
  `MiSans`, `Alibaba PuHuiTi`, `HarmonyOS Sans SC`, `Microsoft YaHei`,
  `PingFang SC`, sans-serif.
- Editorial/literary/culture: `Noto Serif CJK SC`, `Source Han Serif SC`,
  `Songti SC`, `SimSun`, serif. Use serif body only when the deck is image-rich
  or editorial and the screenshots prove readability.
- Friendly handwritten/teaching accents: `LXGW WenKai`, `Kaiti SC`, `KaiTi`.
  Use these for covers, quotes, section markers, or short labels, not dense
  body paragraphs unless previewed.
- Technical/code-adjacent labels: pair a CJK sans with a monospace only for
  code, numbers, file names, or API tokens. Do not set Chinese body text in a
  monospace face.

Always verify font licensing before packaging a downloadable template. Prefer
installed or bundled open-source fonts for generated PPTX files.

## Slide Spacing Tokens

For a 16:9 slide rendered around `1280x720`:

- Outer margins: normal slides `64-96px`; dense report slides may go to `48px`
  only if text remains readable.
- Cover title leading: CJK line-height `1.08-1.18`; ordinary multi-line titles
  `1.14-1.30`.
- Body leading: `1.45-1.75` for Chinese paragraphs; dense labels may use
  `1.25-1.40` only when they are short.
- Title-to-subtitle gap: at least `18-28px`.
- Title-to-body/proof gap: at least `36-56px`, or `0.55-0.80` of the title
  line-height, whichever is larger.
- Body paragraph gap: `0.6-1.0` of the body line-height.
- Chips, badges, source notes, and captions: keep at least `24-36px` away from
  body copy or visual proof objects unless they are attached labels.
- Media clearance from title/body: default `28px` minimum, more when the media
  edge is visually busy.

For PPTX coordinates, treat `0.22in` as the minimum normal clearance and
increase it for Chinese headlines or image-rich slides.

## Chinese Copy And Line Length

- Use Chinese punctuation for Chinese sentences. Do not add spaces between
  Chinese characters.
- Keep Latin letters/numbers readable in mixed copy; apply a consistent
  half-space or font fallback strategy around English and numbers when the
  renderer supports it.
- Avoid long unbroken Chinese paragraphs on slides. Prefer 1 claim sentence plus
  2-4 short evidence chunks.
- Practical line length targets:
  - Large claim/body text: `12-24` Chinese characters per line.
  - Compact explanation panels: `18-32` Chinese characters per line.
  - Dense tables and labels: shorter labels beat wrapped paragraphs.
- Do not use negative letter spacing as a generic cinematic shortcut for CJK.
  Use weight, size, contrast, line breaks, and whitespace instead.

## QA Checklist

Before final export or upload:

- Inspect every thumbnail: title/body separation must be visible without zooming
  in.
- Inspect the first page of each section: no decorative background linework
  should be present unless explicitly approved and semantically named.
- Check all Chinese titles for awkward line breaks, crushed punctuation,
  negative letter spacing, and overly tight leading.
- Check body text at presentation size and mobile preview size; if it reads like
  a screenshot caption or a web card, simplify.
- If a slide feels "designed" only because of lines, grids, rails, or borders,
  delete the decoration and rebuild hierarchy with typography, spacing, media,
  or real proof objects.
