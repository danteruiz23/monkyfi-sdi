// Plan section of order detail (Phase 4 step 7): milestones with owners and the three date types,
// supplier dependencies with follow-up, shared resources, supplier inputs and the delivery forecast.
// Read-only. A date is shown as committed only with an approval record (D58).
import type { Plan } from "@/lib/data";
import type { Translate } from "@/lib/i18n";

export function PlanSection({ plan, t }: { plan: Plan | null; t: Translate }) {
  if (!plan?.milestones) {
    return (
      <section className="card" data-testid="plan">
        <h2>{t("ui.plan_title")}</h2>
        <p className="muted">{t("ui.plan_not_built")}</p>
      </section>
    );
  }
  const g2Ids = new Set((plan.g2?.requirements ?? []).map((r) => r.id));
  const inputs = plan.supplier_inputs;
  const forecast = plan.delivery_forecast;
  return (
    <section className="card" data-testid="plan">
      <h2>{t("ui.plan_title")}</h2>
      <p data-supplier-inputs={inputs?.status ?? "none"}>
        {inputs?.status === "missing"
          ? t("ui.supplier_inputs_missing", { items: inputs.missing.join(", ") })
          : t("ui.supplier_inputs_complete")}
        {" · "}
        <span data-delivery-forecast={forecast?.status ?? "none"}>
          {forecast?.status === "estimated" && forecast.date
            ? t("ui.delivery_forecast_estimated", { date: forecast.date })
            : t("ui.delivery_forecast_not_estimable", {
                reason: t(`forecast_reason.${forecast?.reason ?? "no_standard_interval"}`),
              })}
        </span>
      </p>

      <div className="table-wrap">
        <table data-testid="milestones">
          <thead>
            <tr>
              <th>{t("ui.col_milestone")}</th>
              <th>{t("ui.col_internal_owner")}</th>
              <th>{t("ui.col_applies")}</th>
              <th>{t("ui.col_state")}</th>
              <th>{t("ui.col_requested")}</th>
              <th>{t("ui.col_forecast")}</th>
              <th>{t("ui.col_committed")}</th>
            </tr>
          </thead>
          <tbody>
            {plan.milestones.map((m) => (
              <tr key={m.key} data-milestone={m.key} data-owner={m.owner} data-state={m.state}>
                <td>{t(`milestone.${m.key}`)}</td>
                <td>{t(`owner_role.${m.owner}`)}</td>
                <td>{t(`milestone_applicability.${m.applicability}`)}</td>
                <td>
                  <span className={`badge ${m.state === "blocked" ? "stage-blocked" : "neutral"}`}>
                    {t(`milestone_state.${m.state}`)}
                  </span>
                  {m.blocked_by.length > 0 && (
                    <span className="muted small block">
                      {m.blocked_by.map((b) => (g2Ids.has(b) ? t(`g2_requirement.${b}`) : b)).join("; ")}
                    </span>
                  )}
                </td>
                <td>
                  {m.requested_date ? (
                    <>
                      <span className="date">{m.requested_date}</span>
                      <span className="badge date-requested">{t("date_type.requested")}</span>
                    </>
                  ) : (
                    "—"
                  )}
                  {m.requested_conflict.length > 0 && (
                    <span className="muted small block">{t("ui.conflict_quote", { dates: m.requested_conflict.join(", ") })}</span>
                  )}
                </td>
                <td data-forecast-status={m.forecast_status}>
                  {m.forecast_date ? (
                    <>
                      <span className="date">{m.forecast_date}</span>
                      <span className="badge date-forecast">{t("date_type.forecast")}</span>
                      <span className="muted small block">
                        {t("ui.assumptions")}: {m.forecast_assumptions.join(" ")}
                      </span>
                    </>
                  ) : (
                    <span className="muted small">
                      {t("forecast_status.not_estimable")} — {t(`forecast_reason.${m.forecast_reason ?? "no_dated_evidence"}`)}
                    </span>
                  )}
                </td>
                <td>
                  {m.committed_date && m.commitment_approval_id ? (
                    <>
                      <span className="date">{m.committed_date}</span>
                      <span className="badge date-committed">{t("date_type.committed")}</span>
                      <span className="muted small block">{t("ui.approval_record", { id: m.commitment_approval_id })}</span>
                    </>
                  ) : m.committed_awaiting_approval ? (
                    <>
                      <span className="date">{m.committed_awaiting_approval}</span>
                      <span className="badge date-committed_awaiting_approval">
                        {t("date_type.committed_awaiting_approval")}
                      </span>
                    </>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>{t("ui.dependencies_title")}</h3>
      {(plan.dependencies ?? []).length === 0 ? (
        <p className="muted">{t("ui.dependencies_none")}</p>
      ) : (
        <div className="table-wrap">
          <table data-testid="dependencies">
            <thead>
              <tr>
                <th>{t("ui.col_supplier")}</th>
                <th>{t("ui.col_what")}</th>
                <th>{t("ui.col_supplier_date")}</th>
                <th>{t("ui.col_supplier_input")}</th>
                <th>{t("ui.col_follow_up")}</th>
              </tr>
            </thead>
            <tbody>
              {(plan.dependencies ?? []).map((d) => (
                <tr key={d.dependency_id} data-dependency={d.dependency_id} data-supplier-input={d.supplier_input}>
                  <td>
                    {d.dependency_id} {d.supplier}
                  </td>
                  <td>
                    {d.description}
                    <span className="muted small block">{d.source_doc_id}</span>
                  </td>
                  <td>
                    {d.supplier_date ? (
                      <>
                        <span className="date">{d.supplier_date}</span>
                        <span className={`badge ${d.supplier_date_type === "committed" ? "neutral" : "date-forecast"}`}>
                          {d.supplier_date_type === "committed" ? t("ui.supplier_firm_foc") : t("date_type.forecast")}
                        </span>
                        {d.assumptions.length > 0 && (
                          <span className="muted small block">
                            {t("ui.assumptions")}: {d.assumptions.join(" ")}
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="muted">{t("ui.no_supplier_date")}</span>
                    )}
                  </td>
                  <td>{t(`supplier_input.${d.supplier_input}`)}</td>
                  <td>
                    {d.follow_up ? (
                      <>
                        {t(`follow_up_state.${d.follow_up.state}`)}
                        {d.follow_up.first_follow_up_on && (
                          <span className="muted small block">
                            {t("ui.follow_up_dates", {
                              first: d.follow_up.first_follow_up_on,
                              escalation: d.follow_up.escalation_on ?? "—",
                            })}
                          </span>
                        )}
                        {d.follow_up.anchor && (
                          <span className="muted small block" data-anchor="last_supplier_email">
                            {t("ui.follow_up_anchor_last_supplier_email", { date: d.follow_up.anchor })}
                          </span>
                        )}
                      </>
                    ) : (
                      t("ui.follow_up_not_needed")
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(plan.shared_resources ?? []).length > 0 && (
        <>
          <h3>{t("ui.shared_title")}</h3>
          <ul className="compact">
            {(plan.shared_resources ?? []).map((r) => (
              <li key={r.shared_resource_id} data-shared={r.shared_resource_id} data-blocked={String(r.is_blocked)}>
                <code>{r.shared_resource_id}</code>{" "}
                <span className={`badge ${r.is_blocked ? "stage-blocked" : "neutral"}`}>{t(`shared_state.${r.state}`)}</span>{" "}
                {t("ui.shared_linked", { orders: r.linked_order_ids.join(", ") })}
                {r.linked_not_in_run.length > 0 && (
                  <span className="muted small"> ({t("ui.shared_not_in_run", { orders: r.linked_not_in_run.join(", ") })})</span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
