import Link from "next/link";
import { notFound } from "next/navigation";
import { loadVersion, stageRules, versionsOf } from "@/lib/data";
import { isLanguage, translator } from "@/lib/i18n";
import {
  BUCKETS,
  capacityOf,
  customerOf,
  fieldBuckets,
  isApprovedCommitment,
  keyDate,
  openFindings,
  otherBlockers,
  progressOf,
  requirementsOf,
  severityCounts,
} from "@/lib/model";
import { GateBadge, SeverityBadge, SeverityCounts } from "@/lib/ui";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ lang: string; id: string }>;
  searchParams: Promise<{ v?: string }>;
}

export default async function OrderPage({ params, searchParams }: Props) {
  const { lang, id } = await params;
  const { v } = await searchParams;
  if (!isLanguage(lang)) notFound();
  const t = translator(lang);
  const versions = versionsOf(id);
  const latest = versions[versions.length - 1];
  const versionNo = v && /^\d+$/.test(v) ? Number(v) : latest;
  const order = versions.length ? loadVersion(id, versionNo) : null;
  if (!order) {
    return (
      <section>
        <Link href={`/${lang}`}>{t("ui.back_to_orders")}</Link>
        <p>{t("ui.not_found")}</p>
      </section>
    );
  }

  const { extraction, validation } = order;
  const progress = progressOf(validation, stageRules());
  const requirements = requirementsOf(order);
  const open = openFindings(validation);
  const capacity = capacityOf(extraction);
  const date = keyDate(extraction, order.plan);
  const change = validation.version_change;
  const decision = validation.gate.human_decision;
  const buckets = fieldBuckets(extraction);
  const blockers = otherBlockers(order);
  const actions = (order.plan?.actions ?? []).filter((a) => a.status === "open");
  const needsActionCount = buckets.needs_action.length + blockers.length;

  return (
    <article data-order={id} data-version={versionNo}>
      <Link href={`/${lang}`}>{t("ui.back_to_orders")}</Link>
      <header className="order-head">
        <h1>{id}</h1>
        <nav className="versions">
          {versions.map((n) => (
            <Link key={n} href={`/${lang}/orders/${id}?v=${n}`} className={n === versionNo ? "active" : undefined}>
              {t("ui.version", { n })}
              {n === latest && <span className="small"> · {t("ui.current_version")}</span>}
            </Link>
          ))}
        </nav>
      </header>
      <dl className="summary">
        <div>
          <dt>{t("ui.col_customer")}</dt>
          <dd>{customerOf(extraction) ?? t("field_status.missing")}</dd>
        </div>
        <div>
          <dt>{t("ui.col_service")}</dt>
          <dd>
            {extraction.product ? t(`product.${extraction.product}`) : t("field_status.missing")}
            {" · "}
            {capacity.value ?? (capacity.status ? t(`field_status.${capacity.status}`) : t("field_status.missing"))}
          </dd>
        </div>
        <div>
          <dt>{t("ui.col_key_date")}</dt>
          <dd>
            {date ? (
              <>
                <span className="date">{date.date}</span>
                <span className={`badge date-${date.type}`}>{t(`date_type.${date.type}`)}</span>
              </>
            ) : (
              t("ui.no_date")
            )}
          </dd>
        </div>
        <div>
          <dt>{t("ui.col_findings")}</dt>
          <dd>
            <SeverityCounts counts={severityCounts(validation.findings)} t={t} />
          </dd>
        </div>
      </dl>

      <section className="card" data-testid="progress">
        <h2>{t("ui.progress_title")}</h2>
        <p className="progress-value">
          {t("ui.progress_value", { done: progress.done, total: progress.total, percent: progress.percent })}
        </p>
        <div
          className="bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={progress.total}
          aria-valuenow={progress.done}
          aria-label={t("ui.progress_title")}
        >
          <div className="bar-fill" style={{ width: `${progress.percent}%` }} />
        </div>
        <ol className="stages">
          {progress.stages.map((stage) => (
            <li key={stage.key} className={`stage stage-${stage.state}`}>
              <span className="stage-name">{t(`stage.${stage.key}`)}</span>
              {stage.state !== "upcoming" && (
                <span className="stage-state">
                  {stage.state === "assumed_complete" && stage.assumption
                    ? t(`stage_assumption.${stage.assumption}`)
                    : stage.state === "blocked" && stage.gate
                      ? t("ui.stage_blocked_by_gate", { gate: stage.gate })
                      : t(`stage_state.${stage.state}`)}
                </span>
              )}
            </li>
          ))}
        </ol>
        <p className="muted small">{t("ui.progress_method", { total: progress.total })}</p>

        <h3>{t("ui.workstreams_title")}</h3>
        <p className="muted small">{t("ui.workstreams_note")}</p>
        {open.length === 0 && actions.length === 0 ? (
          <p>{t("ui.workstreams_none")}</p>
        ) : (
          <div className="table-wrap">
            <table data-testid="workstreams">
              <thead>
                <tr>
                  <th>{t("ui.col_workstream")}</th>
                  <th>{t("ui.col_status")}</th>
                  <th>{t("ui.col_internal_owner")}</th>
                  <th>{t("ui.col_resolving_party")}</th>
                  <th>{t("ui.col_due")}</th>
                </tr>
              </thead>
              <tbody>
                {open.map((finding) => (
                  <tr key={finding.finding_id}>
                    <td>
                      <a href={`#${finding.finding_id}`}>{finding.finding_id}</a>{" "}
                      <SeverityBadge severity={finding.severity} t={t} /> <code>{finding.field_key}</code>
                    </td>
                    <td>{t(`finding_status.${finding.status}`)}</td>
                    <td>{t(`owner_role.${finding.owner}`)}</td>
                    <td>{t(`owner_role.${finding.resolving_party}`)}</td>
                    <td className="date">{finding.due_date}</td>
                  </tr>
                ))}
                {actions.map((action) => (
                  <tr key={action.action_id} data-action={action.action_id}>
                    <td>
                      {action.action_id} {t(`plan_action.${action.action}`)}{" "}
                      <span className="muted small">
                        · {action.milestone ? t(`milestone.${action.milestone}`) : `${action.dependency} ${action.supplier}`}
                      </span>
                    </td>
                    <td>{t(`finding_status.${action.status}`)}</td>
                    <td>{t(`owner_role.${action.owner}`)}</td>
                    <td>{t(`owner_role.${action.owner}`)}</td>
                    <td className="date">
                      {action.due_date ?? t("ui.due_not_set")}
                      {action.anchor_kind === "last_supplier_email" && action.anchor && (
                        <span className="muted small block" data-anchor="last_supplier_email">
                          {t("ui.follow_up_anchor_last_supplier_email", { date: action.anchor })}
                        </span>
                      )}
                      {(action.history ?? [])
                        .filter((h) => h.event === "first_follow_up_due_not_answered")
                        .map((h) => (
                          <span key={h.event} className="muted small block" data-history={h.event}>
                            {t("ui.follow_up_history_not_answered", { date: h.on })}
                          </span>
                        ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card" data-testid="gate">
        <h2>{t("ui.gate_title")}</h2>
        <p>
          <GateBadge recommendation={validation.gate.recommendation} t={t} />{" "}
          <span className="muted">{t("ui.gate_human_decides")}</span>
        </p>
        <p className="small">
          {decision
            ? t("ui.gate_human_decision", { approver: decision.approval.approver, reason: decision.approval.reason })
            : t("ui.gate_no_human_decision")}
        </p>
        <h3>{t("ui.requirements_title")}</h3>
        <div className="table-wrap">
          <table data-testid="requirements">
            <thead>
              <tr>
                <th>{t("ui.col_requirement")}</th>
                <th>{t("ui.col_result")}</th>
                <th>{t("ui.col_detail")}</th>
                <th>{t("ui.col_blocking")}</th>
              </tr>
            </thead>
            <tbody>
              {requirements.map((row) => (
                <tr key={row.group} className={`requirement-${row.result}`}>
                  <td>{t(`field_group.${row.group}`)}</td>
                  <td>
                    <span className={`badge requirement-${row.result}`}>{t(`ui.requirement_${row.result}`)}</span>
                  </td>
                  <td>
                    {row.total !== null && row.ok !== null
                      ? t("ui.requirement_detail", { ok: row.ok, total: row.total })
                      : row.scopingRun === false
                        ? t("ui.requirement_scoping_not_run")
                        : row.result === "met"
                          ? t("ui.requirement_scoping_ok")
                          : t("finding_rule.SEG-OTHER-CUSTOMER")}
                  </td>
                  <td>
                    {row.blocking.map((finding) => (
                      <a key={finding.finding_id} href={`#${finding.finding_id}`} className="finding-ref">
                        {finding.finding_id} <code>{finding.field_key}</code>
                      </a>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card" data-testid="findings">
        <h2>{t("ui.findings_title")}</h2>
        {validation.findings.length === 0 ? (
          <p>{t("ui.findings_none")}</p>
        ) : (
          <p className="muted">{t("ui.findings_count", { count: validation.findings.length })}</p>
        )}
        {validation.findings.map((finding) => (
          <div key={finding.finding_id} id={finding.finding_id} className="finding" data-finding={finding.finding_id}>
            <h3>
              <span className="finding-id">{finding.finding_id}</span> <SeverityBadge severity={finding.severity} t={t} />{" "}
              <code data-testid="finding-field">{finding.field_key}</code>
              <span className={`badge ${finding.blocks_gate ? "gate-block" : "neutral"}`}>
                {finding.blocks_gate ? t("ui.blocks_gate") : t("ui.does_not_block")}
              </span>
              {finding.reopened && <span className="badge neutral">{t("ui.reopened")}</span>}
            </h3>
            <p>{t(finding.description.key, finding.description.params)}</p>
            <h4>{t("ui.conflicting_values")}</h4>
            {finding.conflicting_values.length === 0 ? (
              <p className="muted">{t("ui.no_value_found")}</p>
            ) : (
              <div className="table-wrap">
                <table className="values">
                  <thead>
                    <tr>
                      <th>{t("ui.col_value")}</th>
                      <th>{t("ui.col_document")}</th>
                      <th>{t("ui.col_page")}</th>
                      <th>{t("ui.col_location")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {finding.conflicting_values.map((value, index) => (
                      <tr key={index} data-testid="conflicting-value">
                        <td className="value">{value.raw_value}</td>
                        <td>
                          {value.filename}
                          {value.stale_source && <span className="badge neutral">{t("ui.earlier_version")}</span>}
                        </td>
                        <td>{value.page}</td>
                        <td className="muted">{value.location}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <dl className="finding-meta">
              <div>
                <dt>{t("ui.internal_owner")}</dt>
                <dd>{t(`owner_role.${finding.owner}`)}</dd>
              </div>
              <div>
                <dt>{t("ui.resolving_party")}</dt>
                <dd>{t(`owner_role.${finding.resolving_party}`)}</dd>
              </div>
              <div>
                <dt>{t("ui.due")}</dt>
                <dd className="date">{finding.due_date}</dd>
              </div>
              <div>
                <dt>{t("ui.col_status")}</dt>
                <dd>{t(`finding_status.${finding.status}`)}</dd>
              </div>
              <div>
                <dt>{t("ui.impact")}</dt>
                <dd>{t(`impact.${finding.impact}`)}</dd>
              </div>
              <div>
                <dt>{t("ui.rule")}</dt>
                <dd>
                  <code>{finding.rule_id}</code>
                </dd>
              </div>
            </dl>
            <p className="action">
              <strong>{t("ui.action")}: </strong>
              {t(finding.action.key, finding.action.params)}
            </p>
          </div>
        ))}
      </section>

      {change && (
        <section className="card" data-testid="changes">
          <h2>{t("ui.changes_title", { n: change.previous_version_no })}</h2>
          <p>
            {t("ui.changes_summary", {
              reopened: change.reopened_validations.length,
              total: change.reopened_validations.length + change.unchanged_validations,
            })}{" "}
            {change.plan_impact ? t("ui.changes_plan_impact") : t("ui.changes_no_plan_impact")}
          </p>
          {change.changed_fields.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("ui.col_field")}</th>
                    <th>{t("ui.col_previous")}</th>
                    <th>{t("ui.col_current")}</th>
                    <th>{t("validation.plan_impact")}</th>
                  </tr>
                </thead>
                <tbody>
                  {change.changed_fields.map((field) => (
                    <tr key={field.field_key}>
                      <td>
                        <code>{field.field_key}</code>
                      </td>
                      <td>{field.previous.join(" · ")}</td>
                      <td>{field.current.join(" · ")}</td>
                      <td>{field.plan_impact ? t("ui.plan_impact_yes") : t("ui.plan_impact_no")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <section className="card" data-testid="fields">
        <h2>{t("ui.fields_title")}</h2>
        <ul className="bucket-counts" aria-label={t("ui.fields_counts_label")}>
          {BUCKETS.map((bucket) => (
            <li key={bucket} className={`bucket-count bucket-${bucket}`} data-bucket-count={bucket}>
              <span className="bucket-number">{bucket === "needs_action" ? needsActionCount : buckets[bucket].length}</span>
              <a href={`#fields-${bucket}`}>{t(`ui.bucket_${bucket}`)}</a>
            </li>
          ))}
        </ul>

        <div id="fields-needs_action" className="bucket bucket-needs_action" data-bucket="needs_action">
          <h3>
            {t("ui.bucket_needs_action")} <span className="badge gate-block">{needsActionCount}</span>
          </h3>
          <p className="muted small">{t("ui.bucket_needs_action_note")}</p>
          {needsActionCount === 0 ? (
            <p>{t("ui.bucket_empty")}</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("ui.col_field")}</th>
                    <th>{t("ui.col_field_status")}</th>
                    <th>{t("ui.col_explanation")}</th>
                    <th>{t("ui.col_finding")}</th>
                  </tr>
                </thead>
                <tbody>
                  {buckets.needs_action.map((field) => {
                    const finding = validation.findings.find((f) => f.field_key === field.field_key);
                    const printed = field.sources.filter((source) => !source.placeholder);
                    return (
                      <tr key={field.field_key} data-field={field.field_key}>
                        <td>
                          <code>{field.field_key}</code>
                        </td>
                        <td>
                          <span className={`badge status-${field.status}`}>{t(`field_status.${field.status}`)}</span>
                        </td>
                        <td>
                          {field.status === "contradictory" ? (
                            <>
                              {t("ui.explain_contradictory", { count: new Set(printed.map((s) => s.raw_value)).size })}{" "}
                              {printed
                                .map((source) =>
                                  t("ui.conflict_item", {
                                    value: source.raw_value,
                                    document: source.filename,
                                    page: t("ui.page_abbrev", { page: source.page }),
                                  }),
                                )
                                .join(" · ")}
                            </>
                          ) : field.status === "stale" ? (
                            t("ui.explain_stale")
                          ) : (
                            t("ui.explain_missing")
                          )}
                        </td>
                        <td>
                          {finding ? (
                            <a href={`#${finding.finding_id}`} className="finding-ref">
                              {finding.finding_id} <SeverityBadge severity={finding.severity} t={t} />
                            </a>
                          ) : (
                            <span className="muted">{t("ui.no_finding")}</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {blockers.map(({ finding, triggers }) => (
                    <tr key={finding.finding_id} data-blocker={finding.finding_id} data-field={finding.field_key}>
                      <td>
                        <code>{finding.rule_id}</code> <code>{finding.field_key}</code>
                      </td>
                      <td>
                        <span className="badge gate-block">{t("ui.package_finding")}</span>
                      </td>
                      <td>
                        {t(finding.description.key, finding.description.params)} {t("ui.explain_triggered_by")}{" "}
                        {triggers
                          .map((source) =>
                            t("ui.conflict_item", {
                              value: source.raw_value,
                              document: source.filename,
                              page: t("ui.page_abbrev", { page: source.page }),
                            }),
                          )
                          .join(" · ")}
                      </td>
                      <td>
                        <a href={`#${finding.finding_id}`} className="finding-ref">
                          {finding.finding_id} <SeverityBadge severity={finding.severity} t={t} />
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {(["pending", "verified"] as const).map((bucket) =>
          bucket === "verified" && buckets.verified.length === 0 ? null : (
            <div key={bucket} id={`fields-${bucket}`} className={`bucket bucket-${bucket}`} data-bucket={bucket}>
              <h3>
                {t(`ui.bucket_${bucket}`)} <span className="badge neutral">{buckets[bucket].length}</span>
              </h3>
              <p className="muted small">{t(`ui.bucket_${bucket}_note`)}</p>
              {buckets[bucket].length === 0 ? (
                <p>{t("ui.bucket_empty")}</p>
              ) : (
                <div className="table-wrap">
                  <table className="fields">
                    <thead>
                      <tr>
                        <th>{t("ui.col_field")}</th>
                        <th>{t("ui.col_field_value")}</th>
                        <th>{t("ui.col_source")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {buckets[bucket].map((field) => (
                        <tr key={field.field_key} data-field={field.field_key}>
                          <td>
                            <code>{field.field_key}</code>
                          </td>
                          <td className="value">
                            {field.raw_value}
                            {field.field_key === "dates.committed" &&
                              typeof field.normalized_value === "string" &&
                              !isApprovedCommitment(order.plan, field.normalized_value) && (
                                <>
                                  {" "}
                                  <span className="badge date-committed_awaiting_approval">
                                    {t("date_type.committed_awaiting_approval")}
                                  </span>
                                </>
                              )}
                          </td>
                          <td className="muted">
                            {field.source
                              ? `${field.source.filename} · ${t("ui.page_abbrev", { page: field.source.page })}`
                              : t("ui.no_source")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ),
        )}

        <div id="fields-not_set" className="bucket bucket-not_set" data-bucket="not_set">
          <h3>
            {t("ui.bucket_not_set")} <span className="badge neutral">{buckets.not_set.length}</span>
          </h3>
          <p className="muted small">{t("ui.bucket_not_set_note")}</p>
          {buckets.not_set.length === 0 ? (
            <p>{t("ui.bucket_empty")}</p>
          ) : (
            <ul className="compact">
              {buckets.not_set.map((field) => {
                const printed = field.sources.find((source) => source.placeholder);
                const where = printed
                  ? { document: printed.filename, page: t("ui.page_abbrev", { page: printed.page }), text: printed.raw_value }
                  : null;
                return (
                  <li key={field.field_key} data-field={field.field_key}>
                    <code>{field.field_key}</code>
                    <span className={`badge status-${field.status}`}>{t(`field_status.${field.status}`)}</span>{" "}
                    <span className="muted">
                      {field.status === "not_applicable"
                        ? where
                          ? t("ui.reason_printed_not_applicable", where)
                          : t("ui.reason_condition_not_met")
                        : where
                          ? t("ui.reason_awaited", where)
                          : t("ui.reason_not_set")}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>

      <p className="muted small">
        {t("ui.extraction_run", {
          model: validation.run.extraction_model,
          version: validation.run.validator_version,
          date: validation.run.evaluated_at,
        })}
      </p>
    </article>
  );
}
