# supabase/migrations

Postgres migrations for Supabase.

- `20261109000000_initial_schema.sql` — the 18 tables of SPEC 8.1 with tenant RLS. The tenant comes from the JWT (`app_metadata.tenant_id`); policies exist only for the `authenticated` role; every foreign key includes `tenant_id`; `approval` and `audit_event` are append-only.

**Status: not executed.** There is no local Postgres. The migration is parsed with the Postgres parser and compared with `schemas/entities/` by `tests/test_schemas.py`. Applying it to a Supabase project needs Dante's approval, and RLS is exercised with the second synthetic tenant in Phase 7.
