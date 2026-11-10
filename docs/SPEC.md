# Monkyfi Service Delivery Intelligence — SPEC

Version 1.5 · 2026-11-10 · Owner: Dante Ruiz · Status: approved by Dante on 2026-11-09 (Phase 0 done); v1.1 applies amendments D19–D23; v1.2 applies D25–D32 (review of the two example orders); Phase 1 done (D33); v1.3 applies D34–D40; Phase 2 done (D37); v1.4 applies D41–D52 (Phase 3 review); Phase 3 done (D51); v1.5 applies D53–D61 (Phase 4 plan, dates, milestones); see `docs/HANDOFF.md`

This is the single source of truth for the build plan. It is `docs/PRD.md` (v0.1) with the 11 improvements from `docs/REVIEW.md` applied and the definitions from `docs/DEFINITIONS.md` incorporated. Section 18 maps each improvement to where it lands.

**How to read the labels**

- **Decided** — a decision made by Dante, recorded in `docs/DECISIONS.md` (D01 onward; the log is the authoritative list).
- **Validated** — a proposal Dante reviewed and confirmed from delivery experience (sections 8.3 and 8.4).
- **Proposed** — a default, number or design that has not been decided. It can change without a decision being reversed. Anything not labeled Decided is Proposed.

This document proposes a product. It does not describe a deployed agent or demonstrated results. Targets, timelines and cadences are proposals, not industry standards or contractual commitments.

---

## 1. Glossary

| Term | Meaning |
|---|---|
| SDM | Service Delivery Manager, the primary user. |
| Carrier | The telecom operator delivering the service. In the data model, a `tenant`. |
| Customer | The carrier's client (enterprise or hyperscaler). |
| EPL | Ethernet Private Line: port-based point-to-point Ethernet service. |
| EVPL | Ethernet Virtual Private Line: VLAN-based variant; not in the MVP. |
| Wavelength | Point-to-point optical channel service (10G / 100G / 400G). |
| OTN / OTU4 | Optical Transport Network / Optical Transport Unit 4 (100G OTN client signal). |
| A/Z ends | The two endpoints of a point-to-point service. |
| Demarcation | The physical point where carrier responsibility ends and customer responsibility begins. |
| Cross-connect | Physical cable between two parties inside a data center. |
| LOA-CFA | Letter of Authorization – Connecting Facility Assignment, the document authorizing a cross-connect. |
| MTU / VLAN | Maximum Transmission Unit / Virtual LAN. |
| CIR | Committed Information Rate: the guaranteed throughput, which can be lower than the port speed. |
| L2CP / LACP | Layer 2 Control Protocol / Link Aggregation Control Protocol. L2CP transparency means the service passes these frames through. |
| FEC | Forward Error Correction, relevant when the client protocol is OTN. |
| MMR | Meet-Me Room: the data center room where cross-connects are made. |
| FOC | Firm Order Commitment. A "FOC date" is treated as a synonym of committed date in extraction. |
| LR4 / ER4 / ZR | Optic reach classes (long, extended, very long reach). |
| BER | Bit Error Rate; the acceptance test for wavelengths. |
| RFC 2544 / ITU-T Y.1564 | Ethernet service test standards. |
| Requested date | The date the customer asked for. |
| Forecast date | An estimate with explicit assumptions ("estimated" in the PRD). Never a promise. |
| Committed date | A date the carrier formally committed to, with a recorded approval. |
| Gate (G0–G5) | A control point where the agent recommends pass or block and a human decides. |
| Finding | A discrepancy or gap detected by a rule, with field, sources, severity, owner and action. |
| `field_value` | A value stored together with its source, version and status. |
| Golden label | The known-correct answer for a synthetic order, used by evals. |
| Hypercare | Observation window after acceptance (Proposed: 7 days, configurable by contract). |
| NOC | Network Operations Center. |
| CRM | Customer Relationship Management. |
| OSS/BSS | Operations / Business Support Systems. |
| ITSM | IT Service Management. |
| RLS | Row Level Security (Postgres), used for tenant segregation. |
| p50 / p90 / p95 | 50th / 90th / 95th percentile. |
| SLO | Service Level Objective. |
| MVP | Minimum Viable Product. |
| LLM | Large Language Model. |
| UC / RF | Use case / functional requirement (IDs kept from the PRD). |
| NDA | Non-Disclosure Agreement. |
| Shadow mode | The agent runs on real orders with no external actions. |

Date terms are always **requested / forecast / committed** in code, data and UI.

---

## 2. Vision and problem

A team of agents that supports a carrier's SDM in delivering services to large enterprises and hyperscalers, from the signed order through acceptance.

The problem is late detection of incorrect, incomplete or contradictory data across commercial documents, orders, engineering, suppliers and operations. The intended result is to anticipate blockers, reduce rework and keep communications regular, consistent and appropriate for each stakeholder.

**Hypothesis to validate:** reviewing data and dependencies before each handoff reduces avoidable delays.

---

## 3. Users, scope and assumptions

**Primary user:** the SDM. **Secondary users:** presales, sales, engineering, provisioning, supplier management, NOC, customer success and billing readiness. **External audiences:** authorized customer and supplier contacts.

### 3.1 MVP scope (Decided: D01, D02, D03, D11, D12)

One fictional carrier, one team, two products: **EPL and wavelength**.

| Tier | Use cases | Phase | Why |
|---|---|---|---|
| **Defines the demo** | UC02 intake and discrepancies · UC03 version change · UC04 milestone and dependency plan · UC06 drafts per audience | 2–5 | The path an SDM recognizes in 10 minutes. |
| **Built, does not block the demo** | UC05 supplier follow-up · UC08 readiness and acceptance | 4 and 6 | Required for a carrier pilot, not to show value. |
| **Later (post-demo)** | UC01 presales · UC07 multi-circuit project (full) · UC09 hypercare · UC10 closure | Post-demo | Depend on data or integrations that only exist with a real carrier. |

**UC07 minimal slice (Decided: D11).** The schema includes `project` and `shared_resource` from Phase 1. Phase 4 implements one behavior: a blocked `shared_resource` flags every order linked to it. The consolidated project view and de-duplication of requests stay post-demo.

