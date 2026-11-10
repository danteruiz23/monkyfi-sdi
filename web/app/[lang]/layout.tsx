import type { ReactNode } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { LANGUAGES, isLanguage, translator } from "@/lib/i18n";
import "../globals.css";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLanguage(lang)) return {};
  const t = translator(lang);
  return { title: `${t("app.name")} · ${t("app.synthetic_mark")}` };
}

export default async function Layout({ children, params }: { children: ReactNode; params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLanguage(lang)) notFound();
  const t = translator(lang);
  return (
    <html lang={lang}>
      <body>
        <div className="synthetic-mark" role="note" data-testid="synthetic-mark">
          {t("app.synthetic_mark")}
        </div>
        <header className="topbar">
          <Link href={`/${lang}`} className="brand">
            {t("app.name")}
          </Link>
          <nav className="languages" aria-label={t("ui.language")}>
            {LANGUAGES.map((code) => (
              <Link key={code} href={`/${code}`} className={code === lang ? "active" : undefined} hrefLang={code}>
                {t(`language.${code}`)}
              </Link>
            ))}
          </nav>
        </header>
        <main>{children}</main>
        <footer className="footer">
          <span>{t("ui.read_only")}</span>
          <span className="synthetic-inline">{t("app.synthetic_mark")}</span>
        </footer>
      </body>
    </html>
  );
}
