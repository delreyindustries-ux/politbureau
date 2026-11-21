/* Polit Bureau — perfils de votants (21/11/2026).
 *
 * Dades: config/perfils.json (src/politbureau/perfils.py), incrustades a la
 * pagina. Tres vistes:
 *   1. per partit: retrat dels seus votants i dels que te a l'abast, que en
 *      pensen de cada politica, i a quins col·lectius te mes vots a l'abast;
 *   2. per col·lectiu: la fitxa sencera del grup;
 *   3. per tema o politica: els col·lectius ordenats.
 * L'enllac guarda el partit, el grup i el tema triats.
 */
(function () {
  "use strict";
  var el = document.getElementById("perfils-data");
  if (!el) return;
  var X = JSON.parse(el.textContent), D = X.d, META = X.meta;
  var ES = (document.documentElement.lang || "ca").slice(0, 2) === "es", L = ES ? "es" : "ca";
  var $ = function (s) { return document.querySelector(s); };
  var T = ES ? {
    group: "Colectivo", vote: "Voto", reach: "A su alcance", people: "≈ personas", loyal: "Fieles", from: "Vienen de",
    issues: "Les preocupa", all: "Todo el mundo", more: "Ver todos los colectivos", less: "Ver menos",
    opps: "Dónde tiene votos a su alcance", read: "Qué dicen los datos", themes: "Qué les preocupa (problemas de España)",
    personal: "Y a ellos personalmente", votes: "A quién votan (voto + simpatía)", moving: "Cuánto se mueve su voto",
    volatile: "votan según lo que les convenza en cada momento", always: "votan siempre al mismo partido",
    late: "deciden durante la campaña o el mismo día", undecided: "aún no saben a quién votarán",
    ideol: "Ideología media (1 izquierda, 10 derecha)", eco_p: "ven bien su economía personal", eco_s: "ven bien la economía de España",
    leaders: "Líderes: nota media (1 a 10) y % que les pone 6 o más", pm: "Prefieren de presidente", contest: "Quién se juega más aquí",
    risk: "Si lo dejan, se van a", avg: "media", distinct: "le distingue", n: "entrevistas", none: "–",
    who: "Quiénes son", size: "del electorado", age: "Edad media", years: "años", turnout: "Participación",
    prob: "probabilidad media de ir a votar (0-10)", sure: "seguro que irán a votar (10 sobre 10)", voted: "votaron en 2023",
    ops: "Qué piensan de cada política", item: "Pregunta", grp: "Este grupo", tot: "Media", diff: "Diferencia",
    direct: "Voto directo (sin simpatía)", recall: "Qué votaron en 2023", close: "Partido más cercano a sus ideas",
    when: "Cuándo deciden el voto", ministers: "Ministros mejor y peor valorados (entre quien los conoce)",
    portrait: "Retrato: quiénes son sus votantes y los que tiene a su alcance", voters: "Sus votantes", total: "Todo el mundo",
    pol: "Qué piensan sus votantes y los que puede ganar", gap: "A su alcance − votantes",
    kpi_share: "del voto declarado", kpi_reach: "votantes a su alcance", kpi_loyal: "de sus votantes de 2023 lo repetirían",
    kpi_sure: "de sus votantes seguro que irá a votar", went: "Los que se le van, a dónde", explore: "Explora un tema o una política",
    pick: "Tema o política", rank: "Colectivos de más a menos", sort_p: "Ordenar por %", sort_n: "Ordenar por personas",
    issue_l: "Problemas de España (% que lo cita)", op_l: "Políticas y opiniones (% a favor o de acuerdo)",
    small: "poca muestra", ideo_dist: "Distribución ideológica"
  } : {
    group: "Col·lectiu", vote: "Vot", reach: "A l'abast", people: "≈ persones", loyal: "Fidels", from: "Vénen de",
    issues: "Els preocupa", all: "Tothom", more: "Mostra tots els col·lectius", less: "Mostra'n menys",
    opps: "On té vots a l'abast", read: "Què diuen les dades", themes: "Què els preocupa (problemes d'Espanya)",
    personal: "I a ells personalment", votes: "A qui voten (vot + simpatia)", moving: "Quant es mou el seu vot",
    volatile: "voten segons el que els convenci en cada moment", always: "voten sempre el mateix partit",
    late: "decideixen durant la campanya o el mateix dia", undecided: "encara no saben a qui votaran",
    ideol: "Ideologia mitjana (1 esquerra, 10 dreta)", eco_p: "veuen bé la seva economia personal", eco_s: "veuen bé l'economia d'Espanya",
    leaders: "Líders: nota mitjana (1 a 10) i % que els posa un 6 o més", pm: "Prefereixen de president", contest: "Qui s'hi juga més",
    risk: "Si el deixen, se'n van a", avg: "mitjana", distinct: "el distingeix", n: "entrevistes", none: "–",
    who: "Qui són", size: "de l'electorat", age: "Edat mitjana", years: "anys", turnout: "Participació",
    prob: "probabilitat mitjana d'anar a votar (0-10)", sure: "segur que aniran a votar (10 sobre 10)", voted: "van votar el 2023",
    ops: "Què pensen de cada política", item: "Pregunta", grp: "Aquest grup", tot: "Mitjana", diff: "Diferència",
    direct: "Vot directe (sense simpatia)", recall: "Què van votar el 2023", close: "Partit més proper a les seves idees",
    when: "Quan decideixen el vot", ministers: "Ministres més ben i més mal valorats (entre qui els coneix)",
    portrait: "Retrat: qui són els seus votants i els que té a l'abast", voters: "Els seus votants", total: "Tothom",
    pol: "Què pensen els seus votants i els que pot guanyar", gap: "A l'abast − votants",
    kpi_share: "del vot declarat", kpi_reach: "votants a l'abast", kpi_loyal: "dels seus votants del 2023 el repetirien",
    kpi_sure: "dels seus votants segur que anirà a votar", went: "Els que se li'n van, on van", explore: "Explora un tema o una política",
    pick: "Tema o política", rank: "Col·lectius de més a menys", sort_p: "Ordena per %", sort_n: "Ordena per persones",
    issue_l: "Problemes d'Espanya (% que el cita)", op_l: "Polítiques i opinions (% a favor o d'acord)",
    small: "poca mostra", ideo_dist: "Distribució ideològica"
  };
  var PM = ES ? { "N.S.": "No sabe", "N.C.": "No contesta", "Ninguno/a de ellos/as": "Ninguno", "Otro/a": "Otro" } :
    { "N.S.": "No ho sap", "N.C.": "No contesta", "Ninguno/a de ellos/as": "Cap", "Otro/a": "Un altre" };
  function f1(x) { return x === null || x === undefined ? T.none : (Math.round(x * 10) / 10).toFixed(1).replace(".", ","); }
  function fp(x) { return x === null || x === undefined ? T.none : f1(x) + " %"; }
  function big(n) {
    if (!n) return "0";
    if (n >= 1e6) return (Math.round(n / 1e5) / 10).toFixed(1).replace(".", ",") + (ES ? " millones" : " milions");
    return Math.round(n / 1000).toLocaleString(ES ? "es-ES" : "ca-ES") + " mil";
  }
  function lc(s) { return s.charAt(0).toLowerCase() + s.slice(1); }
  function nm(k) { return ((META[k] || {}).name || {})[L] || k; }
  function col(k) { return (META[k] || {}).color || "#999"; }
  function sw(k) { return '<span class="sw" style="background:' + col(k) + '"></span>'; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function diff(v, a, unit) {
    if (v === null || v === undefined || a === null || a === undefined) return "";
    var d = v - a, cls = Math.abs(d) >= 5 ? (d > 0 ? "up" : "down") : "";
    return ' <small class="' + cls + '">(' + (d >= 0 ? "+" : "−") + f1(Math.abs(d)) + (unit || "") + ")</small>";
  }
  function bar(v, max, c) {
    return '<span class="pf-bar" style="width:' + Math.max(1, Math.round(80 * (v || 0) / (max || 1))) + "px" + (c ? ";color:" + c : "") + '"></span>';
  }
  var OPS = {};
  D.ops.forEach(function (o) { OPS[o.k] = o; });

  var GROUPS = [{ id: "all", label: T.all, dim: "", g: D.total }];
  D.dims.forEach(function (dm) {
    dm.groups.forEach(function (g) {
      var lab = dm.key === "ideology" ? (ES ? "Ideología " : "Ideologia ") + g.label[L] : g.label[L];
      GROUPS.push({ id: g.id, label: lab, dim: dm.title[L], g: g });
    });
  });
  var byId = {};
  GROUPS.forEach(function (x) { byId[x.id] = x; });
  var state = { p: D.focus[0], g: "all", t: "op:viv_dret", all: false, sort: "p" };

  function readHash() {
    decodeURIComponent(location.hash.slice(1)).split("&").forEach(function (kv) {
      var i = kv.indexOf("="), k = kv.slice(0, i), v = kv.slice(i + 1);
      if (k === "p" && D.focus.indexOf(v) >= 0) state.p = v;
      if (k === "g" && byId[v]) state.g = v;
      if (k === "t" && v) state.t = v;
    });
  }
  function writeHash() {
    history.replaceState(null, "", "#p=" + encodeURIComponent(state.p) + "&g=" + encodeURIComponent(state.g) + "&t=" + encodeURIComponent(state.t));
  }
  function opsTable(rows, heads) {
    var h = '<div class="tablewrap"><table class="results pf-ops"><thead><tr><th>' + T.item + "</th>" +
      heads.map(function (x) { return '<th class="num">' + x + "</th>"; }).join("") + "</tr></thead><tbody>", last = null;
    rows.forEach(function (r) {
      var o = OPS[r.k];
      if (o.b !== last) { h += '<tr class="pf-block"><td colspan="' + (heads.length + 1) + '">' + esc(D.blocks[o.b][L]) + "</td></tr>"; last = o.b; }
      h += "<tr><td>" + esc(o.l[L]) + "</td>" + r.cells.map(function (c) { return '<td class="num">' + c + "</td>"; }).join("") + "</tr>";
    });
    return h + "</tbody></table></div>";
  }

  /* ------------------------------------------------------------ 1. per partit */
  function partyView() {
    var p = state.p, tot = D.total.parties[p] || {}, A = D.total;
    $("#pf-h-party").textContent = nm(p);
    var went = (tot.went || []).map(function (s) { return nm(s.k) + " " + fp(s.p); }).join(", ");
    $("#pf-kpis").innerHTML = '<div class="pf-kpis">' + [
      [fp(tot.share), T.kpi_share],
      [big(tot.reach_people), T.kpi_reach + " (" + fp(tot.reach) + ")"],
      [fp(tot.loyal), T.kpi_loyal],
      [fp(tot.sure_voters), T.kpi_sure]
    ].map(function (k) { return '<div class="pf-kpi"><b>' + k[0] + "</b><span>" + k[1] + "</span></div>"; }).join("") + "</div>" +
      (went ? '<p class="pf-went"><b>' + T.went + ":</b> " + went + "</p>" : "") +
      ((tot.from || []).length ? '<p class="pf-went"><b>' + T.from + ":</b> " + tot.from.map(function (s) { return nm(s.k) + " " + fp(s.p); }).join(", ") +
        ". <b>" + T.risk + ":</b> " + (tot.risk || []).map(function (s) { return nm(s.k) + " " + fp(s.p); }).join(", ") + "</p>" : "");
    var w = tot.who_voters || {}, wr = tot.who_reach || {};
    var h = "<h3>" + T.portrait + '</h3><div class="tablewrap"><table class="results"><thead><tr><th></th><th class="num">' + T.voters +
      '</th><th class="num">' + T.reach + '</th><th class="num">' + T.total + "</th></tr></thead><tbody>" +
      "<tr><td>" + T.age + '</td><td class="num">' + f1(tot.age_voters) + '</td><td class="num">' + f1(tot.age_reach) + '</td><td class="num">' + f1(A.age) + "</td></tr>" +
      "<tr><td>" + T.ideol + '</td><td class="num">' + f1(tot.ideo_voters) + '</td><td class="num">' + f1(tot.ideo_reach) + '</td><td class="num">' + f1(A.ideology) + "</td></tr>" +
      D.compose.map(function (c) {
        return "<tr><td>" + esc(c.l[L]) + '</td><td class="num">' + fp(w[c.k]) + diff(w[c.k], A.who[c.k]) + '</td><td class="num">' + fp(wr[c.k]) +
          diff(wr[c.k], A.who[c.k]) + '</td><td class="num">' + fp(A.who[c.k]) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    h += '<details class="minor"><summary>' + (ES ? "Retrato completo por sexo, edad, estudios, situación laboral, clase, ingresos, religión, municipio y origen" :
      "Retrat complet per sexe, edat, estudis, situació laboral, classe, ingressos, religió, municipi i origen") + '</summary><div class="pf-grid">' +
      (tot.portrait || []).map(function (dm) {
        return "<div><h4>" + esc(dm.title[L]) + '</h4><table class="results pf-mini"><thead><tr><th></th><th class="num">' + T.voters + '</th><th class="num">' +
          T.reach + '</th><th class="num">' + T.total + "</th></tr></thead><tbody>" + dm.cells.map(function (c) {
            return "<tr><td>" + esc(c.l[L]) + '</td><td class="num">' + fp(c.v) + diff(c.v, c.t) + '</td><td class="num">' + fp(c.r) +
              '</td><td class="num">' + fp(c.t) + "</td></tr>";
          }).join("") + "</tbody></table></div>";
      }).join("") + "</div></details>";
    h += '<div class="pf-grid"><div><h4>' + T.issues + " — " + T.voters.toLowerCase() + '</h4><p class="pf-tags">' +
      (tot.issues_voters || []).map(function (s) { return "<span>" + esc(s.l[L]) + " " + fp(s.p) + "</span>"; }).join("") + "</p></div><div><h4>" +
      T.issues + " — " + T.reach.toLowerCase() + '</h4><p class="pf-tags">' +
      (tot.issues || []).map(function (s) { return "<span>" + esc(s.l[L]) + " " + fp(s.p) + "</span>"; }).join("") + "</p></div></div>";
    var ov = tot.ops_voters || {}, orr = tot.ops_reach || {}, more = [], less = [];
    var rows = D.ops.filter(function (o) { return ov[o.k] !== undefined; }).map(function (o) {
      var d = (orr[o.k] !== undefined ? orr[o.k] - ov[o.k] : null);
      if (d !== null && d >= 5 && o.b !== "leaders") more.push([o, d]);
      if (d !== null && d <= -5 && o.b !== "leaders") less.push([o, d]);
      return { k: o.k, cells: [fp(ov[o.k]), fp(orr[o.k]), fp(A.ops[o.k]), d === null ? T.none :
        '<span class="' + (d >= 5 ? "up" : d <= -5 ? "down" : "") + '">' + (d >= 0 ? "+" : "−") + f1(Math.abs(d)) + "</span>"] };
    });
    more.sort(function (a, b) { return b[1] - a[1]; }); less.sort(function (a, b) { return a[1] - b[1]; });
    var txt = (more.length ? (ES ? "Los votantes a su alcance apoyan más que los suyos: " : "Els votants a l'abast donen més suport que els seus a: ") +
      more.slice(0, 3).map(function (x) { return "<b>" + esc(x[0].l[L]) + "</b> (+" + f1(x[1]) + ")"; }).join(", ") + ". " : "") +
      (less.length ? (ES ? "Y menos: " : "I menys a: ") + less.slice(0, 3).map(function (x) { return "<b>" + esc(x[0].l[L]) + "</b> (−" + f1(-x[1]) + ")"; }).join(", ") + "." : "");
    h += "<h3>" + T.pol + "</h3>" + (txt ? '<p class="pf-read">' + txt + "</p>" : "") + opsTable(rows, [T.voters, T.reach, T.tot, T.gap]);
    $("#pf-party-detail").innerHTML = h;
    opps();
  }

  function opps() {
    var p = state.p;
    $("#pf-h-opps").textContent = T.opps + ": " + nm(p);
    var key = state.sort === "n" ? "reach_people" : "reach";
    var rows = GROUPS.filter(function (x) { return x.id !== "all" && x.g.parties[p]; })
      .sort(function (a, b) { return b.g.parties[p][key] - a.g.parties[p][key]; });
    var top = rows.slice(0, 3).map(function (x) { return "<b>" + esc(x.label) + "</b> (" + fp(x.g.parties[p].reach) + ", " + big(x.g.parties[p].reach_people) + ")"; });
    var loyal = rows.filter(function (x) { return x.g.parties[p].loyal !== undefined; })
      .sort(function (a, b) { return a.g.parties[p].loyal - b.g.parties[p].loyal; })[0];
    $("#pf-summary").innerHTML = (ES ? "Donde más: " : "On més: ") + top.join(", ") + "." +
      (loyal ? (ES ? " Donde menos fieles: " : " On menys fidels: ") + esc(loyal.label) + " (" + fp(loyal.g.parties[p].loyal) + ")." : "");
    var max = rows.length ? rows[0].g.parties[p][key] : 1;
    var t = $("#pf-opps");
    t.querySelector("thead").innerHTML = "<tr><th>" + T.group + '</th><th class="num">' + T.vote + '</th><th class="num">' + T.reach +
      '</th><th class="num">' + T.people + '</th><th class="num">' + T.loyal + "</th><th>" + T.from + "</th><th>" + T.issues + "</th></tr>";
    var shown = state.all ? rows : rows.slice(0, 20);
    t.querySelector("tbody").innerHTML = shown.map(function (x, i) {
      var r = x.g.parties[p];
      return "<tr" + (i >= 5 ? ' class="dim"' : "") + '><td><a href="#" data-g="' + esc(x.id) + '">' + esc(x.label) + "</a> <small>" + esc(x.dim) +
        (r.n_reach < 50 ? " · " + T.small + " (" + r.n_reach + ")" : "") + "</small></td>" +
        '<td class="num">' + fp(r.share) + '</td><td class="num">' + (key === "reach" ? bar(r.reach, max) : "") + fp(r.reach) + '</td><td class="num">' +
        (key === "reach_people" ? bar(r.reach_people, max) : "") + big(r.reach_people) + '</td><td class="num">' + fp(r.loyal) + "</td><td>" +
        (r.from || []).slice(0, 2).map(function (s) { return sw(s.k) + nm(s.k) + " <small>" + fp(s.p) + "</small>"; }).join(" · ") + "</td><td>" +
        (r.issues || []).slice(0, 3).map(function (s) { return esc(s.l[L]) + " <small>" + fp(s.p) + "</small>"; }).join(" · ") + "</td></tr>";
    }).join("") + (rows.length > 20 ? '<tr><td colspan="7"><button type="button" id="pf-more">' + (state.all ? T.less : T.more) + "</button></td></tr>" : "");
    $("#pf-sort").textContent = state.sort === "n" ? T.sort_p : T.sort_n;
  }

  /* ------------------------------------------------------------ 2. per col·lectiu */
  function card() {
    var x = byId[state.g], g = x.g, A = D.total, isAll = x.id === "all", h = "";
    var cmp = function (v, a, u) { return isAll ? "" : diff(v, a, u); };
    var bits = [];
    if (!isAll) bits.push((ES ? "Son el " : "Són el ") + fp(g.size) + " " + T.size + " (≈ " + big(g.people) + (ES ? " de personas)." : " de persones)."));
    if (g.distinct.length) bits.push((ES ? "Pesan más que en la media: " : "Pesen més que a la mitjana: ") +
      g.distinct.map(function (s) { return "<b>" + esc(s.l[L]) + "</b> (×" + f1(s.lift) + ")"; }).join(", ") + ".");
    else if (!isAll) bits.push(ES ? "Sus preocupaciones son las de la media." : "Les seves preocupacions són les de la mitjana.");
    var opd = D.ops.filter(function (o) { return g.ops[o.k] !== undefined && A.ops[o.k] !== undefined && o.b !== "leaders"; })
      .map(function (o) { return [o, g.ops[o.k] - A.ops[o.k]]; }).sort(function (a, b) { return Math.abs(b[1]) - Math.abs(a[1]); })
      .filter(function (z) { return Math.abs(z[1]) >= 5; }).slice(0, 3);
    if (!isAll && opd.length) bits.push((ES ? "Donde más se separan de la media: " : "On més s'aparten de la mitjana: ") + opd.map(function (z) {
      return esc(z[0].l[L]) + " (" + fp(g.ops[z[0].k]) + ", " + (z[1] > 0 ? "+" : "−") + f1(Math.abs(z[1])) + ")";
    }).join("; ") + ".");
    var mob = g.volatile - A.volatile;
    if (!isAll && Math.abs(mob) >= 4) bits.push(mob > 0 ?
      (ES ? "Su voto se mueve más que la media: " : "El seu vot es mou més que la mitjana: ") + fp(g.volatile) + " " + T.volatile + "." :
      (ES ? "Su voto es más fiel que la media: solo un " : "El seu vot és més fidel que la mitjana: només un ") + fp(g.volatile) + " " + T.volatile + ".");
    if (!isAll && g.undecided - A.undecided >= 3) bits.push((ES ? "Hay más indecisos que en la media: " : "Hi ha més indecisos que a la mitjana: ") + fp(g.undecided) + ".");
    if (!isAll && g.sure - A.sure <= -5) bits.push((ES ? "Votan menos: solo un " : "Voten menys: només un ") + fp(g.sure) + " " + T.sure + ".");
    var best = D.focus.slice().sort(function (a, b) { return (g.parties[b] || {}).reach - (g.parties[a] || {}).reach; })[0];
    var br = g.parties[best];
    if (br && br.reach) bits.push((ES ? "El partido con más votantes al alcance aquí es " : "El partit amb més votants a l'abast aquí és ") + "<b>" + nm(best) +
      "</b> (" + fp(br.reach) + ", ≈ " + big(br.reach_people) + (br.from && br.from[0] ? (ES ? ", sobre todo " : ", sobretot ") + (br.from[0].k === "UND" ? "indecisos" :
        (ES ? "votantes de " : "votants de ") + nm(br.from[0].k)) : "") + ")" +
      (br.issues && br.issues[0] ? (ES ? "; a esos votantes les preocupa sobre todo " : "; a aquests votants els preocupa sobretot ") +
        lc(esc(br.issues[0].l[L])) : "") + ".");
    h += "<h3>" + esc(x.label) + (x.dim ? " <small>" + esc(x.dim) + "</small>" : "") + "</h3><p><small>" + g.n.toLocaleString(ES ? "es-ES" : "ca-ES") +
      " " + T.n + "</small></p>";
    h += '<p class="pf-read"><b>' + T.read + ".</b> " + bits.join(" ") + "</p>";
    h += '<div class="pf-grid"><div><h4>' + T.who + "</h4><ul><li><b>" + fp(g.size) + "</b> " + T.size + " (≈ " + big(g.people) + ")</li><li>" + T.age + ": <b>" +
      f1(g.age) + "</b> " + T.years + cmp(g.age, A.age) + "</li>" + D.compose.map(function (c) {
        return "<li>" + esc(c.l[L]) + ": <b>" + fp(g.who[c.k]) + "</b>" + cmp(g.who[c.k], A.who[c.k]) + "</li>";
      }).join("") + "</ul></div><div><h4>" + T.turnout + "</h4><ul><li><b>" + f1(g.prob) + "</b> " + T.prob + cmp(g.prob, A.prob) + "</li><li><b>" + fp(g.sure) +
      "</b> " + T.sure + cmp(g.sure, A.sure) + "</li><li><b>" + fp(g.voted23) + "</b> " + T.voted + cmp(g.voted23, A.voted23) + "</li></ul><h4>" + T.moving +
      "</h4><ul><li><b>" + fp(g.volatile) + "</b> " + T.volatile + cmp(g.volatile, A.volatile) + "</li><li><b>" + fp(g.always) + "</b> " + T.always + cmp(g.always, A.always) +
      "</li><li><b>" + fp(g.undecided) + "</b> " + T.undecided + cmp(g.undecided, A.undecided) + "</li></ul><h4>" + T.when + "</h4><ul>" + g.when.map(function (w, i) {
        return "<li>" + esc(w.l[L]) + ": <b>" + fp(w.p) + "</b>" + cmp(w.p, A.when[i].p) + "</li>";
      }).join("") + "</ul></div>";
    var imax = g.issues.length ? g.issues[0].p : 1;
    h += "<div><h4>" + T.themes + '</h4><table class="pf-mini">' + g.issues.map(function (s) {
      var hot = g.distinct.some(function (d) { return d.k === s.k; });
      return "<tr" + (hot ? ' class="hot" title="' + T.distinct + '"' : "") + "><td>" + esc(s.l[L]) + '</td><td class="num">' + bar(s.p, imax) + fp(s.p) +
        (isAll || !s.lift ? "" : ' <small class="' + (s.lift >= 1.25 ? "up" : s.lift <= 0.8 ? "down" : "") + '">×' + f1(s.lift) + "</small>") + "</td></tr>";
    }).join("") + "</table><h4>" + T.personal + '</h4><p class="pf-tags">' + g.personal.map(function (s) {
      return "<span>" + esc(s.l[L]) + " " + fp(s.p) + "</span>";
    }).join("") + "</p></div>";
    var vk = Object.keys(g.vote).slice(0, 8), vmax = vk.length ? g.vote[vk[0]] : 1;
    var tags = function (o) { return Object.keys(o).map(function (k) { return "<span>" + nm(k) + " " + fp(o[k]) + "</span>"; }).join(""); };
    h += "<div><h4>" + T.votes + "</h4>" + vk.map(function (k) {
      return '<div class="pf-row">' + sw(k) + nm(k) + " " + bar(g.vote[k], vmax, col(k)) + fp(g.vote[k]) + cmp(g.vote[k], A.vote[k] || 0) + "</div>";
    }).join("") + "<h4>" + T.direct + '</h4><p class="pf-tags">' + tags(g.direct) + "</p><h4>" + T.recall + '</h4><p class="pf-tags">' + tags(g.recall) +
      "</p><h4>" + T.close + '</h4><p class="pf-tags">' + tags(g.close) + "</p></div>";
    var lab = ["1-2", "3-4", "5-6", "7-8", "9-10"], dmax = Math.max.apply(null, g.ideo_dist);
    h += "<div><h4>" + T.ideol + ": " + f1(g.ideology) + cmp(g.ideology, A.ideology) + "</h4><h4>" + T.ideo_dist + '</h4><table class="pf-mini">' +
      g.ideo_dist.map(function (v, i) { return "<tr><td>" + lab[i] + '</td><td class="num">' + bar(v, dmax) + fp(v) + cmp(v, A.ideo_dist[i]) + "</td></tr>"; }).join("") +
      "</table><ul><li><b>" + fp(g.eco_personal) + "</b> " + T.eco_p + cmp(g.eco_personal, A.eco_personal) + "</li><li><b>" + fp(g.eco_spain) + "</b> " + T.eco_s +
      cmp(g.eco_spain, A.eco_spain) + "</li></ul></div>";
    h += "<div><h4>" + T.leaders + "</h4><ul>" + g.leaders.map(function (l, i) {
      return "<li>" + esc(l.name) + ": <b>" + f1(l.mean) + "</b>" + cmp(l.mean, A.leaders[i].mean) + " · " + fp(l.good) + "</li>";
    }).join("") + "</ul><h4>" + T.pm + "</h4><ul>" + g.pm.map(function (s) { return "<li>" + esc(PM[s.name] || s.name) + " " + fp(s.p) + "</li>"; }).join("") +
      "</ul>" + (g.ministers.length ? "<h4>" + T.ministers + "</h4><ul>" + g.ministers.map(function (m) {
        return "<li>" + esc(m.name) + ": <b>" + f1(m.mean) + "</b></li>";
      }).join("") + "</ul>" : "") + "</div></div>";
    var rows = D.ops.filter(function (o) { return g.ops[o.k] !== undefined; }).map(function (o) {
      return { k: o.k, cells: [fp(g.ops[o.k]), fp(A.ops[o.k]), isAll ? T.none : diff(g.ops[o.k], A.ops[o.k]).replace(/[()]/g, "")] };
    });
    h += "<h4>" + T.ops + "</h4>" + opsTable(rows, [T.grp, T.tot, T.diff]);
    h += "<h4>" + T.contest + '</h4><div class="tablewrap"><table class="results"><thead><tr><th>' + (ES ? "Partido" : "Partit") + '</th><th class="num">' +
      T.vote + '</th><th class="num">' + T.reach + '</th><th class="num">' + T.people + '</th><th class="num">' + T.loyal + "</th><th>" + T.from + "</th><th>" + T.risk +
      "</th><th>" + T.issues + "</th></tr></thead><tbody>" + D.focus.slice().sort(function (a, b) { return (g.parties[b] || {}).reach - (g.parties[a] || {}).reach; }).map(function (p) {
        var r = g.parties[p] || {};
        return "<tr><td>" + sw(p) + nm(p) + '</td><td class="num">' + fp(r.share) + '</td><td class="num"><b>' + fp(r.reach) + '</b></td><td class="num">' +
          big(r.reach_people) + '</td><td class="num">' + fp(r.loyal) + "</td><td>" + (r.from || []).slice(0, 2).map(function (s) { return nm(s.k) + " <small>" + fp(s.p) + "</small>"; }).join(" · ") +
          "</td><td>" + (r.risk || []).map(function (s) { return nm(s.k) + " <small>" + fp(s.p) + "</small>"; }).join(" · ") + "</td><td>" +
          (r.issues || []).slice(0, 3).map(function (s) { return esc(s.l[L]); }).join(" · ") + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    $("#pf-card").innerHTML = h;
  }

  /* ------------------------------------------------------------ 3. per tema */
  var TOPICS = [];
  (function () {
    var seen = {};
    GROUPS.forEach(function (x) { x.g.issues.forEach(function (s) { if (!seen[s.k]) seen[s.k] = s.l; }); });
    D.total.issues.forEach(function (s) { TOPICS.push({ id: "is:" + s.k, l: s.l[L], kind: "issue" }); delete seen[s.k]; });
    Object.keys(seen).forEach(function (k) { TOPICS.push({ id: "is:" + k, l: seen[k][L], kind: "issue" }); });
    D.ops.forEach(function (o) { TOPICS.push({ id: "op:" + o.k, l: o.l[L], kind: "op" }); });
  })();
  function topicValue(g, id) {
    if (id.slice(0, 3) === "op:") return g.ops[id.slice(3)];
    var k = id.slice(3), s = g.issues.filter(function (z) { return z.k === k; })[0];
    return s ? s.p : undefined;
  }
  function topicView() {
    var id = state.t, rows = GROUPS.filter(function (x) { return x.id !== "all" && topicValue(x.g, id) !== undefined; })
      .sort(function (a, b) { return topicValue(b.g, id) - topicValue(a.g, id); });
    var avg = topicValue(D.total, id), max = rows.length ? topicValue(rows[0].g, id) : 1;
    var note = id.slice(0, 3) === "is:" ? (ES ? "Solo aparecen los grupos donde el tema está entre sus doce primeros." :
      "Només hi surten els grups on el tema és entre els seus dotze primers.") : "";
    $("#pf-topic").innerHTML = "<p>" + T.tot + ": <b>" + fp(avg) + "</b>. " + note + '</p><div class="tablewrap"><table class="results"><tbody>' + rows.map(function (x) {
      var v = topicValue(x.g, id);
      return '<tr><td><a href="#" data-g="' + esc(x.id) + '">' + esc(x.label) + "</a> <small>" + esc(x.dim) + '</small></td><td class="num">' + bar(v, max) + fp(v) +
        diff(v, avg) + "</td></tr>";
    }).join("") + "</tbody></table></div>";
  }

  function render() { partyView(); card(); topicView(); writeHash(); }

  function init() {
    readHash();
    var ps = $("#pf-party"), gs = $("#pf-group"), ts = $("#pf-topicsel");
    ps.innerHTML = D.focus.map(function (p) { return '<option value="' + p + '">' + esc(nm(p)) + "</option>"; }).join("");
    var html = "", cur = null;
    GROUPS.forEach(function (x) {
      if (x.dim !== cur) { if (cur) html += "</optgroup>"; if (x.dim) html += '<optgroup label="' + esc(x.dim) + '">'; cur = x.dim; }
      html += '<option value="' + esc(x.id) + '">' + esc(x.label) + "</option>";
    });
    gs.innerHTML = html + (cur ? "</optgroup>" : "");
    ts.innerHTML = '<optgroup label="' + esc(T.op_l) + '">' + TOPICS.filter(function (t) { return t.kind === "op"; }).map(function (t) {
      return '<option value="' + esc(t.id) + '">' + esc(t.l) + "</option>";
    }).join("") + '</optgroup><optgroup label="' + esc(T.issue_l) + '">' + TOPICS.filter(function (t) { return t.kind === "issue"; }).map(function (t) {
      return '<option value="' + esc(t.id) + '">' + esc(t.l) + "</option>";
    }).join("") + "</optgroup>";
    if (!TOPICS.some(function (t) { return t.id === state.t; })) state.t = TOPICS[0].id;
    ps.value = state.p; gs.value = state.g; ts.value = state.t;
    ps.addEventListener("change", function () { state.p = ps.value; render(); });
    gs.addEventListener("change", function () { state.g = gs.value; render(); });
    ts.addEventListener("change", function () { state.t = ts.value; render(); });
    $("#pf-sort").addEventListener("click", function () { state.sort = state.sort === "n" ? "p" : "n"; opps(); });
    var goGroup = function (e) {
      var a = e.target.closest && e.target.closest("a[data-g]");
      if (a) {
        e.preventDefault(); state.g = a.dataset.g; gs.value = state.g; render();
        $("#pf-cardsec").scrollIntoView({ behavior: "smooth", block: "start" });
        return true;
      }
      return false;
    };
    $("#pf-opps").addEventListener("click", function (e) {
      if (!goGroup(e) && e.target.id === "pf-more") { state.all = !state.all; opps(); }
    });
    $("#pf-topic").addEventListener("click", goGroup);
    render();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