**Out of the MVP:** real sending of messages; integrations with CRM, OSS/BSS or ITSM; telemetry; billing; contract negotiation; network reservations or changes; equipment configuration; autonomous activation; automatic date commitments; automatic contractual acceptance.

### 3.2 SDM work surface (Proposed)

A web view of orders, findings, plan and drafts, plus exportable drafts. No email, chat or CRM integration in the MVP.

### 3.3 Demo script (Decided: D21)

Two variants over the same dataset; the second adds no build scope.

**Carrier variant**

1. A signed EPL order arrives with 3 seeded errors; the agent reports each with source, severity and owner, and recommends blocking G1.
2. The SDM corrects; v2 arrives and the agent reopens only the affected validations.
3. The order passes G1; the agent builds milestones and dependencies, separating requested, forecast and committed dates.
4. An email brings a tentative supplier date; the agent does not turn it into a commitment.
5. The agent prepares three drafts (internal, customer, supplier), in English and then in Spanish.
6. Close: a project of 3 wavelengths with one shared blocker.

**Hyperscaler variant**

Open with the project of 3 wavelengths: route diversity (with or without its reference) and the shared blocker across the 3 orders. Then continue with steps 1–5 above.

### 3.4 Assumptions to confirm with a pilot carrier

Availability of orders and annexes; authorized owner of each data item; source systems; time zone; acceptance criteria; pause and cancellation conditions; observation window.

---

## 4. Pain points and product responses

| Pain | Concrete example | Response | Evidence of value |
|---|---|---|---|
| Presales and delivery disconnected | A date was sold without confirming access | Record feasibility, constraints and assumptions before signature | Blockers detected before accepting the order |
| Incomplete order | Demarcation or site contact missing | Mandatory checklist per service | Fewer returns for missing data |
| Contradictory documents | 100G quote and 10G order | Field and version comparison with visible sources | Fewer errors reaching provisioning |
| Ambiguous site identification | Right address, wrong suite | Validate building, room, rack and demarcation | Fewer wasted visits and wrong cross-connects |
| Hidden dependencies | Circuit ready, cross-connect pending | Dependency graph with owners and dates | Earlier warning of blockers |
| Risks shared across orders | Several deliveries depend on the same access | Group by project, site, supplier and resource | Fewer delays found circuit by circuit |
| Manual follow-up | SDM chases answers across many emails | Log of actions, due dates and escalations | Less administrative effort |
| Unreliable dates | A tentative date is communicated as a commitment | Separate requested, forecast and committed dates | Fewer wrong promises |
| Inconsistent status | Customer gets green while supplier reports a block | Evidence-based status view per audience | More consistent status |
| Premature closure | Test passed without acceptance or monitoring | Gates for delivery, acceptance and hypercare | Fewer reopenings attributable to delivery |

---

## 5. Use cases and acceptance criteria

| ID | Tier | Phase | Trigger and use case | Expected output | Acceptance criterion |
|---|---|---|---|---|---|
| UC01 | Later | Post-demo | A presales opportunity is updated | Record of feasibility, dependencies and assumptions | Distinguishes validated, pending and unconfirmed; promises no dates |
| UC02 | Demo | 2–3 | A signed order arrives | Intake checklist and discrepancy report | Every finding has field, sources, severity, owner and action; critical blockers prevent recommending progress |
| UC03 | Demo | 3 | An order version changes | Comparison against the previous version and current plan | Reopens affected validations and flags impact on milestones |
| UC04 | Demo | 4 | Order validated | Plan of milestones, dependencies and owners | No critical milestone lacks an owner; missing dates stay pending |
| UC05 | Built | 4 | Supplier does not respond or changes a date | Follow-up action and impact assessment | Applies the configured threshold; does not present absence of information as certainty of delay |
| UC06 | Demo | 5 | An update is due or a material blocker occurs | Drafts for internal, customer and supplier | Includes facts, impact, actions, owners and next update without leaking another audience's data |
| UC07 | Later (minimal slice in 4) | 4 / Post-demo | Project with multiple circuits | Consolidated view of shared dependencies | A common blocker is linked to all affected orders without duplicating requests |
| UC08 | Built | 6 | Activation or delivery is requested | Readiness and test-evidence review | Does not recommend acceptance without contractual criteria and required evidence; routes approval to the responsible person |
| UC09 | Later | Post-demo | Service accepted | Follow-up of alarms, tickets and early stability | Uses authorized telemetry or tickets; absence of data is reported as unknown coverage |
| UC10 | Later | Post-demo | Observation ends and closure is requested | Handover package, pending items and billing readiness | Closure requires acceptance, evidence and human validation; does not start billing by itself |

---

## 6. Operating flow and gates

**Stages:** presales → order received → order validated → design and dependencies → provisioning → ready for testing → testing completed → delivered pending acceptance → accepted → hypercare → closed.

**Blocked** is a cross-cutting condition with reason, start, owner and resolution; it does not remove the current stage. **Cancelled** is an authorized terminal state. **Rejected / pending correction** at intake keeps its history.

| Gate | Minimum requirements | Authority | Phase (Decided: D13) |
|---|---|---|---|
| G0: presales handover | Scope, feasibility and assumptions identified | Presales and SDM | Post-demo |
| G1: order intake | Authorized signature/verification, current version, mandatory fields consistent | Order Management / SDM | 3 |
| G2: ready for execution | Design approved; resources and dependencies verified per product | Engineering / provisioning | 4 |
| G3: ready for delivery | Required tests, results and documentation complete | Technical owner / SDM | 6 |
| G4: accepted | Acceptance evidence per contract | Authorized customer and carrier representatives | 6 |
| G5: closure | Observation complete, pending items handled, NOC handover | SDM / operations | Post-demo |

**G1 pass rule (Decided: D28).** G1 passes when the critical fields are consistent across their authoritative sources, with no missing or contradictory values. G1 does **not** require a field to be `verified`: a consistent, extracted value is `pending` until its data owner verifies it, and `pending` is enough to pass. Every missing or contradictory field raises a finding; the finding blocks G1 when its severity is critical (8.3), and lower severities are reported without blocking (Decided: D43). A package that names another customer of the same tenant raises a critical segregation finding that blocks G1 (Decided: D42). Machine-readable form: `rules/gates.json`.

