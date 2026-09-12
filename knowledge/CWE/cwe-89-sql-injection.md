# CWE-89: SQL Injection

## Description
The product builds a SQL query using externally-influenced input, but it
does not neutralize or separate special elements that could modify the
intended query structure. An attacker who controls part of the input can
alter the query's logic — for example, turning a single-row lookup into
a full-table dump, or adding a second statement.

## Typical vulnerable shape
```
query = "SELECT * FROM users WHERE username = '" + username + "'"
cursor.execute(query)
```
If `username` is `' OR '1'='1`, the resulting query returns every row in
the table instead of the intended single user.

## Fix
Use parameterized queries so the driver treats the value as data, never
as part of the SQL grammar:
```
cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
```

## Recommendation for reviewers
Any string concatenation or f-string used to build a query that includes
a variable derived from user/request input should be treated as HIGH
severity until proven otherwise (e.g. proven to come from a trusted,
already-validated internal source).
