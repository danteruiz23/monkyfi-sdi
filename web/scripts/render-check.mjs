// Phase 3 exit criterion (D45): SYN-EPL-0001 and SYN-WAV-0016 render with all their findings visible.
// D52: when G1 recommends block, "needs action" is never empty, and every open finding that blocks G1 has a
// row there that links to it; a package-level finding shows the document and page that triggered it.
// D58: a date without an approval record is never displayed as committed (list and detail pages); a stated
// commitment without one is shown as "committed — awaiting approval".
// Starts the built view, fetches the pages in both languages and compares them with validation.json.
// Usage, from web/: npm run build && npm run render-check [-- ORDER_ID ...]
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const PORT = 3999;
const root = path.resolve(process.cwd(), "..");
const dataDir = path.resolve(root, process.env.SDI_VIEW_DATA_DIR || "runs/phase3-view");
const orders = process.argv.slice(2).length ? process.argv.slice(2) : ["SYN-EPL-0001", "SYN-WAV-0016"];
const mark = (lang) => JSON.parse(fs.readFileSync(path.join(root, "locales", `${lang}.json`), "utf8")).app.synthetic_mark;
const locale = (lang) => JSON.parse(fs.readFileSync(path.join(root, "locales", `${lang}.json`), "utf8"));
const readPlan = (order, version) => {
  const file = path.join(dataDir, order, version, "plan.json");
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : null;
};
/** Every badge styled as an approved commitment, with the date printed just before it. */
function committedBadges(html) {
  return [...html.matchAll(/<span class="date">([^<]*)<\/span><span class="badge date-committed">/g)].map((m) => m[1]);
}
function checkCommitments(where, rawHtml, approved, lang) {
  // Count only rendered markup: Next.js repeats the page text inside <script> payloads.
  const html = rawHtml.replace(/<script\b[\s\S]*?<\/script>/g, "");
  const all = (html.match(/class="badge date-committed"/g) || []).length;
  const dated = committedBadges(html);
  if (all !== dated.length) problems.push(`${where}: a committed badge is not next to its date`);
  for (const date of dated) {
    if (!approved.includes(date)) problems.push(`${where}: ${date} is displayed as committed without an approval record`);
  }
  const label = escape(locale(lang).date_type.committed);
  const labels = html.split(label).length - 1;
  if (labels !== all) problems.push(`${where}: "${locale(lang).date_type.committed}" appears ${labels} time(s), ${all} approved commitment(s)`);
  commitmentChecks += 1;
}
const escape = (text) => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");

const server = spawn("npx", ["next", "start", "-p", String(PORT)], { stdio: "ignore" });
const stop = () => server.kill("SIGTERM");
process.on("exit", stop);

async function get(url) {
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      const response = await fetch(url);
      return { status: response.status, html: await response.text() };
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error(`no answer from ${url}`);
}

