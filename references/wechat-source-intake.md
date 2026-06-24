# WeChat Source Intake

WeChat public-account articles are special web sources. They often use
MicroMessenger user-agent behavior, lazy images, `data-src`, CDN hotlink
protection, temporary share links, and anti-bot checks. Generic HTML-to-Markdown
tools may extract text but lose images.

## Default Route

When the input host is `mp.weixin.qq.com`, `source_to_markdown.py` first tries
the optional `jackwener/wechat-article-to-markdown` CLI when the command
`wechat-article-to-markdown` is installed. If it is unavailable or fails, the
script marks the input as `source_type: wechat_article`, runs the normal URL
extractor as a baseline, and records specialized open-source candidates in
`source_manifest.json`.

If the baseline extraction has weak text or no images, do not build important
slide claims from it. Use a specialized extractor, ask the user for an exported
copy, or mark the source as partial.

## Open-Source Candidates

These projects were checked as primary GitHub sources on 2026-06-20.

| Project | Why It Matters | Best Fit | Risk |
|---|---|---|---|
| `jackwener/wechat-article-to-markdown` | Uses Camoufox, extracts title/account/time/original link, converts WeChat HTML to Markdown, downloads images to local `images/`, handles code snippets. | Primary optional extractor for single article to Markdown with local images. | Browser dependency and anti-bot behavior can drift. |
| `gxcsoccer/wechat-article-crawler` | Uses MicroMessenger UA, repairs lazy images, exports structured metadata/Markdown, downloads images with `Referer` to bypass hotlink protection. | Python/Crawl4AI route for article plus images. | Requires valid non-expired article URL; high frequency may trigger CAPTCHA/IP blocks. |
| `fengxxc/wechatmp2markdown` | Go CLI/server can convert `mp.weixin.qq.com/s/...` to Markdown and save article images or return a zip in server mode. | Lightweight CLI/server workflows. | Binary/build workflow varies by platform; table support noted as TODO. |
| `Digidai/website2markdown` | General URL-to-Markdown project with WeChat adapter, MicroMessenger UA, and image proxy for hotlink bypass. | Hosted/service-style or MCP-style extraction across many sites. | Larger service surface; review deployment and privacy before use. |
| `NanmiCoder/NewsCrawler` | Multi-platform crawler that includes WeChat, CLI/Web UI/JSON/Markdown/MCP/Claude skill style outputs. | Broader news/content collection workflows. | GPL-3.0 license may be incompatible with bundling into permissive projects. |
| `xzdev/wechat-article-parser` | Small Go parser returning title, author, URL, summary, photos, read time, publish time. | Metadata/image URL parsing experiments. | Minimal project, very small maintenance footprint. |

Microsoft `markitdown` currently has a reported issue where WeChat article
conversion can produce empty Markdown image links. Treat `markitdown` as a
generic fallback, not the preferred WeChat image route.

## Recommended Selection

Use this priority:

1. For a single article inside an agent workflow, use
   `jackwener/wechat-article-to-markdown` first:

   ```bash
   uv tool install wechat-article-to-markdown
   wechat-article-to-markdown "https://mp.weixin.qq.com/s/xxxxxxxx" -o sources/wechat_articles
   ```

   `qiaomu-ppt/scripts/source_to_markdown.py` will call this command
   automatically when it is available.
2. If the primary route fails or needs a Python/Crawl4AI workflow, try
   `gxcsoccer/wechat-article-crawler`.
3. For a local CLI/server utility, try `fengxxc/wechatmp2markdown`.
4. For a larger extraction service that also handles Feishu/Lark, Zhihu, Yuque,
   Notion, and similar sources, evaluate `Digidai/website2markdown`.
5. For platform-wide news collection, evaluate `NanmiCoder/NewsCrawler` and
   confirm GPL-3.0 compatibility before integration.

## PPT Rules

- Save the article body as Markdown and all usable article images under
  `sources/images/`.
- Preserve article title, account name, author, publish time, original URL, and
  extraction route in `source_manifest.json`.
- Use article images only when they are actually fetched or user-provided.
  Do not claim image evidence from an empty `![]()` placeholder.
- If the article is inaccessible, expired, or blocked by anti-bot checks, record
  `wechat_content_not_fetched` or `wechat_images_not_extracted` and ask for an
  export/copy.
- For public decks, consider copyright and fair-use boundaries. WeChat article
  screenshots and images may not be reusable without permission.
