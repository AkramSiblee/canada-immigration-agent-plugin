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
