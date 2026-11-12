// Immigration Agent dashboard. Every value from case files is inserted as text (never as HTML).
"use strict";
const KEY = document.querySelector('meta[name="agent-key"]').content;
const main = document.getElementById("main");

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
    toast(`Copied "${cmd}". Paste it in the Claude app (Code tab, this agent folder).`);
  } catch {
    toast(`Type this in the Claude app: ${cmd}`);
  }
}

const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? iso + "T00:00:00" : iso);
  return isNaN(d) ? iso : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
};
const fmtLeft = (n) => n === "" || n === null || n === undefined ? "" : n < 0 ? `${-n} day${n === -1 ? "" : "s"} overdue` : n === 0 ? "today" : `in ${n} day${n === 1 ? "" : "s"}`;
const fmtSize = (b) => b < 1024 ? `${b} B` : b < 1048576 ? `${Math.round(b / 1024)} KB` : `${(b / 1048576).toFixed(1)} MB`;
const money = (v) => { const n = Number(v); return isNaN(n) ? v : n.toLocaleString(undefined, { style: "currency", currency: "CAD" }); };
const caseLink = (folder, text) => el("a", { href: "#case/" + encodeURIComponent(folder) }, text || folder);

function cmdList(cmds) {
  return el("div", { class: "cmds" }, cmds.map((c) =>
    el("div", { class: "cmd" },
      el("div", {}, el("div", { class: "t" }, c.label), el("div", { class: "small muted" }, c.help), el("code", {}, c.command)),
      el("button", { class: "btn", onclick: () => copyCommand(c.command), title: "Copy, then paste in the Claude app" }, "Copy for Claude"))));
}

function alertTable(alerts, showCase) {
  if (!alerts.length) return el("div", { class: "empty" }, "Nothing needs attention. ✓");
  return el("div", { class: "tablewrap" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "Level"), showCase && el("th", {}, "Case"), el("th", {}, "What"), el("th", {}, "When"))),
    el("tbody", {}, alerts.map((a) => el("tr", {},
      el("td", {}, el("span", { class: "pill " + a.level }, a.level)),
      showCase && el("td", {}, a.case === "All files" ? a.case : caseLink(a.case)),
      el("td", {}, el("div", {}, `${a.kind}: ${a.text}`), el("div", { class: "step" }, a.step)),
      el("td", { class: "num" }, a.day ? el("div", {}, fmtDate(a.day)) : "", el("div", { class: "step" }, fmtLeft(a.left))))))));
}

function kbPanel(kb, policy) {
  const stale = kb.counts.stale + kb.counts["needs seed"];
  return el("section", { class: "panel" },
    el("h2", {}, "Knowledge base"),
    el("p", {}, el("span", { class: "pill " + (stale ? "Soon" : "ok") }, stale ? `${stale} to review` : "Up to date"), ` ${kb.counts.ok} of ${kb.total} files current`),
    policy && policy.date ? el("p", { class: "small muted" }, `Policy changes last checked ${fmtDate(policy.date)}` + (policy.age > policy.stale_after ? " — ask Claude: /changelog" : "")) : null);
}

