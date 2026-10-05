"""Split a SQL file into the single statements asyncpg runs one at a time (migration 0002).

Every test here fails until `app/db/sqlsplit.py` exists. The last test splits the real schema file,
so a statement the splitter would cut in the wrong place shows up here and not in a migration.
"""

from pathlib import Path

from app.db.sqlsplit import split_statements


def test_statements_are_split_on_semicolons() -> None:
    assert split_statements("CREATE TABLE a (id int);\nCREATE TABLE b (id int);") == [
        "CREATE TABLE a (id int)",
        "CREATE TABLE b (id int)",
    ]


def test_a_semicolon_inside_a_quoted_string_does_not_end_a_statement() -> None:
    sql = "COMMENT ON TABLE a IS 'one; two; it''s three';\nSELECT 1;"

    assert split_statements(sql) == ["COMMENT ON TABLE a IS 'one; two; it''s three'", "SELECT 1"]


def test_a_semicolon_in_a_comment_is_ignored_and_the_comment_is_dropped() -> None:
    sql = "-- first; second\nSELECT 1; -- trailing; note\nSELECT 2;"

    assert split_statements(sql) == ["SELECT 1", "SELECT 2"]


def test_a_dollar_quoted_function_body_is_one_statement() -> None:
    sql = "CREATE FUNCTION f() RETURNS int LANGUAGE sql AS $$ SELECT 1; SELECT 2; $$;\nSELECT 3;"

    statements = split_statements(sql)

    assert len(statements) == 2
    assert statements[0].endswith("$$")
    assert "SELECT 1; SELECT 2;" in statements[0]


def test_begin_and_commit_are_dropped_because_alembic_owns_the_transaction() -> None:
    assert split_statements("BEGIN;\nSELECT 1;\nCOMMIT;") == ["SELECT 1"]


def test_the_design_schema_splits_into_whole_statements() -> None:
    statements = split_statements(Path("docs/design/schema.sql").read_text(encoding="utf-8"))
    heads = [" ".join(statement.split()[:2]) for statement in statements]

    assert set(heads) <= {"CREATE TYPE", "CREATE TABLE", "COMMENT ON", "CREATE INDEX"} | {
        "CREATE UNIQUE",
        "CREATE FUNCTION",
        "CREATE TRIGGER",
    }
    assert heads.count("CREATE TABLE") == 12
    assert heads.count("CREATE FUNCTION") == 2
    assert heads.count("CREATE TRIGGER") == 2
    assert heads.count("CREATE TYPE") == 8
