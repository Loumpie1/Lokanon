/* Lokanon – Oberfläche Version 5 „Arbeitsplatz“ (docs/anforderungen/lernen-und-loeschfristen.md, Abschnitt 12).
   Bereiche: Start, Aktueller Vorgang (Prüfen → Fertig), Fälle und gelernte Angaben, Protokoll, Einstellungen.
   Jedes Bedienelement, das die Einführung zeigt, trägt einen data-tour-Anker (ui/einfuehrung/drehbuch.js);
   wichtige Aktionen meldet melde() an die Einführung. Hilfetexte kommen aus ui/einfuehrung/hilfetexte.js. */
(() => {
  "use strict";
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  // Linien-Symbole, 16 px, Strich 1,3
  const ICO = {
    datei: '<path d="M9 2H4.5A1.5 1.5 0 0 0 3 3.5v9A1.5 1.5 0 0 0 4.5 14h7a1.5 1.5 0 0 0 1.5-1.5V6L9 2Z"/><path d="M9 2v4h4M8 8v4M6 10h4"/>',
    ordner: '<path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h3l1.5 1.5h4.5A1.5 1.5 0 0 1 14 6v5.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 11.5v-7Z"/>',
    text: '<rect x="3.5" y="3" width="9" height="11" rx="1.5"/><path d="M6 2.5h4V4H6zM6 7h4M6 9.5h4M6 12h2"/>',
    markieren: '<path d="m9.5 3 3.5 3.5-6 6H3.5V9l6-6Z"/><path d="M2.5 14.5h11"/>',
    rueck: '<path d="M6 4 3 7l3 3"/><path d="M3 7h6.5a3.5 3.5 0 0 1 0 7H8"/>',
    schild: '<path d="M8 1.8 13 3.6v4c0 3.2-2.1 5.6-5 6.6-2.9-1-5-3.4-5-6.6v-4L8 1.8Z"/><path d="M5.5 8h5"/>',
    start: '<path d="M2.5 7 8 2.5 13.5 7v6a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1V7Z"/>',
    liste: '<path d="M3 3.5h10M3 8h10M3 12.5h6"/>',
    faelle: '<path d="M2.5 5.5h11v7a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1v-7ZM4 3h8l1.5 2.5h-11L4 3Z"/>',
    uhr: '<circle cx="8" cy="8" r="5.5"/><path d="M8 5v3l2 1.5"/>',
    play: '<path d="M5 3.5v9l7-4.5-7-4.5Z"/>',
    zahnrad: '<circle cx="8" cy="8" r="2"/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4"/>',
    x: '<path d="M4 4l8 8M12 4l-8 8"/>', check: '<path d="m3.5 8.5 3 3 6-7"/>',
    warn: '<path d="M8 2.2 14.2 13H1.8L8 2.2Z"/><path d="M8 6.5v3M8 11.2v.2"/>',
    pfeil: '<path d="m6 3.5 4.5 4.5L6 12.5"/>', runter: '<path d="m4.5 6 3.5 3.5L11.5 6"/>',
    punkte: '<circle cx="3.5" cy="8" r=".9"/><circle cx="8" cy="8" r=".9"/><circle cx="12.5" cy="8" r=".9"/>',
    suche: '<circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 3 3"/>',
    schloss: '<rect x="3.5" y="7" width="9" height="6.5" rx="1"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2"/>',
    scan: '<rect x="3" y="2.5" width="10" height="11" rx="1"/><path d="M1.5 8h13"/>',
    stift: '<path d="M10.5 2.5 13.5 5.5 6 13H3v-3l7.5-7.5Z"/>',
    kopie: '<rect x="5" y="5" width="8.5" height="8.5" rx="1"/><path d="M3 10.5V3.5A1 1 0 0 1 4 2.5h6.5"/>',
    pfeilzurueck: '<path d="M7 3.5 2.5 8 7 12.5M2.5 8h11"/>',
  };
  const ico = (n, cls = "") => `<svg class="ico ${cls}" viewBox="0 0 16 16" aria-hidden="true">${ICO[n] || ""}</svg>`;
  const view = $("#view");
  const merke = (k, v) => { try { localStorage.setItem("lokanon." + k, JSON.stringify(v)); } catch {} };
  const gemerkt = (k, d) => { try { const v = localStorage.getItem("lokanon." + k); return v === null ? d : JSON.parse(v); } catch { return d; } };
  const S = { status: null, cfg: null, z: null, faelle: null, ansicht: "start", docIndex: 0, docMode: "markiert", filter: "alle",
    gewaehlt: null, stelle: null, markiermodus: false, poll: null, pollStatus: null, auf: new Set(), suche: "", sucheErg: null,
    auswahl: new Set() };
  const HILFE = window.LokanonHilfe || {};
  const datum = (iso) => { if (!iso) return ""; const [j, m, t] = iso.slice(0, 10).split("-"); return `${t}.${m}.${j}`; };
  const plusMonate = (monate) => { const d = new Date(); d.setMonth(d.getMonth() + monate); return d.toISOString().slice(0, 10); };

  // ------------------------------------------------------------ Grundbausteine
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
  function toast(msg, kind = "", aktion = null) {
    const t = document.createElement("div"); t.className = "toast " + kind; t.setAttribute("role", "status");
    const span = document.createElement("span"); span.textContent = msg; t.appendChild(span);
    if (aktion) { const b = document.createElement("button"); b.textContent = aktion.label; b.onclick = () => { t.remove(); aktion.fn(); }; t.appendChild(b); }
    $("#toasts").appendChild(t); setTimeout(() => t.remove(), aktion ? 9000 : kind === "danger" ? 6500 : 3200);
  }
  // Meldung an die Einführung (ui/einfuehrung/fuehrung.js wartet bei „Selbst tun“-Schritten darauf)
  function melde(art, detail = {}) { document.dispatchEvent(new CustomEvent("lokanon", { detail: { ...detail, art } })); }
  function modal(html, { wide = false, full = false, tour = "" } = {}) {
    const root = $("#modal-root");
    root.innerHTML = `<div class="modal ${wide ? "wide" : ""} ${full ? "full" : ""}" role="dialog" aria-modal="true" ${tour ? `data-tour="${tour}"` : ""}>${html}</div>`;
    root.hidden = false;
    root.onclick = (e) => { if (e.target === root) closeModal(); };
    $$(".x", root).forEach((b) => (b.onclick = closeModal));
    const f = $("[autofocus]", root) || $(".mfuss .btn", root); if (f) f.focus();
    return root.firstElementChild;
  }
  function closeModal() { const root = $("#modal-root"); root.hidden = true; root.innerHTML = ""; }
  const kopf = (titel, unter = "") => `<div class="mkopf"><div><h2>${titel}</h2>${unter ? `<p>${unter}</p>` : ""}</div><button class="iconbtn x" aria-label="Schließen">${ico("x")}</button></div>`;
  function bestaetigen(text, fn, ja = "Ja") {
    const m = modal(`${kopf("Bitte bestätigen")}<div class="minhalt"><p>${esc(text)}</p></div>
      <div class="mfuss"><button class="btn x" autofocus>Abbrechen</button><button class="btn primary" id="ja">${esc(ja)}</button></div>`);
    $("#ja", m).onclick = () => { closeModal(); fn(); };
  }
  const copy = async (text, ok = "Kopiert") => { try { await navigator.clipboard.writeText(text); toast(ok, "ok"); } catch { toast("Kopieren nicht möglich, bitte markieren und kopieren.", "danger"); } };
  const oeffnen = (pfad) => api("/system/oeffnen", { json: { pfad } }).catch((e) => toast(e.message, "danger"));
  const kb = (n) => (n > 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB");
  const hilfeKnopf = (key, was = "Mehr dazu") => (HILFE[key] ? `<button type="button" class="info" data-hilfe="${key}" aria-label="${esc(was)}: ${esc(HILFE[key].titel)}">i</button>` : "");

  // Kontexthilfe (i): Kurzbegründung und „Mehr dazu“ in einer kleinen Blase, kein Tooltip beim Überfahren
  function hilfeZeigen(key, anker) {
    schliesseSchwebendes();
    const h = HILFE[key]; if (!h) return;
    const p = document.createElement("div"); p.className = "hilfe-pop"; p.id = "hilfe-pop"; p.setAttribute("role", "dialog");
    p.innerHTML = `<b>${esc(h.titel)}</b><div>${h.kurz}</div>${h.mehr ? `<div class="mehr">${h.mehr}</div>` : ""}
      ${h.kapitel ? `<div><button class="linkbtn" data-kapitel="${esc(h.kapitel)}">${ico("play")} Im Programm zeigen</button></div>` : ""}`;
    document.body.appendChild(p);
    const r = anker.getBoundingClientRect();
    p.style.left = Math.max(12, Math.min(r.left - 20, innerWidth - p.offsetWidth - 12)) + "px";
    p.style.top = (r.bottom + 8 + p.offsetHeight > innerHeight ? Math.max(12, r.top - p.offsetHeight - 8) : r.bottom + 8) + "px";
    const k = $("[data-kapitel]", p); if (k) k.onclick = () => { schliesseSchwebendes(); tourStarten(k.dataset.kapitel); };
  }
  function menue(anker, eintraege) {
    schliesseSchwebendes();
    const m = document.createElement("div"); m.className = "menue"; m.id = "menue"; m.setAttribute("role", "menu");
    m.innerHTML = eintraege.map((e, i) => e === "-" ? `<div class="trenn"></div>` : e.titel ? `<div class="titel-m">${esc(e.titel)}</div>`
      : `<button role="menuitem" data-i="${i}" class="${e.gefahr ? "gefahr" : ""}" ${e.tour ? `data-tour="${e.tour}"` : ""}>${esc(e.label)}</button>`).join("");
    document.body.appendChild(m);
    const r = anker.getBoundingClientRect();
    m.style.left = Math.max(8, Math.min(r.left, innerWidth - m.offsetWidth - 8)) + "px";
    m.style.top = (r.bottom + 4 + m.offsetHeight > innerHeight ? Math.max(8, r.top - m.offsetHeight - 4) : r.bottom + 4) + "px";
    $$("button", m).forEach((b) => (b.onclick = () => { schliesseSchwebendes(); eintraege[+b.dataset.i].fn(); }));
    const erst = $("button", m); if (erst) erst.focus();
  }
  function schliesseSchwebendes() { ["#hilfe-pop", "#menue"].forEach((s) => { const e = $(s); if (e) e.remove(); }); }
  document.addEventListener("click", (e) => {
    const h = e.target.closest("[data-hilfe]");
    if (h) { e.preventDefault(); e.stopPropagation(); hilfeZeigen(h.dataset.hilfe, h); return; }
    if (!e.target.closest("#hilfe-pop, #menue")) schliesseSchwebendes();
  }, true);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { schliesseSchwebendes(); leisteZu(); if (!$("#modal-root").hidden) closeModal(); }
  });

  // ------------------------------------------------------------ Start, Rahmen, Navigation
  async function boot() {
    S.status = await api("/status");
    S.cfg = await api("/einstellungen");
    $("#btn-hilfe").onclick = (e) => hilfeMenue(e.currentTarget);
    $("#marke").onclick = (e) => { e.preventDefault(); zeige("start"); };
    $("#uebung-ende").onclick = () => tourBeenden();
    rahmen();
    if (!S.status.eingerichtet) return renderWizard();
    await laden(true);
    faelleLaden();
    direktlink();
  }
  function direktlink() {
    const h = decodeURIComponent(location.hash.slice(1));
    if (h.startsWith("einstellungen")) zeige("einstellungen", h.split("/")[1] || "");
    else if (h === "faelle") zeige("faelle");
    else if (h === "vorstellung") vorstellungDialog();
    else if (h === "zurueck" && (S.cfg.erweitert || {}).rueckuebersetzung) zurueckDialog();
    else if (h === "hilfe") hilfeDialog();
    else if (h.startsWith("einfuehrung")) tourStarten(h.split("/")[1] || "");
  }
  window.addEventListener("hashchange", direktlink);  // Links aus der Anleitung („Im Programm zeigen“)
  async function laden(ansichtWaehlen = false) {
    S.z = await api("/zustand");
    if (ansichtWaehlen) { const f = S.z.fortschritt; S.ansicht = f.laeuft || f.fertig || S.z.ergebnis ? "vorgang" : "start"; }
    render();
  }
  async function faelleLaden() {
    try { S.faelle = await api("/faelle"); } catch { S.faelle = null; }
    rahmen();
    if (S.ansicht === "start") renderStart();
    if (S.ansicht === "faelle") renderFaelle();
  }
  function zeige(ansicht, abschnitt = "") {
    S.ansicht = ansicht; leisteZu(); schliesseSchwebendes();
    render();
    if (ansicht === "faelle" || ansicht === "start") faelleLaden();
    if (abschnitt) setTimeout(() => { const z = $(`#a-${abschnitt}`); if (z) z.scrollIntoView({ block: "start" }); }, 60);
    melde("ansicht-" + ansicht);
  }
  function rahmen() {
    const z = S.z, bereit = S.status.modelle_bereit;
    const hat = z && (z.fortschritt.laeuft || z.fortschritt.fertig || z.ergebnis);
    const warn = S.faelle ? S.faelle.hinweise.length : 0;
    const navi = (id, icon, label, extra = "") => `<button class="navi" data-a="${id}" data-tour="nav-${id}" ${S.ansicht === id ? 'aria-current="page"' : ""}>${ico(icon)}${label}${extra}</button>`;
    $("#nav").innerHTML = `${navi("start", "start", "Start")}
      ${navi("vorgang", "liste", "Aktueller Vorgang", hat ? "" : "")}
      ${navi("faelle", "faelle", "Fälle und gelernte Angaben", warn ? `<span class="zaehler" title="Fristen laufen bald ab">${warn}</span>` : "")}
      ${navi("protokoll", "uhr", "Protokoll")}
      <div class="trenn"></div>
      <button class="navi" data-a="einfuehrung" data-tour="nav-einfuehrung">${ico("play")}Einführung</button>
      ${navi("einstellungen", "zahnrad", "Einstellungen")}
      <span class="fill"></span>
      <div class="lokal"><b>${ico("schloss")}Nur auf diesem PC</b>Erkennung und Schwärzung laufen hier. Keine Internetverbindung nötig.</div>`;
    $$("#nav [data-a]").forEach((b) => (b.onclick = () => b.dataset.a === "einfuehrung" ? tourStarten("") : zeige(b.dataset.a)));
    $("#nav [data-a=vorgang]").disabled = !hat;
    const fall = z && z.fall ? ` · Fall ${z.fall}` : "";
    $("#kontext").textContent = z && z.dokumente && z.dokumente.length ? `${vorgangsName()}${fall} · ${z.dokumente.length} ${z.dokumente.length === 1 ? "Datei" : "Dateien"}` : "";
    $("#status").innerHTML = `<span><i class="punkt ${bereit ? "" : "laden"}"></i>${bereit ? "Läuft lokal" : "Sprachmodelle werden geladen …"}</span>
      ${bereit ? "<span>Sprachmodelle bereit</span>" : ""}
      <span class="fill"></span>${S.ansicht === "vorgang" && z && z.fortschritt.fertig && !z.ergebnis ? "<span>M Markieren · Strg+Z Rückgängig</span>" : ""}
      <span>Version ${esc(S.status.version)}</span>`;
    $("#uebung-band").hidden = !(S.status.uebung || (z && z.uebung));
    if (!bereit && !S.pollStatus) S.pollStatus = setInterval(async () => { try { S.status = await api("/status"); } catch { return; } if (S.status.modelle_bereit) { clearInterval(S.pollStatus); S.pollStatus = null; rahmen(); } }, 1500);
  }
  function vorgangsName() {
    const z = S.z; if (!z) return "";
    if (z.ordner) return z.ordner.split(/[\\/]/).pop();
    return z.dokumente && z.dokumente[0] ? z.dokumente[0].name.replace(/\.[^.]+$/, "") : "";
  }
  function befehle(html) { $("#befehle").innerHTML = html; }
  function render() {
    rahmen();
    const z = S.z;
    if (S.ansicht === "vorgang") {
      if (!z || !(z.fortschritt.laeuft || z.fortschritt.fertig || z.ergebnis)) S.ansicht = "start";
    }
    if (S.ansicht === "start") return renderStart();
    if (S.ansicht === "faelle") return renderFaelle();
    if (S.ansicht === "protokoll") return renderProtokoll();
    if (S.ansicht === "einstellungen") return renderEinstellungen();
    if (z.fortschritt.laeuft) return renderLaeuft();
    if (z.ergebnis) return renderFertig();
    return renderPruefen();
  }
  function hilfeMenue(anker) {
    const kap = (window.LokanonDrehbuch || { kapitel: [] }).kapitel;
    menue(anker, [{ label: "Anleitung", fn: hilfeDialog }, { label: "Einführung starten (ca. 5 Min.)", fn: () => tourStarten(""), tour: "menue-einfuehrung" },
      { titel: "Einzelne Kapitel" }, ...kap.map((k) => ({ label: `${k.nr}. ${k.titel}`, fn: () => tourStarten(k.id) })),
      "-", { label: `Neu in ${S.status.version.replace(/-dev$/, "")}`, fn: () => tourStarten("neu") },
      { label: "Lokanon vorstellen", fn: vorstellungDialog }]);
  }

  // ------------------------------------------------------------ Dateien ablegen (überall im Fenster)
  let zieht = 0;
  window.addEventListener("dragenter", (e) => { if (e.dataTransfer && [...e.dataTransfer.types].includes("Files")) { zieht++; document.body.classList.add("ziehen"); } });
  window.addEventListener("dragleave", () => { zieht = Math.max(0, zieht - 1); if (!zieht) document.body.classList.remove("ziehen"); });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => { e.preventDefault(); zieht = 0; document.body.classList.remove("ziehen"); if (e.dataTransfer && e.dataTransfer.files.length) neueDateien(() => hochladen(e.dataTransfer.files)); });
  // Neue Dateien verwerfen die laufende Prüfung: dann erst fragen
  // Die offene Prüfung wird erst verworfen, wenn wirklich neue Dateien gewählt sind. Bricht man den Datei- oder
  // Ordnerdialog ab, bleibt sie unverändert offen.
  function neueDateien(fn) {
    const z = S.z;
    if (z && z.fortschritt.fertig && !z.ergebnis && z.identitaeten.length) bestaetigen("Neue Dateien ablegen? Die aktuelle Prüfung wird verworfen, sobald Sie Dateien gewählt haben.", () => { S.verwerfen = true; fn(); }, "Neue Dateien");
    else { S.verwerfen = false; fn(); }
  }
  async function vorAblegen() { if (S.verwerfen) { S.verwerfen = false; await api("/leeren", { method: "POST" }); } }
  function dateiWaehlen() {
    const i = document.createElement("input"); i.type = "file"; i.multiple = true; i.accept = ".pdf,.docx,.xlsx,.csv,.txt,.md";
    i.onchange = () => hochladen(i.files); i.oncancel = () => (S.verwerfen = false); i.click();
  }
  async function hochladen(files) {
    if (!files || !files.length) { S.verwerfen = false; return; }
    const form = new FormData();
    for (const f of files) form.append("datei", f, f.name);
    try { await vorAblegen(); await api("/dateien", { form }); await analyseStarten(); } catch (e) { toast(e.message, "danger"); }
  }
  async function ordnerWaehlen() {
    let pfad = "";
    try { pfad = (await api("/system/ordner-waehlen", { method: "POST" })).pfad; } catch { pfad = await pfadDialog(); }
    if (!pfad) { S.verwerfen = false; return; }
    try { await vorAblegen(); await api("/ordner", { json: { pfad } }); await analyseStarten(); } catch (e) { toast(e.message, "danger"); }
  }
  function pfadDialog() {
    return new Promise((resolve) => {
      const m = modal(`${kopf("Ordner eintippen", "Der Ordnerdialog steht hier nicht zur Verfügung.")}
        <div class="minhalt"><input class="input" id="pf-in" placeholder="z. B. C:\\Akten\\Mandant Müller" autofocus></div>
        <div class="mfuss"><button class="btn x">Abbrechen</button><button class="btn primary" id="pf-ok">Übernehmen</button></div>`);
      const fertig = (v) => { closeModal(); resolve(v); };
      $("#pf-ok", m).onclick = () => fertig($("#pf-in", m).value.trim());
      $("#pf-in", m).onkeydown = (e) => { if (e.key === "Enter") fertig($("#pf-in", m).value.trim()); };
      $$(".x", m).forEach((b) => (b.onclick = () => fertig("")));
      $("#pf-in", m).focus();
    });
  }
  function textDialog() {
    const m = modal(`${kopf("Text einfügen", "Zum Beispiel eine E-Mail oder einen Absatz aus einem Schriftsatz.")}
      <div class="minhalt"><textarea class="input" id="txt" rows="10" placeholder="Text hier einfügen …" autofocus></textarea></div>
      <div class="mfuss"><button class="btn x">Abbrechen</button><button class="btn primary" id="txt-ok">Erkennen und prüfen</button></div>`);
    $("#txt", m).focus();
    $$(".x", m).forEach((b) => b.addEventListener("click", () => (S.verwerfen = false)));
    $("#txt-ok", m).onclick = async () => { try { await vorAblegen(); await api("/text", { json: { text: $("#txt", m).value } }); closeModal(); await analyseStarten(); } catch (e) { toast(e.message, "danger"); } };
  }
  async function analyseStarten(begriffe = []) {
    try { await api("/analyse", { json: { begriffe } }); S.docIndex = 0; S.gewaehlt = null; S.stelle = null; S.ansicht = "vorgang"; await laden(); pollen(); } catch (e) { toast(e.message, "danger"); }
  }
  function pollen() {
    clearInterval(S.poll);
    S.poll = setInterval(async () => {
      try {
        const f = await api("/fortschritt");
        const bar = $("#pbar");
        if (bar) { bar.classList.toggle("unbestimmt", f.prozent < 5); bar.firstElementChild.style.width = f.prozent + "%"; $("#p-schritt").textContent = f.schritt || "…"; $("#p-datei").textContent = f.datei || " "; }
        if (!f.laeuft) {
          clearInterval(S.poll); if (f.fehler) toast(f.fehler, "danger");
          await laden();
          if (S.z.ergebnis) { melde("anonymisiert"); faelleLaden(); } else if (f.fertig) melde("analysiert");
        }
      } catch (e) { clearInterval(S.poll); toast(e.message, "danger"); }
    }, 500);
  }

  // ------------------------------------------------------------ Start
  function renderStart() {
    befehle(`<button class="cmd" data-c="dateien" data-tour="befehl-dateien">${ico("datei")}Dateien hinzufügen</button>
      <button class="cmd" data-c="ordner">${ico("ordner")}Ordner öffnen</button>
      <button class="cmd" data-c="text">${ico("text")}Text einfügen</button>
      <span class="sep"></span><button class="cmd" data-c="tour">${ico("play")}Einführung</button>`);
    const z = S.z; const f = z ? z.fortschritt : {};
    const offen = z && z.dateien.length && !f.fertig && !f.laeuft;
    const fv = S.faelle;
    view.innerHTML = `<section class="flaeche seite">
      <div class="start-oben">
        <div class="start-neu">
          <div><h1>Neuer Vorgang</h1><p class="muted" style="margin-top:2px">Dateien ablegen, prüfen, anonymisierte Kopien erhalten. Sie können Dateien auch an eine beliebige Stelle in dieses Fenster ziehen.</p></div>
          <div class="kacheln">
            <button class="kachel haupt" data-c="dateien" data-tour="neu-dateien">${ico("datei", "l")}<b>Dateien hinzufügen</b><span>PDF, Word, Excel, Text, auch gescannt</span></button>
            <button class="kachel" data-c="ordner" data-tour="neu-ordner">${ico("ordner", "l")}<b>Ordner öffnen</b><span>Kopien landen neben den Originalen</span></button>
            <button class="kachel" data-c="text" data-tour="neu-text">${ico("text", "l")}<b>Text einfügen</b><span>Aus E-Mail oder Zwischenablage</span></button>
          </div>
          ${f.fehler ? `<div class="notice danger">${ico("warn")}<div><b>Das hat nicht geklappt.</b> ${esc(f.fehler)} <button class="linkbtn" data-c="protokoll">Details</button></div></div>` : ""}
          ${offen ? `<div class="dateiliste">${z.dateien.map((d) => `<div class="datei"><span class="ext">${esc(d.name.split(".").pop())}</span><span class="name">${esc(d.name)}</span><span class="muted small">${kb(d.groesse)}</span><button class="iconbtn" data-del="${esc(d.name)}" aria-label="${esc(d.name)} entfernen">${ico("x")}</button></div>`).join("")}</div>
            <div class="row"><button class="btn primary" data-c="analyse">Erkennen und prüfen</button></div>` : ""}
          <div class="row muted" style="font-size:13px">${ico("play")}Zum ersten Mal hier? <button class="linkbtn" data-c="tour" data-tour="start-einfuehrung">Einführung starten</button> · 5 Minuten, mit Beispieldokument</div>
        </div>
        <section class="fristen" aria-labelledby="fristen-t" data-tour="fristen">
          <div class="row between"><h2 id="fristen-t">Fälle und Fristen ${hilfeKnopf("frist")}</h2><button class="linkbtn" data-c="faelle">Alle Fälle</button></div>
          ${!fv ? `<span class="muted small">Wird geladen …</span>` : fristenPanel(fv)}
        </section>
      </div>
      <section aria-labelledby="zuletzt-t" style="display:flex;flex-direction:column;gap:8px;min-width:0" data-tour="zuletzt">
        <div class="row"><h2 id="zuletzt-t">Zuletzt bearbeitet</h2><span class="muted small">Nur Vorgangsname und Fall, keine Inhalte</span><span style="flex:1"></span>
          <button class="btn klein" id="ausw-del" ${S.auswahl.size ? "" : "disabled"}>Auswahl löschen</button></div>
        ${!fv ? "" : fv.vorgaenge.length ? `<div class="tabelle-box"><table class="tabelle"><thead><tr><th style="width:28px"><input type="checkbox" id="ausw-alle" aria-label="Alle auswählen"></th><th>Vorgang</th><th>Fall</th><th>Dateien</th><th>Angaben</th><th>Geändert</th><th>Stand</th><th style="width:40px"><span class="sr">Aktionen</span></th></tr></thead><tbody>
          ${fv.vorgaenge.slice(0, 30).map((v) => `<tr><td><input type="checkbox" data-v="${v.id}" ${S.auswahl.has(v.id) ? "checked" : ""} aria-label="${esc(v.name)} auswählen"></td>
            <td><b>${esc(v.name)}</b></td><td class="mono">${esc(v.fall_name)}</td><td>${v.dateien}</td><td>${v.angaben}</td><td>${zeitText(v.zeit)}</td>
            <td><span class="stand"><i class="punkt"></i>Anonymisiert</span></td><td><button class="iconbtn" data-menue="${v.id}" aria-label="Aktionen für ${esc(v.name)}">${ico("punkte")}</button></td></tr>`).join("")}
          </tbody></table></div>` : `<div class="leer">Noch keine Vorgänge. Nach dem ersten Anonymisieren stehen sie hier.</div>`}
      </section>
    </section>`;
    const tun = { dateien: () => neueDateien(dateiWaehlen), ordner: () => neueDateien(ordnerWaehlen), text: () => neueDateien(textDialog), tour: () => tourStarten(""),
      analyse: () => analyseStarten(), faelle: () => zeige("faelle"), protokoll: () => zeige("protokoll") };
    $$("[data-c]").forEach((b) => (b.onclick = () => tun[b.dataset.c] && tun[b.dataset.c]()));
    $$("[data-del]").forEach((b) => (b.onclick = async () => { S.z = await api("/datei-entfernen", { json: { name: b.dataset.del } }); render(); }));
    $$("[data-v]").forEach((c) => (c.onchange = () => { c.checked ? S.auswahl.add(c.dataset.v) : S.auswahl.delete(c.dataset.v); $("#ausw-del").disabled = !S.auswahl.size; }));
    const alle = $("#ausw-alle"); if (alle) alle.onchange = () => { $$("[data-v]").forEach((c) => { c.checked = alle.checked; c.onchange(); }); };
    $("#ausw-del").onclick = () => loeschDialog({ vorgaenge: [...S.auswahl] });
    $$("[data-menue]").forEach((b) => (b.onclick = () => vorgangMenue(b, fv.vorgaenge.find((v) => v.id === b.dataset.menue))));
    $$("[data-fall-verl]").forEach((b) => (b.onclick = () => verlaengernMenue(b, b.dataset.fallVerl)));
    $$("[data-fall-zu]").forEach((b) => (b.onclick = () => fallAktion(b.dataset.fallZu, "abschliessen")));
  }
  function fristenPanel(fv) {
    const h = fv.hinweise[0];
    const andere = fv.faelle.filter((f) => !h || f.id !== h.id).slice(0, 3);
    return `${h ? `<div class="notice warn" style="flex-direction:column;gap:8px" data-tour="fristhinweis"><div><span class="mono" style="font-weight:600;color:var(--ink)">${esc(h.name)}</span> · ${h.angaben.length} gelernte Angaben werden am <b>${datum(h.loeschdatum)}</b> gelöscht</div>
        <div class="row"><button class="btn klein" data-fall-verl="${h.id}">Verlängern</button><button class="btn klein" data-fall-zu="${h.id}">Fall abgeschlossen</button></div></div>` : ""}
      ${andere.map((f) => `<div class="zeile"><span class="mono">${esc(f.name)}</span><span class="muted">${f.angaben.length} Angaben · ${fristText(f)}</span></div>`).join("")}
      ${!fv.faelle.length ? `<span class="muted small">Noch keine Fälle. Lokanon legt sie beim Anonymisieren an, meist aus dem Aktenzeichen.</span>` : ""}`;
  }
  const fristText = (f) => (f.status === "laeuft" ? "Mandat läuft" : f.loeschdatum ? `bis ${datum(f.loeschdatum)}` : "ohne Frist");
  function zeitText(iso) {
    const d = new Date(iso); const heute = new Date();
    const uhr = d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
    if (d.toDateString() === heute.toDateString()) return `Heute, ${uhr}`;
    const gestern = new Date(heute); gestern.setDate(heute.getDate() - 1);
    if (d.toDateString() === gestern.toDateString()) return `Gestern, ${uhr}`;
    return d.toLocaleDateString("de-DE");
  }
  function vorgangMenue(anker, v) {
    const ordner = v.kopien && v.kopien[0] ? v.kopien[0].replace(/[\\/][^\\/]*$/, "") : "";
    menue(anker, [...(ordner ? [{ label: "Ordner mit den Kopien öffnen", fn: () => oeffnen(ordner) }] : []),
      { label: "Vorgang löschen …", fn: () => loeschDialog({ vorgaenge: [v.id] }), gefahr: true },
      { label: `Ganzen Fall ${v.fall_name} löschen …`, fn: () => loeschDialog({ faelle: [v.fall] }), gefahr: true }]);
  }

  // ------------------------------------------------------------ Vorgang: läuft
  function renderLaeuft() {
    const f = S.z.fortschritt; const anonym = f.fertig && !S.z.ergebnis;
    befehle(`<span class="hinweis">${anonym ? "Kopien werden erzeugt und gegengeprüft …" : "Lokanon liest und erkennt …"}</span>`);
    view.innerHTML = `<section class="flaeche fortschritt" aria-live="polite">
      <div class="muted">${anonym ? "Dateien werden erzeugt" : "Lokanon liest und erkennt"}</div>
      <h2 id="p-schritt">${esc(f.schritt || "Modelle laden …")}</h2>
      <p class="muted" id="p-datei">${esc(f.datei || " ")}</p>
      <div class="balken ${f.prozent < 5 ? "unbestimmt" : ""}" id="pbar"><i style="width:${f.prozent}%"></i></div>
      <p class="muted small">${S.status.modelle_bereit ? "Gescannte Seiten brauchen etwas länger (Texterkennung)." : "Beim ersten Start werden die Sprachmodelle geladen, das dauert ein bis zwei Minuten."}</p>
    </section>`;
    pollen();
  }

  // ------------------------------------------------------------ Vorgang: Prüfen
  const GRUPPEN_KURZ = { "Personen": "Personen", "Selbst markiert": "Selbst markiert", "Firmen und Einrichtungen": "Firmen", "Adressen und Kontakt": "Adressen",
    "Nummern und Kennzeichen": "Nummern", "Daten und Sonstiges": "Sonstiges" };
  function renderPruefen() {
    const z = S.z; const ids = z.identitaeten;
    const ersetzt = ids.filter((i) => i.aktiv).length, unsicher = ids.filter((i) => i.unsicher && i.aktiv).length;
    const gruppen = [...new Set(ids.map((i) => i.gruppe))];
    const kopieWort = z.dateien.length === 1 ? "Kopie" : "Kopien";
    const alt = $("#leinwand"); const docTop = alt ? alt.scrollTop : 0; const listTop = $("#liste") ? $("#liste").scrollTop : 0;
    befehle(`<button class="cmd" data-c="dateien">${ico("datei")}Dateien hinzufügen</button>
      <button class="cmd" data-c="ordner">${ico("ordner")}Ordner öffnen</button><span class="sep"></span>
      <button class="cmd" data-c="markieren" data-tour="befehl-markieren" aria-pressed="${S.markiermodus}" title="Taste M">${ico("markieren")}Übersehenes markieren</button>
      <button class="cmd" data-c="rueck" data-tour="befehl-rueckgaengig" ${z.rueckgaengig ? "" : "disabled"} title="${z.rueckgaengig ? "Rückgängig: " + esc(z.rueckgaengig) + " (Strg+Z)" : "Nichts zum Rückgängigmachen"}">${ico("rueck")}Rückgängig</button>
      <span class="fill"></span><span class="hinweis" title="${esc(z.ordner || z.ausgabe_ordner)}">${z.ordner ? "Kopien neben den Originalen" : "Kopien nach " + esc(z.ausgabe_ordner)}</span>
      <button class="btn primary" data-c="anon" data-tour="befehl-anonymisieren" title="Jetzt die anonymisierte ${kopieWort} schreiben: ${ersetzt} ${ersetzt === 1 ? "Angabe wird" : "Angaben werden"} ersetzt">${ico("schild")}Anonymisierte ${kopieWort} erstellen<span class="zahl">${ersetzt} ${ersetzt === 1 ? "Angabe" : "Angaben"}</span></button>`);
    const fehler = z.fortschritt.fehler;
    view.innerHTML = `
      <section class="flaeche dokbereich" aria-label="Dokument" data-tour="dokument">
        <div class="dokkopf"><div class="reiter" role="tablist" data-tour="reiter">${z.dokumente.map((d, i) => `<button role="tab" data-i="${i}" aria-selected="${i === S.docIndex}" title="${esc(d.name)}">${/\.pdf$/i.test(d.name) && (z.dateien[i] || {}).ocr ? ico("scan") : ""}${esc(d.name)}</button>`).join("")}</div>
          <span class="fill"></span>
          <div class="umschalter" role="group" aria-label="Ansicht"><button data-m="markiert" aria-pressed="${S.docMode === "markiert"}">Original mit Markierungen</button><button data-m="anonym" aria-pressed="${S.docMode === "anonym"}">Anonymisiert</button></div></div>
        <div class="leinwand" id="leinwand"><div class="docview ${S.markiermodus ? "markiermodus" : ""}" id="docview" tabindex="0" data-tour="docview"></div></div>
        <div class="legende"><span><i style="background:var(--mark-person)"></i>Person</span><span><i style="background:var(--mark-firma)"></i>Firma</span><span><i style="background:var(--mark-ort)"></i>Adresse, Kontakt</span><span><i style="background:var(--mark-nummer)"></i>Nummer</span><span><i style="background:var(--mark-eigene)"></i>selbst markiert</span><span><i style="outline:1px dashed var(--line-3)"></i>bleibt stehen</span></div>
      </section>
      <aside class="flaeche pruefbereich" aria-label="Prüfen" data-tour="pruefbereich">
        <div class="pruefkopf" data-tour="pruefen-kopf">
          <div><h1>${ids.length} ${ids.length === 1 ? "Angabe" : "Angaben"}</h1><div class="zahlen">${ersetzt} werden ersetzt · ${ids.length - ersetzt} ${ids.length - ersetzt === 1 ? "bleibt" : "bleiben"} stehen · ${z.dateien.length} ${z.dateien.length === 1 ? "Datei" : "Dateien"}</div></div>
          <div class="fallzeile" data-tour="fallzeile">Fall: <span class="mono">${esc(z.fall || "noch keiner")}</span>${z.fall_bestaetigt ? "" : `<span class="muted small">(vorgeschlagen)</span>`}<button class="linkbtn" id="fall-aendern">ändern</button>${hilfeKnopf("fall")}</div>
          ${fehler ? `<div class="notice danger">${ico("warn")}<div><b>Das Anonymisieren hat nicht geklappt.</b> ${esc(fehler)} <button class="linkbtn" data-c="protokoll">Details</button></div></div>` : ""}
          ${unsicher ? `<div class="notice warn" role="status" data-tour="hinweis-ansehen">${ico("warn")}<div><b>${unsicher} ${unsicher === 1 ? "Angabe" : "Angaben"} bitte ansehen.</b> Lokanon ersetzt im Zweifel. Schalten Sie aus, was kein Personenbezug ist. <button class="linkbtn" data-f="unsicher">Nur diese zeigen</button></div></div>`
            : `<div class="notice ok">${ico("check")}<div><b>Alles eindeutig.</b> Prüfen Sie die Liste und das Dokument, dann „Anonymisierte ${kopieWort} erstellen“.</div></div>`}
        </div>
        <div class="pivot" role="tablist" aria-label="Filter" data-tour="filter">${["alle", ...gruppen, "unsicher"].map((g) => {
          const n = g === "alle" ? ids.length : g === "unsicher" ? unsicher : ids.filter((i) => i.gruppe === g).length;
          return `<button role="tab" data-f="${esc(g)}" aria-selected="${S.filter === g}">${g === "alle" ? "Alle" : g === "unsicher" ? "Ansehen" : esc(GRUPPEN_KURZ[g] || g)} ${n}</button>`; }).join("")}</div>
        <div class="liste" id="liste"></div>
        <div class="nachtrag" data-tour="nachtrag"><span><label for="nachtrag">Fehlt etwas? Im Dokument markieren (Taste M) oder hier eintragen</label>${hilfeKnopf("markieren")}</span>
          <div class="row" style="flex-wrap:nowrap"><input class="input" id="nachtrag" placeholder="z. B. Kundennummer 48213, mehrere mit Komma"><button class="btn" id="btn-nachtrag">Suchen</button></div></div>
        <div class="abschluss" data-tour="pruefen-abschluss"><p><b>Alles geprüft?</b> Dann schreibt Lokanon ${z.dateien.length === 1 ? "die anonymisierte Kopie" : `${z.dateien.length} anonymisierte Kopien`} ${z.ordner ? "neben die Originale" : "in den Ablageordner"}. Ihre Originale bleiben unverändert.</p>
          <button class="btn primary" data-c="anon">${ico("schild")}Anonymisierte ${kopieWort} erstellen</button></div>
      </aside>`;
    renderListe();
    renderDocPanel();
    $("#leinwand").scrollTop = docTop; $("#liste").scrollTop = listTop;
    const tun = { dateien: () => neueDateien(dateiWaehlen), ordner: () => neueDateien(ordnerWaehlen), markieren: () => markiermodus(!S.markiermodus),
      rueck: rueckgaengig, anon: anonymisieren, protokoll: () => zeige("protokoll") };
    $$("[data-c]").forEach((b) => (b.onclick = () => tun[b.dataset.c] && tun[b.dataset.c]()));
    $$("[data-f]").forEach((b) => (b.onclick = () => { S.filter = b.dataset.f; renderPruefen(); }));
    $$(".reiter [data-i]").forEach((b) => (b.onclick = () => { S.docIndex = +b.dataset.i; S.stelle = null; renderPruefen(); }));
    $$(".umschalter [data-m]").forEach((b) => (b.onclick = () => { S.docMode = b.dataset.m; renderPruefen(); }));
    $("#fall-aendern").onclick = fallDialog;
    $("#btn-nachtrag").onclick = () => {
      const t = $("#nachtrag").value.split(",").map((s) => s.trim()).filter(Boolean);
      if (t.length) analyseStarten(t);
    };
    $("#nachtrag").onkeydown = (e) => { if (e.key === "Enter") $("#btn-nachtrag").click(); };
  }
  function fallDialog() {
    const namen = S.faelle ? S.faelle.faelle.map((f) => f.name) : [];
    const m = modal(`${kopf("Fall für diesen Vorgang", "Lokanon schlägt das Aktenzeichen aus dem Dokument vor. Gelernte Angaben und Fristen hängen am Fall.")}
      <div class="minhalt"><label class="feld"><span class="small muted">Aktenzeichen oder Name des Falls</span><input class="input" id="fall-in" list="fall-liste" value="${esc(S.z.fall || "")}" autofocus></label>
        <datalist id="fall-liste">${namen.map((n) => `<option value="${esc(n)}">`).join("")}</datalist>
        <p class="muted small">Tipp: Nehmen Sie das Aktenzeichen, keine Namen. Der Fall erscheint in der Übersicht und im Löschprotokoll (dort nur als Nummer).</p></div>
      <div class="mfuss"><button class="btn x">Abbrechen</button><button class="btn primary" id="fall-ok">Übernehmen</button></div>`);
    $("#fall-in", m).focus();
    const ok = async () => { try { S.z = await api("/fall-setzen", { json: { name: $("#fall-in", m).value } }); closeModal(); render(); melde("fall-gesetzt"); } catch (e) { toast(e.message, "danger"); } };
    $("#fall-ok", m).onclick = ok; $("#fall-in", m).onkeydown = (e) => { if (e.key === "Enter") ok(); };
  }
  function markiermodus(an) {
    S.markiermodus = an;
    const b = $("[data-c=markieren]"); if (b) b.setAttribute("aria-pressed", an);
    const dv = $("#docview"); if (dv) dv.classList.toggle("markiermodus", an);
    if (an && S.docMode !== "markiert") { S.docMode = "markiert"; renderPruefen(); }
    if (an) toast("Markieren: Wort anklicken oder mehrere Wörter mit der Maus überstreichen.", "");
    melde(an ? "markiermodus-an" : "markiermodus-aus");
  }

  // Dokument: Original mit Markierungen oder anonymisierte Fassung
  function renderDocPanel() {
    const z = S.z; const d = z.dokumente[S.docIndex]; const dv = $("#docview"); if (!dv) return;
    if (d) { if (S.docMode === "markiert") dv.innerHTML = d.markiert_html; else dv.textContent = d.anonym; }
    dv.onclick = (e) => {
      if (!getSelection().isCollapsed) return;
      const m = e.target.closest(".m");
      if (m) { if (m.dataset.ph) zeigeKarte(m.dataset.ph); stellenLeiste(m); return; }
      if (S.markiermodus && S.docMode === "markiert") wortAnklicken(e);
    };
    dv.onmouseup = () => setTimeout(auswahlPruefen, 0);
    dv.onkeyup = (e) => { if (e.shiftKey) auswahlPruefen(); };
    if (S.stelle) markiereStelle(false);
  }
  // Markiermodus: ein Klick markiert das ganze Wort unter dem Mauszeiger
  function wortAnklicken(e) {
    let node, off;
    if (document.caretPositionFromPoint) { const p = document.caretPositionFromPoint(e.clientX, e.clientY); if (p) { node = p.offsetNode; off = p.offset; } }
    else if (document.caretRangeFromPoint) { const r = document.caretRangeFromPoint(e.clientX, e.clientY); if (r) { node = r.startContainer; off = r.startOffset; } }
    if (!node || node.nodeType !== 3) return;
    const t = node.textContent; let a = off, b = off;
    while (a > 0 && /[\wäöüÄÖÜß\-]/.test(t[a - 1])) a--;
    while (b < t.length && /[\wäöüÄÖÜß\-]/.test(t[b])) b++;
    if (b - a < 2) return;
    const r = document.createRange(); r.setStart(node, a); r.setEnd(node, b);
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
    auswahlPruefen();
  }
  // Zeichenposition im Originaltext: alles vor (node, off) ohne die Platzhalter-Etiketten
  function offsetBis(dv, node, off) {
    const r = document.createRange(); r.setStart(dv, 0); r.setEnd(node, off);
    const f = r.cloneContents(); f.querySelectorAll("sup.ph").forEach((x) => x.remove());
    return f.textContent.length;
  }
  function bereichAus(dv, s, e) {
    const w = document.createTreeWalker(dv, NodeFilter.SHOW_TEXT, { acceptNode: (n) => (n.parentElement.closest("sup.ph") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    const r = document.createRange(); let pos = 0, n, start = false;
    while ((n = w.nextNode())) {
      const len = n.textContent.length;
      if (!start && s <= pos + len) { r.setStart(n, s - pos); start = true; }
      if (start && e <= pos + len) { r.setEnd(n, e - pos); return r; }
      pos += len;
    }
    return null;
  }
  function leisteZu() { const l = $("#leiste"); if (l) l.remove(); }
  function leisteZeigen(html, rect, tour = "") {
    leisteZu();
    const p = $("#leinwand"); const pr = p.getBoundingClientRect();
    const scrollRaum = p.scrollHeight - p.clientHeight - p.scrollTop;  // vor dem Einfügen messen: das Fenster selbst zählt sonst mit
    const l = document.createElement("div"); l.className = "leiste"; l.id = "leiste"; l.setAttribute("role", "dialog"); if (tour) l.dataset.tour = tour; l.innerHTML = html;
    p.appendChild(l);
    $$("[data-lz=abbrechen]", l).forEach((b) => (b.onclick = () => { leisteZu(); getSelection().removeAllRanges(); melde("leiste-abgebrochen"); }));
    // Sichtbarer Teil des Dokumentbereichs (auch wenn das Fenster ihn unten abschneidet). Unter der Auswahl, wenn dort
    // Platz ist, sonst darüber, sonst dort, wo mehr Platz ist; nie oben oder unten aus dem sichtbaren Teil heraus.
    const rahmenR = (p.closest(".dokbereich") || p).getBoundingClientRect();
    const sichtOben = Math.max(pr.top, rahmenR.top, 0) + 8, sichtUnten = Math.min(pr.bottom, rahmenR.bottom, window.innerHeight) - 8;
    l.style.maxHeight = Math.max(160, sichtUnten - sichtOben) + "px";
    const breite = l.offsetWidth; let hoehe = l.offsetHeight;
    let oben = rect.top, unten = rect.bottom, y, x = rect.left;
    if (sichtUnten - unten >= hoehe + 8) y = unten + 8;
    else if (oben - sichtOben >= hoehe + 8) y = oben - hoehe - 8;
    else if (pr.right - 8 - rect.right >= breite + 8) { x = rect.right + 8; y = oben - 24; }
    else if (rect.left - pr.left - 8 >= breite + 8) { x = rect.left - breite - 8; y = oben - 24; }
    else {
      // Niedriges, schmales Fenster: Dokument so weit hochschieben, dass unter dem Wort Platz ist; was dann noch
      // fehlt, scrollt im Fenster selbst. Das Wort bleibt immer sichtbar.
      const dy = Math.max(0, Math.min(unten + hoehe + 16 - sichtUnten, oben - sichtOben - 8, scrollRaum));
      if (dy) { const vor = p.scrollTop; p.scrollTop += dy; const echt = p.scrollTop - vor; oben -= echt; unten -= echt; }
      const platzUnten = sichtUnten - unten - 8, platzOben = oben - sichtOben - 8;
      if (platzUnten >= Math.min(hoehe, 200) || platzUnten >= platzOben) { l.style.maxHeight = Math.max(120, platzUnten) + "px"; hoehe = l.offsetHeight; y = unten + 8; }
      else { l.style.maxHeight = Math.max(120, platzOben) + "px"; hoehe = l.offsetHeight; y = oben - 8 - hoehe; }
    }
    y = Math.max(sichtOben, Math.min(y, sichtUnten - hoehe));
    l.style.top = y - pr.top + p.scrollTop + "px";
    l.style.left = Math.max(p.scrollLeft + 8, Math.min(x - pr.left + p.scrollLeft, p.scrollLeft + pr.width - breite - 8)) + "px";
    return l;
  }
  document.addEventListener("mousedown", (e) => { const l = $("#leiste"); if (l && !l.contains(e.target) && !e.target.closest("#docview") && !e.target.closest(".fuehrung")) leisteZu(); });
  document.addEventListener("keydown", (e) => {
    const tippt = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "") || !$("#modal-root").hidden;
    const pruefen = S.ansicht === "vorgang" && S.z && S.z.fortschritt.fertig && !S.z.ergebnis;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !tippt && pruefen && S.z.rueckgaengig) { e.preventDefault(); rueckgaengig(); }
    if (e.key.toLowerCase() === "m" && !e.ctrlKey && !e.metaKey && !e.altKey && !tippt && pruefen) { e.preventDefault(); markiermodus(!S.markiermodus); }
  });
  async function rueckgaengig() {
    try { const z = await api("/rueckgaengig", { method: "POST" }); S.z = z; leisteZu(); renderPruefen(); toast(`Rückgängig: ${z.rueckgaengig}`, "ok"); melde("rueckgaengig"); }
    catch (e) { toast(e.message, "danger"); }
  }
  function mitRueckgaengig(text) { toast(text, "ok", { label: "Rückgängig", fn: rueckgaengig }); }

  async function auswahlPruefen() {
    const dv = $("#docview"); const sel = getSelection();
    if (!dv || S.docMode !== "markiert" || sel.isCollapsed || !sel.rangeCount) return;
    const r = sel.getRangeAt(0);
    if (!dv.contains(r.commonAncestorContainer)) return;
    const s = offsetBis(dv, r.startContainer, r.startOffset), e = offsetBis(dv, r.endContainer, r.endOffset);
    if (e - s < 2) return;
    let a;
    try { a = await api("/auswahl", { json: { dok: S.docIndex, s, e } }); } catch (err) { toast(err.message, "danger"); return; }
    markierLeiste(a, r.getBoundingClientRect());
  }
  function zaehlung(a) {
    const neu = a.dateien.flatMap((f) => f.stellen.map((st) => ({ ...st, dok: f.i }))).filter((st) => !st.schon);
    const andere = a.dateien.filter((f) => f.i !== S.docIndex && f.stellen.some((st) => !st.schon));
    return { neu, andere };
  }
  // Markierfenster direkt an der Auswahl: Art, Anzahl Stellen, „Nur hier“ oder „Überall ersetzen“
  function markierLeiste(a, rect) {
    const ids = S.z.identitaeten;
    const zeigen = (a, art) => {
      const { neu, andere } = zaehlung(a);
      const l = leisteZeigen(`
        <div class="kopf"><b>„${esc(a.begriff)}“ anonymisieren</b><span class="muted small">${neu.length} ${neu.length === 1 ? "Stelle" : "Stellen"}</span></div>
        <div class="gruppe"><span class="lbl" id="lz-art-t">Was ist es?</span>
          <div class="arten" role="radiogroup" aria-labelledby="lz-art-t" data-tour="markier-arten">${a.arten.map(([k, t]) => `<button type="button" role="radio" data-k="${k}" aria-checked="${k === art}">${esc(t)}</button>`).join("")}</div></div>
        ${ids.length ? `<label class="gruppe" data-tour="markier-zuordnung"><span class="lbl">Ersetzen durch</span>
          <select id="lz-zu"><option value="">einen neuen Platzhalter</option>${ids.map((i) => `<option value="${esc(i.ph)}">denselben wie „${esc(i.name)}“ ${esc(i.anzeige)}</option>`).join("")}</select>
          <small>Spitzname, Kürzel oder andere Schreibweise einer schon gefundenen Angabe? Dann deren Platzhalter wählen.</small></label>` : ""}
        <div class="muted small">${andere.length ? `Auch in ${andere.map((f) => esc(f.name) + ` (${f.stellen.filter((st) => !st.schon).length}×)`).join(", ")} · ` : ""}${neu.length > 1 ? `<button class="linkbtn" id="lz-einzeln">Stellen ansehen</button>` : ""}${a.gesamt - neu.length ? ` · ${a.gesamt - neu.length} schon markiert` : ""}</div>
        ${a.warnung ? `<div class="notice warn">${ico("warn")}<div>Sehr häufig. Bitte die Stellen einzeln ansehen.</div></div>` : ""}
        <div class="aktionen"><button class="btn klein abbrechen" data-lz="abbrechen" title="Nichts markieren (Esc)">Abbrechen</button>${neu.length > 1 ? `<button class="btn klein" id="lz-hier">Nur hier</button>` : ""}
          <button class="btn klein primary" id="lz-alle" data-tour="markier-ueberall">${neu.length > 1 ? (a.warnung ? "Einzeln ansehen" : "Überall ersetzen") : "Ersetzen"}</button></div>`, rect, "markierfenster");
      const zu = () => ($("#lz-zu", l) || {}).value || "";
      $$(".arten [data-k]", l).forEach((b) => (b.onclick = async () => { try { const n = await api("/auswahl", { json: { dok: a.dok, s: a.s, e: a.e, art: b.dataset.k } }); a = n; zeigen(n, b.dataset.k); melde("art-gewaehlt", { entity: b.dataset.k }); } catch (e) { toast(e.message, "danger"); } }));
      const hier = [{ dok: a.dok, s: a.s, e: a.e }];
      const aktArt = () => ($(".arten [aria-checked=true]", l) || {}).dataset?.k || a.art;
      if ($("#lz-einzeln", l)) $("#lz-einzeln", l).onclick = () => { leisteZu(); fundDialog(a, aktArt(), zu()); };
      if ($("#lz-hier", l)) $("#lz-hier", l).onclick = () => markierenAnwenden(a, aktArt(), hier, zu());
      $("#lz-alle", l).onclick = () => (a.warnung && neu.length > 1 ? (leisteZu(), fundDialog(a, aktArt(), zu())) : markierenAnwenden(a, aktArt(), neu.length > 1 ? neu.map((st) => ({ dok: st.dok, s: st.s, e: st.e })) : hier, zu()));
    };
    zeigen(a, a.art);
    melde("auswahl", { begriff: a.begriff });
  }
  async function markierenAnwenden(a, art, stellen, gehoert_zu) {
    try {
      const z = await api("/markieren", { json: { begriff: a.begriff, art, stellen, ursprung: { dok: a.dok, s: a.s }, gehoert_zu } });
      S.z = z; leisteZu(); closeModal(); getSelection().removeAllRanges(); renderPruefen();
      mitRueckgaengig(`${z.neu} ${z.neu === 1 ? "Stelle" : "Stellen"} markiert`);
      melde("markiert", { begriff: a.begriff, entity: art });
    } catch (e) { toast(e.message, "danger"); }
  }
  function fundDialog(a, art, gehoert_zu) {
    const zeile = (f, st, k) => `<label class="fund" data-dok="${f.i}" data-s="${st.s}" data-e="${st.e}">
        <input type="checkbox" data-k="${k}" ${st.schon ? "disabled" : "checked"} aria-label="Stelle übernehmen">
        <span><span class="ctx">${st.ctx}</span>${st.schon ? `<span class="schon"> · gehört schon zu ${esc(st.schon.includes("_") ? "[" + st.schon + "]" : st.schon)}</span>` : st.gruppe === "teil" ? `<span class="schon"> · Namensteil</span>` : ""}</span></label>`;
    let k = 0; const alle = [];
    const listen = a.dateien.map((f) => `<div class="fund-datei">${esc(f.name)} · ${f.stellen.length}</div>${f.stellen.map((st) => { alle.push({ dok: f.i, ...st }); return zeile(f, st, k++); }).join("")}`).join("");
    const m = modal(`${kopf(`„${esc(a.begriff)}“ im Vorgang`, `${a.gesamt} Fundstellen. Ein Klick auf den Text zeigt die Stelle im Dokument.`)}
      <div class="minhalt"><div class="fund-kopf"><button class="linkbtn" id="fd-keine">keine</button><button class="linkbtn" id="fd-alle">alle</button></div>
      ${a.warnung ? `<div class="notice warn">${ico("warn")}<div>Sehr häufig. Vielleicht ist der Begriff zu allgemein.</div></div>` : ""}
      <div class="fund-liste">${listen}</div></div>
      <div class="mfuss"><button class="btn x">Abbrechen</button><button class="btn primary" id="fd-ok">Auswahl anwenden</button></div>`, { wide: true });
    const boxen = () => $$(".fund input", m).filter((i) => !i.disabled);
    const zaehlen = () => { const n = boxen().filter((i) => i.checked).length; $("#fd-ok", m).textContent = n ? `${n} ${n === 1 ? "Stelle" : "Stellen"} anwenden` : "Nichts ausgewählt"; $("#fd-ok", m).disabled = !n; };
    boxen().forEach((i) => (i.onchange = zaehlen)); zaehlen();
    $("#fd-keine", m).onclick = () => { boxen().forEach((i) => (i.checked = false)); zaehlen(); };
    $("#fd-alle", m).onclick = () => { boxen().forEach((i) => (i.checked = true)); zaehlen(); };
    $$(".fund .ctx", m).forEach((c) => (c.onclick = (e) => { e.preventDefault(); const f = c.closest(".fund"); closeModal(); zeigeOffset(+f.dataset.dok, +f.dataset.s, +f.dataset.e); }));
    $("#fd-ok", m).onclick = () => markierenAnwenden(a, art, boxen().filter((i) => i.checked).map((i) => { const st = alle[+i.dataset.k]; return { dok: st.dok, s: st.s, e: st.e }; }), gehoert_zu);
  }
  function zeigeOffset(di, s, e) {
    if (S.docIndex !== di || S.docMode !== "markiert") { S.docIndex = di; S.docMode = "markiert"; renderPruefen(); }
    const dv = $("#docview"); const r = bereichAus(dv, s, e); if (!r) return;
    const lw = $("#leinwand"); const rr = r.getBoundingClientRect(), lr = lw.getBoundingClientRect();
    lw.scrollTo({ top: lw.scrollTop + rr.top - lr.top - lw.clientHeight / 2, behavior: "smooth" });
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  }
  // Klick auf eine Markierung: nicht anonymisieren (nur hier / im ganzen Vorgang / künftig immer) oder doch anonymisieren
  function stellenLeiste(m) {
    const dok = S.docIndex, s = +m.dataset.s, e = +m.dataset.e;
    const wort = m.firstChild ? m.firstChild.textContent : m.textContent;
    const i = S.z.identitaeten.find((x) => x.ph === m.dataset.ph);
    const rect = m.getBoundingClientRect();
    const l = m.classList.contains("bleibt")
      ? leisteZeigen(`<div class="kopf"><b>„${esc(wort)}“ bleibt stehen</b></div><div class="aktionen"><button class="btn klein abbrechen" data-lz="abbrechen" title="Nichts ändern (Esc)">Abbrechen</button><button class="btn klein primary" data-a="wieder">Doch anonymisieren</button></div>`, rect)
      : leisteZeigen(`<div class="kopf"><b>„${esc(wort)}“ wird zu <span class="ph">${esc(i ? i.anzeige : "")}</span></b></div>
          <div class="muted small">Nicht anonymisieren:</div>
          <div class="wahl">
            <button data-a="hier">Nur hier<small>${/\.(pdf|docx|xlsx|csv)$/i.test(S.z.dokumente[dok].name) ? "In der PDF- oder Word-Kopie wird derselbe Text trotzdem überall ersetzt" : "Diese eine Stelle bleibt stehen"}</small></button>
            <button data-a="vorgang">Im ganzen Vorgang<small>${i ? `Alle ${i.anzahl} Stellen von „${esc(i.name)}“` : "Alle Stellen dieser Angabe"}</small></button>
            <button data-a="immer">Künftig immer stehen lassen<small>Wird verschlüsselt gemerkt, ohne Frist (meist Fachbegriffe)</small></button>
          </div>
          <div class="aktionen"><button class="btn klein abbrechen" data-lz="abbrechen" title="Nichts ändern (Esc)">Abbrechen</button></div>`, rect);
    $$("[data-a]", l).forEach((b) => (b.onclick = async () => {
      try {
        S.z = await api("/stelle", { json: { dok, s, e, aktion: b.dataset.a } }); leisteZu(); renderPruefen();
        mitRueckgaengig(b.dataset.a === "wieder" ? "Wird wieder anonymisiert" : b.dataset.a === "hier" ? "Diese Stelle bleibt stehen" : "Bleibt im ganzen Vorgang stehen");
      } catch (err) { toast(err.message, "danger"); }
    }));
  }
  function vorkommen(ph) {
    const out = [];
    S.z.dokumente.forEach((d, i) => { const n = d.markiert_html.split(`data-ph="${esc(ph)}"`).length - 1; for (let k = 0; k < n; k++) out.push([i, k]); });
    return out;
  }
  // Karte → Stelle: erster Klick zeigt das erste Vorkommen, jeder weitere das nächste (auch in anderen Dateien)
  function zeigeStelle(ph, weiter = false) {
    const occ = vorkommen(ph);
    if (!occ.length) return;
    const nr = weiter && S.stelle && S.stelle.ph === ph ? (S.stelle.nr + 1) % occ.length : 0;
    const [di] = occ[nr];
    S.stelle = { ph, nr, gesamt: occ.length, k: occ[nr][1] };
    if (S.docMode !== "markiert" || S.docIndex !== di) { S.docMode = "markiert"; S.docIndex = di; renderPruefen(); }
    else markiereStelle(true);
    const z = $(`.zeile[data-ph="${CSS.escape(ph)}"] .stelle-nr`); if (z) z.textContent = `Stelle ${nr + 1} von ${occ.length}`;
  }
  function markiereStelle(weich) {
    const dv = $("#docview"); if (!dv || !S.stelle) return;
    $$("[data-ph].aktuell, [data-ph].mit", dv).forEach((m) => { m.classList.remove("aktuell", "mit"); m.removeAttribute("data-flagge"); });
    const alle = $$(`[data-ph="${CSS.escape(S.stelle.ph)}"]`, dv);
    alle.forEach((m) => m.classList.add("mit"));
    const m = alle[S.stelle.k]; if (!m) return;
    const i = S.z.identitaeten.find((x) => x.ph === S.stelle.ph);
    m.classList.add("aktuell");
    if (i) m.dataset.flagge = `${i.anzeige} · ${S.stelle.gesamt} ${S.stelle.gesamt === 1 ? "Stelle" : "Stellen"}`;
    const lw = $("#leinwand");
    const ziel = m.getBoundingClientRect().top - lw.getBoundingClientRect().top + lw.scrollTop - lw.clientHeight / 2;
    lw.scrollTo({ top: Math.max(0, ziel), behavior: weich ? "smooth" : "auto" });
  }
  function zeigeKarte(ph) {
    if (S.filter !== "alle" && !S.z.identitaeten.some((i) => i.ph === ph && (S.filter === "unsicher" ? i.unsicher : i.gruppe === S.filter))) S.filter = "alle";
    S.gewaehlt = ph; renderPruefen();
    const el = $(`.zeile[data-ph="${CSS.escape(ph)}"]`); if (!el) return;
    el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    el.classList.remove("blitz"); void el.offsetWidth; el.classList.add("blitz");
  }
  function renderListe() {
    const z = S.z; let ids = z.identitaeten;
    if (S.filter === "unsicher") ids = ids.filter((i) => i.unsicher); else if (S.filter !== "alle") ids = ids.filter((i) => i.gruppe === S.filter);
    const liste = $("#liste");
    if (!ids.length) { liste.innerHTML = `<p class="leer">Nichts in dieser Auswahl.</p>`; return; }
    const gruppen = [...new Set(ids.map((i) => i.gruppe))];
    liste.innerHTML = gruppen.map((g) => {
      const items = ids.filter((i) => i.gruppe === g);
      return `<div class="grp"><span>${esc(g)}</span><span>${items.filter((i) => i.aktiv).length} von ${items.length} werden ersetzt</span></div>${items.map(zeile).join("")}`;
    }).join("");
    $$(".zeile", liste).forEach((el) => {
      const ph = el.dataset.ph; const i = S.z.identitaeten.find((x) => x.ph === ph);
      $(".zeile-kopf input", el).onchange = async (e) => { await identitaet({ ph, aktiv: e.target.checked }); melde(e.target.checked ? "karte-an" : "karte-aus", { name: i.name }); };
      $(".zeile-kopf", el).onclick = (e) => {
        if (e.target.closest("input, button")) return;
        S.gewaehlt = S.gewaehlt === ph ? null : ph; renderPruefen();
        if (S.gewaehlt) { zeigeStelle(ph); melde("karte-gewaehlt", { name: i.name }); }
      };
      const phb = $(".zeile-kopf .ph", el); if (phb && phb.tagName === "BUTTON") phb.onclick = () => { S.gewaehlt = ph; renderPruefen(); bezeichnungEdit(ph); };
      if (S.gewaehlt !== ph) return;
      $$(".vorschlaege [data-v]", el).forEach((b) => (b.onclick = async () => { await identitaet({ ph, bezeichnung: b.dataset.v }); melde("bezeichnung", { name: i.name, wert: b.dataset.v }); }));
      $$(".frage [data-ziel]", el).forEach((b) => (b.onclick = () => identitaet({ ph, zuordnen: { text: b.dataset.text, ph: b.dataset.ziel } })));
      const sel = $("select.zu", el); if (sel) sel.onchange = () => { if (sel.value) identitaet({ ph, gehoert_zu: sel.value }); };
      const tr = $("select.tr", el); if (tr) tr.onchange = () => { if (tr.value) identitaet({ ph, trennen: tr.value }); };
      const lb = $(".lern", el); if (lb) lb.onclick = () => stehenLernen(ph);
      const st = $(".stelle", el); if (st) st.onclick = () => zeigeStelle(ph, true);
      const be = $(".bez-aendern", el); if (be) be.onclick = () => bezeichnungEdit(ph);
      const br = $(".bez-reset", el); if (br) br.onclick = () => identitaet({ ph, bezeichnung: "" });
    });
    if (S.stelle) { const n = $(`.zeile[data-ph="${CSS.escape(S.stelle.ph)}"] .stelle-nr`); if (n) n.textContent = `Stelle ${S.stelle.nr + 1} von ${S.stelle.gesamt}`; }
  }
  function zeile(i) {
    const gew = S.gewaehlt === i.ph;
    const varianten = i.varianten.filter((v) => v !== i.name);
    const meta = i.unsicher && i.aktiv ? `<span class="meta warn">Bitte ansehen · ${esc(i.gruende.join("; "))}</span>`
      : `<span class="meta">${i.anzahl}× in ${i.dateien.length} ${i.dateien.length === 1 ? "Datei" : "Dateien"}${varianten.length ? " · auch „" + esc(varianten.slice(0, 2).join("“, „")) + "“" : ""}${i.aus_gedaechtnis ? " · gelernt" : ""}</span>`;
    const andere = S.z.identitaeten.filter((o) => o.ph !== i.ph && o.gruppe === i.gruppe);
    return `<div class="zeile ${gew ? "gewaehlt" : ""} ${i.aktiv ? "" : "aus"}" data-ph="${esc(i.ph)}" data-tour="zeile" data-name="${esc(i.name)}">
      <div class="zeile-kopf"><input type="checkbox" ${i.aktiv ? "checked" : ""} aria-label="${esc(i.name)} ersetzen" data-tour="zeile-schalter">
        <span class="text"><span class="name">${esc(i.name)}</span>${meta}</span>
        ${i.aktiv ? `<button class="ph" title="Platzhalter ändern">${esc(i.anzeige)}</button>` : `<span class="ph">bleibt</span>`}</div>
      ${gew ? `<div class="detail">
        <div>Erkannt: ${esc(i.belege.join(", ") || i.quellen.join(", "))} · ${esc(i.sicherheit)}${i.aus_einzeln ? ` · ${i.aus_einzeln} ${i.aus_einzeln === 1 ? "Stelle bleibt" : "Stellen bleiben"} stehen` : ""}</div>
        <div class="snip">${i.beispiel}</div>
        ${i.fragen.map((f) => `<div class="frage"><span>„${esc(f.text)}“ allein passt zu ${f.kandidaten.length} Personen. Wer ist gemeint?</span><span class="knoepfe">${f.kandidaten.map((k) => `<button class="btn klein" data-text="${esc(f.text)}" data-ziel="${esc(k.ph)}">${esc(k.name)}</button>`).join("")}</span></div>`).join("")}
        ${i.aktiv ? `<div class="knoepfe" data-tour="platzhalter-vorschlaege"><span>Platzhalter:</span><span class="vorschlaege">${i.vorschlaege.slice(0, 5).map((v) => `<button data-v="${esc(v)}">${esc(v)}</button>`).join("")}</span><button class="linkbtn bez-aendern">eigener Name</button>${i.bezeichnung ? `<button class="linkbtn bez-reset">Standard</button>` : ""}</div>` : ""}
        <div class="knoepfe">${andere.length ? `<select class="zu" aria-label="Gehört zu"><option value="">Gehört zu …</option>${andere.map((o) => `<option value="${esc(o.ph)}">${esc(o.name)}</option>`).join("")}</select>` : ""}
          ${i.varianten.length > 1 ? `<select class="tr" aria-label="Trennen"><option value="">Trennen …</option>${i.varianten.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("")}</select>` : ""}
          <button class="linkbtn stelle">Im Dokument zeigen</button><span class="stelle-nr"></span></div>
        ${!i.aktiv ? (i.gelernt ? `<div>Bleibt künftig immer stehen · änderbar unter Fälle und gelernte Angaben</div>` : `<div class="knoepfe"><button class="linkbtn lern">Künftig immer stehen lassen</button>${hilfeKnopf("stehen_lassen")}</div>`) : ""}
      </div>` : ""}
    </div>`;
  }
  function bezeichnungEdit(ph) {
    const el = $(`.zeile[data-ph="${CSS.escape(ph)}"] [data-tour=platzhalter-vorschlaege]`); const i = S.z.identitaeten.find((x) => x.ph === ph);
    if (!el) return;
    el.innerHTML = `<span class="phedit">[<input id="bez" value="${esc(i.bezeichnung || "")}" placeholder="${esc(i.ph)}" maxlength="40" aria-label="Eigener Platzhalter">]</span><button class="btn klein" id="bez-ok">Übernehmen</button><button class="linkbtn" id="bez-x">Abbrechen</button>`;
    const inp = $("#bez", el); inp.focus(); inp.select();
    const ok = async () => { await identitaet({ ph, bezeichnung: inp.value }); melde("bezeichnung", { name: i.name, wert: inp.value }); };
    $("#bez-ok", el).onclick = ok; inp.onkeydown = (e) => { if (e.key === "Enter") ok(); if (e.key === "Escape") renderPruefen(); };
    $("#bez-x", el).onclick = renderPruefen;
  }
  async function stehenLernen(ph) {
    const i = S.z.identitaeten.find((x) => x.ph === ph); if (!i) return;
    try { S.z = await api("/lernen", { json: { art: "stehen_lassen", begriffe: i.varianten } }); renderPruefen(); toast("Wird künftig nicht mehr vorgeschlagen", "ok"); }
    catch (e) { toast(e.message, "danger"); }
  }
  async function identitaet(body) {
    try { S.z = await api("/identitaet", { json: body }); renderPruefen(); } catch (e) { toast(e.message, "danger"); }
  }
  async function anonymisieren() {
    leisteZu(); markiermodus(false);
    try { await api("/anonymisieren", { method: "POST" }); await laden(); } catch (e) { toast(e.message, "danger"); }
  }

  // ------------------------------------------------------------ Vorgang: Fertig (mit Frage „künftig vorschlagen?“)
  function renderFertig() {
    const z = S.z; const r = z.ergebnis; const ok = r.dateien.filter((d) => d.status === "ok").length;
    const n = r.dateien.length, fehl = n - ok; const erw = z.erweitert || {};
    befehle(`<button class="cmd" data-c="ordner">${ico("ordner")}Ordner öffnen</button>
      <button class="cmd" data-c="pruefen">${ico("pfeilzurueck")}Zurück zum Prüfen</button><span class="sep"></span>
      ${erw.ki_anweisung ? `<button class="cmd" data-c="anweisung" data-tour="befehl-ki">${ico("kopie")}KI-Anweisung kopieren</button>` : ""}
      ${erw.rueckuebersetzung ? `<button class="cmd" data-c="zurueck" data-tour="befehl-zurueck">${ico("rueck")}Antwort zurückübersetzen</button>` : ""}
      <button class="cmd" data-c="protokoll">${ico("uhr")}Protokoll</button>
      <span class="fill"></span><button class="btn primary" data-c="neu">${ico("datei")}Neuer Vorgang</button>`);
    const dateiZeile = (d) => d.status === "ok"
      ? `<div class="ergebnis-datei"><span class="st">${ico("check")}</span><div style="flex:1;min-width:0"><b>${esc(d.ausgabe)}</b>${d.textfassung ? ` <span class="muted small">+ ${esc(d.textfassung)}</span>` : ""}<div class="muted small">aus ${esc(d.name)} · ${d.ersetzt} Stellen ersetzt · Gegenprüfung bestanden</div></div>
          <button class="btn klein" data-oeffne="${r.dateien.indexOf(d)}" data-tour="datei-oeffnen" title="${esc(d.ausgabe)} mit dem Standardprogramm öffnen">${ico("datei")}Öffnen</button></div>`
      : `<div class="ergebnis-datei fehl"><span class="st">${ico("warn")}</span><div style="flex:1;min-width:0"><b>${esc(d.name)}</b>: keine Kopie erzeugt
          <div class="small">${esc(d.hinweis)}</div>
          ${d.funde && d.funde.length ? `<ul class="funde">${d.funde.map((f) => `<li><b>„${esc(f.text)}“</b> ${esc(f.ort)}</li>`).join("")}</ul>` : ""}
          ${d.rat ? `<div><b>Was Sie tun können:</b> ${esc(d.rat)}</div>` : ""}
          ${d.ersatz ? `<div class="small">Stattdessen erzeugt: <b>${esc(d.textfassung)}</b> (geprüfte Textfassung ohne Layout)</div>` : ""}</div></div>`;
    const hinweise = r.hinweise.filter((t) => !r.dateien.some((d) => t.startsWith(d.name + ":")));
    view.innerHTML = `<section class="flaeche seite">
      <div class="ergebnis-kopf"><span class="zeichen ${fehl ? "fehl" : ""}">${ico(fehl ? "warn" : "check")}</span>
        <div><h1>${ok} von ${n} ${n === 1 ? "Datei" : "Dateien"} anonymisiert</h1><p class="muted">${!fehl ? "Alle Kopien sind gegengeprüft: kein Originaltext mehr gefunden." : `Bei ${fehl === 1 ? "einer Datei" : fehl + " Dateien"} hat es nicht geklappt. Unten steht, woran es lag und was Sie tun können.`}</p></div></div>
      ${r.merken && r.merken.length && !r.gemerkt ? merkenPanel(r) : ""}
      <div class="pfad"><span title="${esc(r.ordner)}">${esc(r.ordner)}</span><button class="btn klein" data-c="ordner">Ordner öffnen</button></div>
      <div data-tour="ergebnis-dateien">${r.dateien.filter((d) => d.status !== "ok").map(dateiZeile).join("")}${r.dateien.filter((d) => d.status === "ok").map(dateiZeile).join("")}</div>
      ${hinweise.length ? `<div class="notice warn">${ico("warn")}<div>${hinweise.map(esc).join("<br>")}</div></div>` : ""}
      ${r.schluessel_pfad ? `<div class="notice info">${ico("schloss")}<div>Schlüssel für die Rückübersetzung gespeichert (verschlüsselt): <code>${esc(r.schluessel_pfad)}</code></div></div>` : ""}
    </section>`;
    const tun = { ordner: () => oeffnen(r.ordner), neu: neuerVorgang, protokoll: () => zeige("protokoll"), anweisung: anweisungDialog, zurueck: zurueckDialog,
      pruefen: async () => { try { S.z = await api("/zurueck-zum-pruefen", { method: "POST" }); render(); } catch (e) { toast(e.message, "danger"); } } };
    $$("[data-c]").forEach((b) => (b.onclick = () => tun[b.dataset.c] && tun[b.dataset.c]()));
    $$("[data-oeffne]").forEach((b) => (b.onclick = async () => {
      try { await api("/ergebnis/oeffnen", { json: { i: +b.dataset.oeffne } }); melde("datei-geoeffnet"); } catch (e) { toast(e.message, "danger"); }
    }));
    if ($("#merken")) merkenVerhalten(r);
  }
  async function neuerVorgang() { S.z = await api("/leeren", { method: "POST" }); S.docIndex = 0; S.filter = "alle"; S.gewaehlt = null; S.stelle = null; zeige("start"); }
  function merkenPanel(r) {
    const bis = datum(plusMonate(r.frist_monate || 12));
    const namen = S.faelle ? S.faelle.faelle.map((f) => f.name) : [];
    return `<section class="merken" id="merken" aria-labelledby="merken-t" data-tour="merken">
      <div><h2 id="merken-t">${r.merken.length} ${r.merken.length === 1 ? "Angabe" : "Angaben"} für künftige Dokumente merken?</h2>
        <p class="muted" style="font-size:13px">Sie haben ${r.merken.length === 1 ? "sie" : "sie"} selbst markiert. Lokanon schlägt ${r.merken.length === 1 ? "sie" : "sie"} dann bei neuen Dokumenten von sich aus vor.</p></div>
      <label class="feld" data-tour="merken-fall"><span class="small"><b>Fall</b> ${hilfeKnopf("fall")}</span>
        <input class="input" id="merken-fall" list="merken-faelle" value="${esc(r.fall || "")}" style="max-width:320px"><datalist id="merken-faelle">${namen.map((n) => `<option value="${esc(n)}">`).join("")}</datalist></label>
      <div class="liste-m" data-tour="merken-liste">${r.merken.map((k, i) => `<div class="m-item">
        <label class="m-haupt"><input type="checkbox" data-m="${i}" checked><span><b>${esc(k.text)}</b> · ${esc(k.art_text)}</span><span class="frist" id="frist-${i}">${k.personenbezug && !k.regel ? "bis " + bis : "ohne Frist"}</span></label>
        ${k.regel ? `<div class="regel"><label><input type="checkbox" data-r="${i}" checked><span>Stattdessen die Regel lernen: <b>${esc(k.regel.text)}</b>. Gespeichert wird dann keine Nummer und kein Name.</span></label>${hilfeKnopf("regel")}</div>` : ""}</div>`).join("")}</div>
      <div class="fuss">${ico("schloss")}<span>Nur auf diesem PC, verschlüsselt. Personennamen löscht Lokanon ${r.frist_monate || 12} Monate nach dem letzten Fund.</span><button class="linkbtn" data-hilfe="speichern_warum" data-tour="merken-warum">Warum?</button></div>
      <div class="row"><button class="btn primary" id="merken-ok" data-tour="merken-ok">Merken</button><button class="btn" id="merken-nein">Nicht merken</button>
        <label class="checkbox small" style="margin-left:8px"><input type="checkbox" id="merken-nie"><span>Nicht mehr fragen</span></label></div>
    </section>`;
  }
  function merkenVerhalten(r) {
    $("#merken-ok").onclick = async () => {
      const eintraege = [];
      r.merken.forEach((k, i) => {
        const regel = $(`[data-r="${i}"]`);
        if (k.regel && regel && regel.checked) eintraege.push({ regel: k.regel });
        else if ($(`[data-m="${i}"]`).checked) eintraege.push({ text: k.text, art: k.art });
      });
      try {
        const res = await api("/merken", { json: { fall: $("#merken-fall").value.trim() || r.fall, eintraege } });
        r.gemerkt = true; renderFertig(); faelleLaden();
        toast(`${eintraege.length} ${eintraege.length === 1 ? "Angabe" : "Angaben"} gemerkt · Fall ${$("#merken-fall") ? "" : ""}${r.fall}`, "ok", { label: "Ansehen", fn: () => zeige("faelle") });
        melde("gemerkt", { neu: res.neu });
        const ein = (S.cfg.einfuehrung || {}).gesehen || [];
        if (!ein.includes("gespeichert") && !(window.LokanonTour && window.LokanonTour.laeuft)) setTimeout(() => toast("Wie Sie gemerkte Angaben verwalten und löschen: in 3 Minuten erklärt.", "", { label: "Zeigen", fn: () => tourStarten("gespeichert") }), 3400);
      } catch (e) { toast(e.message, "danger"); }
    };
    const bis = datum(plusMonate(r.frist_monate || 12));
    $$("[data-r]").forEach((c) => (c.onchange = () => {
      const i = c.dataset.r; if (c.checked) $(`[data-m="${i}"]`).checked = true;
      $(`#frist-${i}`).textContent = c.checked || !r.merken[i].personenbezug ? "ohne Frist" : "bis " + bis;
    }));
    $("#merken-nein").onclick = async () => {
      if ($("#merken-nie").checked) { try { await api("/einstellungen", { method: "PUT", json: { werte: { aufbewahrung: { lernen_fragen: false } } } }); toast("Lokanon fragt nicht mehr. Wieder einschalten: Einstellungen → Aufbewahrung.", ""); } catch (e) { toast(e.message, "danger"); } }
      r.gemerkt = true; renderFertig();
    };
  }

  // ------------------------------------------------------------ Fälle und gelernte Angaben
  function renderFaelle() {
    befehle(`<button class="cmd" data-c="aufbewahrung">${ico("zahnrad")}Fristen einstellen</button>
      <button class="cmd" data-c="protokoll-l">${ico("uhr")}Löschprotokoll</button>
      <span class="fill"></span><span class="hinweis">Alles verschlüsselt, nur auf diesem PC ${hilfeKnopf("verschluesselt")}</span>`);
    const fv = S.faelle;
    if (!fv) { view.innerHTML = `<section class="flaeche seite"><p class="muted">Wird geladen …</p></section>`; return; }
    const angabeChip = (a, mitFall = false) => `<span class="angabe">${esc(a.text)} <small>${esc(artText(a))}${mitFall ? "" : ""}</small><button class="iconbtn" data-weg="${a.id}" aria-label="${esc(a.text)} vergessen">${ico("x")}</button></span>`;
    const se = S.sucheErg;
    view.innerHTML = `<section class="flaeche seite">
      <header><h1>Fälle und gelernte Angaben</h1><p>Was Lokanon sich gemerkt hat, wofür und wie lange. ${hilfeKnopf("speichern")}</p></header>
      <div class="suche" data-tour="suche"><input class="input" id="suche" placeholder="Namen oder Fall suchen, z. B. für einen Löschwunsch" value="${esc(S.suche)}" aria-label="Namen oder Fall suchen"><button class="btn" id="suche-go">${ico("suche")}Suchen</button></div>
      ${se ? `<div class="treffer-suche" data-tour="suchergebnis">${se.angaben.length || se.faelle.length ? `
          ${se.angaben.length ? `<div><b>Gelernte Angaben:</b> ${se.angaben.map((a) => esc(a.text)).join(", ")}</div>` : ""}
          ${se.faelle.length ? `<div><b>Fälle:</b> ${se.faelle.map((f) => `<span class="mono">${esc(f.name)}</span>`).join(", ")}</div>` : ""}
          <div class="row"><button class="btn danger klein" id="ueberall" data-tour="ueberall-loeschen">„${esc(S.suche)}“ überall löschen …</button>${hilfeKnopf("ueberall_loeschen")}</div>`
        : `<span class="muted">Nichts gefunden zu „${esc(S.suche)}“.</span>`}</div>` : ""}
      ${fv.hinweise.length ? `<div class="notice warn" data-tour="fristhinweis">${ico("uhr")}<div>${fv.hinweise.map((h) => `<div><span class="mono" style="font-weight:600">${esc(h.name)}</span>: ${h.angaben.length} gelernte Angaben werden am <b>${datum(h.loeschdatum)}</b> gelöscht. <button class="linkbtn" data-fall-verl="${h.id}">Verlängern</button></div>`).join("")}</div></div>` : ""}
      <section style="display:grid;gap:8px"><h2>Fälle ${hilfeKnopf("fall")}</h2>
        ${fv.faelle.length ? `<div class="faelle" data-tour="faelle">${fv.faelle.map((f) => `<div class="fall ${S.auf.has(f.id) ? "auf" : ""}" data-tour="fall" data-name="${esc(f.name)}" data-id="${f.id}">
          <div class="fall-kopf" role="button" tabindex="0" aria-expanded="${S.auf.has(f.id)}"><span class="pfeil">${ico("pfeil")}</span><span class="mono" title="${esc(f.name)}">${esc(f.name)}</span>
            <span class="was">${f.status === "laeuft" ? `<span class="chip laeuft">Mandat läuft</span>` : f.status === "abgeschlossen" ? `<span class="chip zu">abgeschlossen</span>` : f.warnung ? `<span class="chip warn">läuft bald ab</span>` : ""}
              <span>${f.angaben.length} ${f.angaben.length === 1 ? "Angabe" : "Angaben"} · ${f.vorgaenge.length} ${f.vorgaenge.length === 1 ? "Vorgang" : "Vorgänge"}</span></span>
            <span class="muted small">${f.status === "laeuft" ? "keine Frist" : f.loeschdatum ? "Löschung am " + datum(f.loeschdatum) : ""}</span></div>
          ${S.auf.has(f.id) ? `<div class="fall-inhalt">
            <div class="angaben">${f.angaben.length ? f.angaben.map((a) => angabeChip(a)).join("") : `<span class="muted small">Keine gelernten Angaben, nur Vorgänge.</span>`}</div>
            ${f.vorgaenge.length ? `<div class="muted small">Vorgänge: ${f.vorgaenge.map((v) => `${esc(v.name)} (${zeitText(v.zeit)})`).join(" · ")}</div>` : ""}
            <div class="muted small">Zuletzt gefunden: ${datum(f.zuletzt)}${f.status === "abgeschlossen" ? ` · abgeschlossen am ${datum(f.abgeschlossen_am)}` : ""}</div>
            <div class="row"><button class="btn klein" data-fall-verl="${f.id}" data-tour="fall-verlaengern">Verlängern ${ico("runter")}</button>${hilfeKnopf("verlaengern")}
              ${f.status === "abgeschlossen" ? `<button class="btn klein" data-fall-auf="${f.id}">Wieder öffnen</button>` : `<button class="btn klein" data-fall-zu="${f.id}" data-tour="fall-abschliessen">Fall abgeschlossen</button>${hilfeKnopf("abschliessen")}`}
              <button class="btn klein" data-fall-name="${f.id}">Umbenennen</button><span style="flex:1"></span>
              <button class="btn klein ghost" data-fall-del="${f.id}" style="color:var(--danger)" data-tour="fall-loeschen">Fall löschen …</button></div>
          </div>` : ""}</div>`).join("")}</div>` : `<div class="leer">Noch keine Fälle. Lokanon legt sie beim Anonymisieren an, meist aus dem Aktenzeichen.</div>`}
      </section>
      <section style="display:grid;gap:8px"><h2>Ohne Fall <span class="muted small" style="font-weight:400">kein Personenbezug, keine Frist</span></h2>
        ${fv.ohne_fall.length ? `<div class="angaben">${fv.ohne_fall.map((a) => angabeChip(a)).join("")}</div>` : `<div class="muted small">Leer. Hier stehen „Künftig immer stehen lassen“ und Projekte oder Kürzel.</div>`}</section>
      <section style="display:grid;gap:8px"><h2>Gelernte Regeln ${hilfeKnopf("regel")}</h2>
        ${fv.regeln.length ? `<div class="angaben">${fv.regeln.map((r) => `<span class="angabe">${r.art === "bezeichnung" ? `Wert nach „${esc(r.wert)}“` : `Nummern wie „${esc(r.form)}“`} <small>seit ${datum(r.gelernt)}</small><button class="iconbtn" data-weg="${r.id}" aria-label="Regel vergessen">${ico("x")}</button></span>`).join("")}</div>` : `<div class="muted small">Noch keine. Markieren Sie einen Wert hinter einer Bezeichnung („Mandantennr.: 48213“), bietet Lokanon am Ende an, die Bezeichnung zu lernen statt der Nummer.</div>`}</section>
      <section style="display:grid;gap:8px" id="a-loeschprotokoll" data-tour="loeschprotokoll"><h2>Löschprotokoll ${hilfeKnopf("loeschprotokoll")}</h2>
        ${fv.loeschprotokoll.length ? `<div class="tabelle-box"><table class="tabelle"><thead><tr><th>Nr.</th><th>Wann</th><th>Was</th><th>Gelöscht</th><th>Grund</th><th></th></tr></thead><tbody>
          ${fv.loeschprotokoll.map((e) => `<tr><td class="mono">${esc(e.nr)}</td><td>${zeitText(e.zeit)}</td><td>${esc(e.was)}</td><td>${Object.entries(e.anzahl).map(([k, v]) => `${v} ${esc(LOESCH_NAMEN[k] || k)}`).join(", ") || "–"}${e.nicht_geloescht ? ` · <span style="color:var(--danger)">${e.nicht_geloescht} nicht gelöscht</span>` : ""}</td><td>${esc(e.grund)}</td>
            <td><button class="btn klein" data-nachweis="${esc(e.nr)}" data-tour="nachweis">Nachweis</button></td></tr>`).join("")}</tbody></table></div>` : `<div class="muted small">Noch nichts gelöscht.</div>`}</section>
    </section>`;
    const suchen = async () => { S.suche = $("#suche").value.trim(); try { S.sucheErg = S.suche.length >= 2 ? await api("/gedaechtnis/suche?q=" + encodeURIComponent(S.suche)) : null; } catch (e) { toast(e.message, "danger"); } renderFaelle(); if (S.sucheErg) melde("suche", { q: S.suche }); };
    $("#suche-go").onclick = suchen; $("#suche").onkeydown = (e) => { if (e.key === "Enter") suchen(); };
    if ($("#ueberall")) $("#ueberall").onclick = () => loeschDialog({ name: S.suche });
    $$(".fall-kopf").forEach((k) => { const auf = () => { const id = k.parentElement.dataset.id; S.auf.has(id) ? S.auf.delete(id) : (S.auf.add(id), melde("fall-auf", { name: k.parentElement.dataset.name })); renderFaelle(); };
      k.onclick = auf; k.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); auf(); } }; });
    $$("[data-weg]").forEach((b) => (b.onclick = () => bestaetigen("Diese Angabe vergessen? Lokanon schlägt sie dann nicht mehr vor.", async () => { try { S.faelle = await api("/angabe/" + b.dataset.weg, { method: "DELETE" }); renderFaelle(); rahmen(); } catch (e) { toast(e.message, "danger"); } }, "Vergessen")));
    $$("[data-fall-verl]").forEach((b) => (b.onclick = () => verlaengernMenue(b, b.dataset.fallVerl)));
    $$("[data-fall-zu]").forEach((b) => (b.onclick = () => fallAktion(b.dataset.fallZu, "abschliessen")));
    $$("[data-fall-auf]").forEach((b) => (b.onclick = () => fallAktion(b.dataset.fallAuf, "wieder_oeffnen")));
    $$("[data-fall-name]").forEach((b) => (b.onclick = () => umbenennenDialog(b.dataset.fallName)));
    $$("[data-fall-del]").forEach((b) => (b.onclick = () => loeschDialog({ faelle: [b.dataset.fallDel] })));
    $$("[data-nachweis]").forEach((b) => (b.onclick = () => nachweisZeigen(b.dataset.nachweis)));
    $$("[data-c]").forEach((b) => (b.onclick = () => (b.dataset.c === "aufbewahrung" ? zeige("einstellungen", "aufbewahrung") : $("#a-loeschprotokoll").scrollIntoView({ block: "start", behavior: "smooth" }))));
  }
  const LOESCH_NAMEN = { angaben: "Angaben", schluessel: "Schlüssel", vorgangsordner: "Vorgangsordner", testfaelle: "Testfälle", kopien: "Kopien" };
  const ARTEN_TEXT = { PERSON: "Person", ORGANIZATION: "Firma", ADRESSE: "Adresse", PLZ_ORT: "Ort", EMAIL_ADDRESS: "E-Mail", TELEFON: "Telefon", KENNNUMMER: "Kennnummer", DATUM: "Datum", PROJEKT: "Projekt", MANUELL: "Sonstiges" };
  const artText = (a) => (a.richtung === "stehen" ? "bleibt stehen" : ARTEN_TEXT[a.art] || a.art || "");
  function verlaengernMenue(anker, id) {
    menue(anker, [{ titel: "Gelernte Angaben behalten …" }, { label: "6 Monate länger", fn: () => fallAktion(id, "verlaengern", 6) },
      { label: "12 Monate länger", fn: () => fallAktion(id, "verlaengern", 12) }, { label: "24 Monate länger", fn: () => fallAktion(id, "verlaengern", 24) },
      "-", { label: "Bis auf Widerruf (Mandat läuft)", fn: () => fallAktion(id, "verlaengern", 0), tour: "verlaengern-widerruf" }]);
  }
  async function fallAktion(id, aktion, monate = 0, name = "") {
    try {
      S.faelle = await api("/fall", { json: { id, aktion, monate, name } });
      rahmen(); S.ansicht === "start" ? renderStart() : renderFaelle();
      toast(aktion === "verlaengern" ? (monate ? `Verlängert um ${monate} Monate` : "Mandat läuft: keine Frist, bis Sie den Fall abschließen") : aktion === "abschliessen" ? "Fall abgeschlossen. Die kurze Frist läuft." : aktion === "umbenennen" ? "Umbenannt" : "Fall wieder geöffnet", "ok");
      melde(aktion === "verlaengern" ? "fall-verlaengert" : aktion === "abschliessen" ? "fall-abgeschlossen" : "fall-" + aktion);
    } catch (e) { toast(e.message, "danger"); }
  }
  function umbenennenDialog(id) {
    const f = S.faelle.faelle.find((x) => x.id === id);
    const m = modal(`${kopf("Fall umbenennen")}<div class="minhalt"><input class="input" id="fn" value="${esc(f.name)}" autofocus aria-label="Name des Falls"><p class="muted small">Am besten das Aktenzeichen, keine Namen.</p></div>
      <div class="mfuss"><button class="btn x">Abbrechen</button><button class="btn primary" id="fn-ok">Umbenennen</button></div>`);
    $("#fn", m).focus();
    $("#fn-ok", m).onclick = () => { closeModal(); fallAktion(id, "umbenennen", 0, $("#fn", m).value); };
  }

  // Löschen: eine Rückfrage, alle Folgen sichtbar; eine zweite nur bei echtem Risiko
  async function loeschDialog(ziel) {
    let v;
    try { v = await api("/loeschen/vorschau", { json: ziel }); } catch (e) { toast(e.message, "danger"); return; }
    const a = v.anzahl;
    const titel = ziel.name ? `„${esc(ziel.name)}“ überall löschen?` : v.faelle.length === 1 ? `Fall <span class="mono">${esc(v.faelle[0].name)}</span> löschen?`
      : v.faelle.length ? `${v.faelle.length} Fälle löschen?` : v.vorgaenge.length === 1 ? `Vorgang „${esc(v.vorgaenge[0].name)}“ löschen?` : `${v.vorgaenge.length} Vorgänge löschen?`;
    const unter = `${v.vorgaenge.length} ${v.vorgaenge.length === 1 ? "Vorgang" : "Vorgänge"}${v.faelle.length ? " · " + v.faelle.map((f) => esc(f.name)).join(", ") : ""}`;
    const z = (key, name, hi, anzahl, extra = "") => `<label class="loesch-zeile"><input type="checkbox" data-k="${key}" checked><span><span class="nm">${name}${extra}</span>${hi ? `<br><span class="hi">${hi}</span>` : ""}</span><span class="ct">${anzahl}</span></label>`;
    const teile = [];
    if (a.angaben || !ziel.vorgaenge) teile.push(z("angaben", "Gelernte Angaben", a.geteilt ? `${a.geteilt} weitere bleiben, weil sie auch zu einem anderen Fall gehören.` : "", a.angaben, hilfeKnopf("frist")));
    if (a.schluessel) teile.push(z("schluessel", "Schlüssel für die Rückübersetzung", "KI-Antworten zu diesem Fall lassen sich danach nicht mehr zurückübersetzen.", `${a.schluessel} ${a.schluessel === 1 ? "Datei" : "Dateien"}`));
    if (a.vorgangsordner) teile.push(z("vorgangsordner", "Vorgangsordner mit Prüfbericht und Kopie der Originale", "", `${a.vorgangsordner} ${a.vorgangsordner === 1 ? "Ordner" : "Ordner"}`));
    if (a.testfaelle) teile.push(z("testfaelle", "Eigene Testfälle", "", a.testfaelle));
    const m = modal(`${kopf(titel, unter)}
      <div class="minhalt">
        ${v.warnungen.length ? `<div class="notice warn" id="ld-warn">${ico("warn")}<div>${v.warnungen.map(esc).join("<br>")}</div></div>` : ""}
        <div class="loesch-teil">Wird gelöscht · enthält Personendaten</div>${teile.join("")}
        ${a.kopien ? `<div class="loesch-teil">Sie entscheiden</div><label class="loesch-zeile"><input type="checkbox" id="ld-kopien"><span><span class="nm">Anonymisierte Kopien</span><br><span class="hi">${a.kopien} ${a.kopien === 1 ? "Datei" : "Dateien"} in ${v.kopien_ordner.map(esc).join(", ")}. Enthalten keine Namen und kommen in den Papierkorb. Was Sie schon an eine KI gegeben haben, kann Lokanon nicht löschen. ${hilfeKnopf("ki_kopien")}</span></span><span class="ct">${a.kopien} ${a.kopien === 1 ? "Datei" : "Dateien"}</span></label>` : ""}
        <div class="loesch-teil">Bleibt</div>
        <div class="bleibt"><span>${ico("check")}Ihre Originaldateien. Lokanon verändert sie nie. ${hilfeKnopf("originale_bleiben")}</span><span>${ico("check")}Protokoll ohne Namen (löscht sich nach 30 Tagen) und ein Eintrag im Löschprotokoll als Nachweis. ${hilfeKnopf("protokoll_bleibt")}</span></div>
        <fieldset class="grund"><legend>Grund</legend>
          ${[["mandant", "Wunsch des Mandanten"], ["abgeschlossen", "Fall abgeschlossen"], ["sonstiges", "Sonstiges"]].map(([k, t]) => `<label><input type="radio" name="grund" value="${k}" ${k === (ziel.name ? "mandant" : ziel.vorgaenge ? "sonstiges" : "abgeschlossen") ? "checked" : ""}>${t}</label>`).join("")}</fieldset>
      </div>
      <div class="mfuss"><button class="btn x" autofocus>Abbrechen</button><button class="btn danger" id="ld-ok" data-tour="loeschen-ok"></button></div>`, { tour: "loeschdialog" });
    melde("loeschdialog");
    const grund = () => $("input[name=grund]:checked", m).value;
    const knopf = () => {
      const g = grund(); $$("[data-k]", m).forEach((c) => { if (g !== "sonstiges") c.checked = true; c.disabled = g !== "sonstiges"; });
      const ang = $("[data-k=angaben]", m) && $("[data-k=angaben]", m).checked ? a.angaben : 0;
      const dat = ["schluessel", "vorgangsordner", "testfaelle"].reduce((s, k) => s + ($(`[data-k=${k}]`, m) && $(`[data-k=${k}]`, m).checked ? a[k] : 0), 0);
      const kop = $("#ld-kopien", m) && $("#ld-kopien", m).checked ? a.kopien : 0;
      const teileT = [ang ? `${ang} ${ang === 1 ? "Angabe" : "Angaben"}` : "", dat ? `${dat} ${dat === 1 ? "Datei" : "Dateien"}` : ""].filter(Boolean);
      const korb = kop ? `${kop} ${kop === 1 ? "Kopie" : "Kopien"} in den Papierkorb` : "";
      $("#ld-ok", m).textContent = teileT.length ? `${teileT.join(" und ")} endgültig löschen${korb ? ", " + korb : ""}`
        : korb ? `${korb} legen` : (v.faelle.length ? "Fall aus der Übersicht löschen" : "Aus der Liste löschen");
    };
    $$("input", m).forEach((i) => (i.onchange = knopf)); knopf();
    let bestaetigt = !v.warnungen.length;
    $("#ld-ok", m).onclick = async () => {
      if (!bestaetigt) { bestaetigt = true; $("#ld-ok", m).textContent = "Trotzdem löschen"; $("#ld-warn", m).scrollIntoView({ block: "nearest" }); $("#ld-warn", m).animate([{ outline: "2px solid var(--warn)" }, { outline: "0" }], 900); return; }
      const auswahl = Object.fromEntries($$("[data-k]", m).map((c) => [c.dataset.k, c.checked]));
      try {
        const r = await api("/loeschen", { json: { ...ziel, grund: grund(), kopien: !!($("#ld-kopien", m) && $("#ld-kopien", m).checked), auswahl } });
        S.faelle = r.uebersicht; S.auswahl.clear(); S.sucheErg = null;
        closeModal(); await laden(); loeschErgebnis(r); melde("geloescht");
      } catch (e) { toast(e.message, "danger"); }
    };
  }
  function loeschErgebnis(r) {
    const g = Object.entries(r.geloescht).filter(([, n]) => n);
    const m = modal(`${kopf(r.fehler.length ? "Nicht alles ließ sich löschen" : "Gelöscht", `Eintrag ${esc(r.protokoll_nr)} im Löschprotokoll`)}
      <div class="minhalt">${g.length ? `<div class="bleibt">${g.map(([k, n]) => `<span>${ico("check")}${n} ${esc(LOESCH_NAMEN[k] || k)}</span>`).join("")}</div>` : `<p class="muted">Es gab keine gespeicherten Daten mehr, nur den Eintrag in der Übersicht.</p>`}
        ${r.fehler.length ? `<div class="notice danger">${ico("warn")}<div><b>Diese Dateien sind noch da:</b><ul class="funde">${r.fehler.map((f) => `<li><code>${esc(f.pfad)}</code><br>${esc(f.grund)}</li>`).join("")}</ul>Bitte schließen Sie sie in anderen Programmen und versuchen Sie es erneut, oder löschen Sie sie von Hand.</div></div>` : ""}</div>
      <div class="mfuss">${r.fehler.length ? `<button class="btn" id="le-nochmal">Erneut versuchen</button>` : ""}<button class="btn" id="le-nachweis" data-tour="nachweis-oeffnen">Nachweis öffnen</button><button class="btn primary x">Fertig</button></div>`);
    $("#le-nachweis", m).onclick = () => nachweisZeigen(r.protokoll_nr);
    if ($("#le-nochmal", m)) $("#le-nochmal", m).onclick = async () => { try { const n = await api("/loeschen/nochmal", { json: { pfade: r.fehler.map((f) => f.pfad) } }); closeModal(); loeschErgebnis({ ...r, fehler: n.fehler }); } catch (e) { toast(e.message, "danger"); } };
    render(); faelleLaden();
  }
  function nachweisZeigen(nr) {
    const m = modal(`${kopf("Löschbestätigung " + esc(nr), "Ohne Namen. Zum Ablegen in der Akte oder für den Mandanten.")}
      <div class="minhalt"><iframe class="help-frame" style="min-height:52vh" src="/api/loeschnachweis/${encodeURIComponent(nr)}" title="Löschbestätigung"></iframe></div>
      <div class="mfuss"><button class="btn" id="nw-cp">Text kopieren</button><button class="btn primary x">Schließen</button></div>`, { wide: true });
    $("#nw-cp", m).onclick = async () => { const t = await (await fetch("/api/loeschnachweis/" + encodeURIComponent(nr))).text(); const d = document.createElement("div"); d.innerHTML = t; copy(d.innerText, "Bestätigung kopiert"); };
    melde("nachweis");
  }

  // ------------------------------------------------------------ Protokoll
  async function renderProtokoll() {
    befehle(`<button class="cmd" data-c="ordner">${ico("ordner")}Ordner öffnen</button><button class="cmd" data-c="kopie">${ico("kopie")}Kopieren</button>`);
    let p;
    try { p = await api("/protokoll"); } catch (e) { toast(e.message, "danger"); return; }
    if (S.ansicht !== "protokoll") return;
    const zeilen = p.eintraege.map((e) => `${e.zeit} [${e.stufe}] ${e.text}`).join("\n");
    view.innerHTML = `<section class="flaeche seite"><header><h1>Protokoll des letzten Durchlaufs</h1>
      <p>Ohne Klartext: Namen und andere erkannte Angaben stehen als Platzhalter, Dateien als Nummer. Sie können es daher weitergeben, wenn Sie Hilfe brauchen. Ältere Protokolle löscht Lokanon nach 30 Tagen.</p></header>
      ${p.eintraege.length ? `<div class="protokoll">${p.eintraege.map((e) => `<div class="pz ${esc(e.stufe)}"><span class="zeit">${esc(e.zeit)}</span><span class="stufe">${e.stufe === "fehler" ? "Fehler" : e.stufe === "warnung" ? "Hinweis" : "Info"}</span><span class="t">${esc(e.text)}</span></div>`).join("")}</div>`
        : `<p class="leer">Noch keine Einträge in dieser Sitzung.</p>`}
      <p class="muted small">Ordner: <code>${esc(p.ordner)}</code></p></section>`;
    $("[data-c=ordner]").onclick = () => oeffnen(p.ordner);
    $("[data-c=kopie]").onclick = () => (zeilen ? copy(zeilen, "Protokoll kopiert") : toast("Noch nichts zu kopieren."));
  }

  // ------------------------------------------------------------ Einstellungen
  async function renderEinstellungen() {
    befehle(`<span class="fill"></span><button class="btn primary" data-c="speichern">Speichern</button>`);
    S.cfg = await api("/einstellungen");
    if (S.ansicht !== "einstellungen") return;
    const c = S.cfg; const erw = c.erweitert || {}; const grp = c._gruppen || {}; const auf = c.aufbewahrung || {};
    const radio = (name, werte, aktuell) => `<div class="radios">${werte.map(([v, t]) => `<label><input type="radio" name="${name}" value="${v}" ${String(aktuell) === String(v) ? "checked" : ""}>${t}</label>`).join("")}</div>`;
    const sw = (id, an, titel, text, tour = "") => `<label class="swrow" ${tour ? `data-tour="${tour}"` : ""}><span class="t"><b>${titel}</b><span>${text}</span></span><span class="switch"><input type="checkbox" id="${id}" ${an ? "checked" : ""}><span class="track"></span></span></label>`;
    view.innerHTML = `<section class="flaeche seite"><header><h1>Einstellungen</h1><p>Gespeichert nur auf diesem PC.</p></header><div class="abschnitte">
      <div class="abschnitt" id="a-kanzlei"><h2>Ihre Kanzlei</h2><p class="desc">Diese Namen werden nie ersetzt: Kanzleiname, Mitarbeitende, eigene Telefonnummern und E-Mail-Adressen. Eine Angabe je Zeile.</p>
        <textarea class="input" id="s-allow" rows="5" aria-label="Nie ersetzen">${esc((c.allow_list || []).join("\n"))}</textarea>
        <label class="lbl" for="s-deny">Immer ersetzen <span class="muted small" style="font-weight:400">(interne Kürzel, Projektnamen; dauerhaft, ohne Frist)</span></label>
        <textarea class="input" id="s-deny" rows="2">${esc((c.deny_list || []).join("\n"))}</textarea></div>
      <div class="abschnitt" id="a-aufbewahrung" data-tour="aufbewahrung"><h2>Aufbewahrung und Löschfristen ${hilfeKnopf("aufbewahrung")}</h2>
        <p class="desc">Gelernte Angaben, Schlüssel, Vorgangsordner und Testfälle gehören zu einem Fall und werden mit ihm gelöscht. Alles ist verschlüsselt und nur unter Ihrem Windows-Konto lesbar.</p>
        <div class="feld"><span class="lbl">Personenbezogene Angaben löschen, wenn sie so lange nicht mehr vorkamen ${hilfeKnopf("frist")}</span>${radio("frist", [[3, "3 Monate"], [6, "6 Monate"], [12, "12 Monate"], [24, "24 Monate"]], auf.personen_monate || 12)}</div>
        <div class="feld"><span class="lbl">Nach „Fall abgeschlossen“ löschen nach</span>${radio("frist-zu", [[1, "1 Monat"], [3, "3 Monaten"], [6, "6 Monaten"]], auf.abgeschlossen_monate || 3)}</div>
        ${sw("s-fragen", auf.lernen_fragen !== false, "Nach dem Anonymisieren fragen, ob selbst markierte Angaben gemerkt werden", "Aus: Lokanon merkt sich nichts Selbstmarkiertes. Bestehende Angaben bleiben bis zu ihrer Frist.")}
        <p class="desc">Fest: Das Protokoll ohne Namen löscht sich nach 30 Tagen. Projekte, Kürzel, Regeln und „Künftig immer stehen lassen“ haben keinen Personenbezug und keine Frist. <button class="linkbtn" data-c="faelle">Gelernte Angaben ansehen</button></p>
        <p class="desc">Warum nicht 6 Jahre wie die Handakte? ${hilfeKnopf("handakte")} · Und meine Datensicherung? ${hilfeKnopf("sicherung")} · Warum verschlüsselt? ${hilfeKnopf("verschluesselt")}</p></div>
      <div class="abschnitt" id="a-erkennung"><h2>Erkennung</h2>
        ${sw("s-inst", c.keep_institutions, "Gerichte, Behörden, Versicherer, Kliniken stehen lassen", "Meist kein Personenbezug; einzelne lassen sich beim Prüfen trotzdem ersetzen.")}
        ${sw("s-orte", c.mask_locations, "Ortsnamen ohne Adresse ersetzen", "„Mülheim“ im Fließtext. Adressen und PLZ mit Ort werden immer ersetzt.")}
        <div class="feld"><span class="lbl">Datumsangaben</span>${radio("datum", [["kontext", "nur mit Personenbezug (Geburt, Tod)"], ["alle", "jedes Datum"], ["keine", "keine"]], c.datum_modus)}</div>
        <div class="feld"><span class="lbl">Was erkannt wird</span><div class="zwei" id="s-ents">${Object.entries(grp).map(([g, ents]) => `<label class="checkbox"><input type="checkbox" data-ents="${esc(ents.join(","))}" ${ents.some((e) => (c.entities || []).includes(e)) ? "checked" : ""}><span>${esc(g)}</span></label>`).join("")}</div></div></div>
      <div class="abschnitt" id="a-ausgabe"><h2>Ausgabe</h2>
        <div class="zwei"><label class="feld"><span class="lbl">Zusatz im Dateinamen</span><input class="input" id="s-suffix" value="${esc(c.suffix || "_anonymisiert")}"></label>
          <div class="feld"><span class="lbl">Ablage bei Drag &amp; Drop</span><div class="row" style="flex-wrap:nowrap"><input class="input" id="s-out" value="${esc(c.ausgabe_ordner || "")}" placeholder="${esc(c._ausgabe_ordner_effektiv)}" aria-label="Ablage"><button class="btn" id="s-out-pick">Wählen</button></div><span class="muted small">Bei „Ordner öffnen“ landen die Kopien neben den Originalen.</span></div></div>
        ${sw("s-md", c.ki_textfassung, "Zusätzlich eine Textfassung (.md) erzeugen", "Reiner Text ohne Layout, mit dem KI-Assistenten am besten arbeiten.")}</div>
      <div class="abschnitt" id="a-erweitert"><h2>Erweitert</h2><p class="desc">Alles hier ist aus, bis Sie es brauchen.</p>
        ${sw("s-rz", erw.rueckuebersetzung, "Antworten der KI zurückübersetzen", "Lokanon speichert je Vorgang einen verschlüsselten Schlüssel. Er gehört zum Fall und wird mit ihm gelöscht.")}
        <div class="feld" id="s-pw-row" ${erw.rueckuebersetzung ? "" : "hidden"}><label class="lbl" for="s-pw">Passwort für Schlüsseldateien</label><input class="input" type="password" id="s-pw" value="${esc(c.schluessel_passwort || "")}" placeholder="einmal festlegen" style="max-width:320px"><span class="muted small">Schlüssel: ${esc(c._schluessel_ordner_effektiv)}</span></div>
        ${sw("s-ki", erw.ki_anweisung, "KI-Anweisung und Claude-Skill anzeigen", "Nach dem Anonymisieren erscheint „KI-Anweisung kopieren“.")}
        ${sw("s-tf", erw.testfaelle, "Geprüfte Vorgänge als eigene Testfälle speichern", 'Text und Ihre Korrekturen bleiben verschlüsselt auf diesem PC, damit sich neue Lokanon-Versionen an Ihren Dokumenten messen lassen. Sie gehören zum Fall und werden mit ihm gelöscht. <span id="s-tf-stand"></span>')}
        ${sw("s-vg", erw.vorgaenge, "Vorgangsordner mit Prüfbericht und Protokoll", `Je Vorgang ein Ordner mit Kopie der Originale, Prüfbericht (Klartext) und Protokoll unter ${esc(c._vorgaenge_ordner_effektiv)}. Gehört zum Fall und wird mit ihm gelöscht.`)}</div>
      <div class="abschnitt" id="a-vorstellung"><h2>Lokanon vorstellen</h2><p class="desc">Produktvorstellung und Filme für Kolleginnen, Kollegen und Mandanten. Läuft ohne Internet.</p><div id="s-mkt"><span class="muted small">Wird geladen …</span></div></div>
      <div class="row between"><span class="muted small">Lokanon ${esc(S.status.version)} · Daten: ${esc(S.status.daten_ordner)}</span><button class="btn primary" data-c="speichern">Speichern</button></div>
    </div></section>`;
    vorstellungFuellen($("#s-mkt"));
    (async () => { let t; try { t = await api("/testfaelle"); } catch { return; } const z = $("#s-tf-stand"); if (!z || !t.vorgaenge) return;
      z.innerHTML = `${t.vorgaenge} ${t.vorgaenge === 1 ? "Vorgang" : "Vorgänge"} gespeichert · <button class="linkbtn" id="s-tf-del">alle löschen</button>`;
      $("#s-tf-del").onclick = (e) => { e.preventDefault(); bestaetigen("Alle eigenen Testfälle löschen?", async () => { await api("/testfaelle", { method: "DELETE" }); toast("Testfälle gelöscht", "ok"); renderEinstellungen(); }, "Löschen"); }; })();
    $("#s-rz").onchange = (e) => { $("#s-pw-row").hidden = !e.target.checked; };
    $("#s-out-pick").onclick = async () => { try { const r = await api("/system/ordner-waehlen", { method: "POST" }); if (r.pfad) $("#s-out").value = r.pfad; } catch (e) { toast(e.message, "danger"); } };
    $$("[data-c=faelle]").forEach((b) => (b.onclick = () => zeige("faelle")));
    $$("[data-c=speichern]").forEach((b) => (b.onclick = async () => {
      const lines = (id) => $(id).value.split("\n").map((s) => s.trim()).filter(Boolean);
      const wert = (n) => ($(`input[name=${n}]:checked`) || {}).value;
      const entities = [].concat(...$$("#s-ents input").filter((i) => i.checked).map((i) => i.dataset.ents.split(",")));
      const werte = { allow_list: lines("#s-allow"), deny_list: lines("#s-deny"), keep_institutions: $("#s-inst").checked, mask_locations: $("#s-orte").checked,
        datum_modus: wert("datum") || "kontext", entities, suffix: $("#s-suffix").value, ausgabe_ordner: $("#s-out").value.trim(), ki_textfassung: $("#s-md").checked,
        schluessel_passwort: $("#s-pw").value,
        aufbewahrung: { personen_monate: +wert("frist") || 12, abgeschlossen_monate: +wert("frist-zu") || 3, lernen_fragen: $("#s-fragen").checked },
        erweitert: { rueckuebersetzung: $("#s-rz").checked, ki_anweisung: $("#s-ki").checked, vorgaenge: $("#s-vg").checked, testfaelle: $("#s-tf").checked } };
      if (werte.erweitert.rueckuebersetzung && !werte.schluessel_passwort) { toast("Bitte ein Passwort für die Schlüsseldateien festlegen.", "danger"); return; }
      try { await api("/einstellungen", { method: "PUT", json: { werte } }); S.cfg = await api("/einstellungen"); toast("Einstellungen gespeichert", "ok"); S.z = await api("/zustand"); faelleLaden(); } catch (e) { toast(e.message, "danger"); }
    }));
  }

  // ------------------------------------------------------------ Erweitert: KI-Anweisung, Rückübersetzung, Vorstellung, Anleitung
  async function anweisungDialog() {
    const a = await api("/anweisung");
    const m = modal(`${kopf("Anweisung für ChatGPT oder Claude", "Einmal als Projekt-Anweisung einfügen. Die KI lässt die Platzhalter dann stehen.")}
      <div class="minhalt"><pre class="anweisung">${esc(a.text)}</pre></div>
      <div class="mfuss"><a class="btn" href="/api/skill.zip">Claude-Skill laden</a><button class="btn primary" id="cp">Kopieren</button></div>`, { wide: true });
    $("#cp", m).onclick = () => copy(a.text, "Anweisung kopiert");
  }
  async function zurueckDialog() {
    let keys = { schluessel: [], aktuell: "" };
    try { keys = await api("/schluessel"); } catch {}
    const m = modal(`${kopf("Antwort zurückübersetzen", "Setzt die Originale wieder ein, nur hier auf diesem PC.")}
      <div class="minhalt"><label class="feld"><span class="small muted">Schlüssel</span><select class="input" id="zk-key"><option value="">Aktueller Vorgang</option>${keys.schluessel.map((k) => `<option value="${esc(k.pfad)}" ${k.pfad === keys.aktuell ? "selected" : ""}>${esc(k.name)}</option>`).join("")}</select></label>
        <textarea class="input" id="zk-in" rows="7" placeholder="Antwort der KI hier einfügen …" aria-label="Antwort der KI"></textarea>
        <div class="row" style="justify-content:flex-end"><button class="btn primary" id="zk-go">Zurückübersetzen</button></div>
        <textarea class="input" id="zk-out" rows="7" readonly placeholder="Ergebnis" aria-label="Ergebnis"></textarea></div>
      <div class="mfuss"><button class="btn" id="zk-cp">Ergebnis kopieren</button><button class="btn x">Schließen</button></div>`, { wide: true });
    $("#zk-go", m).onclick = async () => {
      try { const r = await api("/zurueck", { json: { text: $("#zk-in", m).value, schluessel_pfad: $("#zk-key", m).value } }); $("#zk-out", m).value = r.text; toast(r.platzhalter ? `${r.platzhalter} Platzhalter zurückübersetzt (${r.quelle})` : `Keine Platzhalter gefunden (${r.quelle})`, r.platzhalter ? "ok" : "danger"); }
      catch (e) { toast(e.message, "danger"); }
    };
    $("#zk-cp", m).onclick = () => copy($("#zk-out", m).value);
  }
  async function vorstellungFuellen(ziel) {
    let mk;
    try { mk = await api("/marketing"); } catch { ziel.innerHTML = `<span class="muted small">Die Produktvorstellung ist in dieser Installation nicht enthalten.</span>`; return; }
    const teile = [];
    if (mk.deck) teile.push(`<button class="mkt-item" data-deck>${ico("play")}<span><b>Produktvorstellung</b><small>Interaktive Visitenkarte</small></span></button>`);
    mk.filme.forEach((f, i) => teile.push(`<button class="mkt-item" data-film="${i}">${ico("play")}<span><b>${esc(f.titel)}</b><small>Film · ${esc(f.dauer)}</small></span></button>`));
    if (!teile.length) { ziel.innerHTML = `<span class="muted small">Die Produktvorstellung ist in dieser Installation nicht enthalten.</span>`; return; }
    ziel.innerHTML = `<div class="mkt-grid">${teile.join("")}</div>`;
    $$("[data-deck]", ziel).forEach((b) => (b.onclick = () => modal(`${kopf("Produktvorstellung")}<div class="minhalt"><iframe class="help-frame" src="${esc(mk.deck_url)}" title="Produktvorstellung"></iframe></div>`, { full: true })));
    $$("[data-film]", ziel).forEach((b) => (b.onclick = () => { const f = mk.filme[+b.dataset.film]; modal(`${kopf(esc(f.titel))}<div class="minhalt"><video class="mkt-video" src="${esc(f.url)}" controls autoplay playsinline></video></div>`, { full: true }); }));
  }
  function vorstellungDialog() { const m = modal(`${kopf("Lokanon vorstellen", "Produktvorstellung und Filme, ohne Internet.")}<div class="minhalt"><div id="v-mkt"></div></div>`, { wide: true }); vorstellungFuellen($("#v-mkt", m)); }
  function hilfeDialog() { modal(`${kopf("Anleitung")}<div class="minhalt"><iframe class="help-frame" src="/anleitung/" title="Anleitung"></iframe></div>`, { full: true }); }

  // ------------------------------------------------------------ Einführung (ui/einfuehrung/fuehrung.js)
  function tourStarten(kapitel) {
    if (!window.LokanonTour) { toast("Die Einführung ist in dieser Installation nicht enthalten.", "danger"); return; }
    schliesseSchwebendes(); closeModal();
    window.LokanonTour.start(kapitel || "");
  }
  async function tourBeenden() { if (window.LokanonTour && window.LokanonTour.laeuft) window.LokanonTour.beenden(); else { await api("/einfuehrung/ende", { method: "POST" }); S.status = await api("/status"); await laden(true); faelleLaden(); } }

  // ------------------------------------------------------------ Erster Start
  function renderWizard() {
    $("#nav").hidden = true; befehle("");
    view.innerHTML = `<section class="flaeche seite" style="max-width:640px;margin:24px auto"><div><div class="muted small">Erster Start</div><h1>Was Lokanon nie ersetzen soll</h1>
      <p class="muted" style="margin-top:6px">Ihr Kanzleiname, Ihre Mitarbeitenden, Ihre Telefonnummern und E-Mail-Adressen stehen in jedem Schriftsatz. Sie bleiben stehen. Eine Angabe je Zeile; das lässt sich jederzeit in den Einstellungen ändern.</p></div>
      <label class="feld"><span class="lbl" style="font-weight:600">Kanzlei</span><input class="input" id="w-kanzlei" placeholder="z. B. Rechtsanwälte Beispiel &amp; Partner"></label>
      <label class="feld"><span class="lbl" style="font-weight:600">Mitarbeitende und eigene Kontaktdaten</span><textarea class="input" id="w-leute" rows="5" placeholder="Dr. Anna Beispiel&#10;Max Mustermann&#10;0208 123456&#10;kanzlei@beispiel.de"></textarea></label>
      <div class="row" style="justify-content:flex-end"><button class="btn primary" id="w-ok">Weiter</button></div></section>`;
    $("#w-ok").onclick = async () => {
      const allow = [$("#w-kanzlei").value.trim(), ...$("#w-leute").value.split("\n").map((s) => s.trim())].filter(Boolean);
      try {
        await api("/einstellungen", { method: "PUT", json: { werte: { allow_list: [...new Set(allow)], eingerichtet: true } } });
        S.status.eingerichtet = true; S.cfg = await api("/einstellungen"); $("#nav").hidden = false; await laden(true); faelleLaden();
        const m = modal(`${kopf("Eingerichtet")}<div class="minhalt"><p>Möchten Sie Lokanon einmal an einem Beispiel ausprobieren? Die Einführung zeigt alles Schritt für Schritt im Programm, mit erfundenen Daten.</p></div>
          <div class="mfuss"><button class="btn x">Später</button><button class="btn primary" id="w-tour">Einführung starten (ca. 5 Min.)</button></div>`);
        $("#w-tour", m).onclick = () => { closeModal(); tourStarten(""); };
      } catch (e) { toast(e.message, "danger"); }
    };
  }

  // Schnittstelle für die Einführung: nur was ein Schritt zum Vorführen („Zeig es mir“) braucht
  window.LokanonApp = {
    api, zeige, laden, render, melde, state: S, faelleLaden, schliesse: closeModal,
    async uebungBeginnen() { await api("/einfuehrung/start", { method: "POST" }); S.status = await api("/status"); S.z = await api("/zustand"); S.faelle = await api("/faelle"); zeige("start"); },
    async beispielLaden() { S.z = await api("/einfuehrung/beispiel", { method: "POST" }); S.docIndex = 0; S.filter = "alle"; S.gewaehlt = null; S.stelle = null; S.docMode = "markiert"; zeige("vorgang"); melde("analysiert"); },
    async uebungBeenden() { await api("/einfuehrung/ende", { method: "POST" }); S.status = await api("/status"); S.markiermodus = false; S.auf.clear(); S.suche = ""; S.sucheErg = null; await laden(true); faelleLaden(); },
    async einstellungMerken(werte) { await api("/einstellungen", { method: "PUT", json: { werte } }); S.cfg = await api("/einstellungen"); },
    // Vorführen: ein Wort im Dokument markieren, als wäre es mit der Maus ausgewählt
    markiereWort(wort, dok = 0) {
      if (S.docIndex !== dok || S.docMode !== "markiert") { S.docIndex = dok; S.docMode = "markiert"; renderPruefen(); }
      const dv = $("#docview"); const w = document.createTreeWalker(dv, NodeFilter.SHOW_TEXT); let n;
      while ((n = w.nextNode())) { const i = n.textContent.indexOf(wort); if (i >= 0 && !n.parentElement.closest(".m")) {
        const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + wort.length); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
        const lw = $("#leinwand"); lw.scrollTop += r.getBoundingClientRect().top - lw.getBoundingClientRect().top - 140; return auswahlPruefen(); } }
    },
    zeileName(name) { return $(`.zeile[data-name="${CSS.escape(name)}"]`); },
  };

  boot().catch((e) => { view.innerHTML = `<div class="notice danger">Der lokale Server antwortet nicht. Bitte Lokanon neu starten. (${esc(e.message)})</div>`; });
})();