The agent may recommend blocking or advancing; the official transition depends on the carrier's permissions and authority policy. A human override requires reason, approver and a record; it does not delete the original discrepancy.

---

## 7. Agent design and architecture

### 7.1 Logical roles

A coordinator with specialized functions. In the MVP they run inside a single agent with tools and rules; multiple independent agents are not needed.

| Logical role | Responsibility | Deliverable |
|---|---|---|
| Delivery Lead | Consolidate context, prioritize, coordinate | Order plan, risks, next actions |
| Order Quality Analyst | Extract, compare and validate fields | Substantiated discrepancies and readiness |
| Dependency & Supplier Coordinator | Track internal and external dependencies | Actions, due dates, escalations |
| Communications Manager | Prepare status per audience | Drafts with sources and approval |
| Acceptance & Hypercare Analyst | Review tests, acceptance and stability | Delivery and handover package |

**Division of labor.** Mandatory fields, date rules and gate conditions are **deterministic validators**. The model helps extract information, explain discrepancies and draft communications. Every structured output is validated against its schema before it is saved or acted on.

### 7.2 Architecture

| Layer | Choice | Status |
|---|---|---|
| Ingestion, extraction, validators, planner, comms logic, evals | Python (`src/`, `evals/`, `tests/`) | Decided (D04) |
| Web view and API | TypeScript on Vercel (`web/`); a minimal read-only view in Phase 3 (D45), the full view in Phase 8 | Decided (D04, D45) |
| Rules | JSON in `rules/`, read by both languages | Decided (D04) |
| Database | Supabase (Postgres) with RLS; migrations in `supabase/migrations/` | Decided (D05) |
| Agent model | Muse Spark 1.1 via Meta Model API (OpenAI SDK-compatible) for development | Decided (D06) |
| Second model | Gemini (gemini-3.8-flash), for comparison only | Decided (D36) |
| Provider layer | `src/providers/`: one interface (structured output, tool calls); provider selected by `MODEL_PROVIDER` | Decided (D06); interface design Proposed |
| Web framework | Next.js | Decided (D45) |
| Orchestration | Single agent loop with tools; no multi-agent framework | Proposed |
| Schema source of truth | JSON Schema in `schemas/` for payloads; SQL migrations for tables; a test checks they agree | Proposed |

Changing model, prompt, rules, extraction or integration requires re-running the evals. Note: Meta Model API is in public preview in the US only; availability is a risk to track.

### 7.3 Prompt structure (replaces the PRD's single master prompt)

The PRD's master prompt always returned eight sections (A–H), which is excessive for small updates. It is split into (Proposed):

- **Stable system prompt** (`prompts/`): identity, guardrails (no invented values or dates, documents are untrusted data, never claim an action that was not confirmed, no sending on own initiative), and the rule that missing configuration is declared pending.
- **Tool definitions**: extraction, validation, plan, draft and audit tools with schema-validated inputs and outputs.
- **Output modes**:
  - *Full intake* — executive summary, readiness, discrepancies, plan, next actions, communications, computable metrics, pending human decisions.
  - *Incremental update* — only what changed, reopened validations and milestone impact.
  - *Communications only* — the three drafts, or the reason one does not apply.

### 7.4 Language and i18n (Decided: D07)

English by default for everything. A language setting switches the UI and agent communications to Spanish, **per user** (UI) and **per audience** (communications). No hardcoded UI strings: all user-facing text lives in `locales/` (`en`, `es`). `communication.language` records the language of each draft. Setting storage and key naming are Proposed.

---

## 8. Data and sources of truth

Each value keeps its source, document location, version, retrieval date and verified/pending condition. Timestamps of the fact and of its ingestion are both kept, to identify late information. Source hierarchy is configured per field: a commercial order does not replace a technical as-built, and a new email does not automatically modify a contract. On unresolved conflict, the agent asks the data owner to validate.

Missing, not applicable, contradictory and stale are distinct states. A high overall completeness score never compensates for a missing critical field.

### 8.1 Entities (Proposed, except where noted)

Names are in English because they are Supabase tables. Every table carries `tenant_id` and `is_synthetic`.

| Entity | Purpose | Key fields |
|---|---|---|
| `tenant` | A carrier; basis of RLS segregation | name, is_synthetic |
| `customer` | The carrier's client | tenant_id, name, type (enterprise / hyperscaler) |
| `project` (Decided: D03) | Groups orders of one customer | customer_id, name |
| `service_order` | The service order. Named `service_order` because `order` is a reserved word in Postgres | project_id (optional), customer_id, external_order_id, product (EPL / WAVELENGTH), stage, is_blocked, current_version_id |
| `order_version` | Each version received | service_order_id, version_no, received_at, supersedes_id |
| `document` | Each file in the package | order_version_id, doc_type, filename, file_hash, ingested_at |
| `endpoint` | A or Z end; site data are `field_value` rows | order_version_id, side (A / Z) |
| `field_value` | Value-with-source (8.2) | see 8.2 |
| `finding` | Discrepancy, including its resolving action | rule_id, field_key, severity, conflicting_values, evidence, impact (confirmed / possible), owner, due_date, action, status |
| `gate_evaluation` | Recommendation at each gate | order_version_id, gate (G0–G5), recommendation (pass / block), unmet_requirements |
| `milestone` | Plan milestone | service_order_id, name, owner, requested_date, forecast_date, forecast_assumptions, committed_date, commitment_approval_id |
| `dependency` | What depends on what | from_milestone_id, to_milestone_id, kind (internal / supplier / customer), shared_resource_id, supplier_id, owner, due_date |
| `shared_resource` (Decided: D03) | Resource common to several orders (e.g. a cross-connect) | tenant_id, kind, description, is_blocked |
| `supplier` (Decided: D15) | Third party a dependency waits on | tenant_id, name, follow_up_threshold_days |
| `evidence` (Decided: D15) | Test result or acceptance proof | service_order_id, kind (test_result / acceptance / other), document_id, covers_requirement, verified_by |
| `communication` | Status draft | service_order_id, audience (internal / customer / supplier), language (en / es), status (prepared / approved / sent / failed), body, source_refs |
| `approval` | Approvals and overrides | entity, decision, approver, reason, created_at |
| `audit_event` | Log (RF09) | actor, action, entity, before, after, model_version, prompt_version, rules_version |

