/* Führung durch Lokanon: dunkelt alles außer dem Bedienelement des Schritts ab und zeigt daneben eine Sprechblase.
   „Zeigen“-Schritte gehen mit „Weiter“, „Selbst tun“-Schritte warten auf das Ereignis, das ui/app.js mit melde()
   schickt. Nach 20 Sekunden ohne Aktion bietet die Blase „Zeig es mir“ an. Läuft in einer Übungssitzung
   (POST /api/einfuehrung/start), die beim Beenden mit allen Daten gelöscht wird. Ohne fremde Bibliothek, offline. */
(() => {
  "use strict";
  const D = window.LokanonDrehbuch, H = window.LokanonHilfe || {};
  const $ = (s, c = document) => c.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const warte = (ms) => new Promise((r) => setTimeout(r, ms));
  const T = { laeuft: false, liste: [], i: 0, kapitelGesehen: new Set(), zeigTimer: null, tick: null, ereignis: null, selbsttest: false, fehler: [] };

  const selektor = (s) => (s.ziel ? `[data-tour="${s.ziel}"]` + (s.name ? `[data-name="${CSS.escape(s.name)}"]` : "") : "");
  const kapitelVon = (s) => D.kapitel.find((k) => k.id === s.kapitel);
  function sichtbar(el) { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  async function zielFinden(s, ms = 5000) {
    if (!s.ziel) return null;
    for (let t = 0; t < ms; t += 100) { const el = $(selektor(s)); if (el && sichtbar(el)) return el; await warte(100); }
    return undefined;
  }

  // ------------------------------------------------------------ Darstellung
  function aufbauen() {
    abbauen();
    const r = document.createElement("div"); r.className = "fuehrung"; r.id = "fuehrung";
    r.innerHTML = `<div class="f-maske f-oben"></div><div class="f-maske f-links"></div><div class="f-maske f-rechts"></div><div class="f-maske f-unten"></div>
      <div class="f-deckel"></div><div class="f-rahmen"></div>
      <div class="f-blase" role="dialog" aria-modal="false" aria-labelledby="f-titel"><div class="f-pfeil"></div>
        <div class="f-kopf"><span class="f-stand" id="f-stand"></span><button class="f-x" id="f-ende" aria-label="Einführung beenden">×</button></div>
        <h2 id="f-titel"></h2><div class="f-text" id="f-text"></div><div class="f-aufgabe" id="f-aufgabe"></div>
        <div class="f-fuss"><button class="f-btn" id="f-zurueck">Zurück</button><button class="f-btn f-zeig" id="f-zeig" hidden>Zeig es mir</button>
          <span class="f-fill"></span><button class="f-btn f-primaer" id="f-weiter">Weiter</button></div></div>
      <div class="f-ansage" aria-live="polite" id="f-ansage"></div>`;
    document.body.appendChild(r);
    document.body.classList.add("tour-aktiv");
    $("#f-ende").onclick = () => beenden();
    $("#f-zurueck").onclick = () => gehe(T.i - 1);
    $("#f-weiter").onclick = () => weiter();
    $("#f-zeig").onclick = () => vormachen();
  }
  function abbauen() { const r = $("#fuehrung"); if (r) r.remove(); document.body.classList.remove("tour-aktiv"); clearInterval(T.tick); clearTimeout(T.zeigTimer); }
  function platzieren() {
    const s = T.liste[T.i]; if (!s || !$("#fuehrung")) return;
    const el = s.ziel ? $(selektor(s)) : null;
    const b = $(".f-blase"), pf = $(".f-pfeil"); const W = innerWidth, Hh = innerHeight;
    let r = el && sichtbar(el) ? el.getBoundingClientRect() : null;
    const pad = 6;
    const box = r ? { l: Math.max(0, r.left - pad), t: Math.max(0, r.top - pad), r: Math.min(W, r.right + pad), b: Math.min(Hh, r.bottom + pad) } : { l: W / 2, t: Hh / 2, r: W / 2, b: Hh / 2 };
    const setze = (sel, css) => Object.assign($(sel).style, css);
    setze(".f-oben", { left: "0", top: "0", width: W + "px", height: box.t + "px" });
    setze(".f-unten", { left: "0", top: box.b + "px", width: W + "px", height: Math.max(0, Hh - box.b) + "px" });
    setze(".f-links", { left: "0", top: box.t + "px", width: box.l + "px", height: Math.max(0, box.b - box.t) + "px" });
    setze(".f-rechts", { left: box.r + "px", top: box.t + "px", width: Math.max(0, W - box.r) + "px", height: Math.max(0, box.b - box.t) + "px" });
    setze(".f-rahmen", r ? { display: "block", left: box.l + "px", top: box.t + "px", width: box.r - box.l + "px", height: box.b - box.t + "px" } : { display: "none" });
    // Bei „Zeigen“ ist das Element nur zu sehen, nicht zu bedienen
    setze(".f-deckel", r && s.art !== "tun" ? { display: "block", left: box.l + "px", top: box.t + "px", width: box.r - box.l + "px", height: box.b - box.t + "px" } : { display: "none" });
    const bw = b.offsetWidth, bh = b.offsetHeight, abst = 14;
    let x, y, seite;
    if (!r) { x = (W - bw) / 2; y = (Hh - bh) / 2; seite = ""; }
    else if (W - box.r >= bw + abst + 8) { x = box.r + abst; y = Math.min(Math.max(8, box.t), Hh - bh - 8); seite = "links"; }
    else if (box.l >= bw + abst + 8) { x = box.l - bw - abst; y = Math.min(Math.max(8, box.t), Hh - bh - 8); seite = "rechts"; }
    else if (Hh - box.b >= bh + abst + 8) { x = Math.min(Math.max(8, box.l), W - bw - 8); y = box.b + abst; seite = "oben"; }
    else if (box.t >= bh + abst + 8) { x = Math.min(Math.max(8, box.l), W - bw - 8); y = box.t - bh - abst; seite = "unten"; }
    else { x = W - bw - 16; y = Hh - bh - 16; seite = ""; }
    b.style.left = Math.round(x) + "px"; b.style.top = Math.round(y) + "px";
    pf.className = "f-pfeil " + seite;
    if (seite === "links" || seite === "rechts") pf.style.top = Math.min(Math.max(16, (box.t + box.b) / 2 - y - 8), bh - 24) + "px", pf.style.left = "";
    else if (seite) pf.style.left = Math.min(Math.max(16, (box.l + box.r) / 2 - x - 8), bw - 24) + "px", pf.style.top = "";
  }
  window.addEventListener("resize", platzieren);
  window.addEventListener("scroll", platzieren, true);

  // ------------------------------------------------------------ Ablauf
  async function start(kapitelId = "") {
    if (!D) return;
    if (T.laeuft) abbauen();
    const app = window.LokanonApp;
    const version = (app.state.status.version || "").replace(/-dev$/, "");
    T.liste = kapitelId === "neu" ? D.schritte.filter((s) => s.seit === version)
      : kapitelId ? D.schritte.filter((s) => s.kapitel === kapitelId) : D.schritte.slice();
    if (!T.liste.length) { T.liste = D.schritte.slice(); }
    T.modus = kapitelId === "neu" ? "neu" : kapitelId ? "kapitel" : "alle";
    T.laeuft = true; T.i = 0; T.kapitelGesehen = new Set(); T.fehler = [];
    await app.uebungBeginnen();
    aufbauen();
    T.tick = setInterval(platzieren, 250);
    await gehe(0, true);
  }
  async function gehe(i, vorbereiten = false) {
    const app = window.LokanonApp;
    if (i < 0) return;
    if (i >= T.liste.length) return abschluss();
    clearTimeout(T.zeigTimer); T.ereignis = null;
    const vorher = T.liste[T.i]; T.i = i; const s = T.liste[i];
    // Kapitelbeginn: Zustand herstellen, den das Kapitel erwartet. In der ganzen Einführung baut ein Kapitel auf dem
    // vorigen auf und braucht das nicht; bei „Neu in …“ und beim Zurückblättern schon.
    const k = kapitelVon(s);
    const wechsel = vorbereiten || (vorher && vorher.kapitel !== s.kapitel);
    const durchgehend = !vorbereiten && T.modus === "alle" && vorher && kapitelFolgt(vorher, s);
    if (wechsel && k && k.vorbereiten && !durchgehend) await k.vorbereiten(app);
    T.kapitelGesehen.add(s.kapitel);
    if (s.ueberspringen && s.ueberspringen(app)) return gehe(i + 1);
    if (s.vorher) await s.vorher(app);
    zeigeText(s, "");
    const el = await zielFinden(s);
    if (el === undefined) { T.fehler.push(`Ziel fehlt: ${s.kapitel} / ${s.titel} (${selektor(s)})`); if (T.selbsttest) return gehe(i + 1); }
    if (el) el.scrollIntoView({ block: "nearest", inline: "nearest" });
    platzieren();
    if (s.art === "tun") {
      T.ereignis = s;
      T.zeigTimer = setTimeout(() => { const z = $("#f-zeig"); if (z) z.hidden = false; platzieren(); }, 20000);
      if (T.selbsttest) { await warte(150); vormachen(); }
    } else if (T.selbsttest) { await warte(120); weiter(); }
  }
  // Kapitel, die direkt aufeinander folgen, bauen aufeinander auf: dann nicht neu vorbereiten
  function kapitelFolgt(a, b) { const ia = D.kapitel.findIndex((k) => k.id === a.kapitel), ib = D.kapitel.findIndex((k) => k.id === b.kapitel); return ib === ia + 1; }
  function zeigeText(s, status) {
    const k = kapitelVon(s); const imKap = T.liste.filter((x) => x.kapitel === s.kapitel); const nr = imKap.indexOf(s) + 1;
    $("#f-stand").textContent = `${k ? k.titel : ""} · ${nr} von ${imKap.length}`;
    $("#f-titel").textContent = s.titel;
    const h = s.hilfe && H[s.hilfe];
    $("#f-text").innerHTML = (s.text ? `<p>${esc(s.text)}</p>` : "") + (h ? `<div>${h.kurz}</div>${h.mehr ? `<p class="f-mehr">${h.mehr}</p>` : ""}` : "");
    $("#f-aufgabe").innerHTML = s.art === "tun" ? (status ? `<b class="f-gut">✓ ${esc(status)}</b>` : `<b>Jetzt Sie:</b> ${esc(s.aufgabe || "")}`) : "";
    $("#f-aufgabe").hidden = s.art !== "tun";
    const w = $("#f-weiter"); w.disabled = s.art === "tun" && !status; w.textContent = T.i === T.liste.length - 1 ? "Fertig" : "Weiter";
    $("#f-zurueck").disabled = T.i === 0;
    $("#f-zeig").hidden = true;
    $("#f-ansage").textContent = `${s.titel}. ${s.text || (h ? h.titel : "")} ${s.art === "tun" ? s.aufgabe || "" : ""}`;
    requestAnimationFrame(platzieren);
    setTimeout(() => { const f = $(s.art === "tun" ? "#f-titel" : "#f-weiter"); if (f && !T.selbsttest && s.art !== "tun") f.focus({ preventScroll: true }); }, 50);
  }
  async function weiter() {
    const s = T.liste[T.i]; if (!s) return;
    if (s.nachher) await s.nachher(window.LokanonApp);
    gehe(T.i + 1);
  }
  async function vormachen() {
    const s = T.liste[T.i]; if (!s || !s.vormachen) return;
    $("#f-zeig").hidden = true;
    try { await s.vormachen(window.LokanonApp); } catch (e) { T.fehler.push(`Vormachen gescheitert: ${s.titel}: ${e.message}`); }
    if (T.selbsttest) {
      for (let t = 0; t < 8000 && T.ereignis === s; t += 100) await warte(100);
      if (T.ereignis === s) { T.fehler.push(`Ereignis „${s.warten}“ kam nicht: ${s.kapitel} / ${s.titel}`); T.ereignis = null; gehe(T.i + 1); }
    }
  }
  document.addEventListener("lokanon", (e) => {
    const s = T.ereignis; if (!T.laeuft || !s) return;
    if (e.detail.art !== s.warten || (s.bedingung && !s.bedingung(e.detail))) return;
    T.ereignis = null; clearTimeout(T.zeigTimer);
    zeigeText(s, "Gut so");
    setTimeout(() => { if (T.liste[T.i] === s) weiter(); }, T.selbsttest ? 200 : 900);
  });
  document.addEventListener("keydown", (e) => {
    if (!T.laeuft) return;
    if (e.key === "Escape" && !document.querySelector("#modal-root:not([hidden])")) { e.preventDefault(); beenden(); }
    if (e.key === "Enter" && document.activeElement && document.activeElement.closest(".f-blase") && !$("#f-weiter").disabled) { e.preventDefault(); weiter(); }
  });
  function abschluss() {
    clearTimeout(T.zeigTimer); T.ereignis = null;
    $("#f-stand").textContent = "Einführung";
    $("#f-titel").textContent = "Geschafft";
    $("#f-text").innerHTML = "<p>Das Beispiel wird jetzt gelöscht. Die Einführung und einzelne Kapitel finden Sie jederzeit oben rechts unter ? → Einführung.</p>";
    $("#f-aufgabe").hidden = true; $("#f-zeig").hidden = true;
    const w = $("#f-weiter"); w.disabled = false; w.textContent = "Beenden"; w.onclick = () => beenden(true);
    T.liste = T.liste.concat([{ ziel: null, kapitel: "", titel: "" }]); T.i = T.liste.length - 1; platzieren();
    if (T.selbsttest) beenden(true);
  }
  async function beenden(fertig = false) {
    if (!T.laeuft) return;
    const gesehen = [...T.kapitelGesehen];
    T.laeuft = false; T.ereignis = null; abbauen();
    const app = window.LokanonApp;
    try { await app.uebungBeenden(); } catch {}
    try {
      const alt = (app.state.cfg.einfuehrung || {}).gesehen || [];
      await app.einstellungMerken({ einfuehrung: { gesehen: [...new Set([...alt, ...(fertig ? gesehen : [])])], version: (app.state.status.version || "").replace(/-dev$/, "") } });
    } catch {}
    if (!T.selbsttest) { const t = document.getElementById("toasts"); if (t) { const d = document.createElement("div"); d.className = "toast"; d.textContent = "Einführung beendet. Jederzeit wieder über ? → Einführung."; t.appendChild(d); setTimeout(() => d.remove(), 4000); } }
  }
  // Kapitel mit „Zeig es mir“ durchspielen und melden, wo ein Ziel fehlt oder ein Ereignis nicht kommt.
  // Ohne Angabe die ganze Einführung; sonst ein Kapitel oder "neu".
  async function selbsttest(kapitelId = "") {
    T.selbsttest = true;
    try {
      await start(kapitelId);
      for (let t = 0; t < 240000 && T.laeuft; t += 250) await warte(250);
    } finally { T.selbsttest = false; }
    return T.fehler.slice();
  }
  window.LokanonTour = { start, beenden, selbsttest, get laeuft() { return T.laeuft; }, get fehler() { return T.fehler.slice(); } };
})();
