/* Polit Bureau — perfils de votants (21/11/2026).
 *
 * Dades: config/perfils.json (src/politbureau/perfils.py), incrustades a la
 * pagina. Dues vistes: per partit (on te vots a l'abast) i per col·lectiu
 * (la fitxa del grup). L'enllac guarda el partit i el grup triats.
 */
(function () {
  "use strict";
  var el = document.getElementById("perfils-data");
  if (!el) return;
  var X = JSON.parse(el.textContent), D = X.d, META = X.meta;
  var ES = (document.documentElement.lang || "ca").slice(0, 2) === "es", L = ES ? "es" : "ca";
  var $ = function (s) { return document.querySelector(s); };
  var T = ES ? {
    group: "Colectivo", vote: "Voto al partido", reach: "A su alcance", loyal: "Fieles", from: "Vienen de",
    issues: "Les preocupa", all: "Todo el mundo", more: "Ver todos los colectivos", less: "Ver menos",
    opps: "Dónde tiene votos a su alcance", read: "Qué dicen los datos", themes: "Qué les preocupa (problemas de España)",
    personal: "Y a ellos personalmente", votes: "A quién votan", moving: "Cuánto se mueve su voto",
    volatile: "votan según lo que les convenza en cada momento", late: "deciden durante la campaña o el mismo día",
    undecided: "aún no saben a quién votarán", ideol: "Ideología media (1 izquierda, 10 derecha)",
    eco_p: "ven bien su economía personal", eco_s: "ven bien la economía de España", leaders: "Nota a los líderes (1 a 10)",
    pm: "Prefieren de presidente", contest: "Quién se juega más aquí", risk: "Si lo dejan, se van a", avg: "media",
    distinct: "le distingue", n: "entrevistas", none: "–"
  } : {
    group: "Col·lectiu", vote: "Vot al partit", reach: "A l'abast", loyal: "Fidels", from: "Vénen de",
    issues: "Els preocupa", all: "Tothom", more: "Mostra tots els col·lectius", less: "Mostra'n menys",
    opps: "On té vots a l'abast", read: "Què diuen les dades", themes: "Què els preocupa (problemes d'Espanya)",
    personal: "I a ells personalment", votes: "A qui voten", moving: "Quant es mou el seu vot",
    volatile: "voten segons el que els convenci en cada moment", late: "decideixen durant la campanya o el mateix dia",
    undecided: "encara no saben a qui votaran", ideol: "Ideologia mitjana (1 esquerra, 10 dreta)",
    eco_p: "veuen bé la seva economia personal", eco_s: "veuen bé l'economia d'Espanya", leaders: "Nota als líders (1 a 10)",
    pm: "Prefereixen de president", contest: "Qui s'hi juga més", risk: "Si el deixen, se'n van a", avg: "mitjana",
    distinct: "el distingeix", n: "entrevistes", none: "–"
  };
  var PM = ES ? { "N.S.": "No sabe", "N.C.": "No contesta", "Ninguno/a de ellos/as": "Ninguno", "Otro/a": "Otro" } :
    { "N.S.": "No ho sap", "N.C.": "No contesta", "Ninguno/a de ellos/as": "Cap", "Otro/a": "Un altre" };
  function f1(x) { return x === null || x === undefined ? T.none : (Math.round(x * 10) / 10).toFixed(1).replace(".", ","); }
  function nm(k) { return ((META[k] || {}).name || {})[L] || k; }
  function sw(k) { return '<span class="sw" style="background:' + ((META[k] || {}).color || "#999") + '"></span>'; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  var GROUPS = [{ id: "all", label: T.all, dim: "", g: D.total }];
  D.dims.forEach(function (dm) {
    dm.groups.forEach(function (g) {
      var lab = dm.key === "ideology" ? (ES ? "Ideología " : "Ideologia ") + g.label[L] : g.label[L];
      GROUPS.push({ id: g.id, label: lab, dim: dm.title[L], g: g });
    });
  });
  var byId = {};
  GROUPS.forEach(function (x) { byId[x.id] = x; });
  var state = { p: D.focus[0], g: "all", all: false };

  function readHash() {
    var h = decodeURIComponent(location.hash.slice(1));
    h.split("&").forEach(function (kv) {
      var i = kv.indexOf("="), k = kv.slice(0, i), v = kv.slice(i + 1);
      if (k === "p" && D.focus.indexOf(v) >= 0) state.p = v;
      if (k === "g" && byId[v]) state.g = v;
    });
  }
  function writeHash() {
    history.replaceState(null, "", "#p=" + encodeURIComponent(state.p) + "&g=" + encodeURIComponent(state.g));
  }

  /* ------------------------------------------------------------ per partit */
  function opps() {
    var p = state.p, tot = D.total.parties[p] || {};
    $("#pf-h-opps").textContent = T.opps + ": " + nm(p);
    var rows = GROUPS.filter(function (x) { return x.id !== "all" && x.g.parties[p]; })
      .sort(function (a, b) { return b.g.parties[p].reach - a.g.parties[p].reach; });
    var top = rows.slice(0, 3).map(function (x) { return "<b>" + esc(x.label) + "</b> (" + f1(x.g.parties[p].reach) + " %)"; });
    var loyal = rows.filter(function (x) { return x.g.parties[p].loyal !== undefined; })
      .sort(function (a, b) { return a.g.parties[p].loyal - b.g.parties[p].loyal; })[0];
    var src = (tot.from || [])[0];
    $("#pf-summary").innerHTML = (ES ?
      nm(p) + " tiene el <b>" + f1(tot.share) + " %</b> del voto declarado y otro <b>" + f1(tot.reach) + " %</b> de la gente a su alcance" +
        (src ? ", sobre todo " + (src.k === "UND" ? "indecisos" : "votantes de " + nm(src.k)) + " (" + f1(src.p) + " %)" : "") +
        ". Donde más: " + top.join(", ") + "." +
        (loyal ? " Donde menos fieles: " + esc(loyal.label) + " (" + f1(loyal.g.parties[p].loyal) + " % de sus votantes de 2023)." : "")
      : nm(p) + " té el <b>" + f1(tot.share) + " %</b> del vot declarat i un altre <b>" + f1(tot.reach) + " %</b> de la gent a l'abast" +
        (src ? ", sobretot " + (src.k === "UND" ? "indecisos" : "votants de " + nm(src.k)) + " (" + f1(src.p) + " %)" : "") +
        ". On més: " + top.join(", ") + "." +
        (loyal ? " On menys fidels: " + esc(loyal.label) + " (" + f1(loyal.g.parties[p].loyal) + " % dels seus votants del 2023)." : ""));
    var max = rows.length ? rows[0].g.parties[p].reach : 1;
    var t = $("#pf-opps");
    t.querySelector("thead").innerHTML = "<tr><th>" + T.group + '</th><th class="num">' + T.vote + '</th><th class="num">' + T.reach +
      '</th><th class="num">' + T.loyal + "</th><th>" + T.from + "</th><th>" + T.issues + "</th></tr>";
    var shown = state.all ? rows : rows.slice(0, 15);
    t.querySelector("tbody").innerHTML = shown.map(function (x, i) {
      var r = x.g.parties[p];
      return "<tr" + (i >= 5 ? ' class="dim"' : "") + '><td><a href="#" data-g="' + esc(x.id) + '">' + esc(x.label) + "</a> <small>" + esc(x.dim) +
        (r.n_reach < 50 ? " · " + (ES ? "poca muestra" : "poca mostra") + " (" + r.n_reach + ")" : "") + "</small></td>" +
        '<td class="num">' + f1(r.share) + ' %</td><td class="num"><span class="pf-bar" style="width:' + Math.round(50 * r.reach / max) + 'px"></span>' +
        f1(r.reach) + ' %</td><td class="num">' + (r.loyal !== undefined ? f1(r.loyal) + " %" : T.none) + "</td><td>" +
        (r.from || []).slice(0, 2).map(function (s) { return sw(s.k) + nm(s.k) + " <small>" + f1(s.p) + " %</small>"; }).join(" · ") + "</td><td>" +
        (r.issues || []).map(function (s) { return esc(s.l[L]) + " <small>" + f1(s.p) + " %</small>"; }).join(" · ") + "</td></tr>";
    }).join("") + (rows.length > 15 ? '<tr><td colspan="6"><button type="button" id="pf-more">' + (state.all ? T.less : T.more) + "</button></td></tr>" : "");
  }

  /* ------------------------------------------------------------ per col·lectiu */
  function card() {
    var x = byId[state.g], g = x.g, A = D.total, h = "";
    var cmp = function (v, a) {
      if (x.id === "all" || v === null || a === null) return "";
      var d = v - a;
      return " <small>(" + (d >= 0 ? "+" : "−") + f1(Math.abs(d)) + " " + T.avg + ")</small>";
    };
    // Lectura
    var bits = [];
    if (g.distinct.length) bits.push((ES ? "Pesan más que en la media: " : "Pesen més que a la mitjana: ") +
      g.distinct.map(function (s) { return "<b>" + esc(s.l[L]) + "</b> (×" + f1(s.lift) + ")"; }).join(", ") + ".");
    else if (x.id !== "all") bits.push(ES ? "Sus preocupaciones son las de la media." : "Les seves preocupacions són les de la mitjana.");
    var mob = g.volatile - A.volatile;
    if (x.id !== "all" && Math.abs(mob) >= 4) bits.push(mob > 0 ?
      (ES ? "Su voto se mueve más que la media: " : "El seu vot es mou més que la mitjana: ") + f1(g.volatile) + " % " + T.volatile + "." :
      (ES ? "Su voto es más fiel que la media: solo un " : "El seu vot és més fidel que la mitjana: només un ") + f1(g.volatile) + " % " + T.volatile + ".");
    if (x.id !== "all" && g.undecided - A.undecided >= 3) bits.push((ES ? "Hay más indecisos que en la media: " : "Hi ha més indecisos que a la mitjana: ") +
      f1(g.undecided) + " %.");
    var best = D.focus.slice().sort(function (a, b) { return (g.parties[b] || {}).reach - (g.parties[a] || {}).reach; })[0];
    var br = g.parties[best];
    if (br && br.reach) bits.push((ES ? "El partido con más votantes al alcance aquí es " : "El partit amb més votants a l'abast aquí és ") + "<b>" + nm(best) +
      "</b> (" + f1(br.reach) + " %" + (br.from && br.from[0] ? (ES ? ", sobre todo " : ", sobretot ") + (br.from[0].k === "UND" ? (ES ? "indecisos" : "indecisos") :
        (ES ? "votantes de " : "votants de ") + nm(br.from[0].k)) : "") + ")" +
      (br.issues && br.issues[0] ? (ES ? "; a esos votantes les preocupa sobre todo " : "; a aquests votants els preocupa sobretot ") +
        esc(br.issues[0].l[L]).toLowerCase() : "") + ".");
    h += "<h3>" + esc(x.label) + (x.dim ? " <small>" + esc(x.dim) + "</small>" : "") + "</h3><p><small>" + g.n.toLocaleString(ES ? "es-ES" : "ca-ES") +
      " " + T.n + "</small></p>";
    h += '<p class="pf-read"><b>' + T.read + ".</b> " + bits.join(" ") + "</p>";
    h += '<div class="pf-grid"><div><h3>' + T.themes + '</h3><p class="pf-tags">' + g.issues.map(function (s) {
      var hot = g.distinct.some(function (d) { return d.k === s.k; });
      return "<span" + (hot ? ' class="hot" title="' + T.distinct + '"' : "") + ">" + esc(s.l[L]) + " " + f1(s.p) + " %</span>";
    }).join("") + g.distinct.filter(function (d) { return !g.issues.some(function (s) { return s.k === d.k; }); }).map(function (s) {
      return '<span class="hot" title="' + T.distinct + '">' + esc(s.l[L]) + " " + f1(s.p) + " %</span>";
    }).join("") + "</p><h3>" + T.personal + '</h3><p class="pf-tags">' + g.personal.map(function (s) {
      return "<span>" + esc(s.l[L]) + " " + f1(s.p) + " %</span>";
    }).join("") + "</p></div>";
    var vk = Object.keys(g.vote).slice(0, 7);
    var vmax = vk.length ? g.vote[vk[0]] : 1;
    h += "<div><h3>" + T.votes + "</h3>" + vk.map(function (k) {
      return "<div>" + sw(k) + nm(k) + ' <span class="pf-bar" style="width:' + Math.round(90 * g.vote[k] / vmax) + "px;color:" +
        ((META[k] || {}).color || "#999") + '"></span>' + f1(g.vote[k]) + " %" + cmp(g.vote[k], A.vote[k] || 0) + "</div>";
    }).join("") + "</div>";
    h += "<div><h3>" + T.moving + "</h3><ul><li><b>" + f1(g.volatile) + " %</b> " + T.volatile + cmp(g.volatile, A.volatile) + "</li><li><b>" +
      f1(g.late) + " %</b> " + T.late + cmp(g.late, A.late) + "</li><li><b>" + f1(g.undecided) + " %</b> " + T.undecided + cmp(g.undecided, A.undecided) +
      "</li></ul><p>" + T.ideol + ": <b>" + f1(g.ideology) + "</b>" + cmp(g.ideology, A.ideology) + "</p><ul><li><b>" + f1(g.eco_personal) + " %</b> " +
      T.eco_p + cmp(g.eco_personal, A.eco_personal) + "</li><li><b>" + f1(g.eco_spain) + " %</b> " + T.eco_s + cmp(g.eco_spain, A.eco_spain) + "</li></ul></div>";
    h += "<div><h3>" + T.leaders + "</h3><ul>" + g.leaders.map(function (l, i) {
      return "<li>" + esc(l.name) + ": <b>" + f1(l.mean) + "</b>" + cmp(l.mean, A.leaders[i].mean) + "</li>";
    }).join("") + "</ul><h3>" + T.pm + "</h3><ul>" + g.pm.map(function (s) { return "<li>" + esc(PM[s.name] || s.name) + " " + f1(s.p) + " %</li>"; }).join("") +
      "</ul></div></div>";
    h += "<h3>" + T.contest + '</h3><div class="tablewrap"><table class="results"><thead><tr><th>' + (ES ? "Partido" : "Partit") + '</th><th class="num">' +
      T.vote + '</th><th class="num">' + T.reach + '</th><th class="num">' + T.loyal + "</th><th>" + T.from + "</th><th>" + T.risk + "</th><th>" + T.issues +
      "</th></tr></thead><tbody>" + D.focus.slice().sort(function (a, b) { return (g.parties[b] || {}).reach - (g.parties[a] || {}).reach; }).map(function (p) {
        var r = g.parties[p] || {};
        return "<tr><td>" + sw(p) + nm(p) + '</td><td class="num">' + f1(r.share) + ' %</td><td class="num"><b>' + f1(r.reach) + ' %</b></td><td class="num">' +
          (r.loyal !== undefined ? f1(r.loyal) + " %" : T.none) + "</td><td>" + (r.from || []).slice(0, 2).map(function (s) { return nm(s.k) + " <small>" + f1(s.p) + " %</small>"; }).join(" · ") +
          "</td><td>" + (r.risk || []).map(function (s) { return nm(s.k) + " <small>" + f1(s.p) + " %</small>"; }).join(" · ") + "</td><td>" +
          (r.issues || []).slice(0, 2).map(function (s) { return esc(s.l[L]); }).join(" · ") + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    $("#pf-card").innerHTML = h;
  }

  function render() { opps(); card(); writeHash(); }

  function init() {
    readHash();
    var ps = $("#pf-party"), gs = $("#pf-group");
    ps.innerHTML = D.focus.map(function (p) { return '<option value="' + p + '">' + esc(nm(p)) + "</option>"; }).join("");
    var html = "", cur = null;
    GROUPS.forEach(function (x) {
      if (x.dim !== cur) { if (cur !== null) html += "</optgroup>"; if (x.dim) html += '<optgroup label="' + esc(x.dim) + '">'; cur = x.dim; }
      html += '<option value="' + esc(x.id) + '">' + esc(x.label) + "</option>";
    });
    gs.innerHTML = html + "</optgroup>";
    ps.value = state.p; gs.value = state.g;
    ps.addEventListener("change", function () { state.p = ps.value; render(); });
    gs.addEventListener("change", function () { state.g = gs.value; render(); });
    $("#pf-opps").addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("a[data-g]");
      if (a) {
        e.preventDefault(); state.g = a.dataset.g; gs.value = state.g; render();
        $("#pf-card").scrollIntoView({ behavior: "smooth", block: "start" });
      } else if (e.target.id === "pf-more") { state.all = !state.all; opps(); }
    });
    render();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
