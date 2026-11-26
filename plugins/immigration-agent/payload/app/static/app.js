// Immigration Agent dashboard. Every value from case files is inserted as text (never as HTML).
"use strict";
const KEY = document.querySelector('meta[name="agent-key"]').content;
const main = document.getElementById("main");
const SVG = "http://www.w3.org/2000/svg";

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    e.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return e;
}

// Line icons (24 x 24, drawn with the text colour).
const ICONS = {
  copy: "M9 9h10v10H9zM5 15V5h10",
  open: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4",
  back: "M19 12H5M11 6l-6 6 6 6",
  check: "M5 12.5l4.5 4.5L19 7.5",
  folder: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
  growth: "M3 17l6-6 4 4 8-8M14 7h7v7",
  share: "M8.6 13.5l6.8 4M15.4 6.5l-6.8 4M18 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  calendar: "M7 3v3M17 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM12 12v5M9.5 14.5h5",
};
function icon(name) {
  const s = document.createElementNS(SVG, "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  s.setAttribute("aria-hidden", "true");
  const p = document.createElementNS(SVG, "path");
  p.setAttribute("d", ICONS[name]);
  s.append(p);
  return s;
}

const CLOSED = "The dashboard has stopped (it stops by itself a few minutes after its window is closed, or when the computer sleeps). Open it again from the Immigration Agent Dashboard shortcut on your desktop.";

async function api(path) {
  let r;
  try { r = await fetch(path, { credentials: "same-origin", cache: "no-store" }); } catch { throw new Error(CLOSED); }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `The dashboard could not load this page (${r.status}). Reopen it from its shortcut.`);
  return body;
}

