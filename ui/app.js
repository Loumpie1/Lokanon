/* Lokanon – Oberfläche, Version 3: ein Bildschirm, drei Zustände (Ablegen → Prüfen → Fertig).
   Alles Weitere (Rückübersetzung, KI-Anweisung, Vorgangsordner) hängt an Schaltern in den Einstellungen. */
(() => {
  "use strict";
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const view = $("#view");
  const merke = (k, v) => { try { localStorage.setItem("lokanon." + k, JSON.stringify(v)); } catch {} };
  const gemerkt = (k, d) => { try { const v = localStorage.getItem("lokanon." + k); return v === null ? d : JSON.parse(v); } catch { return d; } };
  const S = { status: null, cfg: null, z: null, docIndex: 0, docMode: "markiert", filter: "alle", poll: null, pollStatus: null, laufText: "",
    docAn: gemerkt("docAn", true), stelle: null };
  const GRUPPEN_FARBE = { "Personen": "var(--g-person)", "Firmen und Einrichtungen": "var(--g-firma)", "Adressen und Kontakt": "var(--g-adresse)",
    "Nummern und Kennzeichen": "var(--g-nummer)", "Daten und Sonstiges": "var(--g-sonst)" };

  // ------------------------------------------------------------ API, Toasts, Dialoge
  async function api(path, opt = {}) {
    const init = { method: opt.method || (opt.json || opt.form ? "POST" : "GET") };
    if (opt.json) { init.headers = { "Content-Type": "application/json" }; init.body = JSON.stringify(opt.json); }
    if (opt.form) init.body = opt.form;
    const r = await fetch("/api" + path, init);
    const ct = r.headers.get("content-type") || "";
    const data = ct.includes("json") ? await r.json() : await r.text();
    if (!r.ok) throw new Error((data && data.fehler) || r.statusText);
    return data;
  }
  function toast(msg, kind = "") {
    const t = document.createElement("div"); t.className = "toast " + kind; t.textContent = msg;
    $("#toasts").appendChild(t); setTimeout(() => t.remove(), kind === "danger" ? 6500 : 3200);
  }
  function modal(html, { wide = false, full = false } = {}) {
    const root = $("#modal-root"); root.innerHTML = `<div class="modal ${wide ? "wide" : ""} ${full ? "full" : ""}" role="dialog" aria-modal="true">${html}</div>`;
    root.hidden = false;
    root.onclick = (e) => { if (e.target === root) closeModal(); };
    $$(".x", root).forEach((b) => (b.onclick = closeModal));
    return root.firstElementChild;
  }
  function closeModal() { const root = $("#modal-root"); root.hidden = true; root.innerHTML = ""; }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#modal-root").hidden) closeModal(); });
  const copy = async (text, ok = "Kopiert") => { try { await navigator.clipboard.writeText(text); toast(ok, "ok"); } catch { toast("Kopieren nicht möglich, bitte markieren und kopieren.", "danger"); } };
  const oeffnen = (pfad) => api("/system/oeffnen", { json: { pfad } }).catch((e) => toast(e.message, "danger"));
  const kb = (n) => (n > 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB");

  // ------------------------------------------------------------ Start und Zustand
  async function boot() {
    S.status = await api("/status");
    S.cfg = await api("/einstellungen");
    badge();
    $("#btn-einstellungen").onclick = () => einstellungenDialog();  // ohne Klick-Ereignis als Abschnitt
    $("#btn-hilfe").onclick = hilfeDialog;
    $("#btn-zurueck").onclick = zurueckDialog;
    $("#brand").onclick = (e) => { e.preventDefault(); if (S.z && (S.z.ergebnis || S.z.fortschritt.fertig)) neuStart(); };
    if (!S.status.eingerichtet) return renderWizard();
    await laden();
    direktlink();
  }
  // Direktlinks: #einstellungen, #einstellungen/erweitert, #vorstellung, #zurueck, #hilfe
  function direktlink() {
    const h = decodeURIComponent(location.hash.slice(1));
    if (h.startsWith("einstellungen")) einstellungenDialog(h.split("/")[1] || "");
    else if (h === "vorstellung") vorstellungDialog();
    else if (h === "zurueck" && (S.cfg.erweitert || {}).rueckuebersetzung) zurueckDialog();
    else if (h === "hilfe") hilfeDialog();
  }
  function badge() {
    const b = $("#local-badge"); const bereit = S.status.modelle_bereit;
    b.classList.toggle("laden", !bereit);
    $("#local-text").textContent = bereit ? "Läuft lokal auf diesem PC" : "Sprachmodelle werden geladen …";
    $("#btn-zurueck").hidden = !(S.cfg && S.cfg.erweitert && S.cfg.erweitert.rueckuebersetzung);
    if (!bereit && !S.pollStatus) S.pollStatus = setInterval(async () => { S.status = await api("/status"); if (S.status.modelle_bereit) { clearInterval(S.pollStatus); S.pollStatus = null; badge(); } }, 1500);
  }
  async function laden() { S.z = await api("/zustand"); render(); }
  function render() {
    const z = S.z; const f = z.fortschritt;
    if (f.laeuft) return renderLaeuft();
    if (z.ergebnis) return renderFertig();
    if (f.fertig) return renderPruefen();
    return renderAblegen();
  }
  async function neuStart() { S.z = await api("/leeren", { method: "POST" }); S.docIndex = 0; S.filter = "alle"; render(); }

  // ------------------------------------------------------------ Zustand 1: Ablegen
  function renderAblegen() {
    const z = S.z; const f = z.fortschritt;
    view.innerHTML = `
      <section class="ablegen">
        <h1>Dateien anonymisieren</h1>
        <p class="sub">Legen Sie Dateien ab oder wählen Sie den Ordner, in dem sie liegen. Lokanon zeigt, was es erkannt hat, Sie prüfen, dann entstehen Kopien ohne Namen. Alles auf diesem PC.</p>
        <div class="dropzone" id="drop" tabindex="0" role="button" aria-label="Dateien auswählen">
          <svg class="big-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/></svg>
          <b>Dateien hierher ziehen</b>
          <span>oder klicken und auswählen · PDF, Word, Excel, Text</span>
          <input type="file" id="fileinput" multiple accept=".pdf,.docx,.xlsx,.csv,.txt,.md" hidden>
        </div>
        <div class="or">oder</div>
        <div class="alt">
          <button class="btn big" id="btn-ordner">Ordner wählen</button>
          <button class="btn ghost" id="btn-text">Text einfügen</button>
        </div>
        ${f.fehler ? `<div class="notice danger" style="margin-top:16px;text-align:left"><div><b>Das hat nicht geklappt.</b> ${esc(f.fehler)}<div class="row" style="margin-top:8px"><button class="btn" id="btn-details">Details ansehen</button><span class="small">Die Dateien bleiben in der Liste, Sie können es erneut versuchen.</span></div></div></div>` : ""}
        ${z.dateien.length ? `<div class="filelist">${z.dateien.map((d) => `<div class="file"><span class="ext">${esc(d.name.split(".").pop())}</span><span class="name">${esc(d.name)}</span><span class="muted small">${kb(d.groesse)}</span><button class="iconbtn" data-del="${esc(d.name)}" title="Entfernen">✕</button></div>`).join("")}</div>
          <div class="row" style="justify-content:center;margin-top:14px"><button class="btn primary big" id="btn-start">Erkennen und prüfen</button></div>` : ""}
        <div class="facts">
          <div class="fact"><b>Nichts verlässt den Rechner</b><span>Erkennung, Texterkennung und Schwärzung laufen hier. Internet ist nicht nötig.</span></div>
          <div class="fact"><b>Sie entscheiden</b><span>Jede Person, jede Angabe hat einen Schalter. Platzhalter bekommen auf Wunsch eigene Namen wie „Mandant“.</span></div>
          <div class="fact"><b>Gleiche Datei, gleicher Name</b><span>Aus <code>Klage.docx</code> wird <code>Klage${esc(S.cfg.suffix || "_anonymisiert")}.docx</code>, aus einem PDF eine geschwärzte PDF.</span></div>
        </div>
      </section>`;
    const drop = $("#drop"), input = $("#fileinput");
    drop.onclick = () => input.click();
    drop.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } };
    input.onchange = () => hochladen(input.files);
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => hochladen(e.dataTransfer.files));
    $("#btn-ordner").onclick = ordnerWaehlen;
    $("#btn-text").onclick = textDialog;
    $$("[data-del]").forEach((b) => (b.onclick = async () => { S.z = await api("/datei-entfernen", { json: { name: b.dataset.del } }); render(); }));
    if ($("#btn-start")) $("#btn-start").onclick = () => analyseStarten();
    if ($("#btn-details")) $("#btn-details").onclick = protokollDialog;
  }
  async function hochladen(files) {
    if (!files || !files.length) return;
    const form = new FormData();
    for (const f of files) form.append("datei", f, f.name);
    try { await api("/dateien", { form }); await analyseStarten(); } catch (e) { toast(e.message, "danger"); }
  }
  async function ordnerWaehlen() {
    let pfad = "";
    try {
      const r = await api("/system/ordner-waehlen", { method: "POST" });
      pfad = r.pfad;
    } catch (e) {
      // Kein Systemdialog (z. B. im Browser-Fallback): Pfad eintippen lassen
      pfad = await pfadDialog();
    }
    if (!pfad) return;
    try { await api("/ordner", { json: { pfad } }); await analyseStarten(); } catch (e) { toast(e.message, "danger"); }
  }
  function pfadDialog() {
    return new Promise((resolve) => {
      const m = modal(`<div class="mhead"><h2>Ordner eintippen</h2><button class="x" aria-label="Schließen">✕</button></div>
        <p class="muted">Der Ordnerdialog steht hier nicht zur Verfügung. Bitte den Pfad des Ordners mit den Dateien eingeben.</p>
        <input class="input" id="pf-in" placeholder="z. B. C:\\Akten\\Mandant Müller" style="width:100%">
        <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn primary" id="pf-ok">Übernehmen</button></div>`);
      const fertig = (v) => { closeModal(); resolve(v); };
      $("#pf-ok", m).onclick = () => fertig($("#pf-in", m).value.trim());
      $("#pf-in", m).onkeydown = (e) => { if (e.key === "Enter") fertig($("#pf-in", m).value.trim()); };
      $$(".x", m).forEach((b) => (b.onclick = () => fertig("")));
      $("#pf-in", m).focus();
    });
  }
  function textDialog() {
    const m = modal(`<div class="mhead"><h2>Text einfügen</h2><button class="x" aria-label="Schließen">✕</button></div>
      <p class="muted small" style="margin-bottom:10px">Zum Beispiel eine E-Mail oder einen Absatz aus einem Schriftsatz. Der Text wird wie eine Datei behandelt.</p>
      <textarea class="input" id="txt" rows="10" placeholder="Text hier einfügen …"></textarea>
      <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn primary" id="txt-ok">Erkennen und prüfen</button></div>`);
    $("#txt", m).focus();
    $("#txt-ok", m).onclick = async () => { try { await api("/text", { json: { text: $("#txt", m).value } }); closeModal(); await analyseStarten(); } catch (e) { toast(e.message, "danger"); } };
  }
  async function analyseStarten(begriffe = []) {
    try { await api("/analyse", { json: { begriffe } }); S.docIndex = 0; await laden(); pollen(); } catch (e) { toast(e.message, "danger"); }
  }
  function pollen() {
    clearInterval(S.poll);
    S.poll = setInterval(async () => {
      try {
        const f = await api("/fortschritt");
        const bar = $("#pbar");
        if (bar) { bar.classList.toggle("indeterminate", f.prozent < 5); bar.firstElementChild.style.width = f.prozent + "%"; $("#p-schritt").textContent = f.schritt || "…"; $("#p-datei").textContent = f.datei || " "; }
        if (!f.laeuft) { clearInterval(S.poll); if (f.fehler) toast(f.fehler, "danger"); await laden(); }
      } catch (e) { clearInterval(S.poll); toast(e.message, "danger"); }
    }, 500);
  }
  function renderLaeuft() {
    const f = S.z.fortschritt; const anonym = f.fertig && !S.z.ergebnis && f.schritt === "Anonymisiere";
    view.innerHTML = `<section class="progress-panel">
      <div class="eyebrow">${anonym ? "Dateien werden erzeugt" : "Lokanon liest und erkennt"}</div>
      <h2 id="p-schritt">${esc(f.schritt || "Modelle laden …")}</h2>
      <p class="muted" id="p-datei">${esc(f.datei || " ")}</p>
      <div class="bar ${f.prozent < 5 ? "indeterminate" : ""}" id="pbar"><i style="width:${f.prozent}%"></i></div>
      <p class="muted small">${S.status.modelle_bereit ? "Gescannte Seiten brauchen etwas länger (Texterkennung)." : "Beim ersten Start werden die Sprachmodelle geladen, das dauert ein bis zwei Minuten."}</p>
    </section>`;
    pollen();
  }

  // ------------------------------------------------------------ Zustand 2: Prüfen
  function renderPruefen() {
    const z = S.z; const ids = z.identitaeten;
    const ersetzt = ids.filter((i) => i.aktiv).length, unsicher = ids.filter((i) => i.unsicher && i.aktiv).length;
    const gruppen = [...new Set(ids.map((i) => i.gruppe))];
    // Neu zeichnen ohne Springen: Fensterposition und Lage im Dokument merken
    const alt = $("#docview"); const docTop = alt ? alt.scrollTop : 0; const winTop = window.scrollY;
    const fehler = z.fortschritt.fehler;
    view.innerHTML = `
      <div class="pruefen ${S.docAn ? "" : "ohne-doc"}" id="pruefen">
        <section class="liste-sp">
          <div class="summary"><h1>${ids.length} ${ids.length === 1 ? "Angabe" : "Angaben"} gefunden</h1><span class="muted">${ersetzt} werden ersetzt · ${z.dateien.length} ${z.dateien.length === 1 ? "Datei" : "Dateien"}</span>
            <button class="btn ghost doc-schalter" id="btn-doc" aria-pressed="${S.docAn}">${S.docAn ? "Dokument ausblenden" : "Dokument einblenden"}</button></div>
          ${fehler ? `<div class="notice danger"><div><b>Das Anonymisieren hat nicht geklappt.</b> ${esc(fehler)} <button class="linkbtn" id="btn-details">Details</button></div></div>` : ""}
          ${unsicher ? `<div class="notice warn unsure" id="unsure" title="Nur unsichere anzeigen"><div><b>${unsicher} ${unsicher === 1 ? "Angabe" : "Angaben"} bitte ansehen.</b> Lokanon ersetzt im Zweifel. Was kein Personenbezug ist, schalten Sie aus.</div></div>` : `<div class="notice ok"><div><b>Alles eindeutig.</b> Prüfen Sie die Liste${S.docAn ? " und das Dokument rechts" : ""}, dann anonymisieren.</div></div>`}
          <p class="muted small tipp">Tipp: Ein Klick auf eine Karte zeigt die Stelle im Dokument, ein Klick auf eine Markierung im Dokument zeigt die Karte.</p>
          <div class="toolbar" style="margin-top:12px">
            <input class="input" id="nachtrag" placeholder="Fehlt etwas? Begriff eintragen, mehrere mit Komma">
            <button class="btn" id="btn-nachtrag">Nachtragen</button>
          </div>
          <label class="checkbox small nachtrag-immer"><input type="checkbox" id="nachtrag-immer"><span>künftig in allen Dokumenten suchen <span class="muted">(wird in Ihren Einstellungen gespeichert)</span></span></label>
          <div class="filter" id="filter">${["alle", ...gruppen, "unsicher"].map((g) => `<button class="${S.filter === g ? "on" : ""}" data-f="${esc(g)}">${g === "alle" ? "Alle" : g === "unsicher" ? "Bitte ansehen" : esc(g)}</button>`).join("")}</div>
          <div id="liste"></div>
        </section>
        <aside class="docpanel" id="docpanel" ${S.docAn ? "" : "hidden"}></aside>
      </div>
      <div class="actionbar"><div class="inner">
        <span class="hint">${esc(z.ordner ? "Die anonymisierten Dateien kommen neben die Originale in " + z.ordner : "Die anonymisierten Dateien kommen nach " + z.ausgabe_ordner)}</span>
        <button class="btn ghost" id="btn-neu">Neue Dateien</button>
        <button class="btn primary big" id="btn-anon">Geprüft, jetzt anonymisieren</button>
      </div></div>`;
    renderListe();
    renderDocPanel();
    const dv = $("#docview"); if (dv) dv.scrollTop = docTop;
    window.scrollTo(0, winTop);
    $("#btn-doc").onclick = () => docSchalten(!S.docAn);
    if ($("#btn-details")) $("#btn-details").onclick = protokollDialog;
    $$("#filter button").forEach((b) => (b.onclick = () => { S.filter = b.dataset.f; renderPruefen(); }));
    if ($("#unsure")) $("#unsure").onclick = () => { S.filter = "unsicher"; renderPruefen(); };
    $("#btn-nachtrag").onclick = async () => {
      const t = $("#nachtrag").value.split(",").map((s) => s.trim()).filter(Boolean);
      if (!t.length) return;
      if ($("#nachtrag-immer").checked) { try { await api("/lernen", { json: { art: "immer_ersetzen", begriffe: t } }); } catch (e) { toast(e.message, "danger"); return; } }
      analyseStarten(t);
    };
    $("#nachtrag").onkeydown = (e) => { if (e.key === "Enter") $("#btn-nachtrag").click(); };
    $("#btn-neu").onclick = () => bestaetigen("Neue Dateien ablegen? Die aktuelle Prüfung wird verworfen.", neuStart);
    $("#btn-anon").onclick = anonymisieren;
  }
  function docSchalten(an) {
    S.docAn = an; merke("docAn", an);
    $("#pruefen").classList.toggle("ohne-doc", !an);
    $("#docpanel").hidden = !an;
    const b = $("#btn-doc"); b.textContent = an ? "Dokument ausblenden" : "Dokument einblenden"; b.setAttribute("aria-pressed", an);
    if (an) renderDocPanel();
  }
  // Dokumentbereich: Ansicht, Dateireiter, Text. Wird ohne die Kartenliste neu gezeichnet.
  function renderDocPanel() {
    const p = $("#docpanel"); if (!p || !S.docAn) return;
    const z = S.z; const d = z.dokumente[S.docIndex];
    p.innerHTML = `
      <div class="dockopf"><b>Dokument</b><div class="filter" style="margin:0"><button id="m-orig" class="${S.docMode === "markiert" ? "on" : ""}">Original mit Markierungen</button><button id="m-anon" class="${S.docMode === "anonym" ? "on" : ""}">Anonymisiert</button></div>
        <button class="iconbtn" id="doc-zu" title="Dokument ausblenden" aria-label="Dokument ausblenden">✕</button></div>
      ${z.dokumente.length > 1 ? `<div class="doctabs" id="doctabs">${z.dokumente.map((x, i) => `<button class="${i === S.docIndex ? "on" : ""}" data-i="${i}" title="${esc(x.name)}">${esc(x.name)}</button>`).join("")}</div>`
        : `<div class="docname" title="${esc(d ? d.name : "")}">${esc(d ? d.name : "")}</div>`}
      <div class="docview" id="docview" tabindex="0"></div>
      <div class="legend"><span><i style="background:var(--mark-person)"></i>Person</span><span><i style="background:var(--mark-firma)"></i>Firma</span><span><i style="background:var(--mark-ort)"></i>Adresse/Ort</span><span><i style="background:var(--mark-nummer)"></i>Nummer</span><span><i style="border:1px dashed var(--muted)"></i>bleibt stehen</span></div>`;
    const dv = $("#docview");
    if (d) { if (S.docMode === "markiert") dv.innerHTML = d.markiert_html; else dv.textContent = d.anonym; }
    $("#m-orig").onclick = () => { S.docMode = "markiert"; renderDocPanel(); };
    $("#m-anon").onclick = () => { S.docMode = "anonym"; renderDocPanel(); };
    $("#doc-zu").onclick = () => docSchalten(false);
    $$("#doctabs button").forEach((b) => (b.onclick = () => { S.docIndex = +b.dataset.i; S.stelle = null; renderDocPanel(); }));
    // Markierung im Dokument → zugehörige Karte
    dv.onclick = (e) => { const m = e.target.closest("[data-ph]"); if (m) zeigeKarte(m.dataset.ph); };
    if (S.stelle) markiereStelle(false);
  }
  // Alle Vorkommen einer Identität über alle Dokumente: [[Dokument, n-tes Vorkommen im Dokument], …]
  function vorkommen(ph) {
    const out = [];
    S.z.dokumente.forEach((d, i) => {
      const n = d.markiert_html.split(`data-ph="${esc(ph)}"`).length - 1;
      for (let k = 0; k < n; k++) out.push([i, k]);
    });
    return out;
  }
  // Karte → Stelle: erster Klick zeigt das erste Vorkommen, jeder weitere das nächste (auch in anderen Dateien)
  function zeigeStelle(ph) {
    const occ = vorkommen(ph);
    if (!occ.length) { toast("Diese Angabe steht in keinem gelesenen Text."); return; }
    const nr = S.stelle && S.stelle.ph === ph ? (S.stelle.nr + 1) % occ.length : 0;
    const [di] = occ[nr];
    S.stelle = { ph, nr, gesamt: occ.length, k: occ[nr][1] };
    if (!S.docAn) docSchalten(true);
    if (S.docMode !== "markiert" || S.docIndex !== di) { S.docMode = "markiert"; S.docIndex = di; renderDocPanel(); }
    else markiereStelle(true);
    // Schmales Fenster: Das Dokument steht unter der Liste, also dorthin scrollen
    const p = $("#docpanel"); if (getComputedStyle(p).position !== "sticky") p.scrollIntoView({ block: "start", behavior: "smooth" });
    $$(".ident").forEach((el) => el.classList.toggle("gewaehlt", el.dataset.ph === ph));
    const z = $(`.ident[data-ph="${CSS.escape(ph)}"] .stelle-nr`);
    if (z) z.textContent = `Stelle ${nr + 1} von ${occ.length}`;
  }
  function markiereStelle(weich) {
    const dv = $("#docview"); if (!dv || !S.stelle) return;
    $$("[data-ph].aktuell, [data-ph].mit", dv).forEach((m) => m.classList.remove("aktuell", "mit"));
    const alle = $$(`[data-ph="${CSS.escape(S.stelle.ph)}"]`, dv);
    alle.forEach((m) => m.classList.add("mit"));
    const m = alle[S.stelle.k]; if (!m) return;
    m.classList.add("aktuell");
    const ziel = m.offsetTop - dv.clientHeight / 2 + m.offsetHeight / 2;
    dv.scrollTo({ top: Math.max(0, ziel), behavior: weich ? "smooth" : "auto" });
  }
  // Stelle → Karte: Filter notfalls aufheben, Karte in den sichtbaren Bereich holen und kurz hervorheben
  function zeigeKarte(ph) {
    let el = $(`.ident[data-ph="${CSS.escape(ph)}"]`);
    if (!el && S.filter !== "alle") { S.filter = "alle"; renderPruefen(); el = $(`.ident[data-ph="${CSS.escape(ph)}"]`); }
    if (!el) return;
    $$(".ident").forEach((x) => x.classList.toggle("gewaehlt", x === el));
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    el.classList.remove("blitz"); void el.offsetWidth; el.classList.add("blitz");
  }
  function renderListe() {
    const z = S.z; let ids = z.identitaeten;
    if (S.filter === "unsicher") ids = ids.filter((i) => i.unsicher); else if (S.filter !== "alle") ids = ids.filter((i) => i.gruppe === S.filter);
    const liste = $("#liste");
    if (!ids.length) { liste.innerHTML = `<p class="muted" style="margin-top:14px">Nichts in dieser Auswahl.</p>`; return; }
    const gruppen = [...new Set(ids.map((i) => i.gruppe))];
    let n = 0;
    liste.innerHTML = gruppen.map((g) => {
      const items = ids.filter((i) => i.gruppe === g);
      return `<div class="group-title"><span class="dot" style="background:${GRUPPEN_FARBE[g] || "var(--line-2)"}"></span>${esc(g)}<span class="count">· ${items.filter((i) => i.aktiv).length} von ${items.length} werden ersetzt</span></div>
        <div class="cards">${items.map((i) => karte(i, n++)).join("")}</div>`;
    }).join("");
    // Verhalten
    $$(".ident", liste).forEach((el) => {
      const ph = el.dataset.ph;
      $(".sw", el).onchange = (e) => identitaet({ ph, aktiv: e.target.checked });
      const phb = $(".phbtn", el); if (phb) phb.onclick = () => bezeichnungEdit(el, ph);
      $$(".sugg button", el).forEach((b) => (b.onclick = () => identitaet({ ph, bezeichnung: b.dataset.v })));
      $$(".frage button", el).forEach((b) => (b.onclick = () => identitaet({ ph, zuordnen: { text: b.dataset.text, ph: b.dataset.ziel } })));
      const sel = $("select.zu", el); if (sel) sel.onchange = () => { if (sel.value) identitaet({ ph, gehoert_zu: sel.value }); };
      const tr = $("select.tr", el); if (tr) tr.onchange = () => { if (tr.value) identitaet({ ph, trennen: tr.value }); };
      const lb = $(".lern", el); if (lb) lb.onclick = () => lernen(ph);
      $(".stelle", el).onclick = () => zeigeStelle(ph);
      el.onclick = (e) => { if (!e.target.closest("input, select, button, label, .phbtn, .phedit, a")) zeigeStelle(ph); };
    });
    if (S.stelle) {
      const el = $(`.ident[data-ph="${CSS.escape(S.stelle.ph)}"]`);
      if (el) { el.classList.add("gewaehlt"); $(".stelle-nr", el).textContent = `Stelle ${S.stelle.nr + 1} von ${S.stelle.gesamt}`; }
    }
  }
  function karte(i, n) {
    const andere = S.z.identitaeten.filter((o) => o.ph !== i.ph && o.gruppe === i.gruppe);
    const varianten = i.varianten.filter((v) => v !== i.name);
    return `<div class="ident ${i.aktiv ? "" : "aus"}" data-ph="${esc(i.ph)}" style="--g:${GRUPPEN_FARBE[i.gruppe] || "var(--line-2)"};--i:${n}">
      <div class="head">
        <div class="name">${esc(i.name)}${varianten.length ? `<small>auch: ${varianten.map(esc).join(" · ")}</small>` : ""}</div>
        <div class="swlabel"><label class="switch"><input type="checkbox" class="sw" ${i.aktiv ? "checked" : ""} aria-label="${esc(i.name)} ersetzen"><span class="track"></span></label><span>${i.aktiv ? "wird ersetzt" : "bleibt stehen"}</span></div>
      </div>
      <div class="phrow"><span class="arrow">wird zu</span>
        ${i.aktiv ? `<span class="phbtn" title="Klicken und eigenen Namen vergeben">${esc(i.anzeige)}</span>
        ${i.vorschlaege.length && !i.bezeichnung ? `<span class="sugg">${i.vorschlaege.slice(0, 4).map((v) => `<button data-v="${esc(v)}">${esc(v)}</button>`).join("")}</span>` : ""}
        ${i.bezeichnung ? `<button class="linkbtn sugg-reset" data-v="">Standard</button>` : ""}` : `<span class="muted small">bleibt im Text stehen</span>`}
      </div>
      <div class="meta">${esc(i.typ)} · ${i.anzahl}× in ${i.dateien.length} ${i.dateien.length === 1 ? "Datei" : "Dateien"} · ${esc(i.sicherheit)}${i.belege.length ? " · erkannt über " + esc(i.belege.join(", ")) : ""}</div>
      <div class="stellezeile"><button class="linkbtn stelle" title="Im Dokument zeigen; erneut klicken für die nächste Stelle">Im Dokument zeigen</button><span class="stelle-nr muted small"></span></div>
      <div class="snip">${i.beispiel}</div>
      ${i.gruende.length ? `<div class="warnline">Bitte ansehen: ${esc(i.gruende.join("; "))}</div>` : ""}
      ${!i.aktiv ? (i.gelernt ? `<div class="lernzeile muted small">Steht künftig immer · änderbar unter Einstellungen → Gelernte Begriffe</div>`
        : `<div class="lernzeile"><button class="linkbtn lern">Künftig immer stehen lassen</button><span class="muted small">sonst nur in diesem Durchlauf</span></div>`) : ""}
      ${i.fragen.map((f) => `<div class="frage"><span>„${esc(f.text)}“ allein: wer ist gemeint?</span>${f.kandidaten.map((k) => `<button data-text="${esc(f.text)}" data-ziel="${esc(k.ph)}">${esc(k.name)}</button>`).join("")}</div>`).join("")}
      <div class="actions">
        ${andere.length ? `<label>gehört zu <select class="mini zu"><option value="">…</option>${andere.map((o) => `<option value="${esc(o.ph)}">${esc(o.name)}</option>`).join("")}</select></label>` : ""}
        ${i.varianten.length > 1 ? `<label>trennen <select class="mini tr"><option value="">…</option>${i.varianten.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("")}</select></label>` : ""}
      </div>
    </div>`;
  }
  function bezeichnungEdit(el, ph) {
    const row = $(".phrow", el); const i = S.z.identitaeten.find((x) => x.ph === ph);
    row.innerHTML = `<span class="arrow">wird zu</span><span class="phedit">[<input id="bez" value="${esc(i.bezeichnung || "")}" placeholder="${esc(i.ph)}" maxlength="40">]</span><button class="btn" id="bez-ok" style="padding:4px 10px">Übernehmen</button><button class="linkbtn" id="bez-x">Abbrechen</button>`;
    const inp = $("#bez", row); inp.focus(); inp.select();
    const ok = () => identitaet({ ph, bezeichnung: inp.value });
    $("#bez-ok", row).onclick = ok; inp.onkeydown = (e) => { if (e.key === "Enter") ok(); if (e.key === "Escape") renderPruefen(); };
    $("#bez-x", row).onclick = renderPruefen;
  }
  async function lernen(ph) {
    const i = S.z.identitaeten.find((x) => x.ph === ph); if (!i) return;
    try { S.z = await api("/lernen", { json: { art: "stehen_lassen", begriffe: i.varianten } }); renderPruefen(); toast("Wird künftig nicht mehr vorgeschlagen", "ok"); }
    catch (e) { toast(e.message, "danger"); }
  }
  async function identitaet(body) {
    try { S.z = await api("/identitaet", { json: body }); renderPruefen(); } catch (e) { toast(e.message, "danger"); }
  }
  document.addEventListener("click", (e) => { const b = e.target.closest(".sugg-reset"); if (b) identitaet({ ph: b.closest(".ident").dataset.ph, bezeichnung: "" }); });
  function bestaetigen(text, fn) {
    const m = modal(`<p style="margin-bottom:16px">${esc(text)}</p><div class="row" style="justify-content:flex-end"><button class="btn x">Abbrechen</button><button class="btn primary" id="ja">Ja</button></div>`);
    $("#ja", m).onclick = () => { closeModal(); fn(); };
  }
  async function anonymisieren() {
    try { await api("/anonymisieren", { method: "POST" }); await laden(); } catch (e) { toast(e.message, "danger"); }
  }

  // ------------------------------------------------------------ Zustand 3: Fertig
  function renderFertig() {
    const z = S.z; const r = z.ergebnis; const ok = r.dateien.filter((d) => d.status === "ok").length;
    const n = r.dateien.length, fehl = n - ok;
    const erw = z.erweitert || {};
    const dateiZeile = (d) => d.status === "ok"
      ? `<div class="result-file"><span class="st ok">✓</span><div style="flex:1;min-width:0"><b>${esc(d.ausgabe)}</b>${d.textfassung ? ` <span class="muted small">+ ${esc(d.textfassung)}</span>` : ""}<div class="muted small">aus ${esc(d.name)} · ${d.ersetzt} Stellen ersetzt</div></div></div>`
      : `<div class="result-file fehl"><span class="st fehler">!</span><div style="flex:1;min-width:0"><b>${esc(d.name)}</b>: keine Kopie erzeugt
          <div class="small">${esc(d.hinweis)}</div>
          ${d.funde && d.funde.length ? `<ul class="funde">${d.funde.map((f) => `<li><b>„${esc(f.text)}“</b> ${esc(f.ort)}</li>`).join("")}</ul>` : ""}
          ${d.rat ? `<div class="rat"><b>Was Sie tun können:</b> ${esc(d.rat)}</div>` : ""}
          ${d.ersatz ? `<div class="small ersatz">Stattdessen erzeugt: <b>${esc(d.textfassung)}</b> (geprüfte Textfassung ohne Layout)</div>` : ""}
        </div></div>`;
    view.innerHTML = `<section class="fertig">
      ${fehl ? `<svg class="warnsym" viewBox="0 0 60 60" aria-hidden="true"><path d="M30 6 56 52H4Z"/><path d="M30 24v13M30 44v.5"/></svg>`
        : `<svg class="check" viewBox="0 0 60 60" aria-hidden="true"><circle cx="30" cy="30" r="26"/><path d="M18 31l8 8 16-17"/></svg>`}
      <h1 style="text-align:center">${ok} von ${n} ${n === 1 ? "Datei" : "Dateien"} anonymisiert</h1>
      <p class="muted" style="text-align:center;margin:6px 0 20px">${!fehl ? "Alle Kopien sind geprüft und ohne Personenbezug." : `Bei ${fehl === 1 ? "einer Datei" : fehl + " Dateien"} hat es nicht geklappt. Unten steht, woran es lag und was Sie tun können.`}</p>
      <div class="card raised stack">
        <div class="row between"><div class="pathbox" style="flex:1"><span title="${esc(r.ordner)}">${esc(r.ordner)}</span></div><button class="btn" id="btn-open">Ordner öffnen</button></div>
        <div>${r.dateien.filter((d) => d.status !== "ok").map(dateiZeile).join("")}${r.dateien.filter((d) => d.status === "ok").map(dateiZeile).join("")}</div>
        ${(() => { const h = r.hinweise.filter((t) => !r.dateien.some((d) => t.startsWith(d.name + ":"))); return h.length ? `<div class="notice warn"><div>${h.map(esc).join("<br>")}</div></div>` : ""; })()}
        ${r.schluessel_pfad ? `<div class="notice info small"><div>Schlüssel für die Rückübersetzung gespeichert: <code>${esc(r.schluessel_pfad)}</code></div></div>` : ""}
      </div>
      <div class="row" style="justify-content:center;margin-top:22px;gap:10px">
        <button class="btn ${fehl ? "primary big" : ""}" id="btn-pruefen">Zurück zum Prüfen</button>
        <button class="btn ghost" id="btn-details">Protokoll</button>
        ${erw.ki_anweisung ? `<button class="btn" id="btn-anw">KI-Anweisung kopieren</button>` : ""}
        ${erw.rueckuebersetzung ? `<button class="btn" id="btn-zk">Antwort zurückübersetzen</button>` : ""}
        <button class="btn ${fehl ? "" : "primary big"}" id="btn-neu">Neue Dateien</button>
      </div>
    </section>`;
    $("#btn-open").onclick = () => oeffnen(r.ordner);
    $("#btn-neu").onclick = neuStart;
    $("#btn-pruefen").onclick = async () => { try { S.z = await api("/zurueck-zum-pruefen", { method: "POST" }); render(); } catch (e) { toast(e.message, "danger"); } };
    $("#btn-details").onclick = protokollDialog;
    if ($("#btn-anw")) $("#btn-anw").onclick = anweisungDialog;
    if ($("#btn-zk")) $("#btn-zk").onclick = zurueckDialog;
  }

  // ------------------------------------------------------------ Protokoll (ohne Klartext)
  async function protokollDialog() {
    let p;
    try { p = await api("/protokoll"); } catch (e) { toast(e.message, "danger"); return; }
    const zeilen = p.eintraege.map((e) => `${e.zeit} [${e.stufe}] ${e.text}`).join("\n");
    const m = modal(`<div class="mhead"><h2>Protokoll des letzten Durchlaufs</h2><button class="x" aria-label="Schließen">✕</button></div>
      <p class="muted small" style="margin-bottom:10px">Ohne Klartext: Namen und andere erkannte Angaben stehen hier als Platzhalter, Dateien als Nummer. Sie können das Protokoll daher weitergeben, wenn Sie Hilfe brauchen.</p>
      ${p.eintraege.length ? `<div class="protokoll">${p.eintraege.map((e) => `<div class="pz ${esc(e.stufe)}"><span class="zeit">${esc(e.zeit)}</span><span class="stufe">${e.stufe === "fehler" ? "Fehler" : e.stufe === "warnung" ? "Hinweis" : "Info"}</span><span class="t">${esc(e.text)}</span></div>`).join("")}</div>`
        : `<p class="muted">Noch keine Einträge in dieser Sitzung.</p>`}
      <div class="row between" style="margin-top:12px"><span class="muted small">Ältere Protokolle: <code>${esc(p.ordner)}</code></span>
        <div class="row"><button class="btn" id="pr-ordner">Ordner öffnen</button><button class="btn primary" id="pr-cp" ${zeilen ? "" : "disabled"}>Kopieren</button></div></div>`, { wide: true });
    $("#pr-ordner", m).onclick = () => oeffnen(p.ordner);
    $("#pr-cp", m).onclick = () => copy(zeilen, "Protokoll kopiert");
  }

  // ------------------------------------------------------------ Erweitert: KI-Anweisung, Rückübersetzung
  async function anweisungDialog() {
    const a = await api("/anweisung");
    const m = modal(`<div class="mhead"><h2>Anweisung für ChatGPT oder Claude</h2><button class="x" aria-label="Schließen">✕</button></div>
      <p class="muted small" style="margin-bottom:10px">Einmal als Projekt-Anweisung einfügen. Die KI lässt die Platzhalter dann stehen.</p>
      <pre class="anweisung">${esc(a.text)}</pre>
      <div class="row" style="justify-content:flex-end;margin-top:12px;gap:8px"><a class="btn" href="/api/skill.zip">Claude-Skill laden</a><button class="btn primary" id="cp">Kopieren</button></div>`, { wide: true });
    $("#cp", m).onclick = () => copy(a.text, "Anweisung kopiert");
  }
  async function zurueckDialog() {
    let keys = { schluessel: [], aktuell: "" };
    try { keys = await api("/schluessel"); } catch {}
    const m = modal(`<div class="mhead"><h2>Antwort zurückübersetzen</h2><button class="x" aria-label="Schließen">✕</button></div>
      <div class="stack">
        <label class="field"><span class="small muted">Schlüssel</span><select class="input" id="zk-key"><option value="">Aktueller Durchlauf</option>${keys.schluessel.map((k) => `<option value="${esc(k.pfad)}" ${k.pfad === keys.aktuell ? "selected" : ""}>${esc(k.name)}</option>`).join("")}</select></label>
        <textarea class="input" id="zk-in" rows="8" placeholder="Antwort der KI hier einfügen …"></textarea>
        <div class="row" style="justify-content:flex-end"><button class="btn primary" id="zk-go">Zurückübersetzen</button></div>
        <textarea class="input" id="zk-out" rows="8" readonly placeholder="Ergebnis"></textarea>
        <div class="row" style="justify-content:flex-end"><button class="btn" id="zk-cp">Kopieren</button></div>
      </div>`, { wide: true });
    $("#zk-go", m).onclick = async () => {
      try { const r = await api("/zurueck", { json: { text: $("#zk-in", m).value, schluessel_pfad: $("#zk-key", m).value } }); $("#zk-out", m).value = r.text; toast(r.platzhalter ? `${r.platzhalter} Platzhalter zurückübersetzt (Schlüssel: ${r.quelle})` : `Keine Platzhalter gefunden (Schlüssel: ${r.quelle})`, r.platzhalter ? "ok" : "danger"); }
      catch (e) { toast(e.message, "danger"); }
    };
    $("#zk-cp", m).onclick = () => copy($("#zk-out", m).value);
  }

  // ------------------------------------------------------------ Einstellungen
  async function einstellungenDialog(abschnitt = "") {
    S.cfg = await api("/einstellungen");
    const c = S.cfg; const erw = c.erweitert || {};
    const grp = c._gruppen || {};
    const m = modal(`<div class="mhead"><h2>Einstellungen</h2><button class="x" aria-label="Schließen">✕</button></div>
      <div class="settings">
        <div class="sect"><h3>Ihre Kanzlei</h3><p class="desc">Diese Namen werden nie ersetzt: Kanzleiname, Mitarbeitende, eigene Telefonnummern und E-Mail-Adressen. Eine Angabe je Zeile, Namensteile zählen mit.</p>
          <textarea class="input" id="s-allow" rows="5">${esc((c.allow_list || []).join("\n"))}</textarea>
          <label class="lbl">Immer ersetzen <span class="muted small">(interne Kürzel, Projektnamen)</span></label>
          <textarea class="input" id="s-deny" rows="2">${esc((c.deny_list || []).join("\n"))}</textarea></div>
        <div class="sect" id="s-gelernt"><h3>Gelernte Begriffe</h3><p class="desc">Was Sie beim Prüfen mit „Künftig immer stehen lassen“ oder „künftig in allen Dokumenten suchen“ festgelegt haben. Gespeichert nur auf diesem PC.</p>
          <div id="s-lern"></div></div>
        <div class="sect"><h3>Erkennung</h3>
          <label class="checkbox"><input type="checkbox" id="s-inst" ${c.keep_institutions ? "checked" : ""}><span><b>Gerichte, Behörden, Versicherer, Kliniken stehen lassen</b><br><span class="muted small">Meist kein Personenbezug; einzelne lassen sich beim Prüfen trotzdem ersetzen.</span></span></label>
          <label class="checkbox"><input type="checkbox" id="s-orte" ${c.mask_locations ? "checked" : ""}><span><b>Ortsnamen ohne Adresse ersetzen</b><br><span class="muted small">„Mülheim“ im Fließtext. Adressen und PLZ mit Ort werden immer ersetzt.</span></span></label>
          <div class="field"><label class="lbl">Datumsangaben</label><div class="radio-row" id="s-datum">${[["kontext", "nur mit Personenbezug (Geburt, Tod)"], ["alle", "jedes Datum"], ["keine", "keine"]].map(([v, t]) => `<label class="radio-chip ${c.datum_modus === v ? "on" : ""}"><input type="radio" name="datum" value="${v}" ${c.datum_modus === v ? "checked" : ""}>${t}</label>`).join("")}</div></div>
          <div class="field"><label class="lbl">Was erkannt wird</label><div class="two" id="s-ents">${Object.entries(grp).map(([g, ents]) => `<label class="checkbox"><input type="checkbox" data-ents="${esc(ents.join(","))}" ${ents.some((e) => (c.entities || []).includes(e)) ? "checked" : ""}><span>${esc(g)}</span></label>`).join("")}</div></div></div>
        <div class="sect"><h3>Ausgabe</h3>
          <div class="two"><div class="field"><label class="lbl">Zusatz im Dateinamen</label><input class="input" id="s-suffix" value="${esc(c.suffix || "_anonymisiert")}"></div>
            <div class="field"><label class="lbl">Ablage bei Drag &amp; Drop</label><div class="row"><input class="input" id="s-out" style="flex:1" value="${esc(c.ausgabe_ordner || "")}" placeholder="${esc(c._ausgabe_ordner_effektiv)}"><button class="btn" id="s-out-pick">Wählen</button></div><span class="muted small">Bei „Ordner wählen“ landen die Kopien neben den Originalen.</span></div></div>
          <label class="checkbox"><input type="checkbox" id="s-md" ${c.ki_textfassung ? "checked" : ""}><span><b>Zusätzlich eine Textfassung (.md) erzeugen</b><br><span class="muted small">Reiner Text ohne Layout, mit dem KI-Assistenten am besten arbeiten.</span></span></label></div>
        <div class="sect" id="s-erweitert"><h3>Erweitert</h3><p class="desc">Alles hier ist aus, bis Sie es brauchen.</p>
          <label class="swrow"><div class="t"><b>Antworten der KI zurückübersetzen</b><span>Lokanon speichert je Durchlauf einen verschlüsselten Schlüssel und zeigt oben „Antwort zurückübersetzen“.</span></div><span class="switch"><input type="checkbox" id="s-rz" ${erw.rueckuebersetzung ? "checked" : ""}><span class="track"></span></span></label>
          <div class="field" id="s-pw-row" ${erw.rueckuebersetzung ? "" : "hidden"}><label class="lbl">Passwort für Schlüsseldateien</label><input class="input" type="password" id="s-pw" value="${esc(c.schluessel_passwort || "")}" placeholder="einmal festlegen"><span class="muted small">Liegt in Ihrer Einstellungsdatei auf diesem PC. Schlüssel: ${esc(c._schluessel_ordner_effektiv)}</span></div>
          <label class="swrow"><div class="t"><b>KI-Anweisung und Claude-Skill anzeigen</b><span>Nach dem Anonymisieren erscheint „KI-Anweisung kopieren“.</span></div><span class="switch"><input type="checkbox" id="s-ki" ${erw.ki_anweisung ? "checked" : ""}><span class="track"></span></span></label>
          <label class="swrow"><div class="t"><b>Vorgangsordner mit Prüfbericht und Protokoll</b><span>Je Durchlauf ein Ordner mit Originalen, Kopien, Prüfbericht (Klartext) und Protokoll unter ${esc(c._vorgaenge_ordner_effektiv)}.</span></div><span class="switch"><input type="checkbox" id="s-vg" ${erw.vorgaenge ? "checked" : ""}><span class="track"></span></span></label>
        </div>
        <div class="sect" id="s-vorstellung"><h3>Lokanon vorstellen</h3><p class="desc">Produktvorstellung und Filme für Kolleginnen, Kollegen und Mandanten. Läuft ohne Internet.</p>
          <div class="mkt" id="s-mkt"><span class="muted small">Wird geladen …</span></div></div>
        <div class="row between"><span class="muted small">Lokanon ${esc(S.status.version)} · Einstellungen: ${esc(S.status.daten_ordner)} · <button class="linkbtn" id="s-prot">Protokoll</button></span><button class="btn primary" id="s-save">Speichern</button></div>
      </div>`, { wide: true });
    vorstellungFuellen($("#s-mkt", m));
    $("#s-prot", m).onclick = protokollDialog;
    const gel = JSON.parse(JSON.stringify(c.gelernt || {}));
    const lernListe = () => {
      const zeilen = [["stehen_lassen", "bleibt stehen"], ["immer_ersetzen", "wird immer ersetzt"]].flatMap(([art, was]) =>
        (gel[art] || []).map((g, k) => `<div class="lernrow"><span><b>${esc(g.begriff)}</b> <span class="muted small">${was} · seit ${esc(g.datum || "")}</span></span><button class="linkbtn" data-art="${art}" data-k="${k}" aria-label="${esc(g.begriff)} vergessen">vergessen</button></div>`));
      $("#s-lern", m).innerHTML = zeilen.length ? zeilen.join("") : `<span class="muted small">Noch nichts gelernt.</span>`;
      $$("#s-lern button", m).forEach((b) => (b.onclick = () => { gel[b.dataset.art].splice(+b.dataset.k, 1); lernListe(); }));
    };
    lernListe();
    if (abschnitt) { const z = $(`#s-${abschnitt}`, m); if (z) setTimeout(() => z.scrollIntoView({ block: "start" }), 50); }
    $$("#s-datum label", m).forEach((l) => (l.onclick = () => { $$("#s-datum label", m).forEach((x) => x.classList.remove("on")); l.classList.add("on"); }));
    $("#s-rz", m).onchange = (e) => { $("#s-pw-row", m).hidden = !e.target.checked; };
    $("#s-out-pick", m).onclick = async () => { try { const r = await api("/system/ordner-waehlen", { method: "POST" }); if (r.pfad) $("#s-out", m).value = r.pfad; } catch (e) { toast(e.message, "danger"); } };
    $("#s-save", m).onclick = async () => {
      const lines = (id) => $(id, m).value.split("\n").map((s) => s.trim()).filter(Boolean);
      const entities = [].concat(...$$("#s-ents input", m).filter((i) => i.checked).map((i) => i.dataset.ents.split(",")));
      const werte = { gelernt: gel, allow_list: lines("#s-allow"), deny_list: lines("#s-deny"), keep_institutions: $("#s-inst", m).checked, mask_locations: $("#s-orte", m).checked,
        datum_modus: ($("#s-datum input:checked", m) || {}).value || "kontext", entities, suffix: $("#s-suffix", m).value, ausgabe_ordner: $("#s-out", m).value.trim(),
        ki_textfassung: $("#s-md", m).checked, schluessel_passwort: $("#s-pw", m).value,
        erweitert: { rueckuebersetzung: $("#s-rz", m).checked, ki_anweisung: $("#s-ki", m).checked, vorgaenge: $("#s-vg", m).checked } };
      if (werte.erweitert.rueckuebersetzung && !werte.schluessel_passwort) { toast("Bitte ein Passwort für die Schlüsseldateien festlegen.", "danger"); return; }
      try { await api("/einstellungen", { method: "PUT", json: { werte } }); S.cfg = await api("/einstellungen"); badge(); closeModal(); toast("Einstellungen gespeichert", "ok"); await laden(); } catch (e) { toast(e.message, "danger"); }
    };
  }
  // ------------------------------------------------------------ Produktvorstellung: Deck und Filme
  async function vorstellungFuellen(ziel) {
    let mk;
    try { mk = await api("/marketing"); } catch { ziel.innerHTML = `<span class="muted small">Die Produktvorstellung ist in dieser Installation nicht enthalten.</span>`; return; }
    const teile = [];
    if (mk.deck) teile.push(`<button class="mkt-item" data-deck><span class="mkt-ico" aria-hidden="true">◆</span><span><b>Produktvorstellung</b><small>Interaktive Visitenkarte · zum Durchscrollen</small></span></button>`);
    mk.filme.forEach((f, i) => teile.push(`<button class="mkt-item" data-film="${i}"><span class="mkt-ico" aria-hidden="true">▶</span><span><b>${esc(f.titel)}</b><small>Film · ${esc(f.dauer)}</small></span></button>`));
    if (!teile.length) { ziel.innerHTML = `<span class="muted small">Die Produktvorstellung ist in dieser Installation nicht enthalten.</span>`; return; }
    ziel.innerHTML = `<div class="mkt-grid">${teile.join("")}</div>${mk.ordner ? `<button class="btn ghost small" id="mkt-ordner" style="margin-top:8px">Ordner mit den Dateien öffnen</button>` : ""}`;
    $$("[data-deck]", ziel).forEach((b) => (b.onclick = () => deckDialog(mk.deck_url)));
    $$("[data-film]", ziel).forEach((b) => (b.onclick = () => filmDialog(mk.filme[+b.dataset.film])));
    if ($("#mkt-ordner", ziel)) $("#mkt-ordner", ziel).onclick = () => oeffnen(mk.ordner);
  }
  function vorstellungDialog() {
    const m = modal(`<div class="mhead"><h2>Lokanon vorstellen</h2><button class="x" aria-label="Schließen">✕</button></div>
      <p class="muted small" style="margin-bottom:12px">Produktvorstellung und Filme, ohne Internet.</p><div class="mkt" id="v-mkt"></div>`, { wide: true });
    vorstellungFuellen($("#v-mkt", m));
  }
  function deckDialog(url) {
    modal(`<div class="mhead"><h2>Produktvorstellung</h2><button class="x" aria-label="Schließen">✕</button></div><iframe class="help-frame" src="${esc(url)}" title="Produktvorstellung"></iframe>`, { full: true });
  }
  function filmDialog(f) {
    modal(`<div class="mhead"><h2>${esc(f.titel)}</h2><button class="x" aria-label="Schließen">✕</button></div>
      <video class="mkt-video" src="${esc(f.url)}" controls autoplay playsinline></video>`, { full: true });
  }
  function hilfeDialog() {
    modal(`<div class="mhead"><h2>Anleitung</h2><button class="x" aria-label="Schließen">✕</button></div><iframe class="help-frame" src="/anleitung/" title="Anleitung"></iframe>`, { full: true });
  }

  // ------------------------------------------------------------ Erster Start
  function renderWizard() {
    view.innerHTML = `<section class="wizard"><div class="card raised stack">
      <div><div class="eyebrow">Erster Start</div><h1>Was Lokanon nie ersetzen soll</h1><p class="muted" style="margin-top:6px">Ihr Kanzleiname, Ihre Mitarbeitenden, Ihre Telefonnummern und E-Mail-Adressen stehen in jedem Schriftsatz. Sie gehören Ihnen und bleiben stehen. Eine Angabe je Zeile; Sie können das jederzeit in den Einstellungen ändern.</p></div>
      <div class="field"><label class="lbl" for="w-kanzlei">Kanzlei</label><input class="input" id="w-kanzlei" placeholder="z. B. Rechtsanwälte Beispiel &amp; Partner"></div>
      <div class="field"><label class="lbl" for="w-leute">Mitarbeitende und eigene Kontaktdaten</label><textarea class="input" id="w-leute" rows="5" placeholder="Dr. Anna Beispiel\nMax Mustermann\n0208 123456\nkanzlei@beispiel.de"></textarea></div>
      <div class="row" style="justify-content:flex-end"><button class="btn primary big" id="w-ok">Los geht’s</button></div>
    </div></section>`;
    $("#w-ok").onclick = async () => {
      const allow = [$("#w-kanzlei").value.trim(), ...$("#w-leute").value.split("\n").map((s) => s.trim())].filter(Boolean);
      try { await api("/einstellungen", { method: "PUT", json: { werte: { allow_list: [...new Set(allow)], eingerichtet: true } } }); S.status.eingerichtet = true; S.cfg = await api("/einstellungen"); await laden(); } catch (e) { toast(e.message, "danger"); }
    };
  }

  boot().catch((e) => { view.innerHTML = `<div class="notice danger">Der lokale Server antwortet nicht. Bitte Lokanon neu starten. (${esc(e.message)})</div>`; });
})();
