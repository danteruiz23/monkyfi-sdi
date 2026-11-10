-- Monkyfi Service Delivery Intelligence — initial schema (SPEC 8.1, 8.2) with tenant RLS (D05, D16).
-- Every table carries tenant_id and is_synthetic. The tenant table is the exception: its id is the tenant.
-- Foreign keys include tenant_id, so a row can never reference a row of another tenant.
-- Keep in sync with schemas/entities/*.schema.json (tests/test_schema_agreement.py).

create table public.tenant (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (name)
);

create table public.customer (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  name text not null,
  type text not null check (type in ('enterprise', 'hyperscaler')),
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, name)
);

create table public.project (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  customer_id uuid not null,
  name text not null,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, customer_id) references public.customer (tenant_id, id)
);

create table public.supplier (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  name text not null,
  follow_up_threshold_days integer not null,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  check (follow_up_threshold_days > 0)
);

create table public.shared_resource (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  kind text not null,
  description text not null,
  is_blocked boolean not null,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id)
);

create table public.service_order (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  project_id uuid,
  customer_id uuid not null,
  external_order_id text not null,
  product text not null check (product in ('EPL', 'WAVELENGTH')),
  stage text not null check (stage in ('presales', 'order_received', 'order_validated', 'design_and_dependencies', 'provisioning', 'ready_for_testing', 'testing_completed', 'delivered_pending_acceptance', 'accepted', 'hypercare', 'closed', 'cancelled', 'pending_correction')),
  is_blocked boolean not null,
  blocked_reason text,
  blocked_since timestamptz,
  blocked_owner text,
  current_version_id uuid,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (tenant_id, external_order_id),
  check (not is_blocked or blocked_reason is not null),
  foreign key (tenant_id, project_id) references public.project (tenant_id, id),
  foreign key (tenant_id, customer_id) references public.customer (tenant_id, id)
);

create table public.order_version (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  service_order_id uuid not null,
  version_no integer not null,
  received_at timestamptz not null,
  supersedes_id uuid,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (service_order_id, version_no),
  check (version_no >= 1),
  foreign key (tenant_id, service_order_id) references public.service_order (tenant_id, id),
  foreign key (tenant_id, supersedes_id) references public.order_version (tenant_id, id)
);

create table public.document (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  order_version_id uuid not null,
  doc_type text not null check (doc_type in ('quote', 'order_form', 'technical_annex', 'loa_cfa', 'email', 'test_report', 'other')),
  filename text not null,
  file_hash text not null,
  ingested_at timestamptz not null,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, order_version_id) references public.order_version (tenant_id, id)
);

create table public.endpoint (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  order_version_id uuid not null,
  side text not null check (side in ('A', 'Z')),
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  unique (order_version_id, side),
  foreign key (tenant_id, order_version_id) references public.order_version (tenant_id, id)
);

create table public.field_value (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  order_version_id uuid not null,
  endpoint_id uuid,
  field_key text not null,
  raw_value text,
  normalized_value jsonb,
  status text not null check (status in ('verified', 'pending', 'missing', 'not_applicable', 'contradictory', 'stale')),
  source_document_id uuid,
  source_location text,
  fact_timestamp timestamptz,
  ingested_at timestamptz not null,
  extracted_by text not null check (extracted_by in ('model', 'rule', 'human')),
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  check (raw_value is null or (source_document_id is not null and source_location is not null)),
  foreign key (tenant_id, order_version_id) references public.order_version (tenant_id, id),
  foreign key (tenant_id, endpoint_id) references public.endpoint (tenant_id, id),
  foreign key (tenant_id, source_document_id) references public.document (tenant_id, id)
);

create table public.approval (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  entity text not null,
  entity_id uuid not null,
  decision text not null check (decision in ('approved', 'rejected', 'override')),
  approver text not null,
  reason text,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  check (decision <> 'override' or reason is not null)
);

create table public.finding (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  service_order_id uuid not null,
  order_version_id uuid not null,
  rule_id text not null,
  field_key text,
  severity text not null check (severity in ('critical', 'high', 'medium', 'info')),
  conflicting_values jsonb not null,
  evidence jsonb not null,
  impact text not null check (impact in ('confirmed', 'possible')),
  owner text,
  due_date date,
  action text,
  status text not null check (status in ('open', 'in_progress', 'resolved', 'overridden')),
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, service_order_id) references public.service_order (tenant_id, id),
  foreign key (tenant_id, order_version_id) references public.order_version (tenant_id, id)
);

create table public.gate_evaluation (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  order_version_id uuid not null,
  gate text not null check (gate in ('G0', 'G1', 'G2', 'G3', 'G4', 'G5')),
  recommendation text not null check (recommendation in ('pass', 'block')),
  unmet_requirements jsonb not null,
  evaluated_at timestamptz not null,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, order_version_id) references public.order_version (tenant_id, id)
);

create table public.milestone (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  service_order_id uuid not null,
  name text not null,
  owner text,
  is_critical boolean not null,
  requested_date date,
  forecast_date date,
  forecast_assumptions text,
  forecast_status text not null check (forecast_status in ('pending', 'estimated', 'not_estimable')),
  committed_date date,
  commitment_approval_id uuid,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  check (forecast_date is null or forecast_assumptions is not null),
  check (committed_date is null or commitment_approval_id is not null),
  foreign key (tenant_id, service_order_id) references public.service_order (tenant_id, id),
  foreign key (tenant_id, commitment_approval_id) references public.approval (tenant_id, id)
);

create table public.dependency (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  service_order_id uuid not null,
  from_milestone_id uuid,
  to_milestone_id uuid,
  kind text not null check (kind in ('internal', 'supplier', 'customer')),
  shared_resource_id uuid,
  supplier_id uuid,
  description text,
  owner text,
  due_date date,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, service_order_id) references public.service_order (tenant_id, id),
  foreign key (tenant_id, from_milestone_id) references public.milestone (tenant_id, id),
  foreign key (tenant_id, to_milestone_id) references public.milestone (tenant_id, id),
  foreign key (tenant_id, shared_resource_id) references public.shared_resource (tenant_id, id),
  foreign key (tenant_id, supplier_id) references public.supplier (tenant_id, id)
);

create table public.evidence (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  service_order_id uuid not null,
  kind text not null check (kind in ('test_result', 'acceptance', 'other')),
  document_id uuid,
  covers_requirement text not null,
  verified_by text,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  foreign key (tenant_id, service_order_id) references public.service_order (tenant_id, id),
  foreign key (tenant_id, document_id) references public.document (tenant_id, id)
);

create table public.communication (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  service_order_id uuid not null,
  audience text not null check (audience in ('internal', 'customer', 'supplier')),
  language text not null check (language in ('en', 'es')),
  status text not null check (status in ('prepared', 'approved', 'sent', 'failed')),
  body text not null,
  source_refs jsonb not null,
  approval_id uuid,
  channel_confirmation text,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id),
  check (status not in ('approved', 'sent') or approval_id is not null),
  check (status <> 'sent' or channel_confirmation is not null),
  foreign key (tenant_id, service_order_id) references public.service_order (tenant_id, id),
  foreign key (tenant_id, approval_id) references public.approval (tenant_id, id)
);

create table public.audit_event (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenant (id),
  actor text not null,
  action text not null,
  entity text not null,
  entity_id uuid,
  before jsonb,
  after jsonb,
  model_version text,
  prompt_version text,
  rules_version text,
  is_synthetic boolean not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, id)
);

alter table public.service_order add constraint service_order_current_version_id_fkey foreign key (tenant_id, current_version_id) references public.order_version (tenant_id, id);

-- Indexes on tenant and foreign-key columns.
create index customer_tenant_id_idx on public.customer (tenant_id);
create index project_tenant_id_idx on public.project (tenant_id);
create index project_customer_id_idx on public.project (customer_id);
create index supplier_tenant_id_idx on public.supplier (tenant_id);
create index shared_resource_tenant_id_idx on public.shared_resource (tenant_id);
create index service_order_tenant_id_idx on public.service_order (tenant_id);
create index service_order_project_id_idx on public.service_order (project_id);
create index service_order_customer_id_idx on public.service_order (customer_id);
create index service_order_current_version_id_idx on public.service_order (current_version_id);
create index order_version_tenant_id_idx on public.order_version (tenant_id);
create index order_version_service_order_id_idx on public.order_version (service_order_id);
create index order_version_supersedes_id_idx on public.order_version (supersedes_id);
create index document_tenant_id_idx on public.document (tenant_id);
create index document_order_version_id_idx on public.document (order_version_id);
create index endpoint_tenant_id_idx on public.endpoint (tenant_id);
create index endpoint_order_version_id_idx on public.endpoint (order_version_id);
create index field_value_tenant_id_idx on public.field_value (tenant_id);
create index field_value_order_version_id_idx on public.field_value (order_version_id);
create index field_value_endpoint_id_idx on public.field_value (endpoint_id);
create index field_value_source_document_id_idx on public.field_value (source_document_id);
create index approval_tenant_id_idx on public.approval (tenant_id);
create index finding_tenant_id_idx on public.finding (tenant_id);
create index finding_service_order_id_idx on public.finding (service_order_id);
create index finding_order_version_id_idx on public.finding (order_version_id);
create index gate_evaluation_tenant_id_idx on public.gate_evaluation (tenant_id);
create index gate_evaluation_order_version_id_idx on public.gate_evaluation (order_version_id);
create index milestone_tenant_id_idx on public.milestone (tenant_id);
create index milestone_service_order_id_idx on public.milestone (service_order_id);
create index milestone_commitment_approval_id_idx on public.milestone (commitment_approval_id);
create index dependency_tenant_id_idx on public.dependency (tenant_id);
create index dependency_service_order_id_idx on public.dependency (service_order_id);
create index dependency_from_milestone_id_idx on public.dependency (from_milestone_id);
create index dependency_to_milestone_id_idx on public.dependency (to_milestone_id);
create index dependency_shared_resource_id_idx on public.dependency (shared_resource_id);
create index dependency_supplier_id_idx on public.dependency (supplier_id);
create index evidence_tenant_id_idx on public.evidence (tenant_id);
create index evidence_service_order_id_idx on public.evidence (service_order_id);
create index evidence_document_id_idx on public.evidence (document_id);
create index communication_tenant_id_idx on public.communication (tenant_id);
create index communication_service_order_id_idx on public.communication (service_order_id);
create index communication_approval_id_idx on public.communication (approval_id);
create index audit_event_tenant_id_idx on public.audit_event (tenant_id);
create index field_value_field_key_idx on public.field_value (order_version_id, field_key);

-- Tenant segregation. The tenant comes from the signed JWT (app_metadata.tenant_id), which a user cannot edit.
create schema if not exists app;

create or replace function app.current_tenant_id() returns uuid
language sql stable
set search_path = ''
as $$ select nullif((select auth.jwt()) -> 'app_metadata' ->> 'tenant_id', '')::uuid $$;

grant usage on schema app to authenticated;
grant execute on function app.current_tenant_id() to authenticated;

-- Policies exist only for the authenticated role: anon has no access. The service role bypasses RLS and is
-- used only by server-side jobs. 'append' tables (approval, audit_event) can be read and inserted, never
-- updated or deleted. Role-based permissions inside a tenant are added in Phase 7.

alter table public.tenant enable row level security;
create policy tenant_select on public.tenant for select to authenticated using (id = (select app.current_tenant_id()));

alter table public.customer enable row level security;
create policy customer_select on public.customer for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy customer_insert on public.customer for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy customer_update on public.customer for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy customer_delete on public.customer for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.project enable row level security;
create policy project_select on public.project for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy project_insert on public.project for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy project_update on public.project for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy project_delete on public.project for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.supplier enable row level security;
create policy supplier_select on public.supplier for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy supplier_insert on public.supplier for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy supplier_update on public.supplier for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy supplier_delete on public.supplier for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.shared_resource enable row level security;
create policy shared_resource_select on public.shared_resource for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy shared_resource_insert on public.shared_resource for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy shared_resource_update on public.shared_resource for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy shared_resource_delete on public.shared_resource for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.service_order enable row level security;
create policy service_order_select on public.service_order for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy service_order_insert on public.service_order for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy service_order_update on public.service_order for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy service_order_delete on public.service_order for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.order_version enable row level security;
create policy order_version_select on public.order_version for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy order_version_insert on public.order_version for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy order_version_update on public.order_version for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy order_version_delete on public.order_version for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.document enable row level security;
create policy document_select on public.document for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy document_insert on public.document for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy document_update on public.document for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy document_delete on public.document for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.endpoint enable row level security;
create policy endpoint_select on public.endpoint for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy endpoint_insert on public.endpoint for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy endpoint_update on public.endpoint for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy endpoint_delete on public.endpoint for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.field_value enable row level security;
create policy field_value_select on public.field_value for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy field_value_insert on public.field_value for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy field_value_update on public.field_value for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy field_value_delete on public.field_value for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.approval enable row level security;
create policy approval_select on public.approval for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy approval_insert on public.approval for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));

alter table public.finding enable row level security;
create policy finding_select on public.finding for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy finding_insert on public.finding for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy finding_update on public.finding for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy finding_delete on public.finding for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.gate_evaluation enable row level security;
create policy gate_evaluation_select on public.gate_evaluation for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy gate_evaluation_insert on public.gate_evaluation for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy gate_evaluation_update on public.gate_evaluation for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy gate_evaluation_delete on public.gate_evaluation for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.milestone enable row level security;
create policy milestone_select on public.milestone for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy milestone_insert on public.milestone for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy milestone_update on public.milestone for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy milestone_delete on public.milestone for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.dependency enable row level security;
create policy dependency_select on public.dependency for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy dependency_insert on public.dependency for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy dependency_update on public.dependency for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy dependency_delete on public.dependency for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.evidence enable row level security;
create policy evidence_select on public.evidence for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy evidence_insert on public.evidence for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy evidence_update on public.evidence for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy evidence_delete on public.evidence for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.communication enable row level security;
create policy communication_select on public.communication for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy communication_insert on public.communication for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
create policy communication_update on public.communication for update to authenticated using (tenant_id = (select app.current_tenant_id())) with check (tenant_id = (select app.current_tenant_id()));
create policy communication_delete on public.communication for delete to authenticated using (tenant_id = (select app.current_tenant_id()));

alter table public.audit_event enable row level security;
create policy audit_event_select on public.audit_event for select to authenticated using (tenant_id = (select app.current_tenant_id()));
create policy audit_event_insert on public.audit_event for insert to authenticated with check (tenant_id = (select app.current_tenant_id()));
