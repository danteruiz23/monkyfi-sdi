import type { Translate } from "./i18n";
import type { Severity } from "./data";
import { SEVERITIES } from "./data";

export function SeverityBadge({ severity, t }: { severity: Severity; t: Translate }) {
  return <span className={`badge severity-${severity}`}>{t(`severity.${severity}`)}</span>;
}

export function GateBadge({ recommendation, t }: { recommendation: "pass" | "block"; t: Translate }) {
  return <span className={`badge gate-${recommendation}`}>{t(`recommendation.${recommendation}`)}</span>;
}

export function SeverityCounts({ counts, t }: { counts: Record<Severity, number>; t: Translate }) {
  return (
    <span className="counts">
      {SEVERITIES.map((severity) => (
        <span
          key={severity}
          className={`count severity-${severity}${counts[severity] ? "" : " zero"}`}
          title={t(`severity.${severity}`)}
        >
          <span className="count-label">{t(`severity.${severity}`)}</span>
          <span className="count-value">{counts[severity]}</span>
        </span>
      ))}
    </span>
  );
}