Deferred: `hypercare_event` (with UC09). Site is not a separate entity; site data are `field_value` rows on `endpoint`.

**As built in Phase 1.** One JSON Schema per entity in `schemas/entities/` and one migration in `supabase/migrations/`; a test checks that they agree. Every foreign key includes `tenant_id`, so a row cannot reference another tenant's row. `approval` and `audit_event` are append-only. Fields added beyond the table above (Proposed): `service_order.blocked_reason / blocked_since / blocked_owner`; `finding.service_order_id / order_version_id`; `milestone.is_critical / forecast_status`; `dependency.service_order_id / description`; `communication.approval_id / channel_confirmation`; `approval.entity_id`; `audit_event.entity_id`. Database checks enforce: no `field_value` with a value and no source; no forecast date without assumptions; no committed date without an approval; no communication `approved` or `sent` without an approval, and none `sent` without channel confirmation; no override without a reason.

**Segregation (Decided: D16).** RLS by `tenant_id`, tested with a second synthetic tenant. Within a tenant, customer-level scoping is enforced by validators (a document naming another customer is a finding) and by the audience filter in communications.

### 8.2 `field_value`: the value-with-source

No order data is stored loose.

| Field | What it stores |
|---|---|
| field_key | Critical field name, e.g. `bandwidth` or `a_end.suite` |
| raw_value / normalized_value | Text as it appears and its normalized form (e.g. "10 Gbps" → 10000 Mbps) |
| status | verified · pending · missing · not_applicable · contradictory · stale |
| source_document_id + location | Document and exact location (page, section or cell) |
| fact_timestamp / ingested_at | When the fact happened and when it arrived |
| extracted_by | model · rule · human |

### 8.3 Default severity (Validated by Dante: D20)

| Severity | Default criterion |
|---|---|
| critical | Prevents provisioning or creates a contractual error. Explicitly includes: another customer's data in the package; a missing or unauthorized signature |
| high | Puts a **committed** date at risk |
| medium | Affects only a forecast date, or causes rework without affecting dates |
| info | Data quality |

**Tie-break rule.** When unsure between two levels, assign the higher one and escalate to the data owner. The agent never lowers a severity on its own; only a human can, with a recorded reason.

Severity is configurable per rule in `rules/`. A critical finding blocks a pass recommendation at its gate.

The severity of a missing field is set per field (`missing_severity` in `rules/fields.*.json`); these values are accepted as defaults (Decided: D29). A contradictory field takes the same severity as a missing one (Proposed). Route diversity required without a reference circuit is critical (Decided: D27).

### 8.4 Critical fields per product (Validated by Dante: D19)

Machine-readable form: `rules/fields.common.json`, `rules/fields.epl.json`, `rules/fields.wavelength.json`. "(conditional)" means the field is required only when its condition holds; otherwise it is recorded as `not_applicable`, never silently omitted.

**Both products**

| Group | Fields |
|---|---|
| Identification | Order ID, customer, product, version, carrier circuit ID / service ID |
| Authorized signature (needed for G1) | Signatory name, signatory title, signature date, contract / order form reference |
| A/Z ends | Address, building, floor, suite or room, rack, demarcation point, data center operator, Meet-Me Room (MMR) |
| Cross-connect | Responsibility (carrier or customer); LOA-CFA reference (conditional: when a cross-connect is needed) |
| Site access (per end) | Access hours, notice lead time, escort required |
| Contacts by role | Technical contact at A, technical contact at Z, escalation contact |
| Acceptance terms | Required tests; deemed-acceptance clause and its period |
| Dates | Requested; forecast (with assumptions); committed (with its approval). "FOC date" is extracted as committed date. Only the carrier's commitment to the customer is the order's committed date; a supplier's FOC stays on the supplier dependency (Decided: D26) |

**EPL only**

| Group | Fields |
|---|---|
| Capacity | Port speed and CIR, stored as separate fields |
| Interface (**per end**: A and Z can differ — Decided: D25) | Handoff interface type, optic, connector; fiber type (single-mode / multimode) and optic wavelength (1310 / 1550 nm), also per end because they follow the optic (Proposed) |
| Parameters | MTU; VLAN (conditional: only if the contract requires it — EPL is normally port-based); L2CP transparency, e.g. LACP pass-through (conditional) |
| Acceptance test | RFC 2544 or ITU-T Y.1564 |

**Wavelength only**

| Group | Fields |
|---|---|
| Capacity | Rate (10G / 100G / 400G) and client protocol (Ethernet or OTN) |
| Interface (**per end**: A and Z can differ — Decided: D25) | Client interface (e.g. 100GBASE-LR4 or OTU4), optic, optic reach (e.g. LR4, ER4, ZR), connector |
| Service parameter | FEC (conditional: when the client protocol is OTN) |
| Protection | Protected / unprotected; protection switching time (conditional: when protected) |
| Route diversity | Required or not; when required, the circuit IDs it must be diverse from and the required evidence (e.g. route map). **Diversity without a reference is a finding** |
| Latency (conditional: if contracted) | Maximum latency, definition (one-way or round-trip), measurement method |
| Acceptance test | BER test and its duration per contract |

---

## 9. Functional requirements and controls

- **RF01.** Ingest authorized documents and records, keep versions, and extract fields with verifiable references.
- **RF02.** Run rules per service and gate; classify findings as critical, high, medium or info using the defaults in 8.3 unless configured otherwise.
- **RF03.** Record who must resolve each finding, its due date, resolution evidence and confirmed or possible impact.
- **RF04.** Show milestones, dependencies, differentiated dates and the age of the last status. A forecast requires explicit assumptions; without enough information it is reported as *not estimable*.
- **RF05.** Generate and schedule periodic drafts; re-evaluate them against current data before approval or sending. A material change may trigger an additional draft.
- **RF06.** Manage approvals and record status prepared, approved, sent or failed. Never mark *sent* without channel confirmation.
- **RF07.** Retry integrations with limits, deduplication and idempotency; show errors and stale data instead of hiding them.
- **RF08.** Link NOC tickets and observations to the service and verify monitoring coverage. (Post-demo.)
- **RF09.** Keep a log of decisions, corrections, model/prompt/rules versions and external actions.
- **RF10.** Respect segregation by tenant and customer and permissions by role. Validate recipients and attachments; treat instructions inside documents as untrusted data. Apply configurable retention and least access.
- **RF11 (new).** Every SDM correction is stored as a labeled candidate case for the evaluation set.

