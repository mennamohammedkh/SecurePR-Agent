# Secure Coding Checklist (general)

A short, practical checklist to apply during code review, independent of
any single vulnerability class.

## Input handling
- Validate/allow-list input at the boundary (API endpoint, CLI arg,
  file parser) rather than deep inside business logic.
- Never trust a client-supplied field for authorization decisions.

## Output handling
- Escape/encode output for the context it will be rendered in (HTML,
  SQL, shell, log file) — a value that's safe in one context may not be
  safe in another.

## Secrets
- No credentials, tokens, or private keys in source code or commit
  history. Use environment variables or a secret manager.

## Error handling
- Don't leak stack traces, internal paths, or database errors to
  end users; log them internally instead.
- Fail closed on unexpected errors in security-relevant code paths
  (auth checks, input guardrails) rather than defaulting to "allow".

## Dependencies
- Pin dependency versions; review new dependencies before adding them.

## Review flag guidance
When a PR touches authentication, authorization, data access (SQL/ORM),
or anything parsing external input (webhooks, file uploads, deserializing
untrusted payloads), it should be treated as higher-risk and reviewed
against this checklist even if the diff looks small.