const pages = {
  async home() {
    const d = await api("/api/home");
    document.getElementById("firm").textContent = d.firm || "Set up your firm profile in Claude";
    document.getElementById("today").textContent = fmtDate(d.today);
    const c = d.counts;
    const urgent = d.alerts.filter((a) => a.rank === 1), soon = d.alerts.filter((a) => a.rank === 2), house = d.alerts.filter((a) => a.rank === 3);
    return [
      el("div", { class: "head" }, el("div", {}, el("h1", {}, "Today"), el("div", { class: "muted" }, fmtDate(d.today) + (d.firm ? " · " + d.firm : "")))),
      el("div", { class: "tiles" },
        el("div", { class: "tile urgent" }, el("div", { class: "n" }, c.urgent), el("div", { class: "l" }, "Urgent")),
        el("div", { class: "tile soon" }, el("div", { class: "n" }, c.soon), el("div", { class: "l" }, "Coming up")),
        el("div", { class: "tile" }, el("div", { class: "n" }, c.week), el("div", { class: "l" }, "Deadlines in 7 days")),
        el("a", { class: "tile", href: "#cases" }, el("div", { class: "n" }, c.cases), el("div", { class: "l" }, "Active cases"))),
      el("div", { class: "grid2" },
        el("div", {},
          el("section", { class: "panel" }, el("h2", {}, "Needs attention"), alertTable([...urgent, ...soon], true)),
          house.length ? el("details", { class: "panel" }, el("summary", {}, el("strong", {}, `File housekeeping (${house.length})`)), alertTable(house, true)) : null),
        el("div", {},
          el("section", { class: "panel" }, el("h2", {}, "Ask Claude"), el("p", { class: "small muted" }, "Copy a command, then paste it in the Claude app (Code tab) in this agent folder."), cmdList(d.commands)),
          kbPanel(d.kb, d.policy_check))),
    ];
  },

  async cases() {
    const d = await api("/api/cases");
    const body = el("tbody");
    const render = (q) => {
      body.replaceChildren();
      const rows = d.active.filter((r) => !q || JSON.stringify(r).toLowerCase().includes(q));
      if (!rows.length) body.append(el("tr", {}, el("td", { colspan: 6, class: "empty" }, d.active.length ? "No case matches." : "No active cases yet. Ask Claude: /case new")));
      for (const r of rows) {
        body.append(el("tr", {},
          el("td", {}, caseLink(r.folder, r.id), el("div", { class: "small muted" }, r.program)),
          el("td", {}, r.client || el("span", { class: "muted" }, r.error || "")),
          el("td", {}, r.province),
          el("td", {}, r.next_action || el("span", { class: "muted" }, "Not set")),
          el("td", { class: "num" }, r.next_deadline ? [el("div", {}, fmtDate(r.next_deadline.due)), el("div", { class: "step" }, fmtLeft(r.next_deadline.left))] : el("span", { class: "muted" }, "None")),
          el("td", {}, r.urgent ? el("span", { class: "pill Urgent" }, `${r.urgent} urgent`) : null, " ", r.soon ? el("span", { class: "pill Soon" }, `${r.soon} soon`) : null)));
      }
    };
    render("");
    const search = el("input", { type: "search", placeholder: "Search by name, case number or program", "aria-label": "Search cases", oninput: (e) => render(e.target.value.trim().toLowerCase()) });
    return [
      el("div", { class: "head" }, el("div", {}, el("h1", {}, "Cases"), el("div", { class: "muted" }, `${d.active.length} active · ${d.closed.length} closed`)), search),
      el("section", { class: "panel" }, el("div", { class: "tablewrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ["Case", "Client", "Province", "Next action", "Next deadline", "Alerts"].map((h) => el("th", {}, h)))), body))),
      d.closed.length ? el("details", { class: "panel" }, el("summary", {}, el("strong", {}, `Closed files (${d.closed.length})`)),
        el("table", {}, el("tbody", {}, d.closed.map((r) => el("tr", {}, el("td", {}, caseLink(r.folder, r.case_id || r.folder)), el("td", {}, r.client), el("td", {}, r.program), el("td", { class: "num" }, "Closed " + fmtDate(r.closed)), el("td", { class: "num" }, r.destroy_after ? "Keep until " + fmtDate(r.destroy_after) : "")))))) : null,
    ];
  },

  async case(folder) {
    const d = await api("/api/case?folder=" + encodeURIComponent(folder));
    const i = d.info;
    const groups = {};
    for (const f of d.files) (groups[f.group || "(case folder)"] ||= []).push(f);
    const m = d.money;
    return [
      el("div", { class: "crumb" }, el("a", { href: "#cases" }, "← Cases")),
      el("div", { class: "head" },
        el("div", {}, el("h1", {}, `${i.case_id || d.folder}: ${i.client || ""}`), el("div", { class: "muted" }, [i.program, i.province, i.opened && "opened " + fmtDate(i.opened), d.closed && "CLOSED"].filter(Boolean).join(" · "))),
        el("button", { class: "btn primary", onclick: () => openPath(d.path) }, "Open case folder")),
      el("div", { class: "grid2" },
        el("div", {},
          el("section", { class: "panel" }, el("h2", {}, "Needs attention"), alertTable(d.alerts, false)),
          el("section", { class: "panel" }, el("h2", {}, "Deadlines"),
            d.deadlines.length ? el("div", { class: "tablewrap" }, el("table", {},
              el("thead", {}, el("tr", {}, ["Due", "What", "Basis", ""].map((h) => el("th", {}, h)))),
              el("tbody", {}, d.deadlines.map((r) => el("tr", {},
                el("td", { class: "num" }, fmtDate(r.due), el("div", { class: "step" }, r.done ? "" : fmtLeft(r.left))),
                el("td", {}, `${r.type}: ${r.description}`), el("td", { class: "small muted" }, r.basis),
                el("td", {}, r.done ? el("span", { class: "pill done" }, "Done") : r.left < 0 ? el("span", { class: "pill Urgent" }, "Overdue") : null)))))) : el("div", { class: "empty" }, "No deadlines tracked. Ask Claude to add one.")),
          el("section", { class: "panel" }, el("h2", {}, "Files"),
            Object.keys(groups).length ? Object.entries(groups).map(([g, fs]) => el("div", { class: "files-group" }, el("h3", {}, g),
              fs.map((f) => el("div", { class: "file" }, el("button", { onclick: () => openPath(f.path), title: "Open" }, f.name), el("span", { class: "small muted num" }, `${fmtDate(f.modified)} · ${fmtSize(f.size)}`))))) : el("div", { class: "empty" }, "No files yet."))),
        el("div", {},
          el("section", { class: "panel" }, el("h2", {}, "Ask Claude about this case"), cmdList(d.commands)),
          el("section", { class: "panel" }, el("h2", {}, "File"),
            el("dl", { class: "kv" },
              el("dt", {}, "Next action"), el("dd", {}, i.next_action || "Not set"),
              el("dt", {}, "Status expiry"), el("dd", {}, fmtDate(i.status_expiry) || "—"),
              el("dt", {}, "Passport expiry"), el("dd", {}, fmtDate(i.passport_expiry) || "—"),
              el("dt", {}, "Conflict check"), el("dd", {}, i.conflict_check || "—"),
              el("dt", {}, "Agreement signed"), el("dd", {}, i.agreement_signed || "—"),
              el("dt", {}, "IMM 5476 on file"), el("dd", {}, i.imm5476_on_file || "—"))),
          el("section", { class: "panel" }, el("h2", {}, "Money"),
            m.error ? el("div", { class: "error" }, m.error) : !m.has_ledger ? el("div", { class: "muted" }, "No billing recorded yet.") :
              el("dl", { class: "kv" }, el("dt", {}, "Invoiced"), el("dd", {}, money(m.invoiced)), el("dt", {}, "Received"), el("dd", {}, money(m.received)),
                el("dt", {}, "Unpaid"), el("dd", {}, money(m.owing)), el("dt", {}, "Held in client account"), el("dd", {}, money(m.held)))),
          d.updates.length ? el("section", { class: "panel" }, el("h2", {}, "Submitted and received"),
            d.updates.map((u) => el("div", { class: "file" }, el("span", {}, `${u.kind}: ${u.what}`), el("span", { class: "small muted num" }, fmtDate(u.date) + (u.notified ? " · client told" : " · client not told yet"))))) : null,
          el("section", { class: "panel" }, el("h2", {}, "Recent activity"),
            d.log.length ? d.log.map((l) => el("div", { class: "file" }, el("span", {}, l.text), el("span", { class: "small muted num" }, fmtDate(l.date)))) : el("div", { class: "muted" }, "No activity logged.")))),
    ];
  },

  async documents() {
    const d = await api("/api/documents");
    const list = el("div");
    const render = (q) => {
      list.replaceChildren();
      const rows = d.files.filter((f) => !q || (f.name + " " + f.group).toLowerCase().includes(q));
      if (!rows.length) list.append(el("div", { class: "empty" }, d.files.length ? "No document matches." : "No finished documents yet. Claude saves them in the Output folder."));
      for (const f of rows) list.append(el("div", { class: "file" },
        el("div", {}, el("button", { onclick: () => openPath(f.path) }, f.name), el("div", { class: "small muted" }, f.group)),
        el("span", { class: "small muted num" }, `${fmtDate(f.modified)} · ${fmtSize(f.size)}`)));
    };
    render("");
    return [
      el("div", { class: "head" }, el("div", {}, el("h1", {}, "Documents"), el("div", { class: "muted" }, "Finished letters, forms, reports and checklists, newest first")),
        el("div", {}, el("input", { type: "search", placeholder: "Search documents", "aria-label": "Search documents", oninput: (e) => render(e.target.value.trim().toLowerCase()) }), " ",
          d.folder ? el("button", { class: "btn", onclick: () => openPath(d.folder) }, "Open Output folder") : null)),
      el("section", { class: "panel" }, list),
    ];
  },

  async agent() {
    const d = await api("/api/agent");
    const notes = el("div", { class: "notes" });
    let ul = null;
    for (const line of d.whats_new.split(/\r?\n/)) {
      if (/^##\s/.test(line)) { notes.append(el("h2", {}, "Version " + line.replace(/^##\s+v?/, ""))); ul = null; }
      else if (/^\s*-\s/.test(line)) { if (!ul) { ul = el("ul"); notes.append(ul); } ul.append(el("li", {}, line.replace(/^\s*-\s+/, "").replace(/`/g, ""))); }
    }
    return [
      el("div", { class: "head" }, el("div", {}, el("h1", {}, "Agent & updates"), el("div", { class: "muted" }, `Version ${d.version}` + (d.install.updated ? ` · last updated ${fmtDate(d.install.updated)}` : "")))),
      el("div", { class: "grid2" },
        el("section", { class: "panel" }, el("h2", {}, "What's new"), notes),
        el("div", {},
          el("section", { class: "panel" }, el("h2", {}, "Getting updates"),
            el("p", { class: "small" }, "Updates arrive by themselves when auto-update is on in the Claude app (/plugin › Marketplaces › Enable auto-update). They install when you next start Claude in this folder. Your client files are never changed."),
            cmdList([{ label: "Check for updates", command: "/immigration-agent:update", help: "Your version and what's new" }])),
          kbPanel(d.kb),
          d.kb.attention.length ? el("section", { class: "panel" }, el("h2", {}, "Files to review"),
            d.kb.attention.map((r) => el("div", { class: "file" }, el("span", { class: "small" }, r.file), el("span", { class: "pill Soon" }, r.state)))) : null)),
    ];
  },
};

async function route() {
  const [page, arg] = (location.hash.slice(1) || "home").split("/");
  const name = pages[page] ? page : "home";
  for (const a of document.querySelectorAll("#nav a")) a.classList.toggle("on", a.dataset.page === (name === "case" ? "cases" : name));
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
api("/api/home").then((d) => {
  document.getElementById("firm").textContent = d.firm || "";
  document.getElementById("today").textContent = fmtDate(d.today);
}).catch(() => {});
route();