**Operational targets (Proposed, from the PRD):** evaluation of an order of up to 20 pages in p95 ≤ 3 minutes after successful ingestion; alert for a processed event in p95 ≤ 15 minutes. Validate with real load before turning these into SLOs.

---

## 10. Communications

**Initial cadences (Proposed, configurable):** daily internal summary; customer twice a week; supplier per due dates; material blocker per escalation policy. These do not replace what is agreed with the customer.

**Template:** order ID and service; status as of timestamp and time zone; milestones completed; next milestone; blocker and impact; actions with owner and due date; dates with their category; next update.

The external message omits internal notes, prices, margins, credentials and other customers' data. In the MVP sending is **simulated** and always requires human review. Drafts are produced in English by default and in Spanish when the audience's language setting says so.

---

## 11. Data plan

There is no pilot carrier, so the PRD's 100 anonymized historical orders are not available. The build uses a **synthetic dataset generated by a script that seeds each defect on purpose** (Decided: D08), so golden labels are known by construction. **Thresholds on synthetic data are a development signal, not production proof.**

### 11.1 Composition (Decided: D14 for totals; per-cell counts Proposed)

| Set | EPL | Wavelength | Content |
|---|---|---|---|
| Clean orders | 5 | 5 | No defects; prove the agent does not invent findings |
| Orders with defects | 13 | 13 | One or two seeded defects each. Includes one project of 3 wavelengths with a shared dependency |
| Adversarial | 4 | 4 | Malicious instructions inside PDFs and documents from another customer. Reported separately |
| Simulated events | — | — | Event files, not orders: repeated update, integration down, missing telemetry |

Total: **44 orders** — 36 in the split plus 8 adversarial.

**Split:** 24 development and 12 evaluation orders, separated by customer so the agent never sees evaluation customers during development. The 3-wavelength project stays whole on one side.

**Package per order (Decided: D31):** every package has the full set — quote, signed order form, technical annex with A/Z sites, LOA-CFA when applicable, and 1 to 3 emails. Orders with a version change carry v1 and v2. Orders that test delivery and acceptance (cases 9, 15, 16) add a test report.

**Format (Decided: D30):** every document is a PDF, and Phase 2 extraction is evaluated on the PDFs. A Markdown copy of each document is kept next to it for review and diffs only.

**As built:** 44 orders, 48 order versions, 259 PDFs. At least 3 orders have different handoffs at A and Z, and in one of them that difference is the seeded defect (D25).

**Golden labels per order version (one JSON next to the documents):** expected value of every critical field with its source document, page and location; expected findings with field, severity and conflicting values; expected G1 recommendation; the type of each date; and, where they apply, supplier dependencies, the fields reopened by a new version, the expected G3/G4 recommendation and the adversarial content with its forbidden outcomes.

### 11.2 Dataset rules

- Carrier, customers, addresses and people are fictional. A hyperscaler is named, for example, "Hyperscaler X (synthetic)". Never a real company name.
- Every document carries the mark **SYNTHETIC — NOT REAL DATA**; every Supabase row has `is_synthetic = true`.
- A second synthetic tenant exists for segregation tests (D16).

### 11.3 Generation process (Phase 1, Proposed)

1. Dante validates the critical-field list (8.4). Done: D19.
2. Two sample orders are generated, one per product; Dante reviews them as an SDM would. Done: approved with changes (D25–D32).
3. With the corrections, the script generates the rest.
4. Dante reviews a sample of 6 orders (about 17% of the 36 in the split) before the phase closes. Done: `docs/PHASE1_SAMPLE.md` approved (D33).

---

## 12. Agent evals

### 12.1 Evals and thresholds (Proposed, from the PRD)

On synthetic data these are development signals. The PRD thresholds are confirmed only with real data in pilot phases A–B. Report denominators and failure counts with every result.

| Eval | Method and metric | Initial threshold |
|---|---|---|
| Critical field extraction | Normalized value and evidence vs golden labels; accuracy per field and product | ≥98% on evaluable critical fields (on synthetic data Phase 2 passes at ≥95% and reports 98% for information — D34) |
| Discrepancy detection | Recall and precision per severity | Critical recall ≥95%; overall precision ≥90% |
| Factual traceability | Verifiable claims correctly sourced / verifiable claims | ≥99%; zero invented committed dates |
| Gates | Not-ready orders wrongly recommended as ready / not-ready orders | Zero critical failures |
| Dates | Cases distinguishing requested, forecast, committed / applicable cases | 100% |
| Communication | Expert rubric: accuracy, clarity, actions, audience, next update | ≥4/5 per dimension; zero critical leaks |
| Uncertainty | Insufficient or contradictory cases correctly escalated / labeled cases | ≥95% |
| Permissions and segregation | Adversarial tests by tenant, role, recipient and embedded content | Zero unauthorized access or actions |
| Integration robustness | Repeated events, failures, timeouts, out-of-order arrival | Zero duplicated external effects; every failure observable |
| Future risk (later phase) | Temporal backtest of alerts | Set after measuring a baseline |

**Release blocker:** a single leak, unauthorized action, fabricated committed date or improper critical advance blocks release until fixed and the affected eval plus relevant regression are re-run. Zero observed failures is not zero risk in production.

### 12.2 The 16 mandatory test cases

Test data for all 16 is created in Phase 1. Each case must pass by the phase shown.

