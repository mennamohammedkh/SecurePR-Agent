# CWE-798: Use of Hard-coded Credentials

## Description
Source code contains a password, API key, token, or other secret written
directly into the code (or a config file committed alongside it) instead
of being loaded from a secret manager or environment variable at
runtime. Anyone with read access to the repository (including, in an
open-source or leaked-repo scenario, the public) can read the secret.

## Typical vulnerable shape
```
API_KEY = "sk-live-abc123..."
DB_PASSWORD = "hunter2"
```

## Fix
- Load secrets from environment variables or a secret manager
  (e.g. `os.environ["API_KEY"]`), never as a literal in source.
- Rotate any credential that was ever committed, even if the commit is
  later removed — assume it is compromised once it hits version control.
- Add the relevant files to `.gitignore` and use a `.env.example` with
  placeholder values for documentation.

## Recommendation for reviewers
Treat any literal that looks like a key/token/password assigned directly
in code as HIGH severity, regardless of whether the surrounding feature
seems "internal only" — internal-only assumptions are frequently wrong
once a repo is shared, forked, or made public.
