"""Database rows for the synthetic dataset.

SYNTHETIC — NOT REAL DATA. Every row has is_synthetic = true.

build_rows() returns the rows that exist before the agent runs: tenants, customers,
projects, suppliers, shared resources, orders, versions, documents and endpoints.
Tables the agent fills (findings, gate evaluations, milestones, communications,
approvals, audit events and field values) stay empty.

golden_field_values() turns the golden labels into field_value-shaped rows. They
exist to check that the field_value schema fits the data; they are expected
answers and must never be loaded as agent output.

IDs are UUIDv5, so the rows are the same on every run.

Usage (from the repo root):
    python data/synthetic/seed.py            # writes data/synthetic/seed/<table>.json (git-ignored)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://monkyfi.example/sdi/synthetic")

TABLES = ["tenant", "customer", "project", "supplier", "shared_resource", "service_order", "order_version",
          "document", "endpoint", "field_value", "approval", "finding", "gate_evaluation", "milestone",
          "dependency", "evidence", "communication", "audit_event"]

SUPPLIERS = ["Supplier Echo Fiber (synthetic)", "Supplier Sierra Access (synthetic)"]
FOLLOW_UP_THRESHOLD_DAYS = 3  # business days to the first follow-up (D55, Proposed default, per supplier)
ESCALATION_THRESHOLD_DAYS = 5  # business days to escalation (D55)

# The second tenant exists only so that tenant segregation can be tested (D16).
SECOND_TENANT_CUSTOMER = "Manufacturer Uniform (synthetic)"
SECOND_TENANT_ORDER = "SYN-BETA-0001"


def uid(*parts) -> str:
    return str(uuid.uuid5(NAMESPACE, "/".join(str(p) for p in parts)))


def load_goldens(data_dir: Path = HERE) -> list[tuple[Path, dict]]:
    return [(p.parent, json.loads(p.read_text(encoding="utf-8")))
            for p in sorted((data_dir / "orders").glob("*/v*/golden.json"))]


def build_rows(data_dir: Path = HERE) -> dict[str, list[dict]]:
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: dict[str, list[dict]] = {table: [] for table in TABLES}
    tenant_name, second_name = manifest["tenant"], manifest["segregation_tenant"]
    tenant, second = uid("tenant", tenant_name), uid("tenant", second_name)

    def add(table: str, tenant_id: str | None = tenant, **values):
        row = {"id": values.pop("id")}
        if table != "tenant":
            row["tenant_id"] = tenant_id
        rows[table].append({**row, **values, "is_synthetic": True})

    add("tenant", id=tenant, name=tenant_name)
    add("tenant", id=second, name=second_name)
    for name in SUPPLIERS:
        add("supplier", id=uid("supplier", name), name=name, follow_up_threshold_days=FOLLOW_UP_THRESHOLD_DAYS,
            escalation_threshold_days=ESCALATION_THRESHOLD_DAYS)

    latest: dict[str, dict] = {}
    for version_dir, golden in load_goldens(data_dir):
        order = golden["order"]
        order_id = order["external_order_id"]
        customer_id = uid("customer", order["customer"])
        if not any(r["id"] == customer_id for r in rows["customer"]):
            add("customer", id=customer_id, name=order["customer"], type=order["customer_type"])
        project_id = None
        if order["project"]:
            project_id = uid("project", order["project"])
            if not any(r["id"] == project_id for r in rows["project"]):
                add("project", id=project_id, customer_id=customer_id, name=order["project"])
        so_id = uid("service_order", order_id)
        version_id = uid("order_version", order_id, order["version_no"])
        add("order_version", id=version_id, service_order_id=so_id, version_no=order["version_no"],
            received_at=order["received_at"],
            supersedes_id=uid("order_version", order_id, order["version_no"] - 1) if order["version_no"] > 1 else None)
        for doc in golden["documents"]:
            content = (version_dir / "documents" / doc["filename"]).read_bytes()
            add("document", id=uid("document", order_id, order["version_no"], doc["doc_id"]),
                order_version_id=version_id, doc_type=doc["doc_type"], filename=doc["filename"],
                file_hash=hashlib.sha256(content).hexdigest(), ingested_at=order["received_at"])
        for side in ("A", "Z"):
            add("endpoint", id=uid("endpoint", order_id, order["version_no"], side),
                order_version_id=version_id, side=side)
        for resource in golden["shared_resources"]:
            resource_id = uid("shared_resource", resource["shared_resource_id"])
            if not any(r["id"] == resource_id for r in rows["shared_resource"]):
                add("shared_resource", id=resource_id, kind=resource["kind"], description=resource["description"],
                    is_blocked=resource["is_blocked"])
            if order["version_no"] == 1:
                add("dependency", id=uid("dependency", order_id, resource["shared_resource_id"]),
                    service_order_id=so_id, from_milestone_id=None, to_milestone_id=None, kind="customer",
                    shared_resource_id=resource_id, supplier_id=None,
                    description=f"Depends on shared resource {resource['shared_resource_id']}",
                    owner=None, due_date=None)
        latest[order_id] = {  # the last version seen is the current one
            "id": so_id, "project_id": project_id, "customer_id": customer_id, "external_order_id": order_id,
            "product": order["product"], "stage": order["stage"], "is_blocked": False, "blocked_reason": None,
            "blocked_since": None, "blocked_owner": None, "current_version_id": version_id}
    for values in latest.values():
        add("service_order", **values)

    # Second tenant: one customer, one order, one version. No documents.
    customer_id = uid("customer", second_name, SECOND_TENANT_CUSTOMER)
    so_id = uid("service_order", SECOND_TENANT_ORDER)
    version_id = uid("order_version", SECOND_TENANT_ORDER, 1)
    add("customer", second, id=customer_id, name=SECOND_TENANT_CUSTOMER, type="enterprise")
    add("service_order", second, id=so_id, project_id=None, customer_id=customer_id,
        external_order_id=SECOND_TENANT_ORDER, product="EPL", stage="order_received", is_blocked=False,
        blocked_reason=None, blocked_since=None, blocked_owner=None, current_version_id=version_id)
    add("order_version", second, id=version_id, service_order_id=so_id, version_no=1,
        received_at="2026-11-02T09:00:00Z", supersedes_id=None)
    return rows


def golden_field_values(data_dir: Path = HERE) -> list[dict]:
    """Golden labels as field_value-shaped rows (schema check only; never agent output)."""
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    tenant = uid("tenant", manifest["tenant"])
    rows = []
    for _, golden in load_goldens(data_dir):
        order = golden["order"]
        order_id, version_no = order["external_order_id"], order["version_no"]
        for field in golden["expected_fields"]:
            key = field["field_key"]
            side = {"a_end": "A", "z_end": "Z"}.get(key.split(".")[0])
            source = next((s for s in field["sources"] if s["raw_value"] == field["raw_value"]), None)
            rows.append({
                "id": uid("field_value", order_id, version_no, key), "tenant_id": tenant,
                "order_version_id": uid("order_version", order_id, version_no),
                "endpoint_id": uid("endpoint", order_id, version_no, side) if side else None,
                "field_key": key, "raw_value": field["raw_value"], "normalized_value": field["normalized_value"],
                "status": field["expected_status"],
                "source_document_id": uid("document", order_id, version_no, source["doc_id"]) if source else None,
                "source_location": f"page {source['page']}, {source['location']}" if source else None,
                "fact_timestamp": None, "ingested_at": order["received_at"], "extracted_by": "rule",
                "is_synthetic": True})
    return rows


if __name__ == "__main__":
    out = HERE / "seed"
    out.mkdir(exist_ok=True)
    for table, table_rows in build_rows().items():
        (out / f"{table}.json").write_text(json.dumps(table_rows, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
        print(f"{table}: {len(table_rows)} rows")