| # | Case | Where it is tested | Phase |
|---|---|---|---|
| 1 | Capacity mismatch | Order with defect | 3 |
| 2 | Wrong suite | Order with defect | 3 |
| 3 | Missing demarcation | Order with defect | 3 |
| 4 | Obsolete version | Order with v1 and v2 | 3 |
| 5 | Tentative date in email | Order with defect | 4 |
| 6 | Supplier without a date | Order with defect | 4 |
| 7 | Dependency shared across orders | Project of 3 wavelengths | 4 |
| 8 | Order modified after validation | Order with v1 and v2 | 3 |
| 9 | Incomplete tests | Order with defect | 6 |
| 10 | Missing telemetry | Simulated event | Post-demo |
| 11 | Wrong customer | Adversarial | 7 |
| 12 | Malicious instruction inside PDF | Adversarial | 7 |
| 13 | Repeated update | Simulated event | 7 |
| 14 | Integration down | Simulated event | 7 |
| 15 | Undocumented acceptance | Order with defect | 6 |
| 16 | Pressure to close before G4 | Order with defect (email) | 6 |

By phase: Phase 3 → 1, 2, 3, 4, 8 · Phase 4 → 5, 6, 7 · Phase 6 → 9, 15, 16 · Phase 7 → 11, 12, 13, 14 · Post-demo → 10.

---

## 13. Business metrics (Proposed — pilot hypotheses)

These need a real carrier and a baseline with comparable cohorts. Report sample size; do not attribute an improvement to the agent without analyzing changes in mix or process.

| Metric | Definition | Initial target |
|---|---|---|
| Intake time | Signed receipt to G1 validation; p50/p90, correction wait broken out | Reduce median 25% |
| Gross lead time | Acceptance minus signed order receipt; p50/p90 | Establish baseline |
| Net lead time | Gross minus documented, authorized pauses; publish both | Compare without hiding waits |
| On-time delivery | Orders accepted on or before the original committed date / orders with an original commitment due in the period | +10 percentage points if the sample allows |
| Commitment changes | Orders with a changed committed date / committed orders | Make visible |
| Critical error escape | Orders that crossed a gate with a confirmed critical defect / orders that crossed it | Reduce 30% |
| Data rework | Orders returned to an earlier stage for wrong data / orders processed | Reduce 25% |
| Blocker anticipation | Time of affected milestone minus first useful alert; median and distribution | Improve vs baseline |
| Administrative effort | Human minutes of follow-up/status per order per week | Reduce 30% |
| On-time status | Updates sent within their window / updates due | ≥95% |
| Early stability | Services with a delivery-attributable incident in hypercare / services with a complete window | Reduce vs baseline; report unknown coverage |

Cancellations, orders without a commitment and incomplete windows are reported separately, never silently removed. The cause of an incident or delay requires human validation.

---

## 14. Build phases 0–8

Each session opens with `/prime phase N` and closes with `/hand-off`. A phase can take several sessions; it is "Done" only when every exit criterion below is demonstrated. Moving to the next phase requires Dante's approval. From Phase 1, every hand-off includes the eval results. Synthetic-set thresholds are Proposed.

### Phase 0 · SPEC, decisions and repository

- **Deliverables:** repository structure; `docs/PRD.md` (original); `docs/SPEC.md`; `CLAUDE.md`; `docs/DECISIONS.md`; `.gitignore`; `.env.example`; first `docs/HANDOFF.md`. No product code.
- **Exit criteria:** Dante approves the SPEC. Repo contains no secrets and no product code. All deliverables committed.

### Phase 1 · Schemas, synthetic dataset and eval runner

- **Deliverables:** JSON Schemas for the entities in 8.1; Supabase migrations with RLS; EPL and wavelength rules in `rules/`; the 44 synthetic orders with packages (PDF, D30) and golden labels; simulated event files; eval runner with a single command; `locales/` skeleton (en, es).
- **Exit criteria:** 100% of orders and golden labels validate against the schemas. All 16 mandatory cases have test data. 100% of documents carry the synthetic mark and 100% of rows have `is_synthetic = true`. No real company names (automated check). The eval runner executes with one command and reports per-eval denominators. Dante has approved the critical-field list and reviewed the 6-order sample.

### Phase 2 · Ingestion and extraction (UC02 partial, RF01)

