/* Lokanon – Oberfläche. Ein geführter Weg in vier Schritten; alle Daten kommen vom lokalen Server (127.0.0.1). */
(() => {
  "use strict";
  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const view = $("#view");

  const S = {                       // Zustand der Oberfläche
    status: null, cfg: null, vorgang: null, schritt: 1, pollTimer: null, docIndex: 0, docMode: "markiert",
    filter: "", busy: false, route: "start", einrichtSeite: 1, einricht: {},
  };
  const GRUPPEN_FARBE = {
    "Personen": "var(--g-person)", "Firmen und Einrichtungen": "var(--g-firma)", "Adressen und Orte": "var(--g-ort)",
    "Kontaktdaten": "var(--g-kontakt)", "Akten, Zeichen, Verträge": "var(--g-akten)", "Konto und Steuer": "var(--g-konto)",
    "Ausweise und Nummern": "var(--g-ausweis)", "Fahrzeug": "var(--g-fahrzeug)", "Datum": "var(--g-datum)",
    "Beruf und Gesundheit": "var(--g-beruf)", "Eigene Begriffe": "var(--g-eigene)",
  };
  const ANBIETER = ["ChatGPT Business / Enterprise", "Claude Team / Enterprise", "Microsoft 365 Copilot Chat",
    "EU-Anbieter (Langdock, innoGPT, Mistral Team)", "ChatGPT Plus/Pro (Consumer, ohne AVV)", "Claude Pro/Max (Consumer, ohne AVV)",
    "Lokale KI (Ollama)", "Sonstiges"];

  // ------------------------------------------------------------ Server
  async function api(path, opts = {}) {
    const o = { headers: {}, ...opts };
    if (o.json !== undefined) { o.method = o.method || "POST"; o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(o.json); }
    const r = await fetch("/api" + path, o);
    let data = null;
    try { data = await r.json(); } catch { data = null; }
    if (!r.ok) throw new Error((data && data.fehler) || `Fehler ${r.status}`);
    return data;
  }
  function toast(msg, kind = "") {
    const t = document.createElement("div"); t.className = "toast " + kind; t.textContent = msg;
    $("#toasts").appendChild(t); setTimeout(() => t.remove(), kind === "danger" ? 7000 : 3500);
  }
  function modal(html, actions = []) {
    const root = $("#modal-root"); root.hidden = false;
    root.innerHTML = `<div class="modal" role="dialog" aria-modal="true">${html}<div class="row" style="justify-content:flex-end;margin-top:16px" id="modal-actions"></div></div>`;
    const box = $("#modal-actions");
    actions.forEach(([label, fn, cls]) => { const b = document.createElement("button"); b.className = "btn " + (cls || ""); b.textContent = label;
      b.onclick = async () => { if (await fn() !== false) { root.hidden = true; } }; box.appendChild(b); });
    return root;
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast("Kopiert", "ok"); }
    catch { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); toast("Kopiert", "ok"); }
  }
  function bytes(n) { return n > 1e6 ? (n / 1e6).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB"; }
  function datum(iso) { if (!iso) return ""; const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" }); }

  // ------------------------------------------------------------ Router
  window.addEventListener("hashchange", render);
  async function render() {
    let hash = (location.hash || "#start").slice(1);
    const tief = hash.match(/^vorgang\/([1-4])$/);  // Direktlink auf einen Schritt, z. B. #vorgang/3
    if (tief) { S.schritt = +tief[1]; hash = "vorgang"; }
    S.route = hash;
    document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("active", a.dataset.nav === hash));
    try {
      S.status = await api("/status");
      $("#version").textContent = "Version " + S.status.version;
      const badge = $("#local-badge");
      badge.classList.toggle("laden", !S.status.modelle_bereit);
      $("#local-text").textContent = S.status.modelle_bereit ? "Läuft lokal auf diesem PC" : "Sprachmodelle werden geladen …";
      if (!S.status.modelle_bereit && !S.pollStatus) { S.pollStatus = setInterval(async () => { const st = await api("/status"); if (st.modelle_bereit) { clearInterval(S.pollStatus); S.pollStatus = null; badge.classList.remove("laden"); $("#local-text").textContent = "Läuft lokal auf diesem PC"; } }, 1500); }
      if (!S.status.eingerichtet && hash !== "einrichten") { location.hash = "#einrichten"; return; }
    } catch (e) { view.innerHTML = `<div class="notice danger">Der lokale Server antwortet nicht. Bitte Lokanon neu starten.</div>`; return; }
    const routes = { start: renderStart, vorgang: renderVorgang, zurueck: renderZurueck, einstellungen: renderEinstellungen, hilfe: renderHilfe, einrichten: renderEinrichten };
    (routes[hash] || renderStart)();
  }

  // ------------------------------------------------------------ Start
  async function renderStart() {
    const [liste, cfg] = await Promise.all([api("/vorgaenge"), api("/einstellungen")]);
    S.cfg = cfg;
    const offen = await api("/vorgang?kurz=1");
    $("#nav-vorgang").hidden = !offen.id;
    const zuletzt = (liste.zuletzt_ordner || []).slice(0, 4);
    view.innerHTML = `
      <div class="page-head"><div><h1>Mandatsunterlagen für die KI vorbereiten</h1>
        <p class="sub">Legen Sie Dateien ab oder wählen Sie einen Aktenordner. Lokanon erkennt Personendaten, Sie prüfen und entscheiden, dann entstehen Kopien, die Sie gefahrlos in ChatGPT oder Claude geben können.</p></div></div>
      <div class="hero">
        <section class="card raised">
          <div class="eyebrow">Neuer Vorgang</div>
          <h2 style="margin:4px 0 14px">Was möchten Sie vorbereiten?</h2>
          <label class="field" style="margin-bottom:14px"><span>Name des Vorgangs <span class="hint">(Akte, Mandat, Aktenzeichen – wird auch der Ordnername)</span></span>
            <input class="input" id="v-name" value="" placeholder="z. B. Müller ./. Autohaus Krause – 3 O 123/26"></label>
          <div class="choice">
            <div class="dropzone" id="dz" tabindex="0" role="button" aria-label="Dateien ablegen oder auswählen">
              <div class="big-ico">⤓</div><b>Dateien hierher ziehen</b><div class="muted small">oder klicken und auswählen · PDF, Word, Excel, Text</div>
              <input type="file" id="dz-input" multiple accept=".pdf,.docx,.xlsx,.txt,.md,.csv" hidden></div>
            <div class="dropzone" id="dz-folder" tabindex="0" role="button" aria-label="Aktenordner wählen">
              <div class="big-ico">▤</div><b>Aktenordner wählen</b><div class="muted small">alle Dateien eines Ordners; die Ausgabe landet im Unterordner „Lokanon“</div></div>
          </div>
          <div id="dz-files" class="filelist"></div>
          <div class="row" style="margin-top:14px"><button class="btn ghost" id="text-btn">Stattdessen Text einfügen</button>
            ${zuletzt.length ? `<span class="muted small">Zuletzt:</span>${zuletzt.map((p) => `<button class="linkbtn" data-ordner="${esc(p)}" title="${esc(p)}">${esc(p.split(/[\\/]/).filter(Boolean).pop())}</button>`).join(" · ")}` : ""}
          </div>
        </section>
        <section class="card">
          <div class="eyebrow">Bisherige Vorgänge</div>
          <div class="vlist" style="margin-top:10px" id="vlist">
            ${liste.vorgaenge.length ? liste.vorgaenge.slice(0, 8).map((v) => `<div class="vitem"><div class="t"><b>${esc(v.name)}</b><span>${v.dateien} Datei(en) · ${v.platzhalter} Platzhalter · ${esc(datum(v.angelegt))}${v.abgeschlossen ? " · abgeschlossen" : ""}</span></div>
                <button class="btn" data-open="${esc(v.basis)}" title="Vorgangsordner öffnen">Ordner</button></div>`).join("")
              : `<p class="muted">Noch keine Vorgänge. Der erste entsteht links.</p>`}
          </div>
          ${liste.vorgaenge.length ? `<p class="muted small" style="margin-top:10px">Antworten zu früheren Vorgängen übersetzen Sie unter „Antwort zurückübersetzen“ mit der zugehörigen Schlüsseldatei zurück.</p>` : ""}
        </section>
      </div>
      <div class="facts">
        <div class="fact"><b>Nichts verlässt den Rechner</b><span>Erkennung, Texterkennung und Schwärzung laufen hier. Internet ist nicht nötig.</span></div>
        <div class="fact"><b>Sie entscheiden</b><span>Jeder erkannte Begriff hat einen Schalter. Platzhalter bekommen auf Wunsch eigene Namen wie „Mandant“.</span></div>
        <div class="fact"><b>Nachvollziehbar</b><span>Je Vorgang ein Ordner mit Originalen, Kopien, Prüfbericht und Protokoll. Der Schlüssel bleibt verschlüsselt bei Ihnen.</span></div>
      </div>`;
    const pending = [];
    const dz = $("#dz"), inp = $("#dz-input");
    const renderPending = () => { $("#dz-files").innerHTML = pending.map((f, i) => `<div class="file"><span class="ext">${esc(f.name.split(".").pop())}</span><span class="name">${esc(f.name)}</span><span class="muted small">${bytes(f.size)}</span><button class="iconbtn" data-rm="${i}" title="Entfernen">✕</button></div>`).join("") + (pending.length ? `<div class="row" style="margin-top:6px"><button class="btn primary big" id="start-upload">Vorgang anlegen und analysieren</button></div>` : "");
      document.querySelectorAll("[data-rm]").forEach((b) => b.onclick = () => { pending.splice(+b.dataset.rm, 1); renderPending(); });
      const sb = $("#start-upload"); if (sb) sb.onclick = () => startMitDateien(pending); };
    const addFiles = (files) => { for (const f of files) if (!pending.some((p) => p.name === f.name)) pending.push(f); renderPending(); };
    dz.onclick = () => inp.click(); dz.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") inp.click(); };
    inp.onchange = () => addFiles(inp.files);
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
    dz.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
    $("#dz-folder").onclick = async () => { try { const r = await api("/system/ordner-waehlen", { method: "POST" }); if (r.pfad) startMitOrdner(r.pfad); } catch (e) { toast(e.message, "danger"); } };
    document.querySelectorAll("[data-ordner]").forEach((b) => b.onclick = () => startMitOrdner(b.dataset.ordner));
    document.querySelectorAll("[data-open]").forEach((b) => b.onclick = () => oeffnen(b.dataset.open));
    $("#text-btn").onclick = () => modal(`<h2>Text einfügen</h2><p class="muted small" style="margin:6px 0 10px">Zum Beispiel eine E-Mail oder einen Absatz aus einem Schriftsatz.</p><textarea class="input" id="m-text" rows="10"></textarea>`,
      [["Abbrechen", () => true], ["Analysieren", async () => { const t = $("#m-text").value; if (!t.trim()) return false; await startMitText(t); }, "primary"]]);
  }
  async function neuerVorgang(ordner = "") {
    const name = ($("#v-name") && $("#v-name").value.trim()) || "";
    const z = await api("/vorgang", { json: { name, ordner } });
    S.vorgang = z; S.schritt = 1; $("#nav-vorgang").hidden = false; return z;
  }
  async function startMitDateien(files) {
    try { await neuerVorgang(); for (const f of files) { const fd = new FormData(); fd.append("datei", f, f.name); await api("/vorgang/datei", { method: "POST", body: fd }); }
      location.hash = "#vorgang"; await analyseStarten(); } catch (e) { toast(e.message, "danger"); }
  }
  async function startMitOrdner(pfad) { try { await neuerVorgang(pfad); location.hash = "#vorgang"; await analyseStarten(); } catch (e) { toast(e.message, "danger"); } }
  async function startMitText(text) { try { await neuerVorgang(); await api("/vorgang/text", { json: { text } }); location.hash = "#vorgang"; await analyseStarten(); } catch (e) { toast(e.message, "danger"); } }
  async function oeffnen(pfad) { try { await api("/system/oeffnen", { json: { pfad } }); } catch (e) { toast(e.message, "danger"); } }

  // ------------------------------------------------------------ Vorgang: Rahmen und Schritte
  async function renderVorgang() {
    const z = await api("/vorgang?kurz=1");
    if (!z.id) { location.hash = "#start"; return; }
    S.vorgang = z;
    if (z.fortschritt.laeuft) { renderFortschritt(); pollFortschritt(); return; }
    if (z.fortschritt.fertig && S.schritt < 2) S.schritt = 2;
    if (!z.fortschritt.fertig) S.schritt = 1;
    const full = z.fortschritt.fertig ? await api("/vorgang") : z;
    S.vorgang = full;
    const steps = ["Dateien", "Prüfen", "Fertigstellen", "Antwort"];
    const maxStep = full.fortschritt && full.fortschritt.fertig ? (full.ausgaben && full.ausgaben.length ? 4 : 3) : 1;
    if (S.schritt > maxStep) S.schritt = maxStep;
    view.innerHTML = `
      <div class="page-head"><div><div class="eyebrow">Vorgang</div><h1>${esc(full.name)}</h1></div>
        <div class="row"><button class="btn" id="open-basis">Vorgangsordner öffnen</button><button class="btn ghost" id="neu-btn">Neuer Vorgang</button></div></div>
      <div class="stepper">${steps.map((s, i) => { const n = i + 1; const cls = n === S.schritt ? "current" : n < S.schritt || n <= maxStep ? "done" : ""; return `<div class="step ${cls}" data-step="${n}"><span class="n">${n < S.schritt ? "✓" : n}</span>${s}</div>`; }).join("")}</div>
      <div id="step-body"></div>`;
    $("#open-basis").onclick = () => oeffnen(full.basis);
    $("#neu-btn").onclick = () => { location.hash = "#start"; };
    document.querySelectorAll(".step.done").forEach((el) => el.onclick = () => { S.schritt = +el.dataset.step; renderVorgang(); });
    const body = $("#step-body");
    ({ 1: renderSchritt1, 2: renderSchritt2, 3: renderSchritt3, 4: renderSchritt4 }[S.schritt])(body, full);
  }

  function renderSchritt1(body, z) {
    const files = z.dateien || [];
    body.innerHTML = `<section class="card">
      <h2>Dateien dieses Vorgangs</h2>
      <p class="muted" style="margin:4px 0 12px">${z.ordner ? `Aktenordner: <code>${esc(z.ordner)}</code>` : `Ihre Dateien liegen gesichert unter <code>${esc(z.originale)}</code>.`}</p>
      <div class="filelist">${files.map((f) => `<div class="file"><span class="ext">${esc(f.name.split(".").pop())}</span><span class="name">${esc(f.name)}</span><span class="muted small">${bytes(f.groesse || 0)}</span>${z.ordner ? "" : `<button class="iconbtn" data-rm="${esc(f.name)}" title="Entfernen">✕</button>`}</div>`).join("") || `<p class="muted">Noch keine Dateien.</p>`}</div>
      ${z.ordner ? "" : `<div class="row" style="margin-top:12px"><button class="btn" id="more-btn">Weitere Dateien hinzufügen</button><input type="file" id="more-input" multiple accept=".pdf,.docx,.xlsx,.txt,.md,.csv" hidden></div>`}
      <div class="row" style="margin-top:18px"><button class="btn primary big" id="analyse-btn" ${files.length ? "" : "disabled"}>Analyse starten</button>
        <span class="muted small">Dauert je Seite wenige Sekunden; gescannte Seiten brauchen Texterkennung und etwas länger.</span></div>
    </section>`;
    document.querySelectorAll("[data-rm]").forEach((b) => b.onclick = async () => { await api("/vorgang/datei-entfernen", { json: { name: b.dataset.rm } }); renderVorgang(); });
    const mi = $("#more-input"); if (mi) { $("#more-btn").onclick = () => mi.click(); mi.onchange = async () => { for (const f of mi.files) { const fd = new FormData(); fd.append("datei", f, f.name); await api("/vorgang/datei", { method: "POST", body: fd }); } renderVorgang(); }; }
    $("#analyse-btn").onclick = analyseStarten;
  }

  async function analyseStarten(begriffe = []) {
    try { await api("/vorgang/analysieren", { json: { begriffe } }); renderFortschritt(); pollFortschritt(); } catch (e) { toast(e.message, "danger"); }
  }
  function renderFortschritt() {
    view.innerHTML = `<div class="card raised progress-panel" style="max-width:720px;margin:60px auto">
      <div class="eyebrow">Analyse läuft</div><h2 id="p-schritt" style="margin-top:6px">Modelle laden …</h2>
      <p class="muted" id="p-datei">&nbsp;</p>
      <div class="bar indeterminate" id="p-bar"><i></i></div>
      <p class="muted small">Alles passiert auf diesem PC. Beim ersten Start dauert das Laden der Sprachmodelle etwa eine halbe Minute.</p></div>`;
  }
  function pollFortschritt() {
    clearInterval(S.pollTimer);
    S.pollTimer = setInterval(async () => {
      try {
        const f = await api("/vorgang/fortschritt");
        const bar = $("#p-bar");
        if (bar) { bar.classList.toggle("indeterminate", f.prozent < 5); bar.firstElementChild.style.width = f.prozent + "%"; $("#p-schritt").textContent = f.schritt || "…"; $("#p-datei").textContent = f.datei || " "; }
        if (!f.laeuft) { clearInterval(S.pollTimer); if (f.fehler) { toast(f.fehler, "danger"); S.schritt = 1; } else { S.schritt = 2; S.docIndex = 0; } renderVorgang(); }
      } catch (e) { clearInterval(S.pollTimer); toast(e.message, "danger"); }
    }, 600);
  }

  // ------------------------------------------------------------ Schritt 2: Prüfen
  function renderSchritt2(body, z) {
    const begriffe = z.begriffe || [];
    const unsicher = begriffe.filter((g) => g.unsicher && g.aktiv);
    const gruppen = [...new Set(begriffe.map((g) => g.gruppe))];
    const aktiv = begriffe.filter((g) => g.aktiv).length;
    body.innerHTML = `
      <div class="pruefen">
        <section>
          <div class="toolbar">
            <div><h2 style="display:inline">${begriffe.length} Begriffe gefunden</h2> <span class="muted">· ${aktiv} werden ersetzt · ${z.platzhalter_anzahl} Platzhalter</span></div>
          </div>
          ${unsicher.length ? `<details class="card unsure" open style="padding:12px 16px;margin-bottom:12px"><summary>Bitte ansehen: ${unsicher.length} ${unsicher.length === 1 ? "Begriff ist" : "Begriffe sind"} nicht eindeutig</summary>
            <ul>${unsicher.map((g) => `<li><b>${esc(g.begriff)}</b> (${esc(g.typ)}): ${esc(g.gruende.join("; "))}</li>`).join("")}</ul>
            <p class="muted small" style="margin-top:8px">Lokanon ersetzt im Zweifel. Wenn ein Begriff kein Personenbezug ist, schalten Sie ihn unten aus.</p></details>` : ""}
          <div class="toolbar">
            <div class="filter"><button class="${S.filter ? "" : "on"}" data-f="">Alle</button>${gruppen.map((g) => `<button class="${S.filter === g ? "on" : ""}" data-f="${esc(g)}">${esc(g)}</button>`).join("")}</div>
          </div>
          <div class="row" style="margin-bottom:6px"><input class="input" id="nachtrag" placeholder="Begriff übersehen? Hier eintragen, mehrere mit Komma" style="max-width:420px"><button class="btn" id="nachtrag-btn">Nachtragen</button></div>
          <div id="groups"></div>
        </section>
        <aside class="docpanel">
          <div class="row between"><h3>Dokumente</h3>
            <div class="filter"><button class="${S.docMode === "markiert" ? "on" : ""}" data-m="markiert">Original mit Markierungen</button><button class="${S.docMode === "anonym" ? "on" : ""}" data-m="anonym">Anonymisiert</button></div></div>
          <div class="doctabs" id="doctabs"></div>
          <div class="docview" id="docview"></div>
          <div class="legend"><span><i style="background:var(--mark-person)"></i>Person</span><span><i style="background:var(--mark-firma)"></i>Firma</span><span><i style="background:var(--mark-ort)"></i>Adresse/Ort</span><span><i style="background:var(--mark-nummer)"></i>Nummern</span><span><i style="background:var(--mark-datum)"></i>Datum</span><span><i style="border:1px dashed var(--muted)"></i>bleibt stehen</span></div>
          <div class="row" style="margin-top:16px;justify-content:flex-end"><button class="btn primary big" id="weiter3">Weiter zu „Fertigstellen“ →</button></div>
        </aside>
      </div>`;
    document.querySelectorAll("[data-f]").forEach((b) => b.onclick = () => { S.filter = b.dataset.f; renderSchritt2(body, z); });
    document.querySelectorAll("[data-m]").forEach((b) => b.onclick = () => { S.docMode = b.dataset.m; renderDoc(z); document.querySelectorAll("[data-m]").forEach((x) => x.classList.toggle("on", x.dataset.m === S.docMode)); });
    $("#weiter3").onclick = () => { S.schritt = 3; renderVorgang(); };
    $("#nachtrag-btn").onclick = async () => { const t = $("#nachtrag").value.split(",").map((s) => s.trim()).filter(Boolean); if (!t.length) return; try { await api("/vorgang/nachtragen", { json: { begriffe: t } }); renderFortschritt(); pollFortschritt(); } catch (e) { toast(e.message, "danger"); } };
    $("#nachtrag").onkeydown = (e) => { if (e.key === "Enter") $("#nachtrag-btn").click(); };
    renderGroups(z); renderDoc(z);
  }
  function renderGroups(z) {
    const begriffe = (z.begriffe || []).filter((g) => !S.filter || g.gruppe === S.filter);
    const byG = {}; begriffe.forEach((g) => (byG[g.gruppe] = byG[g.gruppe] || []).push(g));
    let i = 0;
    $("#groups").innerHTML = Object.entries(byG).map(([gruppe, items]) => `
      <div class="group-title"><span class="dot" style="background:${GRUPPEN_FARBE[gruppe] || "var(--muted)"}"></span>${esc(gruppe)} <span class="count">· ${items.filter((g) => g.aktiv).length} von ${items.length} werden ersetzt</span></div>
      <div class="cards">${items.map((g) => `
        <div class="term ${g.aktiv ? "" : "aus"}" style="--g:${GRUPPEN_FARBE[gruppe] || "var(--line-2)"};--i:${i++}" data-key="${esc(g.key)}">
          <div class="head"><span class="word">${esc(g.begriff)}</span><span class="arrow">→</span>
            ${g.aktiv ? `<span class="ph-edit" data-ph="${esc(g.ph_basis)}"><span class="ph">${esc(g.platzhalter || "[" + g.typ + "]")}</span>${g.ph_basis ? `<button class="linkbtn" data-rename="${esc(g.ph_basis)}" title="Eigene Bezeichnung vergeben, z. B. Mandant">${g.bezeichnung ? "ändern" : "benennen"}</button>` : ""}</span>` : `<span class="muted">bleibt stehen</span>`}
            ${g.unsicher && g.aktiv ? `<span class="chip warn" title="${esc(g.gruende.join("; "))}">prüfen</span>` : ""}</div>
          <div class="meta">${esc(g.typ)} · ${g.anzahl}× in ${g.dateien.length} Datei${g.dateien.length === 1 ? "" : "en"} · ${g.sicherheit} · ${esc(g.quellen.join(", "))}</div>
          <div class="snip">${g.beispiel}</div>
          <div class="foot"><label class="switch-label"><span class="switch"><input type="checkbox" ${g.aktiv ? "checked" : ""} data-toggle="${esc(g.key)}" aria-label="${esc(g.begriff)} ersetzen"><span class="track"></span></span>${g.aktiv ? "wird ersetzt" : "bleibt stehen"}</label></div>
        </div>`).join("")}</div>`).join("") || `<p class="muted">Keine Begriffe in dieser Gruppe.</p>`;
    document.querySelectorAll("[data-toggle]").forEach((cb) => cb.onchange = async () => {
      try { const nz = await api("/vorgang/begriff", { json: { key: cb.dataset.toggle, aktiv: cb.checked } }); S.vorgang = nz; renderSchritt2($("#step-body"), nz); } catch (e) { toast(e.message, "danger"); }
    });
    document.querySelectorAll("[data-rename]").forEach((b) => b.onclick = () => renameDialog(b.dataset.rename, z));
  }
  function renameDialog(ph, z) {
    const g = (z.begriffe || []).find((x) => x.ph_basis === ph) || {};
    const vorschlaege = g.vorschlaege || [];
    modal(`<h2>Eigene Bezeichnung</h2><p class="muted small" style="margin:6px 0 12px">Statt <span class="ph">[${esc(ph)}]</span> steht dann überall im Vorgang Ihre Bezeichnung, z. B. <span class="ph">[MANDANT]</span>. Die KI versteht das genauso, die Rückübersetzung auch.</p>
      <label class="field"><span>Bezeichnung für „${esc(g.begriff || "")}“</span><input class="input" id="m-bez" list="m-list" value="${esc(g.bezeichnung || "")}" placeholder="z. B. Mandant"><datalist id="m-list">${vorschlaege.map((v) => `<option value="${esc(v)}">`).join("")}</datalist></label>
      <div class="row" style="margin-top:8px">${vorschlaege.slice(0, 6).map((v) => `<button class="radio-chip" data-v="${esc(v)}">${esc(v)}</button>`).join("")}</div>`,
      [["Zurücksetzen", async () => { await setzeBezeichnung(ph, ""); }, "ghost"], ["Abbrechen", () => true], ["Übernehmen", async () => { await setzeBezeichnung(ph, $("#m-bez").value); }, "primary"]]);
    document.querySelectorAll("[data-v]").forEach((b) => b.onclick = () => { $("#m-bez").value = b.dataset.v; });
    setTimeout(() => $("#m-bez").focus(), 50);
  }
  async function setzeBezeichnung(ph, bez) {
    try { const nz = await api("/vorgang/bezeichnung", { json: { platzhalter: ph, bezeichnung: bez } }); S.vorgang = nz; renderSchritt2($("#step-body"), nz); } catch (e) { toast(e.message, "danger"); return false; }
  }
  function renderDoc(z) {
    const docs = z.dokumente || [];
    if (S.docIndex >= docs.length) S.docIndex = 0;
    $("#doctabs").innerHTML = docs.map((d, i) => `<button class="${i === S.docIndex ? "on" : ""}" data-doc="${i}" title="${esc(d.name)}">${esc(d.name)}${d.ocr ? " · OCR" : ""}</button>`).join("");
    document.querySelectorAll("[data-doc]").forEach((b) => b.onclick = () => { S.docIndex = +b.dataset.doc; renderDoc(z); });
    const d = docs[S.docIndex];
    const dv = $("#docview");
    if (!d) { dv.textContent = ""; return; }
    dv.innerHTML = S.docMode === "markiert" ? d.markiert_html : esc(d.anonym);
    const info = d.ocr ? `<div class="notice warn small" style="margin-top:8px">${d.ocr} von ${d.seiten} Seiten per Texterkennung gelesen. Erkannter Text kann Fehler enthalten, deshalb hier besonders genau hinsehen.</div>` : "";
    dv.insertAdjacentHTML("afterend", "");
    const old = $("#ocr-info"); if (old) old.remove();
    if (info) dv.insertAdjacentHTML("afterend", `<div id="ocr-info">${info}</div>`);
  }

  // ------------------------------------------------------------ Schritt 3: Fertigstellen
  function renderSchritt3(body, z) {
    const consumer = (a) => /Consumer/.test(a);
    body.innerHTML = `
      <div class="grid-2">
        <section class="card raised">
          <h2>Dateien für die KI erzeugen</h2>
          <p class="muted" style="margin:4px 0 14px">Es entstehen Kopien mit Platzhaltern. Die Originale bleiben unverändert.</p>
          <div class="stack">
            <label class="field"><span>Ziel-KI <span class="hint">(fürs Protokoll; Consumer-Konten haben keinen Vertrag zur Auftragsverarbeitung)</span></span>
              <select class="input" id="anbieter">${ANBIETER.map((a) => `<option>${esc(a)}</option>`).join("")}</select></label>
            <div id="consumer-warn" class="notice warn" hidden><span>⚠</span><span>Bei Consumer-Konten ist Lokanon die einzige Schutzschicht. Schalten Sie dort das Training ab und laden Sie nur die Dateien aus „Fuer die KI“ hoch. Mehr dazu in der Anleitung.</span></div>
            <div><div class="eyebrow" style="margin-bottom:6px">Zusätzlich zur Textfassung</div>
              <label class="checkbox"><input type="checkbox" id="f-pdf" checked><span><b>PDF-Sichtkopie</b> <span class="muted">– echte Schwärzung, mit Gegenprüfung</span></span></label>
              <label class="checkbox"><input type="checkbox" id="f-docx" checked><span><b>Word-Kopie</b> <span class="muted">– ohne Namen und Metadaten</span></span></label>
              <label class="checkbox"><input type="checkbox" id="f-xlsx" checked><span><b>Excel-Kopie</b></span></label></div>
            <label class="checkbox"><input type="checkbox" id="geprueft"><span><b>Ich habe die Begriffe geprüft.</b> <span class="muted">Die Prüfung durch einen Menschen ist Pflicht vor dem Versand an eine KI.</span></span></label>
            <div class="row"><button class="btn primary big" id="erzeugen" disabled>Dateien erzeugen</button></div>
          </div>
          <div id="ergebnis" style="margin-top:18px"></div>
        </section>
        <div class="stack">
          <section class="card">
            <h3>So geht es in der KI weiter</h3>
            <ol class="steps-mini" style="margin-top:10px">
              <li><span>In ChatGPT oder Claude ein <b>Projekt</b> anlegen und die Anweisung unten als Projekt-Anweisung einfügen.</span></li>
              <li><span>Nur die Dateien aus dem Ordner <b>„Fuer die KI“</b> hochladen oder deren Text einfügen.</span></li>
              <li><span>Die Antwort kopieren und unter <b>„Antwort“</b> zurückübersetzen.</span></li>
            </ol>
            <div class="row between" style="margin:14px 0 6px"><b>Anweisung für die KI</b><button class="btn" id="copy-anw">Kopieren</button></div>
            <pre class="anweisung" id="anw">…</pre>
            <p class="muted small" style="margin-top:8px">Für Claude gibt es die Anweisung auch als Skill-Datei: <a href="/api/skill.zip">lokanon-pseudonyme.zip</a></p>
          </section>
          <section class="card" id="schluessel-card">
            <h3>Vorgang abschließen</h3>
            <p class="muted small" style="margin:4px 0 10px">Der Schlüssel (Platzhalter → Original) wird mit Ihrem Passwort verschlüsselt gespeichert. Ohne ihn lässt sich eine Antwort später nicht zurückübersetzen. Die Datei ist so schützenswert wie die Akte.</p>
            <div class="row"><input class="input" type="password" id="pw" placeholder="Passwort für den Schlüssel" style="max-width:260px" autocomplete="new-password"><button class="btn primary" id="abschliessen" disabled>Schlüssel speichern</button></div>
            <div id="schluessel-info" style="margin-top:10px">${z.schluessel_pfad ? `<div class="notice ok"><span>✓</span><span>Schlüssel gespeichert: <code>${esc(z.schluessel_pfad)}</code></span></div>` : ""}</div>
          </section>
        </div>
      </div>`;
    api("/anweisung").then((r) => { $("#anw").textContent = r.text; });
    $("#copy-anw").onclick = () => copy($("#anw").textContent);
    const sel = $("#anbieter"); sel.onchange = () => { $("#consumer-warn").hidden = !consumer(sel.value); };
    $("#geprueft").onchange = () => { $("#erzeugen").disabled = !$("#geprueft").checked; };
    $("#pw").oninput = () => { $("#abschliessen").disabled = !$("#pw").value; };
    $("#abschliessen").onclick = async () => {
      try { const r = await api("/vorgang/abschliessen", { json: { passwort: $("#pw").value } });
        $("#schluessel-info").innerHTML = `<div class="notice ok"><span>✓</span><span>Schlüssel gespeichert: <code>${esc(r.schluessel_pfad)}</code>. Der Vorgang ist abgeschlossen; die Antwort können Sie jederzeit zurückübersetzen.</span></div>`; $("#pw").value = ""; $("#abschliessen").disabled = true; toast("Vorgang abgeschlossen", "ok"); }
      catch (e) { toast(e.message, "danger"); }
    };
    if (z.ausgaben && z.ausgaben.length) renderErgebnis(z);
    $("#erzeugen").onclick = async () => {
      const btn = $("#erzeugen"); btn.disabled = true; btn.innerHTML = `<span class="spinner"></span> Erzeuge Dateien …`;
      const formate = [["pdf", "#f-pdf"], ["docx", "#f-docx"], ["xlsx", "#f-xlsx"]].filter(([, s]) => $(s).checked).map(([f]) => f);
      try { const r = await api("/vorgang/ausgabe", { json: { formate, anbieter: sel.value } }); S.vorgang = await api("/vorgang"); renderErgebnis(S.vorgang, r); toast("Dateien erzeugt", "ok"); }
      catch (e) { toast(e.message, "danger"); }
      btn.disabled = false; btn.textContent = "Dateien erneut erzeugen";
    };
  }
  function renderErgebnis(z) {
    const aus = z.ausgaben || [];
    const fehler = aus.some((a) => a.status === "fehler");
    $("#ergebnis").innerHTML = `
      <svg class="check" viewBox="0 0 60 60" aria-hidden="true"><circle cx="30" cy="30" r="26"/><path d="M18 31l8 8 16-17"/></svg>
      <h3 style="text-align:center;margin-bottom:12px">${fehler ? "Dateien erzeugt – bitte Hinweise beachten" : "Dateien erzeugt"}</h3>
      <div class="pathbox"><span title="${esc(z.ki_ordner)}">${esc(z.ki_ordner)}</span><button class="btn" id="open-ki">Ordner öffnen</button></div>
      <div style="margin-top:12px">${aus.map((a) => `<div class="result-file"><span class="st ${a.status}">${a.status === "ok" ? "✓" : "!"}</span><div style="min-width:0"><b>${esc(a.name)}</b><div class="muted small">${esc(a.dateien.join(", "))}</div>${a.hinweis ? `<div class="small" style="color:var(--${a.status === "fehler" ? "danger" : "warn"})">${esc(a.hinweis)}</div>` : ""}</div></div>`).join("")}</div>
      ${fehler ? `<div class="notice danger" style="margin-top:10px"><span>✕</span><span>Mindestens eine Datei enthält noch Originaltext. Diese Datei nicht hochladen. Begriff unter „Prüfen“ nachtragen und erneut erzeugen.</span></div>` : ""}
      <div class="row" style="margin-top:12px"><a class="btn" href="/api/vorgang/ki.zip">Als ZIP herunterladen</a><button class="btn ghost" id="open-basis2">Prüfbericht und Protokoll</button><button class="btn primary" id="weiter4">Weiter zu „Antwort“ →</button></div>`;
    $("#open-ki").onclick = () => oeffnen(z.ki_ordner);
    $("#open-basis2").onclick = () => oeffnen(z.basis);
    $("#weiter4").onclick = () => { S.schritt = 4; renderVorgang(); };
  }

  // ------------------------------------------------------------ Schritt 4: Antwort
  function renderSchritt4(body, z) {
    body.innerHTML = `<section class="card raised" style="max-width:900px">
      <h2>Antwort der KI zurückübersetzen</h2>
      <p class="muted" style="margin:4px 0 12px">Antwort einfügen. Platzhalter wie <span class="ph">[PERSON_1]</span> oder <span class="ph">[MANDANT]</span> werden durch die Originale ersetzt, auch wenn die KI sie leicht verändert hat.</p>
      <textarea class="input" id="antwort" rows="9" placeholder="Antwort hier einfügen …"></textarea>
      <div class="row" style="margin-top:10px"><button class="btn primary" id="zurueck-btn">Zurückübersetzen</button></div>
      <div id="zurueck-out" hidden style="margin-top:14px"><div class="row between"><b>Ergebnis</b><button class="btn" id="copy-out">Kopieren</button></div>
        <pre class="anweisung" id="out" style="max-height:none"></pre>
        <p class="muted small" style="margin-top:8px">Inhalt vor der Weiterverwendung prüfen. Die KI kann Fakten falsch wiedergegeben haben; die Rückübersetzung ersetzt nur die Platzhalter.</p></div>
    </section>`;
    $("#zurueck-btn").onclick = async () => {
      try { const r = await api("/zurueck", { json: { text: $("#antwort").value } }); $("#out").textContent = r.text; $("#zurueck-out").hidden = false; } catch (e) { toast(e.message, "danger"); }
    };
    $("#copy-out").onclick = () => copy($("#out").textContent);
  }

  // ------------------------------------------------------------ Zurückübersetzen (eigenständig)
  async function renderZurueck() {
    const [keys, offen] = await Promise.all([api("/schluessel"), api("/vorgang?kurz=1")]);
    view.innerHTML = `
      <div class="page-head"><div><h1>Antwort zurückübersetzen</h1><p class="sub">Für den offenen Vorgang oder für einen früheren Vorgang mit seiner Schlüsseldatei und dem Passwort.</p></div></div>
      <section class="card raised" style="max-width:900px">
        <div class="grid-2">
          <label class="field"><span>Schlüssel</span><select class="input" id="key-sel">${offen.id ? `<option value="">Offener Vorgang: ${esc(offen.name)}</option>` : ""}${keys.schluessel.map((k) => `<option value="${esc(k.pfad)}">${esc(k.name)}</option>`).join("")}</select>
            <span class="hint">Schlüsselordner: <code>${esc(keys.ordner)}</code></span></label>
          <label class="field" id="pw-field"><span>Passwort</span><input class="input" type="password" id="pw2" autocomplete="current-password"></label>
        </div>
        <textarea class="input" id="antwort" rows="9" placeholder="Antwort der KI hier einfügen …" style="margin-top:12px"></textarea>
        <div class="row" style="margin-top:10px"><button class="btn primary" id="zurueck-btn">Zurückübersetzen</button></div>
        <div id="zurueck-out" hidden style="margin-top:14px"><div class="row between"><b>Ergebnis</b><button class="btn" id="copy-out">Kopieren</button></div><pre class="anweisung" id="out" style="max-height:none"></pre></div>
      </section>`;
    const sel = $("#key-sel"); const sync = () => { $("#pw-field").hidden = !sel.value; }; sel.onchange = sync; sync();
    $("#zurueck-btn").onclick = async () => {
      try { const r = await api("/zurueck", { json: { text: $("#antwort").value, schluessel_pfad: sel.value, passwort: $("#pw2").value } }); $("#out").textContent = r.text; $("#zurueck-out").hidden = false; toast(`${r.platzhalter} Platzhalter aus „${r.vorgang}“`, "ok"); } catch (e) { toast(e.message, "danger"); }
    };
    $("#copy-out").onclick = () => copy($("#out").textContent);
  }

  // ------------------------------------------------------------ Einstellungen
  async function renderEinstellungen() {
    const cfg = await api("/einstellungen");
    const gruppen = cfg._gruppen || {};
    const aktiv = new Set(cfg.entities || []);
    view.innerHTML = `
      <div class="page-head"><div><h1>Einstellungen</h1><p class="sub">Was in Ihren Dokumenten stehen bleiben darf, wo Vorgänge und Schlüssel liegen, und was erkannt wird.</p></div></div>
      <div class="grid-2">
        <section class="card stack">
          <h2>Ihre Kanzlei</h2>
          <label class="field"><span>Nie ersetzen <span class="hint">– Kanzleiname, Mitarbeiter, eigene Telefonnummern und E-Mail-Adressen, eine je Zeile. Namensteile zählen mit.</span></span><textarea class="input" id="allow" rows="7">${esc((cfg.allow_list || []).join("\n"))}</textarea></label>
          <label class="field"><span>Immer ersetzen <span class="hint">– interne Projektnamen, Kundenkürzel</span></span><textarea class="input" id="deny" rows="4">${esc((cfg.deny_list || []).join("\n"))}</textarea></label>
        </section>
        <section class="card stack">
          <h2>Verhalten</h2>
          <label class="checkbox"><input type="checkbox" id="keep" ${cfg.keep_institutions ? "checked" : ""}><span><b>Gerichte, Behörden, Versicherer, Kliniken stehen lassen</b><br><span class="muted small">Diese Einrichtungen sind meist kein Personenbezug. Einzelne lassen sich beim Prüfen trotzdem ersetzen.</span></span></label>
          <label class="checkbox"><input type="checkbox" id="loc" ${cfg.mask_locations ? "checked" : ""}><span><b>Ortsnamen ohne Adresse ersetzen</b><br><span class="muted small">„Mülheim“ im Fließtext. Adressen und PLZ mit Ort werden immer ersetzt.</span></span></label>
          <div><div class="eyebrow" style="margin-bottom:6px">Datumsangaben</div><div class="radio-row" id="datum">${[["kontext", "nur mit Personenbezug (Geburt, Tod)"], ["alle", "jedes Datum"], ["keine", "keine"]].map(([v, l]) => `<label class="radio-chip ${cfg.datum_modus === v ? "on" : ""}"><input type="radio" name="datum" value="${v}" ${cfg.datum_modus === v ? "checked" : ""}>${l}</label>`).join("")}</div></div>
          <div><div class="eyebrow" style="margin-bottom:6px">Was erkannt wird</div><div class="stack" style="gap:6px">${Object.entries(gruppen).map(([g, ents]) => `<label class="checkbox"><input type="checkbox" data-grp="${esc(g)}" ${ents.some((e) => aktiv.has(e)) ? "checked" : ""}><span>${esc(g)}</span></label>`).join("")}</div></div>
          <h2 style="margin-top:8px">Ordner</h2>
          <label class="field"><span>Vorgänge <span class="hint">– hier landen hochgeladene Dateien, Kopien und Berichte</span></span><input class="input" id="vo" value="${esc(cfg.vorgaenge_ordner || cfg._vorgaenge_ordner_effektiv)}"></label>
          <label class="field"><span>Schlüsseldateien <span class="hint">– bitte außerhalb von OneDrive, Dropbox oder anderen Cloud-Ordnern</span></span><input class="input" id="so" value="${esc(cfg.schluessel_ordner || cfg._schluessel_ordner_effektiv)}"></label>
          <div class="row"><button class="btn primary" id="save">Speichern</button><button class="btn ghost" id="wizard">Einrichtung erneut starten</button></div>
        </section>
      </div>`;
    document.querySelectorAll("#datum .radio-chip").forEach((l) => l.onclick = () => { document.querySelectorAll("#datum .radio-chip").forEach((x) => x.classList.remove("on")); l.classList.add("on"); });
    $("#save").onclick = async () => {
      const entities = []; document.querySelectorAll("[data-grp]").forEach((cb) => { if (cb.checked) entities.push(...gruppen[cb.dataset.grp]); });
      const werte = { allow_list: $("#allow").value.split("\n").map((s) => s.trim()).filter(Boolean), deny_list: $("#deny").value.split("\n").map((s) => s.trim()).filter(Boolean),
        keep_institutions: $("#keep").checked, mask_locations: $("#loc").checked, datum_modus: $('input[name="datum"]:checked').value,
        vorgaenge_ordner: $("#vo").value.trim(), schluessel_ordner: $("#so").value.trim(), entities };
      try { await api("/einstellungen", { method: "PUT", json: { werte } }); toast("Gespeichert", "ok"); } catch (e) { toast(e.message, "danger"); }
    };
    $("#wizard").onclick = async () => { await api("/einstellungen", { method: "PUT", json: { werte: { eingerichtet: false } } }); location.hash = "#einrichten"; };
  }

  // ------------------------------------------------------------ Ersteinrichtung (3 Bildschirme)
  async function renderEinrichten() {
    const cfg = S.cfg || (await api("/einstellungen"));
    const e = S.einricht;
    const seite = S.einrichtSeite;
    const dots = `<div class="dots">${[1, 2, 3].map((n) => `<i class="${n <= seite ? "on" : ""}"></i>`).join("")}</div>`;
    let inner = "";
    if (seite === 1) inner = `${dots}<div class="eyebrow">Willkommen</div><h1 style="margin:4px 0 8px">Lokanon einrichten</h1>
      <p class="muted" style="margin-bottom:18px">Drei kurze Schritte. Lokanon muss wissen, was in Ihren Dokumenten stehen bleiben darf, weil es Ihre eigene Kanzlei sonst wie einen Mandanten behandelt. Es verlässt nichts diesen Rechner.</p>
      <div class="stack">
        <div><div class="eyebrow" style="margin-bottom:6px">Wofür nutzen Sie Lokanon?</div><div class="radio-row" id="profil">${[["kanzlei", "Anwaltskanzlei"], ["praxis", "Arztpraxis (Vorschau)"], ["allgemein", "Allgemein"]].map(([v, l]) => `<label class="radio-chip ${(e.profil || "kanzlei") === v ? "on" : ""}"><input type="radio" name="profil" value="${v}" ${(e.profil || "kanzlei") === v ? "checked" : ""}>${l}</label>`).join("")}</div></div>
        <label class="field"><span>Name Ihrer Kanzlei oder Praxis</span><input class="input" id="w-name" value="${esc(e.name || "")}" placeholder="z. B. Lehmkuhl & Partner Rechtsanwälte"></label>
        <label class="field"><span>Eigene Personen <span class="hint">– Anwälte, Mitarbeiter; eine je Zeile. „Annette Lehmkuhl“ erlaubt auch „Frau Lehmkuhl“.</span></span><textarea class="input" id="w-personen" rows="4">${esc(e.personen || "")}</textarea></label>
        <label class="field"><span>Eigene Kontaktdaten <span class="hint">– Telefon, Fax, E-Mail, Anschrift; eine je Zeile</span></span><textarea class="input" id="w-kontakt" rows="4">${esc(e.kontakt || "")}</textarea></label>
      </div>`;
    if (seite === 2) inner = `${dots}<div class="eyebrow">Schritt 2 von 3</div><h1 style="margin:4px 0 8px">Was soll ersetzt werden?</h1>
      <p class="muted" style="margin-bottom:18px">Die Vorgaben passen für die meisten Kanzleien. Beim Prüfen jedes Vorgangs können Sie einzelne Begriffe trotzdem ein- oder ausschalten.</p>
      <div class="stack">
        <label class="checkbox"><input type="checkbox" id="w-keep" ${e.keep !== false ? "checked" : ""}><span><b>Gerichte, Behörden, Versicherer, Kliniken stehen lassen</b><br><span class="muted small">Das Amtsgericht ist kein Personenbezug. Der Arbeitgeber eines Mandanten lässt sich beim Prüfen einzeln ersetzen.</span></span></label>
        <label class="checkbox"><input type="checkbox" id="w-loc" ${e.loc ? "checked" : ""}><span><b>Ortsnamen ohne Adresse ersetzen</b><br><span class="muted small">„in Essen“ im Fließtext. Adressen und PLZ mit Ort werden immer ersetzt. Bei kleinen Orten sinnvoll.</span></span></label>
        <div><div class="eyebrow" style="margin-bottom:6px">Datumsangaben</div><div class="radio-row" id="w-datum">${[["kontext", "nur mit Personenbezug (Geburt, Tod) – empfohlen"], ["alle", "jedes Datum ersetzen"], ["keine", "Daten stehen lassen"]].map(([v, l]) => `<label class="radio-chip ${(e.datum || "kontext") === v ? "on" : ""}"><input type="radio" name="w-datum" value="${v}" ${(e.datum || "kontext") === v ? "checked" : ""}>${l}</label>`).join("")}</div></div>
      </div>`;
    if (seite === 3) inner = `${dots}<div class="eyebrow">Schritt 3 von 3</div><h1 style="margin:4px 0 8px">Wo soll Lokanon ablegen?</h1>
      <p class="muted" style="margin-bottom:18px">Vorgänge enthalten Kopien Ihrer Dateien. Schlüsseldateien machen die Platzhalter rückübersetzbar und gehören nicht in die Cloud.</p>
      <div class="stack">
        <label class="field"><span>Ordner für Vorgänge</span><input class="input" id="w-vo" value="${esc(e.vo || cfg._vorgaenge_ordner_effektiv)}"></label>
        <label class="field"><span>Ordner für Schlüsseldateien <span class="hint">– außerhalb von OneDrive, Dropbox und ähnlichen</span></span><input class="input" id="w-so" value="${esc(e.so || cfg._schluessel_ordner_effektiv)}"></label>
        <div class="notice info"><span>ℹ</span><span>Bei „Aktenordner wählen“ entsteht stattdessen ein Unterordner „Lokanon“ direkt in der Akte.</span></div>
      </div>`;
    view.innerHTML = `<div class="wizard card raised" style="padding:28px 32px">${inner}
      <div class="row between" style="margin-top:22px"><button class="btn ghost" id="w-back" ${seite === 1 ? "hidden" : ""}>Zurück</button><span></span><button class="btn primary big" id="w-next">${seite === 3 ? "Einrichtung abschließen" : "Weiter"}</button></div></div>`;
    document.querySelectorAll(".radio-row").forEach((row) => row.querySelectorAll(".radio-chip").forEach((l) => l.onclick = () => { row.querySelectorAll(".radio-chip").forEach((x) => x.classList.remove("on")); l.classList.add("on"); }));
    const sammeln = () => {
      if (seite === 1) { e.profil = $('input[name="profil"]:checked').value; e.name = $("#w-name").value; e.personen = $("#w-personen").value; e.kontakt = $("#w-kontakt").value; }
      if (seite === 2) { e.keep = $("#w-keep").checked; e.loc = $("#w-loc").checked; e.datum = $('input[name="w-datum"]:checked').value; }
      if (seite === 3) { e.vo = $("#w-vo").value; e.so = $("#w-so").value; }
    };
    $("#w-back").onclick = () => { sammeln(); S.einrichtSeite--; renderEinrichten(); };
    $("#w-next").onclick = async () => {
      sammeln();
      if (seite < 3) { S.einrichtSeite++; renderEinrichten(); return; }
      const zeilen = (s) => (s || "").split("\n").map((x) => x.trim()).filter(Boolean);
      const alt = (cfg.allow_list || []).filter((a) => !["Lehmkuhl & Partner", "Annette Lehmkuhl", "0201 8945120", "kanzlei@lehmkuhl-partner.example"].includes(a));
      const allow = [...new Set([...alt, e.name, ...zeilen(e.personen), ...zeilen(e.kontakt)].map((s) => (s || "").trim()).filter(Boolean))];
      const werte = { profil: e.profil || "kanzlei", allow_list: allow, keep_institutions: e.keep !== false, mask_locations: !!e.loc, datum_modus: e.datum || "kontext",
        vorgaenge_ordner: e.vo || "", schluessel_ordner: e.so || "", eingerichtet: true };
      try { await api("/einstellungen", { method: "PUT", json: { werte } }); S.einrichtSeite = 1; S.einricht = {}; toast("Einrichtung gespeichert", "ok"); location.hash = "#start"; } catch (err) { toast(err.message, "danger"); }
    };
  }

  // ------------------------------------------------------------ Hilfe
  function renderHilfe() {
    view.innerHTML = `<div class="page-head"><div><h1>Anleitung</h1><p class="sub">Schritt für Schritt, mit Tarifvergleich, rechtlichem Rahmen und Checkliste. Druckbar als PDF.</p></div></div>
      <iframe class="help-frame" src="/anleitung/index.html" title="Anleitung"></iframe>`;
  }

  render();
})();
