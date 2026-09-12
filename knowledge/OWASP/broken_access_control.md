# Broken Access Control & Authentication Weaknesses

Access control enforces that a user can only perform actions and access
data they are actually permitted to. Authentication weaknesses let an
attacker bypass proving who they are in the first place. In PR review,
these two are often tangled together (a login or permissions-check
change).

## Common patterns to flag in code review
- A route or function that reads an ID from the request (e.g.
  `user_id` in a URL) and fetches/updates that record without checking
  the current session actually owns it (IDOR — Insecure Direct Object
  Reference).
- Authentication logic that trusts a client-supplied field (e.g. a
  `role` or `is_admin` flag sent in the request body) instead of
  deriving it server-side from a verified session/token.
- Password or token comparisons using `==` instead of a constant-time
  comparison, which can leak timing information.
- Missing checks after a permission failure (log the failure but still
  continue executing the privileged action).

## Recommended mitigation
- Re-derive the acting user's identity and permissions server-side on
  every request; never trust a role/permission value sent by the client.
- Check object ownership/scope explicitly before returning or mutating a
  resource.
- Use vetted authentication libraries/frameworks rather than hand-rolled
  session or token logic.
- Fail closed: on any exception or unexpected state in an auth check,
  deny access by default.
