# Security Policy

## Reporting

Please report security issues privately to the maintainer before opening a public issue.

- X: https://x.com/vista8
- GitHub: https://github.com/joeseesun/

## Sensitive Data

Qiaomu PPT should never store or print:

- API keys, cookies, passwords, access tokens, or private certificates.
- Private source documents unless the user explicitly provides them for local processing.
- Login-only page content in public examples.

If URL ingestion cannot access a page without credentials, it should record `missing_evidence` instead of fabricating success.

## Supported Versions

The public repository tracks the latest release on `main`.
