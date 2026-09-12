# Injection (SQL, Command, and related)

Injection flaws happen when untrusted input is passed into an interpreter
(a SQL query, a shell command, an LDAP query, etc.) as part of a command
or query, without separating the data from the instruction. The
interpreter ends up executing part of the attacker's input as code.

## Common patterns to flag in code review
- Building a SQL query by concatenating or f-string-formatting a raw
  user-controlled value directly into the query string, instead of using
  placeholders.
- Passing user input straight into `subprocess`, `os.system`, or `eval`
  calls.
- Building LDAP or XPath queries the same way as SQL, by string
  concatenation.

## Recommended mitigation
- Use parameterized queries / prepared statements (e.g. `cursor.execute(
  "SELECT * FROM users WHERE id = %s", (user_id,))`) so the database
  driver keeps data and code separate.
- Use an ORM's query builder instead of raw SQL where practical.
- Allow-list validate any input that must be used to build a command or
  identifier that can't be parameterized.
- Apply least privilege to the database account used by the application.

## Severity notes for risk scoring
Injection that can affect data confidentiality/integrity (e.g. an
attacker-controlled `WHERE` clause) is typically HIGH severity. Injection
limited to a low-privilege, tightly-scoped context (e.g. a hardcoded
allow-list of values) may be scored lower, but should still be flagged.
