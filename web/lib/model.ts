// What the screens show, derived from the run files and rules/. No value is invented here:
// every number is a count of records, and every date is one the documents state.
import {
  Extraction,
  Field,
  Finding,
  OrderVersion,
  SEVERITIES,
  Severity,
  StageRule,
  Validation,
  fieldRules,
} from "./data";

export function fieldOf(extraction: Extraction, key: string): Field | undefined {
  return extraction.fields.find((f) => f.field_key === key);
}

export function customerOf(extraction: Extraction): string | null {
  return fieldOf(extraction, "customer_name")?.raw_value ?? null;
}

/** The capacity as printed (port speed for EPL, rate for wavelength), or the field's status when it has no single value. */
export function capacityOf(extraction: Extraction): { value: string | null; status: string | null } {
  const field = fieldOf(extraction, extraction.product === "WAVELENGTH" ? "rate" : "port_speed");
  return { value: field?.raw_value ?? null, status: field ? field.status : null };
}

export type DateType = "committed" | "forecast" | "requested";

/** The strongest date the order states: committed, else forecast, else requested. Its type is always shown. */
export function keyDate(extraction: Extraction): { type: DateType; date: string } | null {
  for (const type of ["committed", "forecast", "requested"] as DateType[]) {
    const field = fieldOf(extraction, `dates.${type}`);
    if (field && typeof field.normalized_value === "string" && ["pending", "verified"].includes(field.status)) {
      return { type, date: field.normalized_value };
    }
  }
  return null;
}

export function severityCounts(findings: Finding[]): Record<Severity, number> {
  const counts = { critical: 0, high: 0, medium: 0, info: 0 };
  for (const finding of findings) counts[finding.severity] += 1;
  return counts;
}

export function openFindings(validation: Validation): Finding[] {
  return validation.findings.filter((f) => f.status === "open" || f.status === "in_progress");
}

export type StageState = "completed" | "assumed_complete" | "current" | "blocked" | "upcoming";
export interface Progress {
  stages: { key: string; state: StageState; assumption?: string; gate: string | null }[];
  done: number;
  total: number;
  percent: number;
  current: string;
}

/** Completed stages over all stages, equal weights from rules/stages.json. A stage with an exit gate is
 *  completed only by a human decision; the agent's recommendation never completes it. */
export function progressOf(validation: Validation, rules: StageRule[]): Progress {
  const passedByHuman = (gate: string | null) =>
    gate !== null && gate === validation.gate.gate && validation.gate.human_decision?.outcome === "pass";
  const stages: Progress["stages"] = [];
  let reachedCurrent = false;
  for (const rule of rules) {
    let state: StageState;
    if (reachedCurrent) state = "upcoming";
    else if (rule.assumed_complete) state = "assumed_complete";
    else if (passedByHuman(rule.exit_gate)) state = "completed";
    else {
      reachedCurrent = true;
      const blocked =
        rule.exit_gate === validation.gate.gate &&
        validation.gate.recommendation === "block" &&
        validation.gate.human_decision === null;
      state = blocked ? "blocked" : "current";
    }
    stages.push({ key: rule.key, state, assumption: rule.assumed_complete, gate: rule.exit_gate });
  }
  const weight = (key: string) => rules.find((r) => r.key === key)?.weight ?? 0;
  const total = rules.reduce((sum, r) => sum + r.weight, 0);
  const doneStages = stages.filter((s) => s.state === "completed" || s.state === "assumed_complete");
  const doneWeight = doneStages.reduce((sum, s) => sum + weight(s.key), 0);
  const current = stages.find((s) => s.state === "current" || s.state === "blocked") ?? stages[stages.length - 1];
  return {
    stages,
    done: doneStages.length,
    total: rules.length,
    percent: total ? Math.round((100 * doneWeight) / total) : 0,
    current: current.key,
  };
}

export type RequirementResult = "met" | "met_with_findings" | "unmet";
export interface Requirement {
  group: string;
  result: RequirementResult;
  ok: number | null;
  total: number | null;
  blocking: Finding[];
  scopingRun?: boolean;
}

const SCOPING_PREFIX = "SEG-";

/** G1 requirements, one per field group of the product plus customer scoping. A group is unmet when one of
 *  its findings blocks the gate. */
export function requirementsOf(order: OrderVersion): Requirement[] {
  const { extraction, validation } = order;
  if (!extraction.product) return [];
  const rules = fieldRules(extraction.product);
  const groups = new Map<string, { ok: number; total: number; findings: Finding[] }>();
  for (const field of extraction.fields) {
    const rule = rules.get(field.field_key);
    if (!rule || rule.gate !== "G1") continue;
    const entry = groups.get(rule.group) ?? { ok: 0, total: 0, findings: [] };
    entry.total += 1;
    if (!["missing", "contradictory"].includes(field.status)) entry.ok += 1;
    groups.set(rule.group, entry);
  }
  const scoping: Finding[] = [];
  for (const finding of validation.findings) {
    if (finding.rule_id.startsWith(SCOPING_PREFIX)) scoping.push(finding);
    else groups.get(rules.get(finding.field_key)?.group ?? "")?.findings.push(finding);
  }
  const resultOf = (findings: Finding[]): RequirementResult =>
    findings.some((f) => f.blocks_gate && f.status !== "resolved")
      ? "unmet"
      : findings.length
        ? "met_with_findings"
        : "met";
  const rows: Requirement[] = [...groups.entries()].map(([group, entry]) => ({
    group,
    result: resultOf(entry.findings),
    ok: entry.ok,
    total: entry.total,
    blocking: entry.findings.filter((f) => f.blocks_gate),
  }));
  rows.push({
    group: "customer_scoping",
    result: resultOf(scoping),
    ok: null,
    total: null,
    blocking: scoping.filter((f) => f.blocks_gate),
    scopingRun: validation.run.customer_scoping,
  });
  return rows;
}

export type Bucket = "needs_action" | "pending" | "not_set" | "verified";
export const BUCKETS: Bucket[] = ["needs_action", "pending", "not_set", "verified"];

/** Where a critical field goes in the panel (D48). Stale fields need action; a pending field with no
 *  value (still awaited) is "not set", not "pending confirmation". */
export function bucketOf(field: Field): Bucket {
  if (["contradictory", "missing", "stale"].includes(field.status)) return "needs_action";
  if (field.status === "verified") return "verified";
  if (field.status === "pending" && field.raw_value !== null) return "pending";
  return "not_set";
}

export function fieldBuckets(extraction: Extraction): Record<Bucket, Field[]> {
  const buckets: Record<Bucket, Field[]> = { needs_action: [], pending: [], not_set: [], verified: [] };
  for (const field of extraction.fields) buckets[bucketOf(field)].push(field);
  return buckets;
}

export { SEVERITIES };