const problems = [];
let checked = 0;
let blockerRows = 0;
let commitmentChecks = 0;
let awaitingShown = 0;
for (const lang of ["en", "es"]) {
  const list = await get(`http://localhost:${PORT}/${lang}`);
  if (list.status !== 200 || !list.html.includes(mark(lang))) problems.push(`${lang} orders list: status ${list.status} or no synthetic mark`);
  const listApproved = [];
  for (const order of fs.readdirSync(dataDir).filter((n) => n.startsWith("SYN-"))) {
    for (const version of fs.readdirSync(path.join(dataDir, order)).filter((n) => /^v\d+$/.test(n))) {
      listApproved.push(...(readPlan(order, version)?.dates.order.committed ?? []));
    }
  }
  checkCommitments(`${lang} orders list`, list.html, listApproved, lang);
  for (const order of orders) {
    if (!list.html.includes(`data-order="${order}"`)) problems.push(`${lang} orders list: ${order} is not listed`);
    const versions = fs.readdirSync(path.join(dataDir, order)).filter((n) => /^v\d+$/.test(n)).sort();
    for (const version of versions) {
      const validation = JSON.parse(fs.readFileSync(path.join(dataDir, order, version, "validation.json"), "utf8"));
      const page = await get(`http://localhost:${PORT}/${lang}/orders/${order}?v=${version.slice(1)}`);
      const where = `${lang} ${order} ${version}`;
      if (page.status !== 200) problems.push(`${where}: status ${page.status}`);
      if (!page.html.includes(mark(lang))) problems.push(`${where}: no synthetic mark`);
      const approved = readPlan(order, version)?.dates.order.committed ?? [];
      checkCommitments(where, page.html, approved, lang);
      const stated = JSON.parse(fs.readFileSync(path.join(dataDir, order, version, "extraction.json"), "utf8"))
        .fields.find((f) => f.field_key === "dates.committed");
      if (stated && typeof stated.normalized_value === "string" && ["pending", "verified"].includes(stated.status)
          && !approved.includes(stated.normalized_value)) {
        if (!page.html.includes(`<span class="date">${stated.normalized_value}</span><span class="badge date-committed_awaiting_approval">`)) {
          problems.push(`${where}: stated commitment ${stated.normalized_value} is not shown as awaiting approval`);
        }
        awaitingShown += 1;
      } else if (stated && approved.includes(stated.normalized_value)
          && !committedBadges(page.html).includes(stated.normalized_value)) {
        problems.push(`${where}: approved commitment ${stated.normalized_value} is not shown as committed`);
      }
      const shown = (page.html.match(/data-finding="/g) || []).length;
      if (shown !== validation.findings.length) problems.push(`${where}: ${shown} findings shown, ${validation.findings.length} expected`);
      const extraction = JSON.parse(fs.readFileSync(path.join(dataDir, order, version, "extraction.json"), "utf8"));
      const needsAction = extraction.fields.filter((f) => ["contradictory", "missing", "stale"].includes(f.status));
      const panelStart = page.html.indexOf('data-bucket="needs_action"');
      const panel = panelStart < 0 ? "" : page.html.slice(panelStart, page.html.indexOf('data-bucket="pending"'));
      for (const field of needsAction) {
        const finding = validation.findings.find((f) => f.field_key === field.field_key);
        const rowStart = panel.indexOf(`data-field="${field.field_key}"`);
        const row = rowStart < 0 ? "" : panel.slice(rowStart, panel.indexOf("</tr>", rowStart));
        if (!row) problems.push(`${where}: ${field.field_key} is not in "needs action"`);
        else if (finding && !row.includes(`href="#${finding.finding_id}"`)) problems.push(`${where}: ${field.field_key} has no link to ${finding.finding_id}`);
        for (const source of field.sources) {
          if (row && !row.includes(escape(source.raw_value))) problems.push(`${where}: ${field.field_key} value "${source.raw_value}" is not explained`);
        }
      }
      const rowFields = new Set(needsAction.map((f) => f.field_key));
      const blocking = validation.findings.filter((f) => f.blocks_gate && ["open", "in_progress"].includes(f.status));
      const blockers = blocking.filter((f) => !rowFields.has(f.field_key));
      for (const finding of blockers) {
        const rowStart = panel.indexOf(`data-blocker="${finding.finding_id}"`);
        const row = rowStart < 0 ? "" : panel.slice(rowStart, panel.indexOf("</tr>", rowStart));
        if (!row) { problems.push(`${where}: blocking ${finding.finding_id} (${finding.rule_id}) is not in "needs action"`); continue; }
        if (!row.includes(`href="#${finding.finding_id}"`)) problems.push(`${where}: blocker row has no link to ${finding.finding_id}`);
        const current = extraction.fields.find((f) => f.field_key === finding.field_key)?.raw_value ?? null;
        const differing = finding.conflicting_values.filter((v) => v.raw_value !== current);
        for (const source of differing.length ? differing : finding.conflicting_values) {
          for (const text of [source.filename, source.raw_value]) {
            if (!row.includes(escape(text))) problems.push(`${where}: blocker ${finding.finding_id} does not show "${text}"`);
          }
        }
      }
      const rows = (panel.match(/<tr[^>]*data-field="/g) || []).length;
      if (validation.gate.recommendation === "block" && rows === 0) problems.push(`${where}: G1 recommends block and "needs action" is empty`);
      if (rows !== needsAction.length + blockers.length) problems.push(`${where}: ${rows} "needs action" rows, ${needsAction.length + blockers.length} expected`);
      const counts = [...page.html.matchAll(/data-bucket-count="(\w+)"[^>]*><span[^>]*>(\d+)</g)].map((m) => Number(m[2]));
      const expectedTotal = extraction.fields.length + blockers.length;
      if (counts.length !== 4 || counts[0] !== needsAction.length + blockers.length || counts.reduce((a, b) => a + b, 0) !== expectedTotal) {
        problems.push(`${where}: status counts ${counts.join("+")} do not add up to ${extraction.fields.length} fields + ${blockers.length} other blockers`);
      }
      blockerRows += blockers.length;
      for (const finding of validation.findings) {
        checked += 1;
        const start = page.html.indexOf(`data-finding="${finding.finding_id}"`);
        const next = page.html.indexOf('data-finding="', start + 1);
        const block = start < 0 ? "" : page.html.slice(start, next < 0 ? undefined : next);
        const needed = [finding.field_key, finding.rule_id, finding.due_date,
          ...finding.conflicting_values.flatMap((v) => [v.raw_value, v.filename])];
        for (const text of needed) {
          if (!block.includes(escape(text))) problems.push(`${where} ${finding.finding_id}: "${text}" is not shown`);
        }
      }
    }
  }
}
stop();
console.log(`SYNTHETIC — NOT REAL DATA. Render check: ${orders.join(", ")}; ${checked} finding renderings and ${blockerRows} package-level blocker rows, ${commitmentChecks} pages checked for unapproved commitments (${awaitingShown} shown awaiting approval) in en and es.`);
for (const problem of problems) console.log(`  - ${problem}`);
console.log(problems.length ? "FAIL" : "PASS");
process.exit(problems.length ? 1 : 0);