async function openPath(path) {
  const r = await fetch("/api/open", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Agent-Key": KEY }, body: JSON.stringify({ path }) });
  const body = await r.json().catch(() => ({}));
  toast(r.ok ? "Opening…" : (body.error || "Could not open it"));
}

let toastTimer;
function toast(text) {
  const t = document.getElementById("toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3500);
}

async function copyCommand(cmd) {
  try {
    await navigator.clipboard.writeText(cmd);
    toast(`Copied ${cmd}. Paste it in the Claude app (Code tab, this agent folder).`);
  } catch {
    toast(`Type this in the Claude app: ${cmd}`);
  }
}

const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
  return isNaN(d) ? iso : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
};
const fmtLong = (iso) => {
  const d = new Date((iso || "") + "T00:00:00");
  return isNaN(d) ? "" : d.toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
};
const fmtLeft = (n) => n === "" || n === null || n === undefined ? "" : n < 0 ? `${-n} day${n === -1 ? "" : "s"} overdue` : n === 0 ? "Due today" : `In ${n} day${n === 1 ? "" : "s"}`;
const fmtSize = (b) => b < 1024 ? `${b} B` : b < 1048576 ? `${Math.round(b / 1024)} KB` : `${(b / 1048576).toFixed(1)} MB`;
const money = (v) => { const n = Number(v); return isNaN(n) ? v : n.toLocaleString(undefined, { style: "currency", currency: "CAD" }); };
const initials = (name) => (name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
const extOf = (name) => { const m = /\.([a-z0-9]+)$/i.exec(name || ""); return m ? m[1].toLowerCase() : ""; };
const caseTag = (folder, text) => el("a", { class: "case-tag", href: "#case/" + encodeURIComponent(folder) }, text || folder);

function dueChip(left, level) {
  if (left === "" || left === null || left === undefined) return null;
  const tone = level === "Urgent" || level === "Soon" ? level : left < 0 ? "Urgent" : left <= 7 ? "Soon" : "neutral";
  return el("span", { class: "pill " + tone }, fmtLeft(left));
}

function pageHead(eyebrow, title, sub, actions) {
  return el("div", { class: "head" },
    el("div", { class: "head-text" }, eyebrow ? el("div", { class: "eyebrow" }, eyebrow) : null, el("h1", {}, title), sub ? el("div", { class: "sub" }, sub) : null),
    actions ? el("div", { class: "head-actions" }, actions) : null);
}

function panel(title, extra, ...body) {
  return el("section", { class: "panel" },
    el("div", { class: "panel-head" }, el("h2", {}, title), extra || null),
    ...body);
}

function empty(text, ok) {
  return el("div", { class: "empty" }, ok ? icon("check") : null, el("div", {}, text));
}

function searchBox(placeholder, onInput) {
  return el("label", { class: "search" }, icon("search"),
    el("input", { type: "search", placeholder, "aria-label": placeholder, oninput: (e) => onInput(e.target.value.trim().toLowerCase()) }));
}

function cmdList(cmds) {
  return el("div", { class: "cmds" }, cmds.map((c) =>
    el("div", { class: "cmd" },
      el("div", { class: "cmd-text" }, el("div", { class: "t" }, c.label), el("div", { class: "hlp" }, c.help), el("code", {}, c.command)),
      el("button", { class: "btn", onclick: () => copyCommand(c.command), title: "Copy, then paste in the Claude app" }, icon("copy"), "Copy"))));
}

function alertList(alerts, showCase) {
  if (!alerts.length) return empty("Nothing needs attention.", true);
  return el("div", { class: "alerts" }, alerts.map((a) =>
    el("div", { class: "alert " + a.level },
      el("div", { class: "alert-main" },
        el("div", { class: "alert-top" },
          el("span", { class: "pill " + a.level }, a.level),
          showCase ? (a.case === "All files" ? el("span", { class: "case-tag" }, a.case) : caseTag(a.case)) : null,
          el("span", { class: "alert-what" }, a.kind)),
        el("div", { class: "alert-text" }, a.text),
        a.step ? el("div", { class: "alert-step" }, el("b", {}, "Next step: "), a.step) : null),
      el("div", { class: "due" },
        a.day ? el("div", { class: "due-date" }, fmtDate(a.day)) : null,
        dueChip(a.left, a.level)))));
}

function kbPanel(kb, policy) {
  const stale = kb.counts.stale + kb.counts["needs seed"];
  const bar = el("span");
  bar.style.width = `${kb.total ? Math.round((kb.counts.ok / kb.total) * 100) : 0}%`;
  return panel("Knowledge base", el("span", { class: "pill " + (stale ? "Soon" : "ok") }, stale ? `${stale} to review` : "Up to date"),
    el("div", { class: "panel-body kb" },
      el("div", { class: "kb-line" }, el("span", { class: "kb-big" }, `${kb.counts.ok} / ${kb.total}`), el("span", { class: "small muted" }, "files current")),
      el("div", { class: "meter" + (stale ? " warn" : "") }, bar),
      policy && policy.date ? el("div", { class: "small muted" }, `Policy changes last checked ${fmtDate(policy.date)}`,
        policy.age > policy.stale_after ? el("span", {}, ". Ask Claude: ", el("code", { class: "mono" }, "/changelog")) : null) : null));
}

// ---- IRCC data tab: a summary strip, then processing times or the application inventory (one at a time) ----
const COUNTRY_KEY = "agent.irccCountry";
const IRCC_VIEW_KEY = "agent.irccView";
const nf = (v) => (v === null || v === undefined || v === "" ? "–" : Number(v).toLocaleString("en-CA"));
const signed = (v) => (v === null || v === undefined ? "" : v === 0 ? "no change" : `${v < 0 ? "↓" : "↑"} ${Math.abs(v).toLocaleString("en-CA")}`);

function freshPill(stale, label) {
  return el("span", { class: "pill " + (stale ? "Soon" : "ok") }, stale ? "Out of date" : label);
}

function irccSummary(inv, t, rd) {
  const tile = (label, value, sub, cls) => el("div", { class: "isum " + (cls || "") }, el("div", { class: "l" }, label), el("div", { class: "n" }, value), sub ? el("div", { class: "h" }, sub) : null);
  const tiles = [];
  if (inv && inv.pr) {
    const since = inv.prev_data_as_of ? ` since ${fmtDate(inv.prev_data_as_of)}` : "";
    tiles.push(tile("Permanent residence in queue", nf(inv.pr.total.not_finalized), inv.pr.total.change === null ? null : signed(inv.pr.total.change) + since, inv.pr.total.change < 0 ? "down" : "up"));
    const rows = inv.pr.rows.filter((r) => r.waiting_pct !== null && r.waiting_pct !== undefined);
    const all = rows.reduce((s, r) => s + r.not_finalized, 0);
    if (all) {
      const held = Math.round(rows.reduce((s, r) => s + r.not_finalized * r.waiting_pct, 0) / all);
      tiles.push(tile("PR files held for space", `${held}%`, rows.map((r) => `${r.label} ${r.waiting_pct}%`).join(" · ")));
    }
    if (inv.tr) tiles.push(tile("Temporary residence in queue", nf(inv.tr.total.not_finalized), inv.tr.total.change === null ? null : signed(inv.tr.total.change) + since, inv.tr.total.change < 0 ? "down" : "up"));
  }
  if (t) {
    const cec = t.pr.flatMap((g) => g.rows).find((r) => r.key === "cec");
    if (cec) tiles.push(tile("Express Entry (CEC) estimate", cec.time || "–", cec.waiting ? `${cec.waiting} waiting` : null));
  }
  const last = rd && rd.rows[0];
  if (last && tiles.length < 4) tiles.push(tile("Latest Express Entry round", `CRS ${last.crs}`, `#${last.number} · ${fmtDate(last.date)} · ${nf(last.size)} invitations`));
  return tiles.length ? el("div", { class: "isums" }, tiles) : null;
}

function segmented(options, current, onPick, label) {
  const box = el("div", { class: "segctl", role: "tablist", "aria-label": label });
  const paint = () => { for (const b of box.children) { const on = b.dataset.key === current; b.classList.toggle("on", on); b.setAttribute("aria-selected", on ? "true" : "false"); } };
  for (const [key, text] of options) box.append(el("button", { role: "tab", "data-key": key, onclick: () => { current = key; paint(); onPick(key); } }, text));
  paint();
  return box;
}

function countryCard(t) {
  if (!t.countries.length) return null;
  let code = "";
  try { code = localStorage.getItem(COUNTRY_KEY) || ""; } catch { /* storage unavailable */ }
  if (!t.countries.some((c) => c.code === code)) code = t.countries.some((c) => c.code === "IN") ? "IN" : t.countries[0].code;
  const tiles = el("div", { class: "ctimes" });
  const show = () => {
    const c = t.countries.find((x) => x.code === code);
    tiles.replaceChildren(...t.country_cols.map((col) => el("div", { class: "ctime" },
      el("div", { class: "l" }, col.label), el("div", { class: "n" + (c[col.key] ? "" : " none") }, c[col.key] || "Not published"))));
  };
  const sel = el("select", { id: "ircc-country", onchange: (e) => { code = e.target.value; try { localStorage.setItem(COUNTRY_KEY, code); } catch { /* ignore */ } show(); } },
    t.countries.map((c) => el("option", { value: c.code, selected: c.code === code }, c.country)));
  show();
  const all = el("details", { class: "call" }, el("summary", {}, `Compare all ${t.countries.length} countries`),
    el("div", { class: "inv-scroll" }, el("table", { class: "inv-table" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Country of residence"), t.country_cols.map((col) => el("th", { scope: "col", class: "num" }, col.label)))),
      el("tbody", {}, t.countries.map((c) => el("tr", {}, el("th", { scope: "row" }, c.country), t.country_cols.map((col) => el("td", { class: "num" }, c[col.key] || "–"))))))));
  return el("section", { class: "panel" },
    el("div", { class: "panel-head" }, el("h2", {}, "Visas and permits from outside Canada"), freshPill(t.stale, `Updated ${fmtDate(t.country_updated)}`)),
    el("div", { class: "panel-body ccard" },
      el("div", { class: "ccard-pick" }, el("label", { class: "field-label", for: "ircc-country" }, "Client lives in"), sel),
      tiles),
    el("div", { class: "panel-body" }, all));
}

function timesTable(t) {
  const sets = { pr: { groups: t.pr, waiting: true, updated: t.pr_updated }, other: { groups: t.other, waiting: false, updated: t.other_updated } };
  let which = "pr", q = "";
  const table = el("div", { class: "inv-scroll" });
  const stamp = el("span");
  const draw = () => {
    const s = sets[which];
    stamp.replaceChildren(freshPill(t.stale, `Updated ${fmtDate(s.updated)}`));
    const groups = s.groups.map((g) => ({ ...g, rows: g.rows.filter((r) => !q || (g.group + " " + r.label).toLowerCase().includes(q)) })).filter((g) => g.rows.length);
    table.replaceChildren(groups.length ? el("table", { class: "inv-table times clean" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col" }, which === "pr" ? "Program" : "Service"), el("th", { scope: "col", class: "num" }, "IRCC estimate"),
        s.waiting ? el("th", { scope: "col", class: "num" }, "People waiting") : null)),
      groups.map((g) => el("tbody", {},
        el("tr", { class: "grp" }, el("th", { scope: "rowgroup", colspan: s.waiting ? "3" : "2" }, g.group)),
        g.rows.map((r) => el("tr", {}, el("th", { scope: "row" }, r.label), el("td", { class: "num time" }, r.time || "–"),
          s.waiting ? el("td", { class: "num muted" }, r.waiting || "–") : null))))) : empty("Nothing matches your search."));
  };
  draw();
  return el("section", { class: "panel" },
    el("div", { class: "panel-head" }, el("h2", {}, "Processing times"), stamp),
    el("div", { class: "times-tools" },
      segmented([["pr", "PR and citizenship"], ["other", "In Canada and other services"]], which, (k) => { which = k; draw(); }, "Which processing times"),
      searchBox("Find a program or service", (v) => { q = v; draw(); })),
    table);
}

function inventoryView(inv) {
  if (!inv || !inv.pr || !inv.pr.rows.length) return panel("Application inventory", null, empty("No inventory data in this version."));
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const m = Number((inv.data_as_of || "").slice(5, 7));
  const fin = m ? `Finalized ${m === 1 ? "Jan" : `Jan–${MONTHS[m - 1]}`}` : "Finalized this year";
  const chg = (v) => el("td", { class: "num " + (v > 0 ? "up" : v < 0 ? "down" : "") }, v === null || v === undefined ? "–" : v === 0 ? "0" : (v > 0 ? "+" : "−") + Math.abs(v).toLocaleString("en-CA"));
  const bar = (pct) => el("td", { class: "held" }, pct === null || pct === undefined ? "–" : el("div", { class: "held-cell" },
    el("div", { class: "held-bar" }, (() => { const s = el("span"); s.style.width = `${pct}%`; return s; })()), el("span", { class: "held-n" }, `${pct}%`)));
  const tbl = (title, part, pr) => el("section", { class: "panel" },
    el("div", { class: "panel-head" }, el("h2", {}, `${title}: ${nf(part.total.not_finalized)} in queue`),
      part.total.change === null ? null : el("span", { class: "count" }, `${signed(part.total.change)} in a month`)),
    el("div", { class: "inv-scroll" }, el("table", { class: "inv-table clean" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Category"), el("th", { scope: "col", class: "num" }, "In queue"), el("th", { scope: "col", class: "num" }, "Change"),
        pr ? el("th", { scope: "col" }, "Held for space") : null, el("th", { scope: "col", class: "num" }, fin))),
      el("tbody", {}, part.rows.map((r) => el("tr", {}, el("th", { scope: "row" }, r.label), el("td", { class: "num strong" }, nf(r.not_finalized)), chg(r.change),
        pr ? bar(r.waiting_pct) : null, el("td", { class: "num muted" }, nf(r.finalized_ytd))))))));
  return el("div", { class: "col" },
    tbl("Permanent residence", inv.pr, true),
    inv.tr ? tbl("Temporary residence", inv.tr, false) : null,
    el("p", { class: "footnote" }, `In queue: applications not yet finalized on ${fmtDate(inv.data_as_of)}. Change: since ${fmtDate(inv.prev_data_as_of)}. `,
      "Held for space: files waiting because the yearly admission targets are full (not a processing delay). IRCC rounds figures to the nearest 5. Source: ",
      el("a", { href: inv.source, target: "_blank", rel: "noopener" }, inv.source_name), `, page dated ${fmtDate(inv.page_date)}.`,
      inv.stale ? el("span", { class: "warn" }, ` Older than ${inv.stale_after} days: ask Claude /changelog.`) : null));
}

function roundsView(rd) {
  if (!rd || !rd.rows.length) return panel("Express Entry rounds", null, empty("No rounds saved yet on this computer. Click Check now to read IRCC's rounds page."));
  let q = "";
  const year = String(new Date().getFullYear());
  const thisYear = rd.rows.filter((r) => (r.date || "").startsWith(year));
  const table = el("div", { class: "inv-scroll" });
  const draw = () => {
    const rows = rd.rows.filter((r) => !q || `${r.name} ${r.number} ${r.date} ${fmtDate(r.date)}`.toLowerCase().includes(q));
    table.replaceChildren(rows.length ? el("table", { class: "inv-table clean rounds" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Date"), el("th", { scope: "col", class: "num" }, "Round"), el("th", { scope: "col" }, "Round type"),
        el("th", { scope: "col", class: "num" }, "CRS cut-off"), el("th", { scope: "col", class: "num" }, "Invitations (ITAs)"), el("th", { scope: "col" }, "Details"))),
      el("tbody", {}, rows.map((r) => el("tr", { title: r.programs ? `Programs: ${r.programs}` : null },
        el("td", { class: "nowrap" }, fmtDate(r.date)), el("td", { class: "num muted" }, `#${r.number}`), el("th", { scope: "row" }, r.name),
        el("td", { class: "num strong" }, nf(r.crs)), el("td", { class: "num" }, nf(r.size)),
        el("td", {}, el("a", { href: r.url, target: "_blank", rel: "noopener", title: `IRCC's page for round #${r.number}` }, "IRCC page ↗")))))) : empty("Nothing matches your search."));
  };
  draw();
  return el("div", { class: "col" },
    el("section", { class: "panel" },
      el("div", { class: "panel-head" }, el("h2", {}, "Express Entry rounds"),
        rd.rows[rd.rows.length - 1].date < year ? el("span", { class: "count" }, `${thisYear.length} rounds and ${nf(thisYear.reduce((s, r) => s + (r.size || 0), 0))} invitations in ${year}`) : null),
      el("div", { class: "times-tools" }, searchBox("Find a round type, number or date", (v) => { q = v; draw(); })),
      table),
    el("p", { class: "footnote" }, `Most recent ${rd.rows.length} rounds as IRCC publishes them. Details opens IRCC's page for that round: tie-breaking rule, programs covered and the CRS score distribution. Source: `,
      el("a", { href: rd.source, target: "_blank", rel: "noopener" }, rd.source_name), rd.checked ? `, read ${fmtDate(rd.checked)}.` : ".",
      rd.stale ? el("span", { class: "warn" }, " Not read in the last day: click Check now.") : null,
      " To see which of your clients a round reaches, ask Claude: ", el("code", { class: "mono" }, "/draws check")));
}

