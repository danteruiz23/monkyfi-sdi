import Link from "next/link";
import { notFound } from "next/navigation";
import { DATA_DIR_NAME } from "@/lib/config";
import { listOrders, stageRules } from "@/lib/data";
import { isLanguage, translator } from "@/lib/i18n";
import { capacityOf, customerOf, keyDate, progressOf, severityCounts } from "@/lib/model";
import { GateBadge, SeverityCounts } from "@/lib/ui";

export const dynamic = "force-dynamic";

export default async function OrdersPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLanguage(lang)) notFound();
  const t = translator(lang);
  const orders = listOrders();
  const stages = stageRules();

  return (
    <section>
      <h1>{t("ui.orders_title")}</h1>
      <p className="muted">
        {orders.length ? t("ui.orders_count", { count: orders.length }) : t("ui.no_orders", { dir: DATA_DIR_NAME })}
      </p>
      {orders.length > 0 && (
        <div className="table-wrap">
          <table className="orders" data-testid="orders-table">
            <thead>
              <tr>
                <th>{t("ui.col_order")}</th>
                <th>{t("ui.col_customer")}</th>
                <th>{t("ui.col_service")}</th>
                <th>{t("ui.col_stage")}</th>
                <th>{t("ui.col_g1")}</th>
                <th>{t("ui.col_findings")}</th>
                <th>{t("ui.col_key_date")}</th>
              </tr>
            </thead>
            <tbody>
              {orders.map(({ orderId, versionNo, extraction, validation, plan }) => {
                const progress = progressOf(validation, stages);
                const current = progress.stages.find((s) => s.key === progress.current);
                const capacity = capacityOf(extraction);
                const date = keyDate(extraction, plan);
                return (
                  <tr key={orderId} data-order={orderId}>
                    <td>
                      <Link href={`/${lang}/orders/${orderId}`} className="order-link">
                        {orderId}
                      </Link>
                      <span className="muted small"> {t("ui.version", { n: versionNo })}</span>
                    </td>
                    <td>{customerOf(extraction) ?? t("field_status.missing")}</td>
                    <td>
                      {extraction.product ? t(`product.${extraction.product}`) : t("field_status.missing")}
                      <span className="muted">
                        {" · "}
                        {capacity.value ?? (capacity.status ? t(`field_status.${capacity.status}`) : t("field_status.missing"))}
                      </span>
                    </td>
                    <td>
                      {t(`stage.${progress.current}`)}
                      {current?.state === "blocked" && (
                        <span className="badge stage-blocked">{t("stage_state.blocked")}</span>
                      )}
                    </td>
                    <td>
                      <GateBadge recommendation={validation.gate.recommendation} t={t} />
                    </td>
                    <td>
                      <SeverityCounts counts={severityCounts(validation.findings)} t={t} />
                    </td>
                    <td>
                      {date ? (
                        <>
                          <span className="date">{date.date}</span>
                          <span className={`badge date-${date.type}`}>{t(`date_type.${date.type}`)}</span>
                        </>
                      ) : (
                        <span className="muted">{t("ui.no_date")}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
