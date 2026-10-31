/* Lokanon – Oberfläche, Version 3: ein Bildschirm, drei Zustände (Ablegen → Prüfen → Fertig).
   Alles Weitere (Rückübersetzung, KI-Anweisung, Vorgangsordner) hängt an Schaltern in den Einstellungen. */
(() => {
  "use strict";
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const view = $("#view");
  const S = { status: null, cfg: null, z: null, docIndex: 0, docMode: "markiert", filter: "alle", poll: null, pollStatus: null, laufText: "" };
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
    $("#btn-einstellungen").onclick = einstellungenDialog;
    $("#btn-hilfe").onclick = hilfeDialog;
    $("#btn-zurueck").onclick = zurueckDialog;
    $("#brand").onclick = (e) => { e.preventDefault(); if (S.z && (S.z.ergebnis || S.z.fortschritt.fertig)) neuStart(); };
    if (!S.status.eingerichtet) return renderWizard();
    await laden();
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
        ${f.fehler ? `<div class="notice danger" style="margin-top:16px;text-align:left"><b>Das hat nicht geklappt.</b> ${esc(f.fehler)}</div>` : ""}
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
    if ($("#btn-start")) $("#btn-start").onclick = analyseStarten;
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
    view.innerHTML = `
      <div class="pruefen">
        <section>
          <div class="summary"><h1>${ids.length} ${ids.length === 1 ? "Angabe" : "Angaben"} gefunden</h1><span class="muted">${ersetzt} werden ersetzt · ${z.dateien.length} ${z.dateien.length === 1 ? "Datei" : "Dateien"}</span></div>
          ${unsicher ? `<div class="notice warn unsure" id="unsure" title="Nur unsichere anzeigen"><b>${unsicher} ${unsicher === 1 ? "Angabe" : "Angaben"} bitte ansehen.</b> Lokanon ersetzt im Zweifel. Was kein Personenbezug ist, schalten Sie aus.</div>` : `<div class="notice ok"><b>Alles eindeutig.</b> Prüfen Sie die Liste und das Dokument rechts, dann anonymisieren.</div>`}
          <div class="toolbar" style="margin-top:12px">
            <input class="input" id="nachtrag" placeholder="Fehlt etwas? Begriff eintragen, mehrere mit Komma">
            <button class="btn" id="btn-nachtrag">Nachtragen</button>
          </div>
          <div class="filter" id="filter">${["alle", ...gruppen, "unsicher"].map((g) => `<button class="${S.filter === g ? "on" : ""}" data-f="${esc(g)}">${g === "alle" ? "Alle" : g === "unsicher" ? "Bitte ansehen" : esc(g)}</button>`).join("")}</div>
          <div id="liste"></div>
        </section>
        <aside class="docpanel">
          <div class="row between" style="margin-bottom:8px"><b>Dokument</b><div class="filter" style="margin:0"><button id="m-orig" class="${S.docMode === "markiert" ? "on" : ""}">Original mit Markierungen</button><button id="m-anon" class="${S.docMode === "anonym" ? "on" : ""}">Anonymisiert</button></div></div>
          <div class="doctabs" id="doctabs">${z.dokumente.map((d, i) => `<button class="${i === S.docIndex ? "on" : ""}" data-i="${i}" title="${esc(d.name)}">${esc(d.name)}</button>`).join("")}</div>
          <div class="docview" id="docview"></div>
          <div class="legend"><span><i style="background:var(--mark-person)"></i>Person</span><span><i style="background:var(--mark-firma)"></i>Firma</span><span><i style="background:var(--mark-ort)"></i>Adresse/Ort</span><span><i style="background:var(--mark-nummer)"></i>Nummer</span><span><i style="border:1px dashed var(--muted)"></i>bleibt stehen</span></div>
        </aside>
      </div>
      <div class="actionbar"><div class="inner">
        <span class="hint">${esc(z.ordner ? "Die anonymisierten Dateien kommen neben die Originale in " + z.ordner : "Die anonymisierten Dateien kommen nach " + z.ausgabe_ordner)}</span>
        <button class="btn ghost" id="btn-neu">Neue Dateien</button>
        <button class="btn primary big" id="btn-anon">Geprüft, jetzt anonymisieren</button>
      </div></div>`;
    renderListe();
    renderDoc();
    $$("#filter button").forEach((b) => (b.onclick = () => { S.filter = b.dataset.f; renderPruefen(); }));
    if ($("#unsure")) $("#unsure").onclick = () => { S.filter = "unsicher"; renderPruefen(); };
    $("#btn-nachtrag").onclick = () => { const t = $("#nachtrag").value.split(",").map((s) => s.trim()).filter(Boolean); if (t.length) analyseStarten(t); };
    $("#nachtrag").onkeydown = (e) => { if (e.key === "Enter") $("#btn-nachtrag").click(); };
    $("#m-orig").onclick = () => { S.docMode = "markiert"; renderPruefen(); };
    $("#m-anon").onclick = () => { S.docMode = "anonym"; renderPruefen(); };
    $$("#doctabs button").forEach((b) => (b.onclick = () => { S.docIndex = +b.dataset.i; renderPruefen(); }));
    $("#btn-neu").onclick = () => bestaetigen("Neue Dateien ablegen? Die aktuelle Prüfung wird verworfen.", neuStart);
    $("#btn-anon").onclick = anonymisieren;
  }
  function renderDoc() {
    const d = S.z.dokumente[S.docIndex]; const dv = $("#docview");
    if (!d) { dv.textContent = ""; return; }
    if (S.docMode === "markiert") dv.innerHTML = d.markiert_html; else dv.textContent = d.anonym;
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
    });
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
      <div class="meta">${esc(i.typ)} · ${i.anzahl}× in ${i.dateien.length} ${i.dateien.length === 1 ? "Datei" : "Dateien"} · ${esc(i.sicherheit)}${i.quellen.length ? " · " + esc(i.quellen.join(", ")) : ""}</div>
      <div class="snip">${i.beispiel}</div>
      ${i.gruende.length ? `<div class="warnline">Bitte ansehen: ${esc(i.gruende.join("; "))}</div>` : ""}
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
    const erw = z.erweitert || {};
    view.innerHTML = `<section class="fertig">
      <svg class="check" viewBox="0 0 60 60"><circle cx="30" cy="30" r="26"/><path d="M18 31l8 8 16-17"/></svg>
      <h1 style="text-align:center">${ok} von ${r.dateien.length} ${r.dateien.length === 1 ? "Datei" : "Dateien"} anonymisiert</h1>
      <p class="muted" style="text-align:center;margin:6px 0 20px">${ok === r.dateien.length ? "Alle Kopien sind geprüft und ohne Personenbezug." : "Bei einer Datei hat es nicht geklappt, Hinweis unten."}</p>
      <div class="card raised stack">
        <div class="row between"><div class="pathbox" style="flex:1"><span title="${esc(r.ordner)}">${esc(r.ordner)}</span></div><button class="btn" id="btn-open">Ordner öffnen</button></div>
        <div>${r.dateien.map((d) => `<div class="result-file"><span class="st ${d.status}">${d.status === "ok" ? "✓" : "!"}</span><div style="flex:1;min-width:0"><b>${esc(d.ausgabe)}</b>${d.textfassung ? ` <span class="muted small">+ ${esc(d.textfassung)}</span>` : ""}<div class="muted small">aus ${esc(d.name)} · ${d.ersetzt} Stellen ersetzt${d.hinweis ? ` · <span style="color:var(--danger)">${esc(d.hinweis)}</span>` : ""}</div></div></div>`).join("")}</div>
        ${r.hinweise.length ? `<div class="notice warn"><div>${r.hinweise.map(esc).join("<br>")}</div></div>` : ""}
        ${r.schluessel_pfad ? `<div class="notice info small"><div>Schlüssel für die Rückübersetzung gespeichert: <code>${esc(r.schluessel_pfad)}</code></div></div>` : ""}
      </div>
      <div class="row" style="justify-content:center;margin-top:22px;gap:10px">
        ${erw.ki_anweisung ? `<button class="btn" id="btn-anw">KI-Anweisung kopieren</button>` : ""}
        ${erw.rueckuebersetzung ? `<button class="btn" id="btn-zk">Antwort zurückübersetzen</button>` : ""}
        <button class="btn primary big" id="btn-neu">Neue Dateien</button>
      </div>
    </section>`;
    $("#btn-open").onclick = () => oeffnen(r.ordner);
    $("#btn-neu").onclick = neuStart;
    if ($("#btn-anw")) $("#btn-anw").onclick = anweisungDialog;
    if ($("#btn-zk")) $("#btn-zk").onclick = zurueckDialog;
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
  async function einstellungenDialog() {
    S.cfg = await api("/einstellungen");
    const c = S.cfg; const erw = c.erweitert || {};
    const grp = c._gruppen || {};
    const m = modal(`<div class="mhead"><h2>Einstellungen</h2><button class="x" aria-label="Schließen">✕</button></div>
      <div class="settings">
        <div class="sect"><h3>Ihre Kanzlei</h3><p class="desc">Diese Namen werden nie ersetzt: Kanzleiname, Mitarbeitende, eigene Telefonnummern und E-Mail-Adressen. Eine Angabe je Zeile, Namensteile zählen mit.</p>
          <textarea class="input" id="s-allow" rows="5">${esc((c.allow_list || []).join("\n"))}</textarea>
          <label class="lbl">Immer ersetzen <span class="muted small">(interne Kürzel, Projektnamen)</span></label>
          <textarea class="input" id="s-deny" rows="2">${esc((c.deny_list || []).join("\n"))}</textarea></div>
        <div class="sect"><h3>Erkennung</h3>
          <label class="checkbox"><input type="checkbox" id="s-inst" ${c.keep_institutions ? "checked" : ""}><span><b>Gerichte, Behörden, Versicherer, Kliniken stehen lassen</b><br><span class="muted small">Meist kein Personenbezug; einzelne lassen sich beim Prüfen trotzdem ersetzen.</span></span></label>
          <label class="checkbox"><input type="checkbox" id="s-orte" ${c.mask_locations ? "checked" : ""}><span><b>Ortsnamen ohne Adresse ersetzen</b><br><span class="muted small">„Mülheim“ im Fließtext. Adressen und PLZ mit Ort werden immer ersetzt.</span></span></label>
          <div class="field"><label class="lbl">Datumsangaben</label><div class="radio-row" id="s-datum">${[["kontext", "nur mit Personenbezug (Geburt, Tod)"], ["alle", "jedes Datum"], ["keine", "keine"]].map(([v, t]) => `<label class="radio-chip ${c.datum_modus === v ? "on" : ""}"><input type="radio" name="datum" value="${v}" ${c.datum_modus === v ? "checked" : ""}>${t}</label>`).join("")}</div></div>
          <div class="field"><label class="lbl">Was erkannt wird</label><div class="two" id="s-ents">${Object.entries(grp).map(([g, ents]) => `<label class="checkbox"><input type="checkbox" data-ents="${esc(ents.join(","))}" ${ents.some((e) => (c.entities || []).includes(e)) ? "checked" : ""}><span>${esc(g)}</span></label>`).join("")}</div></div></div>
        <div class="sect"><h3>Ausgabe</h3>
          <div class="two"><div class="field"><label class="lbl">Zusatz im Dateinamen</label><input class="input" id="s-suffix" value="${esc(c.suffix || "_anonymisiert")}"></div>
            <div class="field"><label class="lbl">Ablage bei Drag &amp; Drop</label><div class="row"><input class="input" id="s-out" style="flex:1" value="${esc(c.ausgabe_ordner || "")}" placeholder="${esc(c._ausgabe_ordner_effektiv)}"><button class="btn" id="s-out-pick">Wählen</button></div><span class="muted small">Bei „Ordner wählen“ landen die Kopien neben den Originalen.</span></div></div>
          <label class="checkbox"><input type="checkbox" id="s-md" ${c.ki_textfassung ? "checked" : ""}><span><b>Zusätzlich eine Textfassung (.md) erzeugen</b><br><span class="muted small">Reiner Text ohne Layout, mit dem KI-Assistenten am besten arbeiten.</span></span></label></div>
        <div class="sect"><h3>Erweitert</h3><p class="desc">Alles hier ist aus, bis Sie es brauchen.</p>
          <label class="swrow"><div class="t"><b>Antworten der KI zurückübersetzen</b><span>Lokanon speichert je Durchlauf einen verschlüsselten Schlüssel und zeigt oben „Antwort zurückübersetzen“.</span></div><span class="switch"><input type="checkbox" id="s-rz" ${erw.rueckuebersetzung ? "checked" : ""}><span class="track"></span></span></label>
          <div class="field" id="s-pw-row" ${erw.rueckuebersetzung ? "" : "hidden"}><label class="lbl">Passwort für Schlüsseldateien</label><input class="input" type="password" id="s-pw" value="${esc(c.schluessel_passwort || "")}" placeholder="einmal festlegen"><span class="muted small">Liegt in Ihrer Einstellungsdatei auf diesem PC. Schlüssel: ${esc(c._schluessel_ordner_effektiv)}</span></div>
          <label class="swrow"><div class="t"><b>KI-Anweisung und Claude-Skill anzeigen</b><span>Nach dem Anonymisieren erscheint „KI-Anweisung kopieren“.</span></div><span class="switch"><input type="checkbox" id="s-ki" ${erw.ki_anweisung ? "checked" : ""}><span class="track"></span></span></label>
          <label class="swrow"><div class="t"><b>Vorgangsordner mit Prüfbericht und Protokoll</b><span>Je Durchlauf ein Ordner mit Originalen, Kopien, Prüfbericht (Klartext) und Protokoll unter ${esc(c._vorgaenge_ordner_effektiv)}.</span></div><span class="switch"><input type="checkbox" id="s-vg" ${erw.vorgaenge ? "checked" : ""}><span class="track"></span></span></label>
        </div>
        <div class="row between"><span class="muted small">Lokanon ${esc(S.status.version)} · Einstellungen: ${esc(S.status.daten_ordner)}</span><button class="btn primary" id="s-save">Speichern</button></div>
      </div>`, { wide: true });
    $$("#s-datum label", m).forEach((l) => (l.onclick = () => { $$("#s-datum label", m).forEach((x) => x.classList.remove("on")); l.classList.add("on"); }));
    $("#s-rz", m).onchange = (e) => { $("#s-pw-row", m).hidden = !e.target.checked; };
    $("#s-out-pick", m).onclick = async () => { try { const r = await api("/system/ordner-waehlen", { method: "POST" }); if (r.pfad) $("#s-out", m).value = r.pfad; } catch (e) { toast(e.message, "danger"); } };
    $("#s-save", m).onclick = async () => {
      const lines = (id) => $(id, m).value.split("\n").map((s) => s.trim()).filter(Boolean);
      const entities = [].concat(...$$("#s-ents input", m).filter((i) => i.checked).map((i) => i.dataset.ents.split(",")));
      const werte = { allow_list: lines("#s-allow"), deny_list: lines("#s-deny"), keep_institutions: $("#s-inst", m).checked, mask_locations: $("#s-orte", m).checked,
        datum_modus: ($("#s-datum input:checked", m) || {}).value || "kontext", entities, suffix: $("#s-suffix", m).value, ausgabe_ordner: $("#s-out", m).value.trim(),
        ki_textfassung: $("#s-md", m).checked, schluessel_passwort: $("#s-pw", m).value,
        erweitert: { rueckuebersetzung: $("#s-rz", m).checked, ki_anweisung: $("#s-ki", m).checked, vorgaenge: $("#s-vg", m).checked } };
      if (werte.erweitert.rueckuebersetzung && !werte.schluessel_passwort) { toast("Bitte ein Passwort für die Schlüsseldateien festlegen.", "danger"); return; }
      try { await api("/einstellungen", { method: "PUT", json: { werte } }); S.cfg = await api("/einstellungen"); badge(); closeModal(); toast("Einstellungen gespeichert", "ok"); await laden(); } catch (e) { toast(e.message, "danger"); }
    };
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
