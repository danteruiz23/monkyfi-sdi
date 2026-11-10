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
const dataDir = path.resolve(root, process.env.SDI_VIEW_DATA_DIR || "runs/phase4-view");
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
const stageRules = JSON.parse(fs.readFileSync(path.join(root, "rules", "stages.json"), "utf8")).stages;
/** D68, computed here independently of the view: completed stages end to end and within the service
 *  delivery span. A stage counts when assumed complete, when a human passed its gate (G1 in validation.json,
 *  G2 in plan.json), or, without a gate, when a later gate was passed by a human; counting stops at the
 *  first stage that is not complete. */
function expectedProgress(validation, plan) {
  const passed = new Set();
  if (validation.gate.human_decision?.outcome === "pass") passed.add(validation.gate.gate);
  if (plan?.g2?.human_decision?.outcome === "pass") passed.add("G2");
  const done = [];
  for (const [i, stage] of stageRules.entries()) {
    const later = stageRules.slice(i + 1).some((s) => s.exit_gate && passed.has(s.exit_gate));
    if (stage.assumed_complete || (stage.exit_gate && passed.has(stage.exit_gate)) || (!stage.exit_gate && later)) done.push(stage);
    else break;
  }
  const sd = stageRules.filter((s) => s.scope === "service_delivery");
  return { all: [done.length, stageRules.length], sd: [done.filter((s) => s.scope === "service_delivery").length, sd.length] };
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
let actionRows = 0;
let sharedRows = 0;
let g2Pages = 0;
let progressPages = 0;
let planPages = 0;
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
      const plan = readPlan(order, version);
      const expected = expectedProgress(validation, plan);
      for (const [name, [done, total]] of [["service_delivery", expected.sd], ["end_to_end", expected.all]]) {
        const percent = Math.round((100 * done) / total);
        const key = name === "service_delivery" ? "progress_service_delivery" : "progress_end_to_end";
        const text = escape(locale(lang).ui[key].replace("{done}", done).replace("{total}", total).replace("{percent}", percent));
        if (!page.html.includes(`data-progress="${name}" data-done="${done}" data-total="${total}"`) || !page.html.includes(text)) {
          problems.push(`${where}: ${name} progress should read ${done} of ${total} (${percent}%)`);
        }
      }
      if (order === "SYN-EPL-0013" && (expected.sd.join("/") !== "3/8" || expected.all.join("/") !== "4/11")) {
        problems.push(`${where}: D68 example expects service delivery 3 of 8 and end to end 4 of 11`);
      }
      for (const scope of ["before", "service_delivery", "after"]) {
        if (!page.html.includes(`data-scope="${scope}"`)) problems.push(`${where}: progress span ${scope} missing`);
      }
      progressPages += 1;

      // D50: "Pending confirmation" is collapsed by default and grouped by field group with a count per group.
      const pendingStart = page.html.indexOf('data-bucket="pending"');
      const pendingTag = page.html.slice(page.html.lastIndexOf("<", pendingStart), page.html.indexOf(">", pendingStart) + 1);
      if (!pendingTag.startsWith("<details") || /\sopen(=|\s|>)/.test(pendingTag)) problems.push(`${where}: pending block is not collapsed by default`);
      const pendingFields = JSON.parse(fs.readFileSync(path.join(dataDir, order, version, "extraction.json"), "utf8")).fields.filter((f) => f.status === "pending" && f.raw_value !== null);
      const groupCounts = [...page.html.matchAll(/data-field-group="(\w+)" data-count="(\d+)"/g)];
      if (groupCounts.reduce((sum, m) => sum + Number(m[2]), 0) !== pendingFields.length) {
        problems.push(`${where}: pending group counts do not add up to ${pendingFields.length}`);
      }

      // Plan section (step 7): every milestone with its owner; dependencies; never "estimable" wording (D62).
      if (plan?.milestones) {
        const section = page.html.slice(page.html.indexOf('data-testid="plan"'), page.html.indexOf('data-testid="findings"'));
        for (const m of plan.milestones) {
          const start = section.indexOf(`data-milestone="${m.key}"`);
          const row = start < 0 ? "" : section.slice(start, section.indexOf("</tr>", start));
          if (!row || !row.includes(`data-owner="${m.owner}"`) || !row.includes(escape(locale(lang).owner_role[m.owner]))) {
            problems.push(`${where}: milestone ${m.key} is not shown with its owner`);
          }
          if (m.is_critical && !m.owner) problems.push(`${where}: critical milestone ${m.key} has no owner`);
          if (m.forecast_date && !row.includes(m.forecast_date)) problems.push(`${where}: forecast of ${m.key} not shown`);
        }
        for (const d of plan.dependencies ?? []) {
          if (!section.includes(`data-dependency="${d.dependency_id}" data-supplier-input="${d.supplier_input}"`)) {
            problems.push(`${where}: dependency ${d.dependency_id} not shown with its supplier input`);
          }
        }
        for (const r of plan.shared_resources ?? []) {
          if (!section.includes(`data-shared="${r.shared_resource_id}" data-blocked="${r.is_blocked}"`)) {
            problems.push(`${where}: shared resource ${r.shared_resource_id} not shown on this order`);
          }
        }
        if (/estimable \/|"estimable"/i.test(section)) problems.push(`${where}: "estimable" wording shown (D62)`);
        planPages += 1;
      }
      if (plan?.g2) {
        const card = page.html.slice(page.html.indexOf('data-testid="g2"'), page.html.indexOf('data-testid="findings"'));
        const text = locale(lang);
        if (!card.includes(escape(text.recommendation[plan.g2.recommendation]))) problems.push(`${where}: G2 recommendation not shown`);
        for (const r of plan.g2.requirements) {
          const start = card.indexOf(`data-g2-requirement="${r.id}"`);
          const row = start < 0 ? "" : card.slice(start, card.indexOf("</tr>", start));
          if (!row.includes(`data-result="${r.result}"`)) problems.push(`${where}: G2 ${r.id} not shown as ${r.result}`);
          for (const item of r.missing) {
            const kind = item.split(":")[0];
            const label = text.g2_missing[kind].split("{")[0].trim();
            if (!row.includes(escape(label))) problems.push(`${where}: G2 ${r.id} does not explain ${item}`);
          }
        }
        const decided = plan.g2.human_decision ? plan.g2.human_decision.outcome : "none";
        if (!card.includes(`data-g2-decision="${decided}"`)) problems.push(`${where}: G2 human decision not shown`);
        const stageName = escape(text.stage.design_and_dependencies);
        const stageAt = page.html.indexOf(`<span class="stage-name">${stageName}</span>`);
        const stageLi = page.html.slice(page.html.lastIndexOf("<li", stageAt), stageAt);
        if (decided === "pass" && !stageLi.includes("stage-completed")) problems.push(`${where}: G2 passed but design stage not completed`);
        if (decided !== "pass" && stageLi.includes("stage-completed")) problems.push(`${where}: design stage completed without a human G2 pass`);
        g2Pages += 1;
      }
      const approved = plan?.dates.order.committed ?? [];
      const workstreams = page.html.slice(page.html.indexOf('data-testid="workstreams"'), page.html.indexOf('data-testid="gate"'));
      for (const action of (plan?.actions ?? []).filter((a) => a.status === "open")) {
        const start = workstreams.indexOf(`data-action="${action.action_id}"`);
        const row = start < 0 ? "" : workstreams.slice(start, workstreams.indexOf("</tr>", start));
        if (!row || !row.includes(escape(locale(lang).plan_action[action.action])) || !row.includes(escape(locale(lang).owner_role[action.owner]))) {
          problems.push(`${where}: plan action ${action.action_id} (${action.action}) is not in the workstreams with its owner`);
        }
        if (action.anchor_kind === "last_supplier_email"
            && !row.includes(escape(locale(lang).ui.follow_up_anchor_last_supplier_email.replace("{date}", action.anchor)))) {
          problems.push(`${where}: follow-up ${action.action_id} does not say it is counted from the last supplier email`);
        }
        if (action.shared_resource) {
          for (const linked of action.linked_order_ids ?? []) {
            if (!row.includes(linked)) problems.push(`${where}: shared ${action.shared_resource} does not name linked order ${linked}`);
          }
          sharedRows += 1;
        }
        for (const h of action.history ?? []) {
          if (!row.includes(`data-history="${h.event}"`)) problems.push(`${where}: ${action.action_id} history ${h.event} is not shown`);
        }
        actionRows += 1;
      }
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
console.log(`SYNTHETIC — NOT REAL DATA. Render check: ${orders.join(", ")}; ${checked} finding renderings and ${blockerRows} package-level blocker rows, ${commitmentChecks} pages checked for unapproved commitments (${awaitingShown} shown awaiting approval), ${actionRows} plan action rows (${sharedRows} shared-resource rows), ${g2Pages} G2 cards, ${progressPages} pages with both progress numbers, ${planPages} plan sections, in en and es.`);
for (const problem of problems) console.log(`  - ${problem}`);
console.log(problems.length ? "FAIL" : "PASS");
process.exit(problems.length ? 1 : 0);
