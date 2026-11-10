"""Entity schemas, the SQL migration, and the rows built from the dataset.

There is no local Postgres, so the migration is parsed (pglast uses the real
Postgres parser) and compared with the JSON Schemas. It has not been executed.
"""

import re

import pglast
import pytest
from jsonschema import Draft202012Validator, FormatChecker

import seed
from conftest import ROOT, load

ENTITIES = ROOT / "schemas" / "entities"
MIGRATION = next((ROOT / "supabase" / "migrations").glob("*_initial_schema.sql")).read_text(encoding="utf-8")
SQL_TO_JSON = {"uuid": ("string", "uuid"), "text": ("string", None), "boolean": ("boolean", None),
               "integer": ("integer", None), "date": ("string", "date"), "timestamptz": ("string", "date-time"),
               "jsonb": (None, None)}
ROWS = seed.build_rows()


def parse_tables(sql: str) -> dict[str, dict[str, dict]]:
    """{table: {column: {"type", "nullable", "default", "enum"}}} from the create table statements."""
    tables = {}
    for name, body in re.findall(r"create table public\.(\w+) \((.*?)\n\);", sql, re.S):
        columns = {}
        for line in body.split(",\n"):
            m = re.match(r"\s+(\w+) (uuid|text|boolean|integer|date|timestamptz|jsonb)\b(.*)", line)
            if not m:
                continue  # table constraint
            column, sql_type, rest = m.groups()
            enum = re.search(rf"check \({column} in \((.*?)\)\)", rest)
            columns[column] = {"type": sql_type,
                               "nullable": "not null" not in rest and "primary key" not in rest,
                               "default": " default " in rest,
                               "enum": re.findall(r"'([^']*)'", enum.group(1)) if enum else None}
        tables[name] = columns
    return tables


TABLES = parse_tables(MIGRATION)


def test_migration_is_valid_postgres_sql():
    assert len(pglast.parse_sql(MIGRATION)) > 50


def test_there_are_18_entities_in_both_places():  # SPEC 8.1
    assert sorted(TABLES) == sorted(p.name.removesuffix(".schema.json") for p in ENTITIES.iterdir())
    assert sorted(TABLES) == sorted(seed.TABLES) and len(TABLES) == 18


@pytest.mark.parametrize("table", sorted(TABLES))
class TestEntity:
    def test_json_schema_and_sql_agree(self, table):
        schema = load(ENTITIES / f"{table}.schema.json")
        Draft202012Validator.check_schema(schema)
        columns, properties = TABLES[table], schema["properties"]
        assert schema["additionalProperties"] is False
        assert list(properties) == list(columns), "same columns, same order"
        for name, column in columns.items():
            prop = properties[name]
            if column["enum"]:
                assert [v for v in prop["enum"] if v is not None] == column["enum"], name
                assert (None in prop["enum"]) == column["nullable"], name
                continue
            json_type, json_format = SQL_TO_JSON[column["type"]]
            types = prop.get("type")
            types = types if isinstance(types, list) else [types] if types else []
            assert [t for t in types if t != "null"] == ([json_type] if json_type else []), name
            assert prop.get("format") == json_format, name
            if json_type:
                assert ("null" in types) == column["nullable"], name
        required = [name for name, column in columns.items() if not column["nullable"] and not column["default"]]
        assert schema["required"] == required

    def test_table_carries_tenant_and_synthetic_flag(self, table):
        columns = TABLES[table]
        assert columns["is_synthetic"] == {"type": "boolean", "nullable": False, "default": False, "enum": None}
        if table != "tenant":
            assert columns["tenant_id"]["type"] == "uuid" and not columns["tenant_id"]["nullable"]

    def test_row_level_security_is_enabled_with_tenant_policies(self, table):
        assert f"alter table public.{table} enable row level security;" in MIGRATION
        policies = re.findall(rf"create policy \w+ on public\.{table} for (\w+) to (\w+) (.*);", MIGRATION)
        assert policies and {role for _, role, _ in policies} == {"authenticated"}
        assert "select" in {command for command, _, _ in policies}
        for _, _, condition in policies:
            assert "app.current_tenant_id()" in condition
        if table in ("audit_event", "approval", "tenant"):  # append-only or read-only
            assert not {"update", "delete"} & {command for command, _, _ in policies}

    def test_foreign_keys_cannot_cross_tenants(self, table):
        body = re.search(rf"create table public\.{table} \((.*?)\n\);", MIGRATION, re.S).group(1)
        altered = re.findall(rf"alter table public\.{table} add constraint \w+ (foreign key .*);", MIGRATION)
        for fk in re.findall(r"foreign key \((.*?)\) references public\.\w+ \((.*?)\)", body + "\n".join(altered)):
            assert fk[0].startswith("tenant_id, ") and fk[1] == "tenant_id, id", fk

    def test_rows_match_schema_and_are_synthetic(self, table):
        validator = Draft202012Validator(load(ENTITIES / f"{table}.schema.json"), format_checker=FormatChecker())
        for row in ROWS[table]:
            errors = [e.message for e in validator.iter_errors(row)]
            assert not errors, (row.get("id"), errors)
            assert row["is_synthetic"] is True


def test_row_counts_match_the_dataset():
    assert len(ROWS["tenant"]) == 2
    assert len(ROWS["service_order"]) == 44 + 1  # 44 orders plus one for the second tenant
    assert len(ROWS["order_version"]) == 48 + 1
    assert len(ROWS["shared_resource"]) == 1 and len(ROWS["dependency"]) == 3
    total = sum(len(rows) for rows in ROWS.values())
    assert total == sum(row["is_synthetic"] is True for rows in ROWS.values() for row in rows)


def test_row_references_stay_inside_one_tenant():
    owner = {row["id"]: row.get("tenant_id", row["id"]) for rows in ROWS.values() for row in rows}
    assert len(set(owner.values())) == 2, "two tenants, so segregation can be tested (D16)"
    for table, rows in ROWS.items():
        for row in rows:
            for column, value in row.items():
                if column.endswith("_id") and column not in ("tenant_id", "external_order_id") and value is not None:
                    assert owner[value] == row["tenant_id"], (table, column)


def test_golden_field_values_fit_the_field_value_schema():
    validator = Draft202012Validator(load(ENTITIES / "field_value.schema.json"), format_checker=FormatChecker())
    rows = seed.golden_field_values()
    assert len(rows) > 2500
    for row in rows:
        assert not [e.message for e in validator.iter_errors(row)], row["field_key"]
        assert row["is_synthetic"] is True
        if row["raw_value"] is not None:  # no value without a source
            assert row["source_document_id"] and row["source_location"]