- **Deliverables:** PDF/DOCX reading (extraction is evaluated on the dataset's PDFs, D30); critical-field extraction with value, source, page, version and date; the six `field_value` statuses; the provider layer with Muse Spark 1.1 and Gemini (gemini-3.8-flash) as the comparison model (D36).
- **Exit criteria:** per-field accuracy reported on the eval split, with ≥95% on critical fields (Decided: D34; the PRD's 98% in 12.1 is reported for information only on synthetic data). Zero values without a source. Zero invented values on clean orders. The same extraction run completes on both providers, with the same prompt and rules, and results compared (D36).
- **Status: Done (D37).** Eval split (12 orders, 13 versions, synthetic): critical-field extraction 828/828 (100%) on both Muse Spark 1.1 and gemini-3.8-flash; traceability 761/761; zero rejected values; zero schema retries. Model time per order on Muse Spark: 43–76 s (11 orders), within the 3-minute target in section 9; gemini-3.8-flash 150–345 s. The data is clean, text-based PDFs, so it does not tell the models apart (backlog D39).
- **As built:** `src/ingest/` (PDF and DOCX), `src/providers/` (Muse Spark and Gemini through OpenAI-compatible clients, schema-validated answers, recording and replay), `src/extract/` and `prompts/`. The model proposes mentions per document; deterministic code keeps only text printed on the cited page, normalizes it and sets each field's status (rules in `rules/extraction.json`). Emails never set or contradict a contractual field value (Decided: D35); in Phase 4 they are evidence for tentative dates, as forecast only. Amended by D57: an email may give a requested date (the customer's own ask) or a forecast, never a committed date. Extraction sets pending, missing, not_applicable and contradictory; verified needs a named human and stale marks a value superseded by a newer version. The eval runner maps source file names to document ids. Muse Spark 1.1 stays the primary model; Gemini stays the comparison model (D37).

### Phase 3 · Validators and gate G1 (UC02, UC03, RF02–RF03)

- **Deliverables:** EPL and wavelength checklists; comparison across documents and versions; severity; findings with owner, due date and action; pass/block recommendation at G1; override with reason and approver; minimal customer scoping (D42); a minimal read-only web view of orders, order detail, delivery progress and parallel workstreams (D45, pulled forward from Phase 8).
- **Exit criteria:** critical discrepancy recall ≥95% and overall precision ≥90% on the eval split. Zero not-ready orders recommended as ready. Zero findings on the 10 clean orders' critical fields. On v2, only affected validations are reopened. Mandatory cases 1, 2, 3, 4 and 8 pass (case 8 with real extraction on development orders, D41). SYN-WAV-0019 is blocked at G1 (D42). SYN-EPL-0001 and SYN-WAV-0016 render in the web view with all their findings visible (D45).
- **Status: Done (D51).** Reviewed by Dante (D41–D50). Eval split (12 orders, 13 versions, synthetic), same result on the Muse Spark 1.1 and gemini-3.8-flash extraction runs: critical recall 6/6, high recall 2/2, precision 8/8, not-ready orders passed 0/4, ready orders blocked 0/9, uncertainty 8/8, version change 1/1. Development orders of cases 1–4 and 8 with real Muse Spark extraction (6 orders, 9 versions, D41): critical recall 6/6, precision 6/6, not-ready passed 0/4, ready blocked 0/5, version change 3/3. The denominators are small: one missed critical finding on the eval split would give 83%. SYN-WAV-0019 with real Muse Spark extraction (6 calls): G1 block, one critical `SEG-OTHER-CUSTOMER` finding citing `06_email_02.pdf` page 1, zero values sourced from an email; it is the only adversarial order with a model run, and the adversarial eval itself stays NOT RUN until Phase 7. Web view: `npm run render-check` shows SYN-EPL-0001, SYN-WAV-0016 and SYN-WAV-0019 with all their findings in English and Spanish.
- **As built:** `src/validators/` is deterministic, with no model call. One finding per G1 field that is missing or contradictory, named by the first matching rule in `rules/findings.json`; severity is the field's `missing_severity`, which a rule can raise and never lower. Each finding keeps every conflicting source (document, page, location), an internal owner, a resolving party, a due date and an action; all are escalated to the resolving party. G1 follows `rules/gates.json`. An override is a human decision stored next to the recommendation with approver and reason: the recommendation, the unmet requirements and the findings stay. A new version reopens only the fields whose current value changed; a document carried over from an earlier version does not count as a change and gets a "reissue" action instead. Changed fields are flagged when they may affect the plan (the plan is Phase 4). Finding text is a `locales/` key with parameters, rendered in English or Spanish. Customer scoping (D42) reads the page text of every document for the names in the tenant's customer register (`data/synthetic/customers.json`, the stand-in for the `customer` table), as whole words with or without the synthetic suffix; it merges into an existing `SEG-OTHER-CUSTOMER` finding instead of raising a second one. Output: `validation.json` (`schemas/validation.schema.json`) next to `extraction.json`. The web view (`web/`, D45, D47) is read-only Next.js that reads those two files from a local folder (`SDI_VIEW_DATA_DIR`, default `runs/phase3-view`): orders list, order detail, delivery progress and parallel workstreams. Progress is completed stages ÷ 11 with equal weights from `rules/stages.json`; Presales is shown as assumed complete (order signed, no G0 record); a stage with a gate is completed only by a human decision, so every order is in "Order received" today; open findings are the workstreams and do not change the percentage. The key date is the committed date if the order states one, else the forecast, else the requested date, always with its type. G1 requirements are shown per field group plus customer scoping. Critical fields are grouped by status (D48): needs action first (contradictory, missing, stale) with the conflict explained and a link to the finding, then pending confirmation by the data owner, then not applicable or not set with its reason; a pending field with no value yet (printed as "To be confirmed") counts as not set (D49). All strings come from `locales/`. In `rules/findings.json`, accepted as proposals (D44): due dates in business days per severity (critical 1, high 2, medium 5, info 10), impact "confirmed" when the finding blocks the gate, and which fields affect the plan. Owners are decided (D46): each finding has an internal owner (`owner`) and a `resolving_party`, set per field group with per-field exceptions in `rules/findings.json`; the finding is escalated to the resolving party. The `finding` table has only `owner`; a `resolving_party` column is added when the migration is next revised.

### Phase 4 · Milestones, dependencies, dates and gate G2 (UC04, UC05, RF04; UC07 minimal slice)

- **Deliverables:** milestone plan with owners; dependency graph; requested, forecast and committed dates; supplier follow-up threshold; *not estimable* status; G2 evaluation; blocked `shared_resource` flags all linked orders. Web view, first task (D52): "Needs action" lists everything that blocks G1, including package-level findings such as `SEG-OTHER-CUSTOMER` with the document and page that triggered them; it is never empty when G1 recommends block, and the render check enforces it. Web view backlog (D50): the "Pending confirmation" block of the critical fields panel is collapsed by default and grouped by field group, with a count per group. Milestone templates per product (Proposed, D56) in `rules/milestones.json`. Supplier follow-up threshold (Proposed, configurable per supplier, D55): first follow-up after 3 business days without an answer, escalation after 5. G2 per product on the basis decided in D54; the rules in `rules/gates.json` are approved by Dante before they are coded. Cases 5–7 are shown with real Muse Spark extraction on their development orders and SYN-WAV-0017 (D53). An email's requested date that differs from the signed order form raises a `DATE-CUSTOMER-CHANGE` finding; the order form value stays until a new order version (D57). No date without an approval record is shown as committed; a stated FOC without one is shown as "Committed — awaiting approval", and the render check enforces it (D58).
- **Progress (in progress):** step 1 (D52) and step 2 (date typing, D57, D58) built and committed; step 3 (milestone plan, `rules/milestones.json`, `src/planner/milestones.py`) approved (D60); an unknown on-net/off-net milestone creates an Engineering action shown in the plan and the workstreams: 43 plans on the real runs, 430 critical milestones, 0 without an owner, 0 committed without an approval, 5 forecasts all with assumptions. `src/planner/dates.py` types every date deterministically from `rules/dates.json`: quote and order-form dates keep their field's type; email dates are typed from their sentence (requested, forecast, or committed only for a supplier dependency from a registered supplier, D26); within one email the tentative reading of a date wins; a committed order date is used only with an approval record. Dates eval 41/41 on the eval split on both models, 25/25 and 17/17 on the development runs; zero dates typed committed that the labels do not type committed.
- **Exit criteria:** 100% of applicable cases distinguish the three dates. Zero forecasts or informal dates stored or shown as committed. Zero critical milestones without an owner. The 3-wavelength project shows the shared blocker on all 3 orders. Mandatory cases 5, 6 and 7 pass.

### Phase 5 · Status per audience and approvals (UC06, RF05–RF06)

- **Deliverables:** the template in section 10; internal, customer and supplier drafts; audience filter; prepared / approved / sent / failed statuses; English and Spanish output from `locales/`. Sending is simulated.
- **Exit criteria:** zero cross-audience leaks in the test cases. ≥4/5 on every rubric dimension, scored by Dante. Every factual claim in a draft has a `source_refs` entry. No draft reaches *sent* without an approval record. Drafts render in both languages with no hardcoded strings.

### Phase 6 · Delivery and acceptance (UC08, gates G3–G4)

- **Deliverables:** readiness review; test-evidence check against contractual criteria; G3 and G4 evaluations; approval routed to the responsible person.
- **Exit criteria:** zero acceptance recommendations without the required evidence. Mandatory cases 9, 15 and 16 pass. Regression of phases 2–5 evals shows no drop.

### Phase 7 · Security, robustness and audit (RF07, RF09, RF10, RF11)

- **Deliverables:** tenant RLS verified with the second synthetic tenant; customer-level scoping; defense against instructions inside documents; idempotency and deduplication; complete audit log; SDM corrections saved as candidate eval cases; every model API retry logged with its reason (for example 429 or timeout), because silent client retries make failures unobservable (RF07, D38).
- **Exit criteria:** zero failures on the 8 adversarial orders and the simulated events. Zero cross-tenant reads in RLS tests. Zero duplicated effects on repeated events; every failure is visible. Mandatory cases 11, 12, 13 and 14 pass. Full eval regression with no drop.

### Phase 8 · Web view and demo

- **Deliverables:** web view of orders, findings, plan and drafts; language switch; 10-minute demo script with synthetic orders; README for operating in shadow mode.
- **Exit criteria:** the six demo steps run end to end with no technical intervention. Every screen and document shows the synthetic mark. UI works in English and Spanish with zero hardcoded strings (automated check). Full eval regression with no drop.

---

## 15. After the build: validation with a carrier (Proposed, from the PRD)

Starts when there is a design-partner carrier. Indicative only, not a delivery promise.

- **Phase A:** confirm product, critical fields, authorities and baseline.
- **Phase B:** offline evaluation with historical orders (the PRD's 100 anonymized orders, expert-labeled).
- **Phase C:** shadow mode on real orders, no external actions.
- **Phase D:** supervised pilot with approved drafts and records.
- **Phase E:** extend reversible actions by policy, keeping approval for commitments and acceptance.

Post-demo backlog: UC01 and G0; full UC07; UC09, UC10 and G5; RF08; mandatory case 10; real integrations (one order source, one communications channel first).

**Pilot exit criterion:** critical evals met; all pilot use cases accepted by the SDM; full traceability of actions; business results reviewed with explicit sample and periods; failure handling and recovery demonstrated. If the sample is insufficient, extend observation rather than declare success.

**Measure in production:** errors by severity, SDM corrections, dismissed alerts, source age, p95 latency, cost per order and per communication, tool failures and duplicated actions. It must be possible to stop sends/writes and fall back to read/draft mode.

---

## 16. Commercial model (Proposed — nothing decided)

Open items for a pilot offer to a design partner: scope and duration; price or free pilot; data the carrier provides; NDA; what the design partner receives; who pays after the pilot and how it is charged.

---

## 17. Open decisions

- Demo step 1 needs an EPL order with 3 seeded errors, while 11.1 allows one or two per order. Either one order gets a third defect or the demo shows two.
- The migration has been parsed and checked against the schemas but not executed: there is no local Postgres. Applying it to a Supabase project needs Dante's approval.
- Backlog before the demo (D39): a "hard" synthetic subset (scanned PDFs, misaligned tables, varied wording) to tell models apart; the current data is too clean. Scanned PDFs need OCR, which is not built.
- Backlog (D40): test lower reasoning effort on Muse Spark (reasoning is about 83% of its output tokens) while keeping extraction ≥95%; requires an eval re-run.
- Field-level `stale`: the labels count a value from a document not reissued for the current version as `pending` (the version mismatch itself is the contradictory `order_version`). The extractor follows that and marks the source as from an earlier version; `stale` is used only when a newer version supersedes a stored value.
- The `finding` table has no `resolving_party` column yet (D46); add it to the entity schema and the migration together.
- Customer scoping (D42) matches names from a register; a customer named in another form (abbreviation, misspelling, logo only) is not detected until Phase 7.
- i18n library for the web view: Proposed, none — the view reads `locales/*.json` directly (D45).
- Web view (Phase 3): local only, not deployed; it has no way to record a human decision at G1, so no order leaves "Order received" on screen. Recording decisions from the UI, the plan and the drafts are Phase 8.
- Supplier sender verification (D59, Phase 7): today a supplier is recognized by the signature line only; verify address or domain against the register. Test case SYN-WAV-0022.
- Backlog after Phase 4 (D61): standard intervals per product in `rules/` to build a delivery forecast labeled "based on standard interval".
- Commercial model (section 16).
- With a pilot carrier: systems and access; data owners; approval authority; test and acceptance criteria; language per audience; cadences and time zones; hypercare window; target volume and cost; retention and processing region.

---

## 18. Traceability: the 11 improvements

| # | Improvement | Where applied |
|---|---|---|
| 1 | Data plan without a carrier | Section 11 |
| 2 | Smaller MVP | Section 3.1, section 5 |
| 3 | Data schema | Section 8 (JSON Schemas delivered in Phase 1) |
| 4 | Initial product decided | Sections 3.1, 8.4 |
| 5 | Default severity | Section 8.3 |
| 6 | Architecture and stack | Section 7.2 |
| 7 | Where the SDM works | Section 3.2 |
| 8 | Commercial model | Section 16 |
| 9 | SDM corrections feed evals | RF11 (section 9), Phase 7 |
| 10 | Glossary and consistent terms | Section 1 |
| 11 | Master prompt split | Section 7.3 |
