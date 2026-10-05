"""Split a SQL script into single statements.

asyncpg runs one statement per call, so a migration cannot hand it the whole script. A semicolon
ends a statement only outside single quotes, a `$$` block and a `--` comment. `BEGIN` and `COMMIT`
are dropped: alembic owns the transaction.
"""

_TRANSACTION_WORDS = frozenset({"BEGIN", "COMMIT"})


def split_statements(sql: str) -> list[str]:
    """The statements in `sql`, without comments, in order."""
    statements: list[str] = []
    current: list[str] = []
    in_quote = False
    in_dollar = False
    index = 0
    while index < len(sql):
        char = sql[index]
        pair = sql[index : index + 2]
        if not in_quote and not in_dollar and pair == "--":
            newline = sql.find("\n", index)
            index = len(sql) if newline == -1 else newline
            continue
        if not in_dollar and char == "'":
            in_quote = not in_quote
        elif not in_quote and pair == "$$":
            in_dollar = not in_dollar
            current.append(pair)
            index += 2
            continue
        if char == ";" and not in_quote and not in_dollar:
            _finish(current, statements)
            current = []
        else:
            current.append(char)
        index += 1
    _finish(current, statements)
    return statements


def _finish(current: list[str], statements: list[str]) -> None:
    statement = "".join(current).strip()
    if statement and statement.upper() not in _TRANSACTION_WORDS:
        statements.append(statement)
