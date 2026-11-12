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
      if (!rows.length) body.append(el("tr", {}, el("td", { colspan: 6 }, empty(d.active.length ? "No case matches your search." : "No active cases yet. Ask Claude: /case new"))));
      for (const r of rows) {
        body.append(el("tr", {},
          el("td", {}, el("div", { class: "cell-stack" }, caseTag(r.folder, r.id), r.program ? el("span", { class: "small muted" }, r.program) : null)),
          el("td", {}, r.client ? el("div", { class: "client" }, el("span", { class: "avatar" }, initials(r.client)), el("span", {}, r.client)) : el("span", { class: "muted" }, r.error || "")),
          el("td", {}, r.province || el("span", { class: "muted" }, "—")),
          el("td", {}, r.next_action || el("span", { class: "muted" }, "Not set")),
          el("td", {}, r.next_deadline ? el("div", { class: "cell-stack" }, el("span", { class: "num" }, fmtDate(r.next_deadline.due)), dueChip(r.next_deadline.left)) : el("span", { class: "muted" }, "None")),
          el("td", {}, el("div", { class: "cell-stack" }, r.urgent ? el("span", { class: "pill Urgent" }, `${r.urgent} urgent`) : null, r.soon ? el("span", { class: "pill Soon" }, `${r.soon} coming up`) : null,
            !r.urgent && !r.soon ? el("span", { class: "pill ok" }, "Clear") : null))));
      }
    };
    render("");
    return [
      pageHead("Practice", "Cases", `${d.active.length} active · ${d.closed.length} closed`, searchBox("Search by name, case number or program", render)),
      el("section", { class: "panel" }, el("div", { class: "tablewrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ["Case", "Client", "Province", "Next action", "Next deadline", "Alerts"].map((h) => el("th", {}, h)))), body))),
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
          panel("Files", el("span", { class: "count" }, d.files.length ? `${d.files.length} file${d.files.length === 1 ? "" : "s"}` : ""),
            Object.keys(groups).length ? el("div", {}, Object.entries(groups).map(([g, fs]) => el("div", { class: "files-group" }, el("h3", {}, g),
              fs.map((f) => fileRow(f, null))))) : empty("No files yet."))),
        el("div", { class: "col" },
          panel("Ask Claude about this case", null, cmdList(d.commands)),
          panel("File checks", null, el("div", { class: "panel-body" }, el("dl", { class: "kv" },
            el("dt", {}, "Next action"), el("dd", {}, dash(i.next_action)),
            el("dt", {}, "Status expiry"), el("dd", {}, dash(fmtDate(i.status_expiry))),
            el("dt", {}, "Passport expiry"), el("dd", {}, dash(fmtDate(i.passport_expiry))),
            el("dt", {}, "Conflict check"), el("dd", {}, dash(i.conflict_check)),
            el("dt", {}, "Agreement signed"), el("dd", {}, dash(i.agreement_signed)),
            el("dt", {}, "IMM 5476 on file"), el("dd", {}, dash(i.imm5476_on_file))))),
          panel("Money", null, el("div", { class: "panel-body" },
            m.error ? el("div", { class: "error" }, m.error) : !m.has_ledger ? el("div", { class: "muted" }, "No billing recorded yet.") :
              el("dl", { class: "kv" }, el("dt", {}, "Invoiced"), el("dd", {}, money(m.invoiced)), el("dt", {}, "Received"), el("dd", {}, money(m.received)),
                el("dt", {}, "Unpaid"), el("dd", { class: owing ? "warn" : "strong" }, money(m.owing)), el("dt", {}, "Held in client account"), el("dd", {}, money(m.held))))),
          d.updates.length ? panel("Submitted and received", null,
            el("div", {}, d.updates.map((u) => el("div", { class: "row" }, el("span", {}, el("span", { class: "alert-what" }, u.kind + ": "), u.what),
              el("span", { class: "cell-stack" }, el("span", { class: "file-meta" }, fmtDate(u.date)), el("span", { class: "pill " + (u.notified ? "ok" : "Soon") }, u.notified ? "Client told" : "Client not told")))))) : null,
          panel("Recent activity", null,
            d.log.length ? el("div", {}, d.log.map((l) => el("div", { class: "row" }, el("span", {}, l.text), el("span", { class: "file-meta" }, fmtDate(l.date))))) : empty("No activity logged.")))),
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

function fileRow(f, sub) {
  const ext = extOf(f.name);
  return el("div", { class: "file" },
    el("span", { class: "ext " + ext }, (ext || "file").slice(0, 4).toUpperCase()),
    el("div", { class: "file-main" }, el("button", { onclick: () => openPath(f.path), title: "Open" }, f.name), sub ? el("span", { class: "small muted" }, sub) : null),
    el("span", { class: "file-meta" }, `${fmtDate(f.modified)} · ${fmtSize(f.size)}`));
}

function setFrame(d) {
  document.getElementById("firm").textContent = d.firm || "Firm profile not set up";
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