const PNP_PROV_KEY = "agent.pnpProvince";

function provincialView(pv) {
  if (!pv) return panel("Provincial draws", null, empty("Provincial draws couldn't be loaded."));
  const provs = [...new Map(pv.rows.map((r) => [r.province, r.province_name])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
  let prov = "", q = "";
  try { prov = localStorage.getItem(PNP_PROV_KEY) || ""; } catch { /* ignore */ }
  if (prov && !provs.some(([c]) => c === prov)) prov = "";
  const table = el("div", { class: "inv-scroll" });
  const head = el("span", { class: "count" });
  const draw = () => {
    const rows = pv.rows.filter((r) => (!prov || r.province === prov) && (!q || `${r.province_name} ${r.province} ${r.stream} ${r.date} ${fmtDate(r.date)}`.toLowerCase().includes(q)));
    const draws = new Set(rows.filter((r) => !r.recorded).map((r) => r.province + r.date)).size;
    head.replaceChildren(rows.length ? `${draws} draw${draws === 1 ? "" : "s"}, ${rows.length} stream row${rows.length === 1 ? "" : "s"}` : "");
    table.replaceChildren(rows.length ? el("table", { class: "inv-table clean rounds" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Date"), el("th", { scope: "col" }, "Province"), el("th", { scope: "col" }, "Stream"),
        el("th", { scope: "col", class: "num" }, "Minimum score"), el("th", { scope: "col", class: "num" }, "Invitations"), el("th", { scope: "col" }, "Details"))),
      el("tbody", {}, rows.map((r) => el("tr", {},
        el("td", { class: "nowrap" }, r.monthly ? fmtDate(r.date).replace(/ \d+,/, "") : fmtDate(r.date)),
        el("td", { class: "nowrap" }, r.province_name),
        el("th", { scope: "row" }, r.stream, r.note ? el("div", { class: "small muted" }, r.note) : null, r.recorded ? el("span", { class: "tag", title: r.note || "Recorded with /draws pnp-add" }, " recorded by you") : null),
        el("td", { class: "num strong" }, r.score || "–"), el("td", { class: "num" }, r.count || "–"),
        el("td", {}, r.link ? el("a", { href: r.link, target: "_blank", rel: "noopener", title: `${r.province_name}'s own draw page` }, `${r.site || "Official page"} ↗`) : "–"))))) : empty(pv.rows.length ? "Nothing matches." : "No provincial draws saved yet on this computer. Click Check now to read the provinces' draw pages."));
  };
  draw();
  const sel = el("select", { "aria-label": "Province", onchange: (e) => { prov = e.target.value; try { localStorage.setItem(PNP_PROV_KEY, prov); } catch { /* ignore */ } draw(); } },
    el("option", { value: "" }, "All provinces"), provs.map(([c, n]) => el("option", { value: c, selected: c === prov }, n)));
  const failed = pv.read.filter((s) => s.ok === false);
  return el("div", { class: "col" },
    failed.length ? el("div", { class: "error" }, "Last check couldn't read: " + failed.map((s) => `${s.name} (${s.error})`).join("; ") + ". Its last good draws are shown.") : null,
    el("section", { class: "panel" },
      el("div", { class: "panel-head" }, el("h2", {}, "Provincial draws"), head),
      el("div", { class: "times-tools" }, sel, searchBox("Find a stream or date", (v) => { q = v; draw(); })),
      table),
    el("p", { class: "footnote" }, `Draws from the last ${Math.round(pv.keep_days / 30)} months, read from each province's own draw page and shown as the province publishes them ("<5" and "–" mean the province gave no exact figure). `,
      "Nova Scotia publishes a monthly total, not each draw. Minimum score is the province's own points system, not CRS; where one Ontario draw covers several streams, each stream's minimum is listed under it. ",
      pv.checked ? `Read ${fmtDate(pv.checked)}.` : "", pv.stale ? el("span", { class: "warn" }, " Not read in the last day: click Check now.") : null),
    el("p", { class: "footnote" }, "Check these on the official page (not read automatically): ",
      pv.by_hand.map((b, i) => [i ? " · " : "", el("a", { href: b.url, target: "_blank", rel: "noopener", title: b.why }, b.name)]).flat()));
}

function irccDataView(d, start) {
  const t = d.times, inv = d.inventory, rd = d.rounds, pv = d.pnp;
  let view = start || "times";
  if (!start) { try { view = localStorage.getItem(IRCC_VIEW_KEY) || "times"; } catch { /* ignore */ } }
  const body = el("div");
  const timesView = () => t ? el("div", { class: "col" }, countryCard(t), timesTable(t),
    el("p", { class: "footnote" }, "IRCC's estimates for a new application, based on the files already ahead in the queue: not a promise for any one file. Countries: how long most recent applications took, from a complete application to a decision. Source: ",
      el("a", { href: t.source, target: "_blank", rel: "noopener" }, t.source_name), t.read_date ? `, read ${fmtDate(t.read_date)}.` : ".",
      t.stale ? el("span", { class: "warn" }, ` Older than ${t.stale_after} days: ask Claude /changelog.`) : null, " Check IRCC's tool on the day you advise."))
    : panel("Processing times", null, empty("No processing time data in this version."));
  const draw = () => body.replaceChildren(view === "inventory" ? inventoryView(inv) : view === "rounds" ? roundsView(rd) : view === "pnp" ? provincialView(pv) : timesView());
  draw();
  const r = d.refresh || {}, failed = Object.entries(r.parts || {}).filter(([, p]) => p.ok === false);
  const hours = r.checked ? (Date.now() - new Date(r.checked).getTime()) / 3600000 : null;
  const off = !d.running && (hours === null || hours > 36);
  const checked = d.running ? "Checking IRCC's pages…" : r.checked ? `IRCC's pages checked ${fmtDate(r.checked)}.${off ? "" : " Updates by itself every day."}` : "IRCC's pages not checked yet on this computer.";
  return el("div", { class: "ircc-data" },
    irccSummary(inv, t, rd),
    el("div", { class: "data-bar" },
      segmented([["times", "Processing times"], ["inventory", "Application inventory"], ["rounds", "Express Entry rounds"], ["pnp", "Provincial draws"]], view, (k) => { view = k; try { localStorage.setItem(IRCC_VIEW_KEY, k); } catch { /* ignore */ } draw(); }, "IRCC data"),
      el("div", { class: "head-actions" }, el("span", { class: "small muted" }, checked), checkNowButton({ running: d.running }, route))),
    off ? el("section", { class: "tip", role: "note" },
      el("div", { class: "ub-text" }, el("div", { class: "tip-title" }, "Daily updates may be off on this computer"),
        el("div", { class: "small" }, "The news and IRCC figures refresh by themselves once a day when the daily updates are on. Turn them on once, or click Check now.")),
      el("button", { class: "btn", onclick: () => copyCommand("/daily-updates on") }, icon("copy"), "Copy /daily-updates on")) : null,
    failed.length ? el("div", { class: "error" }, "Last check failed for " + failed.map(([k, p]) => `${{ times: "processing times", inventory: "inventory", rounds: "Express Entry rounds" }[k] || k} (${p.error})`).join("; ") + ". The figures shown are the last good ones.") : null,
    d.error ? el("div", { class: "error" }, d.error) : null,
    body);
}

// Optional reminder: the firm profile adds the letterhead; it can be dismissed and is never required.
const HIDE_PROFILE = "agent.hideProfileTip";
function profileTip(set) {
  let hidden = false;
  try { hidden = localStorage.getItem(HIDE_PROFILE) === "1"; } catch { /* storage unavailable: show it */ }
  if (set || hidden) return null;
  const box = el("section", { class: "tip", role: "note" },
    el("div", { class: "ub-text" },
      el("div", { class: "tip-title" }, "Optional: add your firm details"),
      el("div", { class: "small" }, "Adds your letterhead and logo, and fills in your name and licence on agreements and letters. Without it, documents are on plain paper and Claude asks for your details each time.")),
    el("div", { class: "head-actions" },
      el("button", { class: "btn", onclick: () => copyCommand("/firm-profile") }, icon("copy"), "Copy /firm-profile"),
      el("button", { class: "link-btn", onclick: () => { try { localStorage.setItem(HIDE_PROFILE, "1"); } catch { /* ignore */ } box.remove(); } }, "Not now")));
  return box;
}

// The dashboard program was started before the last update: it still runs the old code until it is reopened.
function restartBanner(d) {
  if (!d.version || d.running_version === d.version) return null;
  return el("section", { class: "update-banner", role: "status" },
    el("div", { class: "ub-text" },
      el("div", { class: "ub-title" }, `Updated to version ${d.version}: reopen the dashboard`),
      el("div", { class: "small" }, "This dashboard was started before the update, so some parts may be missing or out of date. Close this window, then open the dashboard again from its shortcut.")));
}

function updateBanner(u) {
  if (!u || !u.state) return null;
  const steps = u.state === "available"
    ? [`In the Claude app, type /plugin, open Marketplaces, choose immigration-agent-marketplace, then Update marketplace (and Enable auto-update).`,
       "Quit and reopen Claude, then start a new conversation in this agent folder. The update installs by itself.",
       "Reopen this dashboard."]
    : ["Start a new conversation in Claude in this agent folder. The update installs by itself.", "Reopen this dashboard."];
  return el("section", { class: "update-banner", role: "status" },
    el("div", { class: "ub-text" },
      el("div", { class: "ub-title" }, u.state === "available" ? `Version ${u.latest} is available` : `Version ${u.latest} is downloaded and ready to install`),
      el("div", { class: "small" }, `This folder has version ${u.folder}. Your client files are never changed by an update.`),
      el("ol", {}, steps.map((s) => el("li", {}, s)))),
    u.state === "available" ? el("button", { class: "btn", onclick: () => copyCommand("/plugin") }, icon("copy"), "Copy /plugin") : null);
}

// ---- News from official sources (saved by the daily alerts or the Check now button; the page itself reads no web page) ----
async function postJSON(path, body) {
  const r = await fetch(path, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Agent-Key": KEY }, body: JSON.stringify(body || {}) });
  const out = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(out.error || "That didn't work");
  return out;
}

async function openLink(id) {
  try { await postJSON("/api/open-link", { id }); toast("Opening the official page in your browser…"); } catch (e) { toast(e.message); }
}

function filesBadge(files) {
  if (!files || !files.length) return null;
  const strong = files.some((f) => f.strong);
  return el("details", { class: "news-files" },
    el("summary", {}, el("span", { class: "pill " + (strong ? "Soon" : "neutral") }, `${files.length} of your files`)),
    el("div", { class: "small" }, files.map((f) => el("div", {}, caseTag(f.folder, f.id), ` ${f.client}: ${f.why}`))));
}

const hostOf = (url) => { try { return new URL(url).hostname.replace(/^www\d?\./, ""); } catch { return "source"; } };

function newsRow(n, tags, compact) {
  return el("div", { class: "news-item" + (n.coming ? " coming" : "") },
    el("div", { class: "news-date num" }, fmtDate(n.date)),
    el("div", { class: "news-body" },
      el("div", { class: "news-top" }, el("span", { class: "tag news-tag " + n.tag }, tags[n.tag] || n.tag),
        el("span", { class: "small muted" }, n.source_label)),
      el("div", { class: "news-title" }, n.title),
      !compact && n.detail.length ? el("ul", { class: "news-detail small muted" }, n.detail.map((x) => el("li", {}, x))) : null,
      filesBadge(n.files)),
    el("div", { class: "news-actions" },
      n.link ? el("button", { class: "btn news-src", title: `Read the full official page: ${n.link}`, "aria-label": `Read the full official page on ${hostOf(n.link)}`, onclick: () => openLink(n.id) }, icon("open"), hostOf(n.link)) : null,
      el("button", { class: "btn icon", title: `Copy /news post ${n.id}: Claude drafts a short client message about it`, "aria-label": "Share with clients", onclick: () => copyCommand(`/news post ${n.id}`) }, icon("share"))));
}

function newsChecked(d) {
  if (d.running) return "Checking the official sources…";
  return d.checked ? `Checked ${fmtDate(d.checked)}${d.stale ? " (over a day ago)" : ""}` : "Not checked yet";
}

function checkNowButton(d, after) {
  return el("button", { class: "btn", disabled: d.running, onclick: async (e) => {
    const b = e.currentTarget;
    b.disabled = true;
    b.textContent = "Checking…";
    try {
      await postJSON("/api/news/check");
      toast("Reading IRCC, ESDC and the provincial pages. This takes about a minute.");
      const wait = async () => { const n = await api("/api/ircc").catch(() => ({ running: false })); if (n.running) setTimeout(wait, 4000); else after(); };
      setTimeout(wait, 4000);
    } catch (err) { toast(err.message); b.disabled = false; b.textContent = "Check now"; }
  } }, d.running ? "Checking…" : "Check now");
}

function newsPanel(d, rerender, tag) {
  let mine = false, q = "";
  const list = el("div", { class: "news-list" });
  const show = () => {
    list.replaceChildren();
    const rows = d.items.filter((n) => (!tag || n.tag === tag) && (!mine || n.files.length) && (!q || JSON.stringify([n.title, n.detail, n.source_label]).toLowerCase().includes(q)));
    if (!rows.length) list.append(empty(d.items.length ? "No news matches." : "No news saved yet. Click Check now, or wait for the daily alerts."));
    for (const n of rows.slice(0, 150)) list.append(newsRow(n, d.tags));
  };
  const failed = d.sources.filter((s) => s.ok === false), hand = d.sources.filter((s) => s.by_hand);
  show();
  return el("section", { class: "panel" },
    el("div", { class: "panel-head" }, el("h2", {}, tag ? `News: ${d.tags[tag]}` : "All news and updates"),
      el("div", { class: "head-actions" }, el("span", { class: "count" }, newsChecked(d)), checkNowButton(d, rerender))),
    el("p", { class: "hint" }, "From official sources only (IRCC, ESDC, Job Bank, each province's own page), last 60 days. Click the site name (canada.ca, alberta.ca…) to read the full official page. \"Your files\" is a keyword or score match: a prompt to review, not a finding. Share copies a command: Claude checks the source and drafts a short message for clients who agreed to hear from you."),
    el("div", { class: "news-filters" },
      el("label", { class: "small news-mine" }, el("input", { type: "checkbox", onchange: (e) => { mine = e.target.checked; show(); } }), " Only news that may concern my files"),
      searchBox("Search the news", (v) => { q = v; show(); })),
    d.error ? el("div", { class: "error" }, d.error) : null,
    list,
    el("details", { class: "news-sources" }, el("summary", { class: "small" }, `Sources (${d.sources.length - hand.length} read automatically${failed.length ? `, ${failed.length} failed at the last check` : ""}, ${hand.length} to check by hand)`),
      el("div", {}, d.sources.map((s) => el("div", { class: "row small" },
        el("span", {}, el("a", { href: s.url, target: "_blank", rel: "noopener noreferrer" }, s.label), s.error ? el("div", { class: "muted" }, s.error) : null),
        el("span", { class: "pill " + (s.by_hand ? "neutral" : s.ok ? "ok" : s.ok === false ? "Soon" : "neutral") }, s.by_hand ? "Check by hand" : s.ok ? `${s.count} items` : s.ok === false ? "Failed" : "Not read yet"))))));
}

const pages = {
  async home() {
    const d = await api("/api/home");
    setFrame(d);
    const c = d.counts;
    const urgent = d.alerts.filter((a) => a.rank === 1), soon = d.alerts.filter((a) => a.rank === 2), house = d.alerts.filter((a) => a.rank === 3);
    const stat = (cls, n, label, hint, href) => el(href ? "a" : "div", { class: `stat ${cls}${Number(n) ? "" : " zero"}`, href },
      el("div", { class: "l" }, label), el("div", { class: "n" }, n), el("div", { class: "h" }, hint));
    const attention = [...urgent, ...soon];
    return [
      pageHead(fmtLong(d.today), "Today", d.firm || null),
      restartBanner(d),
      updateBanner(d.update),
      profileTip(d.profile_set),
      el("div", { class: "stats" },
        stat("urgent", c.urgent, "Urgent", "Act on these first"),
        stat("soon", c.soon, "Coming up", "Plan for these"),
        stat("", c.week, "Deadlines", "Due in the next 7 days"),
        stat("accent", c.cases, "Active cases", "Open the case list", "#cases")),
      el("div", { class: "grid2" },
        el("div", { class: "col" },
          panel("Needs attention", el("span", { class: "count" }, attention.length ? `${attention.length} item${attention.length === 1 ? "" : "s"}` : ""), alertList(attention, true)),
          house.length ? el("details", { class: "panel" }, el("summary", {}, el("h2", {}, `File housekeeping (${house.length})`)), alertList(house, true)) : null),
        el("div", { class: "col" },
          panel("Ask Claude", null, el("p", { class: "hint" }, "Copy a command, then paste it in the Claude app (Code tab) in this agent folder."), cmdList(d.commands)),
          kbPanel(d.kb, d.policy_check))),
    ];
  },

  async cases() {
    const d = await api("/api/cases");
    const body = el("tbody");
    const render = (q) => {
      body.replaceChildren();
      const rows = d.active.filter((r) => !q || JSON.stringify(r).toLowerCase().includes(q));
      if (!rows.length) body.append(el("tr", {}, el("td", { colspan: 7 },empty(d.active.length ? "No case matches your search." : "No active cases yet. Ask Claude: /case new"))));
      for (const r of rows) {
        body.append(el("tr", {},
          el("td", {}, el("div", { class: "cell-stack" }, caseTag(r.folder, r.id), r.program ? el("span", { class: "small muted" }, r.program) : null)),
          el("td", {}, r.client ? el("div", { class: "client" }, el("span", { class: "avatar" }, initials(r.client)), el("span", {}, r.client)) : el("span", { class: "muted" }, r.error || "")),
          el("td", {}, r.province || el("span", { class: "muted" }, "—")),
          el("td", {}, el("a", { class: "plain-link", href: "#case/" + encodeURIComponent(r.folder) }, miniProgress(r.progress))),
          el("td", {}, r.next_action || el("span", { class: "muted" }, "Not set")),
          el("td", {}, r.next_deadline ? el("div", { class: "cell-stack" }, el("span", { class: "num" }, fmtDate(r.next_deadline.due)), dueChip(r.next_deadline.left)) : el("span", { class: "muted" }, "None")),
          el("td", {}, el("div", { class: "cell-stack" }, r.urgent ? el("span", { class: "pill Urgent" }, `${r.urgent} urgent`) : null, r.soon ? el("span", { class: "pill Soon" }, `${r.soon} coming up`) : null,
            !r.urgent && !r.soon ? el("span", { class: "pill ok" }, "Clear") : null))));
      }
    };
    render("");
    return [
      pageHead("Practice", "Cases", `${d.active.length} active · ${d.closed.length} closed`, [
        d.active.length ? el("a", { class: "btn", href: "/api/calendar.ics", download: "immigration-deadlines.ics",
          title: "Open deadlines and expiry dates of every active case, with reminders 7 days and 1 day before. Titles show the case number only." },
          icon("calendar"), "Add deadlines to calendar") : null,
        searchBox("Search by name, case number or program", render)]),
      el("section", { class: "panel" }, el("div", { class: "tablewrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ["Case", "Client", "Province", "Documents", "Next action", "Next deadline", "Alerts"].map((h) => el("th", {}, h)))), body))),
      d.closed.length ? el("details", { class: "panel" }, el("summary", {}, el("h2", {}, `Closed files (${d.closed.length})`)),
        el("div", { class: "tablewrap" }, el("table", {},
          el("thead", {}, el("tr", {}, ["Case", "Client", "Program", "Closed", "Keep until"].map((h) => el("th", {}, h)))),
          el("tbody", {}, d.closed.map((r) => el("tr", {}, el("td", {}, caseTag(r.folder, r.case_id || r.folder)), el("td", {}, r.client), el("td", {}, r.program),
            el("td", { class: "num" }, fmtDate(r.closed)), el("td", { class: "num" }, r.destroy_after ? fmtDate(r.destroy_after) : "—"))))))) : null,
    ];
  },

  async case(folder) {
    const d = await api("/api/case?folder=" + encodeURIComponent(folder));
    const i = d.info;
    const groups = {};
    for (const f of d.files) (groups[f.group || "Case folder"] ||= []).push(f);
    const m = d.money;
    const dash = (v) => v || el("span", { class: "muted" }, "—");
    const owing = Number(m.owing) > 0;
    return [
      el("a", { class: "crumb", href: "#cases" }, icon("back"), "All cases"),
      el("div", { class: "head" },
        el("div", { class: "head-text" },
          el("div", { class: "eyebrow" }, d.closed ? "Closed case file" : "Case file"),
          el("h1", {}, i.client || i.case_id || d.folder),
          el("div", { class: "alert-top" }, el("span", { class: "case-tag" }, i.case_id || d.folder), i.program ? el("span", { class: "tag" }, i.program) : null,
            el("span", { class: "sub" }, [i.province, i.opened && "Opened " + fmtDate(i.opened)].filter(Boolean).join(" · ")),
            d.closed ? el("span", { class: "pill done" }, "Closed") : null)),
        el("div", { class: "head-actions" }, el("button", { class: "btn primary", onclick: () => openPath(d.path) }, icon("folder"), "Open case folder"))),
      checklistPanel(d),
      el("div", { class: "grid2" },
        el("div", { class: "col" },
          panel("Needs attention", null, alertList(d.alerts, false)),
          panel("Deadlines", el("span", { class: "count" }, d.deadlines.length ? `${d.deadlines.length} tracked` : ""),
            d.deadlines.length ? el("div", { class: "tablewrap" }, el("table", {},
              el("thead", {}, el("tr", {}, ["Due", "What", "Basis", "Status"].map((h) => el("th", {}, h)))),
              el("tbody", {}, d.deadlines.map((r) => el("tr", {},
                el("td", {}, el("div", { class: "cell-stack" }, el("span", { class: "num" }, fmtDate(r.due)))),
                el("td", {}, el("div", { class: "alert-what" }, r.type), el("div", { class: "small muted" }, r.description)),
                el("td", { class: "small muted" }, r.basis),
                el("td", {}, r.done ? el("span", { class: "pill done" }, "Done") : dueChip(r.left))))))) : empty("No deadlines tracked yet. Ask Claude to add one.")),
          d.validity && (d.validity.error || d.validity.items.length) ? panel("Document validity",
            el("span", { class: "count" }, d.validity.plan && d.validity.plan.plan_filing ? "Filing planned " + fmtDate(d.validity.plan.plan_filing) : ""),
            d.validity.error ? el("div", { class: "error" }, d.validity.error) : el("div", { class: "tablewrap" }, el("table", {},
              el("thead", {}, el("tr", {}, ["Document", "Dated", "Good until", "Status"].map((h) => el("th", {}, h)))),
              el("tbody", {}, d.validity.items.map((r) => el("tr", {},
                el("td", {}, el("div", { class: "alert-what" }, r.label), el("div", { class: "small muted" }, r.person)),
                el("td", { class: "num" }, fmtDate(r.from)), el("td", { class: "num" }, fmtDate(r.until)),
                el("td", {}, r.problem ? el("span", { class: "pill Urgent" }, r.problem) : dueChip(r.left)))))))) : null,
          panel("Files", el("span", { class: "count" }, d.files.length ? `${d.files.length} file${d.files.length === 1 ? "" : "s"}` : ""),
            Object.keys(groups).length ? el("div", {}, Object.entries(groups).map(([g, fs]) => el("div", { class: "files-group" }, el("h3", {}, g),
              fs.map((f) => fileRow(f, null))))) : empty("No files yet."))),
        el("div", { class: "col" },
          panel("Ask Claude about this case", null, cmdList(d.commands)),
          panel("File checks", null, el("div", { class: "panel-body" }, el("dl", { class: "kv" },
            el("dt", {}, "Next action"), el("dd", {}, dash(i.next_action)),
            el("dt", {}, "Status expiry"), el("dd", {}, dash(fmtDate(i.status_expiry))),
            el("dt", {}, "Passport expiry"), el("dd", {}, dash(fmtDate(i.passport_expiry))),
            d.ptime ? [el("dt", {}, "Processing time"), el("dd", { class: d.ptime.past ? "warn" : "" }, d.ptime.submitted ? `${d.ptime.elapsed} days since filing · IRCC: ${d.ptime.words || "no time posted"}` : "No submitted date")] : null,
            d.held ? [el("dt", {}, "IRCC held for space"), el("dd", {}, `${d.held.waiting_pct}% of ${d.held.label.toLowerCase()} files (data to ${fmtDate(d.held.data_as_of)})`)] : null,
            el("dt", {}, "Conflict check"), el("dd", {}, dash(i.conflict_check)),
            el("dt", {}, "Agreement signed"), el("dd", {}, dash(i.agreement_signed)),
            el("dt", {}, "IMM 5476 on file"), el("dd", {}, dash(i.imm5476_on_file))))),
          panel("Money", null, el("div", { class: "panel-body" },
            m.error ? el("div", { class: "error" }, m.error) : !m.has_ledger ? el("div", {}, el("div", { class: "muted" }, "No billing recorded yet."),
                m.hours && Number(m.hours) ? el("dl", { class: "kv" }, el("dt", {}, "Hours recorded"), el("dd", {}, m.hours)) : null) :
              el("dl", { class: "kv" }, el("dt", {}, "Invoiced"), el("dd", {}, money(m.invoiced)), el("dt", {}, "Received"), el("dd", {}, money(m.received)),
                el("dt", {}, "Unpaid"), el("dd", { class: owing ? "warn" : "strong" }, money(m.owing)), el("dt", {}, "Held in client account"), el("dd", {}, money(m.held)),
                m.hours && Number(m.hours) ? [el("dt", {}, "Hours recorded"), el("dd", {}, m.hours), el("dt", {}, "Per hour"), el("dd", {}, m.rate ? money(m.rate) : "—")] : null))),
          d.tasks.length || d.reviews.length ? panel("Tasks and reviews", null, el("div", {},
            d.reviews.map((r) => el("div", { class: "row" }, el("span", {}, el("span", { class: "alert-what" }, "Review: "), r.file, el("div", { class: "small muted" }, `prepared by ${r.prepared_by}`)),
              el("span", { class: "pill Soon" }, "Waiting for sign-off"))),
            d.tasks.map((t) => el("div", { class: "row" }, el("span", {}, el("span", { class: "alert-what" }, `#${t.id} `), t.task, el("div", { class: "small muted" }, t.assigned)),
              t.due ? el("span", { class: "file-meta" }, fmtDate(t.due)) : null)))) : null,
          d.updates.length ? panel("Submitted and received", null,
            el("div", {}, d.updates.map((u) => el("div", { class: "row" }, el("span", {}, el("span", { class: "alert-what" }, u.kind + ": "), u.what),
              el("span", { class: "cell-stack" }, el("span", { class: "file-meta" }, fmtDate(u.date)), el("span", { class: "pill " + (u.notified ? "ok" : "Soon") }, u.notified ? "Client told" : "Client not told")))))) : null,
          panel("Recent activity", null,
            d.log.length ? el("div", {}, d.log.map((l) => el("div", { class: "row" }, el("span", {}, l.text), el("span", { class: "file-meta" }, fmtDate(l.date))))) : empty("No activity logged.")))),
    ];
  },

  async ircc(arg) {
    const [d, news] = await Promise.all([api("/api/ircc"), api("/api/news").catch((e) => ({ failed: e.message }))]);
    const tags = news.failed ? {} : news.tags;
    const count = (k) => news.failed ? 0 : k === "news" ? news.items.length : news.items.filter((n) => n.tag === k).length;
    const keys = ["data", "news", ...Object.keys(tags)];
    let current = keys.includes(arg) ? arg : "data";  // #ircc/times, #ircc/inventory, #ircc/rounds and #ircc/pnp open the data tab on that view
    const data = irccDataView(d, ["times", "inventory", "rounds", "pnp"].includes(arg) ? arg : null);
    const body = el("div", { class: "tab-body" });
    const bar = el("div", { class: "tabs page-tabs", role: "tablist", "aria-label": "IRCC data and news" });
    const show = () => {
      for (const b of bar.children) { const on = b.dataset.key === current; b.classList.toggle("on", on); b.setAttribute("aria-selected", on ? "true" : "false"); }
      body.replaceChildren(current === "data" ? data : news.failed ? el("div", { class: "error" }, news.failed) : newsPanel(news, route, current === "news" ? "" : current));
      history.replaceState(null, "", "#ircc/" + current);
    };
    const tab = (key, label, n) => el("button", { class: "tab", role: "tab", "data-key": key, onclick: () => { current = key; show(); } },
      label, n === null ? null : el("span", { class: "tab-n" }, n));
    bar.append(tab("data", "IRCC data", null), tab("news", "All news", count("news")), ...Object.entries(tags).map(([k, l]) => tab(k, l, count(k))));
    show();
    return [
      pageHead("IRCC's own published figures and official news", "IRCC data and news", "Inventory, processing times, Express Entry rounds and provincial draws, and news from IRCC, ESDC, Job Bank and the provinces' own pages."),
      bar,
      body,
    ];
  },

  async growth() {
    const d = await api("/api/growth");
    const opps = el("tbody");
    const render = (q) => {
      opps.replaceChildren();
      const rows = d.opportunities.filter((r) => !q || JSON.stringify(r).toLowerCase().includes(q));
      if (!rows.length) opps.append(el("tr", {}, el("td", { colspan: 5 }, empty(d.opportunities.length ? "Nothing matches your search." : "No opportunities found in the files. Only dates recorded in the files are used (PR date, PR card expiry, status expiry, date of birth, trips, test dates)."))));
      for (const r of rows) {
        opps.append(el("tr", {},
          el("td", {}, el("div", { class: "cell-stack" }, r.when ? el("span", { class: "num" }, fmtDate(r.when)) : el("span", { class: "muted" }, "Review"), r.when ? (r.left <= 0 ? el("span", { class: "pill ok" }, "Now") : dueChip(r.left)) : null)),
          el("td", {}, el("div", { class: "cell-stack" }, caseTag(r.case, r.id), el("span", { class: "small" }, r.client), el("span", { class: "small muted" }, `${r.program} · ${r.state} file`))),
          el("td", {}, el("div", { class: "alert-what" }, r.kind), el("div", { class: "small muted" }, r.why)),
          el("td", { class: "small" }, r.service),
          el("td", {}, el("span", { class: "pill " + (r.consent === "yes" ? "ok" : "Soon") }, r.consent === "yes" ? "Agreed to contact" : "Consent not recorded"))));
      }
    };
    render("");
    const gapText = (g) => g >= 0 ? `+${g} over` : `${-g} below`;
    return [
      pageHead("Practice", "Opportunities", "Clients who may need you again, and the latest Express Entry rounds",
        [searchBox("Search by name, case or opportunity", render)]),
      el("section", { class: "panel" },
        el("div", { class: "panel-head" }, el("h2", {}, "Clients to review"), el("span", { class: "count" }, `${d.opportunities.length} item${d.opportunities.length === 1 ? "" : "s"}`)),
        el("p", { class: "hint" }, "Each item is a prompt to review the file, not a finding that the client qualifies. Contact only clients who agreed to hear about future services: privacy and anti-spam rules apply."),
        el("div", { class: "tablewrap" }, el("table", {},
          el("thead", {}, el("tr", {}, ["When", "Client", "Opportunity", "Service", "Contact"].map((h) => el("th", {}, h)))), opps)),
        d.errors.length ? el("div", { class: "error" }, "Could not read: " + d.errors.join(", ")) : null),
      el("div", { class: "grid2" },
        el("div", { class: "col" },
          panel("Express Entry rounds", el("span", { class: "count" }, d.checked ? "Checked " + fmtDate(d.checked) : "Not checked yet"),
            d.rounds.length ? el("div", {}, d.rounds.map((r) => el("div", { class: "row" },
              el("span", {}, el("span", { class: "alert-what" }, `#${r.number} ${r.name}`), el("div", { class: "small muted" }, `${fmtDate(r.date)} · ${r.size ?? "?"} invitations · lowest CRS ${r.crs}`),
                r.matches.length ? el("div", { class: "small" }, r.matches.map((m) => el("div", {}, caseTag(m.folder, m.id), ` ${m.client}: CRS ${m.crs} (${gapText(m.gap)})`))) : el("div", { class: "small muted" }, "No recorded client score at or within 10 points")),
              r.matches.some((m) => m.gap >= 0) ? el("span", { class: "pill Soon" }, "Check accounts") : null)))
              : empty("No rounds saved yet. The daily alerts read IRCC's feed once a day, or ask Claude: /draws check")),
          panel("Prospects", el("span", { class: "count" }, d.prospects.length ? `${d.prospects.length} open` : ""),
            d.prospects.length ? el("div", {}, d.prospects.map((p) => el("div", { class: "row" },
              el("span", {}, el("span", { class: "alert-what" }, `${p.id} ${p.name}`), el("div", { class: "small muted" }, [p.stage, p.program, p.source, p.quote && money(p.quote)].filter(Boolean).join(" · "))),
              p.followup ? el("span", { class: "pill Soon" }, `Follow up (${p.followup}d)`) : el("span", { class: "pill ok" }, p.stage)))) : empty("No open prospects. Ask Claude: /prospects add")),
          d.pnp.length ? panel("Provincial draws recorded", null, el("div", {}, d.pnp.map((p) => el("div", { class: "row" },
            el("span", {}, el("span", { class: "alert-what" }, `${p.province} ${p.stream}`), el("div", { class: "small muted" }, `minimum score ${p.min_score}${p.note ? " · " + p.note : ""}`)),
            el("span", { class: "file-meta" }, fmtDate(p.date)))))) : null),
        el("div", { class: "col" },
          d.licence ? panel("Your licence", el("span", { class: "count" }, "CPD term " + d.licence.term), el("div", { class: "panel-body" }, el("dl", { class: "kv" },
            el("dt", {}, "CPD hours"), el("dd", { class: Number(d.licence.done) < Number(d.licence.owed) ? "warn" : "strong" }, `${d.licence.done} of ${d.licence.owed} by ${fmtDate(d.licence.end)}`),
            el("dt", {}, "Professionalism or Code"), el("dd", {}, `${d.licence.pro_done} of ${d.licence.pro_owed}`),
            d.licence.due.flatMap((x) => [el("dt", {}, x.what), el("dd", { class: x.paid ? "" : "warn" }, (x.paid ? "Paid · " : "Due ") + fmtDate(x.day))])))) : null,
          panel("Ask Claude", null, el("p", { class: "hint" }, "A match means the score you recorded is at or above the cut-off, not that an invitation was issued. Check the client's IRCC account."), cmdList(d.commands)))),
    ];
  },

  async documents() {
    const d = await api("/api/documents");
    const list = el("div");
    const render = (q) => {
      list.replaceChildren();
      const rows = d.files.filter((f) => !q || (f.name + " " + f.group).toLowerCase().includes(q));
      if (!rows.length) list.append(empty(d.files.length ? "No document matches your search." : "No finished documents yet. Claude saves them in the Output folder."));
      for (const f of rows) list.append(fileRow(f, f.group));
    };
    render("");
    return [
      pageHead("Output folder", "Documents", "Finished letters, forms, reports and checklists, newest first",
        [searchBox("Search documents", render), d.folder ? el("button", { class: "btn", onclick: () => openPath(d.folder) }, icon("open"), "Open Output folder") : null]),
      panel("All documents", el("span", { class: "count" }, `${d.files.length} file${d.files.length === 1 ? "" : "s"}`), list),
    ];
  },

  async agent() {
    const d = await api("/api/agent");
    const releases = [];
    let cur = null;
    for (const line of d.whats_new.split(/\r?\n/)) {
      if (/^##\s/.test(line)) { cur = { v: line.replace(/^##\s+v?/, "").trim(), items: [] }; releases.push(cur); }
      else if (cur && /^\s*-\s/.test(line)) cur.items.push(line.replace(/^\s*-\s+/, "").replace(/`/g, ""));
    }
    return [
      pageHead("Canada Immigration Agent", "Agent & updates", `Version ${d.version}` + (d.install.updated ? ` · last updated ${fmtDate(d.install.updated)}` : "")),
      updateBanner(d.update),
      el("div", { class: "grid2" },
        panel("What's new", null, el("div", { class: "timeline" }, releases.map((r) =>
          el("div", { class: "release" },
            el("div", { class: "v" }, el("div", {}, r.v), r.v === d.version ? el("span", { class: "pill ok" }, "Installed") : null),
            el("ul", {}, r.items.map((t) => el("li", {}, t))))))),
        el("div", { class: "col" },
          panel("Getting updates", null,
            el("p", { class: "hint" }, "Updates arrive by themselves when auto-update is on in the Claude app (/plugin › Marketplaces › Enable auto-update). They install when you next start Claude in this folder. Your client files are never changed."),
            cmdList([{ label: "Check for updates", command: "/immigration-agent:update", help: "Your version and what's new" }])),
          kbPanel(d.kb),
          d.kb.attention.length ? panel("Files to review", null,
            el("div", {}, d.kb.attention.map((r) => el("div", { class: "row" }, el("span", { class: "small mono" }, r.file), el("span", { class: "pill Soon" }, r.state))))) : null)),
    ];
  },
};

// ---- Document checklist: progress summary on top, the full checklist below ----
const STATES = {
  received: { label: "Received", tone: "ok" },
  prepared: { label: "Prepared, not yet signed", tone: "Soon" },
  missing: { label: "Still missing", tone: "Urgent" },
  confirm: { label: "To confirm", tone: "Soon" },
  "not-needed": { label: "Not needed", tone: "done" },
};

async function changeChecklist(body) {
  let r;
  try {
    r = await fetch("/api/checklist", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Agent-Key": KEY }, body: JSON.stringify(body) });
  } catch { throw new Error(CLOSED); }
  const out = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(out.error || "Could not save the change");
  return out.checklist;
}

function ring(percent) {
  const s = document.createElementNS(SVG, "svg");
  s.setAttribute("viewBox", "0 0 120 120");
  s.setAttribute("class", "ring");
  s.setAttribute("role", "img");
  s.setAttribute("aria-label", `${percent}% of required documents received`);
  const circ = 2 * Math.PI * 52;
  for (const [cls, dash] of [["ring-track", circ], ["ring-fill", (circ * percent) / 100]]) {
    const c = document.createElementNS(SVG, "circle");
    c.setAttribute("cx", "60"); c.setAttribute("cy", "60"); c.setAttribute("r", "52");
    c.setAttribute("class", cls);
    c.setAttribute("stroke-dasharray", `${dash} ${circ}`);
    s.append(c);
  }
  return el("div", { class: "ring-wrap" + (percent === 100 ? " full" : "") }, s,
    el("div", { class: "ring-label" }, el("div", { class: "ring-n" }, `${percent}%`), el("div", { class: "ring-h" }, "received")));
}

function progressSummary(cl) {
  const p = cl.progress;
  const tile = (cls, n, label, hint) => el("div", { class: "pstat " + cls + (n ? "" : " zero") }, el("div", { class: "n" }, n), el("div", { class: "l" }, label), el("div", { class: "h" }, hint));
  const bar = el("div", { class: "stack", role: "img", "aria-label": `${p.received} received, ${p.missing} still missing, ${p.confirm} to confirm, ${p.not_needed} not needed` });
  for (const [k, n] of [["received", p.received], ["missing", p.missing], ["confirm", p.confirm], ["not-needed", p.not_needed]]) {
    if (!n) continue;
    const seg = el("span", { class: "seg " + k, title: `${STATES[k].label}: ${n}` });
    seg.style.flexGrow = n;
    bar.append(seg);
  }
  return el("div", { class: "progress-top" },
    ring(p.percent),
    el("div", { class: "progress-side" },
      el("div", { class: "pstats" },
        tile("", p.needed, "Required", "Documents this client must provide"),
        tile("ok", p.received, "Received", "On file or marked received"),
        tile("Urgent", p.missing, "Still missing", "Ask the client for these"),
        tile("Soon", p.confirm, "To confirm", "Decide if they apply to this client")),
      bar,
      el("div", { class: "legend" }, ["received", "missing", "confirm", "not-needed"].map((k) => el("span", { class: "lg " + k }, STATES[k].label))),
      p.confirm ? el("div", { class: "small muted" }, `The percentage counts required documents only. ${p.confirm} item${p.confirm === 1 ? "" : "s"} still to confirm: mark each as missing (it applies) or not needed.`) : null));
}

function checklistItem(it, readOnly, act) {
  const st = STATES[it.status];
  const btn = (mark, label) => el("button", {
    class: "seg-btn" + (it.status === mark ? " on " + mark : ""), "aria-pressed": it.status === mark ? "true" : "false",
    onclick: () => act({ action: "mark", no: it.no, mark: it.mark === mark ? "" : mark }), title: it.mark === mark ? "Click again to go back to the automatic match" : `Mark as ${label.toLowerCase()}`,
  }, label);
  const autoNote = it.mark ? `Marked by you ${fmtDate(it.marked)}` + (it.auto !== it.status ? ` (automatic check: ${STATES[it.auto].label.toLowerCase()})` : "") : it.status === "received" ? "Found in the case documents" : "";
  return el("div", { class: "ck " + it.status },
    el("span", { class: "ck-icon", "aria-hidden": "true" }, it.status === "received" ? icon("check") : null),
    el("div", { class: "ck-main" },
      el("div", { class: "ck-title" }, el("span", { class: "ck-no" }, it.no), it.item),
      el("div", { class: "ck-meta" },
        el("span", { class: "pill " + st.tone }, st.label),
        it.required !== "always" && it.condition ? el("span", { class: "small muted" }, "Only if: " + it.condition) : null,
        it.note ? el("span", { class: "small muted" }, it.note) : null),
      it.files.length ? el("div", { class: "ck-files" }, it.files.map((f) => el("button", { class: "ck-file", onclick: () => openPath(f.path), title: "Open" }, icon("open"), f.name))) : null,
      autoNote ? el("div", { class: "ck-auto" }, autoNote) : null),
    readOnly ? null : el("div", { class: "ck-actions" },
      el("div", { class: "seg-group", role: "group", "aria-label": "Mark this item" }, btn("received", "Received"), btn("missing", "Missing"), btn("not-needed", "Not needed")),
      it.extra ? el("button", { class: "link-btn", onclick: () => act({ action: "remove", no: it.no }) }, "Remove") : null));
}

function checklistPanel(d) {
  const cl = d.checklist;
  if (!cl) return panel("Document progress", null, empty(`No IRCC checklist is stored for the program "${d.info.program || "not set"}". Stored: visitor, study permit, work permit, Express Entry, spousal, PGP, super visa, citizenship, PR card.`));
  if (cl.error) return panel("Document progress", null, el("div", { class: "panel-body" }, el("div", { class: "error" }, cl.error)));
  const wrap = el("section", { class: "panel checklist" });
  let data = cl, filter = "all";
  const readOnly = d.closed;
  const act = async (body) => {
    try { data = await changeChecklist({ ...body, folder: d.folder }); render(); }
    catch (e) { toast(e.message); }
  };
  const render = () => {
    const counts = { all: data.items.length };
    for (const it of data.items) counts[it.status] = (counts[it.status] || 0) + 1;
    const tabs = el("div", { class: "tabs", role: "tablist" }, [["all", "All"], ["missing", "Still missing"], ["received", "Received"], ["confirm", "To confirm"], ["not-needed", "Not needed"]].map(([k, label]) =>
      el("button", { class: "tab" + (filter === k ? " on" : ""), role: "tab", "aria-selected": filter === k ? "true" : "false", onclick: () => { filter = k; render(); } }, label, el("span", { class: "tab-n" }, counts[k] || 0))));
    const shown = data.items.filter((it) => filter === "all" || it.status === filter);
    const groups = {};
    for (const it of shown) (groups[it.group] ||= []).push(it);
    const input = el("input", { type: "text", maxlength: "200", placeholder: "Add a document the visa office or this client needs, e.g. Employer leave letter", "aria-label": "Document to add" });
    const add = async () => { if (input.value.trim()) { await act({ action: "add", item: input.value }); } };
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") add(); });
    wrap.replaceChildren(
      el("div", { class: "panel-head" }, el("h2", {}, "Document progress"),
        el("span", { class: "count" }, `${data.progress.received} of ${data.progress.needed} required received`)),
      el("div", { class: "panel-body" }, progressSummary(data)),
      el("div", { class: "ck-head" },
        el("div", { class: "ck-source small muted" }, `${data.title}: IRCC ${data.source} (${data.version}), read ${fmtDate(data.read)}. `,
          el("a", { href: data.url, target: "_blank", rel: "noopener noreferrer" }, "Official list"),
          data.old ? el("span", { class: "pill Soon" }, "Check IRCC's current version") : null),
        tabs),
      shown.length ? el("div", {}, Object.entries(groups).map(([g, items]) => el("div", { class: "ck-group" }, el("h3", {}, g), items.map((it) => checklistItem(it, readOnly, act)))))
        : empty(filter === "missing" ? "Nothing is missing." : "No items here.", filter === "missing"),
      readOnly ? null : el("div", { class: "ck-add" }, input, el("button", { class: "btn", onclick: add }, "Add document")),
      el("p", { class: "hint ck-hint" }, "Documents are matched from the case's 03-documents folder and the latest /extract. Your marks win over the automatic match; click a mark again to undo it. Every change is kept in the case folder."));
  };
  render();
  return wrap;
}

function miniProgress(p) {
  if (!p) return el("span", { class: "muted small" }, "No checklist");
  const bar = el("span");
  bar.style.width = `${p.percent}%`;
  return el("div", { class: "mini" },
    el("div", { class: "mini-top" }, el("span", { class: "num strong" }, `${p.percent}%`), el("span", { class: "small muted num" }, `${p.received} of ${p.needed}`)),
    el("div", { class: "meter" + (p.percent === 100 ? "" : p.missing ? " warn" : "") }, bar),
    p.confirm ? el("span", { class: "small muted" }, `${p.confirm} to confirm`) : null);
}

function fileRow(f, sub) {
  const ext = extOf(f.name);
  return el("div", { class: "file" },
    el("span", { class: "ext " + ext }, (ext || "file").slice(0, 4).toUpperCase()),
    el("div", { class: "file-main" }, el("button", { onclick: () => openPath(f.path), title: "Open" }, f.name), sub ? el("span", { class: "small muted" }, sub) : null),
    el("span", { class: "file-meta" }, `${fmtDate(f.modified)} · ${fmtSize(f.size)}`));
}

function setFrame(d) {
  document.getElementById("firm").textContent = d.firm || "Firm details: optional";
  document.getElementById("today").textContent = fmtLong(d.today);
  const badge = document.getElementById("nav-urgent");
  badge.textContent = d.counts && d.counts.urgent ? d.counts.urgent : "";
  badge.hidden = !(d.counts && d.counts.urgent);
}

async function route() {
  const [page, arg] = (location.hash.slice(1) || "home").split("/");
  const name = pages[page] ? page : "home";
  for (const a of document.querySelectorAll("#nav a")) {
    const on = a.dataset.page === (name === "case" ? "cases" : name);
    a.classList.toggle("on", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  try {
    const content = await pages[name](arg ? decodeURIComponent(arg) : undefined);
    main.replaceChildren(...content.filter(Boolean));
  } catch (e) {
    main.replaceChildren(el("div", { class: "error" }, e.message));
  }
  main.focus({ preventScroll: true });
}

// Tell the dashboard program this window is still open; it stops by itself once no window checks in.
function alive() {
  fetch("/api/alive", { method: "POST", credentials: "same-origin", headers: { "X-Agent-Key": KEY } }).catch(() => {});
}
alive();
setInterval(alive, 30000);

window.addEventListener("hashchange", route);
document.addEventListener("visibilitychange", () => { if (!document.hidden) route(); });
api("/api/home").then(setFrame).catch(() => {});
route();
