/* Simulador de coalicions.
 *
 * Pregunta que respon: si diversos partits s'haguessin presentat en una sola
 * llista, quants escons haurien tret? La suma NO es la resposta, per dues
 * raons independents:
 *
 *  1. La llei d'Hondt no es additiva. Els vots que a cada partit li sobraven
 *     per separat poden sumar prou per a un esco mes. Verificat sobre les 52
 *     circumscripcions i les dues capes, 6.316 parelles: en 437 la coalicio
 *     guanya escons i en cap no en perd.
 *  2. L'electorat no es una massa que es transfereixi sencera. Una part dels
 *     votants d'un partit no segueix la coalicio. Per aixo aqui no hi ha UNA
 *     xifra sino QUATRE ESCENARIS, i el de transferencia perfecta es el sostre,
 *     no la previsio.
 *
 * El Congres s'escull per circumscripcio, aixi que a la comunitat i a l'Estat
 * es reparteix provincia per provincia i despres se suma. Repartir els 350
 * escons de cop a escala estatal donaria una cambra que no s'assembla a la
 * real: castigaria molt menys els partits de vot repartit.
 *
 * El repartiment ha de donar EXACTAMENT el mateix que `model/seats.py`. Si
 * canvia alla, ha de canviar aqui.
 */
(function () {
  "use strict";

  var THRESHOLD = 0.03;

  /* Els escenaris. `keep` es quina part del vot dels socis segueix la llista
     conjunta; el que es perd va a l'abstencio, no a un altre partit, que es el
     supost mes sobri: repartir-lo entre rivals seria inventar-se un transvasament
     que cap dada no sustenta. */
  var SCENARIOS = [
    { id: "full",  keep: 1.00 },
    { id: "mob",   keep: 1.05 },
    { id: "leak",  keep: 0.90 },
    { id: "break", keep: 0.80 }
  ];

  function dhondt(shares, seats) {
    var codes = Object.keys(shares), res = {}, valid = 0, i, p;
    for (i = 0; i < codes.length; i++) { res[codes[i]] = 0; valid += shares[codes[i]]; }
    if (!valid || seats <= 0) return res;
    var running = codes.filter(function (c) { return shares[c] / valid >= THRESHOLD; });
    if (!running.length) return res;
    for (i = 0; i < seats; i++) {
      var best = null, bq = -1, bv = -1;
      for (var j = 0; j < running.length; j++) {
        p = running[j];
        var q = shares[p] / (res[p] + 1);
        // Mateix desempat que a Python: primer el quocient, despres els vots.
        if (q > bq || (q === bq && shares[p] > bv)) { best = p; bq = q; bv = shares[p]; }
      }
      res[best] += 1;
    }
    return res;
  }

  function fmt(n, d) { return n.toFixed(d === undefined ? 1 : d).replace(".", ","); }
  function thousands(n) {
    return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  function boot() {
    var host = document.getElementById("coalition");
    if (!host) return;
    var data;
    try { data = JSON.parse(document.getElementById("coalition-data").textContent); }
    catch (e) { return; }
    if (!data || !data.parties || data.parties.length < 2) return;

    var T = host.dataset;
    var layer = "now";
    var picked = {};

    var list = host.querySelector(".cparties");
    var out = host.querySelector(".cresult");

    /* Reparteix tota la cambra amb un conjunt de partits fusionats.
       `keep` aplica l'escenari: el vot que no segueix la coalicio desapareix
       del recompte, aixi que la resta de partits pugen de percentatge sols. */
    function share(codes, keep) {
      var merged = {}, joined = {};
      codes.forEach(function (c) { joined[c] = true; });
      var totals = {}, detail = [];
      data.constituencies.forEach(function (con) {
        var base = con[layer] || {}, s = {}, sum = 0;
        Object.keys(base).forEach(function (p) {
          if (joined[p]) sum += base[p]; else s[p] = base[p];
        });
        if (sum > 0) s.__coalition__ = sum * keep;
        var got = dhondt(s, con.magnitude);
        detail.push({ code: con.code, name: con.name, got: got, share: s.__coalition__ || 0,
                      magnitude: con.magnitude, valid: con.valid });
        Object.keys(got).forEach(function (p) {
          if (got[p]) merged[p] = (merged[p] || 0) + got[p];
        });
      });
      return { seats: merged, detail: detail };
    }

    function baseline() {
      var totals = {};
      data.constituencies.forEach(function (con) {
        var got = dhondt(con[layer] || {}, con.magnitude);
        Object.keys(got).forEach(function (p) {
          if (got[p]) totals[p] = (totals[p] || 0) + got[p];
        });
      });
      return totals;
    }

    function votesOf(codes, keep) {
      var v = 0;
      data.constituencies.forEach(function (con) {
        var base = con[layer] || {};
        codes.forEach(function (c) { if (base[c]) v += base[c] * con.valid / 100; });
      });
      return v * keep;
    }

    function render() {
      var base = baseline();
      var chosen = data.parties.filter(function (p) { return picked[p.code]; });

      Array.prototype.forEach.call(list.children, function (li) {
        var code = li.dataset.code;
        li.querySelector(".cs").textContent = base[code] || 0;
        li.classList.toggle("on", !!picked[code]);
      });

      if (chosen.length < 2) {
        out.innerHTML = '<p class="note">' + T.hint + "</p>";
        return;
      }

      var codes = chosen.map(function (p) { return p.code; });
      var before = codes.reduce(function (a, c) { return a + (base[c] || 0); }, 0);
      var names = chosen.map(function (p) { return p.name; }).join(" + ");

      var rows = SCENARIOS.map(function (sc) {
        var r = share(codes, sc.keep);
        return { sc: sc, got: r.seats.__coalition__ || 0, seats: r.seats,
                 votes: votesOf(codes, sc.keep) };
      });

      var html = '<p class="csum">' + names + " &middot; " + T.separate
        + ": <b>" + before + "</b> " + (before === 1 ? T.seat : T.seats) + "</p>"
        + '<table class="results scen"><thead><tr><th>' + T.scenario + "</th>"
        + '<th class="n">' + T.votes + "</th>"
        + '<th class="n">' + T.seats + "</th>"
        + '<th class="n">' + T.change + "</th></tr></thead><tbody>";

      rows.forEach(function (r) {
        var d = r.got - before;
        var cls = d > 0 ? "up" : (d < 0 ? "dn" : "");
        html += "<tr><td>" + T["sc_" + r.sc.id] + "</td>"
          + '<td class="n">' + thousands(r.votes) + "</td>"
          + '<td class="n"><b>' + r.got + "</b></td>"
          + '<td class="n ' + cls + '">' + (d > 0 ? "+" : "") + (d || "=") + "</td></tr>";
      });
      html += "</tbody></table>";

      // D'on surten o cap a on van els escons, en l'escenari de suma neta.
      var full = rows[0];
      var moved = [], seen = {};
      Object.keys(full.seats).concat(Object.keys(base)).forEach(function (c) {
        if (c === "__coalition__" || picked[c] || seen[c]) return;
        seen[c] = true;
        var d = (full.seats[c] || 0) - (base[c] || 0);
        if (d !== 0) {
          var p = data.parties.filter(function (x) { return x.code === c; })[0];
          moved.push((p ? p.name : c) + " " + (d > 0 ? "+" : "") + d);
        }
      });
      moved.sort();
      if (moved.length) html += '<p class="note">' + T.from + ": " + moved.join(", ") + "</p>";
      html += '<p class="note">' + T.caveat + "</p>";
      out.innerHTML = html;
    }

    data.parties.forEach(function (p) {
      var li = document.createElement("li");
      li.dataset.code = p.code;
      li.innerHTML = '<span class="sw" style="background:' + p.color + '"></span>'
        + '<span class="cn">' + p.name + "</span><span class=\"cs\"></span>";
      li.setAttribute("role", "button");
      li.setAttribute("tabindex", "0");
      li.addEventListener("click", function () { picked[p.code] = !picked[p.code]; render(); });
      li.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); li.click(); }
      });
      list.appendChild(li);
    });

    Array.prototype.forEach.call(host.querySelectorAll(".clayer button"), function (b) {
      b.addEventListener("click", function () {
        layer = b.dataset.layer;
        Array.prototype.forEach.call(host.querySelectorAll(".clayer button"), function (x) {
          x.classList.toggle("on", x === b);
        });
        render();
      });
    });

    Array.prototype.forEach.call(host.querySelectorAll(".cpreset button"), function (b) {
      b.addEventListener("click", function () {
        picked = {};
        var side = b.dataset.preset;
        data.parties.forEach(function (p) {
          if (side === "left" && p.pos < data.psoe) picked[p.code] = true;
          if (side === "leftpsoe" && p.pos <= data.psoe) picked[p.code] = true;
          if (side === "clear") picked = {};
        });
        render();
      });
    });

    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
})();
