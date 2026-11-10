// Reads the local run files. Read-only: nothing here writes, sends or calls a model.
import fs from "node:fs";
import path from "node:path";
import { DATA_DIR, RULES_DIR } from "./config";

export type Severity = "critical" | "high" | "medium" | "info";
export const SEVERITIES: Severity[] = ["critical", "high", "medium", "info"];

export interface Source {
  filename: string;
  doc_type: string;
  page: number;
  location: string;
  raw_value: string;
  stale_source: boolean;
  placeholder?: string | null;
}
export interface Field {
  field_key: string;
  status: string;
  raw_value: string | null;
  normalized_value: unknown;
  source: { filename: string; page: number; location: string } | null;
  sources: Source[];
}
export interface Extraction {
  synthetic: boolean;
  order_dir_id: string;
  version_no: number;
  product: "EPL" | "WAVELENGTH" | null;
  run: { provider: string; model: string };
  fields: Field[];
}
export interface Text {
  key: string;
  params: Record<string, string | number>;
}
export interface Finding {
  finding_id: string;
  rule_id: string;
  field_key: string;
  severity: Severity;
  field_status: string;
  conflicting_values: Source[];
  impact: string;
  blocks_gate: boolean;
  owner: string;
  resolving_party: string;
  escalated: boolean;
  due_date: string;
  action: Text;
  description: Text;
  status: string;
  reopened?: boolean;
}
export interface Approval {
  approver: string;
  reason: string;
}
export interface Validation {
  synthetic: boolean;
  version_no: number;
  run: { validator_version: string; extraction_model: string; evaluated_at: string; customer_scoping: boolean };
  findings: Finding[];
  gate: {
    gate: string;
    recommendation: "pass" | "block";
    unmet_requirements: { finding_id: string; field_key: string; severity: Severity }[];
    human_decision: { outcome: string; approval: Approval } | null;
  };
  version_change: {
    previous_version_no: number;
    changed_fields: { field_key: string; previous: string[]; current: string[]; plan_impact: boolean }[];
    reopened_validations: string[];
    unchanged_validations: number;
    plan_impact: boolean;
  } | null;
}
/** plan.json from the Phase 4 planner (src/planner). Optional: a run folder without it has no approvals. */
export interface Plan {
  synthetic: boolean;
  dates: {
    order: {
      requested: string[];
      forecast: string[];
      committed: string[];
      committed_awaiting_approval: string[];
    };
  };
  actions?: PlanAction[];
}
/** An open question in the plan with an owner (D60), shown as a workstream. */
export interface PlanAction {
  action_id: string;
  action: string;
  milestone: string | null;
  dependency?: string;
  supplier?: string;
  owner: string;
  status: string;
  due_date: string | null;
  anchor?: string | null;
  anchor_kind?: string;
  history?: { event: string; on: string; owner: string }[];
}
export interface OrderVersion {
  orderId: string;
  versionNo: number;
  extraction: Extraction;
  validation: Validation;
  plan: Plan | null;
}
export interface StageRule {
  key: string;
  weight: number;
  exit_gate: string | null;
  assumed_complete?: string;
}

function readJson<T>(file: string): T {
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

const ORDER_ID = /^[A-Za-z0-9_-]+$/;

/** Versions of one order that have both files, oldest first. */
export function versionsOf(orderId: string): number[] {
  if (!ORDER_ID.test(orderId)) return [];
  const dir = path.join(/*turbopackIgnore: true*/ DATA_DIR, orderId);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => /^v\d+$/.test(name))
    .filter((name) => ["extraction.json", "validation.json"].every((f) => fs.existsSync(path.join(/*turbopackIgnore: true*/ dir, name, f))))
    .map((name) => Number(name.slice(1)))
    .sort((a, b) => a - b);
}

export function loadVersion(orderId: string, versionNo: number): OrderVersion | null {
  if (!versionsOf(orderId).includes(versionNo)) return null;
  const dir = path.join(/*turbopackIgnore: true*/ DATA_DIR, orderId, `v${versionNo}`);
  return {
    orderId,
    versionNo,
    extraction: readJson<Extraction>(path.join(/*turbopackIgnore: true*/ dir, "extraction.json")),
    validation: readJson<Validation>(path.join(/*turbopackIgnore: true*/ dir, "validation.json")),
    plan: fs.existsSync(path.join(/*turbopackIgnore: true*/ dir, "plan.json"))
      ? readJson<Plan>(path.join(/*turbopackIgnore: true*/ dir, "plan.json"))
      : null,
  };
}

/** The current (latest) version of every order in the run folder. */
export function listOrders(): OrderVersion[] {
  if (!fs.existsSync(DATA_DIR)) return [];
  const orders: OrderVersion[] = [];
  for (const orderId of fs.readdirSync(DATA_DIR).sort()) {
    const versions = versionsOf(orderId);
    const latest = versions.length ? loadVersion(orderId, versions[versions.length - 1]) : null;
    if (latest) orders.push(latest);
  }
  return orders;
}

export function stageRules(): StageRule[] {
  return readJson<{ stages: StageRule[] }>(path.join(/*turbopackIgnore: true*/ RULES_DIR, "stages.json")).stages;
}

interface FieldRule {
  key: string;
  group: string;
  scope: "order" | "endpoint";
  gate: string;
}

/** {field key: rule} for a product, with endpoint fields expanded per end. Same reading as src/extract/catalog.py. */
export function fieldRules(product: "EPL" | "WAVELENGTH"): Map<string, FieldRule> {
  const files = ["fields.common.json", product === "EPL" ? "fields.epl.json" : "fields.wavelength.json"];
  const rules = new Map<string, FieldRule>();
  for (const file of files) {
    for (const rule of readJson<{ fields: FieldRule[] }>(path.join(/*turbopackIgnore: true*/ RULES_DIR, file)).fields) {
      if (rule.scope === "endpoint") for (const end of ["a_end", "z_end"]) rules.set(`${end}.${rule.key}`, rule);
      else rules.set(rule.key, rule);
    }
  }
  return rules;
}
